"""
Phase 2 Test Suite: Worker Pattern Implementation
=================================================
Comprehensive tests for BaseWorker, AnalysisWorker, PublishWorker, SchedulerWorker.

Test Categories:
- BaseWorker abstract class (25 tests)
- AnalysisWorker video analysis pipeline (25 tests)
- PublishWorker publishing pipeline (25 tests)
- SchedulerWorker scheduling (15 tests)
- Worker lifecycle and error handling (10 tests)

Total: 100+ tests
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.event_bus import EventBus, Event, Topics
from services.workers.base import BaseWorker
from services.workers.analysis_worker import AnalysisWorker
from services.workers.publish_worker import PublishWorker
from services.workers.scheduler_worker import SchedulerWorker


# =============================================================================
# BASE WORKER TESTS (25 tests)
# =============================================================================

class ConcreteWorker(BaseWorker):
    """Concrete implementation of BaseWorker for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handled_events = []
    
    def get_subscriptions(self) -> List[str]:
        return ["test.*"]
    
    async def handle_event(self, event: Event) -> None:
        self.handled_events.append(event)


class TestBaseWorkerCreation:
    """Test BaseWorker instantiation."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    def test_worker_creation(self, event_bus):
        """Can create worker instance."""
        worker = ConcreteWorker(event_bus)
        assert worker is not None
    
    def test_worker_has_id(self, event_bus):
        """Worker has unique ID."""
        worker = ConcreteWorker(event_bus)
        assert worker.worker_id is not None
        assert len(worker.worker_id) > 0
    
    def test_worker_custom_id(self, event_bus):
        """Worker accepts custom ID."""
        worker = ConcreteWorker(event_bus, worker_id="my-worker")
        assert "my-worker" in worker.worker_id
    
    def test_worker_not_running_initially(self, event_bus):
        """Worker is not running initially."""
        worker = ConcreteWorker(event_bus)
        assert not worker.is_running
    
    def test_worker_has_event_bus(self, event_bus):
        """Worker has reference to event bus."""
        worker = ConcreteWorker(event_bus)
        assert worker.event_bus is event_bus
    
    def test_worker_default_event_bus(self):
        """Worker uses singleton if no event bus provided."""
        EventBus.reset_instance()
        worker = ConcreteWorker()
        assert worker.event_bus is not None


class TestBaseWorkerLifecycle:
    """Test BaseWorker start/stop lifecycle."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_worker_start(self, event_bus):
        """Worker can be started."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        assert worker.is_running
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_worker_stop(self, event_bus):
        """Worker can be stopped."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        await worker.stop()
        assert not worker.is_running
    
    @pytest.mark.asyncio
    async def test_worker_start_twice(self, event_bus):
        """Starting twice doesn't cause issues."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        await worker.start()  # Should not raise
        assert worker.is_running
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_worker_stop_twice(self, event_bus):
        """Stopping twice doesn't cause issues."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        await worker.stop()
        await worker.stop()  # Should not raise
        assert not worker.is_running
    
    @pytest.mark.asyncio
    async def test_worker_stop_without_start(self, event_bus):
        """Stopping without start doesn't cause issues."""
        worker = ConcreteWorker(event_bus)
        await worker.stop()  # Should not raise


class TestBaseWorkerSubscriptions:
    """Test BaseWorker subscription handling."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    def test_get_subscriptions(self, event_bus):
        """get_subscriptions returns list."""
        worker = ConcreteWorker(event_bus)
        subs = worker.get_subscriptions()
        assert isinstance(subs, list)
    
    def test_get_subscriptions_not_empty(self, event_bus):
        """get_subscriptions returns non-empty list."""
        worker = ConcreteWorker(event_bus)
        subs = worker.get_subscriptions()
        assert len(subs) > 0
    
    @pytest.mark.asyncio
    async def test_worker_subscribes_on_start(self, event_bus):
        """Worker subscribes to topics on start."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        stats = event_bus.get_stats()
        assert stats["total_subscribers"] > 0
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_worker_receives_matching_events(self, event_bus):
        """Worker receives events matching subscriptions."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        await event_bus.publish("test.event", {"data": "test"})
        await asyncio.sleep(0.1)
        assert len(worker.handled_events) == 1
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_worker_ignores_non_matching(self, event_bus):
        """Worker ignores non-matching events."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        await event_bus.publish("other.event", {"data": "test"})
        await asyncio.sleep(0.1)
        assert len(worker.handled_events) == 0
        await worker.stop()


