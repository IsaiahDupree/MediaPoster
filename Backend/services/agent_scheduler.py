"""
Agent Scheduler Service
========================
AC-002: Schedule agent runs with cron/interval, enable/disable

Manages scheduled execution of autonomous agents (narrative, experiments, content_mix, etc.)
Calculates next run times, tracks execution history, and handles enable/disable states.

Features:
- Interval-based scheduling (run every N seconds)
- Cron expression support (complex schedules)
- Enable/disable schedules
- Next run time calculation
- Integration with agent run tracking
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from loguru import logger
from croniter import croniter
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import async_session_maker


class AgentScheduler:
    """
    Agent Scheduler Service

    Manages scheduled execution of autonomous agents.
    Coordinates with agent runners to execute scheduled tasks.

    Usage:
        scheduler = AgentScheduler.get_instance()
        await scheduler.start()

        # Create a schedule
        schedule_id = await scheduler.create_schedule(
            agent_type="narrative",
            schedule_name="Daily Narrative Cycle",
            interval_seconds=86400,
            config={"budget_per_run": 5.0}
        )

        # Get next run time
        next_run = await scheduler.get_next_run_time(schedule_id)

        # Check for due schedules
        due_schedules = await scheduler.get_due_schedules()
    """

    _instance: Optional["AgentScheduler"] = None

    def __init__(self):
        """Initialize agent scheduler"""
        if AgentScheduler._instance is not None:
            raise RuntimeError("Use AgentScheduler.get_instance()")

        self._is_running = False
        self._check_task: Optional[asyncio.Task] = None
        self._check_interval = 60  # Check for due schedules every 60 seconds

        logger.info("📅 Agent Scheduler initialized")

    @classmethod
    def get_instance(cls) -> "AgentScheduler":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self):
        """Start the scheduler background task"""
        if self._is_running:
            logger.warning("Agent Scheduler already running")
            return

        self._is_running = True
        self._check_task = asyncio.create_task(self._schedule_check_loop())
        logger.success("✓ Agent Scheduler started (checking every 60s)")

    async def stop(self):
        """Stop the scheduler background task"""
        self._is_running = False

        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

        logger.info("Agent Scheduler stopped")

    async def _schedule_check_loop(self):
        """Background loop to check for due schedules"""
        while self._is_running:
            try:
                await self._process_due_schedules()
            except Exception as e:
                logger.error(f"Error in schedule check loop: {e}")

            # Wait before next check
            await asyncio.sleep(self._check_interval)

    async def _process_due_schedules(self):
        """Find and process schedules that are due to run"""
        due_schedules = await self.get_due_schedules()

        if not due_schedules:
            return

        logger.info(f"Found {len(due_schedules)} schedules due to run")

        for schedule in due_schedules:
            try:
                await self._execute_schedule(schedule)
            except Exception as e:
                logger.error(f"Error executing schedule {schedule['id']}: {e}")

    async def _execute_schedule(self, schedule: Dict[str, Any]):
        """Execute a scheduled agent run"""
        from services.agent_framework import get_run_manager

        run_manager = get_run_manager()

        # Create a new run
        run_id = await run_manager.create_run(
            schedule_id=schedule['id'],
            agent_type=schedule['agent_type'],
            config=schedule.get('config_json', {}),
            triggered_by='schedule'
        )

        logger.info(f"Queued run {run_id} for schedule {schedule['schedule_name']}")

        # Update schedule's last run info
        await self._update_schedule_last_run(schedule['id'], run_id)

    async def get_due_schedules(self) -> List[Dict[str, Any]]:
        """
        Get all schedules that are due to run

        Returns:
            List of schedule dictionaries
        """
        async with async_session_maker() as session:
            from sqlalchemy import text

            # Find schedules where next_run_at <= NOW and enabled = true
            query = text("""
                SELECT id, workspace_id, agent_type, topic, schedule_name, description,
                       interval_seconds, cron_expression, next_run_at, last_run_at,
                       last_run_status, config_json
                FROM agent_schedules
                WHERE enabled = true
                  AND next_run_at IS NOT NULL
                  AND next_run_at <= NOW()
                ORDER BY next_run_at ASC
            """)

            result = await session.execute(query)
            rows = result.fetchall()

            schedules = []
            for row in rows:
                schedules.append({
                    'id': str(row[0]),
                    'workspace_id': str(row[1]) if row[1] else None,
                    'agent_type': row[2],
                    'topic': row[3],
                    'schedule_name': row[4],
                    'description': row[5],
                    'interval_seconds': row[6],
                    'cron_expression': row[7],
                    'next_run_at': row[8],
                    'last_run_at': row[9],
                    'last_run_status': row[10],
                    'config_json': row[11]
                })

            return schedules

    async def create_schedule(
        self,
        agent_type: str,
        schedule_name: str,
        description: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        cron_expression: Optional[str] = None,
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> str:
        """
        Create a new agent schedule

        Args:
            agent_type: Type of agent to run (e.g., 'narrative', 'experiments')
            schedule_name: Human-readable name
            description: Optional description
            interval_seconds: Run every N seconds (e.g., 3600 = hourly)
            cron_expression: Cron expression (e.g., '0 9 * * *' = daily at 9am)
            enabled: Whether schedule is active
            config: Agent-specific configuration
            workspace_id: Optional workspace UUID

        Returns:
            Schedule UUID as string
        """
        if not interval_seconds and not cron_expression:
            raise ValueError("Either interval_seconds or cron_expression is required")

        # Calculate initial next_run_at
        if interval_seconds:
            next_run_at = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
        elif cron_expression:
            next_run_at = self._calculate_cron_next_run(cron_expression)
        else:
            next_run_at = None

        async with async_session_maker() as session:
            from sqlalchemy import text

            schedule_id = uuid4()

            query = text("""
                INSERT INTO agent_schedules
                (id, workspace_id, agent_type, schedule_name, description,
                 interval_seconds, cron_expression, next_run_at, enabled, config_json)
                VALUES
                (:id, :workspace_id, :agent_type, :schedule_name, :description,
                 :interval_seconds, :cron_expression, :next_run_at, :enabled, :config_json)
                RETURNING id
            """)

            await session.execute(query, {
                'id': schedule_id,
                'workspace_id': UUID(workspace_id) if workspace_id else None,
                'agent_type': agent_type,
                'schedule_name': schedule_name,
                'description': description,
                'interval_seconds': interval_seconds,
                'cron_expression': cron_expression,
                'next_run_at': next_run_at,
                'enabled': enabled,
                'config_json': config or {}
            })

            await session.commit()

        logger.success(f"Created schedule {schedule_name} ({schedule_id})")
        return str(schedule_id)

    async def update_schedule(
        self,
        schedule_id: str,
        enabled: Optional[bool] = None,
        interval_seconds: Optional[int] = None,
        cron_expression: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an existing schedule

        Args:
            schedule_id: Schedule UUID
            enabled: Enable/disable the schedule
            interval_seconds: New interval
            cron_expression: New cron expression
            config: Updated configuration

        Returns:
            True if updated successfully
        """
        async with async_session_maker() as session:
            from sqlalchemy import text

            updates = []
            params = {'id': UUID(schedule_id)}

            if enabled is not None:
                updates.append("enabled = :enabled")
                params['enabled'] = enabled

            if interval_seconds is not None:
                updates.append("interval_seconds = :interval_seconds")
                params['interval_seconds'] = interval_seconds

                # Recalculate next_run_at
                next_run_at = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
                updates.append("next_run_at = :next_run_at")
                params['next_run_at'] = next_run_at

            if cron_expression is not None:
                updates.append("cron_expression = :cron_expression")
                params['cron_expression'] = cron_expression

                # Recalculate next_run_at
                next_run_at = self._calculate_cron_next_run(cron_expression)
                updates.append("next_run_at = :next_run_at")
                params['next_run_at'] = next_run_at

            if config is not None:
                updates.append("config_json = :config_json")
                params['config_json'] = config

            if not updates:
                return True

            updates.append("updated_at = NOW()")

            query = text(f"""
                UPDATE agent_schedules
                SET {', '.join(updates)}
                WHERE id = :id
                RETURNING id
            """)

            result = await session.execute(query, params)
            await session.commit()

            return result.rowcount > 0

    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule

        Args:
            schedule_id: Schedule UUID

        Returns:
            True if deleted successfully
        """
        async with async_session_maker() as session:
            from sqlalchemy import text

            query = text("""
                DELETE FROM agent_schedules
                WHERE id = :id
                RETURNING id
            """)

            result = await session.execute(query, {'id': UUID(schedule_id)})
            await session.commit()

            return result.rowcount > 0

    async def get_next_run_time(self, schedule_id: str) -> Optional[datetime]:
        """
        Get the next run time for a schedule

        Args:
            schedule_id: Schedule UUID

        Returns:
            Next run time or None if schedule doesn't exist
        """
        async with async_session_maker() as session:
            from sqlalchemy import text

            query = text("""
                SELECT next_run_at
                FROM agent_schedules
                WHERE id = :id
            """)

            result = await session.execute(query, {'id': UUID(schedule_id)})
            row = result.fetchone()

            return row[0] if row else None

    async def _update_schedule_last_run(self, schedule_id: str, run_id: str):
        """Update schedule's last run info"""
        async with async_session_maker() as session:
            from sqlalchemy import text

            query = text("""
                UPDATE agent_schedules
                SET last_run_id = :run_id,
                    updated_at = NOW()
                WHERE id = :id
            """)

            await session.execute(query, {
                'id': UUID(schedule_id),
                'run_id': UUID(run_id)
            })
            await session.commit()

    def _calculate_cron_next_run(self, cron_expression: str) -> datetime:
        """
        Calculate next run time from cron expression

        Args:
            cron_expression: Cron expression (e.g., '0 9 * * *')

        Returns:
            Next run datetime
        """
        try:
            cron = croniter(cron_expression, datetime.now(timezone.utc))
            return cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Invalid cron expression '{cron_expression}': {e}")
            # Default to 1 hour from now
            return datetime.now(timezone.utc) + timedelta(hours=1)


# Singleton accessor
def get_agent_scheduler() -> AgentScheduler:
    """Get the global agent scheduler instance"""
    return AgentScheduler.get_instance()
