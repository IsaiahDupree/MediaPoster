"""
Tests for ACTP Winner Selector
"""

import pytest
from datetime import datetime, timedelta, timezone

from services.creative_testing_pipeline.winner_selector import WinnerSelector
from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
from services.creative_testing_pipeline.models import (
    AdDeployment,
    AdDeploymentStatus,
    Creative,
    GenerationSource,
    OrganicPost,
    Platform,
)
from services.creative_testing_pipeline.config import ACTPConfig


class TestOrganicScoring:
    """Test organic quality score calculation."""

    def setup_method(self):
        self.config = ACTPConfig()
        self.analytics = AnalyticsCollector(config=self.config)

    def test_high_engagement_high_score(self):
        metrics = {
            "views": 10000,
            "likes": 500,
            "comments": 50,
            "shares": 100,
            "watch_time_seconds": 12,
        }
        score = self.analytics.calculate_organic_score(
            metrics, Platform.YOUTUBE_SHORTS, post_age_hours=24.0
        )
        assert score > 50
        assert score <= 100

    def test_zero_views_returns_low_score(self):
        metrics = {"views": 0, "likes": 0, "comments": 0, "shares": 0}
        score = self.analytics.calculate_organic_score(
            metrics, Platform.TIKTOK, post_age_hours=24.0
        )
        assert score >= 0
        assert score < 10

    def test_high_view_velocity_boosts_score(self):
        metrics_slow = {"views": 100, "likes": 5, "comments": 1, "shares": 0}
        metrics_fast = {"views": 100, "likes": 5, "comments": 1, "shares": 0}

        score_slow = self.analytics.calculate_organic_score(
            metrics_slow, Platform.TIKTOK, post_age_hours=48.0
        )
        score_fast = self.analytics.calculate_organic_score(
            metrics_fast, Platform.TIKTOK, post_age_hours=1.0
        )
        assert score_fast > score_slow

    def test_tiktok_completion_rate_included(self):
        metrics_low = {
            "views": 1000, "likes": 50, "comments": 5, "shares": 10,
            "completion_rate": 0.1,
        }
        metrics_high = {
            "views": 1000, "likes": 50, "comments": 5, "shares": 10,
            "completion_rate": 0.9,
        }
        score_low = self.analytics.calculate_organic_score(
            metrics_low, Platform.TIKTOK, post_age_hours=24.0
        )
        score_high = self.analytics.calculate_organic_score(
            metrics_high, Platform.TIKTOK, post_age_hours=24.0
        )
        assert score_high > score_low

    def test_score_capped_at_100(self):
        metrics = {
            "views": 1000000, "likes": 100000, "comments": 50000,
            "shares": 50000, "watch_time_seconds": 60, "completion_rate": 1.0,
        }
        score = self.analytics.calculate_organic_score(
            metrics, Platform.YOUTUBE_SHORTS, post_age_hours=1.0
        )
        assert score <= 100


class TestAdScoring:
    """Test ad performance score calculation."""

    def setup_method(self):
        self.config = ACTPConfig()
        self.analytics = AnalyticsCollector(config=self.config)

    def test_high_ctr_high_score(self):
        metrics = {
            "impressions": 10000, "clicks": 300, "spend_cents": 500,
            "three_second_views": 5000, "thru_plays": 2000, "conversions": 10,
        }
        score = self.analytics.calculate_ad_score(metrics)
        assert score > 40

    def test_zero_clicks_low_score(self):
        metrics = {
            "impressions": 10000, "clicks": 0, "spend_cents": 500,
            "three_second_views": 0, "thru_plays": 0, "conversions": 0,
        }
        score = self.analytics.calculate_ad_score(metrics)
        assert score < 20

    def test_efficient_cpc_boosts_score(self):
        # Same clicks but lower spend = better CPC efficiency
        metrics_expensive = {
            "impressions": 10000, "clicks": 100, "spend_cents": 5000,
            "three_second_views": 3000, "thru_plays": 1000, "conversions": 5,
        }
        metrics_cheap = {
            "impressions": 10000, "clicks": 100, "spend_cents": 100,
            "three_second_views": 3000, "thru_plays": 1000, "conversions": 5,
        }
        score_expensive = self.analytics.calculate_ad_score(metrics_expensive)
        score_cheap = self.analytics.calculate_ad_score(metrics_cheap)
        assert score_cheap > score_expensive

    def test_ad_score_capped_at_100(self):
        metrics = {
            "impressions": 100, "clicks": 50, "spend_cents": 1,
            "three_second_views": 90, "thru_plays": 80, "conversions": 30,
        }
        score = self.analytics.calculate_ad_score(metrics)
        assert score <= 100


