"""
Unit tests for BaseWorker class.

Tests:
- Worker initialization
- Event subscription
- Event emission
- Worker lifecycle
"""

import pytest
import asyncio
from typing import List
from services.event_bus.bus import EventBus
from services.event_bus.event import Event
from services.event_bus.topics import Topics
from services.workers.base import BaseWorker


class MockWorkerImpl(BaseWorker):
    """Mock implementation of BaseWorker for testing."""
    
    def __init__(self, event_bus=None, worker_id=None):
        self.received_events: List[Event] = []
        self._subscribed_topics = [Topics.MEDIA_INGESTED, Topics.ANALYSIS_COMPLETED]
        super().__init__(event_bus, worker_id)
    
    def get_subscriptions(self) -> List[str]:
        return self._subscribed_topics
    
    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


class TestBaseWorkerInitialization:
    """Tests for BaseWorker initialization."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    def test_worker_has_event_bus(self):
        """Worker should have event bus reference."""
        bus = EventBus.get_instance()
        worker = MockWorkerImpl(bus)
        
        assert worker.event_bus is bus
    
    def test_worker_has_worker_id(self):
        """Worker should have worker ID."""
        worker = MockWorkerImpl()
        
        assert worker.worker_id is not None
        assert len(worker.worker_id) > 0
    
    def test_worker_accepts_custom_id(self):
        """Worker should accept custom worker ID."""
        worker = MockWorkerImpl(worker_id="my-custom-worker")
        
        assert worker.worker_id == "my-custom-worker"
    
    def test_worker_creates_eventbus_if_none(self):
        """Worker should create EventBus if none provided."""
        worker = MockWorkerImpl()
        
        assert worker.event_bus is not None


class TestWorkerSubscriptions:
    """Tests for worker event subscriptions."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    def test_get_subscriptions_returns_list(self):
        """get_subscriptions should return list."""
        worker = MockWorkerImpl()
        
        subs = worker.get_subscriptions()
        
        assert isinstance(subs, list)
    
    def test_get_subscriptions_contains_topics(self):
        """get_subscriptions should contain expected topics."""
        worker = MockWorkerImpl()
        
        subs = worker.get_subscriptions()
        
        assert Topics.MEDIA_INGESTED in subs
        assert Topics.ANALYSIS_COMPLETED in subs


class TestWorkerEventHandling:
    """Tests for worker event handling."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_handle_event_receives_event(self):
        """handle_event should receive event object."""
        bus = EventBus.get_instance()
        worker = MockWorkerImpl(bus)
        
        event = Event(topic=Topics.MEDIA_INGESTED, payload={"media_id": "123"})
        await worker.handle_event(event)
        
        assert len(worker.received_events) == 1
        assert worker.received_events[0].topic == Topics.MEDIA_INGESTED


class TestWorkerEmission:
    """Tests for worker event emission."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_emit_publishes_event(self):
        """emit should publish event to bus."""
        bus = EventBus.get_instance()
        worker = MockWorkerImpl(bus, worker_id="test-worker")
        received = []
        
        async def handler(event):
            received.append(event)
        
        bus.subscribe("test.event", handler)
        
        await worker.emit("test.event", {"data": "value"})
        
        assert len(received) == 1
        assert received[0].payload["data"] == "value"
    
    @pytest.mark.asyncio
    async def test_emit_uses_worker_source(self):
        """emit should use worker ID as source."""
        bus = EventBus.get_instance()
        worker = MockWorkerImpl(bus, worker_id="my-worker")
        
        await worker.emit("test.event", {})
        
        events = bus.get_recent_events()
        assert events[0].source == "my-worker"
    
    @pytest.mark.asyncio
    async def test_emit_with_correlation_id(self):
        """emit should pass correlation ID."""
        bus = EventBus.get_instance()
        worker = MockWorkerImpl(bus)
        
        await worker.emit("test.event", {}, correlation_id="my-correlation")
        
        events = bus.get_recent_events()
        assert events[0].correlation_id == "my-correlation"


class TestWorkerProgress:
    """Tests for worker progress emission."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_emit_progress_publishes_progress_event(self):
        """emit_progress should publish progress event."""
        bus = EventBus.get_instance()
        worker = MockWorkerImpl(bus)
        received = []
        
        async def handler(event):
            received.append(event)
        
        bus.subscribe("media.analysis.progress", handler)
        
        await worker.emit_progress(
            base_topic="media.analysis",
            progress=50,
            step="processing",
            correlation_id="workflow-123"
        )
        
        assert len(received) == 1
        assert received[0].payload["progress"] == 50
        assert received[0].payload["step"] == "processing"
    
    @pytest.mark.asyncio
    async def test_emit_progress_includes_extra_payload(self):
        """emit_progress should include extra payload."""
        bus = EventBus.get_instance()
        worker = MockWorkerImpl(bus)
        
        await worker.emit_progress(
            base_topic="media.analysis",
            progress=75,
            step="finalizing",
            correlation_id="workflow-123",
            extra_data="some value"
        )
        
        events = bus.get_recent_events()
        assert events[0].payload["extra_data"] == "some value"


class TestWorkerLifecycle:
    """Tests for worker lifecycle."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_start_marks_running(self):
        """start should mark worker as running."""
        bus = EventBus.get_instance()
        worker = MockWorkerImpl(bus)
        
        await worker.start()
        
        assert worker.is_running is True
    
    @pytest.mark.asyncio
    async def test_start_emits_started_event(self):
        """start should emit WORKER_STARTED event."""
        bus = EventBus.get_instance()
        worker = MockWorkerImpl(bus, worker_id="test-worker")
        received = []
        
        async def handler(event):
            received.append(event)
        
        bus.subscribe(Topics.WORKER_STARTED, handler)
        
        await worker.start()
        
        assert len(received) == 1
        assert received[0].payload["worker_id"] == "test-worker"
    
    @pytest.mark.asyncio
    async def test_stop_marks_not_running(self):
        """stop should mark worker as not running."""
        bus = EventBus.get_instance()
        worker = MockWorkerImpl(bus)
        
        await worker.start()
        await worker.stop()
        
        assert worker.is_running is False
