"""
Tests for Weekly Plan Generator (OPS-012)
==========================================
"""

import pytest
from datetime import datetime, timedelta, timezone

from services.planner_service import (
    PlannerService,
    SlotType,
    AwarenessLevel,
    get_planner_service
)


class TestPlannerServiceCore:
    """Test core planner functionality"""

    def test_service_initialization(self):
        """Test service initializes correctly"""
        planner = PlannerService()
        assert planner.plans == {}

    def test_singleton_pattern(self):
        """Test get_planner_service returns singleton"""
        service1 = get_planner_service()
        service2 = get_planner_service()
        assert service1 is service2


class TestWeeklyPlanGeneration:
    """Test weekly plan generation"""

    def test_generate_basic_plan(self):
        """Test generating a basic weekly plan"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 19, tzinfo=timezone.utc)  # Monday

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=7,
            platforms=["x"]
        )

        assert plan.plan_id.startswith("plan_")
        assert len(plan.slots) == 49  # 7 days * 7 slots
        assert plan.week_start == week_start
        assert plan.distribution is not None

    def test_plan_follows_distribution(self):
        """Test plan follows 40/30/20/10 distribution"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=10,  # 70 total slots
            platforms=["x"]
        )

        total = len(plan.slots)
        distribution = plan.distribution

        # Check distribution (allow 2 slots tolerance due to rounding)
        assert abs(distribution["value"] - 28) <= 2  # 40% of 70 = 28
        assert abs(distribution["authority"] - 21) <= 2  # 30% of 70 = 21
        assert abs(distribution["tribe"] - 14) <= 2  # 20% of 70 = 14
        assert abs(distribution["offer"] - 7) <= 2  # 10% of 70 = 7

    def test_slots_chronologically_ordered(self):
        """Test slots are in chronological order"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=7
        )

        for i in range(len(plan.slots) - 1):
            assert plan.slots[i].scheduled_time <= plan.slots[i + 1].scheduled_time

    def test_slots_spread_across_week(self):
        """Test slots are spread across 7 days"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=7
        )

        # Get unique days
        days = set(slot.scheduled_time.date() for slot in plan.slots)

        # Should have slots on all 7 days
        assert len(days) == 7

    def test_normalize_to_monday(self):
        """Test week_start is normalized to Monday"""
        planner = PlannerService()

        # Start on Wednesday
        wednesday = datetime(2026, 1, 22, 14, 30, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=wednesday,
            slots_per_day=7
        )

        # Should be normalized to Monday 00:00
        assert plan.week_start.weekday() == 0  # Monday
        assert plan.week_start.hour == 0
        assert plan.week_start.minute == 0

    def test_platform_rotation(self):
        """Test platforms are rotated across slots"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=6,  # 42 slots
            platforms=["x", "instagram", "linkedin"]
        )

        # Count platform distribution
        platform_counts = {}
        for slot in plan.slots:
            platform_counts[slot.platform] = platform_counts.get(slot.platform, 0) + 1

        # Each platform should have ~14 slots (42 / 3)
        for platform in ["x", "instagram", "linkedin"]:
            assert 12 <= platform_counts.get(platform, 0) <= 16


class TestSlotTypeMapping:
    """Test slot type and awareness level mapping"""

    def test_value_slots_have_correct_awareness(self):
        """Test VALUE slots map to PROBLEM/SOLUTION aware"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=10
        )

        value_slots = [s for s in plan.slots if s.slot_type == SlotType.VALUE]

        for slot in value_slots:
            assert slot.awareness_level in [
                AwarenessLevel.PROBLEM_AWARE,
                AwarenessLevel.SOLUTION_AWARE
            ]

    def test_authority_slots_have_correct_awareness(self):
        """Test AUTHORITY slots map to SOLUTION/PRODUCT aware"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=10
        )

        authority_slots = [s for s in plan.slots if s.slot_type == SlotType.AUTHORITY]

        for slot in authority_slots:
            assert slot.awareness_level in [
                AwarenessLevel.SOLUTION_AWARE,
                AwarenessLevel.PRODUCT_AWARE
            ]

    def test_offer_slots_have_correct_awareness(self):
        """Test OFFER slots map to PRODUCT/MOST aware"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=10
        )

        offer_slots = [s for s in plan.slots if s.slot_type == SlotType.OFFER]

        for slot in offer_slots:
            assert slot.awareness_level in [
                AwarenessLevel.PRODUCT_AWARE,
                AwarenessLevel.MOST_AWARE
            ]


