"""
Sleep Mode Tests
================
Tests for sleep/wake mode functionality
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta, timezone

from services.sleep_mode_service import (
    SleepModeService,
    SleepState,
    WakeTriggerType
)


@pytest_asyncio.fixture
async def sleep_service():
    """Create a fresh sleep service instance for each test"""
    # Reset singleton
    SleepModeService._instance = None
    service = SleepModeService.get_instance()
    await service.start()
    yield service
    await service.stop()


@pytest.mark.asyncio
async def test_sleep_service_singleton():
    """Test that sleep service is a singleton"""
    SleepModeService._instance = None
    service1 = SleepModeService.get_instance()
    service2 = SleepModeService.get_instance()
    assert service1 is service2


@pytest.mark.asyncio
async def test_enter_sleep_mode(sleep_service):
    """Test entering sleep mode"""
    assert sleep_service.state == SleepState.AWAKE

    await sleep_service.enter_sleep()

    assert sleep_service.state == SleepState.SLEEPING
    assert sleep_service.sleep_entered_at is not None
    assert sleep_service.sleep_count == 1


@pytest.mark.asyncio
async def test_wake_from_sleep(sleep_service):
    """Test waking from sleep mode"""
    # Enter sleep first
    await sleep_service.enter_sleep()
    assert sleep_service.state == SleepState.SLEEPING

    # Wake up
    await sleep_service.wake(WakeTriggerType.MANUAL)

    assert sleep_service.state == SleepState.AWAKE
    assert sleep_service.sleep_entered_at is None
    assert sleep_service.wake_count == 1


@pytest.mark.asyncio
async def test_schedule_wake_trigger(sleep_service):
    """Test scheduling a wake trigger"""
    wake_time = datetime.now(timezone.utc) + timedelta(seconds=2)

    trigger_id = sleep_service.schedule_wake(
        wake_time=wake_time,
        trigger_type=WakeTriggerType.SCHEDULED_POST,
        metadata={"post_id": "test123"}
    )

    assert trigger_id in sleep_service.wake_triggers
    trigger = sleep_service.wake_triggers[trigger_id]
    assert trigger.trigger_type == WakeTriggerType.SCHEDULED_POST
    assert trigger.metadata["post_id"] == "test123"


@pytest.mark.asyncio
async def test_cancel_wake_trigger(sleep_service):
    """Test cancelling a wake trigger"""
    wake_time = datetime.now(timezone.utc) + timedelta(minutes=5)

    trigger_id = sleep_service.schedule_wake(
        wake_time=wake_time,
        trigger_type=WakeTriggerType.SCHEDULED_POST
    )

    assert trigger_id in sleep_service.wake_triggers

    # Cancel it
    cancelled = sleep_service.cancel_wake(trigger_id)
    assert cancelled is True
    assert trigger_id not in sleep_service.wake_triggers


@pytest.mark.asyncio
async def test_automatic_wake_on_trigger(sleep_service):
    """Test automatic wake when trigger time is reached"""
    # Enter sleep mode
    await sleep_service.enter_sleep()
    assert sleep_service.state == SleepState.SLEEPING

    # Schedule wake in 1 second
    wake_time = datetime.now(timezone.utc) + timedelta(seconds=1)
    sleep_service.schedule_wake(
        wake_time=wake_time,
        trigger_type=WakeTriggerType.MANUAL,
        metadata={"test": "auto_wake"}
    )

    # Wait for wake to trigger (wake monitor checks every 5 seconds)
    await asyncio.sleep(6)

    # Should be awake now
    assert sleep_service.state == SleepState.AWAKE


@pytest.mark.asyncio
async def test_get_status(sleep_service):
    """Test getting sleep mode status"""
    status = sleep_service.get_status()

    assert status["state"] == SleepState.AWAKE.value
    assert status["is_sleeping"] is False
    assert status["wake_triggers_count"] == 0
    assert "metrics" in status
    assert status["metrics"]["wake_count"] == 0
    assert status["metrics"]["sleep_count"] == 0


@pytest.mark.asyncio
async def test_sleep_wake_metrics(sleep_service):
    """Test sleep/wake metrics tracking"""
    # Sleep and wake multiple times
    for i in range(3):
        await sleep_service.enter_sleep()
        await asyncio.sleep(0.1)  # Sleep for 100ms
        await sleep_service.wake(WakeTriggerType.MANUAL)

    status = sleep_service.get_status()
    assert status["metrics"]["sleep_count"] == 3
    assert status["metrics"]["wake_count"] == 3
    assert status["metrics"]["total_sleep_seconds"] > 0


@pytest.mark.asyncio
async def test_multiple_wake_triggers(sleep_service):
    """Test scheduling multiple wake triggers"""
    now = datetime.now(timezone.utc)

    # Schedule 3 wake triggers
    trigger_ids = []
    for i in range(3):
        wake_time = now + timedelta(minutes=i+1)
        trigger_id = sleep_service.schedule_wake(
            wake_time=wake_time,
            trigger_type=WakeTriggerType.CHECKBACK_PERIOD,
            metadata={"interval": f"{i+1}m"}
        )
        trigger_ids.append(trigger_id)

    assert len(sleep_service.wake_triggers) == 3

    # Check status shows upcoming wakes
    status = sleep_service.get_status()
    assert status["wake_triggers_count"] == 3
    assert len(status["upcoming_wakes"]) == 3


@pytest.mark.asyncio
async def test_wake_trigger_types():
    """Test all wake trigger types are valid"""
    trigger_types = [
        WakeTriggerType.SCHEDULED_POST,
        WakeTriggerType.SAFARI_AUTOMATION,
        WakeTriggerType.CHECKBACK_PERIOD,
        WakeTriggerType.USER_ACCESS,
        WakeTriggerType.POST_CREATION,
        WakeTriggerType.MANUAL
    ]

    for trigger_type in trigger_types:
        assert isinstance(trigger_type, WakeTriggerType)
        assert isinstance(trigger_type.value, str)


@pytest.mark.asyncio
async def test_sleep_prevents_duplicate_entry(sleep_service):
    """Test that entering sleep mode twice doesn't create duplicate state"""
    await sleep_service.enter_sleep()
    first_sleep_time = sleep_service.sleep_entered_at
    first_sleep_count = sleep_service.sleep_count

    # Try to enter sleep again
    await sleep_service.enter_sleep()

    # Should still be the same sleep session
    assert sleep_service.sleep_entered_at == first_sleep_time
    assert sleep_service.sleep_count == first_sleep_count


