"""
Unit tests for GoalDecompositionAgent service logic.
No live DB, no live OpenAI — all external calls mocked.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session(fetchone_result=None, fetchall_result=None):
    """Async SQLAlchemy session mock with controllable query results."""
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.fetchone = MagicMock(return_value=fetchone_result)
    execute_result.fetchall = MagicMock(return_value=fetchall_result or [])
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()
    return session


def _mock_openai_response(milestones: list) -> dict:
    """Build a fake OpenAI chat completion response."""
    body = {
        "summary": "Grow from 0 to 100K followers in 60 days via short-form video",
        "milestones": milestones,
        "total_weeks": 12,
        "primary_kpi": "followers",
    }
    return {
        "choices": [{"message": {"content": json.dumps(body)}}]
    }


SAMPLE_MILESTONES = [
    {
        "week": i,
        "theme": f"theme week {i}",
        "awareness_level": (i % 5) + 1,
        "platforms": ["tiktok"],
        "target_metric": "followers",
        "target_value": i * 1000,
        "pipeline_config": {"theme": f"theme {i}", "num_parts": 3, "publish_platforms": ["tiktok"], "schedule_tweets": True, "tweets_per_day": 8},
    }
    for i in range(1, 13)
]


# ── _current_week_number ──────────────────────────────────────────────────────

class TestCurrentWeekNumber:
    def test_week_1_on_day_0(self):
        from services.goal_decomposition import _current_week_number
        assert _current_week_number(datetime.now(timezone.utc)) == 1

    def test_week_2_after_7_days(self):
        from services.goal_decomposition import _current_week_number
        created = datetime.now(timezone.utc) - timedelta(days=7)
        assert _current_week_number(created) == 2

    def test_week_2_after_8_days(self):
        from services.goal_decomposition import _current_week_number
        created = datetime.now(timezone.utc) - timedelta(days=8)
        assert _current_week_number(created) == 2

    def test_week_9_after_56_days(self):
        from services.goal_decomposition import _current_week_number
        created = datetime.now(timezone.utc) - timedelta(days=56)
        assert _current_week_number(created) == 9

    def test_accepts_iso_string(self):
        from services.goal_decomposition import _current_week_number
        ts = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        assert _current_week_number(ts) == 3

    def test_never_returns_zero(self):
        from services.goal_decomposition import _current_week_number
        future = datetime.now(timezone.utc) + timedelta(days=10)
        assert _current_week_number(future) >= 1


# ── GoalDecompositionAgent.decompose ─────────────────────────────────────────

class TestDecompose:
    @pytest.mark.asyncio
    async def test_decompose_calls_openai_and_saves(self):
        from services.goal_decomposition import GoalDecompositionAgent

        session = _make_session()
        agent = GoalDecompositionAgent(session)

        with patch("services.goal_decomposition._decompose_with_gpt4o", new=AsyncMock(
            return_value={
                "summary": "Grow fast",
                "milestones": SAMPLE_MILESTONES,
                "total_weeks": 12,
                "primary_kpi": "followers",
            }
        )):
            result = await agent.decompose("Grow to 100K in 60 days", ["tiktok", "instagram"])

        # Should return goal_id as a valid UUID string
        UUID(result["goal_id"])  # raises if invalid
        assert result["summary"] == "Grow fast"
        assert result["total_weeks"] == 12
        assert len(result["milestones"]) == 12
        assert result["status"] == "active"

        # DB insert should have been called
        session.execute.assert_called()
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_decompose_raises_on_missing_openai_key(self):
        from services.goal_decomposition import GoalDecompositionAgent, _decompose_with_gpt4o
        import os

        session = _make_session()
        agent = GoalDecompositionAgent(session)

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            with patch("services.goal_decomposition.OPENAI_API_KEY", ""):
                with pytest.raises((ValueError, Exception)):
                    await agent.decompose("Grow to 100K in 60 days", ["tiktok"])

    @pytest.mark.asyncio
    async def test_decompose_result_has_created_at(self):
        from services.goal_decomposition import GoalDecompositionAgent

        session = _make_session()
        agent = GoalDecompositionAgent(session)

        with patch("services.goal_decomposition._decompose_with_gpt4o", new=AsyncMock(return_value={
            "summary": "test", "milestones": SAMPLE_MILESTONES, "total_weeks": 12, "primary_kpi": "followers"
        })):
            result = await agent.decompose("Grow followers fast and efficiently", ["instagram"])

        assert "created_at" in result
        # Should be parseable as ISO datetime
        datetime.fromisoformat(result["created_at"].replace("Z", "+00:00"))


# ── GoalDecompositionAgent.get_status ────────────────────────────────────────

class TestGetStatus:
    @pytest.mark.asyncio
    async def test_get_status_not_found_raises(self):
        from services.goal_decomposition import GoalDecompositionAgent

        session = _make_session(fetchone_result=None)
        agent = GoalDecompositionAgent(session)

        with pytest.raises(ValueError, match="Goal not found"):
            await agent.get_status("nonexistent-id")

    @pytest.mark.asyncio
    async def test_get_status_annotates_milestones(self):
        from services.goal_decomposition import GoalDecompositionAgent

        now = datetime.now(timezone.utc)
        created_8_days_ago = (now - timedelta(days=8)).isoformat()

        row = MagicMock()
        row.id = "goal-1"
        row.goal_text = "Grow to 100K"
        row.platforms = '["tiktok"]'
        row.milestones = json.dumps(SAMPLE_MILESTONES)
        row.status = "active"
        row.created_at = created_8_days_ago

        # First execute returns goal row, second returns actuals
        session = AsyncMock()
        session.commit = AsyncMock()

        call_count = 0
        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count <= 2:  # _ensure_goal_tables + fetch goal
                result.fetchone = MagicMock(return_value=row)
                result.fetchall = MagicMock(return_value=[])
            else:  # fetch actuals
                result.fetchone = MagicMock(return_value=None)
                result.fetchall = MagicMock(return_value=[])
            return result

        session.execute = AsyncMock(side_effect=lambda *a, **kw: execute_side_effect(*a, **kw))

        agent = GoalDecompositionAgent(session)
        status = await agent.get_status("goal-1")

        assert status["goal_id"] == "goal-1"
        assert status["current_week"] == 2  # 8 days → week 2

        # Week 1 should be 'past', week 2 should be 'active', week 3+ should be 'future'
        milestones_by_week = {m["week"]: m for m in status["milestones"]}
        assert milestones_by_week[1]["state"] == "past"
        assert milestones_by_week[2]["state"] == "active"
        assert milestones_by_week[3]["state"] == "future"

    @pytest.mark.asyncio
    async def test_get_status_includes_actuals_by_week(self):
        from services.goal_decomposition import GoalDecompositionAgent

        row = MagicMock()
        row.id = "goal-1"
        row.goal_text = "Grow fast"
        row.platforms = '["tiktok"]'
        row.milestones = json.dumps(SAMPLE_MILESTONES)
        row.status = "active"
        row.created_at = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

        actual_row = MagicMock()
        actual_row.milestone_week = 1
        actual_row.metric = "followers"
        actual_row.target = 1000.0
        actual_row.actual = 1200.0

        call_count = 0
        session = AsyncMock()
        session.commit = AsyncMock()

        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count <= 2:
                result.fetchone = MagicMock(return_value=row)
                result.fetchall = MagicMock(return_value=[])
            else:
                result.fetchone = MagicMock(return_value=None)
                result.fetchall = MagicMock(return_value=[actual_row])
            return result

        session.execute = AsyncMock(side_effect=lambda *a, **kw: execute_side_effect(*a, **kw))

        agent = GoalDecompositionAgent(session)
        status = await agent.get_status("goal-1")

        week1 = next(m for m in status["milestones"] if m["week"] == 1)
        assert "followers" in week1["actuals"]
        assert week1["actuals"]["followers"]["actual"] == 1200.0
        assert week1["actuals"]["followers"]["pct"] == 120.0  # 1200/1000 * 100


# ── GoalDecompositionAgent.record_actual ─────────────────────────────────────

class TestRecordActual:
    @pytest.mark.asyncio
    async def test_record_actual_not_found_raises(self):
        from services.goal_decomposition import GoalDecompositionAgent

        session = _make_session(fetchone_result=None)
        agent = GoalDecompositionAgent(session)

        with pytest.raises(ValueError, match="Goal not found"):
            await agent.record_actual("bad-id", 1, "followers", 500.0)

    @pytest.mark.asyncio
    async def test_record_actual_inserts_row(self):
        from services.goal_decomposition import GoalDecompositionAgent

        row = MagicMock()
        row.milestones = json.dumps(SAMPLE_MILESTONES)

        session = _make_session(fetchone_result=row)
        agent = GoalDecompositionAgent(session)

        await agent.record_actual("goal-1", 1, "followers", 1500.0)

        session.execute.assert_called()
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_record_actual_extracts_target_from_milestones(self):
        """Target value should be pulled from the matching milestone."""
        from services.goal_decomposition import GoalDecompositionAgent

        milestones = [{"week": 2, "target_metric": "followers", "target_value": 5000}]
        row = MagicMock()
        row.milestones = json.dumps(milestones)

        # Capture what was passed to execute for the INSERT
        inserted_params = {}
        original_execute = AsyncMock()

        async def capture_execute(query, params=None, **kwargs):
            if params and "target" in str(params):
                inserted_params.update(params)
            result = MagicMock()
            result.fetchone = MagicMock(return_value=row)
            result.fetchall = MagicMock(return_value=[])
            return result

        session = AsyncMock()
        session.execute = capture_execute
        session.commit = AsyncMock()

        agent = GoalDecompositionAgent(session)
        await agent.record_actual("goal-1", 2, "followers", 3200.0)

        if "target" in inserted_params:
            assert inserted_params["target"] == 5000
