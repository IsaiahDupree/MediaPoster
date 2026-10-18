"""
Automation Registry Service (BM-007)
=====================================
Database-backed registry for tracking all system automations, their schedules,
resource requirements, and execution history.

This service provides:
- CRUD operations for automations
- Status tracking and metrics
- Schedule management
- Resource requirement tracking
- Run history and analytics

Usage:
    registry = AutomationRegistry.get_instance()

    # Register a new automation
    automation_id = await registry.register_automation(
        name="Post Scheduler",
        automation_type="post_scheduler",
        schedule_type="interval",
        schedule_config={"interval_seconds": 60},
        resource_requirements={"cpu": "low", "memory": "low"}
    )

    # Start a run
    run_id = await registry.start_run(automation_id, triggered_by="schedule")

    # Complete the run
    await registry.complete_run(run_id, status="success")
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from loguru import logger
from enum import Enum

from database.connection import async_session_maker
from sqlalchemy import text, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession


class AutomationStatus(Enum):
    """Automation status states"""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"


class AutomationType(Enum):
    """Types of automations"""
    POST_SCHEDULER = "post_scheduler"
    SAFARI_AUTOMATION = "safari_automation"
    METRICS_FETCHER = "metrics_fetcher"
    WORKER = "worker"
    CUSTOM = "custom"


class ScheduleType(Enum):
    """Schedule types"""
    CRON = "cron"
    INTERVAL = "interval"
    ONE_TIME = "one_time"
    EVENT_DRIVEN = "event_driven"
    NONE = None


class RunStatus(Enum):
    """Run status states"""
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AutomationRegistry:
    """
    Automation Registry Service

    Manages the registry of all system automations with scheduling,
    resource tracking, and execution history.
    """

    _instance: Optional["AutomationRegistry"] = None

    def __init__(self):
        """Initialize automation registry"""
        if AutomationRegistry._instance is not None:
            raise RuntimeError("Use AutomationRegistry.get_instance()")

        logger.info("📋 Automation Registry initialized")

    @classmethod
    def get_instance(cls) -> "AutomationRegistry":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def register_automation(
        self,
        name: str,
        automation_type: str,
        description: Optional[str] = None,
        schedule_type: Optional[str] = None,
        schedule_config: Optional[Dict[str, Any]] = None,
        resource_requirements: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        max_concurrent_runs: int = 1,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> str:
        """
        Register a new automation

        Args:
            name: Human-readable name
            automation_type: Type of automation
            description: Optional description
            schedule_type: How the automation is scheduled
            schedule_config: Schedule configuration (cron, interval, etc.)
            resource_requirements: Resource needs (cpu, memory, etc.)
            config: Automation-specific configuration
            priority: Priority level (1-10, higher = more important)
            max_concurrent_runs: Maximum concurrent runs allowed
            tags: Optional tags for categorization
            created_by: Who created this automation

        Returns:
            Automation ID (UUID)
        """
        async with async_session_maker() as session:
            automation_id = str(uuid4())

            query = text("""
                INSERT INTO automations (
                    id, name, description, automation_type, status,
                    schedule_type, schedule_config, resource_requirements,
                    config, priority, max_concurrent_runs, tags, created_by
                ) VALUES (
                    :id, :name, :description, :automation_type, :status,
                    :schedule_type, :schedule_config, :resource_requirements,
                    :config, :priority, :max_concurrent_runs, :tags, :created_by
                )
            """)

            await session.execute(query, {
                "id": automation_id,
                "name": name,
                "description": description,
                "automation_type": automation_type,
                "status": AutomationStatus.ACTIVE.value,
                "schedule_type": schedule_type,
                "schedule_config": schedule_config,
                "resource_requirements": resource_requirements or {},
                "config": config or {},
                "priority": priority,
                "max_concurrent_runs": max_concurrent_runs,
                "tags": tags or [],
                "created_by": created_by
            })

            await session.commit()

            logger.info(f"✓ Automation registered: {name} ({automation_id[:8]})")
            return automation_id

    async def get_automation(self, automation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get automation by ID

        Args:
            automation_id: Automation UUID

        Returns:
            Automation dictionary or None if not found
        """
        async with async_session_maker() as session:
            query = text("SELECT * FROM automations WHERE id = :id")
            result = await session.execute(query, {"id": automation_id})
            row = result.fetchone()

            if not row:
                return None

            return dict(row._mapping)

    async def list_automations(
        self,
        status: Optional[str] = None,
        automation_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all automations with optional filters

        Args:
            status: Filter by status
            automation_type: Filter by type
            tags: Filter by tags (any match)
            enabled_only: Only return enabled automations

        Returns:
            List of automation dictionaries
        """
        async with async_session_maker() as session:
            conditions = []
            params = {}

            if status:
                conditions.append("status = :status")
                params["status"] = status

            if automation_type:
                conditions.append("automation_type = :automation_type")
                params["automation_type"] = automation_type

            if enabled_only:
                conditions.append("enabled = true")

            if tags:
                conditions.append("tags && :tags")
                params["tags"] = tags

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = text(f"""
                SELECT * FROM automations
                WHERE {where_clause}
                ORDER BY priority DESC, name ASC
            """)

            result = await session.execute(query, params)
            rows = result.fetchall()

            return [dict(row._mapping) for row in rows]

    async def update_automation(
        self,
        automation_id: str,
        **updates
    ) -> bool:
        """
        Update automation fields

        Args:
            automation_id: Automation UUID
            **updates: Fields to update

        Returns:
            True if updated, False if not found
        """
        if not updates:
            return False

        async with async_session_maker() as session:
            # Build update query
            set_clauses = []
            params = {"id": automation_id}

            for key, value in updates.items():
                set_clauses.append(f"{key} = :{key}")
                params[key] = value

            set_clauses.append("updated_at = NOW()")

            query = text(f"""
                UPDATE automations
                SET {", ".join(set_clauses)}
                WHERE id = :id
            """)

            result = await session.execute(query, params)
            await session.commit()

            if result.rowcount == 0:
                return False

            logger.info(f"✓ Automation updated: {automation_id[:8]}")
            return True

    async def delete_automation(self, automation_id: str) -> bool:
        """
        Delete automation (cascades to runs)

        Args:
            automation_id: Automation UUID

        Returns:
            True if deleted, False if not found
        """
        async with async_session_maker() as session:
            query = text("DELETE FROM automations WHERE id = :id")
            result = await session.execute(query, {"id": automation_id})
            await session.commit()

            if result.rowcount == 0:
                return False

            logger.info(f"🗑️ Automation deleted: {automation_id[:8]}")
            return True

    async def start_run(
        self,
        automation_id: str,
        triggered_by: str = "system",
        trigger_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Start a new automation run

        Args:
            automation_id: Automation UUID
            triggered_by: What triggered the run
            trigger_metadata: Additional trigger context

        Returns:
            Run ID (UUID) or None if automation doesn't exist or can't start
        """
        async with async_session_maker() as session:
            # Check automation exists and can run
            check_query = text("""
                SELECT enabled, max_concurrent_runs, current_runs
                FROM automations
                WHERE id = :id
            """)
            result = await session.execute(check_query, {"id": automation_id})
            row = result.fetchone()

            if not row:
                logger.warning(f"Automation not found: {automation_id[:8]}")
                return None

            if not row.enabled:
                logger.warning(f"Automation disabled: {automation_id[:8]}")
                return None

            if row.current_runs >= row.max_concurrent_runs:
                logger.warning(
                    f"Max concurrent runs reached for {automation_id[:8]}: "
                    f"{row.current_runs}/{row.max_concurrent_runs}"
                )
                return None

            # Create run
            run_id = str(uuid4())

            insert_query = text("""
                INSERT INTO automation_runs (
                    id, automation_id, status, triggered_by, trigger_metadata
                ) VALUES (
                    :id, :automation_id, :status, :triggered_by, :trigger_metadata
                )
            """)

            await session.execute(insert_query, {
                "id": run_id,
                "automation_id": automation_id,
                "status": RunStatus.RUNNING.value,
                "triggered_by": triggered_by,
                "trigger_metadata": trigger_metadata or {}
            })

            await session.commit()

            logger.info(f"▶️ Run started: {run_id[:8]} (automation: {automation_id[:8]})")
            return run_id

    async def complete_run(
        self,
        run_id: str,
        status: str,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        logs: Optional[str] = None
    ) -> bool:
        """
        Complete an automation run

        Args:
            run_id: Run UUID
            status: Final status (success, failure, timeout, cancelled)
            error_message: Error message if failed
            result_data: Result data from the automation
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage in MB
            logs: Execution logs

        Returns:
            True if completed, False if not found
        """
        async with async_session_maker() as session:
            # Calculate duration
            duration_query = text("""
                SELECT EXTRACT(EPOCH FROM (NOW() - started_at)) as duration
                FROM automation_runs
                WHERE id = :id
            """)
            result = await session.execute(duration_query, {"id": run_id})
            row = result.fetchone()

            if not row:
                return False

            duration = row.duration

            # Update run
            update_query = text("""
                UPDATE automation_runs
                SET
                    completed_at = NOW(),
                    duration_seconds = :duration,
                    status = :status,
                    error_message = :error_message,
                    result_data = :result_data,
                    cpu_usage_percent = :cpu_usage,
                    memory_usage_mb = :memory_usage,
                    logs = :logs
                WHERE id = :id
            """)

            await session.execute(update_query, {
                "id": run_id,
                "duration": duration,
                "status": status,
                "error_message": error_message,
                "result_data": result_data or {},
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "logs": logs
            })

            await session.commit()

            logger.info(
                f"✓ Run completed: {run_id[:8]} | "
                f"Status: {status} | Duration: {duration:.1f}s"
            )
            return True

    async def get_run_history(
        self,
        automation_id: str,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get run history for an automation

        Args:
            automation_id: Automation UUID
            limit: Maximum number of runs to return
            status: Filter by status

        Returns:
            List of run dictionaries
        """
        async with async_session_maker() as session:
            conditions = ["automation_id = :automation_id"]
            params = {"automation_id": automation_id, "limit": limit}

            if status:
                conditions.append("status = :status")
                params["status"] = status

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT * FROM automation_runs
                WHERE {where_clause}
                ORDER BY started_at DESC
                LIMIT :limit
            """)

            result = await session.execute(query, params)
            rows = result.fetchall()

            return [dict(row._mapping) for row in rows]

    async def get_active_runs(self) -> List[Dict[str, Any]]:
        """
        Get all currently running automations

        Returns:
            List of active run dictionaries
        """
        async with async_session_maker() as session:
            query = text("""
                SELECT ar.*, a.name as automation_name
                FROM automation_runs ar
                JOIN automations a ON ar.automation_id = a.id
                WHERE ar.status = 'running'
                ORDER BY ar.started_at ASC
            """)

            result = await session.execute(query)
            rows = result.fetchall()

            return [dict(row._mapping) for row in rows]

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get overall automation registry statistics

        Returns:
            Statistics dictionary with counts and metrics
        """
        async with async_session_maker() as session:
            # Automation counts
            automation_query = text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'active') as active,
                    COUNT(*) FILTER (WHERE status = 'paused') as paused,
                    COUNT(*) FILTER (WHERE status = 'disabled') as disabled,
                    COUNT(*) FILTER (WHERE status = 'error') as error,
                    SUM(current_runs) as total_running
                FROM automations
            """)
            automation_result = await session.execute(automation_query)
            automation_stats = dict(automation_result.fetchone()._mapping)

            # Run stats (last 24 hours)
            run_query = text("""
                SELECT
                    COUNT(*) as total_runs_24h,
                    COUNT(*) FILTER (WHERE status = 'success') as successful_runs_24h,
                    COUNT(*) FILTER (WHERE status = 'failure') as failed_runs_24h,
                    AVG(duration_seconds) as avg_duration_24h
                FROM automation_runs
                WHERE started_at >= NOW() - INTERVAL '24 hours'
            """)
            run_result = await session.execute(run_query)
            run_stats = dict(run_result.fetchone()._mapping)

            return {
                "automations": automation_stats,
                "runs_24h": run_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Singleton accessor
def get_automation_registry() -> AutomationRegistry:
    """Get the singleton automation registry instance"""
    return AutomationRegistry.get_instance()
