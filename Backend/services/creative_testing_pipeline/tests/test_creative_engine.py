"""
Tests for ACTP Creative Engine - Validation, tagging, search, cost, dedup, platform specs
"""

import pytest

from services.creative_testing_pipeline.creative_engine import CreativeEngine
from services.creative_testing_pipeline.models import Creative, GenerationSource
from services.creative_testing_pipeline.monitoring import CostTracker


class TestCostEstimation:
    """Test generation cost estimation."""

    def test_sora_cost_positive(self):
        engine = CreativeEngine()
        est = engine.estimate_generation_cost("sora", 5)
        assert est["total_estimated_cents"] > 0
        assert est["count"] == 5

    def test_cost_includes_usd(self):
        engine = CreativeEngine()
        est = engine.estimate_generation_cost("veo3", 3)
        assert "total_estimated_usd" in est
        assert est["total_estimated_usd"] == est["total_estimated_cents"] / 100

    def test_unknown_provider_zero_gen_cost(self):
        engine = CreativeEngine()
        est = engine.estimate_generation_cost("unknown", 1)
        assert est["generation_cost_cents"] == 0


class TestPlatformSpecs:
    """Test platform video spec definitions and validation."""

    def setup_method(self):
        self.engine = CreativeEngine()

    def test_all_platforms_defined(self):
        assert "youtube_shorts" in self.engine.PLATFORM_SPECS
        assert "tiktok" in self.engine.PLATFORM_SPECS
        assert "instagram_reels" in self.engine.PLATFORM_SPECS
        assert "meta_ads" in self.engine.PLATFORM_SPECS

    def test_specs_have_required_fields(self):
        for platform, spec in self.engine.PLATFORM_SPECS.items():
            assert "max_duration" in spec
            assert "min_resolution" in spec
            assert "max_file_size_mb" in spec
            assert "codecs" in spec

    def test_valid_metadata_passes(self):
        meta = {"duration_seconds": 15, "file_size_bytes": 10_000_000, "codec": "h264"}
        result = self.engine.validate_for_platform(meta, "youtube_shorts")
        assert result["valid"] is True
        assert result["errors"] == []

    def test_exceeding_duration_fails(self):
        meta = {"duration_seconds": 120, "file_size_bytes": 10_000_000, "codec": "h264"}
        result = self.engine.validate_for_platform(meta, "youtube_shorts")
        assert result["valid"] is False

    def test_wrong_codec_fails(self):
        meta = {"duration_seconds": 15, "file_size_bytes": 10_000_000, "codec": "av1"}
        result = self.engine.validate_for_platform(meta, "instagram_reels")
        assert result["valid"] is False

    def test_file_too_large_fails(self):
        meta = {"duration_seconds": 15, "file_size_bytes": 300_000_000_000, "codec": "h264"}
        result = self.engine.validate_for_platform(meta, "tiktok")
        assert result["valid"] is False

    def test_unknown_platform_passes(self):
        result = self.engine.validate_for_platform({}, "unknown")
        assert result["valid"] is True


class TestAutoTagging:
    """Test auto-tag generation from creative metadata."""

    @pytest.mark.asyncio
    async def test_tags_include_source(self):
        engine = CreativeEngine()
        creative = Creative(
            campaign_id="c1", round_id="r1",
            generation_source=GenerationSource.SORA,
            generation_metadata={"brief": {"style": "ugc", "target_emotion": "fear"}},
            angle="productivity hack",
        )
        tags = await engine.auto_tag_creative(creative)
        assert any("source:sora" in t for t in tags)

    @pytest.mark.asyncio
    async def test_tags_include_style(self):
        engine = CreativeEngine()
        creative = Creative(
            campaign_id="c1", round_id="r1",
            generation_source=GenerationSource.VEO3,
            generation_metadata={"brief": {"style": "cinematic"}},
        )
        tags = await engine.auto_tag_creative(creative)
        assert "style:cinematic" in tags

    @pytest.mark.asyncio
    async def test_winner_tag(self):
        engine = CreativeEngine()
        creative = Creative(
            campaign_id="c1", round_id="r1",
            generation_source=GenerationSource.SORA,
            is_winner=True,
        )
        tags = await engine.auto_tag_creative(creative)
        assert "winner" in tags

    @pytest.mark.asyncio
    async def test_variation_tag(self):
        engine = CreativeEngine()
        creative = Creative(
            campaign_id="c1", round_id="r1",
            generation_source=GenerationSource.REMIX,
            parent_creative_id="parent-1",
        )
        tags = await engine.auto_tag_creative(creative)
        assert "variation" in tags


