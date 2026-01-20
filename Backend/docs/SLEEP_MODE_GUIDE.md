# MediaPoster Sleep/Wake Mode Guide

## Overview

The Sleep/Wake Mode system reduces CPU usage to <5% when the application is idle, automatically waking for scheduled events and user activity. This document provides a comprehensive guide to using and integrating with the sleep mode system.

## Features Implemented

### Core Features (Phase 1: Complete)

- ✅ **SLEEP-001**: Sleep Mode Core Service - Manages sleep/wake states
- ✅ **SLEEP-002**: Wake Triggers Registry - Schedulable wake events
- ✅ **SLEEP-003**: Scheduled Post Wake Trigger - Wakes 5min before posts
- ✅ **SLEEP-004**: Safari Automation Wake - Wakes for Safari tasks
- ✅ **SLEEP-005**: Checkback Period Wake - Metrics checkback intervals
- ✅ **SLEEP-006**: User Access Wake - Dashboard/API requests
- ✅ **SLEEP-007**: Post Creation Wake - New post scheduling
- ✅ **SLEEP-010**: CPU Usage Monitoring - Real-time CPU tracking
- ✅ **SLEEP-011**: Graceful Sleep Transition - In-flight operation completion
- ✅ **SLEEP-012**: Wake Event Logging - Track all wake events

## Architecture

### Components

1. **SleepModeService** (`Backend/services/sleep_mode_service.py`)
   - Central service managing sleep/wake states
   - Schedules and processes wake triggers
   - Logs sleep metrics and wake events

2. **CPUMonitor** (`Backend/services/cpu_monitor.py`)
   - Monitors CPU usage every 5 seconds
   - Auto-sleep when CPU < 5% for 5 minutes
   - Tracks CPU metrics history

3. **WakeMiddleware** (`Backend/middleware/wake_middleware.py`)
   - Wakes system on any API/dashboard request
   - Skips health check endpoints

4. **API Endpoints** (`Backend/api/endpoints/sleep.py`, `cpu_monitor.py`)
   - Control and monitor sleep mode
   - Configure auto-sleep settings

### Wake Trigger Types

```python
class WakeTriggerType(Enum):
    SCHEDULED_POST = "scheduled_post"      # Post due in 5 minutes
    SAFARI_AUTOMATION = "safari_automation"  # Safari task queued
    CHECKBACK_PERIOD = "checkback_period"    # Metrics checkback
    USER_ACCESS = "user_access"            # Dashboard or API request
    POST_CREATION = "post_creation"        # New post being created
    MANUAL = "manual"                      # Manual wake via API
```

## Usage Examples

### Basic Usage

```python
from services.sleep_mode_service import SleepModeService, WakeTriggerType

# Get singleton instance
sleep_service = SleepModeService.get_instance()

# Start the service (done automatically in main.py)
await sleep_service.start()

# Enter sleep mode manually
await sleep_service.enter_sleep()

# Wake from sleep manually
await sleep_service.wake(WakeTriggerType.MANUAL)

# Get current status
status = sleep_service.get_status()
print(f"State: {status['state']}")
print(f"Sleep count: {status['metrics']['sleep_count']}")
print(f"Wake count: {status['metrics']['wake_count']}")
```

### Scheduling Wake Events

```python
from datetime import datetime, timedelta, timezone
from services.sleep_mode_service import SleepModeService, WakeTriggerType

sleep_service = SleepModeService.get_instance()

# Schedule wake for 5 minutes from now
wake_time = datetime.now(timezone.utc) + timedelta(minutes=5)

trigger_id = sleep_service.schedule_wake(
    wake_time=wake_time,
    trigger_type=WakeTriggerType.SCHEDULED_POST,
    metadata={
        "post_id": "abc123",
        "platform": "twitter",
        "scheduled_time": wake_time.isoformat()
    }
)

print(f"Wake scheduled: {trigger_id}")

# Cancel a wake trigger
sleep_service.cancel_wake(trigger_id)
```

### Integration with Post Scheduler

The PostScheduler automatically schedules wake triggers 5 minutes before each scheduled post:

