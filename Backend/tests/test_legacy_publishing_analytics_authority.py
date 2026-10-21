"""Publishing analytics router cannot bypass Airtime or ScriptHub."""
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.endpoints import publishing_analytics


@pytest.mark.parametrize(
    "route,args,error_code",
    [
        (publishing_analytics.schedule_post, (None,), "airtime_required"),
        (publishing_analytics.reschedule_post, ("post-id", "2030-01-01T00:00:00Z"), "airtime_required"),
        (publishing_analytics.regenerate_content, ("post-id", None), "script_hub_required"),
    ],
)
async def test_legacy_schedule_and_generation_routes_fail_before_side_effects(route, args, error_code):
    with pytest.raises(HTTPException) as raised:
        await route(*args)
    assert raised.value.status_code == 409
    assert raised.value.detail["error"] == error_code
