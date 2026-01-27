"""
Task queue system using Celery and Redis for background job processing
"""

from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app
celery_app = Celery(
    "snowflake",
    broker=REDIS_URL,
    backend=REDIS_URL
)

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
)

# Import tasks to register them
from backend.services import workflow

# Define Celery tasks
@celery_app.task(name="run_alphafold_then_dock", bind=True)
def run_alphafold_then_dock_task(self, job_id, sequence, ligand_files, parameters):
    """Celery task wrapper for AlphaFold + docking workflow"""
    import asyncio
    return asyncio.run(
        workflow.run_alphafold_then_dock(
            job_id, sequence, ligand_files, parameters
        )
    )

@celery_app.task(name="run_docking_only", bind=True)
def run_docking_only_task(self, job_id, protein_pdb, ligand_files, parameters):
    """Celery task wrapper for docking-only workflow"""
    import asyncio
    return asyncio.run(
        workflow.run_docking_only(
            job_id, protein_pdb, ligand_files, parameters
        )
    )