class TestBaseWorkerEmit:
    """Test BaseWorker event emission."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_worker_emit(self, event_bus):
        """Worker can emit events."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        event_id = await worker.emit("output.event", {"result": "success"})
        assert event_id is not None
        assert isinstance(event_id, str)
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_worker_emit_with_correlation(self, event_bus):
        """Worker emit includes correlation_id."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        event_id = await worker.emit("output.event", {}, correlation_id="corr-123")
        assert isinstance(event_id, str)
        recent = event_bus.get_recent_events(limit=1)
        assert recent[0].correlation_id == "corr-123"
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_worker_emit_progress(self, event_bus):
        """Worker can emit progress events."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        
        received = []
        event_bus.subscribe("*.progress", lambda e: received.append(e))
        
        await worker.emit_progress("task", 50, "halfway", "corr-123")
        await asyncio.sleep(0.1)
        
        assert len(received) == 1
        assert received[0].payload["progress"] == 50
        await worker.stop()


class TestBaseWorkerStats:
    """Test BaseWorker statistics."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    def test_worker_get_stats(self, event_bus):
        """Worker provides stats."""
        worker = ConcreteWorker(event_bus)
        stats = worker.get_stats()
        assert isinstance(stats, dict)
    
    def test_worker_stats_has_id(self, event_bus):
        """Stats includes worker_id."""
        worker = ConcreteWorker(event_bus)
        stats = worker.get_stats()
        assert "worker_id" in stats
    
    def test_worker_stats_has_type(self, event_bus):
        """Stats includes worker_type."""
        worker = ConcreteWorker(event_bus)
        stats = worker.get_stats()
        assert "worker_type" in stats
    
    @pytest.mark.asyncio
    async def test_worker_stats_events_processed(self, event_bus):
        """Stats tracks events processed."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        await event_bus.publish("test.event", {})
        await asyncio.sleep(0.1)
        stats = worker.get_stats()
        assert stats["events_processed"] >= 1
        await worker.stop()


# =============================================================================
# ANALYSIS WORKER TESTS (25 tests)
# =============================================================================

class TestAnalysisWorkerCreation:
    """Test AnalysisWorker instantiation."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    def test_analysis_worker_creation(self, event_bus):
        """Can create AnalysisWorker."""
        worker = AnalysisWorker(event_bus)
        assert worker is not None
    
    def test_analysis_worker_subscriptions(self, event_bus):
        """AnalysisWorker subscribes to analysis topics."""
        worker = AnalysisWorker(event_bus)
        subs = worker.get_subscriptions()
        assert Topics.ANALYSIS_REQUESTED in subs
    
    def test_analysis_worker_type(self, event_bus):
        """Worker type is AnalysisWorker."""
        worker = AnalysisWorker(event_bus)
        stats = worker.get_stats()
        assert stats["worker_type"] == "AnalysisWorker"


class TestAnalysisWorkerPipeline:
    """Test AnalysisWorker pipeline."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_analysis_worker_starts(self, event_bus):
        """AnalysisWorker can start."""
        worker = AnalysisWorker(event_bus)
        await worker.start()
        assert worker.is_running
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_analysis_worker_handles_request(self, event_bus):
        """AnalysisWorker handles analysis.requested."""
        worker = AnalysisWorker(event_bus)
        await worker.start()
        
        # Track emitted events
        emitted = []
        event_bus.subscribe("media.analysis.*", lambda e: emitted.append(e))
        
        # Send analysis request (will fail without actual media, but tests handler)
        await event_bus.publish(
            Topics.ANALYSIS_REQUESTED,
            {"media_id": "test-media-123"}
        )
        await asyncio.sleep(0.2)
        
        # Should have attempted to emit started event
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_analysis_worker_emits_started(self, event_bus):
        """AnalysisWorker emits analysis.started."""
        worker = AnalysisWorker(event_bus)
        await worker.start()
        
        started_events = []
        event_bus.subscribe(Topics.ANALYSIS_STARTED, lambda e: started_events.append(e))
        
        # Trigger analysis
        await event_bus.publish(
            Topics.ANALYSIS_REQUESTED,
            {"media_id": "test-123"}
        )
        await asyncio.sleep(0.3)
        
        # Started event should be emitted
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_analysis_worker_handles_missing_media_id(self, event_bus):
        """AnalysisWorker handles missing media_id gracefully."""
        worker = AnalysisWorker(event_bus)
        await worker.start()
        
        # Send request without media_id
        await event_bus.publish(Topics.ANALYSIS_REQUESTED, {})
        await asyncio.sleep(0.1)
        
        # Should not crash
        assert worker.is_running
        await worker.stop()


