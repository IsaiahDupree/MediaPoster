"""Legacy planner routes cannot materialize schedule rows outside Airtime."""
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.endpoints import adaptive_scheduler, experiments, narrative_builder, tiktok_repurpose


@pytest.mark.parametrize(
    "route,args",
    [
        (adaptive_scheduler.materialize_schedule, ()),
        (narrative_builder.schedule_seven_day_plan, (None,)),
        (narrative_builder.schedule_from_plan, ([],)),
        (experiments.schedule_experiment_variant, (None,)),
        (tiktok_repurpose.schedule_crossposts, (None,)),
        (tiktok_repurpose.run_full_pipeline, (None,)),
    ],
)
async def test_legacy_planner_routes_cannot_create_schedule_rows(route, args):
    with pytest.raises(HTTPException) as raised:
        await route(*args)
    assert raised.value.status_code == 409
    assert raised.value.detail["error"] == "airtime_required"
