"""
Tests for Auto-Curator Service (CUR-005)
"""
import pytest
from services.auto_curator import (
    AutoCurator,
    CurationRule,
    CurationDecision,
    get_auto_curator
)


class TestAutoCurator:
    """Test auto-curator basic functionality"""

    def test_curator_initialization(self):
        """Test curator initializes with default rules"""
        curator = AutoCurator()

        assert curator is not None
        assert len(curator.list_rules()) > 0

    def test_singleton_pattern(self):
        """Test curator singleton pattern"""
        curator1 = get_auto_curator()
        curator2 = get_auto_curator()

        assert curator1 is curator2

    def test_add_rule(self):
        """Test adding a curation rule"""
        curator = AutoCurator()

        rule = CurationRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test description",
            conditions={"sentiment_score": {"min": 0.7}},
            decision=CurationDecision.APPROVE,
            priority=5
        )

        initial_count = len(curator.list_rules())
        curator.add_rule(rule)

        assert len(curator.list_rules()) == initial_count + 1

    def test_remove_rule(self):
        """Test removing a curation rule"""
        curator = AutoCurator()

        rule = CurationRule(
            rule_id="removable_rule",
            name="Removable",
            description="Will be removed",
            conditions={},
            decision=CurationDecision.MANUAL_REVIEW
        )

        curator.add_rule(rule)
        assert curator.get_rule("removable_rule") is not None

        removed = curator.remove_rule("removable_rule")
        assert removed is True
        assert curator.get_rule("removable_rule") is None

    def test_curate_high_quality_content(self):
        """Test curation of high quality content"""
        curator = AutoCurator()

        content_analysis = {
            "sentiment_score": 0.9,
            "quality_score": 0.85,
            "brand_safety_score": 0.95,
            "viral_score": 0.7
        }

        result = curator.curate(content_analysis)

        assert result.decision == CurationDecision.APPROVE
        assert result.confidence > 0.5
        assert len(result.matched_rules) > 0
        assert result.processing_time_ms < 5000  # <5s requirement


    def test_curate_poor_quality_content(self):
        """Test curation of poor quality content"""
        curator = AutoCurator()

        content_analysis = {
            "sentiment_score": 0.5,
            "quality_score": 0.2,  # Very low quality
            "brand_safety_score": 0.8,
            "viral_score": 0.3
        }

        result = curator.curate(content_analysis)

        assert result.decision == CurationDecision.REJECT
        assert len(result.matched_rules) > 0

    def test_curate_negative_sentiment(self):
        """Test curation of negative sentiment content"""
        curator = AutoCurator()

        content_analysis = {
            "sentiment_score": 0.1,  # Very negative
            "quality_score": 0.7,
            "brand_safety_score": 0.9,
            "viral_score": 0.5
        }

        result = curator.curate(content_analysis)

        assert result.decision == CurationDecision.REJECT

    def test_curate_ambiguous_content(self):
        """Test curation of ambiguous content"""
        curator = AutoCurator()

        content_analysis = {
            "sentiment_score": 0.5,  # Neutral
            "quality_score": 0.5,
            "brand_safety_score": 0.7,
            "viral_score": 0.5
        }

        result = curator.curate(content_analysis)

        # Should go to manual review
        assert result.decision == CurationDecision.MANUAL_REVIEW

    def test_performance_requirement(self):
        """Test that curation meets <5s performance requirement"""
        curator = AutoCurator()

        content_analysis = {
            "sentiment_score": 0.7,
            "quality_score": 0.6,
            "brand_safety_score": 0.8,
            "viral_score": 0.5
        }

        result = curator.curate(content_analysis)

        # Performance requirement: <5s per video
        assert result.processing_time_ms < 5000

    def test_evaluate_condition_min_threshold(self):
        """Test min threshold condition evaluation"""
        curator = AutoCurator()

        scores = {"sentiment_score": 0.8}

        # Pass condition
        assert curator.evaluate_condition(
            "sentiment_score",
            {"min": 0.7},
            scores
        ) is True

        # Fail condition
        assert curator.evaluate_condition(
            "sentiment_score",
            {"min": 0.9},
            scores
        ) is False

    def test_evaluate_condition_max_threshold(self):
        """Test max threshold condition evaluation"""
        curator = AutoCurator()

        scores = {"quality_score": 0.3}

        # Pass condition
        assert curator.evaluate_condition(
            "quality_score",
            {"max": 0.5},
            scores
        ) is True

        # Fail condition
        assert curator.evaluate_condition(
            "quality_score",
            {"max": 0.2},
            scores
        ) is False

    def test_get_stats(self):
        """Test getting curator statistics"""
        curator = AutoCurator()

        stats = curator.get_stats()

        assert "total_rules" in stats
        assert "enabled_rules" in stats
        assert "approve_rules" in stats
        assert "reject_rules" in stats
        assert "manual_review_rules" in stats

        assert stats["total_rules"] > 0


