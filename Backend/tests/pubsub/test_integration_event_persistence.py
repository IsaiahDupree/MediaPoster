"""
Integration Tests: Event Persistence & Replay
==============================================
Tests against real database for event history.

Tests:
- Events persisted to database
- Event querying with filters
- Event replay functionality
- Workflow tracking by correlation_id
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List

from services.event_bus import EventBus, Event, Topics
from services.workers.event_history_worker import EventHistoryWorker
from database.connection import async_session_maker, init_db
from sqlalchemy import text


@pytest_asyncio.fixture
async def db_session():
    """Get database session."""
    if not async_session_maker:
        await init_db()
    
    if not async_session_maker:
        pytest.skip("Database not available")
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def event_bus():
    """Get fresh event bus."""
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()


@pytest_asyncio.fixture
async def history_worker(event_bus):
    """Create and start event history worker."""
    worker = EventHistoryWorker(event_bus)
    await worker.start()
    yield worker
    await worker.stop()


@pytest.mark.asyncio
async def test_event_persisted_to_database(event_bus, history_worker, db_session):
    """Events are persisted to database."""
    correlation_id = "test-correlation-123"
    
    # Publish event
    event_id = await event_bus.publish(
        Topics.MEDIA_INGESTED,
        {"media_id": "test-123", "file_path": "/test/path"},
        correlation_id=correlation_id
    )
    
    # Wait for worker to persist
    await asyncio.sleep(0.5)
    
    # Check database
    query = text("""
        SELECT event_id, topic, correlation_id, payload
        FROM event_history
        WHERE event_id = :event_id
    """)
    
    result = await db_session.execute(query, {"event_id": event_id})
    row = result.fetchone()
    
    assert row is not None, "Event not found in database"
    assert row.topic == Topics.MEDIA_INGESTED
    assert row.correlation_id == correlation_id
    assert "media_id" in row.payload


@pytest.mark.asyncio
async def test_event_query_by_topic(event_bus, history_worker, db_session):
    """Can query events by topic."""
    # Publish multiple events
    await event_bus.publish(Topics.MEDIA_INGESTED, {"media_id": "1"})
    await event_bus.publish(Topics.PUBLISH_COMPLETED, {"post_id": "1"})
    await event_bus.publish(Topics.MEDIA_INGESTED, {"media_id": "2"})
    
    await asyncio.sleep(0.5)
    
    # Query by topic
    query = text("""
        SELECT COUNT(*) as count
        FROM event_history
        WHERE topic = :topic
    """)
    
    result = await db_session.execute(query, {"topic": Topics.MEDIA_INGESTED})
    count = result.scalar()
    
    assert count >= 2, f"Expected at least 2 events, got {count}"


@pytest.mark.asyncio
async def test_event_query_by_correlation_id(event_bus, history_worker, db_session):
    """Can query events by correlation_id (workflow tracking)."""
    correlation_id = "workflow-test-456"
    
    # Publish related events
    await event_bus.publish(
        Topics.MEDIA_INGESTED,
        {"media_id": "123"},
        correlation_id=correlation_id
    )
    await event_bus.publish(
        Topics.ANALYSIS_COMPLETED,
        {"media_id": "123"},
        correlation_id=correlation_id
    )
    await event_bus.publish(
        Topics.PUBLISH_COMPLETED,
        {"media_id": "123"},
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.5)
    
    # Query workflow
    query = text("""
        SELECT topic, timestamp
        FROM event_history
        WHERE correlation_id = :correlation_id
        ORDER BY timestamp ASC
    """)
    
    result = await db_session.execute(query, {"correlation_id": correlation_id})
    rows = result.fetchall()
    
    assert len(rows) >= 3, f"Expected at least 3 events, got {len(rows)}"
    
    # Verify order
    topics = [row.topic for row in rows]
    assert Topics.MEDIA_INGESTED in topics
    assert Topics.ANALYSIS_COMPLETED in topics
    assert Topics.PUBLISH_COMPLETED in topics


@pytest.mark.asyncio
async def test_event_replay(event_bus, history_worker, db_session):
    """Can replay events from database."""
    correlation_id = "replay-test-789"
    received_events = []
    
    async def handler(event):
        received_events.append(event)
    
    event_bus.subscribe(Topics.MEDIA_INGESTED, handler)
    
    # Publish original event
    original_id = await event_bus.publish(
        Topics.MEDIA_INGESTED,
        {"media_id": "replay-123"},
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.5)
    
    # Clear received events
    received_events.clear()
    
    # Get event from database and replay
    query = text("""
        SELECT event_id, topic, source, correlation_id, payload, metadata, timestamp
        FROM event_history
        WHERE event_id = :event_id
    """)
    
    result = await db_session.execute(query, {"event_id": original_id})
    row = result.fetchone()
    
    assert row is not None
    
    # Reconstruct event
    replayed_event = Event(
        id=row.event_id,
        topic=row.topic,
        timestamp=row.timestamp,
        source=row.source,
        correlation_id=row.correlation_id,
        payload=row.payload if isinstance(row.payload, dict) else {},
        metadata=row.metadata if isinstance(row.metadata, dict) else {}
    )
    
    # Add replay metadata
    replayed_event.metadata["replayed_at"] = datetime.now(timezone.utc).isoformat()
    
    # Replay
    await event_bus.publish_event(replayed_event)
    await asyncio.sleep(0.1)
    
    # Should have received replayed event
    assert len(received_events) == 1
    assert received_events[0].payload["media_id"] == "replay-123"
    assert "replayed_at" in received_events[0].metadata


@pytest.mark.asyncio
async def test_event_query_time_range(event_bus, history_worker, db_session):
    """Can query events by time range."""
    # Publish event now
    await event_bus.publish(Topics.MEDIA_INGESTED, {"media_id": "time-test"})
    await asyncio.sleep(0.5)
    
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    one_hour_later = now + timedelta(hours=1)
    
    # Query recent events
    query = text("""
        SELECT COUNT(*) as count
        FROM event_history
        WHERE timestamp >= :since
          AND timestamp <= :until
    """)
    
    result = await db_session.execute(query, {
        "since": one_hour_ago,
        "until": one_hour_later
    })
    count = result.scalar()
    
    assert count >= 1, "Should have at least one recent event"


@pytest.mark.asyncio
async def test_batch_persistence(event_bus, history_worker, db_session):
    """Multiple events are batched and persisted."""
    # Publish many events quickly
    event_ids = []
    for i in range(10):
        event_id = await event_bus.publish(
            Topics.MEDIA_INGESTED,
            {"media_id": f"batch-{i}"}
        )
        event_ids.append(event_id)
    
    # Wait for batch flush
    await asyncio.sleep(1.0)
    
    # Check all persisted
    query = text("""
        SELECT COUNT(*) as count
        FROM event_history
        WHERE event_id = ANY(:event_ids)
    """)
    
    result = await db_session.execute(query, {"event_ids": event_ids})
    count = result.scalar()
    
    assert count >= 10, f"Expected at least 10 events, got {count}"

