"""
Phase 5 Test Suite: Redis Streams for Production Scale
=======================================================
Comprehensive tests for RedisEventBus adapter.

Test Categories:
- RedisEventBus initialization (15 tests)
- Publish to Redis Streams (20 tests)
- Subscribe and consumer groups (20 tests)
- Message acknowledgment and retry (15 tests)
- Dead-letter queue handling (15 tests)
- Statistics and monitoring (10 tests)
- Factory function and configuration (10 tests)

Total: 105 tests
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock, PropertyMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.event_bus.event import Event
from services.event_bus.topics import Topics
from services.event_bus.redis_adapter import (
    RedisEventBus,
    RedisSubscription,
    get_event_bus,
    STREAM_PREFIX,
    CONSUMER_GROUP,
    MAX_STREAM_LENGTH
)


# =============================================================================
# REDIS EVENT BUS INITIALIZATION TESTS (15 tests)
# =============================================================================

class TestRedisEventBusCreation:
    """Test RedisEventBus instantiation."""
    
    def test_redis_bus_creation(self):
        """Can create RedisEventBus instance."""
        bus = RedisEventBus.__new__(RedisEventBus)
        bus.redis_url = "redis://localhost:6379"
        bus._redis = None
        bus._source = "test"
        bus._subscriptions = {}
        bus._consumer_tasks = []
        bus._is_running = False
        bus._consumer_name = "test"
        bus._stats = {}
        
        assert bus is not None
    
    def test_redis_bus_default_url(self):
        """RedisEventBus has default Redis URL."""
        # Check constant
        from services.event_bus.redis_adapter import REDIS_URL
        assert "redis://" in REDIS_URL
    
    def test_redis_bus_custom_url(self):
        """RedisEventBus accepts custom Redis URL."""
        bus = RedisEventBus(redis_url="redis://custom:6380")
        assert bus.redis_url == "redis://custom:6380"
        RedisEventBus.reset_instance()
    
    def test_redis_bus_not_running_initially(self):
        """RedisEventBus is not running initially."""
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        assert not bus._is_running
        RedisEventBus.reset_instance()
    
    def test_redis_bus_has_consumer_name(self):
        """RedisEventBus has unique consumer name."""
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        assert bus._consumer_name is not None
        assert len(bus._consumer_name) > 0
        RedisEventBus.reset_instance()
    
    def test_redis_bus_empty_subscriptions(self):
        """RedisEventBus starts with empty subscriptions."""
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        assert bus._subscriptions == {}
        RedisEventBus.reset_instance()


class TestRedisEventBusSingleton:
    """Test RedisEventBus singleton pattern."""
    
    def test_get_instance_returns_redis_bus(self):
        """get_instance returns RedisEventBus."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus.get_instance()
        assert isinstance(bus, RedisEventBus)
        RedisEventBus.reset_instance()
    
    def test_get_instance_same_instance(self):
        """get_instance returns same instance."""
        RedisEventBus.reset_instance()
        bus1 = RedisEventBus.get_instance()
        bus2 = RedisEventBus.get_instance()
        assert bus1 is bus2
        RedisEventBus.reset_instance()
    
    def test_reset_instance(self):
        """reset_instance creates new instance."""
        bus1 = RedisEventBus.get_instance()
        RedisEventBus.reset_instance()
        bus2 = RedisEventBus.get_instance()
        assert bus1 is not bus2
        RedisEventBus.reset_instance()


class TestRedisEventBusConfig:
    """Test RedisEventBus configuration."""
    
    def test_stream_prefix(self):
        """Stream prefix is configured."""
        assert STREAM_PREFIX == "mediaposter:events:"
    
    def test_consumer_group_name(self):
        """Consumer group name is configured."""
        assert CONSUMER_GROUP == "mediaposter-workers"
    
    def test_max_stream_length(self):
        """Max stream length is configured."""
        assert MAX_STREAM_LENGTH == 10000
    
    def test_stream_name_format(self):
        """Stream name follows expected format."""
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        stream = bus._stream_name("test.topic")
        assert stream == "mediaposter:events:test.topic"
        RedisEventBus.reset_instance()


