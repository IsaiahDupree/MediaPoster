"""
Channel Analyzer API Endpoints (TubeLab-style)
===============================================
Provides YouTube channel analytics with:
- Revenue/RPM estimates
- Insight pills (high demand, loyal viewers, etc.)
- Niche detection
- Discover/search functionality
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from loguru import logger

from services.trend_intelligence.channel_analyzer import (
    YouTubeChannelAnalyzer,
    ChannelMetrics,
    InsightType
)

router = APIRouter(prefix="/api/v1/channels", tags=["Channel Analyzer"])


# =========================================================================
# Request/Response Models
# =========================================================================

class ChannelAnalyzeRequest(BaseModel):
    channel_id: str
    videos_to_analyze: int = 30


class ChannelBatchRequest(BaseModel):
    channel_ids: List[str]
    videos_per_channel: int = 20


class DiscoverRequest(BaseModel):
    query: str
    max_results: int = 20
    min_subscribers: Optional[int] = None
    max_subscribers: Optional[int] = None
    min_views_sub: Optional[float] = None
    content_type: Optional[str] = None  # "long_form", "shorts", "mixed"


class InsightResponse(BaseModel):
    type: str
    label: str
    tooltip: str
    score: float
    confidence: float


class VideoResponse(BaseModel):
    video_id: str
    title: str
    published_at: str
    views: int
    likes: int
    comments: int
    duration_seconds: int
    thumbnail_url: str
    like_rate: float
    comment_rate: float


class ChannelResponse(BaseModel):
    channel_id: str
    title: str
    handle: str
    description: str
    country: str
    language: str
    subscribers: int
    total_views: int
    total_videos: int
    thumbnail_url: str
    
    # TubeLab-style metrics
    typical_views: int
    views_sub_multiplier: float
    velocity_7d: float
    velocity_30d: float
    active_days: int
    uploads_30d: int
    views_30d: int
    
    # Revenue
    rpm_estimate: float
    revenue_30d_estimate: float
    monetization_likelihood: float
    
    # Engagement
    avg_like_rate: float
    avg_comment_rate: float
    avg_engagement_rate: float
    avg_duration_seconds: int
    content_type: str
    upload_consistency: float
    
    # Niche
    niche_tags: List[str]
    
    # Insights
    insights: List[InsightResponse]
    
    # Videos
    recent_videos: List[VideoResponse]
    top_videos: List[VideoResponse]


class DiscoverResponse(BaseModel):
    query: str
    total_results: int
    channels: List[ChannelResponse]


# =========================================================================
# Helper Functions
# =========================================================================

def metrics_to_response(metrics: ChannelMetrics) -> ChannelResponse:
    """Convert ChannelMetrics to API response"""
    return ChannelResponse(
        channel_id=metrics.channel_id,
        title=metrics.title,
        handle=metrics.handle,
        description=metrics.description[:500] if metrics.description else "",
        country=metrics.country,
        language=metrics.language,
        subscribers=metrics.subscribers,
        total_views=metrics.total_views,
        total_videos=metrics.total_videos,
        thumbnail_url=metrics.thumbnail_url,
        typical_views=metrics.typical_views,
        views_sub_multiplier=metrics.views_sub_multiplier,
        velocity_7d=metrics.velocity_7d,
        velocity_30d=metrics.velocity_30d,
        active_days=metrics.active_days,
        uploads_30d=metrics.uploads_30d,
        views_30d=metrics.views_30d,
        rpm_estimate=metrics.rpm_estimate,
        revenue_30d_estimate=metrics.revenue_30d_estimate,
        monetization_likelihood=metrics.monetization_likelihood,
        avg_like_rate=metrics.avg_like_rate,
        avg_comment_rate=metrics.avg_comment_rate,
        avg_engagement_rate=metrics.avg_engagement_rate,
        avg_duration_seconds=metrics.avg_duration_seconds,
        content_type=metrics.content_type,
        upload_consistency=metrics.upload_consistency,
        niche_tags=metrics.niche_tags,
        insights=[
            InsightResponse(
                type=i.type.value if hasattr(i.type, 'value') else str(i.type),
                label=i.label,
                tooltip=i.tooltip,
                score=i.score,
                confidence=i.confidence
            )
            for i in metrics.insights
        ],
        recent_videos=[
            VideoResponse(
                video_id=v.video_id,
                title=v.title,
                published_at=v.published_at.isoformat() if v.published_at else "",
                views=v.views,
                likes=v.likes,
                comments=v.comments,
                duration_seconds=v.duration_seconds,
                thumbnail_url=v.thumbnail_url,
                like_rate=v.like_rate,
                comment_rate=v.comment_rate
            )
            for v in metrics.recent_videos
        ],
        top_videos=[
            VideoResponse(
                video_id=v.video_id,
                title=v.title,
                published_at=v.published_at.isoformat() if v.published_at else "",
                views=v.views,
                likes=v.likes,
                comments=v.comments,
                duration_seconds=v.duration_seconds,
                thumbnail_url=v.thumbnail_url,
                like_rate=v.like_rate,
                comment_rate=v.comment_rate
            )
            for v in metrics.top_videos
        ]
    )


# =========================================================================
# Endpoints
# =========================================================================

@router.post("/analyze", response_model=ChannelResponse)
async def analyze_channel(request: ChannelAnalyzeRequest):
    """
    Analyze a single YouTube channel with TubeLab-style metrics.
    
    Returns:
    - Core stats (subs, views, uploads)
    - Computed metrics (typical_views, velocity, rpm_estimate)
    - Insight pills (high demand, loyal viewers, etc.)
    - Recent/top videos
    """
    analyzer = YouTubeChannelAnalyzer()
    
    try:
        metrics = await analyzer.analyze_channel(
            request.channel_id,
            videos_to_analyze=request.videos_to_analyze
        )
        
        if not metrics:
            raise HTTPException(
                status_code=404,
                detail=f"Channel not found: {request.channel_id}"
            )
        
        return metrics_to_response(metrics)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await analyzer.close()


@router.get("/analyze/{channel_id}", response_model=ChannelResponse)
async def analyze_channel_get(
    channel_id: str,
    videos: int = Query(30, ge=5, le=100, description="Number of videos to analyze")
):
    """GET endpoint for channel analysis"""
    analyzer = YouTubeChannelAnalyzer()
    
    try:
        metrics = await analyzer.analyze_channel(channel_id, videos_to_analyze=videos)
        
        if not metrics:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        return metrics_to_response(metrics)
    finally:
        await analyzer.close()


@router.post("/batch", response_model=List[ChannelResponse])
async def analyze_channels_batch(request: ChannelBatchRequest):
    """Analyze multiple channels in batch"""
    if len(request.channel_ids) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 channels per batch"
        )
    
    analyzer = YouTubeChannelAnalyzer()
    
    try:
        results = await analyzer.analyze_channels_batch(
            request.channel_ids,
            videos_per_channel=request.videos_per_channel
        )
        
        return [metrics_to_response(m) for m in results]
    finally:
        await analyzer.close()


@router.post("/discover", response_model=DiscoverResponse)
async def discover_channels(request: DiscoverRequest):
    """
    Discover channels by niche/keyword (TubeLab Niche Finder style).
    
    Searches for channels matching the query and returns analyzed results
    with metrics, insights, and filtering options.
    """
    analyzer = YouTubeChannelAnalyzer()
    
    try:
        channels = await analyzer.discover_channels_by_niche(
            request.query,
            max_results=request.max_results
        )
        
        # Apply filters
        filtered = channels
        
        if request.min_subscribers:
            filtered = [c for c in filtered if c.subscribers >= request.min_subscribers]
        
        if request.max_subscribers:
            filtered = [c for c in filtered if c.subscribers <= request.max_subscribers]
        
        if request.min_views_sub:
            filtered = [c for c in filtered if c.views_sub_multiplier >= request.min_views_sub]
        
        if request.content_type:
            filtered = [c for c in filtered if c.content_type == request.content_type]
        
        return DiscoverResponse(
            query=request.query,
            total_results=len(filtered),
            channels=[metrics_to_response(c) for c in filtered]
        )
    finally:
        await analyzer.close()


@router.get("/discover/{query}", response_model=DiscoverResponse)
async def discover_channels_get(
    query: str,
    max_results: int = Query(20, ge=1, le=50),
    min_subs: Optional[int] = Query(None, description="Minimum subscribers"),
    max_subs: Optional[int] = Query(None, description="Maximum subscribers"),
    min_views_sub: Optional[float] = Query(None, description="Minimum views/sub multiplier"),
    content_type: Optional[str] = Query(None, description="long_form, shorts, or mixed")
):
    """GET endpoint for channel discovery"""
    request = DiscoverRequest(
        query=query,
        max_results=max_results,
        min_subscribers=min_subs,
        max_subscribers=max_subs,
        min_views_sub=min_views_sub,
        content_type=content_type
    )
    return await discover_channels(request)


@router.get("/insights/types")
async def get_insight_types():
    """Get available insight types and their descriptions"""
    return {
        "insights": [
            {
                "type": InsightType.HIGH_DEMAND.value,
                "label": "High Demand",
                "description": "Views significantly exceed subscriber count"
            },
            {
                "type": InsightType.LOYAL_VIEWERS.value,
                "label": "Loyal Viewers",
                "description": "Strong returning audience relative to subscriber base"
            },
            {
                "type": InsightType.HIGH_COMMITMENT.value,
                "label": "High Commitment",
                "description": "Long-form content with high comment engagement"
            },
            {
                "type": InsightType.HIGH_QUALITY.value,
                "label": "High Quality",
                "description": "High engagement rates and consistent uploads"
            },
            {
                "type": InsightType.FACELESS.value,
                "label": "Faceless",
                "description": "Content without on-camera presence"
            },
            {
                "type": InsightType.CASH_COW.value,
                "label": "Cash Cow",
                "description": "High estimated revenue potential"
            },
            {
                "type": InsightType.BREAKOUT.value,
                "label": "Breakout",
                "description": "Has viral videos significantly above typical performance"
            },
            {
                "type": InsightType.CONSISTENT.value,
                "label": "Consistent",
                "description": "Regular upload schedule maintained"
            },
            {
                "type": InsightType.VIRAL_POTENTIAL.value,
                "label": "Viral Potential",
                "description": "High engagement indicates content shareability"
            }
        ]
    }


@router.get("/niches")
async def get_available_niches():
    """Get available niche categories with RPM estimates"""
    from services.trend_intelligence.channel_analyzer import RPM_BY_NICHE
    
    return {
        "niches": [
            {"name": niche, "estimated_rpm": rpm}
            for niche, rpm in sorted(RPM_BY_NICHE.items(), key=lambda x: -x[1])
        ]
    }
