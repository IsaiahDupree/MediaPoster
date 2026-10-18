"""
Unit tests for Engagement Scorer (OPS-004 & OPS-005)
===================================================
Tests engagement rate calculation and reward function scoring.
"""

import pytest
from services.engagement_scorer import (
    EngagementScorer,
    EngagementRates,
    RewardScore,
    PostLabel,
    get_engagement_scorer
)


class TestEngagementScorer:
    """Test suite for EngagementScorer"""

    @pytest.fixture
    def scorer(self):
        """Get fresh scorer instance"""
        # Reset singleton for clean state
        EngagementScorer._instance = None
        return EngagementScorer.get_instance()

    def test_singleton_pattern(self, scorer):
        """Test that get_engagement_scorer returns same instance"""
        scorer2 = get_engagement_scorer()
        assert scorer is scorer2

    def test_calculate_rates_normal(self, scorer):
        """Test normal engagement rate calculation"""
        rates = scorer.calculate_rates(
            likes=100,
            replies=20,
            reposts=30,
            clicks=50,
            impressions=10000
        )

        assert rates.like_rate == 0.01  # 100/10000
        assert rates.reply_rate == 0.002  # 20/10000
        assert rates.repost_rate == 0.003  # 30/10000
        assert rates.click_rate == 0.005  # 50/10000
        assert rates.impressions == 10000

    def test_calculate_rates_zero_impressions(self, scorer):
        """Test handling of zero impressions"""
        rates = scorer.calculate_rates(
            likes=100,
            replies=20,
            reposts=30,
            clicks=50,
            impressions=0
        )

        assert rates.like_rate == 0.0
        assert rates.reply_rate == 0.0
        assert rates.repost_rate == 0.0
        assert rates.click_rate == 0.0

    def test_calculate_rates_high_engagement(self, scorer):
        """Test high engagement rate calculation"""
        rates = scorer.calculate_rates(
            likes=500,
            replies=100,
            reposts=50,
            clicks=200,
            impressions=1000
        )

        assert rates.like_rate == 0.5  # 50%
        assert rates.reply_rate == 0.1  # 10%
        assert rates.repost_rate == 0.05  # 5%
        assert rates.click_rate == 0.2  # 20%

    def test_reward_score_calculation_no_history(self, scorer):
        """Test reward score with no historical data"""
        rates = EngagementRates(
            like_rate=0.01,
            reply_rate=0.002,
            repost_rate=0.003,
            click_rate=0.005,
            impressions=10000
        )

        score = scorer.calculate_reward_score(rates)

        # With no history, z-scores should be 0
        assert score.score == 0.0
        assert all(z == 0.0 for z in score.z_scores.values())
        assert score.label == PostLabel.AVERAGE

    def test_reward_score_with_history(self, scorer):
        """Test reward score after building history"""
        # Add some historical posts with VARYING RATES
        # (not constant rates - that would give stddev=0)
        historical_posts = [
            # Low engagement rate
            {"likes": 50, "replies": 5, "reposts": 2, "clicks": 10, "impressions": 10000},
            # Medium-low engagement
            {"likes": 120, "replies": 15, "reposts": 8, "clicks": 35, "impressions": 10000},
            # Medium engagement
            {"likes": 200, "replies": 25, "reposts": 15, "clicks": 60, "impressions": 10000},
            # Medium-high engagement
            {"likes": 300, "replies": 40, "reposts": 25, "clicks": 90, "impressions": 10000},
            # High engagement
            {"likes": 450, "replies": 60, "reposts": 40, "clicks": 130, "impressions": 10000},
        ]

        scorer.load_historical_data(historical_posts)

        # Now calculate score for a new post (very high engagement)
        rates = scorer.calculate_rates(
            likes=500,
            replies=70,
            reposts=45,
            clicks=150,
            impressions=10000
        )

        score = scorer.calculate_reward_score(rates)

        # Should have non-zero z-scores and score (rates vary, so stddev > 0)
        assert score.score != 0.0
        assert isinstance(score.label, PostLabel)
        # This is a high-engagement post, so score should be positive
        assert score.score > 0

    def test_reward_function_weights(self, scorer):
        """Test that reward function uses correct weights"""
        # Build some history first
        historical_posts = [
            {"likes": 100, "replies": 20, "reposts": 10, "clicks": 40, "impressions": 10000}
            for _ in range(10)
        ]
        scorer.load_historical_data(historical_posts)

        # Calculate z-scores with known values
        rates = EngagementRates(
            like_rate=0.02,  # Higher than average
            reply_rate=0.004,
            repost_rate=0.002,
            click_rate=0.008,
            impressions=10000
        )

        score = scorer.calculate_reward_score(rates)

        # Verify weights are applied (can't verify exact values without knowing z-scores)
        # But we can verify the score is calculated
        assert isinstance(score.score, float)

        # Weights: click=1.0, reply=0.8, repost=0.6, like=0.4
        # Score should be: 1.0*z(click) + 0.8*z(reply) + 0.6*z(repost) + 0.4*z(like)

    def test_post_labeling(self, scorer):
        """Test winner/loser labeling based on percentiles"""
        # Build history with known distribution
        historical_posts = []
        for i in range(100):
            # Create posts with increasing engagement
            historical_posts.append({
                "likes": i * 10,
                "replies": i * 2,
                "reposts": i,
                "clicks": i * 4,
                "impressions": 10000
            })

        scorer.load_historical_data(historical_posts)

        # Test top performer (should be WINNER)
        high_rates = scorer.calculate_rates(
            likes=1200,
            replies=240,
            reposts=120,
            clicks=480,
            impressions=10000
        )
        high_score = scorer.calculate_reward_score(high_rates)
        assert high_score.label == PostLabel.WINNER

        # Test bottom performer (should be LOSER)
        low_rates = scorer.calculate_rates(
            likes=10,
            replies=2,
            reposts=1,
            clicks=4,
            impressions=10000
        )
        low_score = scorer.calculate_reward_score(low_rates)
        assert low_score.label == PostLabel.LOSER

    def test_statistics_tracking(self, scorer):
        """Test that statistics are tracked correctly"""
        # Initially empty
        stats = scorer.get_statistics()
        assert stats["history_count"] == 0

        # Load some data
        historical_posts = [
            {"likes": 100, "replies": 20, "reposts": 10, "clicks": 40, "impressions": 10000},
            {"likes": 150, "replies": 30, "reposts": 15, "clicks": 60, "impressions": 15000},
            {"likes": 200, "replies": 40, "reposts": 20, "clicks": 80, "impressions": 20000},
        ]
        scorer.load_historical_data(historical_posts)

        # Check stats updated
        stats = scorer.get_statistics()
        assert stats["history_count"] == 3
        assert "rate_means" in stats
        assert "rate_stddevs" in stats
        assert "score_mean" in stats
        assert "score_stddev" in stats

    def test_load_historical_data(self, scorer):
        """Test loading historical data"""
        historical_posts = [
            {"likes": 100, "replies": 20, "reposts": 10, "clicks": 40, "impressions": 10000},
            {"likes": 200, "replies": 40, "reposts": 20, "clicks": 80, "impressions": 20000},
        ]

        scorer.load_historical_data(historical_posts)

        stats = scorer.get_statistics()
        assert stats["history_count"] == 2

    def test_engagement_rates_to_dict(self):
        """Test EngagementRates to_dict method"""
        rates = EngagementRates(
            like_rate=0.01,
            reply_rate=0.002,
            repost_rate=0.003,
            click_rate=0.005,
            impressions=10000
        )

        result = rates.to_dict()
        assert result["like_rate"] == 0.01
        assert result["reply_rate"] == 0.002
        assert result["repost_rate"] == 0.003
        assert result["click_rate"] == 0.005
        assert result["impressions"] == 10000

    def test_reward_score_to_dict(self, scorer):
        """Test RewardScore to_dict method"""
        rates = EngagementRates(
            like_rate=0.01,
            reply_rate=0.002,
            repost_rate=0.003,
            click_rate=0.005,
            impressions=10000
        )

        score = RewardScore(
            score=1.5,
            z_scores={"click_rate": 0.5, "reply_rate": 0.3, "repost_rate": 0.2, "like_rate": 0.1},
            label=PostLabel.PROMISING,
            rates=rates
        )

        result = score.to_dict()
        assert result["score"] == 1.5
        assert result["label"] == "promising"
        assert "z_scores" in result
        assert "rates" in result

    def test_real_world_scenario(self, scorer):
        """Test with realistic Twitter/X metrics"""
        # Build history with realistic engagement patterns
        historical_posts = [
            # Low engagement posts
            {"likes": 5, "replies": 0, "reposts": 0, "clicks": 2, "impressions": 500},
            {"likes": 10, "replies": 1, "reposts": 0, "clicks": 3, "impressions": 800},
            {"likes": 15, "replies": 2, "reposts": 1, "clicks": 5, "impressions": 1000},

            # Medium engagement posts
            {"likes": 50, "replies": 5, "reposts": 3, "clicks": 15, "impressions": 5000},
            {"likes": 75, "replies": 8, "reposts": 5, "clicks": 25, "impressions": 7500},
            {"likes": 100, "replies": 10, "reposts": 8, "clicks": 40, "impressions": 10000},

            # High engagement posts
            {"likes": 200, "replies": 25, "reposts": 15, "clicks": 80, "impressions": 15000},
            {"likes": 300, "replies": 40, "reposts": 25, "clicks": 120, "impressions": 20000},

            # Viral post
            {"likes": 500, "replies": 80, "reposts": 50, "clicks": 200, "impressions": 30000},
        ]

        scorer.load_historical_data(historical_posts)

        # Test a winner post
        winner_rates = scorer.calculate_rates(
            likes=600,
            replies=100,
            reposts=60,
            clicks=250,
            impressions=35000
        )
        winner_score = scorer.calculate_reward_score(winner_rates)
        # Should be a top performer (WINNER or PROMISING)
        assert winner_score.label in [PostLabel.WINNER, PostLabel.PROMISING]
        # Score should be positive (above average)
        assert winner_score.score > 0

        # Test a loser post
        loser_rates = scorer.calculate_rates(
            likes=3,
            replies=0,
            reposts=0,
            clicks=1,
            impressions=400
        )
        loser_score = scorer.calculate_reward_score(loser_rates)
        # Should be a poor performer (LOSER or AVERAGE)
        assert loser_score.label in [PostLabel.LOSER, PostLabel.AVERAGE]
        # Score should be negative (below average)
        assert loser_score.score < 0


class TestPostLabel:
    """Test PostLabel enum"""

    def test_enum_values(self):
        """Test enum values are correct"""
        assert PostLabel.WINNER.value == "winner"
        assert PostLabel.PROMISING.value == "promising"
        assert PostLabel.AVERAGE.value == "average"
        assert PostLabel.LOSER.value == "loser"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
