#!/usr/bin/env python3
"""
Sleep Mode Demo Script
======================
Demonstrates the sleep/wake mode functionality with a simple example.

Usage:
    python scripts/demo_sleep_mode.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add Backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.sleep_mode_service import SleepModeService, WakeTriggerType
from services.cpu_monitor import get_cpu_monitor
from loguru import logger


async def main():
    """Demo sleep mode functionality"""

    print("=" * 70)
    print("MediaPoster Sleep Mode Demo")
    print("=" * 70)
    print()

    # Initialize services
    print("1. Initializing Sleep Mode Service...")
    sleep_service = SleepModeService.get_instance()
    await sleep_service.start()

    print("2. Initializing CPU Monitor...")
    cpu_monitor = get_cpu_monitor()
    await cpu_monitor.start()

    # Show initial status
    print("\n📊 Initial Status:")
    status = sleep_service.get_status()
    print(f"   State: {status['state']}")
    print(f"   Wake triggers: {status['wake_triggers_count']}")

    cpu_status = cpu_monitor.get_status()
    if cpu_status.get('current_metrics'):
        cpu_pct = cpu_status['current_metrics']['cpu_percent']
        print(f"   CPU usage: {cpu_pct:.1f}%")

    # Schedule a wake trigger for 10 seconds from now
    print("\n3. Scheduling wake trigger (10 seconds from now)...")
    wake_time = datetime.now(timezone.utc) + timedelta(seconds=10)
    trigger_id = sleep_service.schedule_wake(
        wake_time=wake_time,
        trigger_type=WakeTriggerType.MANUAL,
        metadata={"demo": "test"}
    )
    print(f"   Wake trigger scheduled: {trigger_id[:8]}...")
    print(f"   Wake time: {wake_time.strftime('%H:%M:%S UTC')}")

    # Enter sleep mode
    print("\n4. Entering sleep mode...")
    await sleep_service.enter_sleep(grace_period_seconds=1.0)

    status = sleep_service.get_status()
    print(f"   State: {status['state']}")
    print(f"   Sleep count: {status['metrics']['sleep_count']}")

    # Wait for wake trigger
    print("\n5. Waiting for wake trigger to fire...")
    print("   (watching for 12 seconds)")

    for i in range(12):
        await asyncio.sleep(1)
        if sleep_service.is_awake():
            print(f"\n   ✅ System woke up after {i+1} seconds!")
            break
        print(f"   💤 Still sleeping... ({i+1}s)", end="\r")

    # Show final status
    print("\n\n📊 Final Status:")
    status = sleep_service.get_status()
    print(f"   State: {status['state']}")
    print(f"   Sleep count: {status['metrics']['sleep_count']}")
    print(f"   Wake count: {status['metrics']['wake_count']}")
    print(f"   Total sleep time: {status['metrics']['total_sleep_seconds']:.1f}s")

    # Show wake events
    if status.get('recent_wake_events'):
        print("\n📜 Recent Wake Events:")
        for event in status['recent_wake_events']:
            print(f"   - {event['trigger_type']} at {event['timestamp']}")
            print(f"     Slept for: {event['sleep_duration_seconds']:.1f}s")

    # Manual wake (if still sleeping)
    if sleep_service.is_sleeping():
        print("\n6. Manually waking system...")
        await sleep_service.wake(WakeTriggerType.MANUAL)

    # Cleanup
    print("\n7. Stopping services...")
    await cpu_monitor.stop()
    await sleep_service.stop()

    print("\n" + "=" * 70)
    print("Demo Complete! ✅")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  - Check API endpoints: http://localhost:5555/api/sleep/status")
    print("  - Run full tests: pytest tests/unit/test_sleep_mode_service.py -v")
    print("  - Read docs: Backend/SLEEP_MODE_README.md")
    print()


if __name__ == "__main__":
    asyncio.run(main())
