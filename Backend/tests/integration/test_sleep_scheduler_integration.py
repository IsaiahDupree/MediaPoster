"""
Integration Test: Sleep Mode + Post Scheduler
==============================================
Tests the integration between Sleep Mode Service and Post Scheduler.

Verifies:
- Post scheduler schedules wake triggers for upcoming posts
- System wakes 5 minutes before scheduled posts
- Posts execute on time after wake
- Metrics scheduler integrates with sleep mode for checkback periods
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch

from services.sleep_mode_service import (
    SleepModeService,
    SleepState,
    WakeTriggerType
)
from services.post_scheduler import PostScheduler
from services.metrics_scheduler import MetricsSyncScheduler, SyncInterval


@pytest_asyncio.fixture
async def sleep_service():
    """Create sleep service for testing"""
    SleepModeService._instance = None
    service = SleepModeService.get_instance()
    await service.start()
    yield service
    await service.stop()
    SleepModeService._instance = None


@pytest.fixture
def mock_post_scheduler():
    """Mock post scheduler"""
    scheduler = Mock(spec=PostScheduler)
    scheduler._scheduled_wake_triggers = {}
    scheduler.sleep_service = None
    return scheduler


@pytest_asyncio.fixture
async def metrics_scheduler(sleep_service):
    """Create metrics scheduler with sleep service"""
    scheduler = MetricsSyncScheduler()
    scheduler._scheduled_wake_triggers = {}
    scheduler._sleep_service = sleep_service  # Inject sleep service
    return scheduler


class TestSleepSchedulerIntegration:
    """Test Sleep Mode + Post Scheduler integration"""

    @pytest.mark.asyncio
    async def test_post_scheduler_has_sleep_service_reference(self, sleep_service):
        """Test post scheduler can access sleep service"""
        scheduler = PostScheduler()

        # Verify lazy loading works
        assert scheduler.sleep_service is not None
        assert scheduler.sleep_service is sleep_service

    @pytest.mark.asyncio
    async def test_schedule_wake_for_upcoming_posts(self, sleep_service):
        """Test scheduler schedules wake triggers for upcoming posts"""
        scheduler = PostScheduler()

        # Create mock upcoming posts
        now = datetime.now(timezone.utc)
        upcoming_posts = [
            {
                "id": "post1",
                "platform": "instagram",
                "scheduled_at": now + timedelta(minutes=10)
            },
            {
                "id": "post2",
                "platform": "tiktok",
                "scheduled_at": now + timedelta(minutes=20)
            }
        ]

        # Schedule wake triggers
        await scheduler._schedule_wake_triggers_for_upcoming_posts(upcoming_posts)

        # Verify wake triggers were scheduled (5 min before each post)
        assert len(scheduler._scheduled_wake_triggers) == 2
        assert "post1" in scheduler._scheduled_wake_triggers
        assert "post2" in scheduler._scheduled_wake_triggers

        # Verify sleep service has the triggers
        assert len(sleep_service.wake_triggers) == 2

    @pytest.mark.asyncio
    async def test_wake_trigger_scheduled_5_minutes_before_post(self, sleep_service):
        """Test wake is scheduled exactly 5 minutes before post time"""
        scheduler = PostScheduler()

        now = datetime.now(timezone.utc)
        post_time = now + timedelta(minutes=10)
        expected_wake_time = post_time - timedelta(minutes=5)

        upcoming_posts = [{
            "id": "test_post",
            "platform": "instagram",
            "scheduled_at": post_time
        }]

        await scheduler._schedule_wake_triggers_for_upcoming_posts(upcoming_posts)

        # Find the trigger in sleep service
        trigger_id = scheduler._scheduled_wake_triggers["test_post"]
        trigger = sleep_service.wake_triggers[trigger_id]

        # Verify wake time is 5 minutes before post
        time_diff = abs((trigger.wake_time - expected_wake_time).total_seconds())
        assert time_diff < 1  # Within 1 second
        assert trigger.trigger_type == WakeTriggerType.SCHEDULED_POST

    @pytest.mark.asyncio
    async def test_does_not_schedule_past_wake_times(self, sleep_service):
        """Test does not schedule wake for posts in the past or very soon"""
        scheduler = PostScheduler()

        now = datetime.now(timezone.utc)
        upcoming_posts = [
            {
                "id": "past_post",
                "platform": "instagram",
                "scheduled_at": now - timedelta(minutes=10)  # Past
            },
            {
                "id": "very_soon_post",
                "platform": "tiktok",
                "scheduled_at": now + timedelta(minutes=2)  # Less than 5 min
            }
        ]

        await scheduler._schedule_wake_triggers_for_upcoming_posts(upcoming_posts)

        # Should not schedule any triggers
        assert len(scheduler._scheduled_wake_triggers) == 0
        assert len(sleep_service.wake_triggers) == 0

    @pytest.mark.asyncio
    async def test_does_not_duplicate_wake_triggers(self, sleep_service):
        """Test does not create duplicate wake triggers for same post"""
        scheduler = PostScheduler()

        now = datetime.now(timezone.utc)
        upcoming_posts = [{
            "id": "test_post",
            "platform": "instagram",
            "scheduled_at": now + timedelta(minutes=10)
        }]

        # Schedule twice
        await scheduler._schedule_wake_triggers_for_upcoming_posts(upcoming_posts)
        await scheduler._schedule_wake_triggers_for_upcoming_posts(upcoming_posts)

        # Should only have one trigger
        assert len(scheduler._scheduled_wake_triggers) == 1
        assert len(sleep_service.wake_triggers) == 1


class TestMetricsSchedulerIntegration:
    """Test Sleep Mode + Metrics Scheduler integration"""

    @pytest.mark.asyncio
    async def test_metrics_scheduler_has_sleep_service_reference(self, sleep_service):
        """Test metrics scheduler can access sleep service"""
        scheduler = MetricsSyncScheduler()
        scheduler._sleep_service = sleep_service

        assert scheduler.sleep_service is not None
        assert scheduler.sleep_service is sleep_service

    @pytest.mark.asyncio
    async def test_metrics_checkback_schedules_wake(self, metrics_scheduler, sleep_service):
        """Test metrics checkback schedules wake trigger"""
        scheduler = metrics_scheduler

        # Record a sync to schedule next checkback
        scheduler.record_sync("instagram", success=True, posts_synced=5)

        # Verify wake trigger was scheduled
        assert "instagram" in scheduler._scheduled_wake_triggers

        trigger_id = scheduler._scheduled_wake_triggers["instagram"]
        assert trigger_id in sleep_service.wake_triggers

        trigger = sleep_service.wake_triggers[trigger_id]
        assert trigger.trigger_type == WakeTriggerType.CHECKBACK_PERIOD
        assert trigger.metadata["platform"] == "instagram"

    @pytest.mark.asyncio
    async def test_metrics_checkback_cancels_old_trigger(self, metrics_scheduler, sleep_service):
        """Test new checkback cancels old wake trigger"""
        scheduler = metrics_scheduler

        # Schedule first checkback
        scheduler.record_sync("instagram", success=True, posts_synced=5)
        first_trigger_id = scheduler._scheduled_wake_triggers["instagram"]

        # Schedule second checkback (should cancel first)
        scheduler.record_sync("instagram", success=True, posts_synced=3)
        second_trigger_id = scheduler._scheduled_wake_triggers["instagram"]

        # Verify old trigger was cancelled
        assert first_trigger_id != second_trigger_id
        assert first_trigger_id not in sleep_service.wake_triggers
        assert second_trigger_id in sleep_service.wake_triggers

    @pytest.mark.asyncio
    async def test_metrics_wake_at_next_sync_time(self, metrics_scheduler, sleep_service):
        """Test wake is scheduled at exact next sync time"""
        scheduler = metrics_scheduler

        # Set interval to 1 hour
        scheduler.set_interval("instagram", SyncInterval.HOURLY)
        scheduler.record_sync("instagram", success=True, posts_synced=5)

        config = scheduler.configs["instagram"]
        expected_wake_time = config.next_sync

        # Get the scheduled trigger
        trigger_id = scheduler._scheduled_wake_triggers["instagram"]
        trigger = sleep_service.wake_triggers[trigger_id]

        # Verify wake time matches next sync time
        time_diff = abs((trigger.wake_time - expected_wake_time).total_seconds())
        assert time_diff < 1  # Within 1 second


class TestSleepWakeWorkflow:
    """Test complete sleep/wake workflow"""

    @pytest.mark.asyncio
    async def test_full_sleep_wake_cycle_with_scheduler(self, sleep_service):
        """Test complete cycle: sleep → schedule post → wake → execute"""
        scheduler = PostScheduler()

        # Step 1: Enter sleep mode
        await sleep_service.enter_sleep(grace_period_seconds=0)
        assert sleep_service.state == SleepState.SLEEPING

        # Step 2: Schedule a post with wake trigger
        # Post needs to be >5 minutes in future so wake trigger (5min before) is in future
        now = datetime.now(timezone.utc)
        upcoming_posts = [{
            "id": "test_post",
            "platform": "instagram",
            "scheduled_at": now + timedelta(minutes=6)  # 6 minutes (wake will be in 1 min)
        }]

        await scheduler._schedule_wake_triggers_for_upcoming_posts(upcoming_posts)

        # Step 3: Verify wake trigger was scheduled
        assert "test_post" in scheduler._scheduled_wake_triggers
        trigger_id = scheduler._scheduled_wake_triggers["test_post"]
        assert trigger_id in sleep_service.wake_triggers

        # Step 4: Manually trigger wake (simulating wake monitor finding due trigger)
        trigger = sleep_service.wake_triggers[trigger_id]
        await sleep_service.wake(trigger.trigger_type, trigger.metadata)

        # Verify system is awake
        assert sleep_service.state == SleepState.AWAKE
        assert sleep_service.wake_count == 1

    @pytest.mark.asyncio
    async def test_user_access_wakes_system(self, sleep_service):
        """Test user access immediately wakes system"""
        # Enter sleep
        await sleep_service.enter_sleep(grace_period_seconds=0)
        assert sleep_service.is_sleeping()

        # Simulate user access
        await sleep_service.wake(
            WakeTriggerType.USER_ACCESS,
            metadata={"path": "/api/videos", "method": "GET"}
        )

        # System should be awake
        assert sleep_service.is_awake()
        assert sleep_service.wake_count == 1

        # Verify wake event was logged
        wake_log = sleep_service.get_wake_event_log(limit=1)
        assert len(wake_log) == 1
        assert wake_log[0]["trigger_type"] == "user_access"


class TestWorkerPauseResume:
    """Test worker pause/resume during sleep/wake"""

    @pytest.mark.asyncio
    async def test_workers_receive_sleep_event(self, sleep_service):
        """Test workers receive sleep.entered event"""
        event_received = False
        received_event = None

        async def mock_handler(event):
            nonlocal event_received, received_event
            event_received = True
            received_event = event

        # Subscribe to sleep event
        from services.event_bus import Topics
        sleep_service.event_bus.subscribe(Topics.SLEEP_ENTERED, mock_handler)

        # Enter sleep
        await sleep_service.enter_sleep(grace_period_seconds=0)
        await asyncio.sleep(0.1)  # Give event time to propagate

        # Verify event was received
        assert event_received is True
        assert received_event is not None

    @pytest.mark.asyncio
    async def test_workers_receive_wake_event(self, sleep_service):
        """Test workers receive sleep.wake event"""
        event_received = False
        received_event = None

        async def mock_handler(event):
            nonlocal event_received, received_event
            event_received = True
            received_event = event

        # Subscribe to wake event
        from services.event_bus import Topics
        sleep_service.event_bus.subscribe(Topics.SLEEP_WAKE, mock_handler)

        # Enter sleep then wake
        await sleep_service.enter_sleep(grace_period_seconds=0)
        await sleep_service.wake(WakeTriggerType.MANUAL)
        await asyncio.sleep(0.1)  # Give event time to propagate

        # Verify event was received
        assert event_received is True
        assert received_event is not None


class TestCPUMonitorIntegration:
    """Test CPU Monitor + Sleep Mode integration"""

    @pytest.mark.asyncio
    async def test_cpu_monitor_can_trigger_sleep(self, sleep_service):
        """Test CPU monitor can trigger auto-sleep"""
        from services.cpu_monitor import CPUMonitor

        # Reset CPU monitor singleton
        CPUMonitor._instance = None
        monitor = CPUMonitor.get_instance()

        # Verify it can access sleep service
        assert monitor.sleep_service is not None
        assert monitor.sleep_service is sleep_service

        # Cleanup
        CPUMonitor._instance = None

    @pytest.mark.asyncio
    async def test_auto_sleep_configuration(self, sleep_service):
        """Test auto-sleep can be configured"""
        from services.cpu_monitor import CPUMonitor

        CPUMonitor._instance = None
        monitor = CPUMonitor.get_instance()

        # Enable auto-sleep
        monitor.enable_auto_sleep(
            idle_threshold=5.0,
            idle_timeout_seconds=300
        )

        assert monitor._auto_sleep_enabled is True
        assert monitor._idle_threshold_percent == 5.0
        assert monitor._idle_timeout_seconds == 300

        # Disable auto-sleep
        monitor.disable_auto_sleep()
        assert monitor._auto_sleep_enabled is False

        CPUMonitor._instance = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
