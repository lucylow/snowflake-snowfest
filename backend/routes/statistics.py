"""
Statistics API endpoints for data analysis
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import json

from backend.database import get_db
from backend.models import Job

router = APIRouter()

@router.get("/statistics/job/{job_id}")
async def get_job_statistics(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get statistical analysis for a single job"""
    from sqlalchemy import select
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.docking_results:
        raise HTTPException(status_code=400, detail="No docking results available for this job")
    
    # Extract binding affinities
    docking_results = job.docking_results if isinstance(job.docking_results, dict) else json.loads(job.docking_results)
    all_affinities = []
    
    results = docking_results.get("results", [])
    for result in results:
        modes = result.get("modes", [])
        for mode in modes:
            affinity = mode.get("affinity")
            if affinity is not None:
                all_affinities.append(affinity)
    
    if not all_affinities:
        raise HTTPException(status_code=400, detail="No valid binding affinities found")
    
    # Calculate basic statistics
    sorted_affinities = sorted(all_affinities)
    n = len(all_affinities)
    mean = sum(all_affinities) / n
    median = sorted_affinities[n // 2] if n % 2 == 0 else sorted_affinities[n // 2]
    
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

@router.post("/statistics/compare")
async def compare_jobs(job_ids: List[str], db: AsyncSession = Depends(get_db)):
    """Compare statistics across multiple jobs"""
    from sqlalchemy import select
    
    if len(job_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 jobs for comparison")
    
    jobs_data = []
    for job_id in job_ids:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            continue
        
        if not job.docking_results:
            continue
        
        docking_results = job.docking_results if isinstance(job.docking_results, dict) else json.loads(job.docking_results)
        all_affinities = []
        
        results = docking_results.get("results", [])
        for result in results:
            modes = result.get("modes", [])
            for mode in modes:
                affinity = mode.get("affinity")
                if affinity is not None:
                    all_affinities.append(affinity)
        
        if all_affinities:
            n = len(all_affinities)
            mean = sum(all_affinities) / n
            min_score = min(all_affinities)
            
            jobs_data.append({
                "job_id": job_id,
                "job_name": job.job_name,
                "count": n,
                "mean": round(mean, 4),
                "min": round(min_score, 4),
                "best_score": round(min_score, 4),
            })
    
    if len(jobs_data) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 jobs with valid results")
    
    # Calculate aggregate statistics
    all_means = [j["mean"] for j in jobs_data]
    aggregate_mean = sum(all_means) / len(all_means)
    mean_variance = sum((m - aggregate_mean) ** 2 for m in all_means) / len(all_means)
    
    return {
        "job_count": len(jobs_data),
        "jobs": jobs_data,
        "aggregate": {
            "mean_of_means": round(aggregate_mean, 4),
            "variance": round(mean_variance, 4),
            "best_overall": round(min(j["best_score"] for j in jobs_data), 4),
        }
    }
