"""
TikTok Analytics API Endpoints
Fetch TikTok video comments using Safari automation
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, List
import logging
import asyncio

from services.tiktok_analytics_service import (
    get_tiktok_analytics_service,
    TikTokComment,
)
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter(tags=["TikTok Analytics"])


@router.get("/status", response_model=dict)
async def get_tiktok_status():
    """
    Check TikTok automation status
    
    Returns:
        Configuration status and username
    """
    service = get_tiktok_analytics_service()
    
    return {
        "username_configured": bool(service.tiktok_username),
        "username": service.tiktok_username if service.tiktok_username else None,
        "automation_initialized": service._initialized,
    }


@router.get("/comments", response_model=dict)
async def get_profile_comments(
    username: Optional[str] = None,
    max_videos: int = Query(default=5, ge=1, le=20),
    max_comments_per_video: int = Query(default=30, ge=1, le=100)
):
    """
    Get comments for all recent videos from a TikTok profile
    
    Args:
        username: TikTok username (uses env var if not provided)
        max_videos: Maximum videos to check (1-20)
        max_comments_per_video: Maximum comments per video (1-100)
        
    Returns:
        All comments organized by video
        
    Note: This endpoint uses Safari automation and may take time.
    """
    service = get_tiktok_analytics_service()
    
    if not username and not service.tiktok_username:
        raise HTTPException(
            status_code=400,
            detail="No TikTok username provided and TIKTOK_USERNAME not configured"
        )
    
    try:
        result = await service.get_all_profile_comments(
            username=username,
            max_videos=max_videos,
            max_comments_per_video=max_comments_per_video
        )
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"Error fetching TikTok comments: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch TikTok comments: {str(e)}"
        )


@router.get("/video/comments", response_model=dict)
async def get_video_comments(
    video_url: str,
    max_results: int = Query(default=50, ge=1, le=100)
):
    """
    Get comments for a specific TikTok video
    
    Args:
        video_url: Full TikTok video URL
        max_results: Maximum comments to fetch (1-100)
        
    Returns:
        List of comments with author info, text
    """
    service = get_tiktok_analytics_service()
    
    if not video_url or "/video/" not in video_url:
        raise HTTPException(
            status_code=400,
            detail="Invalid TikTok video URL. Expected format: https://www.tiktok.com/@username/video/1234567890"
        )
    
    try:
        comments = await service.get_video_comments(video_url, limit=max_results)
        
        video_id = service._extract_video_id(video_url)
        
        return {
            "success": True,
            "video_url": video_url,
            "video_id": video_id,
            "count": len(comments),
            "comments": [c.model_dump() for c in comments],
        }
    except Exception as e:
        logger.error(f"Error fetching video comments: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch video comments: {str(e)}"
        )


@router.get("/profile/videos", response_model=dict)
async def get_profile_videos(
    username: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=30)
):
    """
    Get recent videos from a TikTok profile
    
    Args:
        username: TikTok username (uses env var if not provided)
        limit: Maximum videos to fetch (1-30)
        
    Returns:
        List of video URLs and IDs
    """
    service = get_tiktok_analytics_service()
    
    if not username and not service.tiktok_username:
        raise HTTPException(
            status_code=400,
            detail="No TikTok username provided and TIKTOK_USERNAME not configured"
        )
    
    try:
        videos = await service.get_profile_videos(username=username, limit=limit)
        
        return {
            "success": True,
            "username": username or service.tiktok_username,
            "count": len(videos),
            "videos": videos,
        }
    except Exception as e:
        logger.error(f"Error fetching profile videos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch profile videos: {str(e)}"
        )
