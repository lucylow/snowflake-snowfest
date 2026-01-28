"""
Task queue system using Celery and Redis for background job processing
"""

from celery import Celery
from celery.exceptions import Retry, TaskError
import os
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app
try:
    celery_app = Celery(
        "snowflake",
        broker=REDIS_URL,
        backend=REDIS_URL
    )
except Exception as e:
    logger.error(f"Failed to initialize Celery app: {str(e)}", exc_info=True)
    raise

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 4,  # 4 hour timeout
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=10,
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
)

# Import tasks to register them
from backend.services import workflow

# Define Celery tasks
@celery_app.task(name="run_alphafold_then_dock", bind=True, max_retries=3)
def run_alphafold_then_dock_task(self, job_id, sequence, ligand_files, parameters):
    """Celery task wrapper for AlphaFold + docking workflow"""
    import asyncio
    from backend.exceptions import BackendError
    
    try:
        logger.info(f"Starting Celery task for AlphaFold + docking workflow, job {job_id}")
        result = asyncio.run(
            workflow.run_alphafold_then_dock(
                job_id, sequence, ligand_files, parameters
            )
        )
        logger.info(f"Completed Celery task for job {job_id}")
        return result
    except Exception as e:
        logger.error(f"Celery task failed for job {job_id}: {str(e)}", exc_info=True)
        
        # Retry on transient errors
        if isinstance(e, (ConnectionError, TimeoutError)) and self.request.retries < self.max_retries:
            logger.info(f"Retrying task for job {job_id} (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        # Don't retry on permanent errors
        raise TaskError(f"Task failed for job {job_id}: {str(e)}")

@celery_app.task(name="run_docking_only", bind=True, max_retries=3)
def run_docking_only_task(self, job_id, protein_pdb, ligand_files, parameters):
    """Celery task wrapper for docking-only workflow"""
    import asyncio
    from backend.exceptions import BackendError
    
    try:
        logger.info(f"Starting Celery task for docking-only workflow, job {job_id}")
        result = asyncio.run(
            workflow.run_docking_only(
                job_id, protein_pdb, ligand_files, parameters
            )
        )
        logger.info(f"Completed Celery task for job {job_id}")
        return result
    except Exception as e:
        logger.error(f"Celery task failed for job {job_id}: {str(e)}", exc_info=True)
        
        # Retry on transient errors
        if isinstance(e, (ConnectionError, TimeoutError)) and self.request.retries < self.max_retries:
            logger.info(f"Retrying task for job {job_id} (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        # Don't retry on permanent errors
        raise TaskError(f"Task failed for job {job_id}: {str(e)}")
