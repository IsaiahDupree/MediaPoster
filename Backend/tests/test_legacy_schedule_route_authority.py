"""Legacy mounted scheduling routes must not bypass canonical Airtime."""
from pathlib import Path
import inspect
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.endpoints import external_scheduling, schedule


ROUTES = [
    (schedule.create_scheduled_post, (None,)),
    (schedule.update_scheduled_post, ("post-id", None)),
    (schedule.delete_scheduled_post, ("post-id",)),
    (schedule.reschedule_post, ("post-id", "2030-01-01T00:00:00Z")),
    (schedule.record_posted_content, (None,)),
    (schedule.publish_now, (None,)),
    (schedule.publish_scheduled_post, ("post-id",)),
    (schedule.process_due_posts_now, ()),
    (external_scheduling.submit_video, (None, None)),
    (external_scheduling.bulk_schedule_videos, (None,)),
    (external_scheduling.smart_schedule_video, (None,)),
    (external_scheduling.smart_bulk_schedule, (None,)),
]


@pytest.mark.parametrize("route,args", ROUTES)
async def test_mounted_legacy_schedule_writes_fail_before_side_effects(route, args):
    with pytest.raises(HTTPException) as raised:
        if inspect.iscoroutinefunction(route):
            await route(*args)
        else:
            route(*args)
    assert raised.value.status_code == 409
    assert raised.value.detail["error"] == "airtime_required"


def test_legacy_schedule_helper_is_disabled_before_database_access():
    with pytest.raises(HTTPException) as raised:
        external_scheduling.create_scheduled_post(
            content_id="content",
            platform="instagram",
            account_id="account",
            scheduled_at="2030-01-01T00:00:00Z",
            title="title",
            caption="caption",
            hashtags=[],
        )
    assert raised.value.status_code == 409
    assert raised.value.detail["error"] == "airtime_required"