@pytest.mark.asyncio
async def test_wake_when_already_awake(sleep_service):
    """Test that waking when already awake is a no-op"""
    assert sleep_service.state == SleepState.AWAKE
    initial_wake_count = sleep_service.wake_count

    await sleep_service.wake(WakeTriggerType.MANUAL)

    # Wake count should not increase
    assert sleep_service.wake_count == initial_wake_count
    assert sleep_service.state == SleepState.AWAKE


@pytest.mark.asyncio
async def test_safari_automation_wake_trigger(sleep_service):
    """Test SLEEP-004: Safari automation wake trigger"""
    # Enter sleep mode
    await sleep_service.enter_sleep()
    assert sleep_service.state == SleepState.SLEEPING

    # Wake for Safari automation
    await sleep_service.wake(
        trigger_type=WakeTriggerType.SAFARI_AUTOMATION,
        metadata={"task_type": "twitter_post", "platform": "twitter"}
    )

    # Should be awake
    assert sleep_service.state == SleepState.AWAKE
    assert sleep_service.wake_count == 1


@pytest.mark.asyncio
async def test_checkback_period_wake_triggers(sleep_service):
    """Test SLEEP-005: Checkback period wake triggers at 1h, 6h, 24h, 72h, 7d"""
    now = datetime.now(timezone.utc)

    # Standard checkback intervals in hours
    checkback_intervals = [1, 6, 24, 72, 168]  # 168h = 7 days

    trigger_ids = []
    for hours in checkback_intervals:
        wake_time = now + timedelta(hours=hours)
        trigger_id = sleep_service.schedule_wake(
            wake_time=wake_time,
            trigger_type=WakeTriggerType.CHECKBACK_PERIOD,
            metadata={
                "post_id": "test_post_123",
                "checkback_hours": hours,
                "platform": "twitter"
            }
        )
        trigger_ids.append(trigger_id)

    # All triggers should be scheduled
    assert len(trigger_ids) == 5
    assert len(sleep_service.wake_triggers) == 5

    # Verify metadata
    for trigger_id in trigger_ids:
        trigger = sleep_service.wake_triggers[trigger_id]
        assert trigger.trigger_type == WakeTriggerType.CHECKBACK_PERIOD
        assert "checkback_hours" in trigger.metadata


