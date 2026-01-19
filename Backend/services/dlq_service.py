"""
Dead Letter Queue Service (OPS-020)
====================================
Queue for failed jobs that need retry or investigation.

When a job fails after max retries:
- Store in DLQ with error details
- Track retry attempts
- Support manual retry
- Alert on persistent failures
"""

import asyncio
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass, field
from uuid import uuid4
from loguru import logger

from services.event_bus import EventBus


class DLQReason(Enum):
    """Reasons for job being in DLQ"""
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    FATAL_ERROR = "fatal_error"
    RATE_LIMIT_EXHAUSTED = "rate_limit_exhausted"
    INVALID_INPUT = "invalid_input"
    EXTERNAL_SERVICE_FAILURE = "external_service_failure"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class DLQStatus(Enum):
    """Status of DLQ items"""
    PENDING = "pending"  # Waiting for investigation
    INVESTIGATING = "investigating"  # Being looked at
    RETRYING = "retrying"  # Manual retry in progress
    RESOLVED = "resolved"  # Successfully retried
    ABANDONED = "abandoned"  # Given up on this job


@dataclass
class DLQItem:
    """Dead letter queue item"""
    dlq_id: str
    job_id: str
    job_type: str
    payload: Dict[str, Any]
    error_message: str
    error_trace: Optional[str]
    reason: DLQReason
    retry_count: int
    created_at: datetime
    updated_at: datetime
    status: DLQStatus = DLQStatus.PENDING
    resolved_at: Optional[datetime] = None
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "dlq_id": self.dlq_id,
            "job_id": self.job_id,
            "job_type": self.job_type,
            "payload": self.payload,
            "error_message": self.error_message,
            "error_trace": self.error_trace,
            "reason": self.reason.value,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "notes": self.notes
        }


