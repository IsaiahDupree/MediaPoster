"""
Same-Day Adjustment Service (AUTO-007)
======================================
Adjusts remaining content slots based on early performance of posted content.

Features:
- Monitor early performance (1-3 hours after posting)
- Identify winners and losers
- Adjust remaining slots to prioritize winning templates, topics, formats
- Real-time optimization within the same day

Integration:
- Subscribes to POST_PUBLISHED events
- Monitors metrics at 1h, 3h intervals
- Adjusts slots that haven't been published yet
"""

import os
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from loguru import logger
from sqlalchemy import create_engine, text
from dataclasses import dataclass

from services.event_bus import EventBus, Topics


@dataclass
class PerformanceThreshold:
    """Thresholds for determining content performance"""
    winner_multiplier: float = 1.5  # 50% above average
    loser_multiplier: float = 0.6   # 40% below average
    min_impressions: int = 100      # Min impressions to evaluate


@dataclass
class SlotAdjustment:
    """Represents an adjustment to a scheduled slot"""
    slot_id: str
    original_template_id: Optional[str]
    new_template_id: Optional[str]
    original_topic: Optional[str]
    new_topic: Optional[str]
    reason: str
    confidence: float


class SameDayAdjuster:
    """
    Monitors early content performance and adjusts remaining slots in real-time.

    Workflow:
    1. Track posts as they publish throughout the day
    2. Check 1h and 3h metrics for early signals
    3. Identify patterns: which templates/topics/formats are winning
    4. Adjust remaining unpublished slots to favor winners
    5. Log all adjustments for learning
    """

    _instance: Optional["SameDayAdjuster"] = None

    def __init__(self):
        if SameDayAdjuster._instance is not None:
            raise RuntimeError("Use SameDayAdjuster.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("same-day-adjuster")

        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        )
        self.engine = create_engine(self.database_url)

        # Configuration
        self.check_interval = int(os.getenv("SAME_DAY_CHECK_INTERVAL", "3600"))  # 1 hour
        self.thresholds = PerformanceThreshold()

        # State
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self._monitored_posts: Dict[str, datetime] = {}  # post_id -> published_at

        SameDayAdjuster._instance = self
        logger.info("✓ SameDayAdjuster initialized")

    @classmethod
    def get_instance(cls) -> "SameDayAdjuster":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the same-day adjuster service"""
        if self._is_running:
            logger.warning("⚠️  SameDayAdjuster already running")
            return

        self._is_running = True

        # Subscribe to post published events
        self.event_bus.subscribe(Topics.POST_PUBLISHED, self._on_post_published)

        # Start monitoring loop
        self._task = asyncio.create_task(self._monitoring_loop())

        await self.event_bus.publish(
            Topics.SERVICE_STARTED,
            {"service": "same_day_adjuster"}
        )

        logger.success("🚀 SameDayAdjuster started")

    async def stop(self) -> None:
        """Stop the same-day adjuster service"""
        self._is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self.event_bus.publish(
            Topics.SERVICE_STOPPED,
            {"service": "same_day_adjuster"}
        )

        logger.info("🛑 SameDayAdjuster stopped")

    async def _on_post_published(self, event) -> None:
        """Handle post published event"""
        post_id = event.payload.get("post_id")
        if post_id:
            self._monitored_posts[post_id] = datetime.now(timezone.utc)
            logger.info(f"📊 Monitoring post for same-day adjustment: {post_id}")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.info("🔍 Same-day adjustment monitoring loop started")

        while self._is_running:
            try:
                # Check performance and make adjustments
                await self._check_and_adjust()

                # Wait for next interval
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in same-day adjustment loop: {e}")
                await asyncio.sleep(self.check_interval)

        logger.info("🛑 Same-day adjustment monitoring loop stopped")

    async def _check_and_adjust(self) -> None:
        """Check performance and adjust remaining slots"""
        try:
            # Get today's posts with early metrics
            early_performers = await self._get_early_performance()

            if not early_performers:
                logger.debug("No posts with early performance data today")
                return

            # Analyze performance patterns
            patterns = await self._analyze_patterns(early_performers)

            # Get remaining unpublished slots for today
            remaining_slots = await self._get_remaining_slots()

            if not remaining_slots:
                logger.debug("No remaining slots to adjust today")
                return

            # Make adjustments
            adjustments = await self._generate_adjustments(patterns, remaining_slots)

            if adjustments:
                await self._apply_adjustments(adjustments)
                logger.success(f"✓ Applied {len(adjustments)} same-day adjustments")

        except Exception as e:
            logger.error(f"❌ Error in check_and_adjust: {e}")

    async def _get_early_performance(self) -> List[Dict[str, Any]]:
        """Get performance data for posts published 1-6 hours ago"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        pc.id,
                        pc.platform_post_id,
                        pc.posted_at,
                        pc.views,
                        pc.likes,
                        pc.comments,
                        pc.shares,
                        pc.engagement_rate,
                        pc.platform,
                        pc.title,
                        EXTRACT(EPOCH FROM (NOW() - pc.posted_at)) / 3600 as hours_since_posted
                    FROM posted_content pc
                    WHERE
                        pc.posted_at >= CURRENT_DATE
                        AND pc.posted_at <= NOW() - INTERVAL '1 hour'
                        AND pc.posted_at >= NOW() - INTERVAL '6 hours'
                        AND pc.views >= :min_impressions
                    ORDER BY pc.posted_at DESC
                """), {"min_impressions": self.thresholds.min_impressions})

                posts = []
                for row in result:
                    posts.append({
                        "id": str(row[0]),
                        "platform_post_id": row[1],
                        "posted_at": row[2],
                        "views": row[3] or 0,
                        "likes": row[4] or 0,
                        "comments": row[5] or 0,
                        "shares": row[6] or 0,
                        "saves": 0,
                        "engagement_rate": float(row[7]) if row[7] else 0.0,
                        "template_id": None,
                        "topic": row[9],
                        "content_type": row[8],
                        "awareness_level": "general",
                        "hours_since_posted": float(row[10]) if row[10] else 0
                    })

                return posts
        except Exception as e:
            logger.error(f"❌ Error getting early performance: {e}")
            return []

    async def _analyze_patterns(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance patterns to identify winners and losers"""
        if not posts:
            return {}

        # Calculate average metrics
        avg_views = sum(p["views"] for p in posts) / len(posts)
        avg_engagement = sum(p["engagement_rate"] for p in posts) / len(posts)

        # Identify winners and losers
        winners = []
        losers = []

        for post in posts:
            # Combined score: views + engagement
            score = (post["views"] / max(avg_views, 1)) * 0.6 + \
                   (post["engagement_rate"] / max(avg_engagement, 0.01)) * 0.4

            if score >= self.thresholds.winner_multiplier:
                winners.append(post)
            elif score <= self.thresholds.loser_multiplier:
                losers.append(post)

        # Extract patterns from winners
        winning_templates = [p["template_id"] for p in winners if p.get("template_id")]
        winning_topics = [p["topic"] for p in winners if p.get("topic")]
        winning_awareness = [p["awareness_level"] for p in winners if p.get("awareness_level")]

        losing_templates = [p["template_id"] for p in losers if p.get("template_id")]
        losing_topics = [p["topic"] for p in losers if p.get("topic")]

        patterns = {
            "avg_views": avg_views,
            "avg_engagement": avg_engagement,
            "winner_count": len(winners),
            "loser_count": len(losers),
            "winning_templates": list(set(winning_templates)),
            "winning_topics": list(set(winning_topics)),
            "winning_awareness": list(set(winning_awareness)),
            "losing_templates": list(set(losing_templates)),
            "losing_topics": list(set(losing_topics)),
            "total_analyzed": len(posts)
        }

        logger.info(f"📊 Performance patterns: {patterns['winner_count']} winners, {patterns['loser_count']} losers from {len(posts)} posts")

        return patterns

    async def _get_remaining_slots(self) -> List[Dict[str, Any]]:
        """Get unpublished slots scheduled for today"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        id,
                        scheduled_at,
                        template_id,
                        topic,
                        awareness_level,
                        content_type,
                        platform
                    FROM scheduled_posts
                    WHERE
                        scheduled_at::date = CURRENT_DATE
                        AND scheduled_at > NOW()
                        AND status = 'pending'
                    ORDER BY scheduled_at ASC
                """))

                slots = []
                for row in result:
                    slots.append({
                        "id": str(row[0]),
                        "scheduled_at": row[1],
                        "template_id": str(row[2]) if row[2] else None,
                        "topic": row[3],
                        "awareness_level": row[4],
                        "content_type": row[5],
                        "platform": row[6]
                    })

                return slots
        except Exception as e:
            logger.error(f"❌ Error getting remaining slots: {e}")
            return []

    async def _generate_adjustments(
        self,
        patterns: Dict[str, Any],
        slots: List[Dict[str, Any]]
    ) -> List[SlotAdjustment]:
        """Generate adjustments based on patterns"""
        adjustments = []

        winning_templates = patterns.get("winning_templates", [])
        losing_templates = patterns.get("losing_templates", [])
        winning_topics = patterns.get("winning_topics", [])
        losing_topics = patterns.get("losing_topics", [])

        if not winning_templates and not winning_topics:
            logger.debug("No clear winners to promote")
            return adjustments

        for slot in slots:
            adjustment = None

            # Replace losing templates with winning ones
            if slot.get("template_id") in losing_templates and winning_templates:
                adjustment = SlotAdjustment(
                    slot_id=slot["id"],
                    original_template_id=slot["template_id"],
                    new_template_id=winning_templates[0],  # Use top winner
                    original_topic=slot.get("topic"),
                    new_topic=None,
                    reason="Replacing underperforming template with today's winner",
                    confidence=0.8
                )

            # Replace losing topics with winning ones
            elif slot.get("topic") in losing_topics and winning_topics:
                adjustment = SlotAdjustment(
                    slot_id=slot["id"],
                    original_template_id=slot.get("template_id"),
                    new_template_id=None,
                    original_topic=slot["topic"],
                    new_topic=winning_topics[0],  # Use top winner topic
                    reason="Replacing underperforming topic with today's winner",
                    confidence=0.7
                )

            if adjustment:
                adjustments.append(adjustment)

        return adjustments

    async def _apply_adjustments(self, adjustments: List[SlotAdjustment]) -> None:
        """Apply adjustments to scheduled slots"""
        try:
            with self.engine.connect() as conn:
                for adj in adjustments:
                    updates = []
                    params = {"slot_id": adj.slot_id}

                    if adj.new_template_id:
                        updates.append("template_id = :template_id")
                        params["template_id"] = adj.new_template_id

                    if adj.new_topic:
                        updates.append("topic = :topic")
                        params["topic"] = adj.new_topic

                    if updates:
                        # Update the slot
                        conn.execute(
                            text(f"""
                                UPDATE scheduled_posts
                                SET {', '.join(updates)},
                                    updated_at = NOW()
                                WHERE id = :slot_id
                            """),
                            params
                        )

                        # Log adjustment
                        conn.execute(text("""
                            INSERT INTO slot_adjustments
                            (id, slot_id, adjustment_type, reason, confidence, created_at, metadata)
                            VALUES
                            (gen_random_uuid(), :slot_id, 'same_day', :reason, :confidence, NOW(), :metadata)
                        """), {
                            "slot_id": adj.slot_id,
                            "reason": adj.reason,
                            "confidence": adj.confidence,
                            "metadata": {
                                "original_template": adj.original_template_id,
                                "new_template": adj.new_template_id,
                                "original_topic": adj.original_topic,
                                "new_topic": adj.new_topic
                            }
                        })

                        conn.commit()

                        logger.info(f"✓ Adjusted slot {adj.slot_id}: {adj.reason}")

                        # Emit event
                        await self.event_bus.publish(
                            Topics.SLOT_ADJUSTED,
                            {
                                "slot_id": adj.slot_id,
                                "adjustment_type": "same_day",
                                "reason": adj.reason,
                                "confidence": adj.confidence
                            }
                        )

        except Exception as e:
            logger.error(f"❌ Error applying adjustments: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "is_running": self._is_running,
            "check_interval": self.check_interval,
            "monitored_posts_count": len(self._monitored_posts),
            "thresholds": {
                "winner_multiplier": self.thresholds.winner_multiplier,
                "loser_multiplier": self.thresholds.loser_multiplier,
                "min_impressions": self.thresholds.min_impressions
            }
        }
