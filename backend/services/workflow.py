import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from datetime import datetime

from backend.database import async_session_maker
from backend.config import settings
from backend.models import Job, JobStatus
from backend.services.alphafold import run_alphafold, extract_quality_metrics, ModelPreset, DatabasePreset
from backend.services.docking import run_autodock_vina
from backend.services.ai_report import generate_ai_report
from backend.services.blockchain import store_on_blockchain
from backend.services.binding_site import analyze_binding_sites
from backend.services.molecular_properties import calculate_molecular_properties

logger = logging.getLogger(__name__)

async def update_job_status(
    job_id: str,
    status: JobStatus,
    error_message: str = None,
    progress: float = None,
    progress_message: str = None,
    **kwargs
):
    """
    Update job status in database with optional progress tracking.
    
    Args:
        job_id: Job identifier
        status: New job status
        error_message: Optional error message
        progress: Progress percentage (0-100)
        progress_message: Optional human-readable progress message
        **kwargs: Additional fields to update
    """
    from sqlalchemy.exc import SQLAlchemyError
    from backend.exceptions import DatabaseError
    
    async with async_session_maker() as session:
        try:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if not job:
                logger.warning(f"Job {job_id} not found when updating status")
                return
            
            job.status = status
            if error_message:
                job.error_message = error_message
            
            # Update progress if provided
            if progress is not None:
                if hasattr(job, 'progress'):
                    job.progress = max(0, min(100, progress))  # Clamp to 0-100
            
            # Update additional fields
            for key, value in kwargs.items():
                if hasattr(job, key):
                    try:
                        setattr(job, key, value)
                    except Exception as e:
                        logger.warning(f"Failed to set {key} for job {job_id}: {str(e)}")
            
            if status == JobStatus.COMPLETED:
                job.completed_at = datetime.now()
                if progress is None:
                    # Ensure progress is 100% on completion
                    if hasattr(job, 'progress'):
                        job.progress = 100.0
            
            await session.commit()
            log_msg = f"Job {job_id} status updated to {status}"
            if progress is not None:
                log_msg += f" (progress: {progress:.1f}%)"
            if progress_message:
                log_msg += f" - {progress_message}"
            logger.info(log_msg)
        except SQLAlchemyError as e:
            logger.error(f"Database error updating job {job_id} status: {str(e)}", exc_info=True)
            await session.rollback()
            raise DatabaseError(f"Failed to update job status: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating job {job_id} status: {str(e)}", exc_info=True)
            await session.rollback()
            raise

