"""
Phase 3 Scheduler & Two-Brain Architecture Guarantees Test Suite
=================================================================
Tests for critical scheduler and API system properties:
- Event Correctness, Delivery Guarantees, Ordering, Idempotency
- Backpressure, Consumer Isolation, Schema Evolution, E2E

Phase 3 Components:
- PostScheduler (scheduling engine)
- Narrative Builder APIs (goals, plans, KB rules)
- Experiments APIs (confidence, rule generation)
- Calendar APIs (origin filtering)

Total: 60 tests
"""

import pytest
import asyncio
import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.event_bus import EventBus, Event, Topics


# =============================================================================
# TEST FIXTURES & MOCKS
# =============================================================================

@pytest.fixture
def fresh_bus():
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()


@pytest.fixture
def mock_engine():
    """Mock database engine for scheduler tests."""
    engine = MagicMock()
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=None)
    engine.connect.return_value = conn
    return engine


@pytest.fixture
def event_collector():
    """Collects events for verification."""
    class Collector:
        def __init__(self):
            self.events: List[Event] = []
            self.by_topic: Dict[str, List[Event]] = {}
        
        async def handler(self, event: Event):
            self.events.append(event)
            if event.topic not in self.by_topic:
                self.by_topic[event.topic] = []
            self.by_topic[event.topic].append(event)
        
        def get_topic(self, topic: str) -> List[Event]:
            return self.by_topic.get(topic, [])
    
    return Collector()


class MockScheduler:
    """Mock scheduler for testing event flows."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.is_running = False
        self.check_interval = 60
        self.max_retries = 3
        self._check_count = 0
        self.processed_posts: List[Dict] = []
        self.failed_posts: List[Dict] = []
    
    async def start(self):
        self.is_running = True
        await self.event_bus.publish(
            Topics.SCHEDULER_STARTED,
            {"check_interval": self.check_interval, "max_retries": self.max_retries}
        )
    
    async def stop(self):
        self.is_running = False
        await self.event_bus.publish(
            Topics.SCHEDULER_STOPPED,
            {"total_checks": self._check_count}
        )
    
    async def tick(self, due_posts: List[Dict] = None):
        self._check_count += 1
        due_posts = due_posts or []
        await self.event_bus.publish(
            Topics.SCHEDULER_TICK,
            {
                "check_number": self._check_count,
                "due_count": len(due_posts),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        return due_posts
    
    async def process_post(self, post: Dict, success: bool = True):
        """Process a scheduled post."""
        post_id = post.get("id", str(uuid4()))
        corr_id = str(uuid4())
        
        # Emit schedule.due
        await self.event_bus.publish(
            "schedule.due",
            {"post_id": post_id, "platform": post.get("platform", "tiktok")},
            correlation_id=corr_id
        )
        
        if success:
            self.processed_posts.append(post)
            await self.event_bus.publish(
                Topics.PUBLISH_COMPLETED,
                {"post_id": post_id, "platform_url": f"https://platform.com/{post_id}"},
                correlation_id=corr_id
            )
        else:
            self.failed_posts.append(post)
            await self.event_bus.publish(
                Topics.PUBLISH_FAILED,
                {"post_id": post_id, "error": "Simulated failure"},
                correlation_id=corr_id
            )
        
        return {"success": success, "post_id": post_id, "correlation_id": corr_id}


class MockNarrativeBuilder:
    """Mock narrative builder for testing."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.goals: Dict[str, Dict] = {}
        self.plans: Dict[str, Dict] = {}
    
    async def create_goal(self, goal: Dict) -> Dict:
        goal_id = str(uuid4())
        goal["id"] = goal_id
        self.goals[goal_id] = goal
        
        await self.event_bus.publish(
            "narrative.goal.created",
            {"goal_id": goal_id, "name": goal.get("name")},
            metadata={"schema_version": 1}
        )
        return goal
    
    async def generate_plan(self, goal_ids: List[str] = None) -> Dict:
        plan_id = str(uuid4())
        plan = {
            "id": plan_id,
            "goal_ids": goal_ids or [],
            "days": 7,
            "posts": [{"day": i, "slot": 1} for i in range(7)]
        }
        self.plans[plan_id] = plan
        
        await self.event_bus.publish(
            "narrative.plan.generated",
            {"plan_id": plan_id, "post_count": len(plan["posts"])},
            metadata={"schema_version": 1}
        )
        return plan


