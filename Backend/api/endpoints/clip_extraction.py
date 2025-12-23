"""
Clip Extraction API Endpoints
=============================
REST API for extracting short-form clips from long-form videos.

Endpoints:
    POST /api/clip-extraction/extract - Start extraction job
    GET  /api/clip-extraction/jobs - List extraction jobs
    GET  /api/clip-extraction/jobs/{job_id} - Get job status
    GET  /api/clip-extraction/clips/{media_id} - Get clips for a video
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clip-extraction", tags=["Clip Extraction"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


class ExtractionOptions(BaseModel):
    """Options for clip extraction."""
    min_clip_duration: int = Field(default=10, ge=5, le=30, description="Minimum clip duration in seconds")
    max_clip_duration: int = Field(default=60, ge=15, le=120, description="Maximum clip duration in seconds")
    max_clips: int = Field(default=7, ge=1, le=15, description="Maximum number of clips to extract")
    add_subtitles: bool = Field(default=True, description="Add word-level subtitles")
    font_size: int = Field(default=24, ge=12, le=48, description="Subtitle font size")
    font_color: str = Field(default="#FFFFFF", description="Subtitle font color")


class ExtractionRequest(BaseModel):
    """Request to extract clips from a video."""
    video_path: Optional[str] = Field(None, description="Path to video file (if local)")
    video_url: Optional[str] = Field(None, description="URL to video (YouTube, etc)")
    media_id: Optional[str] = Field(None, description="ID of video in media library")
    output_dir: Optional[str] = Field(None, description="Output directory for clips")
    options: ExtractionOptions = Field(default_factory=ExtractionOptions)


class ExtractionJob(BaseModel):
    """Extraction job status."""
    job_id: str
    media_id: str
    status: str  # pending, processing, completed, failed
    progress: int = 0
    step: str = ""
    clips_count: int = 0
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class ClipInfo(BaseModel):
    """Information about an extracted clip."""
    clip_id: str
    filename: str
    path: str
    start_time: str
    end_time: str
    duration: float
    relevance_score: float
    text: str
    reasoning: str


# In-memory job tracking (use Redis in production)
_extraction_jobs: Dict[str, Dict[str, Any]] = {}


def get_engine():
    """Get database engine."""
    return create_engine(DATABASE_URL)


@router.post("/extract")
async def start_extraction(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Start a clip extraction job.
    
    Triggers the clip extraction pipeline via pub/sub events.
    Returns immediately with a job_id for status tracking.
    """
    # Resolve video path
    video_path = request.video_path
    
    if request.media_id and not video_path:
        # Look up path from database
        video_path = await _get_video_path(request.media_id)
        if not video_path:
            raise HTTPException(status_code=404, detail=f"Video not found: {request.media_id}")
    
    if request.video_url and not video_path:
        # TODO: Download video from URL
        raise HTTPException(status_code=501, detail="URL download not yet implemented")
    
    if not video_path:
        raise HTTPException(status_code=400, detail="Must provide video_path, video_url, or media_id")
    
    if not Path(video_path).exists():
        raise HTTPException(status_code=404, detail=f"Video file not found: {video_path}")
    
    # Create job
    job_id = str(uuid4())
    media_id = request.media_id or str(uuid4())
    
    job = {
        "job_id": job_id,
        "media_id": media_id,
        "video_path": video_path,
        "status": "pending",
        "progress": 0,
        "step": "queued",
        "clips_count": 0,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "options": request.options.model_dump()
    }
    _extraction_jobs[job_id] = job
    
    # Trigger extraction via event bus
    try:
        from services.event_bus import EventBus, Topics
        
        bus = EventBus.get_instance()
        await bus.publish(
            Topics.CLIP_EXTRACTION_REQUESTED,
            {
                "job_id": job_id,
                "video_path": video_path,
                "media_id": media_id,
                "output_dir": request.output_dir,
                "options": request.options.model_dump()
            }
        )
        
        job["status"] = "processing"
        job["step"] = "event_published"
        
    except Exception as e:
        logger.warning(f"Event bus not available, running synchronously: {e}")
        # Fallback: run in background task
        background_tasks.add_task(_run_extraction_sync, job_id, video_path, media_id, request)
    
    return {
        "job_id": job_id,
        "media_id": media_id,
        "status": "processing",
        "message": "Extraction job started"
    }


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """List extraction jobs."""
    jobs = list(_extraction_jobs.values())
    
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    
    # Sort by created_at desc
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "jobs": jobs[:limit],
        "total": len(jobs)
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    """Get extraction job status."""
    job = _extraction_jobs.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return job


@router.get("/clips/{media_id}")
async def get_clips(media_id: str) -> Dict[str, Any]:
    """Get extracted clips for a video."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, clip_path, start_time_sec, end_time_sec,
                           clip_type, metadata, created_at
                    FROM video_clips
                    WHERE source_video_id = :media_id
                    ORDER BY start_time_sec
                """),
                {"media_id": media_id}
            ).fetchall()
            
            clips = []
            for row in result:
                metadata = row[5] or {}
                clips.append({
                    "clip_id": str(row[0]),
                    "path": row[1],
                    "start_time_sec": row[2],
                    "end_time_sec": row[3],
                    "clip_type": row[4],
                    "text": metadata.get("text", ""),
                    "relevance_score": metadata.get("relevance_score", 0),
                    "reasoning": metadata.get("reasoning", ""),
                    "filename": metadata.get("filename", ""),
                    "created_at": row[6].isoformat() if row[6] else None
                })
            
            return {
                "media_id": media_id,
                "clips": clips,
                "count": len(clips)
            }
            
    except Exception as e:
        logger.error(f"Error fetching clips: {e}")
        return {"media_id": media_id, "clips": [], "count": 0, "error": str(e)}


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str) -> Dict[str, Any]:
    """Cancel an extraction job."""
    job = _extraction_jobs.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    if job["status"] in ["completed", "failed"]:
        return {"message": f"Job already {job['status']}", "job_id": job_id}
    
    job["status"] = "cancelled"
    job["step"] = "cancelled_by_user"
    
    return {"message": "Job cancelled", "job_id": job_id}


async def _get_video_path(media_id: str) -> Optional[str]:
    """Look up video path from database."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT source_uri FROM videos WHERE id = :id"),
                {"id": media_id}
            ).fetchone()
            
            if result and result[0]:
                return result[0]
    except Exception as e:
        logger.warning(f"Could not get video path: {e}")
    
    return None


async def _run_extraction_sync(
    job_id: str,
    video_path: str,
    media_id: str,
    request: ExtractionRequest
):
    """Run extraction synchronously as fallback."""
    job = _extraction_jobs.get(job_id)
    if not job:
        return
    
    try:
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(
            font_size=request.options.font_size,
            font_color=request.options.font_color
        )
        
        def progress_callback(pct: int, step: str):
            job["progress"] = pct
            job["step"] = step
        
        result = await service.extract_clips(
            video_path=video_path,
            output_dir=Path(request.output_dir) if request.output_dir else None,
            progress_callback=progress_callback,
            min_clip_duration=request.options.min_clip_duration,
            max_clip_duration=request.options.max_clip_duration,
            max_clips=request.options.max_clips
        )
        
        if result.success:
            job["status"] = "completed"
            job["clips_count"] = len(result.clips)
            job["completed_at"] = datetime.now().isoformat()
        else:
            job["status"] = "failed"
            job["error"] = result.error
            
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)


def update_job_status(job_id: str, status: str, **kwargs):
    """Update job status (called by worker)."""
    job = _extraction_jobs.get(job_id)
    if job:
        job["status"] = status
        job.update(kwargs)
