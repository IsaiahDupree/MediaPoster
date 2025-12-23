"""
Tests for Experiments Scheduler
==============================
Unit and integration tests for the experiments scheduling system.
"""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4


# =============================================================================
# MODEL TESTS
# =============================================================================

class TestExperimentModels:
    """Test experiment data models."""
    
    def test_experiment_creation(self):
        from services.experiments_scheduler.models import (
            Experiment, ExperimentStatus
        )
        
        exp = Experiment(
            name="Test Experiment",
            goal="Test if hooks improve engagement",
            description="Testing hook variations"
        )
        
        assert exp.name == "Test Experiment"
        assert exp.status == ExperimentStatus.DRAFT
        assert exp.id is not None
    
    def test_experiment_to_dict(self):
        from services.experiments_scheduler.models import Experiment
        
        exp = Experiment(
            name="Test",
            goal="Test goal"
        )
        
        data = exp.to_dict()
        
        assert data["name"] == "Test"
        assert data["goal"] == "Test goal"
        assert "id" in data
        assert "status" in data
    
    def test_hypothesis_creation(self):
        from services.experiments_scheduler.models import (
            Hypothesis, HypothesisStatus
        )
        
        hyp = Hypothesis(
            statement="Question hooks increase views",
            independent_variable="hook_type",
            dependent_variable="view_count",
            success_metric="view_count",
            success_threshold=1.2
        )
        
        assert hyp.statement == "Question hooks increase views"
        assert hyp.status == HypothesisStatus.PENDING
        assert hyp.success_threshold == 1.2
    
    def test_hypothesis_to_dict(self):
        from services.experiments_scheduler.models import Hypothesis
        
        hyp = Hypothesis(
            statement="Test hypothesis",
            success_metric="engagement_rate",
            success_threshold=1.3
        )
        
        data = hyp.to_dict()
        
        assert data["statement"] == "Test hypothesis"
        assert data["success_metric"] == "engagement_rate"
        assert data["success_threshold"] == 1.3
    
    def test_post_origin_types(self):
        from services.experiments_scheduler.models import (
            PostOrigin, OriginType
        )
        
        # Narrative origin
        origin = PostOrigin(
            origin_type=OriginType.NARRATIVE,
            narrative_goal_id="goal-123",
            pillar="Process/How-To",
            scheduled_by="ai_narrative"
        )
        
        assert origin.origin_type == OriginType.NARRATIVE
        assert origin.pillar == "Process/How-To"
        
        # Experiments origin
        exp_origin = PostOrigin(
            origin_type=OriginType.EXPERIMENTS,
            experiment_id="exp-123",
            hypothesis_id="hyp-456",
            variant="variant",
            scheduled_by="ai_experiments"
        )
        
        assert exp_origin.origin_type == OriginType.EXPERIMENTS
        assert exp_origin.variant == "variant"
    
    def test_content_pattern(self):
        from services.experiments_scheduler.models import ContentPattern
        
        pattern = ContentPattern(
            pattern_type="hook",
            category="question_hook",
            name="Question Opening Pattern",
            description="Start with an engaging question",
            success_rate=0.75,
            avg_improvement=1.35
        )
        
        assert pattern.pattern_type == "hook"
        assert pattern.success_rate == 0.75
        assert pattern.avg_improvement == 1.35
    
    def test_experiment_winner(self):
        from services.experiments_scheduler.models import (
            ExperimentWinner, WinnerType
        )
        
        winner = ExperimentWinner(
            experiment_id="exp-123",
            video_id="vid-456",
            ranking_score=0.85,
            winner_type=WinnerType.WINNER
        )
        
        assert winner.ranking_score == 0.85
        assert winner.promoted_to_narrative == False


# =============================================================================
# HYPOTHESIS ENGINE TESTS
# =============================================================================

