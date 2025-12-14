"""
RapidAPI Comments API Endpoints
Fetch comments from TikTok, Instagram, Threads, Facebook via RapidAPI
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from services.rapidapi_comments_service import get_rapidapi_comments_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["RapidAPI Comments"])


@router.get("/status", response_model=dict)
async def get_status():
    """
    Check RapidAPI comments configuration status
    """
    service = get_rapidapi_comments_service()
    return service.get_status()


@router.get("/tiktok", response_model=dict)
async def get_tiktok_comments(
    video_url: Optional[str] = None,
    video_id: Optional[str] = None,
    count: int = Query(default=50, ge=1, le=100)
):
    """
    Fetch comments from a TikTok video via RapidAPI
    """
    service = get_rapidapi_comments_service()
    
    if not video_url and not video_id:
        raise HTTPException(status_code=400, detail="Either video_url or video_id required")
    
    comments = await service.fetch_tiktok_comments(video_url=video_url, video_id=video_id, count=count)
    
    return {
        "success": True,
        "platform": "tiktok",
        "count": len(comments),
        "comments": [c.model_dump() for c in comments],
    }


@router.get("/tiktok/all", response_model=dict)
async def get_all_tiktok_comments(
    username: Optional[str] = None,
    max_posts: int = Query(default=5, ge=1, le=20),
    max_comments_per_post: int = Query(default=30, ge=1, le=100)
):
    """
    Fetch comments for all recent TikTok videos from a user
    """
    service = get_rapidapi_comments_service()
    result = await service.fetch_all_comments_for_platform(
        platform="tiktok",
        username=username,
        max_posts=max_posts,
        max_comments_per_post=max_comments_per_post
    )
    
    return {"success": True, **result}


@router.get("/instagram", response_model=dict)
async def get_instagram_comments(
    post_url: Optional[str] = None,
    post_id: Optional[str] = None,
    count: int = Query(default=50, ge=1, le=100)
):
    """
    Fetch comments from an Instagram post via RapidAPI
    """
    service = get_rapidapi_comments_service()
    
    if not post_url and not post_id:
        raise HTTPException(status_code=400, detail="Either post_url or post_id required")
    
    comments = await service.fetch_instagram_comments(post_url=post_url, post_id=post_id, count=count)
    
    return {
        "success": True,
        "platform": "instagram",
        "count": len(comments),
        "comments": [c.model_dump() for c in comments],
    }


@router.get("/instagram/all", response_model=dict)
async def get_all_instagram_comments(
    username: Optional[str] = None,
    max_posts: int = Query(default=5, ge=1, le=20),
    max_comments_per_post: int = Query(default=30, ge=1, le=100)
):
    """
    Fetch comments for all recent Instagram posts from a user
    """
    service = get_rapidapi_comments_service()
    result = await service.fetch_all_comments_for_platform(
        platform="instagram",
        username=username,
        max_posts=max_posts,
        max_comments_per_post=max_comments_per_post
    )
    
    return {"success": True, **result}


@router.get("/threads", response_model=dict)
async def get_threads_comments(
    post_id: str,
    count: int = Query(default=50, ge=1, le=100)
):
    """
    Fetch replies from a Threads post via RapidAPI
    """
    service = get_rapidapi_comments_service()
    comments = await service.fetch_threads_comments(post_id=post_id, count=count)
    
    return {
        "success": True,
        "platform": "threads",
        "count": len(comments),
        "comments": [c.model_dump() for c in comments],
    }


@router.get("/threads/all", response_model=dict)
async def get_all_threads_comments(
    username: Optional[str] = None,
    max_posts: int = Query(default=5, ge=1, le=20),
    max_comments_per_post: int = Query(default=30, ge=1, le=100)
):
    """
    Fetch comments for all recent Threads posts from a user
    """
    service = get_rapidapi_comments_service()
    result = await service.fetch_all_comments_for_platform(
        platform="threads",
        username=username,
        max_posts=max_posts,
        max_comments_per_post=max_comments_per_post
    )
    
    return {"success": True, **result}


@router.get("/facebook", response_model=dict)
async def get_facebook_comments(
    post_id: str,
    count: int = Query(default=50, ge=1, le=100)
):
    """
    Fetch comments from a Facebook post via RapidAPI
    """
    service = get_rapidapi_comments_service()
    comments = await service.fetch_facebook_comments(post_id=post_id, count=count)
    
    return {
        "success": True,
        "platform": "facebook",
        "count": len(comments),
        "comments": [c.model_dump() for c in comments],
    }


@router.get("/facebook/all", response_model=dict)
async def get_all_facebook_comments(
    page_id: Optional[str] = None,
    max_posts: int = Query(default=5, ge=1, le=20),
    max_comments_per_post: int = Query(default=30, ge=1, le=100)
):
    """
    Fetch comments for all recent Facebook posts from a page
    """
    service = get_rapidapi_comments_service()
    result = await service.fetch_all_comments_for_platform(
        platform="facebook",
        username=page_id,
        max_posts=max_posts,
        max_comments_per_post=max_comments_per_post
    )
    
    return {"success": True, **result}
