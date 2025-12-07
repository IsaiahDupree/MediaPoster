"""
Clip Management API Endpoints
Comprehensive API for clip selection, editing, and publishing
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from services.clip_selector import ClipSelector, ClipSuggestion
from services.clip_editor import ClipEditor
from services.clip_publisher import ClipPublisher

router = APIRouter()


# ==================== Request/Response Models ====================

class ClipCreateRequest(BaseModel):
    """Request to create a new clip"""
    video_id: str
    user_id: str
    start_time: float
    end_time: float
    title: Optional[str] = None
    description: Optional[str] = None
    clip_type: str = "custom"
    overlay_config: Optional[Dict] = None
    caption_config: Optional[Dict] = None
    thumbnail_config: Optional[Dict] = None


class ClipUpdateRequest(BaseModel):
    """Request to update clip configuration"""
    overlay_config: Optional[Dict] = None
    caption_config: Optional[Dict] = None
    thumbnail_config: Optional[Dict] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ClipPublishRequest(BaseModel):
    """Request to publish clip to platforms"""
    platforms: List[str]
    schedule_time: Optional[datetime] = None
    custom_configs: Optional[Dict[str, Dict]] = None


# ==================== Clip Suggestion Endpoints ====================

@router.get("/suggest")
async def suggest_clips(
    video_id: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    max_clips: int = Query(5),
    min_duration: float = Query(15.0),
    max_duration: float = Query(180.0),
    db: AsyncSession = Depends(get_db)
):
    """Get AI-powered clip suggestions for a video"""
    # Validate required parameters first, before any DB operations
    if not video_id:
        raise HTTPException(status_code=400, detail="video_id is required")
    
    # For now, return empty suggestions until ClipSelector is converted to async
    from loguru import logger
    logger.warning("ClipSelector needs async conversion - returning empty suggestions")
    
    return {
        "video_id": video_id,
        "platform": platform,
        "suggestions": []
    }


# ==================== Clip CRUD Endpoints ====================

@router.post("/create")
async def create_clip(request: ClipCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new video clip"""
    editor = ClipEditor(db)
    
    try:
        clip = editor.create_clip(**request.dict())
        return {"clip_id": str(clip.id), "status": clip.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{clip_id}")
async def get_clip(clip_id: str, db: AsyncSession = Depends(get_db)):
    """Get clip details"""
    editor = ClipEditor(db)
    
    try:
        return editor.get_clip_preview_data(clip_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{clip_id}")
async def update_clip(clip_id: str, request: ClipUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update clip configuration"""
    editor = ClipEditor(db)
    
    try:
        clip = editor.update_clip_config(clip_id, **request.dict(exclude_unset=True))
        return {"clip_id": str(clip.id), "status": clip.status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{clip_id}")
async def delete_clip(clip_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a clip"""
    editor = ClipEditor(db)
    
    if not editor.delete_clip(clip_id):
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return {"message": "Clip deleted"}


@router.get("/video/{video_id}")
async def get_video_clips(video_id: str, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Get all clips for a video"""
    editor = ClipEditor(db)
    clips = editor.get_video_clips(video_id, status=status)
    
    return {"video_id": video_id, "total_clips": len(clips), "clips": [
        {"clip_id": str(c.id), "title": c.title, "start_time": c.start_time, 
         "end_time": c.end_time, "status": c.status, "ai_score": c.ai_score}
        for c in clips
    ]}


# ==================== Platform Variant Endpoints  ====================

@router.post("/{clip_id}/variants")
async def generate_platform_variants(clip_id: str, platforms: Optional[List[str]] = None, db: AsyncSession = Depends(get_db)):
    """Generate platform-specific configurations"""
    editor = ClipEditor(db)
    
    try:
        variants = editor.generate_platform_variants(clip_id, platforms=platforms)
        return {"clip_id": clip_id, "variants": variants}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Publishing Endpoints ====================

@router.post("/{clip_id}/publish")
async def publish_clip(clip_id: str, request: ClipPublishRequest, db: AsyncSession = Depends(get_db)):
    """Publish clip to multiple platforms"""
    publisher = ClipPublisher(db)
    
    try:
        posts = await publisher.publish_clip(
            clip_id=clip_id,
            platforms=request.platforms,
            schedule_time=request.schedule_time,
            custom_configs=request.custom_configs
        )
        
        return {"clip_id": clip_id, "published_count": len(posts), "posts": [
            {"post_id": str(p.id), "platform": p.platform, "status": p.status}
            for p in posts
        ]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{clip_id}/posts")
async def get_clip_posts(clip_id: str, db: AsyncSession = Depends(get_db)):
    """Get all platform posts for a clip"""
    publisher = ClipPublisher(db)
    posts = publisher.get_clip_posts(clip_id)
    return {"clip_id": clip_id, "total_posts": len(posts), "posts": posts}


@router.get("/{clip_id}/performance")
async def get_clip_performance(clip_id: str, db: AsyncSession = Depends(get_db)):
    """Get aggregated performance metrics"""
    publisher = ClipPublisher(db)
    return publisher.get_clip_performance(clip_id)
