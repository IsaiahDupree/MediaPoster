"""
Tests for PRD-06 Agent Orchestration features.
Covers: GoalDecompositionAgent, CrossPipelineLearningService, AgentBudgetEnforcer, API endpoints.
Uses FastAPI TestClient — no live server required.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ── Pure unit tests (no DB, no HTTP) ─────────────────────────────────────────

class TestGoalDecompositionPure:
    def test_current_week_number_day_zero(self):
        """A goal created just now is on week 1."""
        from services.goal_decomposition import _current_week_number
        now = datetime.now(timezone.utc)
        assert _current_week_number(now) == 1

    def test_current_week_number_week_two(self):
        """A goal created 8 days ago is on week 2."""
        from services.goal_decomposition import _current_week_number
        from datetime import timedelta
        created = datetime.now(timezone.utc) - timedelta(days=8)
        assert _current_week_number(created) == 2

    def test_current_week_number_string_input(self):
        """Accepts ISO string timestamp."""
        from services.goal_decomposition import _current_week_number
        ts = datetime.now(timezone.utc).isoformat()
        assert _current_week_number(ts) == 1


class TestBudgetEnforcerPure:
    """Test BudgetHaltError is importable and budget math is correct."""

    def test_budget_halt_error_is_exception(self):
        from services.agent_budget_enforcer import BudgetHaltError
        err = BudgetHaltError("test")
        assert isinstance(err, Exception)
        assert "test" in str(err)

    def test_daily_budget_default_from_env(self):
        import os
        from services.agent_budget_enforcer import DAILY_BUDGET_USD
        expected = float(os.environ.get("AGENT_DAILY_BUDGET_USD", "10.0"))
        assert DAILY_BUDGET_USD == expected


# ── API endpoint tests (TestClient + mocked services) ─────────────────────────

@pytest.fixture
def client():
    """FastAPI TestClient with get_db dependency overridden (no real DB needed)."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.endpoints.orchestrator_goals import router
    from database.connection import get_db

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(
        fetchone=MagicMock(return_value=None),
        fetchall=MagicMock(return_value=[]),
    ))
    mock_session.commit = AsyncMock()

    async def override_get_db():
        yield mock_session

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


