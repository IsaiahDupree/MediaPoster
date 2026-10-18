"""
Unit Tests: Event Bus Routing & Topic Matching
==============================================
Pure logic tests for event routing without broker/DB.

Tests:
- Topic pattern matching (wildcards, exact matches)
- Event routing to correct handlers
- Multiple subscribers per topic
- Topic pattern precedence
"""

import pytest
import asyncio
from typing import List
from unittest.mock import AsyncMock

from services.event_bus import EventBus, Event, Topics
from services.event_bus.topics import Topics as TopicsClass


class TestTopicPatternMatching:
    """Test topic pattern matching logic."""
    
    @pytest.fixture
    def bus(self):
        EventBus.reset_instance()
        bus = EventBus.get_instance()
        yield bus
        EventBus.reset_instance()
    
    def test_exact_match(self, bus):
        """Exact topic matches work."""
        assert TopicsClass.matches_pattern("media.ingested", "media.ingested")
        assert not TopicsClass.matches_pattern("media.ingested", "media.updated")
    
    def test_wildcard_suffix(self, bus):
        """Wildcard suffix matches multiple topics."""
        assert TopicsClass.matches_pattern("media.*", "media.ingested")
        assert TopicsClass.matches_pattern("media.*", "media.updated")
        assert TopicsClass.matches_pattern("media.*", "media.deleted")
        assert not TopicsClass.matches_pattern("media.*", "publish.completed")
    
    def test_wildcard_prefix(self, bus):
        """Wildcard prefix matches multiple topics."""
        assert TopicsClass.matches_pattern("*.completed", "media.analysis.completed")
        assert TopicsClass.matches_pattern("*.completed", "publish.completed")
        assert TopicsClass.matches_pattern("*.completed", "analysis.completed")
        assert not TopicsClass.matches_pattern("*.completed", "publish.started")
    
    def test_wildcard_middle(self, bus):
        """Wildcard in middle - current implementation supports prefix/suffix only."""
        # Current implementation supports:
        # - prefix.* (wildcard at end)
        # - *.suffix (wildcard at start)
        # - * (matches everything)
        # Middle wildcards like "media.*.completed" are NOT supported
        # Use prefix/suffix patterns instead:
        assert TopicsClass.matches_pattern("media.*", "media.analysis.completed")
        assert TopicsClass.matches_pattern("*.completed", "media.analysis.completed")
        # Middle wildcard pattern doesn't work
        assert not TopicsClass.matches_pattern("media.*.completed", "media.analysis.completed")
    
    def test_all_wildcard(self, bus):
        """Single wildcard matches all topics."""
        assert TopicsClass.matches_pattern("*", "media.ingested")
        assert TopicsClass.matches_pattern("*", "publish.completed")
        assert TopicsClass.matches_pattern("*", "any.topic.here")
    
    def test_case_sensitive(self, bus):
        """Topic matching is case-sensitive."""
        assert TopicsClass.matches_pattern("media.ingested", "media.ingested")
        assert not TopicsClass.matches_pattern("media.ingested", "MEDIA.INGESTED")
    
    def test_empty_pattern(self, bus):
        """Empty pattern behavior - empty matches empty."""
        # Empty pattern matches empty topic (reasonable behavior)
        assert TopicsClass.matches_pattern("", "")
        # Empty pattern doesn't match non-empty topics
        assert not TopicsClass.matches_pattern("", "media.ingested")


class TestEventRouting:
    """Test event routing to correct handlers."""
    
    @pytest.fixture
    def bus(self):
        EventBus.reset_instance()
        bus = EventBus.get_instance()
        yield bus
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_exact_topic_routing(self, bus):
        """Events route to exact topic subscribers."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        bus.subscribe("media.ingested", handler1)
        bus.subscribe("media.updated", handler2)
        
        await bus.publish("media.ingested", {"media_id": "123"})
        await asyncio.sleep(0.1)
        
        handler1.assert_called_once()
        handler2.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_wildcard_routing(self, bus):
        """Events route to wildcard pattern subscribers."""
        handler = AsyncMock()
        bus.subscribe("media.*", handler)
        
        await bus.publish("media.ingested", {"media_id": "123"})
        await bus.publish("media.updated", {"media_id": "456"})
        await asyncio.sleep(0.1)
        
        assert handler.call_count == 2
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_topic(self, bus):
        """Multiple subscribers to same topic all receive event."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        handler3 = AsyncMock()
        
        bus.subscribe("publish.completed", handler1)
        bus.subscribe("publish.completed", handler2)
        bus.subscribe("publish.completed", handler3)
        
        await bus.publish("publish.completed", {"post_id": "123"})
        await asyncio.sleep(0.1)
        
        handler1.assert_called_once()
        handler2.assert_called_once()
        handler3.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_patterns_match(self, bus):
        """Event matching multiple patterns goes to all."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        bus.subscribe("media.*", handler1)
        bus.subscribe("*.completed", handler2)
        
        await bus.publish("media.analysis.completed", {"media_id": "123"})
        await asyncio.sleep(0.1)
        
        handler1.assert_called_once()
        handler2.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_subscribers_no_error(self, bus):
        """Publishing to topic with no subscribers doesn't error."""
        await bus.publish("unknown.topic", {"data": "test"})
        await asyncio.sleep(0.1)
        # Should not raise


class TestEventCorrelation:
    """Test correlation ID tracking."""
    
    @pytest.fixture
    def bus(self):
        EventBus.reset_instance()
        bus = EventBus.get_instance()
        yield bus
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_correlation_id_preserved(self, bus):
        """Correlation ID is preserved through event."""
        correlation_id = "test-workflow-123"
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        bus.subscribe("test.*", handler)
        
        await bus.publish("test.event", {"data": 1}, correlation_id=correlation_id)
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0].correlation_id == correlation_id
    
    @pytest.mark.asyncio
    async def test_auto_generated_correlation_id(self, bus):
        """Correlation ID auto-generated if not provided."""
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        bus.subscribe("test.*", handler)
        
        await bus.publish("test.event", {"data": 1})
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0].correlation_id is not None
        assert len(received_events[0].correlation_id) > 0


class TestEventMetadata:
    """Test event metadata and source tracking."""
    
    @pytest.fixture
    def bus(self):
        EventBus.reset_instance()
        bus = EventBus.get_instance()
        yield bus
        EventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_source_tracking(self, bus):
        """Event source is tracked."""
        bus.set_source("test-service")
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        bus.subscribe("test.*", handler)
        
        await bus.publish("test.event", {"data": 1})
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0].source == "test-service"
    
    @pytest.mark.asyncio
    async def test_custom_metadata(self, bus):
        """Custom metadata is preserved."""
        metadata = {"retry_count": 3, "priority": "high"}
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        bus.subscribe("test.*", handler)
        
        await bus.publish("test.event", {"data": 1}, metadata=metadata)
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0].metadata["retry_count"] == 3
        assert received_events[0].metadata["priority"] == "high"

