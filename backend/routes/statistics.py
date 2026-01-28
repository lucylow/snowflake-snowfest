"""
Statistics API endpoints for data analysis
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any
import json
import logging

from backend.database import get_db
from backend.models import Job
from backend.exceptions import NotFoundError, ValidationError, DatabaseError

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/statistics/job/{job_id}")
async def get_job_statistics(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get statistical analysis for a single job"""
    from sqlalchemy import select
    
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        
        if not job.docking_results:
            raise ValidationError("No docking results available for this job")
        
        # Extract binding affinities with error handling
        try:
            docking_results = job.docking_results if isinstance(job.docking_results, dict) else json.loads(job.docking_results)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse docking results for job {job_id}: {str(e)}")
            raise ValidationError("Invalid docking results format")
        
        if not isinstance(docking_results, dict):
            raise ValidationError("Docking results must be a dictionary")
        
        all_affinities = []
        
        try:
            results = docking_results.get("results", [])
            if not isinstance(results, list):
                raise ValidationError("Docking results must contain a 'results' list")
            
            for result in results:
                if not isinstance(result, dict):
                    continue
                modes = result.get("modes", [])
                if not isinstance(modes, list):
                    continue
                for mode in modes:
                    if not isinstance(mode, dict):
                        continue
                    affinity = mode.get("affinity")
                    if affinity is not None:
                        try:
                            affinity_float = float(affinity)
                            all_affinities.append(affinity_float)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid affinity value: {affinity}")
                            continue
        except Exception as e:
            logger.error(f"Error extracting affinities for job {job_id}: {str(e)}", exc_info=True)
            raise ValidationError("Failed to extract binding affinities from results")
        
        if not all_affinities:
            raise ValidationError("No valid binding affinities found")
        
        # Calculate basic statistics
        try:
            sorted_affinities = sorted(all_affinities)
            n = len(all_affinities)
            mean = sum(all_affinities) / n
            median = sorted_affinities[n // 2] if n % 2 == 1 else (sorted_affinities[n // 2 - 1] + sorted_affinities[n // 2]) / 2
            
            variance = sum((x - mean) ** 2 for x in all_affinities) / (n - 1) if n > 1 else 0
            std_dev = variance ** 0.5
            
            q1_idx = n // 4
            q3_idx = 3 * n // 4
            q1 = sorted_affinities[q1_idx] if q1_idx < n else sorted_affinities[0]
            q3 = sorted_affinities[q3_idx] if q3_idx < n else sorted_affinities[-1]
            iqr = q3 - q1
            
            return {
                "job_id": job_id,
                "statistics": {
                    "count": n,
                    "mean": round(mean, 4),
                    "median": round(median, 4),
                    "std_dev": round(std_dev, 4),
                    "variance": round(variance, 4),
                    "min": round(min(all_affinities), 4),
                    "max": round(max(all_affinities), 4),
                    "range": round(max(all_affinities) - min(all_affinities), 4),
                    "q1": round(q1, 4),
                    "q2": round(median, 4),
                    "q3": round(q3, 4),
                    "iqr": round(iqr, 4),
                    "p25": round(sorted_affinities[n // 4] if n >= 4 else sorted_affinities[0], 4),
                    "p50": round(median, 4),
                    "p75": round(sorted_affinities[3 * n // 4] if n >= 4 else sorted_affinities[-1], 4),
                    "p90": round(sorted_affinities[int(n * 0.9)] if n >= 10 else sorted_affinities[-1], 4),
                    "p95": round(sorted_affinities[int(n * 0.95)] if n >= 20 else sorted_affinities[-1], 4),
                },
                "outliers": {
                    "lower_bound": round(q1 - 1.5 * iqr, 4),
                    "upper_bound": round(q3 + 1.5 * iqr, 4),
                    "count": len([x for x in all_affinities if x < q1 - 1.5 * iqr or x > q3 + 1.5 * iqr]),
                }
            }
        except (ZeroDivisionError, IndexError, ValueError) as e:
            logger.error(f"Error calculating statistics for job {job_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to calculate statistics")
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"Database error getting statistics for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error retrieving job statistics")
    except Exception as e:
        logger.error(f"Unexpected error getting statistics for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/statistics/compare")
async def compare_jobs(job_ids: List[str], db: AsyncSession = Depends(get_db)):
    """Compare statistics across multiple jobs"""
    from sqlalchemy import select
    
    try:
        if not job_ids or len(job_ids) < 2:
            raise ValidationError("Need at least 2 jobs for comparison")
        
        if len(job_ids) > 50:
            raise ValidationError("Cannot compare more than 50 jobs at once")
        
        jobs_data = []
        errors = []
        
        for job_id in job_ids:
            if not job_id or not job_id.strip():
                errors.append(f"Invalid job ID: {job_id}")
                continue
            
            try:
                result = await db.execute(select(Job).where(Job.id == job_id))
                job = result.scalar_one_or_none()
                
                if not job:
                    errors.append(f"Job not found: {job_id}")
                    continue
                
                if not job.docking_results:
                    errors.append(f"No docking results for job: {job_id}")
                    continue
                
                try:
                    docking_results = job.docking_results if isinstance(job.docking_results, dict) else json.loads(job.docking_results)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse docking results for job {job_id}: {str(e)}")
                    errors.append(f"Invalid results format for job: {job_id}")
                    continue
                
                if not isinstance(docking_results, dict):
                    errors.append(f"Invalid results format for job: {job_id}")
                    continue
                
                all_affinities = []
                
                try:
                    results = docking_results.get("results", [])
                    if not isinstance(results, list):
                        continue
                    
                    for result in results:
                        if not isinstance(result, dict):
                            continue
                        modes = result.get("modes", [])
                        if not isinstance(modes, list):
                            continue
                        for mode in modes:
                            if not isinstance(mode, dict):
                                continue
                            affinity = mode.get("affinity")
                            if affinity is not None:
                                try:
                                    affinity_float = float(affinity)
                                    all_affinities.append(affinity_float)
                                except (ValueError, TypeError):
                                    continue
                except Exception as e:
                    logger.warning(f"Error extracting affinities for job {job_id}: {str(e)}")
                    continue
                
                if all_affinities:
                    n = len(all_affinities)
                    mean = sum(all_affinities) / n
                    min_score = min(all_affinities)
                    
                    jobs_data.append({
                        "job_id": job_id,
                        "job_name": job.job_name or f"Job {job_id[:8]}",
                        "count": n,
                        "mean": round(mean, 4),
                        "min": round(min_score, 4),
                        "best_score": round(min_score, 4),
                    })
            except SQLAlchemyError as e:
                logger.error(f"Database error processing job {job_id}: {str(e)}")
                errors.append(f"Database error for job: {job_id}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing job {job_id}: {str(e)}", exc_info=True)
                errors.append(f"Error processing job: {job_id}")
                continue
        
        if len(jobs_data) < 2:
            error_msg = "Need at least 2 jobs with valid results"
            if errors:
                error_msg += f". Errors: {', '.join(errors[:5])}"
            raise ValidationError(error_msg)
        
        # Calculate aggregate statistics
        try:
            all_means = [j["mean"] for j in jobs_data]
            aggregate_mean = sum(all_means) / len(all_means)
            mean_variance = sum((m - aggregate_mean) ** 2 for m in all_means) / len(all_means)
            
            response = {
                "job_count": len(jobs_data),
                "jobs": jobs_data,
                "aggregate": {
                    "mean_of_means": round(aggregate_mean, 4),
                    "variance": round(mean_variance, 4),
                    "best_overall": round(min(j["best_score"] for j in jobs_data), 4),
                }
            }
            
            if errors:
                response["warnings"] = errors[:10]  # Limit warnings
            
            return response
        except (ZeroDivisionError, ValueError) as e:
            logger.error(f"Error calculating aggregate statistics: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to calculate aggregate statistics")
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"Database error comparing jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error comparing jobs")
    except Exception as e:
        logger.error(f"Unexpected error comparing jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
