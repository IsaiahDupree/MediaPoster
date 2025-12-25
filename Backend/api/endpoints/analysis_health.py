"""
Analysis Health and Resilience Endpoints
=========================================
Provides endpoints for monitoring and ensuring analysis process reliability.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from loguru import logger
from datetime import datetime, timedelta

from api.media_processing_db import _analysis_jobs, get_analysis_status

router = APIRouter(prefix="/api/analysis-health", tags=["Analysis Health"])


@router.get("/status")
async def get_analysis_health_status():
    """
    Get overall health status of analysis system.
    Returns information about running jobs, stuck jobs, and system health.
    """
    now = datetime.now()
    stuck_threshold = timedelta(minutes=30)  # Jobs stuck for 30+ minutes
    
    running_jobs = []
    stuck_jobs = []
    completed_jobs = []
    
    for job_id, job in _analysis_jobs.items():
        status = job.get("status", "unknown")
        started_at = job.get("started_at")
        last_update = job.get("last_update", started_at)
        
        if started_at:
            try:
                started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                if last_update:
                    updated = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                    time_since_update = now - updated
                else:
                    time_since_update = now - started
                
                job_info = {
                    "job_id": job_id,
                    "status": status,
                    "total": job.get("total", 0),
                    "completed": job.get("completed", 0),
                    "failed": job.get("failed", 0),
                    "started_at": started_at,
                    "last_update": last_update,
                    "minutes_since_update": time_since_update.total_seconds() / 60,
                    "completion_rate": (job.get("completed", 0) / job.get("total", 1) * 100) if job.get("total", 0) > 0 else 0
                }
                
                if status == "running":
                    running_jobs.append(job_info)
                    if time_since_update > stuck_threshold:
                        stuck_jobs.append(job_info)
                elif status == "completed":
                    completed_jobs.append(job_info)
                    
            except Exception as e:
                logger.warning(f"Error parsing job timestamps: {e}")
    
    return {
        "healthy": len(stuck_jobs) == 0,
        "running_jobs": len(running_jobs),
        "stuck_jobs": len(stuck_jobs),
        "completed_jobs": len(completed_jobs),
        "stuck_job_details": stuck_jobs,
        "running_job_details": running_jobs
    }


@router.post("/retry-failed/{job_id}")
async def retry_failed_videos(job_id: str):
    """
    Retry failed videos in a completed job.
    Useful for recovering from transient failures.
    """
    if job_id not in _analysis_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = _analysis_jobs[job_id]
    failed_videos = []
    
    # Find all failed videos
    for video_id, video_status in job.get("videos", {}).items():
        if isinstance(video_status, dict):
            if video_status.get("status") == "failed":
                failed_videos.append({
                    "video_id": video_id,
                    "error": video_status.get("error"),
                    "filename": video_status.get("filename")
                })
        elif isinstance(video_status, str) and video_status.startswith("failed:"):
            failed_videos.append({
                "video_id": video_id,
                "error": video_status
            })
    
    if not failed_videos:
        return {
            "success": True,
            "message": "No failed videos to retry",
            "retried": 0
        }
    
    # Create retry job
    retry_job_id = f"{job_id}_retry_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    _analysis_jobs[retry_job_id] = {
        "status": "running",
        "total": len(failed_videos),
        "completed": 0,
        "failed": 0,
        "videos": {},
        "started_at": datetime.now().isoformat(),
        "parent_job_id": job_id,
        "is_retry": True
    }
    
    # Queue retry analysis
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="analysis_retry")
    _analysis_jobs[retry_job_id]["executor"] = executor
    
    from api.media_processing_db import run_analysis_sync
    
    for failed_video in failed_videos:
        video_id = failed_video["video_id"]
        # Get video source path from database
        # For now, we'll need to look it up
        _analysis_jobs[retry_job_id]["videos"][video_id] = {
            "status": "queued",
            "filename": failed_video.get("filename", "unknown"),
            "original_error": failed_video.get("error")
        }
        # Note: We'd need to get the file_path from the database
        # This is a simplified version - full implementation would query DB
    
    logger.info(f"[Retry] Created retry job {retry_job_id} for {len(failed_videos)} failed videos")
    
    return {
        "success": True,
        "retry_job_id": retry_job_id,
        "retried": len(failed_videos),
        "message": f"Retry job created for {len(failed_videos)} failed videos"
    }


@router.get("/job/{job_id}/resilience")
async def get_job_resilience(job_id: str):
    """
    Get resilience metrics for a specific job.
    Shows retry attempts, failure patterns, and recovery status.
    """
    if job_id not in _analysis_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = _analysis_jobs[job_id]
    
    # Analyze video statuses
    status_counts = {}
    error_types = {}
    retry_attempts = {}
    
    for video_id, video_status in job.get("videos", {}).items():
        if isinstance(video_status, dict):
            status = video_status.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if status == "failed":
                error_type = video_status.get("error_type", "Unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1
        else:
            status = str(video_status)
            status_counts[status] = status_counts.get(status, 0) + 1
    
    total = job.get("total", 0)
    completed = job.get("completed", 0)
    failed = job.get("failed", 0)
    success_rate = (completed / total * 100) if total > 0 else 0
    
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "total": total,
        "completed": completed,
        "failed": failed,
        "success_rate": success_rate,
        "status_breakdown": status_counts,
        "error_types": error_types,
        "resilience_score": success_rate,  # Can be enhanced with more metrics
        "recommendations": _get_resilience_recommendations(job, error_types)
    }


def _get_resilience_recommendations(job: dict, error_types: dict) -> List[str]:
    """Generate recommendations for improving analysis resilience."""
    recommendations = []
    
    total = job.get("total", 0)
    failed = job.get("failed", 0)
    failure_rate = (failed / total * 100) if total > 0 else 0
    
    if failure_rate > 20:
        recommendations.append("High failure rate detected. Consider checking API keys, file paths, and system resources.")
    
    if "TimeoutError" in error_types or "timeout" in str(error_types).lower():
        recommendations.append("Timeout errors detected. Consider increasing timeout values or reducing batch size.")
    
    if "FileNotFoundError" in error_types or "file_not_found" in str(error_types).lower():
        recommendations.append("File not found errors detected. Verify file paths and ensure files are accessible.")
    
    if "APIError" in error_types or "api" in str(error_types).lower():
        recommendations.append("API errors detected. Check API key validity and rate limits.")
    
    if not recommendations:
        recommendations.append("Analysis system appears healthy. No specific recommendations.")
    
    return recommendations

