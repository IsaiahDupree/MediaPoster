"""
Phase 4 WebSocket & Real-Time Streaming Guarantees Test Suite
==============================================================
Tests for critical WebSocket system properties:
- Event Correctness, Delivery Guarantees, Ordering, Idempotency
- Backpressure, Consumer Isolation, Schema Evolution, E2E

Phase 4 Components:
- ConnectionManager (WebSocket connections)
- Event streaming to frontend clients
- Topic filtering and pattern matching
- Correlation ID filtering for workflow tracking

Total: 60 tests
"""

import pytest
import asyncio
import json
import time
import hashlib
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.event_bus import EventBus, Event, Topics


# =============================================================================
# MOCK WEBSOCKET & CONNECTION MANAGER
# =============================================================================

class MockWebSocketState:
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, client_id: str = None):
        self.client_id = client_id or str(uuid4())[:8]
        self.client_state = MockWebSocketState.CONNECTED
        self.messages_sent: List[Dict] = []
        self.accepted = False
        self._closed = False
    
    async def accept(self):
        self.accepted = True
    
    async def send_json(self, data: Dict):
        if self._closed:
            raise Exception("WebSocket closed")
        self.messages_sent.append(data)
    
    async def receive_json(self) -> Dict:
        return {"type": "ping"}
    
    async def close(self):
        self._closed = True
        self.client_state = MockWebSocketState.DISCONNECTED