class TestSufficientDataChecks:
    """Test minimum data thresholds."""

    def setup_method(self):
        self.selector = WinnerSelector()

    def test_sufficient_organic_data(self):
        posts = [
            OrganicPost(
                creative_id="c1", platform=Platform.TIKTOK,
                status="published", metrics={"views": 150},
            )
        ]
        assert self.selector.has_sufficient_data(posts, min_views=100) is True

    def test_insufficient_organic_data(self):
        posts = [
            OrganicPost(
                creative_id="c1", platform=Platform.TIKTOK,
                status="published", metrics={"views": 50},
            )
        ]
        assert self.selector.has_sufficient_data(posts, min_views=100) is False

    def test_unpublished_posts_ignored(self):
        posts = [
            OrganicPost(
                creative_id="c1", platform=Platform.TIKTOK,
                status="failed", metrics={"views": 500},
            )
        ]
        assert self.selector.has_sufficient_data(posts, min_views=100) is False

    def test_sufficient_ad_data(self):
        ads = [
            AdDeployment(
                creative_id="c1", round_id="r1", platform=Platform.META_ADS,
                metrics={"impressions": 1500},
            )
        ]
        assert self.selector.has_sufficient_ad_data(ads, min_impressions=1000) is True

    def test_insufficient_ad_data(self):
        ads = [
            AdDeployment(
                creative_id="c1", round_id="r1", platform=Platform.META_ADS,
                metrics={"impressions": 500},
            )
        ]
        assert self.selector.has_sufficient_ad_data(ads, min_impressions=1000) is False


class TestWinnerSelectionRanking:
    """Test that winners are correctly ranked and selected."""

    def setup_method(self):
        self.selector = WinnerSelector()

    @pytest.mark.asyncio
    async def test_organic_winners_ranked_by_score(self):
        creatives = [
            Creative(id="c1", campaign_id="camp1", round_id="r1",
                     hook="Hook A", generation_source=GenerationSource.SORA),
            Creative(id="c2", campaign_id="camp1", round_id="r1",
                     hook="Hook B", generation_source=GenerationSource.SORA),
            Creative(id="c3", campaign_id="camp1", round_id="r1",
                     hook="Hook C", generation_source=GenerationSource.SORA),
        ]
        posts = [
            OrganicPost(
                creative_id="c1", platform=Platform.TIKTOK,
                status="published", metrics={"views": 500, "likes": 10, "comments": 1, "shares": 0},
                posted_at=datetime.now(timezone.utc) - timedelta(hours=24),
            ),
            OrganicPost(
                creative_id="c2", platform=Platform.TIKTOK,
                status="published", metrics={"views": 5000, "likes": 300, "comments": 50, "shares": 100},
                posted_at=datetime.now(timezone.utc) - timedelta(hours=24),
            ),
            OrganicPost(
                creative_id="c3", platform=Platform.TIKTOK,
                status="published", metrics={"views": 1000, "likes": 30, "comments": 5, "shares": 2},
                posted_at=datetime.now(timezone.utc) - timedelta(hours=24),
            ),
        ]

        winners = await self.selector.select_organic_winners(
            creatives, posts, "r1", top_n=2
        )

        assert len(winners) == 2
        # c2 should be #1 (highest engagement)
        assert winners[0].creative_id == "c2"
        assert winners[0].rank == 1
        assert winners[0].score > winners[1].score


class TestTieBreaking:
    """Test tie-breaking logic."""

    def setup_method(self):
        self.selector = WinnerSelector()

    def test_higher_shares_wins(self):
        a = Creative(id="a", campaign_id="c1", round_id="r1", generation_source=GenerationSource.SORA)
        b = Creative(id="b", campaign_id="c1", round_id="r1", generation_source=GenerationSource.SORA)

        posts_a = [OrganicPost(
            creative_id="a", platform=Platform.TIKTOK, status="published",
            metrics={"views": 1000, "likes": 50, "comments": 5, "shares": 20},
        )]
        posts_b = [OrganicPost(
            creative_id="b", platform=Platform.TIKTOK, status="published",
            metrics={"views": 1000, "likes": 50, "comments": 5, "shares": 10},
        )]

        winner = self.selector.break_tie(a, b, posts_a, posts_b)
        assert winner.id == "a"

    def test_higher_comments_breaks_share_tie(self):
        a = Creative(id="a", campaign_id="c1", round_id="r1", generation_source=GenerationSource.SORA)
        b = Creative(id="b", campaign_id="c1", round_id="r1", generation_source=GenerationSource.SORA)

        posts_a = [OrganicPost(
            creative_id="a", platform=Platform.TIKTOK, status="published",
            metrics={"views": 1000, "likes": 50, "comments": 10, "shares": 5},
        )]
        posts_b = [OrganicPost(
            creative_id="b", platform=Platform.TIKTOK, status="published",
            metrics={"views": 1000, "likes": 50, "comments": 3, "shares": 5},
        )]

        winner = self.selector.break_tie(a, b, posts_a, posts_b)
        assert winner.id == "a"

    def test_recency_as_final_tiebreak(self):
        now = datetime.now(timezone.utc)
        a = Creative(
            id="a", campaign_id="c1", round_id="r1",
            generation_source=GenerationSource.SORA,
            created_at=now - timedelta(hours=2),
        )
        b = Creative(
            id="b", campaign_id="c1", round_id="r1",
            generation_source=GenerationSource.SORA,
            created_at=now,
        )

        posts_a = [OrganicPost(
            creative_id="a", platform=Platform.TIKTOK, status="published",
            metrics={"views": 1000, "likes": 50, "comments": 5, "shares": 5},
        )]
        posts_b = [OrganicPost(
            creative_id="b", platform=Platform.TIKTOK, status="published",
            metrics={"views": 1000, "likes": 50, "comments": 5, "shares": 5},
        )]

        winner = self.selector.break_tie(a, b, posts_a, posts_b)
        assert winner.id == "b"  # newer wins


