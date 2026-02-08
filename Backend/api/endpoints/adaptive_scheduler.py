"""
Adaptive Scheduler API (ADAPT-001)
====================================
Endpoints for viewing, overriding, and triggering the adaptive scheduling system.
Integrates 44 services across 4 waves for a fully autonomous content scheduling pipeline.

Wave 1 (Core): Blotato, BackgroundPublisher, NarrativeScheduler, VisualCampaign
Wave 2 (Scoring): FATE, TrendBrief, EngagementScorer, WeeklyPlanner, TikTokRepurpose, etc.
Wave 3 (Intelligence): InsightsEngine, BanditAllocator, ContentMix, ABTesting, AI Gen, etc.
Wave 4 (Closed-Loop): TemplateLeaderboard, QAGate, AwarenessClassifier, Competitor, etc.

Endpoints:
    GET  /api/adaptive/status              - Service status (44 services)
    GET  /api/adaptive/schedule            - Current weekly schedule
    GET  /api/adaptive/schedule/7days      - Next 7 days with dates + accounts
    GET  /api/adaptive/content/scored      - Top-scored content
    GET  /api/adaptive/crosspost/queue     - Pending cross-posts + target accounts
    GET  /api/adaptive/offers              - All offers with rotation state
    GET  /api/adaptive/offers/active       - Launchable offers only
    GET  /api/adaptive/videos/pool         - Approved video pool (NarrativeScheduler)
    GET  /api/adaptive/performance         - Performance feedback summary (PostTracker)
    GET  /api/adaptive/products            - Visual campaign products
    GET  /api/adaptive/fate/scores         - FATE persuasion scores for video pool
    GET  /api/adaptive/trends              - Active trend briefs
    GET  /api/adaptive/dm/outreach         - DM outreach queue coordinated with schedule
    GET  /api/adaptive/insights            - Hook pattern + posting time insights
    GET  /api/adaptive/segments            - Segment-level performance patterns
    GET  /api/adaptive/templates/winners   - Winning templates from leaderboard
    GET  /api/adaptive/awareness           - Pool awareness stage distribution
    GET  /api/adaptive/competitor          - Competitor intelligence learnings
    GET  /api/adaptive/benchmarks          - Performance vs competitors/industry
    GET  /api/adaptive/recommendations     - AI-generated daily recommendations
    POST /api/adaptive/adapt               - Trigger core adaptation cycle
    POST /api/adaptive/adapt/full          - Trigger FULL integrated cycle (all 44 services)
    POST /api/adaptive/materialize         - Write schedule to scheduled_posts DB
    POST /api/adaptive/fate/score          - FATE-score the video pool
    POST /api/adaptive/trends/fetch        - Generate trend briefs
    POST /api/adaptive/rewards/compute     - Compute z-score reward function
    POST /api/adaptive/tiktok/repurpose    - Run TikTok repurpose pipeline
    POST /api/adaptive/repurpose/clips     - Generate clips from long-form video
    POST /api/adaptive/dm/coordinate       - Coordinate DM outreach with schedule
    POST /api/adaptive/auto-schedule       - Register recurring cycle via AgentScheduler
    POST /api/adaptive/insights/apply      - Apply insights to schedule
    POST /api/adaptive/bandit/allocate     - Run bandit allocation on formats
    POST /api/adaptive/mix/align           - Align schedule with content mix plan
    POST /api/adaptive/ab-test             - Create A/B test for slot configs
    POST /api/adaptive/ai/generate         - AI-generate captions for empty slots
    POST /api/adaptive/thumbnails/select   - AI-select thumbnails for pool videos
    POST /api/adaptive/sora/generate       - Generate Sora AI video for a slot
    POST /api/adaptive/sleep/sync          - Sync sleep mode with post schedule
    POST /api/adaptive/dco/optimize        - Run DCO creative optimization
    POST /api/adaptive/engagement/trigger  - Trigger post-publish engagement
    POST /api/adaptive/pool/health         - Check video pool analysis health
    POST /api/adaptive/pool/curate         - Auto-curate video pool
    POST /api/adaptive/qa/check            - QA gate check all slots
    POST /api/adaptive/awareness/classify  - Classify pool by awareness stage
    POST /api/adaptive/approval/submit     - Submit schedule for human approval
    POST /api/adaptive/learn/update        - Trigger template learning update
    POST /api/adaptive/trend-intel/ingest  - Ingest trend intelligence
    POST /api/adaptive/sora-daily          - Coordinate daily Sora pipeline
    GET  /api/adaptive/content-gaps        - Content gap analysis vs competitors
    GET  /api/adaptive/inventory           - Content inventory status
    POST /api/adaptive/hooks/inject        - Inject proven hooks into schedule
    POST /api/adaptive/dedup/check         - Deduplication check on schedule
    POST /api/adaptive/formats/classify    - Auto-classify pool video formats
    POST /api/adaptive/clips/select        - AI-select best clips for slots
    POST /api/adaptive/offers/track        - Generate tracked offer links (UTM)
    POST /api/adaptive/daily/sync          - Sync daily automation (Sora + Twitter)
    POST /api/adaptive/checkbacks/schedule - Schedule post-publish checkbacks
    POST /api/adaptive/leads/discover      - Discover new leads for outreach
    POST /api/adaptive/embeddings/generate - Generate semantic embeddings for pool
    POST /api/adaptive/meta-ads/coordinate - Coordinate Meta Ads with organic schedule
    POST /api/adaptive/route               - Route slot to multiple platforms
    POST /api/adaptive/email/trigger       - Trigger email sequences for leads
    POST /api/adaptive/publish/due        - Process and publish due scheduled posts
    GET  /api/adaptive/calendar           - Calendar view of upcoming posts
    POST /api/adaptive/nightly/analyze    - Trigger nightly content analysis
    POST /api/adaptive/hydrate            - Refresh dashboard data sources
    GET  /api/adaptive/trends/velocity    - Trend velocity + scoring
    GET  /api/adaptive/analytics/content  - Content performance analytics
    POST /api/adaptive/touchpoints/check  - Detect orphaned touchpoints
    POST /api/adaptive/twitter/campaigns  - Sync Twitter campaigns
    GET  /api/adaptive/queue/external     - External submission queue status
    POST /api/adaptive/slot                - Add a schedule slot
    PUT  /api/adaptive/slot                - Override a schedule slot
    DELETE /api/adaptive/slot              - Remove a schedule slot
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from loguru import logger


router = APIRouter(prefix="/api/adaptive", tags=["Adaptive Scheduler"])


# =========================================================================
# REQUEST MODELS
# =========================================================================

class SlotRequest(BaseModel):
    day: str
    platform: str
    time_est: Optional[str] = "12:00 PM"
    format: Optional[str] = "Short-form"
    content_type: Optional[str] = "original"
    notes: Optional[str] = ""


class SlotOverride(BaseModel):
    day: str
    platform: str
    updates: Dict[str, Any]


class AdaptRequest(BaseModel):
    """Trigger an adaptation cycle. Optionally pass platform list."""
    platforms: List[str] = ["youtube", "tiktok", "instagram", "instagram_graph", "facebook_ads"]


# =========================================================================
# ENDPOINTS
# =========================================================================

@router.get("/status")
async def get_status():
    """Get adaptive scheduler service status."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.get_status()


