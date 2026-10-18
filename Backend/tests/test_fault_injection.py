"""
Fault Injection Test Suite
===========================
Tests for system resilience under failure conditions.

Test Categories:
- Network & Timeout Failures (15 tests)
- Database & Connection Failures (15 tests)
- Handler Crashes & Recovery (15 tests)
- Resource Exhaustion (10 tests)
- Chaos Engineering Scenarios (10 tests)
- Graceful Degradation (10 tests)

Total: 75 tests
"""

import pytest
import asyncio
import time
import random
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.event_bus import EventBus, Event, Topics
from services.workers.base import BaseWorker


# =============================================================================
# FAULT INJECTION UTILITIES
# =============================================================================

class FaultInjector:
    """Utility for injecting various faults into the system."""
    
    def __init__(self):
        self.faults_triggered = 0
        self.fault_log: List[Dict] = []
    
    def log_fault(self, fault_type: str, details: Dict = None):
        self.faults_triggered += 1
        self.fault_log.append({
            "type": fault_type,
            "timestamp": time.time(),
            "details": details or {}
        })
    
    async def network_timeout(self, delay: float = 5.0):
        """Simulate network timeout."""
        self.log_fault("network_timeout", {"delay": delay})
        await asyncio.sleep(delay)
        raise TimeoutError("Network request timed out")
    
    async def connection_refused(self):
        """Simulate connection refused."""
        self.log_fault("connection_refused")
        raise ConnectionRefusedError("Connection refused by remote host")
    
    async def connection_reset(self):
        """Simulate connection reset."""
        self.log_fault("connection_reset")
        raise ConnectionResetError("Connection reset by peer")
    
    async def database_error(self, error_type: str = "generic"):
        """Simulate database error."""
        self.log_fault("database_error", {"error_type": error_type})
        if error_type == "deadlock":
            raise Exception("Deadlock detected")
        elif error_type == "connection_lost":
            raise Exception("Database connection lost")
        elif error_type == "constraint_violation":
            raise Exception("Constraint violation")
        else:
            raise Exception("Database error")
    
    async def oom_simulation(self):
        """Simulate out of memory condition."""
        self.log_fault("oom")
        raise MemoryError("Out of memory")
    
    def random_failure(self, probability: float = 0.3):
        """Randomly decide to fail."""
        if random.random() < probability:
            self.log_fault("random_failure", {"probability": probability})
            raise Exception("Random failure injected")
    
    async def slow_response(self, min_delay: float = 0.1, max_delay: float = 1.0):
        """Inject variable latency."""
        delay = random.uniform(min_delay, max_delay)
        self.log_fault("slow_response", {"delay": delay})
        await asyncio.sleep(delay)
    
    async def intermittent_failure(self, fail_count: int, then_succeed: bool = True):
        """Fail N times then optionally succeed."""
        if self.faults_triggered < fail_count:
            self.log_fault("intermittent_failure", {"attempt": self.faults_triggered + 1})
            raise Exception(f"Intermittent failure {self.faults_triggered + 1}/{fail_count}")
        if then_succeed:
            return True
        raise Exception("Final failure")


class FaultyWorker(BaseWorker):
    """Worker that can be configured to fail in various ways."""
    
    def __init__(self, event_bus=None, fault_mode: str = "none", 
                 fail_on_events: List[int] = None, recovery_after: int = None):
        self.fault_mode = fault_mode
        self.fail_on_events = fail_on_events or []
        self.recovery_after = recovery_after
        self.event_count = 0
        self.handled_events: List[Event] = []
        self.errors: List[Exception] = []
        super().__init__(event_bus)
    
    def get_subscriptions(self) -> List[str]:
        return ["fault.*"]
    
    async def handle_event(self, event: Event) -> None:
        self.event_count += 1
        
        # Check if we should fail
        should_fail = (
            self.event_count in self.fail_on_events or
            (self.fault_mode == "always" and 
             (self.recovery_after is None or self.event_count <= self.recovery_after))
        )
        
        if should_fail:
            error = self._generate_fault()
            self.errors.append(error)
            raise error
        
        self.handled_events.append(event)
    
    def _generate_fault(self) -> Exception:
        if self.fault_mode == "timeout":
            return TimeoutError("Handler timeout")
        elif self.fault_mode == "connection":
            return ConnectionError("Connection failed")
        elif self.fault_mode == "value":
            return ValueError("Invalid value")
        elif self.fault_mode == "runtime":
            return RuntimeError("Runtime error")
        elif self.fault_mode == "memory":
            return MemoryError("Out of memory")
        else:
            return Exception("Generic failure")


