"""
Post Tracking Service (PTK-001, PTK-002, PTK-006)
==================================================
Captures and stores URLs of published posts, schedules engagement checkbacks,
and computes performance scores.

Features:
- PTK-001: Post URL Capture System
- PTK-002: Post Reference Database Schema (uses existing models)
- PTK-006: Post Performance Scoring

The service:
1. Captures post URLs from Safari automation and Blotato API
2. Links URLs to internal post records (ScheduledPost, PostedContent)
3. Schedules checkback periods for engagement tracking
4. Computes performance scores based on metrics
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ScheduledPost, PostedContent, ContentMetricsSnapshot
from services.event_bus.bus import EventBus
from services.event_bus.topics import Topics


class PostTracker:
    """
    Post Tracking Service

    Tracks published posts, captures URLs, schedules checkbacks,
    and computes performance scores.

    Usage:
        tracker = PostTracker.get_instance()

        # Capture post URL after publishing
        await tracker.capture_post_url(
            scheduled_post_id=uuid,
            platform_url="https://twitter.com/user/status/123",
            platform_post_id="123"
        )

        # Schedule engagement checkbacks
        await tracker.schedule_checkbacks(scheduled_post_id=uuid)

        # Compute performance score
        score = await tracker.compute_performance_score(scheduled_post_id=uuid)
    """

    _instance: Optional["PostTracker"] = None

    def __init__(self):
        """Initialize post tracker"""
        if PostTracker._instance is not None:
            raise RuntimeError("Use PostTracker.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("post-tracker")

        # Checkback periods (PTK-003)
        self.checkback_periods = [
            timedelta(hours=1),    # 1 hour
            timedelta(hours=6),    # 6 hours
            timedelta(hours=24),   # 1 day
            timedelta(hours=72),   # 3 days
            timedelta(days=7),     # 1 week
        ]

        logger.info("📊 Post Tracker initialized")

    @classmethod
    def get_instance(cls) -> "PostTracker":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def capture_post_url(
        self,
        db: AsyncSession,
        scheduled_post_id: Optional[UUID] = None,
        posted_content_id: Optional[UUID] = None,
        platform_url: Optional[str] = None,
        platform_post_id: Optional[str] = None,
        platform: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Capture and store post URL (PTK-001)

        Args:
            db: Database session
            scheduled_post_id: ID of scheduled post (if applicable)
            posted_content_id: ID of posted content (if applicable)
            platform_url: Public URL to the published post
            platform_post_id: Platform's internal post ID
            platform: Platform name (twitter, instagram, etc.)
            metadata: Additional metadata

        Returns:
            Result dictionary with success status
        """
        try:
            if not platform_url and not platform_post_id:
                raise ValueError("Either platform_url or platform_post_id must be provided")

            # Update ScheduledPost if provided
            if scheduled_post_id:
                result = await db.execute(
                    select(ScheduledPost).where(ScheduledPost.id == scheduled_post_id)
                )
                scheduled_post = result.scalar_one_or_none()

                if scheduled_post:
                    scheduled_post.platform_url = platform_url or scheduled_post.platform_url
                    scheduled_post.platform_post_id = platform_post_id or scheduled_post.platform_post_id
                    scheduled_post.status = 'published'
                    scheduled_post.published_at = datetime.now(timezone.utc)

                    await db.commit()

                    logger.info(
                        f"✓ Post URL captured | Scheduled Post: {scheduled_post_id} | "
                        f"URL: {platform_url}"
                    )

                    # Emit event for post published
                    await self.event_bus.publish(
                        Topics.POST_PUBLISHED,
                        {
                            "scheduled_post_id": str(scheduled_post_id),
                            "platform_url": platform_url,
                            "platform_post_id": platform_post_id,
                            "platform": platform or scheduled_post.platform,
                            "published_at": scheduled_post.published_at.isoformat(),
                            "metadata": metadata or {}
                        }
                    )

                    # Schedule engagement checkbacks (PTK-003)
                    await self.schedule_checkbacks(db, scheduled_post_id)
                else:
                    logger.warning(f"Scheduled post {scheduled_post_id} not found")

            # Update PostedContent if provided
            if posted_content_id:
                result = await db.execute(
                    select(PostedContent).where(PostedContent.id == posted_content_id)
                )
                posted_content = result.scalar_one_or_none()

                if posted_content:
                    posted_content.platform_url = platform_url or posted_content.platform_url
                    posted_content.platform_post_id = platform_post_id or posted_content.platform_post_id
                    posted_content.status = 'published'
                    posted_content.posted_at = datetime.now(timezone.utc)

                    await db.commit()

                    logger.info(
                        f"✓ Post URL captured | Posted Content: {posted_content_id} | "
                        f"URL: {platform_url}"
                    )
                else:
                    logger.warning(f"Posted content {posted_content_id} not found")

            return {
                "success": True,
                "platform_url": platform_url,
                "platform_post_id": platform_post_id,
                "scheduled_post_id": str(scheduled_post_id) if scheduled_post_id else None,
                "posted_content_id": str(posted_content_id) if posted_content_id else None
            }

        except Exception as e:
            logger.error(f"Error capturing post URL: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def schedule_checkbacks(
        self,
        db: AsyncSession,
        scheduled_post_id: UUID
    ) -> List[datetime]:
        """
        Schedule engagement checkback periods (PTK-003)

        Checkback periods:
        - 1 hour after publish
        - 6 hours after publish
        - 24 hours (1 day) after publish
        - 72 hours (3 days) after publish
        - 168 hours (7 days) after publish

        Args:
            db: Database session
            scheduled_post_id: ID of the scheduled post

        Returns:
            List of checkback times
        """
        try:
            # Get the published post
            result = await db.execute(
                select(ScheduledPost).where(ScheduledPost.id == scheduled_post_id)
            )
            scheduled_post = result.scalar_one_or_none()

            if not scheduled_post or not scheduled_post.published_at:
                logger.warning(f"Post {scheduled_post_id} not found or not published yet")
                return []

            published_at = scheduled_post.published_at
            checkback_times = []

            # Calculate checkback times
            for period in self.checkback_periods:
                checkback_time = published_at + period
                checkback_times.append(checkback_time)

                # Emit checkback scheduled event
                await self.event_bus.publish(
                    Topics.CHECKBACK_SCHEDULED,
                    {
                        "scheduled_post_id": str(scheduled_post_id),
                        "platform": scheduled_post.platform,
                        "platform_url": scheduled_post.platform_url,
                        "checkback_time": checkback_time.isoformat(),
                        "hours_after_publish": period.total_seconds() / 3600
                    }
                )

            logger.info(
                f"✓ Checkbacks scheduled | Post: {scheduled_post_id} | "
                f"Periods: {len(checkback_times)}"
            )

            return checkback_times

        except Exception as e:
            logger.error(f"Error scheduling checkbacks: {e}")
            return []

    async def compute_performance_score(
        self,
        db: AsyncSession,
        scheduled_post_id: UUID
    ) -> Optional[float]:
        """
        Compute performance score for a post (PTK-006)

        Score is calculated based on:
        - Engagement rate (likes + comments + shares) / views
        - View velocity (views per hour)
        - Save rate (saves / views)
        - Comment sentiment (if available)

        Score range: 0.0 to 100.0

        Args:
            db: Database session
            scheduled_post_id: ID of the scheduled post

        Returns:
            Performance score (0-100) or None if insufficient data
        """
        try:
            # Get latest metrics snapshot
            result = await db.execute(
                select(ContentMetricsSnapshot)
                .where(ContentMetricsSnapshot.scheduled_post_id == scheduled_post_id)
                .order_by(ContentMetricsSnapshot.snapshot_at.desc())
                .limit(1)
            )
            snapshot = result.scalar_one_or_none()

            if not snapshot:
                logger.debug(f"No metrics snapshot found for post {scheduled_post_id}")
                return None

            # Get the scheduled post for time-based metrics
            result = await db.execute(
                select(ScheduledPost).where(ScheduledPost.id == scheduled_post_id)
            )
            scheduled_post = result.scalar_one_or_none()

            if not scheduled_post or not scheduled_post.published_at:
                return None

            # Calculate time since publish (in hours)
            time_since_publish = (
                datetime.now(timezone.utc) - scheduled_post.published_at
            ).total_seconds() / 3600

            if time_since_publish == 0:
                time_since_publish = 0.1  # Avoid division by zero

            # Calculate component scores
            views = snapshot.views or 0
            likes = snapshot.likes or 0
            comments = snapshot.comments or 0
            shares = snapshot.shares or 0
            saves = snapshot.saves or 0

            # 1. Engagement Rate Score (40 points)
            if views > 0:
                engagement_rate = (likes + comments + shares) / views
                engagement_score = min(engagement_rate * 100, 40)
            else:
                engagement_score = 0

            # 2. View Velocity Score (30 points)
            views_per_hour = views / time_since_publish
            # Normalize: 100 views/hour = 30 points
            velocity_score = min(views_per_hour / 100 * 30, 30)

            # 3. Save Rate Score (20 points)
            if views > 0:
                save_rate = saves / views
                save_score = min(save_rate * 100, 20)
            else:
                save_score = 0

            # 4. Virality Score (10 points)
            if views > 0:
                share_rate = shares / views
                virality_score = min(share_rate * 100, 10)
            else:
                virality_score = 0

            # Total score (0-100)
            total_score = engagement_score + velocity_score + save_score + virality_score

            logger.info(
                f"📊 Performance score computed | Post: {scheduled_post_id} | "
                f"Score: {total_score:.2f} | "
                f"Engagement: {engagement_score:.1f} | "
                f"Velocity: {velocity_score:.1f} | "
                f"Saves: {save_score:.1f} | "
                f"Virality: {virality_score:.1f}"
            )

            return round(total_score, 2)

        except Exception as e:
            logger.error(f"Error computing performance score: {e}")
            return None

    async def get_post_tracking_status(
        self,
        db: AsyncSession,
        scheduled_post_id: UUID
    ) -> Dict[str, Any]:
        """
        Get tracking status for a post

        Args:
            db: Database session
            scheduled_post_id: ID of the scheduled post

        Returns:
            Status dictionary with URL, checkbacks, and score
        """
        try:
            # Get scheduled post
            result = await db.execute(
                select(ScheduledPost).where(ScheduledPost.id == scheduled_post_id)
            )
            scheduled_post = result.scalar_one_or_none()

            if not scheduled_post:
                return {
                    "success": False,
                    "error": "Post not found"
                }

            # Get latest metrics
            result = await db.execute(
                select(ContentMetricsSnapshot)
                .where(ContentMetricsSnapshot.scheduled_post_id == scheduled_post_id)
                .order_by(ContentMetricsSnapshot.snapshot_at.desc())
                .limit(1)
            )
            latest_snapshot = result.scalar_one_or_none()

            # Compute performance score
            performance_score = await self.compute_performance_score(db, scheduled_post_id)

            # Calculate checkback schedule
            checkback_schedule = []
            if scheduled_post.published_at:
                for period in self.checkback_periods:
                    checkback_time = scheduled_post.published_at + period
                    checkback_schedule.append({
                        "time": checkback_time.isoformat(),
                        "hours_after_publish": period.total_seconds() / 3600,
                        "completed": checkback_time < datetime.now(timezone.utc)
                    })

            return {
                "success": True,
                "post_id": str(scheduled_post_id),
                "platform": scheduled_post.platform,
                "platform_url": scheduled_post.platform_url,
                "platform_post_id": scheduled_post.platform_post_id,
                "status": scheduled_post.status,
                "published_at": scheduled_post.published_at.isoformat() if scheduled_post.published_at else None,
                "performance_score": performance_score,
                "latest_metrics": {
                    "views": latest_snapshot.views if latest_snapshot else 0,
                    "likes": latest_snapshot.likes if latest_snapshot else 0,
                    "comments": latest_snapshot.comments if latest_snapshot else 0,
                    "shares": latest_snapshot.shares if latest_snapshot else 0,
                    "saves": latest_snapshot.saves if latest_snapshot else 0,
                    "engagement_rate": latest_snapshot.engagement_rate if latest_snapshot else 0.0,
                    "snapshot_at": latest_snapshot.snapshot_at.isoformat() if latest_snapshot else None
                },
                "checkback_schedule": checkback_schedule
            }

        except Exception as e:
            logger.error(f"Error getting post tracking status: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton accessor
def get_post_tracker() -> PostTracker:
    """Get the singleton post tracker instance"""
    return PostTracker.get_instance()
