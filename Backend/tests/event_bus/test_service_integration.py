"""
Integration tests for interconnected services via pub/sub.

Tests:
- Service-to-service communication
- Workflow event chains
- Cross-service correlation
- Event propagation
"""

import pytest
import asyncio
from typing import List, Dict, Any
from services.event_bus.bus import EventBus
from services.event_bus.event import Event
from services.event_bus.topics import Topics


class MockAnalysisService:
    """Mock analysis service for testing."""
    
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self.processed = []
        self.bus.subscribe(Topics.ANALYSIS_REQUESTED, self._handle_analysis_request)
    
    async def _handle_analysis_request(self, event: Event):
        media_id = event.payload.get("media_id")
        self.processed.append(media_id)
        
        # Emit progress
        await self.bus.publish(
            Topics.ANALYSIS_PROGRESS,
            {"media_id": media_id, "progress": 50},
            correlation_id=event.correlation_id
        )
        
        # Emit completion
        await self.bus.publish(
            Topics.ANALYSIS_COMPLETED,
            {"media_id": media_id, "result": {"analyzed": True}},
            correlation_id=event.correlation_id
        )


class MockPublishService:
    """Mock publish service for testing."""
    
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self.published = []
        self.bus.subscribe(Topics.PUBLISH_REQUESTED, self._handle_publish_request)
    
    async def _handle_publish_request(self, event: Event):
        media_id = event.payload.get("media_id")
        platform = event.payload.get("platform")
        
        # Emit started
        await self.bus.publish(
            Topics.PUBLISH_STARTED,
            {"media_id": media_id, "platform": platform},
            correlation_id=event.correlation_id
        )
        
        # Simulate publish
        self.published.append({"media_id": media_id, "platform": platform})
        
        # Emit completed
        await self.bus.publish(
            Topics.PUBLISH_COMPLETED,
            {"media_id": media_id, "platform": platform, "url": f"https://{platform}.com/post/123"},
            correlation_id=event.correlation_id
        )


class MockMetricsService:
    """Mock metrics service for testing."""
    
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self.fetched = []
        # Subscribe to publish completed to auto-fetch metrics
        self.bus.subscribe(Topics.PUBLISH_COMPLETED, self._handle_publish_completed)
    
    async def _handle_publish_completed(self, event: Event):
        media_id = event.payload.get("media_id")
        platform = event.payload.get("platform")
        
        self.fetched.append({"media_id": media_id, "platform": platform})
        
        # Emit metrics updated
        await self.bus.publish(
            Topics.METRICS_UPDATED,
            {"media_id": media_id, "views": 100, "likes": 10},
            correlation_id=event.correlation_id
        )


class TestServiceToServiceCommunication:
    """Tests for service-to-service communication."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_analysis_service_responds_to_request(self):
        """Analysis service should respond to analysis request."""
        bus = EventBus.get_instance()
        service = MockAnalysisService(bus)
        
        await bus.publish(Topics.ANALYSIS_REQUESTED, {"media_id": "media-123"})
        
        assert "media-123" in service.processed
    
    @pytest.mark.asyncio
    async def test_analysis_emits_progress_and_completion(self):
        """Analysis should emit progress and completion events."""
        bus = EventBus.get_instance()
        service = MockAnalysisService(bus)
        events = []
        
        async def collector(event):
            events.append(event)
        
        bus.subscribe("*", collector)
        
        await bus.publish(Topics.ANALYSIS_REQUESTED, {"media_id": "media-123"})
        
        topics = [e.topic for e in events]
        assert Topics.ANALYSIS_PROGRESS in topics
        assert Topics.ANALYSIS_COMPLETED in topics
    
    @pytest.mark.asyncio
    async def test_publish_service_responds_to_request(self):
        """Publish service should respond to publish request."""
        bus = EventBus.get_instance()
        service = MockPublishService(bus)
        
        await bus.publish(Topics.PUBLISH_REQUESTED, {
            "media_id": "media-123",
            "platform": "instagram"
        })
        
        assert len(service.published) == 1
        assert service.published[0]["platform"] == "instagram"


class TestWorkflowEventChains:
    """Tests for workflow event chains."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_publish_triggers_metrics_fetch(self):
        """Publish completion should trigger metrics fetch."""
        bus = EventBus.get_instance()
        publish_service = MockPublishService(bus)
        metrics_service = MockMetricsService(bus)
        
        await bus.publish(Topics.PUBLISH_REQUESTED, {
            "media_id": "media-123",
            "platform": "tiktok"
        })
        
        # Metrics service should have fetched
        assert len(metrics_service.fetched) == 1
        assert metrics_service.fetched[0]["platform"] == "tiktok"
    
    @pytest.mark.asyncio
    async def test_full_analysis_to_publish_chain(self):
        """Full chain: analysis → publish → metrics."""
        bus = EventBus.get_instance()
        analysis_service = MockAnalysisService(bus)
        publish_service = MockPublishService(bus)
        metrics_service = MockMetricsService(bus)
        all_events = []
        
        async def collector(event):
            all_events.append(event)
        
        bus.subscribe("*", collector)
        
        # Trigger publish after analysis completes
        async def trigger_publish_after_analysis(event):
            if event.topic == Topics.ANALYSIS_COMPLETED:
                await bus.publish(Topics.PUBLISH_REQUESTED, {
                    "media_id": event.payload.get("media_id"),
                    "platform": "instagram"
                }, correlation_id=event.correlation_id)
        
        bus.subscribe(Topics.ANALYSIS_COMPLETED, trigger_publish_after_analysis)
        
        # Start the chain
        await bus.publish(Topics.ANALYSIS_REQUESTED, {"media_id": "media-123"})
        
        topics = [e.topic for e in all_events]
        
        # Verify full chain
        assert Topics.ANALYSIS_REQUESTED in topics
        assert Topics.ANALYSIS_COMPLETED in topics
        assert Topics.PUBLISH_REQUESTED in topics
        assert Topics.PUBLISH_COMPLETED in topics
        assert Topics.METRICS_UPDATED in topics


