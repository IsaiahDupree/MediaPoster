"""
Posted Content API Endpoints
Tracks content that has been published to social media platforms
"""

from fastapi import APIRouter, Query, HTTPException, Depends, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
import logging
import uuid

from database.connection import get_db
from database.models import PostedContent as PostedContentModel
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/posted-content", tags=["posted-content"])


class PostedContentItem(BaseModel):
    """A piece of content that has been posted to a platform"""
    id: str
    platform: str
    platform_post_id: str
    platform_url: Optional[str] = None  # URL may not be available immediately
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
    platform_url: Optional[str] = None  # URL may not be available immediately
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
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of posted content from database.
    """
    try:
        # Build query
        query = select(PostedContentModel)
        
        if platform:
            query = query.where(func.lower(PostedContentModel.platform) == platform.lower())
        if account_username:
            query = query.where(func.lower(PostedContentModel.account_username) == account_username.lower())
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Paginate and order
        query = query.order_by(PostedContentModel.posted_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)
        
        result = await db.execute(query)
        posts = result.scalars().all()
        
        # Convert to response format
        items = []
        for p in posts:
            items.append(PostedContentItem(
                id=str(p.id),
                platform=p.platform,
                platform_post_id=p.platform_post_id or '',
                platform_url=p.platform_url,
                account_username=p.account_username or '',
                local_content_id=str(p.media_id) if p.media_id else None,
                description=p.caption,
                posted_at=p.posted_at.isoformat() if p.posted_at else datetime.now().isoformat(),
                status=p.status or 'published',
                views=p.views or 0,
                likes=p.likes or 0,
                comments=p.comments or 0,
                shares=p.shares or 0,
            ))
        
        return PostedContentResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error fetching posted content: {e}")
        return PostedContentResponse(items=[], total=0, page=page, limit=limit)


@router.post("/record")
async def record_post(request: PostRecordRequest, db: AsyncSession = Depends(get_db)):
    """
    Record a new post after publishing via Blotato.
    Stores the platform URL for analytics tracking in database.
    """
    try:
        new_post = PostedContentModel(
            platform=request.platform,
            platform_post_id=request.blotato_submission_id,
            platform_url=request.platform_url,
            account_id=request.blotato_account_id,
            account_username=request.blotato_account_id,
            media_id=uuid.UUID(request.media_id) if request.media_id else None,
            caption=request.caption,
            status=request.status,
            posted_at=datetime.now(),
        )
        
        db.add(new_post)
        await db.commit()
        await db.refresh(new_post)
        
        logger.info(f"✓ Recorded post to DB: {request.platform} - {request.platform_url}")
        
        # Emit CONTENT_POSTED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.CONTENT_POSTED, {
                "post_id": str(new_post.id),
                "media_id": request.media_id,
                "platform": request.platform,
                "platform_url": request.platform_url,
                "account_id": request.blotato_account_id,
            })
            logger.info(f"[PubSub] Emitted CONTENT_POSTED for {new_post.id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit CONTENT_POSTED: {e}")
        
        return {
            "success": True,
            "id": str(new_post.id),
            "platform_url": request.platform_url
        }
    except Exception as e:
        logger.error(f"Error recording post: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-submission/{submission_id}")
async def get_by_submission_id(submission_id: str, db: AsyncSession = Depends(get_db)):
    """Get post record by Blotato submission ID"""
    try:
        query = select(PostedContentModel).where(PostedContentModel.platform_post_id == submission_id)
        result = await db.execute(query)
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        return {
            "id": str(post.id),
            "platform": post.platform,
            "platform_post_id": post.platform_post_id,
            "platform_url": post.platform_url,
            "media_id": str(post.media_id) if post.media_id else None,
            "caption": post.caption,
            "status": post.status,
            "posted_at": post.posted_at.isoformat() if post.posted_at else None,
            "views": post.views,
            "likes": post.likes,
            "comments": post.comments,
            "shares": post.shares,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching post by submission ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-media/{media_id}")
async def get_posts_by_media(media_id: str, db: AsyncSession = Depends(get_db)):
    """Get all posts for a specific media item"""
    try:
        query = select(PostedContentModel).where(PostedContentModel.media_id == uuid.UUID(media_id))
        result = await db.execute(query)
        posts = result.scalars().all()
        
        return {
            "posts": [
                {
                    "id": str(p.id),
                    "platform": p.platform,
                    "platform_url": p.platform_url,
                    "status": p.status,
                    "posted_at": p.posted_at.isoformat() if p.posted_at else None,
                }
                for p in posts
            ],
            "count": len(posts)
        }
    except Exception as e:
        logger.error(f"Error fetching posts by media ID: {e}")
        return {"posts": [], "count": 0}


@router.patch("/{post_id}")
async def update_post_metrics(
    post_id: str,
    views: Optional[int] = None,
    likes: Optional[int] = None,
    comments: Optional[int] = None,
    shares: Optional[int] = None,
    saves: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update metrics for a specific posted content record"""
    try:
        query = select(PostedContentModel).where(PostedContentModel.id == uuid.UUID(post_id))
        result = await db.execute(query)
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if views is not None:
            post.views = views
        if likes is not None:
            post.likes = likes
        if comments is not None:
            post.comments = comments
        if shares is not None:
            post.shares = shares
        if saves is not None:
            post.saves = saves
        
        await db.commit()
        
        logger.info(f"✓ Updated metrics for {post_id}: views={views}, likes={likes}, comments={comments}")
        return {"success": True, "id": post_id, "views": post.views, "likes": post.likes, "comments": post.comments}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating post metrics: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/by-submission/{submission_id}/url")
