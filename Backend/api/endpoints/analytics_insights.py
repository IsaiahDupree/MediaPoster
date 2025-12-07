"""
FastAPI Endpoints for Analytics & Insights - Phase 5
North Star Metrics, dashboards, and content recommendations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import uuid

from database.connection import get_db
from services.analytics_service import AnalyticsService
from services.insights_engine import InsightsEngine

router = APIRouter()


# ==================== Request/Response Models ====================

class WeeklyMetricsResponse(BaseModel):
    """Weekly North Star Metrics"""
    week_start: date
    engaged_reach: int
    content_leverage_score: float
    warm_lead_flow: int
    total_posts: int
    total_views: int
    avg_retention_pct: float
    platform_breakdown: dict


class DashboardResponse(BaseModel):
    """Overview dashboard data"""
    current_week: dict
    platform_breakdown: dict
    weeks_analyzed: int
    trend_data: List[dict]


class PostPerformanceResponse(BaseModel):
    """Detailed post performance"""
    post: dict
    metrics_timeline: List[dict]
    comments_analysis: dict
    latest_metrics: Optional[dict]


class InsightResponse(BaseModel):
    """Content insight"""
    type: str
    priority: str
    title: str
    description: str
    expected_impact: str
    action: str


class RecommendationsResponse(BaseModel):
    """Content recommendations"""
    recommendations: List[InsightResponse]
    total: int


# ==================== Endpoints ====================

@router.post("/metrics/calculate-weekly")
def calculate_weekly_metrics(
    week_start: date = Query(..., description="Week start date (Monday)"),
    user_id: Optional[str] = Query(None, description="User ID filter"),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate North Star Metrics for a specific week
    
    North Star Metrics:
    - Weekly Engaged Reach
    - Content Leverage Score
    - Warm Lead Flow
    
    Example:
        ```
        POST /api/analytics/metrics/calculate-weekly?week_start=2025-11-18
        ```
    """
    analytics = AnalyticsService(db)
    
    user_uuid = uuid.UUID(user_id) if user_id else None
    
    metrics = analytics.calculate_weekly_metrics(
        week_start=week_start,
        user_id=user_uuid
    )
    
    return metrics


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    weeks: int = Query(4, description="Number of weeks to analyze"),
    user_id: Optional[str] = Query(None, description="User ID filter"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overview dashboard with trends
    
    Returns:
    - Current week North Star Metrics
    - Week-over-week trends
    - Platform breakdown
    - Historical data
    
    Example:
        ```
        GET /api/analytics/dashboard?weeks=8
        ```
    """
    try:
        # For now, return empty dashboard until AnalyticsService is converted to async
        from loguru import logger
        logger.warning("AnalyticsService needs async conversion - returning empty dashboard")
        
        return DashboardResponse(
            current_week={},
            platform_breakdown={},
            weeks_analyzed=weeks,
            trend_data=[]
        )
    except Exception as e:
        from loguru import logger
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/post/{post_id}/performance", response_model=PostPerformanceResponse)
def get_post_performance(
    post_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed performance analysis for a post
    
    Returns:
    - Metrics timeline (checkback data)
    - Comment sentiment analysis
    - Engagement breakdown
    
    Example:
        ```
        GET /api/analytics/post/{post_id}/performance
        ```
    """
    analytics = AnalyticsService(db)
    
    post_uuid = uuid.UUID(post_id)
    
    performance = analytics.get_post_performance_detail(post_uuid)
    
    if "error" in performance:
        raise HTTPException(status_code=404, detail=performance["error"])
    
    return performance


@router.get("/insights/hooks")
def get_hook_insights(
    min_sample_size: int = Query(10, description="Minimum posts needed"),
    lookback_days: int = Query(30, description="Days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get insights about which hook types perform best
    
    Analyzes:
    - Hook type effectiveness
    - Retention by hook type
    - Sample size and confidence
    
    Example:
        ```
        GET /api/analytics/insights/hooks?min_sample_size=5&lookback_days=60
        ```
    """
    insights_engine = InsightsEngine(db)
    
    insights = insights_engine.detect_hook_patterns(
        min_sample_size=min_sample_size,
        lookback_days=lookback_days
    )
    
    return {
        "insights": insights,
        "total": len(insights),
        "lookback_days": lookback_days
    }


@router.get("/insights/posting-times/{platform}")
def get_optimal_posting_times(
    platform: str,
    lookback_days: int = Query(30, description="Days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get optimal posting times for a platform
    
    Analyzes hourly performance to find best posting windows
    
    Example:
        ```
        GET /api/analytics/insights/posting-times/tiktok
        ```
    """
    insights_engine = InsightsEngine(db)
    
    timing = insights_engine.detect_optimal_posting_times(
        platform=platform,
        lookback_days=lookback_days
    )
    
    return timing


@router.get("/insights/topics")
def get_topic_insights(
    lookback_days: int = Query(30, description="Days to analyze"),
    min_sample_size: int = Query(5, description="Minimum posts per topic"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get high-performing content topics
    
    Identifies which topics/themes drive engagement
    
    Example:
        ```
        GET /api/analytics/insights/topics?lookback_days=60
        ```
    """
    insights_engine = InsightsEngine(db)
    
    topics = insights_engine.detect_high_performing_topics(
        lookback_days=lookback_days,
        min_sample_size=min_sample_size
    )
    
    return {
        "topics": topics,
        "total": len(topics),
        "lookback_days": lookback_days
    }


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_content_recommendations(
    user_id: Optional[str] = Query(None, description="User ID filter"),
    limit: int = Query(10, description="Max recommendations"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized content recommendations
    
    Returns actionable recommendations based on:
    - Hook performance
    - Optimal posting times
    - High-performing topics
    - CTA effectiveness
    
    Example:
        ```
        GET /api/analytics/recommendations?limit=5
        ```
    """
    insights_engine = InsightsEngine(db)
    
    user_uuid = uuid.UUID(user_id) if user_id else None
    
    recommendations = insights_engine.generate_content_recommendations(
        user_id=user_uuid,
        limit=limit
    )
    
    return RecommendationsResponse(
        recommendations=[InsightResponse(**r) for r in recommendations],
        total=len(recommendations)
    )


@router.get("/metrics/north-star")
def get_north_star_metrics(
    weeks: int = Query(4, description="Number of weeks for trend"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get North Star Metrics trend over time
    
    Returns historical data for:
    - Weekly Engaged Reach
    - Content Leverage Score  
    - Warm Lead Flow
    
    Example:
        ```
        GET /api/analytics/metrics/north-star?weeks=8
        ```
    """
    analytics = AnalyticsService(db)
    
    dashboard = analytics.get_overview_dashboard(weeks=weeks)
    
    if "trend_data" in dashboard:
        return {
            "trend_data": dashboard["trend_data"],
            "current_week": dashboard["current_week"],
            "weeks_analyzed": dashboard["weeks_analyzed"]
        }
    
    return {"message": "No data available"}


@router.get("/platform-comparison")
def compare_platform_performance(
    lookback_days: int = Query(30, description="Days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare performance across platforms
    
    Shows which platforms drive the most:
    - Reach
    - Engagement
    - Conversions
    
    Example:
        ```
        GET /api/analytics/platform-comparison?lookback_days=60
        ```
    """
    from database.models import PlatformPost, PlatformCheckback
    from sqlalchemy import func
    
    cutoff = datetime.now() - timedelta(days=lookback_days)
    
    # Query platform performance
    platform_stats = db.query(
        PlatformPost.platform,
        func.count(PlatformPost.id).label('total_posts'),
        func.sum(PlatformCheckback.views).label('total_views'),
        func.avg(PlatformCheckback.like_rate).label('avg_like_rate'),
        func.avg(PlatformCheckback.save_rate).label('avg_save_rate')
    ).join(
        PlatformCheckback
    ).filter(
        PlatformPost.published_at >= cutoff
    ).group_by(
        PlatformPost.platform
    ).all()
    
    comparison = [
        {
            "platform": platform,
            "total_posts": int(total_posts),
            "total_views": int(total_views or 0),
            "avg_like_rate": round(float(avg_like_rate or 0) * 100, 2),
            "avg_save_rate": round(float(avg_save_rate or 0) * 100, 2)
        }
        for platform, total_posts, total_views, avg_like_rate, avg_save_rate in platform_stats
    ]
    
    return {
        "comparison": comparison,
        "lookback_days": lookback_days
    }
