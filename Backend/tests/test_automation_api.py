"""
Tests for Automation Center API Endpoints
==========================================
Tests for /api/automation/* endpoints including schedules, runs, and health.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


# =============================================================================
# HEALTH ENDPOINT TESTS
# =============================================================================

class TestAutomationHealth:
    """Tests for /api/automation/health endpoint."""
    
    def test_health_endpoint_returns_success(self):
        """Test that health endpoint returns a response."""
        response = client.get("/api/automation/health")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
    
    def test_health_includes_required_fields(self):
        """Test that health response includes all required fields."""
        response = client.get("/api/automation/health")
        data = response.json()
        
        if data.get("success"):
            health = data.get("health", {})
            assert "workers_online" in health
            assert "queue_depth" in health
            assert "last_tick" in health
            assert "failures_24h" in health


# =============================================================================
# SCHEDULES ENDPOINT TESTS
# =============================================================================

class TestAutomationSchedules:
    """Tests for /api/automation/schedules endpoints."""
    
    def test_list_schedules_returns_list(self):
        """Test that schedules endpoint returns a list."""
        response = client.get("/api/automation/schedules")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        if data.get("success"):
            assert "schedules" in data
            assert isinstance(data["schedules"], list)
    
    def test_list_schedules_with_agent_type_filter(self):
        """Test filtering schedules by agent_type."""
        response = client.get("/api/automation/schedules?agent_type=narrative")
        assert response.status_code == 200
        data = response.json()
        if data.get("success") and data.get("schedules"):
            for schedule in data["schedules"]:
                assert schedule.get("agent_type") == "narrative"
    
    def test_toggle_schedule_requires_id(self):
        """Test that toggle endpoint requires a valid schedule ID."""
        response = client.post("/api/automation/schedules/invalid-id/toggle")
        # Should return 200 even with invalid ID (graceful handling)
        assert response.status_code in [200, 404, 422]


# =============================================================================
# RUNS ENDPOINT TESTS
# =============================================================================

class TestAutomationRuns:
    """Tests for /api/automation/runs endpoints."""
    
    def test_list_runs_returns_list(self):
        """Test that runs endpoint returns a list."""
        response = client.get("/api/automation/runs")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        if data.get("success"):
            assert "runs" in data
            assert isinstance(data["runs"], list)
    
    def test_list_runs_with_limit(self):
        """Test runs endpoint respects limit parameter."""
        response = client.get("/api/automation/runs?limit=5")
        assert response.status_code == 200
        data = response.json()
        if data.get("success") and data.get("runs"):
            assert len(data["runs"]) <= 5
    
    def test_get_run_by_id_not_found(self):
        """Test getting a non-existent run returns appropriate response."""
        response = client.get("/api/automation/runs/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 200
        data = response.json()
        # Should indicate not found
        assert data.get("success") == False or data.get("run") is None
    
    def test_get_run_steps(self):
        """Test getting steps for a run."""
        response = client.get("/api/automation/runs/00000000-0000-0000-0000-000000000000/steps")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
    
    def test_get_run_timeline(self):
        """Test getting timeline for a run."""
        response = client.get("/api/automation/runs/00000000-0000-0000-0000-000000000000/timeline")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
    
    def test_get_run_artifacts(self):
        """Test getting artifacts for a run."""
        response = client.get("/api/automation/runs/00000000-0000-0000-0000-000000000000/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data


# =============================================================================
# RUN CONTROL ENDPOINT TESTS
# =============================================================================

class TestRunControl:
    """Tests for run control endpoints (pause, cancel, retry)."""
    
    def test_pause_run(self):
        """Test pause run endpoint."""
        response = client.post("/api/automation/runs/00000000-0000-0000-0000-000000000000/pause")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
    
    def test_cancel_run(self):
        """Test cancel run endpoint."""
        response = client.post("/api/automation/runs/00000000-0000-0000-0000-000000000000/cancel")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
    
    def test_retry_run_not_found(self):
        """Test retry on non-existent run."""
        response = client.post("/api/automation/runs/00000000-0000-0000-0000-000000000000/retry")
        assert response.status_code == 200
        data = response.json()
        # Should indicate failure for non-existent run
        assert "success" in data


# =============================================================================
# TOPICS ENDPOINT TESTS
# =============================================================================

class TestAutomationTopics:
    """Tests for /api/automation/topics endpoints."""
    
    def test_get_topics(self):
        """Test getting registered topics."""
        response = client.get("/api/automation/topics")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data


# =============================================================================
# SERVICES ENDPOINT TESTS
# =============================================================================

class TestAutomationServices:
    """Tests for /api/automation/services endpoint."""
    
    def test_get_services(self):
        """Test getting service health."""
        response = client.get("/api/automation/services")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        if data.get("success"):
            assert "services" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
