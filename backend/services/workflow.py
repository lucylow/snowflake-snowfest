import logging
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy import select
from datetime import datetime

from backend.database import async_session_maker
from backend.models import Job, JobStatus
from backend.services.alphafold import run_alphafold
from backend.services.docking import run_autodock_vina
from backend.services.ai_report import generate_ai_report
from backend.services.blockchain import store_on_blockchain

logger = logging.getLogger(__name__)

async def update_job_status(
    job_id: str,
    status: JobStatus,
    error_message: str = None,
    **kwargs
):
    """Update job status in database"""
    async with async_session_maker() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if job:
            job.status = status
            if error_message:
                job.error_message = error_message
            
            # Update additional fields
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            
            if status == JobStatus.COMPLETED:
                job.completed_at = datetime.now()
            
            await session.commit()
            logger.info(f"Job {job_id} status updated to {status}")

async def run_alphafold_then_dock(
    job_id: str,
    sequence: str,
    ligand_files: List[str],
    parameters: Dict[str, Any]
):
    """
    Complete workflow: AlphaFold structure prediction → Molecular docking → AI report
    
    Args:
        job_id: Unique job identifier
        sequence: Protein amino acid sequence
        ligand_files: List of ligand file contents
        parameters: Docking parameters
    """
    try:
        # Step 1: Structure Prediction
        logger.info(f"Starting AlphaFold prediction for job {job_id}")
        await update_job_status(job_id, JobStatus.PREDICTING_STRUCTURE)
        
        predicted_pdb, plddt_score = await run_alphafold(sequence, job_id)
        
        await update_job_status(
            job_id,
            JobStatus.STRUCTURE_PREDICTED,
            predicted_pdb_path=str(predicted_pdb),
            plddt_score=plddt_score
        )
        
        logger.info(f"Structure predicted for job {job_id}, pLDDT: {plddt_score:.2f}")
        
        # Step 2: Molecular Docking
        logger.info(f"Starting docking for job {job_id}")
        await update_job_status(job_id, JobStatus.DOCKING)
        
        docking_results = await run_autodock_vina(
            protein_pdb_path=predicted_pdb,
            ligand_files=ligand_files,
            parameters=parameters,
            job_id=job_id
        )
        
        await update_job_status(
            job_id,
            JobStatus.ANALYZING,
            docking_results=docking_results,
            top_binding_score=docking_results.get("best_score")
        )
        
        logger.info(f"Docking completed for job {job_id}, best score: {docking_results.get('best_score')}")
        
        # Step 3: AI Report Generation
        logger.info(f"Generating AI report for job {job_id}")
        
        ai_report = await generate_ai_report(
            job_id=job_id,
            sequence=sequence,
            plddt_score=plddt_score,
            docking_results=docking_results,
            stakeholder="researcher"
        )
        
        await update_job_status(
            job_id,
            JobStatus.ANALYZING,
            ai_report_content=ai_report
        )
        
        # Step 4: Blockchain Verification
        logger.info(f"Storing verification on blockchain for job {job_id}")
        
        blockchain_tx = await store_on_blockchain(
            job_id=job_id,
            predicted_pdb_path=predicted_pdb,
            report_content=ai_report
        )
        
        await update_job_status(
            job_id,
            JobStatus.COMPLETED,
            blockchain_tx_hash=blockchain_tx.get("tx_hash"),
            structure_hash=blockchain_tx.get("structure_hash"),
            report_hash=blockchain_tx.get("report_hash")
        )
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in workflow for job {job_id}: {str(e)}")
        await update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message=str(e)
        )
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
        pdb_dir = Path(f"/workspace/uploads/{job_id}")
        pdb_dir.mkdir(parents=True, exist_ok=True)
        pdb_path = pdb_dir / "protein.pdb"
        
        async with aiofiles.open(pdb_path, 'w') as f:
            await f.write(protein_pdb)
        
        await update_job_status(
            job_id,
            JobStatus.DOCKING,
            protein_pdb_path=str(pdb_path)
        )
        
        # Step 2: Molecular Docking
        logger.info(f"Starting docking for job {job_id}")
        
        docking_results = await run_autodock_vina(
            protein_pdb_path=pdb_path,
            ligand_files=ligand_files,
            parameters=parameters,
            job_id=job_id
        )
        
        await update_job_status(
            job_id,
            JobStatus.ANALYZING,
            docking_results=docking_results,
            top_binding_score=docking_results.get("best_score")
        )
        
        logger.info(f"Docking completed for job {job_id}, best score: {docking_results.get('best_score')}")
        
        # Step 3: AI Report Generation
        logger.info(f"Generating AI report for job {job_id}")
        
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
            ai_report_content=ai_report
        )
        
        # Step 4: Blockchain Verification
        logger.info(f"Storing verification on blockchain for job {job_id}")
        
        blockchain_tx = await store_on_blockchain(
            job_id=job_id,
            predicted_pdb_path=pdb_path,
            report_content=ai_report
        )
        
        await update_job_status(
            job_id,
            JobStatus.COMPLETED,
            blockchain_tx_hash=blockchain_tx.get("tx_hash"),
            structure_hash=blockchain_tx.get("structure_hash"),
            report_hash=blockchain_tx.get("report_hash")
        )
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in docking workflow for job {job_id}: {str(e)}")
        await update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message=str(e)
        )
        raise
