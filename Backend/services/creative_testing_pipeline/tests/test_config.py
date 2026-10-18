"""
Tests for ACTP Configuration
"""

import pytest

from services.creative_testing_pipeline.config import (
    ACTPConfig,
    AdTestConfig,
    IterationConfig,
    OrganicTestConfig,
    ScalingConfig,
    ScoringWeights,
    VideoGenerationConfig,
)


class TestACTPConfig:
    """Test configuration defaults and overrides."""

    def test_default_config(self):
        config = ACTPConfig()
        assert config.organic_test.wait_hours == 24
        assert config.ad_test.budget_per_creative_cents == 500
        assert config.scaling.budget_tiers_cents == [500, 2000, 5000, 10000]
        assert config.video_generation.default_provider == "sora"
        assert config.iteration.max_rounds == 10

    def test_from_dict_partial_override(self):
        data = {
            "organic_test": {"wait_hours": 48, "creatives_per_round": 10},
            "ad_test": {"budget_per_creative_cents": 1000},
        }
        config = ACTPConfig.from_dict(data)
        assert config.organic_test.wait_hours == 48
        assert config.organic_test.creatives_per_round == 10
        # Non-overridden fields keep defaults
        assert config.organic_test.min_views_for_decision == 100
        assert config.ad_test.budget_per_creative_cents == 1000
        assert config.ad_test.wait_hours == 48  # Default

    def test_from_dict_empty_keeps_defaults(self):
        config = ACTPConfig.from_dict({})
        default = ACTPConfig()
        assert config.organic_test.wait_hours == default.organic_test.wait_hours

    def test_to_dict_roundtrip(self):
        config = ACTPConfig()
        d = config.to_dict()
        assert isinstance(d, dict)
        assert "organic_test" in d
        assert "ad_test" in d
        assert d["organic_test"]["wait_hours"] == 24

    def test_scoring_weights_sum_roughly_to_one(self):
        w = ScoringWeights()
        organic_sum = (
            w.organic_engagement_rate + w.organic_view_velocity
            + w.organic_completion_rate + w.organic_comment_sentiment
        )
        assert abs(organic_sum - 1.0) < 0.01

        ad_sum = (
            w.ad_ctr + w.ad_cpc_efficiency + w.ad_hook_rate
            + w.ad_hold_rate + w.ad_conversion_rate
        )
        assert abs(ad_sum - 1.0) < 0.01

    def test_scaling_tiers_ascending(self):
        config = ACTPConfig()
        tiers = config.scaling.budget_tiers_cents
        for i in range(1, len(tiers)):
            assert tiers[i] > tiers[i - 1]
