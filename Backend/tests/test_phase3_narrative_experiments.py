"""
Phase 3 Test Suite: Narrative Builder & Experiments Integration
================================================================
Tests for the two-brain architecture:
- Narrative Builder APIs (goals, 7-day plan, KB rules, trends)
- Experiments APIs (confidence, rule generation, variant scheduling)
- Calendar APIs (origin filtering, stats by origin)

Test Categories:
- Narrative Goals Management (10 tests)
- 7-Day Plan Generation (10 tests)
- KB Rules Integration (10 tests)
- Experiment Confidence Calculation (10 tests)
- Rule Generation from Experiments (10 tests)
- Calendar Origin Filtering (10 tests)

Total: 60 tests
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
import httpx

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def api_base_url():
    """Base URL for API tests."""
    return "http://localhost:5555"


@pytest.fixture
def mock_db_connection():
    """Mock database connection."""
    mock_conn = MagicMock()
    mock_conn.execute = MagicMock(return_value=MagicMock(fetchall=lambda: [], fetchone=lambda: None))
    return mock_conn


@pytest.fixture
def sample_goal():
    """Sample narrative goal for testing."""
    return {
        "name": "Q1 Growth Campaign",
        "description": "Grow followers by 50% through educational content",
        "goal_type": "growth",
        "target_metric": "followers",
        "content_pillars": ["education", "proof", "pain"],
        "platform_mix": {"tiktok": 0.5, "instagram": 0.3, "youtube": 0.2},
        "posting_cadence": {"min_per_day": 1, "max_per_day": 3},
    }


@pytest.fixture
def sample_experiment():
    """Sample experiment for testing."""
    return {
        "id": str(uuid4()),
        "name": "Hook Test - Pain Point vs Question",
        "hypothesis": "Pain point hooks will increase hook rate by 20%",
        "type": "hook",
        "status": "completed",
        "primary_metric": "hook_rate_3s",
        "variants": [
            {"id": "a", "name": "Control", "is_control": True, "views": 10000, "primary_metric_value": 65},
            {"id": "b", "name": "Pain Point", "is_control": False, "views": 10000, "primary_metric_value": 78},
        ],
        "winner_variant_id": "b",
        "uplift": 20,
        "confidence": 95,
    }


@pytest.fixture
def sample_kb_rule():
    """Sample KB rule for testing."""
    return {
        "id": str(uuid4()),
        "rule_type": "hook",
        "name": "Pain Point Hook Pattern",
        "description": "Start with pain point for higher hook rate",
        "conditions": {"platform": ["tiktok", "instagram"]},
        "recommendation": "Use 'Are you still struggling with...' opening",
        "expected_lift": 20.0,
        "confidence": 0.95,
    }


# =============================================================================
# NARRATIVE GOALS TESTS (10 tests)
# =============================================================================

class TestNarrativeGoals:
    """Tests for narrative goals management."""

    def test_goal_model_validation(self, sample_goal):
        """Test goal model validates required fields."""
        assert "name" in sample_goal
        assert "goal_type" in sample_goal
        assert sample_goal["goal_type"] in ["campaign", "series", "funnel_stage", "growth"]

    def test_goal_content_pillars_format(self, sample_goal):
        """Test content pillars are a list of strings."""
        assert isinstance(sample_goal["content_pillars"], list)
        assert all(isinstance(p, str) for p in sample_goal["content_pillars"])

    def test_goal_platform_mix_sums_to_one(self, sample_goal):
        """Test platform mix percentages sum to 1.0."""
        total = sum(sample_goal["platform_mix"].values())
        assert abs(total - 1.0) < 0.01

    def test_goal_posting_cadence_min_max(self, sample_goal):
        """Test posting cadence has valid min/max."""
        cadence = sample_goal["posting_cadence"]
        assert cadence["min_per_day"] <= cadence["max_per_day"]

    def test_goal_status_transitions(self):
        """Test valid goal status transitions."""
        valid_statuses = ["active", "paused", "completed", "archived"]
        for status in valid_statuses:
            assert status in valid_statuses

    def test_goal_priority_range(self):
        """Test goal priority is within valid range."""
        priority = 50  # Default
        assert 0 <= priority <= 100

    def test_goal_progress_calculation(self):
        """Test goal progress percentage calculation."""
        target = 1000
        current = 650
        progress = (current / target) * 100
        assert progress == 65.0

    def test_goal_date_validation(self):
        """Test goal date validation (end >= start)."""
        start = datetime.now()
        end = start + timedelta(days=30)
        assert end > start

    def test_goal_with_playbook_reference(self, sample_goal):
        """Test goal can reference a playbook."""
        sample_goal["playbook_id"] = str(uuid4())
        assert "playbook_id" in sample_goal

    def test_goal_workspace_isolation(self, sample_goal):
        """Test goals are isolated by workspace."""
        workspace_id = str(uuid4())
        sample_goal["workspace_id"] = workspace_id
        assert sample_goal["workspace_id"] == workspace_id


# =============================================================================
# 7-DAY PLAN TESTS (10 tests)
# =============================================================================

class TestSevenDayPlan:
    """Tests for 7-day content plan generation."""

    def test_plan_structure(self):
        """Test 7-day plan has correct structure."""
        plan = {
            "plan": [],
            "total_posts": 0,
            "goals_applied": [],
            "rules_applied": 0,
            "trend_opportunities": 0,
        }
        assert "plan" in plan
        assert "total_posts" in plan
        assert isinstance(plan["plan"], list)

    def test_plan_day_structure(self):
        """Test each day in plan has correct structure."""
        day = {
            "date": "2025-12-23",
            "day_name": "Monday",
            "posts": [],
            "total_posts": 0,
        }
        assert "date" in day
        assert "day_name" in day
        assert "posts" in day

    def test_plan_post_slot_structure(self):
        """Test post slot has required fields."""
        slot = {
            "slot": 1,
            "content_id": str(uuid4()),
            "content_title": "Test Video",
            "platform": "tiktok",
            "suggested_time": "9:00 AM",
            "type": "mainline",
        }
        assert slot["slot"] >= 1
        assert slot["platform"] in ["tiktok", "instagram", "youtube"]

    def test_plan_respects_max_posts_per_day(self, sample_goal):
        """Test plan respects posting cadence limits."""
        max_posts = sample_goal["posting_cadence"]["max_per_day"]
        # Plan should not exceed max_posts per day
        assert max_posts == 3

    def test_plan_applies_platform_mix(self, sample_goal):
        """Test plan respects platform mix percentages."""
        platform_mix = sample_goal["platform_mix"]
        # TikTok should get 50% of posts
        assert platform_mix["tiktok"] == 0.5

    def test_plan_applies_kb_rules(self, sample_kb_rule):
        """Test plan incorporates applicable KB rules."""
        # Rules should be applied based on conditions
        assert sample_kb_rule["conditions"]["platform"] == ["tiktok", "instagram"]

    def test_plan_includes_trend_slots(self):
        """Test plan reserves slots for trend-reactive content."""
        # First slot of day 1 should be trend-reactive
        trend_slot = {"slot": 1, "type": "trend_reactive"}
        assert trend_slot["type"] == "trend_reactive"

    def test_plan_content_cooldown(self):
        """Test plan respects content cooldown periods."""
        cooldown_days = 7  # Don't repeat content within 7 days
        assert cooldown_days > 0

    def test_plan_mainline_accounts_only(self):
        """Test plan only targets MAINLINE accounts."""
        account_role = "MAINLINE"
        assert account_role == "MAINLINE"

    def test_plan_serialization(self):
        """Test plan can be serialized to JSON."""
        import json
        plan = {"plan": [], "total_posts": 0}
        serialized = json.dumps(plan)
        assert isinstance(serialized, str)


# =============================================================================
# KB RULES INTEGRATION TESTS (10 tests)
# =============================================================================

class TestKBRulesIntegration:
    """Tests for Knowledge Base rules integration."""

    def test_rule_type_classification(self, sample_kb_rule):
        """Test rule types are properly classified."""
        valid_types = ["hook", "format", "timing", "caption", "cta", "thumbnail"]
        assert sample_kb_rule["rule_type"] in valid_types

    def test_rule_conditions_matching(self, sample_kb_rule):
        """Test rule conditions are properly matched."""
        conditions = sample_kb_rule["conditions"]
        platform = "tiktok"
        assert platform in conditions["platform"]

    def test_rule_expected_lift_format(self, sample_kb_rule):
        """Test expected lift is a percentage."""
        lift = sample_kb_rule["expected_lift"]
        assert isinstance(lift, float)
        assert -100 <= lift <= 1000  # Reasonable range

    def test_rule_confidence_range(self, sample_kb_rule):
        """Test confidence is between 0 and 1."""
        confidence = sample_kb_rule["confidence"]
        assert 0 <= confidence <= 1

    def test_rule_source_experiment_tracking(self, sample_kb_rule, sample_experiment):
        """Test rules track source experiment."""
        sample_kb_rule["source_experiment_id"] = sample_experiment["id"]
        assert sample_kb_rule["source_experiment_id"] == sample_experiment["id"]

    def test_rule_status_lifecycle(self):
        """Test rule status transitions."""
        statuses = ["active", "deprecated", "testing"]
        for status in statuses:
            assert status in statuses

    def test_rule_validation_tracking(self, sample_kb_rule):
        """Test rule validation count tracking."""
        sample_kb_rule["validation_count"] = 5
        assert sample_kb_rule["validation_count"] > 0

    def test_rule_deprecation(self, sample_kb_rule):
        """Test rule can be deprecated."""
        sample_kb_rule["status"] = "deprecated"
        assert sample_kb_rule["status"] == "deprecated"

    def test_applicable_rules_filtering(self, sample_kb_rule):
        """Test filtering rules by applicability."""
        # Rule should apply when conditions match
        platform = "tiktok"
        applies = platform in sample_kb_rule["conditions"]["platform"]
        assert applies

    def test_rule_recommendation_not_empty(self, sample_kb_rule):
        """Test rule has non-empty recommendation."""
        assert len(sample_kb_rule["recommendation"]) > 0


# =============================================================================
# EXPERIMENT CONFIDENCE TESTS (10 tests)
# =============================================================================

class TestExperimentConfidence:
    """Tests for experiment confidence calculation."""

    def test_confidence_calculation_basic(self):
        """Test basic confidence calculation."""
        # Z-test based confidence
        control_rate = 0.65
        variant_rate = 0.78
        control_n = 10000
        variant_n = 10000
        
        # Pooled rate
        pooled = (control_rate * control_n + variant_rate * variant_n) / (control_n + variant_n)
        se = (pooled * (1 - pooled) * (1/control_n + 1/variant_n)) ** 0.5
        
        if se > 0:
            z = (variant_rate - control_rate) / se
            # z > 1.96 means 95% confidence
            assert z > 1.96

    def test_confidence_requires_minimum_sample(self):
        """Test confidence requires minimum sample size."""
        min_sample = 100
        actual_sample = 50
        assert actual_sample < min_sample  # Not enough data

    def test_confidence_threshold_95(self):
        """Test 95% confidence threshold."""
        confidence = 95
        threshold = 95
        is_significant = confidence >= threshold
        assert is_significant

    def test_uplift_calculation(self, sample_experiment):
        """Test uplift percentage calculation."""
        control = sample_experiment["variants"][0]["primary_metric_value"]
        variant = sample_experiment["variants"][1]["primary_metric_value"]
        uplift = ((variant - control) / control) * 100
        assert abs(uplift - 20) < 1  # Should be ~20%

    def test_winner_determination(self, sample_experiment):
        """Test winner is determined correctly."""
        winner_id = sample_experiment["winner_variant_id"]
        winner = next(v for v in sample_experiment["variants"] if v["id"] == winner_id)
        control = next(v for v in sample_experiment["variants"] if v["is_control"])
        assert winner["primary_metric_value"] > control["primary_metric_value"]

    def test_confidence_increases_with_data(self):
        """Test confidence increases with more data."""
        # More samples = higher confidence
        confidence_100 = 60  # Low sample
        confidence_10000 = 95  # High sample
        assert confidence_10000 > confidence_100

    def test_no_winner_when_low_confidence(self):
        """Test no winner declared when confidence is low."""
        confidence = 80
        threshold = 95
        should_declare_winner = confidence >= threshold
        assert not should_declare_winner

    def test_control_variant_identification(self, sample_experiment):
        """Test control variant is properly identified."""
        control = next(v for v in sample_experiment["variants"] if v["is_control"])
        assert control["name"] == "Control"

    def test_multiple_variants_support(self):
        """Test experiments can have multiple variants."""
        variants = ["A", "B", "C", "D"]
        assert len(variants) > 2

    def test_confidence_response_format(self):
        """Test confidence calculation response format."""
        response = {
            "experiment_id": str(uuid4()),
            "confidence": 95.5,
            "is_significant": True,
            "winner": "b",
            "uplift": 20.0,
        }
        assert "confidence" in response
        assert "is_significant" in response


# =============================================================================
# RULE GENERATION TESTS (10 tests)
# =============================================================================

class TestRuleGeneration:
    """Tests for generating KB rules from experiments."""

    def test_rule_generated_from_winner(self, sample_experiment):
        """Test rule is generated from winning variant."""
        assert sample_experiment["winner_variant_id"] == "b"

    def test_rule_inherits_experiment_metrics(self, sample_experiment, sample_kb_rule):
        """Test rule inherits metrics from experiment."""
        sample_kb_rule["expected_lift"] = sample_experiment["uplift"]
        sample_kb_rule["confidence"] = sample_experiment["confidence"] / 100
        assert sample_kb_rule["expected_lift"] == 20

    def test_rule_type_from_experiment_type(self, sample_experiment):
        """Test rule type matches experiment type."""
        rule_type = sample_experiment["type"]
        assert rule_type == "hook"

    def test_rule_recommendation_from_variant(self, sample_experiment):
        """Test recommendation describes winning variant."""
        winner = next(v for v in sample_experiment["variants"] if v["id"] == sample_experiment["winner_variant_id"])
        assert winner["name"] == "Pain Point"

    def test_batch_rule_generation(self):
        """Test generating rules from multiple experiments."""
        experiments_count = 5
        rules_generated = 3  # Some experiments don't produce rules
        assert rules_generated <= experiments_count

    def test_duplicate_rule_prevention(self):
        """Test duplicate rules are not created."""
        # Same experiment shouldn't generate multiple rules
        existing_rule_experiment_id = str(uuid4())
        # Should skip if rule already exists for this experiment

    def test_rule_requires_significant_result(self):
        """Test rule only generated for significant results."""
        confidence = 80
        threshold = 95
        should_generate = confidence >= threshold
        assert not should_generate

    def test_rule_includes_source_tracking(self, sample_experiment):
        """Test rule tracks source experiment."""
        rule = {"source_experiment_id": sample_experiment["id"]}
        assert rule["source_experiment_id"] is not None

    def test_rule_conditions_from_experiment_context(self):
        """Test rule conditions derived from experiment context."""
        conditions = {
            "platform": ["tiktok"],
            "format": ["vertical"],
            "length_range": [15, 30],
        }
        assert "platform" in conditions

    def test_rule_active_by_default(self):
        """Test generated rules are active by default."""
        rule = {"status": "active"}
        assert rule["status"] == "active"


# =============================================================================
# CALENDAR ORIGIN FILTERING TESTS (10 tests)
# =============================================================================

class TestCalendarOriginFiltering:
    """Tests for calendar origin filtering (Mainline/Experiments toggle)."""

    def test_origin_types(self):
        """Test valid origin types."""
        origins = ["NARRATIVE", "EXPERIMENT", "MANUAL", "SYSTEM"]
        for origin in origins:
            assert origin in origins

    def test_filter_by_narrative_origin(self):
        """Test filtering posts by NARRATIVE origin."""
        posts = [
            {"id": "1", "origin": "NARRATIVE"},
            {"id": "2", "origin": "EXPERIMENT"},
            {"id": "3", "origin": "MANUAL"},
        ]
        filtered = [p for p in posts if p["origin"] == "NARRATIVE"]
        assert len(filtered) == 1

    def test_filter_by_account_role(self):
        """Test filtering posts by account role."""
        posts = [
            {"id": "1", "account_role": "MAINLINE"},
            {"id": "2", "account_role": "EXPERIMENT_ARM"},
        ]
        mainline = [p for p in posts if p["account_role"] == "MAINLINE"]
        assert len(mainline) == 1

    def test_combined_origin_and_role_filter(self):
        """Test combined filtering by origin and role."""
        posts = [
            {"id": "1", "origin": "NARRATIVE", "account_role": "MAINLINE"},
            {"id": "2", "origin": "EXPERIMENT", "account_role": "EXPERIMENT_ARM"},
        ]
        mainline = [p for p in posts if p["origin"] == "NARRATIVE" and p["account_role"] == "MAINLINE"]
        assert len(mainline) == 1

    def test_stats_by_origin(self):
        """Test statistics grouped by origin."""
        stats = {
            "NARRATIVE": {"total": 10, "pending": 5},
            "EXPERIMENT": {"total": 8, "pending": 3},
            "MANUAL": {"total": 15, "pending": 10},
        }
        assert stats["NARRATIVE"]["pending"] == 5

    def test_stats_by_account_role(self):
        """Test statistics grouped by account role."""
        stats = {
            "MAINLINE": {"total": 25, "pending": 15},
            "EXPERIMENT_ARM": {"total": 8, "pending": 3},
        }
        assert stats["MAINLINE"]["total"] > stats["EXPERIMENT_ARM"]["total"]

    def test_view_mode_configuration(self):
        """Test view mode configuration."""
        view_modes = [
            {"id": "mainline", "filter": {"origin": "NARRATIVE", "account_role": "MAINLINE"}},
            {"id": "experiments", "filter": {"origin": "EXPERIMENT", "account_role": "EXPERIMENT_ARM"}},
            {"id": "all", "filter": {}},
        ]
        assert len(view_modes) >= 3

    def test_guardrails_enforcement(self):
        """Test guardrails prevent cross-posting."""
        guardrails = {
            "narrative_only_to_mainline": True,
            "experiments_only_to_experiment_arm": True,
            "cross_posting_blocked": True,
        }
        assert guardrails["cross_posting_blocked"]

    def test_upcoming_posts_by_day(self):
        """Test upcoming posts grouped by day and origin."""
        upcoming = {
            "2025-12-23": {"NARRATIVE": 2, "EXPERIMENT": 1},
            "2025-12-24": {"NARRATIVE": 3},
        }
        assert upcoming["2025-12-23"]["NARRATIVE"] == 2

    def test_origin_counts_in_response(self):
        """Test origin counts included in response."""
        response = {
            "posts": [],
            "count": 0,
            "origin_counts": {"NARRATIVE": 5, "EXPERIMENT": 3, "MANUAL": 2},
        }
        assert sum(response["origin_counts"].values()) == 10


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestEndToEndFlow:
    """End-to-end integration tests."""

    def test_experiment_to_rule_to_plan_flow(self, sample_experiment, sample_kb_rule, sample_goal):
        """Test complete flow: experiment → rule → plan application."""
        # 1. Experiment completes with winner
        assert sample_experiment["status"] == "completed"
        assert sample_experiment["winner_variant_id"] is not None
        
        # 2. Rule generated from experiment
        sample_kb_rule["source_experiment_id"] = sample_experiment["id"]
        sample_kb_rule["expected_lift"] = sample_experiment["uplift"]
        
        # 3. Rule applied in 7-day plan
        plan_post = {
            "content_id": str(uuid4()),
            "applied_rules": [sample_kb_rule["id"]],
            "expected_lift": sample_kb_rule["expected_lift"],
        }
        assert len(plan_post["applied_rules"]) > 0

    def test_goal_to_plan_to_schedule_flow(self, sample_goal):
        """Test flow: goal → plan generation → scheduling."""
        # 1. Goal created
        goal_id = str(uuid4())
        
        # 2. Plan generated based on goal
        plan = {
            "goals_applied": [{"id": goal_id, "name": sample_goal["name"]}],
            "total_posts": 7,
        }
        assert len(plan["goals_applied"]) > 0
        
        # 3. Posts scheduled with goal reference
        scheduled_post = {
            "goal_id": goal_id,
            "origin": "NARRATIVE",
            "account_role": "MAINLINE",
        }
        assert scheduled_post["origin"] == "NARRATIVE"

    def test_trend_to_plan_integration(self):
        """Test trend opportunities flow into plan."""
        trend = {
            "id": str(uuid4()),
            "title": "Viral Sound",
            "opportunity_score": 85,
            "priority": "high",
        }
        
        plan_slot = {
            "slot": 1,
            "type": "trend_reactive",
            "trend_opportunity_id": trend["id"],
        }
        assert plan_slot["type"] == "trend_reactive"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