@router.get("/schedule")
async def get_schedule():
    """Get the current adaptive weekly schedule."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return {
        "schedule": service.get_weekly_schedule(),
        "total_slots": len(service.get_weekly_schedule()),
        "adaptation_count": service.get_status()["adaptation_count"],
    }


@router.get("/schedule/7days")
async def get_next_7_days():
    """Get schedule for the next 7 days with concrete dates."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return {
        "next_7_days": service.get_next_7_days(),
        "generated_at": __import__("datetime").datetime.now().isoformat(),
    }


@router.get("/content/scored")
async def get_scored_content(
    top_n: int = Query(20, description="Number of top-scored items to return", ge=1, le=100)
):
    """Get top-scored content across all platforms (ranked by composite score)."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    scored = service.get_scored_content(top_n=top_n)
    return {
        "scored_content": scored,
        "total": len(scored),
    }


@router.get("/crosspost/queue")
async def get_crosspost_queue():
    """Get pending cross-post candidates."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    queue = service.get_cross_post_queue()
    return {
        "cross_post_queue": queue,
        "total": len(queue),
    }


@router.get("/offers")
async def get_offers():
    """Get all 11 software product offers with rotation state."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return {
        "offers": service.get_offers(),
        "total": len(service.get_offers()),
    }


@router.get("/offers/active")
async def get_active_offers():
    """Get only launchable offers (>= 60% built)."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    active = service.get_launchable_offers()
    return {
        "active_offers": active,
        "total": len(active),
    }


