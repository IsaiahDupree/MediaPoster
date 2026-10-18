"""
Explainer Video API
===================
REST API endpoints for the explainer video engine.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from services.explainer_video import (
    ExplainerVideoService,
    ContentBrief,
    ContentItem,
    ContentItemType,
    VideoMeta,
    StyleConfig,
    PacingConfig,
    AudioConfig,
    NarrationConfig,
    FormatRegistry,
    get_format_registry,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/explainer", tags=["Explainer Video"])

# Service instance
_service: Optional[ExplainerVideoService] = None

def get_service() -> ExplainerVideoService:
    global _service
    if _service is None:
        _service = ExplainerVideoService()
    return _service


# =========================================================================
# REQUEST/RESPONSE MODELS
# =========================================================================

class TopicInput(BaseModel):
    """Input for a single topic."""
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    narration_script: Optional[str] = None


class CreateBriefFromPromptRequest(BaseModel):
    """Request to generate a brief from a prompt."""
    prompt: str = Field(..., description="Natural language description of the video")
    format_id: str = Field(default="explainer_v1", description="Target format")
    num_topics: int = Field(default=10, ge=1, le=50, description="Number of topics to generate")


class CreateBriefFromTopicsRequest(BaseModel):
    """Request to create a brief from a list of topics."""
    title: str = Field(..., description="Video title")
    topics: List[TopicInput] = Field(..., description="List of topics")
    format_id: str = Field(default="explainer_v1")
    description: Optional[str] = None
    target_duration_seconds: int = Field(default=600, ge=60, le=7200)


class CreateVideoRequest(BaseModel):
    """Request to create a video."""
    brief_id: Optional[str] = None
    brief: Optional[Dict] = None
    format_id: str = Field(default="explainer_v1")
    resolve_assets: bool = True
    generate_tts: bool = True
    render: bool = True


class BriefResponse(BaseModel):
    """Response containing a content brief."""
    id: str
    video: Dict
    items: List[Dict]
    style: Dict
    pacing: Dict
    audio: Dict
    estimated_duration_seconds: float


class FormatResponse(BaseModel):
    """Response containing a video format."""
    format_id: str
    name: str
    description: str
    layout: str
    aspect_ratio: str
    tags: List[str]


class JobResponse(BaseModel):
    """Response containing a render job."""
    id: str
    brief_id: str
    format_id: str
    status: str
    progress: float
    created_at: str
    completed_at: Optional[str]
    output_path: Optional[str]
    error: Optional[str]


# =========================================================================
# BRIEF ENDPOINTS
# =========================================================================

@router.post("/brief/from-prompt", response_model=BriefResponse)
async def create_brief_from_prompt(request: CreateBriefFromPromptRequest):
    """
    Generate a content brief from a natural language prompt using AI.
    
    Example:
        POST /api/explainer/brief/from-prompt
        {"prompt": "Create an explainer about machine learning algorithms", "num_topics": 10}
    """
    service = get_service()
    
    try:
        brief = await service.generate_brief_from_prompt(
            prompt=request.prompt,
            format_id=request.format_id,
            num_topics=request.num_topics,
        )
        
        return BriefResponse(
            id=brief.id,
            video=brief.video.to_dict(),
            items=[item.to_dict() for item in brief.items],
            style=brief.style.to_dict(),
            pacing=brief.pacing.to_dict(),
            audio=brief.audio.to_dict(),
            estimated_duration_seconds=brief.calculate_total_duration(),
        )
        
    except Exception as e:
        logger.error(f"Failed to generate brief: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brief/from-topics", response_model=BriefResponse)
async def create_brief_from_topics(request: CreateBriefFromTopicsRequest):
    """
    Create a content brief from a list of topics.
    AI will generate narration scripts for each topic.
    
    Example:
        POST /api/explainer/brief/from-topics
        {
            "title": "Every Sorting Algorithm Explained",
            "topics": [
                {"title": "Bubble Sort"},
                {"title": "Quick Sort"},
                {"title": "Merge Sort"}
            ]
        }
    """
    service = get_service()
    
    try:
        topic_titles = [t.title for t in request.topics]
        
        brief = await service.generate_brief_from_topics(
            title=request.title,
            topics=topic_titles,
            format_id=request.format_id,
        )
        
        # Apply custom descriptions if provided
        for i, topic_input in enumerate(request.topics):
            if i < len(brief.items) and topic_input.description:
                brief.items[i].description = topic_input.description
        
        return BriefResponse(
            id=brief.id,
            video=brief.video.to_dict(),
            items=[item.to_dict() for item in brief.items],
            style=brief.style.to_dict(),
            pacing=brief.pacing.to_dict(),
            audio=brief.audio.to_dict(),
            estimated_duration_seconds=brief.calculate_total_duration(),
        )
        
    except Exception as e:
        logger.error(f"Failed to create brief: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# FORMAT ENDPOINTS
# =========================================================================

@router.get("/formats", response_model=List[FormatResponse])
async def list_formats():
    """
    List all available video formats.
    
    Returns formats like:
    - explainer_v1: Classic "Every X Explained" format
    - listicle_v1: Top 10 style format
    - shorts_v1: Vertical short-form content
    - dev_vlog_v1: Developer vlog format
    """
    registry = get_format_registry()
    
    return [
        FormatResponse(
            format_id=f.format_id,
            name=f.name,
            description=f.description,
            layout=f.layout.value,
            aspect_ratio=f.aspect_ratio,
            tags=f.tags,
        )
        for f in registry.list_all()
    ]


@router.get("/formats/{format_id}")
async def get_format(format_id: str):
    """Get details of a specific format."""
    registry = get_format_registry()
    format_config = registry.get(format_id)
    
    if not format_config:
        raise HTTPException(status_code=404, detail=f"Format not found: {format_id}")
    
    return format_config.to_dict()


# =========================================================================
# VIDEO CREATION ENDPOINTS
# =========================================================================

@router.post("/video/create", response_model=JobResponse)
async def create_video(
    request: CreateVideoRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a video from a content brief.
    
    Can either provide:
    - brief_id: ID of a previously created brief
    - brief: Full brief JSON object
    
    Returns a job that can be polled for status.
    """
    service = get_service()
    
    try:
        # Get or create brief
        if request.brief:
            brief = ContentBrief.from_dict(request.brief)
        elif request.brief_id:
            # TODO: Load brief from storage
            raise HTTPException(status_code=400, detail="brief_id not yet supported, provide full brief")
        else:
            raise HTTPException(status_code=400, detail="Either brief_id or brief required")
        
        # Start video creation (async)
        job = await service.create_video(
            brief=brief,
            format_id=request.format_id,
            resolve_assets=request.resolve_assets,
            generate_tts=request.generate_tts,
            render=request.render,
        )
        
        return JobResponse(
            id=job.id,
            brief_id=job.brief_id,
            format_id=job.format_id,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            output_path=job.output_path,
            error=job.error,
        )
        
    except Exception as e:
        logger.error(f"Failed to create video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/jobs", response_model=List[JobResponse])
