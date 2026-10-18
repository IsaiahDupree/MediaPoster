"""
Unit tests for EventBus pub/sub system.

Tests:
- Event publishing
- Topic subscriptions
- Wildcard pattern matching
- Event logging
- Dead-letter queue
- Event replay
"""

import pytest
import asyncio
from datetime import datetime, timezone
from services.event_bus.bus import EventBus
from services.event_bus.event import Event
from services.event_bus.topics import Topics


class TestEventBusInitialization:
    """Tests for EventBus initialization."""
    
    def setup_method(self):
        """Reset singleton before each test."""
        EventBus.reset_instance()
    
    def teardown_method(self):
        """Reset singleton after each test."""
        EventBus.reset_instance()
    
    def test_get_instance_returns_eventbus(self):
        """Should return EventBus instance."""
        bus = EventBus.get_instance()
        
        assert bus is not None
        assert isinstance(bus, EventBus)
    
    def test_get_instance_returns_singleton(self):
        """Should return same instance each time."""
        bus1 = EventBus.get_instance()
        bus2 = EventBus.get_instance()
        
        assert bus1 is bus2
    
    def test_reset_instance_clears_singleton(self):
        """Reset should clear the singleton."""
        bus1 = EventBus.get_instance()
        EventBus.reset_instance()
        bus2 = EventBus.get_instance()
        
        assert bus1 is not bus2
    
    def test_eventbus_has_subscribers_dict(self):
        """EventBus should have subscribers dictionary."""
        bus = EventBus.get_instance()
        
        assert hasattr(bus, '_subscribers')
        assert isinstance(bus._subscribers, dict)
    
    def test_eventbus_has_event_log(self):
        """EventBus should have event log."""
        bus = EventBus.get_instance()
        
        assert hasattr(bus, '_event_log')
        assert isinstance(bus._event_log, list)


class TestEventPublishing:
    """Tests for event publishing."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_publish_returns_event_id(self):
        """Publish should return event ID."""
        bus = EventBus.get_instance()
        
        event_id = await bus.publish("test.topic", {"data": "value"})
        
        assert event_id is not None
        assert isinstance(event_id, str)
        assert len(event_id) > 0
    
    @pytest.mark.asyncio
    async def test_publish_logs_event(self):
        """Published event should be logged."""
        bus = EventBus.get_instance()
        
        await bus.publish("test.topic", {"data": "value"})
        
        events = bus.get_recent_events()
        assert len(events) == 1
        assert events[0].topic == "test.topic"
    
    @pytest.mark.asyncio
    async def test_publish_with_correlation_id(self):
        """Should use provided correlation ID."""
        bus = EventBus.get_instance()
        
        await bus.publish("test.topic", {"data": "value"}, correlation_id="my-correlation-123")
        
        events = bus.get_recent_events()
        assert events[0].correlation_id == "my-correlation-123"
    
    @pytest.mark.asyncio
    async def test_publish_with_custom_source(self):
        """Should use provided source."""
        bus = EventBus.get_instance()
        
        await bus.publish("test.topic", {"data": "value"}, source="my-service")
        
        events = bus.get_recent_events()
        assert events[0].source == "my-service"
    
    @pytest.mark.asyncio
    async def test_publish_multiple_events(self):
        """Should log multiple events."""
        bus = EventBus.get_instance()
        
        await bus.publish("topic.1", {"num": 1})
        await bus.publish("topic.2", {"num": 2})
        await bus.publish("topic.3", {"num": 3})
        
        events = bus.get_recent_events()
        assert len(events) == 3


class TestEventSubscriptions:
    """Tests for event subscriptions."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_subscribe_receives_events(self):
        """Subscriber should receive matching events."""
        bus = EventBus.get_instance()
        received = []
        
        async def handler(event):
            received.append(event)
        
        bus.subscribe("test.topic", handler)
        await bus.publish("test.topic", {"data": "value"})
        
        assert len(received) == 1
        assert received[0].topic == "test.topic"
    
    @pytest.mark.asyncio
    async def test_subscribe_returns_subscription_id(self):
        """Subscribe should return subscription ID."""
        bus = EventBus.get_instance()
        
        async def handler(event):
            pass
        
        sub_id = bus.subscribe("test.topic", handler)
        
        assert sub_id is not None
        assert "test.topic" in sub_id
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_topic(self):
        """Multiple subscribers should all receive events."""
        bus = EventBus.get_instance()
        received1 = []
        received2 = []
        
        async def handler1(event):
            received1.append(event)
        
        async def handler2(event):
            received2.append(event)
        
        bus.subscribe("test.topic", handler1)
        bus.subscribe("test.topic", handler2)
        await bus.publish("test.topic", {"data": "value"})
        
        assert len(received1) == 1
        assert len(received2) == 1
    
    @pytest.mark.asyncio
    async def test_subscriber_does_not_receive_other_topics(self):
        """Subscriber should not receive events from other topics."""
        bus = EventBus.get_instance()
        received = []
        
        async def handler(event):
            received.append(event)
        
        bus.subscribe("topic.a", handler)
        await bus.publish("topic.b", {"data": "value"})
        
        assert len(received) == 0
    
    @pytest.mark.asyncio
    async def test_unsubscribe_stops_receiving(self):
        """After unsubscribe, handler should not receive events."""
        bus = EventBus.get_instance()
        received = []
        
        async def handler(event):
            received.append(event)
        
        bus.subscribe("test.topic", handler)
        await bus.publish("test.topic", {"data": "before"})
        
        bus.unsubscribe("test.topic", handler)
        await bus.publish("test.topic", {"data": "after"})
        
        assert len(received) == 1
        assert received[0].payload["data"] == "before"