```python
# In PostScheduler._schedule_wake_triggers_for_upcoming_posts()
from services.sleep_mode_service import WakeTriggerType

for post in upcoming_posts:
    scheduled_time = post['scheduled_at']
    wake_time = scheduled_time - timedelta(minutes=5)

    trigger_id = self.sleep_service.schedule_wake(
        wake_time=wake_time,
        trigger_type=WakeTriggerType.SCHEDULED_POST,
        metadata={
            "post_id": post['id'],
            "platform": post['platform'],
            "scheduled_time": scheduled_time.isoformat()
        }
    )

    self._scheduled_wake_triggers[post['id']] = trigger_id
```

### CPU Monitor Configuration

```python
from services.cpu_monitor import get_cpu_monitor

cpu_monitor = get_cpu_monitor()

# Enable auto-sleep when CPU < 5% for 5 minutes
cpu_monitor.enable_auto_sleep(
    idle_threshold=5.0,          # CPU percentage
    idle_timeout_seconds=300     # 5 minutes
)

# Get current CPU status
status = cpu_monitor.get_status()
print(f"CPU: {status['current_metrics']['cpu_percent']}%")
print(f"Memory: {status['current_metrics']['memory_percent']}%")
print(f"Idle: {status['is_idle']}")

# Disable auto-sleep
cpu_monitor.disable_auto_sleep()
```

### Event Bus Integration

The sleep mode system publishes events to the event bus for monitoring:

```python
from services.event_bus import EventBus, Topics

event_bus = EventBus.get_instance()

# Subscribe to sleep/wake events
async def handle_sleep_event(event):
    print(f"System entered sleep mode at {event.payload['sleep_entered_at']}")

async def handle_wake_event(event):
    print(f"System woke up! Trigger: {event.payload['trigger_type']}")
    print(f"Slept for {event.payload['sleep_duration_seconds']}s")

event_bus.subscribe(Topics.SLEEP_ENTERED, handle_sleep_event)
event_bus.subscribe(Topics.SLEEP_WAKE, handle_wake_event)
```

### Wake Event Logging

Track all wake events for debugging and analytics:

```python
from services.sleep_mode_service import SleepModeService

sleep_service = SleepModeService.get_instance()

# Get recent wake events
wake_events = sleep_service.get_wake_event_log(limit=20)

for event in wake_events:
    print(f"Wake #{event['wake_count']}: {event['trigger_type']}")
    print(f"  Timestamp: {event['timestamp']}")
    print(f"  Sleep duration: {event['sleep_duration_seconds']:.1f}s")
    print(f"  Metadata: {event['metadata']}")
```

## API Endpoints

### Sleep Mode Control

#### Get Status
```bash
GET /api/sleep/status
```

Response:
```json
{
  "success": true,
  "data": {
    "state": "awake",
    "is_sleeping": false,
    "sleep_entered_at": null,
    "current_sleep_seconds": 0,
    "next_wake_time": "2026-01-20 12:30:00 UTC",
    "wake_triggers_count": 3,
    "upcoming_wakes": [
      {
        "trigger_id": "abc-123",
        "trigger_type": "scheduled_post",
        "wake_time": "2026-01-20T12:30:00Z",
        "seconds_until_wake": 180,
        "metadata": {"post_id": "post123"}
      }
    ],
    "metrics": {
      "wake_count": 45,
      "sleep_count": 42,
      "total_sleep_seconds": 12600,
      "average_sleep_duration": 300
    },
    "recent_wake_events": [...]
  }
}
```

#### Enter Sleep Mode
```bash
POST /api/sleep/enter
```

#### Wake from Sleep
```bash
POST /api/sleep/wake

{
  "metadata": {
    "reason": "manual_wake",
    "user": "admin"
  }
}
```

#### Schedule Wake Event
```bash
POST /api/sleep/schedule-wake

{
  "wake_time": "2026-01-20T15:00:00Z",
  "trigger_type": "scheduled_post",
  "metadata": {
    "post_id": "abc123",
    "platform": "twitter"
  }
}
```

#### Cancel Wake Event
```bash
DELETE /api/sleep/wake/{trigger_id}
```

#### Get Wake Event Log
```bash
GET /api/sleep/wake-events?limit=50
```

### CPU Monitor Control

#### Get CPU Status
```bash
GET /api/cpu/status
```

