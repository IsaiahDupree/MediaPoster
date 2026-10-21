"""Mounted legacy social publishing and queue APIs fail closed."""
from pathlib import Path
import inspect
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.endpoints import platform_publishing, publishing, publishing_queue, twitter_api


@pytest.mark.parametrize(
    "route,args",
    [
        (platform_publishing.publish_video, (None,)),
        (twitter_api.publish_tweet, (None, None)),
        (twitter_api.publish_thread, (None, None)),
        (publishing.schedule_post, (None, None)),
        (publishing_queue.add_to_queue, (None,)),
        (publishing_queue.bulk_schedule, (None,)),
        (publishing_queue.retry_item, ("id",)),
        (publishing_queue.reschedule_item, ("id", None)),
        (publishing_queue.cancel_item, ("id",)),
    ],
)
async def test_legacy_social_write_routes_return_airtime_required(route, args):
    with pytest.raises(HTTPException) as raised:
        if inspect.iscoroutinefunction(route):
            await route(*args)
        else:
            route(*args)
    assert raised.value.status_code == 409
    assert raised.value.detail["error"] == "airtime_required"


@pytest.mark.parametrize(
    "route,args",
    [
        (publishing_queue.get_publishing_queue, ()),
        (publishing_queue.get_publishing_analytics, ()),
        (publishing_queue.process_queue, ()),
    ],
)
def test_legacy_queue_stubs_do_not_report_fabricated_success(route, args):
    with pytest.raises(HTTPException) as raised:
        route(*args)
    assert raised.value.status_code == 501
    assert raised.value.detail["error"] == "capability_unavailable"
