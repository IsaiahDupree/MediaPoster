"""
B-Roll Video Producer API
==========================
API endpoints for producing B-roll videos with trendy text overlays.
"""
import os
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from loguru import logger

from services.broll_video_producer import (
    BrollVideoProducer,
    BrollVideoRequest,
    BrollVideoResult,
    TextStyle,
    TextPosition,
    get_producer,
)


router = APIRouter(prefix="/broll-producer", tags=["B-Roll Producer"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ProduceVideoRequest(BaseModel):
    """Request to produce a B-roll video with text overlays"""
    video_id: Optional[str] = Field(None, description="Specific video ID to use, or auto-select")
    min_duration: float = Field(5.0, ge=1.0, le=300.0, description="Minimum video duration in seconds")
    max_duration: float = Field(30.0, ge=1.0, le=300.0, description="Maximum video duration in seconds")
    require_no_people: bool = Field(False, description="Only select videos without people")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    
    use_trending_text: bool = Field(True, description="Generate AI-powered trending text overlays")
    custom_text: Optional[str] = Field(None, description="Custom text to overlay (overrides AI)")
    text_style: str = Field("bold_center", description="Text style: bold_center, subtitle, headline, quote, minimal, impact")
    text_position: str = Field("center", description="Text position: top, center, bottom, lower_third")
    niche: str = Field("general", description="Content niche for text generation")
    tone: str = Field("engaging", description="Tone: engaging, inspirational, humorous, professional")
    
    output_format: str = Field("mp4", description="Output format")
    resolution: str = Field("1080x1920", description="Output resolution")
    fps: int = Field(30, ge=15, le=60, description="Frames per second")


class ProduceVideoResponse(BaseModel):
    """Response from video production"""
    job_id: str
    success: bool
    video_path: Optional[str] = None
    video_url: Optional[str] = None
    source_video_id: Optional[str] = None
    text_overlays: List[dict] = []
    duration_seconds: float = 0.0
    file_size_mb: float = 0.0
    trending_phrases_used: List[str] = []
    error: Optional[str] = None


class TrendingPhrase(BaseModel):
    """A trending phrase with score"""
    phrase: str
    score: float


class TrendingPhrasesResponse(BaseModel):
    """Response with trending phrases"""
    phrases: List[TrendingPhrase]
    niche: str


class BrollCandidateResponse(BaseModel):
    """B-roll candidate info"""
    id: str
    file_name: str
    duration_sec: float
    score: Optional[float]
    topics: List[str]
    thumbnail_url: str
    video_url: str


# =============================================================================
# PRODUCTION ENDPOINTS
# =============================================================================

@router.post("/produce", response_model=ProduceVideoResponse)
async def produce_broll_video(request: ProduceVideoRequest):
    """
    Produce a B-roll video with AI-generated trendy text overlays.
    
    Pipeline:
    1. Find/select B-roll video from media library
    2. Generate trendy text overlays using AI
    3. Render final video with text burned in
    4. Return video URL
    
    Example:
    ```
    POST /api/broll-producer/produce
    {
        "use_trending_text": true,
        "niche": "productivity",
        "tone": "inspirational",
        "text_position": "center"
    }
    ```
    """
    try:
        producer = get_producer()
        
        # Convert API request to service request
        service_request = BrollVideoRequest(
            video_id=request.video_id,
            min_duration=request.min_duration,
            max_duration=request.max_duration,
            require_no_people=request.require_no_people,
            tags=request.tags,
            use_trending_text=request.use_trending_text,
            custom_text=request.custom_text,
            text_style=TextStyle(request.text_style) if request.text_style else TextStyle.BOLD_CENTER,
            text_position=TextPosition(request.text_position) if request.text_position else TextPosition.CENTER,
            niche=request.niche,
            tone=request.tone,
            output_format=request.output_format,
            resolution=request.resolution,
            fps=request.fps,
        )
        
        result = await producer.produce(service_request)
        
        return ProduceVideoResponse(
            job_id=result.job_id,
            success=result.success,
            video_path=result.video_path,
            video_url=result.video_url,
            source_video_id=result.source_video_id,
            text_overlays=result.text_overlays,
            duration_seconds=result.duration_seconds,
            file_size_mb=result.file_size_mb,
            trending_phrases_used=result.trending_phrases_used,
            error=result.error,
        )
        
    except Exception as e:
        logger.error(f"Video production failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/produce/async")
async def produce_broll_video_async(
    request: ProduceVideoRequest,
    background_tasks: BackgroundTasks
):
    """
    Start async video production job.
    Returns immediately with job_id for polling.
    """
    import uuid
    job_id = str(uuid.uuid4())
    
    async def run_production():
        producer = get_producer()
        service_request = BrollVideoRequest(
            job_id=job_id,
            video_id=request.video_id,
            min_duration=request.min_duration,
            max_duration=request.max_duration,
            require_no_people=request.require_no_people,
            tags=request.tags,
            use_trending_text=request.use_trending_text,
            custom_text=request.custom_text,
            text_style=TextStyle(request.text_style) if request.text_style else TextStyle.BOLD_CENTER,
            text_position=TextPosition(request.text_position) if request.text_position else TextPosition.CENTER,
            niche=request.niche,
            tone=request.tone,
        )
        await producer.produce(service_request)
    
    background_tasks.add_task(run_production)
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Video production started. Poll /status/{job_id} for progress."
    }


# =============================================================================
# OUTPUT ENDPOINTS
# =============================================================================

@router.get("/output/{job_id}")
async def get_output_video(job_id: str):
    """
    Get the produced video file.
    """
    output_dir = Path("data/broll_outputs")
    video_path = output_dir / f"{job_id}.mp4"
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"broll_{job_id}.mp4"
    )


