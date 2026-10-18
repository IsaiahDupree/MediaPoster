"""
Unit Tests: Topic Routing Logic
================================
Test the dispatcher: topic → handler routing with wildcards.

These tests verify:
- Exact topic matching
- Wildcard pattern matching (*.completed, media.*)
- Handler registration and unregistration
- Multiple handlers per topic
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from services.event_bus import EventBus, Event, Topics


class TestTopicMatching:
    """Test topic pattern matching logic."""
    
    def test_exact_topic_match(self):
        """Exact topic should match itself."""
        assert Topics.matches_pattern("media.ingested", "media.ingested") is True
        assert Topics.matches_pattern("media.ingested", "media.updated") is False
    
    def test_wildcard_suffix_match(self):
        """Pattern 'media.*' should match any media.X topic."""
        assert Topics.matches_pattern("media.*", "media.ingested") is True
        assert Topics.matches_pattern("media.*", "media.updated") is True
        assert Topics.matches_pattern("media.*", "publish.completed") is False
    
    def test_wildcard_prefix_match(self):
        """Pattern '*.completed' should match any X.completed topic."""
        assert Topics.matches_pattern("*.completed", "analysis.completed") is True
        assert Topics.matches_pattern("*.completed", "publish.completed") is True
        assert Topics.matches_pattern("*.completed", "media.started") is False
    
    def test_global_wildcard_match(self):
        """Pattern '*' should match everything."""
        assert Topics.matches_pattern("*", "media.ingested") is True
        assert Topics.matches_pattern("*", "publish.completed") is True
        assert Topics.matches_pattern("*", "any.topic.at.all") is True
    
    def test_nested_topic_match(self):
        """Nested topics like media.analysis.completed should match."""
        assert Topics.matches_pattern("media.analysis.*", "media.analysis.completed") is True
        assert Topics.matches_pattern("media.analysis.*", "media.analysis.started") is True
        assert Topics.matches_pattern("media.analysis.*", "media.ingested") is False
    
    def test_no_match_different_prefix(self):
        """Different prefixes should not match."""
        assert Topics.matches_pattern("media.*", "publish.completed") is False
        assert Topics.matches_pattern("analysis.*", "media.updated") is False


class TestHandlerRegistration:
    """Test handler registration and dispatch."""
    
    @pytest.fixture
    def fresh_bus(self):
        """Fresh EventBus instance."""
        EventBus.reset_instance()
        bus = EventBus.get_instance()
        yield bus
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_single_handler_receives_event(self, fresh_bus):
        """A registered handler should receive matching events."""
        received = []
        
        async def handler(event):
            received.append(event)
        
        fresh_bus.subscribe("test.topic", handler)
        await fresh_bus.publish("test.topic", {"data": "value"})
        
        assert len(received) == 1
        assert received[0].payload["data"] == "value"
    
    @pytest.mark.asyncio
    async def test_multiple_handlers_same_topic(self, fresh_bus):
        """Multiple handlers for same topic all receive the event."""
        received_1 = []
        received_2 = []
        
        async def handler_1(event):
            received_1.append(event)
        
        async def handler_2(event):
            received_2.append(event)
        
        fresh_bus.subscribe("test.topic", handler_1)
        fresh_bus.subscribe("test.topic", handler_2)
        await fresh_bus.publish("test.topic", {"data": "value"})
        
        assert len(received_1) == 1
        assert len(received_2) == 1
    
    @pytest.mark.asyncio
    async def test_wildcard_handler_receives_matching_events(self, fresh_bus):
        """Wildcard handler receives all matching events."""
        received = []
        
        async def handler(event):
            received.append(event)
        
        fresh_bus.subscribe("media.*", handler)
        await fresh_bus.publish("media.ingested", {"id": "1"})
        await fresh_bus.publish("media.updated", {"id": "2"})
        await fresh_bus.publish("publish.completed", {"id": "3"})
        
        assert len(received) == 2
        topics = [e.topic for e in received]
        assert "media.ingested" in topics
        assert "media.updated" in topics
        assert "publish.completed" not in topics
    
    @pytest.mark.asyncio
    async def test_unsubscribe_removes_handler(self, fresh_bus):
        """Unsubscribed handler should not receive events."""
        received = []
        
        async def handler(event):
            received.append(event)
        
        fresh_bus.subscribe("test.topic", handler)
        await fresh_bus.publish("test.topic", {"msg": "first"})
        
        assert len(received) == 1
        
        fresh_bus.unsubscribe("test.topic", handler)
        await fresh_bus.publish("test.topic", {"msg": "second"})
        
        assert len(received) == 1  # Still 1, didn't receive second
    
    @pytest.mark.asyncio
    async def test_handler_failure_goes_to_dlq(self, fresh_bus):
        """Failed handlers should put events in dead-letter queue."""
        async def failing_handler(event):
            raise ValueError("Handler failed intentionally")
        
        fresh_bus.subscribe("test.topic", failing_handler)
        await fresh_bus.publish("test.topic", {"data": "value"})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) == 1
        event, error = dlq[0]
        assert "Handler failed intentionally" in error
    
    @pytest.mark.asyncio
    async def test_one_handler_failure_doesnt_block_others(self, fresh_bus):
        """One handler failing shouldn't prevent other handlers from running."""
        received = []
        
        async def failing_handler(event):
            raise ValueError("I fail")
        
        async def good_handler(event):
            received.append(event)
        
        fresh_bus.subscribe("test.topic", failing_handler)
        fresh_bus.subscribe("test.topic", good_handler)
        
        await fresh_bus.publish("test.topic", {"data": "value"})
        
        assert len(received) == 1  # Good handler still received it