# =========================================================================
# WAVE 1 INTEGRATION ENDPOINTS
# =========================================================================

@router.get("/videos/pool")
async def get_video_pool(
    limit: int = Query(20, description="Max videos to return", ge=1, le=200)
):
    """Get available analyzed/approved videos from NarrativeScheduler pool."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    pool = service.get_video_pool(limit=limit)
    return {"video_pool": pool, "total": len(pool)}


@router.get("/performance")
async def get_performance_summary():
    """Get performance feedback summary (PostTracker scores -> slot confidence)."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.get_performance_summary()


@router.get("/products")
async def get_campaign_products():
    """Get products from VisualCampaignService for content enrichment."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    products = service.get_visual_campaign_products()
    return {"products": products, "total": len(products)}


@router.post("/materialize")
async def materialize_schedule():
    """
    Write the adaptive schedule into the scheduled_posts DB table.
    PostScheduler picks them up and publishes via BackgroundPublisher -> Blotato -> Platform.
    """
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    created = service.materialize_schedule_to_db()
    return {"success": True, "materialized": len(created), "posts": created}


# =========================================================================
# WAVE 2 INTEGRATION ENDPOINTS
# =========================================================================

@router.get("/fate/scores")
async def get_fate_scores():
    """Get FATE persuasion scores for the video pool."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return {
        "fate_scores": service._fate_scores,
        "total_scored": len(service._fate_scores),
        "video_pool_size": len(service._video_pool),
    }


@router.post("/fate/score")
async def fate_score_pool():
    """Run FATE persuasion scoring on the entire video pool."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    result = service.fate_score_video_pool()
    return {"success": True, **result}


@router.get("/trends")
async def get_trend_briefs():
    """Get active trend briefs (AI-generated content ideas + hooks)."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return {
        "trend_briefs": service._active_trend_briefs,
        "total": len(service._active_trend_briefs),
    }


class TrendRequest(BaseModel):
    trend_names: List[str] = ["AI tools", "productivity hacks", "software development"]


@router.post("/trends/fetch")
async def fetch_trend_briefs(request: TrendRequest):
    """Generate AI-powered trend briefs and inject into schedule slots."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    briefs = await service.fetch_trend_briefs(trend_names=request.trend_names)
    enriched = service.inject_trend_briefs_into_schedule()
    return {
        "success": True,
        "briefs_generated": len(briefs),
        "slots_enriched": enriched,
        "briefs": briefs,
    }


@router.post("/rewards/compute")
async def compute_reward_scores():
    """Apply z-score reward function to scored content (winner/loser classification)."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    results = service.compute_reward_scores()
    return {"success": True, "scored": len(results), "results": results[:20]}


class RepurposeRequest(BaseModel):
    username: str = "isaiah_dupree"


@router.post("/tiktok/repurpose")
async def run_tiktok_repurpose(request: RepurposeRequest):
    """Run TikTok repurpose pipeline: fetch -> download -> analyze -> queue cross-posts."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    result = await service.run_tiktok_repurpose_pipeline(username=request.username)
    return result


class ClipRequest(BaseModel):
    video_path: str
    title: str = ""


@router.post("/repurpose/clips")
async def generate_clips(request: ClipRequest):
    """Extract short clips from long-form video and add to pool."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    result = await service.generate_clips_from_long_content(
        video_path=request.video_path, title=request.title
    )
    return result


@router.get("/dm/outreach")
async def get_dm_outreach():
    """Get DM outreach queue coordinated with content schedule."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return {
        "outreach_queue": service._dm_outreach_queue,
        "total_tasks": len(service._dm_outreach_queue),
    }


@router.post("/dm/coordinate")
async def coordinate_dm_outreach():
    """Coordinate DM outreach timing with content posting schedule."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    tasks = service.coordinate_dm_outreach()
    return {"success": True, "tasks_queued": len(tasks), "tasks": tasks[:20]}


class AutoScheduleRequest(BaseModel):
    interval_hours: int = 24


