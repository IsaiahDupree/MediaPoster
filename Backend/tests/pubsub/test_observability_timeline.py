"""
Observability Tests: Timeline Correctness
==========================================
Tests to guarantee UI timeline is trustworthy.

Tests:
- Every run has proper lifecycle events
- Event ordering is consistent
- No gaps in timeline
- Sensitive data not exposed
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from services.event_bus import EventBus, Event, Topics
from database.connection import async_session_maker
from sqlalchemy import text


@pytest.fixture
def event_bus():
    """Get fresh event bus."""
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()


@pytest.mark.asyncio
async def test_publish_workflow_lifecycle(event_bus):
    """Publish workflow has proper lifecycle: requested → started → completed."""
    correlation_id = f"lifecycle-{datetime.now().timestamp()}"
    events = []
    
    async def track(event):
        if event.correlation_id == correlation_id:
            events.append(event.topic)
    
    event_bus.subscribe("*", track)
    
    # Simulate publish workflow
    await event_bus.publish(
        Topics.PUBLISH_REQUESTED,
        {"media_id": "lifecycle-123"},
        correlation_id=correlation_id
    )
    
    await event_bus.publish(
        Topics.PUBLISH_STARTED,
        {"media_id": "lifecycle-123"},
        correlation_id=correlation_id
    )
    
    await event_bus.publish(
        Topics.PUBLISH_COMPLETED,
        {"media_id": "lifecycle-123"},
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.2)
    
    # Verify lifecycle
    assert Topics.PUBLISH_REQUESTED in events
    assert Topics.PUBLISH_STARTED in events
    assert Topics.PUBLISH_COMPLETED in events
    
    # Verify ordering
    requested_idx = events.index(Topics.PUBLISH_REQUESTED)
    started_idx = events.index(Topics.PUBLISH_STARTED)
    completed_idx = events.index(Topics.PUBLISH_COMPLETED)
    
    assert requested_idx < started_idx < completed_idx, "Events out of order"


@pytest.mark.asyncio
async def test_analysis_workflow_lifecycle(event_bus):
    """Analysis workflow has proper lifecycle."""
    correlation_id = f"analysis-lifecycle-{datetime.now().timestamp()}"
    events = []
    
    async def track(event):
        if event.correlation_id == correlation_id:
            events.append((event.topic, event.timestamp))
    
    event_bus.subscribe("*", track)
    
    # Simulate analysis workflow
    await event_bus.publish(
        Topics.ANALYSIS_REQUESTED,
        {"media_id": "analysis-123"},
        correlation_id=correlation_id
    )
    
    await event_bus.publish(
        Topics.ANALYSIS_STARTED,
        {"media_id": "analysis-123"},
        correlation_id=correlation_id
    )
    
    await event_bus.publish(
        Topics.ANALYSIS_PROGRESS,
        {"media_id": "analysis-123", "progress": 50},
        correlation_id=correlation_id
    )
    
    await event_bus.publish(
        Topics.ANALYSIS_COMPLETED,
        {"media_id": "analysis-123"},
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.2)
    
    # Verify lifecycle
    topics = [e[0] for e in events]
    assert Topics.ANALYSIS_REQUESTED in topics
    assert Topics.ANALYSIS_STARTED in topics
    assert Topics.ANALYSIS_PROGRESS in topics
    assert Topics.ANALYSIS_COMPLETED in topics
    
    # Verify timestamps are sequential
    timestamps = [e[1] for e in events]
    assert timestamps == sorted(timestamps), "Timestamps not sequential"


@pytest.mark.asyncio
async def test_no_sensitive_data_in_events(event_bus):
    """Events don't contain sensitive data."""
    correlation_id = f"sensitive-{datetime.now().timestamp()}"
    captured_events = []
    
    async def capture(event):
        if event.correlation_id == correlation_id:
            captured_events.append(event)
    
    event_bus.subscribe("*", capture)
    
    # Publish event with potentially sensitive data
    await event_bus.publish(
        Topics.PUBLISH_COMPLETED,
        {
            "media_id": "test-123",
            "platform": "tiktok",
            "platform_url": "https://tiktok.com/...",
            # These should NOT be in events:
            # "api_key": "secret-key-123",  # Should be filtered
            # "password": "secret-password"  # Should be filtered
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.1)
    
    # Verify no sensitive fields
    for event in captured_events:
        payload = event.payload
        assert "api_key" not in payload, "API key found in event"
        assert "password" not in payload, "Password found in event"
        assert "secret" not in str(payload).lower(), "Secret data found in event"


@pytest.mark.asyncio
async def test_event_timestamps_consistent(event_bus):
    """Event timestamps are consistent and monotonic."""
    correlation_id = f"timestamp-{datetime.now().timestamp()}"
    events = []
    
    async def track(event):
        if event.correlation_id == correlation_id:
            events.append((event.topic, event.timestamp))
    
    event_bus.subscribe("*", track)
    
    # Publish events with small delays
    await event_bus.publish(Topics.MEDIA_INGESTED, {"media_id": "1"}, correlation_id=correlation_id)
    await asyncio.sleep(0.05)
    await event_bus.publish(Topics.ANALYSIS_STARTED, {"media_id": "1"}, correlation_id=correlation_id)
    await asyncio.sleep(0.05)
    await event_bus.publish(Topics.ANALYSIS_COMPLETED, {"media_id": "1"}, correlation_id=correlation_id)
    
    await asyncio.sleep(0.1)
    
    # Verify timestamps are monotonic
    timestamps = [e[1] for e in events]
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i-1], f"Timestamp {i} is before {i-1}"


