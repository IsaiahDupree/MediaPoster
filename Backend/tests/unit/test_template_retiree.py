"""
Unit Tests for Template Retiree Service (AUTO-004)
===================================================
Tests template retirement functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from services.template_retiree import (
    TemplateRetiree,
    RetirementCandidate
)
from database.models import ContentTemplate


# =========================================================================
# FIXTURES
# =========================================================================

@pytest.fixture
def retiree():
    """Get retiree instance"""
    # Reset singleton for testing
    TemplateRetiree._instance = None
    return TemplateRetiree.get_instance()


@pytest.fixture
def old_template():
    """Create an old template (past grace period)"""
    return ContentTemplate(
        id=uuid4(),
        brand_id=uuid4(),
        name="Old Template",
        description="An old template",
        template_type="post",
        prompt_text="Create a post about {topic}",
        required_variables=["topic"],
        fate_focus=0.25,
        fate_authority=0.25,
        fate_tribe=0.25,
        fate_emotion=0.25,
        awareness_level="problem_aware",
        cta_strength="soft",
        usage_count=75,
        avg_reward_score=0.15,  # Low performance
        performance_label="loser",
        is_active=True,
        created_by="system",
        created_at=datetime.now(timezone.utc) - timedelta(days=60)  # 60 days old
    )


@pytest.fixture
def new_template():
    """Create a new template (in grace period)"""
    return ContentTemplate(
        id=uuid4(),
        brand_id=uuid4(),
        name="New Template",
        description="A new template",
        template_type="post",
        prompt_text="Create a post about {topic}",
        required_variables=["topic"],
        fate_focus=0.25,
        fate_authority=0.25,
        fate_tribe=0.25,
        fate_emotion=0.25,
        awareness_level="problem_aware",
        cta_strength="soft",
        usage_count=60,
        avg_reward_score=0.15,
        performance_label="untested",
        is_active=True,
        created_by="system",
        created_at=datetime.now(timezone.utc) - timedelta(days=15)  # 15 days old
    )


# =========================================================================
# INITIALIZATION TESTS
# =========================================================================

class TestRetireeInit:
    """Test initialization and singleton pattern"""

    def test_singleton(self):
        """Test singleton pattern"""
        retiree1 = TemplateRetiree.get_instance()
        retiree2 = TemplateRetiree.get_instance()
        assert retiree1 is retiree2

    def test_init_raises_on_direct_instantiation(self):
        """Test that direct instantiation raises error"""
        with pytest.raises(RuntimeError):
            TemplateRetiree()

    def test_default_config(self, retiree):
        """Test default configuration values"""
        assert retiree.allocation_threshold == 0.05
        assert retiree.min_uses_for_retirement == 50
        assert retiree.grace_period_days == 30
        assert retiree.consecutive_cycles_required == 3


# =========================================================================
# GRACE PERIOD TESTS
# =========================================================================

class TestGracePeriod:
    """Test grace period logic"""

    def test_in_grace_period_new_template(self, retiree, new_template):
        """Test that new templates are in grace period"""
        assert retiree._in_grace_period(new_template)

    def test_not_in_grace_period_old_template(self, retiree, old_template):
        """Test that old templates are not in grace period"""
        assert not retiree._in_grace_period(old_template)

    def test_grace_period_boundary(self, retiree):
        """Test grace period at exact boundary"""
        template = ContentTemplate(
            id=uuid4(),
            brand_id=uuid4(),
            name="Boundary Template",
            template_type="post",
            prompt_text="test",
            required_variables=[],
            fate_focus=0.25,
            fate_authority=0.25,
            fate_tribe=0.25,
            fate_emotion=0.25,
            awareness_level="problem_aware",
            usage_count=50,
            is_active=True,
            created_at=datetime.now(timezone.utc) - timedelta(days=30)  # Exactly 30 days
        )

        # Should not be in grace period (30 days is the cutoff)
        assert not retiree._in_grace_period(template)


# =========================================================================
# LOW ALLOCATION TRACKING TESTS
# =========================================================================

class TestLowAllocationTracking:
    """Test low allocation tracking"""

    def test_record_low_allocation(self, retiree):
        """Test recording low allocation"""
        template_id = uuid4()

        retiree._record_low_allocation(template_id)
        assert template_id in retiree._low_allocation_history
        assert len(retiree._low_allocation_history[template_id]) == 1

    def test_count_consecutive_low_cycles_none(self, retiree):
        """Test counting cycles with no history"""
        template_id = uuid4()
        assert retiree._count_consecutive_low_cycles(template_id) == 0

    def test_count_consecutive_low_cycles_multiple(self, retiree):
        """Test counting multiple consecutive cycles"""
        template_id = uuid4()

        # Record 4 low allocation cycles
        for _ in range(4):
            retiree._record_low_allocation(template_id)

        assert retiree._count_consecutive_low_cycles(template_id) == 4

    def test_clear_low_allocation(self, retiree):
        """Test clearing low allocation history"""
        template_id = uuid4()

        # Record some cycles
        retiree._record_low_allocation(template_id)
        retiree._record_low_allocation(template_id)
        assert template_id in retiree._low_allocation_history

        # Clear history
        retiree._clear_low_allocation(template_id)
        assert template_id not in retiree._low_allocation_history

    def test_low_allocation_history_limit(self, retiree):
        """Test that history is limited to last 10 timestamps"""
        template_id = uuid4()

        # Record 15 cycles
        for _ in range(15):
            retiree._record_low_allocation(template_id)

        # Should only keep last 10
        assert len(retiree._low_allocation_history[template_id]) == 10


# =========================================================================
# RETIREMENT CANDIDATE TESTS
# =========================================================================

class TestRetirementCandidates:
    """Test retirement candidate identification"""

    def test_retirement_candidate_dataclass(self):
        """Test RetirementCandidate dataclass"""
        candidate = RetirementCandidate(
            template_id=uuid4(),
            template_name="Test Template",
            allocation=0.02,
            usage_count=75,
            created_at=datetime.now(timezone.utc),
            consecutive_low_cycles=4
        )

        assert candidate.allocation == 0.02
        assert candidate.consecutive_low_cycles == 4


# =========================================================================
# INTEGRATION TESTS
# =========================================================================

class TestIntegration:
    """Integration tests for retiree"""

    @pytest.mark.asyncio
    async def test_lifecycle(self, retiree):
        """Test service lifecycle"""
        assert not retiree._is_running

        await retiree.start()
        assert retiree._is_running

        await retiree.stop()
        assert not retiree._is_running

    def test_allocation_threshold_check(self, retiree):
        """Test that allocation threshold is correctly configured"""
        # 5% = 0.05
        assert retiree.allocation_threshold == 0.05

        # Templates with < 5% allocation should be candidates
        assert 0.04 < retiree.allocation_threshold
        assert 0.06 > retiree.allocation_threshold
