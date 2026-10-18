"""
Human Approval Queue (AUTO-005)
================================
Queue system for content requiring human review before publishing.

Features:
- Priority queue with scoring
- Approval/rejection workflow
- Feedback collection
- Automatic retry on rejection
- Analytics and reporting
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import asyncio

from services.event_bus import EventBus, Topics
from database.connection import async_session_maker


class ApprovalStatus(str, Enum):
    """Approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalPriority(str, Enum):
    """Approval priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ApprovalItem:
    """Item in approval queue"""
    id: str = field(default_factory=lambda: str(uuid4()))
    content_id: str = ""
    content_type: str = ""  # "post", "video", "comment", "dm"
    content_data: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    priority: ApprovalPriority = ApprovalPriority.MEDIUM
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    feedback: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # AI scores to help reviewers
    quality_score: float = 0.0
    engagement_prediction: float = 0.0
    brand_safety_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "content_id": self.content_id,
            "content_type": self.content_type,
            "content_data": self.content_data,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "assigned_to": self.assigned_to,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "feedback": self.feedback,
            "quality_score": self.quality_score,
            "engagement_prediction": self.engagement_prediction,
            "brand_safety_score": self.brand_safety_score,
            "metadata": self.metadata
        }


class ApprovalQueue:
    """
    Human Approval Queue (AUTO-005)

    Manages content requiring human review before automated actions.

    Usage:
        queue = ApprovalQueue()
        await queue.start()

        # Add item to queue
        item_id = await queue.add_item(
            content_id="post-123",
            content_type="post",
            content_data={"text": "My post", "platform": "tiktok"},
            priority=ApprovalPriority.HIGH,
            quality_score=0.85
        )

        # Review item
        await queue.approve_item(
            item_id=item_id,
            reviewed_by="user@example.com",
            feedback="Looks great!"
        )

        # Or reject
        await queue.reject_item(
            item_id=item_id,
            reviewed_by="user@example.com",
            feedback="Needs better hook"
        )
    """

    # Singleton instance
    _instance: Optional["ApprovalQueue"] = None

    def __init__(self):
        """Initialize Approval Queue"""
        self.queue: Dict[str, ApprovalItem] = {}
        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("approval-queue")
        self._is_running = False
        self._cleanup_task = None

        logger.info("✅ Approval Queue initialized")

    @classmethod
    def get_instance(cls) -> "ApprovalQueue":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self):
        """Start the approval queue service"""
        if self._is_running:
            logger.warning("Approval Queue already running")
            return

        self._is_running = True

        # Start cleanup task (runs every hour)
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Emit event
        await self.event_bus.publish(
            Topics.WORKER_STARTED,
            {
                "worker": "approval-queue",
                "status": "started"
            }
        )

        logger.success("✓ Approval Queue started")

    async def stop(self):
        """Stop the approval queue service"""
        if not self._is_running:
            return

        self._is_running = False

        # Stop cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Emit event
        await self.event_bus.publish(
            Topics.WORKER_STOPPED,
            {
                "worker": "approval-queue",
                "status": "stopped"
            }
        )

        logger.success("✓ Approval Queue stopped")

    async def add_item(
        self,
        content_id: str,
        content_type: str,
        content_data: Dict[str, Any],
        priority: ApprovalPriority = ApprovalPriority.MEDIUM,
        quality_score: float = 0.0,
        engagement_prediction: float = 0.0,
        brand_safety_score: float = 0.0,
        expires_in_hours: Optional[int] = 24,
        assigned_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add item to approval queue

        Args:
            content_id: ID of content to approve
            content_type: Type of content (post, video, comment, dm)
            content_data: Content data (text, media, etc.)
            priority: Priority level
            quality_score: AI quality score (0-1)
            engagement_prediction: Predicted engagement (0-1)
            brand_safety_score: Brand safety score (0-1)
            expires_in_hours: Hours until item expires (None = no expiry)
            assigned_to: Optional user to assign to
            metadata: Optional additional metadata

        Returns:
            Item ID
        """
        # Calculate expiry time
        expires_at = None
        if expires_in_hours is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        # Create item
        item = ApprovalItem(
            content_id=content_id,
            content_type=content_type,
            content_data=content_data,
            priority=priority,
            quality_score=quality_score,
            engagement_prediction=engagement_prediction,
            brand_safety_score=brand_safety_score,
            expires_at=expires_at,
            assigned_to=assigned_to,
            metadata=metadata or {}
        )

        # Add to queue
        self.queue[item.id] = item

        # Emit event
        await self.event_bus.publish(
            "approval.item.added",
            {
                "item_id": item.id,
                "content_id": content_id,
                "content_type": content_type,
                "priority": priority.value,
                "quality_score": quality_score,
                "expires_at": expires_at.isoformat() if expires_at else None
            }
        )

        logger.info(f"Added item to approval queue: {item.id} (content={content_id}, priority={priority.value})")

        return item.id

    async def approve_item(
        self,
        item_id: str,
        reviewed_by: str,
        feedback: str = ""
    ) -> bool:
        """
        Approve an item

        Args:
            item_id: Item ID
            reviewed_by: Reviewer identifier (user ID or email)
            feedback: Optional feedback

        Returns:
            True if approved, False if item not found
        """
        if item_id not in self.queue:
            logger.warning(f"Approval item not found: {item_id}")
            return False

        item = self.queue[item_id]

        # Update item
        item.status = ApprovalStatus.APPROVED
        item.reviewed_by = reviewed_by
        item.reviewed_at = datetime.now(timezone.utc)
        item.feedback = feedback

        # Emit event
        await self.event_bus.publish(
            "approval.item.approved",
            {
                "item_id": item_id,
                "content_id": item.content_id,
                "content_type": item.content_type,
                "reviewed_by": reviewed_by,
                "feedback": feedback,
                "quality_score": item.quality_score
            }
        )

        logger.success(f"✓ Approved item: {item_id} by {reviewed_by}")

        return True

    async def reject_item(
        self,
        item_id: str,
        reviewed_by: str,
        feedback: str = "",
        allow_retry: bool = True
    ) -> bool:
        """
        Reject an item

        Args:
            item_id: Item ID
            reviewed_by: Reviewer identifier
            feedback: Rejection reason
            allow_retry: Whether to allow retry after rejection

        Returns:
            True if rejected, False if item not found
        """
        if item_id not in self.queue:
            logger.warning(f"Approval item not found: {item_id}")
            return False

        item = self.queue[item_id]

        # Update item
        item.status = ApprovalStatus.REJECTED
        item.reviewed_by = reviewed_by
        item.reviewed_at = datetime.now(timezone.utc)
        item.feedback = feedback

        # Emit event
        await self.event_bus.publish(
            "approval.item.rejected",
            {
                "item_id": item_id,
                "content_id": item.content_id,
                "content_type": item.content_type,
                "reviewed_by": reviewed_by,
                "feedback": feedback,
                "allow_retry": allow_retry
            }
        )

        logger.info(f"Rejected item: {item_id} by {reviewed_by} (reason: {feedback[:50]})")

        return True

    async def get_pending_items(
        self,
        priority: Optional[ApprovalPriority] = None,
        content_type: Optional[str] = None,
        assigned_to: Optional[str] = None,
        limit: int = 50
    ) -> List[ApprovalItem]:
        """
        Get pending items from queue

        Args:
            priority: Filter by priority
            content_type: Filter by content type
            assigned_to: Filter by assignee
            limit: Maximum items to return

        Returns:
            List of pending items, sorted by priority and creation time
        """
        # Filter items
        items = [
            item for item in self.queue.values()
            if item.status == ApprovalStatus.PENDING
        ]

        # Apply filters
        if priority:
            items = [item for item in items if item.priority == priority]

        if content_type:
            items = [item for item in items if item.content_type == content_type]

        if assigned_to:
            items = [item for item in items if item.assigned_to == assigned_to]

        # Sort by priority (urgent > high > medium > low) and creation time
        priority_order = {
            ApprovalPriority.URGENT: 0,
            ApprovalPriority.HIGH: 1,
            ApprovalPriority.MEDIUM: 2,
            ApprovalPriority.LOW: 3
        }

        items.sort(
            key=lambda x: (priority_order[x.priority], x.created_at)
        )

        return items[:limit]

    async def get_item(self, item_id: str) -> Optional[ApprovalItem]:
        """Get a specific item by ID"""
        return self.queue.get(item_id)

    async def assign_item(
        self,
        item_id: str,
        assigned_to: str
    ) -> bool:
        """
        Assign an item to a reviewer

        Args:
            item_id: Item ID
            assigned_to: User ID or email to assign to

        Returns:
            True if assigned, False if item not found
        """
        if item_id not in self.queue:
            return False

        item = self.queue[item_id]
        item.assigned_to = assigned_to

        logger.info(f"Assigned item {item_id} to {assigned_to}")

        return True

    async def remove_item(self, item_id: str) -> bool:
        """Remove an item from the queue"""
        if item_id in self.queue:
            del self.queue[item_id]
            logger.debug(f"Removed item from queue: {item_id}")
            return True
        return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        total_items = len(self.queue)

        pending = sum(1 for item in self.queue.values() if item.status == ApprovalStatus.PENDING)
        approved = sum(1 for item in self.queue.values() if item.status == ApprovalStatus.APPROVED)
        rejected = sum(1 for item in self.queue.values() if item.status == ApprovalStatus.REJECTED)
        expired = sum(1 for item in self.queue.values() if item.status == ApprovalStatus.EXPIRED)

        # Priority breakdown
        urgent = sum(1 for item in self.queue.values() if item.priority == ApprovalPriority.URGENT and item.status == ApprovalStatus.PENDING)
        high = sum(1 for item in self.queue.values() if item.priority == ApprovalPriority.HIGH and item.status == ApprovalStatus.PENDING)

        # Average scores for pending items
        pending_items = [item for item in self.queue.values() if item.status == ApprovalStatus.PENDING]
        avg_quality = sum(item.quality_score for item in pending_items) / len(pending_items) if pending_items else 0.0
        avg_engagement = sum(item.engagement_prediction for item in pending_items) / len(pending_items) if pending_items else 0.0

        return {
            "total_items": total_items,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "expired": expired,
            "pending_urgent": urgent,
            "pending_high": high,
            "average_quality_score": round(avg_quality, 3),
            "average_engagement_prediction": round(avg_engagement, 3),
            "is_running": self._is_running
        }

    async def _cleanup_loop(self):
        """Background task to clean up expired items"""
        while self._is_running:
            try:
                await self._cleanup_expired_items()
                await asyncio.sleep(3600)  # Run every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Brief pause on error

    async def _cleanup_expired_items(self):
        """Mark expired items and emit events"""
        now = datetime.now(timezone.utc)
        expired_count = 0

        for item in list(self.queue.values()):
            if (
                item.status == ApprovalStatus.PENDING
                and item.expires_at
                and now >= item.expires_at
            ):
                item.status = ApprovalStatus.EXPIRED
                expired_count += 1

                # Emit event
                await self.event_bus.publish(
                    "approval.item.expired",
                    {
                        "item_id": item.id,
                        "content_id": item.content_id,
                        "content_type": item.content_type
                    }
                )

        if expired_count > 0:
            logger.info(f"Marked {expired_count} items as expired")


# Singleton accessor
def get_approval_queue() -> ApprovalQueue:
    """Get the global Approval Queue instance"""
    return ApprovalQueue.get_instance()