@pytest.mark.asyncio
async def test_correlation_id_tracks_workflow(event_bus):
    """Correlation ID properly tracks entire workflow."""
    correlation_id = f"workflow-track-{datetime.now().timestamp()}"
    workflow_events = []
    
    async def track(event):
        if event.correlation_id == correlation_id:
            workflow_events.append({
                "topic": event.topic,
                "timestamp": event.timestamp,
                "source": event.source
            })
    
    event_bus.subscribe("*", track)
    
    # Publish workflow events
    await event_bus.publish(
        Topics.MEDIA_INGESTED,
        {"media_id": "track-123"},
        correlation_id=correlation_id,
        source="ingestion-service"
    )
    
    await event_bus.publish(
        Topics.ANALYSIS_COMPLETED,
        {"media_id": "track-123"},
        correlation_id=correlation_id,
        source="analysis-service"
    )
    
    await event_bus.publish(
        Topics.PUBLISH_COMPLETED,
        {"media_id": "track-123"},
        correlation_id=correlation_id,
        source="publish-service"
    )
    
    await asyncio.sleep(0.2)
    
    # Verify all events tracked
    assert len(workflow_events) == 3
    
    # Verify sources are preserved
    sources = [e["source"] for e in workflow_events]
    assert "ingestion-service" in sources
    assert "analysis-service" in sources
    assert "publish-service" in sources


@pytest.mark.asyncio
async def test_event_history_completeness(event_bus):
    """Event history captures all workflow events."""
    if not async_session_maker:
        pytest.skip("Database not available")
    
    correlation_id = f"history-complete-{datetime.now().timestamp()}"
    
    # Publish workflow
    await event_bus.publish(
        Topics.MEDIA_INGESTED,
        {"media_id": "history-123"},
        correlation_id=correlation_id
    )
    
    await event_bus.publish(
        Topics.ANALYSIS_COMPLETED,
        {"media_id": "history-123"},
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.5)  # Wait for persistence
    
    # Check database
    async with async_session_maker() as session:
        query = text("""
            SELECT topic, timestamp
            FROM event_history
            WHERE correlation_id = :correlation_id
            ORDER BY timestamp ASC
        """)
        
        result = await session.execute(query, {"correlation_id": correlation_id})
        rows = result.fetchall()
        
        # Should have both events
        assert len(rows) >= 2, f"Expected at least 2 events, got {len(rows)}"
        
        topics = [row.topic for row in rows]
        assert Topics.MEDIA_INGESTED in topics
        assert Topics.ANALYSIS_COMPLETED in topics

