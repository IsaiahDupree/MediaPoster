"""
Sleep Mode Service
==================
Central service to manage application sleep/wake states for CPU efficiency.

When the application is idle (no scheduled posts, no user activity), it enters
a low-power sleep mode to reduce CPU usage to <5%.

Wake Triggers:
- Scheduled posts (5 minutes before post time)
- Safari automation tasks queued
- Checkback periods (1h, 6h, 24h, 72h, 7d)
- User dashboard/API access
- New post creation

The service pauses workers, reduces polling frequency, and schedules wake events.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from uuid import uuid4
from loguru import logger

from services.event_bus import EventBus, Topics
from dataclasses import dataclass, field


@dataclass
class WakeEventLog:
    """Log entry for a wake event (SLEEP-012)"""
    timestamp: datetime
    trigger_type: str
    sleep_duration_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    wake_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "trigger_type": self.trigger_type,
            "sleep_duration_seconds": self.sleep_duration_seconds,
            "metadata": self.metadata,
            "wake_count": self.wake_count
        }


class SleepState(Enum):
    """Sleep mode states"""
    AWAKE = "awake"
    SLEEPING = "sleeping"
    WAKING = "waking"


class WakeTriggerType(Enum):
    """Types of triggers that can wake the system"""
    SCHEDULED_POST = "scheduled_post"      # Post due in 5 minutes
    SAFARI_AUTOMATION = "safari_automation"  # Safari task queued
    CHECKBACK_PERIOD = "checkback_period"    # Metrics checkback (1h, 6h, 24h, 72h, 7d)
    USER_ACCESS = "user_access"            # Dashboard or API request
    POST_CREATION = "post_creation"        # New post being created
    MANUAL = "manual"                      # Manual wake via API


class WakeTrigger:
    """Represents a scheduled wake event"""

    def __init__(
        self,
        trigger_id: str,
        trigger_type: WakeTriggerType,
        wake_time: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.trigger_id = trigger_id
        self.trigger_type = trigger_type
        self.wake_time = wake_time
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trigger_id": self.trigger_id,
            "trigger_type": self.trigger_type.value,
            "wake_time": self.wake_time.isoformat(),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class SleepModeService:
    """
    Sleep Mode Service

    Manages application sleep/wake cycles to reduce CPU usage when idle.
    Coordinates with PostScheduler and workers to pause/resume operations.

    Usage:
        sleep_service = SleepModeService.get_instance()
        await sleep_service.start()

        # Enter sleep mode
        await sleep_service.enter_sleep()

        # Schedule wake for specific time
        wake_id = sleep_service.schedule_wake(
            wake_time=datetime.now(timezone.utc) + timedelta(minutes=5),
            trigger_type=WakeTriggerType.SCHEDULED_POST,
            metadata={"post_id": "abc123"}
        )

        # Manual wake
        await sleep_service.wake(WakeTriggerType.MANUAL)
    """

    _instance: Optional["SleepModeService"] = None

    def __init__(self):
        """Initialize sleep mode service"""
        if SleepModeService._instance is not None:
            raise RuntimeError("Use SleepModeService.get_instance()")

        self.state = SleepState.AWAKE
        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("sleep-mode-service")

        # Wake triggers management
        self.wake_triggers: Dict[str, WakeTrigger] = {}
        self._wake_task: Optional[asyncio.Task] = None
        self._is_running = False

        # Sleep mode metrics
        self.sleep_entered_at: Optional[datetime] = None
        self.wake_count = 0
        self.sleep_count = 0
        self.total_sleep_seconds = 0.0

        # Workers to pause during sleep
        self._paused_workers: List[str] = []

        # SLEEP-012: Wake event logging
        self.wake_event_log: List[WakeEventLog] = []
        self._max_wake_log_entries = 100  # Keep last 100 wake events

        logger.info("💤 Sleep Mode Service initialized")

    @classmethod
    def get_instance(cls) -> "SleepModeService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the sleep mode service"""
        if self._is_running:
            logger.warning("Sleep mode service already running")
            return

        self._is_running = True
        self._wake_task = asyncio.create_task(self._wake_monitor_loop())

        # Subscribe to SCHEDULE_CREATED events to wake on post creation
        self.event_bus.subscribe(Topics.SCHEDULE_CREATED, self._handle_schedule_created)

        await self.event_bus.publish(
            Topics.SLEEP_SERVICE_STARTED,
            {
                "state": self.state.value,
                "started_at": datetime.now(timezone.utc).isoformat()
            }
        )

        logger.success("✓ Sleep Mode Service started")

    async def stop(self) -> None:
        """Stop the sleep mode service"""
        self._is_running = False

        if self._wake_task:
            self._wake_task.cancel()
            try:
                await self._wake_task
            except asyncio.CancelledError:
                pass

        # Wake up if sleeping
        if self.state == SleepState.SLEEPING:
            await self.wake(WakeTriggerType.MANUAL, skip_event=True)

        await self.event_bus.publish(
            Topics.SLEEP_SERVICE_STOPPED,
            {
                "total_sleep_seconds": self.total_sleep_seconds,
                "wake_count": self.wake_count,
                "sleep_count": self.sleep_count,
                "stopped_at": datetime.now(timezone.utc).isoformat()
            }
        )

        logger.info("🛑 Sleep Mode Service stopped")

    async def enter_sleep(self, grace_period_seconds: float = 2.0) -> None:
        """
        Enter sleep mode - reduce CPU usage to <5%

        This implements SLEEP-011: Graceful Sleep Transition
        Completes in-flight operations before sleeping.

        Actions:
        1. Wait for grace period to allow in-flight operations to complete
        2. Pause PostScheduler polling (will wake for scheduled posts)
        3. Pause background workers
        4. Reduce event bus polling
        5. Emit sleep entered event

        Args:
            grace_period_seconds: Seconds to wait for in-flight operations (default: 2.0)
        """
        if self.state == SleepState.SLEEPING:
            logger.warning("Already in sleep mode")
            return

        logger.info(f"💤 Entering sleep mode (grace period: {grace_period_seconds}s)...")

        # SLEEP-011: Graceful transition - wait for in-flight operations
        if grace_period_seconds > 0:
            logger.debug(f"⏳ Waiting {grace_period_seconds}s for in-flight operations...")
            await asyncio.sleep(grace_period_seconds)

        self.state = SleepState.SLEEPING
        self.sleep_entered_at = datetime.now(timezone.utc)
        self.sleep_count += 1

        # Pause workers by emitting sleep event
        await self.event_bus.publish(
            Topics.SLEEP_ENTERED,
            {
                "sleep_entered_at": self.sleep_entered_at.isoformat(),
                "next_wake_time": self._get_next_wake_time(),
                "wake_triggers_count": len(self.wake_triggers),
                "grace_period_seconds": grace_period_seconds
            }
        )

        logger.success(f"✓ Sleep mode active | Next wake: {self._get_next_wake_time()}")

    async def wake(
        self,
        trigger_type: WakeTriggerType,
        metadata: Optional[Dict[str, Any]] = None,
        skip_event: bool = False
    ) -> None:
        """
        Wake from sleep mode - restore normal operation

        Args:
            trigger_type: What triggered the wake
            metadata: Additional wake context
            skip_event: Skip emitting wake event (for internal use)
        """
        if self.state == SleepState.AWAKE:
            logger.debug(f"Already awake (trigger: {trigger_type.value})")
            return

        # Calculate sleep duration
        sleep_duration = 0.0
        if self.sleep_entered_at:
            sleep_duration = (
                datetime.now(timezone.utc) - self.sleep_entered_at
            ).total_seconds()
            self.total_sleep_seconds += sleep_duration

        logger.info(f"⏰ Waking from sleep | Trigger: {trigger_type.value} | Slept: {sleep_duration:.1f}s")

        self.state = SleepState.WAKING
        self.wake_count += 1

        # SLEEP-012: Log wake event
        wake_log = WakeEventLog(
            timestamp=datetime.now(timezone.utc),
            trigger_type=trigger_type.value,
            sleep_duration_seconds=sleep_duration,
            metadata=metadata or {},
            wake_count=self.wake_count
        )
        self.wake_event_log.append(wake_log)

        # Trim log to max size
        if len(self.wake_event_log) > self._max_wake_log_entries:
            self.wake_event_log = self.wake_event_log[-self._max_wake_log_entries:]

        # Resume workers by emitting wake event
        if not skip_event:
            await self.event_bus.publish(
                Topics.SLEEP_WAKE,
                {
                    "trigger_type": trigger_type.value,
                    "metadata": metadata or {},
                    "sleep_duration_seconds": sleep_duration,
                    "wake_count": self.wake_count,
                    "woke_at": datetime.now(timezone.utc).isoformat()
                }
            )

        # Mark as awake
        self.state = SleepState.AWAKE
        self.sleep_entered_at = None

        logger.success(f"✓ System awake | Trigger: {trigger_type.value}")

    def schedule_wake(
        self,
        wake_time: datetime,
        trigger_type: WakeTriggerType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Schedule a future wake event

        Args:
            wake_time: When to wake
            trigger_type: Why to wake
            metadata: Additional context

        Returns:
            Wake trigger ID

        Raises:
            ValueError: If wake_time is not in the future
        """
        # Validate wake_time is in the future
        now = datetime.now(timezone.utc)
        if wake_time <= now:
            raise ValueError(f"wake_time must be in the future (got {wake_time}, now is {now})")

        trigger_id = str(uuid4())

        trigger = WakeTrigger(
            trigger_id=trigger_id,
            trigger_type=trigger_type,
            wake_time=wake_time,
            metadata=metadata
        )

        self.wake_triggers[trigger_id] = trigger

        logger.info(
            f"⏰ Wake scheduled | Type: {trigger_type.value} | "
            f"Time: {wake_time.strftime('%Y-%m-%d %H:%M:%S UTC')} | "
            f"ID: {trigger_id[:8]}"
        )

        return trigger_id

    def cancel_wake(self, trigger_id: str) -> bool:
        """
        Cancel a scheduled wake event

        Args:
            trigger_id: ID of wake trigger to cancel

        Returns:
            True if cancelled, False if not found
        """
        if trigger_id in self.wake_triggers:
            trigger = self.wake_triggers.pop(trigger_id)
            logger.info(f"❌ Wake cancelled | ID: {trigger_id[:8]} | Type: {trigger.trigger_type.value}")
            return True
        return False

    def _get_next_wake_time(self) -> Optional[str]:
        """Get the next scheduled wake time"""
        if not self.wake_triggers:
            return None

        next_trigger = min(self.wake_triggers.values(), key=lambda t: t.wake_time)
        return next_trigger.wake_time.strftime("%Y-%m-%d %H:%M:%S UTC")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current sleep mode status

        Returns:
            Status dictionary with state, metrics, and triggers
        """
        now = datetime.now(timezone.utc)

        # Calculate current sleep duration if sleeping
        current_sleep_seconds = 0.0
        if self.state == SleepState.SLEEPING and self.sleep_entered_at:
            current_sleep_seconds = (now - self.sleep_entered_at).total_seconds()

        # Get upcoming wake triggers
        upcoming_wakes = []
        for trigger in sorted(self.wake_triggers.values(), key=lambda t: t.wake_time):
            if trigger.wake_time > now:
                upcoming_wakes.append({
                    "trigger_id": trigger.trigger_id,
                    "trigger_type": trigger.trigger_type.value,
                    "wake_time": trigger.wake_time.isoformat(),
                    "seconds_until_wake": (trigger.wake_time - now).total_seconds(),
                    "metadata": trigger.metadata
                })

        return {
            "state": self.state.value,
            "is_sleeping": self.state == SleepState.SLEEPING,
            "sleep_entered_at": self.sleep_entered_at.isoformat() if self.sleep_entered_at else None,
            "current_sleep_seconds": current_sleep_seconds,
            "next_wake_time": self._get_next_wake_time(),
            "wake_triggers_count": len(self.wake_triggers),
            "upcoming_wakes": upcoming_wakes[:5],  # Next 5 wake events
            "metrics": {
                "wake_count": self.wake_count,
                "sleep_count": self.sleep_count,
                "total_sleep_seconds": self.total_sleep_seconds,
                "average_sleep_duration": (
                    self.total_sleep_seconds / self.sleep_count if self.sleep_count > 0 else 0.0
                )
            },
            "recent_wake_events": [log.to_dict() for log in self.wake_event_log[-10:]]  # Last 10 wakes
        }

    def get_wake_event_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get wake event log (SLEEP-012)

        Args:
            limit: Maximum number of events to return (default: 50)

        Returns:
            List of wake event dictionaries, most recent first
        """
        return [log.to_dict() for log in reversed(self.wake_event_log[-limit:])]

    async def _wake_monitor_loop(self) -> None:
        """Background loop to check for due wake triggers"""
        logger.info("🔍 Wake monitor loop started")

        while self._is_running:
            try:
                now = datetime.now(timezone.utc)

                # Check for due wake triggers
                due_triggers = []
                for trigger_id, trigger in list(self.wake_triggers.items()):
                    if trigger.wake_time <= now:
                        due_triggers.append((trigger_id, trigger))

                # Process due triggers
                for trigger_id, trigger in due_triggers:
                    logger.info(f"⏰ Wake trigger due | Type: {trigger.trigger_type.value}")

                    # Wake the system
                    await self.wake(
                        trigger_type=trigger.trigger_type,
                        metadata=trigger.metadata
                    )

                    # Remove trigger
                    self.wake_triggers.pop(trigger_id, None)

                # Sleep for 5 seconds (low-impact polling)
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in wake monitor loop: {e}")
                await asyncio.sleep(5)

        logger.info("🛑 Wake monitor loop stopped")

    async def _handle_schedule_created(self, event: Any) -> None:
        """
        Handle SCHEDULE_CREATED events by waking the system immediately.

        This implements SLEEP-007: Post Creation Wake Trigger.
        When a new post is being created/scheduled, wake the system to ensure
        responsive UI and immediate processing.

        Args:
            event: The schedule.created event
        """
        try:
            payload = event.payload if hasattr(event, 'payload') else event

            logger.info(
                f"📝 Post creation detected | "
                f"Schedule ID: {payload.get('schedule_id', 'unknown')}"
            )

            # Wake immediately if sleeping
            if self.state == SleepState.SLEEPING:
                await self.wake(
                    trigger_type=WakeTriggerType.POST_CREATION,
                    metadata={
                        "schedule_id": payload.get('schedule_id'),
                        "platform": payload.get('platform'),
                        "scheduled_time": payload.get('scheduled_time')
                    }
                )
            else:
                logger.debug("Already awake, no action needed")

        except Exception as e:
            logger.error(f"Error handling schedule created event: {e}")

    def is_sleeping(self) -> bool:
        """Check if currently in sleep mode"""
        return self.state == SleepState.SLEEPING

    def is_awake(self) -> bool:
        """Check if currently awake"""
        return self.state == SleepState.AWAKE
