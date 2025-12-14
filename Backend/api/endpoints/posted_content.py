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