async def list_jobs():
    """List all render jobs."""
    service = get_service()
    
    return [
        JobResponse(
            id=job.id,
            brief_id=job.brief_id,
            format_id=job.format_id,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            output_path=job.output_path,
            error=job.error,
        )
        for job in service.list_jobs()
    ]


@router.get("/video/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get status of a render job."""
    service = get_service()
    job = service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return JobResponse(
        id=job.id,
        brief_id=job.brief_id,
        format_id=job.format_id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        output_path=job.output_path,
        error=job.error,
    )


# =========================================================================
# ASSET ENDPOINTS
# =========================================================================

@router.get("/assets/music")
async def search_music(
    query: str = "ambient",
    genre: Optional[str] = None,
    count: int = 5
):
    """
    Search for background music.
    
    Example:
        GET /api/explainer/assets/music?query=upbeat&count=5
    """
    service = get_service()
    
    try:
        assets = await service.asset_manager.search_music(
            query=query,
            genre=genre,
            count=count,
        )
        
        return {"assets": [a.to_dict() for a in assets]}
        
    except Exception as e:
        logger.error(f"Music search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/broll")
async def search_broll(
    query: str,
    orientation: str = "landscape",
    count: int = 5
):
    """
    Search for B-roll video clips.
    
    Example:
        GET /api/explainer/assets/broll?query=technology&count=5
    """
    service = get_service()
    
    try:
        assets = await service.asset_manager.search_broll(
            query=query,
            orientation=orientation,
            count=count,
        )
        
        return {"assets": [a.to_dict() for a in assets]}
        
    except Exception as e:
        logger.error(f"B-roll search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/sfx")
async def search_sound_effects(
    query: str,
    duration_max: Optional[float] = None,
    count: int = 5
):
    """
    Search for sound effects.
    
    Example:
        GET /api/explainer/assets/sfx?query=whoosh&count=3
    """
    service = get_service()
    
    try:
        assets = await service.asset_manager.search_sound_effects(
            query=query,
            duration_max=duration_max,
            count=count,
        )
        
        return {"assets": [a.to_dict() for a in assets]}
        
    except Exception as e:
        logger.error(f"SFX search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/memes")
async def search_memes(query: str, count: int = 5):
    """
    Search for meme templates.
    
    Example:
        GET /api/explainer/assets/memes?query=drake&count=3
    """
    service = get_service()
    
    try:
        assets = await service.asset_manager.search_memes(
            query=query,
            count=count,
        )
        
        return {"assets": [a.to_dict() for a in assets]}
        
    except Exception as e:
        logger.error(f"Meme search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assets/generate-image")
async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    style: str = "vivid"
):
    """
    Generate an image using DALL-E.
    
    Example:
        POST /api/explainer/assets/generate-image
        {"prompt": "futuristic city skyline at sunset", "size": "1792x1024"}
    """
    service = get_service()
    
    try:
        asset = await service.asset_manager.generate_image(
            prompt=prompt,
            size=size,
            style=style,
        )
        
        if not asset:
            raise HTTPException(status_code=500, detail="Image generation failed")
        
        return {"asset": asset.to_dict()}
        
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# QUICK START ENDPOINTS
# =========================================================================

@router.post("/quick-start")
async def quick_start(
    title: str,
    topics: List[str],
    format_id: str = "explainer_v1"
):
    """
    Quick start - create a video with minimal input.
    
    Just provide a title and list of topics.
    
    Example:
        POST /api/explainer/quick-start
        {
            "title": "Every Python Library Explained",
            "topics": ["NumPy", "Pandas", "Matplotlib", "TensorFlow", "PyTorch"]
        }
    """
    service = get_service()
    
    try:
        # Generate brief with narration
        brief = await service.generate_brief_from_topics(
            title=title,
            topics=topics,
            format_id=format_id,
        )
        
        # Create video
        job = await service.create_video(
            brief=brief,
            format_id=format_id,
            resolve_assets=True,
            generate_tts=True,
            render=True,
        )
        
        return {
            "brief_id": brief.id,
            "job_id": job.id,
            "status": job.status,
            "estimated_duration_seconds": brief.calculate_total_duration(),
            "topic_count": len(brief.items),
        }
        
    except Exception as e:
        logger.error(f"Quick start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
