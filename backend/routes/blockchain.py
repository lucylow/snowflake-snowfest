from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import logging

from backend.services.blockchain import verify_blockchain_record
from backend.database import async_session_maker
from backend.models import Job

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/blockchain/verify/{tx_hash}")
async def verify_transaction(tx_hash: str):
    """Verify a blockchain transaction"""
    
    if not tx_hash or not tx_hash.strip():
        raise HTTPException(status_code=400, detail="Transaction hash is required")
    
    try:
        result = await verify_blockchain_record(tx_hash)
        return result
    except Exception as e:
        logger.error(f"Error verifying transaction {tx_hash}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error verifying transaction: {str(e)}")

@router.get("/blockchain/job/{job_id}")
async def get_job_blockchain_record(job_id: str):
    """Get blockchain record for a specific job"""
    
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    try:
        async with async_session_maker() as session:
            try:
                result = await session.execute(select(Job).where(Job.id == job_id))
                job = result.scalar_one_or_none()
            except SQLAlchemyError as e:
                logger.error(f"Database error getting job {job_id}: {str(e)}")
                raise HTTPException(status_code=500, detail="Database error retrieving job")
            
            if not job:
                raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
            
            if not job.blockchain_tx_hash:
                return {
                    "job_id": job_id,
                    "has_blockchain_record": False,
                    "message": "Job has not been stored on blockchain yet"
                }
            
            try:
                verification = await verify_blockchain_record(job.blockchain_tx_hash)
            except Exception as e:
                logger.error(f"Error verifying blockchain record for job {job_id}: {str(e)}")
                # Return partial result even if verification fails
                verification = {
                    "verified": False,
                    "message": f"Verification error: {str(e)}",
                    "tx_hash": job.blockchain_tx_hash
                }
            
            return {
                "job_id": job_id,
                "has_blockchain_record": True,
                "tx_hash": job.blockchain_tx_hash,
                "structure_hash": job.structure_hash,
                "report_hash": job.report_hash,
                "verification": verification
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting blockchain record for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