@router.post("/auto-schedule")
async def register_auto_schedule(request: AutoScheduleRequest):
    """Register the adaptive cycle as a recurring agent via AgentScheduler."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    result = await service.register_adaptive_cycle_schedule(
        interval_hours=request.interval_hours
    )
    return result


class FullCycleRequest(BaseModel):
    """Trigger a full integrated cycle with all 17 services."""
    platforms: List[str] = ["youtube", "tiktok", "instagram", "instagram_graph", "facebook_ads"]


@router.post("/adapt/full")
async def trigger_full_integrated_cycle(request: FullCycleRequest):
    """
    Trigger the FULL integrated adaptive cycle using ALL 17 services:

    1. Strategic analysis + content scoring + cross-posts + offers + fatigue
    2. FATE-score the video pool (persuasion framework)
    3. Fetch trend briefs + inject into schedule slots
    4. Compute z-score engagement rewards
    5. Merge WeeklyPlanner bandit allocation insights
    6. Coordinate DM outreach with posting schedule
    7. Track offer CTAs via Meta Pixel
    8. Materialize to scheduled_posts DB for BackgroundPublisher execution
    """
    try:
        from services.adaptive_scheduler_service import get_adaptive_scheduler
        from services.strategic_analysis_service import get_strategic_analysis_service
        from services.event_bus import EventBus

        bus = EventBus.get_instance()

        strategy_service = get_strategic_analysis_service(event_bus=bus)
        adaptive_service = get_adaptive_scheduler()
        if not adaptive_service._started:
            await adaptive_service.start(event_bus=bus)

        # Run strategic analysis
        logger.info(f"Full Integrated Cycle: Running strategic analysis for {request.platforms}")
        report = await strategy_service.run_full_analysis(platforms=request.platforms)

        # Run full integrated cycle
        result = await adaptive_service.run_full_integrated_cycle(report.to_dict())

        return {"success": True, **result}

    except Exception as e:
        logger.error(f"Full integrated cycle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# CORE ADAPTATION ENDPOINT
# =========================================================================

@router.post("/adapt")
async def trigger_adaptation(request: AdaptRequest):
    """
    Trigger a full adaptation cycle:
    1. Run strategic analysis across all platforms
    2. Score content
    3. Identify cross-post candidates
    4. Rotate offers
    5. Adapt the weekly schedule

    Returns the updated schedule and cross-post queue.
    """
    try:
        from services.adaptive_scheduler_service import get_adaptive_scheduler
        from services.strategic_analysis_service import get_strategic_analysis_service
        from services.event_bus import EventBus

        bus = EventBus.get_instance()

        # Get or start services
        strategy_service = get_strategic_analysis_service(event_bus=bus)
        adaptive_service = get_adaptive_scheduler()
        if not adaptive_service._started:
            await adaptive_service.start(event_bus=bus)

        # Run strategic analysis
        logger.info(f"Adaptive: Running strategic analysis for {request.platforms}")
        report = await strategy_service.run_full_analysis(platforms=request.platforms)

        # Ingest into adaptive scheduler
        await adaptive_service.ingest_assessment(report.to_dict())

        return {
            "success": True,
            "adaptation_number": adaptive_service._adaptation_count,
            "schedule": adaptive_service.get_weekly_schedule(),
            "schedule_slots": len(adaptive_service.get_weekly_schedule()),
            "cross_post_queue": adaptive_service.get_cross_post_queue(),
            "scored_content_top5": adaptive_service.get_scored_content(top_n=5),
            "fatigue_warnings": adaptive_service._check_fatigue(),
        }

    except Exception as e:
        logger.error(f"Adaptation cycle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# WAVE 3 + 4 ENDPOINTS
# =========================================================================

@router.get("/insights")
async def get_insights():
    """Get hook pattern + optimal posting time insights from InsightsEngine."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    hooks = service.get_hook_pattern_insights()
    return {"hook_patterns": hooks}


@router.get("/segments")
async def get_segment_insights():
    """Get segment-level performance patterns from PerformanceCorrelator."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.get_segment_performance_insights()


@router.get("/templates/winners")
async def get_winning_templates():
    """Get top-performing templates from the leaderboard."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.get_winning_templates()


@router.get("/awareness")
async def get_awareness_distribution():
    """Get awareness stage distribution of video pool."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.classify_pool_awareness()


@router.get("/competitor")
async def get_competitor_insights(username: str = ""):
    """Get competitor intelligence learnings."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.get_competitor_insights(username)


@router.get("/benchmarks")
async def get_benchmarks():
    """Get performance benchmarks vs competitors and industry."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.get_performance_benchmarks()


@router.get("/recommendations")
async def get_recommendations():
    """Get AI-generated daily content and strategy recommendations."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.get_ai_recommendations()