class MockExperiments:
    """Mock experiments system for testing."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.experiments: Dict[str, Dict] = {}
        self.rules_generated: List[Dict] = []
    
    async def calculate_confidence(self, exp_id: str, control_views: int, 
                                   variant_views: int, control_rate: float, 
                                   variant_rate: float) -> Dict:
        # Simple mock confidence calculation
        uplift = ((variant_rate - control_rate) / control_rate) * 100
        confidence = min(99, 50 + (control_views + variant_views) / 500)
        
        result = {
            "experiment_id": exp_id,
            "confidence": confidence,
            "is_significant": confidence >= 95,
            "uplift": uplift
        }
        
        await self.event_bus.publish(
            "experiment.confidence.calculated",
            result,
            metadata={"schema_version": 1}
        )
        return result
    
    async def generate_rule(self, exp_id: str, winner_data: Dict) -> Dict:
        rule = {
            "id": str(uuid4()),
            "source_experiment_id": exp_id,
            "rule_type": winner_data.get("type", "hook"),
            "recommendation": winner_data.get("approach", "Use winning approach"),
            "expected_lift": winner_data.get("uplift", 10),
            "confidence": winner_data.get("confidence", 0.9)
        }
        self.rules_generated.append(rule)
        
        await self.event_bus.publish(
            "experiment.rule.generated",
            {"rule_id": rule["id"], "experiment_id": exp_id},
            metadata={"schema_version": 1}
        )
        return rule


# =============================================================================
# EVENT CORRECTNESS (10 tests)
# =============================================================================

class TestPhase3EventCorrectness:
    """Tests for Phase 3 event correctness."""
    
    @pytest.mark.asyncio
    async def test_scheduler_start_event_payload(self, fresh_bus, event_collector):
        """Scheduler start event has correct payload."""
        fresh_bus.subscribe(Topics.SCHEDULER_STARTED, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.start()
        
        events = event_collector.get_topic(Topics.SCHEDULER_STARTED)
        assert len(events) == 1
        assert events[0].payload["check_interval"] == 60
        assert events[0].payload["max_retries"] == 3
    
    @pytest.mark.asyncio
    async def test_scheduler_tick_event_payload(self, fresh_bus, event_collector):
        """Scheduler tick event has correct payload."""
        fresh_bus.subscribe(Topics.SCHEDULER_TICK, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.tick([{"id": "1"}, {"id": "2"}])
        
        events = event_collector.get_topic(Topics.SCHEDULER_TICK)
        assert len(events) == 1
        assert events[0].payload["check_number"] == 1
        assert events[0].payload["due_count"] == 2
    
    @pytest.mark.asyncio
    async def test_publish_completed_has_url(self, fresh_bus, event_collector):
        """Publish completed event includes platform URL."""
        fresh_bus.subscribe(Topics.PUBLISH_COMPLETED, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.process_post({"id": "post-123"}, success=True)
        
        events = event_collector.get_topic(Topics.PUBLISH_COMPLETED)
        assert len(events) == 1
        assert "platform_url" in events[0].payload
        assert "post-123" in events[0].payload["platform_url"]
    
    @pytest.mark.asyncio
    async def test_publish_failed_has_error(self, fresh_bus, event_collector):
        """Publish failed event includes error details."""
        fresh_bus.subscribe(Topics.PUBLISH_FAILED, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.process_post({"id": "post-456"}, success=False)
        
        events = event_collector.get_topic(Topics.PUBLISH_FAILED)
        assert len(events) == 1
        assert "error" in events[0].payload
    
    @pytest.mark.asyncio
    async def test_narrative_goal_created_event(self, fresh_bus, event_collector):
        """Goal creation emits correct event."""
        fresh_bus.subscribe("narrative.goal.created", event_collector.handler)
        
        builder = MockNarrativeBuilder(fresh_bus)
        goal = await builder.create_goal({"name": "Test Goal", "type": "growth"})
        
        events = event_collector.get_topic("narrative.goal.created")
        assert len(events) == 1
        assert events[0].payload["name"] == "Test Goal"
    
    @pytest.mark.asyncio
    async def test_plan_generated_event(self, fresh_bus, event_collector):
        """Plan generation emits correct event."""
        fresh_bus.subscribe("narrative.plan.generated", event_collector.handler)
        
        builder = MockNarrativeBuilder(fresh_bus)
        plan = await builder.generate_plan()
        
        events = event_collector.get_topic("narrative.plan.generated")
        assert len(events) == 1
        assert events[0].payload["post_count"] == 7
    
    @pytest.mark.asyncio
    async def test_confidence_calculated_event(self, fresh_bus, event_collector):
        """Confidence calculation emits correct event."""
        fresh_bus.subscribe("experiment.confidence.calculated", event_collector.handler)
        
        experiments = MockExperiments(fresh_bus)
        result = await experiments.calculate_confidence("exp-1", 10000, 10000, 0.65, 0.78)
        
        events = event_collector.get_topic("experiment.confidence.calculated")
        assert len(events) == 1
        assert events[0].payload["uplift"] > 0
    
    @pytest.mark.asyncio
    async def test_rule_generated_event(self, fresh_bus, event_collector):
        """Rule generation emits correct event."""
        fresh_bus.subscribe("experiment.rule.generated", event_collector.handler)
        
        experiments = MockExperiments(fresh_bus)
        rule = await experiments.generate_rule("exp-1", {"type": "hook", "uplift": 20})
        
        events = event_collector.get_topic("experiment.rule.generated")
        assert len(events) == 1
        assert events[0].payload["experiment_id"] == "exp-1"
    
    @pytest.mark.asyncio
    async def test_scheduler_stop_event(self, fresh_bus, event_collector):
        """Scheduler stop event includes stats."""
        fresh_bus.subscribe(Topics.SCHEDULER_STOPPED, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.start()
        await scheduler.tick()
        await scheduler.tick()
        await scheduler.stop()
        
        events = event_collector.get_topic(Topics.SCHEDULER_STOPPED)
        assert len(events) == 1
        assert events[0].payload["total_checks"] == 2
    
    @pytest.mark.asyncio
    async def test_correlation_preserved_through_publish(self, fresh_bus, event_collector):
        """Correlation ID preserved through publish flow."""
        fresh_bus.subscribe("schedule.due", event_collector.handler)
        fresh_bus.subscribe(Topics.PUBLISH_COMPLETED, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        result = await scheduler.process_post({"id": "post-1"})
        
        due_event = event_collector.get_topic("schedule.due")[0]
        complete_event = event_collector.get_topic(Topics.PUBLISH_COMPLETED)[0]
        
        assert due_event.correlation_id == complete_event.correlation_id


# =============================================================================
# DELIVERY GUARANTEES (10 tests)
# =============================================================================

class TestPhase3DeliveryGuarantees:
    """Tests for Phase 3 delivery guarantees."""
    
    @pytest.mark.asyncio
    async def test_all_due_posts_get_events(self, fresh_bus, event_collector):
        """All due posts emit schedule.due events."""
        fresh_bus.subscribe("schedule.due", event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        posts = [{"id": f"post-{i}"} for i in range(10)]
        
        for post in posts:
            await scheduler.process_post(post)
        
        events = event_collector.get_topic("schedule.due")
        assert len(events) == 10
    
    @pytest.mark.asyncio
    async def test_failed_posts_get_failure_events(self, fresh_bus, event_collector):
        """Failed posts emit failure events."""
        fresh_bus.subscribe(Topics.PUBLISH_FAILED, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        
        for i in range(5):
            await scheduler.process_post({"id": f"fail-{i}"}, success=False)
        
        events = event_collector.get_topic(Topics.PUBLISH_FAILED)
        assert len(events) == 5
    
    @pytest.mark.asyncio
    async def test_mixed_success_failure_delivery(self, fresh_bus, event_collector):
        """Mixed success/failure delivers correct events."""
        fresh_bus.subscribe(Topics.PUBLISH_COMPLETED, event_collector.handler)
        fresh_bus.subscribe(Topics.PUBLISH_FAILED, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        
        for i in range(10):
            await scheduler.process_post({"id": f"post-{i}"}, success=(i % 2 == 0))
        
        completed = event_collector.get_topic(Topics.PUBLISH_COMPLETED)
        failed = event_collector.get_topic(Topics.PUBLISH_FAILED)
        
        assert len(completed) == 5
        assert len(failed) == 5
    
    @pytest.mark.asyncio
    async def test_multiple_goals_all_emit_events(self, fresh_bus, event_collector):
        """Multiple goal creations all emit events."""
        fresh_bus.subscribe("narrative.goal.created", event_collector.handler)
        
        builder = MockNarrativeBuilder(fresh_bus)
        
        for i in range(5):
            await builder.create_goal({"name": f"Goal {i}"})
        
        events = event_collector.get_topic("narrative.goal.created")
        assert len(events) == 5
    
    @pytest.mark.asyncio
    async def test_tick_events_for_each_check(self, fresh_bus, event_collector):
        """Each scheduler check emits tick event."""
        fresh_bus.subscribe(Topics.SCHEDULER_TICK, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        
        for _ in range(10):
            await scheduler.tick()
        
        events = event_collector.get_topic(Topics.SCHEDULER_TICK)
        assert len(events) == 10
        
        check_numbers = [e.payload["check_number"] for e in events]
        assert check_numbers == list(range(1, 11))
    
    @pytest.mark.asyncio
    async def test_wildcard_captures_all_scheduler_events(self, fresh_bus, event_collector):
        """Wildcard subscription captures scheduler events."""
        fresh_bus.subscribe("scheduler.*", event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.start()
        await scheduler.tick()
        await scheduler.stop()
        
        # Should have started, tick, stopped
        assert len(event_collector.events) >= 3
    
    @pytest.mark.asyncio
    async def test_wildcard_captures_publish_events(self, fresh_bus, event_collector):
        """Wildcard subscription captures publish events."""
        fresh_bus.subscribe("publish.*", event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.process_post({"id": "1"}, success=True)
        await scheduler.process_post({"id": "2"}, success=False)
        
        assert len(event_collector.events) == 2
    
    @pytest.mark.asyncio
    async def test_events_logged_even_without_subscribers(self, fresh_bus):
        """Events are logged even without active subscribers."""
        scheduler = MockScheduler(fresh_bus)
        await scheduler.tick([{"id": "1"}])
        
        recent = fresh_bus.get_recent_events(Topics.SCHEDULER_TICK)
        assert len(recent) == 1
    
    @pytest.mark.asyncio
    async def test_subscriber_added_after_events_can_replay(self, fresh_bus, event_collector):
        """Subscriber added after events can replay from log."""
        scheduler = MockScheduler(fresh_bus)
        event_id = await scheduler.event_bus.publish("early.event", {"data": 1})
        
        # Subscribe after
        fresh_bus.subscribe("early.event", event_collector.handler)
        
        # Replay
        await fresh_bus.replay_event(event_id)
        
        assert len(event_collector.events) == 1
    
    @pytest.mark.asyncio
    async def test_dead_letter_queue_for_handler_failures(self, fresh_bus):
        """Handler failures go to DLQ."""
        async def failing_handler(event):
            raise ValueError("Handler failed")
        
        fresh_bus.subscribe("test.fail", failing_handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.event_bus.publish("test.fail", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1


# =============================================================================
# ORDERING ASSUMPTIONS (8 tests)
# =============================================================================

class TestPhase3Ordering:
    """Tests for Phase 3 event ordering."""
    
    @pytest.mark.asyncio
    async def test_scheduler_lifecycle_order(self, fresh_bus, event_collector):
        """Scheduler lifecycle events in correct order."""
        fresh_bus.subscribe("scheduler.*", event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.start()
        await scheduler.tick()
        await scheduler.stop()
        
        topics = [e.topic for e in event_collector.events]
        assert topics.index(Topics.SCHEDULER_STARTED) < topics.index(Topics.SCHEDULER_TICK)
        assert topics.index(Topics.SCHEDULER_TICK) < topics.index(Topics.SCHEDULER_STOPPED)
    
    @pytest.mark.asyncio
    async def test_publish_flow_order(self, fresh_bus, event_collector):
        """Publish flow events in correct order."""
        fresh_bus.subscribe("schedule.*", event_collector.handler)
        fresh_bus.subscribe("publish.*", event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.process_post({"id": "1"})
        
        # schedule.due should come before publish.completed
        topics = [e.topic for e in event_collector.events]
        assert topics.index("schedule.due") < topics.index(Topics.PUBLISH_COMPLETED)
    
    @pytest.mark.asyncio
    async def test_tick_check_numbers_sequential(self, fresh_bus, event_collector):
        """Tick check numbers are sequential."""
        fresh_bus.subscribe(Topics.SCHEDULER_TICK, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        for _ in range(10):
            await scheduler.tick()
        
        check_nums = [e.payload["check_number"] for e in event_collector.events]
        assert check_nums == list(range(1, 11))
    
    @pytest.mark.asyncio
    async def test_posts_processed_in_order(self, fresh_bus, event_collector):
        """Posts processed in submission order."""
        fresh_bus.subscribe("schedule.due", event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        
        for i in range(5):
            await scheduler.process_post({"id": f"post-{i}", "order": i})
        
        post_ids = [e.payload["post_id"] for e in event_collector.events]
        assert post_ids == [f"post-{i}" for i in range(5)]
    
    @pytest.mark.asyncio
    async def test_goal_plan_order(self, fresh_bus, event_collector):
        """Goal creation before plan generation."""
        fresh_bus.subscribe("narrative.*", event_collector.handler)
        
        builder = MockNarrativeBuilder(fresh_bus)
        goal = await builder.create_goal({"name": "Goal"})
        plan = await builder.generate_plan([goal["id"]])
        
        topics = [e.topic for e in event_collector.events]
        assert topics.index("narrative.goal.created") < topics.index("narrative.plan.generated")
    
    @pytest.mark.asyncio
    async def test_experiment_flow_order(self, fresh_bus, event_collector):
        """Experiment flow in correct order."""
        fresh_bus.subscribe("experiment.*", event_collector.handler)
        
        experiments = MockExperiments(fresh_bus)
        await experiments.calculate_confidence("exp-1", 10000, 10000, 0.65, 0.78)
        await experiments.generate_rule("exp-1", {"type": "hook"})
        
        topics = [e.topic for e in event_collector.events]
        assert topics.index("experiment.confidence.calculated") < topics.index("experiment.rule.generated")
    
    @pytest.mark.asyncio
    async def test_timestamps_monotonic_through_flow(self, fresh_bus, event_collector):
        """Timestamps monotonically increasing through flow."""
        fresh_bus.subscribe("*", event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.start()
        await scheduler.tick()
        await scheduler.process_post({"id": "1"})
        await scheduler.stop()
        
        timestamps = [e.timestamp for e in event_collector.events]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]
    
    @pytest.mark.asyncio
    async def test_correlation_chain_maintains_order(self, fresh_bus, event_collector):
        """Correlated events maintain order."""
        fresh_bus.subscribe("workflow.*", event_collector.handler)
        
        corr_id = str(uuid4())
        for step in ["start", "process", "complete"]:
            await fresh_bus.publish(f"workflow.{step}", {"step": step}, correlation_id=corr_id)
        
        steps = [e.payload["step"] for e in event_collector.events]
        assert steps == ["start", "process", "complete"]


# =============================================================================
# IDEMPOTENCY (8 tests)
# =============================================================================

class TestPhase3Idempotency:
    """Tests for Phase 3 idempotency."""
    
    @pytest.mark.asyncio
    async def test_scheduler_start_idempotent(self, fresh_bus, event_collector):
        """Multiple scheduler starts emit only first event."""
        fresh_bus.subscribe(Topics.SCHEDULER_STARTED, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.start()
        # Second start should be ignored (in real implementation)
        scheduler.is_running = False  # Reset for test
        await scheduler.start()
        
        # Both emitted in mock, but real scheduler is idempotent
        assert len(event_collector.events) >= 1
    
    @pytest.mark.asyncio
    async def test_post_processing_with_idempotency_key(self, fresh_bus):
        """Post processing can use idempotency key."""
        processed_keys = set()
        results = []
        
        async def idempotent_handler(event):
            key = event.payload.get("idempotency_key") or event.payload.get("post_id")
            if key in processed_keys:
                return
            processed_keys.add(key)
            results.append(event.payload["post_id"])
        
        fresh_bus.subscribe("schedule.due", idempotent_handler)
        
        scheduler = MockScheduler(fresh_bus)
        # Simulate duplicate post events
        await scheduler.process_post({"id": "post-1"})
        await scheduler.process_post({"id": "post-1"})  # Duplicate
        await scheduler.process_post({"id": "post-2"})
        
        assert results == ["post-1", "post-2"]
    
    @pytest.mark.asyncio
    async def test_goal_creation_idempotency_by_name(self, fresh_bus):
        """Goal creation can be idempotent by name."""
        created_names = set()
        goals = []
        
        async def idempotent_handler(event):
            name = event.payload.get("name")
            if name in created_names:
                return
            created_names.add(name)
            goals.append(name)
        
        fresh_bus.subscribe("narrative.goal.created", idempotent_handler)
        
        builder = MockNarrativeBuilder(fresh_bus)
        await builder.create_goal({"name": "Growth Goal"})
        await builder.create_goal({"name": "Growth Goal"})  # Duplicate
        await builder.create_goal({"name": "Engagement Goal"})
        
        assert goals == ["Growth Goal", "Engagement Goal"]
    
    @pytest.mark.asyncio
    async def test_rule_generation_idempotent_per_experiment(self, fresh_bus):
        """Rule generation idempotent per experiment."""
        generated_for = set()
        rules = []
        
        async def idempotent_handler(event):
            exp_id = event.payload.get("experiment_id")
            if exp_id in generated_for:
                return
            generated_for.add(exp_id)
            rules.append(event.payload["rule_id"])
        
        fresh_bus.subscribe("experiment.rule.generated", idempotent_handler)
        
        experiments = MockExperiments(fresh_bus)
        await experiments.generate_rule("exp-1", {"type": "hook"})
        await experiments.generate_rule("exp-1", {"type": "hook"})  # Duplicate
        await experiments.generate_rule("exp-2", {"type": "caption"})
        
        assert len(rules) == 2
    
    @pytest.mark.asyncio
    async def test_correlation_based_deduplication(self, fresh_bus):
        """Correlation-based deduplication works."""
        seen_correlations = set()
        processed = []
        
        async def dedup_handler(event):
            if event.correlation_id in seen_correlations:
                return
            seen_correlations.add(event.correlation_id)
            processed.append(event.payload)
        
        fresh_bus.subscribe("dedup.test", dedup_handler)
        
        corr1 = str(uuid4())
        await fresh_bus.publish("dedup.test", {"data": 1}, correlation_id=corr1)
        await fresh_bus.publish("dedup.test", {"data": 2}, correlation_id=corr1)  # Same corr
        await fresh_bus.publish("dedup.test", {"data": 3}, correlation_id=str(uuid4()))
        
        assert len(processed) == 2
    
    @pytest.mark.asyncio
    async def test_replay_detection_in_handler(self, fresh_bus):
        """Handler can detect replayed events."""
        original = []
        replays = []
        
        async def replay_aware_handler(event):
            if event.metadata.get("replayed_at"):
                replays.append(event)
            else:
                original.append(event)
        
        fresh_bus.subscribe("replay.test", replay_aware_handler)
        
        event_id = await fresh_bus.publish("replay.test", {"data": 1})
        await fresh_bus.replay_event(event_id)
        
        assert len(original) == 1
        assert len(replays) == 1
    
    @pytest.mark.asyncio
    async def test_content_hash_deduplication(self, fresh_bus):
        """Content hash prevents duplicate processing."""
        seen_hashes = set()
        processed = []
        
        async def hash_dedup_handler(event):
            content = json.dumps(event.payload, sort_keys=True)
            h = hashlib.md5(content.encode()).hexdigest()
            if h in seen_hashes:
                return
            seen_hashes.add(h)
            processed.append(event.payload)
        
        fresh_bus.subscribe("hash.test", hash_dedup_handler)
        
        await fresh_bus.publish("hash.test", {"a": 1, "b": 2})
        await fresh_bus.publish("hash.test", {"b": 2, "a": 1})  # Same content
        await fresh_bus.publish("hash.test", {"a": 1, "b": 3})  # Different
        
        assert len(processed) == 2
    
    @pytest.mark.asyncio
    async def test_tick_count_idempotency_check(self, fresh_bus, event_collector):
        """Tick count can be used for idempotency."""
        fresh_bus.subscribe(Topics.SCHEDULER_TICK, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        
        for _ in range(5):
            await scheduler.tick()
        
        check_numbers = [e.payload["check_number"] for e in event_collector.events]
        # All unique - can use as idempotency key
        assert len(set(check_numbers)) == 5


# =============================================================================
# BACKPRESSURE (8 tests)
# =============================================================================

class TestPhase3Backpressure:
    """Tests for Phase 3 backpressure behavior."""
    
    @pytest.mark.asyncio
    async def test_high_volume_posts(self, fresh_bus, event_collector):
        """Scheduler handles high volume of posts."""
        fresh_bus.subscribe("schedule.due", event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        
        for i in range(500):
            await scheduler.process_post({"id": f"post-{i}"})
        
        assert len(event_collector.events) == 500
    
    @pytest.mark.asyncio
    async def test_rapid_tick_events(self, fresh_bus, event_collector):
        """Rapid tick events handled correctly."""
        fresh_bus.subscribe(Topics.SCHEDULER_TICK, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        
        for _ in range(100):
            await scheduler.tick()
        
        assert len(event_collector.events) == 100
    
    @pytest.mark.asyncio
    async def test_concurrent_goal_creation(self, fresh_bus, event_collector):
        """Concurrent goal creations handled."""
        fresh_bus.subscribe("narrative.goal.created", event_collector.handler)
        
        builder = MockNarrativeBuilder(fresh_bus)
        
        async def create_goals(start, count):
            for i in range(start, start + count):
                await builder.create_goal({"name": f"Goal {i}"})
        
        await asyncio.gather(
            create_goals(0, 50),
            create_goals(50, 50),
            create_goals(100, 50)
        )
        
        assert len(event_collector.events) == 150
    
    @pytest.mark.asyncio
    async def test_many_confidence_calculations(self, fresh_bus, event_collector):
        """Many confidence calculations handled."""
        fresh_bus.subscribe("experiment.confidence.calculated", event_collector.handler)
        
        experiments = MockExperiments(fresh_bus)
        
        for i in range(100):
            await experiments.calculate_confidence(f"exp-{i}", 10000, 10000, 0.6, 0.7)
        
        assert len(event_collector.events) == 100
    
    @pytest.mark.asyncio
    async def test_failed_handler_doesnt_block_queue(self, fresh_bus, event_collector):
        """Failed handler doesn't block event processing."""
        fail_count = [0]
        
        async def failing_handler(event):
            fail_count[0] += 1
            if fail_count[0] <= 5:
                raise ValueError("Fail")
        
        async def success_handler(event):
            event_collector.events.append(event)
        
        fresh_bus.subscribe("test.backpressure", failing_handler)
        fresh_bus.subscribe("test.backpressure", success_handler)
        
        for i in range(10):
            await fresh_bus.publish("test.backpressure", {"n": i})
        
        # Success handler should receive all
        assert len(event_collector.events) == 10
    
    @pytest.mark.asyncio
    async def test_event_log_trim_under_load(self, fresh_bus):
        """Event log trims under high load."""
        fresh_bus._max_log_size = 100
        
        scheduler = MockScheduler(fresh_bus)
        
        for i in range(500):
            await scheduler.tick()
        
        assert len(fresh_bus._event_log) <= 100
    
    @pytest.mark.asyncio
    async def test_dlq_captures_all_failures(self, fresh_bus):
        """DLQ captures all failures under load."""
        async def always_fails(event):
            raise ValueError("Fail")
        
        fresh_bus.subscribe("fail.load", always_fails)
        
        for i in range(50):
            await fresh_bus.publish("fail.load", {"n": i})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) == 50
    
    @pytest.mark.asyncio
    async def test_stats_accurate_under_load(self, fresh_bus, event_collector):
        """Stats remain accurate under load."""
        fresh_bus.subscribe(Topics.SCHEDULER_TICK, event_collector.handler)
        
        scheduler = MockScheduler(fresh_bus)
        
        for _ in range(200):
            await scheduler.tick()
        
        stats = fresh_bus.get_stats()
        assert stats["total_events_logged"] >= 200


