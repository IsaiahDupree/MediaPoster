"""Real HTTP-boundary regression tests for the legacy Sora publisher."""
from pathlib import Path
import sys

import pytest
from aiohttp import web
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.adaptive_scheduler_service import AdaptiveSchedulerService
from services.sora_daily.pipeline_worker import SoraDailyPipelineWorker
from services.sora_daily.story_generator import StoryGenerator
from services.sora_daily.trend_prompts import TrendPromptLibrary
from services.sora_daily.daily_scheduler import DailySoraScheduler
from services.sora_daily.youtube_publisher import YouTubePublisher
from services.sora_daily.script_generator import SoraScriptGenerator
from services.safari_automation_orchestrator import SafariAutomationOrchestrator
from api.endpoints import safari_automation as safari_routes
from api.endpoints.adaptive_scheduler import coordinate_sora_daily as adaptive_sora_route
from api.endpoints import sora_daily as sora_routes


REQUEST_STATE = web.AppKey("request_state", dict)


@pytest.fixture
async def local_blotato_boundary(monkeypatch):
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
    port = site._server.sockets[0].getsockname()[1]
    monkeypatch.setenv("BLOTATO_URL", f"http://127.0.0.1:{port}")
    try:
        yield app[REQUEST_STATE]
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_sora_generation_and_adaptive_entrypoint_fail_closed(local_blotato_boundary):
    worker = object.__new__(SoraDailyPipelineWorker)
    worker_result = await worker.run_daily_pipeline()
    assert worker_result["error"] == "script_hub_required"

    scheduler = object.__new__(AdaptiveSchedulerService)
    scheduler_result = await scheduler.coordinate_sora_daily()
    assert scheduler_result["coordinated"] is False
    assert scheduler_result["error"] == "script_hub_required"
    assert local_blotato_boundary["count"] == 0


@pytest.mark.asyncio
async def test_youtube_publisher_never_generates_or_uploads_outside_governed_path(local_blotato_boundary):
    publisher = YouTubePublisher()

    metadata = await publisher.generate_metadata("prompt", "theme")
    single = await publisher.publish_single("video.mp4", "prompt", "theme")
    movie = await publisher.publish_movie(["video.mp4"], ["prompt"], "theme")
    upload = await publisher._upload_video("video.mp4", "title", "description", [])

    assert metadata["error"] == "script_hub_required"
    assert single["error"] == "airtime_required"
    assert movie["error"] == "airtime_required"
    assert upload["error"] == "airtime_required"
    assert local_blotato_boundary["count"] == 0


@pytest.mark.asyncio
async def test_adaptive_api_exposes_terminal_script_hub_contract(local_blotato_boundary):
    with pytest.raises(HTTPException) as raised:
        await adaptive_sora_route()

    assert raised.value.status_code == 409
    assert raised.value.detail["error"] == "script_hub_required"
    assert local_blotato_boundary["count"] == 0


@pytest.mark.parametrize(
    "route,args",
    [
        (sora_routes.start_daily_run, (None, None)),
        (sora_routes._generate_jobs_with_trends, (None,)),
        (sora_routes.resume_daily_run, ()),
        (sora_routes.retry_job, ("job-1", None)),
        (sora_routes.generate_single_prompt, ()),
        (sora_routes.generate_movie_arc, ()),
        (sora_routes.get_random_trend_content, ()),
        (sora_routes.generate_custom_trend_prompt, (None,)),
        (sora_routes.generate_scripts, (None, None)),
        (sora_routes._run_script_generation, ("job-1", "manual", 1, False, [])),
        (sora_routes.generate_scripts_sync, (None,)),
    ],
)
async def test_legacy_sora_generation_routes_fail_closed(route, args, local_blotato_boundary):
    with pytest.raises(HTTPException) as raised:
        await route(*args)

    assert raised.value.status_code == 409
    assert raised.value.detail["error"] == "script_hub_required"
    assert local_blotato_boundary["count"] == 0


@pytest.mark.parametrize(
    "route,args,error_code",
    [
        (safari_routes.queue_tweet, (None,), "script_hub_required"),
        (safari_routes.queue_sora_generation, (None,), "script_hub_required"),
        (safari_routes.process_video, (None,), "airtime_required"),
        (safari_routes.trigger_script_generation, (None, None), "script_hub_required"),
        (safari_routes.trigger_script_generation_sync, (None,), "script_hub_required"),
        (safari_routes.queue_script_for_scheduler, ("script-1",), "script_hub_required"),
        (safari_routes._run_safari_script_generation, ("job-1", "manual", 1, False, []), "script_hub_required"),
    ],
)
async def test_safari_automation_generation_and_distribution_routes_are_governed(route, args, error_code, local_blotato_boundary):
    with pytest.raises(HTTPException) as raised:
        await route(*args)

    assert raised.value.status_code == 409
    assert raised.value.detail["error"] == error_code
    assert local_blotato_boundary["count"] == 0


@pytest.mark.asyncio
async def test_sora_script_generator_public_methods_cannot_bypass_script_hub(local_blotato_boundary):
    generator = object.__new__(SoraScriptGenerator)
    calls = [
        generator.generate_from_live_trends(),
        generator.generate_from_descriptions(["trend"]),
        generator.generate_from_offers_and_trends(),
        generator.generate_from_collected_trends(),
        generator._generate_scripts_from_trends([], 1, False),
    ]

    for call in calls:
        with pytest.raises(RuntimeError, match="script_hub_required"):
            await call
    assert local_blotato_boundary["count"] == 0


@pytest.mark.asyncio
async def test_safari_orchestrator_cannot_run_legacy_video_or_publish_helpers(local_blotato_boundary):
    orchestrator = object.__new__(SafariAutomationOrchestrator)
    assert await orchestrator._schedule_tweet() is False
    assert await orchestrator._handle_tweet(None) == {"success": False, "error": "script_hub_required"}
    assert await orchestrator.queue_sora_generation("prompt") is False
    assert await orchestrator.process_downloaded_video("video.mp4") is False
    assert await orchestrator._queue_blotato_distribution("video.mp4") is False
    assert await orchestrator._handle_sora_generate(None) == {"success": False, "error": "script_hub_required"}
    assert await orchestrator._handle_blotato_post(None) == {"success": False, "error": "airtime_required"}
    assert local_blotato_boundary["count"] == 0


@pytest.mark.asyncio
async def test_legacy_sora_generator_and_scheduler_methods_cannot_bypass_script_hub(local_blotato_boundary):
    story = object.__new__(StoryGenerator)
    prompt_calls = [
        story.generate_single_prompt(),
        story.generate_movie_prompt(1, "theme"),
        story.generate_trend_prompt(),
        story.generate_trend_series(),
        story.generate_story_arc(),
    ]
    for call in prompt_calls:
        with pytest.raises(RuntimeError, match="script_hub_required"):
            await call

    trend_library = object.__new__(TrendPromptLibrary)
    with pytest.raises(RuntimeError, match="script_hub_required"):
        await trend_library.generate_custom_trend_prompt("trend")

    scheduler = object.__new__(DailySoraScheduler)
    with pytest.raises(RuntimeError, match="script_hub_required"):
        await scheduler.generate_daily_jobs(["trend"])
    assert local_blotato_boundary["count"] == 0
