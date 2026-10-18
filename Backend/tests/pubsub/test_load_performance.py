"""
Load & Performance Tests: Queue Pressure & Realtime
====================================================
Tests to validate throughput and prevent silent lag.

Tests:
- Producer burst (1k events)
- Consumer scaling
- Latency measurements
- Event insert rate
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from typing import List

from services.event_bus import EventBus, Event, Topics


@pytest.fixture
def event_bus():
    """Get fresh event bus."""
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()


@pytest.mark.asyncio
async def test_producer_burst(event_bus):
    """Test handling 1000 events published quickly."""
    events_processed = []
    
    async def handler(event):
        events_processed.append(event.id)
    
    event_bus.subscribe(Topics.MEDIA_INGESTED, handler)
    
    # Publish 1000 events
    start_time = time.time()
    event_ids = []
    
    for i in range(1000):
        event_id = await event_bus.publish(
            Topics.MEDIA_INGESTED,
            {"media_id": f"burst-{i}"}
        )
        event_ids.append(event_id)
    
    publish_time = time.time() - start_time
    
    # Wait for processing
    await asyncio.sleep(2.0)
    
    # Verify all processed
    assert len(events_processed) == 1000, f"Expected 1000 events, got {len(events_processed)}"
    
    # Publish should be fast (< 1 second for 1000 events)
    assert publish_time < 1.0, f"Publish took {publish_time:.2f}s, expected < 1.0s"


@pytest.mark.asyncio
async def test_multiple_consumers_scaling(event_bus):
    """Test multiple consumers processing events."""
    handler1_events = []
    handler2_events = []
    handler3_events = []
    
    async def handler1(event):
        handler1_events.append(event.id)
    
    async def handler2(event):
        handler2_events.append(event.id)
    
    async def handler3(event):
        handler3_events.append(event.id)
    
    # Multiple subscribers to same topic
    event_bus.subscribe(Topics.MEDIA_INGESTED, handler1)
    event_bus.subscribe(Topics.MEDIA_INGESTED, handler2)
    event_bus.subscribe(Topics.MEDIA_INGESTED, handler3)
    
    # Publish events
    for i in range(100):
        await event_bus.publish(
            Topics.MEDIA_INGESTED,
            {"media_id": f"scale-{i}"}
        )
    
    await asyncio.sleep(0.5)
    
    # All handlers should receive all events
    assert len(handler1_events) == 100
    assert len(handler2_events) == 100
    assert len(handler3_events) == 100


@pytest.mark.asyncio
async def test_event_latency(event_bus):
    """Test latency from publish to handler."""
    latencies = []
    
    async def handler(event):
        receive_time = time.time()
        # Extract publish time from metadata if available
        if "publish_timestamp" in event.metadata:
            publish_time = event.metadata["publish_timestamp"]
            latency = receive_time - publish_time
            latencies.append(latency)
    
    event_bus.subscribe(Topics.MEDIA_INGESTED, handler)
    
    # Publish events with timestamps
    for i in range(50):
        await event_bus.publish(
            Topics.MEDIA_INGESTED,
            {"media_id": f"latency-{i}"},
            metadata={"publish_timestamp": time.time()}
        )
    
    await asyncio.sleep(0.3)
    
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        # Average latency should be < 10ms for in-memory bus
        assert avg_latency < 0.01, f"Average latency {avg_latency*1000:.2f}ms too high"
        # Max latency should be < 50ms
        assert max_latency < 0.05, f"Max latency {max_latency*1000:.2f}ms too high"


@pytest.mark.asyncio
async def test_concurrent_publishers(event_bus):
    """Test concurrent publishers don't interfere."""
    events_received = []
    
    async def handler(event):
        events_received.append(event.id)
    
    event_bus.subscribe(Topics.MEDIA_INGESTED, handler)
    
    # Publish concurrently
    async def publish_batch(start_idx, count):
        for i in range(count):
            await event_bus.publish(
                Topics.MEDIA_INGESTED,
                {"media_id": f"concurrent-{start_idx + i}"}
            )
    
    # 5 concurrent publishers, 20 events each
    await asyncio.gather(
        publish_batch(0, 20),
        publish_batch(20, 20),
        publish_batch(40, 20),
        publish_batch(60, 20),
        publish_batch(80, 20)
    )
    
    await asyncio.sleep(0.5)
    
    # Should receive all 100 events
    assert len(events_received) == 100


@pytest.mark.asyncio
async def test_event_throughput(event_bus):
    """Test events per second throughput."""
    events_processed = 0
    
    async def handler(event):
        nonlocal events_processed
        events_processed += 1
    
    event_bus.subscribe(Topics.MEDIA_INGESTED, handler)
    
    # Publish for 1 second
    start_time = time.time()
    end_time = start_time + 1.0
    published = 0
    
    while time.time() < end_time:
        await event_bus.publish(
            Topics.MEDIA_INGESTED,
            {"media_id": f"throughput-{published}"}
        )
        published += 1
    
    # Wait for processing
    await asyncio.sleep(0.5)
    
    elapsed = time.time() - start_time
    throughput = events_processed / elapsed
    
    # Should handle at least 1000 events/second
    assert throughput > 1000, f"Throughput {throughput:.0f} events/s too low"


@pytest.mark.asyncio
async def test_memory_usage_under_load(event_bus):
    """Test memory doesn't grow unbounded under load."""
    import sys
    
    # Clear event log
    event_bus._event_log.clear()
    
    initial_size = sys.getsizeof(event_bus._event_log)
    
    # Publish many events
    for i in range(5000):
        await event_bus.publish(
            Topics.MEDIA_INGESTED,
            {"media_id": f"memory-{i}"}
        )
    
    await asyncio.sleep(0.2)
    
    # Event log should be bounded (max_log_size = 1000)
    assert len(event_bus._event_log) <= 1000, "Event log exceeded max size"
    
    final_size = sys.getsizeof(event_bus._event_log)
    
    # Size should be bounded
    size_increase = final_size - initial_size
    assert size_increase < 10 * 1024 * 1024, "Memory growth too large"  # < 10MB

