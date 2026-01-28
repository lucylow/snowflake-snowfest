from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging

from backend.database import engine

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint with database connectivity check"""
    try:
        # Check database connectivity
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "service": "SNOWFLAKE API",
            "version": "1.0.0",
            "database": "connected"
        }
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "SNOWFLAKE API",
                "version": "1.0.0",
                "database": "disconnected",
                "error": "Database connection failed"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "SNOWFLAKE API",
                "version": "1.0.0",
                "error": "Health check failed"
            }
        )

@router.get("/health/ready")
async def readiness_check():
    """Readiness check endpoint - checks if service is ready to accept requests"""
    try:
        # Check database connectivity
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "service": "SNOWFLAKE API"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service not ready")

@router.get("/health/live")
async def liveness_check():
    """Liveness check endpoint - checks if service is alive"""
    return {
        "status": "alive",
        "service": "SNOWFLAKE API"
    }
