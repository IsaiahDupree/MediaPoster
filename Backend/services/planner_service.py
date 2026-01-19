"""
Weekly Plan Generator (OPS-012)
================================
Generates weekly content slots following awareness distribution:
- 40% Problem/Solution-aware value posts
- 30% Authority posts (proof, mechanisms)
- 20% Tribe/Identity posts
- 10% Direct offer posts

Performance Target: Generate 200 slots in <30 seconds
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class SlotType(Enum):
    """Content slot types based on awareness levels"""
    VALUE = "value"  # Problem/Solution-aware
    AUTHORITY = "authority"  # Proof, mechanisms
    TRIBE = "tribe"  # Identity, us-vs-them
    OFFER = "offer"  # Direct offer


class AwarenessLevel(Enum):
    """Eugene Schwartz's 5 Awareness Levels"""
    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    MOST_AWARE = "most_aware"


@dataclass
class ContentSlot:
    """
    A scheduled content slot with awareness targeting

    Attributes:
        slot_id: Unique slot identifier
        scheduled_time: When to publish
        slot_type: VALUE/AUTHORITY/TRIBE/OFFER
        awareness_level: Target awareness level
        brand_id: Brand for this slot (optional)
        offer_id: Offer to promote (optional, required for OFFER slots)
        icp_id: Target ICP (optional)
        platform: Target platform
        metadata: Additional slot configuration
    """
    slot_id: str
    scheduled_time: datetime
    slot_type: SlotType
    awareness_level: AwarenessLevel
    platform: str
    brand_id: Optional[str] = None
    offer_id: Optional[str] = None
    icp_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "slot_id": self.slot_id,
            "scheduled_time": self.scheduled_time.isoformat(),
            "slot_type": self.slot_type.value,
            "awareness_level": self.awareness_level.value,
            "platform": self.platform,
            "brand_id": self.brand_id,
            "offer_id": self.offer_id,
            "icp_id": self.icp_id,
            "metadata": self.metadata
        }


@dataclass
class WeeklyPlan:
    """
    A complete weekly content plan

    Attributes:
        plan_id: Unique plan identifier
        week_start: Start of week (Monday)
        week_end: End of week (Sunday)
        slots: List of content slots
        distribution: Actual slot type distribution
        created_at: When plan was generated
    """
    plan_id: str
    week_start: datetime
    week_end: datetime
    slots: List[ContentSlot]
    distribution: Dict[str, int]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "plan_id": self.plan_id,
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "slots": [slot.to_dict() for slot in self.slots],
            "distribution": self.distribution,
            "total_slots": len(self.slots),
            "created_at": self.created_at.isoformat()
        }


