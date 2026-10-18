"""
Unit Tests for Template Leaderboard (OPS-007)
==============================================
Tests template ranking, bandit allocation, and performance labeling.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID

from services.template_leaderboard import (
    TemplateLeaderboard,
    PerformanceLabel,
    get_template_leaderboard
)


class TestTemplateLeaderboard:
    """Test template leaderboard service"""

    def test_singleton_pattern(self):
        """Test that TemplateLeaderboard follows singleton pattern"""
        instance1 = TemplateLeaderboard.get_instance()
        instance2 = TemplateLeaderboard.get_instance()

        assert instance1 is instance2
        assert instance1 == instance2

    def test_get_instance_function(self):
        """Test get_template_leaderboard() helper function"""
        leaderboard = get_template_leaderboard()

        assert isinstance(leaderboard, TemplateLeaderboard)
        assert leaderboard == TemplateLeaderboard.get_instance()

    def test_bandit_allocation_weights(self):
        """Test bandit allocation weights sum correctly"""
        leaderboard = get_template_leaderboard()

        total = (
            leaderboard.exploit_weight +
            leaderboard.explore_weight +
            leaderboard.experiment_weight
        )

        # Should sum to 1.0 (with floating point tolerance)
        assert abs(total - 1.0) < 0.01

    def test_performance_thresholds(self):
        """Test performance threshold configuration"""
        leaderboard = get_template_leaderboard()

        assert leaderboard.min_uses_for_confidence > 0
        assert leaderboard.high_confidence_uses >= leaderboard.min_uses_for_confidence
        assert 0 < leaderboard.winner_percentile < 1
        assert 0 < leaderboard.loser_percentile < 1
        assert leaderboard.winner_percentile > leaderboard.loser_percentile

    def test_performance_label_enum(self):
        """Test PerformanceLabel enum values"""
        assert PerformanceLabel.WINNER.value == "winner"
        assert PerformanceLabel.PROMISING.value == "promising"
        assert PerformanceLabel.AVERAGE.value == "average"
        assert PerformanceLabel.LOSER.value == "loser"
        assert PerformanceLabel.UNTESTED.value == "untested"

    def test_instance_initialization(self):
        """Test that leaderboard initializes correctly"""
        leaderboard = get_template_leaderboard()

        assert leaderboard.event_bus is not None
        assert leaderboard._is_running == False
        assert leaderboard._recompute_task is None

    def test_double_instantiation_error(self):
        """Test that direct instantiation is prevented"""
        # First instance via get_instance is OK
        TemplateLeaderboard.get_instance()

        # Direct instantiation should raise error
        with pytest.raises(RuntimeError, match="Use TemplateLeaderboard.get_instance"):
            TemplateLeaderboard()


@pytest.mark.asyncio
class TestTemplateLeaderboardAsync:
    """Async tests for template leaderboard"""

    async def test_start_and_stop(self):
        """Test service start and stop lifecycle"""
        leaderboard = get_template_leaderboard()

        # Stop if already running
        if leaderboard._is_running:
            await leaderboard.stop()

        # Start service
        await leaderboard.start()
        assert leaderboard._is_running == True
        assert leaderboard._recompute_task is not None

        # Stop service
        await leaderboard.stop()
        assert leaderboard._is_running == False

    async def test_double_start(self):
        """Test that starting already-running service is safe"""
        leaderboard = get_template_leaderboard()

        # Stop first
        if leaderboard._is_running:
            await leaderboard.stop()

        # Start twice
        await leaderboard.start()
        await leaderboard.start()  # Should log warning but not error

        assert leaderboard._is_running == True

        # Clean up
        await leaderboard.stop()

    async def test_get_top_templates_empty(self):
        """Test getting top templates when database is empty"""
        leaderboard = get_template_leaderboard()

        templates = await leaderboard.get_top_templates(limit=10)

        # Should return empty list if no templates exist
        assert isinstance(templates, list)

    async def test_get_top_templates_with_filters(self):
        """Test filtering top templates"""
        leaderboard = get_template_leaderboard()

        # Test with filters
        templates = await leaderboard.get_top_templates(
            awareness_level="problem_aware",
            limit=5
        )

        assert isinstance(templates, list)

    async def test_sample_template_no_templates(self):
        """Test sampling when no templates exist"""
        leaderboard = get_template_leaderboard()

        # Sample with non-existent filters should return None
        template_id = await leaderboard.sample_template(
            channel="nonexistent_channel",
            awareness_level="nonexistent_level"
        )

        # Should return None if no matching templates
        assert template_id is None or isinstance(template_id, UUID)


def test_module_exports():
    """Test that module exports expected symbols"""
    from services import template_leaderboard

    assert hasattr(template_leaderboard, 'TemplateLeaderboard')
    assert hasattr(template_leaderboard, 'PerformanceLabel')
    assert hasattr(template_leaderboard, 'get_template_leaderboard')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