async def run_alphafold_then_dock(
    job_id: str,
    sequence: str,
    ligand_files: List[str],
    parameters: Dict[str, Any]
):
    """
    Complete Drug Discovery Workflow: 
    1. Input Sequence → 2. AlphaFold Prediction → 3. Quality Assessment → 
    4. Binding Site Analysis → 5. Molecular Docking → 6. Therapeutic Insights
    
    Args:
        job_id: Unique job identifier
        sequence: Protein amino acid sequence
        ligand_files: List of ligand file contents
        parameters: Docking parameters
    """
    try:
        # Step 1: Input Sequence (0-5% progress)
        logger.info(f"Starting complete workflow for job {job_id}")
        await update_job_status(
            job_id, 
            JobStatus.SUBMITTED,
            progress=0.0,
            progress_message="Input sequence validated and ready for processing..."
        )
        
        # Step 2: AlphaFold Structure Prediction (5-35% progress)
        logger.info(f"Starting AlphaFold prediction for job {job_id}")
        await update_job_status(
            job_id, 
            JobStatus.PREDICTING_STRUCTURE,
            progress=5.0,
            progress_message="Initializing AlphaFold structure prediction..."
        )
        
        # Progress callback for status updates
        async def progress_callback(status: str, progress: float):
            logger.info(f"AlphaFold progress for job {job_id}: {status} ({progress*100:.1f}%)")
            await update_job_status(
                job_id,
                JobStatus.PREDICTING_STRUCTURE,
                progress=5.0 + (progress * 30.0),  # Map to 5-35% range
                progress_message=f"AlphaFold: {status}"
            )
        
        predicted_pdb, plddt_score, quality_metrics = await run_alphafold(
            sequence, 
            job_id,
            progress_callback=progress_callback
        )
        
        await update_job_status(
            job_id,
            JobStatus.STRUCTURE_PREDICTED,
            progress=35.0,
            progress_message=f"AlphaFold prediction completed (pLDDT: {plddt_score:.2f})",
            predicted_pdb_path=str(predicted_pdb),
            plddt_score=plddt_score
        )
        
        logger.info(f"Structure predicted for job {job_id}, pLDDT: {plddt_score:.2f}")
        
        # Step 3: Quality Assessment (35-45% progress)
        logger.info(f"Performing quality assessment for job {job_id}")
        await update_job_status(
            job_id,
            JobStatus.STRUCTURE_PREDICTED,
            progress=35.0,
            progress_message="Assessing structure quality and confidence..."
        )
        
        # Extract comprehensive quality metrics
        if not quality_metrics:
            quality_metrics = await extract_quality_metrics(predicted_pdb)
        
        await update_job_status(
            job_id,
            JobStatus.STRUCTURE_PREDICTED,
            progress=45.0,
            progress_message=f"Quality assessment completed (pLDDT: {plddt_score:.2f}, "
                           f"Confidence: {'High' if plddt_score > 90 else 'Medium' if plddt_score > 70 else 'Low'})",
            quality_metrics=quality_metrics
        )
        
        logger.info(f"Quality assessment completed for job {job_id}")
        
        # Step 4: Binding Site Analysis (45-55% progress)
        logger.info(f"Analyzing binding sites for job {job_id}")
        await update_job_status(
            job_id,
            JobStatus.STRUCTURE_PREDICTED,
            progress=45.0,
            progress_message="Identifying potential drug binding sites..."
        )
        
        binding_site_results = await analyze_binding_sites(
            pdb_path=predicted_pdb,
            job_id=job_id
        )
        
        # Update docking parameters with binding site coordinates if not provided
        if binding_site_results.get("binding_site_coordinates") and not parameters.get("center_x"):
            coords = binding_site_results["binding_site_coordinates"]
            parameters["center_x"] = coords.get("center_x", parameters.get("center_x", 0.0))
            parameters["center_y"] = coords.get("center_y", parameters.get("center_y", 0.0))
            parameters["center_z"] = coords.get("center_z", parameters.get("center_z", 0.0))
            if not parameters.get("size_x"):
                estimated_size = coords.get("estimated_size", 20.0)
                parameters["size_x"] = estimated_size
                parameters["size_y"] = estimated_size
                parameters["size_z"] = estimated_size
        
        await update_job_status(
            job_id,
            JobStatus.DOCKING,
            progress=55.0,
            progress_message=f"Binding site analysis completed ({binding_site_results.get('num_pockets', 0)} pockets found, "
                           f"druggability: {binding_site_results.get('druggability_score', 0.0):.2f})"
        )
        
        logger.info(f"Binding site analysis completed for job {job_id}: {binding_site_results.get('num_pockets', 0)} pockets found")
        
        # Step 5: Molecular Docking (55-75% progress)
        logger.info(f"Starting docking for job {job_id}")
        await update_job_status(
            job_id, 
            JobStatus.DOCKING,
            progress=55.0,
            progress_message="Preparing protein and ligands for molecular docking..."
        )
        
        docking_results = await run_autodock_vina(
            protein_pdb_path=predicted_pdb,
            ligand_files=ligand_files,
            parameters=parameters,
            job_id=job_id
        )
        
        # Calculate molecular properties for top ligands
        molecular_properties = {}
        if docking_results.get("results"):
            valid_results = [r for r in docking_results["results"] if r.get("binding_affinity") is not None]
            valid_results.sort(key=lambda x: x.get("binding_affinity", float('inf')))
            
            # Calculate properties for top 3 ligands
            for result in valid_results[:3]:
                ligand_idx = result.get("ligand_index", 0)
                if ligand_idx < len(ligand_files):
                    try:
                        props = calculate_molecular_properties(
                            ligand_sdf=ligand_files[ligand_idx],
                            ligand_name=result.get("ligand_name", f"ligand_{ligand_idx}")
                        )
                        molecular_properties[result.get("ligand_name")] = props
                    except Exception as e:
                        logger.warning(f"Failed to calculate molecular properties for {result.get('ligand_name')}: {str(e)}")
        
        docking_results["molecular_properties"] = molecular_properties
        
        best_score = docking_results.get("best_score")
        best_score_str = f"{best_score:.2f}" if best_score is not None else "N/A"
        await update_job_status(
            job_id,
            JobStatus.ANALYZING,
            progress=75.0,
            progress_message=f"Docking completed (best score: {best_score_str} kcal/mol)",
            docking_results=docking_results,
            top_binding_score=best_score
        )
        
        logger.info(f"Docking completed for job {job_id}, best score: {best_score_str}")
        
        # Step 6: Therapeutic Insights (75-95% progress)
        logger.info(f"Generating therapeutic insights for job {job_id}")
        await update_job_status(
            job_id,
            JobStatus.ANALYZING,
            progress=75.0,
            progress_message="Generating AI-powered therapeutic insights and clinical analysis..."
        )
        
        # Enhance docking results with binding site and quality information
        enhanced_docking_results = {
            **docking_results,
            "binding_site_analysis": binding_site_results,
            "quality_metrics": quality_metrics,
            "plddt_score": plddt_score
        }
        
        ai_report = await generate_ai_report(
            job_id=job_id,
            sequence=sequence,
            plddt_score=plddt_score,
            docking_results=enhanced_docking_results,
            stakeholder="researcher"
        )
        
        await update_job_status(
            job_id,
            JobStatus.ANALYZING,
            progress=95.0,
            progress_message="Therapeutic insights generated, storing on blockchain...",
            ai_report_content=ai_report
        )
        
        logger.info(f"Therapeutic insights generated for job {job_id}")
        
        # Blockchain Verification (95-100% progress)
        logger.info(f"Storing verification on blockchain for job {job_id}")
        
        blockchain_tx = await store_on_blockchain(
            job_id=job_id,
            predicted_pdb_path=predicted_pdb,
            report_content=ai_report
        )
        
        await update_job_status(
            job_id,
            JobStatus.COMPLETED,
            progress=100.0,
            progress_message="Complete drug discovery workflow finished successfully",
            blockchain_tx_hash=blockchain_tx.get("tx_hash"),
            structure_hash=blockchain_tx.get("structure_hash"),
            report_hash=blockchain_tx.get("report_hash")
        )
        
        logger.info(f"Job {job_id} completed successfully - Complete workflow finished")
        
    except Exception as e:
        logger.error(f"Error in workflow for job {job_id}: {str(e)}", exc_info=True)
        try:
            await update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e)
            )
        except Exception as status_error:
            logger.error(f"Failed to update job status to FAILED for job {job_id}: {str(status_error)}", exc_info=True)
        raise

