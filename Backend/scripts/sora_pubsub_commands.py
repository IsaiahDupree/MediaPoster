#!/usr/bin/env python3
"""
Sora Pub/Sub Commands
======================
Scripts for Sora automation using the pub/sub event architecture.

Usage:
    python scripts/sora_pubsub_commands.py check-usage
    python scripts/sora_pubsub_commands.py generate "prompt text"
    python scripts/sora_pubsub_commands.py batch "prompt1" "prompt2" "prompt3"
    python scripts/sora_pubsub_commands.py start-worker
    python scripts/sora_pubsub_commands.py subscribe-all
"""

import asyncio
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent dir to path for imports
sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')


async def check_usage():
    """Request Sora usage check via pub/sub."""
    from services.event_bus import EventBus, Topics
    
    bus = EventBus.get_instance()
    
    # Set up handler to receive response
    usage_received = asyncio.Event()
    usage_data = {}
    
    async def on_usage_checked(event):
        nonlocal usage_data
        usage_data = event.payload
        usage_received.set()
        print(f"\n✅ Usage checked:")
        print(f"   Video gens left: {event.payload.get('video_gens_left', '?')}")
        print(f"   Free: {event.payload.get('free_count', '?')}")
        print(f"   Paid: {event.payload.get('paid_count', '?')}")
        print(f"   Resets: {event.payload.get('reset_date', '?')}")
    
    async def on_usage_low(event):
        print(f"\n⚠️  LOW USAGE WARNING: {event.payload.get('video_gens_left')} gens left!")
    
    # Subscribe to responses
    bus.subscribe(Topics.SORA_USAGE_CHECKED, on_usage_checked)
    bus.subscribe(Topics.SORA_USAGE_LOW, on_usage_low)
    
    # Start worker to handle request
    from services.workers.sora_worker import get_sora_worker
    worker = get_sora_worker(bus)
    await worker.start()
    
    # Publish request
    print("📤 Requesting Sora usage check...")
    event_id = await bus.publish(
        Topics.SORA_USAGE_CHECK_REQUESTED,
        {"requested_at": datetime.utcnow().isoformat()},
        source="cli"
    )
    print(f"   Event ID: {event_id}")
    
    # Wait for response (timeout 30s)
    try:
        await asyncio.wait_for(usage_received.wait(), timeout=30)
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for usage check")
    
    await worker.stop()
    return usage_data


async def generate_video(prompt: str, character: str = "isaiahdupree"):
    """Request video generation via pub/sub."""
    from services.event_bus import EventBus, Topics
    
    bus = EventBus.get_instance()
    
    # Set up handlers
    async def on_started(event):
        print(f"\n🎬 Video generation started:")
        print(f"   Prompt: {event.payload.get('prompt', '')[:50]}...")
    
    async def on_completed(event):
        print(f"\n✅ Video completed: {event.payload.get('video_id')}")
    
    async def on_downloaded(event):
        print(f"\n📥 Video downloaded: {event.payload.get('local_path')}")
    
    async def on_failed(event):
        print(f"\n❌ Video failed: {event.payload.get('error')}")
    
    async def on_poll_tick(event):
        print(f"   🔄 Poll tick #{event.payload.get('tick')}: {event.payload.get('queue_count')} generating")
    
    # Subscribe
    bus.subscribe(Topics.SORA_VIDEO_STARTED, on_started)
    bus.subscribe(Topics.SORA_VIDEO_COMPLETED, on_completed)
    bus.subscribe(Topics.SORA_VIDEO_DOWNLOADED, on_downloaded)
    bus.subscribe(Topics.SORA_VIDEO_FAILED, on_failed)
    bus.subscribe(Topics.SORA_POLL_TICK, on_poll_tick)
    
    # Start worker
    from services.workers.sora_worker import get_sora_worker
    worker = get_sora_worker(bus)
    await worker.start()
    
    # Publish request
    print(f"📤 Requesting video generation...")
    print(f"   Prompt: {prompt[:60]}...")
    print(f"   Character: @{character}")
    
    event_id = await bus.publish(
        Topics.SORA_VIDEO_REQUESTED,
        {
            "prompt": prompt,
            "character": character,
            "duration": 15,
            "aspect_ratio": "Portrait"
        },
        source="cli"
    )
    print(f"   Event ID: {event_id}")
    
    # Wait for completion (15 min timeout for generation)
    print("\n⏳ Waiting for video generation (may take 8-12 minutes)...")
    await asyncio.sleep(900)  # 15 min max
    
    await worker.stop()