class TestBrandOfferICP:
    """Test brand, offer, and ICP assignment"""

    def test_brand_id_assigned_to_all_slots(self):
        """Test brand_id is assigned to all slots"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=7,
            brand_id="brand_123"
        )

        for slot in plan.slots:
            assert slot.brand_id == "brand_123"

    def test_offer_id_only_on_offer_slots(self):
        """Test offer_id is only assigned to OFFER slots"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=10,
            offer_id="offer_456"
        )

        for slot in plan.slots:
            if slot.slot_type == SlotType.OFFER:
                assert slot.offer_id == "offer_456"
            else:
                assert slot.offer_id is None

    def test_icp_id_assigned_to_all_slots(self):
        """Test icp_id is assigned to all slots"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=7,
            icp_id="icp_789"
        )

        for slot in plan.slots:
            assert slot.icp_id == "icp_789"


class TestPlanValidation:
    """Test plan validation"""

    def test_valid_plan_passes_validation(self):
        """Test a valid plan passes validation"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=10,
            offer_id="offer_123"
        )

        result = planner.validate_plan(plan)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_empty_plan_fails_validation(self):
        """Test empty plan fails validation"""
        planner = PlannerService()

        from services.planner_service import WeeklyPlan

        empty_plan = WeeklyPlan(
            plan_id="test_plan",
            week_start=datetime(2026, 1, 20, tzinfo=timezone.utc),
            week_end=datetime(2026, 1, 26, tzinfo=timezone.utc),
            slots=[],
            distribution={}
        )

        result = planner.validate_plan(empty_plan)

        assert result["valid"] is False
        assert "no slots" in result["errors"][0].lower()


class TestPerformance:
    """Test performance requirements"""

    def test_generate_200_slots_quickly(self):
        """Test can generate 200 slots in <30 seconds"""
        import time

        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        start_time = time.time()

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=29,  # ~203 slots total
            platforms=["x", "instagram", "linkedin"]
        )

        elapsed = time.time() - start_time

        assert len(plan.slots) >= 200
        assert elapsed < 30.0  # Must complete in <30 seconds

    def test_generate_large_plan_500_slots(self):
        """Test can generate even larger plans (500 slots)"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=72,  # ~504 slots
            platforms=["x", "instagram", "tiktok", "linkedin"]
        )

        assert len(plan.slots) >= 500


class TestPlanRetrieval:
    """Test plan storage and retrieval"""

    def test_get_plan_by_id(self):
        """Test retrieving a plan by ID"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=7
        )

        retrieved = planner.get_plan(plan.plan_id)

        assert retrieved is not None
        assert retrieved.plan_id == plan.plan_id
        assert len(retrieved.slots) == len(plan.slots)

    def test_get_nonexistent_plan(self):
        """Test retrieving a non-existent plan returns None"""
        planner = PlannerService()

        result = planner.get_plan("nonexistent_plan_id")

        assert result is None


class TestSerialization:
    """Test plan and slot serialization"""

    def test_slot_to_dict(self):
        """Test slot serialization"""
        from services.planner_service import ContentSlot

        slot = ContentSlot(
            slot_id="slot_123",
            scheduled_time=datetime(2026, 1, 20, 10, 0, tzinfo=timezone.utc),
            slot_type=SlotType.VALUE,
            awareness_level=AwarenessLevel.PROBLEM_AWARE,
            platform="x",
            brand_id="brand_123"
        )

        data = slot.to_dict()

        assert data["slot_id"] == "slot_123"
        assert data["slot_type"] == "value"
        assert data["awareness_level"] == "problem_aware"
        assert data["platform"] == "x"

    def test_plan_to_dict(self):
        """Test plan serialization"""
        planner = PlannerService()
        week_start = datetime(2026, 1, 20, tzinfo=timezone.utc)

        plan = planner.generate_weekly_plan(
            week_start=week_start,
            slots_per_day=7
        )

        data = plan.to_dict()

        assert data["plan_id"] == plan.plan_id
        assert data["total_slots"] == 49
        assert "slots" in data
        assert "distribution" in data