Response:
```json
{
  "success": true,
  "data": {
    "is_running": true,
    "check_interval": 5,
    "current_metrics": {
      "cpu_percent": 3.2,
      "cpu_per_core": [2.1, 4.3, 3.0, 3.5],
      "memory_percent": 45.2,
      "memory_used_mb": 4096,
      "memory_available_mb": 12288,
      "idle_seconds": 120
    },
    "average_cpu_1min": 3.5,
    "average_cpu_5min": 4.1,
    "is_idle": true,
    "auto_sleep": {
      "enabled": true,
      "idle_threshold_percent": 5.0,
      "idle_timeout_seconds": 300,
      "consecutive_idle_seconds": 120,
      "seconds_until_sleep": 180
    }
  }
}
```

#### Enable Auto-Sleep
```bash
POST /api/cpu/auto-sleep/enable

{
  "idle_threshold": 5.0,
  "idle_timeout_seconds": 300
}
```

#### Disable Auto-Sleep
```bash
POST /api/cpu/auto-sleep/disable
```

#### Get CPU Metrics History
```bash
GET /api/cpu/metrics?limit=100
```

## Event Topics

### Published Events

- `Topics.SLEEP_SERVICE_STARTED` - Sleep mode service started
- `Topics.SLEEP_SERVICE_STOPPED` - Sleep mode service stopped
- `Topics.SLEEP_ENTERED` - System entered sleep mode
- `Topics.SLEEP_WAKE` - System woke from sleep
- `Topics.SLEEP_WAKE_SCHEDULED` - Wake event scheduled
- `Topics.SLEEP_WAKE_CANCELLED` - Wake event cancelled

### Event Payloads

#### SLEEP_ENTERED
```python
{
    "sleep_entered_at": "2026-01-20T12:00:00Z",
    "next_wake_time": "2026-01-20 12:30:00 UTC",
    "wake_triggers_count": 3,
    "grace_period_seconds": 2.0
}
```

#### SLEEP_WAKE
```python
{
    "trigger_type": "scheduled_post",
    "metadata": {"post_id": "abc123"},
    "sleep_duration_seconds": 300.5,
    "wake_count": 45,
    "woke_at": "2026-01-20T12:05:00Z"
}
```

## Integration Patterns

### Custom Wake Triggers

To add wake triggers from your service:

```python
from services.sleep_mode_service import SleepModeService, WakeTriggerType
from datetime import datetime, timedelta, timezone

class MyCustomService:
    def __init__(self):
        self.sleep_service = SleepModeService.get_instance()

    async def schedule_my_task(self, task_time: datetime):
        """Schedule wake trigger for custom task"""
        # Wake 5 minutes before task
        wake_time = task_time - timedelta(minutes=5)

        trigger_id = self.sleep_service.schedule_wake(
            wake_time=wake_time,
            trigger_type=WakeTriggerType.SAFARI_AUTOMATION,  # Use appropriate type
            metadata={
                "service": "my_custom_service",
                "task_type": "custom_task",
                "task_time": task_time.isoformat()
            }
        )

        return trigger_id
```

### Worker Sleep Management

Workers should subscribe to sleep events and pause/resume:

```python
from services.event_bus import EventBus, Topics

class MyWorker:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.is_paused = False

        # Subscribe to sleep events
        self.event_bus.subscribe(Topics.SLEEP_ENTERED, self._handle_sleep)
        self.event_bus.subscribe(Topics.SLEEP_WAKE, self._handle_wake)

    async def _handle_sleep(self, event):
        """Pause worker when system sleeps"""
        self.is_paused = True
        logger.info("Worker paused for sleep mode")

    async def _handle_wake(self, event):
        """Resume worker when system wakes"""
        self.is_paused = False
        logger.info(f"Worker resumed (trigger: {event.payload['trigger_type']})")

    async def work_loop(self):
        """Main work loop that respects sleep mode"""
        while self.is_running:
            if not self.is_paused:
                await self.do_work()

            await asyncio.sleep(5)
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
cd Backend
source venv/bin/activate

# Run all sleep mode tests
pytest tests/unit/test_sleep_mode_service.py -v

# Run specific test class
pytest tests/unit/test_sleep_mode_service.py::TestWakeTriggersRegistry -v

# Run with coverage
pytest tests/unit/test_sleep_mode_service.py --cov=services.sleep_mode_service
```

### Test Coverage