async def run_docking_only(
    job_id: str,
    protein_pdb: str,
    ligand_files: List[str],
    parameters: Dict[str, Any]
):
    """
    Docking-only workflow: Use existing PDB → Molecular docking → AI report
    
    Args:
        job_id: Unique job identifier
        protein_pdb: PDB file content as string
        ligand_files: List of ligand file contents
        parameters: Docking parameters
    """
    try:
        # Step 1: Save uploaded PDB file
        logger.info(f"Saving uploaded PDB for job {job_id}")
        
        import aiofiles
        from backend.exceptions import FileProcessingError
        
        try:
            pdb_dir = settings.UPLOADS_DIR / job_id
            pdb_dir.mkdir(parents=True, exist_ok=True)
            pdb_path = pdb_dir / "protein.pdb"
            
            async with aiofiles.open(pdb_path, 'w') as f:
                await f.write(protein_pdb)
        except OSError as e:
            logger.error(f"Failed to create directory or write PDB file for job {job_id}: {str(e)}")
            raise FileProcessingError(f"Failed to save uploaded PDB file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error saving PDB file for job {job_id}: {str(e)}", exc_info=True)
            raise FileProcessingError(f"Unexpected error saving PDB file: {str(e)}")
        
        await update_job_status(
            job_id,
            JobStatus.DOCKING,
            progress=0.0,
            progress_message="Preparing protein and ligands for docking...",
            protein_pdb_path=str(pdb_path)
        )
        
        # Step 2: Molecular Docking (0-70% progress)
        logger.info(f"Starting docking for job {job_id}")
        
        docking_results = await run_autodock_vina(
            protein_pdb_path=pdb_path,
            ligand_files=ligand_files,
            parameters=parameters,
            job_id=job_id
        )
        
        best_score = docking_results.get("best_score")
        best_score_str = f"{best_score:.2f}" if best_score is not None else "N/A"
        await update_job_status(
            job_id,
            JobStatus.ANALYZING,
            progress=70.0,
            progress_message=f"Docking completed (best score: {best_score_str} kcal/mol)",
            docking_results=docking_results,
            top_binding_score=best_score
        )
        
        logger.info(f"Docking completed for job {job_id}, best score: {best_score_str}")
        
        # Step 3: AI Report Generation (70-95% progress)
        logger.info(f"Generating AI report for job {job_id}")
        await update_job_status(
            job_id,
            JobStatus.ANALYZING,
            progress=70.0,
            progress_message="Generating AI-powered analysis report..."
        )
        
        ai_report = await generate_ai_report(
            job_id=job_id,
            sequence=None,
            plddt_score=None,
            docking_results=docking_results,
            stakeholder="researcher"
        )
        
        await update_job_status(
            job_id,
            JobStatus.ANALYZING,
            progress=95.0,
            progress_message="AI report generated, storing on blockchain...",
            ai_report_content=ai_report
        )
        
        # Step 4: Blockchain Verification (95-100% progress)
        logger.info(f"Storing verification on blockchain for job {job_id}")
        
        blockchain_tx = await store_on_blockchain(
            job_id=job_id,
            predicted_pdb_path=pdb_path,
            report_content=ai_report
        )
        
        await update_job_status(
            job_id,
            JobStatus.COMPLETED,
            progress=100.0,
            progress_message="Job completed successfully",
            blockchain_tx_hash=blockchain_tx.get("tx_hash"),
            structure_hash=blockchain_tx.get("structure_hash"),
            report_hash=blockchain_tx.get("report_hash")
        )
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in docking workflow for job {job_id}: {str(e)}", exc_info=True)
        try:
            await update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e)
            )
        except Exception as status_error:
            logger.error(f"Failed to update job status to FAILED for job {job_id}: {str(status_error)}", exc_info=True)
        raise