class TestCurationRules:
    """Test curation rule management"""

    def test_rule_priority_order(self):
        """Test that rules are evaluated in priority order"""
        curator = AutoCurator()

        # Add high priority rule
        high_priority = CurationRule(
            rule_id="high_priority",
            name="High Priority",
            description="High priority rule",
            conditions={"sentiment_score": {"min": 0.5}},
            decision=CurationDecision.APPROVE,
            priority=10
        )

        # Add low priority rule
        low_priority = CurationRule(
            rule_id="low_priority",
            name="Low Priority",
            description="Low priority rule",
            conditions={"sentiment_score": {"min": 0.5}},
            decision=CurationDecision.REJECT,
            priority=1
        )

        curator.add_rule(high_priority)
        curator.add_rule(low_priority)

        content_analysis = {
            "sentiment_score": 0.6
        }

        result = curator.curate(content_analysis)

        # High priority rule should win
        assert result.decision == CurationDecision.APPROVE
        assert "high_priority" in result.matched_rules

    def test_rule_update(self):
        """Test updating an existing rule"""
        curator = AutoCurator()

        # Add rule
        rule = CurationRule(
            rule_id="update_test",
            name="Original Name",
            description="Original",
            conditions={"sentiment_score": {"min": 0.7}},
            decision=CurationDecision.APPROVE
        )
        curator.add_rule(rule)

        # Update rule (same ID, different content)
        updated_rule = CurationRule(
            rule_id="update_test",
            name="Updated Name",
            description="Updated",
            conditions={"sentiment_score": {"min": 0.8}},
            decision=CurationDecision.REJECT,
            priority=5
        )
        curator.add_rule(updated_rule)

        # Verify update
        retrieved = curator.get_rule("update_test")
        assert retrieved.name == "Updated Name"
        assert retrieved.decision == CurationDecision.REJECT
        assert retrieved.conditions["sentiment_score"]["min"] == 0.8


class TestCurationTargets:
    """Test that curation meets acceptance criteria"""

    def test_auto_curation_rate_target(self):
        """Test that auto-curation achieves 40-60% auto-curated target"""
        curator = AutoCurator()

        # Simulate 100 content pieces with varying quality
        test_cases = []

        # 20% excellent (should auto-approve)
        for _ in range(20):
            test_cases.append({
                "sentiment_score": 0.85,
                "quality_score": 0.85,
                "brand_safety_score": 0.95
            })

        # 20% poor (should auto-reject)
        for _ in range(20):
            test_cases.append({
                "sentiment_score": 0.15,
                "quality_score": 0.2,
                "brand_safety_score": 0.6
            })

        # 60% ambiguous (should go to manual review)
        for _ in range(60):
            test_cases.append({
                "sentiment_score": 0.5,
                "quality_score": 0.5,
                "brand_safety_score": 0.7
            })

        # Curate all
        results = [curator.curate(case) for case in test_cases]

        # Count auto-curated (approved + rejected)
        auto_curated = sum(
            1 for r in results
            if r.decision in [CurationDecision.APPROVE, CurationDecision.REJECT]
        )
        manual_review = sum(
            1 for r in results
            if r.decision == CurationDecision.MANUAL_REVIEW
        )

        auto_curation_rate = auto_curated / len(results)

        # Should meet 40-60% auto-curation target
        assert 0.4 <= auto_curation_rate <= 0.6
        assert manual_review <= 60  # At most 60% manual review

    def test_performance_target(self):
        """Test that all curations meet <5s performance target"""
        curator = AutoCurator()

        # Test 10 curations
        for _ in range(10):
            content_analysis = {
                "sentiment_score": 0.7,
                "quality_score": 0.6,
                "brand_safety_score": 0.8
            }

            result = curator.curate(content_analysis)

            # Must be under 5 seconds
            assert result.processing_time_ms < 5000
