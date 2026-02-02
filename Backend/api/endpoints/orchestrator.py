"""
Orchestrator API Endpoints (ARCH-007)
======================================
REST API for Master Orchestrator pipeline management.

Endpoints:
    POST   /api/orchestrator/pipeline/start    - Start new pipeline
    GET    /api/orchestrator/pipeline/:id      - Get pipeline status
    GET    /api/orchestrator/pipelines         - List pipelines
    DELETE /api/orchestrator/pipeline/:id      - Cancel pipeline
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from services.master_orchestrator import MasterOrchestrator, PipelineConfig

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


# ============================================================================
# Request/Response Models
# ============================================================================

class StartPipelineRequest(BaseModel):
    """Request to start a new orchestrated pipeline."""

    theme: str = Field(..., description="Video theme/topic", min_length=1)
    num_parts: int = Field(3, ge=1, le=5, description="Number of video parts (1-5)")
    character: Optional[str] = Field(None, description="Sora @character (e.g., @isaiahdupree)")
    publish_platforms: List[str] = Field(
        default=["tiktok", "instagram", "youtube"],
        description="Platforms to publish to"
    )
    schedule_tweets: bool = Field(True, description="Whether to schedule Twitter campaign")
    tweets_per_day: int = Field(12, ge=1, le=60, description="Tweets per day (1-60)")
    offer_url: Optional[str] = Field(None, description="Offer URL to track and promote")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "theme": "AI automation revolutionizing content creation",
                "num_parts": 3,
                "character": "@isaiahdupree",
                "publish_platforms": ["tiktok", "instagram", "youtube"],
                "schedule_tweets": True,
                "tweets_per_day": 12,
                "offer_url": "https://blotato.com/offers/ai-automation"
            }
        }


# Alias for backwards compatibility
RunPipelineRequest = StartPipelineRequest


class PipelineStatusResponse(BaseModel):
    """Pipeline status response."""

    pipeline_id: str
    theme: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    steps_completed: int
    total_steps: int
    video_path: Optional[str] = None
    published_count: int = 0
    tweets_scheduled: int = 0
    error: Optional[str] = None


class PipelineListItem(BaseModel):
    """Pipeline list item."""

    pipeline_id: str
    theme: str
    status: str
    started_at: datetime
    video_path: Optional[str] = None
    published_count: int = 0
    tweets_scheduled: int = 0


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/pipeline/start")
async def start_pipeline(
    request: StartPipelineRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Start a new orchestrated pipeline (ARCH-007).

    Workflow:
        1. Generate 3-part Sora video
        2. Stitch parts together
        3. Analyze content with AI
        4. Publish to multiple platforms
        5. Schedule Twitter campaign (optional)
        6. Track offer performance (optional)

    Returns:
        - pipeline_id: Unique pipeline identifier
        - status: Pipeline status (initializing)
        - message: Human-readable message
    """
    try:
        orchestrator = MasterOrchestrator.get_instance()

        # Create pipeline config
        config = PipelineConfig(
            theme=request.theme,
            num_parts=request.num_parts,
            character=request.character,
            publish_platforms=request.publish_platforms,
            schedule_tweets=request.schedule_tweets,
            tweets_per_day=request.tweets_per_day,
            offer_url=request.offer_url,
            metadata=request.metadata
        )

        # Start pipeline in background
        pipeline_id = await orchestrator.start_pipeline(config)

        return {
            "success": True,
            "pipeline_id": pipeline_id,
            "status": "initializing",
            "message": f"Pipeline started: {request.theme}",
            "steps": [
                "Sora video generation",
                "Content analysis",
                "Multi-platform publishing",
                "Twitter campaign scheduling" if request.schedule_tweets else None,
                "Offer tracking" if request.offer_url else None
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {str(e)}")


@router.post("/pipeline/run")
async def run_pipeline(
    request: StartPipelineRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Alias for /pipeline/start - runs a new orchestrated pipeline (ARCH-007).

    This is an alternative endpoint name for better API discoverability.
    Internally calls the same start_pipeline logic.
    """
    return await start_pipeline(request, background_tasks)


@router.get("/pipeline/{pipeline_id}")
async def get_pipeline_status(pipeline_id: str) -> Dict[str, Any]:
    """
    Get status of a running or completed pipeline.

    Args:
        pipeline_id: Unique pipeline identifier

    Returns:
        Pipeline status including progress, outputs, and errors
    """
    try:
        orchestrator = MasterOrchestrator.get_instance()
        status = orchestrator.get_pipeline_status(pipeline_id)

        if "error" in status and status["error"] == "Pipeline not found":
            raise HTTPException(status_code=404, detail="Pipeline not found")

        return {"success": True, **status}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline status: {str(e)}")


@router.get("/pipelines")
async def list_pipelines(
    status: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    List recent pipelines.

    Args:
        status: Filter by status (initializing, generating_video, analyzing, publishing, completed, failed)
        limit: Max number of results (default 10)

    Returns:
        List of pipeline summaries
    """
    try:
        orchestrator = MasterOrchestrator.get_instance()
        pipelines = await orchestrator.list_pipelines(status=status, limit=limit)

        return {
            "success": True,
            "count": len(pipelines),
            "pipelines": [
                PipelineListItem(
                    pipeline_id=p.get("pipeline_id", ""),
                    theme=p.get("theme", ""),
                    status=p.get("status", ""),
                    started_at=p.get("started_at", datetime.now().isoformat()),
                    video_path=p.get("stitched_video"),
                    published_count=p.get("published_count", 0),
                    tweets_scheduled=p.get("tweets_scheduled", 0)
                )
                for p in pipelines
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list pipelines: {str(e)}")


@router.get("/pipeline/{pipeline_id}/events")
async def get_pipeline_events(pipeline_id: str) -> Dict[str, Any]:
    """
    Get all events for a pipeline (for debugging/monitoring).

    Args:
        pipeline_id: Unique pipeline identifier

    Returns:
        List of event bus events for this pipeline
    """
    try:
        from services.event_bus import EventBus

        bus = EventBus.get_instance()

        # Get events by correlation_id
        events = bus.get_recent_events(correlation_id=pipeline_id, limit=100)

        return {
            "success": True,
            "pipeline_id": pipeline_id,
            "event_count": len(events),
            "events": [
                {
                    "event_id": e.event_id,
                    "topic": e.topic,
                    "timestamp": e.timestamp.isoformat(),
                    "payload": e.payload,
                    "source": e.source
                }
                for e in events
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline events: {str(e)}")


@router.get("/stats")
async def get_orchestrator_stats() -> Dict[str, Any]:
    """
    Get orchestrator performance metrics.

    Returns:
        Aggregated stats about pipeline executions
    """
    try:
        from config.supabase_client import get_supabase_client

        supabase = get_supabase_client()

        # Get pipeline metrics (last 30 days)
        result = supabase.rpc("get_pipeline_metrics", {"days": 30}).execute()

        if result.data and len(result.data) > 0:
            metrics = result.data[0]
        else:
            metrics = {
                "total_pipelines": 0,
                "successful_pipelines": 0,
                "failed_pipelines": 0,
                "success_rate": 0,
                "avg_duration_seconds": 0,
                "total_videos_generated": 0,
                "total_posts_published": 0,
                "total_tweets_scheduled": 0
            }

        return {
            "success": True,
            "period_days": 30,
            "metrics": metrics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ============================================================================
# Metrics (ARCH-008)
# ============================================================================

@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get aggregate pipeline metrics for dashboard widget (ARCH-008)."""
    try:
        orchestrator = MasterOrchestrator.get_instance()
        metrics = orchestrator.get_pipeline_metrics()
        return {"success": True, **metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check orchestrator health."""
    try:
        orchestrator = MasterOrchestrator.get_instance()

        return {
            "success": True,
            "status": "healthy",
            "active_pipelines": len(orchestrator.active_pipelines),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# Analytics Endpoints (ARCH-006)
# ============================================================================

@router.get("/pipeline/{pipeline_id}/analytics")
async def get_pipeline_analytics(pipeline_id: str) -> Dict[str, Any]:
    """
    Get AI-powered analytics for a pipeline (ARCH-006).

    Analyzes content performance and provides optimization suggestions.

    Args:
        pipeline_id: Pipeline identifier

    Returns:
        Analytics feedback with AI insights and suggestions
    """
    try:
        from services.analytics_feedback_loop import AnalyticsFeedbackLoop

        feedback_loop = AnalyticsFeedbackLoop.get_instance()
        analysis = await feedback_loop.analyze_pipeline_performance(pipeline_id)

        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])

        if "status" in analysis and analysis["status"] == "waiting":
            return {
                "success": False,
                "status": "waiting",
                "message": analysis["message"]
            }

        return {
            "success": True,
            "pipeline_id": pipeline_id,
            **analysis
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.get("/analytics/top-themes")
async def get_top_performing_themes(limit: int = 10) -> Dict[str, Any]:
    """
    Get top performing themes for content ideas (ARCH-006).

    Returns themes with best engagement and views.

    Args:
        limit: Number of themes to return (default 10)

    Returns:
        List of top themes with performance metrics
    """
    try:
        from services.analytics_feedback_loop import AnalyticsFeedbackLoop

        feedback_loop = AnalyticsFeedbackLoop.get_instance()
        themes = feedback_loop.get_top_performing_themes(limit=limit)

        return {
            "success": True,
            "count": len(themes),
            "themes": themes
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top themes: {str(e)}")


@router.get("/analytics/historical")
async def get_historical_insights(
    days: int = 30,
    min_rating: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get historical performance insights (ARCH-006).

    Returns past feedback for learning and pattern identification.

    Args:
        days: Number of days to look back (default 30)
        min_rating: Minimum rating filter (excellent, good, average, poor)

    Returns:
        Historical analytics insights
    """
    try:
        from services.analytics_feedback_loop import AnalyticsFeedbackLoop

        feedback_loop = AnalyticsFeedbackLoop.get_instance()
        insights = feedback_loop.get_historical_insights(
            days=days,
            min_rating=min_rating
        )

        return {
            "success": True,
            "count": len(insights),
            "period_days": days,
            "insights": insights
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get historical insights: {str(e)}")


# ============================================================================
# Traffic Tracking Endpoints (ARCH-005)
# ============================================================================

@router.get("/pipeline/{pipeline_id}/traffic")
async def get_pipeline_traffic(pipeline_id: str) -> Dict[str, Any]:
    """
    Get traffic report for a pipeline (ARCH-005).

    Shows clicks, conversions, and revenue from offer links.

    Args:
        pipeline_id: Pipeline identifier

    Returns:
        Traffic metrics and conversion data
    """
    try:
        from services.offer_traffic_tracker import OfferTrafficTracker

        tracker = OfferTrafficTracker.get_instance()
        report = tracker.get_pipeline_traffic_report(pipeline_id)

        return {
            "success": True,
            **report
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get traffic report: {str(e)}")


@router.get("/traffic/platform-performance")
async def get_platform_performance(days: int = 30) -> Dict[str, Any]:
    """
    Get performance metrics by platform (ARCH-005).

    Shows which platforms drive the most traffic and conversions.

    Args:
        days: Number of days to analyze (default 30)

    Returns:
        Platform performance metrics
    """
    try:
        from services.offer_traffic_tracker import OfferTrafficTracker
        from datetime import timezone, timedelta

        tracker = OfferTrafficTracker.get_instance()

        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        end_date = datetime.now(timezone.utc)

        platforms = tracker.get_platform_performance(
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "platforms": platforms
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get platform performance: {str(e)}")


@router.get("/traffic/top-campaigns")
async def get_top_campaigns(
    limit: int = 10,
    metric: str = "clicks"
) -> Dict[str, Any]:
    """
    Get top performing campaigns (ARCH-005).

    Returns campaigns with best traffic or conversions.

    Args:
        limit: Number of campaigns to return (default 10)
        metric: Sort by clicks, conversions, or revenue_usd (default clicks)

    Returns:
        Top performing campaigns
    """
    try:
        from services.offer_traffic_tracker import OfferTrafficTracker

        tracker = OfferTrafficTracker.get_instance()
        campaigns = tracker.get_top_performing_campaigns(
            limit=limit,
            metric=metric
        )

        return {
            "success": True,
            "count": len(campaigns),
            "sorted_by": metric,
            "campaigns": campaigns
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top campaigns: {str(e)}")
