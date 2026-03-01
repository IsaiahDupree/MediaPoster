"""
Tests for ACTP Ad Deployer - Format validation, fatigue, budget pacing, CPA, bid strategy
"""

import pytest

from services.creative_testing_pipeline.ad_deployer import AdBudgetDeployer as AdDeployer
from services.creative_testing_pipeline.models import (
    AdDeployment,
    AdDeploymentStatus,
    Platform,
)


def _make_deployment(**overrides) -> AdDeployment:
    defaults = {
        "creative_id": "c1",
        "round_id": "r1",
        "platform": Platform.META_ADS,
        "budget_cents": 500,
        "spend_cents": 250,
        "status": AdDeploymentStatus.ACTIVE,
        "metrics": {
            "impressions": 5000,
            "clicks": 100,
            "spend_cents": 250,
            "three_second_views": 2500,
            "thru_plays": 1000,
            "conversions": 3,
            "ctr": 2.0,
            "cpc": 2.5,
            "frequency": 1.5,
        },
    }
    defaults.update(overrides)
    return AdDeployment(**defaults)


class TestCreativeFormatValidation:
    """Test ad platform creative format validation."""

    def setup_method(self):
        self.deployer = AdDeployer()

    def test_valid_meta_creative(self):
        meta = {"duration_seconds": 30, "file_size_bytes": 50_000_000}
        result = self.deployer.validate_creative_for_ad_platform(meta, "meta_ads")
        assert result["valid"] is True

    def test_too_long_for_tiktok(self):
        meta = {"duration_seconds": 120, "file_size_bytes": 10_000_000}
        result = self.deployer.validate_creative_for_ad_platform(meta, "tiktok_ads")
        assert result["valid"] is False
        assert any("Duration" in e for e in result["errors"])

    def test_file_too_large(self):
        meta = {"duration_seconds": 15, "file_size_bytes": 600_000_000_000}
        result = self.deployer.validate_creative_for_ad_platform(meta, "tiktok_ads")
        assert result["valid"] is False

    def test_unknown_platform_passes(self):
        result = self.deployer.validate_creative_for_ad_platform({}, "youtube_ads")
        assert result["valid"] is True

    def test_specs_include_aspect_ratios(self):
        assert "9:16" in self.deployer.AD_PLATFORM_SPECS["meta_ads"]["aspect_ratios"]
        assert "9:16" in self.deployer.AD_PLATFORM_SPECS["tiktok_ads"]["aspect_ratios"]


class TestAdFatigueDetection:
    """Test ad fatigue detection."""

    def setup_method(self):
        self.deployer = AdDeployer()

    def test_healthy_ad_not_fatigued(self):
        dep = _make_deployment(metrics={
            "impressions": 5000, "ctr": 2.5, "frequency": 1.2, "cpc": 1.5,
        })
        result = self.deployer.detect_ad_fatigue(dep)
        assert result["is_fatigued"] is False
        assert result["recommendation"] == "monitor"

    def test_high_frequency_triggers_fatigue(self):
        dep = _make_deployment(metrics={
            "impressions": 10000, "ctr": 0.3, "frequency": 5.0, "cpc": 6.0,
        })
        result = self.deployer.detect_ad_fatigue(dep)
        assert result["is_fatigued"] is True
        assert result["recommendation"] == "refresh"
        assert result["fatigue_score"] >= 50

    def test_low_ctr_contributes(self):
        dep = _make_deployment(metrics={
            "impressions": 5000, "ctr": 0.2, "frequency": 1.0, "cpc": 1.0,
        })
        result = self.deployer.detect_ad_fatigue(dep)
        assert len(result["signals"]) > 0


class TestBudgetPacing:
    """Test budget pacing checks."""

    def setup_method(self):
        self.deployer = AdDeployer()

    def test_on_pace(self):
        dep = _make_deployment(budget_cents=1000, spend_cents=500)
        result = self.deployer.check_budget_pace(dep, days_elapsed=5, total_days=10)
        assert result["on_pace"] is True
        assert result["status"] == "on_pace"

    def test_underspending(self):
        dep = _make_deployment(budget_cents=1000, spend_cents=100)
        result = self.deployer.check_budget_pace(dep, days_elapsed=8, total_days=10)
        assert result["on_pace"] is False
        assert result["status"] == "underspending"

    def test_overspending(self):
        dep = _make_deployment(budget_cents=1000, spend_cents=900)
        result = self.deployer.check_budget_pace(dep, days_elapsed=3, total_days=10)
        assert result["on_pace"] is False
        assert result["status"] == "overspending"

    def test_zero_days_safe(self):
        dep = _make_deployment()
        result = self.deployer.check_budget_pace(dep, days_elapsed=0, total_days=0)
        assert result["on_pace"] is True


