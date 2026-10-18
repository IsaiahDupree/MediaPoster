"""
Agent Event Service (AC-005)
=============================
Service for logging and querying agent events.

Provides:
- Append-only event logging
- Filtering by agent, run, step, topic, status
- Event timeline queries
- Debugging support
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.agent_event import AgentEvent, AgentEventType, AgentEventStatus
from loguru import logger


class AgentEventService:
    """
    Service for managing agent events (AC-005)

    Usage:
        service = AgentEventService(db_session)

        # Log an event
        await service.log_event(
            agent_id="content_ops_agent_1",
            agent_name="Content Ops Controller",
            run_id=run_uuid,
            event_type=AgentEventType.ACTION,
            step=1,
            topic="content_generation",
            message="Generated content from template",
            details={"template_id": "tpl_001", "output_length": 250}
        )

        # Query events
        events = await service.get_events(
            run_id=run_uuid,
            topic="content_generation"
        )
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with database session"""
        self.session = session

    async def log_event(
        self,
        agent_id: str,
        agent_name: str,
        run_id: uuid.UUID,
        event_type: AgentEventType,
        message: str,
        step: int = 0,
        topic: Optional[str] = None,
        status: AgentEventStatus = AgentEventStatus.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> AgentEvent:
        """
        Log a new agent event (append-only)

        Args:
            agent_id: Unique identifier for the agent instance
            agent_name: Human-readable agent name/type
            run_id: UUID of the agent run/session
            event_type: Type of event (started, step, action, etc.)
            message: Human-readable event description
            step: Step number within the run
            topic: Category/topic for filtering
            status: Event status (success, failed, etc.)
            details: Additional structured data
            error: Error message if failed
            duration_ms: Duration of this step

        Returns:
            Created AgentEvent
        """
        try:
            event = AgentEvent(
                agent_id=agent_id,
                agent_name=agent_name,
                run_id=run_id,
                event_type=event_type,
                status=status,
                step=step,
                topic=topic,
                message=message,
                details=details,
                error=error,
                duration_ms=duration_ms
            )

            self.session.add(event)
            await self.session.commit()
            await self.session.refresh(event)

            logger.debug(f"Logged agent event: {agent_name} [{event_type.value}] - {message}")

            return event

        except Exception as e:
            logger.error(f"Failed to log agent event: {e}")
            await self.session.rollback()
            raise

    async def get_events(
        self,
        agent_id: Optional[str] = None,
        run_id: Optional[uuid.UUID] = None,
        topic: Optional[str] = None,
        event_type: Optional[AgentEventType] = None,
        status: Optional[AgentEventStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AgentEvent]:
        """
        Query agent events with filters

        Args:
            agent_id: Filter by agent ID
            run_id: Filter by run ID
            topic: Filter by topic
            event_type: Filter by event type
            status: Filter by status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching AgentEvents
        """
        try:
            # Build query with filters
            query = select(AgentEvent)

            filters = []
            if agent_id:
                filters.append(AgentEvent.agent_id == agent_id)
            if run_id:
                filters.append(AgentEvent.run_id == run_id)
            if topic:
                filters.append(AgentEvent.topic == topic)
            if event_type:
                filters.append(AgentEvent.event_type == event_type)
            if status:
                filters.append(AgentEvent.status == status)

            if filters:
                query = query.where(and_(*filters))

            # Order by step and created_at
            query = query.order_by(AgentEvent.step, AgentEvent.created_at)

            # Apply pagination
            query = query.limit(limit).offset(offset)

            # Execute query
            result = await self.session.execute(query)
            events = result.scalars().all()

            return list(events)

        except Exception as e:
            logger.error(f"Failed to query agent events: {e}")
            raise

    async def get_run_timeline(
        self,
        run_id: uuid.UUID
    ) -> List[AgentEvent]:
        """
        Get complete timeline for a specific agent run

        Args:
            run_id: UUID of the agent run

        Returns:
            List of all events in chronological order
        """
        return await self.get_events(run_id=run_id, limit=10000)

    async def get_failed_events(
        self,
        agent_id: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 50
    ) -> List[AgentEvent]:
        """
        Get failed events for debugging

        Args:
            agent_id: Filter by agent ID
            topic: Filter by topic
            limit: Maximum number of results

        Returns:
            List of failed events
        """
        return await self.get_events(
            agent_id=agent_id,
            topic=topic,
            status=AgentEventStatus.FAILED,
            limit=limit
        )

    async def get_latest_run(
        self,
        agent_id: str
    ) -> Optional[uuid.UUID]:
        """
        Get the most recent run ID for an agent

        Args:
            agent_id: Agent identifier

        Returns:
            UUID of most recent run, or None if no runs found
        """
        try:
            query = (
                select(AgentEvent.run_id)
                .where(AgentEvent.agent_id == agent_id)
                .order_by(desc(AgentEvent.created_at))
                .limit(1)
            )

            result = await self.session.execute(query)
            run_id = result.scalar_one_or_none()

            return run_id

        except Exception as e:
            logger.error(f"Failed to get latest run: {e}")
            return None

    async def count_events(
        self,
        agent_id: Optional[str] = None,
        run_id: Optional[uuid.UUID] = None,
        topic: Optional[str] = None,
        status: Optional[AgentEventStatus] = None
    ) -> int:
        """
        Count events matching filters

        Args:
            agent_id: Filter by agent ID
            run_id: Filter by run ID
            topic: Filter by topic
            status: Filter by status

        Returns:
            Count of matching events
        """
        try:
            from sqlalchemy import func

            query = select(func.count(AgentEvent.id))

            filters = []
            if agent_id:
                filters.append(AgentEvent.agent_id == agent_id)
            if run_id:
                filters.append(AgentEvent.run_id == run_id)
            if topic:
                filters.append(AgentEvent.topic == topic)
            if status:
                filters.append(AgentEvent.status == status)

            if filters:
                query = query.where(and_(*filters))

            result = await self.session.execute(query)
            count = result.scalar()

            return count or 0

        except Exception as e:
            logger.error(f"Failed to count events: {e}")
            return 0


# Context manager for automatic event logging within a run
class AgentRunContext:
    """
    Context manager for automatic agent event logging

    Usage:
        async with AgentRunContext(
            session=db_session,
            agent_id="my_agent",
            agent_name="My Agent",
            topic="my_topic"
        ) as ctx:
            # Log steps
            await ctx.log_step("Step 1: Initialize", details={"status": "ok"})
            await ctx.log_action("Generated content")
            await ctx.log_decision("Chose template A", details={"reason": "best match"})
    """

    def __init__(
        self,
        session: AsyncSession,
        agent_id: str,
        agent_name: str,
        topic: Optional[str] = None
    ):
        self.service = AgentEventService(session)
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.topic = topic
        self.run_id = uuid.uuid4()
        self.step = 0
        self.start_time = None

    async def __aenter__(self):
        """Start agent run"""
        self.start_time = datetime.now(timezone.utc)
        await self.service.log_event(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            run_id=self.run_id,
            event_type=AgentEventType.STARTED,
            message=f"Started {self.agent_name} run",
            step=0,
            topic=self.topic
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End agent run"""
        duration_ms = None
        if self.start_time:
            duration_ms = int((datetime.now(timezone.utc) - self.start_time).total_seconds() * 1000)

        if exc_type is None:
            await self.service.log_event(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                run_id=self.run_id,
                event_type=AgentEventType.COMPLETED,
                message=f"Completed {self.agent_name} run",
                step=self.step + 1,
                topic=self.topic,
                duration_ms=duration_ms
            )
        else:
            await self.service.log_event(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                run_id=self.run_id,
                event_type=AgentEventType.FAILED,
                status=AgentEventStatus.FAILED,
                message=f"Failed {self.agent_name} run",
                step=self.step + 1,
                topic=self.topic,
                error=str(exc_val),
                duration_ms=duration_ms
            )

    async def log_step(self, message: str, **kwargs):
        """Log a step"""
        self.step += 1
        await self.service.log_event(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            run_id=self.run_id,
            event_type=AgentEventType.STEP,
            message=message,
            step=self.step,
            topic=self.topic,
            **kwargs
        )

    async def log_action(self, message: str, **kwargs):
        """Log an action"""
        self.step += 1
        await self.service.log_event(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            run_id=self.run_id,
            event_type=AgentEventType.ACTION,
            message=message,
            step=self.step,
            topic=self.topic,
            **kwargs
        )

    async def log_decision(self, message: str, **kwargs):
        """Log a decision"""
        self.step += 1
        await self.service.log_event(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            run_id=self.run_id,
            event_type=AgentEventType.DECISION,
            message=message,
            step=self.step,
            topic=self.topic,
            **kwargs
        )

    async def log_error(self, message: str, error: str, **kwargs):
        """Log an error"""
        self.step += 1
        await self.service.log_event(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            run_id=self.run_id,
            event_type=AgentEventType.ERROR,
            status=AgentEventStatus.FAILED,
            message=message,
            error=error,
            step=self.step,
            topic=self.topic,
            **kwargs
        )