@router.post("/insights/apply")
async def apply_insights():
    """Apply InsightsEngine hook patterns and optimal posting times to schedule."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.apply_insights_to_schedule()


@router.post("/bandit/allocate")
async def bandit_allocate():
    """Run bandit allocation to dynamically weight content formats."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.apply_bandit_allocation()


@router.post("/mix/align")
async def align_content_mix():
    """Align schedule with ContentMixPlanner distribution targets."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.align_with_content_mix()


class ABTestRequest(BaseModel):
    platform: str = "tiktok"
    variation_type: str = "posting_time"
    variations: Optional[List[str]] = None

@router.post("/ab-test")
async def create_ab_test(request: ABTestRequest):
    """Create an A/B test for schedule slot configurations."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.create_slot_ab_test(request.platform, request.variation_type, request.variations)


@router.post("/ai/generate")
async def ai_generate_captions():
    """AI-generate captions for empty schedule slots."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.generate_content_for_empty_slots()


@router.post("/thumbnails/select")
async def select_thumbnails(limit: int = 10):
    """AI-select best thumbnails for videos in the pool."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.select_thumbnails_for_pool(limit=limit)


class SoraGenerateRequest(BaseModel):
    slot_day: str = "Monday"
    slot_platform: str = "tiktok"
    topic: str = ""

@router.post("/sora/generate")
async def generate_sora_video(request: SoraGenerateRequest):
    """Generate Sora AI video for a specific schedule slot."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.generate_ai_video_for_slot(request.slot_day, request.slot_platform, request.topic)


@router.post("/sleep/sync")
async def sync_sleep():
    """Sync SleepModeService with the adaptive post schedule."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.sync_sleep_schedule()


@router.post("/dco/optimize")
async def dco_optimize():
    """Run DCO creative combination optimization."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.optimize_creative_combinations()


@router.post("/engagement/trigger")
async def trigger_engagement(platform: str = "instagram", post_url: str = ""):
    """Trigger post-publish engagement orchestration."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.trigger_post_engagement(platform=platform, post_url=post_url)


@router.post("/pool/health")
async def check_pool_health():
    """Check video pool analysis health — flags under-analyzed content."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.check_pool_analysis_health()


@router.post("/pool/curate")
async def curate_pool():
    """Auto-curate video pool using sentiment, quality, and brand safety rules."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.curate_video_pool()


@router.post("/qa/check")
async def qa_check_all():
    """Run QA gate on all schedule slots (FATE, awareness, length, forbidden, CTA)."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.qa_gate_all_slots()


@router.post("/awareness/classify")
async def classify_awareness():
    """Classify video pool by awareness stage (1-5) for funnel coverage."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.classify_pool_awareness()


@router.post("/approval/submit")
async def submit_for_approval():
    """Submit high-stakes schedule slots for human approval."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.submit_schedule_for_approval()


@router.post("/learn/update")
async def trigger_learning():
    """Trigger template learning update — promote winners, demote losers."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.trigger_learning_update()


@router.post("/trend-intel/ingest")
async def ingest_trend_intel():
    """Ingest trend intelligence from the full trend pipeline."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.ingest_trend_intelligence()


@router.post("/sora-daily")
async def coordinate_sora_daily():
    """Coordinate daily Sora video generation pipeline with schedule needs."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.coordinate_sora_daily()


class ContentGenRequest(BaseModel):
    slot_index: int = 0
    awareness_level: int = 3
    offer_id: str = ""

@router.post("/content/generate")
async def generate_content_for_slot(request: ContentGenRequest):
    """Generate FATE-scored, awareness-aligned content for a specific slot."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.generate_content_for_slot(request.slot_index, request.awareness_level, request.offer_id)


# =========================================================================
# WAVE 5 ENDPOINTS
# =========================================================================

@router.get("/content-gaps")
async def get_content_gaps():
    """Analyze content gaps vs competitors — find missing themes."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.analyze_content_gaps()


@router.get("/inventory")
async def get_inventory():
    """Get content inventory status for long-horizon planning."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.sync_inventory_schedule()


@router.post("/hooks/inject")
async def inject_hooks():
    """Inject proven, high-performing hooks into schedule slots."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.inject_hooks_into_slots()