class TestSpendAlerts:
    """Test spend alert system."""

    def setup_method(self):
        self.deployer = AdDeployer()

    def test_under_threshold_no_alert(self):
        dep = _make_deployment(budget_cents=1000, spend_cents=500)
        result = self.deployer.check_spend_alert(dep, alert_threshold_pct=80)
        assert result["alert"] is False
        assert result["overspent"] is False

    def test_over_threshold_alerts(self):
        dep = _make_deployment(budget_cents=1000, spend_cents=850)
        result = self.deployer.check_spend_alert(dep, alert_threshold_pct=80)
        assert result["alert"] is True

    def test_overspent_detected(self):
        dep = _make_deployment(budget_cents=500, spend_cents=600)
        result = self.deployer.check_spend_alert(dep)
        assert result["overspent"] is True


class TestCPATracking:
    """Test cost per acquisition calculation."""

    def setup_method(self):
        self.deployer = AdDeployer()

    def test_normal_cpa(self):
        dep = _make_deployment(spend_cents=1000, metrics={"conversions": 5})
        result = self.deployer.calculate_cpa(dep)
        assert result["cpa_cents"] == 200
        assert result["cpa_usd"] == 2.0

    def test_zero_conversions(self):
        dep = _make_deployment(spend_cents=500, metrics={"conversions": 0})
        result = self.deployer.calculate_cpa(dep)
        assert result["cpa_cents"] == 500  # spend / 1

    def test_fields_present(self):
        dep = _make_deployment()
        result = self.deployer.calculate_cpa(dep)
        assert "deployment_id" in result
        assert "cpa_cents" in result
        assert "cpa_usd" in result


class TestBidStrategy:
    """Test bid strategy selection."""

    def setup_method(self):
        self.deployer = AdDeployer()

    def test_low_budget_lowest_cost(self):
        result = self.deployer.select_bid_strategy("organic", 500)
        assert result["strategy"] == "lowest_cost"

    def test_medium_budget_cost_cap(self):
        result = self.deployer.select_bid_strategy("ad", 3000)
        assert result["strategy"] == "cost_cap"

    def test_high_budget_target_cost(self):
        result = self.deployer.select_bid_strategy("ad", 10000)
        assert result["strategy"] == "target_cost"

    def test_all_strategies_defined(self):
        for key in self.deployer.BID_STRATEGIES:
            assert "description" in self.deployer.BID_STRATEGIES[key]
            assert "meta_key" in self.deployer.BID_STRATEGIES[key]


class TestDayparting:
    """Test dayparting schedule."""

    def setup_method(self):
        self.deployer = AdDeployer()

    def test_schedule_has_all_days(self):
        result = self.deployer.get_daypart_schedule()
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            assert day in result["schedule"]

    def test_schedule_has_start_end(self):
        result = self.deployer.get_daypart_schedule()
        for day, times in result["schedule"].items():
            assert "start" in times
            assert "end" in times

    def test_timezone_parameter(self):
        result = self.deployer.get_daypart_schedule("America/Los_Angeles")
        assert result["timezone"] == "America/Los_Angeles"


class TestAdPreview:
    """Test ad preview link generation."""

    def setup_method(self):
        self.deployer = AdDeployer()

    def test_meta_preview_link(self):
        dep = _make_deployment(
            platform=Platform.META_ADS,
            external_ad_id="12345",
        )
        link = self.deployer.generate_preview_link(dep)
        assert link is not None
        assert "12345" in link
        assert "facebook.com" in link

    def test_no_external_id_returns_none(self):
        dep = _make_deployment(external_ad_id=None)
        link = self.deployer.generate_preview_link(dep)
        assert link is None