class PlannerService:
    """
    Weekly Plan Generator Service

    Generates content slots following the awareness × FATE framework:
    - 40% Value posts (Problem/Solution-aware)
    - 30% Authority posts (proof, mechanisms)
    - 20% Tribe posts (identity, us-vs-them)
    - 10% Offer posts (direct CTAs)

    Usage:
        planner = PlannerService()

        plan = planner.generate_weekly_plan(
            week_start=datetime(2026, 1, 20),
            slots_per_day=7,
            platforms=["x", "instagram", "linkedin"],
            brand_id="brand_123",
            offer_id="offer_456"
        )
    """

    # Distribution targets (must sum to 1.0)
    SLOT_TYPE_DISTRIBUTION = {
        SlotType.VALUE: 0.40,  # 40% value posts
        SlotType.AUTHORITY: 0.30,  # 30% authority posts
        SlotType.TRIBE: 0.20,  # 20% tribe posts
        SlotType.OFFER: 0.10  # 10% offer posts
    }

    # Awareness level mapping by slot type
    AWARENESS_MAPPING = {
        SlotType.VALUE: [AwarenessLevel.PROBLEM_AWARE, AwarenessLevel.SOLUTION_AWARE],
        SlotType.AUTHORITY: [AwarenessLevel.SOLUTION_AWARE, AwarenessLevel.PRODUCT_AWARE],
        SlotType.TRIBE: [AwarenessLevel.PROBLEM_AWARE, AwarenessLevel.SOLUTION_AWARE],
        SlotType.OFFER: [AwarenessLevel.PRODUCT_AWARE, AwarenessLevel.MOST_AWARE]
    }

    def __init__(self):
        """Initialize planner service"""
        self.plans: Dict[str, WeeklyPlan] = {}
        logger.info("📅 Weekly Planner Service initialized")

    def generate_weekly_plan(
        self,
        week_start: datetime,
        slots_per_day: int = 7,
        platforms: Optional[List[str]] = None,
        brand_id: Optional[str] = None,
        offer_id: Optional[str] = None,
        icp_id: Optional[str] = None
    ) -> WeeklyPlan:
        """
        Generate a weekly content plan

        Args:
            week_start: Start of week (will be normalized to Monday 00:00)
            slots_per_day: Number of content slots per day (default: 7)
            platforms: List of platforms to target (default: ["x"])
            brand_id: Brand ID for all slots (optional)
            offer_id: Offer ID for offer slots (optional)
            icp_id: ICP ID for all slots (optional)

        Returns:
            WeeklyPlan with generated slots

        Raises:
            ValueError: If invalid parameters
        """
        # Default platforms
        if platforms is None:
            platforms = ["x"]

        # Normalize week_start to Monday 00:00
        week_start = self._normalize_to_monday(week_start)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        # Calculate total slots for the week
        total_slots = slots_per_day * 7

        logger.info(f"📅 Generating weekly plan: {total_slots} slots from {week_start.date()} to {week_end.date()}")

        # Generate slot distribution
        slot_distribution = self._calculate_distribution(total_slots)

        # Generate slots
        slots = self._generate_slots(
            week_start=week_start,
            distribution=slot_distribution,
            platforms=platforms,
            brand_id=brand_id,
            offer_id=offer_id,
            icp_id=icp_id
        )

        # Create plan
        plan = WeeklyPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            week_start=week_start,
            week_end=week_end,
            slots=slots,
            distribution=slot_distribution
        )

        # Store plan
        self.plans[plan.plan_id] = plan

        logger.success(f"✓ Generated plan {plan.plan_id} with {len(slots)} slots")
        logger.info(f"  Distribution: {slot_distribution}")

        return plan

    def get_plan(self, plan_id: str) -> Optional[WeeklyPlan]:
        """Get a plan by ID"""
        return self.plans.get(plan_id)

    def _normalize_to_monday(self, date: datetime) -> datetime:
        """Normalize datetime to Monday 00:00 UTC of the same week"""
        # Ensure timezone aware
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        # Find Monday of this week (0 = Monday, 6 = Sunday)
        days_since_monday = date.weekday()
        monday = date - timedelta(days=days_since_monday)

        # Set to 00:00:00
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)

    def _calculate_distribution(self, total_slots: int) -> Dict[str, int]:
        """
        Calculate slot distribution following 40/30/20/10 rule

        Args:
            total_slots: Total number of slots to generate

        Returns:
            Dictionary mapping slot_type to count
        """
        distribution = {}

        for slot_type, percentage in self.SLOT_TYPE_DISTRIBUTION.items():
            count = round(total_slots * percentage)
            distribution[slot_type.value] = count

        # Adjust for rounding errors - add/subtract from largest category
        total_allocated = sum(distribution.values())
        diff = total_slots - total_allocated

        if diff != 0:
            # Add/subtract from VALUE (largest category)
            distribution[SlotType.VALUE.value] += diff

        return distribution

    def _generate_slots(
        self,
        week_start: datetime,
        distribution: Dict[str, int],
        platforms: List[str],
        brand_id: Optional[str],
        offer_id: Optional[str],
        icp_id: Optional[str]
    ) -> List[ContentSlot]:
        """
        Generate content slots spread across the week

        Args:
            week_start: Start of week
            distribution: Slot type distribution
            platforms: Target platforms
            brand_id: Brand ID
            offer_id: Offer ID
            icp_id: ICP ID

        Returns:
            List of ContentSlot objects
        """
        slots = []
        slot_index = 0

        # Generate slots for each type
        for slot_type_str, count in distribution.items():
            slot_type = SlotType(slot_type_str)

            for i in range(count):
                # Calculate scheduled time (spread evenly across week)
                total_slots = sum(distribution.values())
                days_offset = (slot_index * 7) / total_slots
                hours_offset = ((slot_index * 7 * 24) / total_slots) % 24

                scheduled_time = week_start + timedelta(
                    days=int(days_offset),
                    hours=int(hours_offset)
                )

                # Select awareness level for this slot type
                awareness_levels = self.AWARENESS_MAPPING.get(
                    slot_type,
                    [AwarenessLevel.PROBLEM_AWARE]
                )
                # Alternate between awareness levels
                awareness_level = awareness_levels[i % len(awareness_levels)]

                # Select platform (rotate through platforms)
                platform = platforms[slot_index % len(platforms)]

                # Create slot
                slot = ContentSlot(
                    slot_id=f"slot_{uuid.uuid4().hex[:12]}",
                    scheduled_time=scheduled_time,
                    slot_type=slot_type,
                    awareness_level=awareness_level,
                    platform=platform,
                    brand_id=brand_id,
                    offer_id=offer_id if slot_type == SlotType.OFFER else None,
                    icp_id=icp_id,
                    metadata={
                        "week_start": week_start.isoformat(),
                        "slot_index": slot_index
                    }
                )

                slots.append(slot)
                slot_index += 1

        # Sort by scheduled time
        slots.sort(key=lambda s: s.scheduled_time)

        return slots

    def validate_plan(self, plan: WeeklyPlan) -> Dict[str, Any]:
        """
        Validate a weekly plan

        Checks:
        - Distribution matches targets (within tolerance)
        - All slots have required fields
        - Slots are chronologically ordered
        - No duplicate slot IDs

        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []

        # Check total slots
        if len(plan.slots) == 0:
            errors.append("Plan has no slots")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check distribution (allow 2% tolerance)
        total_slots = len(plan.slots)
        for slot_type, target_pct in self.SLOT_TYPE_DISTRIBUTION.items():
            actual_count = plan.distribution.get(slot_type.value, 0)
            actual_pct = actual_count / total_slots

            if abs(actual_pct - target_pct) > 0.02:  # 2% tolerance
                warnings.append(
                    f"{slot_type.value}: expected {target_pct*100:.0f}%, "
                    f"got {actual_pct*100:.0f}%"
                )

        # Check all slots have required fields
        for i, slot in enumerate(plan.slots):
            if not slot.slot_id:
                errors.append(f"Slot {i}: missing slot_id")
            if not slot.scheduled_time:
                errors.append(f"Slot {i}: missing scheduled_time")
            if not slot.platform:
                errors.append(f"Slot {i}: missing platform")

            # Check offer slots have offer_id
            if slot.slot_type == SlotType.OFFER and not slot.offer_id:
                warnings.append(f"Slot {slot.slot_id}: OFFER slot missing offer_id")

        # Check chronological order
        for i in range(len(plan.slots) - 1):
            if plan.slots[i].scheduled_time > plan.slots[i + 1].scheduled_time:
                errors.append("Slots are not in chronological order")
                break

        # Check for duplicate slot IDs
        slot_ids = [s.slot_id for s in plan.slots]
        if len(slot_ids) != len(set(slot_ids)):
            errors.append("Duplicate slot IDs found")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


# Singleton instance
_planner_service: Optional[PlannerService] = None


def get_planner_service() -> PlannerService:
    """Get or create the global planner service instance"""
    global _planner_service
    if _planner_service is None:
        _planner_service = PlannerService()
    return _planner_service
