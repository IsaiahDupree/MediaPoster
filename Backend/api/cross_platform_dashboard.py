"""
Cross-Platform Analytics Dashboard API
========================================
Endpoints matching the PRD spec for the unified analytics dashboard.
"""

from typing import Optional
from fastapi import APIRouter, Query
from loguru import logger

router = APIRouter(prefix="/api/dashboard", tags=["cross-platform-dashboard"])


@router.get("/overview")
async def get_overview(period: str = Query("7d", description="Period: 7d, 14d, 30d, 90d")):
    """Dashboard scorecard: views, engagement, posts published within period."""
    from services.cross_platform_dashboard import CrossPlatformDashboardService

    days = _parse_period(period)
    svc = CrossPlatformDashboardService()
    return await svc.get_overview(period_days=days)


@router.get("/top-posts")
async def get_top_posts(
    period: str = Query("7d"),
    limit: int = Query(10, ge=1, le=50),
    sort_by: str = Query("views", description="views, likes, engagement, comments"),
):
    """Top-performing posts across all platforms within period."""
    from services.cross_platform_dashboard import CrossPlatformDashboardService

    days = _parse_period(period)
    svc = CrossPlatformDashboardService()
    posts = await svc.get_top_posts(period_days=days, limit=limit, sort_by=sort_by)
    return {"posts": posts, "period": period, "sort_by": sort_by}


@router.get("/growth")
async def get_growth_trends(
    platform: Optional[str] = None,
    period: str = Query("30d"),
    granularity: str = Query("day", description="day or week"),
):
    """Time-series growth data: views, likes, posts over time."""
    from services.cross_platform_dashboard import CrossPlatformDashboardService

    days = _parse_period(period)
    svc = CrossPlatformDashboardService()
    return await svc.get_growth_trends(platform=platform, period_days=days, granularity=granularity)


@router.get("/content/{media_id}")
async def get_content_performance(media_id: str):
    """Cross-platform comparison for one piece of content."""
    from services.cross_platform_dashboard import CrossPlatformDashboardService

    svc = CrossPlatformDashboardService()
    return await svc.get_content_performance(media_id=media_id)


@router.get("/content")
async def get_content_leaderboard():
    """All-time content leaderboard across platforms."""
    from services.cross_platform_dashboard import CrossPlatformDashboardService

    svc = CrossPlatformDashboardService()
    return await svc.get_content_performance()


@router.get("/compare")
async def compare_accounts(
    platform: str = Query(..., description="Platform to compare accounts on"),
    period: str = Query("30d"),
):
    """Compare performance between accounts on the same platform."""
    from services.cross_platform_dashboard import CrossPlatformDashboardService

    days = _parse_period(period)
    svc = CrossPlatformDashboardService()
    return await svc.compare_accounts(platform=platform, period_days=days)


@router.get("/heatmap/{platform}")
async def get_posting_heatmap(platform: str, period: str = Query("60d")):
    """Posting times heatmap — ties into Smart Posting Times."""
    from services.smart_posting_times import SmartPostingTimesService

    days = _parse_period(period)
    svc = SmartPostingTimesService()
    return await svc.get_heatmap_data(platform=platform, lookback_days=days)


def _parse_period(period: str) -> int:
    """Parse period string like '7d', '30d', '90d' into days int."""
    try:
        return int(period.rstrip("d"))
    except ValueError:
        return 7