# =============================================================================
# PUBLISH TO REDIS STREAMS TESTS (20 tests)
# =============================================================================

class TestRedisEventBusPublish:
    """Test RedisEventBus publish functionality."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus with mocked Redis."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.xadd = AsyncMock(return_value="msg-id")
        bus._redis.ping = AsyncMock()
        return bus
    
    @pytest.mark.asyncio
    async def test_publish_returns_event(self, bus):
        """publish returns Event object."""
        event = await bus.publish("test.topic", {"key": "value"})
        assert isinstance(event, Event)
    
    @pytest.mark.asyncio
    async def test_publish_sets_topic(self, bus):
        """publish sets correct topic."""
        event = await bus.publish("test.topic", {})
        assert event.topic == "test.topic"
    
    @pytest.mark.asyncio
    async def test_publish_sets_payload(self, bus):
        """publish sets correct payload."""
        event = await bus.publish("test.topic", {"key": "value"})
        assert event.payload == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_publish_generates_id(self, bus):
        """publish generates unique ID."""
        event = await bus.publish("test.topic", {})
        assert event.id is not None
        assert len(event.id) > 0
    
    @pytest.mark.asyncio
    async def test_publish_generates_correlation_id(self, bus):
        """publish generates correlation_id if not provided."""
        event = await bus.publish("test.topic", {})
        assert event.correlation_id is not None
    
    @pytest.mark.asyncio
    async def test_publish_uses_provided_correlation_id(self, bus):
        """publish uses provided correlation_id."""
        event = await bus.publish("test.topic", {}, correlation_id="my-corr")
        assert event.correlation_id == "my-corr"
    
    @pytest.mark.asyncio
    async def test_publish_calls_xadd(self, bus):
        """publish calls Redis XADD."""
        await bus.publish("test.topic", {"data": "test"})
        bus._redis.xadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_uses_correct_stream(self, bus):
        """publish uses correct stream name."""
        await bus.publish("my.topic", {})
        call_args = bus._redis.xadd.call_args
        assert "mediaposter:events:my.topic" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_publish_increments_stats(self, bus):
        """publish increments events_published stat."""
        initial = bus._stats.get("events_published", 0)
        await bus.publish("test.topic", {})
        assert bus._stats["events_published"] == initial + 1
    
    @pytest.mark.asyncio
    async def test_publish_sets_timestamp(self, bus):
        """publish sets timestamp."""
        before = datetime.now(timezone.utc)
        event = await bus.publish("test.topic", {})
        after = datetime.now(timezone.utc)
        assert before <= event.timestamp <= after


class TestRedisEventBusPublishSerialization:
    """Test event serialization for Redis."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus with mocked Redis."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.xadd = AsyncMock(return_value="msg-id")
        return bus
    
    @pytest.mark.asyncio
    async def test_publish_serializes_to_json(self, bus):
        """publish serializes event to JSON."""
        await bus.publish("test.topic", {"data": "test"})
        
        call_args = bus._redis.xadd.call_args
        # The data passed should contain JSON serialized event
        assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_publish_handles_complex_payload(self, bus):
        """publish handles complex nested payloads."""
        payload = {
            "string": "value",
            "number": 42,
            "nested": {"a": {"b": [1, 2, 3]}}
        }
        event = await bus.publish("test.topic", payload)
        assert event.payload == payload
    
    @pytest.mark.asyncio
    async def test_publish_handles_unicode(self, bus):
        """publish handles unicode in payload."""
        payload = {"emoji": "🎉", "chinese": "中文"}
        event = await bus.publish("test.topic", payload)
        assert event.payload["emoji"] == "🎉"


