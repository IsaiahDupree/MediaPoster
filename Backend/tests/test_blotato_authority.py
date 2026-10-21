"""Regression tests for legacy Blotato write endpoints in MediaPoster."""
from pathlib import Path
import sys

import pytest
from aiohttp import web
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import blotato_router as routes

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


@pytest.mark.parametrize(
    "route,args,error_code",
    [
        (routes.publish_post, (routes.PublishPostRequest(account_id="a", text="copy", platform="twitter"),), "airtime_required"),
        (routes.publish_to_multiple_platforms, (routes.MultiPlatformPostRequest(account_ids={"twitter": "a"}, text="copy", platforms=["twitter"]),), "airtime_required"),
        (routes.bulk_publish, (routes.BulkPublishRequest(accounts=[routes.AccountPublishItem(blotato_account_id="a", platform="twitter", username="owner", text="copy")]),), "airtime_required"),
        (routes.full_publish, (routes.FullPublishRequest(media_id="m", blotato_account_id="a", platform="twitter", username="owner", text="copy"), None), "airtime_required"),
        (routes.full_publish_with_tracking, (routes.FullPublishWithTrackingRequest(media_id="m", blotato_account_id="a", platform="twitter", username="owner", text="copy"),), "airtime_required"),
        (routes.upload_media, (routes.UploadMediaRequest(url="https://example.invalid/media.mp4"),), "airtime_required"),
        (routes.create_video, (routes.CreateVideoRequest(script="approved script"),), "foundry_required"),
        (routes.create_pov_video, ("approved script",), "foundry_required"),
        (routes.create_slideshow_video, ([{"text": "slide"}],), "foundry_required"),
        (routes.create_narrated_video, ("approved script",), "foundry_required"),
        (routes.delete_video, ("video-1",), "foundry_required"),
    ],
)
async def test_mounted_blotato_mutations_fail_closed(route, args, error_code, local_provider_boundary):
    with pytest.raises(HTTPException) as raised:
        await route(*args)
    assert raised.value.status_code == 409
    assert raised.value.detail["error"] == error_code
    assert local_provider_boundary["count"] == 0
