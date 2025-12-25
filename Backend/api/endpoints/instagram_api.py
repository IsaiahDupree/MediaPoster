"""
Instagram API Endpoints
TrendTok-style Instagram analytics and trend discovery
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from services.instagram.instagram_service import get_instagram_service
from services.instagram.adapters import SearchType

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ProfileResponse(BaseModel):
    id: str
    username: str
    full_name: str
    bio: str
    followers_count: int
    following_count: int
    media_count: int
    is_verified: bool
    profile_pic_url: str
    provider: str


class MediaItemResponse(BaseModel):
    id: str
    media_type: str
    caption: str
    permalink: str
    thumbnail_url: str
    like_count: int
    comment_count: int
    play_count: Optional[int]
    timestamp: str
    video_url: Optional[str]
    hashtags: List[str]
    mentions: List[str]


class MediaPageResponse(BaseModel):
    items: List[MediaItemResponse]
    cursor: Optional[str]
    has_more: bool


class HashtagResponse(BaseModel):
    tag: str
    media_count: int
    top_posts_count: int
    recent_posts_count: int


class FetchJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/profile/{identifier}")
async def get_profile(identifier: str):
    """
    Fetch Instagram profile information.
    
    Args:
        identifier: Username, user ID, or profile URL
        
    Returns:
        Profile data
    """
    try:
        service = get_instagram_service()
        profile = await service.fetch_and_save_profile(identifier)
        
        return ProfileResponse(
            id=profile.id,
            username=profile.username,
            full_name=profile.full_name,
            bio=profile.bio,
            followers_count=profile.followers_count,
            following_count=profile.following_count,
            media_count=profile.media_count,
            is_verified=profile.is_verified,
            profile_pic_url=profile.profile_pic_url,
            provider=profile.provider
        )
    except Exception as e:
        logger.error(f"Error fetching profile {identifier}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media/{identifier}")
async def get_media(
    identifier: str,
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to fetch")
):
    """
    Fetch media posts from an Instagram profile.
    
    Args:
        identifier: Username, user ID, or profile URL
        cursor: Pagination cursor from previous request
        limit: Max items to fetch (1-100)
        
    Returns:
        Paginated media items
    """
    try:
        service = get_instagram_service()
        media_page = await service.fetch_and_save_media(identifier, cursor, limit)
        
        items = [
            MediaItemResponse(
                id=item.id,
                media_type=item.media_type.value,
                caption=item.caption,
                permalink=item.permalink,
                thumbnail_url=item.thumbnail_url,
                like_count=item.like_count,
                comment_count=item.comment_count,
                play_count=item.play_count,
                timestamp=item.timestamp.isoformat(),
                video_url=item.video_url,
                hashtags=item.hashtags,
                mentions=item.mentions
            )
            for item in media_page.items
        ]
        
        return MediaPageResponse(
            items=items,
            cursor=media_page.cursor,
            has_more=media_page.has_more
        )
    except Exception as e:
        logger.error(f"Error fetching media for {identifier}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reels/{identifier}")
async def get_reels(
    identifier: str,
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Number of reels to fetch")
):
    """
    Fetch reels from an Instagram profile.
    
    Args:
        identifier: Username, user ID, or profile URL
        cursor: Pagination cursor from previous request
        limit: Max reels to fetch (1-100)
        
    Returns:
        Paginated reel items
    """
    try:
        service = get_instagram_service()
        reels_page = await service.fetch_and_save_reels(identifier, cursor, limit)
        
        items = [
            MediaItemResponse(
                id=item.id,
                media_type=item.media_type.value,
                caption=item.caption,
                permalink=item.permalink,
                thumbnail_url=item.thumbnail_url,
                like_count=item.like_count,
                comment_count=item.comment_count,
                play_count=item.play_count,
                timestamp=item.timestamp.isoformat(),
                video_url=item.video_url,
                hashtags=item.hashtags,
                mentions=item.mentions
            )
            for item in reels_page.items
        ]
        
        return MediaPageResponse(
            items=items,
            cursor=reels_page.cursor,
            has_more=reels_page.has_more
        )
    except Exception as e:
        logger.error(f"Error fetching reels for {identifier}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hashtag/{tag}")
async def get_hashtag(tag: str):
    """
    Fetch hashtag information and top posts.
    
    Args:
        tag: Hashtag (with or without #)
        
    Returns:
        Hashtag data with top posts
    """
    try:
        service = get_instagram_service()
        hashtag_data = await service.fetch_and_save_hashtag(tag)
        
        return HashtagResponse(
            tag=hashtag_data.tag,
            media_count=hashtag_data.media_count,
            top_posts_count=len(hashtag_data.top_posts),
            recent_posts_count=len(hashtag_data.recent_posts)
        )
    except Exception as e:
        logger.error(f"Error fetching hashtag {tag}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search(
    query: str = Query(..., description="Search query"),
    type: str = Query("accounts", description="Search type: accounts, hashtags, places")
):
    """
    Search for Instagram accounts, hashtags, or places.
    
    Args:
        query: Search query
        type: Type of search (accounts, hashtags, places)
        
    Returns:
        Search results
    """
    try:
        service = get_instagram_service()
        
        # Map string to enum
        search_type = SearchType.ACCOUNTS
        if type == "hashtags":
            search_type = SearchType.HASHTAGS
        elif type == "places":
            search_type = SearchType.PLACES
        
        results = await service.adapter.search(query, search_type)
        
        return {
            "accounts": [
                {
                    "id": acc.id,
                    "username": acc.username,
                    "full_name": acc.full_name,
                    "followers_count": acc.followers_count,
                    "is_verified": acc.is_verified,
                    "profile_pic_url": acc.profile_pic_url
                }
                for acc in results.accounts
            ],
            "hashtags": results.hashtags,
            "cursor": results.cursor,
            "has_more": results.has_more
        }
    except Exception as e:
        logger.error(f"Error searching {query}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Check if Instagram service is healthy.
    
    Returns:
        Health status
    """
    try:
        service = get_instagram_service()
        is_healthy = await service.adapter.is_healthy()
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "provider": service.adapter.name,
            "provider_type": service.adapter.type
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.post("/fetch/batch")
async def fetch_batch(
    background_tasks: BackgroundTasks,
    usernames: List[str] = Query(..., description="List of usernames to fetch")
):
    """
    Fetch multiple profiles and their media in the background.
    
    Args:
        usernames: List of Instagram usernames
        
    Returns:
        Job ID for tracking
    """
    import uuid
    job_id = str(uuid.uuid4())
    
    async def fetch_all():
        service = get_instagram_service()
        for username in usernames:
            try:
                await service.fetch_and_save_profile(username)
                await service.fetch_and_save_reels(username, limit=20)
                logger.info(f"Batch fetch completed for {username}")
            except Exception as e:
                logger.error(f"Batch fetch failed for {username}: {e}")
    
    background_tasks.add_task(fetch_all)
    
    return FetchJobResponse(
        job_id=job_id,
        status="started",
        message=f"Fetching data for {len(usernames)} accounts"
    )