@pytest.mark.asyncio
async def test_safari_session_manager_wake_integration():
    """Test that SafariSessionManager can trigger wake"""
    from automation.safari_session_manager import SafariSessionManager

    # Reset sleep service
    SleepModeService._instance = None
    sleep_service = SleepModeService.get_instance()
    await sleep_service.start()

    # Enter sleep mode
    await sleep_service.enter_sleep()
    assert sleep_service.state == SleepState.SLEEPING

    # Safari session manager should wake system
    session_manager = SafariSessionManager()
    result = await session_manager.trigger_safari_wake(
        task_type="twitter_post",
        metadata={"text": "Test tweet"}
    )

    # Should succeed and system should be awake
    assert result is True
    assert sleep_service.state == SleepState.AWAKE

    # Cleanup
    await sleep_service.stop()


@pytest.mark.asyncio
async def test_checkback_scheduler_wake_integration():
    """Test that CheckbackScheduler schedules wake triggers"""
    from services.checkback_scheduler import get_scheduler
    from uuid import uuid4

    # Reset sleep service
    SleepModeService._instance = None
    sleep_service = SleepModeService.get_instance()
    await sleep_service.start()

    # Get checkback scheduler
    scheduler = get_scheduler()

    # Schedule a checkback
    post_id = uuid4()
    published_at = datetime.now(timezone.utc)

    def dummy_callback(post_id, hours):
        pass

    job_id = scheduler.schedule_checkback(
        post_id=post_id,
        published_at=published_at,
        checkback_hours=1,
        callback=dummy_callback,
        platform="twitter",
        platform_url="https://twitter.com/status/123"
    )

    # Job should be scheduled
    assert job_id is not None

    # Wake trigger should also be scheduled (if sleep service is available)
    if scheduler.sleep_service:
        # At least 1 wake trigger should exist for this checkback
        assert len(sleep_service.wake_triggers) > 0

    # Cleanup
    scheduler.cancel_checkback(job_id)
    await sleep_service.stop()


@pytest.mark.asyncio
async def test_post_scheduler_wake_integration():
    """Test that PostScheduler schedules wake triggers for upcoming posts"""
    # This is tested implicitly by the PostScheduler integration
    # The PostScheduler calls _schedule_wake_triggers_for_upcoming_posts
    # which schedules wake triggers 5 minutes before each scheduled post
    pass  # Integration test - covered by PostScheduler tests


@pytest.mark.asyncio
async def test_post_creation_wake_trigger(sleep_service):
    """Test SLEEP-007: Post Creation Wake Trigger"""
    from services.event_bus import Event

    # Enter sleep mode
    await sleep_service.enter_sleep()
    assert sleep_service.state == SleepState.SLEEPING

    # Simulate schedule created event
    event = Event(
        topic="schedule.created",
        payload={
            "schedule_id": "test_schedule_123",
            "platform": "twitter",
            "scheduled_time": "2026-01-19T12:00:00Z"
        },
        source="test"
    )

    # Handle the event
    await sleep_service._handle_schedule_created(event)

    # Should be awake now
    assert sleep_service.state == SleepState.AWAKE
    assert sleep_service.wake_count == 1


