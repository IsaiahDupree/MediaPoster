"""
Event History API
=================
Endpoints for querying and replaying events from the database.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from database.connection import get_db
from services.event_bus import EventBus, Event, Topics
from loguru import logger

router = APIRouter(prefix="/api/event-history", tags=["Event History"])


class EventHistoryResponse(BaseModel):
    """Response model for event history query."""
    id: str
    event_id: str
    topic: str
    source: str
    correlation_id: Optional[str]
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    created_at: datetime


class EventHistoryListResponse(BaseModel):
    """Response model for event history list."""
    events: List[EventHistoryResponse]
    total: int
    limit: int
    offset: int


@router.get("/events", response_model=EventHistoryListResponse)
async def get_events(
    topic: Optional[str] = Query(None, description="Filter by topic (supports wildcards)"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    source: Optional[str] = Query(None, description="Filter by source"),
    since: Optional[datetime] = Query(None, description="Filter events after this timestamp"),
    until: Optional[datetime] = Query(None, description="Filter events before this timestamp"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
):
    """
    Query event history with filters.
    
    Supports filtering by:
    - topic (exact match or wildcard pattern)
    - correlation_id (workflow tracking)
    - source (service that emitted the event)
    - timestamp range (since/until)
    """
    try:
        # Build query
        query = text("""
            SELECT 
                id,
                event_id,
                topic,
                source,
                correlation_id,
                payload,
                metadata,
                timestamp,
                created_at
            FROM event_history
            WHERE 1=1
        """)
        
        params = {}
        
        if topic:
            if '*' in topic or '%' in topic:
                # Wildcard pattern
                pattern = topic.replace('*', '%')
                query += " AND topic LIKE :topic_pattern"
                params["topic_pattern"] = pattern
            else:
                query += " AND topic = :topic"
                params["topic"] = topic
        
        if correlation_id:
            query += " AND correlation_id = :correlation_id"
            params["correlation_id"] = correlation_id
        
        if source:
            query += " AND source = :source"
            params["source"] = source
        
        if since:
            query += " AND timestamp >= :since"
            params["since"] = since
        
        if until:
            query += " AND timestamp <= :until"
            params["until"] = until
        
        # Get total count
        count_query = text(f"""
            SELECT COUNT(*) as total
            FROM ({query}) as filtered
        """)
        count_result = await db.execute(count_query, params)
        total = count_result.scalar() or 0
        
        # Add ordering and pagination
        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        
        # Execute query
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        # Convert to response models
        events = []
        for row in rows:
            events.append(EventHistoryResponse(
                id=str(row.id),
                event_id=row.event_id,
                topic=row.topic,
                source=row.source,
                correlation_id=row.correlation_id,
                payload=row.payload if isinstance(row.payload, dict) else {},
                metadata=row.metadata if isinstance(row.metadata, dict) else {},
                timestamp=row.timestamp,
                created_at=row.created_at
            ))
        
        return EventHistoryListResponse(
            events=events,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error querying event history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{event_id}")
async def get_event_by_id(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific event by its database ID."""
    try:
        query = text("""
            SELECT 
                id,
                event_id,
                topic,
                source,
                correlation_id,
                payload,
                metadata,
                timestamp,
                created_at
            FROM event_history
            WHERE id = :event_id OR event_id = :event_id
            LIMIT 1
        """)
        
        result = await db.execute(query, {"event_id": event_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return EventHistoryResponse(
            id=str(row.id),
            event_id=row.event_id,
            topic=row.topic,
            source=row.source,
            correlation_id=row.correlation_id,
            payload=row.payload if isinstance(row.payload, dict) else {},
            metadata=row.metadata if isinstance(row.metadata, dict) else {},
            timestamp=row.timestamp,
            created_at=row.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow/{correlation_id}")
async def get_workflow_events(
    correlation_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get all events for a specific workflow (correlation_id)."""
    try:
        query = text("""
            SELECT 
                id,
                event_id,
                topic,
                source,
                correlation_id,
                payload,
                metadata,
                timestamp,
                created_at
            FROM event_history
            WHERE correlation_id = :correlation_id
            ORDER BY timestamp ASC
            LIMIT :limit
        """)
        
        result = await db.execute(query, {
            "correlation_id": correlation_id,
            "limit": limit
        })
        rows = result.fetchall()
        
        events = []
        for row in rows:
            events.append(EventHistoryResponse(
                id=str(row.id),
                event_id=row.event_id,
                topic=row.topic,
                source=row.source,
                correlation_id=row.correlation_id,
                payload=row.payload if isinstance(row.payload, dict) else {},
                metadata=row.metadata if isinstance(row.metadata, dict) else {},
                timestamp=row.timestamp,
                created_at=row.created_at
            ))
        
        return {
            "correlation_id": correlation_id,
            "events": events,
            "count": len(events)
        }
        
    except Exception as e:
        logger.error(f"Error fetching workflow events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/{event_id}/replay")
async def replay_event(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Replay a specific event by republishing it to the event bus.
    
    Useful for:
    - Debugging failed workflows
    - Recovering from errors
    - Testing event handlers
    """
    try:
        # Get event from database
        query = text("""
            SELECT 
                event_id,
                topic,
                source,
                correlation_id,
                payload,
                metadata,
                timestamp
            FROM event_history
            WHERE id = :event_id OR event_id = :event_id
            LIMIT 1
        """)
        
        result = await db.execute(query, {"event_id": event_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Reconstruct event
        event = Event(
            id=row.event_id,
            topic=row.topic,
            timestamp=row.timestamp,
            source=row.source,
            correlation_id=row.correlation_id,
            payload=row.payload if isinstance(row.payload, dict) else {},
            metadata={
                **(row.metadata if isinstance(row.metadata, dict) else {}),
                "replayed_at": datetime.utcnow().isoformat(),
                "replayed_from": event_id
            }
        )
        
        # Republish to event bus
        event_bus = EventBus.get_instance()
        replayed_id = await event_bus.publish_event(event)
        
        return {
            "success": True,
            "original_event_id": row.event_id,
            "replayed_event_id": replayed_id,
            "topic": row.topic,
            "message": "Event replayed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replaying event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_event_statistics(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    db: AsyncSession = Depends(get_db)
):
    """Get event statistics for the last N hours."""
    try:
        query = text("""
            SELECT 
                topic,
                COUNT(*) as event_count,
                COUNT(DISTINCT correlation_id) as unique_workflows,
                COUNT(DISTINCT source) as unique_sources,
                MIN(timestamp) as first_event,
                MAX(timestamp) as last_event
            FROM event_history
            WHERE timestamp >= NOW() - INTERVAL ':hours hours'
            GROUP BY topic
            ORDER BY event_count DESC
        """)
        
        result = await db.execute(query, {"hours": hours})
        rows = result.fetchall()
        
        stats = []
        for row in rows:
            stats.append({
                "topic": row.topic,
                "event_count": row.event_count,
                "unique_workflows": row.unique_workflows,
                "unique_sources": row.unique_sources,
                "first_event": row.first_event.isoformat() if row.first_event else None,
                "last_event": row.last_event.isoformat() if row.last_event else None
            })
        
        return {
            "period_hours": hours,
            "topics": stats,
            "total_events": sum(s["event_count"] for s in stats)
        }
        
    except Exception as e:
        logger.error(f"Error fetching event statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

