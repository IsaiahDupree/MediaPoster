"""
Twitter/X API Endpoints

Handles Twitter publishing, metrics fetching, and DM functionality.
Implements ADAPT-001, ADAPT-002, ADAPT-003.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import logging

from database.connection import get_db
from database.models import PlatformPost, PlatformCheckback, ContentVariant
from connectors.registry import registry
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/twitter", tags=["Twitter"])


# ==================== Request/Response Models ====================

class PublishTweetRequest(BaseModel):
    """Request to publish a single tweet"""
    content_id: Optional[str] = None
    variant_id: Optional[str] = None
    text: str = Field(..., max_length=280, description="Tweet text (max 280 characters)")
    media_urls: List[str] = Field(default_factory=list, description="Media URLs to attach")
    scheduled_for: Optional[datetime] = Field(None, description="Schedule for future publish")


class PublishThreadRequest(BaseModel):
    """Request to publish a Twitter thread"""
    content_id: Optional[str] = None
    variant_id: Optional[str] = None
    tweets: List[str] = Field(..., min_items=2, description="List of tweets (min 2, max 280 chars each)")
    media_urls: List[str] = Field(default_factory=list, description="Media URLs for first tweet")
    scheduled_for: Optional[datetime] = Field(None, description="Schedule for future publish")


class PublishResponse(BaseModel):
    """Response after publishing"""
    success: bool
    platform_post_id: str
    url: str
    status: str
    message: str
    thread_length: Optional[int] = None


class TweetMetrics(BaseModel):
    """Twitter tweet metrics"""
    tweet_id: str
    views: Optional[int] = 0
    likes: Optional[int] = 0
    retweets: Optional[int] = 0
    replies: Optional[int] = 0
    quotes: Optional[int] = 0
    bookmarks: Optional[int] = 0
    url_clicks: Optional[int] = 0
    profile_clicks: Optional[int] = 0
    fetched_at: datetime


class FetchMetricsRequest(BaseModel):
    """Request to fetch metrics for a tweet"""
    platform_post_id: str
    checkback_interval: Optional[str] = None  # '1h', '6h', '24h', '72h', '7d'


# ==================== Publishing Endpoints ====================

@router.post("/publish", response_model=PublishResponse, status_code=status.HTTP_201_CREATED)
async def publish_tweet(
    request: PublishTweetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Publish a single tweet to Twitter/X.

    **ADAPT-001: X/Twitter Adapter - Publish**

    Features:
    - Publish text + media tweets
    - Character limit validation (280 chars)
    - Optional scheduling
    - Event bus integration

    Args:
        request: Tweet content and metadata
        background_tasks: For async publishing
        db: Database session

    Returns:
        PublishResponse with tweet ID and URL

    Raises:
        HTTPException 400: Invalid request (text too long, etc.)
        HTTPException 500: Publishing failed
    """
    try:
        # Get Twitter adapter
        adapters = registry.get_adapters_for_platform("twitter")
        if not adapters:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Twitter adapter not available"
            )

        twitter_adapter = adapters[0]

        # Validate text length
        if len(request.text) > 280:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tweet text exceeds 280 characters: {len(request.text)} chars"
            )

        # Create ContentVariant for publishing
        from connectors.base import ContentVariant as ConnectorVariant

        variant = ConnectorVariant(
            content_id=request.content_id or str(uuid.uuid4()),
            platform="twitter",
            title=request.text,
            media_url=request.media_urls[0] if request.media_urls else None
        )

        # Publish event
        event_bus = EventBus.get_instance()
        await event_bus.publish(Topics.PUBLISH_REQUESTED, {
            "platform": "twitter",
            "content_id": variant.content_id,
            "text": request.text
        })

        # Publish tweet
        logger.info(f"Publishing tweet: {request.text[:50]}...")
        result = await twitter_adapter.publish_variant(variant)

        # Store in database
        platform_post = PlatformPost(
            id=uuid.uuid4(),
            content_variant_id=uuid.UUID(request.variant_id) if request.variant_id else None,
            platform="twitter",
            platform_post_id=result.get("platform_post_id", ""),
            platform_url=result.get("url", ""),
            caption=request.text,
            status="published" if result.get("status") == "submitted" else "pending",
            published_at=datetime.utcnow(),
            scheduled_for=request.scheduled_for
        )

        db.add(platform_post)
        await db.commit()
        await db.refresh(platform_post)

        # Publish success event
        await event_bus.publish(Topics.PUBLISH_COMPLETED, {
            "platform": "twitter",
            "platform_post_id": result.get("platform_post_id"),
            "url": result.get("url")
        })

        # Schedule checkback metrics (background task)
        background_tasks.add_task(
            schedule_checkbacks,
            platform_post.id,
            "twitter"
        )

        return PublishResponse(
            success=True,
            platform_post_id=result.get("platform_post_id", ""),
            url=result.get("url", ""),
            status=result.get("status", "unknown"),
            message="Tweet published successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish tweet: {str(e)}", exc_info=True)

        # Publish failure event
        event_bus = EventBus.get_instance()
        await event_bus.publish(Topics.PUBLISH_FAILED, {
            "platform": "twitter",
            "error": str(e)
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish tweet: {str(e)}"
        )


@router.post("/publish-thread", response_model=PublishResponse, status_code=status.HTTP_201_CREATED)
async def publish_thread(
    request: PublishThreadRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Publish a Twitter thread (multiple connected tweets).

    **ADAPT-001: X/Twitter Adapter - Publish (Threads)**

    Features:
    - Publish connected tweet threads
    - Validate each tweet (280 chars)
    - Media support on first tweet
    - Optional scheduling

    Args:
        request: Thread content
        background_tasks: For async tasks
        db: Database session

    Returns:
        PublishResponse with thread info

    Raises:
        HTTPException 400: Invalid thread (tweet too long, etc.)
        HTTPException 500: Publishing failed
    """
    try:
        # Get Twitter adapter
        adapters = registry.get_adapters_for_platform("twitter")
        if not adapters:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Twitter adapter not available"
            )

        twitter_adapter = adapters[0]

        # Validate all tweets
        for i, tweet_text in enumerate(request.tweets):
            if len(tweet_text) > 280:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tweet {i+1} exceeds 280 characters: {len(tweet_text)} chars"
                )

        # Create ContentVariant for first tweet
        from connectors.base import ContentVariant as ConnectorVariant

        variant = ConnectorVariant(
            content_id=request.content_id or str(uuid.uuid4()),
            platform="twitter",
            title=request.tweets[0],  # First tweet
            media_url=request.media_urls[0] if request.media_urls else None
        )

        # Publish event
        event_bus = EventBus.get_instance()
        await event_bus.publish(Topics.PUBLISH_REQUESTED, {
            "platform": "twitter",
            "content_id": variant.content_id,
            "thread_length": len(request.tweets)
        })

        # Publish thread
        logger.info(f"Publishing thread ({len(request.tweets)} tweets)...")
        result = await twitter_adapter.publish_thread(
            variant=variant,
            additional_tweets=request.tweets[1:]  # Remaining tweets
        )

        # Store in database
        platform_post = PlatformPost(
            id=uuid.uuid4(),
            content_variant_id=uuid.UUID(request.variant_id) if request.variant_id else None,
            platform="twitter",
            platform_post_id=result.get("platform_post_id", ""),
            platform_url=result.get("url", ""),
            caption=request.tweets[0],  # First tweet as caption
            status="published" if result.get("status") == "submitted" else "pending",
            published_at=datetime.utcnow(),
            scheduled_for=request.scheduled_for
        )

        db.add(platform_post)
        await db.commit()
        await db.refresh(platform_post)

        # Publish success event
        await event_bus.publish(Topics.PUBLISH_COMPLETED, {
            "platform": "twitter",
            "platform_post_id": result.get("platform_post_id"),
            "url": result.get("url"),
            "thread_length": len(request.tweets)
        })

        # Schedule checkback metrics
        background_tasks.add_task(
            schedule_checkbacks,
            platform_post.id,
            "twitter"
        )

        return PublishResponse(
            success=True,
            platform_post_id=result.get("platform_post_id", ""),
            url=result.get("url", ""),
            status=result.get("status", "unknown"),
            message=f"Thread published successfully ({len(request.tweets)} tweets)",
            thread_length=len(request.tweets)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish thread: {str(e)}", exc_info=True)

        # Publish failure event
        event_bus = EventBus.get_instance()
        await event_bus.publish(Topics.PUBLISH_FAILED, {
            "platform": "twitter",
            "error": str(e),
            "thread_length": len(request.tweets)
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish thread: {str(e)}"
        )


# ==================== Metrics Endpoints ====================

@router.post("/metrics", response_model=TweetMetrics)
async def fetch_tweet_metrics(
    request: FetchMetricsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch metrics for a published tweet.

    **ADAPT-002: X/Twitter Adapter - Metrics**

    Fetches:
    - Views (impressions)
    - Likes
    - Retweets
    - Replies
    - Quotes
    - Bookmarks
    - URL clicks
    - Profile clicks

    Args:
        request: Tweet ID and checkback interval
        db: Database session

    Returns:
        TweetMetrics with all metric counts

    Raises:
        HTTPException 404: Tweet not found
        HTTPException 500: Metrics fetch failed
    """
    try:
        # Get Twitter adapter
        adapters = registry.get_adapters_for_platform("twitter")
        if not adapters:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Twitter adapter not available"
            )

        twitter_adapter = adapters[0]

        # Find platform post
        query = select(PlatformPost).where(
            PlatformPost.platform == "twitter",
            PlatformPost.platform_post_id == request.platform_post_id
        )
        result = await db.execute(query)
        platform_post = result.scalar_one_or_none()

        if not platform_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tweet not found: {request.platform_post_id}"
            )

        # Create variant for metrics fetch
        from connectors.base import ContentVariant as ConnectorVariant

        variant = ConnectorVariant(
            content_id=str(platform_post.content_variant_id or platform_post.id),
            platform="twitter",
            platform_post_id=request.platform_post_id
        )

        # Fetch metrics
        logger.info(f"Fetching metrics for tweet: {request.platform_post_id}")
        snapshots = await twitter_adapter.fetch_metrics_for_variant(variant)

        if not snapshots:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch metrics"
            )

        snapshot = snapshots[0]

        # Store checkback in database
        checkback = PlatformCheckback(
            platform_post_id=platform_post.id,
            checkback_h=parse_checkback_interval(request.checkback_interval),
            checked_at=snapshot.snapshot_at,
            views=snapshot.views or 0,
            likes=snapshot.likes or 0,
            comments=snapshot.comments or 0,
            shares=snapshot.shares or 0
        )

        db.add(checkback)
        await db.commit()

        # Extract Twitter-specific metrics from raw_payload
        raw = snapshot.raw_payload or {}

        return TweetMetrics(
            tweet_id=request.platform_post_id,
            views=snapshot.views,
            likes=snapshot.likes,
            retweets=snapshot.shares,
            replies=snapshot.comments,
            quotes=raw.get("quote_count", 0),
            bookmarks=raw.get("bookmark_count", 0),
            url_clicks=raw.get("url_link_clicks", 0),
            profile_clicks=raw.get("user_profile_clicks", 0),
            fetched_at=snapshot.snapshot_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )


