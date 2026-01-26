"""
Unit Tests for Template Auto-Forker Service (AUTO-003)
========================================================
Tests template auto-forking and A/B testing functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from services.template_auto_forker import (
    TemplateAutoForker,
    ForkType,
    ForkConfig
)
from database.models import ContentTemplate


# =========================================================================
# FIXTURES
# =========================================================================

@pytest.fixture
def auto_forker():
    """Get auto-forker instance"""
    # Reset singleton for testing
    TemplateAutoForker._instance = None
    return TemplateAutoForker.get_instance()


@pytest.fixture
def sample_template():
    """Create a sample template for testing"""
    return ContentTemplate(
        id=uuid4(),
        brand_id=uuid4(),
        name="Test Template",
        description="A test template",
        template_type="post",
        prompt_text="Create a post about {topic}",
        required_variables=["topic"],
        fate_focus=0.30,
        fate_authority=0.25,
        fate_tribe=0.25,
        fate_emotion=0.20,
        awareness_level="problem_aware",
        cta_strength="soft",
        cta_template="Learn more",
        usage_count=25,
        avg_reward_score=0.65,
        performance_label="winner",
        is_active=True,
        created_by="system"
    )


# =========================================================================
# INITIALIZATION TESTS
# =========================================================================

class TestAutoForkerInit:
    """Test initialization and singleton pattern"""

    def test_singleton(self):
        """Test singleton pattern"""
        forker1 = TemplateAutoForker.get_instance()
        forker2 = TemplateAutoForker.get_instance()
        assert forker1 is forker2

    def test_init_raises_on_direct_instantiation(self):
        """Test that direct instantiation raises error"""
        with pytest.raises(RuntimeError):
            TemplateAutoForker()

    def test_default_config(self, auto_forker):
        """Test default configuration values"""
        assert auto_forker.max_forks_per_template == 3
        assert auto_forker.min_uses_before_fork == 20
        assert auto_forker.fork_cooldown_hours == 48
        assert auto_forker.fate_shift_amount == 0.10


# =========================================================================
# FORK CONFIGURATION GENERATION TESTS
# =========================================================================

class TestForkGeneration:
    """Test fork configuration generation"""

    def test_generate_fate_shift(self, auto_forker, sample_template):
        """Test FATE weight shift generation"""
        config = auto_forker._generate_fate_shift(sample_template)

        assert config is not None
        assert config.fork_type == ForkType.FATE_SHIFT
        assert config.parent_id == sample_template.id

        # Verify modifications
        mods = config.modifications
        assert 'fate_focus' in mods
        assert 'fate_authority' in mods
        assert 'fate_tribe' in mods
        assert 'fate_emotion' in mods

        # Verify weights sum to ~1.0
        total = sum([
            mods['fate_focus'],
            mods['fate_authority'],
            mods['fate_tribe'],
            mods['fate_emotion']
        ])
        assert abs(total - 1.0) < 0.01

        # Verify at least one weight changed
        changed = (
            mods['fate_focus'] != sample_template.fate_focus or
            mods['fate_authority'] != sample_template.fate_authority or
            mods['fate_tribe'] != sample_template.fate_tribe or
            mods['fate_emotion'] != sample_template.fate_emotion
        )
        assert changed

    def test_generate_awareness_shift_up(self, auto_forker, sample_template):
        """Test awareness level shift generation (upward)"""
        sample_template.awareness_level = "problem_aware"

        config = auto_forker._generate_awareness_shift(sample_template)

        assert config is not None
        assert config.fork_type == ForkType.AWARENESS_SHIFT
        assert config.modifications['awareness_level'] == "solution_aware"

    def test_generate_awareness_shift_down(self, auto_forker, sample_template):
        """Test awareness level shift generation (downward when at max)"""
        sample_template.awareness_level = "most_aware"

        config = auto_forker._generate_awareness_shift(sample_template)

        assert config is not None
        assert config.modifications['awareness_level'] == "product_aware"

    def test_generate_cta_variation(self, auto_forker, sample_template):
        """Test CTA strength variation generation"""
        sample_template.cta_strength = "soft"

        config = auto_forker._generate_cta_variation(sample_template)

        assert config is not None
        assert config.fork_type == ForkType.CTA_VARIATION
        assert config.modifications['cta_strength'] == "direct"

    def test_generate_cta_variation_wrap(self, auto_forker, sample_template):
        """Test CTA variation wraps around to none"""
        sample_template.cta_strength = "direct"

        config = auto_forker._generate_cta_variation(sample_template)

        assert config is not None
        assert config.modifications['cta_strength'] == "none"

    def test_generate_hook_variation(self, auto_forker, sample_template):
        """Test hook pattern variation generation"""
        config = auto_forker._generate_hook_variation(sample_template)

        assert config is not None
        assert config.fork_type == ForkType.HOOK_VARIATION
        assert 'description' in config.modifications

    def test_generate_style_variation(self, auto_forker, sample_template):
        """Test style/tone variation generation"""
        config = auto_forker._generate_style_variation(sample_template)

        assert config is not None
        assert config.fork_type == ForkType.STYLE_VARIATION
        assert 'description' in config.modifications


# =========================================================================
# COOLDOWN TESTS
# =========================================================================

class TestCooldown:
    """Test fork cooldown logic"""

    def test_can_fork_new_template(self, auto_forker):
        """Test can fork template with no history"""
        template_id = uuid4()
        assert auto_forker._can_fork(template_id)

    def test_cannot_fork_within_cooldown(self, auto_forker):
        """Test cannot fork within cooldown period"""
        template_id = uuid4()

        # Add recent fork to history
        auto_forker._fork_history[template_id] = [
            datetime.now(timezone.utc) - timedelta(hours=24)
        ]

        # Cooldown is 48 hours, so should not be able to fork
        assert not auto_forker._can_fork(template_id)

    def test_can_fork_after_cooldown(self, auto_forker):
        """Test can fork after cooldown expires"""
        template_id = uuid4()

        # Add old fork to history (more than 48 hours ago)
        auto_forker._fork_history[template_id] = [
            datetime.now(timezone.utc) - timedelta(hours=72)
        ]

        assert auto_forker._can_fork(template_id)


# =========================================================================
# INTEGRATION TESTS
# =========================================================================

class TestIntegration:
    """Integration tests for auto-forker"""

    @pytest.mark.asyncio
    async def test_lifecycle(self, auto_forker):
        """Test service lifecycle"""
        assert not auto_forker._is_running

        await auto_forker.start()
        assert auto_forker._is_running

        await auto_forker.stop()
        assert not auto_forker._is_running

    def test_fate_weights_stay_positive(self, auto_forker, sample_template):
        """Test FATE weights never go negative"""
        # Set extreme weights
        sample_template.fate_focus = 0.90
        sample_template.fate_authority = 0.05
        sample_template.fate_tribe = 0.03
        sample_template.fate_emotion = 0.02

        config = auto_forker._generate_fate_shift(sample_template)

        # All weights should be positive
        mods = config.modifications
        assert mods['fate_focus'] > 0
        assert mods['fate_authority'] > 0
        assert mods['fate_tribe'] > 0
        assert mods['fate_emotion'] > 0

    def test_multiple_fork_types(self, auto_forker, sample_template):
        """Test generating all fork types"""
        fork_types = [
            ForkType.FATE_SHIFT,
            ForkType.AWARENESS_SHIFT,
            ForkType.CTA_VARIATION,
            ForkType.HOOK_VARIATION,
            ForkType.STYLE_VARIATION
        ]

        for fork_type in fork_types:
            config = auto_forker._generate_fork_config(sample_template, fork_type)
            assert config is not None
            assert config.fork_type == fork_type
            assert config.parent_id == sample_template.id
            assert len(config.modifications) > 0