class TestWildcardPatterns:
    """Tests for wildcard topic patterns."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_star_suffix_pattern(self):
        """Pattern 'prefix.*' should match all subtopics."""
        bus = EventBus.get_instance()
        received = []
        
        async def handler(event):
            received.append(event.topic)
        
        bus.subscribe("media.*", handler)
        await bus.publish("media.ingested", {})
        await bus.publish("media.updated", {})
        await bus.publish("other.topic", {})
        
        assert len(received) == 2
        assert "media.ingested" in received
        assert "media.updated" in received
    
    @pytest.mark.asyncio
    async def test_star_prefix_pattern(self):
        """Pattern '*.suffix' should match all prefixes."""
        bus = EventBus.get_instance()
        received = []
        
        async def handler(event):
            received.append(event.topic)
        
        bus.subscribe("*.completed", handler)
        await bus.publish("analysis.completed", {})
        await bus.publish("publish.completed", {})
        await bus.publish("publish.started", {})
        
        assert len(received) == 2
        assert "analysis.completed" in received
        assert "publish.completed" in received
    
    @pytest.mark.asyncio
    async def test_star_all_pattern(self):
        """Pattern '*' should match all topics."""
        bus = EventBus.get_instance()
        received = []
        
        async def handler(event):
            received.append(event.topic)
        
        bus.subscribe("*", handler)
        await bus.publish("topic.a", {})
        await bus.publish("topic.b", {})
        await bus.publish("other", {})
        
        assert len(received) == 3


class TestEventLog:
    """Tests for event logging."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_get_recent_events_newest_first(self):
        """Recent events should be returned newest first."""
        bus = EventBus.get_instance()
        
        await bus.publish("topic.1", {"order": 1})
        await bus.publish("topic.2", {"order": 2})
        await bus.publish("topic.3", {"order": 3})
        
        events = bus.get_recent_events()
        
        assert events[0].topic == "topic.3"
        assert events[2].topic == "topic.1"
    
    @pytest.mark.asyncio
    async def test_get_recent_events_with_limit(self):
        """Should respect limit parameter."""
        bus = EventBus.get_instance()
        
        for i in range(10):
            await bus.publish(f"topic.{i}", {"num": i})
        
        events = bus.get_recent_events(limit=3)
        
        assert len(events) == 3
    
    @pytest.mark.asyncio
    async def test_get_recent_events_by_topic_pattern(self):
        """Should filter by topic pattern."""
        bus = EventBus.get_instance()
        
        await bus.publish("media.ingested", {})
        await bus.publish("publish.started", {})
        await bus.publish("media.updated", {})
        
        events = bus.get_recent_events(topic_pattern="media.*")
        
        assert len(events) == 2
        assert all("media" in e.topic for e in events)
    
    @pytest.mark.asyncio
    async def test_get_recent_events_by_correlation_id(self):
        """Should filter by correlation ID."""
        bus = EventBus.get_instance()
        
        await bus.publish("topic.1", {}, correlation_id="workflow-123")
        await bus.publish("topic.2", {}, correlation_id="workflow-456")
        await bus.publish("topic.3", {}, correlation_id="workflow-123")
        
        events = bus.get_recent_events(correlation_id="workflow-123")
        
        assert len(events) == 2
        assert all(e.correlation_id == "workflow-123" for e in events)


