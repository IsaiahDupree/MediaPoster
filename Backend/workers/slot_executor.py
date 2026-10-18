"""
Autonomous Slot Executor
========================
Execute scheduled content slots without human intervention.

AUTO-006: Autonomous Slot Executor

This service orchestrates the automatic execution of scheduled slots by:
1. Monitoring upcoming slots from the weekly plan
2. Triggering slot execution at scheduled times
3. Logging execution status and failures
4. Coordinating with SlotExecutorWorker for actual execution

Unlike manual slot execution, this runs autonomously in the background.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from uuid import uuid4
from loguru import logger
from sqlalchemy import create_engine, text
import os

from services.event_bus import EventBus, Topics


class SlotStatus:
    """Slot execution status constants"""
    SCHEDULED = "scheduled"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AutonomousSlotExecutor:
    """
    Autonomous Slot Executor

    Monitors scheduled slots and triggers execution automatically without
    human intervention. Integrates with the SlotExecutorWorker to perform
    the actual generation/QA/publish pipeline.

    Features:
    - Automatic slot execution based on scheduled time
    - Failure logging and retry logic
    - Coordination with event bus for status tracking
    - Grace period before slot time (5 minutes early wake)

    Usage:
        executor = AutonomousSlotExecutor()
        await executor.start()

        # Service runs continuously, checking for due slots
        # Emits events for each execution
    """

    def __init__(self):
        """Initialize autonomous slot executor"""
        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("autonomous-slot-executor")

        # Database connection
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres"
        )
        self.engine = create_engine(self.database_url)

        # Execution tracking
        self._executing_slots: Dict[str, Dict[str, Any]] = {}
        self._failed_slots: Dict[str, List[Dict[str, Any]]] = {}

        # Configuration
        self.check_interval_seconds = 60  # Check every minute
        self.pre_execution_buffer_minutes = 5  # Wake 5 min before slot time
        self.max_retries = 3
        self.retry_delay_minutes = 15

        # Service state
        self._is_running = False
        self._task: Optional[asyncio.Task] = None

        logger.info("🤖 Autonomous Slot Executor initialized")

    async def start(self) -> None:
        """Start the autonomous executor service"""
        if self._is_running:
            logger.warning("Autonomous Slot Executor is already running")
            return

        self._is_running = True
        self._task = asyncio.create_task(self._execution_loop())

        # Emit startup event
        await self.event_bus.publish(
            Topics.SYSTEM_STARTUP,
            {
                "service": "autonomous_slot_executor",
                "check_interval": self.check_interval_seconds,
                "buffer_minutes": self.pre_execution_buffer_minutes
            }
        )

        logger.success("🤖 Autonomous Slot Executor started")

    async def stop(self) -> None:
        """Stop the autonomous executor service"""
        if not self._is_running:
            return

        self._is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("🤖 Autonomous Slot Executor stopped")

    async def _execution_loop(self) -> None:
        """Main execution loop - checks for due slots continuously"""
        logger.info("🔄 Autonomous execution loop started")

        while self._is_running:
            try:
                # Check for slots that need execution
                await self._check_and_execute_slots()

                # Wait for next check interval
                await asyncio.sleep(self.check_interval_seconds)

            except asyncio.CancelledError:
                logger.info("Execution loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in execution loop: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(self.check_interval_seconds)

    async def _check_and_execute_slots(self) -> None:
        """Check for slots that are due for execution"""
        try:
            # Calculate time window for due slots
            now = datetime.now(timezone.utc)
            buffer_time = now + timedelta(minutes=self.pre_execution_buffer_minutes)

            # Query for scheduled slots within the buffer window
            due_slots = await self._get_due_slots(now, buffer_time)

            if due_slots:
                logger.info(f"⏰ Found {len(due_slots)} slot(s) due for execution")

            for slot in due_slots:
                await self._execute_slot(slot)

        except Exception as e:
            logger.error(f"Error checking for due slots: {e}")

    async def _get_due_slots(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Query database for slots scheduled between start_time and end_time.

        Args:
            start_time: Start of time window
            end_time: End of time window

        Returns:
            List of slot dictionaries with slot details
        """
        try:
            with self.engine.connect() as conn:
                # Query for scheduled slots from weekly_plan_slots table
                # (This assumes a table structure exists)
                query = text("""
                    SELECT
                        id,
                        plan_id,
                        slot_date,
                        slot_time,
                        platform,
                        channel,
                        awareness_level,
                        fate_target,
                        cta_strength,
                        target_offer_id,
                        target_icp_id,
                        status,
                        metadata
                    FROM weekly_plan_slots
                    WHERE status = :scheduled_status
                      AND slot_date::timestamp + slot_time::time >= :start_time
                      AND slot_date::timestamp + slot_time::time <= :end_time
                    ORDER BY slot_date, slot_time
                """)

                result = conn.execute(
                    query,
                    {
                        "scheduled_status": SlotStatus.SCHEDULED,
                        "start_time": start_time,
                        "end_time": end_time
                    }
                )

                slots = []
                for row in result:
                    slots.append({
                        "slot_id": str(row.id),
                        "plan_id": str(row.plan_id) if row.plan_id else None,
                        "slot_date": row.slot_date,
                        "slot_time": row.slot_time,
                        "platform": row.platform,
                        "channel": row.channel,
                        "awareness_level": row.awareness_level,
                        "fate_target": row.fate_target,
                        "cta_strength": row.cta_strength,
                        "target_offer_id": str(row.target_offer_id) if row.target_offer_id else None,
                        "target_icp_id": str(row.target_icp_id) if row.target_icp_id else None,
                        "status": row.status,
                        "metadata": row.metadata or {}
                    })

                return slots

        except Exception as e:
            logger.error(f"Error querying due slots: {e}")
            return []

    async def _execute_slot(self, slot: Dict[str, Any]) -> None:
        """
        Execute a single slot by emitting slot.execute.requested event.

        Args:
            slot: Slot dictionary with execution details
        """
        slot_id = slot["slot_id"]

        # Check if already executing
        if slot_id in self._executing_slots:
            logger.warning(f"Slot {slot_id} is already executing, skipping")
            return

        # Check retry count
        retry_count = len(self._failed_slots.get(slot_id, []))
        if retry_count >= self.max_retries:
            logger.error(
                f"Slot {slot_id} has exceeded max retries ({self.max_retries}), "
                "marking as failed"
            )
            await self._mark_slot_failed(slot_id, "Max retries exceeded")
            return

        logger.info(
            f"🚀 Executing slot {slot_id} | "
            f"platform={slot['platform']} | "
            f"awareness={slot['awareness_level']}"
        )

        # Track execution start
        execution_record = {
            "slot_id": slot_id,
            "started_at": datetime.now(timezone.utc),
            "status": SlotStatus.EXECUTING,
            "retry_count": retry_count
        }
        self._executing_slots[slot_id] = execution_record

        try:
            # Update slot status in database
            await self._update_slot_status(slot_id, SlotStatus.EXECUTING)

            # Emit slot execution event (picked up by SlotExecutorWorker)
            correlation_id = str(uuid4())
            await self.event_bus.publish(
                "slot.execute.requested",
                {
                    **slot,
                    "auto_execution": True,
                    "correlation_id": correlation_id,
                    "retry_count": retry_count
                },
                correlation_id=correlation_id
            )

            logger.success(f"✅ Slot execution triggered: {slot_id}")

            # Subscribe to completion events
            await self._subscribe_to_completion(slot_id, correlation_id)

        except Exception as e:
            logger.error(f"❌ Failed to execute slot {slot_id}: {e}")

            # Log failure
            await self._log_slot_failure(slot_id, str(e))

            # Update status
            await self._update_slot_status(slot_id, SlotStatus.FAILED)

            # Remove from executing
            if slot_id in self._executing_slots:
                del self._executing_slots[slot_id]

    async def _subscribe_to_completion(
        self,
        slot_id: str,
        correlation_id: str
    ) -> None:
        """
        Subscribe to slot completion events.

        Args:
            slot_id: Slot identifier
            correlation_id: Execution correlation ID
        """
        # Listen for completion or failure events
        # (Implementation depends on event bus subscription model)
        # For now, we'll use a polling approach to check status

        async def check_completion():
            """Poll for completion status"""
            max_wait_minutes = 30
            check_interval = 30  # Check every 30 seconds
            elapsed = 0

            while elapsed < max_wait_minutes * 60:
                await asyncio.sleep(check_interval)
                elapsed += check_interval

                # Check if slot execution completed
                status = await self._get_slot_status(slot_id)

                if status == SlotStatus.COMPLETED:
                    logger.success(f"✅ Slot {slot_id} completed successfully")
                    if slot_id in self._executing_slots:
                        del self._executing_slots[slot_id]
                    return

                elif status == SlotStatus.FAILED:
                    logger.error(f"❌ Slot {slot_id} execution failed")
                    await self._log_slot_failure(
                        slot_id,
                        "Execution pipeline failed"
                    )
                    if slot_id in self._executing_slots:
                        del self._executing_slots[slot_id]
                    return

            # Timeout
            logger.warning(f"⏰ Slot {slot_id} execution timed out")
            await self._log_slot_failure(slot_id, "Execution timeout")
            if slot_id in self._executing_slots:
                del self._executing_slots[slot_id]

        # Start completion checker in background
        asyncio.create_task(check_completion())

    async def _update_slot_status(self, slot_id: str, status: str) -> None:
        """
        Update slot status in database.

        Args:
            slot_id: Slot identifier
            status: New status value
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    UPDATE weekly_plan_slots
                    SET status = :status,
                        updated_at = :updated_at
                    WHERE id = :slot_id
                """)

                conn.execute(
                    query,
                    {
                        "status": status,
                        "updated_at": datetime.now(timezone.utc),
                        "slot_id": slot_id
                    }
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Error updating slot status: {e}")

    async def _get_slot_status(self, slot_id: str) -> Optional[str]:
        """
        Get current slot status from database.

        Args:
            slot_id: Slot identifier

        Returns:
            Current status string or None if not found
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT status
                    FROM weekly_plan_slots
                    WHERE id = :slot_id
                """)

                result = conn.execute(query, {"slot_id": slot_id})
                row = result.fetchone()

                return row.status if row else None

        except Exception as e:
            logger.error(f"Error getting slot status: {e}")
            return None

    async def _log_slot_failure(self, slot_id: str, error_message: str) -> None:
        """
        Log slot execution failure.

        Args:
            slot_id: Slot identifier
            error_message: Error description
        """
        failure_record = {
            "timestamp": datetime.now(timezone.utc),
            "error": error_message
        }

        if slot_id not in self._failed_slots:
            self._failed_slots[slot_id] = []

        self._failed_slots[slot_id].append(failure_record)

        # Emit failure event
        await self.event_bus.publish(
            "slot.execution.failed",
            {
                "slot_id": slot_id,
                "error": error_message,
                "retry_count": len(self._failed_slots[slot_id]),
                "timestamp": failure_record["timestamp"].isoformat()
            }
        )

        logger.error(
            f"❌ Slot {slot_id} execution failed | "
            f"error={error_message} | "
            f"attempts={len(self._failed_slots[slot_id])}"
        )

    async def _mark_slot_failed(self, slot_id: str, reason: str) -> None:
        """
        Mark slot as permanently failed.

        Args:
            slot_id: Slot identifier
            reason: Failure reason
        """
        await self._update_slot_status(slot_id, SlotStatus.FAILED)
        await self._log_slot_failure(slot_id, f"Permanently failed: {reason}")

    def get_execution_status(self) -> Dict[str, Any]:
        """
        Get current execution status and statistics.

        Returns:
            Dictionary with execution metrics
        """
        return {
            "is_running": self._is_running,
            "executing_slots": len(self._executing_slots),
            "failed_slots": len(self._failed_slots),
            "check_interval_seconds": self.check_interval_seconds,
            "executions": [
                {
                    "slot_id": slot_id,
                    "started_at": execution["started_at"].isoformat(),
                    "status": execution["status"],
                    "retry_count": execution["retry_count"],
                    "duration_seconds": (
                        datetime.now(timezone.utc) - execution["started_at"]
                    ).total_seconds()
                }
                for slot_id, execution in self._executing_slots.items()
            ],
            "failures": {
                slot_id: [
                    {
                        "timestamp": failure["timestamp"].isoformat(),
                        "error": failure["error"]
                    }
                    for failure in failures
                ]
                for slot_id, failures in self._failed_slots.items()
            }
        }


# Global instance
_instance: Optional[AutonomousSlotExecutor] = None


def get_autonomous_slot_executor() -> AutonomousSlotExecutor:
    """Get or create the singleton instance"""
    global _instance
    if _instance is None:
        _instance = AutonomousSlotExecutor()
    return _instance
