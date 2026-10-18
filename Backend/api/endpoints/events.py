"""
Events API
==========
API endpoints for event bus monitoring and debugging.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any

from services.event_bus import EventBus, Topics

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/topics")
async def list_topics():
    """List all defined event topics."""
    return {
        "topics": Topics.all_topics(),
        "count": len(Topics.all_topics())
    }


@router.get("/recent")
async def get_recent_events(
    topic: Optional[str] = Query(None, description="Filter by topic pattern"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    limit: int = Query(50, le=200, description="Max events to return")
):
    """Get recent events from the event log."""
    bus = EventBus.get_instance()
    events = bus.get_recent_events(
        topic_pattern=topic,
        correlation_id=correlation_id,
        limit=limit
    )
    
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


@router.get("/stats")
async def get_event_bus_stats():
    """Get event bus statistics."""
    bus = EventBus.get_instance()
    return bus.get_stats()


@router.get("/subscribers")
async def get_subscribers(
    topic: Optional[str] = Query(None, description="Filter by topic pattern")
):
    """Get subscriber counts per topic."""
    bus = EventBus.get_instance()
    return bus.get_subscriber_count(topic)


@router.get("/dead-letter")
async def get_dead_letter_queue(
    limit: int = Query(50, le=200)
):
    """Get events from the dead-letter queue (failed events)."""
    bus = EventBus.get_instance()
    dlq = bus.get_dead_letter_queue(limit)
    
    return {
        "events": [
            {"event": e.to_dict(), "error": err}
            for e, err in dlq
        ],
        "count": len(dlq)
    }


@router.post("/dead-letter/clear")
async def clear_dead_letter_queue():
    """Clear the dead-letter queue."""
    bus = EventBus.get_instance()
    count = bus.clear_dead_letter_queue()
    
    return {"cleared": count, "message": f"Cleared {count} failed events"}


@router.post("/replay/{event_id}")
async def replay_event(event_id: str):
    """Replay an event from the log."""
    bus = EventBus.get_instance()
    success = await bus.replay_event(event_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    
    return {"message": f"Event {event_id} replayed", "success": True}


@router.post("/publish")
async def publish_event(
    topic: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None
):
    """Manually publish an event (for testing/debugging)."""
    bus = EventBus.get_instance()
    event_id = await bus.publish(
        topic=topic,
        payload=payload,
        correlation_id=correlation_id,
        source="api-manual"
    )
    
    return {
        "event_id": event_id,
        "topic": topic,
        "message": "Event published"
    }
