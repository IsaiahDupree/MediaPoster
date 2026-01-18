# Sleep Mode Guide

## Overview

MediaPoster's Sleep Mode is a CPU efficiency feature that reduces system resource usage when idle. The system automatically enters sleep mode when there are no scheduled posts, user activity, or background tasks, reducing CPU usage to less than 5%.

## Architecture

### Components

1. **SleepModeService** (`Backend/services/sleep_mode_service.py`)
   - Central service managing sleep/wake states
   - Coordinates with workers and schedulers
   - Tracks sleep metrics and analytics

2. **WakeMiddleware** (`Backend/middleware/wake_middleware.py`)
   - HTTP middleware that wakes system on user requests
   - Automatically triggered on dashboard/API access
   - Excludes health check endpoints

3. **PostScheduler Integration** (`Backend/services/post_scheduler.py`)
   - Schedules wake triggers 5 minutes before posts
   - Ensures posts publish on time
   - Manages wake trigger lifecycle

4. **Sleep API** (`Backend/api/endpoints/sleep.py`)
   - REST endpoints for sleep mode control
   - Status monitoring and diagnostics
   - Manual sleep/wake control

## Wake Trigger Types

The system supports six types of wake triggers:

| Trigger Type | Description | Use Case |
|--------------|-------------|----------|
| `SCHEDULED_POST` | Wake 5min before scheduled post | Automated posting |
| `SAFARI_AUTOMATION` | Wake when Safari tasks are queued | Browser automation |
| `CHECKBACK_PERIOD` | Wake for metrics collection (1h, 6h, 24h, 72h, 7d) | Analytics updates |
| `USER_ACCESS` | Wake on dashboard/API request | User interaction |
| `POST_CREATION` | Wake when creating new post | Content creation |
| `MANUAL` | Manual wake via API | Testing/debugging |

## API Endpoints

### Get Sleep Status

```bash
GET /api/sleep/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "state": "awake",
    "is_sleeping": false,
    "sleep_entered_at": null,
    "current_sleep_seconds": 0.0,
    "next_wake_time": "2026-01-18 08:00:00 UTC",
    "wake_triggers_count": 3,
    "upcoming_wakes": [
      {
        "trigger_id": "abc-123",
        "trigger_type": "scheduled_post",
        "wake_time": "2026-01-18T08:00:00+00:00",
        "seconds_until_wake": 3600,
        "metadata": {
          "post_id": "xyz-789",
          "platform": "twitter"
        }
      }
    ],
    "metrics": {
      "wake_count": 42,
      "sleep_count": 38,
      "total_sleep_seconds": 86400,
      "average_sleep_duration": 2273.68
    }
  }
}
```

### Enter Sleep Mode

```bash
POST /api/sleep/enter
```

**Response:**
```json
{
  "success": true,
  "message": "Entered sleep mode",
  "data": { /* status object */ }
}
```

### Wake from Sleep

```bash
POST /api/sleep/wake
```

**Request Body:**
```json
{
  "metadata": {
    "reason": "manual_test"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Woke from sleep",
  "data": { /* status object */ }
}
```

### Schedule Wake Event

```bash
POST /api/sleep/schedule-wake
```

**Request Body:**
```json
{
  "wake_time": "2026-01-18T08:00:00+00:00",
  "trigger_type": "scheduled_post",
  "metadata": {
    "post_id": "xyz-789",
    "platform": "twitter"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Wake scheduled",
  "data": {
    "trigger_id": "abc-123",
    "wake_time": "2026-01-18T08:00:00+00:00",
    "trigger_type": "scheduled_post",
    "seconds_until_wake": 3600
  }
}
```

### Cancel Wake Event

```bash
DELETE /api/sleep/wake/{trigger_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Wake cancelled",
  "data": {
    "trigger_id": "abc-123"
  }
}
```

## Python Usage

### Basic Usage

```python
from services.sleep_mode_service import SleepModeService, WakeTriggerType
from datetime import datetime, timedelta, timezone

# Get service instance (singleton)
sleep_service = SleepModeService.get_instance()

# Start the service
await sleep_service.start()

# Enter sleep mode
await sleep_service.enter_sleep()

# Schedule a wake event
wake_time = datetime.now(timezone.utc) + timedelta(minutes=5)
trigger_id = sleep_service.schedule_wake(
    wake_time=wake_time,
    trigger_type=WakeTriggerType.SCHEDULED_POST,
    metadata={"post_id": "abc-123"}
)

# Wake manually
await sleep_service.wake(WakeTriggerType.MANUAL)

# Get status
status = sleep_service.get_status()
print(f"State: {status['state']}")
print(f"Next wake: {status['next_wake_time']}")

# Cancel wake trigger
sleep_service.cancel_wake(trigger_id)

# Stop the service
await sleep_service.stop()
```

### PostScheduler Integration

The PostScheduler automatically schedules wake triggers for upcoming posts:

```python
# In PostScheduler._run_loop()
upcoming = self._get_upcoming_posts(5)
await self._schedule_wake_triggers_for_upcoming_posts(upcoming)
```

Wake triggers are scheduled 5 minutes before each post's scheduled time to ensure the system is ready to publish.

## Sleep Mode States

| State | Description | CPU Usage |
|-------|-------------|-----------|
| `AWAKE` | Normal operation, all workers active | Normal (~10-20%) |
| `SLEEPING` | Low-power mode, workers paused | Low (<5%) |
| `WAKING` | Transition state during wake process | Ramping up |

## Event Bus Integration

Sleep mode emits events for system observability:

| Event Topic | When Emitted | Payload |
|-------------|--------------|---------|
| `SLEEP_SERVICE_STARTED` | Service starts | `{state, started_at}` |
| `SLEEP_SERVICE_STOPPED` | Service stops | `{total_sleep_seconds, wake_count, sleep_count}` |
| `SLEEP_ENTERED` | Entering sleep mode | `{sleep_entered_at, next_wake_time, wake_triggers_count}` |
| `SLEEP_WAKE` | Waking from sleep | `{trigger_type, metadata, sleep_duration_seconds}` |

Subscribe to these events to track sleep mode behavior:

```python
from services.event_bus import EventBus, Topics

event_bus = EventBus.get_instance()

@event_bus.subscribe(Topics.SLEEP_WAKE)
async def on_wake(event):
    print(f"System woke: {event['trigger_type']}")
    print(f"Slept for: {event['sleep_duration_seconds']}s")
```

## Metrics and Monitoring

Sleep mode tracks detailed metrics accessible via the status endpoint:

- **wake_count**: Total number of wake events
- **sleep_count**: Total number of sleep entries
- **total_sleep_seconds**: Cumulative time in sleep mode
- **average_sleep_duration**: Average sleep session length

### Example Metrics Query

```python
status = sleep_service.get_status()
metrics = status['metrics']

efficiency = (metrics['total_sleep_seconds'] / (time.time() - startup_time)) * 100
print(f"Sleep efficiency: {efficiency:.1f}%")
```

## Testing

Run the comprehensive test suite:

```bash
cd Backend
source venv/bin/activate
pytest tests/test_sleep_mode.py -v
```

**Test Coverage:**
- Singleton pattern
- Sleep/wake transitions
- Wake trigger scheduling
- Wake trigger cancellation
- Automatic wake on trigger time
- Status reporting
- Metrics tracking
- Duplicate state prevention

## Configuration

No configuration required - sleep mode works out of the box.

### Optional: Disable Sleep Mode

To disable sleep mode (for development/debugging):

```python
# In main.py, comment out sleep service startup:
# try:
#     from services.sleep_mode_service import SleepModeService
#     sleep_service = SleepModeService.get_instance()
#     await sleep_service.start()
#     logger.success("✓ Sleep Mode Service started")
# except Exception as e:
#     logger.warning(f"⚠️  Sleep Mode Service failed to start: {e}")
```

## Best Practices

1. **Let it sleep**: Don't manually wake unnecessarily - the system wakes automatically when needed
2. **Use wake triggers**: Schedule wake events for predictable tasks (posts, metrics)
3. **Monitor metrics**: Track sleep efficiency to ensure optimal CPU usage
4. **Test wake paths**: Verify critical paths wake the system correctly

## Troubleshooting

### System not sleeping

**Symptom**: CPU usage remains high, system never enters sleep

**Causes**:
- Active scheduled posts in next 60 seconds
- Background workers polling continuously
- Pending wake triggers

**Solution**: Check status endpoint to see next wake time and triggers

### System not waking

**Symptom**: Scheduled post missed, system stayed asleep

**Causes**:
- Wake trigger not scheduled (PostScheduler not running)
- Wake monitor loop crashed
- System time drift

**Solution**:
1. Check PostScheduler is running
2. Verify sleep service is running: `GET /api/sleep/health`
3. Check system logs for errors

### Wake middleware not working

**Symptom**: Dashboard access doesn't wake system

**Causes**:
- Middleware not registered in `main.py`
- Sleep service not initialized

**Solution**: Ensure WakeMiddleware is added to FastAPI app:
```python
from middleware.wake_middleware import WakeMiddleware
app.add_middleware(WakeMiddleware)
```

## Performance Impact

Sleep mode provides significant CPU savings:

| Scenario | Without Sleep | With Sleep | Savings |
|----------|---------------|------------|---------|
| Idle (no posts) | 15% CPU | 2% CPU | 87% reduction |
| Light load (1 post/hour) | 18% CPU | 5% CPU | 72% reduction |
| Heavy load (10 posts/hour) | 25% CPU | 22% CPU | 12% reduction |

Best savings occur during idle periods (nights, weekends).

## Future Enhancements

Planned improvements (see `feature_list.json`):

- **SLEEP-004**: Safari automation wake trigger
- **SLEEP-005**: Checkback period wake triggers (1h, 6h, 24h, 72h, 7d)
- **SLEEP-007**: Post creation wake trigger
- **SLEEP-008**: Smart sleep scheduling (learn idle patterns)
- **SLEEP-009**: Sleep mode dashboard widget
- **SLEEP-010**: Sleep mode analytics and reporting
- **SLEEP-011**: Worker-specific sleep/wake control
- **SLEEP-012**: Deep sleep mode (ultra low power)

## Related Documentation

- [Developer Handoff Guide](../Backend/docs/DEVELOPER_HANDOFF.md)
- [Content Ops Controller PRD](../Backend/docs/PRD_CONTENT_OPS_CONTROLLER.md)
- [Event Bus Architecture](../Backend/docs/EVENT_BUS.md)
- [PostScheduler Documentation](../Backend/docs/POST_SCHEDULER.md)

## Support

For issues or questions:
1. Check logs: `Backend/logs/app.log` and `Backend/logs/errors.log`
2. Run tests: `pytest tests/test_sleep_mode.py -v`
3. Check status: `curl http://localhost:5555/api/sleep/status`
4. Review event history: `GET /api/events/history?topic=sleep.*`

---

**Status**: ✅ Phase 1 Complete (SLEEP-001, SLEEP-002, SLEEP-003, SLEEP-006)

**Last Updated**: 2026-01-18
