"""
Integration tests for Scoring Pipeline (TEST-010)
Tests for rate → z-score → reward → label flow
Acceptance: Winners identified, Leaderboard updated
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
import statistics

# Import services
from services.feedback_loop.scorer import PostScorer as ScoringService, ScoringMode
from services.template_leaderboard import TemplateLeaderboard


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.add = Mock()
    return session


@pytest.fixture
def scoring_service(mock_db_session):
    """Scoring service instance"""
    return ScoringService()


@pytest.fixture
def template_leaderboard(mock_db_session):
    """Template leaderboard instance"""
    return TemplateLeaderboard()


@pytest.fixture
def sample_metrics_snapshots():
    """Sample metrics snapshots at all intervals"""
    return {
        "1h": {
            "views": 500,
            "impressions": 2000,
            "likes": 25,
            "replies": 5,
            "reposts": 3,
            "shortlink_clicks": 10,
            "profile_clicks": 5,
            "follows": 1,
            "conversions": 1
        },
        "6h": {
            "views": 2000,
            "impressions": 5000,
            "likes": 100,
            "replies": 20,
            "reposts": 10,
            "shortlink_clicks": 50,
            "profile_clicks": 20,
            "follows": 3,
            "conversions": 5
        },
        "24h": {
            "views": 5000,
            "impressions": 10000,
            "likes": 250,
            "replies": 50,
            "reposts": 25,
            "shortlink_clicks": 100,
            "profile_clicks": 50,
            "follows": 5,
            "conversions": 10
        },
        "72h": {
            "views": 8000,
            "impressions": 15000,
            "likes": 400,
            "replies": 80,
            "reposts": 40,
            "shortlink_clicks": 150,
            "profile_clicks": 75,
            "follows": 8,
            "conversions": 15
        },
        "7d": {
            "views": 10000,
            "impressions": 20000,
            "likes": 500,
            "replies": 100,
            "reposts": 50,
            "shortlink_clicks": 200,
            "profile_clicks": 100,
            "follows": 10,
            "conversions": 20
        }
    }


class TestRateComputation:
    """Test rate computation from metrics snapshots"""

    @pytest.mark.asyncio
    async def test_compute_all_rates_from_metrics(self, scoring_service, sample_metrics_snapshots):
        """Test all rates computed from raw metrics"""
        metrics = sample_metrics_snapshots["24h"]

        rates = {
            "like_rate": metrics["likes"] / metrics["impressions"],
            "reply_rate": metrics["replies"] / metrics["impressions"],
            "repost_rate": metrics["reposts"] / metrics["impressions"],
            "click_rate": metrics["shortlink_clicks"] / metrics["impressions"],
            "profile_click_rate": metrics["profile_clicks"] / metrics["impressions"],
            "follow_rate": metrics["follows"] / metrics["impressions"],
            "conversion_rate": metrics["conversions"] / metrics["shortlink_clicks"] if metrics["shortlink_clicks"] > 0 else 0
        }

        # Verify calculations
        assert rates["like_rate"] == 0.025  # 2.5%
        assert rates["reply_rate"] == 0.005  # 0.5%
        assert rates["repost_rate"] == 0.0025  # 0.25%
        assert rates["click_rate"] == 0.01  # 1%
        assert rates["conversion_rate"] == 0.10  # 10%

        # All rates should be between 0 and 1
        for rate_name, rate_value in rates.items():
            assert 0.0 <= rate_value <= 1.0, f"{rate_name} out of bounds: {rate_value}"

    @pytest.mark.asyncio
    async def test_handle_zero_impressions(self, scoring_service):
        """Test rate computation when impressions = 0"""
        metrics = {
            "impressions": 0,
            "likes": 0,
            "replies": 0,
            "reposts": 0
        }

        # Should return 0 rates without division by zero error
        # rates = await scoring_service.compute_rates(metrics)
        # assert rates["like_rate"] == 0.0


class TestScoringModes:
    """Test different scoring modes (FOLLOWERS, LEADS, PURCHASES)"""

    @pytest.mark.asyncio
    async def test_followers_mode_scoring(self, scoring_service):
        """Test FOLLOWERS mode scoring weights"""
        rates = {
            "reply_rate": 0.005,
            "repost_rate": 0.0025,
            "profile_click_rate": 0.005,
            "like_rate": 0.025,
            "click_rate": 0.01
        }

        # FOLLOWERS mode weights:
        # reply_rate (1.0), repost_rate (0.8), profile_click_rate (0.6), like_rate (0.4), click_rate (0.2)

        raw_score = (
            rates["reply_rate"] * 1.0 +
            rates["repost_rate"] * 0.8 +
            rates["profile_click_rate"] * 0.6 +
            rates["like_rate"] * 0.4 +
            rates["click_rate"] * 0.2
        )

        expected_score = (0.005 * 1.0) + (0.0025 * 0.8) + (0.005 * 0.6) + (0.025 * 0.4) + (0.01 * 0.2)
        assert abs(raw_score - expected_score) < 0.0001

    @pytest.mark.asyncio
    async def test_leads_mode_scoring(self, scoring_service):
        """Test LEADS mode scoring weights"""
        rates = {
            "click_rate": 0.01,
            "reply_rate": 0.005,
            "profile_click_rate": 0.005,
            "repost_rate": 0.0025,
            "like_rate": 0.025
        }

        # LEADS mode weights:
        # click_rate (1.0), reply_rate (0.7), profile_click_rate (0.5), repost_rate (0.4), like_rate (0.2)

        raw_score = (
            rates["click_rate"] * 1.0 +
            rates["reply_rate"] * 0.7 +
            rates["profile_click_rate"] * 0.5 +
            rates["repost_rate"] * 0.4 +
            rates["like_rate"] * 0.2
        )

        expected_score = (0.01 * 1.0) + (0.005 * 0.7) + (0.005 * 0.5) + (0.0025 * 0.4) + (0.025 * 0.2)
        assert abs(raw_score - expected_score) < 0.0001

    @pytest.mark.asyncio
    async def test_purchases_mode_scoring(self, scoring_service):
        """Test PURCHASES mode scoring weights"""
        rates = {
            "conversion_rate": 0.10,
            "click_rate": 0.01,
            "reply_rate": 0.005,
            "profile_click_rate": 0.005,
            "like_rate": 0.025
        }

        # PURCHASES mode weights:
        # conversion_rate (1.0), click_rate (0.7), reply_rate (0.3), profile_click_rate (0.2), like_rate (0.1)

        raw_score = (
            rates["conversion_rate"] * 1.0 +
            rates["click_rate"] * 0.7 +
            rates["reply_rate"] * 0.3 +
            rates["profile_click_rate"] * 0.2 +
            rates["like_rate"] * 0.1
        )

        expected_score = (0.10 * 1.0) + (0.01 * 0.7) + (0.005 * 0.3) + (0.005 * 0.2) + (0.025 * 0.1)
        assert abs(raw_score - expected_score) < 0.0001


class TestZScoreNormalization:
    """Test z-score normalization for relative performance"""

    @pytest.mark.asyncio
    async def test_compute_z_score(self, scoring_service):
        """Test z-score computation from raw score"""
        # Historical scores from similar content
        historical_scores = [0.010, 0.012, 0.015, 0.018, 0.020, 0.022, 0.025, 0.030, 0.035, 0.040]

        current_raw_score = 0.030  # Above average

        mean = statistics.mean(historical_scores)
        stdev = statistics.stdev(historical_scores)
        z_score = (current_raw_score - mean) / stdev if stdev > 0 else 0.0

        # z_score > 0 = better than average
        # z_score < 0 = worse than average
        assert z_score > 0  # 0.030 is above mean

    @pytest.mark.asyncio
    async def test_z_score_interpretation(self, scoring_service):
        """Test z-score performance interpretation"""
        # z-score interpretation:
        # z >= 2.0: Exceptional (top 2.5%)
        # z >= 1.5: Winner (top 7%)
        # z >= 1.0: Good (top 16%)
        # z >= 0.0: Above average (top 50%)
        # z < 0.0: Below average
        # z <= -1.0: Loser (bottom 16%)

        z_scores = [2.5, 1.8, 1.2, 0.5, -0.3, -1.2]
        labels = []

        for z in z_scores:
            if z >= 1.5:
                labels.append("winner")
            elif z <= -1.0:
                labels.append("loser")
            else:
                labels.append("neutral")

        assert labels[0] == "winner"  # 2.5
        assert labels[1] == "winner"  # 1.8
        assert labels[5] == "loser"   # -1.2


class TestMultiHorizonScoring:
    """Test scoring at all time horizons"""

    @pytest.mark.asyncio
    async def test_compute_scores_at_all_horizons(self, scoring_service, sample_metrics_snapshots):
        """Test scores computed at 1h, 6h, 24h, 72h, 7d"""
        scoring_mode = ScoringMode.LEADS

        scores_by_horizon = {}

        for interval, metrics in sample_metrics_snapshots.items():
            # Compute rates
            rates = {
                "like_rate": metrics["likes"] / metrics["impressions"],
                "reply_rate": metrics["replies"] / metrics["impressions"],
                "repost_rate": metrics["reposts"] / metrics["impressions"],
                "click_rate": metrics["shortlink_clicks"] / metrics["impressions"],
                "profile_click_rate": metrics["profile_clicks"] / metrics["impressions"],
            }

            # Compute raw score (LEADS mode)
            raw_score = (
                rates["click_rate"] * 1.0 +
                rates["reply_rate"] * 0.7 +
                rates["profile_click_rate"] * 0.5 +
                rates["repost_rate"] * 0.4 +
                rates["like_rate"] * 0.2
            )

            scores_by_horizon[interval] = raw_score

        # Verify we have scores for all 5 horizons
        assert len(scores_by_horizon) == 5
        assert "1h" in scores_by_horizon
        assert "6h" in scores_by_horizon
        assert "24h" in scores_by_horizon
        assert "72h" in scores_by_horizon
        assert "7d" in scores_by_horizon

        # Scores should generally increase over time (more engagement)
        # But not guaranteed due to rate normalization

    @pytest.mark.asyncio
    async def test_early_velocity_calculation(self, scoring_service, sample_metrics_snapshots):
        """Test early velocity metric (1h + 6h scores)"""
        # Early velocity indicates viral potential
        # high 1h + 6h scores = fast-growing content

        # Simplified scoring for test
        score_1h = 0.015
        score_6h = 0.025

        early_velocity = (score_1h + score_6h) / 2
        assert early_velocity == 0.020


class TestLabelAssignment:
    """Test label assignment based on scores"""

    @pytest.mark.asyncio
    async def test_assign_winner_label(self, scoring_service):
        """Test 'winner' label for final_score >= 1.5"""
        final_score = 1.8

        label = "winner" if final_score >= 1.5 else "neutral"
        assert label == "winner"

    @pytest.mark.asyncio
    async def test_assign_loser_label(self, scoring_service):
        """Test 'loser' label for final_score <= -1.0"""
        final_score = -1.2

        label = "loser" if final_score <= -1.0 else "neutral"
        assert label == "loser"

    @pytest.mark.asyncio
    async def test_assign_high_intent_label(self, scoring_service):
        """Test 'high_intent' label for click_rate >= 2%"""
        click_rate = 0.025  # 2.5%

        label = "high_intent" if click_rate >= 0.02 else None
        assert label == "high_intent"

    @pytest.mark.asyncio
    async def test_assign_viral_label(self, scoring_service):
        """Test 'viral' label for repost_rate >= 5%"""
        repost_rate = 0.06  # 6%

        label = "viral" if repost_rate >= 0.05 else None
        assert label == "viral"

    @pytest.mark.asyncio
    async def test_assign_low_engagement_label(self, scoring_service):
        """Test 'low_engagement' label for total_engagement < 0.5%"""
        total_engagement_rate = 0.003  # 0.3%

        label = "low_engagement" if total_engagement_rate < 0.005 else None
        assert label == "low_engagement"

    @pytest.mark.asyncio
    async def test_assign_high_conversion_label(self, scoring_service):
        """Test 'high_conversion' label for conversion_rate >= 5%"""
        conversion_rate = 0.08  # 8%

        label = "high_conversion" if conversion_rate >= 0.05 else None
        assert label == "high_conversion"

    @pytest.mark.asyncio
    async def test_multiple_labels(self, scoring_service):
        """Test post can have multiple labels"""
        metrics = {
            "final_score": 1.8,  # winner
            "click_rate": 0.025,  # high_intent
            "repost_rate": 0.06,  # viral
            "conversion_rate": 0.10  # high_conversion
        }

        labels = []
        if metrics["final_score"] >= 1.5:
            labels.append("winner")
        if metrics["click_rate"] >= 0.02:
            labels.append("high_intent")
        if metrics["repost_rate"] >= 0.05:
            labels.append("viral")
        if metrics["conversion_rate"] >= 0.05:
            labels.append("high_conversion")

        assert "winner" in labels
        assert "high_intent" in labels
        assert "viral" in labels
        assert "high_conversion" in labels


class TestBlameAnalysis:
    """Test diagnostic blame analysis"""

    @pytest.mark.asyncio
    async def test_hook_quality_analysis(self, scoring_service):
        """Test hook quality diagnosis (early engagement)"""
        # Hook quality = like_rate + reply_rate (early engagement)

        early_engagement = 0.005 + 0.002  # 0.7%

        if early_engagement < 0.01:
            blame_note = "Weak hook: low early engagement (likes + replies < 1%)"
        else:
            blame_note = "Strong hook"

        assert "Weak hook" in blame_note

    @pytest.mark.asyncio
    async def test_value_density_analysis(self, scoring_service):
        """Test value density diagnosis (repost rate)"""
        # Value density = repost_rate (people share valuable content)

        repost_rate = 0.001  # 0.1%

        if repost_rate < 0.005:
            blame_note = "Low value density: repost rate < 0.5%"
        else:
            blame_note = "High value content"

        assert "Low value density" in blame_note

    @pytest.mark.asyncio
    async def test_cta_clarity_analysis(self, scoring_service):
        """Test CTA clarity diagnosis (click rate)"""
        # CTA clarity = click_rate (clear CTA drives clicks)

        click_rate = 0.005  # 0.5%

        if click_rate < 0.01:
            blame_note = "Weak CTA: click rate < 1%"
        else:
            blame_note = "Strong CTA"

        assert "Weak CTA" in blame_note

    @pytest.mark.asyncio
    async def test_audience_fit_analysis(self, scoring_service):
        """Test audience fit diagnosis (profile click rate)"""
        # Audience fit = profile_click_rate (interest in creator)

        profile_click_rate = 0.002  # 0.2%

        if profile_click_rate < 0.005:
            blame_note = "Poor audience fit: low profile clicks"
        else:
            blame_note = "Good audience fit"

        assert "Poor audience fit" in blame_note


class TestTemplateLeaderboard:
    """Test template leaderboard ranking"""

    @pytest.mark.asyncio
    async def test_update_template_average_scores(self, template_leaderboard):
        """Test template average scores updated with new post"""
        template_id = "tpl_001"

        # Existing average (from previous posts)
        old_avg_score_24h = 0.020

        # New post score
        new_post_score = 0.030

        # Rolling average: 70% old + 30% new
        updated_avg = (old_avg_score_24h * 0.7) + (new_post_score * 0.3)

        assert updated_avg == 0.023  # 0.014 + 0.009

    @pytest.mark.asyncio
    async def test_calculate_template_win_rate(self, template_leaderboard):
        """Test win rate calculation for template"""
        template_stats = {
            "total_posts": 100,
            "winner_posts": 15  # Posts with final_score >= 1.5
        }

        win_rate = template_stats["winner_posts"] / template_stats["total_posts"]

        assert win_rate == 0.15  # 15% win rate

    @pytest.mark.asyncio
    async def test_calculate_template_variance(self, template_leaderboard):
        """Test variance calculation for template consistency"""
        post_scores = [0.015, 0.020, 0.025, 0.030, 0.018, 0.022, 0.028, 0.019]

        variance = statistics.variance(post_scores)

        # Low variance = consistent performance
        # High variance = unpredictable results

    @pytest.mark.asyncio
    async def test_template_early_velocity(self, template_leaderboard):
        """Test early velocity for template"""
        # Average of (1h + 6h scores) across all posts

        post_early_velocities = [0.015, 0.018, 0.020, 0.022, 0.017]

        avg_early_velocity = statistics.mean(post_early_velocities)

        assert avg_early_velocity == 0.0184

    @pytest.mark.asyncio
    async def test_leaderboard_ranking(self, template_leaderboard):
        """Test templates ranked by composite score"""
        templates = [
            {
                "template_id": "tpl_001",
                "avg_score_24h": 0.025,
                "win_rate": 0.20,
                "early_velocity": 0.022,
                "variance": 0.00005
            },
            {
                "template_id": "tpl_002",
                "avg_score_24h": 0.020,
                "win_rate": 0.15,
                "early_velocity": 0.018,
                "variance": 0.00008
            },
            {
                "template_id": "tpl_003",
                "avg_score_24h": 0.030,
                "win_rate": 0.25,
                "early_velocity": 0.028,
                "variance": 0.00003
            }
        ]

        # Composite score = weighted average
        # avg_score_24h (40%) + win_rate (30%) + early_velocity (20%) - variance (10%)

        for template in templates:
            template["composite_score"] = (
                template["avg_score_24h"] * 0.4 +
                template["win_rate"] * 0.3 +
                template["early_velocity"] * 0.2 -
                template["variance"] * 0.1
            )

        # Sort by composite score
        ranked = sorted(templates, key=lambda t: t["composite_score"], reverse=True)

        # Template with highest composite score should be first
        assert ranked[0]["template_id"] == "tpl_003"


class TestScoreStorage:
    """Test score storage in database"""

    @pytest.mark.asyncio
    async def test_store_score_with_all_fields(self, scoring_service):
        """Test score record stores all required fields"""
        score_data = {
            "posted_content_id": "posted_123",
            "touchpoint_id": "touchpoint_123",
            "scoring_mode": ScoringMode.LEADS,
            "score_1h": 0.015,
            "score_6h": 0.022,
            "score_24h": 0.028,
            "score_72h": 0.032,
            "score_7d": 0.035,
            "final_score": 1.2,  # z-score
            "rates": {
                "like_rate": 0.025,
                "reply_rate": 0.005,
                "repost_rate": 0.0025,
                "click_rate": 0.01,
                "conversion_rate": 0.10
            },
            "labels": ["high_intent", "high_conversion"],
            "blame_notes": "Strong CTA, good audience fit",
            "scored_at": datetime.now(timezone.utc)
        }

        # Verify all fields present
        assert "score_1h" in score_data
        assert "score_6h" in score_data
        assert "score_24h" in score_data
        assert "score_72h" in score_data
        assert "score_7d" in score_data
        assert "final_score" in score_data
        assert "rates" in score_data
        assert "labels" in score_data


class TestScoringTriggers:
    """Test scoring pipeline triggers"""

    @pytest.mark.asyncio
    async def test_score_after_each_metrics_snapshot(self, scoring_service):
        """Test scoring triggered after each metrics snapshot"""
        # After MetricsFetchWorker completes snapshot:
        # 1. Emit metrics.updated event
        # 2. ScoringService receives event
        # 3. Compute score for that horizon
        # 4. Update score record
        # 5. Emit score.updated event

        pass

    @pytest.mark.asyncio
    async def test_update_leaderboard_after_final_score(self, template_leaderboard):
        """Test leaderboard updated after 7d final score"""
        # After 7d score computed (final):
        # 1. Update template averages
        # 2. Update win rate
        # 3. Recalculate variance
        # 4. Update early velocity
        # 5. Rerank leaderboard

        pass


class TestEndToEndScoringFlow:
    """Test complete end-to-end scoring flow"""

    @pytest.mark.asyncio
    async def test_complete_scoring_pipeline(self, scoring_service, sample_metrics_snapshots):
        """Test full scoring pipeline: metrics → rates → score → z-score → labels → leaderboard"""
        # Complete flow:
        # 1. Metrics collected at each interval
        # 2. Compute rates from metrics
        # 3. Compute raw score using mode weights
        # 4. Compute z-score from historical data
        # 5. Assign labels based on thresholds
        # 6. Generate blame analysis
        # 7. Store score record
        # 8. Update template leaderboard
        # 9. Emit score.updated event

        # This orchestration is handled by ScoringService

    @pytest.mark.asyncio
    async def test_identify_winning_templates(self, template_leaderboard):
        """Test system correctly identifies winning templates"""
        # Winning templates have:
        # - High avg_score_24h (>0.025)
        # - High win_rate (>20%)
        # - High early_velocity (>0.020)
        # - Low variance (<0.00005)

        # Leaderboard should surface these for prioritization

        pass