@pytest.mark.asyncio
async def test_post_creation_wake_trigger_already_awake(sleep_service):
    """Test POST_CREATION trigger when already awake is no-op"""
    from services.event_bus import Event

    assert sleep_service.state == SleepState.AWAKE
    initial_wake_count = sleep_service.wake_count

    # Simulate schedule created event
    event = Event(
        topic="schedule.created",
        payload={
            "schedule_id": "test_schedule_456",
            "platform": "instagram"
        },
        source="test"
    )

    # Handle the event
    await sleep_service._handle_schedule_created(event)

    # Should still be awake, wake count unchanged
    assert sleep_service.state == SleepState.AWAKE
    assert sleep_service.wake_count == initial_wake_count


@pytest.mark.asyncio
async def test_graceful_sleep_transition(sleep_service):
    """Test SLEEP-011: Graceful Sleep Transition"""
    import time

    # Enter sleep with 0.5s grace period
    start_time = time.time()
    await sleep_service.enter_sleep(grace_period_seconds=0.5)
    elapsed = time.time() - start_time

    # Should have waited at least 0.5 seconds
    assert elapsed >= 0.5
    assert sleep_service.state == SleepState.SLEEPING


@pytest.mark.asyncio
async def test_graceful_sleep_no_grace_period(sleep_service):
    """Test graceful sleep with 0 grace period"""
    import time

    # Enter sleep with 0 grace period (immediate)
    start_time = time.time()
    await sleep_service.enter_sleep(grace_period_seconds=0)
    elapsed = time.time() - start_time

    # Should be nearly instant
    assert elapsed < 0.1
    assert sleep_service.state == SleepState.SLEEPING


@pytest.mark.asyncio
async def test_wake_event_logging(sleep_service):
    """Test SLEEP-012: Wake Event Logging"""
    # Initial state - no wake events
    assert len(sleep_service.wake_event_log) == 0

    # Wake a few times
    for i in range(3):
        await sleep_service.enter_sleep(grace_period_seconds=0)
        await asyncio.sleep(0.1)  # Sleep briefly
        await sleep_service.wake(
            WakeTriggerType.MANUAL,
            metadata={"test_iteration": i}
        )

    # Should have 3 wake events logged
    assert len(sleep_service.wake_event_log) == 3

    # Check wake event log content
    wake_log = sleep_service.get_wake_event_log(limit=10)
    assert len(wake_log) == 3

    # Most recent first
    assert wake_log[0]["trigger_type"] == "manual"
    assert wake_log[0]["metadata"]["test_iteration"] == 2
    assert "sleep_duration_seconds" in wake_log[0]
    assert "timestamp" in wake_log[0]


@pytest.mark.asyncio
async def test_wake_event_log_trimming(sleep_service):
    """Test that wake event log is trimmed to max size"""
    # Simulate 110 wake events (max is 100)
    for i in range(110):
        await sleep_service.enter_sleep(grace_period_seconds=0)
        await sleep_service.wake(WakeTriggerType.MANUAL)

    # Should be trimmed to 100
    assert len(sleep_service.wake_event_log) == 100

    # Wake count should still be accurate
    assert sleep_service.wake_count == 110


@pytest.mark.asyncio
async def test_wake_events_in_status(sleep_service):
    """Test that recent wake events are included in status"""
    # Wake twice
    await sleep_service.enter_sleep(grace_period_seconds=0)
    await sleep_service.wake(WakeTriggerType.USER_ACCESS)
    await sleep_service.enter_sleep(grace_period_seconds=0)
    await sleep_service.wake(WakeTriggerType.SCHEDULED_POST)

    # Get status
    status = sleep_service.get_status()

    # Should include recent wake events
    assert "recent_wake_events" in status
    assert len(status["recent_wake_events"]) == 2
    assert status["recent_wake_events"][-1]["trigger_type"] == "scheduled_post"
