"""
Metrics Snapshot Service (OPS-010)
===================================
Automatically collects metrics snapshots at standard intervals after content is published.

Standard Checkback Periods:
- 1h: Early signal (viral potential)
- 6h: Short-term engagement
- 24h: First-day performance
- 72h: 3-day stabilization
- 7d: Week-long performance

Features:
- Schedule snapshot collection for each published post
- Integrate with sleep mode wake triggers
- Store time-series snapshots for growth calculations
- Calculate engagement rates (like_rate, reply_rate, click_rate)
- Support for multiple platforms

Usage:
    from services.metrics_snapshot_service import MetricsSnapshotService

    service = MetricsSnapshotService.get_instance()
    await service.start()

    # Schedule snapshots for a new post
    await service.schedule_snapshots(
        scheduled_post_id="...",
        published_at=datetime.now(timezone.utc),
        platform="twitter",
        platform_url="https://twitter.com/status/123"
    )
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from services.event_bus import EventBus, Topics
from services.sleep_mode_service import SleepModeService, WakeTriggerType
from database.models import ContentMetricsSnapshot, ScheduledPost
from database.connection import async_session_maker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class CheckbackInterval(str, Enum):
    """Standard checkback intervals for metrics collection"""
    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    TWENTY_FOUR_HOURS = "24h"
    SEVENTY_TWO_HOURS = "72h"
    SEVEN_DAYS = "7d"


# Interval to hours mapping
INTERVAL_HOURS = {
    CheckbackInterval.ONE_HOUR: 1,
    CheckbackInterval.SIX_HOURS: 6,
    CheckbackInterval.TWENTY_FOUR_HOURS: 24,
    CheckbackInterval.SEVENTY_TWO_HOURS: 72,
    CheckbackInterval.SEVEN_DAYS: 168,  # 7 * 24
}


@dataclass
class ScheduledSnapshot:
    """A scheduled snapshot collection job"""
    snapshot_id: str
    scheduled_post_id: UUID
    platform: str
    platform_url: str
    interval: CheckbackInterval
    snapshot_time: datetime
    wake_trigger_id: Optional[str] = None
    collected: bool = False
    error: Optional[str] = None


class MetricsSnapshotService:
    """
    Metrics Snapshot Service (OPS-010)

    Automatically schedules and collects metrics snapshots at standard intervals.
    Integrates with Sleep Mode Service to wake the system for snapshot collection.

    Key Features:
    - Schedules snapshots at 1h, 6h, 24h, 72h, 7d after publish
    - Wakes system via sleep mode service for each snapshot
    - Collects metrics from platform APIs
    - Stores time-series data for growth tracking
    - Calculates engagement rates

    Singleton Pattern:
        Use MetricsSnapshotService.get_instance()
    """

    _instance: Optional["MetricsSnapshotService"] = None

    # Standard checkback intervals (matches PRD)
    CHECKBACK_INTERVALS = [
        CheckbackInterval.ONE_HOUR,
        CheckbackInterval.SIX_HOURS,
        CheckbackInterval.TWENTY_FOUR_HOURS,
        CheckbackInterval.SEVENTY_TWO_HOURS,
        CheckbackInterval.SEVEN_DAYS,
    ]

    @classmethod
    def get_instance(cls) -> "MetricsSnapshotService":
        """Get or create singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize the metrics snapshot service"""
        if MetricsSnapshotService._instance is not None:
            raise RuntimeError("Use MetricsSnapshotService.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("metrics-snapshot-service")

        # Lazy-load sleep service (may not be available)
        self._sleep_service: Optional[SleepModeService] = None

        # Track scheduled snapshots
        self._scheduled_snapshots: Dict[str, ScheduledSnapshot] = {}

        # Background worker
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running = False

        # Metrics
        self._snapshots_collected = 0
        self._snapshots_failed = 0

        logger.info("📊 Metrics Snapshot Service initialized")

    @property
    def sleep_service(self) -> Optional[SleepModeService]:
        """Lazy-load sleep mode service"""
        if self._sleep_service is None:
            try:
                self._sleep_service = SleepModeService.get_instance()
            except Exception as e:
                logger.warning(f"Sleep mode service not available: {e}")
        return self._sleep_service

    async def start(self) -> None:
        """Start the metrics snapshot service"""
        if self._is_running:
            logger.warning("Metrics Snapshot Service already running")
            return

        self._is_running = True

        # Subscribe to publish completed events
        self.event_bus.subscribe(
            Topics.PUBLISH_COMPLETED,
            self._handle_publish_completed
        )

        # Start the snapshot collection worker
        self._worker_task = asyncio.create_task(self._snapshot_worker_loop())

        logger.success("✓ Metrics Snapshot Service started")

    async def stop(self) -> None:
        """Stop the metrics snapshot service"""
        self._is_running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Metrics Snapshot Service stopped")

    async def schedule_snapshots(
        self,
        scheduled_post_id: UUID,
        published_at: datetime,
        platform: str,
        platform_url: str
    ) -> List[str]:
        """
        Schedule all snapshot collections for a published post

        Args:
            scheduled_post_id: ID of the scheduled post
            published_at: When the post was published (UTC)
            platform: Platform name (twitter, instagram, etc.)
            platform_url: URL to the published post

        Returns:
            List of snapshot IDs
        """
        snapshot_ids = []

        for interval in self.CHECKBACK_INTERVALS:
            snapshot_id = await self._schedule_snapshot(
                scheduled_post_id=scheduled_post_id,
                published_at=published_at,
                platform=platform,
                platform_url=platform_url,
                interval=interval
            )
            snapshot_ids.append(snapshot_id)

        logger.info(
            f"📊 Scheduled {len(snapshot_ids)} snapshots for post {scheduled_post_id} "
            f"on {platform}"
        )

        return snapshot_ids

    async def _schedule_snapshot(
        self,
        scheduled_post_id: UUID,
        published_at: datetime,
        platform: str,
        platform_url: str,
        interval: CheckbackInterval
    ) -> str:
        """
        Schedule a single snapshot collection

        Args:
            scheduled_post_id: ID of the scheduled post
            published_at: When the post was published
            platform: Platform name
            platform_url: URL to the post
            interval: Checkback interval

        Returns:
            Snapshot ID
        """
        import uuid
        snapshot_id = str(uuid.uuid4())

        # Calculate snapshot time
        hours_offset = INTERVAL_HOURS[interval]
        snapshot_time = published_at + timedelta(hours=hours_offset)

        # Create scheduled snapshot
        scheduled_snapshot = ScheduledSnapshot(
            snapshot_id=snapshot_id,
            scheduled_post_id=scheduled_post_id,
            platform=platform,
            platform_url=platform_url,
            interval=interval,
            snapshot_time=snapshot_time
        )

        self._scheduled_snapshots[snapshot_id] = scheduled_snapshot

        # Schedule wake trigger with sleep service (SLEEP-005 integration)
        if self.sleep_service:
            try:
                wake_trigger_id = self.sleep_service.schedule_wake(
                    wake_time=snapshot_time,
                    trigger_type=WakeTriggerType.CHECKBACK_PERIOD,
                    metadata={
                        "snapshot_id": snapshot_id,
                        "scheduled_post_id": str(scheduled_post_id),
                        "platform": platform,
                        "interval": interval.value,
                        "platform_url": platform_url
                    }
                )
                scheduled_snapshot.wake_trigger_id = wake_trigger_id

                logger.debug(
                    f"⏰ Scheduled wake for snapshot {snapshot_id} at {snapshot_time.isoformat()} "
                    f"({interval.value})"
                )
            except Exception as e:
                logger.warning(f"Failed to schedule wake trigger for snapshot: {e}")

        return snapshot_id

    async def _handle_publish_completed(self, event: Any) -> None:
        """
        Handle PUBLISH_COMPLETED events by scheduling snapshots

        Args:
            event: The publish.completed event
        """
        try:
            payload = event.payload if hasattr(event, 'payload') else event

            scheduled_post_id = payload.get('scheduled_post_id')
            platform = payload.get('platform')
            platform_url = payload.get('platform_url')

            if not all([scheduled_post_id, platform, platform_url]):
                logger.warning("Missing required fields in publish.completed event")
                return

            # Use current time as published_at
            published_at = datetime.now(timezone.utc)

            # Schedule all snapshots
            await self.schedule_snapshots(
                scheduled_post_id=UUID(scheduled_post_id),
                published_at=published_at,
                platform=platform,
                platform_url=platform_url
            )

        except Exception as e:
            logger.error(f"Error handling publish completed event: {e}")

    async def _snapshot_worker_loop(self) -> None:
        """
        Background worker that collects due snapshots

        Runs every minute to check for due snapshots.
        """
        logger.info("📊 Snapshot worker started")

        while self._is_running:
            try:
                now = datetime.now(timezone.utc)

                # Find due snapshots
                due_snapshots = [
                    snapshot for snapshot in self._scheduled_snapshots.values()
                    if not snapshot.collected and snapshot.snapshot_time <= now
                ]

                # Collect each due snapshot
                for snapshot in due_snapshots:
                    try:
                        await self._collect_snapshot(snapshot)
                    except Exception as e:
                        logger.error(
                            f"Error collecting snapshot {snapshot.snapshot_id}: {e}"
                        )
                        snapshot.error = str(e)
                        snapshot.collected = True  # Mark as done to avoid retry loop
                        self._snapshots_failed += 1

                # Clean up old completed snapshots (keep for 7 days)
                cutoff = now - timedelta(days=7)
                old_snapshots = [
                    sid for sid, snap in self._scheduled_snapshots.items()
                    if snap.collected and snap.snapshot_time < cutoff
                ]
                for sid in old_snapshots:
                    del self._scheduled_snapshots[sid]

                # Sleep for 1 minute before next check
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in snapshot worker loop: {e}")
                await asyncio.sleep(60)

        logger.info("🛑 Snapshot worker stopped")

    async def _collect_snapshot(self, snapshot: ScheduledSnapshot) -> None:
        """
        Collect a metrics snapshot for a post

        Args:
            snapshot: The scheduled snapshot to collect
        """
        logger.info(
            f"📊 Collecting {snapshot.interval.value} snapshot for post "
            f"{snapshot.scheduled_post_id} on {snapshot.platform}"
        )

        # Fetch metrics from platform
        metrics = await self._fetch_platform_metrics(
            platform=snapshot.platform,
            platform_url=snapshot.platform_url
        )

        # Store snapshot in database
        async with async_session_maker() as session:
            await self._store_snapshot(
                session=session,
                snapshot=snapshot,
                metrics=metrics
            )

        # Mark as collected
        snapshot.collected = True
        self._snapshots_collected += 1

        # Emit metrics updated event
        await self.event_bus.publish(
            Topics.METRICS_UPDATED,
            {
                "scheduled_post_id": str(snapshot.scheduled_post_id),
                "platform": snapshot.platform,
                "interval": snapshot.interval.value,
                "snapshot_id": snapshot.snapshot_id,
                "metrics": metrics
            }
        )

        logger.success(
            f"✓ Collected {snapshot.interval.value} snapshot for post "
            f"{snapshot.scheduled_post_id}"
        )

    async def _fetch_platform_metrics(
        self,
        platform: str,
        platform_url: str
    ) -> Dict[str, Any]:
        """
        Fetch metrics from platform API

        Args:
            platform: Platform name
            platform_url: URL to the post

        Returns:
            Metrics dictionary
        """
        # TODO: Integrate with platform-specific APIs
        # For now, return mock data
        # In production, this would call:
        # - Twitter API
        # - Instagram Graph API
        # - TikTok API
        # - YouTube Analytics API
        # - etc.

        logger.debug(f"Fetching metrics from {platform} for {platform_url}")

        # Placeholder implementation
        # Will be replaced with actual platform API calls
        return {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "saves": 0,
            "reach": 0,
            "impressions": 0,
            "engagement_rate": 0.0,
            "watch_time_seconds": 0,
            "avg_view_duration": 0.0
        }

    async def _store_snapshot(
        self,
        session: AsyncSession,
        snapshot: ScheduledSnapshot,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Store metrics snapshot in database

        Args:
            session: Database session
            snapshot: The scheduled snapshot
            metrics: Collected metrics
        """
        snapshot_record = ContentMetricsSnapshot(
            scheduled_post_id=snapshot.scheduled_post_id,
            platform=snapshot.platform,
            views=metrics.get("views", 0),
            likes=metrics.get("likes", 0),
            comments=metrics.get("comments", 0),
            shares=metrics.get("shares", 0),
            saves=metrics.get("saves", 0),
            reach=metrics.get("reach", 0),
            impressions=metrics.get("impressions", 0),
            engagement_rate=metrics.get("engagement_rate", 0.0),
            watch_time_seconds=metrics.get("watch_time_seconds", 0),
            avg_view_duration=metrics.get("avg_view_duration", 0.0),
            snapshot_at=snapshot.snapshot_time,
            data_source="api"
        )

        session.add(snapshot_record)
        await session.commit()

        logger.debug(
            f"💾 Stored snapshot for post {snapshot.scheduled_post_id} "
            f"({snapshot.interval.value})"
        )

    def get_status(self) -> Dict[str, Any]:
        """
        Get service status

        Returns:
            Status dictionary
        """
        now = datetime.now(timezone.utc)

        # Count scheduled snapshots by state
        pending = [s for s in self._scheduled_snapshots.values() if not s.collected]
        completed = [s for s in self._scheduled_snapshots.values() if s.collected]

        # Get next due snapshot
        next_snapshot = None
        if pending:
            next_snap = min(pending, key=lambda s: s.snapshot_time)
            next_snapshot = {
                "snapshot_id": next_snap.snapshot_id,
                "scheduled_post_id": str(next_snap.scheduled_post_id),
                "platform": next_snap.platform,
                "interval": next_snap.interval.value,
                "snapshot_time": next_snap.snapshot_time.isoformat(),
                "seconds_until": (next_snap.snapshot_time - now).total_seconds()
            }

        return {
            "is_running": self._is_running,
            "total_scheduled": len(self._scheduled_snapshots),
            "pending_snapshots": len(pending),
            "completed_snapshots": len(completed),
            "snapshots_collected": self._snapshots_collected,
            "snapshots_failed": self._snapshots_failed,
            "next_snapshot": next_snapshot,
            "checkback_intervals": [i.value for i in self.CHECKBACK_INTERVALS]
        }
