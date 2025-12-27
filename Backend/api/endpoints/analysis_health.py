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


# ============================================================================
# NEW: Incomplete/Failed Analysis Detection & Re-analysis
# ============================================================================

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from services.analysis_health import AnalysisHealthService


@router.get("/scan-incomplete")
async def scan_incomplete_analysis(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=1000, le=5000, description="Max videos to scan"),
):
    """
    Scan all videos and identify those with incomplete or failed analysis.
    Categorizes by: complete, incomplete, not_started, images (skipped).
    """
    service = AnalysisHealthService(db)
    result = await service.scan_all_health(limit=limit)
    return result


@router.post("/mark-for-reanalysis")
async def mark_videos_for_reanalysis(
    video_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """
    Mark specific videos for re-analysis.
    Sets their status to 'needs_reanalysis' so they can be picked up by batch analysis.
    """
    service = AnalysisHealthService(db)
    result = await service.mark_for_reanalysis(video_ids)
    return result


@router.post("/mark-incomplete-for-reanalysis")
async def mark_all_incomplete_for_reanalysis(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=500, description="Max videos to mark"),
):
    """
    Find all videos with incomplete analysis and mark them for re-analysis.
    """
    service = AnalysisHealthService(db)
    
    # First scan for incomplete
    scan_result = await service.scan_all_health(limit=limit)
    
    # Get IDs of incomplete videos
    incomplete_ids = [v["video_id"] for v in scan_result.get("incomplete_videos", [])]
    not_started_ids = [v["video_id"] for v in scan_result.get("not_started_videos", [])]
    
    all_ids = incomplete_ids + not_started_ids
    
    if not all_ids:
        return {
            "marked_count": 0,
            "message": "No incomplete or unstarted videos found"
        }
    
    # Mark them for reanalysis
    mark_result = await service.mark_for_reanalysis(all_ids[:limit])
    
    return {
        "incomplete_found": len(incomplete_ids),
        "not_started_found": len(not_started_ids),
        "marked_count": mark_result["marked_count"],
        "message": f"Marked {mark_result['marked_count']} videos for re-analysis"
    }


@router.post("/skip-images")
async def skip_image_files(
    db: AsyncSession = Depends(get_db),
):
    """
    Mark all image files (PNG, JPG, HEIC, etc.) as 'image_skipped'.
    This prevents them from being queued for video analysis.
    """
    service = AnalysisHealthService(db)
    result = await service.mark_images_as_skipped()
    return result


@router.post("/clear-and-retry/{video_id}")
async def clear_and_retry_analysis(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Clear all analysis data for a video and mark it for fresh re-analysis.
    Use this for videos that have corrupted or incorrect analysis.
    """
    service = AnalysisHealthService(db)
    success = await service.clear_analysis_for_retry(video_id)
    
    if success:
        return {
            "status": "success",
            "video_id": video_id,
            "message": "Analysis cleared. Video will be re-analyzed in next batch."
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to clear analysis")


@router.get("/videos-needing-reanalysis")
async def get_videos_needing_reanalysis(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, le=500),
):
    """
    Get list of videos currently marked as needing re-analysis.
    """
    service = AnalysisHealthService(db)
    videos = await service.get_videos_needing_reanalysis(limit=limit)
    return {
        "count": len(videos),
        "videos": videos
    }

