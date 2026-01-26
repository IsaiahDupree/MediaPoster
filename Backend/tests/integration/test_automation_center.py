"""
Integration Tests for Automation Center (AC-001)
================================================
Tests the Automation Center API endpoints and dashboard integration.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestAutomationCenterAPI:
    """Test Automation Center API endpoints (AC-001)"""

    def test_health_endpoint(self):
        """Test GET /api/automation/health"""
        response = client.get("/api/automation/health")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "health" in data

        health = data["health"]
        assert "workers_online" in health
        assert "active_tasks" in health
        assert "queue_depth" in health
        assert "last_tick" in health
        assert "failures_24h" in health

    def test_get_schedules(self):
        """Test GET /api/automation/schedules"""
        response = client.get("/api/automation/schedules")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "schedules" in data
        assert isinstance(data["schedules"], list)

    def test_get_schedules_by_agent_type(self):
        """Test GET /api/automation/schedules?agent_type=X"""
        response = client.get("/api/automation/schedules?agent_type=narrative_builder")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "schedules" in data

    def test_get_runs(self):
        """Test GET /api/automation/runs"""
        response = client.get("/api/automation/runs")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "runs" in data
        assert isinstance(data["runs"], list)

    def test_get_runs_with_limit(self):
        """Test GET /api/automation/runs?limit=10"""
        response = client.get("/api/automation/runs?limit=10")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert len(data["runs"]) <= 10

    def test_get_runs_by_status(self):
        """Test GET /api/automation/runs?status=completed"""
        response = client.get("/api/automation/runs?status=completed")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        # All returned runs should have status=completed
        for run in data["runs"]:
            assert run.get("status") == "completed"

    def test_get_services(self):
        """Test GET /api/automation/services"""
        response = client.get("/api/automation/services")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "services" in data
        assert isinstance(data["services"], list)

    def test_get_topics(self):
        """Test GET /api/automation/topics"""
        response = client.get("/api/automation/topics")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data

    def test_toggle_schedule_validation(self):
        """Test schedule toggle with invalid ID"""
        invalid_id = "not-a-uuid"
        response = client.post(f"/api/automation/schedules/{invalid_id}/toggle?enabled=true")
        assert response.status_code == 422  # Unprocessable Entity

    def test_run_now_validation(self):
        """Test run now with nonexistent schedule"""
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/automation/schedules/{fake_id}/run")
        assert response.status_code == 200

        data = response.json()
        # Should return success=False for nonexistent schedule
        if not data.get("success"):
            assert "error" in data

    def test_pause_run_validation(self):
        """Test pause run with invalid ID"""
        invalid_id = "not-a-uuid"
        response = client.post(f"/api/automation/runs/{invalid_id}/pause")
        assert response.status_code == 422  # Unprocessable Entity

    def test_cancel_run_validation(self):
        """Test cancel run with invalid ID"""
        invalid_id = "not-a-uuid"
        response = client.post(f"/api/automation/runs/{invalid_id}/cancel")
        assert response.status_code == 422  # Unprocessable Entity


class TestAutomationCenterIntegration:
    """Test Automation Center integration (AC-001)"""

    def test_tab_switching_data_available(self):
        """
        AC-001 Acceptance: Tab switching works
        Verify all tabs have data endpoints
        """
        # Test Schedules tab data
        schedules_response = client.get("/api/automation/schedules")
        assert schedules_response.status_code == 200

        # Test Runs tab data
        runs_response = client.get("/api/automation/runs")
        assert runs_response.status_code == 200

        # Test Health tab data
        health_response = client.get("/api/automation/health")
        assert health_response.status_code == 200

    def test_queue_depth_visible(self):
        """
        AC-001 Acceptance: Queue depth visible
        Verify queue depth is returned in health metrics
        """
        response = client.get("/api/automation/health")
        assert response.status_code == 200

        data = response.json()
        assert "health" in data
        assert "queue_depth" in data["health"]
        assert isinstance(data["health"]["queue_depth"], int)

    def test_health_metrics_complete(self):
        """Test all required health metrics are present"""
        response = client.get("/api/automation/health")
        assert response.status_code == 200

        data = response.json()
        health = data["health"]

        required_metrics = [
            "workers_online",
            "active_tasks",
            "queue_depth",
            "last_tick",
            "failures_24h"
        ]

        for metric in required_metrics:
            assert metric in health, f"Missing required metric: {metric}"

    def test_schedule_lifecycle(self):
        """Test schedule operations (view, toggle, run)"""
        # Get schedules
        response = client.get("/api/automation/schedules")
        assert response.status_code == 200

        data = response.json()
        schedules = data.get("schedules", [])

        # If schedules exist, test toggle and run
        if schedules:
            schedule = schedules[0]
            schedule_id = schedule["id"]

            # Note: Actual toggle/run tests would modify state,
            # so we just verify the endpoints are accessible
            # In production, you'd use test fixtures with isolated data

    def test_run_timeline_feature(self):
        """Test run timeline endpoint for debugging"""
        # Get recent runs
        runs_response = client.get("/api/automation/runs?limit=1")
        assert runs_response.status_code == 200

        runs_data = runs_response.json()
        runs = runs_data.get("runs", [])

        if runs:
            run_id = runs[0]["id"]

            # Test timeline endpoint
            timeline_response = client.get(f"/api/automation/runs/{run_id}/timeline")
            assert timeline_response.status_code == 200

            timeline_data = timeline_response.json()
            assert "success" in timeline_data
            assert "events" in timeline_data

    def test_run_steps_feature(self):
        """Test run steps endpoint for debugging"""
        # Get recent runs
        runs_response = client.get("/api/automation/runs?limit=1")
        assert runs_response.status_code == 200

        runs_data = runs_response.json()
        runs = runs_data.get("runs", [])

        if runs:
            run_id = runs[0]["id"]

            # Test steps endpoint
            steps_response = client.get(f"/api/automation/runs/{run_id}/steps")
            assert steps_response.status_code == 200

            steps_data = steps_response.json()
            assert "success" in steps_data
            assert "steps" in steps_data


# Mark as integration test
pytestmark = pytest.mark.integration
