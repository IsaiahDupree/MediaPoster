"""
Worker Sleep Management Tests (SLEEP-008)
==========================================
Tests for worker pause/resume during sleep mode
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone

from services.event_bus import EventBus, Topics
from services.workers.base import BaseWorker
from services.sleep_mode_service import SleepModeService, SleepState


class TestWorker(BaseWorker):
    """Test worker that tracks processed events"""

    def __init__(self, event_bus=None):
        super().__init__(event_bus)
        self.processed_events = []

    def get_subscriptions(self):
        return ["test.event"]

    async def handle_event(self, event):
        self.processed_events.append(event.topic)


@pytest_asyncio.fixture
async def event_bus():
    """Create fresh event bus for each test"""
    EventBus._instance = None
    bus = EventBus.get_instance()
    yield bus
    await bus.shutdown()


@pytest_asyncio.fixture
async def sleep_service():
    """Create fresh sleep service for each test"""
    SleepModeService._instance = None
    service = SleepModeService.get_instance()
    await service.start()
    yield service
    await service.stop()


@pytest.mark.asyncio
async def test_worker_pauses_on_sleep(event_bus, sleep_service):
    """Test that worker pauses when system enters sleep mode"""
    # Create and start worker
    worker = TestWorker(event_bus)
    await worker.start()

    assert worker._is_paused is False

    # Enter sleep mode
    await sleep_service.enter_sleep(grace_period_seconds=0)

    # Wait for sleep event to propagate
    await asyncio.sleep(0.1)

    # Worker should be paused
    assert worker._is_paused is True
    assert worker._paused_at is not None

    await worker.stop()


@pytest.mark.asyncio
async def test_worker_resumes_on_wake(event_bus, sleep_service):
    """Test that worker resumes when system wakes up"""
    # Create and start worker
    worker = TestWorker(event_bus)
    await worker.start()

    # Enter sleep mode
    await sleep_service.enter_sleep(grace_period_seconds=0)
    await asyncio.sleep(0.1)

    assert worker._is_paused is True

    # Wake up
    from services.sleep_mode_service import WakeTriggerType
    await sleep_service.wake(WakeTriggerType.MANUAL)

    # Wait for wake event to propagate
    await asyncio.sleep(0.1)

    # Worker should be resumed
    assert worker._is_paused is False
    assert worker._paused_at is None
    assert worker._total_pause_seconds > 0

    await worker.stop()


@pytest.mark.asyncio
async def test_worker_skips_events_when_paused(event_bus, sleep_service):
    """Test that worker skips processing events when paused"""
    # Create and start worker
    worker = TestWorker(event_bus)
    await worker.start()

    # Process event while awake
    await event_bus.publish("test.event", {"test": "awake"})
    await asyncio.sleep(0.1)

    assert len(worker.processed_events) == 1

    # Enter sleep mode
    await sleep_service.enter_sleep(grace_period_seconds=0)
    await asyncio.sleep(0.1)

    # Publish event while sleeping - should be skipped
    await event_bus.publish("test.event", {"test": "sleeping"})
    await asyncio.sleep(0.1)

    # Still only 1 event processed
    assert len(worker.processed_events) == 1

    # Wake up
    from services.sleep_mode_service import WakeTriggerType
    await sleep_service.wake(WakeTriggerType.MANUAL)
    await asyncio.sleep(0.1)

    # Process event while awake again
    await event_bus.publish("test.event", {"test": "awake_again"})
    await asyncio.sleep(0.1)

    # Should have processed 2 events total (skipped 1 during sleep)
    assert len(worker.processed_events) == 2

    await worker.stop()


@pytest.mark.asyncio
async def test_worker_stats_include_pause_info(event_bus):
    """Test that worker stats include pause/resume information"""
    worker = TestWorker(event_bus)
    await worker.start()

    stats = worker.get_stats()

    assert "is_paused" in stats
    assert "total_pause_seconds" in stats
    assert "paused_at" in stats

    assert stats["is_paused"] is False
    assert stats["total_pause_seconds"] == 0.0
    assert stats["paused_at"] is None

    await worker.stop()


@pytest.mark.asyncio
async def test_worker_tracks_pause_duration(event_bus, sleep_service):
    """Test that worker tracks total pause duration"""
    worker = TestWorker(event_bus)
    await worker.start()

    # Sleep for a short time
    await sleep_service.enter_sleep(grace_period_seconds=0)
    await asyncio.sleep(0.2)

    from services.sleep_mode_service import WakeTriggerType
    await sleep_service.wake(WakeTriggerType.MANUAL)
    await asyncio.sleep(0.1)

    # Should have tracked pause duration
    assert worker._total_pause_seconds > 0.1

    await worker.stop()


@pytest.mark.asyncio
async def test_multiple_workers_pause_and_resume(event_bus, sleep_service):
    """Test that multiple workers all pause and resume correctly"""
    # Create multiple workers
    workers = [TestWorker(event_bus) for _ in range(3)]
    for worker in workers:
        await worker.start()

    # All should be awake
    for worker in workers:
        assert worker._is_paused is False

    # Enter sleep mode
    await sleep_service.enter_sleep(grace_period_seconds=0)
    await asyncio.sleep(0.1)

    # All should be paused
    for worker in workers:
        assert worker._is_paused is True

    # Wake up
    from services.sleep_mode_service import WakeTriggerType
    await sleep_service.wake(WakeTriggerType.MANUAL)
    await asyncio.sleep(0.1)

    # All should be resumed
    for worker in workers:
        assert worker._is_paused is False

    # Cleanup
    for worker in workers:
        await worker.stop()


@pytest.mark.asyncio
async def test_worker_handles_multiple_sleep_wake_cycles(event_bus, sleep_service):
    """Test worker handles multiple sleep/wake cycles correctly"""
    worker = TestWorker(event_bus)
    await worker.start()

    from services.sleep_mode_service import WakeTriggerType

    # Multiple sleep/wake cycles
    for i in range(3):
        # Sleep
        await sleep_service.enter_sleep(grace_period_seconds=0)
        await asyncio.sleep(0.1)
        assert worker._is_paused is True

        # Wake
        await sleep_service.wake(WakeTriggerType.MANUAL)
        await asyncio.sleep(0.1)
        assert worker._is_paused is False

    # Total pause duration should accumulate
    assert worker._total_pause_seconds > 0.2

    await worker.stop()