class TestDecomposeGoalEndpoint:
    def test_decompose_requires_goal(self, client):
        resp = client.post("/api/orchestrator/goals/decompose", json={"goal": "x", "platforms": ["tiktok"]})
        # goal too short (min_length=10)
        assert resp.status_code == 422

    def test_decompose_valid_schema(self, client):
        with patch("api.endpoints.orchestrator_goals.GoalDecompositionAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.decompose = AsyncMock(return_value={
                "goal_id": "test-id",
                "summary": "Grow followers fast",
                "total_weeks": 12,
                "primary_kpi": "followers",
                "milestones": [{"week": 1, "theme": "test", "pipeline_config": {}}],
                "status": "active",
                "created_at": "2026-03-05T00:00:00Z",
            })
            resp = client.post("/api/orchestrator/goals/decompose", json={
                "goal": "Grow to 100K followers in 60 days",
                "platforms": ["tiktok", "instagram"],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["goal_id"] == "test-id"
        assert len(data["data"]["milestones"]) == 1

    def test_decompose_handles_openai_error(self, client):
        with patch("api.endpoints.orchestrator_goals.GoalDecompositionAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.decompose = AsyncMock(side_effect=ValueError("OPENAI_API_KEY not set"))
            resp = client.post("/api/orchestrator/goals/decompose", json={
                "goal": "Grow to 100K followers in 60 days",
                "platforms": ["tiktok"],
            })
        assert resp.status_code == 400
        assert "OPENAI_API_KEY" in resp.json()["detail"]


class TestGoalStatusEndpoint:
    def test_goal_status_not_found(self, client):
        with patch("api.endpoints.orchestrator_goals.GoalDecompositionAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.get_status = AsyncMock(side_effect=ValueError("Goal not found: bad-id"))
            resp = client.get("/api/orchestrator/goals/bad-id/status")
        assert resp.status_code == 404

    def test_goal_status_returns_milestones(self, client):
        with patch("api.endpoints.orchestrator_goals.GoalDecompositionAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.get_status = AsyncMock(return_value={
                "goal_id": "g1",
                "goal_text": "Grow fast",
                "platforms": ["tiktok"],
                "status": "active",
                "current_week": 2,
                "milestones": [{"week": 1, "state": "past", "actuals": {}}, {"week": 2, "state": "active", "actuals": {}}],
            })
            resp = client.get("/api/orchestrator/goals/g1/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_week"] == 2
        assert len(data["milestones"]) == 2


class TestGoalActualsEndpoint:
    def test_record_actual_valid(self, client):
        with patch("api.endpoints.orchestrator_goals.GoalDecompositionAgent") as MockAgent:
            instance = MockAgent.return_value
            instance.record_actual = AsyncMock()
            resp = client.post("/api/orchestrator/goals/g1/actuals", json={
                "milestone_week": 2, "metric": "followers", "actual": 1500.0
            })
        assert resp.status_code == 200
        assert "week 2" in resp.json()["message"]

    def test_record_actual_rejects_negative(self, client):
        resp = client.post("/api/orchestrator/goals/g1/actuals", json={
            "milestone_week": 1, "metric": "followers", "actual": -1
        })
        assert resp.status_code == 422


class TestLearningsEndpoint:
    def test_learnings_returns_context(self, client):
        with patch("api.endpoints.orchestrator_goals.CrossPipelineLearningService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_learnings_context = AsyncMock(return_value={
                "context": "• Best themes: AI automation (7.2% CTR)\n• Awareness level 2 drives most reach",
                "generated_at": "2026-03-05T10:00:00Z",
            })
            resp = client.get("/api/orchestrator/learnings")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "AI automation" in data["context"]


class TestPipelineVariantsEndpoint:
    def test_variants_requires_1_to_10(self, client):
        resp = client.post("/api/orchestrator/pipeline/variants", json={
            "base_theme": "AI content creation",
            "variants": [],  # empty — invalid
        })
        assert resp.status_code == 400

    def test_variants_ranked_by_score(self, client):
        with patch("api.endpoints.orchestrator_goals.CrossPipelineLearningService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_learnings_context = AsyncMock(return_value={"context": "", "generated_at": None})
            resp = client.post("/api/orchestrator/pipeline/variants", json={
                "base_theme": "AI content creation",
                "variants": [
                    {"awareness_level": 1},
                    {"awareness_level": 3},
                    {"awareness_level": 5},
                ],
                "platforms": ["tiktok"],
            })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["variant_count"] == 3
        # awareness 3 should score highest (0.8)
        assert data["recommended_variant"] is not None
        scores = [v["predicted_score"] for v in data["variants"]]
        assert scores == sorted(scores, reverse=True)  # must be ranked desc

    def test_variants_first_is_recommended(self, client):
        with patch("api.endpoints.orchestrator_goals.CrossPipelineLearningService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_learnings_context = AsyncMock(return_value={"context": "", "generated_at": None})
            resp = client.post("/api/orchestrator/pipeline/variants", json={
                "base_theme": "test",
                "variants": [{"awareness_level": 2}, {"awareness_level": 4}],
            })
        variants = resp.json()["data"]["variants"]
        assert variants[0]["status"] == "recommended"
        for v in variants[1:]:
            assert v["status"] == "pending"


class TestBudgetEndpoints:
    def test_budget_status_ok(self, client):
        with patch("api.endpoints.orchestrator_goals.AgentBudgetEnforcer") as MockEnf:
            instance = MockEnf.return_value
            instance.get_today_spend = AsyncMock(return_value=2.5)
            instance.daily_limit = 10.0
            resp = client.get("/api/orchestrator/budget/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["spent_usd"] == 2.5
        assert data["status"] == "ok"
        assert data["pct_used"] == 25.0

    def test_budget_status_warning_at_80pct(self, client):
        with patch("api.endpoints.orchestrator_goals.AgentBudgetEnforcer") as MockEnf:
            instance = MockEnf.return_value
            instance.get_today_spend = AsyncMock(return_value=8.5)
            instance.daily_limit = 10.0
            resp = client.get("/api/orchestrator/budget/status")
        assert resp.json()["data"]["status"] == "warning"

    def test_budget_status_halt_at_100pct(self, client):
        with patch("api.endpoints.orchestrator_goals.AgentBudgetEnforcer") as MockEnf:
            instance = MockEnf.return_value
            instance.get_today_spend = AsyncMock(return_value=11.0)
            instance.daily_limit = 10.0
            resp = client.get("/api/orchestrator/budget/status")
        assert resp.json()["data"]["status"] == "halt"

    def test_record_spend_rejects_zero(self, client):
        resp = client.post("/api/orchestrator/budget/record-spend", json={"amount_usd": 0, "agent_name": "test"})
        assert resp.status_code == 422

    def test_record_spend_valid(self, client):
        with patch("api.endpoints.orchestrator_goals.AgentBudgetEnforcer") as MockEnf:
            instance = MockEnf.return_value
            instance.record_spend = AsyncMock()
            resp = client.post("/api/orchestrator/budget/record-spend", json={"amount_usd": 0.05, "agent_name": "narrative"})
        assert resp.status_code == 200
        assert resp.json()["recorded_usd"] == 0.05


class TestRecordPipelineResult:
    def test_record_valid(self, client):
        with patch("api.endpoints.orchestrator_goals.CrossPipelineLearningService") as MockSvc:
            instance = MockSvc.return_value
            instance.record_pipeline_result = AsyncMock(return_value="row-id-123")
            resp = client.post("/api/orchestrator/pipeline/record", json={
                "pipeline_id": "pipe-1",
                "theme": "AI automation saves time",
                "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
                "awareness_level": 2,
                "platform": "tiktok",
                "published_count": 5,
                "engagement_at_24h": 1250.0,
            })
        assert resp.status_code == 200
        assert resp.json()["result_id"] == "row-id-123"

    def test_record_rejects_invalid_awareness(self, client):
        with patch("api.endpoints.orchestrator_goals.CrossPipelineLearningService"):
            resp = client.post("/api/orchestrator/pipeline/record", json={
                "pipeline_id": "pipe-1",
                "theme": "test",
                "awareness_level": 6,  # invalid — must be 1-5
                "platform": "tiktok",
            })
        assert resp.status_code == 422
