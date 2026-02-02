"""
Tests for Approval Workflow Service (HITL-001)
===============================================
Unit and integration tests for the human-in-the-loop approval gate.

Covers:
    - Service initialisation and singleton pattern
    - submit_for_approval creates an approval item
    - approve() re-emits PUBLISH_REQUESTED to continue the pipeline
    - reject() emits publish.rejected and archives content
    - is_approval_enabled toggle (per-automation and global)
    - Auto-approval timeout configuration
    - EventBus interception of PUBLISH_REQUESTED when approval is enabled
    - Events pass through when approval is disabled
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_singletons():
    """
    Reset all singleton instances before each test so tests are fully
    isolated.  Runs automatically for every test in this module.
    """
    from services.event_bus.bus import EventBus
    from services.approval_queue import ApprovalQueue
    from services.approval_workflow import ApprovalWorkflow

    EventBus.reset_instance()
    ApprovalQueue._instance = None
    ApprovalWorkflow.reset_instance()
    yield
    EventBus.reset_instance()
    ApprovalQueue._instance = None
    ApprovalWorkflow.reset_instance()


@pytest.fixture
def event_bus():
    """Provide a fresh EventBus instance."""
    from services.event_bus.bus import EventBus
    return EventBus.get_instance()


@pytest.fixture
def approval_queue(event_bus):
    """Provide a fresh ApprovalQueue wired to the test EventBus."""
    from services.approval_queue import ApprovalQueue
    queue = ApprovalQueue.get_instance()
    return queue


@pytest.fixture
def workflow(event_bus, approval_queue):
    """Provide a fresh ApprovalWorkflow wired to test EventBus and queue."""
    from services.approval_workflow import ApprovalWorkflow
    wf = ApprovalWorkflow(event_bus=event_bus, approval_queue=approval_queue)
    ApprovalWorkflow._instance = wf
    return wf


# ===========================================================================
# 1. Initialisation and Singleton
# ===========================================================================

class TestInitialisationAndSingleton:
    """Service initialisation and singleton pattern tests."""

    def test_get_instance_returns_singleton(self):
        """get_instance() should return the same object on repeated calls."""
        from services.approval_workflow import ApprovalWorkflow

        first = ApprovalWorkflow.get_instance()
        second = ApprovalWorkflow.get_instance()
        assert first is second

    def test_reset_instance_clears_singleton(self):
        """reset_instance() should allow a new instance to be created."""
        from services.approval_workflow import ApprovalWorkflow

        first = ApprovalWorkflow.get_instance()
        ApprovalWorkflow.reset_instance()
        second = ApprovalWorkflow.get_instance()
        assert first is not second

    def test_module_level_accessor(self):
        """get_approval_workflow() should return the singleton."""
        from services.approval_workflow import get_approval_workflow, ApprovalWorkflow

        wf = get_approval_workflow()
        assert isinstance(wf, ApprovalWorkflow)
        assert wf is get_approval_workflow()

    def test_default_state(self, workflow):
        """Workflow should start with approval disabled and no held events."""
        assert workflow._is_running is False
        assert workflow._enabled_automations == {}
        assert workflow._held_events == {}
        assert workflow.is_approval_enabled() is False

    @pytest.mark.asyncio
    async def test_start_and_stop(self, workflow):
        """start() and stop() should toggle the running flag cleanly."""
        await workflow.start()
        assert workflow._is_running is True
        assert workflow._sweep_task is not None

        await workflow.stop()
        assert workflow._is_running is False
        assert workflow._sweep_task is None

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self, workflow):
        """Calling start() twice should not create duplicate tasks."""
        await workflow.start()
        first_task = workflow._sweep_task
        await workflow.start()  # second call
        assert workflow._sweep_task is first_task
        await workflow.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self, workflow):
        """Calling stop() when not running should be a no-op."""
        await workflow.stop()  # should not raise
        assert workflow._is_running is False


# ===========================================================================
# 2. submit_for_approval
# ===========================================================================

class TestSubmitForApproval:
    """Tests for the submit_for_approval method."""

    @pytest.mark.asyncio
    async def test_submit_creates_item_in_queue(self, workflow, approval_queue):
        """Submitting for approval should add an item to the ApprovalQueue."""
        item_id = await workflow.submit_for_approval(
            content_id="post-001",
            content_type="post",
            content_data={"text": "Hello world", "platform": "tiktok"},
            automation="tiktok",
        )

        assert item_id is not None
        assert isinstance(item_id, str)

        # Verify item exists in the queue
        item = await approval_queue.get_item(item_id)
        assert item is not None
        assert item.content_id == "post-001"
        assert item.content_type == "post"
        assert item.status.value == "pending"

    @pytest.mark.asyncio
    async def test_submit_stores_held_event(self, workflow):
        """The original payload should be stored for later re-emission."""
        original_payload = {
            "pipeline_id": "pipe-123",
            "platform": "instagram",
            "video_path": "/tmp/video.mp4",
        }
        item_id = await workflow.submit_for_approval(
            content_id="vid-001",
            content_type="video",
            content_data=original_payload,
            original_payload=original_payload,
        )

        assert item_id in workflow._held_events
        assert workflow._held_events[item_id] is original_payload

    @pytest.mark.asyncio
    async def test_submit_emits_approval_submitted_event(self, workflow, event_bus):
        """Submitting should emit an approval.submitted event."""
        captured_events = []

        async def _capture(event):
            captured_events.append(event)

        event_bus.subscribe("approval.submitted", _capture)

        await workflow.submit_for_approval(
            content_id="post-002",
            content_type="post",
            content_data={"text": "Test"},
        )

        assert len(captured_events) == 1
        assert captured_events[0].payload["content_id"] == "post-002"

    @pytest.mark.asyncio
    async def test_submit_with_pipeline_and_correlation(self, workflow, approval_queue):
        """Pipeline ID and correlation ID should be stored in item metadata."""
        item_id = await workflow.submit_for_approval(
            content_id="c-100",
            content_type="post",
            content_data={},
            pipeline_id="pipe-abc",
            correlation_id="corr-xyz",
        )

        item = await approval_queue.get_item(item_id)
        assert item.metadata["pipeline_id"] == "pipe-abc"
        assert item.metadata["correlation_id"] == "corr-xyz"

    @pytest.mark.asyncio
    async def test_submit_sets_expiry_based_on_timeout(self, workflow, approval_queue):
        """Item expiry should derive from the auto-approval timeout."""
        workflow.set_auto_approval_timeout(7200)  # 2 hours
        item_id = await workflow.submit_for_approval(
            content_id="c-200",
            content_type="post",
            content_data={},
        )
        item = await approval_queue.get_item(item_id)
        assert item.expires_at is not None


# ===========================================================================
# 3. approve() triggers publish
# ===========================================================================

class TestApprove:
    """Tests for the approve method."""

    @pytest.mark.asyncio
    async def test_approve_updates_queue_status(self, workflow, approval_queue):
        """Approving should set the item status to APPROVED."""
        item_id = await workflow.submit_for_approval(
            content_id="post-approve",
            content_type="post",
            content_data={"text": "Good content"},
        )

        result = await workflow.approve(item_id, reviewed_by="admin@test.com")
        assert result is True

        item = await approval_queue.get_item(item_id)
        assert item.status == "approved" or item.status.value == "approved"

    @pytest.mark.asyncio
    async def test_approve_re_emits_publish_requested(self, workflow, event_bus):
        """Approval should re-emit PUBLISH_REQUESTED with the original payload."""
        from services.event_bus import Topics

        original_payload = {
            "pipeline_id": "pipe-999",
            "platform": "youtube",
            "video_path": "/videos/clip.mp4",
        }

        item_id = await workflow.submit_for_approval(
            content_id="vid-approve",
            content_type="video",
            content_data=original_payload,
            original_payload=original_payload,
        )

        # Collect re-emitted events
        re_emitted = []

        async def _capture_publish(event):
            if event.payload.get("approval_status") == "approved":
                re_emitted.append(event)

        event_bus.subscribe(Topics.PUBLISH_REQUESTED, _capture_publish)

        await workflow.approve(item_id, reviewed_by="editor")

        assert len(re_emitted) == 1
        assert re_emitted[0].payload["pipeline_id"] == "pipe-999"
        assert re_emitted[0].payload["platform"] == "youtube"
        assert re_emitted[0].payload["approved_by"] == "editor"

    @pytest.mark.asyncio
    async def test_approve_emits_approval_approved_event(self, workflow, event_bus):
        """Approving should emit an approval.approved event."""
        item_id = await workflow.submit_for_approval(
            content_id="post-evt",
            content_type="post",
            content_data={},
        )

        captured = []

        async def _capture(event):
            captured.append(event)

        event_bus.subscribe("approval.approved", _capture)

        await workflow.approve(item_id, reviewed_by="user1")

        assert len(captured) == 1
        assert captured[0].payload["item_id"] == item_id
        assert captured[0].payload["reviewed_by"] == "user1"

    @pytest.mark.asyncio
    async def test_approve_clears_held_event(self, workflow):
        """After approval the held event should be removed."""
        item_id = await workflow.submit_for_approval(
            content_id="held-clear",
            content_type="post",
            content_data={"x": 1},
            original_payload={"x": 1},
        )
        assert item_id in workflow._held_events

        await workflow.approve(item_id, reviewed_by="bot")
        assert item_id not in workflow._held_events

    @pytest.mark.asyncio
    async def test_approve_unknown_item_returns_false(self, workflow):
        """Approving a nonexistent item should return False."""
        result = await workflow.approve("nonexistent-id", reviewed_by="x")
        assert result is False

    @pytest.mark.asyncio
    async def test_approve_without_held_payload_still_succeeds(self, workflow):
        """Approval should succeed even if there is no stored payload."""
        item_id = await workflow.submit_for_approval(
            content_id="no-payload",
            content_type="post",
            content_data={"text": "test"},
            # Note: original_payload not provided
        )
        result = await workflow.approve(item_id, reviewed_by="admin")
        assert result is True


# ===========================================================================
# 4. reject() archives content
# ===========================================================================

class TestReject:
    """Tests for the reject method."""

    @pytest.mark.asyncio
    async def test_reject_updates_queue_status(self, workflow, approval_queue):
        """Rejecting should set the item status to REJECTED."""
        item_id = await workflow.submit_for_approval(
            content_id="post-reject",
            content_type="post",
            content_data={"text": "Bad content"},
        )

        result = await workflow.reject(
            item_id, reviewed_by="mod@test.com", feedback="Off-brand"
        )
        assert result is True

        item = await approval_queue.get_item(item_id)
        assert item.status == "rejected" or item.status.value == "rejected"

    @pytest.mark.asyncio
    async def test_reject_emits_publish_rejected(self, workflow, event_bus):
        """Rejection should emit a publish.rejected event."""
        item_id = await workflow.submit_for_approval(
            content_id="post-rej-evt",
            content_type="video",
            content_data={"text": "low quality"},
        )

        captured = []

        async def _capture(event):
            captured.append(event)

        event_bus.subscribe("publish.rejected", _capture)

        await workflow.reject(item_id, reviewed_by="reviewer", feedback="Not suitable")

        assert len(captured) == 1
        assert captured[0].payload["item_id"] == item_id
        assert captured[0].payload["feedback"] == "Not suitable"
        assert captured[0].payload["content_id"] == "post-rej-evt"

    @pytest.mark.asyncio
    async def test_reject_removes_held_event(self, workflow):
        """After rejection the held event should be discarded."""
        item_id = await workflow.submit_for_approval(
            content_id="held-discard",
            content_type="post",
            content_data={"x": 1},
            original_payload={"x": 1},
        )
        assert item_id in workflow._held_events

        await workflow.reject(item_id, reviewed_by="admin")
        assert item_id not in workflow._held_events

    @pytest.mark.asyncio
    async def test_reject_unknown_item_returns_false(self, workflow):
        """Rejecting a nonexistent item should return False."""
        result = await workflow.reject("missing-item", reviewed_by="y")
        assert result is False

    @pytest.mark.asyncio
    async def test_reject_does_not_re_emit_publish(self, workflow, event_bus):
        """Rejection must NOT re-emit PUBLISH_REQUESTED."""
        from services.event_bus import Topics

        item_id = await workflow.submit_for_approval(
            content_id="rej-no-pub",
            content_type="post",
            content_data={"video": "bad.mp4"},
            original_payload={"video": "bad.mp4"},
        )

        re_emitted = []

        async def _capture_publish(event):
            if event.payload.get("approval_status") == "approved":
                re_emitted.append(event)

        event_bus.subscribe(Topics.PUBLISH_REQUESTED, _capture_publish)

        await workflow.reject(item_id, reviewed_by="admin", feedback="nope")

        assert len(re_emitted) == 0


# ===========================================================================
# 5. is_approval_enabled toggle
# ===========================================================================

class TestApprovalToggle:
    """Tests for per-automation enable/disable logic."""

    def test_disabled_by_default(self, workflow):
        """Approval should be disabled by default for any automation."""
        assert workflow.is_approval_enabled() is False
        assert workflow.is_approval_enabled("tiktok") is False
        assert workflow.is_approval_enabled("instagram") is False

    def test_enable_global(self, workflow):
        """Enabling with '*' should affect all automations."""
        workflow.enable_approval("*")
        assert workflow.is_approval_enabled() is True
        assert workflow.is_approval_enabled("tiktok") is True
        assert workflow.is_approval_enabled("youtube") is True

    def test_disable_global(self, workflow):
        """Disabling with '*' should turn off the global gate."""
        workflow.enable_approval("*")
        workflow.disable_approval("*")
        assert workflow.is_approval_enabled() is False
        assert workflow.is_approval_enabled("tiktok") is False

    def test_enable_per_automation(self, workflow):
        """Enabling for a specific automation should not affect others."""
        workflow.enable_approval("tiktok")
        assert workflow.is_approval_enabled("tiktok") is True
        assert workflow.is_approval_enabled("instagram") is False
        assert workflow.is_approval_enabled() is False  # global still off

    def test_specific_overrides_global(self, workflow):
        """Specific automation setting should take precedence over global."""
        workflow.enable_approval("*")
        workflow.disable_approval("instagram")
        # Instagram was explicitly removed, but global is on
        # Resolution: exact match first, then global
        assert workflow.is_approval_enabled("tiktok") is True  # falls to global
        # instagram key is removed (disable_approval pops the key)
        # so it falls back to global "*" which is True
        assert workflow.is_approval_enabled("instagram") is True

    def test_per_automation_enable_with_global_off(self, workflow):
        """Per-automation enable should work when global is off."""
        workflow.enable_approval("youtube")
        assert workflow.is_approval_enabled("youtube") is True
        assert workflow.is_approval_enabled("tiktok") is False

    def test_disable_specific_automation(self, workflow):
        """disable_approval for a specific key should only affect that key."""
        workflow.enable_approval("tiktok")
        workflow.enable_approval("youtube")
        workflow.disable_approval("tiktok")
        assert workflow.is_approval_enabled("tiktok") is False
        assert workflow.is_approval_enabled("youtube") is True

    @pytest.mark.asyncio
    async def test_event_passthrough_when_disabled(self, workflow, event_bus):
        """
        When approval is disabled, PUBLISH_REQUESTED events should pass
        through without being intercepted.
        """
        from services.event_bus import Topics

        # Approval is disabled by default -- publish should not be intercepted
        assert workflow.is_approval_enabled("tiktok") is False

        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {
                "platform": "tiktok",
                "video_path": "/tmp/vid.mp4",
                "pipeline_id": "pipe-pass",
            },
            source="test",
        )

        # No items should have been created in the queue
        pending = await workflow.get_pending()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_event_intercepted_when_enabled(self, workflow, event_bus):
        """
        When approval is enabled, PUBLISH_REQUESTED events should be
        intercepted and added to the queue.
        """
        from services.event_bus import Topics

        workflow.enable_approval("tiktok")

        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {
                "platform": "tiktok",
                "video_path": "/tmp/vid.mp4",
                "pipeline_id": "pipe-intercept",
            },
            source="test",
        )

        pending = await workflow.get_pending(automation="tiktok")
        assert len(pending) == 1
        assert pending[0].content_data["platform"] == "tiktok"

    @pytest.mark.asyncio
    async def test_already_approved_event_not_re_intercepted(self, workflow, event_bus):
        """
        Events that carry approval_status='approved' should not be
        intercepted again (prevent infinite loop).
        """
        from services.event_bus import Topics

        workflow.enable_approval("*")

        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {
                "platform": "tiktok",
                "approval_status": "approved",
                "approved_by": "admin",
            },
            source="ApprovalWorkflow",
        )

        pending = await workflow.get_pending()
        assert len(pending) == 0


# ===========================================================================
# 6. Auto-approval timeout configuration
# ===========================================================================

class TestAutoApprovalTimeout:
    """Tests for auto-approval timeout settings."""

    def test_default_timeout_is_five_days(self, workflow):
        """Default auto-approval timeout should be 5 days (432000 seconds)."""
        from services.approval_workflow import DEFAULT_AUTO_APPROVAL_TIMEOUT_SECONDS

        assert workflow.get_auto_approval_timeout() == DEFAULT_AUTO_APPROVAL_TIMEOUT_SECONDS
        assert DEFAULT_AUTO_APPROVAL_TIMEOUT_SECONDS == 5 * 24 * 60 * 60

    def test_set_global_timeout(self, workflow):
        """Setting global timeout should change the default."""
        workflow.set_auto_approval_timeout(3600)
        assert workflow.get_auto_approval_timeout() == 3600

    def test_set_per_automation_timeout(self, workflow):
        """Per-automation timeout should override the global default."""
        workflow.set_auto_approval_timeout(7200, automation="tiktok")
        assert workflow.get_auto_approval_timeout("tiktok") == 7200
        # Global should remain unchanged
        from services.approval_workflow import DEFAULT_AUTO_APPROVAL_TIMEOUT_SECONDS
        assert workflow.get_auto_approval_timeout() == DEFAULT_AUTO_APPROVAL_TIMEOUT_SECONDS

    def test_per_automation_override_takes_precedence(self, workflow):
        """Per-automation setting should beat the global setting."""
        workflow.set_auto_approval_timeout(100)
        workflow.set_auto_approval_timeout(999, automation="instagram")
        assert workflow.get_auto_approval_timeout("instagram") == 999
        assert workflow.get_auto_approval_timeout("tiktok") == 100  # falls to global

    @pytest.mark.asyncio
    async def test_auto_approval_sweep_approves_expired_items(self, workflow, approval_queue):
        """
        The sweep should auto-approve items whose age exceeds the timeout.
        """
        # Set a very short timeout for testing
        workflow.set_auto_approval_timeout(1)  # 1 second

        item_id = await workflow.submit_for_approval(
            content_id="auto-approve-me",
            content_type="post",
            content_data={"text": "test"},
            original_payload={"text": "test", "platform": "tiktok"},
        )

        # Manually backdate the item's created_at to ensure the timeout fires
        item = await approval_queue.get_item(item_id)
        item.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Run a single sweep iteration
        await workflow._sweep_auto_approvals()

        # Item should now be approved
        item = await approval_queue.get_item(item_id)
        assert item.status.value == "approved"
        assert item.reviewed_by == "auto-approval-timeout"

    @pytest.mark.asyncio
    async def test_auto_approval_disabled_when_timeout_zero(self, workflow, approval_queue):
        """When timeout is 0, items should not be auto-approved."""
        workflow.set_auto_approval_timeout(0)

        item_id = await workflow.submit_for_approval(
            content_id="no-auto",
            content_type="post",
            content_data={"text": "test"},
        )

        item = await approval_queue.get_item(item_id)
        item.created_at = datetime.now(timezone.utc) - timedelta(days=30)

        await workflow._sweep_auto_approvals()

        item = await approval_queue.get_item(item_id)
        assert item.status.value == "pending"

    @pytest.mark.asyncio
    async def test_auto_approval_emits_event(self, workflow, approval_queue, event_bus):
        """Auto-approval should emit an approval.auto_approved event."""
        workflow.set_auto_approval_timeout(1)

        item_id = await workflow.submit_for_approval(
            content_id="auto-evt",
            content_type="post",
            content_data={},
        )

        item = await approval_queue.get_item(item_id)
        item.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)

        captured = []

        async def _capture(event):
            captured.append(event)

        event_bus.subscribe("approval.auto_approved", _capture)

        await workflow._sweep_auto_approvals()

        assert len(captured) == 1
        assert captured[0].payload["item_id"] == item_id


# ===========================================================================
# 7. get_pending
# ===========================================================================

class TestGetPending:
    """Tests for get_pending query method."""

    @pytest.mark.asyncio
    async def test_get_pending_returns_all(self, workflow):
        """get_pending with no filter returns all pending items."""
        await workflow.submit_for_approval(
            content_id="a", content_type="post", content_data={}, automation="tiktok"
        )
        await workflow.submit_for_approval(
            content_id="b", content_type="post", content_data={}, automation="youtube"
        )

        items = await workflow.get_pending()
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_get_pending_filtered_by_automation(self, workflow):
        """get_pending with automation filter only returns matching items."""
        await workflow.submit_for_approval(
            content_id="a", content_type="post", content_data={}, automation="tiktok"
        )
        await workflow.submit_for_approval(
            content_id="b", content_type="post", content_data={}, automation="youtube"
        )

        tiktok_items = await workflow.get_pending(automation="tiktok")
        assert len(tiktok_items) == 1
        assert tiktok_items[0].metadata["automation"] == "tiktok"

    @pytest.mark.asyncio
    async def test_get_pending_empty_when_none(self, workflow):
        """get_pending should return an empty list when the queue is empty."""
        items = await workflow.get_pending()
        assert items == []


# ===========================================================================
# 8. Stats / introspection
# ===========================================================================

class TestStats:
    """Tests for the get_stats method."""

    @pytest.mark.asyncio
    async def test_stats_contain_expected_keys(self, workflow):
        """Stats should include both queue stats and workflow-specific data."""
        stats = await workflow.get_stats()
        assert "pending" in stats
        assert "approved" in stats
        assert "enabled_automations" in stats
        assert "held_events_count" in stats
        assert "auto_approval_timeout_seconds" in stats
        assert "is_running" in stats

    @pytest.mark.asyncio
    async def test_stats_reflect_held_events(self, workflow):
        """held_events_count should reflect stored payloads."""
        await workflow.submit_for_approval(
            content_id="s1",
            content_type="post",
            content_data={},
            original_payload={"p": 1},
        )

        stats = await workflow.get_stats()
        assert stats["held_events_count"] == 1


# ===========================================================================
# 9. End-to-end interception flow
# ===========================================================================

class TestEndToEndFlow:
    """Full interception -> approve -> re-emit cycle."""

    @pytest.mark.asyncio
    async def test_full_intercept_approve_republish_cycle(self, workflow, event_bus):
        """
        1. Enable approval for tiktok
        2. Publish a PUBLISH_REQUESTED event
        3. Verify it was intercepted (queue has 1 pending)
        4. Approve the item
        5. Verify PUBLISH_REQUESTED is re-emitted with approval_status
        """
        from services.event_bus import Topics

        workflow.enable_approval("tiktok")

        # Step 2: Publish
        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {
                "platform": "tiktok",
                "video_path": "/tmp/e2e.mp4",
                "pipeline_id": "pipe-e2e",
                "content_id": "e2e-001",
            },
            source="MasterOrchestrator",
        )

        # Step 3: Verify intercepted
        pending = await workflow.get_pending(automation="tiktok")
        assert len(pending) == 1

        item_id = pending[0].id

        # Step 4: Collect re-emitted events
        re_emitted = []

        async def _capture(event):
            if event.payload.get("approval_status") == "approved":
                re_emitted.append(event)

        event_bus.subscribe(Topics.PUBLISH_REQUESTED, _capture)

        # Approve
        result = await workflow.approve(item_id, reviewed_by="admin")
        assert result is True

        # Step 5: Verify re-emission
        assert len(re_emitted) == 1
        assert re_emitted[0].payload["platform"] == "tiktok"
        assert re_emitted[0].payload["video_path"] == "/tmp/e2e.mp4"
        assert re_emitted[0].payload["approval_status"] == "approved"
        assert re_emitted[0].payload["approved_by"] == "admin"

    @pytest.mark.asyncio
    async def test_full_intercept_reject_cycle(self, workflow, event_bus):
        """
        1. Enable approval globally
        2. Publish a PUBLISH_REQUESTED event
        3. Reject the item
        4. Verify publish.rejected was emitted
        5. Verify PUBLISH_REQUESTED was NOT re-emitted
        """
        from services.event_bus import Topics

        workflow.enable_approval("*")

        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {
                "platform": "youtube",
                "video_path": "/tmp/reject.mp4",
                "content_id": "rej-001",
            },
            source="MasterOrchestrator",
        )

        pending = await workflow.get_pending()
        assert len(pending) == 1

        item_id = pending[0].id

        rejected_events = []
        republished_events = []

        async def _capture_rejected(event):
            rejected_events.append(event)

        async def _capture_publish(event):
            if event.payload.get("approval_status") == "approved":
                republished_events.append(event)

        event_bus.subscribe("publish.rejected", _capture_rejected)
        event_bus.subscribe(Topics.PUBLISH_REQUESTED, _capture_publish)

        await workflow.reject(item_id, reviewed_by="mod", feedback="Off brand")

        assert len(rejected_events) == 1
        assert rejected_events[0].payload["content_id"] == "rej-001"
        assert rejected_events[0].payload["feedback"] == "Off brand"

        assert len(republished_events) == 0

    @pytest.mark.asyncio
    async def test_mixed_platforms_only_enabled_intercepted(self, workflow, event_bus):
        """
        If approval is enabled only for tiktok, youtube events should
        pass through without interception.
        """
        from services.event_bus import Topics

        workflow.enable_approval("tiktok")

        # Tiktok event -- should be intercepted
        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {"platform": "tiktok", "content_id": "tt-1"},
            source="test",
        )

        # YouTube event -- should pass through
        await event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {"platform": "youtube", "content_id": "yt-1"},
            source="test",
        )

        pending = await workflow.get_pending()
        assert len(pending) == 1
        assert pending[0].content_data["platform"] == "tiktok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