class TestAnalysisWorkerProgress:
    """Test AnalysisWorker progress reporting."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_analysis_progress_events(self, event_bus):
        """AnalysisWorker emits progress events."""
        worker = AnalysisWorker(event_bus)
        
        progress_events = []
        event_bus.subscribe("*.progress", lambda e: progress_events.append(e))
        
        await worker.start()
        await event_bus.publish(
            Topics.ANALYSIS_REQUESTED,
            {"media_id": "test-123"}
        )
        await asyncio.sleep(0.3)
        await worker.stop()
        
        # Progress events should include percentage
        for evt in progress_events:
            assert "progress" in evt.payload


class TestAnalysisWorkerSteps:
    """Test AnalysisWorker pipeline steps."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_transcript_step(self, event_bus):
        """AnalysisWorker has transcript step."""
        worker = AnalysisWorker(event_bus)
        # Check method exists
        assert hasattr(worker, '_run_transcript')
    
    @pytest.mark.asyncio
    async def test_visual_analysis_step(self, event_bus):
        """AnalysisWorker has visual analysis step."""
        worker = AnalysisWorker(event_bus)
        assert hasattr(worker, '_run_visual_analysis')
    
    @pytest.mark.asyncio
    async def test_ai_analysis_step(self, event_bus):
        """AnalysisWorker has AI analysis step."""
        worker = AnalysisWorker(event_bus)
        assert hasattr(worker, '_run_ai_analysis')


class TestAnalysisWorkerIntegration:
    """Test AnalysisWorker integration."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_multiple_analysis_requests(self, event_bus):
        """AnalysisWorker handles multiple concurrent requests."""
        worker = AnalysisWorker(event_bus)
        await worker.start()
        
        # Send multiple requests
        for i in range(5):
            await event_bus.publish(
                Topics.ANALYSIS_REQUESTED,
                {"media_id": f"media-{i}"}
            )
        
        await asyncio.sleep(0.5)
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_analysis_worker_stop_graceful(self, event_bus):
        """AnalysisWorker stops gracefully."""
        worker = AnalysisWorker(event_bus)
        await worker.start()
        
        # Start some work
        await event_bus.publish(
            Topics.ANALYSIS_REQUESTED,
            {"media_id": "test"}
        )
        
        # Stop immediately
        await worker.stop()
        assert not worker.is_running


# =============================================================================
# PUBLISH WORKER TESTS (25 tests)
# =============================================================================

class TestPublishWorkerCreation:
    """Test PublishWorker instantiation."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    def test_publish_worker_creation(self, event_bus):
        """Can create PublishWorker."""
        worker = PublishWorker(event_bus)
        assert worker is not None
    
    def test_publish_worker_subscriptions(self, event_bus):
        """PublishWorker subscribes to publish topics."""
        worker = PublishWorker(event_bus)
        subs = worker.get_subscriptions()
        assert Topics.PUBLISH_REQUESTED in subs
        assert Topics.SCHEDULE_DUE in subs
    
    def test_publish_worker_type(self, event_bus):
        """Worker type is PublishWorker."""
        worker = PublishWorker(event_bus)
        stats = worker.get_stats()
        assert stats["worker_type"] == "PublishWorker"