@router.post("/dedup/check")
async def check_dedup():
    """Run deduplication check on the current schedule."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.check_schedule_duplicates()


@router.post("/formats/classify")
async def classify_formats():
    """Auto-classify video pool by format (talking_head, broll, voiceover, etc.)."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.classify_pool_formats()


@router.post("/clips/select")
async def select_clips(limit: int = 5):
    """AI-select best video clips for schedule slots based on engagement signals."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.select_best_clips_for_slots(limit=limit)


@router.post("/offers/track")
async def track_offers():
    """Generate tracked offer URLs with UTM params for conversion attribution."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.generate_tracked_offer_links()


@router.post("/daily/sync")
async def sync_daily():
    """Sync DailyAutomationManager (Sora + Twitter) with adaptive schedule."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.sync_daily_automation()


@router.post("/checkbacks/schedule")
async def schedule_checkbacks():
    """Schedule post-publish metrics collection at 1h, 6h, 24h, 72h, 7d."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.schedule_checkbacks_for_published()


@router.post("/leads/discover")
async def discover_leads():
    """Discover new leads from hashtags, competitors, and engagement signals."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.discover_leads_for_outreach()


@router.post("/embeddings/generate")
async def generate_embeddings():
    """Generate semantic vector embeddings for pool videos (similarity search)."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.embed_pool_for_similarity()


@router.post("/meta-ads/coordinate")
async def coordinate_meta_ads():
    """Coordinate Meta Ads Autopilot with organic posting schedule."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.coordinate_meta_ads()


class RouteRequest(BaseModel):
    slot_index: int = 0
    platforms: Optional[List[str]] = None

@router.post("/route")
async def route_to_platforms(request: RouteRequest):
    """Route a schedule slot to multiple platforms via ChannelRouter."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.route_slot_to_platforms(request.slot_index, request.platforms)


@router.post("/email/trigger")
async def trigger_email():
    """Trigger email sequences for leads aligned with posting schedule."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.trigger_email_sequence_for_leads()


# =========================================================================
# WAVE 6: PUBLISHING & OPERATIONS
# =========================================================================

@router.post("/publish/due")
async def process_due_posts():
    """Process and publish all scheduled posts that are due NOW."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.process_due_posts()


@router.get("/calendar")
async def get_calendar(days: int = Query(default=7, ge=1, le=90)):
    """Get calendar view of upcoming scheduled posts."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.get_calendar_view(days=days)


@router.post("/nightly/analyze")
async def trigger_nightly_analysis():
    """Trigger nightly content analysis batch."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.run_nightly_analysis()


@router.post("/hydrate")
async def hydrate_dashboard():
    """Refresh all dashboard data sources."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.hydrate_dashboard_data()


@router.get("/trends/velocity")
async def get_trend_velocity():
    """Get trend velocity scores and accelerating trends."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.score_trending_content()


@router.get("/analytics/content")
async def get_content_analytics():
    """Get content performance analytics summary."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.track_content_performance()


@router.post("/touchpoints/check")
async def check_touchpoints():
    """Detect orphaned touchpoints missing attribution."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return await service.detect_orphaned_touchpoints()


@router.post("/twitter/campaigns")
async def sync_twitter_campaigns():
    """Sync Twitter campaigns with overall schedule."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.sync_twitter_campaigns()


@router.get("/queue/external")
async def get_external_queue():
    """Check external video submission queue status."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    return service.get_external_queue_status()


# =========================================================================
# MANUAL OVERRIDES
# =========================================================================

@router.post("/slot")
async def add_slot(request: SlotRequest):
    """Manually add a schedule slot."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    success = service.add_slot(request.dict())
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add slot")
    return {"success": True, "schedule": service.get_weekly_schedule()}


@router.put("/slot")
async def override_slot(request: SlotOverride):
    """Override an existing schedule slot."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    success = service.override_slot(request.day, request.platform, request.updates)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No slot found for {request.day}/{request.platform}"
        )
    return {"success": True, "schedule": service.get_weekly_schedule()}


@router.delete("/slot")
async def remove_slot(day: str, platform: str):
    """Remove a schedule slot."""
    from services.adaptive_scheduler_service import get_adaptive_scheduler
    service = get_adaptive_scheduler()
    success = service.remove_slot(day, platform)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No slot found for {day}/{platform}"
        )
    return {"success": True, "schedule": service.get_weekly_schedule()}
