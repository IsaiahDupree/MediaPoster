"""
Unit Tests for Post Tracking Service (PTK-001, PTK-002, PTK-003, PTK-006)
============================================================================
Tests for post URL capture, checkback scheduling, and performance scoring.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4


class TestPostTrackerBasic:
    """Basic tests for PostTracker service"""

    def test_import_post_tracker(self):
        """Test that PostTracker can be imported"""
        from services.post_tracker import PostTracker, get_post_tracker
        assert PostTracker is not None
        assert get_post_tracker is not None

    def test_checkback_periods_defined(self):
        """Test that checkback periods are correctly defined"""
        from services.post_tracker import PostTracker

        PostTracker._instance = None
        tracker = PostTracker.get_instance()

        assert len(tracker.checkback_periods) == 5
        assert tracker.checkback_periods[0] == timedelta(hours=1)
        assert tracker.checkback_periods[1] == timedelta(hours=6)
        assert tracker.checkback_periods[2] == timedelta(hours=24)
        assert tracker.checkback_periods[3] == timedelta(hours=72)
        assert tracker.checkback_periods[4] == timedelta(days=7)


class TestCheckbackSchedulerWorker:
    """Tests for CheckbackSchedulerWorker"""

    def test_import_checkback_worker(self):
        """Test that CheckbackSchedulerWorker can be imported"""
        from services.workers.checkback_scheduler_worker import CheckbackSchedulerWorker
        assert CheckbackSchedulerWorker is not None

    def test_checkback_periods_match(self):
        """Test that worker has correct checkback periods"""
        from services.event_bus.bus import EventBus
        from services.workers.checkback_scheduler_worker import CheckbackSchedulerWorker

        event_bus = EventBus.get_instance()
        worker = CheckbackSchedulerWorker(event_bus)

        assert len(worker.checkback_periods) == 5
        assert worker.checkback_periods[0]['hours'] == 1
        assert worker.checkback_periods[1]['hours'] == 6
        assert worker.checkback_periods[2]['hours'] == 24
        assert worker.checkback_periods[3]['hours'] == 72
        assert worker.checkback_periods[4]['hours'] == 168  # 7 days


class TestPostTrackingAPI:
    """Tests for Post Tracking API endpoints"""

    def test_import_api_endpoints(self):
        """Test that API endpoints can be imported"""
        from api.endpoints import post_tracking
        assert post_tracking is not None
        assert post_tracking.router is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
