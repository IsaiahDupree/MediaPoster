"""
Tests for Scheduler API Endpoints
==================================
Tests for /api/scheduler/* endpoints including tick, worker, and health.
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
# SCHEDULER TICK TESTS
# =============================================================================

class TestSchedulerTick:
    """Tests for /api/scheduler/tick endpoint."""
    
    def test_tick_endpoint_returns_success(self):
        """Test that tick endpoint returns a response."""
        response = client.post("/api/scheduler/tick")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
    
    def test_tick_returns_created_count(self):
        """Test that tick response includes created count."""
        response = client.post("/api/scheduler/tick")
        data = response.json()
        if data.get("success"):
            assert "created" in data
            assert isinstance(data["created"], int)


# =============================================================================
# SCHEDULER WORKER TESTS
# =============================================================================

class TestSchedulerWorker:
    """Tests for /api/scheduler/worker/process endpoint."""
    
    def test_worker_process_returns_success(self):
        """Test that worker process endpoint returns a response."""
        response = client.post("/api/scheduler/worker/process")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
    
    def test_worker_process_returns_processed_count(self):
        """Test that worker response includes processed count."""
        response = client.post("/api/scheduler/worker/process")
        data = response.json()
        if data.get("success"):
            assert "processed" in data
            assert isinstance(data["processed"], int)
    
    def test_worker_process_with_batch_size(self):
        """Test worker process with custom batch size."""
        response = client.post("/api/scheduler/worker/process?batch_size=3")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data


# =============================================================================
# SCHEDULER TRIGGER TESTS
# =============================================================================

class TestSchedulerTrigger:
    """Tests for /api/scheduler/trigger/{schedule_id} endpoint."""
    
    def test_trigger_nonexistent_schedule(self):
        """Test triggering a non-existent schedule."""
        response = client.post("/api/scheduler/trigger/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 200
        data = response.json()
        # Should indicate schedule not found
        assert data.get("success") == False or "error" in data


# =============================================================================
# SCHEDULER HEALTH TESTS
# =============================================================================

class TestSchedulerHealth:
    """Tests for /api/scheduler/health endpoint."""
    
    def test_scheduler_health_returns_success(self):
        """Test that scheduler health endpoint returns a response."""
        response = client.get("/api/scheduler/health")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
    
    def test_scheduler_health_includes_queue_stats(self):
        """Test that scheduler health includes queue statistics."""
        response = client.get("/api/scheduler/health")
        data = response.json()
        if data.get("success"):
            assert "queue" in data
            queue = data["queue"]
            assert "queued" in queue
            assert "processing" in queue
    
    def test_scheduler_health_includes_schedule_stats(self):
        """Test that scheduler health includes schedule statistics."""
        response = client.get("/api/scheduler/health")
        data = response.json()
        if data.get("success"):
            assert "schedules" in data
            schedules = data["schedules"]
            assert "enabled" in schedules
            assert "disabled" in schedules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
