from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from backend.database import get_db
from backend.schemas import JobCreate, JobResponse
from backend.models import Job, JobType
from backend.services.workflow import run_alphafold_then_dock, run_docking_only

router = APIRouter()

@router.post("/jobs", response_model=JobResponse)
async def create_job(
    job: JobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new job for structure prediction and/or docking"""
    
    # Validate input based on job type
    if job.job_type == JobType.SEQUENCE_TO_DOCKING and not job.protein_sequence:
        raise HTTPException(status_code=400, detail="protein_sequence is required for SEQUENCE_TO_DOCKING jobs")
    
    if job.job_type == JobType.DOCKING_ONLY and not job.protein_pdb:
        raise HTTPException(status_code=400, detail="protein_pdb is required for DOCKING_ONLY jobs")
    
    # Create job record
    job_id = str(uuid.uuid4())
    db_job = Job(
        id=job_id,
        job_name=job.job_name,
        job_type=job.job_type,
        protein_sequence=job.protein_sequence if job.job_type == JobType.SEQUENCE_TO_DOCKING else None,
        ligand_files=job.ligand_files,
        docking_parameters=job.docking_parameters
    )
    
    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)
    
    # Submit background task
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
    
    return db_job

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get job status and results"""
    from sqlalchemy import select
    
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        return job
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error getting job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error retrieving job")
    except Exception as e:
        logger.error(f"Unexpected error getting job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 20):
    """List all jobs"""
    from sqlalchemy import select
    
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be non-negative")
    
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    
    try:
        result = await db.execute(select(Job).offset(skip).limit(limit).order_by(Job.created_at.desc()))
        jobs = result.scalars().all()
        
        return jobs
    except SQLAlchemyError as e:
        logger.error(f"Database error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error retrieving jobs")
    except Exception as e:
        logger.error(f"Unexpected error listing jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
