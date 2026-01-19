"""
Tests for Metrics Snapshot Service (OPS-010)
=============================================
Tests for automatic metrics collection at standard intervals.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from services.metrics_snapshot_service import (
    MetricsSnapshotService,
    CheckbackInterval,
    INTERVAL_HOURS
)
from services.event_bus import Event, Topics


@pytest_asyncio.fixture
async def snapshot_service():
    """Create a fresh snapshot service instance for each test"""
    # Reset singleton
    MetricsSnapshotService._instance = None
    service = MetricsSnapshotService.get_instance()
    await service.start()
    yield service
    await service.stop()


@pytest.mark.asyncio
async def test_snapshot_service_singleton():
    """Test that snapshot service is a singleton"""
    MetricsSnapshotService._instance = None
    service1 = MetricsSnapshotService.get_instance()
    service2 = MetricsSnapshotService.get_instance()
    assert service1 is service2


@pytest.mark.asyncio
async def test_checkback_intervals():
    """Test that all standard checkback intervals are defined"""
    intervals = MetricsSnapshotService.CHECKBACK_INTERVALS

    assert len(intervals) == 5
    assert CheckbackInterval.ONE_HOUR in intervals
    assert CheckbackInterval.SIX_HOURS in intervals
    assert CheckbackInterval.TWENTY_FOUR_HOURS in intervals
    assert CheckbackInterval.SEVENTY_TWO_HOURS in intervals
    assert CheckbackInterval.SEVEN_DAYS in intervals


@pytest.mark.asyncio
async def test_interval_hours_mapping():
    """Test that interval hours are correctly mapped"""
    assert INTERVAL_HOURS[CheckbackInterval.ONE_HOUR] == 1
    assert INTERVAL_HOURS[CheckbackInterval.SIX_HOURS] == 6
    assert INTERVAL_HOURS[CheckbackInterval.TWENTY_FOUR_HOURS] == 24
    assert INTERVAL_HOURS[CheckbackInterval.SEVENTY_TWO_HOURS] == 72
    assert INTERVAL_HOURS[CheckbackInterval.SEVEN_DAYS] == 168


@pytest.mark.asyncio
async def test_schedule_snapshots(snapshot_service):
    """Test scheduling all snapshots for a post"""
    post_id = uuid4()
    published_at = datetime.now(timezone.utc)
    platform = "twitter"
    platform_url = "https://twitter.com/status/123"

    snapshot_ids = await snapshot_service.schedule_snapshots(
        scheduled_post_id=post_id,
        published_at=published_at,
        platform=platform,
        platform_url=platform_url
    )

    # Should schedule 5 snapshots (one for each interval)
    assert len(snapshot_ids) == 5

    # All snapshots should be tracked
    assert len(snapshot_service._scheduled_snapshots) == 5

    # Verify each snapshot
    for snapshot_id in snapshot_ids:
        snapshot = snapshot_service._scheduled_snapshots[snapshot_id]
        assert snapshot.scheduled_post_id == post_id
        assert snapshot.platform == platform
        assert snapshot.platform_url == platform_url
        assert not snapshot.collected


@pytest.mark.asyncio
async def test_snapshot_times_calculated_correctly(snapshot_service):
    """Test that snapshot times are calculated correctly based on intervals"""
    post_id = uuid4()
    published_at = datetime.now(timezone.utc)

    await snapshot_service.schedule_snapshots(
        scheduled_post_id=post_id,
        published_at=published_at,
        platform="twitter",
        platform_url="https://twitter.com/status/123"
    )

    # Check each snapshot has correct time offset
    for snapshot in snapshot_service._scheduled_snapshots.values():
        interval_hours = INTERVAL_HOURS[snapshot.interval]
        expected_time = published_at + timedelta(hours=interval_hours)

        # Allow 1 second tolerance for timing differences
        time_diff = abs((snapshot.snapshot_time - expected_time).total_seconds())
        assert time_diff < 1, f"Time difference too large: {time_diff}s"


@pytest.mark.asyncio
async def test_handle_publish_completed_event(snapshot_service):
    """Test that publish.completed events trigger snapshot scheduling"""
    post_id = uuid4()

    # Create publish completed event
    event = Event(
        topic=Topics.PUBLISH_COMPLETED,
        payload={
            "scheduled_post_id": str(post_id),
            "platform": "instagram",
            "platform_url": "https://instagram.com/p/abc123"
        },
        source="test"
    )

    # Handle the event
    await snapshot_service._handle_publish_completed(event)

    # Should have scheduled 5 snapshots
    assert len(snapshot_service._scheduled_snapshots) == 5


@pytest.mark.asyncio
async def test_snapshot_service_status(snapshot_service):
    """Test that service status is reported correctly"""
    status = snapshot_service.get_status()

    assert status["is_running"] is True
    assert status["total_scheduled"] == 0
    assert status["pending_snapshots"] == 0
    assert status["completed_snapshots"] == 0
    assert status["snapshots_collected"] == 0
    assert status["snapshots_failed"] == 0
    assert status["next_snapshot"] is None
    assert len(status["checkback_intervals"]) == 5


@pytest.mark.asyncio
async def test_snapshot_status_with_scheduled(snapshot_service):
    """Test status when snapshots are scheduled"""
    post_id = uuid4()
    published_at = datetime.now(timezone.utc)

    await snapshot_service.schedule_snapshots(
        scheduled_post_id=post_id,
        published_at=published_at,
        platform="twitter",
        platform_url="https://twitter.com/status/123"
    )

    status = snapshot_service.get_status()

    assert status["total_scheduled"] == 5
    assert status["pending_snapshots"] == 5
    assert status["completed_snapshots"] == 0
    assert status["next_snapshot"] is not None
    assert status["next_snapshot"]["interval"] == "1h"  # First interval
    assert status["next_snapshot"]["platform"] == "twitter"


@pytest.mark.asyncio
async def test_wake_trigger_integration(snapshot_service):
    """Test integration with sleep mode wake triggers"""
    # Skip if sleep service not available
    if not snapshot_service.sleep_service:
        pytest.skip("Sleep service not available")

    post_id = uuid4()
    published_at = datetime.now(timezone.utc)

    # Schedule snapshots
    await snapshot_service.schedule_snapshots(
        scheduled_post_id=post_id,
        published_at=published_at,
        platform="twitter",
        platform_url="https://twitter.com/status/123"
    )

    # Each snapshot should have a wake trigger
    for snapshot in snapshot_service._scheduled_snapshots.values():
        assert snapshot.wake_trigger_id is not None

    # Sleep service should have 5 wake triggers
    sleep_service = snapshot_service.sleep_service
    assert len(sleep_service.wake_triggers) == 5


@pytest.mark.asyncio
async def test_fetch_platform_metrics_placeholder(snapshot_service):
    """Test that platform metrics fetching returns correct structure"""
    metrics = await snapshot_service._fetch_platform_metrics(
        platform="twitter",
        platform_url="https://twitter.com/status/123"
    )

    # Should return all required metric fields
    assert "views" in metrics
    assert "likes" in metrics
    assert "comments" in metrics
    assert "shares" in metrics
    assert "saves" in metrics
    assert "reach" in metrics
    assert "impressions" in metrics
    assert "engagement_rate" in metrics
    assert "watch_time_seconds" in metrics
    assert "avg_view_duration" in metrics


@pytest.mark.asyncio
async def test_multiple_posts_scheduled(snapshot_service):
    """Test scheduling snapshots for multiple posts"""
    post1_id = uuid4()
    post2_id = uuid4()
    post3_id = uuid4()

    published_at = datetime.now(timezone.utc)

    # Schedule for 3 posts
    await snapshot_service.schedule_snapshots(
        scheduled_post_id=post1_id,
        published_at=published_at,
        platform="twitter",
        platform_url="https://twitter.com/status/1"
    )

    await snapshot_service.schedule_snapshots(
        scheduled_post_id=post2_id,
        published_at=published_at,
        platform="instagram",
        platform_url="https://instagram.com/p/2"
    )

    await snapshot_service.schedule_snapshots(
        scheduled_post_id=post3_id,
        published_at=published_at,
        platform="tiktok",
        platform_url="https://tiktok.com/@user/video/3"
    )

    # Should have 15 total snapshots (5 per post × 3 posts)
    assert len(snapshot_service._scheduled_snapshots) == 15

    status = snapshot_service.get_status()
    assert status["total_scheduled"] == 15
    assert status["pending_snapshots"] == 15


@pytest.mark.asyncio
async def test_snapshot_intervals_in_order(snapshot_service):
    """Test that snapshots are ordered by time"""
    post_id = uuid4()
    published_at = datetime.now(timezone.utc)

    await snapshot_service.schedule_snapshots(
        scheduled_post_id=post_id,
        published_at=published_at,
        platform="twitter",
        platform_url="https://twitter.com/status/123"
    )

    # Get snapshots sorted by time
    snapshots = sorted(
        snapshot_service._scheduled_snapshots.values(),
        key=lambda s: s.snapshot_time
    )

    # Verify order
    intervals_in_order = [
        CheckbackInterval.ONE_HOUR,
        CheckbackInterval.SIX_HOURS,
        CheckbackInterval.TWENTY_FOUR_HOURS,
        CheckbackInterval.SEVENTY_TWO_HOURS,
        CheckbackInterval.SEVEN_DAYS,
    ]

    for i, snapshot in enumerate(snapshots):
        assert snapshot.interval == intervals_in_order[i]


@pytest.mark.asyncio
async def test_missing_publish_fields(snapshot_service):
    """Test handling of publish.completed event with missing fields"""
    # Event with missing platform_url
    event = Event(
        topic=Topics.PUBLISH_COMPLETED,
        payload={
            "scheduled_post_id": str(uuid4()),
            "platform": "twitter",
            # Missing: platform_url
        },
        source="test"
    )

    # Should handle gracefully without error
    await snapshot_service._handle_publish_completed(event)

    # No snapshots should be scheduled
    assert len(snapshot_service._scheduled_snapshots) == 0


@pytest.mark.asyncio
async def test_snapshot_service_metrics(snapshot_service):
    """Test that service tracks collection metrics"""
    assert snapshot_service._snapshots_collected == 0
    assert snapshot_service._snapshots_failed == 0

    # These would increment during actual collection
    # (tested in integration tests)


@pytest.mark.asyncio
async def test_checkback_interval_values():
    """Test that checkback interval string values are correct"""
    assert CheckbackInterval.ONE_HOUR.value == "1h"
    assert CheckbackInterval.SIX_HOURS.value == "6h"
    assert CheckbackInterval.TWENTY_FOUR_HOURS.value == "24h"
    assert CheckbackInterval.SEVENTY_TWO_HOURS.value == "72h"
    assert CheckbackInterval.SEVEN_DAYS.value == "7d"


@pytest.mark.asyncio
async def test_service_start_stop(snapshot_service):
    """Test service start and stop lifecycle"""
    assert snapshot_service._is_running is True
    assert snapshot_service._worker_task is not None

    await snapshot_service.stop()

    assert snapshot_service._is_running is False