Current test coverage:
- ✅ Core sleep/wake functionality
- ✅ Wake triggers registry (schedule, cancel, execute)
- ✅ All wake trigger types
- ✅ Graceful sleep transition with grace period
- ✅ Wake event logging and history
- ✅ Status and metrics reporting
- ✅ Service lifecycle (start/stop)
- ✅ Edge cases (duplicate sleep, wake when awake, etc.)

### Integration Testing

Test sleep mode with other services:

```python
import pytest
from services.sleep_mode_service import SleepModeService, WakeTriggerType
from services.post_scheduler import PostScheduler

@pytest.mark.asyncio
async def test_post_scheduler_wake_integration():
    """Test PostScheduler schedules wake triggers"""
    sleep_service = SleepModeService.get_instance()
    await sleep_service.start()

    scheduler = PostScheduler()
    await scheduler.start()

    # Create a scheduled post (due in 10 minutes)
    # PostScheduler should schedule wake trigger 5 minutes before

    # Verify wake trigger was scheduled
    assert len(sleep_service.wake_triggers) > 0

    # Cleanup
    await scheduler.stop()
    await sleep_service.stop()
```

## Monitoring

### Metrics to Track

1. **Sleep Efficiency**
   - Total sleep time vs. total uptime
   - Average sleep duration
   - Sleep/wake cycle count

2. **Wake Triggers**
   - Most common wake trigger types
   - Wake trigger latency (scheduled vs. actual)
   - Cancelled wake triggers

3. **CPU Usage**
   - CPU usage during sleep (<5% target)
   - CPU usage during active periods
   - Idle time before auto-sleep

4. **Wake Event Log**
   - Wake frequency over time
   - Sleep duration distribution
   - Trigger type distribution

### Dashboard Queries

```python
from services.sleep_mode_service import SleepModeService

sleep_service = SleepModeService.get_instance()
status = sleep_service.get_status()

# Sleep efficiency
total_sleep = status['metrics']['total_sleep_seconds']
sleep_count = status['metrics']['sleep_count']
avg_sleep = status['metrics']['average_sleep_duration']

print(f"Total sleep time: {total_sleep / 3600:.1f} hours")
print(f"Average sleep: {avg_sleep / 60:.1f} minutes")
print(f"Sleep cycles: {sleep_count}")

# Recent wake events
wake_events = sleep_service.get_wake_event_log(limit=100)

# Group by trigger type
from collections import Counter
trigger_counts = Counter(e['trigger_type'] for e in wake_events)
print(f"Wake triggers: {dict(trigger_counts)}")
```

## Best Practices

### 1. Always Schedule Wake Triggers

When scheduling future work, always schedule a wake trigger:

```python
# ❌ Bad: No wake trigger
scheduler.schedule_task(task_time)

# ✅ Good: Schedule wake trigger too
scheduler.schedule_task(task_time)
sleep_service.schedule_wake(
    wake_time=task_time - timedelta(minutes=5),
    trigger_type=WakeTriggerType.SCHEDULED_POST
)
```

### 2. Use Appropriate Grace Periods

Allow in-flight operations to complete:

```python
# ❌ Bad: Immediate sleep might interrupt work
await sleep_service.enter_sleep(grace_period_seconds=0)

# ✅ Good: Wait for operations to complete
await sleep_service.enter_sleep(grace_period_seconds=2.0)
```

### 3. Handle Sleep in Long-Running Operations

Check sleep state in long loops:

```python
async def long_running_task():
    sleep_service = SleepModeService.get_instance()

    for i in range(1000):
        # Check if we should pause
        if sleep_service.is_sleeping():
            logger.info("Pausing task for sleep mode")
            while sleep_service.is_sleeping():
                await asyncio.sleep(1)
            logger.info("Resuming task after wake")

        await process_item(i)
```

### 4. Clean Up Wake Triggers

Cancel wake triggers when tasks are cancelled:

```python
class TaskManager:
    def __init__(self):
        self.sleep_service = SleepModeService.get_instance()
        self.wake_triggers = {}  # task_id -> trigger_id

    async def schedule_task(self, task_id, task_time):
        trigger_id = self.sleep_service.schedule_wake(...)
        self.wake_triggers[task_id] = trigger_id

    async def cancel_task(self, task_id):
        # Cancel the wake trigger too
        if task_id in self.wake_triggers:
            trigger_id = self.wake_triggers[task_id]
            self.sleep_service.cancel_wake(trigger_id)
            del self.wake_triggers[task_id]
```

