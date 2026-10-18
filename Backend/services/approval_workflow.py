"""
Approval Workflow Service (HITL-001)
====================================
Human-in-the-Loop approval gate for the Master Orchestrator pipeline.

Wraps the existing ApprovalQueue with EventBus integration so the orchestrator
can optionally require human approval before publishing.

Behaviour:
    - Disabled by default (no approval required).
    - When enabled for a pipeline/automation, PUBLISH_REQUESTED events are
      intercepted and held in the ApprovalQueue until a human approves or
      rejects the content.
    - On approval the original PUBLISH_REQUESTED event is re-emitted to
      continue the publishing pipeline.
    - On rejection a ``publish.rejected`` event is emitted.
    - An auto-approval timeout (default 5 days) automatically approves items
      that have not been reviewed within the window.

Acceptance criteria (feature_list.json):
    - Toggle approval on/off per automation
    - Approval queue in database
    - Approval status tracking
    - Disabled by default
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

from services.event_bus import EventBus, Event, Topics
from services.approval_queue import (
    ApprovalQueue,
    ApprovalItem,
    ApprovalStatus,
    ApprovalPriority,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default auto-approval timeout in seconds (5 days)
DEFAULT_AUTO_APPROVAL_TIMEOUT_SECONDS = 5 * 24 * 60 * 60  # 432 000 s

# Topic strings for approval-specific events
TOPIC_APPROVAL_SUBMITTED = "approval.submitted"
TOPIC_APPROVAL_APPROVED = "approval.approved"
TOPIC_APPROVAL_REJECTED = "publish.rejected"
TOPIC_APPROVAL_AUTO_APPROVED = "approval.auto_approved"


class ApprovalWorkflow:
    """
    Orchestrator-aware approval gate (HITL-001).

    The service sits between the Master Orchestrator's publish step and the
    actual publishing workers.  When approval is enabled for a given
    automation key, it intercepts ``PUBLISH_REQUESTED`` events, parks them in
    the :class:`ApprovalQueue`, and waits for a human decision.

    Usage::

        workflow = ApprovalWorkflow.get_instance()
        await workflow.start()

        # Enable approval for a specific automation / pipeline
        workflow.enable_approval("tiktok")

        # Or enable globally
        workflow.enable_approval("*")

        # Later, approve a queued item
        await workflow.approve("item-id-123", reviewed_by="admin@example.com")

    Singleton access::

        workflow = get_approval_workflow()
    """

    # Singleton -----------------------------------------------------------------
    _instance: Optional["ApprovalWorkflow"] = None

    @classmethod
    def get_instance(cls) -> "ApprovalWorkflow":
        """Return the singleton instance, creating it on first call."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (useful in tests)."""
        cls._instance = None

    # --------------------------------------------------------------------------
    # Lifecycle
    # --------------------------------------------------------------------------

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        approval_queue: Optional[ApprovalQueue] = None,
        auto_approval_timeout_seconds: int = DEFAULT_AUTO_APPROVAL_TIMEOUT_SECONDS,
    ):
        # External collaborators
        self.event_bus: EventBus = event_bus or EventBus.get_instance()
        self.approval_queue: ApprovalQueue = approval_queue or ApprovalQueue.get_instance()

        # Per-automation toggle.  Keys are automation names (e.g. "tiktok",
        # "instagram", "twitter", or "*" for global).  Values are booleans.
        # Disabled by default -- no keys present means approval is OFF.
        self._enabled_automations: Dict[str, bool] = {}

        # Auto-approval timeout configuration (seconds).  Can be overridden
        # per-automation via ``set_auto_approval_timeout``.
        self._auto_approval_timeout: int = auto_approval_timeout_seconds
        self._auto_approval_timeouts: Dict[str, int] = {}

        # Map from approval-queue item-id -> original publish event payload so
        # we can re-emit on approval.
        self._held_events: Dict[str, Dict[str, Any]] = {}

        # Background task for auto-approval sweeps
        self._is_running: bool = False
        self._sweep_task: Optional[asyncio.Task] = None

        # Wire up EventBus subscriptions
        self._setup_subscriptions()

        logger.info("ApprovalWorkflow initialised (disabled by default)")

    def _setup_subscriptions(self) -> None:
        """Subscribe to the relevant EventBus topics."""
        self.event_bus.subscribe(
            Topics.PUBLISH_REQUESTED,
            self._handle_publish_requested,
        )
        logger.debug("ApprovalWorkflow subscribed to %s", Topics.PUBLISH_REQUESTED)

    # --------------------------------------------------------------------------
    # Start / Stop
    # --------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the workflow service (auto-approval sweep loop)."""
        if self._is_running:
            logger.warning("ApprovalWorkflow already running")
            return

        self._is_running = True
        self._sweep_task = asyncio.create_task(self._auto_approval_sweep_loop())

        await self.event_bus.publish(
            Topics.SERVICE_STARTED,
            {"service": "approval-workflow", "status": "started"},
            source="ApprovalWorkflow",
        )
        logger.info("ApprovalWorkflow started")

    async def stop(self) -> None:
        """Stop the workflow service."""
        if not self._is_running:
            return

        self._is_running = False

        if self._sweep_task is not None:
            self._sweep_task.cancel()
            try:
                await self._sweep_task
            except asyncio.CancelledError:
                pass
            self._sweep_task = None

        await self.event_bus.publish(
            Topics.SERVICE_STOPPED,
            {"service": "approval-workflow", "status": "stopped"},
            source="ApprovalWorkflow",
        )
        logger.info("ApprovalWorkflow stopped")

    # --------------------------------------------------------------------------
    # Toggle helpers
    # --------------------------------------------------------------------------

    def enable_approval(self, automation: str = "*") -> None:
        """
        Enable approval requirement for *automation*.

        Args:
            automation: Name of the automation / platform (e.g. ``"tiktok"``).
                        Use ``"*"`` to enable for all automations globally.
        """
        self._enabled_automations[automation] = True
        logger.info("Approval enabled for automation=%s", automation)

    def disable_approval(self, automation: str = "*") -> None:
        """
        Disable approval requirement for *automation*.

        Args:
            automation: Name of the automation / platform.  ``"*"`` disables
                        the global gate.
        """
        self._enabled_automations.pop(automation, None)
        logger.info("Approval disabled for automation=%s", automation)

    def is_approval_enabled(self, automation: str = "*") -> bool:
        """
        Check whether approval is required for *automation*.

        Resolution order:
            1. Exact match on *automation* key.
            2. Global ``"*"`` key.
            3. Default: ``False`` (disabled).
        """
        if automation in self._enabled_automations:
            return self._enabled_automations[automation]
        if "*" in self._enabled_automations:
            return self._enabled_automations["*"]
        return False

    # --------------------------------------------------------------------------
    # Auto-approval timeout configuration
    # --------------------------------------------------------------------------

    def set_auto_approval_timeout(
        self,
        seconds: int,
        automation: Optional[str] = None,
    ) -> None:
        """
        Configure the auto-approval timeout.

        Args:
            seconds: Timeout in seconds.  Set to ``0`` to disable auto-approval.
            automation: If provided, override only for this automation key.
                        Otherwise sets the global default.
        """
        if automation is not None:
            self._auto_approval_timeouts[automation] = seconds
        else:
            self._auto_approval_timeout = seconds

        logger.info(
            "Auto-approval timeout set to %ds (automation=%s)",
            seconds,
            automation or "global",
        )

    def get_auto_approval_timeout(self, automation: Optional[str] = None) -> int:
        """Return the effective auto-approval timeout in seconds."""
        if automation and automation in self._auto_approval_timeouts:
            return self._auto_approval_timeouts[automation]
        return self._auto_approval_timeout

    # --------------------------------------------------------------------------
    # Core workflow methods
    # --------------------------------------------------------------------------

    async def submit_for_approval(
        self,
        content_id: str,
        content_type: str,
        content_data: Dict[str, Any],
        automation: str = "*",
        priority: ApprovalPriority = ApprovalPriority.MEDIUM,
        pipeline_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        original_payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Submit content for human approval.

        Creates an :class:`ApprovalItem` in the underlying queue and stores the
        original publish payload so it can be re-emitted on approval.

        Args:
            content_id: Unique content identifier.
            content_type: E.g. ``"post"``, ``"video"``, ``"tweet"``.
            content_data: Payload describing the content.
            automation: Automation key (for timeout resolution).
            priority: Queue priority.
            pipeline_id: Orchestrator pipeline ID (if applicable).
            correlation_id: EventBus correlation ID for tracing.
            original_payload: The full PUBLISH_REQUESTED payload to re-emit
                              on approval.

        Returns:
            The approval item ID.
        """
        timeout_secs = self.get_auto_approval_timeout(automation)
        expires_in_hours: Optional[int] = None
        if timeout_secs > 0:
            expires_in_hours = max(1, timeout_secs // 3600)

        metadata = {
            "automation": automation,
            "pipeline_id": pipeline_id,
            "correlation_id": correlation_id,
        }

        item_id = await self.approval_queue.add_item(
            content_id=content_id,
            content_type=content_type,
            content_data=content_data,
            priority=priority,
            expires_in_hours=expires_in_hours,
            metadata=metadata,
        )

        # Store the original payload so we can re-emit it
        if original_payload is not None:
            self._held_events[item_id] = original_payload

        # Emit submission event
        await self.event_bus.publish(
            TOPIC_APPROVAL_SUBMITTED,
            {
                "item_id": item_id,
                "content_id": content_id,
                "content_type": content_type,
                "automation": automation,
                "pipeline_id": pipeline_id,
            },
            correlation_id=correlation_id,
            source="ApprovalWorkflow",
        )

        logger.info(
            "Content submitted for approval: item_id=%s content_id=%s automation=%s",
            item_id,
            content_id,
            automation,
        )
        return item_id

    async def approve(
        self,
        item_id: str,
        reviewed_by: str = "system",
        feedback: str = "",
    ) -> bool:
        """
        Approve a queued item and continue the publishing pipeline.

        On success, the original ``PUBLISH_REQUESTED`` event is re-emitted so
        downstream workers can proceed.

        Args:
            item_id: Approval queue item ID.
            reviewed_by: Identifier of the reviewer.
            feedback: Optional reviewer feedback.

        Returns:
            ``True`` if the item was found and approved.
        """
        item = await self.approval_queue.get_item(item_id)
        if item is None:
            logger.warning("Approve called for unknown item_id=%s", item_id)
            return False

        success = await self.approval_queue.approve_item(
            item_id=item_id,
            reviewed_by=reviewed_by,
            feedback=feedback,
        )
        if not success:
            return False

        correlation_id = (item.metadata or {}).get("correlation_id")

        # Emit approval event
        await self.event_bus.publish(
            TOPIC_APPROVAL_APPROVED,
            {
                "item_id": item_id,
                "content_id": item.content_id,
                "reviewed_by": reviewed_by,
                "pipeline_id": (item.metadata or {}).get("pipeline_id"),
            },
            correlation_id=correlation_id,
            source="ApprovalWorkflow",
        )

        # Re-emit the held publish event so the pipeline continues
        held_payload = self._held_events.pop(item_id, None)
        if held_payload is not None:
            # Mark payload so downstream knows this passed approval
            held_payload["approval_status"] = "approved"
            held_payload["approved_by"] = reviewed_by

            await self.event_bus.publish(
                Topics.PUBLISH_REQUESTED,
                held_payload,
                correlation_id=correlation_id,
                source="ApprovalWorkflow",
            )
            logger.info(
                "Re-emitted PUBLISH_REQUESTED for approved item_id=%s",
                item_id,
            )

        logger.info("Item approved: item_id=%s by %s", item_id, reviewed_by)
        return True

    async def reject(
        self,
        item_id: str,
        reviewed_by: str = "system",
        feedback: str = "",
    ) -> bool:
        """
        Reject a queued item and notify the pipeline.

        Emits a ``publish.rejected`` event so the orchestrator can handle
        the failure (e.g. archive, retry with edits, notify user).

        Args:
            item_id: Approval queue item ID.
            reviewed_by: Identifier of the reviewer.
            feedback: Rejection reason.

        Returns:
            ``True`` if the item was found and rejected.
        """
        item = await self.approval_queue.get_item(item_id)
        if item is None:
            logger.warning("Reject called for unknown item_id=%s", item_id)
            return False

        success = await self.approval_queue.reject_item(
            item_id=item_id,
            reviewed_by=reviewed_by,
            feedback=feedback,
        )
        if not success:
            return False

        correlation_id = (item.metadata or {}).get("correlation_id")
        pipeline_id = (item.metadata or {}).get("pipeline_id")

        # Remove the held event -- it will not be re-emitted
        self._held_events.pop(item_id, None)

        # Emit rejection event
        await self.event_bus.publish(
            TOPIC_APPROVAL_REJECTED,
            {
                "item_id": item_id,
                "content_id": item.content_id,
                "content_type": item.content_type,
                "reviewed_by": reviewed_by,
                "feedback": feedback,
                "pipeline_id": pipeline_id,
            },
            correlation_id=correlation_id,
            source="ApprovalWorkflow",
        )

        logger.info(
            "Item rejected: item_id=%s by %s reason=%s",
            item_id,
            reviewed_by,
            feedback[:80],
        )
        return True

    async def get_pending(
        self,
        automation: Optional[str] = None,
        limit: int = 50,
    ) -> List[ApprovalItem]:
        """
        Return pending approval items, optionally filtered by automation.

        Args:
            automation: If provided, only return items for this automation.
            limit: Maximum number of items to return.

        Returns:
            List of :class:`ApprovalItem` instances sorted by priority.
        """
        items = await self.approval_queue.get_pending_items(limit=limit)

        if automation is not None:
            items = [
                item
                for item in items
                if (item.metadata or {}).get("automation") == automation
            ]

        return items

    # --------------------------------------------------------------------------
    # EventBus handler
    # --------------------------------------------------------------------------

    async def _handle_publish_requested(self, event: Event) -> None:
        """
        Intercept PUBLISH_REQUESTED events when approval is enabled.

        If the event has already been approved (carries ``approval_status``),
        it is allowed through without re-interception.
        """
        payload = event.payload

        # Avoid re-intercepting events that already passed approval
        if payload.get("approval_status") == "approved":
            return

        # Determine which automation key this publish belongs to
        automation = payload.get("platform") or payload.get("automation") or "*"

        if not self.is_approval_enabled(automation):
            # Approval not required -- let the event flow through
            return

        # Intercept: create an approval item and swallow the event
        content_id = payload.get("content_id") or payload.get("pipeline_id") or str(uuid4())
        content_type = payload.get("content_type") or "post"

        await self.submit_for_approval(
            content_id=content_id,
            content_type=content_type,
            content_data=payload,
            automation=automation,
            pipeline_id=payload.get("pipeline_id"),
            correlation_id=event.correlation_id,
            original_payload=payload,
        )

        logger.info(
            "PUBLISH_REQUESTED intercepted for approval: automation=%s content_id=%s",
            automation,
            content_id,
        )

    # --------------------------------------------------------------------------
    # Auto-approval background sweep
    # --------------------------------------------------------------------------

    async def _auto_approval_sweep_loop(self) -> None:
        """Periodically check for items that should be auto-approved."""
        while self._is_running:
            try:
                await self._sweep_auto_approvals()
                # Sweep every 60 seconds
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # pragma: no cover
                logger.error("Error in auto-approval sweep: %s", exc)
                await asyncio.sleep(30)

    async def _sweep_auto_approvals(self) -> None:
        """
        Auto-approve items whose timeout has elapsed but whose status is
        still PENDING (i.e. not yet expired by the ApprovalQueue's own
        expiry mechanism).

        The auto-approval timeout may be shorter than the queue-level
        ``expires_in_hours`` to allow auto-approval to kick in before the
        item truly expires.
        """
        now = datetime.now(timezone.utc)
        pending = await self.approval_queue.get_pending_items(limit=200)

        for item in pending:
            automation = (item.metadata or {}).get("automation", "*")
            timeout_secs = self.get_auto_approval_timeout(automation)

            if timeout_secs <= 0:
                # Auto-approval disabled for this automation
                continue

            age_seconds = (now - item.created_at).total_seconds()
            if age_seconds >= timeout_secs:
                logger.info(
                    "Auto-approving item_id=%s (age=%ds, timeout=%ds)",
                    item.id,
                    int(age_seconds),
                    timeout_secs,
                )
                await self.approve(
                    item_id=item.id,
                    reviewed_by="auto-approval-timeout",
                    feedback=f"Auto-approved after {timeout_secs}s timeout",
                )

                # Also emit a dedicated auto-approval event
                await self.event_bus.publish(
                    TOPIC_APPROVAL_AUTO_APPROVED,
                    {
                        "item_id": item.id,
                        "content_id": item.content_id,
                        "automation": automation,
                        "timeout_seconds": timeout_secs,
                    },
                    source="ApprovalWorkflow",
                )

    # --------------------------------------------------------------------------
    # Introspection / stats
    # --------------------------------------------------------------------------

    async def get_stats(self) -> Dict[str, Any]:
        """Return combined stats from the underlying queue plus workflow state."""
        queue_stats = await self.approval_queue.get_stats()
        return {
            **queue_stats,
            "enabled_automations": dict(self._enabled_automations),
            "held_events_count": len(self._held_events),
            "auto_approval_timeout_seconds": self._auto_approval_timeout,
            "auto_approval_timeout_overrides": dict(self._auto_approval_timeouts),
            "is_running": self._is_running,
        }


# ---------------------------------------------------------------------------
# Module-level convenience accessor
# ---------------------------------------------------------------------------

def get_approval_workflow() -> ApprovalWorkflow:
    """Return the singleton :class:`ApprovalWorkflow` instance."""
    return ApprovalWorkflow.get_instance()