class TestHypothesisEngine:
    """Test statistical hypothesis testing."""
    
    def test_engine_initialization(self):
        from services.experiments_scheduler.hypothesis_engine import HypothesisEngine
        
        engine = HypothesisEngine(significance_level=0.05)
        assert engine.significance_level == 0.05
    
    def test_analyze_significant_improvement(self):
        from services.experiments_scheduler.hypothesis_engine import HypothesisEngine
        
        engine = HypothesisEngine()
        
        control = [100, 110, 95, 105, 100, 98, 102, 108, 96, 104]
        variant = [150, 145, 160, 155, 148, 152, 158, 145, 162, 150]
        
        result = engine.analyze(control, variant, success_threshold=1.2)
        
        assert result.mean_variant > result.mean_control
        assert result.improvement > 1.4  # About 50% improvement
        assert result.is_significant == True
    
    def test_analyze_no_improvement(self):
        from services.experiments_scheduler.hypothesis_engine import HypothesisEngine
        
        engine = HypothesisEngine()
        
        control = [100, 102, 98, 101, 99, 100, 101, 99, 100, 101]
        variant = [101, 99, 100, 102, 98, 100, 101, 99, 100, 100]
        
        result = engine.analyze(control, variant, success_threshold=1.2)
        
        assert abs(result.improvement - 1.0) < 0.1  # Close to no change
        assert result.is_significant == False
    
    def test_determine_status_passed(self):
        from services.experiments_scheduler.hypothesis_engine import (
            HypothesisEngine, StatisticalResult
        )
        from services.experiments_scheduler.models import HypothesisStatus
        
        engine = HypothesisEngine()
        
        result = StatisticalResult(
            mean_control=100,
            mean_variant=150,
            std_control=10,
            std_variant=12,
            sample_size_control=20,
            sample_size_variant=20,
            improvement=1.5,
            t_statistic=5.0,
            p_value=0.001,
            is_significant=True,
            confidence_level=0.95
        )
        
        status, reason = engine.determine_status(result, min_sample_size=10)
        assert status == HypothesisStatus.PASSED
    
    def test_determine_status_running(self):
        from services.experiments_scheduler.hypothesis_engine import (
            HypothesisEngine, StatisticalResult
        )
        from services.experiments_scheduler.models import HypothesisStatus
        
        engine = HypothesisEngine()
        
        result = StatisticalResult(
            mean_control=100,
            mean_variant=150,
            std_control=10,
            std_variant=12,
            sample_size_control=3,
            sample_size_variant=3,
            improvement=1.5,
            t_statistic=2.0,
            p_value=0.1,
            is_significant=False,
            confidence_level=0.6
        )
        
        status, reason = engine.determine_status(result, min_sample_size=10)
        assert status == HypothesisStatus.RUNNING
        assert "Need more data" in reason
    
    def test_calculate_sample_size(self):
        from services.experiments_scheduler.hypothesis_engine import HypothesisEngine
        
        engine = HypothesisEngine()
        
        size = engine.calculate_required_sample_size(expected_effect_size=0.2)
        assert size >= 10  # Should be reasonable sample size


# =============================================================================
# EXPERIMENT AGENT TESTS
# =============================================================================

class TestExperimentAgent:
    """Test experiment agent capabilities."""
    
    def test_agent_initialization(self):
        from services.experiments_scheduler.experiment_agent import ExperimentAgent
        
        agent = ExperimentAgent()
        assert agent is not None
    
    def test_get_available_actions(self):
        from services.experiments_scheduler.experiment_agent import ExperimentAgent
        
        agent = ExperimentAgent()
        actions = agent.get_available_actions()
        
        assert len(actions) >= 20
        assert any(a["action"] == "browse_ugc_library" for a in actions)
        assert any(a["action"] == "schedule_post" for a in actions)
        assert any(a["action"] == "add_subtitles" for a in actions)
    
    def test_action_categories(self):
        from services.experiments_scheduler.experiment_agent import ExperimentAgent
        
        agent = ExperimentAgent()
        actions = agent.get_available_actions()
        
        categories = set(a["category"] for a in actions)
        
        assert "discovery" in categories
        assert "analysis" in categories
        assert "editing" in categories
        assert "scheduling" in categories
        assert "experiment" in categories
    
    @pytest.mark.asyncio
    async def test_generate_basic_hypotheses(self):
        from services.experiments_scheduler.experiment_agent import ExperimentAgent
        
        agent = ExperimentAgent(openai_api_key=None)  # Force basic generation
        
        hypotheses = agent._generate_basic_hypotheses("Test goal")
        
        assert len(hypotheses) >= 2
        assert all(h.statement for h in hypotheses)
        assert all(h.success_metric for h in hypotheses)
    
    @pytest.mark.asyncio
    async def test_select_content_for_experiment(self):
        from services.experiments_scheduler.experiment_agent import ExperimentAgent
        from services.experiments_scheduler.models import Hypothesis
        
        agent = ExperimentAgent()
        
        hypothesis = Hypothesis(
            statement="Test hypothesis",
            independent_variable="hook_type"
        )
        
        content_pool = [
            {"id": f"vid-{i}", "score": 80 - i} for i in range(10)
        ]
        
        control, variant = await agent.select_content_for_experiment(
            hypothesis, content_pool
        )
        
        assert len(control) > 0
        assert len(variant) > 0
        assert set(control).isdisjoint(set(variant))  # No overlap