class TestBriefToPrompt:
    """Test brief-to-Sora prompt conversion."""

    def test_includes_visual_direction(self):
        engine = CreativeEngine()
        brief = {"visual_direction": "person walking in city", "hook": "Stop scrolling", "style": "ugc"}
        prompt = engine._brief_to_sora_prompt(brief)
        assert "person walking in city" in prompt
        assert "Stop scrolling" in prompt
        assert "ugc" in prompt

    def test_default_style_cinematic(self):
        engine = CreativeEngine()
        brief = {"hook": "Test"}
        prompt = engine._brief_to_sora_prompt(brief)
        assert "cinematic" in prompt

    def test_includes_aspect_ratio(self):
        engine = CreativeEngine()
        brief = {"hook": "Test"}
        prompt = engine._brief_to_sora_prompt(brief)
        assert "9:16" in prompt


class TestAnomalyDetection:
    """Test metric anomaly detection."""

    def test_detects_spike(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        series = [
            {"value": 100, "metric_type": "views"},
            {"value": 110, "metric_type": "views"},
            {"value": 95, "metric_type": "views"},
            {"value": 105, "metric_type": "views"},
            {"value": 98, "metric_type": "views"},
            {"value": 102, "metric_type": "views"},
            {"value": 97, "metric_type": "views"},
            {"value": 103, "metric_type": "views"},
            {"value": 100, "metric_type": "views"},
            {"value": 100000, "metric_type": "views"},  # clear spike
        ]
        anomalies = ac.detect_anomalies(series)
        assert len(anomalies) > 0
        assert anomalies[0]["type"] == "spike"

    def test_detects_sudden_zero(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        series = [
            {"value": 500, "metric_type": "views"},
            {"value": 600, "metric_type": "views"},
            {"value": 550, "metric_type": "views"},
            {"value": 0, "metric_type": "views"},  # sudden zero
        ]
        anomalies = ac.detect_anomalies(series)
        sudden_zeros = [a for a in anomalies if a["type"] == "sudden_zero"]
        assert len(sudden_zeros) > 0

    def test_no_anomaly_in_normal_data(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        series = [{"value": v, "metric_type": "views"} for v in [100, 105, 98, 102, 99]]
        anomalies = ac.detect_anomalies(series)
        assert len(anomalies) == 0

    def test_too_few_points_returns_empty(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        anomalies = ac.detect_anomalies([{"value": 100}])
        assert anomalies == []


class TestROASCalculation:
    """Test ROAS calculation."""

    def test_profitable_roas(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        result = ac.calculate_roas(revenue_cents=1000, spend_cents=500)
        assert result["roas"] == 2.0
        assert result["profit_cents"] == 500
        assert result["break_even"] is True

    def test_unprofitable_roas(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        result = ac.calculate_roas(revenue_cents=200, spend_cents=500)
        assert result["roas"] == 0.4
        assert result["profit_cents"] == -300
        assert result["break_even"] is False

    def test_zero_spend(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        result = ac.calculate_roas(revenue_cents=100, spend_cents=0)
        assert result["roas"] == 0
        assert result["break_even"] is True


class TestMetricValidation:
    """Test metric value validation."""

    def test_valid_views(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        assert ac.validate_metric("views", 5000) is True

    def test_negative_views_invalid(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        assert ac.validate_metric("views", -1) is False

    def test_ctr_over_100_invalid(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        assert ac.validate_metric("ctr", 150) is False

    def test_completion_rate_in_range(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        assert ac.validate_metric("completion_rate", 0.75) is True
        assert ac.validate_metric("completion_rate", 1.5) is False

    def test_unknown_metric_passes(self):
        from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
        ac = AnalyticsCollector()
        assert ac.validate_metric("custom_metric", 999999) is True
