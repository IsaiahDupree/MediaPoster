"""
Bandit Allocator Service (AUTO-002)
====================================
Implements Thompson Sampling for automated template allocation.

Uses Bayesian multi-armed bandit algorithm to optimize the 70/20/10 allocation:
- 70% → Top performers (exploit)
- 20% → Promising templates (explore)
- 10% → New experiments (discover)

Thompson Sampling Algorithm:
1. Track wins/losses for each template (based on reward threshold)
2. Model each template as Beta(wins + 1, losses + 1) distribution
3. Sample theta from each Beta distribution
4. Sort templates by sampled theta values
5. Allocate slots: top performers get 70%, middle get 20%, bottom get 10%

Key Improvements Over Simple Ranking:
- Bayesian uncertainty modeling (explores under-tested templates)
- Probabilistic sampling (avoids premature convergence)
- Adaptive learning (continuously updates allocations)
- Statistical confidence (Beta distributions model uncertainty)
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID
import random
import math
from loguru import logger
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import async_session_maker
from database.models import ContentTemplate, Touchpoint
from services.event_bus import EventBus, Topics


@dataclass
class TemplateStats:
    """Statistical tracking for a template"""
    template_id: UUID
    template_name: str
    awareness_level: str

    # Thompson Sampling parameters
    wins: int = 0          # High-reward outcomes
    losses: int = 0        # Low-reward outcomes
    total_uses: int = 0

    # Performance metrics
    avg_reward: float = 0.0
    avg_engagement_rate: float = 0.0

    # Allocation
    allocation: float = 0.0  # Probability of selection
    bucket: str = "untested"  # winner|promising|experiment|untested

    # Thompson Sampling
    theta_sample: float = 0.0  # Sampled success probability
    confidence: float = 0.0    # Statistical confidence (0-1)


class AllocationBucket(Enum):
    """Allocation bucket types"""
    WINNER = "winner"          # Top 70%
    PROMISING = "promising"    # Middle 20%
    EXPERIMENT = "experiment"  # Bottom 10%
    UNTESTED = "untested"     # Too new to classify


class BanditAllocator:
    """
    Bandit Allocator Service

    Uses Thompson Sampling to compute optimal template allocations.

    Usage:
        allocator = BanditAllocator.get_instance()
        await allocator.start()

        # Compute allocations for templates
        allocations = await allocator.compute_allocations(
            awareness_level="problem_aware"
        )

        # Get allocation for specific template
        allocation = await allocator.get_template_allocation(template_id)
    """

    _instance: Optional["BanditAllocator"] = None

    def __init__(self):
        """Initialize bandit allocator"""
        if BanditAllocator._instance is not None:
            raise RuntimeError("Use BanditAllocator.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("bandit-allocator")

        # Allocation weights (70/20/10 strategy)
        self.winner_weight = 0.70      # Top performers
        self.promising_weight = 0.20   # Under-tested promising
        self.experiment_weight = 0.10  # New experiments

        # Thompson Sampling parameters
        self.reward_threshold = 0.5    # Score > 0.5 = win
        self.min_uses_for_confidence = 10  # Minimum uses for statistical confidence
        self.confidence_factor = 0.95  # 95% confidence interval

        # Allocation constraints
        self.min_allocation = 0.01     # Minimum 1% allocation per template
        self.max_allocation = 0.30     # Maximum 30% allocation per template

        # Cache
        self._allocation_cache: Dict[UUID, float] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 3600  # 1 hour cache

        # Background task
        self._recompute_task: Optional[asyncio.Task] = None
        self._is_running = False

        logger.info("🎰 Bandit Allocator Service initialized")

    @classmethod
    def get_instance(cls) -> "BanditAllocator":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the bandit allocator service"""
        if self._is_running:
            logger.warning("Bandit allocator already running")
            return

        self._is_running = True

        # Start background recompute task (every 2 hours)
        self._recompute_task = asyncio.create_task(self._recompute_loop())

        # Subscribe to template leaderboard updates
        self.event_bus.subscribe(
            Topics.TEMPLATE_LEADERBOARD_UPDATED,
            self._handle_leaderboard_updated
        )

        logger.success("✓ Bandit Allocator Service started")

    async def stop(self) -> None:
        """Stop the bandit allocator service"""
        self._is_running = False

        if self._recompute_task:
            self._recompute_task.cancel()
            try:
                await self._recompute_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Bandit Allocator Service stopped")

    async def compute_allocations(
        self,
        awareness_level: Optional[str] = None,
        brand_id: Optional[UUID] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Compute Thompson Sampling allocations for templates

        Args:
            awareness_level: Filter by awareness level (optional)
            brand_id: Filter by brand (optional)
            force_refresh: Force recompute even if cache is valid

        Returns:
            Dictionary with allocation results
        """
        # Check cache
        if not force_refresh and self._is_cache_valid():
            logger.debug("Using cached allocations")
            return self._get_cached_allocations()

        logger.info("🎰 Computing Thompson Sampling allocations...")

        async with async_session_maker() as session:
            # Build query for active templates
            query = select(ContentTemplate).where(ContentTemplate.is_active == True)

            if awareness_level:
                query = query.where(ContentTemplate.awareness_level == awareness_level)

            if brand_id:
                query = query.where(ContentTemplate.brand_id == brand_id)

            result = await session.execute(query)
            templates = result.scalars().all()

            if not templates:
                logger.warning("No templates found for allocation")
                return {"allocations": {}, "stats": []}

            # Compute stats for each template
            template_stats = []

            for template in templates:
                stats = await self._compute_template_stats(session, template)
                template_stats.append(stats)

            # Apply Thompson Sampling
            template_stats = self._apply_thompson_sampling(template_stats)

            # Assign allocation buckets
            template_stats = self._assign_buckets(template_stats)

            # Compute allocation probabilities
            template_stats = self._compute_allocations_from_buckets(template_stats)

            # Apply constraints (min/max)
            template_stats = self._apply_allocation_constraints(template_stats)

            # Update cache
            self._update_cache(template_stats)

            # Emit event
            await self.event_bus.publish(
                Topics.TEMPLATE_LEADERBOARD_UPDATED,
                {
                    "source": "bandit-allocator",
                    "allocations_updated": len(template_stats),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

            logger.success(f"✓ Computed allocations for {len(template_stats)} templates")

            return {
                "allocations": {
                    str(stats.template_id): stats.allocation
                    for stats in template_stats
                },
                "stats": [
                    {
                        "template_id": str(stats.template_id),
                        "template_name": stats.template_name,
                        "awareness_level": stats.awareness_level,
                        "wins": stats.wins,
                        "losses": stats.losses,
                        "total_uses": stats.total_uses,
                        "avg_reward": round(stats.avg_reward, 3),
                        "allocation": round(stats.allocation, 4),
                        "bucket": stats.bucket,
                        "theta_sample": round(stats.theta_sample, 4),
                        "confidence": round(stats.confidence, 3)
                    }
                    for stats in template_stats
                ]
            }

    async def _compute_template_stats(
        self,
        session: AsyncSession,
        template: ContentTemplate
    ) -> TemplateStats:
        """
        Compute Thompson Sampling statistics for a template

        Args:
            session: Database session
            template: Template to analyze

        Returns:
            TemplateStats with wins/losses computed
        """
        # Get all touchpoints for this template
        result = await session.execute(
            select(Touchpoint).where(Touchpoint.template_id == template.id)
        )
        touchpoints = result.scalars().all()

        # Compute wins/losses based on reward threshold
        wins = 0
        losses = 0
        total_reward = 0.0
        total_engagement = 0.0

        for tp in touchpoints:
            if tp.reward_score is not None:
                total_reward += tp.reward_score

                if tp.reward_score >= self.reward_threshold:
                    wins += 1
                else:
                    losses += 1

            if tp.engagement_rate is not None:
                total_engagement += tp.engagement_rate

        total_uses = len(touchpoints)
        avg_reward = total_reward / total_uses if total_uses > 0 else 0.0
        avg_engagement = total_engagement / total_uses if total_uses > 0 else 0.0

        return TemplateStats(
            template_id=template.id,
            template_name=template.name,
            awareness_level=template.awareness_level,
            wins=wins,
            losses=losses,
            total_uses=total_uses,
            avg_reward=avg_reward,
            avg_engagement_rate=avg_engagement
        )

    def _apply_thompson_sampling(
        self,
        template_stats: List[TemplateStats]
    ) -> List[TemplateStats]:
        """
        Apply Thompson Sampling to rank templates

        Uses Beta distribution: Beta(wins + 1, losses + 1)
        Samples theta from distribution to model uncertainty

        Args:
            template_stats: List of template statistics

        Returns:
            List of template stats with theta_sample and confidence
        """
        for stats in template_stats:
            # Beta distribution parameters
            alpha = stats.wins + 1  # Successes
            beta = stats.losses + 1  # Failures

            # Sample theta (success probability) from Beta(alpha, beta)
            stats.theta_sample = self._sample_beta(alpha, beta)

            # Compute confidence (inverse of variance)
            # High confidence = many samples, low variance
            # Low confidence = few samples, high variance
            variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
            stats.confidence = 1.0 / (1.0 + variance * 100)  # Normalize to [0, 1]

            # Clamp confidence to [0, 1]
            stats.confidence = max(0.0, min(1.0, stats.confidence))

        return template_stats

    def _sample_beta(self, alpha: float, beta: float) -> float:
        """
        Sample from Beta distribution

        Uses inverse CDF method for Beta distribution

        Args:
            alpha: Alpha parameter (wins + 1)
            beta: Beta parameter (losses + 1)

        Returns:
            Sampled theta value [0, 1]
        """
        # For computational efficiency, use approximation
        # Beta(alpha, beta) ~ Normal when alpha, beta are large
        if alpha > 30 and beta > 30:
            # Use normal approximation
            mean = alpha / (alpha + beta)
            variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
            stddev = math.sqrt(variance)

            # Sample from normal and clamp to [0, 1]
            sample = random.gauss(mean, stddev)
            return max(0.0, min(1.0, sample))
        else:
            # Use exact Beta sampling via Gamma distributions
            # Beta(alpha, beta) = Gamma(alpha, 1) / (Gamma(alpha, 1) + Gamma(beta, 1))
            gamma_alpha = random.gammavariate(alpha, 1.0)
            gamma_beta = random.gammavariate(beta, 1.0)

            return gamma_alpha / (gamma_alpha + gamma_beta)

    def _assign_buckets(
        self,
        template_stats: List[TemplateStats]
    ) -> List[TemplateStats]:
        """
        Assign allocation buckets based on Thompson Sampling ranks

        Args:
            template_stats: List of template statistics

        Returns:
            List with buckets assigned
        """
        # Sort by theta_sample (descending)
        sorted_stats = sorted(
            template_stats,
            key=lambda s: s.theta_sample,
            reverse=True
        )

        total_templates = len(sorted_stats)

        # Calculate bucket sizes
        winner_count = max(1, int(total_templates * 0.20))  # Top 20%
        promising_count = max(1, int(total_templates * 0.30))  # Next 30%

        for i, stats in enumerate(sorted_stats):
            if stats.total_uses < 5:
                # Too few uses = untested
                stats.bucket = AllocationBucket.UNTESTED.value
            elif i < winner_count:
                stats.bucket = AllocationBucket.WINNER.value
            elif i < (winner_count + promising_count):
                stats.bucket = AllocationBucket.PROMISING.value
            else:
                stats.bucket = AllocationBucket.EXPERIMENT.value

        return sorted_stats

    def _compute_allocations_from_buckets(
        self,
        template_stats: List[TemplateStats]
    ) -> List[TemplateStats]:
        """
        Compute allocation probabilities from buckets

        70% total → winners
        20% total → promising
        10% total → experiments + untested

        Args:
            template_stats: List with buckets assigned

        Returns:
            List with allocations computed
        """
        # Count templates per bucket
        winners = [s for s in template_stats if s.bucket == AllocationBucket.WINNER.value]
        promising = [s for s in template_stats if s.bucket == AllocationBucket.PROMISING.value]
        experiments = [s for s in template_stats if s.bucket == AllocationBucket.EXPERIMENT.value]
        untested = [s for s in template_stats if s.bucket == AllocationBucket.UNTESTED.value]

        # Distribute allocations within buckets
        # Winners: Split 70% proportional to theta_sample
        total_winner_theta = sum(s.theta_sample for s in winners)
        if total_winner_theta > 0:
            for stats in winners:
                stats.allocation = self.winner_weight * (stats.theta_sample / total_winner_theta)

        # Promising: Split 20% equally
        if promising:
            allocation_per_promising = self.promising_weight / len(promising)
            for stats in promising:
                stats.allocation = allocation_per_promising

        # Experiments + Untested: Split 10% equally
        experiment_pool = experiments + untested
        if experiment_pool:
            allocation_per_experiment = self.experiment_weight / len(experiment_pool)
            for stats in experiment_pool:
                stats.allocation = allocation_per_experiment

        return template_stats

    def _apply_allocation_constraints(
        self,
        template_stats: List[TemplateStats]
    ) -> List[TemplateStats]:
        """
        Apply min/max constraints to allocations

        Args:
            template_stats: List with initial allocations

        Returns:
            List with constrained allocations (sums to 1.0)
        """
        # Renormalize to sum to 1.0 FIRST
        total_allocation = sum(s.allocation for s in template_stats)
        if total_allocation > 0:
            for stats in template_stats:
                stats.allocation /= total_allocation

        # Then apply min/max constraints
        for stats in template_stats:
            stats.allocation = max(self.min_allocation, min(self.max_allocation, stats.allocation))

        # Final renormalization after constraints
        total_allocation = sum(s.allocation for s in template_stats)
        if total_allocation > 0:
            for stats in template_stats:
                stats.allocation /= total_allocation

        return template_stats

    def _update_cache(self, template_stats: List[TemplateStats]) -> None:
        """Update allocation cache"""
        self._allocation_cache = {
            stats.template_id: stats.allocation
            for stats in template_stats
        }
        self._cache_timestamp = datetime.now(timezone.utc)

        logger.debug(f"Cache updated with {len(self._allocation_cache)} allocations")

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cache_timestamp or not self._allocation_cache:
            return False

        age_seconds = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
        return age_seconds < self._cache_ttl_seconds

    def _get_cached_allocations(self) -> Dict[str, Any]:
        """Get allocations from cache"""
        return {
            "allocations": {
                str(tid): alloc for tid, alloc in self._allocation_cache.items()
            },
            "stats": [],
            "cached": True,
            "cache_age_seconds": (
                (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
                if self._cache_timestamp else 0
            )
        }

    async def get_template_allocation(self, template_id: UUID) -> float:
        """
        Get allocation probability for a specific template

        Args:
            template_id: Template UUID

        Returns:
            Allocation probability [0, 1]
        """
        # Check cache
        if self._is_cache_valid() and template_id in self._allocation_cache:
            return self._allocation_cache[template_id]

        # Recompute allocations
        await self.compute_allocations(force_refresh=True)

        return self._allocation_cache.get(template_id, 0.0)

    async def _recompute_loop(self) -> None:
        """Background loop to recompute allocations every 2 hours"""
        logger.info("🔁 Bandit allocator recompute loop started")

        while self._is_running:
            try:
                # Recompute allocations
                await self.compute_allocations(force_refresh=True)

                # Sleep for 2 hours
                await asyncio.sleep(2 * 3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in bandit allocator loop: {e}")
                await asyncio.sleep(300)  # Retry after 5 minutes

        logger.info("🛑 Bandit allocator recompute loop stopped")

    async def _handle_leaderboard_updated(self, event: Any) -> None:
        """
        Handle template leaderboard updated events

        Triggers recomputation of allocations
        """
        try:
            logger.info("📊 Template leaderboard updated, recomputing allocations...")
            await self.compute_allocations(force_refresh=True)
        except Exception as e:
            logger.error(f"Error handling leaderboard update: {e}")


def get_bandit_allocator() -> BanditAllocator:
    """Get bandit allocator instance"""
    return BanditAllocator.get_instance()