async def generate_batch(prompts: list, character: str = "isaiahdupree"):
    """Request batch video generation via pub/sub."""
    from services.event_bus import EventBus, Topics
    
    bus = EventBus.get_instance()
    
    # Set up handlers
    async def on_batch_started(event):
        print(f"\n📦 Batch started: {event.payload.get('count')} videos")
    
    async def on_video_started(event):
        idx = event.payload.get('batch_index', '?')
        total = event.payload.get('batch_total', '?')
        print(f"   🎬 Video {idx+1}/{total} started")
    
    async def on_batch_completed(event):
        print(f"\n✅ Batch completed!")
    
    # Subscribe
    bus.subscribe(Topics.SORA_BATCH_STARTED, on_batch_started)
    bus.subscribe(Topics.SORA_VIDEO_STARTED, on_video_started)
    bus.subscribe(Topics.SORA_BATCH_COMPLETED, on_batch_completed)
    
    # Start worker
    from services.workers.sora_worker import get_sora_worker
    worker = get_sora_worker(bus)
    await worker.start()
    
    # Publish request
    print(f"📤 Requesting batch generation ({len(prompts)} videos)...")
    
    event_id = await bus.publish(
        Topics.SORA_BATCH_REQUESTED,
        {
            "prompts": prompts,
            "character": character,
            "auto_download": True
        },
        source="cli"
    )
    print(f"   Event ID: {event_id}")
    
    # Wait for batch
    await asyncio.sleep(900)
    
    await worker.stop()


async def start_worker():
    """Start the Sora worker and keep it running."""
    from services.event_bus import EventBus, Topics
    from services.workers.sora_worker import get_sora_worker
    
    bus = EventBus.get_instance()
    worker = get_sora_worker(bus)
    
    print("🚀 Starting Sora worker...")
    await worker.start()
    
    print("✅ Sora worker running. Subscribed to:")
    for topic in worker.get_subscriptions():
        print(f"   - {topic}")
    
    print("\nPress Ctrl+C to stop...")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping worker...")
        await worker.stop()


async def subscribe_all():
    """Subscribe to all Sora events and log them."""
    from services.event_bus import EventBus, Topics
    
    bus = EventBus.get_instance()
    
    async def log_event(event):
        print(f"📬 {event.topic} | {event.payload}")
    
    # Subscribe to all Sora events
    bus.subscribe("sora.*", log_event)
    
    print("👂 Listening to all sora.* events...")
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopped")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check-usage":
        asyncio.run(check_usage())
    
    elif command == "generate":
        if len(sys.argv) < 3:
            print("Usage: python sora_pubsub_commands.py generate 'prompt text'")
            sys.exit(1)
        prompt = sys.argv[2]
        character = sys.argv[3] if len(sys.argv) > 3 else "isaiahdupree"
        asyncio.run(generate_video(prompt, character))
    
    elif command == "batch":
        if len(sys.argv) < 3:
            print("Usage: python sora_pubsub_commands.py batch 'prompt1' 'prompt2' ...")
            sys.exit(1)
        prompts = sys.argv[2:]
        asyncio.run(generate_batch(prompts))
    
    elif command == "start-worker":
        asyncio.run(start_worker())
    
    elif command == "subscribe-all":
        asyncio.run(subscribe_all())
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