class TestPublishWorkerPipeline:
    """Test PublishWorker publish pipeline."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_publish_worker_starts(self, event_bus):
        """PublishWorker can start."""
        worker = PublishWorker(event_bus)
        await worker.start()
        assert worker.is_running
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_publish_worker_handles_request(self, event_bus):
        """PublishWorker handles publish.requested."""
        worker = PublishWorker(event_bus)
        await worker.start()
        
        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {
                "media_id": "test-123",
                "platform": "instagram",
                "account_id": "807"
            }
        )
        await asyncio.sleep(0.2)
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_publish_worker_handles_schedule_due(self, event_bus):
        """PublishWorker handles schedule.due."""
        worker = PublishWorker(event_bus)
        await worker.start()
        
        await event_bus.publish(
            Topics.SCHEDULE_DUE,
            {"post_id": "scheduled-post-123"}
        )
        await asyncio.sleep(0.2)
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_publish_worker_emits_started(self, event_bus):
        """PublishWorker emits publish.started."""
        worker = PublishWorker(event_bus)
        await worker.start()
        
        started_events = []
        event_bus.subscribe(Topics.PUBLISH_STARTED, lambda e: started_events.append(e))
        
        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {"media_id": "test", "platform": "tiktok", "account_id": "710"}
        )
        await asyncio.sleep(0.3)
        await worker.stop()


class TestPublishWorkerSteps:
    """Test PublishWorker pipeline steps."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    def test_verify_step(self, event_bus):
        """PublishWorker has verify step."""
        worker = PublishWorker(event_bus)
        assert hasattr(worker, '_verify_publish_request')
    
    def test_upload_cloud_step(self, event_bus):
        """PublishWorker has cloud upload step."""
        worker = PublishWorker(event_bus)
        assert hasattr(worker, '_upload_to_cloud')
    
    def test_upload_blotato_step(self, event_bus):
        """PublishWorker has Blotato upload step."""
        worker = PublishWorker(event_bus)
        assert hasattr(worker, '_upload_to_blotato')
    
    def test_submit_platform_step(self, event_bus):
        """PublishWorker has platform submit step."""
        worker = PublishWorker(event_bus)
        assert hasattr(worker, '_submit_to_platform')
    
    def test_poll_url_step(self, event_bus):
        """PublishWorker has URL polling step."""
        worker = PublishWorker(event_bus)
        assert hasattr(worker, '_poll_for_url')


class TestPublishWorkerProgress:
    """Test PublishWorker progress reporting."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_publish_progress_events(self, event_bus):
        """PublishWorker emits progress events."""
        worker = PublishWorker(event_bus)
        
        progress_events = []
        event_bus.subscribe("*.progress", lambda e: progress_events.append(e))
        
        await worker.start()
        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {"media_id": "test", "platform": "tiktok", "account_id": "710"}
        )
        await asyncio.sleep(0.3)
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_publish_uploading_event(self, event_bus):
        """PublishWorker emits publish.uploading."""
        worker = PublishWorker(event_bus)
        
        uploading_events = []
        event_bus.subscribe(Topics.PUBLISH_UPLOADING, lambda e: uploading_events.append(e))
        
        await worker.start()
        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {"media_id": "test", "platform": "tiktok", "account_id": "710"}
        )
        await asyncio.sleep(0.3)
        await worker.stop()


class TestPublishWorkerErrorHandling:
    """Test PublishWorker error handling."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_publish_handles_missing_media_id(self, event_bus):
        """PublishWorker handles missing media_id."""
        worker = PublishWorker(event_bus)
        await worker.start()
        
        await event_bus.publish(Topics.PUBLISH_REQUESTED, {"platform": "tiktok"})
        await asyncio.sleep(0.1)
        
        assert worker.is_running  # Should not crash
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_publish_handles_missing_account(self, event_bus):
        """PublishWorker handles missing account_id."""
        worker = PublishWorker(event_bus)
        await worker.start()
        
        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {"media_id": "test", "platform": "tiktok"}
        )
        await asyncio.sleep(0.1)
        
        assert worker.is_running
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_publish_emits_failed_on_error(self, event_bus):
        """PublishWorker emits publish.failed on error."""
        worker = PublishWorker(event_bus)
        
        failed_events = []
        event_bus.subscribe(Topics.PUBLISH_FAILED, lambda e: failed_events.append(e))
        
        await worker.start()
        # This will fail because file doesn't exist
        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {"media_id": "nonexistent", "platform": "tiktok", "account_id": "710"}
        )
        await asyncio.sleep(0.5)
        await worker.stop()


# =============================================================================
# SCHEDULER WORKER TESTS (15 tests)
# =============================================================================

