"""
YouTube Analytics API Endpoints
Fetch YouTube channel and video metrics using YouTube Data API v3
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging

from services.youtube_analytics_service import (
    get_youtube_analytics_service,
    YouTubeVideoMetrics,
    YouTubeChannelMetrics,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["YouTube Analytics"])


@router.get("/channel", response_model=dict)
async def get_channel_metrics(channel_id: Optional[str] = None):
    """
    Get YouTube channel metrics
    
    Uses YOUTUBE_CHANNEL_ID from environment if channel_id not provided.
    
    Returns:
        Channel info including subscribers, views, video count
    """
    service = get_youtube_analytics_service()
    metrics = await service.get_channel_metrics(channel_id)
    
    if not metrics:
        raise HTTPException(
            status_code=404, 
            detail="Channel not found or YOUTUBE_API_KEY not configured"
        )
    
    return {
        "success": True,
        "channel": metrics.model_dump(),
        "message": f"Fetched metrics for {metrics.title}"
    }


@router.get("/video/{video_id}", response_model=dict)
async def get_video_metrics(video_id: str):
    """
    Get metrics for a specific YouTube video
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        
    Returns:
        Video metrics including views, likes, comments
    """
    service = get_youtube_analytics_service()
    metrics = await service.get_video_metrics(video_id)
    
    if not metrics:
        raise HTTPException(
            status_code=404,
            detail="Video not found or YOUTUBE_API_KEY not configured"
        )
    
    return {
        "success": True,
        "video": metrics.model_dump(),
    }


@router.get("/videos", response_model=dict)
async def get_channel_videos(
    channel_id: Optional[str] = None,
    max_results: int = Query(default=50, ge=1, le=50),
    order: str = Query(default="date", regex="^(date|viewCount|rating)$")
):
    """
    Get all videos from a YouTube channel with their metrics
    
    Args:
        channel_id: YouTube channel ID (uses env var if not provided)
        max_results: Maximum videos to fetch (1-50)
        order: Sort order - 'date', 'viewCount', 'rating'
        
    Returns:
        List of videos with metrics
        
    Note: This endpoint uses 101 API units (100 for search + 1 for videos)
    """
    service = get_youtube_analytics_service()
    videos = await service.get_channel_videos(channel_id, max_results, order)
    
    # Calculate summary stats
    total_views = sum(v.view_count for v in videos)
    total_likes = sum(v.like_count for v in videos)
    total_comments = sum(v.comment_count for v in videos)
    
    return {
        "success": True,
        "count": len(videos),
        "videos": [v.model_dump() for v in videos],
        "summary": {
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "avg_views": total_views // len(videos) if videos else 0,
        }
    }


@router.get("/summary", response_model=dict)
async def get_youtube_summary(channel_id: Optional[str] = None):
    """
    Get complete YouTube analytics summary
    
    Fetches channel info and all videos with aggregated stats.
    
    Returns:
        Complete summary with channel, videos, and aggregated metrics
    """
    service = get_youtube_analytics_service()
    summary = await service.get_all_metrics_summary(channel_id)
    
    if not summary.get("channel"):
        raise HTTPException(
            status_code=404,
            detail="Channel not found or YOUTUBE_API_KEY not configured"
        )
    
    return {
        "success": True,
        **summary
    }


@router.post("/refresh-posted-content", response_model=dict)
async def refresh_youtube_posted_content():
    """
    Refresh YouTube metrics for all posted content with YouTube URLs
    
    Finds all posted content with YouTube URLs and updates their metrics.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from database.connection import get_db
    from database.models import PostedContent as PostedContentModel
    
    service = get_youtube_analytics_service()
    
    # This would need proper DB session injection
    # For now, return info about what would be updated
    return {
        "success": True,
        "message": "Use /api/posted-content/refresh-analytics endpoint to refresh all posted content metrics",
        "youtube_api_configured": bool(service.api_key),
        "channel_id_configured": bool(service.channel_id),
    }


@router.get("/status", response_model=dict)
async def get_youtube_api_status():
    """
    Check YouTube API configuration status
    
    Returns:
        API key status and channel ID configuration
    """
    service = get_youtube_analytics_service()
    
    status = {
        "api_key_configured": bool(service.api_key),
        "channel_id_configured": bool(service.channel_id),
        "channel_id": service.channel_id[:10] + "..." if service.channel_id else None,
    }
    
    # Try to fetch channel to verify API key works
    if service.api_key and service.channel_id:
        channel = await service.get_channel_metrics()
        if channel:
            status["channel_verified"] = True
            status["channel_name"] = channel.title
            status["subscriber_count"] = channel.subscriber_count
            status["video_count"] = channel.video_count
        else:
            status["channel_verified"] = False
            status["error"] = "Could not verify channel - check API key and channel ID"
    
    return status
