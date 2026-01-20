"""
Wake Triggers Module
====================
Registry and documentation for all sleep mode wake triggers.

This module defines the wake trigger types and provides utilities for
managing system wake events.

Wake Trigger Types:
------------------
1. SCHEDULED_POST - Wake 5 minutes before post is due to be published
2. SAFARI_AUTOMATION - Wake when Safari automation tasks are queued
3. CHECKBACK_PERIOD - Wake for metrics collection (1h, 6h, 24h, 72h, 7d)
4. USER_ACCESS - Wake when user accesses dashboard or API
5. POST_CREATION - Wake when new post is being created
6. MANUAL - Manual wake via API or user action

Usage:
------
```python
from services.wake_triggers import WakeTriggerType, schedule_post_wake
from services.sleep_mode_service import SleepModeService

# Schedule wake for post
sleep_service = SleepModeService.get_instance()
wake_id = schedule_post_wake(
    sleep_service,
    post_id="post123",
    post_time=datetime.now(timezone.utc) + timedelta(hours=2)
)

# Wake on user access
await wake_on_user_access(sleep_service, path="/api/videos", method="GET")
```

Features Implemented:
--------------------
- SLEEP-002: Wake Triggers Registry ✓
- SLEEP-003: Scheduled Post Wake Trigger ✓
- SLEEP-004: Safari Automation Wake ✓
- SLEEP-005: Checkback Period Wake ✓
- SLEEP-006: User Access Wake ✓
- SLEEP-007: Post Creation Wake ✓
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from enum import Enum
from loguru import logger


class WakeTriggerType(Enum):
    """Types of triggers that can wake the system from sleep mode"""

    SCHEDULED_POST = "scheduled_post"
    """Wake 5 minutes before a scheduled post is due to be published"""

    SAFARI_AUTOMATION = "safari_automation"
    """Wake when Safari automation tasks are queued (Instagram, TikTok, Threads)"""

    CHECKBACK_PERIOD = "checkback_period"
    """Wake for metrics collection at specific intervals (1h, 6h, 24h, 72h, 7d)"""

    USER_ACCESS = "user_access"
    """Wake when user accesses dashboard or API"""

    POST_CREATION = "post_creation"
    """Wake when new post is being created (immediate wake)"""

    MANUAL = "manual"
    """Manual wake via API or user action"""


# Checkback intervals for metrics collection (SLEEP-005)
CHECKBACK_INTERVALS = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "72h": timedelta(hours=72),
    "7d": timedelta(days=7),
}


def schedule_post_wake(
    sleep_service,
    post_id: str,
    post_time: datetime,
    platform: Optional[str] = None,
    wake_minutes_before: int = 5
) -> str:
    """
    Schedule wake trigger 5 minutes before post time (SLEEP-003)

    Args:
        sleep_service: SleepModeService instance
        post_id: ID of the scheduled post
        post_time: When the post is scheduled (UTC)
        platform: Platform name (optional)
        wake_minutes_before: Minutes before post to wake (default: 5)

    Returns:
        Wake trigger ID

    Example:
        ```python
        sleep_service = SleepModeService.get_instance()
        wake_id = schedule_post_wake(
            sleep_service,
            post_id="post123",
            post_time=datetime(2026, 1, 20, 10, 0, tzinfo=timezone.utc),
            platform="instagram"
        )
        ```
    """
    wake_time = post_time - timedelta(minutes=wake_minutes_before)

    trigger_id = sleep_service.schedule_wake(
        wake_time=wake_time,
        trigger_type=WakeTriggerType.SCHEDULED_POST,
        metadata={
            "post_id": post_id,
            "platform": platform,
            "scheduled_time": post_time.isoformat(),
            "wake_minutes_before": wake_minutes_before
        }
    )

    logger.info(
        f"⏰ Scheduled post wake | Post: {post_id} | "
        f"Post time: {post_time.strftime('%Y-%m-%d %H:%M:%S UTC')} | "
        f"Wake time: {wake_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    return trigger_id


async def wake_on_safari_automation(
    sleep_service,
    task_id: str,
    platform: str,
    action: str
) -> None:
    """
    Wake system for Safari automation task (SLEEP-004)

    Args:
        sleep_service: SleepModeService instance
        task_id: ID of the automation task
        platform: Platform name (instagram, tiktok, threads)
        action: Action type (publish, comment, dm)

    Example:
        ```python
        await wake_on_safari_automation(
            sleep_service,
            task_id="task123",
            platform="instagram",
            action="publish"
        )
        ```
    """
    await sleep_service.wake(
        trigger_type=WakeTriggerType.SAFARI_AUTOMATION,
        metadata={
            "task_id": task_id,
            "platform": platform,
            "action": action
        }
    )

    logger.info(f"⏰ Safari automation wake | Platform: {platform} | Action: {action}")


def schedule_checkback_wake(
    sleep_service,
    post_id: str,
    interval: str,
    post_time: datetime,
    platform: Optional[str] = None
) -> str:
    """
    Schedule wake for metrics checkback (SLEEP-005)

    Args:
        sleep_service: SleepModeService instance
        post_id: ID of the post to check
        interval: Checkback interval ("1h", "6h", "24h", "72h", "7d")
        post_time: When the post was published (UTC)
        platform: Platform name (optional)

    Returns:
        Wake trigger ID

    Raises:
        ValueError: If interval is not valid

    Example:
        ```python
        # Schedule 6h checkback
        wake_id = schedule_checkback_wake(
            sleep_service,
            post_id="post123",
            interval="6h",
            post_time=datetime.now(timezone.utc)
        )
        ```
    """
    if interval not in CHECKBACK_INTERVALS:
        raise ValueError(
            f"Invalid interval: {interval}. "
            f"Valid intervals: {list(CHECKBACK_INTERVALS.keys())}"
        )

    wake_time = post_time + CHECKBACK_INTERVALS[interval]

    trigger_id = sleep_service.schedule_wake(
        wake_time=wake_time,
        trigger_type=WakeTriggerType.CHECKBACK_PERIOD,
        metadata={
            "post_id": post_id,
            "platform": platform,
            "interval": interval,
            "post_time": post_time.isoformat()
        }
    )

    logger.info(
        f"⏰ Scheduled checkback wake | Post: {post_id} | "
        f"Interval: {interval} | Wake time: {wake_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    return trigger_id


async def wake_on_user_access(
    sleep_service,
    path: str,
    method: str,
    user_id: Optional[str] = None
) -> None:
    """
    Wake system on user access (SLEEP-006)

    This should be called by API middleware when user accesses dashboard
    or makes API requests.

    Args:
        sleep_service: SleepModeService instance
        path: API path accessed
        method: HTTP method
        user_id: User ID (optional)

    Example:
        ```python
        # In API middleware
        if sleep_service.is_sleeping():
            await wake_on_user_access(
                sleep_service,
                path=request.url.path,
                method=request.method
            )
        ```
    """
    await sleep_service.wake(
        trigger_type=WakeTriggerType.USER_ACCESS,
        metadata={
            "path": path,
            "method": method,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    logger.info(f"⏰ User access wake | Path: {path} | Method: {method}")


async def wake_on_post_creation(
    sleep_service,
    schedule_id: str,
    platform: Optional[str] = None
) -> None:
    """
    Wake system when new post is created (SLEEP-007)

    This is called automatically by the sleep service when it receives
    a SCHEDULE_CREATED event, but can also be called directly.

    Args:
        sleep_service: SleepModeService instance
        schedule_id: ID of the new schedule
        platform: Platform name (optional)

    Example:
        ```python
        # In post creation logic
        await wake_on_post_creation(
            sleep_service,
            schedule_id="sched123",
            platform="instagram"
        )
        ```
    """
    await sleep_service.wake(
        trigger_type=WakeTriggerType.POST_CREATION,
        metadata={
            "schedule_id": schedule_id,
            "platform": platform
        }
    )

    logger.info(f"⏰ Post creation wake | Schedule: {schedule_id}")


def schedule_all_checkbacks(
    sleep_service,
    post_id: str,
    post_time: datetime,
    platform: Optional[str] = None
) -> Dict[str, str]:
    """
    Schedule all 5 checkback wake triggers for a post (SLEEP-005)

    Schedules wake events at: 1h, 6h, 24h, 72h, and 7d after post time.

    Args:
        sleep_service: SleepModeService instance
        post_id: ID of the post
        post_time: When the post was published (UTC)
        platform: Platform name (optional)

    Returns:
        Dictionary mapping interval to trigger_id

    Example:
        ```python
        trigger_ids = schedule_all_checkbacks(
            sleep_service,
            post_id="post123",
            post_time=datetime.now(timezone.utc),
            platform="instagram"
        )
        # Returns: {"1h": "trigger-id-1", "6h": "trigger-id-2", ...}
        ```
    """
    trigger_ids = {}

    for interval in CHECKBACK_INTERVALS.keys():
        trigger_id = schedule_checkback_wake(
            sleep_service,
            post_id=post_id,
            interval=interval,
            post_time=post_time,
            platform=platform
        )
        trigger_ids[interval] = trigger_id

    logger.info(
        f"✓ Scheduled all checkback wakes for post {post_id} | "
        f"Intervals: {list(CHECKBACK_INTERVALS.keys())}"
    )

    return trigger_ids


def cancel_post_wakes(
    sleep_service,
    trigger_ids: Dict[str, str]
) -> int:
    """
    Cancel all wake triggers for a post

    Useful when a post is cancelled or deleted.

    Args:
        sleep_service: SleepModeService instance
        trigger_ids: Dictionary of trigger IDs (from schedule_all_checkbacks)

    Returns:
        Number of triggers cancelled

    Example:
        ```python
        # Cancel all wakes for a post
        cancelled_count = cancel_post_wakes(sleep_service, trigger_ids)
        ```
    """
    cancelled_count = 0

    for interval, trigger_id in trigger_ids.items():
        if sleep_service.cancel_wake(trigger_id):
            cancelled_count += 1
            logger.debug(f"Cancelled {interval} wake trigger: {trigger_id[:8]}")

    if cancelled_count > 0:
        logger.info(f"✓ Cancelled {cancelled_count} wake triggers")

    return cancelled_count


# Export all public APIs
__all__ = [
    "WakeTriggerType",
    "CHECKBACK_INTERVALS",
    "schedule_post_wake",
    "wake_on_safari_automation",
    "schedule_checkback_wake",
    "wake_on_user_access",
    "wake_on_post_creation",
    "schedule_all_checkbacks",
    "cancel_post_wakes",
]