class TestDeadLetterQueue:
    """Tests for dead-letter queue (failed events)."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_failed_handler_goes_to_dlq(self):
        """Failed handler should put event in DLQ."""
        bus = EventBus.get_instance()
        
        async def failing_handler(event):
            raise ValueError("Handler failed!")
        
        bus.subscribe("test.topic", failing_handler)
        await bus.publish("test.topic", {"data": "value"})
        
        dlq = bus.get_dead_letter_queue()
        assert len(dlq) == 1
        assert "Handler failed!" in dlq[0][1]
    
    @pytest.mark.asyncio
    async def test_clear_dlq(self):
        """Should be able to clear DLQ."""
        bus = EventBus.get_instance()
        
        async def failing_handler(event):
            raise Exception("Fail")
        
        bus.subscribe("test.topic", failing_handler)
        await bus.publish("test.topic", {})
        
        count = bus.clear_dead_letter_queue()
        
        assert count == 1
        assert len(bus.get_dead_letter_queue()) == 0


class TestEventReplay:
    """Tests for event replay."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_replay_event_by_id(self):
        """Should be able to replay an event by ID."""
        bus = EventBus.get_instance()
        received = []
        
        async def handler(event):
            received.append(event)
        
        bus.subscribe("test.topic", handler)
        event_id = await bus.publish("test.topic", {"data": "original"})
        
        # Replay the event
        success = await bus.replay_event(event_id)
        
        assert success is True
        assert len(received) == 2
    
    @pytest.mark.asyncio
    async def test_replay_nonexistent_event(self):
        """Replaying nonexistent event should return False."""
        bus = EventBus.get_instance()
        
        success = await bus.replay_event("nonexistent-id")
        
        assert success is False


class TestEventBusStats:
    """Tests for event bus statistics."""
    
    def setup_method(self):
        EventBus.reset_instance()
    
    def teardown_method(self):
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_get_stats_returns_dict(self):
        """get_stats should return statistics dict."""
        bus = EventBus.get_instance()
        
        stats = bus.get_stats()
        
        assert isinstance(stats, dict)
        assert "is_running" in stats
        assert "total_events_logged" in stats
        assert "dead_letter_count" in stats
    
    @pytest.mark.asyncio
    async def test_stats_track_events(self):
        """Stats should track published events."""
        bus = EventBus.get_instance()
        
        await bus.publish("topic.1", {})
        await bus.publish("topic.2", {})
        
        stats = bus.get_stats()
        
        assert stats["total_events_logged"] == 2
    
    def test_get_subscriber_count(self):
        """Should return correct subscriber count."""
        bus = EventBus.get_instance()
        
        async def handler(event):
            pass
        
        bus.subscribe("topic.a", handler)
        bus.subscribe("topic.a", handler)
        bus.subscribe("topic.b", handler)
        
        counts = bus.get_subscriber_count()
        
        assert counts["topic.a"] == 2
        assert counts["topic.b"] == 1