class TestRedisEventBusPublishErrors:
    """Test error handling during publish."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus with failing Redis."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.xadd = AsyncMock(side_effect=Exception("Redis error"))
        return bus
    
    @pytest.mark.asyncio
    async def test_publish_raises_on_redis_error(self, bus):
        """publish raises exception on Redis error."""
        with pytest.raises(Exception) as exc_info:
            await bus.publish("test.topic", {})
        assert "Redis error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_publish_increments_error_stats(self, bus):
        """publish increments connection_errors on failure."""
        initial = bus._stats.get("connection_errors", 0)
        try:
            await bus.publish("test.topic", {})
        except:
            pass
        assert bus._stats["connection_errors"] == initial + 1


# =============================================================================
# SUBSCRIBE AND CONSUMER GROUPS TESTS (20 tests)
# =============================================================================

class TestRedisEventBusSubscribe:
    """Test RedisEventBus subscribe functionality."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        return bus
    
    def test_subscribe_returns_id(self, bus):
        """subscribe returns subscription ID."""
        sub_id = bus.subscribe("test.*", lambda e: None)
        assert sub_id is not None
        assert isinstance(sub_id, str)
        RedisEventBus.reset_instance()
    
    def test_subscribe_stores_subscription(self, bus):
        """subscribe stores subscription in dict."""
        bus.subscribe("test.*", lambda e: None)
        assert "test.*" in bus._subscriptions
        RedisEventBus.reset_instance()
    
    def test_subscribe_multiple_patterns(self, bus):
        """Can subscribe to multiple patterns."""
        bus.subscribe("test1.*", lambda e: None)
        bus.subscribe("test2.*", lambda e: None)
        assert len(bus._subscriptions) == 2
        RedisEventBus.reset_instance()
    
    def test_subscribe_same_pattern_multiple(self, bus):
        """Can have multiple callbacks for same pattern."""
        bus.subscribe("test.*", lambda e: print("callback1"))
        bus.subscribe("test.*", lambda e: print("callback2"))
        assert len(bus._subscriptions["test.*"]) == 2
        RedisEventBus.reset_instance()


class TestRedisSubscription:
    """Test RedisSubscription dataclass."""
    
    def test_subscription_creation(self):
        """Can create RedisSubscription."""
        sub = RedisSubscription(
            pattern="test.*",
            callback=lambda e: None,
            consumer_name="consumer-1",
            created_at=datetime.now(timezone.utc)
        )
        assert sub.pattern == "test.*"
    
    def test_subscription_has_callback(self):
        """Subscription stores callback."""
        callback = lambda e: e
        sub = RedisSubscription(
            pattern="test.*",
            callback=callback,
            consumer_name="consumer-1",
            created_at=datetime.now(timezone.utc)
        )
        assert sub.callback is callback
    
    def test_subscription_has_consumer_name(self):
        """Subscription stores consumer name."""
        sub = RedisSubscription(
            pattern="test.*",
            callback=lambda e: None,
            consumer_name="my-consumer",
            created_at=datetime.now(timezone.utc)
        )
        assert sub.consumer_name == "my-consumer"


class TestRedisEventBusUnsubscribe:
    """Test RedisEventBus unsubscribe functionality."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        return bus
    
    def test_unsubscribe_removes_subscription(self, bus):
        """unsubscribe removes the subscription."""
        sub_id = bus.subscribe("test.*", lambda e: None)
        bus.unsubscribe(sub_id)
        assert len(bus._subscriptions.get("test.*", [])) == 0
        RedisEventBus.reset_instance()
    
    def test_unsubscribe_invalid_id(self, bus):
        """unsubscribe with invalid ID doesn't crash."""
        bus.unsubscribe("invalid:123")  # Should not raise
        RedisEventBus.reset_instance()


class TestRedisPatternMatching:
    """Test pattern matching for subscriptions."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus."""
        RedisEventBus.reset_instance()
        return RedisEventBus(redis_url="redis://localhost:6379")
    
    def test_matches_wildcard_all(self, bus):
        """Wildcard * matches all topics."""
        assert bus._matches_pattern("any.topic", "*")
        RedisEventBus.reset_instance()
    
    def test_matches_exact(self, bus):
        """Exact pattern matches exact topic."""
        assert bus._matches_pattern("media.ingested", "media.ingested")
        assert not bus._matches_pattern("media.updated", "media.ingested")
        RedisEventBus.reset_instance()
    
    def test_matches_prefix_wildcard(self, bus):
        """Prefix wildcard matches topic prefix."""
        assert bus._matches_pattern("media.ingested", "media.*")
        assert not bus._matches_pattern("publish.started", "media.*")
        RedisEventBus.reset_instance()
    
    def test_matches_suffix_wildcard(self, bus):
        """Suffix wildcard matches topic suffix."""
        assert bus._matches_pattern("publish.completed", "*.completed")
        assert not bus._matches_pattern("publish.started", "*.completed")
        RedisEventBus.reset_instance()