async def update_platform_url(submission_id: str, platform_url: str, db: AsyncSession = Depends(get_db)):
    """Update the platform URL for a post after it's been published"""
    try:
        query = select(PostedContentModel).where(PostedContentModel.platform_post_id == submission_id)
        result = await db.execute(query)
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post.platform_url = platform_url
        await db.commit()
        
        logger.info(f"✓ Updated platform URL for {submission_id}: {platform_url}")
        return {"success": True, "platform_url": platform_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating platform URL: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def record_posted_content(item: PostedContentItem, db: AsyncSession = Depends(get_db)):
    """
    Record a new piece of posted content (legacy endpoint).
    
    Called after successfully publishing to a platform via Blotato.
    """
    try:
        new_post = PostedContentModel(
            platform=item.platform,
            platform_post_id=item.platform_post_id,
            platform_url=item.platform_url,
            account_username=item.account_username,
            media_id=uuid.UUID(item.local_content_id) if item.local_content_id else None,
            caption=item.description,
            status=item.status,
            views=item.views,
            likes=item.likes,
            comments=item.comments,
            shares=item.shares,
        )
        db.add(new_post)
        await db.commit()
        await db.refresh(new_post)
        logger.info(f"Recording posted content: {item.platform} - {item.platform_post_id}")
        return {"success": True, "id": str(new_post.id)}
    except Exception as e:
        logger.error(f"Error recording posted content: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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
async def get_analytics_for_post(post_id: str, db: AsyncSession = Depends(get_db)):
    """
    Fetch live analytics for a stored post by its ID.
    Looks up the platform_url and fetches current metrics.
    """
    from services.analytics_service import get_external_analytics_fetcher
    
    # Find the post in database
    query = select(PostedContentModel).where(PostedContentModel.id == uuid.UUID(post_id))
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    platform_url = post.platform_url
    if not platform_url:
        raise HTTPException(status_code=400, detail="Post has no platform URL")
    
    fetcher = get_external_analytics_fetcher()
    analytics_result = await fetcher.fetch_analytics_by_url(platform_url)
    
    # Update stored metrics if successful
    if analytics_result.get('success') and analytics_result.get('metrics'):
        metrics = analytics_result['metrics']
        post.views = metrics.get('views', post.views or 0)
        post.likes = metrics.get('likes', post.likes or 0)
        post.comments = metrics.get('comments', post.comments or 0)
        post.shares = metrics.get('shares', post.shares or 0)
        await db.commit()
    
    return {
        "post_id": post_id,
        "platform_url": platform_url,
        "analytics": analytics_result
    }


@router.post("/analytics/refresh-all")
async def refresh_all_analytics(db: AsyncSession = Depends(get_db)):
    """
    Refresh analytics for all stored posts.
    Rate limited to avoid API throttling.
    """
    import asyncio
    from services.analytics_service import get_external_analytics_fetcher
    
    fetcher = get_external_analytics_fetcher()
    results = []
    
    # Get all posts with platform URLs from database
    query = select(PostedContentModel).where(PostedContentModel.platform_url.isnot(None))
    db_result = await db.execute(query)
    posts = db_result.scalars().all()
    
    for post in posts:
        platform_url = post.platform_url
        if not platform_url:
            continue
        
        result = await fetcher.fetch_analytics_by_url(platform_url)
        
        if result.get('success') and result.get('metrics'):
            metrics = result['metrics']
            post.views = metrics.get('views', post.views or 0)
            post.likes = metrics.get('likes', post.likes or 0)
            post.comments = metrics.get('comments', post.comments or 0)
            post.shares = metrics.get('shares', post.shares or 0)
            
            results.append({
                "post_id": str(post.id),
                "platform": post.platform,
                "success": True,
                "metrics": metrics
            })
        else:
            results.append({
                "post_id": str(post.id),
                "platform": post.platform,
                "success": False,
                "error": result.get('error')
            })
        
        # Rate limit: 1 request per second
        await asyncio.sleep(1)
    
    await db.commit()
    
    return {
        "refreshed": len(results),
        "results": results
    }


# =============================================================================
# API USAGE TRACKING ENDPOINTS
# =============================================================================

@router.get("/api-usage/summary")
async def get_api_usage_summary(provider: Optional[str] = None):
    """
    Get API usage summary for all or specific provider.
    
    Args:
        provider: Optional provider name (e.g., "rapidapi_tiktok")
        
    Returns:
        Usage statistics including calls made, remaining, and recommendations
    """
    from services.api_usage_tracker import get_api_usage_tracker, APIProvider
    
    tracker = get_api_usage_tracker()
    
    if provider:
        try:
            api_provider = APIProvider(provider)
            return tracker.get_usage_summary(api_provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    return tracker.get_usage_summary()


@router.get("/api-usage/can-call")
async def check_can_make_api_call(provider: str = "rapidapi_tiktok"):
    """
    Check if we can make an API call within budget.
    
    Args:
        provider: Provider name (default: "rapidapi_tiktok")
        
    Returns:
        Whether the call is allowed, usage percentage, and remaining calls
    """
    from services.api_usage_tracker import get_api_usage_tracker, APIProvider
    
    tracker = get_api_usage_tracker()
    
    try:
        api_provider = APIProvider(provider)
        return tracker.can_make_call(api_provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


@router.post("/api-usage/set-tier")
async def set_api_tier(provider: str, tier: str):
    """
    Set the pricing tier for a provider.
    
    Args:
        provider: Provider name (e.g., "rapidapi_tiktok")
        tier: Tier name (e.g., "basic", "pro", "ultra", "mega")
        
    Returns:
        Updated budget configuration
    """
    from services.api_usage_tracker import get_api_usage_tracker, APIProvider
    
    tracker = get_api_usage_tracker()
    
    try:
        api_provider = APIProvider(provider)
        tracker.set_tier(api_provider, tier)
        return {
            "success": True,
            "message": f"Set {provider} tier to {tier}",
            "summary": tracker.get_usage_summary(api_provider)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api-usage/endpoints")
async def get_available_endpoints():
    """
    Get available API endpoints and their details for all providers.
    
    Returns:
        Complete configuration for all supported API providers
    """
    from services.api_usage_tracker import ALL_API_PROVIDERS, APIProvider
    
    result = {}
    for provider, config in ALL_API_PROVIDERS.items():
        result[provider.value] = {
            "host": config["host"],
            "display_name": config["display_name"],
            "endpoints": config["endpoints"],
            "tiers": {
                name: {
                    "monthly_limit": tier.monthly_limit,
                    "cost_usd": tier.cost_usd,
                    "overage_cost": tier.overage_cost_per_call,
                    "cost_per_call": tier.cost_per_call
                }
                for name, tier in config["tiers"].items()
            },
            "rate_limits": config["rate_limits"]
        }
    
    return result


@router.get("/by-media/{media_id}/fetch-metrics")
async def fetch_metrics_for_media(media_id: str, db: AsyncSession = Depends(get_db)):
    """
    Fetch and update metrics for all posts of a specific media item.
    Returns aggregated totals across all posts.
    """
    import asyncio
    from services.analytics_service import get_external_analytics_fetcher
    
    try:
        # Get all posts for this media
        query = select(PostedContentModel).where(PostedContentModel.media_id == uuid.UUID(media_id))
        result = await db.execute(query)
        posts = result.scalars().all()
        
        if not posts:
            return {"error": "No posts found for this media", "totals": {"views": 0, "likes": 0, "comments": 0, "shares": 0}}
        
        fetcher = get_external_analytics_fetcher()
        totals = {"views": 0, "likes": 0, "comments": 0, "shares": 0}
        updated_posts = []
        
        for post in posts:
            if not post.platform_url:
                continue
            
            try:
                result = await fetcher.fetch_analytics_by_url(post.platform_url)
                
                if result.get('success') and result.get('metrics'):
                    metrics = result['metrics']
                    post.views = metrics.get('views', post.views or 0)
                    post.likes = metrics.get('likes', post.likes or 0)
                    post.comments = metrics.get('comments', post.comments or 0)
                    post.shares = metrics.get('shares', post.shares or 0)
                    
                    updated_posts.append({
                        "id": str(post.id),
                        "platform": post.platform,
                        "metrics": metrics
                    })
                
                # Rate limit
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"Failed to fetch metrics for post {post.id}: {e}")
            
            # Aggregate totals
            totals["views"] += post.views or 0
            totals["likes"] += post.likes or 0
            totals["comments"] += post.comments or 0
            totals["shares"] += post.shares or 0
        
        await db.commit()
        
        return {
            "media_id": media_id,
            "post_count": len(posts),
            "updated_count": len(updated_posts),
            "totals": totals,
            "posts": updated_posts
        }
    except Exception as e:
        logger.error(f"Error fetching metrics for media {media_id}: {e}")
        return {"error": str(e), "totals": {"views": 0, "likes": 0, "comments": 0, "shares": 0}}


@router.get("/{post_id}/comments")
async def get_post_comments(post_id: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """
    Get comments for a specific post.
    Fetches from RapidAPI based on platform and URL.
    """
    import re
    from services.rapidapi_comments_service import RapidAPICommentsService
    
    # Get post from database
    query = select(PostedContentModel).where(PostedContentModel.id == uuid.UUID(post_id))
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    platform = post.platform.lower()
    platform_url = post.platform_url
    
    if not platform_url:
        return {"comments": [], "count": 0, "error": "No platform URL available"}
    
    comments_service = RapidAPICommentsService()
    comments = []
    
    try:
        if platform == "tiktok":
            # Extract video ID from TikTok URL
            match = re.search(r'/video/(\d+)', platform_url)
            if match:
                video_id = match.group(1)
                comments = await comments_service.fetch_tiktok_comments(video_id, limit)
        elif platform == "instagram":
            # Extract post ID from Instagram URL
            match = re.search(r'/p/([A-Za-z0-9_-]+)', platform_url) or re.search(r'/reel/([A-Za-z0-9_-]+)', platform_url)
            if match:
                post_code = match.group(1)
                comments = await comments_service.fetch_instagram_comments(post_code, limit)
        elif platform == "youtube":
            # Extract video ID from YouTube URL
            match = re.search(r'[?&]v=([A-Za-z0-9_-]+)', platform_url) or re.search(r'youtu\.be/([A-Za-z0-9_-]+)', platform_url)
            if match:
                video_id = match.group(1)
                # Use YouTube API for comments
                from services.youtube_service import YouTubeService
                yt_service = YouTubeService()
                yt_comments = await yt_service.get_video_comments(video_id, max_results=limit)
                comments = yt_comments
        
        # Update comment count in database
        if comments:
            post.comments = len(comments)
            await db.commit()
        
        return {
            "post_id": post_id,
            "platform": platform,
            "comments": comments,
            "count": len(comments)
        }
    except Exception as e:
        logger.error(f"Error fetching comments for post {post_id}: {e}")
        return {"comments": [], "count": 0, "error": str(e)}


@router.get("/api-usage/providers")
async def list_api_providers():
    """
    List all configured API providers with their current status.
    
    Returns:
        List of providers with usage summary including days until reset
    """
    from services.api_usage_tracker import get_api_usage_tracker, ALL_API_PROVIDERS, APIProvider
    from datetime import datetime
    
    tracker = get_api_usage_tracker()
    providers = []
    
    # Calculate days until reset (end of month)
    now = datetime.now()
    next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
    days_until_reset = (next_month - now).days
    
    for provider_enum, config in ALL_API_PROVIDERS.items():
        budget_check = tracker.can_make_call(provider_enum)
        budget = tracker._budgets.get(provider_enum.value)
        current_tier = budget.tier_name if budget and hasattr(budget, 'tier_name') else "basic"
        period_end = budget.period_end if budget and hasattr(budget, 'period_end') else None
        current_usage = budget.current_usage if budget and hasattr(budget, 'current_usage') else 0
        monthly_limit = budget.monthly_limit if budget and hasattr(budget, 'monthly_limit') else 0
        
        providers.append({
            "provider": provider_enum.value,
            "display_name": config["display_name"],
            "host": config["host"],
            "base_url": f"https://{config['host']}",
            "endpoint_count": len(config["endpoints"]),
            "current_tier": current_tier,
            "usage_pct": budget_check.get("usage_pct", 0),
            "current_usage": current_usage,
            "monthly_limit": monthly_limit,
            "remaining_calls": budget_check.get("remaining_calls", 0),
            "can_call": budget_check.get("allowed", True),
            "warning": budget_check.get("warning", False),
            "days_until_reset": days_until_reset,
            "period_end": period_end,
        })
    
    return {"providers": providers, "days_until_reset": days_until_reset}


@router.post("/refresh-all-metrics")
async def refresh_all_metrics(
    background_tasks: BackgroundTasks,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a refresh of metrics for all posted content.
    Fetches latest views/likes/comments from RapidAPI for each post.
    
    Args:
        platform: Optional filter to only refresh specific platform
        
    Returns:
        Status message and count of posts being refreshed
    """
    try:
        # Get all posts with platform URLs
        query = select(PostedContentModel).where(PostedContentModel.platform_url.isnot(None))
        if platform:
            query = query.where(func.lower(PostedContentModel.platform) == platform.lower())
        
        result = await db.execute(query)
        posts = result.scalars().all()
        
        if not posts:
            return {"success": True, "message": "No posts with URLs to refresh", "count": 0}
        
        # Start background task to refresh metrics
        background_tasks.add_task(background_refresh_metrics, [str(p.id) for p in posts])
        
        return {
            "success": True,
            "message": f"Started refreshing metrics for {len(posts)} posts",
            "count": len(posts),
            "platforms": list(set(p.platform for p in posts))
        }
    except Exception as e:
        logger.error(f"Error starting metrics refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def background_refresh_metrics(post_ids: List[str]):
    """Background task to refresh metrics for multiple posts"""
    import asyncio
    from database.connection import async_session_maker
    from services.analytics_service import get_external_analytics_fetcher
    
    fetcher = get_external_analytics_fetcher()
    
    async with async_session_maker() as db:
        for post_id in post_ids:
            try:
                query = select(PostedContentModel).where(PostedContentModel.id == uuid.UUID(post_id))
                result = await db.execute(query)
                post = result.scalar_one_or_none()
                
                if not post or not post.platform_url:
                    continue
                
                # Fetch metrics from external API
                metrics_result = await fetcher.fetch_analytics_by_url(post.platform_url)
                
                if metrics_result.get('success') and metrics_result.get('metrics'):
                    metrics = metrics_result['metrics']
                    post.views = metrics.get('views', post.views or 0)
                    post.likes = metrics.get('likes', post.likes or 0)
                    post.comments = metrics.get('comments', post.comments or 0)
                    post.shares = metrics.get('shares', post.shares or 0)
                    
                    # Calculate engagement rate if we have follower count
                    if metrics.get('follower_count') and metrics.get('follower_count') > 0:
                        engagement = (post.likes + post.comments) / metrics['follower_count'] * 100
                        post.engagement_rate = round(engagement, 2)
                    
                    logger.info(f"Updated metrics for post {post_id}: views={post.views}, likes={post.likes}")
                
                # Rate limit between API calls
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Failed to refresh metrics for post {post_id}: {e}")
                continue
        
        await db.commit()
        logger.info(f"Completed refreshing metrics for {len(post_ids)} posts")