# =============================================================================
# PATTERN LEARNER TESTS
# =============================================================================

class TestPatternLearner:
    """Test content pattern learning."""
    
    def test_learner_initialization(self):
        from services.experiments_scheduler.pattern_learner import PatternLearner
        
        learner = PatternLearner()
        assert learner is not None
    
    def test_classify_pattern_type(self):
        from services.experiments_scheduler.pattern_learner import PatternLearner
        
        learner = PatternLearner()
        
        assert learner._classify_pattern_type("hook_type") == "hook"
        assert learner._classify_pattern_type("opening_style") == "hook"
        assert learner._classify_pattern_type("video_format") == "format"
        assert learner._classify_pattern_type("posting_time") == "timing"
        assert learner._classify_pattern_type("caption_length") == "caption"
        assert learner._classify_pattern_type("music_genre") == "audio"
        assert learner._classify_pattern_type("subtitle_overlay") == "subtitle"
        assert learner._classify_pattern_type("unknown_var") == "general"
    
    def test_generate_pattern_name(self):
        from services.experiments_scheduler.pattern_learner import PatternLearner
        
        learner = PatternLearner()
        
        name = learner._generate_pattern_name(
            "Videos with question hooks get 40% more views than statement hooks"
        )
        
        assert "Videos with question hooks" in name
        assert len(name) < 50


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestExperimentsIntegration:
    """Integration tests for experiments system."""
    
    @pytest.mark.asyncio
    async def test_full_experiment_workflow(self):
        from services.experiments_scheduler import (
            ExperimentAgent,
            ExperimentsScheduler,
            HypothesisEngine
        )
        
        # 1. Create agent and plan experiment
        agent = ExperimentAgent(openai_api_key=None)
        
        resources = {
            "types": ["ugc"],
            "video_count": 100,
            "tools": ["subtitles"]
        }
        
        experiment = await agent.plan_experiment(
            goal="Test if subtitles improve watch time",
            available_resources=resources
        )
        
        assert experiment.name is not None
        assert len(experiment.hypotheses) >= 1
        
        # 2. Verify hypothesis structure
        for hyp in experiment.hypotheses:
            assert hyp.statement != ""
            assert hyp.success_metric is not None  # Various metrics possible
        
        # 3. Test hypothesis engine
        engine = HypothesisEngine()
        
        control_metrics = [50, 55, 48, 52, 51]
        variant_metrics = [70, 75, 68, 72, 71]
        
        result = engine.analyze(control_metrics, variant_metrics)
        
        assert result.improvement > 1.3  # Significant improvement


class TestExperimentsAPIEndpoints:
    """Test API endpoint functionality."""
    
    def test_agent_actions_structure(self):
        from services.experiments_scheduler import ExperimentAgent
        
        agent = ExperimentAgent()
        actions = agent.get_available_actions()
        
        # Verify structure
        for action in actions:
            assert "action" in action
            assert "category" in action
            assert isinstance(action["action"], str)
            assert isinstance(action["category"], str)