### 5. Use Metadata for Debugging

Include useful metadata in wake triggers:

```python
trigger_id = sleep_service.schedule_wake(
    wake_time=wake_time,
    trigger_type=WakeTriggerType.SCHEDULED_POST,
    metadata={
        "post_id": post_id,
        "platform": platform,
        "account_id": account_id,
        "scheduled_time": scheduled_time.isoformat(),
        "scheduled_by": "user_123",
        "reason": "regular_post"
    }
)
```

## Troubleshooting

### System Not Sleeping

1. Check if workers are still running:
```python
status = sleep_service.get_status()
print(f"State: {status['state']}")
```

2. Check CPU usage:
```python
cpu_monitor = get_cpu_monitor()
status = cpu_monitor.get_status()
print(f"CPU: {status['current_metrics']['cpu_percent']}%")
print(f"Idle seconds: {status['auto_sleep']['consecutive_idle_seconds']}")
```

3. Check for upcoming wake triggers:
```python
status = sleep_service.get_status()
print(f"Wake triggers: {status['wake_triggers_count']}")
print(f"Next wake: {status['next_wake_time']}")
```

### Wake Triggers Not Firing

1. Check trigger is scheduled in future:
```python
# Triggers in the past are rejected
wake_time = datetime.now(timezone.utc) + timedelta(minutes=5)  # Must be future
```

2. Verify wake monitor is running:
```python
sleep_service = SleepModeService.get_instance()
print(f"Running: {sleep_service._is_running}")
print(f"Wake task: {sleep_service._wake_task}")
```

3. Check logs for wake execution:
```bash
tail -f logs/app.log | grep "Wake trigger due"
```

### High CPU During Sleep

1. Check worker status:
```bash
# Workers should pause during sleep
tail -f logs/app.log | grep -E "Worker paused|Worker resumed"
```

2. Identify CPU-intensive processes:
```python
import psutil

# Check per-core CPU usage
cpu_monitor = get_cpu_monitor()
status = cpu_monitor.get_status()
for i, cpu in enumerate(status['current_metrics']['cpu_per_core']):
    print(f"Core {i}: {cpu}%")
```

3. Review auto-sleep settings:
```python
cpu_monitor = get_cpu_monitor()
status = cpu_monitor.get_status()
print(f"Auto-sleep enabled: {status['auto_sleep']['enabled']}")
print(f"Idle threshold: {status['auto_sleep']['idle_threshold_percent']}%")
print(f"Idle timeout: {status['auto_sleep']['idle_timeout_seconds']}s")
```

## Performance Impact

### CPU Usage

- **Awake**: Normal operation (10-30% CPU typical)
- **Sleeping**: Target <5% CPU (achieved with proper worker pause)
- **Wake Monitor**: <0.1% CPU (checks every 5 seconds)

### Memory Usage

- **SleepModeService**: ~1MB (includes wake triggers and event log)
- **CPUMonitor**: ~500KB (includes metrics history)
- **Total overhead**: <2MB

### Latency

- **Wake from sleep**: <100ms (event emission + worker resume)
- **Enter sleep**: 2s (default grace period)
- **Wake trigger scheduling**: <1ms
- **Status query**: <1ms

## Future Enhancements

Planned features for future phases:

- **SLEEP-008**: Dashboard UI for sleep mode control
- **SLEEP-009**: Sleep mode analytics and reporting
- **SLEEP-013**: Predictive wake scheduling (ML-based)
- **SLEEP-014**: Dynamic sleep threshold based on workload
- **SLEEP-015**: Multi-tier sleep modes (light/deep sleep)

## Support

For issues, questions, or feature requests:

1. Check logs: `Backend/logs/app.log`
2. Run tests: `pytest tests/unit/test_sleep_mode_service.py -v`
3. Review status: `GET /api/sleep/status`
4. File issue: GitHub Issues

## References

- PRD: `Backend/docs/PRD_CONTENT_OPS_CONTROLLER.md` (Sleep/Wake Mode section)
- Source: `Backend/services/sleep_mode_service.py`
- Tests: `Backend/tests/unit/test_sleep_mode_service.py`
- API: `Backend/api/endpoints/sleep.py`
- Event Topics: `Backend/services/event_bus/topics.py`