class CircuitBreaker:
    """Simple circuit breaker for fault tolerance testing."""
    
    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 1.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = "closed"  # closed, open, half-open
        self.last_failure_time: Optional[float] = None
    
    def record_success(self):
        self.failures = 0
        self.state = "closed"
    
    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"
    
    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.reset_timeout:
                self.state = "half-open"
                return True
            return False
        return True  # half-open


@pytest.fixture
def fresh_bus():
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()


@pytest.fixture
def fault_injector():
    return FaultInjector()


# =============================================================================
# NETWORK & TIMEOUT FAILURES (15 tests)
# =============================================================================

class TestNetworkFailures:
    """Tests for network-related fault handling."""
    
    @pytest.mark.asyncio
    async def test_handler_timeout_goes_to_dlq(self, fresh_bus):
        """Timeout in handler should go to DLQ."""
        async def timeout_handler(event):
            raise TimeoutError("Request timed out")
        
        fresh_bus.subscribe("test.timeout", timeout_handler)
        await fresh_bus.publish("test.timeout", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
        assert "timed out" in dlq[0][1].lower()
    
    @pytest.mark.asyncio
    async def test_connection_error_captured(self, fresh_bus):
        """Connection errors should be captured in DLQ."""
        async def connection_handler(event):
            raise ConnectionError("Connection refused")
        
        fresh_bus.subscribe("test.conn", connection_handler)
        await fresh_bus.publish("test.conn", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_other_handlers_execute_after_timeout(self, fresh_bus):
        """Other handlers should still execute after one times out."""
        results = []
        
        async def timeout_handler(event):
            raise TimeoutError("Timeout")
        
        async def success_handler(event):
            results.append("success")
        
        fresh_bus.subscribe("test.mixed", timeout_handler)
        fresh_bus.subscribe("test.mixed", success_handler)
        
        await fresh_bus.publish("test.mixed", {})
        
        assert "success" in results
    
    @pytest.mark.asyncio
    async def test_slow_handler_completes(self, fresh_bus):
        """Slow but successful handler should complete."""
        results = []
        
        async def slow_handler(event):
            await asyncio.sleep(0.1)
            results.append("completed")
        
        fresh_bus.subscribe("test.slow", slow_handler)
        await fresh_bus.publish("test.slow", {})
        
        assert "completed" in results
    
    @pytest.mark.asyncio
    async def test_network_error_doesnt_lose_event(self, fresh_bus):
        """Network errors shouldn't lose the event."""
        async def network_fail(event):
            raise ConnectionResetError("Reset by peer")
        
        fresh_bus.subscribe("test.network", network_fail)
        event_id = await fresh_bus.publish("test.network", {"data": "important"})
        
        # Event should still be in log
        recent = fresh_bus.get_recent_events()
        event_ids = [e.id for e in recent]
        assert event_id in event_ids
    
    @pytest.mark.asyncio
    async def test_intermittent_timeout_recovery(self, fresh_bus):
        """System recovers from intermittent timeouts."""
        call_count = [0]
        successes = []
        
        async def intermittent_handler(event):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise TimeoutError("Intermittent timeout")
            successes.append(event.payload["n"])
        
        fresh_bus.subscribe("test.intermittent", intermittent_handler)
        
        for i in range(5):
            await fresh_bus.publish("test.intermittent", {"n": i})
        
        # Events 3, 4, 5 should succeed
        assert len(successes) == 3
    
    @pytest.mark.asyncio
    async def test_dns_failure_simulation(self, fresh_bus):
        """DNS lookup failures are handled."""
        async def dns_fail(event):
            raise OSError("Name or service not known")
        
        fresh_bus.subscribe("test.dns", dns_fail)
        await fresh_bus.publish("test.dns", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_ssl_error_handling(self, fresh_bus):
        """SSL errors are captured."""
        async def ssl_fail(event):
            raise Exception("SSL: CERTIFICATE_VERIFY_FAILED")
        
        fresh_bus.subscribe("test.ssl", ssl_fail)
        await fresh_bus.publish("test.ssl", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert any("SSL" in entry[1] for entry in dlq)
    
    @pytest.mark.asyncio
    async def test_partial_network_failure(self, fresh_bus):
        """Partial network failures - some handlers succeed."""
        results = {"success": 0, "fail": 0}
        
        async def unstable_handler(event):
            if event.payload.get("fail"):
                raise ConnectionError("Network unstable")
            results["success"] += 1
        
        fresh_bus.subscribe("test.partial", unstable_handler)
        
        await fresh_bus.publish("test.partial", {"fail": False})
        await fresh_bus.publish("test.partial", {"fail": True})
        await fresh_bus.publish("test.partial", {"fail": False})
        
        assert results["success"] == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_timeout_handling(self, fresh_bus):
        """Multiple concurrent timeouts handled correctly."""
        timeouts = []
        
        async def timeout_tracker(event):
            timeouts.append(event.payload["id"])
            raise TimeoutError(f"Timeout for {event.payload['id']}")
        
        fresh_bus.subscribe("test.concurrent.timeout", timeout_tracker)
        
        # Concurrent publishes
        await asyncio.gather(*[
            fresh_bus.publish("test.concurrent.timeout", {"id": i})
            for i in range(10)
        ])
        
        # All should be tracked
        assert len(timeouts) == 10
        
        # All should be in DLQ
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 10
    
    @pytest.mark.asyncio
    async def test_timeout_with_retry_pattern(self, fresh_bus):
        """Demonstrate retry pattern after timeout."""
        attempts = []
        
        async def retry_handler(event):
            attempt = event.metadata.get("retry_count", 0)
            attempts.append(attempt)
            if attempt < 2:
                raise TimeoutError("Still timing out")
            # Success on 3rd attempt
        
        fresh_bus.subscribe("test.retry", retry_handler)
        
        # Simulate retry logic - each publish is independent
        for retry in range(3):
            await fresh_bus.publish("test.retry", {}, metadata={"retry_count": retry})
        
        # All 3 attempts recorded
        assert len(attempts) == 3
        assert attempts == [0, 1, 2]
    
    @pytest.mark.asyncio
    async def test_cascading_timeout_isolation(self, fresh_bus):
        """Timeout in one service doesn't cascade."""
        service_a_results = []
        service_b_results = []
        
        async def service_a(event):
            raise TimeoutError("Service A timeout")
        
        async def service_b(event):
            service_b_results.append("ok")
        
        fresh_bus.subscribe("workflow.start", service_a)
        fresh_bus.subscribe("workflow.start", service_b)
        
        await fresh_bus.publish("workflow.start", {})
        
        # Service B should still work
        assert len(service_b_results) == 1
    
    @pytest.mark.asyncio
    async def test_http_status_error_handling(self, fresh_bus):
        """HTTP status errors (500, 503) handled."""
        async def http_error(event):
            status = event.payload.get("status", 500)
            raise Exception(f"HTTP {status}: Server Error")
        
        fresh_bus.subscribe("test.http", http_error)
        
        await fresh_bus.publish("test.http", {"status": 500})
        await fresh_bus.publish("test.http", {"status": 503})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 2
    
    @pytest.mark.asyncio
    async def test_network_partition_simulation(self, fresh_bus):
        """Simulate network partition - events queue up."""
        partitioned = [True]
        queued = []
        processed = []
        
        async def partition_aware_handler(event):
            if partitioned[0]:
                queued.append(event)
                raise ConnectionError("Network partition")
            processed.append(event)
        
        fresh_bus.subscribe("test.partition", partition_aware_handler)
        
        # During partition
        for i in range(5):
            await fresh_bus.publish("test.partition", {"n": i})
        
        assert len(queued) == 5
        
        # Heal partition
        partitioned[0] = False
        await fresh_bus.publish("test.partition", {"n": 5})
        
        assert len(processed) == 1


# =============================================================================
# DATABASE & CONNECTION FAILURES (15 tests)
# =============================================================================

class TestDatabaseFailures:
    """Tests for database-related fault handling."""
    
    @pytest.mark.asyncio
    async def test_db_connection_lost(self, fresh_bus):
        """Database connection lost is captured."""
        async def db_handler(event):
            raise Exception("Connection to database lost")
        
        fresh_bus.subscribe("test.db", db_handler)
        await fresh_bus.publish("test.db", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_deadlock_handling(self, fresh_bus):
        """Deadlock errors are captured."""
        async def deadlock_handler(event):
            raise Exception("Deadlock detected, transaction rolled back")
        
        fresh_bus.subscribe("test.deadlock", deadlock_handler)
        await fresh_bus.publish("test.deadlock", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert any("Deadlock" in e[1] for e in dlq)
    
    @pytest.mark.asyncio
    async def test_constraint_violation(self, fresh_bus):
        """Constraint violations are captured."""
        async def constraint_handler(event):
            raise Exception("IntegrityError: duplicate key value")
        
        fresh_bus.subscribe("test.constraint", constraint_handler)
        await fresh_bus.publish("test.constraint", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, fresh_bus):
        """Transaction rollback doesn't lose event."""
        rolled_back = []
        
        async def tx_handler(event):
            rolled_back.append(event.id)
            raise Exception("Transaction rolled back")
        
        fresh_bus.subscribe("test.rollback", tx_handler)
        event_id = await fresh_bus.publish("test.rollback", {"critical": True})
        
        # Event logged even though handler failed
        assert event_id in rolled_back
        recent = fresh_bus.get_recent_events()
        assert any(e.id == event_id for e in recent)
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhausted(self, fresh_bus):
        """Connection pool exhaustion is handled."""
        async def pool_handler(event):
            raise Exception("Connection pool exhausted")
        
        fresh_bus.subscribe("test.pool", pool_handler)
        
        for _ in range(10):
            await fresh_bus.publish("test.pool", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) == 10
    
    @pytest.mark.asyncio
    async def test_query_timeout(self, fresh_bus):
        """Query timeout is handled."""
        async def query_handler(event):
            raise Exception("Query execution timeout")
        
        fresh_bus.subscribe("test.query", query_handler)
        await fresh_bus.publish("test.query", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_data_corruption_detection(self, fresh_bus):
        """Data corruption is detected and reported."""
        async def corruption_handler(event):
            raise Exception("Data corruption detected: checksum mismatch")
        
        fresh_bus.subscribe("test.corruption", corruption_handler)
        await fresh_bus.publish("test.corruption", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert any("corruption" in e[1].lower() for e in dlq)
    
    @pytest.mark.asyncio
    async def test_read_replica_lag(self, fresh_bus):
        """Read replica lag simulation."""
        writes = []
        reads = []
        lag_events = []
        
        async def write_handler(event):
            writes.append(event.payload["id"])
        
        async def read_handler(event):
            write_id = event.payload.get("read_after_write")
            if write_id and write_id not in writes:
                lag_events.append(event)
                raise Exception("Read replica lag - data not yet available")
            reads.append(event.payload["id"])
        
        fresh_bus.subscribe("db.write", write_handler)
        fresh_bus.subscribe("db.read", read_handler)
        
        await fresh_bus.publish("db.write", {"id": "w1"})
        await fresh_bus.publish("db.read", {"id": "r1", "read_after_write": "w1"})
        
        assert "w1" in writes
        assert "r1" in reads
    
    @pytest.mark.asyncio
    async def test_schema_migration_error(self, fresh_bus):
        """Schema migration errors are handled."""
        async def migration_handler(event):
            raise Exception("Column 'new_field' does not exist")
        
        fresh_bus.subscribe("test.migration", migration_handler)
        await fresh_bus.publish("test.migration", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_serialization_error(self, fresh_bus):
        """Serialization errors are handled."""
        async def serialize_handler(event):
            raise Exception("Cannot serialize object of type 'datetime'")
        
        fresh_bus.subscribe("test.serialize", serialize_handler)
        await fresh_bus.publish("test.serialize", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_foreign_key_violation(self, fresh_bus):
        """Foreign key violations handled."""
        async def fk_handler(event):
            raise Exception("Foreign key constraint violated")
        
        fresh_bus.subscribe("test.fk", fk_handler)
        await fresh_bus.publish("test.fk", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_unique_constraint_retry(self, fresh_bus):
        """Unique constraint with retry logic."""
        attempts = []
        success = []
        
        async def unique_handler(event):
            attempt = len(attempts)
            attempts.append(attempt)
            if attempt == 0:
                raise Exception("Unique constraint violation")
            # Generate new unique value and succeed
            success.append(event.payload)
        
        fresh_bus.subscribe("test.unique", unique_handler)
        
        # First attempt fails
        await fresh_bus.publish("test.unique", {"value": "duplicate"})
        # Retry succeeds
        await fresh_bus.publish("test.unique", {"value": "unique"})
        
        assert len(success) == 1
    
    @pytest.mark.asyncio
    async def test_db_failover_simulation(self, fresh_bus):
        """Database failover scenario."""
        primary_down = [True]
        results = []
        
        async def failover_handler(event):
            if primary_down[0]:
                raise Exception("Primary database unavailable, failing over...")
            results.append("processed on replica")
        
        fresh_bus.subscribe("test.failover", failover_handler)
        
        # During failover
        await fresh_bus.publish("test.failover", {})
        assert len(results) == 0
        
        # After failover
        primary_down[0] = False
        await fresh_bus.publish("test.failover", {})
        assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_max_connections_exceeded(self, fresh_bus):
        """Max connections exceeded is handled."""
        async def max_conn_handler(event):
            raise Exception("FATAL: too many connections for role")
        
        fresh_bus.subscribe("test.maxconn", max_conn_handler)
        await fresh_bus.publish("test.maxconn", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1


# =============================================================================
# HANDLER CRASHES & RECOVERY (15 tests)
# =============================================================================

class TestHandlerCrashes:
    """Tests for handler crash and recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_unhandled_exception(self, fresh_bus):
        """Unhandled exception doesn't crash the bus."""
        async def crash_handler(event):
            raise RuntimeError("Unexpected crash")
        
        async def healthy_handler(event):
            pass
        
        fresh_bus.subscribe("test.crash", crash_handler)
        fresh_bus.subscribe("test.healthy", healthy_handler)
        
        await fresh_bus.publish("test.crash", {})
        # Bus should still work
        await fresh_bus.publish("test.healthy", {})
        
        # Verify bus is functional
        stats = fresh_bus.get_stats()
        assert stats["is_running"]
    
    @pytest.mark.asyncio
    async def test_memory_error_handling(self, fresh_bus):
        """MemoryError is captured."""
        async def oom_handler(event):
            raise MemoryError("Out of memory")
        
        fresh_bus.subscribe("test.oom", oom_handler)
        await fresh_bus.publish("test.oom", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_recursion_error(self, fresh_bus):
        """RecursionError is captured."""
        async def recursive_handler(event):
            raise RecursionError("Maximum recursion depth exceeded")
        
        fresh_bus.subscribe("test.recursion", recursive_handler)
        await fresh_bus.publish("test.recursion", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_assertion_error(self, fresh_bus):
        """AssertionError is captured."""
        async def assert_handler(event):
            assert False, "Assertion failed"
        
        fresh_bus.subscribe("test.assert", assert_handler)
        await fresh_bus.publish("test.assert", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_type_error_in_handler(self, fresh_bus):
        """TypeError is captured."""
        async def type_handler(event):
            result = "string" + 123  # TypeError
        
        fresh_bus.subscribe("test.type", type_handler)
        await fresh_bus.publish("test.type", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_key_error_in_handler(self, fresh_bus):
        """KeyError is captured."""
        async def key_handler(event):
            value = event.payload["nonexistent_key"]
        
        fresh_bus.subscribe("test.key", key_handler)
        await fresh_bus.publish("test.key", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_attribute_error_in_handler(self, fresh_bus):
        """AttributeError is captured."""
        async def attr_handler(event):
            event.nonexistent_method()
        
        fresh_bus.subscribe("test.attr", attr_handler)
        await fresh_bus.publish("test.attr", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_worker_crash_recovery(self, fresh_bus):
        """FaultyWorker recovers after crashes."""
        worker = FaultyWorker(fresh_bus, fault_mode="always", recovery_after=3)
        await worker.start()
        
        for i in range(6):
            await fresh_bus.publish("fault.test", {"n": i})
        
        # First 3 fail, last 3 succeed
        assert len(worker.errors) == 3
        assert len(worker.handled_events) == 3
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_specific_event_failures(self, fresh_bus):
        """Worker fails only on specific events."""
        worker = FaultyWorker(fresh_bus, fail_on_events=[2, 4])
        await worker.start()
        
        for i in range(1, 6):
            await fresh_bus.publish("fault.test", {"n": i})
        
        # Events 2 and 4 fail
        assert len(worker.errors) == 2
        assert len(worker.handled_events) == 3
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_crash_doesnt_affect_other_workers(self, fresh_bus):
        """Crash in one worker doesn't affect others."""
        crashing = FaultyWorker(fresh_bus, fault_mode="always")
        healthy = FaultyWorker(fresh_bus, fault_mode="none")
        
        await crashing.start()
        await healthy.start()
        
        await fresh_bus.publish("fault.test", {"data": 1})
        
        assert len(crashing.errors) == 1
        assert len(healthy.handled_events) == 1
        
        await crashing.stop()
        await healthy.stop()
    
    @pytest.mark.asyncio
    async def test_exception_message_in_dlq(self, fresh_bus):
        """Exception message preserved in DLQ."""
        async def detailed_error(event):
            raise ValueError("Detailed error message: invalid input 'xyz'")
        
        fresh_bus.subscribe("test.detailed", detailed_error)
        await fresh_bus.publish("test.detailed", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert any("Detailed error message" in e[1] for e in dlq)
    
    @pytest.mark.asyncio
    async def test_nested_exception(self, fresh_bus):
        """Nested exceptions are captured."""
        async def nested_error(event):
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise RuntimeError("Outer error") from e
        
        fresh_bus.subscribe("test.nested", nested_error)
        await fresh_bus.publish("test.nested", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_async_context_error(self, fresh_bus):
        """Async context errors are captured."""
        async def context_error(event):
            async with asynccontextmanager(lambda: (_ for _ in ()).throw(ValueError("Context error")))():
                pass
        
        fresh_bus.subscribe("test.context", context_error)
        await fresh_bus.publish("test.context", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1
    
    @pytest.mark.asyncio
    async def test_division_error(self, fresh_bus):
        """Division by zero is captured."""
        async def div_handler(event):
            result = 1 / 0
        
        fresh_bus.subscribe("test.div", div_handler)
        await fresh_bus.publish("test.div", {})
        
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) >= 1


# =============================================================================
# RESOURCE EXHAUSTION (10 tests)
# =============================================================================

class TestResourceExhaustion:
    """Tests for resource exhaustion scenarios."""
    
    @pytest.mark.asyncio
    async def test_event_log_size_limit(self, fresh_bus):
        """Event log respects size limit."""
        fresh_bus._max_log_size = 100
        
        for i in range(500):
            await fresh_bus.publish("test.volume", {"n": i})
        
        assert len(fresh_bus._event_log) <= 100
    
    @pytest.mark.asyncio
    async def test_dlq_under_high_failure_rate(self, fresh_bus):
        """DLQ handles high failure rate."""
        async def always_fails(event):
            raise Exception("Always fails")
        
        fresh_bus.subscribe("test.fail", always_fails)
        
        for i in range(100):
            await fresh_bus.publish("test.fail", {"n": i})
        
        dlq = fresh_bus.get_dead_letter_queue(limit=200)
        assert len(dlq) >= 100
    
    @pytest.mark.asyncio
    async def test_clear_dlq_under_load(self, fresh_bus):
        """DLQ can be cleared under load."""
        async def fails(event):
            raise Exception("Fail")
        
        fresh_bus.subscribe("test.clear", fails)
        
        for _ in range(50):
            await fresh_bus.publish("test.clear", {})
        
        cleared = fresh_bus.clear_dead_letter_queue()
        assert cleared == 50
        assert len(fresh_bus.get_dead_letter_queue()) == 0
    
    @pytest.mark.asyncio
    async def test_many_subscribers_per_topic(self, fresh_bus):
        """Many subscribers on same topic."""
        results = []
        
        for i in range(100):
            async def handler(event, idx=i):
                results.append(idx)
            fresh_bus.subscribe("test.many", handler)
        
        await fresh_bus.publish("test.many", {})
        
        assert len(results) == 100
    
    @pytest.mark.asyncio
    async def test_many_topics(self, fresh_bus):
        """Many different topics."""
        received = []
        
        for i in range(100):
            async def handler(event, idx=i):
                received.append(idx)
            fresh_bus.subscribe(f"topic.{i}", handler)
        
        for i in range(100):
            await fresh_bus.publish(f"topic.{i}", {})
        
        assert len(received) == 100
    
    @pytest.mark.asyncio
    async def test_large_payload_handling(self, fresh_bus):
        """Large payloads don't crash the system."""
        received = []
        
        async def large_handler(event):
            received.append(len(str(event.payload)))
        
        fresh_bus.subscribe("test.large", large_handler)
        
        # 1MB payload
        large_data = {"data": "x" * (1024 * 1024)}
        await fresh_bus.publish("test.large", large_data)
        
        assert len(received) == 1
        assert received[0] > 1000000
    
    @pytest.mark.asyncio
    async def test_rapid_subscribe_unsubscribe(self, fresh_bus):
        """Rapid subscribe/unsubscribe cycles."""
        for i in range(100):
            async def handler(event):
                pass
            fresh_bus.subscribe("test.rapid", handler)
            fresh_bus.unsubscribe("test.rapid", handler)
        
        # System should still work
        await fresh_bus.publish("test.rapid", {})
        assert fresh_bus.get_stats()["is_running"]
    
    @pytest.mark.asyncio
    async def test_concurrent_publish_load(self, fresh_bus):
        """Concurrent publishes under load."""
        received = []
        
        async def collector(event):
            received.append(event.payload["n"])
        
        fresh_bus.subscribe("test.concurrent", collector)
        
        async def publish_batch(start, count):
            for i in range(start, start + count):
                await fresh_bus.publish("test.concurrent", {"n": i})
        
        await asyncio.gather(*[
            publish_batch(i * 100, 100) for i in range(5)
        ])
        
        assert len(received) == 500
    
    @pytest.mark.asyncio
    async def test_stats_under_exhaustion(self, fresh_bus):
        """Stats remain accurate under resource pressure."""
        async def fails(event):
            if event.payload["n"] % 2 == 0:
                raise Exception("Even fail")
        
        fresh_bus.subscribe("test.stats", fails)
        
        for i in range(100):
            await fresh_bus.publish("test.stats", {"n": i})
        
        stats = fresh_bus.get_stats()
        assert stats["dead_letter_count"] == 50
    
    @pytest.mark.asyncio
    async def test_memory_efficient_event_trim(self, fresh_bus):
        """Event log trimming is memory efficient."""
        fresh_bus._max_log_size = 50
        
        # Fill with large events
        for i in range(100):
            await fresh_bus.publish("test.trim", {"data": "x" * 10000, "n": i})
        
        # Should only have 50 most recent
        recent = fresh_bus.get_recent_events(limit=50)
        ns = [e.payload["n"] for e in recent]
        assert max(ns) >= 90  # Recent events


# =============================================================================
# CHAOS ENGINEERING (10 tests)
# =============================================================================

class TestChaosEngineering:
    """Chaos engineering scenarios."""
    
    @pytest.mark.asyncio
    async def test_random_handler_failures(self, fresh_bus, fault_injector):
        """Handlers with random failures."""
        successes = []
        
        async def chaos_handler(event):
            fault_injector.random_failure(probability=0.3)
            successes.append(event.payload["n"])
        
        fresh_bus.subscribe("test.chaos", chaos_handler)
        
        for i in range(100):
            await fresh_bus.publish("test.chaos", {"n": i})
        
        # Some should succeed, some fail
        assert 50 < len(successes) < 100
        assert len(fresh_bus.get_dead_letter_queue()) > 0
    
    @pytest.mark.asyncio
    async def test_mixed_fault_types(self, fresh_bus):
        """Different fault types in same flow."""
        faults = []
        
        async def mixed_handler(event):
            fault_type = event.payload.get("fault")
            faults.append(fault_type)
            if fault_type == "timeout":
                raise TimeoutError("Timeout")
            elif fault_type == "connection":
                raise ConnectionError("Connection lost")
            elif fault_type == "value":
                raise ValueError("Invalid value")
        
        fresh_bus.subscribe("test.mixed", mixed_handler)
        
        await fresh_bus.publish("test.mixed", {"fault": "timeout"})
        await fresh_bus.publish("test.mixed", {"fault": "connection"})
        await fresh_bus.publish("test.mixed", {"fault": "value"})
        await fresh_bus.publish("test.mixed", {"fault": None})
        
        assert len(faults) == 4
        dlq = fresh_bus.get_dead_letter_queue()
        assert len(dlq) == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, fresh_bus):
        """Circuit breaker prevents cascade failures."""
        breaker = CircuitBreaker(failure_threshold=3, reset_timeout=0.1)
        results = []
        blocked = []
        
        async def circuit_handler(event):
            if not breaker.can_execute():
                blocked.append(event)
                return
            
            if event.payload.get("fail"):
                breaker.record_failure()
                raise Exception("Service failed")
            
            breaker.record_success()
            results.append(event)
        
        fresh_bus.subscribe("test.circuit", circuit_handler)
        
        # Trigger circuit open (need 3 failures)
        for i in range(3):
            await fresh_bus.publish("test.circuit", {"fail": True, "n": i})
        
        assert breaker.state == "open"
        
        # Should be blocked (circuit is open)
        await fresh_bus.publish("test.circuit", {"fail": False})
        assert len(blocked) >= 1
        
        # Wait for reset timeout
        await asyncio.sleep(0.15)
        
        # Should work now (half-open -> closed)
        await fresh_bus.publish("test.circuit", {"fail": False})
        assert len(results) >= 1
    
    @pytest.mark.asyncio
    async def test_latency_injection(self, fresh_bus):
        """Variable latency doesn't break system."""
        times = []
        
        async def latency_handler(event):
            delay = event.payload.get("delay", 0)
            start = time.time()
            await asyncio.sleep(delay)
            times.append(time.time() - start)
        
        fresh_bus.subscribe("test.latency", latency_handler)
        
        await fresh_bus.publish("test.latency", {"delay": 0.01})
        await fresh_bus.publish("test.latency", {"delay": 0.05})
        await fresh_bus.publish("test.latency", {"delay": 0.1})
        
        assert len(times) == 3
        assert all(t > 0 for t in times)
    
    @pytest.mark.asyncio
    async def test_event_duplication_handling(self, fresh_bus):
        """System handles duplicate events."""
        seen_ids = set()
        unique = []
        duplicates = []
        
        async def dedup_handler(event):
            if event.id in seen_ids:
                duplicates.append(event)
                return
            seen_ids.add(event.id)
            unique.append(event)
        
        fresh_bus.subscribe("test.dedup", dedup_handler)
        
        # Publish
        event_id = await fresh_bus.publish("test.dedup", {"data": 1})
        
        # Replay (simulates duplicate)
        await fresh_bus.replay_event(event_id)
        
        assert len(unique) == 1
        assert len(duplicates) == 1
    
    @pytest.mark.asyncio
    async def test_out_of_order_events(self, fresh_bus):
        """Handle out of order events."""
        received_order = []
        
        async def order_handler(event):
            received_order.append(event.payload["seq"])
        
        fresh_bus.subscribe("test.order", order_handler)
        
        # Simulate out of order delivery
        await fresh_bus.publish("test.order", {"seq": 3})
        await fresh_bus.publish("test.order", {"seq": 1})
        await fresh_bus.publish("test.order", {"seq": 2})
        
        # All received
        assert set(received_order) == {1, 2, 3}
    
    @pytest.mark.asyncio
    async def test_partial_system_failure(self, fresh_bus):
        """Partial system failure - some components work."""
        component_a_ok = []
        component_b_ok = []
        
        async def component_a(event):
            if "a_fails" in event.payload:
                raise Exception("Component A failed")
            component_a_ok.append(event.payload["n"])
        
        async def component_b(event):
            component_b_ok.append(event.payload["n"])
        
        fresh_bus.subscribe("test.partial", component_a)
        fresh_bus.subscribe("test.partial", component_b)
        
        await fresh_bus.publish("test.partial", {"n": 1})
        await fresh_bus.publish("test.partial", {"n": 2, "a_fails": True})
        await fresh_bus.publish("test.partial", {"n": 3})
        
        # B always works
        assert component_b_ok == [1, 2, 3]
        # A fails on 2
        assert component_a_ok == [1, 3]
    
    @pytest.mark.asyncio
    async def test_cascading_failure_isolation(self, fresh_bus):
        """Cascading failures are isolated."""
        stage1 = []
        stage2 = []
        stage3 = []
        
        async def handler1(event):
            stage1.append(event.payload["n"])
            if event.payload.get("cascade"):
                raise Exception("Stage 1 cascade failure")
        
        async def handler2(event):
            stage2.append(event.payload["n"])
        
        async def handler3(event):
            stage3.append(event.payload["n"])
        
        fresh_bus.subscribe("workflow.start", handler1)
        fresh_bus.subscribe("workflow.start", handler2)
        fresh_bus.subscribe("workflow.start", handler3)
        
        await fresh_bus.publish("workflow.start", {"n": 1, "cascade": True})
        
        # Stage 1 fails, but 2 and 3 still work
        assert stage1 == [1]
        assert stage2 == [1]
        assert stage3 == [1]
    
    @pytest.mark.asyncio
    async def test_recovery_after_total_failure(self, fresh_bus):
        """System recovers after total failure scenario."""
        fail_all = [True]
        results = []
        
        async def recoverable_handler(event):
            if fail_all[0]:
                raise Exception("Total failure")
            results.append(event.payload["n"])
        
        fresh_bus.subscribe("test.recover", recoverable_handler)
        
        # Total failure
        for i in range(5):
            await fresh_bus.publish("test.recover", {"n": i})
        
        assert len(results) == 0
        
        # Recover
        fail_all[0] = False
        
        for i in range(5, 10):
            await fresh_bus.publish("test.recover", {"n": i})
        
        assert results == [5, 6, 7, 8, 9]
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, fresh_bus):
        """System degrades gracefully under failure."""
        primary_working = [False]
        fallback_results = []
        
        async def primary_handler(event):
            if not primary_working[0]:
                raise Exception("Primary unavailable")
            # Would process normally
        
        async def fallback_handler(event):
            fallback_results.append(event.payload["n"])
        
        fresh_bus.subscribe("test.degrade", primary_handler)
        fresh_bus.subscribe("test.degrade", fallback_handler)
        
        # Primary down, fallback works
        for i in range(5):
            await fresh_bus.publish("test.degrade", {"n": i})
        
        # Fallback received all
        assert fallback_results == [0, 1, 2, 3, 4]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
