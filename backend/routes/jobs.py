from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import uuid
import logging

from backend.database import get_db
from backend.schemas import JobCreate, JobResponse
from backend.models import Job, JobType
from backend.services.workflow import run_alphafold_then_dock, run_docking_only
from backend.exceptions import ValidationError, DatabaseError, NotFoundError

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
