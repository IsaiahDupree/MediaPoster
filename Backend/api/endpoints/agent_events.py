"""
Agent Events API (AC-005)
==========================
Query and filter agent events for debugging and observability.

Endpoints:
- GET /api/agent-events - Query events with filters
- GET /api/agent-events/run/{run_id} - Get timeline for a specific run
- GET /api/agent-events/failed - Get failed events for debugging
- GET /api/agent-events/topics - Get list of available topics
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from uuid import UUID
from loguru import logger

from database.connection import get_db
from services.agent_event_service import AgentEventService
from models.agent_event import AgentEventType, AgentEventStatus


router = APIRouter(prefix="/api/agent-events", tags=["Agent Events"])


@router.get("")
async def get_agent_events(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    run_id: Optional[UUID] = Query(None, description="Filter by run ID"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    Query agent events with filters

    Returns a list of events matching the specified filters, ordered by step and time.

    Args:
        agent_id: Filter by specific agent
        run_id: Filter by specific run
        topic: Filter by category/topic
        event_type: Filter by event type (started, step, action, decision, error, completed, failed)
        status: Filter by status (pending, running, success, failed, skipped)
        limit: Maximum results to return
        offset: Number of results to skip for pagination

    Returns:
        List of agent events with metadata
    """
    try:
        # Parse enums if provided
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = AgentEventType(event_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event_type: {event_type}. Valid values: {[t.value for t in AgentEventType]}"
                )

        status_enum = None
        if status:
            try:
                status_enum = AgentEventStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid values: {[s.value for s in AgentEventStatus]}"
                )

        # Query events
        async for session in get_async_session():
            service = AgentEventService(session)

            events = await service.get_events(
                agent_id=agent_id,
                run_id=run_id,
                topic=topic,
                event_type=event_type_enum,
                status=status_enum,
                limit=limit,
                offset=offset
            )

            # Get total count for pagination
            total = await service.count_events(
                agent_id=agent_id,
                run_id=run_id,
                topic=topic,
                status=status_enum
            )

            return {
                "success": True,
                "data": {
                    "events": [event.to_dict() for event in events],
                    "pagination": {
                        "total": total,
                        "limit": limit,
                        "offset": offset,
                        "has_more": (offset + limit) < total
                    }
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying agent events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run/{run_id}")
async def get_run_timeline(run_id: UUID):
    """
    Get complete timeline for a specific agent run

    Returns all events for the run in chronological order, showing the full
    execution flow from start to completion/failure.

    Args:
        run_id: UUID of the agent run

    Returns:
        Complete timeline of events
    """
    try:
        async for session in get_async_session():
            service = AgentEventService(session)
            events = await service.get_run_timeline(run_id)

            if not events:
                raise HTTPException(
                    status_code=404,
                    detail=f"No events found for run {run_id}"
                )

            # Get summary info
            start_event = events[0] if events else None
            end_event = events[-1] if events else None

            duration_ms = None
            if start_event and end_event and start_event.created_at and end_event.created_at:
                duration_ms = int((end_event.created_at - start_event.created_at).total_seconds() * 1000)

            failed_count = len([e for e in events if e.status == AgentEventStatus.FAILED])

            return {
                "success": True,
                "data": {
                    "run_id": str(run_id),
                    "agent_id": start_event.agent_id if start_event else None,
                    "agent_name": start_event.agent_name if start_event else None,
                    "total_steps": len(events),
                    "failed_steps": failed_count,
                    "duration_ms": duration_ms,
                    "timeline": [event.to_dict() for event in events]
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting run timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failed")
async def get_failed_events(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results")
):
    """
    Get failed events for debugging

    Returns recent failed events to help debug issues with autonomous agents.

    Args:
        agent_id: Filter by specific agent
        topic: Filter by category/topic
        limit: Maximum results to return

    Returns:
        List of failed events
    """
    try:
        async for session in get_async_session():
            service = AgentEventService(session)
            events = await service.get_failed_events(
                agent_id=agent_id,
                topic=topic,
                limit=limit
            )

            return {
                "success": True,
                "data": {
                    "failed_events": [event.to_dict() for event in events],
                    "count": len(events)
                }
            }

    except Exception as e:
        logger.error(f"Error getting failed events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def get_topics():
    """
    Get list of unique topics from agent events

    Useful for discovering available filters and understanding agent activity categories.

    Returns:
        List of unique topics with event counts
    """
    try:
        async for session in get_async_session():
            from sqlalchemy import select, func, distinct
            from models.agent_event import AgentEvent

            # Query distinct topics with counts
            query = (
                select(
                    AgentEvent.topic,
                    func.count(AgentEvent.id).label("count")
                )
                .where(AgentEvent.topic.isnot(None))
                .group_by(AgentEvent.topic)
                .order_by(func.count(AgentEvent.id).desc())
            )

            result = await session.execute(query)
            topics = result.all()

            return {
                "success": True,
                "data": {
                    "topics": [
                        {
                            "topic": topic,
                            "event_count": count
                        }
                        for topic, count in topics
                    ]
                }
            }

    except Exception as e:
        logger.error(f"Error getting topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def get_agents():
    """
    Get list of agents that have logged events

    Useful for discovering available agents and their activity levels.

    Returns:
        List of agents with event counts and latest run info
    """
    try:
        async for session in get_async_session():
            from sqlalchemy import select, func
            from models.agent_event import AgentEvent

            # Query distinct agents with counts
            query = (
                select(
                    AgentEvent.agent_id,
                    AgentEvent.agent_name,
                    func.count(AgentEvent.id).label("event_count"),
                    func.max(AgentEvent.created_at).label("latest_activity")
                )
                .group_by(AgentEvent.agent_id, AgentEvent.agent_name)
                .order_by(func.max(AgentEvent.created_at).desc())
            )

            result = await session.execute(query)
            agents = result.all()

            return {
                "success": True,
                "data": {
                    "agents": [
                        {
                            "agent_id": agent_id,
                            "agent_name": agent_name,
                            "event_count": event_count,
                            "latest_activity": latest_activity.isoformat() if latest_activity else None
                        }
                        for agent_id, agent_name, event_count, latest_activity in agents
                    ]
                }
            }

    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