class TestBayesianConfidence:
    """Test Bayesian confidence scoring."""

    def setup_method(self):
        self.selector = WinnerSelector()

    def test_basic_confidence(self):
        result = self.selector.bayesian_confidence(50, 1000)
        assert 0 < result["mean"] < 1
        assert result["lower_95"] < result["mean"]
        assert result["upper_95"] > result["mean"]
        assert result["samples"] == 1000

    def test_more_data_narrows_interval(self):
        small = self.selector.bayesian_confidence(5, 10)
        large = self.selector.bayesian_confidence(500, 1000)
        small_width = small["upper_95"] - small["lower_95"]
        large_width = large["upper_95"] - large["lower_95"]
        assert large_width < small_width

    def test_zero_successes(self):
        result = self.selector.bayesian_confidence(0, 100)
        assert result["mean"] < 0.1
        assert result["lower_95"] >= 0

    def test_all_successes(self):
        result = self.selector.bayesian_confidence(100, 100)
        assert result["mean"] > 0.9
        assert result["upper_95"] <= 1.0

    def test_score_with_confidence(self):
        creative = Creative(
            id="c1", campaign_id="c1", round_id="r1",
            generation_source=GenerationSource.SORA,
        )
        posts = [
            OrganicPost(
                creative_id="c1", platform=Platform.TIKTOK, status="published",
                metrics={"views": 1000, "likes": 50, "comments": 10, "shares": 5},
            ),
        ]
        result = self.selector.score_with_confidence(creative, posts)
        assert "engagement_rate" in result
        assert "confidence_interval" in result
        assert result["total_views"] == 1000
        assert result["total_engagements"] == 65


class TestThompsonSampling:
    """Test Thompson Sampling exploration."""

    def setup_method(self):
        self.selector = WinnerSelector()

    def test_returns_scored_list(self):
        items = [
            {"creative_id": "a", "views": 1000, "engagements": 100},
            {"creative_id": "b", "views": 1000, "engagements": 50},
            {"creative_id": "c", "views": 1000, "engagements": 200},
        ]
        result = self.selector.thompson_sampling_score(items)
        assert len(result) == 3
        assert all("thompson_score" in r for r in result)
        assert all("mean" in r for r in result)

    def test_sorted_by_score(self):
        items = [
            {"creative_id": "a", "views": 100, "engagements": 10},
            {"creative_id": "b", "views": 100, "engagements": 50},
        ]
        result = self.selector.thompson_sampling_score(items)
        assert result[0]["thompson_score"] >= result[1]["thompson_score"]

    def test_zero_engagement_handled(self):
        items = [{"creative_id": "a", "views": 0, "engagements": 0}]
        result = self.selector.thompson_sampling_score(items)
        assert len(result) == 1
        assert result[0]["thompson_score"] >= 0


class TestElimination:
    """Test elimination round logic."""

    def setup_method(self):
        self.selector = WinnerSelector()

    def test_eliminates_bottom_half(self):
        creatives = [
            Creative(id=f"c{i}", campaign_id="c1", round_id="r1",
                     generation_source=GenerationSource.SORA, organic_score=i * 10)
            for i in range(10)
        ]
        survivors, eliminated = self.selector.eliminate_bottom_performers(creatives, 0.5)
        assert len(survivors) == 5
        assert len(eliminated) == 5
        # All survivors should have higher scores than eliminated
        min_survivor = min(s.organic_score for s in survivors)
        max_eliminated = max(e.organic_score for e in eliminated)
        assert min_survivor >= max_eliminated

    def test_empty_list(self):
        survivors, eliminated = self.selector.eliminate_bottom_performers([])
        assert survivors == []
        assert eliminated == []

    def test_keeps_at_least_one(self):
        creatives = [
            Creative(id="c1", campaign_id="c1", round_id="r1",
                     generation_source=GenerationSource.SORA, organic_score=50)
        ]
        survivors, eliminated = self.selector.eliminate_bottom_performers(creatives, 0.9)
        assert len(survivors) >= 1

    def test_custom_elimination_pct(self):
        creatives = [
            Creative(id=f"c{i}", campaign_id="c1", round_id="r1",
                     generation_source=GenerationSource.SORA, organic_score=i * 5)
            for i in range(20)
        ]
        survivors, _ = self.selector.eliminate_bottom_performers(creatives, 0.75)
        assert len(survivors) == 5  # keep top 25%