class TestTopicsRegistry:
    """Test Topics class constants and utilities."""
    
    def test_media_lifecycle_topics_exist(self):
        """Media lifecycle topics should be defined."""
        assert hasattr(Topics, "MEDIA_INGESTED")
        assert hasattr(Topics, "MEDIA_UPDATED")
        assert hasattr(Topics, "MEDIA_DELETED")
    
    def test_analysis_topics_exist(self):
        """Analysis pipeline topics should be defined."""
        assert hasattr(Topics, "ANALYSIS_REQUESTED")
        assert hasattr(Topics, "ANALYSIS_STARTED")
        assert hasattr(Topics, "ANALYSIS_COMPLETED")
        assert hasattr(Topics, "ANALYSIS_FAILED")
    
    def test_publishing_topics_exist(self):
        """Publishing pipeline topics should be defined."""
        assert hasattr(Topics, "PUBLISH_REQUESTED")
        assert hasattr(Topics, "PUBLISH_STARTED")
        assert hasattr(Topics, "PUBLISH_COMPLETED")
        assert hasattr(Topics, "PUBLISH_FAILED")
    
    def test_scheduling_topics_exist(self):
        """Scheduling topics should be defined."""
        assert hasattr(Topics, "SCHEDULE_CREATED")
        assert hasattr(Topics, "SCHEDULE_DUE")
        assert hasattr(Topics, "SCHEDULER_TICK")
    
    def test_topic_naming_convention(self):
        """Topics should follow domain.entity.action naming."""
        # All topics should be lowercase with dots
        topics = [
            Topics.MEDIA_INGESTED,
            Topics.ANALYSIS_COMPLETED,
            Topics.PUBLISH_STARTED,
        ]
        for topic in topics:
            assert topic == topic.lower()
            assert "." in topic


class TestEventBusStats:
    """Test EventBus statistics and introspection."""
    
    @pytest.fixture
    def fresh_bus(self):
        EventBus.reset_instance()
        bus = EventBus.get_instance()
        yield bus
        EventBus.reset_instance()
    
    def test_get_subscriber_count(self, fresh_bus):
        """Should return count of subscribers per pattern."""
        async def h1(e): pass
        async def h2(e): pass
        
        fresh_bus.subscribe("topic.a", h1)
        fresh_bus.subscribe("topic.a", h2)
        fresh_bus.subscribe("topic.b", h1)
        
        counts = fresh_bus.get_subscriber_count()
        assert counts["topic.a"] == 2
        assert counts["topic.b"] == 1
    
    def test_get_stats(self, fresh_bus):
        """Should return bus statistics."""
        stats = fresh_bus.get_stats()
        
        assert "is_running" in stats
        assert "total_events_logged" in stats
        assert "dead_letter_count" in stats
        assert "subscriber_patterns" in stats
        assert stats["is_running"] is True
    
    @pytest.mark.asyncio
    async def test_event_log_size_limit(self, fresh_bus):
        """Event log should respect max size limit."""
        fresh_bus._max_log_size = 10
        
        for i in range(20):
            await fresh_bus.publish("test.topic", {"i": i})
        
        assert len(fresh_bus._event_log) == 10
        # Should have the most recent events
        assert fresh_bus._event_log[-1].payload["i"] == 19