class DeadLetterQueueService:
    """
    Dead Letter Queue Service.

    Stores failed jobs for investigation and manual retry.
    """

    _instance: Optional["DeadLetterQueueService"] = None

    def __init__(self, event_bus: Optional[EventBus] = None):
        if DeadLetterQueueService._instance is not None:
            raise RuntimeError("Use DeadLetterQueueService.get_instance()")

        self.event_bus = event_bus or EventBus.get_instance()

        # DLQ items: {dlq_id -> DLQItem}
        self._items: Dict[str, DLQItem] = {}

        # Job ID to DLQ ID mapping for quick lookups
        self._job_to_dlq: Dict[str, str] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info("✓ Dead Letter Queue Service initialized")

    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None) -> "DeadLetterQueueService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls(event_bus)
        return cls._instance

    async def add_failed_job(
        self,
        job_id: str,
        job_type: str,
        payload: Dict[str, Any],
        error_message: str,
        error_trace: Optional[str] = None,
        reason: DLQReason = DLQReason.UNKNOWN,
        retry_count: int = 0
    ) -> str:
        """
        Add a failed job to the DLQ.

        Args:
            job_id: Original job identifier
            job_type: Type of job (e.g., "publish_post", "send_dm")
            payload: Job payload/parameters
            error_message: Error message
            error_trace: Full error traceback
            reason: Reason for failure
            retry_count: Number of retries attempted

        Returns:
            DLQ ID
        """
        async with self._lock:
            dlq_id = str(uuid4())
            now = datetime.now(timezone.utc)

            item = DLQItem(
                dlq_id=dlq_id,
                job_id=job_id,
                job_type=job_type,
                payload=payload,
                error_message=error_message,
                error_trace=error_trace,
                reason=reason,
                retry_count=retry_count,
                created_at=now,
                updated_at=now
            )

            self._items[dlq_id] = item
            self._job_to_dlq[job_id] = dlq_id

            logger.error(
                f"📥 Job added to DLQ: {job_type}/{job_id} "
                f"(reason={reason.value}, retries={retry_count})"
            )

            # Publish event
            await self.event_bus.publish(
                "dlq.item.added",
                {
                    "dlq_id": dlq_id,
                    "job_id": job_id,
                    "job_type": job_type,
                    "reason": reason.value,
                    "retry_count": retry_count,
                    "error_message": error_message
                },
                source="dlq-service"
            )

            # Alert on high-priority failures
            if reason in [DLQReason.FATAL_ERROR, DLQReason.INVALID_INPUT]:
                await self.event_bus.publish(
                    "dlq.alert",
                    {
                        "dlq_id": dlq_id,
                        "job_type": job_type,
                        "reason": reason.value,
                        "priority": "high"
                    },
                    source="dlq-service"
                )

            return dlq_id

    async def get_item(self, dlq_id: str) -> Optional[DLQItem]:
        """
        Get DLQ item by ID.

        Args:
            dlq_id: DLQ item identifier

        Returns:
            DLQItem or None if not found
        """
        async with self._lock:
            return self._items.get(dlq_id)

    async def get_item_by_job_id(self, job_id: str) -> Optional[DLQItem]:
        """
        Get DLQ item by original job ID.

        Args:
            job_id: Original job identifier

        Returns:
            DLQItem or None if not found
        """
        async with self._lock:
            dlq_id = self._job_to_dlq.get(job_id)
            if dlq_id:
                return self._items.get(dlq_id)
            return None

    async def list_items(
        self,
        status: Optional[DLQStatus] = None,
        reason: Optional[DLQReason] = None,
        job_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DLQItem]:
        """
        List DLQ items with optional filters.

        Args:
            status: Filter by status
            reason: Filter by failure reason
            job_type: Filter by job type
            limit: Maximum items to return
            offset: Number of items to skip

        Returns:
            List of DLQItem objects
        """
        async with self._lock:
            items = list(self._items.values())

            # Apply filters
            if status:
                items = [item for item in items if item.status == status]
            if reason:
                items = [item for item in items if item.reason == reason]
            if job_type:
                items = [item for item in items if item.job_type == job_type]

            # Sort by created_at descending (newest first)
            items.sort(key=lambda x: x.created_at, reverse=True)

            # Apply pagination
            return items[offset:offset + limit]

    async def update_status(
        self,
        dlq_id: str,
        status: DLQStatus,
        notes: str = ""
    ) -> bool:
        """
        Update DLQ item status.

        Args:
            dlq_id: DLQ item identifier
            status: New status
            notes: Optional notes about status change

        Returns:
            True if updated, False if not found
        """
        async with self._lock:
            item = self._items.get(dlq_id)
            if not item:
                return False

            old_status = item.status
            item.status = status
            item.updated_at = datetime.now(timezone.utc)

            if notes:
                item.notes = f"{item.notes}\n[{datetime.now(timezone.utc).isoformat()}] {notes}"

            if status == DLQStatus.RESOLVED:
                item.resolved_at = datetime.now(timezone.utc)

            logger.info(
                f"📝 DLQ item status updated: {dlq_id} "
                f"({old_status.value} → {status.value})"
            )

            # Publish event
            await self.event_bus.publish(
                "dlq.item.updated",
                {
                    "dlq_id": dlq_id,
                    "old_status": old_status.value,
                    "new_status": status.value,
                    "notes": notes
                },
                source="dlq-service"
            )

            return True

    async def retry_item(self, dlq_id: str) -> Dict:
        """
        Attempt to retry a DLQ item.

        Marks item as retrying and returns job details for re-execution.

        Args:
            dlq_id: DLQ item identifier

        Returns:
            Dictionary with job details
        """
        async with self._lock:
            item = self._items.get(dlq_id)
            if not item:
                raise ValueError(f"DLQ item not found: {dlq_id}")

            if item.status == DLQStatus.RESOLVED:
                raise ValueError(f"DLQ item already resolved: {dlq_id}")

            # Mark as retrying
            item.status = DLQStatus.RETRYING
            item.retry_count += 1
            item.updated_at = datetime.now(timezone.utc)

            logger.info(
                f"🔄 Retrying DLQ item: {dlq_id} "
                f"(job_type={item.job_type}, attempt={item.retry_count})"
            )

            # Publish event
            await self.event_bus.publish(
                "dlq.item.retrying",
                {
                    "dlq_id": dlq_id,
                    "job_id": item.job_id,
                    "job_type": item.job_type,
                    "retry_count": item.retry_count
                },
                source="dlq-service"
            )

            return {
                "dlq_id": dlq_id,
                "job_id": item.job_id,
                "job_type": item.job_type,
                "payload": item.payload,
                "retry_count": item.retry_count
            }

    async def mark_resolved(
        self,
        dlq_id: str,
        notes: str = "Successfully retried"
    ) -> bool:
        """
        Mark DLQ item as resolved.

        Args:
            dlq_id: DLQ item identifier
            notes: Resolution notes

        Returns:
            True if marked resolved, False if not found
        """
        return await self.update_status(dlq_id, DLQStatus.RESOLVED, notes)

    async def mark_abandoned(
        self,
        dlq_id: str,
        notes: str = "Abandoned after investigation"
    ) -> bool:
        """
        Mark DLQ item as abandoned (give up).

        Args:
            dlq_id: DLQ item identifier
            notes: Abandonment reason

        Returns:
            True if marked abandoned, False if not found
        """
        return await self.update_status(dlq_id, DLQStatus.ABANDONED, notes)

    async def get_stats(self) -> Dict:
        """
        Get DLQ statistics.

        Returns:
            Dictionary with stats
        """
        async with self._lock:
            stats = {
                "total": len(self._items),
                "by_status": {status.value: 0 for status in DLQStatus},
                "by_reason": {reason.value: 0 for reason in DLQReason},
                "by_job_type": {},
                "oldest_item": None,
                "newest_item": None
            }

            if not self._items:
                return stats

            items = list(self._items.values())

            # Count by status
            for item in items:
                stats["by_status"][item.status.value] += 1

            # Count by reason
            for item in items:
                stats["by_reason"][item.reason.value] += 1

            # Count by job type
            for item in items:
                stats["by_job_type"][item.job_type] = stats["by_job_type"].get(item.job_type, 0) + 1

            # Find oldest and newest
            sorted_items = sorted(items, key=lambda x: x.created_at)
            stats["oldest_item"] = {
                "dlq_id": sorted_items[0].dlq_id,
                "created_at": sorted_items[0].created_at.isoformat(),
                "job_type": sorted_items[0].job_type
            }
            stats["newest_item"] = {
                "dlq_id": sorted_items[-1].dlq_id,
                "created_at": sorted_items[-1].created_at.isoformat(),
                "job_type": sorted_items[-1].job_type
            }

            return stats

    async def cleanup_resolved(self, older_than_days: int = 30) -> int:
        """
        Remove resolved items older than specified days.

        Args:
            older_than_days: Remove items resolved this many days ago

        Returns:
            Number of items removed
        """
        async with self._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            removed_count = 0

            # Find items to remove
            to_remove = []
            for dlq_id, item in self._items.items():
                if item.status == DLQStatus.RESOLVED and item.resolved_at and item.resolved_at < cutoff:
                    to_remove.append(dlq_id)

            # Remove items
            for dlq_id in to_remove:
                item = self._items[dlq_id]
                del self._items[dlq_id]
                if item.job_id in self._job_to_dlq:
                    del self._job_to_dlq[item.job_id]
                removed_count += 1

            if removed_count > 0:
                logger.info(f"🧹 Cleaned up {removed_count} resolved DLQ items older than {older_than_days} days")

            return removed_count
