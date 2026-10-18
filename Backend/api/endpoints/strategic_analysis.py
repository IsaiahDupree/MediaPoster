"""
Strategic Analysis API
======================
Endpoints for triggering and retrieving cross-platform strategic analysis.

Endpoints:
- POST /api/strategy/analyze         - Trigger a full cross-platform analysis
- GET  /api/strategy/report          - Get the latest strategic report
- GET  /api/strategy/status          - Get service status
- GET  /api/strategy/recommendations - Get latest recommendations only
- GET  /api/strategy/cadence         - Get latest posting cadence only
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel
from loguru import logger

from services.strategic_analysis_service import get_strategic_analysis_service
from services.event_bus import EventBus, Topics


router = APIRouter(prefix="/api/strategy", tags=["Strategic Analysis"])


# ── Request / Response Models ────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    """Request to trigger a strategic analysis run"""
    platforms: List[str] = ["youtube", "tiktok", "instagram", "instagram_graph", "facebook_ads"]


class AnalysisResponse(BaseModel):
    """Response after triggering analysis"""
    status: str
    correlation_id: str
    message: str


class ServiceStatusResponse(BaseModel):
    """Service status"""
    is_running: bool
    has_report: bool
    latest_report_time: Optional[str] = None
    latest_report_status: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalysisResponse)
async def trigger_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger a full cross-platform strategic analysis.

    This fires `strategy.analysis.requested` on the event bus and runs
    the analysis pipeline asynchronously. The pipeline:

    1. Collects live data from YouTube, TikTok, Instagram APIs
    2. Publishes per-platform `strategy.platform.data_ready` events
    3. Sends all data to OpenAI for strategic analysis
    4. Publishes `strategy.recommendations.ready` and `strategy.cadence.updated`
    5. Publishes final `strategy.report.ready` event

    Poll `GET /api/strategy/report` for results, or subscribe to
    `strategy.report.ready` on the event bus.
    """
    from uuid import uuid4

    service = get_strategic_analysis_service()
    correlation_id = str(uuid4())

    async def _run():
        try:
            # Ensure service is started (subscribes to topics)
            if not service._is_running:
                await service.start()

            # Fire the event — the service handler will run the pipeline
            bus = EventBus.get_instance()
            await bus.publish(
                Topics.STRATEGY_ANALYSIS_REQUESTED,
                {"platforms": request.platforms},
                correlation_id=correlation_id,
                source="api",
            )
        except Exception as e:
            logger.error(f"Analysis trigger failed: {e}")

    background_tasks.add_task(_run)

    return AnalysisResponse(
        status="accepted",
        correlation_id=correlation_id,
        message=f"Analysis queued for {', '.join(request.platforms)}. "
                f"Poll GET /api/strategy/report or subscribe to strategy.report.ready",
    )


@router.post("/analyze/sync")
async def trigger_analysis_sync(
    request: AnalysisRequest,
):
    """
    Run a full cross-platform strategic analysis synchronously.

    Returns the complete report when done. This can take 15-30 seconds
    as it fetches live data from all platform APIs and runs AI analysis.
    """
    service = get_strategic_analysis_service()

    if not service._is_running:
        await service.start()

    try:
        report = await service.run_full_analysis(platforms=request.platforms)
        return report.to_dict()
    except Exception as e:
        logger.error(f"Sync analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_latest_report():
    """
    Get the latest strategic analysis report.

    Returns the full report including platform snapshots, AI analysis,
    recommendations, and posting cadence.
    """
    service = get_strategic_analysis_service()
    report = service.get_latest_report()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No analysis report available. Trigger one via POST /api/strategy/analyze",
        )

    return report


@router.get("/status", response_model=ServiceStatusResponse)
async def get_service_status():
    """Get the strategic analysis service status."""
    service = get_strategic_analysis_service()
    status = service.get_status()
    return ServiceStatusResponse(**status)


@router.get("/recommendations")
async def get_recommendations():
    """
    Get only the latest recommendations from the strategic report.

    Returns immediate actions and account consolidation advice.
    """
    service = get_strategic_analysis_service()
    report = service.get_latest_report()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No report available. Trigger analysis first.",
        )

    return {
        "immediate_actions": report.get("recommendations", []),
        "account_consolidation": report.get("ai_analysis", {}).get("account_consolidation", []),
        "diagnosis": report.get("ai_analysis", {}).get("diagnosis", ""),
    }


@router.get("/cadence")
async def get_cadence():
    """
    Get only the latest posting cadence from the strategic report.

    Returns the weekly schedule, content strategy, and KPIs.
    """
    service = get_strategic_analysis_service()
    report = service.get_latest_report()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No report available. Trigger analysis first.",
        )

    return report.get("cadence", {})
