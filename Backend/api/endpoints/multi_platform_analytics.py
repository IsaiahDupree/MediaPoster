"""
Multi-Platform Analytics API (ANALYTICS-001)
==============================================
API endpoints for unified cross-platform analytics

Endpoints:
- GET /api/analytics/unified - Get unified metrics across all platforms
- GET /api/analytics/platform/{platform} - Get metrics for specific platform
- GET /api/analytics/compare - Compare performance across platforms
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from loguru import logger

from services.multi_platform_analytics_aggregator import (
    get_multi_platform_analytics_aggregator,
    UnifiedMetrics,
    PlatformMetrics,
    CrossPlatformComparison
)


router = APIRouter(prefix="/api/analytics", tags=["Multi-Platform Analytics"])


# Response Models

class UnifiedMetricsResponse(BaseModel):
    """Response for unified metrics"""
    total_views: int
    total_impressions: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_saves: int
    total_clicks: int
    total_followers: int
    follower_growth: int
    avg_engagement_rate: float
    avg_watch_time_seconds: float
    avg_completion_rate: float
    total_posts: int
    posts_last_7d: int
    posts_last_30d: int
    best_platform: Optional[str]
    best_platform_engagement_rate: float
    top_post_id: Optional[str]
    top_post_views: int
    last_updated: str
    data_freshness_minutes: int


class PlatformMetricsResponse(BaseModel):
    """Response for platform-specific metrics"""
    platform: str
    account_id: str
    account_username: str
    views: int
    impressions: int
    likes: int
    comments: int
    shares: int
    saves: int
    clicks: int
    followers: int
    follower_growth_7d: int
    follower_growth_30d: int
    engagement_rate: float
    avg_watch_time_seconds: float
    completion_rate: float
    total_posts: int
    posts_last_7d: int
    posts_last_30d: int
    last_updated: str
    errors: list[str]


# API Endpoints

@router.get("/unified", response_model=UnifiedMetricsResponse)
async def get_unified_metrics(
    time_range_days: int = Query(30, description="Number of days to include", ge=1, le=365),
    force_refresh: bool = Query(False, description="Skip cache and fetch fresh data")
):
    """
    Get unified analytics metrics across all platforms

    Aggregates data from Instagram, TikTok, YouTube, Twitter, and other
    connected platforms into a single unified view.

    **Example Response:**
    ```json
    {
        "total_views": 85000,
        "total_likes": 3300,
        "total_comments": 300,
        "total_followers": 30000,
        "avg_engagement_rate": 0.0567,
        "best_platform": "tiktok",
        "best_platform_engagement_rate": 0.065,
        "posts_last_7d": 9,
        "posts_last_30d": 39
    }
    ```

    **Parameters:**
    - `time_range_days`: Number of days to include (default: 30)
    - `force_refresh`: Skip cache and fetch fresh data (default: false)
    """
    try:
        aggregator = get_multi_platform_analytics_aggregator()

        unified = await aggregator.get_unified_metrics(
            time_range_days=time_range_days,
            force_refresh=force_refresh
        )

        return UnifiedMetricsResponse(
            total_views=unified.total_views,
            total_impressions=unified.total_impressions,
            total_likes=unified.total_likes,
            total_comments=unified.total_comments,
            total_shares=unified.total_shares,
            total_saves=unified.total_saves,
            total_clicks=unified.total_clicks,
            total_followers=unified.total_followers,
            follower_growth=unified.follower_growth,
            avg_engagement_rate=unified.avg_engagement_rate,
            avg_watch_time_seconds=unified.avg_watch_time_seconds,
            avg_completion_rate=unified.avg_completion_rate,
            total_posts=unified.total_posts,
            posts_last_7d=unified.posts_last_7d,
            posts_last_30d=unified.posts_last_30d,
            best_platform=unified.best_platform,
            best_platform_engagement_rate=unified.best_platform_engagement_rate,
            top_post_id=unified.top_post_id,
            top_post_views=unified.top_post_views,
            last_updated=unified.last_updated.isoformat(),
            data_freshness_minutes=unified.data_freshness_minutes
        )

    except Exception as e:
        logger.error(f"Error getting unified metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/{platform}", response_model=PlatformMetricsResponse)
async def get_platform_metrics(
    platform: str,
    account_id: Optional[str] = Query(None, description="Specific account ID"),
    time_range_days: int = Query(30, description="Number of days to include", ge=1, le=365)
):
    """
    Get analytics metrics for a specific platform

    Returns detailed metrics for Instagram, TikTok, YouTube, or Twitter.

    **Supported Platforms:**
    - `instagram`
    - `tiktok`
    - `youtube`
    - `twitter`
    - `threads`

    **Example Response:**
    ```json
    {
        "platform": "tiktok",
        "account_id": "tiktok_default",
        "account_username": "@username",
        "views": 50000,
        "likes": 2000,
        "comments": 150,
        "followers": 10000,
        "engagement_rate": 0.049,
        "posts_last_7d": 5,
        "posts_last_30d": 20
    }
    ```
    """
    try:
        aggregator = get_multi_platform_analytics_aggregator()

        metrics = await aggregator.get_platform_metrics(
            platform=platform,
            account_id=account_id,
            time_range_days=time_range_days
        )

        if not metrics:
            raise HTTPException(
                status_code=404,
                detail=f"Platform '{platform}' not found or not supported"
            )

        return PlatformMetricsResponse(**metrics.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting platform metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare")
async def compare_platforms(
    time_range_days: int = Query(30, description="Number of days to include", ge=1, le=365)
):
    """
    Compare performance across all platforms

    Provides platform rankings, best performers, and actionable recommendations
    for optimizing cross-platform content strategy.

    **Example Response:**
    ```json
    {
        "platform_rankings": [
            {
                "platform": "tiktok",
                "views": 50000,
                "engagement_rate": 0.065,
                "followers": 10000,
                "rank_by_engagement": 1,
                "rank_by_views": 1
            },
            {
                "platform": "instagram",
                "views": 10000,
                "engagement_rate": 0.049,
                "followers": 5000,
                "rank_by_engagement": 2,
                "rank_by_views": 2
            }
        ],
        "best_platform_for_views": "tiktok",
        "best_platform_for_engagement": "tiktok",
        "most_consistent_platform": "instagram",
        "recommendations": [
            "TikTok has the highest engagement rate (6.5%). Consider posting more frequently there.",
            "Instagram is underperforming (engagement: 4.9%). Consider A/B testing different content formats."
        ]
    }
    ```
    """
    try:
        aggregator = get_multi_platform_analytics_aggregator()

        comparison = await aggregator.compare_platforms(
            time_range_days=time_range_days
        )

        return {
            "platform_rankings": comparison.platform_rankings,
            "best_platform_for_views": comparison.best_platform_for_views,
            "best_platform_for_engagement": comparison.best_platform_for_engagement,
            "most_consistent_platform": comparison.most_consistent_platform,
            "recommendations": comparison.recommendations
        }

    except Exception as e:
        logger.error(f"Error comparing platforms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check for multi-platform analytics service

    Returns the status of all platform integrations.
    """
    try:
        aggregator = get_multi_platform_analytics_aggregator()

        return {
            "success": True,
            "service": "multi-platform-analytics",
            "platforms_supported": ["instagram", "tiktok", "youtube", "twitter", "threads"],
            "cache_ttl_seconds": aggregator._cache_ttl
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
