"""
Template Auto-Forker Service (AUTO-003)
========================================
Automatically fork winning templates for A/B testing.

When a template reaches "winner" status (top 20% allocation), this service
creates controlled variations to test new hypotheses while maintaining the
winning formula.

Fork Types:
1. FATE Weight Adjustments - Shift emphasis (±10%) between FATE dimensions
2. Awareness Level Shift - Test same template at adjacent awareness levels
3. CTA Variation - Test different CTA strengths (none → soft → direct)
4. Hook Pattern - Rotate hook patterns while keeping body/CTA
5. Style Variation - Adjust tone/formality while preserving structure

Each fork is tracked separately in the bandit allocator to measure
performance relative to the parent template.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import async_session_maker
from database.models import ContentTemplate
from services.event_bus import EventBus, Topics
from services.bandit_allocator import BanditAllocator, AllocationBucket


class ForkType(Enum):
    """Types of template variations to test"""
    FATE_SHIFT = "fate_shift"              # Adjust FATE weights
    AWARENESS_SHIFT = "awareness_shift"    # Test adjacent awareness level
    CTA_VARIATION = "cta_variation"        # Change CTA strength
    HOOK_VARIATION = "hook_variation"      # New hook pattern
    STYLE_VARIATION = "style_variation"    # Tone/formality adjustment


@dataclass
class ForkConfig:
    """Configuration for a template fork"""
    fork_type: ForkType
    parent_id: UUID
    variation_description: str
    modifications: Dict[str, Any]


class TemplateAutoForker:
    """
    Template Auto-Forker Service

    Automatically creates A/B test variations of winning templates.

    Usage:
        forker = TemplateAutoForker.get_instance()
        await forker.start()

        # Manually fork a template
        fork_id = await forker.fork_template(template_id, ForkType.FATE_SHIFT)

        # Auto-fork runs in background, monitors winners
    """

    _instance: Optional["TemplateAutoForker"] = None

    def __init__(self):
        """Initialize template auto-forker"""
        if TemplateAutoForker._instance is not None:
            raise RuntimeError("Use TemplateAutoForker.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("template-auto-forker")

        self.bandit_allocator = BanditAllocator.get_instance()

        # Fork constraints
        self.max_forks_per_template = 3     # Max 3 active forks per parent
        self.min_uses_before_fork = 20      # Minimum 20 uses to establish baseline
        self.fork_cooldown_hours = 48       # Wait 48h between forks of same template

        # FATE adjustment constraints
        self.fate_shift_amount = 0.10       # ±10% adjustment

        # Background task
        self._auto_fork_task: Optional[asyncio.Task] = None
        self._is_running = False

        # Tracking
        self._fork_history: Dict[UUID, List[datetime]] = {}  # parent_id -> fork times

        logger.info("🍴 Template Auto-Forker Service initialized")

    @classmethod
    def get_instance(cls) -> "TemplateAutoForker":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the auto-forker service"""
        if self._is_running:
            logger.warning("Template auto-forker already running")
            return

        self._is_running = True

        # Start background auto-fork task (check every 24 hours)
        self._auto_fork_task = asyncio.create_task(self._auto_fork_loop())

        # Subscribe to template leaderboard updates
        self.event_bus.subscribe(
            Topics.TEMPLATE_LEADERBOARD_UPDATED,
            self._handle_leaderboard_updated
        )

        logger.success("✓ Template Auto-Forker Service started")

    async def stop(self) -> None:
        """Stop the auto-forker service"""
        self._is_running = False

        if self._auto_fork_task:
            self._auto_fork_task.cancel()
            try:
                await self._auto_fork_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Template Auto-Forker Service stopped")

    async def fork_template(
        self,
        template_id: UUID,
        fork_type: ForkType,
        custom_modifications: Optional[Dict[str, Any]] = None
    ) -> Optional[UUID]:
        """
        Create a fork of a template

        Args:
            template_id: Parent template UUID
            fork_type: Type of variation to create
            custom_modifications: Optional custom modifications

        Returns:
            UUID of forked template, or None if fork failed
        """
        async with async_session_maker() as session:
            # Load parent template
            result = await session.execute(
                select(ContentTemplate).where(ContentTemplate.id == template_id)
            )
            parent = result.scalar_one_or_none()

            if not parent:
                logger.error(f"Parent template {template_id} not found")
                return None

            # Check cooldown
            if not self._can_fork(template_id):
                logger.warning(f"Template {template_id} in cooldown period")
                return None

            # Check max forks
            if await self._count_active_forks(session, template_id) >= self.max_forks_per_template:
                logger.warning(f"Template {template_id} has reached max forks")
                return None

            # Generate fork configuration
            if custom_modifications:
                fork_config = ForkConfig(
                    fork_type=fork_type,
                    parent_id=template_id,
                    variation_description=f"Custom {fork_type.value}",
                    modifications=custom_modifications
                )
            else:
                fork_config = self._generate_fork_config(parent, fork_type)

            if not fork_config:
                logger.warning(f"Could not generate fork config for {template_id}")
                return None

            # Create fork
            fork = await self._create_fork(session, parent, fork_config)

            if fork:
                await session.commit()

                # Track fork creation
                if template_id not in self._fork_history:
                    self._fork_history[template_id] = []
                self._fork_history[template_id].append(datetime.now(timezone.utc))

                # Emit event
                await self.event_bus.publish(
                    Topics.TEMPLATE_FORKED,
                    {
                        "parent_id": str(template_id),
                        "fork_id": str(fork.id),
                        "fork_type": fork_type.value,
                        "variation": fork_config.variation_description,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )

                logger.success(f"✓ Created fork {fork.id} from {template_id} ({fork_type.value})")
                return fork.id

            return None

    def _generate_fork_config(
        self,
        parent: ContentTemplate,
        fork_type: ForkType
    ) -> Optional[ForkConfig]:
        """
        Generate fork configuration based on fork type

        Args:
            parent: Parent template
            fork_type: Type of variation

        Returns:
            ForkConfig with modifications, or None if not applicable
        """
        if fork_type == ForkType.FATE_SHIFT:
            return self._generate_fate_shift(parent)

        elif fork_type == ForkType.AWARENESS_SHIFT:
            return self._generate_awareness_shift(parent)

        elif fork_type == ForkType.CTA_VARIATION:
            return self._generate_cta_variation(parent)

        elif fork_type == ForkType.HOOK_VARIATION:
            return self._generate_hook_variation(parent)

        elif fork_type == ForkType.STYLE_VARIATION:
            return self._generate_style_variation(parent)

        return None

    def _generate_fate_shift(self, parent: ContentTemplate) -> ForkConfig:
        """Generate FATE weight shift variation"""
        # Find highest FATE dimension
        fate_weights = {
            'focus': parent.fate_focus,
            'authority': parent.fate_authority,
            'tribe': parent.fate_tribe,
            'emotion': parent.fate_emotion
        }

        max_dim = max(fate_weights, key=fate_weights.get)
        min_dim = min(fate_weights, key=fate_weights.get)

        # Shift 10% from max to min dimension
        new_weights = fate_weights.copy()
        new_weights[max_dim] -= self.fate_shift_amount
        new_weights[min_dim] += self.fate_shift_amount

        # Ensure all weights are non-negative and sum to ~1.0
        new_weights = {k: max(0.05, v) for k, v in new_weights.items()}
        total = sum(new_weights.values())
        new_weights = {k: v / total for k, v in new_weights.items()}

        return ForkConfig(
            fork_type=ForkType.FATE_SHIFT,
            parent_id=parent.id,
            variation_description=f"Shift from {max_dim.upper()} to {min_dim.upper()}",
            modifications={
                'fate_focus': new_weights['focus'],
                'fate_authority': new_weights['authority'],
                'fate_tribe': new_weights['tribe'],
                'fate_emotion': new_weights['emotion']
            }
        )

    def _generate_awareness_shift(self, parent: ContentTemplate) -> Optional[ForkConfig]:
        """Generate awareness level shift variation"""
        # Awareness level progression
        levels = ['unaware', 'problem_aware', 'solution_aware', 'product_aware', 'most_aware']

        try:
            current_idx = levels.index(parent.awareness_level)
        except ValueError:
            logger.warning(f"Unknown awareness level: {parent.awareness_level}")
            return None

        # Try to shift up one level (more aware)
        if current_idx < len(levels) - 1:
            new_level = levels[current_idx + 1]
        # If already at highest level, try shifting down
        elif current_idx > 0:
            new_level = levels[current_idx - 1]
        else:
            return None

        return ForkConfig(
            fork_type=ForkType.AWARENESS_SHIFT,
            parent_id=parent.id,
            variation_description=f"Test at {new_level.replace('_', ' ')}",
            modifications={
                'awareness_level': new_level
            }
        )

    def _generate_cta_variation(self, parent: ContentTemplate) -> Optional[ForkConfig]:
        """Generate CTA strength variation"""
        # CTA progression: none → soft → direct
        cta_levels = ['none', 'soft', 'direct']

        current_cta = parent.cta_strength or 'soft'

        try:
            current_idx = cta_levels.index(current_cta)
        except ValueError:
            current_idx = 1  # Default to soft

        # Try next level
        if current_idx < len(cta_levels) - 1:
            new_cta = cta_levels[current_idx + 1]
        # If at highest, try lowest (wrap around)
        else:
            new_cta = cta_levels[0]

        if new_cta == current_cta:
            return None

        return ForkConfig(
            fork_type=ForkType.CTA_VARIATION,
            parent_id=parent.id,
            variation_description=f"CTA: {current_cta} → {new_cta}",
            modifications={
                'cta_strength': new_cta
            }
        )

    def _generate_hook_variation(self, parent: ContentTemplate) -> ForkConfig:
        """Generate hook pattern variation"""
        # Common hook patterns to test
        hook_patterns = [
            "Question Hook",
            "Bold Statement Hook",
            "Story Hook",
            "Statistic Hook",
            "Challenge Hook"
        ]

        # For now, just tag it - the actual prompt modification
        # would be done by the AI content generator
        return ForkConfig(
            fork_type=ForkType.HOOK_VARIATION,
            parent_id=parent.id,
            variation_description="Test alternative hook pattern",
            modifications={
                'description': (parent.description or "") + " | Hook variation test"
            }
        )

    def _generate_style_variation(self, parent: ContentTemplate) -> ForkConfig:
        """Generate style/tone variation"""
        # Tone shifts to test
        tone_shifts = [
            "More casual",
            "More formal",
            "More energetic",
            "More calm",
            "More humorous"
        ]

        # Pick a tone shift (in production, could use AI to determine best shift)
        tone_shift = tone_shifts[0]

        return ForkConfig(
            fork_type=ForkType.STYLE_VARIATION,
            parent_id=parent.id,
            variation_description=tone_shift,
            modifications={
                'description': (parent.description or "") + f" | {tone_shift} tone"
            }
        )

    async def _create_fork(
        self,
        session: AsyncSession,
        parent: ContentTemplate,
        config: ForkConfig
    ) -> Optional[ContentTemplate]:
        """
        Create the actual forked template in database

        Args:
            session: Database session
            parent: Parent template
            config: Fork configuration

        Returns:
            Created fork template, or None if failed
        """
        try:
            # Create fork with parent's attributes
            fork = ContentTemplate(
                id=uuid4(),
                brand_id=parent.brand_id,

                # Name indicates it's a fork
                name=f"{parent.name} (Fork: {config.variation_description})",
                description=f"Auto-forked from {parent.name} | {config.variation_description}",
                template_type=parent.template_type,

                # Copy content
                prompt_text=parent.prompt_text,
                required_variables=parent.required_variables,

                # Copy FATE weights (may be modified)
                fate_focus=config.modifications.get('fate_focus', parent.fate_focus),
                fate_authority=config.modifications.get('fate_authority', parent.fate_authority),
                fate_tribe=config.modifications.get('fate_tribe', parent.fate_tribe),
                fate_emotion=config.modifications.get('fate_emotion', parent.fate_emotion),

                # Copy or modify awareness level
                awareness_level=config.modifications.get('awareness_level', parent.awareness_level),

                # Copy or modify CTA
                cta_strength=config.modifications.get('cta_strength', parent.cta_strength),
                cta_template=parent.cta_template,

                # Start fresh performance tracking
                usage_count=0,
                avg_reward_score=0.0,
                performance_label='untested',

                # Active by default
                is_active=True,
                created_by='auto-forker'
            )

            session.add(fork)

            return fork

        except Exception as e:
            logger.error(f"Error creating fork: {e}")
            return None

    async def _count_active_forks(
        self,
        session: AsyncSession,
        parent_id: UUID
    ) -> int:
        """Count active forks of a parent template"""
        # Forks have parent name in their name
        result = await session.execute(
            select(ContentTemplate).where(
                ContentTemplate.name.like(f"%{parent_id}%"),
                ContentTemplate.is_active == True,
                ContentTemplate.created_by == 'auto-forker'
            )
        )
        forks = result.scalars().all()
        return len(forks)

    def _can_fork(self, template_id: UUID) -> bool:
        """Check if template is out of cooldown period"""
        if template_id not in self._fork_history:
            return True

        last_fork_time = self._fork_history[template_id][-1]
        cooldown_end = last_fork_time + timedelta(hours=self.fork_cooldown_hours)

        return datetime.now(timezone.utc) >= cooldown_end

    async def _auto_fork_loop(self) -> None:
        """Background loop to auto-fork winning templates"""
        logger.info("🔁 Template auto-fork loop started")

        while self._is_running:
            try:
                # Check for winning templates to fork
                await self._auto_fork_winners()

                # Sleep for 24 hours
                await asyncio.sleep(24 * 3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-fork loop: {e}")
                await asyncio.sleep(3600)  # Retry after 1 hour

        logger.info("🛑 Template auto-fork loop stopped")

    async def _auto_fork_winners(self) -> None:
        """Identify and fork winning templates"""
        logger.info("🔍 Checking for templates to auto-fork...")

        async with async_session_maker() as session:
            # Get all active templates with sufficient usage
            result = await session.execute(
                select(ContentTemplate).where(
                    ContentTemplate.is_active == True,
                    ContentTemplate.usage_count >= self.min_uses_before_fork,
                    ContentTemplate.created_by != 'auto-forker'  # Don't fork forks
                )
            )
            templates = result.scalars().all()

            if not templates:
                logger.debug("No templates ready for forking")
                return

            # Get allocations from bandit allocator
            allocations = await self.bandit_allocator.compute_allocations()

            fork_count = 0

            for template in templates:
                # Check if template is a winner (top 20% allocation)
                template_allocation = allocations['allocations'].get(str(template.id), 0.0)

                # Winners typically have > 10% allocation (top performers in 70% bucket)
                if template_allocation >= 0.10:
                    # Check cooldown
                    if self._can_fork(template.id):
                        # Fork with FATE shift (most common variation type)
                        fork_id = await self.fork_template(template.id, ForkType.FATE_SHIFT)

                        if fork_id:
                            fork_count += 1
                            logger.info(f"✓ Auto-forked winner template {template.name}")

            logger.success(f"✓ Auto-forked {fork_count} winning templates")

    async def _handle_leaderboard_updated(self, event: Any) -> None:
        """
        Handle template leaderboard updated events

        Triggers check for new winners to fork
        """
        try:
            logger.debug("📊 Template leaderboard updated, checking for auto-fork opportunities...")
            # Don't auto-fork on every leaderboard update (too frequent)
            # The daily loop handles auto-forking
        except Exception as e:
            logger.error(f"Error handling leaderboard update: {e}")


def get_template_auto_forker() -> TemplateAutoForker:
    """Get template auto-forker instance"""
    return TemplateAutoForker.get_instance()
