"""
Tests for Dead Letter Queue Service (OPS-020)
==============================================

When a job fails after max retries:
- Store in DLQ with error details
- Track retry attempts
- Support manual retry
- Alert on persistent failures
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone

from services.dlq_service import (
    DeadLetterQueueService,
    DLQReason,
    DLQStatus,
    DLQItem,
)
from services.event_bus import EventBus


@pytest.fixture
def event_bus():
    """Get fresh event bus instance"""
    EventBus._instance = None
    return EventBus.get_instance()


@pytest.fixture
def dlq_service(event_bus):
    """Get fresh DLQ service for each test"""
    DeadLetterQueueService._instance = None
    return DeadLetterQueueService.get_instance(event_bus)


class TestDLQItem:
    """Test DLQItem dataclass"""

    def test_to_dict(self):
        """Test conversion to dictionary"""
        now = datetime.now(timezone.utc)
        item = DLQItem(
            dlq_id="dlq-123",
            job_id="job-456",
            job_type="publish_post",
            payload={"post_id": "abc"},
            error_message="Rate limit exceeded",
            error_trace="Traceback...",
            reason=DLQReason.RATE_LIMIT_EXHAUSTED,
            retry_count=3,
            created_at=now,
            updated_at=now,
            status=DLQStatus.PENDING
        )

        data = item.to_dict()

        assert data["dlq_id"] == "dlq-123"
        assert data["job_id"] == "job-456"
        assert data["job_type"] == "publish_post"
        assert data["payload"]["post_id"] == "abc"
        assert data["error_message"] == "Rate limit exceeded"
        assert data["reason"] == "rate_limit_exhausted"
        assert data["retry_count"] == 3
        assert data["status"] == "pending"


class TestDeadLetterQueueService:
    """Test Dead Letter Queue Service"""

    def test_singleton_pattern(self, event_bus):
        """Test singleton pattern"""
        DeadLetterQueueService._instance = None
        service1 = DeadLetterQueueService.get_instance(event_bus)
        service2 = DeadLetterQueueService.get_instance()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_add_failed_job(self, dlq_service):
        """Test adding failed job to DLQ"""
        dlq_id = await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="publish_post",
            payload={"post_id": "abc", "platform": "twitter"},
            error_message="Connection timeout",
            error_trace="Traceback:\n  File...",
            reason=DLQReason.TIMEOUT,
            retry_count=5
        )

        assert dlq_id is not None

        # Retrieve item
        item = await dlq_service.get_item(dlq_id)
        assert item is not None
        assert item.job_id == "job-123"
        assert item.job_type == "publish_post"
        assert item.error_message == "Connection timeout"
        assert item.reason == DLQReason.TIMEOUT
        assert item.retry_count == 5
        assert item.status == DLQStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_item_by_job_id(self, dlq_service):
        """Test retrieving DLQ item by original job ID"""
        dlq_id = await dlq_service.add_failed_job(
            job_id="job-456",
            job_type="send_dm",
            payload={"message": "Hello"},
            error_message="User blocked",
            reason=DLQReason.EXTERNAL_SERVICE_FAILURE,
            retry_count=2
        )

        # Get by job ID
        item = await dlq_service.get_item_by_job_id("job-456")
        assert item is not None
        assert item.dlq_id == dlq_id
        assert item.job_type == "send_dm"

    @pytest.mark.asyncio
    async def test_list_items_no_filters(self, dlq_service):
        """Test listing all DLQ items"""
        # Add multiple items
        await dlq_service.add_failed_job(
            job_id="job-1",
            job_type="publish_post",
            payload={},
            error_message="Error 1",
            reason=DLQReason.MAX_RETRIES_EXCEEDED,
            retry_count=5
        )
        await dlq_service.add_failed_job(
            job_id="job-2",
            job_type="send_dm",
            payload={},
            error_message="Error 2",
            reason=DLQReason.TIMEOUT,
            retry_count=3
        )

        items = await dlq_service.list_items()

        assert len(items) == 2
        # Should be sorted by created_at descending (newest first)
        assert items[0].job_id == "job-2"
        assert items[1].job_id == "job-1"

    @pytest.mark.asyncio
    async def test_list_items_filter_by_status(self, dlq_service):
        """Test listing items filtered by status"""
        # Add pending item
        dlq_id1 = await dlq_service.add_failed_job(
            job_id="job-pending",
            job_type="publish_post",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )

        # Add and mark investigating
        dlq_id2 = await dlq_service.add_failed_job(
            job_id="job-investigating",
            job_type="publish_post",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )
        await dlq_service.update_status(dlq_id2, DLQStatus.INVESTIGATING)

        # Filter by pending
        pending_items = await dlq_service.list_items(status=DLQStatus.PENDING)
        assert len(pending_items) == 1
        assert pending_items[0].dlq_id == dlq_id1

        # Filter by investigating
        investigating_items = await dlq_service.list_items(status=DLQStatus.INVESTIGATING)
        assert len(investigating_items) == 1
        assert investigating_items[0].dlq_id == dlq_id2

    @pytest.mark.asyncio
    async def test_list_items_filter_by_reason(self, dlq_service):
        """Test listing items filtered by failure reason"""
        await dlq_service.add_failed_job(
            job_id="job-1",
            job_type="publish_post",
            payload={},
            error_message="Timeout",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )
        await dlq_service.add_failed_job(
            job_id="job-2",
            job_type="publish_post",
            payload={},
            error_message="Rate limit",
            reason=DLQReason.RATE_LIMIT_EXHAUSTED,
            retry_count=1
        )

        # Filter by timeout
        timeout_items = await dlq_service.list_items(reason=DLQReason.TIMEOUT)
        assert len(timeout_items) == 1
        assert timeout_items[0].job_id == "job-1"

    @pytest.mark.asyncio
    async def test_list_items_filter_by_job_type(self, dlq_service):
        """Test listing items filtered by job type"""
        await dlq_service.add_failed_job(
            job_id="job-1",
            job_type="publish_post",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )
        await dlq_service.add_failed_job(
            job_id="job-2",
            job_type="send_dm",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )

        # Filter by publish_post
        publish_items = await dlq_service.list_items(job_type="publish_post")
        assert len(publish_items) == 1
        assert publish_items[0].job_id == "job-1"

    @pytest.mark.asyncio
    async def test_list_items_pagination(self, dlq_service):
        """Test pagination of DLQ items"""
        # Add 5 items
        for i in range(5):
            await dlq_service.add_failed_job(
                job_id=f"job-{i}",
                job_type="test",
                payload={},
                error_message="Error",
                reason=DLQReason.TIMEOUT,
                retry_count=1
            )
            # Small delay to ensure distinct timestamps
            await asyncio.sleep(0.01)

        # Get first page (limit=2)
        page1 = await dlq_service.list_items(limit=2, offset=0)
        assert len(page1) == 2
        assert page1[0].job_id == "job-4"  # Newest first
        assert page1[1].job_id == "job-3"

        # Get second page
        page2 = await dlq_service.list_items(limit=2, offset=2)
        assert len(page2) == 2
        assert page2[0].job_id == "job-2"
        assert page2[1].job_id == "job-1"

    @pytest.mark.asyncio
    async def test_update_status(self, dlq_service):
        """Test updating DLQ item status"""
        dlq_id = await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="test",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )

        # Update to investigating
        success = await dlq_service.update_status(
            dlq_id,
            DLQStatus.INVESTIGATING,
            notes="Looking into this issue"
        )

        assert success is True

        item = await dlq_service.get_item(dlq_id)
        assert item.status == DLQStatus.INVESTIGATING
        assert "Looking into this issue" in item.notes

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, dlq_service):
        """Test updating non-existent DLQ item"""
        success = await dlq_service.update_status(
            "nonexistent-id",
            DLQStatus.INVESTIGATING
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_retry_item(self, dlq_service):
        """Test retrying a DLQ item"""
        dlq_id = await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="publish_post",
            payload={"post_id": "abc"},
            error_message="Temporary failure",
            reason=DLQReason.EXTERNAL_SERVICE_FAILURE,
            retry_count=2
        )

        # Retry item
        retry_info = await dlq_service.retry_item(dlq_id)

        assert retry_info["dlq_id"] == dlq_id
        assert retry_info["job_id"] == "job-123"
        assert retry_info["job_type"] == "publish_post"
        assert retry_info["payload"]["post_id"] == "abc"
        assert retry_info["retry_count"] == 3  # Incremented

        # Check status changed to retrying
        item = await dlq_service.get_item(dlq_id)
        assert item.status == DLQStatus.RETRYING
        assert item.retry_count == 3

    @pytest.mark.asyncio
    async def test_retry_item_not_found(self, dlq_service):
        """Test retrying non-existent item raises error"""
        with pytest.raises(ValueError, match="not found"):
            await dlq_service.retry_item("nonexistent-id")

    @pytest.mark.asyncio
    async def test_retry_item_already_resolved(self, dlq_service):
        """Test retrying already resolved item raises error"""
        dlq_id = await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="test",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )

        # Mark resolved
        await dlq_service.mark_resolved(dlq_id)

        # Try to retry
        with pytest.raises(ValueError, match="already resolved"):
            await dlq_service.retry_item(dlq_id)

    @pytest.mark.asyncio
    async def test_mark_resolved(self, dlq_service):
        """Test marking item as resolved"""
        dlq_id = await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="test",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )

        success = await dlq_service.mark_resolved(
            dlq_id,
            notes="Successfully retried after infrastructure fix"
        )

        assert success is True

        item = await dlq_service.get_item(dlq_id)
        assert item.status == DLQStatus.RESOLVED
        assert item.resolved_at is not None
        assert "infrastructure fix" in item.notes

    @pytest.mark.asyncio
    async def test_mark_abandoned(self, dlq_service):
        """Test marking item as abandoned"""
        dlq_id = await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="test",
            payload={},
            error_message="Invalid data",
            reason=DLQReason.INVALID_INPUT,
            retry_count=1
        )

        success = await dlq_service.mark_abandoned(
            dlq_id,
            notes="Invalid input, cannot be fixed"
        )

        assert success is True

        item = await dlq_service.get_item(dlq_id)
        assert item.status == DLQStatus.ABANDONED
        assert "cannot be fixed" in item.notes

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, dlq_service):
        """Test stats for empty DLQ"""
        stats = await dlq_service.get_stats()

        assert stats["total"] == 0
        assert stats["oldest_item"] is None
        assert stats["newest_item"] is None

    @pytest.mark.asyncio
    async def test_get_stats_with_items(self, dlq_service):
        """Test stats with multiple items"""
        # Add items with different statuses and reasons
        dlq_id1 = await dlq_service.add_failed_job(
            job_id="job-1",
            job_type="publish_post",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )

        await asyncio.sleep(0.01)  # Ensure different timestamps

        dlq_id2 = await dlq_service.add_failed_job(
            job_id="job-2",
            job_type="send_dm",
            payload={},
            error_message="Error",
            reason=DLQReason.RATE_LIMIT_EXHAUSTED,
            retry_count=1
        )

        await dlq_service.mark_resolved(dlq_id2)

        stats = await dlq_service.get_stats()

        assert stats["total"] == 2

        # Check status counts
        assert stats["by_status"]["pending"] == 1
        assert stats["by_status"]["resolved"] == 1

        # Check reason counts
        assert stats["by_reason"]["timeout"] == 1
        assert stats["by_reason"]["rate_limit_exhausted"] == 1

        # Check job type counts
        assert stats["by_job_type"]["publish_post"] == 1
        assert stats["by_job_type"]["send_dm"] == 1

        # Check oldest/newest
        assert stats["oldest_item"]["dlq_id"] == dlq_id1
        assert stats["newest_item"]["dlq_id"] == dlq_id2

    @pytest.mark.asyncio
    async def test_cleanup_resolved(self, dlq_service):
        """Test cleaning up old resolved items"""
        # Add resolved item from 40 days ago
        dlq_id_old = await dlq_service.add_failed_job(
            job_id="job-old",
            job_type="test",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )
        await dlq_service.mark_resolved(dlq_id_old)

        # Manually set resolved_at to 40 days ago
        item_old = await dlq_service.get_item(dlq_id_old)
        item_old.resolved_at = datetime.now(timezone.utc) - timedelta(days=40)

        # Add recent resolved item (10 days ago)
        dlq_id_recent = await dlq_service.add_failed_job(
            job_id="job-recent",
            job_type="test",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )
        await dlq_service.mark_resolved(dlq_id_recent)
        item_recent = await dlq_service.get_item(dlq_id_recent)
        item_recent.resolved_at = datetime.now(timezone.utc) - timedelta(days=10)

        # Add pending item
        dlq_id_pending = await dlq_service.add_failed_job(
            job_id="job-pending",
            job_type="test",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )

        # Cleanup items older than 30 days
        removed_count = await dlq_service.cleanup_resolved(older_than_days=30)

        assert removed_count == 1

        # Old item should be gone
        assert await dlq_service.get_item(dlq_id_old) is None

        # Recent resolved and pending should still exist
        assert await dlq_service.get_item(dlq_id_recent) is not None
        assert await dlq_service.get_item(dlq_id_pending) is not None

    @pytest.mark.asyncio
    async def test_thread_safety(self, dlq_service):
        """Test concurrent access is thread-safe"""
        async def add_job(job_id):
            await dlq_service.add_failed_job(
                job_id=job_id,
                job_type="test",
                payload={},
                error_message="Error",
                reason=DLQReason.TIMEOUT,
                retry_count=1
            )

        # Add 10 jobs concurrently
        tasks = [add_job(f"job-{i}") for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify all 10 created
        items = await dlq_service.list_items(limit=100)
        assert len(items) == 10


class TestEventPublishing:
    """Test event publishing for alerting and monitoring"""

    @pytest.mark.asyncio
    async def test_item_added_event(self, dlq_service, event_bus):
        """Test item added event published"""
        events = []
        def capture_event(event):
            events.append(event)

        event_bus.subscribe("dlq.item.added", capture_event)

        await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="publish_post",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=3
        )

        await asyncio.sleep(0.1)

        assert len(events) == 1
        assert events[0].payload["job_id"] == "job-123"
        assert events[0].payload["reason"] == "timeout"

    @pytest.mark.asyncio
    async def test_high_priority_alert(self, dlq_service, event_bus):
        """Test high-priority alerts for critical failures"""
        alerts = []
        def capture_alert(event):
            alerts.append(event)

        event_bus.subscribe("dlq.alert", capture_alert)

        # Fatal error should trigger alert
        await dlq_service.add_failed_job(
            job_id="job-fatal",
            job_type="test",
            payload={},
            error_message="Fatal error",
            reason=DLQReason.FATAL_ERROR,
            retry_count=1
        )

        await asyncio.sleep(0.1)

        assert len(alerts) == 1
        assert alerts[0].payload["priority"] == "high"
        assert alerts[0].payload["reason"] == "fatal_error"

    @pytest.mark.asyncio
    async def test_item_retrying_event(self, dlq_service, event_bus):
        """Test retry event published"""
        events = []
        def capture_event(event):
            events.append(event)

        event_bus.subscribe("dlq.item.retrying", capture_event)

        dlq_id = await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="test",
            payload={},
            error_message="Error",
            reason=DLQReason.TIMEOUT,
            retry_count=1
        )

        await dlq_service.retry_item(dlq_id)

        await asyncio.sleep(0.1)

        assert len(events) == 1
        assert events[0].payload["dlq_id"] == dlq_id
        assert events[0].payload["retry_count"] == 2


class TestDLQReasons:
    """Test different failure reasons"""

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, dlq_service):
        """Test job failing after max retries"""
        dlq_id = await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="publish_post",
            payload={},
            error_message="Failed after 5 retries",
            reason=DLQReason.MAX_RETRIES_EXCEEDED,
            retry_count=5
        )

        item = await dlq_service.get_item(dlq_id)
        assert item.reason == DLQReason.MAX_RETRIES_EXCEEDED
        assert item.retry_count == 5

    @pytest.mark.asyncio
    async def test_rate_limit_exhausted(self, dlq_service):
        """Test rate limit exhaustion"""
        dlq_id = await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="send_dm",
            payload={},
            error_message="Rate limit: 429 Too Many Requests",
            reason=DLQReason.RATE_LIMIT_EXHAUSTED,
            retry_count=3
        )

        item = await dlq_service.get_item(dlq_id)
        assert item.reason == DLQReason.RATE_LIMIT_EXHAUSTED

    @pytest.mark.asyncio
    async def test_invalid_input(self, dlq_service):
        """Test invalid input that cannot be retried"""
        dlq_id = await dlq_service.add_failed_job(
            job_id="job-123",
            job_type="test",
            payload={"bad_field": None},
            error_message="Missing required field",
            reason=DLQReason.INVALID_INPUT,
            retry_count=0
        )

        item = await dlq_service.get_item(dlq_id)
        assert item.reason == DLQReason.INVALID_INPUT
        # Invalid input usually abandoned immediately
        await dlq_service.mark_abandoned(dlq_id, "Bad data")
