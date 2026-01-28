from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import uuid
import logging
import json

from backend.database import get_db
from backend.schemas import JobCreate, JobResponse, AIAnalysisRequest, AIAnalysisResponse, AlphaFoldPredictionRequest, AlphaFoldPredictionResponse
from backend.models import Job, JobType, JobStatus, JobStatus
from backend.services.workflow import run_alphafold_then_dock, run_docking_only, run_alphafold_only
from backend.services.ai_report import (
    generate_structured_ai_analysis, 
    generate_ai_analysis_stream,
    generate_followup_response,
    generate_ensemble_analysis,
    get_conversation_history,
    AIReportError
)
from backend.exceptions import ValidationError, DatabaseError, NotFoundError
from backend.utils.docking_results_adapter import adapt_docking_results_for_frontend

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/jobs", response_model=JobResponse)
async def create_job(
    job: JobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new job for structure prediction and/or docking"""
    
    try:
        # Validate input based on job type
        if job.job_type == JobType.SEQUENCE_TO_DOCKING and not job.protein_sequence:
            raise ValidationError("protein_sequence is required for SEQUENCE_TO_DOCKING jobs")
        
        if job.job_type == JobType.DOCKING_ONLY and not job.protein_pdb:
            raise ValidationError("protein_pdb is required for DOCKING_ONLY jobs")
        
        # Validate ligand files
        if not job.ligand_files or len(job.ligand_files) == 0:
            raise ValidationError("At least one ligand file is required")
        
        # Validate docking parameters
        if not job.docking_parameters:
            raise ValidationError("Docking parameters are required")
        
        # Create job record
        job_id = str(uuid.uuid4())
        db_job = Job(
            id=job_id,
            job_name=job.job_name or f"Job {job_id[:8]}",
            job_type=job.job_type,
            protein_sequence=job.protein_sequence if job.job_type == JobType.SEQUENCE_TO_DOCKING else None,
            ligand_files=job.ligand_files,
            docking_parameters=job.docking_parameters
        )
        
        try:
            db.add(db_job)
            await db.commit()
            await db.refresh(db_job)
        except SQLAlchemyError as e:
            logger.error(f"Database error creating job: {str(e)}", exc_info=True)
            await db.rollback()
            raise DatabaseError(f"Failed to create job in database: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating job: {str(e)}", exc_info=True)
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create job")
        
        # Submit background task
        try:
            if job.job_type == JobType.SEQUENCE_TO_DOCKING:
                background_tasks.add_task(
                    run_alphafold_then_dock,
                    job_id=job_id,
                    sequence=job.protein_sequence,
                    ligand_files=job.ligand_files,
                    parameters=job.docking_parameters
                )
            else:
                background_tasks.add_task(
                    run_docking_only,
                    job_id=job_id,
                    protein_pdb=job.protein_pdb,
                    ligand_files=job.ligand_files,
                    parameters=job.docking_parameters
                )
        except Exception as e:
            logger.error(f"Failed to submit background task for job {job_id}: {str(e)}", exc_info=True)
            # Job is already created, so we log the error but don't fail the request
            # The job will remain in queued state
        
        return db_job
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get job status and results"""
    from sqlalchemy import select
    
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    # Validate UUID format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        
        return job
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"Database error getting job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error retrieving job")
    except Exception as e:
        logger.error(f"Unexpected error getting job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get docking results for a completed job in frontend-friendly format."""
    from sqlalchemy import select

    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        if not job.docking_results:
            raise HTTPException(
                status_code=400,
                detail="Job does not have docking results yet. Please wait for the job to complete.",
            )
        dr = job.docking_results if isinstance(job.docking_results, dict) else {}
        adapted = adapt_docking_results_for_frontend(
            job_id=job_id,
            docking_results=dr,
            protein_structure="",
            ligand_structure="",
        )
        return adapted
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting results for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 20):
    """List all jobs"""
    from sqlalchemy import select
    
    try:
        if skip < 0:
            raise ValidationError("skip must be non-negative")
        
        if limit < 1 or limit > 100:
            raise ValidationError("limit must be between 1 and 100")
        
        result = await db.execute(select(Job).offset(skip).limit(limit).order_by(Job.created_at.desc()))
        jobs = result.scalars().all()
        
        return jobs
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"Database error listing jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error retrieving jobs")
    except Exception as e:
        logger.error(f"Unexpected error listing jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/jobs/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed job with the same inputs."""
    from sqlalchemy import select

    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        if job.status != JobStatus.FAILED:
            raise HTTPException(
                status_code=400,
                detail="Only failed jobs can be retried.",
            )
        if not job.ligand_files or not job.docking_parameters:
            raise HTTPException(
                status_code=400,
                detail="Job missing ligand files or docking parameters; cannot retry.",
            )
        job_type = job.job_type
        if job_type == JobType.SEQUENCE_TO_DOCKING and not job.protein_sequence:
            raise HTTPException(
                status_code=400,
                detail="Sequence-to-docking job missing protein sequence; cannot retry.",
            )
        if job_type == JobType.DOCKING_ONLY:
            from pathlib import Path
            pdb_path = job.protein_pdb_path
            if not pdb_path or not Path(pdb_path).exists():
                raise HTTPException(
                    status_code=400,
                    detail="Docking-only job missing or invalid protein PDB file; cannot retry.",
                )
            import aiofiles
            async with aiofiles.open(pdb_path, "r") as f:
                protein_pdb = await f.read()
        else:
            protein_pdb = None

        job.status = JobStatus.SUBMITTED
        job.error_message = None
        job.progress = 0.0
        job.progress_message = None
        await db.commit()
        await db.refresh(job)

        if job_type == JobType.SEQUENCE_TO_DOCKING:
            background_tasks.add_task(
                run_alphafold_then_dock,
                job_id=job_id,
                sequence=job.protein_sequence,
                ligand_files=job.ligand_files,
                parameters=job.docking_parameters,
            )
        else:
            background_tasks.add_task(
                run_docking_only,
                job_id=job_id,
                protein_pdb=protein_pdb,
                ligand_files=job.ligand_files,
                parameters=job.docking_parameters,
            )
        return job
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrying job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/jobs/{job_id}/analyze", response_model=AIAnalysisResponse)
async def analyze_job(
    job_id: str,
    analysis_request: AIAnalysisRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI analysis for a completed job"""
    from sqlalchemy import select
    
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    # Validate UUID format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    try:
        # Get job from database
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        
        # Check if job has docking results
        if not job.docking_results:
            raise HTTPException(
                status_code=400,
                detail="Job does not have docking results yet. Please wait for the job to complete."
            )
        
        # Generate structured AI analysis
        try:
            analysis_result = await generate_structured_ai_analysis(
                job_id=job_id,
                sequence=job.protein_sequence,
                plddt_score=job.plddt_score,
                docking_results=job.docking_results,
                analysis_type=analysis_request.analysis_type,
                custom_prompt=analysis_request.custom_prompt,
                stakeholder_type=analysis_request.stakeholder_type
            )
            
            # Ensure response matches expected format
            if "analysis" not in analysis_result:
                # Handle case where function returns different structure
                analysis_result = {
                    "analysis": analysis_result,
                    "recommendations": analysis_result.get("recommendations", []),
                    "confidence": analysis_result.get("confidence", 0.75),
                    "metadata": analysis_result.get("metadata", {})
                }
            
            return analysis_result
        except AIReportError as e:
            logger.error(f"AI analysis error for job {job_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error analyzing job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/jobs/{job_id}/analyze/stream")
async def analyze_job_stream(
    job_id: str,
    analysis_request: AIAnalysisRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI analysis with streaming support for real-time updates"""
    from sqlalchemy import select
    
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        
        if not job.docking_results:
            raise HTTPException(
                status_code=400,
                detail="Job does not have docking results yet. Please wait for the job to complete."
            )
        
        async def generate():
            try:
                async for chunk in generate_ai_analysis_stream(
                    job_id=job_id,
                    sequence=job.protein_sequence,
                    plddt_score=job.plddt_score,
                    docking_results=job.docking_results,
                    analysis_type=analysis_request.analysis_type,
                    custom_prompt=analysis_request.custom_prompt,
                    stakeholder_type=analysis_request.stakeholder_type
                ):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Error in streaming analysis: {str(e)}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error streaming analysis for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/jobs/{job_id}/analyze/ensemble")
async def analyze_job_ensemble(
    job_id: str,
    analysis_request: AIAnalysisRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI analysis using multiple models and combine insights"""
    from sqlalchemy import select
    
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        
        if not job.docking_results:
            raise HTTPException(
                status_code=400,
                detail="Job does not have docking results yet. Please wait for the job to complete."
            )
        
        ensemble_result = await generate_ensemble_analysis(
            job_id=job_id,
            sequence=job.protein_sequence,
            plddt_score=job.plddt_score,
            docking_results=job.docking_results,
            analysis_type=analysis_request.analysis_type,
            stakeholder_type=analysis_request.stakeholder_type
        )
        
        return ensemble_result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in ensemble analysis for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/jobs/{job_id}/analyze/followup")
async def analyze_job_followup(
    job_id: str,
    question: str = Body(..., embed=True),
    stakeholder_type: str = Body(default="researcher", embed=True),
    db: AsyncSession = Depends(get_db)
):
    """Generate a follow-up response to a question about the docking results"""
    from sqlalchemy import select
    
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        
        if not job.docking_results:
            raise HTTPException(
                status_code=400,
                detail="Job does not have docking results yet. Please wait for the job to complete."
            )
        
        followup_result = await generate_followup_response(
            job_id=job_id,
            question=question,
            docking_results=job.docking_results,
            stakeholder_type=stakeholder_type
        )
        
        return followup_result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in follow-up analysis for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/jobs/{job_id}/conversation")
async def get_job_conversation(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history for a job"""
    from sqlalchemy import select
    
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        
        history = get_conversation_history(job_id)
        return {"job_id": job_id, "conversation_history": history}
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting conversation for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/alphafold/predict", response_model=AlphaFoldPredictionResponse)
async def predict_structure(
    request: AlphaFoldPredictionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Submit an AlphaFold-only structure prediction job (no docking)"""
    
    try:
        # Validate sequence
        if not request.protein_sequence or not request.protein_sequence.strip():
            raise ValidationError("protein_sequence is required")
        
        # Create job record
        job_id = str(uuid.uuid4())
        db_job = Job(
            id=job_id,
            job_name=request.job_name or f"AlphaFold Prediction {job_id[:8]}",
            job_type=JobType.ALPHAFOLD_ONLY,
            protein_sequence=request.protein_sequence,
            ligand_files=None,  # No ligands for AlphaFold-only
            docking_parameters=None  # No docking for AlphaFold-only
        )
        
        try:
            db.add(db_job)
            await db.commit()
            await db.refresh(db_job)
        except SQLAlchemyError as e:
            logger.error(f"Database error creating AlphaFold job: {str(e)}", exc_info=True)
            await db.rollback()
            raise DatabaseError(f"Failed to create job in database: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating AlphaFold job: {str(e)}", exc_info=True)
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create job")
        
        # Extract configuration
        config = request.alphafold_config
        model_preset = config.model_preset if config else "monomer"
        max_template_date = config.max_template_date if config else None
        db_preset = config.db_preset if config else "reduced_dbs"
        use_gpu_relax = config.use_gpu_relax if config else True
        
        # Submit background task
        try:
            background_tasks.add_task(
                run_alphafold_only,
                job_id=job_id,
                sequence=request.protein_sequence,
                model_preset=model_preset,
                max_template_date=max_template_date,
                db_preset=db_preset,
                use_gpu_relax=use_gpu_relax
            )
        except Exception as e:
            logger.error(f"Failed to submit AlphaFold background task for job {job_id}: {str(e)}", exc_info=True)
            # Job is already created, so we log the error but don't fail the request
        
        return db_job
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in predict_structure: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
