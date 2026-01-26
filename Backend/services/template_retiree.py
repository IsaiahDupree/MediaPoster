"""
Template Retiree Service (AUTO-004)
====================================
Automatically retire losing templates with < 5% allocation.

When a template consistently receives minimal allocation from the bandit
allocator (< 5% for multiple consecutive evaluation cycles), this service
automatically deactivates it to clean up the template pool.

Retirement Criteria:
- Allocation < 5% for 3+ consecutive evaluation cycles
- Minimum 50 uses (must have sufficient data)
- Not manually created in last 30 days (grace period for new templates)

Retired templates are deactivated (is_active = False) but preserved for
analysis. They can be manually reactivated if needed.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass
from uuid import UUID
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import async_session_maker
from database.models import ContentTemplate
from services.event_bus import EventBus, Topics
from services.bandit_allocator import BanditAllocator


@dataclass
class RetirementCandidate:
    """Template candidate for retirement"""
    template_id: UUID
    template_name: str
    allocation: float
    usage_count: int
    created_at: datetime
    consecutive_low_cycles: int


class TemplateRetiree:
    """
    Template Retiree Service

    Automatically retires consistently low-performing templates.

    Usage:
        retiree = TemplateRetiree.get_instance()
        await retiree.start()

        # Manually check for retirement candidates
        candidates = await retiree.get_retirement_candidates()

        # Manually retire a template
        success = await retiree.retire_template(template_id, reason="Manual retirement")
    """

    _instance: Optional["TemplateRetiree"] = None

    def __init__(self):
        """Initialize template retiree"""
        if TemplateRetiree._instance is not None:
            raise RuntimeError("Use TemplateRetiree.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("template-retiree")

        self.bandit_allocator = BanditAllocator.get_instance()

        # Retirement criteria
        self.allocation_threshold = 0.05    # < 5% allocation
        self.min_uses_for_retirement = 50   # Minimum uses before considering retirement
        self.grace_period_days = 30         # New templates get 30-day grace period
        self.consecutive_cycles_required = 3  # Must be low for 3+ cycles

        # Tracking
        self._low_allocation_history: Dict[UUID, List[datetime]] = {}  # template_id -> timestamps

        # Background task
        self._retirement_task: Optional[asyncio.Task] = None
        self._is_running = False

        logger.info("🏁 Template Retiree Service initialized")

    @classmethod
    def get_instance(cls) -> "TemplateRetiree":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the retiree service"""
        if self._is_running:
            logger.warning("Template retiree already running")
            return

        self._is_running = True

        # Start background retirement check task (every 24 hours)
        self._retirement_task = asyncio.create_task(self._retirement_loop())

        # Subscribe to template leaderboard updates
        self.event_bus.subscribe(
            Topics.TEMPLATE_LEADERBOARD_UPDATED,
            self._handle_leaderboard_updated
        )

        logger.success("✓ Template Retiree Service started")

    async def stop(self) -> None:
        """Stop the retiree service"""
        self._is_running = False

        if self._retirement_task:
            self._retirement_task.cancel()
            try:
                await self._retirement_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Template Retiree Service stopped")

    async def get_retirement_candidates(self) -> List[RetirementCandidate]:
        """
        Get templates that are candidates for retirement

        Returns:
            List of retirement candidates with their metrics
        """
        candidates = []

        async with async_session_maker() as session:
            # Get all active templates with sufficient usage
            result = await session.execute(
                select(ContentTemplate).where(
                    ContentTemplate.is_active == True,
                    ContentTemplate.usage_count >= self.min_uses_for_retirement
                )
            )
            templates = result.scalars().all()

            if not templates:
                return candidates

            # Get current allocations from bandit allocator
            allocations = await self.bandit_allocator.compute_allocations()

            # Check each template
            for template in templates:
                # Skip templates in grace period
                if self._in_grace_period(template):
                    continue

                # Get allocation
                allocation = allocations['allocations'].get(str(template.id), 0.0)

                # Check if below threshold
                if allocation < self.allocation_threshold:
                    # Count consecutive low cycles
                    consecutive_cycles = self._count_consecutive_low_cycles(template.id)

                    # Add to candidates if meets criteria
                    if consecutive_cycles >= self.consecutive_cycles_required:
                        candidates.append(RetirementCandidate(
                            template_id=template.id,
                            template_name=template.name,
                            allocation=allocation,
                            usage_count=template.usage_count,
                            created_at=template.created_at,
                            consecutive_low_cycles=consecutive_cycles
                        ))

        return candidates

    async def retire_template(
        self,
        template_id: UUID,
        reason: Optional[str] = None
    ) -> bool:
        """
        Retire (deactivate) a template

        Args:
            template_id: Template UUID to retire
            reason: Optional retirement reason

        Returns:
            True if retired successfully, False otherwise
        """
        async with async_session_maker() as session:
            try:
                # Load template
                result = await session.execute(
                    select(ContentTemplate).where(ContentTemplate.id == template_id)
                )
                template = result.scalar_one_or_none()

                if not template:
                    logger.error(f"Template {template_id} not found")
                    return False

                if not template.is_active:
                    logger.warning(f"Template {template_id} already retired")
                    return False

                # Deactivate template
                await session.execute(
                    update(ContentTemplate)
                    .where(ContentTemplate.id == template_id)
                    .values(
                        is_active=False,
                        performance_label='retired'
                    )
                )

                await session.commit()

                # Emit event
                await self.event_bus.publish(
                    Topics.TEMPLATE_RETIRED,
                    {
                        "template_id": str(template_id),
                        "template_name": template.name,
                        "reason": reason or "Low allocation",
                        "allocation": self.bandit_allocator._allocation_cache.get(template_id, 0.0),
                        "usage_count": template.usage_count,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )

                logger.success(f"✓ Retired template {template.name} ({template_id})")
                return True

            except Exception as e:
                logger.error(f"Error retiring template {template_id}: {e}")
                await session.rollback()
                return False

    def _in_grace_period(self, template: ContentTemplate) -> bool:
        """Check if template is still in grace period"""
        if not template.created_at:
            return False

        age_days = (datetime.now(timezone.utc) - template.created_at).days
        return age_days < self.grace_period_days

    def _count_consecutive_low_cycles(self, template_id: UUID) -> int:
        """Count consecutive evaluation cycles with low allocation"""
        if template_id not in self._low_allocation_history:
            return 0

        history = self._low_allocation_history[template_id]

        # Count recent consecutive timestamps (within last 7 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent = [ts for ts in history if ts >= cutoff]

        return len(recent)

    def _record_low_allocation(self, template_id: UUID) -> None:
        """Record that template had low allocation in this cycle"""
        if template_id not in self._low_allocation_history:
            self._low_allocation_history[template_id] = []

        self._low_allocation_history[template_id].append(datetime.now(timezone.utc))

        # Keep only last 10 timestamps
        self._low_allocation_history[template_id] = self._low_allocation_history[template_id][-10:]

    def _clear_low_allocation(self, template_id: UUID) -> None:
        """Clear low allocation history (template recovered)"""
        if template_id in self._low_allocation_history:
            del self._low_allocation_history[template_id]

    async def _retirement_loop(self) -> None:
        """Background loop to check for retirement candidates"""
        logger.info("🔁 Template retirement loop started")

        while self._is_running:
            try:
                # Check for retirement candidates
                await self._check_and_retire()

                # Sleep for 24 hours
                await asyncio.sleep(24 * 3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retirement loop: {e}")
                await asyncio.sleep(3600)  # Retry after 1 hour

        logger.info("🛑 Template retirement loop stopped")

    async def _check_and_retire(self) -> None:
        """Check for and retire eligible templates"""
        logger.info("🔍 Checking for templates to retire...")

        candidates = await self.get_retirement_candidates()

        if not candidates:
            logger.debug("No templates eligible for retirement")
            return

        retirement_count = 0

        for candidate in candidates:
            # Auto-retire if meets all criteria
            reason = (
                f"Low allocation ({candidate.allocation:.1%}) for "
                f"{candidate.consecutive_low_cycles} consecutive cycles"
            )

            success = await self.retire_template(
                template_id=candidate.template_id,
                reason=reason
            )

            if success:
                retirement_count += 1

        logger.success(f"✓ Retired {retirement_count} templates")

    async def _handle_leaderboard_updated(self, event: dict) -> None:
        """
        Handle template leaderboard updated events

        Updates low allocation tracking
        """
        try:
            logger.debug("📊 Template leaderboard updated, updating retirement tracking...")

            # Get current allocations
            allocations = await self.bandit_allocator.compute_allocations()

            async with async_session_maker() as session:
                # Get all active templates
                result = await session.execute(
                    select(ContentTemplate).where(
                        ContentTemplate.is_active == True,
                        ContentTemplate.usage_count >= self.min_uses_for_retirement
                    )
                )
                templates = result.scalars().all()

                for template in templates:
                    # Skip templates in grace period
                    if self._in_grace_period(template):
                        continue

                    allocation = allocations['allocations'].get(str(template.id), 0.0)

                    # Track low allocation
                    if allocation < self.allocation_threshold:
                        self._record_low_allocation(template.id)
                    else:
                        # Template recovered, clear history
                        self._clear_low_allocation(template.id)

        except Exception as e:
            logger.error(f"Error handling leaderboard update: {e}")


def get_template_retiree() -> TemplateRetiree:
    """Get template retiree instance"""
    return TemplateRetiree.get_instance()
