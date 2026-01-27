from fastapi import APIRouter, HTTPException
from backend.services.blockchain import verify_blockchain_record

router = APIRouter()

@router.get("/blockchain/verify/{tx_hash}")
async def verify_transaction(tx_hash: str):
    """Verify a blockchain transaction"""
    
    if not tx_hash:
        raise HTTPException(status_code=400, detail="Transaction hash is required")
    
    result = await verify_blockchain_record(tx_hash)
    
    return result

@router.get("/blockchain/job/{job_id}")
async def get_job_blockchain_record(job_id: str):
    """Get blockchain record for a specific job"""
    from sqlalchemy import select
    from backend.database import async_session_maker
    from backend.models import Job
    
    async with async_session_maker() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.blockchain_tx_hash:
            return {
                "job_id": job_id,
                "has_blockchain_record": False,
                "message": "Job has not been stored on blockchain yet"
            }
        
        verification = await verify_blockchain_record(job.blockchain_tx_hash)
        
        return {
            "job_id": job_id,
            "has_blockchain_record": True,
            "tx_hash": job.blockchain_tx_hash,
            "structure_hash": job.structure_hash,
            "report_hash": job.report_hash,
            "verification": verification
        }
