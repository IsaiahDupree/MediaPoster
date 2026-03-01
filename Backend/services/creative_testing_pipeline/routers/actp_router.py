"""
ACTP FastAPI Router
====================
API endpoints for the Ad Creative Testing Pipeline.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/actp", tags=["ACTP"])


def _get_db():
    """Get Supabase client."""
    import os
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
    except ImportError:
        pass
    return None


def _get_orchestrator():
    from services.creative_testing_pipeline.orchestrator import PipelineOrchestrator
    return PipelineOrchestrator(db_client=_get_db())


def _get_creative_engine():
    from services.creative_testing_pipeline.creative_engine import CreativeEngine
    return CreativeEngine(db_client=_get_db())


def _get_publisher():
    from services.creative_testing_pipeline.organic_publisher import OrganicPublisher
    return OrganicPublisher(db_client=_get_db())


def _get_analytics():
    from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
    return AnalyticsCollector(db_client=_get_db())


def _get_winner_selector():
    from services.creative_testing_pipeline.winner_selector import WinnerSelector
    return WinnerSelector(db_client=_get_db())


def _get_ad_deployer():
    from services.creative_testing_pipeline.ad_deployer import AdBudgetDeployer
    return AdBudgetDeployer(db_client=_get_db())


def _get_iteration_engine():
    from services.creative_testing_pipeline.iteration_engine import IterationEngine
    return IterationEngine(db_client=_get_db())


def _get_offer_connector():
    from services.creative_testing_pipeline.offer_connector import OfferConnector
    return OfferConnector(db_client=_get_db())


# ─── Campaign Endpoints ──────────────────────────────────

@router.post("/campaigns")
async def create_campaign(body: dict):
    """Create a new test campaign."""
    from services.creative_testing_pipeline.models import CreateCampaignRequest
    try:
        request = CreateCampaignRequest(**body)
        orchestrator = _get_orchestrator()
        campaign = await orchestrator.create_campaign(request)
        return {"campaign": campaign.model_dump(mode="json")}
    except Exception as e:
        logger.error(f"[ACTP API] Create campaign failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaigns")
async def list_campaigns(status: Optional[str] = Query(None)):
    """List all test campaigns."""
    orchestrator = _get_orchestrator()
    campaigns = await orchestrator.list_campaigns(status=status)
    return {"campaigns": [c.model_dump(mode="json") for c in campaigns]}


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get full campaign detail with rounds, creatives, metrics."""
    orchestrator = _get_orchestrator()
    detail = await orchestrator.get_campaign_detail(campaign_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return detail


@router.post("/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: str):
    """Start a campaign — triggers creative generation."""
    orchestrator = _get_orchestrator()
    try:
        campaign = await orchestrator.start_campaign(campaign_id)
        return {"campaign": campaign.model_dump(mode="json")}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    """Pause a running campaign."""
    orchestrator = _get_orchestrator()
    try:
        campaign = await orchestrator.pause_campaign(campaign_id)
        return {"campaign": campaign.model_dump(mode="json")}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/resume")
async def resume_campaign(campaign_id: str):
    """Resume a paused campaign."""
    orchestrator = _get_orchestrator()
    try:
        campaign = await orchestrator.resume_campaign(campaign_id)
        return {"campaign": campaign.model_dump(mode="json")}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Round Endpoints ─────────────────────────────────────

@router.post("/rounds/{round_id}/generate")
async def generate_creatives(round_id: str, body: dict = {}):
    """Generate creatives for a round."""
    orchestrator = _get_orchestrator()
    test_round = await orchestrator._get_round(round_id)
    if not test_round:
        raise HTTPException(status_code=404, detail="Round not found")

    campaign = await orchestrator._get_campaign(test_round.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    engine = _get_creative_engine()
    angles = body.get("angles") or campaign.angles or ["general"]
    provider = body.get("provider")

    briefs = await engine.generate_briefs(campaign, angles)
    creatives = await engine.generate_creatives(campaign, test_round, briefs, provider)

    # Advance round status
    await orchestrator.advance_round(round_id)

    return {
        "creatives": [c.model_dump(mode="json") for c in creatives],
        "count": len(creatives),
    }


@router.post("/rounds/{round_id}/publish")
async def publish_creatives(round_id: str, body: dict = {}):
    """Publish creatives organically."""
    orchestrator = _get_orchestrator()
    test_round = await orchestrator._get_round(round_id)
    if not test_round:
        raise HTTPException(status_code=404, detail="Round not found")

    creatives = await orchestrator._get_creatives_for_round(round_id)
    if not creatives:
        raise HTTPException(status_code=400, detail="No creatives to publish")

    publisher = _get_publisher()
    platforms = body.get("platforms")
    posts = await publisher.publish_creatives(creatives, platforms)

    await orchestrator.advance_round(round_id)

    return {
        "posts": [p.model_dump(mode="json") for p in posts],
        "count": len(posts),
    }


@router.post("/rounds/{round_id}/collect-metrics")
async def collect_metrics(round_id: str):
    """Collect analytics for published posts."""
    orchestrator = _get_orchestrator()
    test_round = await orchestrator._get_round(round_id)
    if not test_round:
        raise HTTPException(status_code=404, detail="Round not found")

    creatives = await orchestrator._get_creatives_for_round(round_id)
    posts = await orchestrator._get_organic_posts_for_round(round_id, creatives)

    analytics = _get_analytics()
    logs = await analytics.collect_metrics(posts, round_id)

    return {"metrics_collected": len(logs)}


@router.post("/rounds/{round_id}/select-winners")
async def select_winners(round_id: str, body: dict = {}):
    """Run winner selection for a round."""
    orchestrator = _get_orchestrator()
    test_round = await orchestrator._get_round(round_id)
    if not test_round:
        raise HTTPException(status_code=404, detail="Round not found")

    creatives = await orchestrator._get_creatives_for_round(round_id)
    top_n = body.get("top_n")

    selector = _get_winner_selector()

    from services.creative_testing_pipeline.models import RoundType
    if test_round.round_type == RoundType.ORGANIC:
        posts = await orchestrator._get_organic_posts_for_round(round_id, creatives)
        winners = await selector.select_organic_winners(creatives, posts, round_id, top_n)
    else:
        ads = await orchestrator._get_ad_deployments_for_round(round_id)
        winners = await selector.select_ad_winners(creatives, ads, round_id, top_n)

    await orchestrator.advance_round(round_id)

    return {
        "winners": [w.model_dump(mode="json") for w in winners],
        "count": len(winners),
    }


@router.post("/rounds/{round_id}/deploy-ads")
async def deploy_ads(round_id: str):
    """Deploy ad spend on winners."""
    orchestrator = _get_orchestrator()
    test_round = await orchestrator._get_round(round_id)
    if not test_round:
        raise HTTPException(status_code=404, detail="Round not found")

    campaign = await orchestrator._get_campaign(test_round.campaign_id)
    creatives = await orchestrator._get_creatives_for_round(round_id)
    winners = await orchestrator._get_winners_for_round(round_id)

    if not winners:
        raise HTTPException(status_code=400, detail="No winners to deploy")

    deployer = _get_ad_deployer()
    deployments = await deployer.deploy_winners(winners, creatives, campaign, test_round)

    await orchestrator.advance_round(round_id)

    return {
        "deployments": [d.model_dump(mode="json") for d in deployments],
        "count": len(deployments),
    }


@router.post("/rounds/{round_id}/iterate")
async def iterate_round(round_id: str, body: dict = {}):
    """Generate next round variations from winners."""
    orchestrator = _get_orchestrator()
    test_round = await orchestrator._get_round(round_id)
    if not test_round:
        raise HTTPException(status_code=404, detail="Round not found")

    campaign = await orchestrator._get_campaign(test_round.campaign_id)
    creatives = await orchestrator._get_creatives_for_round(round_id)
    winners = await orchestrator._get_winners_for_round(round_id)

    iteration = _get_iteration_engine()
    elements = iteration.extract_winning_elements(winners, creatives)
    strategies = body.get("strategies")
    count = body.get("count", 5)
    briefs = await iteration.generate_next_round_briefs(elements, campaign, strategies, count)

    # Create next round
    next_round = await orchestrator.create_next_round(test_round.campaign_id)

    return {
        "briefs": briefs,
        "next_round": next_round.model_dump(mode="json"),
        "winning_elements": elements,
    }


# ─── Creative Endpoints ──────────────────────────────────

@router.get("/creatives/{creative_id}")
async def get_creative(creative_id: str):
    """Get creative detail with all metrics."""
    db = _get_db()
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")

    result = await db.table("actp_creatives").select("*").eq("id", creative_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Creative not found")

    # Get organic posts
    posts = await db.table("actp_organic_posts").select("*").eq("creative_id", creative_id).execute()

    # Get ad deployments
    ads = await db.table("actp_ad_deployments").select("*").eq("creative_id", creative_id).execute()

    # Get performance logs
    logs = await db.table("actp_performance_logs").select("*").eq(
        "creative_id", creative_id
    ).order("measured_at", desc=True).limit(50).execute()

    return {
        "creative": result.data,
        "organic_posts": posts.data or [],
        "ad_deployments": ads.data or [],
        "performance_logs": logs.data or [],
    }


@router.get("/creatives/{creative_id}/lineage")
async def get_creative_lineage(creative_id: str):
    """Get creative genealogy tree."""
    iteration = _get_iteration_engine()
    lineage = await iteration.get_creative_lineage(creative_id)
    return {"lineage": lineage}


# ─── Analytics Endpoints ─────────────────────────────────

@router.get("/analytics/dashboard")
async def get_dashboard():
    """Get pipeline-wide analytics dashboard."""
    db = _get_db()
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")

    campaigns = await db.table("actp_campaigns").select("*").execute()
    rounds = await db.table("actp_rounds").select("*").execute()
    creatives = await db.table("actp_creatives").select("*").execute()
    winners = await db.table("actp_creatives").select("*").eq("is_winner", True).execute()

    all_campaigns = campaigns.data or []
    all_creatives = creatives.data or []

    total_spend = sum(c.get("total_spend_cents", 0) for c in all_campaigns)
    active = [c for c in all_campaigns if c.get("status") not in ("completed", "failed", "draft")]

    return {
        "total_campaigns": len(all_campaigns),
        "active_campaigns": len(active),
        "total_rounds": len(rounds.data or []),
        "total_creatives": len(all_creatives),
        "total_spend_cents": total_spend,
        "total_winners": len(winners.data or []),
        "recent_winners": (winners.data or [])[:10],
    }


# ─── Offer Endpoints ─────────────────────────────────────

@router.get("/offers")
async def list_offers():
    """List active offers from WaitlistLab."""
    connector = _get_offer_connector()
    offers = await connector.get_active_offers()
    return {"offers": offers}


@router.post("/offers/{offer_id}/create-campaign")
async def create_campaign_from_offer(offer_id: str, body: dict):
    """Create a test campaign from a WaitlistLab offer."""
    connector = _get_offer_connector()
    offer = await connector.get_offer_detail(offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    angles = body.get("angles", [])
    mode = body.get("mode", "offer")
    campaign_data = connector.build_campaign_from_offer(offer, angles, mode)

    from services.creative_testing_pipeline.models import CreateCampaignRequest
    request = CreateCampaignRequest(**campaign_data)
    orchestrator = _get_orchestrator()
    campaign = await orchestrator.create_campaign(request)

    return {"campaign": campaign.model_dump(mode="json")}


# ─── Health Check ─────────────────────────────────────────

@router.get("/health")
async def health_check():
    """Pipeline health check with dependency status."""
    from services.creative_testing_pipeline.monitoring import HealthChecker
    checker = HealthChecker(db_client=_get_db())
    return await checker.check()


# ─── Campaign Extended Endpoints ──────────────────────────

@router.post("/campaigns/{campaign_id}/clone")
async def clone_campaign(campaign_id: str, body: dict = {}):
    """Clone a campaign with its config."""
    orchestrator = _get_orchestrator()
    campaign = await orchestrator.clone_campaign(campaign_id, body.get("name"))
    return {"campaign": campaign.model_dump(mode="json")}


@router.post("/campaigns/{campaign_id}/archive")
async def archive_campaign(campaign_id: str):
    """Soft-delete a campaign."""
    orchestrator = _get_orchestrator()
    await orchestrator.archive_campaign(campaign_id)
    return {"status": "archived"}


@router.post("/campaigns/{campaign_id}/restore")
async def restore_campaign(campaign_id: str):
    """Restore an archived campaign."""
    orchestrator = _get_orchestrator()
    campaign = await orchestrator.restore_campaign(campaign_id)
    return {"campaign": campaign.model_dump(mode="json") if campaign else None}


@router.post("/campaigns/{campaign_id}/tags")
async def update_tags(campaign_id: str, body: dict):
    """Add or remove tags on a campaign."""
    orchestrator = _get_orchestrator()
    if body.get("add"):
        campaign = await orchestrator.add_tags(campaign_id, body["add"])
    elif body.get("remove"):
        campaign = await orchestrator.remove_tags(campaign_id, body["remove"])
    else:
        raise HTTPException(status_code=400, detail="Provide 'add' or 'remove' list")
    return {"campaign": campaign.model_dump(mode="json")}


@router.get("/campaigns/{campaign_id}/progress")
async def get_progress(campaign_id: str):
    """Get campaign progress percentage and duration."""
    orchestrator = _get_orchestrator()
    return await orchestrator.get_progress(campaign_id)


@router.post("/campaigns/{campaign_id}/dry-run")
async def start_dry_run(campaign_id: str):
    """Start a campaign in dry-run mode (no publish/spend)."""
    orchestrator = _get_orchestrator()
    campaign = await orchestrator.start_dry_run(campaign_id)
    return {"campaign": campaign.model_dump(mode="json")}


@router.get("/campaigns/{campaign_id}/history")
async def get_campaign_history(campaign_id: str):
    """Get audit history for a campaign."""
    orchestrator = _get_orchestrator()
    history = await orchestrator.get_audit_history("campaign", campaign_id)
    return {"history": history}


# ─── Bulk Operations ─────────────────────────────────────

@router.post("/campaigns/bulk/pause")
async def bulk_pause(body: dict):
    """Pause multiple campaigns."""
    orchestrator = _get_orchestrator()
    results = await orchestrator.bulk_pause(body.get("campaign_ids", []))
    return {"results": results}


@router.post("/campaigns/bulk/resume")
async def bulk_resume(body: dict):
    """Resume multiple campaigns."""
    orchestrator = _get_orchestrator()
    results = await orchestrator.bulk_resume(body.get("campaign_ids", []))
    return {"results": results}


@router.post("/campaigns/bulk/archive")
async def bulk_archive(body: dict):
    """Archive multiple campaigns."""
    orchestrator = _get_orchestrator()
    results = await orchestrator.bulk_archive(body.get("campaign_ids", []))
    return {"results": results}


# ─── Templates ────────────────────────────────────────────

@router.get("/templates")
async def list_templates():
    """List all campaign templates."""
    orchestrator = _get_orchestrator()
    templates = await orchestrator.list_templates()
    return {"templates": templates}


@router.post("/campaigns/{campaign_id}/save-template")
async def save_template(campaign_id: str, body: dict):
    """Save a campaign's config as a reusable template."""
    orchestrator = _get_orchestrator()
    template = await orchestrator.save_as_template(
        campaign_id, body.get("name", "Untitled"), body.get("description", "")
    )
    return {"template": template}


@router.post("/templates/{template_id}/create-campaign")
async def create_from_template(template_id: str, body: dict):
    """Create a campaign from a template."""
    orchestrator = _get_orchestrator()
    campaign = await orchestrator.create_from_template(
        template_id, body.get("name", "New Campaign"), body.get("offer_id")
    )
    return {"campaign": campaign.model_dump(mode="json")}


# ─── Round Extended Endpoints ─────────────────────────────

@router.post("/rounds/{round_id}/retry")
async def retry_round(round_id: str):
    """Retry a failed round."""
    orchestrator = _get_orchestrator()
    test_round = await orchestrator.retry_round(round_id)
    return {"round": test_round.model_dump(mode="json")}


# ─── Creative Extended Endpoints ──────────────────────────

@router.get("/creatives/search")
async def search_creatives(
    q: Optional[str] = Query(None),
    campaign_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    score_min: Optional[float] = Query(None),
    score_max: Optional[float] = Query(None),
    winner_only: bool = Query(False),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
):
    """Search and filter creatives with full-text search."""
    engine = _get_creative_engine()
    return await engine.search_creatives(
        query=q, campaign_id=campaign_id, source=source,
        score_min=score_min, score_max=score_max,
        winner_only=winner_only, limit=limit, offset=offset,
    )


@router.get("/creatives/{creative_id}/decay-curve")
async def get_decay_curve(creative_id: str):
    """Get engagement decay curve for a creative."""
    analytics = _get_analytics()
    return await analytics.calculate_decay_curve(creative_id)


@router.get("/creatives/{creative_id}/velocity")
async def get_velocity_curve(creative_id: str):
    """Get view velocity curve for a creative."""
    analytics = _get_analytics()
    return await analytics.calculate_velocity_curve(creative_id)


@router.get("/creatives/{creative_id}/snapshots")
async def get_snapshots(creative_id: str):
    """Get metric snapshots (time-series) for a creative."""
    analytics = _get_analytics()
    snapshots = await analytics.get_snapshots(creative_id)
    return {"snapshots": snapshots}


@router.post("/creatives/{creative_id}/estimate-cost")
async def estimate_cost(creative_id: str, body: dict = {}):
    """Estimate generation cost for a provider."""
    engine = _get_creative_engine()
    return engine.estimate_generation_cost(
        body.get("provider", "sora"), body.get("count", 1)
    )


# ─── Analytics Extended Endpoints ─────────────────────────

@router.post("/analytics/compare")
async def compare_creatives_endpoint(body: dict):
    """Compare metrics between creatives."""
    analytics = _get_analytics()
    return await analytics.compare_creatives(
        body.get("creative_ids", []), body.get("round_id", "")
    )


@router.get("/analytics/export")
async def export_metrics(
    campaign_id: Optional[str] = Query(None),
    round_id: Optional[str] = Query(None),
    creative_id: Optional[str] = Query(None),
    format: str = Query("json"),
):
    """Export metrics as CSV or JSON."""
    analytics = _get_analytics()
    return await analytics.export_metrics(
        campaign_id=campaign_id, round_id=round_id,
        creative_id=creative_id, format=format,
    )


@router.get("/analytics/round/{round_id}")
async def get_round_analytics(round_id: str):
    """Get aggregate metrics for a round."""
    analytics = _get_analytics()
    return await analytics.aggregate_round_metrics(round_id)


@router.get("/analytics/campaign/{campaign_id}")
async def get_campaign_analytics(campaign_id: str):
    """Get aggregate metrics for a campaign with trend data."""
    analytics = _get_analytics()
    return await analytics.aggregate_campaign_metrics(campaign_id)


# ─── Monitoring Endpoints ─────────────────────────────────

@router.get("/monitoring/latency")
async def get_latency_stats():
    """Get latency statistics per pipeline step."""
    from services.creative_testing_pipeline.monitoring import get_latency_tracker
    return get_latency_tracker().get_stats()


@router.get("/monitoring/errors")
async def get_error_rates():
    """Get error rates per module."""
    from services.creative_testing_pipeline.monitoring import get_error_tracker
    return get_error_tracker().get_error_rates()


@router.get("/monitoring/costs/{campaign_id}")
async def get_cost_breakdown(campaign_id: str):
    """Get cost breakdown for a campaign."""
    from services.creative_testing_pipeline.monitoring import CostTracker
    tracker = CostTracker(db_client=_get_db())
    return await tracker.get_campaign_cost_breakdown(campaign_id)


@router.get("/monitoring/stale")
async def get_stale_campaigns():
    """Detect stale campaigns without recent progress."""
    from services.creative_testing_pipeline.monitoring import StaleCampaignDetector
    detector = StaleCampaignDetector(db_client=_get_db())
    return {"stale_campaigns": await detector.detect_stale()}


@router.get("/monitoring/dlq")
async def get_dead_letter_queue():
    """List pending dead letter queue items."""
    from services.creative_testing_pipeline.monitoring import DeadLetterQueue
    dlq = DeadLetterQueue(db_client=_get_db())
    return {"items": await dlq.list_pending()}


# ─── Security Endpoints ──────────────────────────────────

@router.get("/security/providers")
async def get_provider_status():
    """Check which providers are configured."""
    from services.creative_testing_pipeline.security import SecretsValidator
    return {
        "required": SecretsValidator.validate_required(),
        "optional": SecretsValidator.validate_optional(),
        "providers": SecretsValidator.get_provider_availability(),
    }


@router.get("/publisher/credentials")
async def check_publisher_credentials():
    """Check which publisher platforms are configured."""
    publisher = _get_publisher()
    return {"credentials": publisher.check_credentials()}


# ─── Webhook Configuration CRUD ───────────────────────────

@router.post("/webhooks")
async def create_webhook(body: dict):
    """Register a new outbound webhook endpoint."""
    from ..integration import WebhookManager
    db = _get_db()
    mgr = WebhookManager(db)
    url = body.get("url")
    events = body.get("events", [])
    secret = body.get("secret")
    if not url or not events:
        raise HTTPException(status_code=400, detail="url and events are required")
    return await mgr.create(url, events, secret)


@router.get("/webhooks")
async def list_webhooks():
    """List all registered outbound webhooks."""
    from ..integration import WebhookManager
    db = _get_db()
    mgr = WebhookManager(db)
    return {"webhooks": await mgr.list_all()}


@router.patch("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, body: dict):
    """Update a webhook configuration."""
    from ..integration import WebhookManager
    db = _get_db()
    mgr = WebhookManager(db)
    return await mgr.update(webhook_id, body)


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Deactivate a webhook."""
    from ..integration import WebhookManager
    db = _get_db()
    mgr = WebhookManager(db)
    deleted = await mgr.delete(webhook_id)
    return {"deleted": deleted, "webhook_id": webhook_id}


@router.post("/webhooks/receive")
async def receive_webhook(source: str, event_type: str, body: dict):
    """Receive an inbound webhook from an external platform."""
    from ..integration import WebhookReceiver
    db = _get_db()
    receiver = WebhookReceiver(db)
    return await receiver.receive(source, event_type, body)


# ─── Funnel Tracking Endpoints ────────────────────────────

@router.post("/funnel/click")
async def record_funnel_click(body: dict):
    """Record a click event from a creative."""
    from ..integration import FunnelTracker
    db = _get_db()
    tracker = FunnelTracker(db)
    creative_id = body.get("creative_id")
    source = body.get("source", "unknown")
    if not creative_id:
        raise HTTPException(status_code=400, detail="creative_id required")
    event_id = await tracker.record_click(creative_id, source, body.get("metadata"))
    return {"recorded": True, "event_id": event_id}


@router.post("/funnel/conversion")
async def record_funnel_conversion(body: dict):
    """Record a conversion event."""
    from ..integration import FunnelTracker
    db = _get_db()
    tracker = FunnelTracker(db)
    creative_id = body.get("creative_id")
    if not creative_id:
        raise HTTPException(status_code=400, detail="creative_id required")
    await tracker.record_conversion(
        creative_id,
        body.get("session_id", ""),
        body.get("revenue_cents", 0),
        body.get("metadata"),
    )
    return {"recorded": True}


@router.get("/funnel/{creative_id}/stats")
async def get_funnel_stats(creative_id: str):
    """Get funnel stats for a creative."""
    from ..integration import FunnelTracker
    db = _get_db()
    tracker = FunnelTracker(db)
    return await tracker.get_funnel_stats(creative_id)


# ─── Real-Time Metric Streaming (SSE) ─────────────────────

@router.get("/analytics/{creative_id}/stream")
async def stream_metrics(creative_id: str):
    """Stream real-time metric updates for a creative via Server-Sent Events."""
    from fastapi.responses import StreamingResponse
    import asyncio

    async def event_generator():
        db = _get_db()
        analytics = _get_analytics()
        sent_count = 0
        max_events = 60  # 60 updates max per stream session

        while sent_count < max_events:
            try:
                if db:
                    result = await db.table("actp_performance_logs").select(
                        "metric_type, value, measured_at"
                    ).eq("creative_id", creative_id).order(
                        "measured_at", desc=True
                    ).limit(10).execute()

                    data = json.dumps({
                        "creative_id": creative_id,
                        "metrics": result.data or [],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    data = json.dumps({"creative_id": creative_id, "metrics": [], "timestamp": datetime.now(timezone.utc).isoformat()})

                yield f"data: {data}\n\n"
                sent_count += 1
                await asyncio.sleep(5)
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Completion Rate by Video Second ──────────────────────

@router.get("/analytics/{creative_id}/retention")
async def get_retention_curve(creative_id: str):
    """Get audience retention curve (completion rate by second)."""
    analytics = _get_analytics()
    return await analytics.get_retention_curve(creative_id)


@router.get("/analytics/{creative_id}/peak-engagement")
async def get_peak_engagement(creative_id: str):
    """Get peak engagement time for a creative."""
    analytics = _get_analytics()
    return await analytics.detect_peak_engagement_time(creative_id)


# ─── Competitor Benchmark ─────────────────────────────────

@router.get("/analytics/benchmarks/{platform}")
async def get_platform_benchmarks(platform: str):
    """Get industry benchmark metrics for a platform."""
    benchmarks = {
        "tiktok": {
            "avg_engagement_rate": 5.96,
            "avg_completion_rate": 0.45,
            "avg_ctr_ads": 1.5,
            "avg_cpc_usd": 0.50,
            "avg_cpm_usd": 10.0,
            "source": "TikTok for Business 2024",
        },
        "youtube_shorts": {
            "avg_engagement_rate": 3.2,
            "avg_completion_rate": 0.55,
            "avg_ctr_ads": 0.65,
            "avg_cpc_usd": 0.49,
            "avg_cpm_usd": 9.68,
            "source": "Google Ads Benchmarks 2024",
        },
        "instagram_reels": {
            "avg_engagement_rate": 1.95,
            "avg_completion_rate": 0.38,
            "avg_ctr_ads": 0.88,
            "avg_cpc_usd": 1.28,
            "avg_cpm_usd": 8.83,
            "source": "Meta Ads Benchmarks 2024",
        },
        "meta_ads": {
            "avg_ctr": 0.90,
            "avg_cpc_usd": 1.72,
            "avg_cpm_usd": 14.40,
            "avg_conversion_rate": 9.21,
            "source": "WordStream Meta Benchmarks 2024",
        },
    }
    data = benchmarks.get(platform)
    if not data:
        raise HTTPException(status_code=404, detail=f"No benchmarks for platform: {platform}")
    return {"platform": platform, "benchmarks": data}


# ─── Integration Endpoints ────────────────────────────────

@router.get("/integration/oauth/accounts")
async def list_oauth_accounts():
    """List all connected social OAuth accounts."""
    from ..integration import OAuthManager
    db = _get_db()
    mgr = OAuthManager(db)
    return {"accounts": await mgr.list_connected_accounts()}


@router.post("/integration/offer/{offer_id}/expire")
async def handle_offer_expiry(offer_id: str):
    """Handle offer expiry — pause all related campaigns and ads."""
    from ..integration import OfferExpiryHandler
    db = _get_db()
    handler = OfferExpiryHandler(db)
    return await handler.handle_expiry(offer_id)


@router.get("/integration/landing/{creative_id}/url")
async def get_landing_url(creative_id: str, offer_url: str):
    """Get a tracked landing page URL for a creative."""
    from ..integration import LandingPageManager
    mgr = LandingPageManager(_get_db())
    url = mgr.generate_tracking_url(creative_id, offer_url)
    return {"creative_id": creative_id, "tracking_url": url}


# ─── Creative Library Endpoints ───────────────────────────

@router.get("/creatives/library")
async def list_creative_library(
    campaign_id: Optional[str] = None,
    source: Optional[str] = None,
    winner_only: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """List creatives in the asset library with filtering."""
    engine = _get_engine()
    return await engine.list_library(campaign_id, source, winner_only, limit, offset)


@router.post("/creatives/{creative_id}/approve")
async def approve_creative(creative_id: str, body: dict = {}):
    """Approve a creative for publishing."""
    engine = _get_engine()
    reviewer = body.get("reviewer", "api")
    return await engine.approve_creative(creative_id, reviewer)


@router.post("/creatives/{creative_id}/reject")
async def reject_creative(creative_id: str, body: dict):
    """Reject a creative with a reason."""
    engine = _get_engine()
    reason = body.get("reason", "")
    if not reason:
        raise HTTPException(status_code=400, detail="reason required")
    return await engine.reject_creative(creative_id, reason)


@router.post("/creatives/{creative_id}/submit-approval")
async def submit_creative_for_approval(creative_id: str):
    """Submit a creative for manual approval."""
    engine = _get_engine()
    return await engine.submit_for_approval(creative_id)


@router.post("/creatives/cleanup")
async def cleanup_expired_creatives(max_age_days: int = 90):
    """Clean up expired non-winner creatives."""
    engine = _get_engine()
    return await engine.cleanup_expired_creatives(max_age_days)


# ─── Winner Selection Endpoints ───────────────────────────

@router.get("/campaigns/{campaign_id}/winning-patterns")
async def get_winning_patterns(campaign_id: str):
    """Extract winning patterns from all rounds of a campaign."""
    from ..winner_selector import WinnerSelector
    db = _get_db()
    selector = WinnerSelector(db)
    return {"patterns": await selector.extract_winning_patterns(campaign_id)}


@router.get("/campaigns/{campaign_id}/score-calibration")
async def get_score_calibration(campaign_id: str):
    """Get score calibration data across rounds."""
    from ..winner_selector import WinnerSelector
    db = _get_db()
    selector = WinnerSelector(db)
    return await selector.calibrate_scores(campaign_id)


# ─── Iteration Endpoints ──────────────────────────────────

@router.get("/campaigns/{campaign_id}/diminishing-returns")
async def check_diminishing_returns(campaign_id: str):
    """Check if iteration is yielding diminishing returns."""
    from ..iteration_engine import IterationEngine
    db = _get_db()
    engine = IterationEngine(db)
    return await engine.detect_diminishing_returns(campaign_id)


@router.get("/campaigns/{campaign_id}/angle-exhaustion")
async def check_angle_exhaustion(campaign_id: str):
    """Check if all angles have been exhausted."""
    from ..iteration_engine import IterationEngine
    db = _get_db()
    engine = IterationEngine(db)
    return await engine.detect_angle_exhaustion(campaign_id)


@router.get("/campaigns/{campaign_id}/cross-campaign-insights")
async def get_cross_campaign_insights(campaign_id: str):
    """Get winning patterns from other campaigns."""
    from ..iteration_engine import IterationEngine
    db = _get_db()
    engine = IterationEngine(db)
    return await engine.get_cross_campaign_insights(campaign_id)


# ─── Performance Report ───────────────────────────────────

@router.get("/campaigns/{campaign_id}/report")
async def get_campaign_report(campaign_id: str):
    """Generate a full performance report for a campaign."""
    analytics = _get_analytics()
    return await analytics.generate_report(campaign_id)


# ─── MediaPoster Lite Integration ─────────────────────────

def _get_mplite_publisher():
    from services.creative_testing_pipeline.mplite_publisher import MPLitePublisher
    return MPLitePublisher(db_client=_get_db())


def _get_mplite_client():
    from services.creative_testing_pipeline.mplite_client import MPLiteClient
    return MPLiteClient()


@router.get("/mplite/health")
async def mplite_health():
    """Check MediaPoster Lite API health and connectivity."""
    publisher = _get_mplite_publisher()
    if not publisher.is_configured():
        return {
            "configured": False,
            "message": "MPLITE_KEY not set — set env var to enable MPLite integration",
        }
    try:
        async with _get_mplite_client() as client:
            result = await client.health()
        return {"configured": True, "healthy": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MPLite unreachable: {e}")


@router.get("/mplite/status")
async def mplite_status():
    """Get MediaPoster Lite publishing status — global state, today's counts, queue summary."""
    publisher = _get_mplite_publisher()
    if not publisher.is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        return await publisher.get_queue_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/mplite/daily-summary")
async def mplite_daily_summary():
    """Get today's publish counts by platform from MediaPoster Lite."""
    publisher = _get_mplite_publisher()
    if not publisher.is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        return await publisher.get_daily_summary()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/mplite/can-publish/{platform}")
async def mplite_can_publish(platform: str):
    """Check if MediaPoster Lite can currently publish to a platform."""
    publisher = _get_mplite_publisher()
    if not publisher.is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        return await publisher.can_publish_to(platform)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/mplite/queue")
async def mplite_list_queue(
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List items in the MediaPoster Lite publishing queue."""
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            return await client.list_queue(platform=platform, status=status, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/mplite/queue/stats")
async def mplite_queue_stats():
    """Get MediaPoster Lite queue statistics (counts by status/platform)."""
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            return await client.get_queue_stats()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/mplite/queue/next")
async def mplite_get_next(platform: Optional[str] = Query(None)):
    """Get the next item ready to publish from MediaPoster Lite (used by local machine)."""
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            item = await client.get_next(platform=platform)
        if item is None:
            return {"item": None, "message": "No items ready to publish"}
        return {"item": item}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/mplite/queue/{item_id}")
async def mplite_get_item(item_id: str):
    """Get a specific MediaPoster Lite queue item by ID."""
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            return await client.get_item(item_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/mplite/enqueue")
async def mplite_enqueue(body: dict):
    """
    Enqueue a video for publishing via MediaPoster Lite.

    Body fields:
      - video_url (required): URL of the video to publish
      - platform (required): tiktok | instagram | youtube | twitter | threads
      - account_id (required): platform account ID
      - caption: post caption
      - hashtags: list of hashtags
      - priority: 1-10 (1=highest)
      - scheduled_for: ISO datetime for scheduled publishing
      - title: video title
      - account_username: display username
      - metadata: arbitrary key-value metadata
    """
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            item = await client.enqueue(**body)
        return {"item": item}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mplite/enqueue/creative/{creative_id}")
async def mplite_enqueue_creative(creative_id: str, body: dict):
    """
    Enqueue an ACTP creative for organic publishing via MediaPoster Lite.

    Body fields:
      - platform (required): tiktok | instagram | youtube | twitter | threads
      - account_id (required): platform account ID
      - caption: post caption (defaults to creative hook)
      - hashtags: list of hashtags
      - priority: 1-10
      - scheduled_for: ISO datetime
    """
    publisher = _get_mplite_publisher()
    if not publisher.is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")

    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        result = await db.table("actp_creatives").select("*").eq("id", creative_id).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Creative {creative_id} not found")

        from services.creative_testing_pipeline.models import Creative
        creative = Creative(**result.data)

        caption = body.get("caption") or creative.hook or ""
        platform = body.get("platform")
        account_id = body.get("account_id")

        if not platform:
            raise HTTPException(status_code=400, detail="platform is required")
        if not account_id:
            raise HTTPException(status_code=400, detail="account_id is required")

        enqueue_result = await publisher.enqueue_organic_post(
            creative=creative,
            platform=platform,
            account_id=account_id,
            caption=caption,
            hashtags=body.get("hashtags"),
            priority=body.get("priority", 5),
            scheduled_for=body.get("scheduled_for"),
        )
        return enqueue_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mplite/queue/{item_id}/claim")
async def mplite_claim(item_id: str):
    """Mark a MediaPoster Lite queue item as currently being published."""
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            return await client.claim(item_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/mplite/queue/{item_id}/complete")
async def mplite_complete(item_id: str, body: dict):
    """
    Mark a MediaPoster Lite queue item as successfully published.

    Body fields:
      - platform_url: the live post URL
      - platform_post_id: the platform's post ID
    """
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            return await client.complete(
                item_id,
                platform_url=body.get("platform_url"),
                platform_post_id=body.get("platform_post_id"),
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/mplite/queue/{item_id}/fail")
async def mplite_fail(item_id: str, body: dict):
    """Mark a MediaPoster Lite queue item as failed (will auto-retry)."""
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            return await client.fail(item_id, body.get("error_message", "Unknown error"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/mplite/queue/{item_id}/cancel")
async def mplite_cancel(item_id: str):
    """Cancel a MediaPoster Lite queue item."""
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            return await client.cancel(item_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/mplite/queue/{item_id}/retry")
async def mplite_retry(item_id: str):
    """Retry a failed MediaPoster Lite queue item."""
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            return await client.retry(item_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/mplite/queue/{item_id}/reschedule")
async def mplite_reschedule(item_id: str, body: dict):
    """Reschedule a MediaPoster Lite queue item to a new datetime."""
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    scheduled_for = body.get("scheduled_for")
    if not scheduled_for:
        raise HTTPException(status_code=400, detail="scheduled_for is required")
    try:
        async with _get_mplite_client() as client:
            return await client.reschedule(item_id, scheduled_for)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/mplite/pause")
async def mplite_pause_publishing():
    """Pause all MediaPoster Lite publishing globally."""
    publisher = _get_mplite_publisher()
    if not publisher.is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        return await publisher.pause_publishing()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/mplite/resume")
async def mplite_resume_publishing():
    """Resume MediaPoster Lite publishing globally."""
    publisher = _get_mplite_publisher()
    if not publisher.is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        return await publisher.resume_publishing()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/mplite/history")
async def mplite_history(
    platform: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
):
    """Get MediaPoster Lite publish history."""
    publisher = _get_mplite_publisher()
    if not publisher.is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        return await publisher.get_publish_history(platform=platform, days=days)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/mplite/platforms")
async def mplite_list_platforms():
    """List all platforms configured in MediaPoster Lite."""
    if not _get_mplite_publisher().is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        async with _get_mplite_client() as client:
            return await client.list_platforms()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/mplite/campaigns/{campaign_id}/queue")
async def mplite_campaign_queue(campaign_id: str, platform: Optional[str] = Query(None)):
    """List all MPLite queue items belonging to an ACTP campaign."""
    publisher = _get_mplite_publisher()
    if not publisher.is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        items = await publisher.poll_pending_for_campaign(campaign_id, platform=platform)
        return {"campaign_id": campaign_id, "items": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/mplite/campaigns/{campaign_id}/cancel-queue")
async def mplite_cancel_campaign_queue(campaign_id: str):
    """Cancel all pending MPLite queue items for an ACTP campaign."""
    publisher = _get_mplite_publisher()
    if not publisher.is_configured():
        raise HTTPException(status_code=503, detail="MPLITE_KEY not configured")
    try:
        return await publisher.cancel_campaign_items(campaign_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