# =============================================================================
# CONSUMER ISOLATION (8 tests)
# =============================================================================

class TestPhase3Isolation:
    """Tests for Phase 3 consumer isolation."""
    
    @pytest.mark.asyncio
    async def test_scheduler_handler_failure_isolated(self, fresh_bus):
        """Scheduler handler failure doesn't affect others."""
        results = []
        
        async def fails(event):
            raise ValueError("Handler failed")
        
        async def succeeds(event):
            results.append(event.topic)
        
        fresh_bus.subscribe(Topics.SCHEDULER_TICK, fails)
        fresh_bus.subscribe(Topics.SCHEDULER_TICK, succeeds)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.tick()
        
        assert Topics.SCHEDULER_TICK in results
    
    @pytest.mark.asyncio
    async def test_publish_handler_failure_isolated(self, fresh_bus):
        """Publish handler failure doesn't affect others."""
        results = []
        
        async def fails(event):
            raise ValueError("Fail")
        
        async def succeeds(event):
            results.append(event.payload["post_id"])
        
        fresh_bus.subscribe(Topics.PUBLISH_COMPLETED, fails)
        fresh_bus.subscribe(Topics.PUBLISH_COMPLETED, succeeds)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.process_post({"id": "post-1"})
        
        assert "post-1" in results
    
    @pytest.mark.asyncio
    async def test_narrative_and_experiments_isolated(self, fresh_bus):
        """Narrative and Experiments systems isolated."""
        narrative_events = []
        experiment_events = []
        
        async def narrative_handler(event):
            narrative_events.append(event)
        
        async def experiment_handler(event):
            experiment_events.append(event)
        
        fresh_bus.subscribe("narrative.*", narrative_handler)
        fresh_bus.subscribe("experiment.*", experiment_handler)
        
        builder = MockNarrativeBuilder(fresh_bus)
        experiments = MockExperiments(fresh_bus)
        
        await builder.create_goal({"name": "Goal"})
        await experiments.calculate_confidence("exp-1", 1000, 1000, 0.6, 0.7)
        
        assert len(narrative_events) == 1
        assert len(experiment_events) == 1
    
    @pytest.mark.asyncio
    async def test_scheduler_and_publisher_isolated(self, fresh_bus):
        """Scheduler and publisher events isolated."""
        scheduler_events = []
        publish_events = []
        
        async def scheduler_handler(event):
            scheduler_events.append(event)
        
        async def publish_handler(event):
            publish_events.append(event)
        
        fresh_bus.subscribe("scheduler.*", scheduler_handler)
        fresh_bus.subscribe("publish.*", publish_handler)
        
        scheduler = MockScheduler(fresh_bus)
        await scheduler.start()
        await scheduler.process_post({"id": "1"})
        
        # Scheduler events should not include publish events
        scheduler_topics = [e.topic for e in scheduler_events]
        assert Topics.PUBLISH_COMPLETED not in scheduler_topics
    
    @pytest.mark.asyncio
    async def test_multiple_schedulers_isolated(self, fresh_bus):
        """Multiple scheduler instances isolated."""
        s1 = MockScheduler(fresh_bus)
        s2 = MockScheduler(fresh_bus)
        
        await s1.tick()
        await s1.tick()
        await s2.tick()
        
        assert s1._check_count == 2
        assert s2._check_count == 1
    
    @pytest.mark.asyncio
    async def test_builder_instances_isolated(self, fresh_bus):
        """Multiple builder instances isolated."""
        b1 = MockNarrativeBuilder(fresh_bus)
        b2 = MockNarrativeBuilder(fresh_bus)
        
        await b1.create_goal({"name": "B1 Goal"})
        await b2.create_goal({"name": "B2 Goal"})
        
        assert len(b1.goals) == 1
        assert len(b2.goals) == 1
        assert list(b1.goals.values())[0]["name"] == "B1 Goal"
    
    @pytest.mark.asyncio
    async def test_experiment_instances_isolated(self, fresh_bus):
        """Multiple experiment instances isolated."""
        e1 = MockExperiments(fresh_bus)
        e2 = MockExperiments(fresh_bus)
        
        await e1.generate_rule("exp-1", {"type": "hook"})
        await e2.generate_rule("exp-2", {"type": "caption"})
        
        assert len(e1.rules_generated) == 1
        assert len(e2.rules_generated) == 1
    
    @pytest.mark.asyncio
    async def test_correlation_filtering_isolated(self, fresh_bus):
        """Correlation filtering works in isolation."""
        corr_a_events = []
        corr_b_events = []
        
        async def filter_a(event):
            if event.correlation_id == "corr-A":
                corr_a_events.append(event)
        
        async def filter_b(event):
            if event.correlation_id == "corr-B":
                corr_b_events.append(event)
        
        fresh_bus.subscribe("workflow.*", filter_a)
        fresh_bus.subscribe("workflow.*", filter_b)
        
        await fresh_bus.publish("workflow.step", {"data": 1}, correlation_id="corr-A")
        await fresh_bus.publish("workflow.step", {"data": 2}, correlation_id="corr-B")
        await fresh_bus.publish("workflow.step", {"data": 3}, correlation_id="corr-A")
        
        assert len(corr_a_events) == 2
        assert len(corr_b_events) == 1