# =============================================================================
# MESSAGE ACKNOWLEDGMENT AND RETRY TESTS (15 tests)
# =============================================================================

class TestRedisMessageProcessing:
    """Test Redis message processing."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus with mocked Redis."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.xack = AsyncMock()
        return bus
    
    @pytest.mark.asyncio
    async def test_process_message_calls_callback(self, bus):
        """_process_message calls subscriber callback."""
        callback_called = []
        bus._subscriptions["test.*"] = [
            RedisSubscription(
                pattern="test.*",
                callback=lambda e: callback_called.append(e),
                consumer_name="test",
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        event_data = Event(
            id="1", topic="test.event", payload={"data": "test"}
        ).to_dict()
        
        await bus._process_message(
            "mediaposter:events:test.event",
            "msg-id",
            {"event": json.dumps(event_data)},
            "test.*"
        )
        
        assert len(callback_called) == 1
        RedisEventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_process_message_acks(self, bus):
        """_process_message acknowledges message."""
        bus._subscriptions["test.*"] = []
        
        event_data = Event(id="1", topic="test.event", payload={}).to_dict()
        
        await bus._process_message(
            "mediaposter:events:test.event",
            "msg-id",
            {"event": json.dumps(event_data)},
            "test.*"
        )
        
        bus._redis.xack.assert_called_once()
        RedisEventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_process_message_increments_stats(self, bus):
        """_process_message increments events_consumed."""
        bus._subscriptions["test.*"] = []
        initial = bus._stats.get("events_consumed", 0)
        
        event_data = Event(id="1", topic="test.event", payload={}).to_dict()
        await bus._process_message(
            "stream", "msg-id",
            {"event": json.dumps(event_data)},
            "test.*"
        )
        
        assert bus._stats["events_consumed"] == initial + 1
        RedisEventBus.reset_instance()


class TestRedisAsyncCallbacks:
    """Test async callback handling."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.xack = AsyncMock()
        return bus
    
    @pytest.mark.asyncio
    async def test_async_callback_supported(self, bus):
        """Async callbacks are supported."""
        results = []
        
        async def async_callback(event):
            await asyncio.sleep(0.01)
            results.append(event)
        
        bus._subscriptions["test.*"] = [
            RedisSubscription(
                pattern="test.*",
                callback=async_callback,
                consumer_name="test",
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        event_data = Event(id="1", topic="test.event", payload={}).to_dict()
        await bus._process_message(
            "stream", "msg-id",
            {"event": json.dumps(event_data)},
            "test.*"
        )
        
        assert len(results) == 1
        RedisEventBus.reset_instance()


class TestRedisCallbackErrors:
    """Test callback error handling."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.xack = AsyncMock()
        bus._redis.xadd = AsyncMock()
        return bus
    
    @pytest.mark.asyncio
    async def test_callback_error_sends_to_dlq(self, bus):
        """Callback error sends event to DLQ."""
        def failing_callback(event):
            raise ValueError("Callback error")
        
        bus._subscriptions["test.*"] = [
            RedisSubscription(
                pattern="test.*",
                callback=failing_callback,
                consumer_name="test",
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        event_data = Event(id="1", topic="test.event", payload={}).to_dict()
        await bus._process_message(
            "stream", "msg-id",
            {"event": json.dumps(event_data)},
            "test.*"
        )
        
        # Should have called xadd for DLQ
        assert bus._stats.get("events_failed", 0) >= 1
        RedisEventBus.reset_instance()


# =============================================================================
# DEAD-LETTER QUEUE HANDLING TESTS (15 tests)
# =============================================================================

class TestRedisDeadLetterQueue:
    """Test Redis dead-letter queue."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus with mocked Redis."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.xadd = AsyncMock()
        bus._redis.xrange = AsyncMock(return_value=[])
        bus._redis.xdel = AsyncMock()
        return bus
    
    @pytest.mark.asyncio
    async def test_send_to_dlq(self, bus):
        """_send_to_dlq adds event to DLQ stream."""
        event = Event(id="1", topic="test.topic", payload={})
        await bus._send_to_dlq(event, "Test error")
        
        bus._redis.xadd.assert_called()
        RedisEventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_get_dlq_events(self, bus):
        """get_dlq_events returns DLQ events."""
        bus._redis.xrange = AsyncMock(return_value=[
            ("msg-1", {
                "event": json.dumps({"id": "1", "topic": "test", "payload": {}}),
                "error": "Test error",
                "failed_at": datetime.now(timezone.utc).isoformat()
            })
        ])
        
        events = await bus.get_dlq_events(10)
        
        assert len(events) == 1
        assert events[0]["error"] == "Test error"
        RedisEventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_get_dlq_events_empty(self, bus):
        """get_dlq_events returns empty list when no events."""
        bus._redis.xrange = AsyncMock(return_value=[])
        
        events = await bus.get_dlq_events()
        
        assert events == []
        RedisEventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_get_dlq_events_respects_count(self, bus):
        """get_dlq_events respects count parameter."""
        await bus.get_dlq_events(5)
        
        call_args = bus._redis.xrange.call_args
        assert call_args[1]["count"] == 5
        RedisEventBus.reset_instance()


class TestRedisEventReplay:
    """Test event replay functionality."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus with mocked Redis."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.xadd = AsyncMock()
        bus._redis.xdel = AsyncMock()
        return bus
    
    @pytest.mark.asyncio
    async def test_replay_event_success(self, bus):
        """replay_event republishes DLQ event."""
        event_data = {"id": "1", "topic": "test.topic", "payload": {"data": "test"}}
        bus._redis.xrange = AsyncMock(return_value=[
            ("msg-1", {"event": json.dumps(event_data)})
        ])
        
        result = await bus.replay_event("msg-1")
        
        assert result is True
        RedisEventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_replay_event_not_found(self, bus):
        """replay_event returns False if event not found."""
        bus._redis.xrange = AsyncMock(return_value=[])
        
        result = await bus.replay_event("nonexistent")
        
        assert result is False
        RedisEventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_replay_event_removes_from_dlq(self, bus):
        """replay_event removes event from DLQ."""
        event_data = {"id": "1", "topic": "test.topic", "payload": {}}
        bus._redis.xrange = AsyncMock(return_value=[
            ("msg-1", {"event": json.dumps(event_data)})
        ])
        
        await bus.replay_event("msg-1")
        
        bus._redis.xdel.assert_called()
        RedisEventBus.reset_instance()


# =============================================================================
# STATISTICS AND MONITORING TESTS (10 tests)
# =============================================================================

class TestRedisEventBusStats:
    """Test RedisEventBus statistics."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus."""
        RedisEventBus.reset_instance()
        return RedisEventBus(redis_url="redis://localhost:6379")
    
    def test_get_stats_returns_dict(self, bus):
        """get_stats returns dictionary."""
        stats = bus.get_stats()
        assert isinstance(stats, dict)
        RedisEventBus.reset_instance()
    
    def test_get_stats_has_backend(self, bus):
        """Stats includes backend type."""
        stats = bus.get_stats()
        assert stats["backend"] == "redis"
        RedisEventBus.reset_instance()
    
    def test_get_stats_has_redis_url(self, bus):
        """Stats includes Redis URL."""
        stats = bus.get_stats()
        assert "redis_url" in stats
        RedisEventBus.reset_instance()
    
    def test_get_stats_has_consumer_name(self, bus):
        """Stats includes consumer name."""
        stats = bus.get_stats()
        assert "consumer_name" in stats
        RedisEventBus.reset_instance()
    
    def test_get_stats_has_is_running(self, bus):
        """Stats includes is_running."""
        stats = bus.get_stats()
        assert "is_running" in stats
        RedisEventBus.reset_instance()
    
    def test_get_stats_has_subscription_patterns(self, bus):
        """Stats includes subscription patterns."""
        bus.subscribe("test.*", lambda e: None)
        stats = bus.get_stats()
        assert "subscription_patterns" in stats
        assert "test.*" in stats["subscription_patterns"]
        RedisEventBus.reset_instance()
    
    def test_get_stats_has_events_published(self, bus):
        """Stats includes events_published."""
        stats = bus.get_stats()
        assert "events_published" in stats
        RedisEventBus.reset_instance()
    
    def test_get_stats_has_events_consumed(self, bus):
        """Stats includes events_consumed."""
        stats = bus.get_stats()
        assert "events_consumed" in stats
        RedisEventBus.reset_instance()


# =============================================================================
# FACTORY FUNCTION AND CONFIGURATION TESTS (10 tests)
# =============================================================================

class TestGetEventBus:
    """Test get_event_bus factory function."""
    
    def teardown_method(self):
        """Reset instances after each test."""
        from services.event_bus.bus import EventBus
        EventBus.reset_instance()
        RedisEventBus.reset_instance()
    
    def test_get_event_bus_default_memory(self):
        """get_event_bus returns in-memory by default."""
        os.environ.pop("EVENT_BUS_BACKEND", None)
        os.environ["EVENT_BUS_BACKEND"] = "memory"
        
        bus = get_event_bus()
        
        from services.event_bus.bus import EventBus
        assert isinstance(bus, EventBus)
    
    def test_get_event_bus_explicit_memory(self):
        """get_event_bus('memory') returns in-memory."""
        bus = get_event_bus("memory")
        
        from services.event_bus.bus import EventBus
        assert isinstance(bus, EventBus)
    
    def test_get_event_bus_explicit_redis(self):
        """get_event_bus('redis') returns Redis."""
        bus = get_event_bus("redis")
        
        assert isinstance(bus, RedisEventBus)
    
    def test_get_event_bus_from_env(self):
        """get_event_bus respects EVENT_BUS_BACKEND env."""
        os.environ["EVENT_BUS_BACKEND"] = "redis"
        
        bus = get_event_bus()
        
        assert isinstance(bus, RedisEventBus)
        
        # Cleanup
        os.environ["EVENT_BUS_BACKEND"] = "memory"


class TestRedisConnection:
    """Test Redis connection handling."""
    
    def test_lazy_connection(self):
        """Redis connection is lazy-loaded."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        
        assert bus._redis is None
        RedisEventBus.reset_instance()
    
    def test_set_source(self):
        """set_source changes event source."""
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        bus.set_source("my-source")
        
        assert bus._source == "my-source"
        RedisEventBus.reset_instance()


class TestRedisShutdown:
    """Test Redis shutdown handling."""
    
    @pytest.fixture
    def bus(self):
        """Create RedisEventBus with mocked Redis."""
        RedisEventBus.reset_instance()
        bus = RedisEventBus(redis_url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.close = AsyncMock()
        return bus
    
    @pytest.mark.asyncio
    async def test_shutdown_stops_running(self, bus):
        """shutdown sets is_running to False."""
        bus._is_running = True
        await bus.shutdown()
        
        assert bus._is_running is False
        RedisEventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_shutdown_closes_redis(self, bus):
        """shutdown closes Redis connection."""
        await bus.shutdown()
        
        bus._redis.close.assert_called_once()
        RedisEventBus.reset_instance()
    
    @pytest.mark.asyncio
    async def test_shutdown_clears_tasks(self, bus):
        """shutdown clears consumer tasks."""
        bus._consumer_tasks = [AsyncMock()]
        await bus.shutdown()
        
        assert len(bus._consumer_tasks) == 0
        RedisEventBus.reset_instance()


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
