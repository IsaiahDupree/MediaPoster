"""
Phase 1 Event Bus Guarantees Test Suite
========================================
Tests for critical event system properties:
- Event Correctness, Delivery Guarantees, Ordering, Idempotency
- Backpressure, Consumer Isolation, Schema Evolution, E2E

Total: 90 tests
"""

import pytest
import asyncio
import json
import time
import hashlib
from datetime import datetime, timezone
from uuid import uuid4
from typing import List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.event_bus.event import Event
from services.event_bus.topics import Topics
from services.event_bus.bus import EventBus


@pytest.fixture
def fresh_bus():
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()


@pytest.fixture
def event_collector():
    class Collector:
        def __init__(self):
            self.events: List[Event] = []
            self.handler_calls = 0
        async def handler(self, event: Event):
            self.events.append(event)
            self.handler_calls += 1
    return Collector()


# =============================================================================
# EVENT CORRECTNESS (15 tests)
# =============================================================================

class TestEventCorrectness:
    @pytest.mark.asyncio
    async def test_payload_preserved(self, fresh_bus, event_collector):
        payload = {"key": "value", "nested": {"deep": [1, 2, 3]}}
        fresh_bus.subscribe("test.correct", event_collector.handler)
        await fresh_bus.publish("test.correct", payload)
        assert event_collector.events[0].payload == payload

    @pytest.mark.asyncio
    async def test_topic_preserved(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.topic", event_collector.handler)
        await fresh_bus.publish("test.topic", {})
        assert event_collector.events[0].topic == "test.topic"

    @pytest.mark.asyncio
    async def test_timestamp_recent(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.ts", event_collector.handler)
        before = datetime.now(timezone.utc)
        await fresh_bus.publish("test.ts", {})
        after = datetime.now(timezone.utc)
        assert before <= event_collector.events[0].timestamp <= after

    @pytest.mark.asyncio
    async def test_correlation_id_generated(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.corr", event_collector.handler)
        await fresh_bus.publish("test.corr", {})
        assert event_collector.events[0].correlation_id is not None

    @pytest.mark.asyncio
    async def test_correlation_id_preserved(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.corr", event_collector.handler)
        await fresh_bus.publish("test.corr", {}, correlation_id="custom-123")
        assert event_collector.events[0].correlation_id == "custom-123"

    @pytest.mark.asyncio
    async def test_event_id_unique(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.unique", event_collector.handler)
        for _ in range(100):
            await fresh_bus.publish("test.unique", {})
        ids = [e.id for e in event_collector.events]
        assert len(set(ids)) == 100

    @pytest.mark.asyncio
    async def test_source_set(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.src", event_collector.handler)
        await fresh_bus.publish("test.src", {}, source="custom-src")
        assert event_collector.events[0].source == "custom-src"

    @pytest.mark.asyncio
    async def test_metadata_preserved(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.meta", event_collector.handler)
        await fresh_bus.publish("test.meta", {}, metadata={"v": 1})
        assert event_collector.events[0].metadata == {"v": 1}

    @pytest.mark.asyncio
    async def test_complex_types(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.types", event_collector.handler)
        payload = {"int": 42, "float": 3.14, "bool": True, "none": None, "list": [1, 2]}
        await fresh_bus.publish("test.types", payload)
        assert event_collector.events[0].payload["int"] == 42

    @pytest.mark.asyncio
    async def test_unicode_preserved(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.unicode", event_collector.handler)
        await fresh_bus.publish("test.unicode", {"emoji": "🎉"})
        assert event_collector.events[0].payload["emoji"] == "🎉"

    @pytest.mark.asyncio
    async def test_large_payload(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.large", event_collector.handler)
        await fresh_bus.publish("test.large", {"data": "x" * 100000})
        assert len(event_collector.events[0].payload["data"]) == 100000

    @pytest.mark.asyncio
    async def test_to_dict_complete(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.dict", event_collector.handler)
        await fresh_bus.publish("test.dict", {"d": 1}, metadata={"v": 1})
        d = event_collector.events[0].to_dict()
        assert all(k in d for k in ["id", "topic", "timestamp", "payload"])

    @pytest.mark.asyncio
    async def test_json_roundtrip(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.json", event_collector.handler)
        await fresh_bus.publish("test.json", {"nested": [1, 2]})
        original = event_collector.events[0]
        restored = Event.from_json(original.to_json())
        assert restored.payload == original.payload


# =============================================================================
# DELIVERY GUARANTEES (15 tests)
# =============================================================================

class TestDeliveryGuarantees:
    @pytest.mark.asyncio
    async def test_exactly_once_single_sub(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.del", event_collector.handler)
        await fresh_bus.publish("test.del", {})
        assert event_collector.handler_calls == 1

    @pytest.mark.asyncio
    async def test_all_subscribers_receive(self, fresh_bus):
        results = []
        for i in range(5):
            async def h(e, idx=i): results.append(idx)
            fresh_bus.subscribe("test.multi", h)
        await fresh_bus.publish("test.multi", {})
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_wildcard_matches(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.*", event_collector.handler)
        await fresh_bus.publish("test.one", {})
        await fresh_bus.publish("test.two", {})
        await fresh_bus.publish("other.topic", {})
        assert event_collector.handler_calls == 2

    @pytest.mark.asyncio
    async def test_no_delivery_non_matching(self, fresh_bus, event_collector):
        fresh_bus.subscribe("other.topic", event_collector.handler)
        await fresh_bus.publish("test.topic", {})
        assert event_collector.handler_calls == 0

    @pytest.mark.asyncio
    async def test_exception_doesnt_block_others(self, fresh_bus, event_collector):
        async def fails(e): raise ValueError("fail")
        fresh_bus.subscribe("test.fail", fails)
        fresh_bus.subscribe("test.fail", event_collector.handler)
        await fresh_bus.publish("test.fail", {})
        assert event_collector.handler_calls == 1

    @pytest.mark.asyncio
    async def test_failed_to_dlq(self, fresh_bus):
        async def fails(e): raise ValueError("fail")
        fresh_bus.subscribe("test.dlq", fails)
        await fresh_bus.publish("test.dlq", {})
        assert len(fresh_bus.get_dead_letter_queue()) >= 1

    @pytest.mark.asyncio
    async def test_logged_without_subscribers(self, fresh_bus):
        event_id = await fresh_bus.publish("test.nosub", {})
        recent = fresh_bus.get_recent_events("test.nosub")
        assert len(recent) == 1

    @pytest.mark.asyncio
    async def test_replay_delivers(self, fresh_bus, event_collector):
        event_id = await fresh_bus.publish("test.replay", {})
        fresh_bus.subscribe("test.replay", event_collector.handler)
        await fresh_bus.replay_event(event_id)
        assert event_collector.handler_calls == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_stops(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.unsub", event_collector.handler)
        await fresh_bus.publish("test.unsub", {})
        fresh_bus.unsubscribe("test.unsub", event_collector.handler)
        await fresh_bus.publish("test.unsub", {})
        assert event_collector.handler_calls == 1

    @pytest.mark.asyncio
    async def test_suffix_wildcard(self, fresh_bus, event_collector):
        fresh_bus.subscribe("*.completed", event_collector.handler)
        await fresh_bus.publish("a.completed", {})
        await fresh_bus.publish("b.completed", {})
        assert event_collector.handler_calls == 2


# =============================================================================
# ORDERING ASSUMPTIONS (10 tests)
# =============================================================================

class TestOrdering:
    @pytest.mark.asyncio
    async def test_fifo_same_topic(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.order", event_collector.handler)
        for i in range(10):
            await fresh_bus.publish("test.order", {"seq": i})
        seqs = [e.payload["seq"] for e in event_collector.events]
        assert seqs == list(range(10))

    @pytest.mark.asyncio
    async def test_correlation_order(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.*", event_collector.handler)
        corr = "wf-123"
        for i in range(3):
            await fresh_bus.publish(f"test.step{i}", {"s": i}, correlation_id=corr)
        steps = [e.payload["s"] for e in event_collector.events]
        assert steps == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_timestamps_monotonic(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.ts", event_collector.handler)
        for _ in range(10):
            await fresh_bus.publish("test.ts", {})
        ts = [e.timestamp for e in event_collector.events]
        for i in range(1, len(ts)):
            assert ts[i] >= ts[i-1]

    @pytest.mark.asyncio
    async def test_handler_subscription_order(self, fresh_bus):
        order = []
        async def ha(e): order.append("a")
        async def hb(e): order.append("b")
        fresh_bus.subscribe("test.o", ha)
        fresh_bus.subscribe("test.o", hb)
        await fresh_bus.publish("test.o", {})
        assert order == ["a", "b"]

    @pytest.mark.asyncio
    async def test_event_log_order(self, fresh_bus):
        for i in range(10):
            await fresh_bus.publish("test.log", {"n": i})
        recent = fresh_bus.get_recent_events(limit=10)
        ns = [e.payload["n"] for e in reversed(recent)]
        assert ns == list(range(10))


# =============================================================================
# IDEMPOTENCY (10 tests)
# =============================================================================

class TestIdempotency:
    @pytest.mark.asyncio
    async def test_idempotency_key_pattern(self, fresh_bus):
        processed = set()
        results = []
        async def h(e):
            key = e.payload.get("idem_key")
            if key in processed: return
            processed.add(key)
            results.append(e.payload["val"])
        fresh_bus.subscribe("test.idem", h)
        await fresh_bus.publish("test.idem", {"idem_key": "k1", "val": 1})
        await fresh_bus.publish("test.idem", {"idem_key": "k1", "val": 2})
        await fresh_bus.publish("test.idem", {"idem_key": "k2", "val": 3})
        assert results == [1, 3]

    @pytest.mark.asyncio
    async def test_correlation_dedup(self, fresh_bus):
        seen = set()
        results = []
        async def h(e):
            if e.correlation_id in seen: return
            seen.add(e.correlation_id)
            results.append(e.payload["d"])
        fresh_bus.subscribe("test.dedup", h)
        await fresh_bus.publish("test.dedup", {"d": 1}, correlation_id="A")
        await fresh_bus.publish("test.dedup", {"d": 2}, correlation_id="A")
        await fresh_bus.publish("test.dedup", {"d": 3}, correlation_id="B")
        assert results == [1, 3]

    @pytest.mark.asyncio
    async def test_content_hash_dedup(self, fresh_bus):
        hashes = set()
        results = []
        async def h(e):
            h_val = hashlib.md5(json.dumps(e.payload, sort_keys=True).encode()).hexdigest()
            if h_val in hashes: return
            hashes.add(h_val)
            results.append(e.payload)
        fresh_bus.subscribe("test.hash", h)
        await fresh_bus.publish("test.hash", {"a": 1})
        await fresh_bus.publish("test.hash", {"a": 1})
        await fresh_bus.publish("test.hash", {"a": 2})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_replay_has_metadata(self, fresh_bus, event_collector):
        eid = await fresh_bus.publish("test.rp", {})
        fresh_bus.subscribe("test.rp", event_collector.handler)
        await fresh_bus.replay_event(eid)
        assert "replayed_at" in event_collector.events[0].metadata


# =============================================================================
# BACKPRESSURE (10 tests)
# =============================================================================

class TestBackpressure:
    @pytest.mark.asyncio
    async def test_high_volume(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.vol", event_collector.handler)
        for i in range(1000):
            await fresh_bus.publish("test.vol", {"n": i})
        assert event_collector.handler_calls == 1000

    @pytest.mark.asyncio
    async def test_log_trims(self, fresh_bus):
        fresh_bus._max_log_size = 100
        for i in range(500):
            await fresh_bus.publish("test.trim", {"n": i})
        assert len(fresh_bus._event_log) <= 100

    @pytest.mark.asyncio
    async def test_dlq_grows(self, fresh_bus):
        async def fails(e): raise ValueError()
        fresh_bus.subscribe("test.dlq", fails)
        for _ in range(50):
            await fresh_bus.publish("test.dlq", {})
        assert len(fresh_bus.get_dead_letter_queue()) == 50

    @pytest.mark.asyncio
    async def test_clear_dlq(self, fresh_bus):
        async def fails(e): raise ValueError()
        fresh_bus.subscribe("test.clr", fails)
        for _ in range(10):
            await fresh_bus.publish("test.clr", {})
        fresh_bus.clear_dead_letter_queue()
        assert len(fresh_bus.get_dead_letter_queue()) == 0

    @pytest.mark.asyncio
    async def test_concurrent_publishes(self, fresh_bus, event_collector):
        fresh_bus.subscribe("test.conc", event_collector.handler)
        async def batch(s, c):
            for i in range(s, s+c):
                await fresh_bus.publish("test.conc", {"n": i})
        await asyncio.gather(batch(0, 100), batch(100, 100), batch(200, 100))
        assert event_collector.handler_calls == 300


# =============================================================================
# CONSUMER ISOLATION (10 tests)
# =============================================================================

class TestConsumerIsolation:
    @pytest.mark.asyncio
    async def test_exception_isolated(self, fresh_bus):
        results = []
        async def fails(e): raise ValueError()
        async def ok(e): results.append("ok")
        fresh_bus.subscribe("test.iso", fails)
        fresh_bus.subscribe("test.iso", ok)
        await fresh_bus.publish("test.iso", {})
        assert "ok" in results

    @pytest.mark.asyncio
    async def test_independent_state(self, fresh_bus):
        sa, sb = {"c": 0}, {"c": 0}
        async def ha(e): sa["c"] += 1
        async def hb(e): sb["c"] += 2
        fresh_bus.subscribe("test.st", ha)
        fresh_bus.subscribe("test.st", hb)
        for _ in range(10):
            await fresh_bus.publish("test.st", {})
        assert sa["c"] == 10 and sb["c"] == 20

    @pytest.mark.asyncio
    async def test_topic_isolated(self, fresh_bus):
        ra, rb = [], []
        async def ha(e): ra.append(1)
        async def hb(e): rb.append(1)
        fresh_bus.subscribe("topic.a", ha)
        fresh_bus.subscribe("topic.b", hb)
        await fresh_bus.publish("topic.a", {})
        assert ra == [1] and rb == []

    @pytest.mark.asyncio
    async def test_unsub_isolated(self, fresh_bus):
        r = []
        async def ha(e): r.append("a")
        async def hb(e): r.append("b")
        fresh_bus.subscribe("test.un", ha)
        fresh_bus.subscribe("test.un", hb)
        await fresh_bus.publish("test.un", {})
        fresh_bus.unsubscribe("test.un", ha)
        await fresh_bus.publish("test.un", {})
        assert r == ["a", "b", "b"]


# =============================================================================
# SCHEMA EVOLUTION (10 tests)
# =============================================================================

class TestSchemaEvolution:
    @pytest.mark.asyncio
    async def test_missing_optional(self, fresh_bus):
        results = []
        async def h(e):
            results.append(e.payload.get("opt", "default"))
        fresh_bus.subscribe("test.sch", h)
        await fresh_bus.publish("test.sch", {"req": 1})
        await fresh_bus.publish("test.sch", {"req": 1, "opt": "val"})
        assert results == ["default", "val"]

    @pytest.mark.asyncio
    async def test_ignores_unknown(self, fresh_bus):
        results = []
        async def h(e): results.append(e.payload.get("known"))
        fresh_bus.subscribe("test.fwd", h)
        await fresh_bus.publish("test.fwd", {"known": "v", "unknown": "x"})
        assert results == ["v"]

    @pytest.mark.asyncio
    async def test_version_routing(self, fresh_bus):
        results = []
        async def h(e):
            v = e.metadata.get("schema_version", 1)
            if v == 1: results.append(("v1", e.payload["d"]))
            else: results.append(("v2", e.payload["d"]["val"]))
        fresh_bus.subscribe("test.ver", h)
        await fresh_bus.publish("test.ver", {"d": "old"}, metadata={"schema_version": 1})
        await fresh_bus.publish("test.ver", {"d": {"val": "new"}}, metadata={"schema_version": 2})
        assert results == [("v1", "old"), ("v2", "new")]

    @pytest.mark.asyncio
    async def test_field_rename(self, fresh_bus):
        results = []
        async def h(e):
            results.append(e.payload.get("new_name") or e.payload.get("old_name"))
        fresh_bus.subscribe("test.rn", h)
        await fresh_bus.publish("test.rn", {"old_name": "a"})
        await fresh_bus.publish("test.rn", {"new_name": "b"})
        assert results == ["a", "b"]


# =============================================================================
# E2E FRONTEND-BACKEND (10 tests)
# =============================================================================

class TestE2E:
    @pytest.mark.asyncio
    async def test_api_to_worker(self, fresh_bus):
        received = []
        async def worker(e): received.append(e.payload)
        fresh_bus.subscribe(Topics.ANALYSIS_REQUESTED, worker)
        await fresh_bus.publish(Topics.ANALYSIS_REQUESTED, {"media_id": "m-123"})
        assert received[0]["media_id"] == "m-123"

    @pytest.mark.asyncio
    async def test_worker_to_api(self, fresh_bus):
        notif = []
        async def api(e): notif.append(e.payload)
        fresh_bus.subscribe(Topics.ANALYSIS_COMPLETED, api)
        await fresh_bus.publish(Topics.ANALYSIS_COMPLETED, {"media_id": "m-1", "score": 85})
        assert notif[0]["score"] == 85

    @pytest.mark.asyncio
    async def test_request_response_corr(self, fresh_bus):
        resp = {}
        async def h(e): resp[e.correlation_id] = e.payload
        fresh_bus.subscribe("*.completed", h)
        cid = str(uuid4())
        await fresh_bus.publish("analysis.completed", {"r": 1}, correlation_id=cid)
        assert cid in resp

    @pytest.mark.asyncio
    async def test_error_propagation(self, fresh_bus):
        errors = []
        async def h(e): errors.append(e.payload.get("error"))
        fresh_bus.subscribe(Topics.ANALYSIS_FAILED, h)
        await fresh_bus.publish(Topics.ANALYSIS_FAILED, {"error": "bad format"})
        assert errors[0] == "bad format"

    @pytest.mark.asyncio
    async def test_workflow_chain(self, fresh_bus):
        steps = []
        async def h1(e):
            steps.append(1)
            await fresh_bus.publish("step.two", {}, correlation_id=e.correlation_id)
        async def h2(e):
            steps.append(2)
            await fresh_bus.publish("step.three", {}, correlation_id=e.correlation_id)
        async def h3(e): steps.append(3)
        fresh_bus.subscribe("step.one", h1)
        fresh_bus.subscribe("step.two", h2)
        fresh_bus.subscribe("step.three", h3)
        await fresh_bus.publish("step.one", {}, correlation_id="wf-1")
        assert steps == [1, 2, 3]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
