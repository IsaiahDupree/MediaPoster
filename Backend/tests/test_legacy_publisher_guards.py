"""Real HTTP-boundary regressions for legacy publishers moved to Airtime."""
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import (
    bulk_scheduler,
    daily_publisher,
    direct_publish_test,
    full_workflow_ingest_analyze_publish,
    post_scheduler_monitor,
    publish_approved_videos,
    schedule_7_day_posts,
    schedule_test_videos,
    test_full_publish_flow,
    video_publish_tiktok,
)

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
    port = site._server.sockets[0].getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    old_monitor_url = post_scheduler_monitor.API_URL
    old_video_url = video_publish_tiktok.API_URL
    post_scheduler_monitor.API_URL = url
    video_publish_tiktok.API_URL = url
    try:
        yield {"url": url, "state": app[REQUEST_STATE]}
    finally:
        post_scheduler_monitor.API_URL = old_monitor_url
        video_publish_tiktok.API_URL = old_video_url
        await runner.cleanup()


@pytest.mark.asyncio
async def test_caption_and_schedule_helpers_fail_closed(local_provider_boundary):
    assert post_scheduler_monitor.generate_caption("content-1") is None
    assert post_scheduler_monitor.schedule_post(
        "content-1", "title", "caption", datetime.now(timezone.utc)
    ) is None
    assert video_publish_tiktok.generate_caption("content-1") is None
    result = video_publish_tiktok.publish_via_full_flow(
        "content-1", "710", "owner", "title", "caption"
    )
    assert result["status"] == "blocked"
    assert result["error"].startswith("airtime_required")
    assert local_provider_boundary["state"]["count"] == 0


@pytest.mark.asyncio
async def test_bulk_scheduler_blocks_provider_write_but_keeps_local_preview(local_provider_boundary):
    entry = bulk_scheduler.ScheduleEntry(
        media=bulk_scheduler.MediaItem(path="/tmp/source.mp4", filename="source.mp4"),
        platform="tiktok",
        account_id="710",
        account_username="owner",
        scheduled_time=None,
        caption="Approved supplied copy",
    )

    with pytest.raises(bulk_scheduler.AirtimeRequiredError, match="airtime_required"):
        await bulk_scheduler.schedule_entries([entry], api=None, dry_run=False)

    preview = await bulk_scheduler.schedule_entries([entry], api=None, dry_run=True)

    assert preview.total == 1
    assert preview.scheduled == 0
    assert preview.entries[0]["status"] == "dry_run"
    assert preview.entries[0]["scheduled"] is None
    assert local_provider_boundary["state"]["count"] == 0


def test_legacy_tiktok_cli_exits_before_reading_or_writing():
    assert video_publish_tiktok.main() == 2
    assert post_scheduler_monitor.main() == 2


def test_bulk_scheduler_cli_rejects_non_dry_run_before_media_or_provider_access():
    script = Path(__file__).resolve().parents[2] / "Backend/scripts/bulk_scheduler.py"
    result = subprocess.run(
        [sys.executable, str(script), "--source", "/missing", "--platform", "tiktok", "--account", "710"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    assert "airtime_required" in result.stdout


@pytest.mark.parametrize(
    "script_name",
    [
        "publish_approved_videos.py",
        "full_workflow_ingest_analyze_publish.py",
        "direct_publish_test.py",
        "test_full_publish_flow.py",
    ],
)
def test_additional_legacy_publish_clis_exit_before_io(script_name):
    script = Path(__file__).resolve().parents[1] / "scripts" / script_name
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    assert any(marker in result.stdout + result.stderr for marker in ("airtime_required", "script_hub_required"))


def test_legacy_generation_and_content_write_helpers_cannot_bypass_authority():
    assert direct_publish_test.generate_caption("content-1") is None
    assert publish_approved_videos.generate_title_caption("content-1", {}) is None
    assert publish_approved_videos.publish_video("content-1", "title", "caption")["error"] == "airtime_required"
    with pytest.raises(RuntimeError, match="script_hub_required"):
        full_workflow_ingest_analyze_publish.generate_platform_content("content-1", {})
    with pytest.raises(RuntimeError, match="script_hub_required"):
        full_workflow_ingest_analyze_publish.save_platform_content("content-1", {})
    with pytest.raises(RuntimeError, match="script_hub_required"):
        test_full_publish_flow.generate_content_for_video("content-1")
    assert test_full_publish_flow.publish_to_tiktok("content-1", "title", "copy", [], 710)["error"] == "airtime_required"


@pytest.mark.parametrize(
    "script_name",
    ["schedule_test_videos.py", "schedule_7_day_posts.py", "daily_publisher.py"],
)
def test_additional_legacy_scheduler_clis_exit_before_service_or_queue_access(script_name):
    script = Path(__file__).resolve().parents[1] / "scripts" / script_name
    result = subprocess.run(
        [sys.executable, str(script), "--keep-alive"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    assert "airtime_required" in result.stdout + result.stderr


@pytest.mark.asyncio
async def test_legacy_scheduler_helpers_do_not_create_queue_rows_or_generic_copy():
    assert schedule_test_videos.get_caption_from_analysis({}, "instagram") is None
    assert await schedule_test_videos.schedule_video(None, {"media_id": "1", "filename": "x"}, datetime.now(timezone.utc)) is False
    account = schedule_7_day_posts.BlotatoAccount(blotato_id=710, username="owner", platform="tiktok")
    assert schedule_7_day_posts.schedule_post(None, {"id": "1"}, "tiktok", account, datetime.now(timezone.utc)) is False


def test_daily_publisher_object_cannot_start_services_or_trigger_delivery():
    publisher = daily_publisher.DailyPublisher()
    assert publisher.run() is False
    assert publisher.trigger_publish() is False
    assert publisher.backend_started is False
    assert publisher.supabase_started is False