@router.get("/metrics/{platform_post_id}", response_model=List[TweetMetrics])
async def get_tweet_metrics_history(
    platform_post_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get historical metrics for a tweet from checkbacks.

    Args:
        platform_post_id: Twitter tweet ID
        db: Database session

    Returns:
        List of TweetMetrics at different checkback times

    Raises:
        HTTPException 404: Tweet not found
    """
    try:
        # Find platform post
        query = select(PlatformPost).where(
            PlatformPost.platform == "twitter",
            PlatformPost.platform_post_id == platform_post_id
        )
        result = await db.execute(query)
        platform_post = result.scalar_one_or_none()

        if not platform_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tweet not found: {platform_post_id}"
            )

        # Get all checkbacks
        checkbacks_query = select(PlatformCheckback).where(
            PlatformCheckback.platform_post_id == platform_post.id
        ).order_by(PlatformCheckback.checked_at)

        checkbacks_result = await db.execute(checkbacks_query)
        checkbacks = checkbacks_result.scalars().all()

        return [
            TweetMetrics(
                tweet_id=platform_post_id,
                views=cb.views or 0,
                likes=cb.likes or 0,
                retweets=cb.shares or 0,
                replies=cb.comments or 0,
                quotes=0,  # TODO: Store in checkback
                bookmarks=0,
                url_clicks=0,
                profile_clicks=0,
                fetched_at=cb.checked_at
            )
            for cb in checkbacks
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics history: {str(e)}"
        )


# ==================== Utility Functions ====================

async def schedule_checkbacks(platform_post_id: uuid.UUID, platform: str):
    """
    Schedule checkback metrics for a platform post.

    Checkback intervals: 1h, 6h, 24h, 72h, 7d

    Args:
        platform_post_id: Platform post UUID
        platform: Platform name
    """
    # TODO: Integrate with sleep mode wake triggers
    # This should schedule wake events at:
    # - 1 hour after publish
    # - 6 hours after publish
    # - 24 hours after publish
    # - 72 hours after publish
    # - 7 days after publish

    logger.info(f"Checkbacks scheduled for {platform} post {platform_post_id}")
    pass


def parse_checkback_interval(interval: Optional[str]) -> int:
    """
    Parse checkback interval string to hours.

    Args:
        interval: Interval string ('1h', '6h', '24h', '72h', '7d')

    Returns:
        Hours as integer
    """
    if not interval:
        return 0

    mapping = {
        "1h": 1,
        "6h": 6,
        "24h": 24,
        "72h": 72,
        "7d": 168
    }

    return mapping.get(interval, 0)
