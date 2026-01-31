"""
Template Leaderboard Service (OPS-007)
=======================================
Ranks templates by performance using reward scores and engagement metrics.

Implements bandit allocation strategy:
- 70% → Top performers (exploit)
- 20% → Promising but under-tested (explore)
- 10% → Experiments (new templates)

Performance Labels:
- WINNER: Top 20% performers, high confidence (>10 uses)
- PROMISING: Above average, needs more data (5-10 uses)
- AVERAGE: Middle 60%, adequate performance
- LOSER: Bottom 20%, consistently underperforming
- UNTESTED: <5 uses, insufficient data

Ranking Algorithm:
1. Calculate reward scores from touchpoints
2. Apply confidence penalty for low sample size
3. Group by awareness level and channel
4. Assign performance labels
5. Update template metadata
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from uuid import UUID
from loguru import logger
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import async_session_maker
from database.models import ContentTemplate, Touchpoint
from services.event_bus import EventBus, Topics


class PerformanceLabel(Enum):
    """Template performance classification"""
    WINNER = "winner"          # Top 20%, proven winners
    PROMISING = "promising"    # Above average, needs more data
    AVERAGE = "average"        # Middle 60%
    LOSER = "loser"           # Bottom 20%, consistently bad
    UNTESTED = "untested"     # <5 uses, insufficient data


class TemplateLeaderboard:
    """
    Template Leaderboard Service

    Ranks templates by performance and assigns bandit allocation weights.

    Usage:
        leaderboard = TemplateLeaderboard.get_instance()
        await leaderboard.start()

        # Get top templates for a channel
        top_templates = await leaderboard.get_top_templates(
            channel="twitter",
            awareness_level="problem_aware",
            limit=10
        )

        # Sample template using bandit allocation
        template_id = await leaderboard.sample_template(
            channel="twitter",
            awareness_level="solution_aware"
        )

        # Recompute rankings
        await leaderboard.recompute_rankings()
    """

    _instance: Optional["TemplateLeaderboard"] = None

    def __init__(self):
        """Initialize template leaderboard service"""
        if TemplateLeaderboard._instance is not None:
            raise RuntimeError("Use TemplateLeaderboard.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("template-leaderboard")

        # Bandit allocation weights
        self.exploit_weight = 0.70  # Top performers
        self.explore_weight = 0.20  # Promising
        self.experiment_weight = 0.10  # Untested/new

        # Performance thresholds
        self.min_uses_for_confidence = 5  # Minimum uses to exit UNTESTED
        self.high_confidence_uses = 10    # Uses for full confidence

        # Percentile thresholds
        self.winner_percentile = 0.80    # Top 20%
        self.loser_percentile = 0.20     # Bottom 20%

        # Background task
        self._recompute_task: Optional[asyncio.Task] = None
        self._is_running = False

        logger.info("📊 Template Leaderboard Service initialized")

    @classmethod
    def get_instance(cls) -> "TemplateLeaderboard":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the leaderboard service"""
        if self._is_running:
            logger.warning("Template leaderboard already running")
            return

        self._is_running = True

        # Start background recompute task (every 6 hours)
        self._recompute_task = asyncio.create_task(self._recompute_loop())

        logger.success("✓ Template Leaderboard Service started")

    async def stop(self) -> None:
        """Stop the leaderboard service"""
        self._is_running = False

        if self._recompute_task:
            self._recompute_task.cancel()
            try:
                await self._recompute_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Template Leaderboard Service stopped")

    async def recompute_rankings(self) -> Dict[str, Any]:
        """
        Recompute template rankings and performance labels

        Returns:
            Summary of updated templates
        """
        logger.info("🔄 Recomputing template rankings...")

        if async_session_maker is None:
            logger.warning("Database not initialized, skipping recompute")
            return {"updated": 0, "templates": [], "error": "db_not_initialized"}

        async with async_session_maker() as session:
            # Get all active templates
            result = await session.execute(
                select(ContentTemplate).where(ContentTemplate.is_active == True)
            )
            templates = result.scalars().all()

            if not templates:
                logger.warning("No active templates found")
                return {"updated": 0, "templates": []}

            # Update each template
            updated_count = 0
            updated_templates = []

            for template in templates:
                # Get touchpoints for this template
                touchpoints_result = await session.execute(
                    select(Touchpoint).where(
                        Touchpoint.template_id == template.id
                    )
                )
                touchpoints = touchpoints_result.scalars().all()

                # Calculate average reward score
                usage_count = len(touchpoints)

                if usage_count == 0:
                    avg_reward = 0.0
                    label = PerformanceLabel.UNTESTED
                else:
                    reward_scores = [tp.reward_score for tp in touchpoints if tp.reward_score is not None]
                    avg_reward = sum(reward_scores) / len(reward_scores) if reward_scores else 0.0

                    # Apply confidence penalty for low sample size
                    if usage_count < self.min_uses_for_confidence:
                        confidence_factor = usage_count / self.min_uses_for_confidence
                        avg_reward *= confidence_factor
                        label = PerformanceLabel.UNTESTED
                    else:
                        # Assign label based on percentile ranking
                        label = await self._get_performance_label(
                            session,
                            template,
                            avg_reward,
                            usage_count
                        )

                # Update template
                template.usage_count = usage_count
                template.avg_reward_score = avg_reward
                template.performance_label = label.value
                template.updated_at = datetime.now(timezone.utc)

                updated_count += 1
                updated_templates.append({
                    "template_id": str(template.id),
                    "name": template.name,
                    "usage_count": usage_count,
                    "avg_reward_score": round(avg_reward, 3),
                    "performance_label": label.value
                })

            await session.commit()

        logger.success(f"✓ Updated {updated_count} templates")

        # Emit event
        await self.event_bus.publish(
            Topics.TEMPLATE_LEADERBOARD_UPDATED,
            {
                "updated_count": updated_count,
                "templates": updated_templates[:10],  # Top 10 for logging
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        return {
            "updated": updated_count,
            "templates": updated_templates
        }

    async def _get_performance_label(
        self,
        session: AsyncSession,
        template: ContentTemplate,
        avg_reward: float,
        usage_count: int
    ) -> PerformanceLabel:
        """
        Determine performance label based on percentile ranking

        Args:
            session: Database session
            template: Template to classify
            avg_reward: Average reward score
            usage_count: Number of uses

        Returns:
            Performance label
        """
        # Get all templates with same awareness level and sufficient data
        result = await session.execute(
            select(ContentTemplate).where(
                and_(
                    ContentTemplate.is_active == True,
                    ContentTemplate.awareness_level == template.awareness_level,
                    ContentTemplate.usage_count >= self.min_uses_for_confidence
                )
            )
        )
        similar_templates = result.scalars().all()

        if len(similar_templates) < 5:
            # Not enough data for percentile ranking
            return PerformanceLabel.AVERAGE

        # Calculate percentile
        scores = sorted([t.avg_reward_score for t in similar_templates])
        percentile_index = sum(1 for s in scores if s < avg_reward) / len(scores)

        # Assign label
        if percentile_index >= self.winner_percentile:
            return PerformanceLabel.WINNER
        elif percentile_index <= self.loser_percentile:
            return PerformanceLabel.LOSER
        elif avg_reward > sum(scores) / len(scores):  # Above average
            return PerformanceLabel.PROMISING
        else:
            return PerformanceLabel.AVERAGE

    async def get_top_templates(
        self,
        channel: Optional[str] = None,
        awareness_level: Optional[str] = None,
        brand_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top performing templates

        Args:
            channel: Filter by channel (optional)
            awareness_level: Filter by awareness level (optional)
            brand_id: Filter by brand (optional)
            limit: Maximum number of templates to return

        Returns:
            List of template dictionaries, ordered by performance
        """
        async with async_session_maker() as session:
            # Build query
            query = select(ContentTemplate).where(ContentTemplate.is_active == True)

            if brand_id:
                query = query.where(ContentTemplate.brand_id == brand_id)

            if awareness_level:
                query = query.where(ContentTemplate.awareness_level == awareness_level)

            # Order by reward score, usage count
            query = query.order_by(
                ContentTemplate.avg_reward_score.desc(),
                ContentTemplate.usage_count.desc()
            ).limit(limit)

            result = await session.execute(query)
            templates = result.scalars().all()

            return [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "awareness_level": t.awareness_level,
                    "avg_reward_score": round(t.avg_reward_score, 3),
                    "usage_count": t.usage_count,
                    "performance_label": t.performance_label,
                    "fate_weights": {
                        "focus": t.fate_focus,
                        "authority": t.fate_authority,
                        "tribe": t.fate_tribe,
                        "emotion": t.fate_emotion
                    }
                }
                for t in templates
            ]

    async def sample_template(
        self,
        channel: str,
        awareness_level: str,
        brand_id: Optional[UUID] = None,
        exclude_template_ids: Optional[List[UUID]] = None
    ) -> Optional[UUID]:
        """
        Sample a template using bandit allocation strategy

        70% → Winners (exploit)
        20% → Promising (explore)
        10% → Untested (experiment)

        Args:
            channel: Channel to sample for
            awareness_level: Awareness level to match
            brand_id: Optional brand filter
            exclude_template_ids: Templates to exclude

        Returns:
            Template ID or None if no templates available
        """
        import random

        async with async_session_maker() as session:
            # Build base query
            query = select(ContentTemplate).where(
                and_(
                    ContentTemplate.is_active == True,
                    ContentTemplate.awareness_level == awareness_level
                )
            )

            if brand_id:
                query = query.where(ContentTemplate.brand_id == brand_id)

            if exclude_template_ids:
                query = query.where(~ContentTemplate.id.in_(exclude_template_ids))

            # Determine allocation bucket
            roll = random.random()

            if roll < self.exploit_weight:
                # 70% → Winners
                templates_result = await session.execute(
                    query.where(ContentTemplate.performance_label == PerformanceLabel.WINNER.value)
                    .order_by(ContentTemplate.avg_reward_score.desc())
                )
                templates = templates_result.scalars().all()

                if not templates:
                    # Fallback to promising if no winners
                    templates_result = await session.execute(
                        query.where(ContentTemplate.performance_label == PerformanceLabel.PROMISING.value)
                    )
                    templates = templates_result.scalars().all()

            elif roll < (self.exploit_weight + self.explore_weight):
                # 20% → Promising
                templates_result = await session.execute(
                    query.where(ContentTemplate.performance_label == PerformanceLabel.PROMISING.value)
                    .order_by(ContentTemplate.usage_count.asc())  # Prioritize under-tested
                )
                templates = templates_result.scalars().all()

                if not templates:
                    # Fallback to average
                    templates_result = await session.execute(
                        query.where(ContentTemplate.performance_label == PerformanceLabel.AVERAGE.value)
                    )
                    templates = templates_result.scalars().all()

            else:
                # 10% → Experiments (untested)
                templates_result = await session.execute(
                    query.where(ContentTemplate.performance_label == PerformanceLabel.UNTESTED.value)
                    .order_by(ContentTemplate.created_at.desc())  # Newest first
                )
                templates = templates_result.scalars().all()

                if not templates:
                    # Fallback to any template
                    templates_result = await session.execute(query)
                    templates = templates_result.scalars().all()

            if not templates:
                logger.warning(
                    f"No templates found for channel={channel}, "
                    f"awareness_level={awareness_level}"
                )
                return None

            # Random selection from bucket
            selected_template = random.choice(templates)

            logger.info(
                f"📝 Sampled template: {selected_template.name} "
                f"(label={selected_template.performance_label}, "
                f"score={selected_template.avg_reward_score:.3f})"
            )

            return selected_template.id

    async def _recompute_loop(self) -> None:
        """Background loop to recompute rankings every 6 hours"""
        logger.info("🔁 Template leaderboard recompute loop started")

        while self._is_running:
            try:
                # Recompute rankings
                await self.recompute_rankings()

                # Sleep for 6 hours
                await asyncio.sleep(6 * 3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recompute loop: {e}")
                await asyncio.sleep(600)  # Retry in 10 minutes

        logger.info("🛑 Template leaderboard recompute loop stopped")


# Singleton getter function
_leaderboard_instance: Optional[TemplateLeaderboard] = None

def get_template_leaderboard() -> TemplateLeaderboard:
    """Get singleton TemplateLeaderboard instance"""
    global _leaderboard_instance
    if _leaderboard_instance is None:
        _leaderboard_instance = TemplateLeaderboard.get_instance()
    return _leaderboard_instance
