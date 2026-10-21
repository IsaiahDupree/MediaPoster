"""Real HTTP-boundary tests for legacy Twitter campaign writers."""
from pathlib import Path
import sys

import pytest
from aiohttp import web
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.twitter_campaign_service import TwitterCampaignService
from services.daily_automation.twitter_scheduler import TwitterOfferScheduler
from services.twitter_campaign_scheduler import TwitterCampaignScheduler
from services.tweet_scheduler import TweetScheduler
from services.event_bus import Event, EventBus
from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.workers.twitter_campaign_worker import TwitterCampaignWorker
from routers import twitter_campaign as twitter_routes

REQUEST_STATE = web.AppKey("request_state", dict)


@pytest.fixture
async def local_provider_boundary():
    async def record(request):
        request.app[REQUEST_STATE]["count"] += 1
        return web.json_response({"accepted": True})

    app = web.Application()
    app[REQUEST_STATE] = {"count": 0}
    app.router.add_route("*", "/{tail:.*}", record)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    try:
        yield app[REQUEST_STATE]
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_legacy_twitter_campaign_service_cannot_generate_schedule_or_publish(local_provider_boundary):
    service = object.__new__(TwitterCampaignService)

    with pytest.raises(RuntimeError, match="script_hub_required"):
        service.generate_tweet(None, None, None)
    with pytest.raises(RuntimeError, match="script_hub_required"):
        service.generate_batch_tweets(None)
    with pytest.raises(RuntimeError, match="airtime_required"):
        service.schedule_tweets([])
    assert (await service.post_tweet({"tweet_text": "copy"}))["error"] == "airtime_required"
    with pytest.raises(RuntimeError, match="script_hub_required"):
        await service.run_daily_campaign()
    with pytest.raises(RuntimeError, match="script_hub_required"):
        service.generate_offer_tweet("https://example.invalid", "offer")
    with pytest.raises(RuntimeError, match="airtime_required"):
        service.schedule_offer_tweets("https://example.invalid", "offer")
    assert (await service.process_due_tweets())["error"] == "airtime_required"
    with pytest.raises(RuntimeError, match="script_hub_required"):
        service.schedule_campaign("theme")

    assert local_provider_boundary["count"] == 0


@pytest.mark.asyncio
async def test_legacy_twitter_offer_scheduler_cannot_start_generate_or_post(local_provider_boundary):
    scheduler = object.__new__(TwitterOfferScheduler)
    with pytest.raises(RuntimeError, match="script_hub_required"):
        await scheduler.start()
    with pytest.raises(RuntimeError, match="script_hub_required"):
        await scheduler._posting_loop()
    with pytest.raises(RuntimeError, match="script_hub_required"):
        await scheduler._post_offer()
    with pytest.raises(RuntimeError, match="script_hub_required"):
        await scheduler._generate_offer_tweet(None, {})
    assert await scheduler._post_to_twitter("copy") is False
    assert await scheduler._post_to_twitter_fallback("copy") is False
    assert local_provider_boundary["count"] == 0


@pytest.mark.asyncio
async def test_legacy_campaign_scheduler_cannot_start_or_run_db_polling_loop(local_provider_boundary):
    scheduler = object.__new__(TwitterCampaignScheduler)
    with pytest.raises(RuntimeError, match="airtime_required"):
        await scheduler.start()
    with pytest.raises(RuntimeError, match="airtime_required"):
        await scheduler._run_loop()
    assert local_provider_boundary["count"] == 0


@pytest.mark.asyncio
async def test_legacy_tweet_scheduler_cannot_claim_campaign_or_create_delayed_posts(local_provider_boundary):
    scheduler = object.__new__(TweetScheduler)
    with pytest.raises(RuntimeError, match="airtime_required"):
        await scheduler.schedule_tweet_campaign("pipeline-1", "theme")
    with pytest.raises(RuntimeError, match="airtime_required"):
        await scheduler._schedule_tweet_event({})
    with pytest.raises(RuntimeError, match="airtime_required"):
        await scheduler._post_tweet_delayed({}, 0)
    with pytest.raises(RuntimeError, match="airtime_required"):
        await scheduler._post_tweet({})
    with pytest.raises(RuntimeError, match="script_hub_required"):
        scheduler._build_tweet_text({"theme": "unapproved theme"})
    assert local_provider_boundary["count"] == 0


@pytest.mark.asyncio
async def test_script_hub_block_is_propagated_as_pipeline_failure(local_provider_boundary):
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    orchestrator = MasterOrchestrator(event_bus=bus, use_db=False)
    orchestrator.active_pipelines["pipeline-1"] = {
        "pipeline_id": "pipeline-1",
        "config": PipelineConfig(theme="test", schedule_tweets=True),
        "correlation_id": "correlation-1",
        "current_step": "twitter_campaign",
        "outputs": {},
    }
    worker = TwitterCampaignWorker(event_bus=bus)
    await worker._handle_schedule_request(Event(
        topic="twitter.campaign.schedule_requested",
        payload={"pipeline_id": "pipeline-1", "theme": "test"},
        correlation_id="correlation-1",
    ))

    failed = orchestrator.completed_pipelines["pipeline-1"]
    assert failed["status"] == "failed"
    assert "script_hub_required" in failed["error"]
    assert "pipeline-1" not in orchestrator.active_pipelines
    assert local_provider_boundary["count"] == 0


@pytest.mark.parametrize(
    "route,args,error_code",
    [
        (twitter_routes.start_scheduler, (), "airtime_required"),
        (twitter_routes.generate_tweets, (twitter_routes.GenerateTweetsRequest(count=5), None), "script_hub_required"),
        (twitter_routes.schedule_tweets, (twitter_routes.ScheduleTweetsRequest(tweets=[]),), "airtime_required"),
        (twitter_routes.run_daily_campaign, (None,), "script_hub_required"),
        (twitter_routes.process_due_tweets, (), "airtime_required"),
    ],
)
async def test_legacy_campaign_write_routes_return_migration_contract(route, args, error_code, local_provider_boundary):
    with pytest.raises(HTTPException) as raised:
        await route(*args)
    assert raised.value.status_code == 409
    assert raised.value.detail["error"] == error_code
    assert local_provider_boundary["count"] == 0