class TestCorrelationTracking:
    """Tests for cross-service correlation tracking."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_correlation_preserved_across_services(self):
        """Correlation ID should be preserved across services."""
        bus = EventBus.get_instance()
        analysis_service = MockAnalysisService(bus)
        
        correlation_id = "workflow-abc-123"
        
        await bus.publish(
            Topics.ANALYSIS_REQUESTED,
            {"media_id": "media-123"},
            correlation_id=correlation_id
        )
        
        # Get all events with this correlation ID
        events = bus.get_recent_events(correlation_id=correlation_id)
        
        assert len(events) >= 3  # request, progress, completed
        assert all(e.correlation_id == correlation_id for e in events)
    
    @pytest.mark.asyncio
    async def test_different_workflows_have_different_correlations(self):
        """Different workflows should have different correlation IDs."""
        bus = EventBus.get_instance()
        analysis_service = MockAnalysisService(bus)
        
        await bus.publish(
            Topics.ANALYSIS_REQUESTED,
            {"media_id": "media-1"},
            correlation_id="workflow-1"
        )
        
        await bus.publish(
            Topics.ANALYSIS_REQUESTED,
            {"media_id": "media-2"},
            correlation_id="workflow-2"
        )
        
        workflow1_events = bus.get_recent_events(correlation_id="workflow-1")
        workflow2_events = bus.get_recent_events(correlation_id="workflow-2")
        
        assert len(workflow1_events) >= 1
        assert len(workflow2_events) >= 1
        
        # No overlap
        workflow1_ids = {e.id for e in workflow1_events}
        workflow2_ids = {e.id for e in workflow2_events}
        assert workflow1_ids.isdisjoint(workflow2_ids)


class TestEventPropagation:
    """Tests for event propagation patterns."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_fan_out_to_multiple_services(self):
        """Single event should fan out to multiple subscribers."""
        bus = EventBus.get_instance()
        received1 = []
        received2 = []
        received3 = []
        
        async def handler1(event):
            received1.append(event)
        
        async def handler2(event):
            received2.append(event)
        
        async def handler3(event):
            received3.append(event)
        
        bus.subscribe(Topics.MEDIA_INGESTED, handler1)
        bus.subscribe(Topics.MEDIA_INGESTED, handler2)
        bus.subscribe(Topics.MEDIA_INGESTED, handler3)
        
        await bus.publish(Topics.MEDIA_INGESTED, {"media_id": "123"})
        
        assert len(received1) == 1
        assert len(received2) == 1
        assert len(received3) == 1
    
    @pytest.mark.asyncio
    async def test_wildcard_subscribers_receive_all(self):
        """Wildcard subscriber should receive all matching events."""
        bus = EventBus.get_instance()
        all_publish_events = []
        
        async def publish_monitor(event):
            all_publish_events.append(event)
        
        bus.subscribe("publish.*", publish_monitor)
        
        await bus.publish(Topics.PUBLISH_REQUESTED, {"media_id": "1"})
        await bus.publish(Topics.PUBLISH_STARTED, {"media_id": "1"})
        await bus.publish(Topics.PUBLISH_COMPLETED, {"media_id": "1"})
        await bus.publish(Topics.MEDIA_INGESTED, {"media_id": "2"})  # Should not match
        
        assert len(all_publish_events) == 3
    
    @pytest.mark.asyncio
    async def test_error_in_one_handler_doesnt_stop_others(self):
        """Error in one handler should not prevent other handlers."""
        bus = EventBus.get_instance()
        received = []
        
        async def failing_handler(event):
            raise ValueError("Handler failed!")
        
        async def working_handler(event):
            received.append(event)
        
        bus.subscribe("test.event", failing_handler)
        bus.subscribe("test.event", working_handler)
        
        await bus.publish("test.event", {"data": "value"})
        
        # Working handler should still receive event
        assert len(received) == 1


class TestServiceIsolation:
    """Tests for service isolation and independence."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_services_only_respond_to_subscribed_topics(self):
        """Services should only respond to their subscribed topics."""
        bus = EventBus.get_instance()
        analysis_service = MockAnalysisService(bus)
        publish_service = MockPublishService(bus)
        
        # Send analysis request - only analysis should respond
        await bus.publish(Topics.ANALYSIS_REQUESTED, {"media_id": "123"})
        
        assert len(analysis_service.processed) == 1
        assert len(publish_service.published) == 0
        
        # Send publish request - only publish should respond
        await bus.publish(Topics.PUBLISH_REQUESTED, {
            "media_id": "456",
            "platform": "instagram"
        })
        
        assert len(analysis_service.processed) == 1  # Still 1
        assert len(publish_service.published) == 1
    
    @pytest.mark.asyncio
    async def test_unsubscribed_service_receives_nothing(self):
        """Unsubscribed service should receive no events."""
        bus = EventBus.get_instance()
        received = []
        
        async def handler(event):
            received.append(event)
        
        # Subscribe then unsubscribe
        bus.subscribe("test.topic", handler)
        bus.unsubscribe("test.topic", handler)
        
        await bus.publish("test.topic", {})
        
        assert len(received) == 0