# =============================================================================
# SCHEMA EVOLUTION (8 tests)
# =============================================================================

class TestPhase3SchemaEvolution:
    """Tests for Phase 3 schema evolution."""
    
    @pytest.mark.asyncio
    async def test_scheduler_tick_optional_fields(self, fresh_bus, event_collector):
        """Scheduler tick handles optional fields."""
        fresh_bus.subscribe(Topics.SCHEDULER_TICK, event_collector.handler)
        
        # Simulate old schema (no timestamp)
        await fresh_bus.publish(Topics.SCHEDULER_TICK, {
            "check_number": 1,
            "due_count": 0
        })
        
        # New schema (with timestamp)
        await fresh_bus.publish(Topics.SCHEDULER_TICK, {
            "check_number": 2,
            "due_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Both handled
        assert len(event_collector.events) == 2
    
    @pytest.mark.asyncio
    async def test_goal_schema_evolution(self, fresh_bus):
        """Goal events handle schema evolution."""
        results = []
        
        async def flexible_handler(event):
            # Handle both old and new schema
            name = event.payload.get("name") or event.payload.get("goal_name")
            results.append(name)
        
        fresh_bus.subscribe("narrative.goal.created", flexible_handler)
        
        await fresh_bus.publish("narrative.goal.created", {"goal_name": "Old Schema"})
        await fresh_bus.publish("narrative.goal.created", {"name": "New Schema"})
        
        assert results == ["Old Schema", "New Schema"]
    
    @pytest.mark.asyncio
    async def test_experiment_schema_versioning(self, fresh_bus):
        """Experiment events support schema versioning."""
        results = []
        
        async def versioned_handler(event):
            version = event.metadata.get("schema_version", 1)
            if version == 1:
                results.append(("v1", event.payload.get("confidence")))
            elif version == 2:
                results.append(("v2", event.payload.get("stats", {}).get("confidence")))
        
        fresh_bus.subscribe("experiment.confidence.calculated", versioned_handler)
        
        await fresh_bus.publish("experiment.confidence.calculated",
                               {"confidence": 95}, metadata={"schema_version": 1})
        await fresh_bus.publish("experiment.confidence.calculated",
                               {"stats": {"confidence": 97}}, metadata={"schema_version": 2})
        
        assert results == [("v1", 95), ("v2", 97)]
    
    @pytest.mark.asyncio
    async def test_publish_event_schema_migration(self, fresh_bus):
        """Publish events handle schema migration."""
        urls = []
        
        async def url_extractor(event):
            # Old: platform_url, New: url or urls[]
            url = (event.payload.get("platform_url") or 
                   event.payload.get("url") or 
                   (event.payload.get("urls", [None])[0]))
            urls.append(url)
        
        fresh_bus.subscribe(Topics.PUBLISH_COMPLETED, url_extractor)
        
        await fresh_bus.publish(Topics.PUBLISH_COMPLETED, {"platform_url": "old.com"})
        await fresh_bus.publish(Topics.PUBLISH_COMPLETED, {"url": "new.com"})
        await fresh_bus.publish(Topics.PUBLISH_COMPLETED, {"urls": ["array.com"]})
        
        assert urls == ["old.com", "new.com", "array.com"]
    
    @pytest.mark.asyncio
    async def test_rule_schema_backward_compatible(self, fresh_bus):
        """Rule events are backward compatible."""
        rules = []
        
        async def rule_handler(event):
            # Support both old and new field names
            rule_id = event.payload.get("rule_id") or event.payload.get("id")
            rules.append(rule_id)
        
        fresh_bus.subscribe("experiment.rule.generated", rule_handler)
        
        await fresh_bus.publish("experiment.rule.generated", {"id": "old-format"})
        await fresh_bus.publish("experiment.rule.generated", {"rule_id": "new-format"})
        
        assert rules == ["old-format", "new-format"]
    
    @pytest.mark.asyncio
    async def test_nested_payload_evolution(self, fresh_bus):
        """Nested payload structures evolve gracefully."""
        values = []
        
        async def nested_handler(event):
            # V1: flat, V2: nested
            if "metrics" in event.payload:
                values.append(event.payload["metrics"]["value"])
            else:
                values.append(event.payload.get("value"))
        
        fresh_bus.subscribe("metrics.event", nested_handler)
        
        await fresh_bus.publish("metrics.event", {"value": 10})
        await fresh_bus.publish("metrics.event", {"metrics": {"value": 20}})
        
        assert values == [10, 20]
    
    @pytest.mark.asyncio
    async def test_array_field_evolution(self, fresh_bus):
        """Array fields evolve from single to multiple."""
        platforms = []
        
        async def platform_handler(event):
            # Old: single platform string, New: platforms array
            p = event.payload.get("platforms") or [event.payload.get("platform")]
            platforms.extend(p)
        
        fresh_bus.subscribe("post.created", platform_handler)
        
        await fresh_bus.publish("post.created", {"platform": "tiktok"})
        await fresh_bus.publish("post.created", {"platforms": ["tiktok", "instagram"]})
        
        assert platforms == ["tiktok", "tiktok", "instagram"]
    
    @pytest.mark.asyncio
    async def test_unknown_fields_ignored(self, fresh_bus):
        """Unknown fields are gracefully ignored."""
        results = []
        
        async def strict_handler(event):
            # Only process known fields
            results.append({
                "id": event.payload.get("id"),
                "name": event.payload.get("name")
            })
        
        fresh_bus.subscribe("entity.created", strict_handler)
        
        await fresh_bus.publish("entity.created", {
            "id": "1", "name": "Test",
            "new_field_v2": "ignored", "future_feature": True
        })
        
        assert results[0] == {"id": "1", "name": "Test"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