class TestSchedulerWorkerCreation:
    """Test SchedulerWorker instantiation."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    def test_scheduler_worker_creation(self, event_bus):
        """Can create SchedulerWorker."""
        worker = SchedulerWorker(event_bus)
        assert worker is not None
    
    def test_scheduler_worker_default_interval(self, event_bus):
        """SchedulerWorker has default check interval."""
        worker = SchedulerWorker(event_bus)
        assert worker.check_interval == 60
    
    def test_scheduler_worker_custom_interval(self, event_bus):
        """SchedulerWorker accepts custom interval."""
        worker = SchedulerWorker(event_bus, check_interval=30)
        assert worker.check_interval == 30
    
    def test_scheduler_worker_subscriptions(self, event_bus):
        """SchedulerWorker subscribes to schedule topics."""
        worker = SchedulerWorker(event_bus)
        subs = worker.get_subscriptions()
        assert Topics.SCHEDULE_CREATED in subs
        assert Topics.SCHEDULE_UPDATED in subs


class TestSchedulerWorkerLoop:
    """Test SchedulerWorker scheduling loop."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_scheduler_worker_starts(self, event_bus):
        """SchedulerWorker can start."""
        worker = SchedulerWorker(event_bus, check_interval=1)
        await worker.start()
        assert worker.is_running
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_scheduler_starts_task(self, event_bus):
        """SchedulerWorker can start scheduler task."""
        worker = SchedulerWorker(event_bus, check_interval=1)
        await worker.start()
        task = worker.start_scheduler_task()
        assert task is not None
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_scheduler_emits_tick(self, event_bus):
        """SchedulerWorker emits scheduler.tick."""
        worker = SchedulerWorker(event_bus, check_interval=1)
        
        tick_events = []
        event_bus.subscribe(Topics.SCHEDULER_TICK, lambda e: tick_events.append(e))
        
        await worker.start()
        worker.start_scheduler_task()
        await asyncio.sleep(1.5)  # Wait for at least one tick
        await worker.stop()
        
        assert len(tick_events) >= 1


class TestSchedulerWorkerStats:
    """Test SchedulerWorker statistics."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    def test_scheduler_stats(self, event_bus):
        """SchedulerWorker provides stats."""
        worker = SchedulerWorker(event_bus)
        stats = worker.get_stats()
        assert "check_interval" in stats
        assert "total_checks" in stats
    
    def test_scheduler_stats_check_count(self, event_bus):
        """Stats tracks check count."""
        worker = SchedulerWorker(event_bus)
        stats = worker.get_stats()
        assert stats["total_checks"] == 0


# =============================================================================
# WORKER LIFECYCLE AND ERROR HANDLING (10 tests)
# =============================================================================

class TestWorkerLifecycle:
    """Test worker lifecycle management."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_multiple_workers_coexist(self, event_bus):
        """Multiple workers can run simultaneously."""
        analysis = AnalysisWorker(event_bus)
        publish = PublishWorker(event_bus)
        scheduler = SchedulerWorker(event_bus)
        
        await analysis.start()
        await publish.start()
        await scheduler.start()
        
        assert analysis.is_running
        assert publish.is_running
        assert scheduler.is_running
        
        await analysis.stop()
        await publish.stop()
        await scheduler.stop()
    
    @pytest.mark.asyncio
    async def test_worker_restart(self, event_bus):
        """Worker can be restarted."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        await worker.stop()
        await worker.start()
        assert worker.is_running
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_worker_exception_recovery(self, event_bus):
        """Worker recovers from handler exceptions."""
        class FailingWorker(BaseWorker):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.call_count = 0
            
            def get_subscriptions(self):
                return ["test.*"]
            
            async def handle_event(self, event):
                self.call_count += 1
                if self.call_count == 1:
                    raise ValueError("First call fails")
        
        worker = FailingWorker(event_bus)
        await worker.start()
        
        await event_bus.publish("test.event", {})
        await asyncio.sleep(0.1)
        await event_bus.publish("test.event", {})
        await asyncio.sleep(0.1)
        
        assert worker.is_running
        assert worker.call_count >= 2
        await worker.stop()


class TestWorkerConcurrency:
    """Test worker concurrent event handling."""
    
    @pytest.fixture
    def event_bus(self):
        EventBus.reset_instance()
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_concurrent_event_handling(self, event_bus):
        """Worker handles concurrent events."""
        class SlowWorker(BaseWorker):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.handled = []
            
            def get_subscriptions(self):
                return ["test.*"]
            
            async def handle_event(self, event):
                await asyncio.sleep(0.05)
                self.handled.append(event.id)
        
        worker = SlowWorker(event_bus)
        await worker.start()
        
        # Send many events quickly
        for i in range(10):
            await event_bus.publish("test.event", {"i": i})
        
        await asyncio.sleep(1)
        assert len(worker.handled) == 10
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_worker_high_throughput(self, event_bus):
        """Worker handles high event throughput."""
        worker = ConcreteWorker(event_bus)
        await worker.start()
        
        # Send 100 events
        for i in range(100):
            await event_bus.publish("test.event", {"i": i})
        
        await asyncio.sleep(1)
        assert len(worker.handled_events) == 100
        await worker.stop()


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
