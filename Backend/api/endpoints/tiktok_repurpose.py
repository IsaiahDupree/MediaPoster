"""
TikTok Repurpose API
====================
API endpoints for repurposing TikTok content to other platforms.
"""
import os
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from services.tiktok_repurpose_service import (
    TikTokRepurposeService,
    get_repurpose_service,
    RepurposeResult,
)


router = APIRouter(prefix="/repurpose/tiktok", tags=["TikTok Repurpose"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class FetchRequest(BaseModel):
    """Request to fetch TikTok videos"""
    username: str = Field("isaiahdupree", description="TikTok username without @")
    count: int = Field(12, ge=1, le=50, description="Number of videos to fetch")


class DownloadRequest(BaseModel):
    """Request to download specific videos"""
    video_ids: List[str] = Field(..., description="List of TikTok video IDs")


class CrosspostRequest(BaseModel):
    """Request to schedule cross-posts"""
    video_ids: Optional[List[str]] = Field(None, description="Specific video IDs (or all recent)")
    platforms: List[str] = Field(
        ["instagram", "youtube", "threads", "twitter"],
        description="Platforms to post to"
    )
    account_ids: Optional[Dict[str, int]] = Field(
        None,
        description="Account IDs per platform (uses defaults if not provided)"
    )
    interval_hours: float = Field(1.0, description="Hours between posts")


class FullPipelineRequest(BaseModel):
    """Request to run full pipeline"""
    username: str = Field("isaiahdupree", description="TikTok username")
    count: int = Field(12, ge=1, le=50, description="Number of videos")
    platforms: List[str] = Field(
        ["instagram", "youtube", "threads", "twitter"],
        description="Platforms for cross-posting"
    )
    account_ids: Optional[Dict[str, int]] = Field(
        None,
        description="Account IDs: instagram=807, youtube=228, threads=243, twitter=571"
    )
    download: bool = Field(True, description="Download videos locally")
    analyze: bool = Field(True, description="Run AI analysis")
    schedule_crosspost: bool = Field(True, description="Schedule cross-posts")


class VideoResponse(BaseModel):
    """TikTok video info"""
    video_id: str
    username: str
    url: str
    caption: str
    views: int
    likes: int
    comments: int
    shares: int
    duration: int
    downloaded: bool
    local_path: Optional[str] = None


class PipelineResponse(BaseModel):
    """Pipeline execution result"""
    success: bool
    videos_fetched: int
    videos_downloaded: int
    videos_analyzed: int
    crosspost_scheduled: int
    errors: List[str]
    videos: List[Dict]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/fetch", response_model=List[VideoResponse])
async def fetch_tiktok_videos(request: FetchRequest):
    """
    Fetch latest videos from a TikTok profile via RapidAPI.
    
    Returns video metadata including views, likes, and download URLs.
    
    Example:
    ```json
    {"username": "isaiahdupree", "count": 12}
    ```
    """
    service = get_repurpose_service()
    
    try:
        videos = await service.fetch_tiktok_videos(
            username=request.username,
            count=request.count
        )
        
        return [
            VideoResponse(
                video_id=v.video_id,
                username=v.username,
                url=v.url,
                caption=v.caption or "",
                views=v.views,
                likes=v.likes,
                comments=v.comments,
                shares=v.shares,
                duration=v.duration,
                downloaded=v.downloaded,
                local_path=v.local_path,
            )
            for v in videos
        ]
        
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download")
async def download_videos(request: FetchRequest):
    """
    Fetch and download TikTok videos to local storage.
    
    Saves to: /Volumes/My Passport/MediaPoster/workspace1/tiktok_repurpose/
    """
    service = get_repurpose_service()
    
    try:
        # Fetch videos
        videos = await service.fetch_tiktok_videos(
            username=request.username,
            count=request.count
        )
        
        if not videos:
            raise HTTPException(status_code=404, detail="No videos found")
        
        # Download videos
        downloaded = await service.download_videos(videos)
        
        return {
            "success": True,
            "fetched": len(videos),
            "downloaded": len(downloaded),
            "videos": [
                {
                    "video_id": v.video_id,
                    "local_path": v.local_path,
                    "downloaded": v.downloaded,
                }
                for v in downloaded
            ]
        }
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-posted-content")
async def save_as_posted_content(request: FetchRequest):
    """
    Fetch TikTok videos and save them as posted content with stats.
    
    Associates videos with the TikTok account (710 = isaiah_dupree).
    """
    service = get_repurpose_service()
    
    try:
        # Fetch videos
        videos = await service.fetch_tiktok_videos(
            username=request.username,
            count=request.count
        )
        
        if not videos:
            raise HTTPException(status_code=404, detail="No videos found")
        
        # Save as posted content
        created = await service.save_as_posted_content(videos)
        
        return {
            "success": True,
            "fetched": len(videos),
            "created": created,
            "videos": [
                {
                    "video_id": v.video_id,
                    "url": v.url,
                    "views": v.views,
                    "likes": v.likes,
                }
                for v in videos
            ]
        }
        
    except Exception as e:
        logger.error(f"Save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crosspost")
async def schedule_crossposts(request: CrosspostRequest):
    """
    Schedule cross-posts to other platforms.
    
    Default account IDs:
    - Instagram: 807 (@the_isaiah_dupree)
    - YouTube: 228 (Isaiah Dupree)
    - Threads: 243 (@the_isaiah_dupree)
    - Twitter: 571 (@IsaiahDupree7)
    """
    service = get_repurpose_service()
    
    try:
        # Fetch recent videos if no specific IDs provided
        videos = await service.fetch_tiktok_videos(
            username="isaiahdupree",
            count=12
        )
        
        if not videos:
            raise HTTPException(status_code=404, detail="No videos found")
        
        # Download first
        videos = await service.download_videos(videos)
        
        # Schedule cross-posts
        scheduled = await service.schedule_crossposts(
            videos=videos,
            platforms=request.platforms,
            account_ids=request.account_ids,
            interval_hours=request.interval_hours
        )
        
        return {
            "success": True,
            "scheduled": scheduled,
            "platforms": request.platforms,
        }
        
    except Exception as e:
        logger.error(f"Crosspost error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/full-pipeline", response_model=PipelineResponse)
async def run_full_pipeline(request: FullPipelineRequest):
    """
    Run the complete TikTok repurpose pipeline.
    
    1. Fetch latest videos from TikTok
    2. Download videos locally
    3. Associate as posted content with stats
    4. Analyze videos (transcription, topics)
    5. Schedule cross-posts to other platforms
    
    Example:
    ```json
    {
        "username": "isaiahdupree",
        "count": 12,
        "platforms": ["instagram", "youtube", "threads", "twitter"],
        "account_ids": {
            "instagram": 807,
            "youtube": 228,
            "threads": 243,
            "twitter": 571
        }
    }
    ```
    """
    service = get_repurpose_service()
    
    try:
        result = await service.run_full_pipeline(
            username=request.username,
            count=request.count,
            platforms=request.platforms,
            account_ids=request.account_ids,
            download=request.download,
            analyze=request.analyze,
            schedule_crosspost=request.schedule_crosspost
        )
        
        return PipelineResponse(
            success=result.success,
            videos_fetched=result.videos_fetched,
            videos_downloaded=result.videos_downloaded,
            videos_analyzed=result.videos_analyzed,
            crosspost_scheduled=result.crosspost_scheduled,
            errors=result.errors,
            videos=result.videos
        )
        
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts")
async def get_default_accounts():
    """Get default account mappings for cross-posting."""
    return {
        "accounts": {
            "tiktok": {
                "id": 710,
                "username": "@isaiah_dupree",
                "description": "Source TikTok account"
            },
            "instagram": {
                "id": 807,
                "username": "@the_isaiah_dupree",
                "description": "Instagram target"
            },
            "youtube": {
                "id": 228,
                "username": "Isaiah Dupree",
                "description": "YouTube Shorts target"
            },
            "threads": {
                "id": 243,
                "username": "@the_isaiah_dupree",
                "description": "Threads target"
            },
            "twitter": {
                "id": 571,
                "username": "@IsaiahDupree7",
                "description": "Twitter/X target"
            }
        },
        "note": "Use these IDs in the account_ids parameter for cross-posting"
    }


@router.post("/thumbnails")
async def regenerate_thumbnails(request: FetchRequest):
    """
    Regenerate thumbnails for downloaded TikTok videos.
    
    Uses FFmpeg to extract a frame at 25% of video duration.
    """
    service = get_repurpose_service()
    
    try:
        # Fetch videos
        videos = await service.fetch_tiktok_videos(
            username=request.username,
            count=request.count
        )
        
        if not videos:
            raise HTTPException(status_code=404, detail="No videos found")
        
        # Download if needed
        videos = await service.download_videos(videos)
        
        # Generate thumbnails
        generated = await service.generate_thumbnails(videos)
        
        return {
            "success": True,
            "thumbnails_generated": generated,
            "total_videos": len(videos),
        }
        
    except Exception as e:
        logger.error(f"Thumbnail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/thumbnails/associate")
async def associate_thumbnails():
    """
    Associate generated thumbnails with existing media library entries.
    Updates videos, posted_content, and scheduled_posts tables.
    """
    service = get_repurpose_service()
    
    try:
        updated = await service.associate_thumbnails_with_media()
        
        return {
            "success": True,
            "records_updated": updated,
        }
        
    except Exception as e:
        logger.error(f"Thumbnail association error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_service_status():
    """Check service status and API configuration."""
    rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
    
    return {
        "service": "TikTok Repurpose",
        "rapidapi_configured": bool(rapidapi_key),
        "rapidapi_key_preview": f"{rapidapi_key[:8]}..." if rapidapi_key else "Not configured",
        "storage_path": str(get_repurpose_service().base_storage),
        "endpoints": [
            "POST /fetch - Fetch TikTok videos",
            "POST /download - Download videos locally",
            "POST /save-posted-content - Save as posted content",
            "POST /crosspost - Schedule cross-posts",
            "POST /full-pipeline - Run complete pipeline",
        ]
    }
