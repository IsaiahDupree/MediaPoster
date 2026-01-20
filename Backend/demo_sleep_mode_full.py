#!/usr/bin/env python3
"""
MediaPoster Sleep Mode Demo
============================
Comprehensive demonstration of all sleep mode features:

✓ SLEEP-001: Sleep Mode Core Service
✓ SLEEP-002: Wake Triggers Registry
✓ SLEEP-003: Scheduled Post Wake Trigger
✓ SLEEP-004: Safari Automation Wake
✓ SLEEP-005: Checkback Period Wake
✓ SLEEP-006: User Access Wake
✓ SLEEP-007: Post Creation Wake
✓ SLEEP-010: CPU Usage Monitoring
✓ SLEEP-011: Auto-Sleep on Idle
✓ SLEEP-012: Wake Event Logging

Usage:
    python demo_sleep_mode_full.py
"""

import asyncio
from datetime import datetime, timedelta, timezone
from services.sleep_mode_service import SleepModeService, WakeTriggerType
from services.cpu_monitor import get_cpu_monitor
from services.wake_triggers import (
    schedule_post_wake,
    schedule_checkback_wake,
    schedule_all_checkbacks,
    wake_on_user_access,
    CHECKBACK_INTERVALS
)
from loguru import logger


def print_section(title: str):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_status(sleep_service):
    """Print current sleep mode status"""
    status = sleep_service.get_status()
    print(f"\n📊 Sleep Mode Status:")
    print(f"   State: {status['state']}")
    print(f"   Sleeping: {status['is_sleeping']}")
    print(f"   Wake count: {status['metrics']['wake_count']}")
    print(f"   Sleep count: {status['metrics']['sleep_count']}")
    print(f"   Total sleep time: {status['metrics']['total_sleep_seconds']:.2f}s")
    print(f"   Wake triggers: {status['wake_triggers_count']}")
    if status.get('next_wake_time'):
        print(f"   Next wake: {status['next_wake_time']}")


async def demo_sleep_001_core_service():
    """Demo SLEEP-001: Sleep Mode Core Service"""
    print_section("SLEEP-001: Sleep Mode Core Service")

    sleep_service = SleepModeService.get_instance()
    await sleep_service.start()

    print("\n✓ Sleep service started")
    print_status(sleep_service)

    # Enter sleep mode
    print("\n💤 Entering sleep mode...")
    await sleep_service.enter_sleep(grace_period_seconds=1.0)
    print("✓ Sleep mode active")
    print_status(sleep_service)

    # Wait a bit while sleeping
    await asyncio.sleep(2.0)

    # Wake up
    print("\n⏰ Waking from sleep...")
    await sleep_service.wake(WakeTriggerType.MANUAL)
    print("✓ System awake")
    print_status(sleep_service)

    return sleep_service


async def demo_sleep_002_wake_triggers(sleep_service):
    """Demo SLEEP-002: Wake Triggers Registry"""
    print_section("SLEEP-002: Wake Triggers Registry")

    # Schedule multiple wake triggers
    print("\n📅 Scheduling wake triggers...")

    # Trigger 1: Scheduled post (5 minutes from now)
    trigger_1 = sleep_service.schedule_wake(
        wake_time=datetime.now(timezone.utc) + timedelta(minutes=5),
        trigger_type=WakeTriggerType.SCHEDULED_POST,
        metadata={"post_id": "post123", "platform": "instagram"}
    )
    print(f"   ✓ Scheduled post wake: {trigger_1[:8]}...")

    # Trigger 2: Checkback period (1 hour from now)
    trigger_2 = sleep_service.schedule_wake(
        wake_time=datetime.now(timezone.utc) + timedelta(hours=1),
        trigger_type=WakeTriggerType.CHECKBACK_PERIOD,
        metadata={"interval": "1h", "post_id": "post123"}
    )
    print(f"   ✓ Checkback wake: {trigger_2[:8]}...")

    # Trigger 3: Safari automation (10 minutes from now)
    trigger_3 = sleep_service.schedule_wake(
        wake_time=datetime.now(timezone.utc) + timedelta(minutes=10),
        trigger_type=WakeTriggerType.SAFARI_AUTOMATION,
        metadata={"task_id": "safari123", "action": "publish"}
    )
    print(f"   ✓ Safari automation wake: {trigger_3[:8]}...")

    print_status(sleep_service)

    # Cancel one trigger
    print(f"\n❌ Cancelling trigger: {trigger_2[:8]}...")
    sleep_service.cancel_wake(trigger_2)
    print("   ✓ Cancelled")

    print_status(sleep_service)

    return [trigger_1, trigger_3]


