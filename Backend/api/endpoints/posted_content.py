"""
Posted Content API Endpoints
Tracks content that has been published to social media platforms
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/posted-content", tags=["posted-content"])

# In-memory store for posted content (will be replaced with database)
_posted_content_store: List[dict] = []


class PostedContentItem(BaseModel):
    """A piece of content that has been posted to a platform"""
    id: str
    platform: str
    platform_post_id: str
    platform_url: str
    account_username: str
    local_content_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: List[str] = []
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_rate: float = 0.0
    posted_at: str
    status: str = "published"


class PostRecordRequest(BaseModel):
    """Request to record a new post"""
    media_id: str
    platform: str
    blotato_submission_id: str
    platform_url: str
    blotato_account_id: str
    caption: Optional[str] = None
    status: str = "published"


class PostedContentResponse(BaseModel):
    """Response containing posted content items"""
    items: List[PostedContentItem]
    total: int
    page: int
    limit: int


@router.get("", response_model=PostedContentResponse)
async def get_posted_content(
    limit: int = Query(default=50, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    platform: Optional[str] = None,
    account_username: Optional[str] = None,
):
    """
    Get list of posted content.
    
    This endpoint returns content that has been published to social media platforms.
    """
    # Filter by platform if specified
    filtered = _posted_content_store
    if platform:
        filtered = [p for p in filtered if p.get('platform', '').lower() == platform.lower()]
    if account_username:
        filtered = [p for p in filtered if p.get('account_username', '').lower() == account_username.lower()]
    
    # Paginate
    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    page_items = filtered[start:end]
    
    # Convert to response format
    items = []
    for p in page_items:
        items.append(PostedContentItem(
            id=p.get('id', ''),
            platform=p.get('platform', ''),
            platform_post_id=p.get('blotato_submission_id', ''),
            platform_url=p.get('platform_url', ''),
            account_username=p.get('blotato_account_id', ''),
            local_content_id=p.get('media_id'),
            description=p.get('caption'),
            posted_at=p.get('posted_at', datetime.now().isoformat()),
            status=p.get('status', 'published'),
            views=p.get('views', 0),
            likes=p.get('likes', 0),
            comments=p.get('comments', 0),
            shares=p.get('shares', 0),
        ))
    
    return PostedContentResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/record")
async def record_post(request: PostRecordRequest):
    """
    Record a new post after publishing via Blotato.
    Stores the platform URL for analytics tracking.
    """
    post_record = {
        "id": str(uuid.uuid4()),
        "media_id": request.media_id,
        "platform": request.platform,
        "blotato_submission_id": request.blotato_submission_id,
        "platform_url": request.platform_url,
        "blotato_account_id": request.blotato_account_id,
        "caption": request.caption,
        "status": request.status,
        "posted_at": datetime.now().isoformat(),
        "views": 0,
        "likes": 0,
        "comments": 0,
        "shares": 0,
    }
    
    _posted_content_store.append(post_record)
    logger.info(f"✓ Recorded post: {request.platform} - {request.platform_url}")
    
    return {
        "success": True,
        "id": post_record["id"],
        "platform_url": request.platform_url
    }


@router.get("/by-submission/{submission_id}")
async def get_by_submission_id(submission_id: str):
    """Get post record by Blotato submission ID"""
    for post in _posted_content_store:
        if post.get('blotato_submission_id') == submission_id:
            return post
    raise HTTPException(status_code=404, detail="Post not found")


@router.get("/by-media/{media_id}")
async def get_posts_by_media(media_id: str):
    """Get all posts for a specific media item"""
    posts = [p for p in _posted_content_store if p.get('media_id') == media_id]
    return {"posts": posts, "count": len(posts)}


@router.post("")
async def record_posted_content(item: PostedContentItem):
    """
    Record a new piece of posted content (legacy endpoint).
    
    Called after successfully publishing to a platform via Blotato.
    """
    post_record = item.dict()
    post_record['posted_at'] = item.posted_at
    _posted_content_store.append(post_record)
    logger.info(f"Recording posted content: {item.platform} - {item.platform_post_id}")
    
    return {"success": True, "id": item.id}


# =============================================================================
# ANALYTICS ENDPOINTS - Fetch live metrics from platforms
# =============================================================================

@router.get("/analytics/by-url")
async def get_analytics_by_url(url: str):
    """
    Fetch live analytics for a post by its platform URL.
    
    Supports:
    - TikTok (via RapidAPI)
    - Instagram (coming soon)
    - YouTube (coming soon)
    
    Requires RAPIDAPI_KEY in environment.
    """
    from services.analytics_service import get_external_analytics_fetcher
    
    fetcher = get_external_analytics_fetcher()
    result = await fetcher.fetch_analytics_by_url(url)
    
    return result


@router.get("/analytics/{post_id}")
async def get_analytics_for_post(post_id: str):
    """
    Fetch live analytics for a stored post by its ID.
    Looks up the platform_url and fetches current metrics.
    """
    from services.analytics_service import get_external_analytics_fetcher
    
    # Find the post
    post = None
    for p in _posted_content_store:
        if p.get('id') == post_id:
            post = p
            break
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    platform_url = post.get('platform_url')
    if not platform_url:
        raise HTTPException(status_code=400, detail="Post has no platform URL")
    
    fetcher = get_external_analytics_fetcher()
    result = await fetcher.fetch_analytics_by_url(platform_url)
    
    # Update stored metrics if successful
    if result.get('success') and result.get('metrics'):
        metrics = result['metrics']
        post['views'] = metrics.get('views', post.get('views', 0))
        post['likes'] = metrics.get('likes', post.get('likes', 0))
        post['comments'] = metrics.get('comments', post.get('comments', 0))
        post['shares'] = metrics.get('shares', post.get('shares', 0))
        post['last_analytics_fetch'] = datetime.now().isoformat()
    
    return {
        "post_id": post_id,
        "platform_url": platform_url,
        "analytics": result
    }


@router.post("/analytics/refresh-all")
async def refresh_all_analytics():
    """
    Refresh analytics for all stored posts.
    Rate limited to avoid API throttling.
    """
    import asyncio
    from services.analytics_service import get_external_analytics_fetcher
    
    fetcher = get_external_analytics_fetcher()
    results = []
    
    for post in _posted_content_store:
        platform_url = post.get('platform_url')
        if not platform_url:
            continue
        
        result = await fetcher.fetch_analytics_by_url(platform_url)
        
        if result.get('success') and result.get('metrics'):
            metrics = result['metrics']
            post['views'] = metrics.get('views', post.get('views', 0))
            post['likes'] = metrics.get('likes', post.get('likes', 0))
            post['comments'] = metrics.get('comments', post.get('comments', 0))
            post['shares'] = metrics.get('shares', post.get('shares', 0))
            post['last_analytics_fetch'] = datetime.now().isoformat()
            
            results.append({
                "post_id": post.get('id'),
                "platform": post.get('platform'),
                "success": True,
                "metrics": metrics
            })
        else:
            results.append({
                "post_id": post.get('id'),
                "platform": post.get('platform'),
                "success": False,
                "error": result.get('error')
            })
        
        # Rate limit: 1 request per second
        await asyncio.sleep(1)
    
    return {
        "refreshed": len(results),
        "results": results
    }