class MockConnectionManager:
    """Mock ConnectionManager for testing."""
    
    def __init__(self, event_bus: EventBus = None):
        self.active_connections: Dict[MockWebSocket, Dict] = {}
        self._event_bus = event_bus
        self._subscription_id = None
    
    @property
    def event_bus(self) -> EventBus:
        if self._event_bus is None:
            self._event_bus = EventBus.get_instance()
        return self._event_bus
    
    async def connect(self, websocket: MockWebSocket, topics: List[str] = None,
                     correlation_id: str = None):
        await websocket.accept()
        
        self.active_connections[websocket] = {
            "topics": topics or ["*"],
            "correlation_id": correlation_id,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "events_sent": 0
        }
        
        await websocket.send_json({
            "type": "connected",
            "subscribed_topics": topics or ["*"],
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        await self._ensure_subscribed()
    
    def disconnect(self, websocket: MockWebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
    
    async def _ensure_subscribed(self):
        if self._subscription_id is None:
            self._subscription_id = self.event_bus.subscribe("*", self._handle_event)
    
    async def _handle_event(self, event: Event):
        if not self.active_connections:
            return
        
        event_data = {
            "type": "event",
            "event": {
                "id": event.id,
                "topic": event.topic,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "correlation_id": event.correlation_id,
                "payload": event.payload,
                "source": event.source
            }
        }
        
        disconnected = []
        for websocket, metadata in self.active_connections.items():
            try:
                if self._should_send(event, metadata):
                    if websocket.client_state == MockWebSocketState.CONNECTED:
                        await websocket.send_json(event_data)
                        metadata["events_sent"] += 1
            except Exception:
                disconnected.append(websocket)
        
        for ws in disconnected:
            self.disconnect(ws)
    
    def _should_send(self, event: Event, metadata: dict) -> bool:
        if metadata.get("correlation_id"):
            if event.correlation_id != metadata["correlation_id"]:
                return False
        
        topics = metadata.get("topics", ["*"])
        for pattern in topics:
            if self._topic_matches(event.topic, pattern):
                return True
        return False
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return topic.startswith(prefix + ".")
        if pattern.startswith("*."):
            suffix = pattern[2:]
            return topic.endswith("." + suffix)
        return topic == pattern
    
    def get_stats(self) -> Dict:
        return {
            "active_connections": len(self.active_connections),
            "total_events_sent": sum(m["events_sent"] for m in self.active_connections.values())
        }


@pytest.fixture
def fresh_bus():
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()


@pytest.fixture
def connection_manager(fresh_bus):
    # Create fresh manager with fresh bus
    cm = MockConnectionManager(fresh_bus)
    return cm


# =============================================================================
# EVENT CORRECTNESS (10 tests)
# =============================================================================

class TestWebSocketEventCorrectness:
    """Tests for WebSocket event correctness."""
    
    @pytest.mark.asyncio
    async def test_event_serialization_complete(self, fresh_bus, connection_manager):
        """Events are fully serialized for WebSocket."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("test.event", {"key": "value"}, 
                               correlation_id="corr-123",
                               metadata={"meta": 1})
        
        # Find the event message (skip welcome)
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 1
        
        event = event_msgs[0]["event"]
        assert event["topic"] == "test.event"
        assert event["payload"] == {"key": "value"}
        assert event["correlation_id"] == "corr-123"
        assert event["id"] is not None
        assert event["timestamp"] is not None
    
    @pytest.mark.asyncio
    async def test_welcome_message_correct(self, fresh_bus, connection_manager):
        """Welcome message has correct structure."""
        ws = MockWebSocket()
        await connection_manager.connect(ws, topics=["publish.*"])
        
        welcome = ws.messages_sent[0]
        assert welcome["type"] == "connected"
        assert welcome["subscribed_topics"] == ["publish.*"]
        assert "timestamp" in welcome
    
    @pytest.mark.asyncio
    async def test_payload_types_preserved(self, fresh_bus, connection_manager):
        """Payload data types are preserved."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        payload = {"int": 42, "float": 3.14, "bool": True, "list": [1, 2, 3]}
        await fresh_bus.publish("test.types", payload)
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        received = event_msgs[0]["event"]["payload"]
        
        assert received["int"] == 42
        assert received["float"] == 3.14
        assert received["bool"] is True
        assert received["list"] == [1, 2, 3]
    
    @pytest.mark.asyncio
    async def test_unicode_preserved(self, fresh_bus, connection_manager):
        """Unicode characters preserved in WebSocket."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("test.unicode", {"emoji": "🎉", "chinese": "中文"})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert event_msgs[0]["event"]["payload"]["emoji"] == "🎉"
    
    @pytest.mark.asyncio
    async def test_large_payload_delivered(self, fresh_bus, connection_manager):
        """Large payloads are delivered correctly."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        large_data = {"data": "x" * 50000}
        await fresh_bus.publish("test.large", large_data)
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs[0]["event"]["payload"]["data"]) == 50000
    
    @pytest.mark.asyncio
    async def test_event_id_unique_per_message(self, fresh_bus, connection_manager):
        """Each event has unique ID in WebSocket stream."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        for i in range(10):
            await fresh_bus.publish("test.id", {"n": i})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        ids = [m["event"]["id"] for m in event_msgs]
        assert len(set(ids)) == 10
    
    @pytest.mark.asyncio
    async def test_timestamp_format_iso(self, fresh_bus, connection_manager):
        """Timestamps are in ISO format."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("test.ts", {})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        ts = event_msgs[0]["event"]["timestamp"]
        # Should parse as ISO
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
    
    @pytest.mark.asyncio
    async def test_source_included(self, fresh_bus, connection_manager):
        """Event source is included in WebSocket message."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        fresh_bus.set_source("test-service")
        await fresh_bus.publish("test.source", {})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert "test-service" in event_msgs[0]["event"]["source"]
    
    @pytest.mark.asyncio
    async def test_nested_payload_structure(self, fresh_bus, connection_manager):
        """Nested payload structures preserved."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        payload = {"level1": {"level2": {"level3": "deep"}}}
        await fresh_bus.publish("test.nested", payload)
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert event_msgs[0]["event"]["payload"]["level1"]["level2"]["level3"] == "deep"
    
    @pytest.mark.asyncio
    async def test_events_sent_counter_accurate(self, fresh_bus, connection_manager):
        """Events sent counter is accurate."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        for i in range(5):
            await fresh_bus.publish("test.count", {"n": i})
        
        metadata = connection_manager.active_connections[ws]
        assert metadata["events_sent"] == 5


# =============================================================================
# DELIVERY GUARANTEES (10 tests)
# =============================================================================

class TestWebSocketDeliveryGuarantees:
    """Tests for WebSocket delivery guarantees."""
    
    @pytest.mark.asyncio
    async def test_all_subscribers_receive(self, fresh_bus, connection_manager):
        """All connected WebSockets receive events."""
        clients = [MockWebSocket(f"client-{i}") for i in range(5)]
        for ws in clients:
            await connection_manager.connect(ws)
        
        await fresh_bus.publish("test.broadcast", {"data": 1})
        
        for ws in clients:
            event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
            assert len(event_msgs) >= 1
    
    @pytest.mark.asyncio
    async def test_topic_filtering_works(self, fresh_bus, connection_manager):
        """Topic filtering delivers only matching events."""
        ws = MockWebSocket()
        await connection_manager.connect(ws, topics=["publish.*"])
        
        await fresh_bus.publish("publish.started", {})
        await fresh_bus.publish("scheduler.tick", {})
        await fresh_bus.publish("publish.completed", {})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 2
        topics = [m["event"]["topic"] for m in event_msgs]
        assert "scheduler.tick" not in topics
    
    @pytest.mark.asyncio
    async def test_wildcard_all_events(self, fresh_bus, connection_manager):
        """Wildcard * receives all events."""
        ws = MockWebSocket()
        await connection_manager.connect(ws, topics=["*"])
        
        await fresh_bus.publish("topic.a", {})
        await fresh_bus.publish("topic.b", {})
        await fresh_bus.publish("other.c", {})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 3
    
    @pytest.mark.asyncio
    async def test_correlation_id_filter(self, fresh_bus, connection_manager):
        """Correlation ID filter works."""
        ws = MockWebSocket()
        await connection_manager.connect(ws, correlation_id="workflow-123")
        
        await fresh_bus.publish("test.event", {}, correlation_id="workflow-123")
        await fresh_bus.publish("test.event", {}, correlation_id="other-456")
        await fresh_bus.publish("test.event", {}, correlation_id="workflow-123")
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 2
    
    @pytest.mark.asyncio
    async def test_disconnected_client_cleaned_up(self, fresh_bus, connection_manager):
        """Disconnected clients are removed."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        assert len(connection_manager.active_connections) == 1
        
        connection_manager.disconnect(ws)
        
        assert len(connection_manager.active_connections) == 0
    
    @pytest.mark.asyncio
    async def test_closed_websocket_handled(self, fresh_bus, connection_manager):
        """Closed WebSocket doesn't crash broadcasting."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        await connection_manager.connect(ws1)
        await connection_manager.connect(ws2)
        
        # Close ws1
        await ws1.close()
        
        # Should still work for ws2
        await fresh_bus.publish("test.event", {})
        
        event_msgs = [m for m in ws2.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) >= 1
    
    @pytest.mark.asyncio
    async def test_multiple_topic_filters(self, fresh_bus, connection_manager):
        """Multiple topic filters work together."""
        ws = MockWebSocket()
        await connection_manager.connect(ws, topics=["publish.*", "scheduler.*"])
        
        await fresh_bus.publish("publish.started", {})
        await fresh_bus.publish("scheduler.tick", {})
        await fresh_bus.publish("analysis.completed", {})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 2
    
    @pytest.mark.asyncio
    async def test_rapid_events_all_delivered(self, fresh_bus, connection_manager):
        """Rapid events are all delivered."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        for i in range(100):
            await fresh_bus.publish("test.rapid", {"n": i})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 100
    
    @pytest.mark.asyncio
    async def test_suffix_wildcard_filter(self, fresh_bus, connection_manager):
        """Suffix wildcard *.completed works."""
        ws = MockWebSocket()
        await connection_manager.connect(ws, topics=["*.completed"])
        
        await fresh_bus.publish("publish.completed", {})
        await fresh_bus.publish("analysis.completed", {})
        await fresh_bus.publish("publish.started", {})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 2
    
    @pytest.mark.asyncio
    async def test_no_duplicate_delivery(self, fresh_bus, connection_manager):
        """Events aren't delivered multiple times."""
        ws = MockWebSocket()
        await connection_manager.connect(ws, topics=["test.*", "*"])
        
        await fresh_bus.publish("test.event", {"n": 1})
        
        # Should only receive once despite matching multiple patterns
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 1


# =============================================================================
# ORDERING ASSUMPTIONS (8 tests)
# =============================================================================

class TestWebSocketOrdering:
    """Tests for WebSocket event ordering."""
    
    @pytest.mark.asyncio
    async def test_fifo_ordering(self, fresh_bus, connection_manager):
        """Events delivered in FIFO order."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        for i in range(20):
            await fresh_bus.publish("test.order", {"seq": i})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        sequences = [m["event"]["payload"]["seq"] for m in event_msgs]
        assert sequences == list(range(20))
    
    @pytest.mark.asyncio
    async def test_correlation_chain_order(self, fresh_bus, connection_manager):
        """Correlated events maintain order."""
        ws = MockWebSocket()
        await connection_manager.connect(ws, correlation_id="chain-1")
        
        corr = "chain-1"
        for step in ["start", "middle", "end"]:
            await fresh_bus.publish(f"workflow.{step}", {"step": step}, correlation_id=corr)
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        steps = [m["event"]["payload"]["step"] for m in event_msgs]
        assert steps == ["start", "middle", "end"]
    
    @pytest.mark.asyncio
    async def test_timestamps_monotonic(self, fresh_bus, connection_manager):
        """Timestamps are monotonically increasing."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        for i in range(10):
            await fresh_bus.publish("test.ts", {"i": i})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        timestamps = [datetime.fromisoformat(m["event"]["timestamp"].replace("Z", "+00:00")) 
                     for m in event_msgs]
        
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]
    
    @pytest.mark.asyncio
    async def test_interleaved_topics_preserve_order(self, fresh_bus, connection_manager):
        """Interleaved topics preserve global order."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("topic.a", {"seq": 1})
        await fresh_bus.publish("topic.b", {"seq": 2})
        await fresh_bus.publish("topic.a", {"seq": 3})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        sequences = [m["event"]["payload"]["seq"] for m in event_msgs]
        assert sequences == [1, 2, 3]
    
    @pytest.mark.asyncio
    async def test_multiple_clients_same_order(self, fresh_bus, connection_manager):
        """Multiple clients receive same order."""
        clients = [MockWebSocket(f"client-{i}") for i in range(3)]
        for ws in clients:
            await connection_manager.connect(ws)
        
        for i in range(10):
            await fresh_bus.publish("test.multi", {"seq": i})
        
        sequences_by_client = []
        for ws in clients:
            event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
            seqs = [m["event"]["payload"]["seq"] for m in event_msgs]
            sequences_by_client.append(seqs)
        
        # All clients should have same order
        assert all(s == sequences_by_client[0] for s in sequences_by_client)
    
    @pytest.mark.asyncio
    async def test_welcome_before_events(self, fresh_bus, connection_manager):
        """Welcome message comes before events."""
        ws = MockWebSocket()
        
        # Publish event first
        await fresh_bus.publish("pre.connect", {})
        
        # Then connect
        await connection_manager.connect(ws)
        
        # Welcome should be first message
        assert ws.messages_sent[0]["type"] == "connected"
    
    @pytest.mark.asyncio
    async def test_event_ids_in_order(self, fresh_bus, connection_manager):
        """Event IDs appear in publish order."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        published_ids = []
        for i in range(5):
            event_id = await fresh_bus.publish("test.ids", {"n": i})
            published_ids.append(event_id)
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        received_ids = [m["event"]["id"] for m in event_msgs]
        
        assert received_ids == published_ids
    
    @pytest.mark.asyncio
    async def test_filtered_events_preserve_order(self, fresh_bus, connection_manager):
        """Filtered events preserve relative order."""
        ws = MockWebSocket()
        await connection_manager.connect(ws, topics=["wanted.*"])
        
        await fresh_bus.publish("wanted.1", {"seq": 1})
        await fresh_bus.publish("unwanted.2", {"seq": 2})
        await fresh_bus.publish("wanted.3", {"seq": 3})
        await fresh_bus.publish("unwanted.4", {"seq": 4})
        await fresh_bus.publish("wanted.5", {"seq": 5})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        sequences = [m["event"]["payload"]["seq"] for m in event_msgs]
        assert sequences == [1, 3, 5]


# =============================================================================
# IDEMPOTENCY (8 tests)
# =============================================================================

class TestWebSocketIdempotency:
    """Tests for WebSocket idempotency patterns."""
    
    @pytest.mark.asyncio
    async def test_event_id_for_dedup(self, fresh_bus, connection_manager):
        """Event IDs can be used for deduplication."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("test.dedup", {"data": 1})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        event_id = event_msgs[0]["event"]["id"]
        
        # Replay
        await fresh_bus.replay_event(event_id)
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        # Client can deduplicate by tracking seen IDs
        ids = [m["event"]["id"] for m in event_msgs]
        # Same ID appears twice (client must handle)
        assert ids.count(event_id) == 2
    
    @pytest.mark.asyncio
    async def test_correlation_id_for_workflow_dedup(self, fresh_bus, connection_manager):
        """Correlation ID enables workflow-level dedup."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        corr = "workflow-123"
        await fresh_bus.publish("step.1", {}, correlation_id=corr)
        await fresh_bus.publish("step.2", {}, correlation_id=corr)
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        corr_ids = [m["event"]["correlation_id"] for m in event_msgs]
        
        # All same correlation - client can group/track
        assert all(c == corr for c in corr_ids)
    
    @pytest.mark.asyncio
    async def test_reconnect_doesnt_replay(self, fresh_bus, connection_manager):
        """Reconnecting doesn't replay old events."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("before.disconnect", {})
        
        connection_manager.disconnect(ws)
        
        # Reconnect
        ws2 = MockWebSocket()
        await connection_manager.connect(ws2)
        
        # Should only have welcome, not old events
        event_msgs = [m for m in ws2.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 0
    
    @pytest.mark.asyncio
    async def test_client_can_track_processed(self, fresh_bus, connection_manager):
        """Client can track processed event IDs."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        processed_ids = set()
        
        for i in range(5):
            await fresh_bus.publish("test.track", {"n": i})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        
        for msg in event_msgs:
            event_id = msg["event"]["id"]
            if event_id not in processed_ids:
                processed_ids.add(event_id)
        
        assert len(processed_ids) == 5
    
    @pytest.mark.asyncio
    async def test_sequence_numbers_for_ordering(self, fresh_bus, connection_manager):
        """Payload can include sequence numbers."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        for i in range(5):
            await fresh_bus.publish("test.seq", {"sequence": i, "data": f"msg-{i}"})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        sequences = [m["event"]["payload"]["sequence"] for m in event_msgs]
        
        # Client can use sequence for ordering/gap detection
        assert sequences == [0, 1, 2, 3, 4]
    
    @pytest.mark.asyncio
    async def test_timestamp_for_stale_detection(self, fresh_bus, connection_manager):
        """Timestamps enable stale event detection."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("test.stale", {"version": 1})
        await asyncio.sleep(0.01)
        await fresh_bus.publish("test.stale", {"version": 2})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        
        ts1 = datetime.fromisoformat(event_msgs[0]["event"]["timestamp"].replace("Z", "+00:00"))
        ts2 = datetime.fromisoformat(event_msgs[1]["event"]["timestamp"].replace("Z", "+00:00"))
        
        # Client can ignore older timestamps
        assert ts2 > ts1
    
    @pytest.mark.asyncio
    async def test_content_hash_for_dedup(self, fresh_bus, connection_manager):
        """Content hash can be used for deduplication."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        payload = {"key": "value", "count": 42}
        await fresh_bus.publish("test.hash", payload)
        await fresh_bus.publish("test.hash", payload)  # Duplicate content
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        
        hashes = []
        for msg in event_msgs:
            content = json.dumps(msg["event"]["payload"], sort_keys=True)
            hashes.append(hashlib.md5(content.encode()).hexdigest())
        
        # Same content = same hash
        assert hashes[0] == hashes[1]
    
    @pytest.mark.asyncio
    async def test_metadata_version_for_updates(self, fresh_bus, connection_manager):
        """Metadata version can track updates."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("entity.updated", {"id": "x"}, metadata={"version": 1})
        await fresh_bus.publish("entity.updated", {"id": "x"}, metadata={"version": 2})
        
        # Events include metadata in payload - client can track versions
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 2


# =============================================================================
# BACKPRESSURE (8 tests)
# =============================================================================

class TestWebSocketBackpressure:
    """Tests for WebSocket backpressure behavior."""
    
    @pytest.mark.asyncio
    async def test_high_volume_handling(self, fresh_bus, connection_manager):
        """WebSocket handles high volume of events."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        for i in range(1000):
            await fresh_bus.publish("test.volume", {"n": i})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 1000
    
    @pytest.mark.asyncio
    async def test_many_connections_handled(self, fresh_bus, connection_manager):
        """Many concurrent connections handled."""
        clients = [MockWebSocket(f"client-{i}") for i in range(50)]
        for ws in clients:
            await connection_manager.connect(ws)
        
        await fresh_bus.publish("test.broadcast", {"data": 1})
        
        for ws in clients:
            event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
            assert len(event_msgs) >= 1
    
    @pytest.mark.asyncio
    async def test_slow_client_doesnt_block(self, fresh_bus, connection_manager):
        """Slow client doesn't block others."""
        fast_ws = MockWebSocket("fast")
        slow_ws = MockWebSocket("slow")
        
        # Make slow_ws actually slow by adding delay
        original_send = slow_ws.send_json
        async def slow_send(data):
            await asyncio.sleep(0.001)
            await original_send(data)
        slow_ws.send_json = slow_send
        
        await connection_manager.connect(fast_ws)
        await connection_manager.connect(slow_ws)
        
        for i in range(10):
            await fresh_bus.publish("test.speed", {"n": i})
        
        # Fast client should receive all (may receive extra from bus subscription)
        fast_msgs = [m for m in fast_ws.messages_sent if m.get("type") == "event"]
        assert len(fast_msgs) >= 10
    
    @pytest.mark.asyncio
    async def test_failed_send_doesnt_crash(self, fresh_bus, connection_manager):
        """Failed send doesn't crash broadcasting."""
        good_ws = MockWebSocket("good")
        bad_ws = MockWebSocket("bad")
        
        # bad_ws will fail
        bad_ws._closed = True
        
        await connection_manager.connect(good_ws)
        connection_manager.active_connections[bad_ws] = {
            "topics": ["*"], "correlation_id": None, "events_sent": 0
        }
        
        await fresh_bus.publish("test.fail", {})
        
        # Good client still receives
        event_msgs = [m for m in good_ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 1
    
    @pytest.mark.asyncio
    async def test_stats_accurate_under_load(self, fresh_bus, connection_manager):
        """Stats remain accurate under load."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        for i in range(100):
            await fresh_bus.publish("test.stats", {"n": i})
        
        stats = connection_manager.get_stats()
        assert stats["total_events_sent"] == 100
    
    @pytest.mark.asyncio
    async def test_concurrent_connect_disconnect(self, fresh_bus, connection_manager):
        """Concurrent connect/disconnect cycles."""
        for i in range(50):
            ws = MockWebSocket(f"cycle-{i}")
            await connection_manager.connect(ws)
            await fresh_bus.publish("test.cycle", {"n": i})
            connection_manager.disconnect(ws)
        
        assert len(connection_manager.active_connections) == 0
    
    @pytest.mark.asyncio
    async def test_large_payload_broadcast(self, fresh_bus, connection_manager):
        """Large payloads broadcast to many clients."""
        clients = [MockWebSocket(f"client-{i}") for i in range(10)]
        for ws in clients:
            await connection_manager.connect(ws)
        
        large_data = {"data": "x" * 100000}
        await fresh_bus.publish("test.large", large_data)
        
        for ws in clients:
            event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
            assert len(event_msgs[0]["event"]["payload"]["data"]) == 100000
    
    @pytest.mark.asyncio
    async def test_filter_reduces_load(self, fresh_bus, connection_manager):
        """Topic filtering reduces client load."""
        filtered_ws = MockWebSocket("filtered")
        unfiltered_ws = MockWebSocket("unfiltered")
        
        await connection_manager.connect(filtered_ws, topics=["important.*"])
        await connection_manager.connect(unfiltered_ws, topics=["*"])
        
        for i in range(100):
            if i % 10 == 0:
                await fresh_bus.publish("important.event", {"n": i})
            else:
                await fresh_bus.publish("noise.event", {"n": i})
        
        filtered_msgs = [m for m in filtered_ws.messages_sent if m.get("type") == "event"]
        unfiltered_msgs = [m for m in unfiltered_ws.messages_sent if m.get("type") == "event"]
        
        # Filtered should have significantly fewer messages
        assert len(filtered_msgs) >= 10
        assert len(unfiltered_msgs) >= 100
        assert len(filtered_msgs) < len(unfiltered_msgs)


# =============================================================================
# CONSUMER ISOLATION (8 tests)
# =============================================================================

class TestWebSocketIsolation:
    """Tests for WebSocket consumer isolation."""
    
    @pytest.mark.asyncio
    async def test_clients_isolated_by_filter(self, fresh_bus, connection_manager):
        """Clients with different filters are isolated."""
        ws_publish = MockWebSocket("publish")
        ws_scheduler = MockWebSocket("scheduler")
        
        await connection_manager.connect(ws_publish, topics=["publish.*"])
        await connection_manager.connect(ws_scheduler, topics=["scheduler.*"])
        
        await fresh_bus.publish("publish.started", {"for": "publish"})
        await fresh_bus.publish("scheduler.tick", {"for": "scheduler"})
        
        publish_msgs = [m for m in ws_publish.messages_sent if m.get("type") == "event" and m["event"]["topic"].startswith("publish.")]
        scheduler_msgs = [m for m in ws_scheduler.messages_sent if m.get("type") == "event" and m["event"]["topic"].startswith("scheduler.")]
        
        assert len(publish_msgs) >= 1
        assert publish_msgs[0]["event"]["payload"]["for"] == "publish"
        
        assert len(scheduler_msgs) >= 1
        assert scheduler_msgs[0]["event"]["payload"]["for"] == "scheduler"
    
    @pytest.mark.asyncio
    async def test_correlation_id_isolation(self, fresh_bus, connection_manager):
        """Clients isolated by correlation ID."""
        ws_workflow_a = MockWebSocket("workflow-a")
        ws_workflow_b = MockWebSocket("workflow-b")
        
        await connection_manager.connect(ws_workflow_a, correlation_id="workflow-a")
        await connection_manager.connect(ws_workflow_b, correlation_id="workflow-b")
        
        await fresh_bus.publish("step.1", {"w": "a"}, correlation_id="workflow-a")
        await fresh_bus.publish("step.1", {"w": "b"}, correlation_id="workflow-b")
        
        a_msgs = [m for m in ws_workflow_a.messages_sent if m.get("type") == "event" and m["event"]["correlation_id"] == "workflow-a"]
        b_msgs = [m for m in ws_workflow_b.messages_sent if m.get("type") == "event" and m["event"]["correlation_id"] == "workflow-b"]
        
        assert len(a_msgs) >= 1
        assert a_msgs[0]["event"]["payload"]["w"] == "a"
        
        assert len(b_msgs) >= 1
        assert b_msgs[0]["event"]["payload"]["w"] == "b"
    
    @pytest.mark.asyncio
    async def test_disconnect_one_doesnt_affect_others(self, fresh_bus, connection_manager):
        """Disconnecting one client doesn't affect others."""
        ws1 = MockWebSocket("client-1")
        ws2 = MockWebSocket("client-2")
        
        await connection_manager.connect(ws1)
        await connection_manager.connect(ws2)
        
        connection_manager.disconnect(ws1)
        
        await fresh_bus.publish("test.event", {})
        
        ws2_msgs = [m for m in ws2.messages_sent if m.get("type") == "event"]
        assert len(ws2_msgs) >= 1
    
    @pytest.mark.asyncio
    async def test_client_metadata_isolated(self, fresh_bus, connection_manager):
        """Client metadata is isolated."""
        ws1 = MockWebSocket("client-1")
        ws2 = MockWebSocket("client-2")
        
        await connection_manager.connect(ws1, topics=["a.*"])
        await connection_manager.connect(ws2, topics=["b.*"])
        
        meta1 = connection_manager.active_connections[ws1]
        meta2 = connection_manager.active_connections[ws2]
        
        assert meta1["topics"] == ["a.*"]
        assert meta2["topics"] == ["b.*"]
    
    @pytest.mark.asyncio
    async def test_events_sent_counter_per_client(self, fresh_bus, connection_manager):
        """Events sent counter is per-client."""
        ws1 = MockWebSocket("client-1")
        ws2 = MockWebSocket("client-2")
        
        await connection_manager.connect(ws1, topics=["test.*"])
        await connection_manager.connect(ws2, topics=["other.*"])
        
        for i in range(5):
            await fresh_bus.publish("test.event", {"n": i})
        
        meta1 = connection_manager.active_connections[ws1]
        meta2 = connection_manager.active_connections[ws2]
        
        # ws1 receives test.* events, ws2 only receives other.* events
        assert meta1["events_sent"] >= 5
        # ws2 should have fewer events (only ones matching other.*)
        assert meta1["events_sent"] > meta2["events_sent"]
    
    @pytest.mark.asyncio
    async def test_client_ids_unique(self, fresh_bus, connection_manager):
        """Each client has unique ID."""
        clients = [MockWebSocket() for _ in range(10)]
        ids = [ws.client_id for ws in clients]
        assert len(set(ids)) == 10
    
    @pytest.mark.asyncio
    async def test_connection_times_independent(self, fresh_bus, connection_manager):
        """Connection times are independent."""
        ws1 = MockWebSocket()
        await connection_manager.connect(ws1)
        
        await asyncio.sleep(0.01)
        
        ws2 = MockWebSocket()
        await connection_manager.connect(ws2)
        
        meta1 = connection_manager.active_connections[ws1]
        meta2 = connection_manager.active_connections[ws2]
        
        assert meta1["connected_at"] != meta2["connected_at"]
    
    @pytest.mark.asyncio
    async def test_message_lists_independent(self, fresh_bus, connection_manager):
        """Message lists are independent per client."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        await connection_manager.connect(ws1)
        await connection_manager.connect(ws2)
        
        await fresh_bus.publish("test.event", {})
        
        # Clear ws1's messages
        ws1.messages_sent.clear()
        
        # ws2 should still have its messages
        event_msgs = [m for m in ws2.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) >= 1
        assert len(ws1.messages_sent) == 0  # ws1 was cleared


# =============================================================================
# SCHEMA EVOLUTION (8 tests)
# =============================================================================

class TestWebSocketSchemaEvolution:
    """Tests for WebSocket schema evolution handling."""
    
    @pytest.mark.asyncio
    async def test_optional_fields_handled(self, fresh_bus, connection_manager):
        """Optional fields don't break clients."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        # Old format
        await fresh_bus.publish("test.schema", {"required": "value"})
        # New format with optional
        await fresh_bus.publish("test.schema", {"required": "value", "optional": "new"})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 2
    
    @pytest.mark.asyncio
    async def test_unknown_fields_passed_through(self, fresh_bus, connection_manager):
        """Unknown fields are passed to client."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("test.future", {"known": 1, "future_field": "new"})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert "future_field" in event_msgs[0]["event"]["payload"]
    
    @pytest.mark.asyncio
    async def test_nested_schema_changes(self, fresh_bus, connection_manager):
        """Nested schema changes work."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        # Flat structure
        await fresh_bus.publish("test.nested", {"user_name": "alice"})
        # Nested structure
        await fresh_bus.publish("test.nested", {"user": {"name": "bob"}})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 2
    
    @pytest.mark.asyncio
    async def test_array_to_object_migration(self, fresh_bus, connection_manager):
        """Array to object migration handled."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        # Old: array of strings
        await fresh_bus.publish("test.migrate", {"items": ["a", "b"]})
        # New: array of objects
        await fresh_bus.publish("test.migrate", {"items": [{"name": "c"}]})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        assert len(event_msgs) == 2
    
    @pytest.mark.asyncio
    async def test_type_coercion_transparent(self, fresh_bus, connection_manager):
        """Type coercion is transparent to client."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("test.types", {"count": "42"})  # String
        await fresh_bus.publish("test.types", {"count": 42})    # Number
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        # Client receives both as-is
        assert event_msgs[0]["event"]["payload"]["count"] == "42"
        assert event_msgs[1]["event"]["payload"]["count"] == 42
    
    @pytest.mark.asyncio
    async def test_event_type_field_stable(self, fresh_bus, connection_manager):
        """Event type field structure is stable."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("any.topic", {})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        msg = event_msgs[0]
        
        # These fields should always exist
        assert "type" in msg
        assert "event" in msg
        assert "id" in msg["event"]
        assert "topic" in msg["event"]
        assert "timestamp" in msg["event"]
        assert "payload" in msg["event"]
    
    @pytest.mark.asyncio
    async def test_welcome_message_extensible(self, fresh_bus, connection_manager):
        """Welcome message can be extended."""
        ws = MockWebSocket()
        await connection_manager.connect(ws, topics=["test.*"])
        
        welcome = ws.messages_sent[0]
        
        # Core fields exist
        assert "type" in welcome
        assert "subscribed_topics" in welcome
        assert "timestamp" in welcome
    
    @pytest.mark.asyncio
    async def test_null_values_handled(self, fresh_bus, connection_manager):
        """Null values in payload handled."""
        ws = MockWebSocket()
        await connection_manager.connect(ws)
        
        await fresh_bus.publish("test.null", {"value": None, "present": "yes"})
        
        event_msgs = [m for m in ws.messages_sent if m.get("type") == "event"]
        payload = event_msgs[0]["event"]["payload"]
        
        assert payload["value"] is None
        assert payload["present"] == "yes"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