@router.get("/output/{job_id}/stream")
async def stream_output_video(job_id: str):
    """
    Stream the produced video.
    """
    output_dir = Path("data/broll_outputs")
    video_path = output_dir / f"{job_id}.mp4"
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
    )


# =============================================================================
# TRENDING CONTENT ENDPOINTS
# =============================================================================

@router.get("/trending-phrases", response_model=TrendingPhrasesResponse)
async def get_trending_phrases(
    niche: str = Query("general", description="Content niche"),
    limit: int = Query(10, ge=1, le=50, description="Number of phrases to return")
):
    """
    Get current trending phrases for text overlays.
    
    Uses AI to identify viral text overlay trends.
    """
    try:
        producer = get_producer()
        phrases = await producer.get_trending_phrases(niche=niche, limit=limit)
        
        return TrendingPhrasesResponse(
            phrases=[TrendingPhrase(**p) for p in phrases],
            niche=niche
        )
        
    except Exception as e:
        logger.error(f"Failed to get trending phrases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-text")
async def generate_text_overlays(
    video_id: str = Query(..., description="Video ID to generate text for"),
    niche: str = Query("general", description="Content niche"),
    tone: str = Query("engaging", description="Tone: engaging, inspirational, humorous, professional"),
    count: int = Query(3, ge=1, le=10, description="Number of text options to generate")
):
    """
    Generate AI text overlay suggestions for a specific video.
    
    Returns multiple text options without rendering.
    """
    try:
        producer = get_producer()
        
        # Get video info
        video_info = await producer._get_video_by_id(video_id)
        if not video_info:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Create a mock request for text generation
        request = BrollVideoRequest(
            video_id=video_id,
            niche=niche,
            tone=tone,
            use_trending_text=True,
        )
        
        texts = await producer._generate_trending_text(request, video_info)
        
        return {
            "video_id": video_id,
            "suggestions": texts,
            "video_info": {
                "file_name": video_info.get("file_name"),
                "duration_sec": video_info.get("duration_sec"),
                "topics": video_info.get("topics", []),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CANDIDATE BROWSING ENDPOINTS
# =============================================================================

@router.get("/candidates", response_model=List[BrollCandidateResponse])
async def list_broll_candidates(
    min_duration: float = Query(3.0, ge=0, description="Minimum duration"),
    max_duration: float = Query(60.0, ge=1, description="Maximum duration"),
    limit: int = Query(20, ge=1, le=100, description="Number of candidates"),
    min_score: float = Query(0.0, ge=0, le=100, description="Minimum pre-social score"),
):
    """
    List B-roll video candidates from media library.
    
    Returns videos suitable for B-roll with text overlays.
    """
    from sqlalchemy import create_engine, text
    
    engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres"))
    
    with engine.connect() as conn:
        query = text("""
            SELECT 
                v.id, v.file_name, v.duration_sec,
                va.pre_social_score, va.topics
            FROM videos v
            LEFT JOIN video_analysis va ON v.id = va.video_id
            WHERE v.duration_sec >= :min_duration
              AND v.duration_sec <= :max_duration
              AND v.source_uri IS NOT NULL
              AND (va.pre_social_score >= :min_score OR va.pre_social_score IS NULL)
            ORDER BY va.pre_social_score DESC NULLS LAST
            LIMIT :limit
        """)
        
        result = conn.execute(query, {
            "min_duration": min_duration,
            "max_duration": max_duration,
            "min_score": min_score,
            "limit": limit,
        })
        
        candidates = []
        for row in result:
            candidates.append(BrollCandidateResponse(
                id=str(row[0]),
                file_name=row[1] or "Unknown",
                duration_sec=row[2] or 0,
                score=row[3],
                topics=row[4] or [],
                thumbnail_url=f"/api/media-db/thumbnail/{row[0]}",
                video_url=f"/api/media-provider/stream/{row[0]}",
            ))
        
        return candidates


@router.get("/candidates/{video_id}/preview")
async def preview_candidate(
    video_id: str,
    text: str = Query("Your text here", description="Text to preview"),
    position: str = Query("center", description="Text position"),
    style: str = Query("bold_center", description="Text style"),
):
    """
    Generate a preview frame with text overlay.
    
    Returns a single frame image showing how the text will look.
    """
    # TODO: Implement frame extraction + text overlay preview
    return {
        "video_id": video_id,
        "preview_text": text,
        "position": position,
        "style": style,
        "preview_url": f"/api/media-db/thumbnail/{video_id}",
        "message": "Full preview coming soon - use thumbnail for now"
    }