async def demo_sleep_003_scheduled_post_wake(sleep_service):
    """Demo SLEEP-003: Scheduled Post Wake Trigger"""
    print_section("SLEEP-003: Scheduled Post Wake Trigger")

    # Schedule a wake for a post (5 minutes before post time)
    post_time = datetime.now(timezone.utc) + timedelta(minutes=10)

    print(f"\n📝 Scheduling wake for post at {post_time.strftime('%H:%M:%S UTC')}")

    trigger_id = schedule_post_wake(
        sleep_service,
        post_id="demo_post_123",
        post_time=post_time,
        platform="instagram",
        wake_minutes_before=5
    )

    print(f"   ✓ Wake trigger created: {trigger_id[:8]}...")
    print(f"   ✓ System will wake 5 minutes before post (at {(post_time - timedelta(minutes=5)).strftime('%H:%M:%S UTC')})")

    print_status(sleep_service)


async def demo_sleep_004_safari_automation_wake(sleep_service):
    """Demo SLEEP-004: Safari Automation Wake"""
    print_section("SLEEP-004: Safari Automation Wake")

    # Enter sleep mode
    print("\n💤 Entering sleep mode...")
    await sleep_service.enter_sleep(grace_period_seconds=0)

    await asyncio.sleep(0.5)

    # Trigger safari automation wake
    print("\n🌐 Safari automation task queued - waking system...")
    from services.wake_triggers import wake_on_safari_automation

    await wake_on_safari_automation(
        sleep_service,
        task_id="safari_task_456",
        platform="instagram",
        action="publish"
    )

    print("   ✓ System woke for Safari automation")
    print_status(sleep_service)


