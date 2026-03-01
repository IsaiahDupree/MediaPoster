"""
Tests for ACTP Analytics Collector - Cross-Platform Normalization
"""

import pytest

from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
from services.creative_testing_pipeline.models import Platform
from services.creative_testing_pipeline.config import ACTPConfig


class TestCrossPlatformNormalization:
    """Test that metrics are normalized fairly across platforms."""

    def setup_method(self):
        self.config = ACTPConfig()
        self.analytics = AnalyticsCollector(config=self.config)

    def test_similar_performance_similar_scores(self):
        """Same engagement rate on different platforms should produce similar scores."""
        youtube_metrics = {
            "views": 10000, "likes": 500, "comments": 50,
            "shares": 20, "watch_time_seconds": 12,
        }
        tiktok_metrics = {
            "views": 10000, "likes": 500, "comments": 50,
            "shares": 20, "completion_rate": 0.8,
        }

        yt_score = self.analytics.calculate_organic_score(
            youtube_metrics, Platform.YOUTUBE_SHORTS, 24.0
        )
        tt_score = self.analytics.calculate_organic_score(
            tiktok_metrics, Platform.TIKTOK, 24.0
        )

        # Scores should be within 30 points of each other
        assert abs(yt_score - tt_score) < 30

    def test_empty_metrics_returns_zero(self):
        score = self.analytics.calculate_organic_score({}, Platform.TIKTOK, 24.0)
        assert score >= 0
        assert score < 5

    def test_instagram_defaults_to_50_completion(self):
        """Instagram has no completion rate so defaults to 50."""
        metrics = {"views": 1000, "likes": 50, "comments": 5, "shares": 2}
        score = self.analytics.calculate_organic_score(
            metrics, Platform.INSTAGRAM_REELS, 24.0
        )
        assert score > 0


class TestAdScoreEdgeCases:
    """Test ad scoring edge cases."""

    def setup_method(self):
        self.analytics = AnalyticsCollector()

    def test_zero_impressions_safe(self):
        metrics = {"impressions": 0, "clicks": 0, "spend_cents": 0}
        score = self.analytics.calculate_ad_score(metrics)
        assert score >= 0

    def test_high_spend_low_clicks_penalized(self):
        metrics = {
            "impressions": 10000, "clicks": 2, "spend_cents": 5000,
            "three_second_views": 100, "thru_plays": 10, "conversions": 0,
        }
        score = self.analytics.calculate_ad_score(metrics)
        assert score < 30

    def test_perfect_metrics_near_100(self):
        metrics = {
            "impressions": 1000, "clicks": 50, "spend_cents": 50,
            "three_second_views": 800, "thru_plays": 600, "conversions": 20,
        }
        score = self.analytics.calculate_ad_score(metrics)
        assert score > 70
