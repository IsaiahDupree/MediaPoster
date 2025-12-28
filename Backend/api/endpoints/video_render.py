"""
Video Render API Endpoints
Render videos from creative briefs with quality validation

Enhanced with comprehensive logging for debugging and monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from loguru import logger
from datetime import datetime
import uuid
import time

from database.connection import get_db
from services.video_renderer.creative_brief_renderer import (
    CreativeBriefRenderer,
    CreativeBrief,
    ContentType,
    VideoQuality,
    RenderResult,
)

router = APIRouter(prefix="/api/render", tags=["Video Render"])

# In-memory job tracking (would use Redis/DB in production)
_render_jobs: Dict[str, Dict[str, Any]] = {}


class RenderRequest(BaseModel):
    """Request to render a video from creative brief"""
    content_type: str = Field(..., description="Type: motivational_quote, broll_text, trend_breakdown, etc.")
    primary_text: str = Field(..., description="Main text content")
    duration_seconds: float = Field(default=5.0, ge=1, le=120)
    
    secondary_text: Optional[str] = None
    author_attribution: Optional[str] = None
    call_to_action: Optional[str] = None
    hashtags: List[str] = Field(default_factory=list)
    
    font_family: str = "Inter"
    primary_color: str = "#ffffff"
    secondary_color: str = "rgba(255,255,255,0.8)"
    background_color: str = "rgba(0,0,0,0.5)"
    text_size: int = 64
    
    background_video_path: Optional[str] = None
    background_image_path: Optional[str] = None
    background_music_path: Optional[str] = None
    music_volume: float = 0.3
    
    animation_style: str = "fade"
    animation_duration: float = 0.8
    
    output_width: int = 1080
    output_height: int = 1920
    fps: int = 30
    quality: str = "standard"


class QuickRenderRequest(BaseModel):
    """Simplified request for quick renders"""
    text: str
    style: str = "quote"  # quote, broll, headline
    duration: float = 5.0
    author: Optional[str] = None


class RenderResponse(BaseModel):
    """Response from render request"""
    job_id: str
    status: str
    message: str


class RenderStatusResponse(BaseModel):
    """Status of a render job"""
    job_id: str
    status: str
    progress: float
    video_path: Optional[str]
    quality_passed: Optional[bool]
    render_time_seconds: Optional[float]
    error: Optional[str]


@router.post("/create", response_model=RenderResponse)
async def create_render_job(
    request: RenderRequest,
    background_tasks: BackgroundTasks,
):
    """
    Create a new render job from a creative brief.
    Returns a job_id to track progress.
    """
    job_id = str(uuid.uuid4())
    
    logger.info("=" * 60)
    logger.info(f"📥 [API] POST /api/render/create")
    logger.info(f"   Job ID: {job_id}")
    logger.info(f"   Content Type: {request.content_type}")
    logger.info(f"   Duration: {request.duration_seconds}s")
    logger.info(f"   Text: {request.primary_text[:50]}...")
    logger.info("=" * 60)
    
    # Map string to enum
    try:
        content_type = ContentType(request.content_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content_type. Must be one of: {[t.value for t in ContentType]}"
        )
    
    try:
        quality = VideoQuality(request.quality)
    except ValueError:
        quality = VideoQuality.STANDARD
    
    # Create brief
    brief = CreativeBrief(
        brief_id=job_id,
        content_type=content_type,
        primary_text=request.primary_text,
        secondary_text=request.secondary_text,
        author_attribution=request.author_attribution,
        call_to_action=request.call_to_action,
        hashtags=request.hashtags,
        duration_seconds=request.duration_seconds,
        font_family=request.font_family,
        primary_color=request.primary_color,
        secondary_color=request.secondary_color,
        background_color=request.background_color,
        text_size=request.text_size,
        background_video_path=request.background_video_path,
        background_image_path=request.background_image_path,
        background_music_path=request.background_music_path,
        music_volume=request.music_volume,
        animation_style=request.animation_style,
        animation_duration=request.animation_duration,
        output_width=request.output_width,
        output_height=request.output_height,
        fps=request.fps,
        quality=quality,
    )
    
    # Initialize job tracking
    _render_jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "started_at": datetime.now().isoformat(),
        "brief": brief.to_dict(),
        "result": None,
    }
    
    # Start render in background
    background_tasks.add_task(_run_render_job, job_id, brief)
    
    return RenderResponse(
        job_id=job_id,
        status="queued",
        message=f"Render job created. Track with GET /api/render/status/{job_id}"
    )


@router.post("/quick", response_model=RenderResponse)
async def quick_render(
    request: QuickRenderRequest,
    background_tasks: BackgroundTasks,
):
    """
    Quick render with minimal parameters.
    Good for testing and simple content.
    """
    job_id = str(uuid.uuid4())
    
    # Map style to content type
    style_map = {
        "quote": ContentType.MOTIVATIONAL_QUOTE,
        "broll": ContentType.BROLL_TEXT,
        "headline": ContentType.HOOK_INTRO,
    }
    content_type = style_map.get(request.style, ContentType.BROLL_TEXT)
    
    brief = CreativeBrief(
        brief_id=job_id,
        content_type=content_type,
        primary_text=request.text,
        author_attribution=request.author,
        duration_seconds=request.duration,
    )
    
    _render_jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "started_at": datetime.now().isoformat(),
        "brief": brief.to_dict(),
        "result": None,
    }
    
    background_tasks.add_task(_run_render_job, job_id, brief)
    
    return RenderResponse(
        job_id=job_id,
        status="queued",
        message=f"Quick render started. Track with GET /api/render/status/{job_id}"
    )


@router.get("/status/{job_id}", response_model=RenderStatusResponse)
async def get_render_status(job_id: str):
    """Get status of a render job"""
    if job_id not in _render_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = _render_jobs[job_id]
    result = job.get("result")
    
    return RenderStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        video_path=result.video_path if result else None,
        quality_passed=result.quality_report.passed if result and result.quality_report else None,
        render_time_seconds=result.render_time_seconds if result else None,
        error=result.error_message if result else job.get("error"),
    )


@router.get("/jobs")
async def list_render_jobs(limit: int = 20):
    """List recent render jobs"""
    jobs = []
    for job_id, job in list(_render_jobs.items())[-limit:]:
        jobs.append({
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "started_at": job["started_at"],
            "content_type": job["brief"].get("content_type"),
        })
    
    return {
        "total": len(_render_jobs),
        "jobs": jobs
    }


@router.get("/content-types")
async def list_content_types():
    """List available content types for rendering"""
    return {
        "content_types": [
            {
                "id": t.value,
                "name": t.name.replace("_", " ").title(),
                "description": _get_content_type_description(t),
            }
            for t in ContentType
        ]
    }


@router.post("/test")
async def test_render():
    """
    Run a test render to verify the pipeline is working.
    Creates a simple 3-second motivational quote video.
    """
    job_id = str(uuid.uuid4())
    
    logger.info("=" * 60)
    logger.info(f"🧪 [API] POST /api/render/test")
    logger.info(f"   Job ID: {job_id}")
    logger.info(f"   Type: Test render (motivational quote)")
    logger.info("=" * 60)
    
    brief = CreativeBrief(
        brief_id=job_id,
        content_type=ContentType.MOTIVATIONAL_QUOTE,
        primary_text="Test render successful!",
        author_attribution="MediaPoster",
        duration_seconds=3.0,
        output_width=1080,
        output_height=1920,
    )
    
    renderer = CreativeBriefRenderer()
    
    def progress_callback(progress: float, message: str):
        logger.info(f"   📊 Progress: {progress:.0%} - {message}")
    
    start_time = time.time()
    result = await renderer.render(brief, on_progress=progress_callback)
    total_time = time.time() - start_time
    
    if result.success:
        logger.success(f"✅ [API] Test render completed in {total_time:.2f}s")
    else:
        logger.error(f"❌ [API] Test render failed: {result.error_message}")
    
    return {
        "success": result.success,
        "job_id": job_id,
        "video_path": result.video_path,
        "render_time_seconds": result.render_time_seconds,
        "quality_report": result.quality_report.to_dict() if result.quality_report else None,
        "error": result.error_message,
    }


async def _run_render_job(job_id: str, brief: CreativeBrief):
    """Background task to run render job"""
    try:
        _render_jobs[job_id]["status"] = "rendering"
        
        renderer = CreativeBriefRenderer()
        
        def progress_callback(progress: float, message: str):
            _render_jobs[job_id]["progress"] = progress
            _render_jobs[job_id]["status_message"] = message
        
        result = await renderer.render(brief, on_progress=progress_callback)
        
        _render_jobs[job_id]["status"] = "completed" if result.success else "failed"
        _render_jobs[job_id]["progress"] = 1.0
        _render_jobs[job_id]["result"] = result
        
    except Exception as e:
        logger.error(f"Render job {job_id} failed: {e}")
        _render_jobs[job_id]["status"] = "failed"
        _render_jobs[job_id]["error"] = str(e)


def _get_content_type_description(content_type: ContentType) -> str:
    """Get description for content type"""
    descriptions = {
        ContentType.MOTIVATIONAL_QUOTE: "Elegant quote with author attribution",
        ContentType.BROLL_TEXT: "Text overlay on B-roll footage",
        ContentType.TREND_BREAKDOWN: "Analysis of trending topic",
        ContentType.PRODUCT_PROMO: "Product showcase with CTA",
        ContentType.HOOK_INTRO: "Attention-grabbing intro hook",
        ContentType.CTA_OUTRO: "Call-to-action ending",
    }
    return descriptions.get(content_type, "Video content")