async def demo_sleep_005_checkback_period_wake(sleep_service):
    """Demo SLEEP-005: Checkback Period Wake"""
    print_section("SLEEP-005: Checkback Period Wake")

    post_time = datetime.now(timezone.utc)

    print(f"\n📊 Scheduling all checkback wakes for a post...")
    print(f"   Available intervals: {list(CHECKBACK_INTERVALS.keys())}")

    trigger_ids = schedule_all_checkbacks(
        sleep_service,
        post_id="post_with_checkbacks",
        post_time=post_time,
        platform="instagram"
    )

    print(f"\n   ✓ Scheduled {len(trigger_ids)} checkback wakes:")
    for interval, trigger_id in trigger_ids.items():
        wake_time = post_time + CHECKBACK_INTERVALS[interval]
        print(f"      - {interval} checkback at {wake_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    print_status(sleep_service)


async def demo_sleep_006_user_access_wake(sleep_service):
    """Demo SLEEP-006: User Access Wake"""
    print_section("SLEEP-006: User Access Wake")

    # Enter sleep mode
    print("\n💤 Entering sleep mode...")
    await sleep_service.enter_sleep(grace_period_seconds=0)

    await asyncio.sleep(0.5)

    # User accesses API
    print("\n👤 User accessing dashboard - waking system...")
    await wake_on_user_access(
        sleep_service,
        path="/api/videos",
        method="GET",
        user_id="user123"
    )

    print("   ✓ System woke for user access")
    print_status(sleep_service)


async def demo_sleep_007_post_creation_wake(sleep_service):
    """Demo SLEEP-007: Post Creation Wake"""
    print_section("SLEEP-007: Post Creation Wake")

    # Enter sleep mode
    print("\n💤 Entering sleep mode...")
    await sleep_service.enter_sleep(grace_period_seconds=0)

    await asyncio.sleep(0.5)

    # Post being created
    print("\n📝 New post being created - waking system...")
    from services.wake_triggers import wake_on_post_creation

    await wake_on_post_creation(
        sleep_service,
        schedule_id="new_schedule_789",
        platform="tiktok"
    )

    print("   ✓ System woke for post creation")
    print_status(sleep_service)


async def demo_sleep_010_cpu_monitoring():
    """Demo SLEEP-010: CPU Usage Monitoring"""
    print_section("SLEEP-010: CPU Usage Monitoring")

    cpu_monitor = get_cpu_monitor()
    await cpu_monitor.start()

    print("\n✓ CPU monitor started")

    # Wait for metrics collection
    print("\n⏳ Collecting CPU metrics (3 seconds)...")
    await asyncio.sleep(3.0)

    status = cpu_monitor.get_status()
    current = status.get('current_metrics')

    if current:
        print(f"\n📊 Current CPU Metrics:")
        print(f"   CPU: {current['cpu_percent']:.1f}%")
        print(f"   Memory: {current['memory_percent']:.1f}%")
        print(f"   Memory used: {current['memory_used_mb']:.0f} MB")
        print(f"   Idle: {status['is_idle']}")

    avg_1min = status.get('average_cpu_1min')
    if avg_1min is not None:
        print(f"\n📈 Averages:")
        print(f"   1 minute: {avg_1min:.1f}%")

    print(f"\n📦 Metrics history: {status['metrics_history_size']} entries")

    return cpu_monitor


async def demo_sleep_011_auto_sleep(sleep_service, cpu_monitor):
    """Demo SLEEP-011: Auto-Sleep on Idle"""
    print_section("SLEEP-011: Auto-Sleep on Idle")

    print("\n⚙️  Configuring auto-sleep...")
    print("   Threshold: CPU < 5%")
    print("   Timeout: Idle for 300 seconds")

    cpu_monitor.enable_auto_sleep(
        idle_threshold=5.0,
        idle_timeout_seconds=300
    )

    print("   ✓ Auto-sleep enabled")

    status = cpu_monitor.get_status()
    auto_sleep_config = status['auto_sleep']

    print(f"\n📊 Auto-Sleep Status:")
    print(f"   Enabled: {auto_sleep_config['enabled']}")
    print(f"   Idle threshold: {auto_sleep_config['idle_threshold_percent']}%")
    print(f"   Idle timeout: {auto_sleep_config['idle_timeout_seconds']}s")
    print(f"   Consecutive idle: {auto_sleep_config['consecutive_idle_seconds']:.1f}s")

    if auto_sleep_config['seconds_until_sleep'] is not None:
        print(f"   Time until auto-sleep: {auto_sleep_config['seconds_until_sleep']:.0f}s")


async def demo_sleep_012_wake_event_logging(sleep_service):
    """Demo SLEEP-012: Wake Event Logging"""
    print_section("SLEEP-012: Wake Event Logging")

    print("\n📝 Generating wake events...")

    # Generate several wake events
    for i in range(3):
        await sleep_service.enter_sleep(grace_period_seconds=0)
        await asyncio.sleep(0.2)

        trigger_type = [
            WakeTriggerType.MANUAL,
            WakeTriggerType.USER_ACCESS,
            WakeTriggerType.SCHEDULED_POST
        ][i]

        await sleep_service.wake(
            trigger_type=trigger_type,
            metadata={"test": f"event_{i+1}"}
        )
        print(f"   ✓ Wake event {i+1}: {trigger_type.value}")

    # Get wake event log
    wake_events = sleep_service.get_wake_event_log(limit=10)

    print(f"\n📋 Wake Event Log ({len(wake_events)} events):")
    for event in wake_events[:5]:  # Show last 5
        print(f"   - {event['trigger_type']} | Slept: {event['sleep_duration_seconds']:.2f}s | Wake #{event['wake_count']}")


async def demo_all_features():
    """Run all feature demos"""
    print("\n" + "🚀 " * 30)
    print("  MediaPoster Sleep Mode - Complete Feature Demo")
    print("🚀 " * 30)

    # Core service
    sleep_service = await demo_sleep_001_core_service()

    # Wake triggers registry
    triggers = await demo_sleep_002_wake_triggers(sleep_service)

    # Scheduled post wake
    await demo_sleep_003_scheduled_post_wake(sleep_service)

    # Safari automation wake
    await demo_sleep_004_safari_automation_wake(sleep_service)

    # Checkback period wake
    await demo_sleep_005_checkback_period_wake(sleep_service)

    # User access wake
    await demo_sleep_006_user_access_wake(sleep_service)

    # Post creation wake
    await demo_sleep_007_post_creation_wake(sleep_service)

    # CPU monitoring
    cpu_monitor = await demo_sleep_010_cpu_monitoring()

    # Auto-sleep on idle
    await demo_sleep_011_auto_sleep(sleep_service, cpu_monitor)

    # Wake event logging
    await demo_sleep_012_wake_event_logging(sleep_service)

    # Final summary
    print_section("Demo Complete!")
    print("\n✅ All sleep mode features demonstrated successfully!")
    print("\nImplemented Features:")
    print("   ✓ SLEEP-001: Sleep Mode Core Service")
    print("   ✓ SLEEP-002: Wake Triggers Registry")
    print("   ✓ SLEEP-003: Scheduled Post Wake Trigger")
    print("   ✓ SLEEP-004: Safari Automation Wake")
    print("   ✓ SLEEP-005: Checkback Period Wake")
    print("   ✓ SLEEP-006: User Access Wake")
    print("   ✓ SLEEP-007: Post Creation Wake")
    print("   ✓ SLEEP-010: CPU Usage Monitoring")
    print("   ✓ SLEEP-011: Auto-Sleep on Idle")
    print("   ✓ SLEEP-012: Wake Event Logging")

    print("\n📊 Final Status:")
    print_status(sleep_service)

    # Cleanup
    await cpu_monitor.stop()
    await sleep_service.stop()


if __name__ == "__main__":
    asyncio.run(demo_all_features())
