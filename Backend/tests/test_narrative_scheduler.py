"""
Narrative Scheduler API Tests
==============================
Comprehensive test suite for the AI Narrative Scheduling System.

Run tests:
    pytest tests/test_narrative_scheduler.py -v
"""

import asyncio
import pytest
import sys
from pathlib import Path
from uuid import uuid4
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_goal():
    """Sample narrative goal for testing."""
    from services.narrative_scheduler.models import NarrativeGoal
    return NarrativeGoal(
        goal_statement="Position myself as the go-to expert for DIY electronics",
        primary_cta="waitlist",
        target_audience="Beginner makers aged 25-45",
        time_horizon="next_7_days",
        target_followers=500,
        target_engagement_rate=5.0
    )


@pytest.fixture
def sample_pillars():
    """Sample pillars for testing."""
    from services.narrative_scheduler.models import NarrativePillar
    return [
        NarrativePillar(
            name="Process/How-To",
            pillar_type="value",
            target_percentage=30.0,
            keywords=["how to", "tutorial", "guide"]
        ),
        NarrativePillar(
            name="Pain Points",
            pillar_type="value",
            target_percentage=25.0,
            keywords=["problem", "struggle", "challenge"]
        ),
        NarrativePillar(
            name="Social Proof",
            pillar_type="proof",
            target_percentage=20.0,
            keywords=["results", "success", "testimonial"]
        ),
    ]


@pytest.fixture
def sample_constraints():
    """Sample constraints for testing."""
    from services.narrative_scheduler.models import SchedulingConstraints
    return SchedulingConstraints(
        enabled_platforms=["tiktok", "instagram"],
        max_posts_per_day=3,
        min_posts_per_day=2,
        min_pre_social_score=60
    )


# =============================================================================
# MODEL TESTS
# =============================================================================

class TestNarrativeGoal:
    """Test NarrativeGoal model."""
    
    def test_goal_creation(self, sample_goal):
        """Test goal creation with default values."""
        assert sample_goal.goal_statement != ""
        assert sample_goal.primary_cta == "waitlist"
        assert sample_goal.time_horizon == "next_7_days"
    
    def test_goal_to_dict(self, sample_goal):
        """Test goal serialization."""
        data = sample_goal.to_dict()
        assert "id" in data
        assert data["goal_statement"] == sample_goal.goal_statement
        assert data["primary_cta"] == "waitlist"


class TestNarrativePillar:
    """Test NarrativePillar model."""
    
    def test_pillar_creation(self):
        """Test pillar creation."""
        from services.narrative_scheduler.models import NarrativePillar
        
        pillar = NarrativePillar(
            name="Test Pillar",
            pillar_type="value",
            target_percentage=25.0
        )
        
        assert pillar.name == "Test Pillar"
        assert pillar.pillar_type == "value"
        assert pillar.is_active == True
    
    def test_pillar_to_dict(self, sample_pillars):
        """Test pillar serialization."""
        pillar = sample_pillars[0]
        data = pillar.to_dict()
        
        assert data["name"] == "Process/How-To"
        assert data["target_percentage"] == 30.0
        assert "keywords" in data


class TestSchedulingConstraints:
    """Test SchedulingConstraints model."""
    
    def test_constraints_defaults(self):
        """Test default constraint values."""
        from services.narrative_scheduler.models import SchedulingConstraints
        
        constraints = SchedulingConstraints()
        
        assert "tiktok" in constraints.enabled_platforms
        assert constraints.max_posts_per_day == 3
        assert constraints.min_pre_social_score == 60
    
    def test_constraints_custom(self, sample_constraints):
        """Test custom constraints."""
        assert sample_constraints.max_posts_per_day == 3
        assert sample_constraints.min_posts_per_day == 2


# =============================================================================
# REASONING ENGINE TESTS
# =============================================================================

class TestNarrativeReasoningEngine:
    """Test NarrativeReasoningEngine."""
    
    def test_engine_initialization(self):
        """Test engine creation."""
        from services.narrative_scheduler.reasoning_engine import NarrativeReasoningEngine
        
        engine = NarrativeReasoningEngine()
        assert engine.reasoning_chain == []
        assert engine.step_counter == 0
    
    def test_add_reasoning_step(self):
        """Test adding reasoning steps."""
        from services.narrative_scheduler.reasoning_engine import NarrativeReasoningEngine
        
        engine = NarrativeReasoningEngine()
        step = engine._add_reasoning_step(
            thought="Test thought",
            decision="Test decision",
            confidence=0.9
        )
        
        assert step.step_number == 1
        assert step.thought == "Test thought"
        assert step.decision == "Test decision"
        assert len(engine.reasoning_chain) == 1
    
    @pytest.mark.asyncio
    async def test_generate_weekly_plan(self, sample_goal, sample_pillars, sample_constraints):
        """Test plan generation."""
        from services.narrative_scheduler.reasoning_engine import NarrativeReasoningEngine
        from services.narrative_scheduler.models import VideoCandidate
        
        engine = NarrativeReasoningEngine()
        
        # Create sample videos
        videos = [
            VideoCandidate(
                id=str(uuid4()),
                title=f"Test Video {i}",
                file_path=f"/path/to/video{i}.mp4",
                pre_social_score=80 + i,
                topics=["tutorial", "how to"]
            )
            for i in range(10)
        ]
        
        plan = await engine.generate_weekly_plan(
            goal=sample_goal,
            pillars=sample_pillars,
            constraints=sample_constraints,
            available_videos=videos
        )
        
        assert plan is not None
        assert plan.total_posts > 0
        assert len(plan.reasoning_chain) > 0
        assert plan.status == "draft"


# =============================================================================
# SCHEDULER TESTS
# =============================================================================

class TestNarrativeScheduler:
    """Test NarrativeScheduler service."""
    
    def test_scheduler_initialization(self):
        """Test scheduler creation."""
        from services.narrative_scheduler.scheduler import NarrativeScheduler
        
        scheduler = NarrativeScheduler()
        assert scheduler.engine is not None
        assert scheduler.reasoning_engine is not None
    
    def test_default_goal(self):
        """Test default goal generation."""
        from services.narrative_scheduler.scheduler import NarrativeScheduler
        
        scheduler = NarrativeScheduler()
        goal = scheduler._get_default_goal()
        
        assert goal.goal_statement != ""
        assert goal.primary_cta == "follow"
    
    def test_default_pillars(self):
        """Test default pillars generation."""
        from services.narrative_scheduler.scheduler import NarrativeScheduler
        
        scheduler = NarrativeScheduler()
        pillars = scheduler._get_default_pillars()
        
        assert len(pillars) >= 3
        assert any(p.name == "Process/How-To" for p in pillars)
    
    def test_default_constraints(self):
        """Test default constraints generation."""
        from services.narrative_scheduler.scheduler import NarrativeScheduler
        
        scheduler = NarrativeScheduler()
        constraints = scheduler._get_default_constraints()
        
        assert "tiktok" in constraints.enabled_platforms
        assert constraints.max_posts_per_day == 3


# =============================================================================
# AI CLASSIFIER TESTS
# =============================================================================

class TestAIContentClassifier:
    """Test AIContentClassifier."""
    
    def test_classifier_initialization(self):
        """Test classifier creation."""
        from services.narrative_scheduler.ai_classifier import AIContentClassifier
        
        classifier = AIContentClassifier()
        assert classifier.model == "gpt-4o-mini"
    
    def test_keyword_classification(self):
        """Test keyword-based classification fallback."""
        from services.narrative_scheduler.ai_classifier import AIContentClassifier
        
        classifier = AIContentClassifier(api_key=None)  # Force fallback
        
        result = classifier._keyword_classify(
            title="How to build a DIY electronics project step by step",
            transcript="Today I'll show you how to create this amazing project...",
            topics=["tutorial", "DIY"],
            pillars=None
        )
        
        assert result.primary_pillar == "Process/How-To"
        assert result.confidence > 0
    
    def test_format_pillars(self):
        """Test pillar formatting for prompts."""
        from services.narrative_scheduler.ai_classifier import AIContentClassifier
        
        classifier = AIContentClassifier()
        
        pillars = [
            {"name": "Test Pillar", "pillar_type": "value", "description": "Test", "keywords": ["test"]}
        ]
        
        formatted = classifier._format_pillars(pillars)
        assert "Test Pillar" in formatted
        assert "value" in formatted


# =============================================================================
# CONTENT ORCHESTRATION TESTS
# =============================================================================

class TestContentOrchestration:
    """Test NarrativeContentOrchestrator."""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator creation."""
        from services.narrative_scheduler.content_orchestration import NarrativeContentOrchestrator
        
        orchestrator = NarrativeContentOrchestrator()
        assert orchestrator is not None
    
    @pytest.mark.asyncio
    async def test_generate_brief(self, sample_goal, sample_pillars):
        """Test brief generation."""
        from services.narrative_scheduler.content_orchestration import NarrativeContentOrchestrator
        
        orchestrator = NarrativeContentOrchestrator()
        
        briefs = await orchestrator.generate_content_briefs_from_goal(
            goal=sample_goal,
            pillars=sample_pillars,
            count=3
        )
        
        assert len(briefs) == 3
        assert all(b.topic != "" for b in briefs)
        assert all(b.hook != "" for b in briefs)
    
    def test_get_cta_for_goal(self):
        """Test CTA generation."""
        from services.narrative_scheduler.content_orchestration import NarrativeContentOrchestrator
        
        orchestrator = NarrativeContentOrchestrator()
        
        cta = orchestrator._get_cta_for_goal("waitlist")
        assert "waitlist" in cta.lower() or "link" in cta.lower()
        
        cta = orchestrator._get_cta_for_goal("follow")
        assert "follow" in cta.lower()
    
    def test_generate_basic_script(self, sample_goal, sample_pillars):
        """Test basic script generation without AI."""
        from services.narrative_scheduler.content_orchestration import (
            NarrativeContentOrchestrator,
            ContentBriefFromNarrative
        )
        
        orchestrator = NarrativeContentOrchestrator(openai_api_key=None)
        
        brief = ContentBriefFromNarrative(
            topic="Test topic",
            hook="Check this out!",
            key_points=["Point 1", "Point 2"],
            call_to_action="Follow for more!"
        )
        
        script = orchestrator._generate_basic_script(brief)
        
        assert "Check this out!" in script
        assert "Follow for more!" in script


# =============================================================================
# WEEKLY AUTOMATION TESTS
# =============================================================================

class TestWeeklyAutomation:
    """Test WeeklyAutomation."""
    
    def test_automation_initialization(self):
        """Test automation creation."""
        from services.narrative_scheduler.weekly_automation import WeeklyAutomation
        
        automation = WeeklyAutomation()
        assert automation.config.reflection_day == 6  # Sunday
        assert automation.config.apply_learnings == True
    
    def test_automation_config(self):
        """Test custom configuration."""
        from services.narrative_scheduler.weekly_automation import (
            WeeklyAutomation,
            AutomationConfig
        )
        
        config = AutomationConfig(
            reflection_day=5,  # Saturday
            auto_approve_plans=True
        )
        
        automation = WeeklyAutomation(config=config)
        assert automation.config.reflection_day == 5
        assert automation.config.auto_approve_plans == True
    
    def test_should_run_checks(self):
        """Test schedule checking logic."""
        from services.narrative_scheduler.weekly_automation import WeeklyAutomation
        
        automation = WeeklyAutomation()
        
        # These will return False unless it's exactly the right day/hour
        # Just verify they don't raise exceptions
        result = automation.should_run_reflection()
        assert isinstance(result, bool)
        
        result = automation.should_run_plan_generation()
        assert isinstance(result, bool)


# =============================================================================
# REFLECTION SYSTEM TESTS
# =============================================================================

class TestReflectionSystem:
    """Test ReflectionSystem."""
    
    def test_reflection_initialization(self):
        """Test reflection system creation."""
        from services.narrative_scheduler.reflection_system import ReflectionSystem
        
        system = ReflectionSystem()
        assert system.engine is not None
    
    @pytest.mark.asyncio
    async def test_get_learnings(self):
        """Test getting accumulated learnings."""
        from services.narrative_scheduler.reflection_system import ReflectionSystem
        
        system = ReflectionSystem()
        
        learnings = await system.get_accumulated_learnings(
            min_confidence=0.5,
            unapplied_only=True
        )
        
        # May return empty list if no learnings exist
        assert isinstance(learnings, list)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for the full narrative scheduling pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_plan_generation(self):
        """Test complete plan generation with defaults."""
        from services.narrative_scheduler.scheduler import NarrativeScheduler
        
        scheduler = NarrativeScheduler()
        
        plan = await scheduler.generate_7_day_plan(use_defaults=True)
        
        assert plan is not None
        assert plan.total_posts > 0
        assert len(plan.scheduled_slots) > 0
        assert len(plan.reasoning_chain) > 0
    
    @pytest.mark.asyncio
    async def test_full_weekly_cycle(self):
        """Test complete weekly automation cycle."""
        from services.narrative_scheduler.weekly_automation import WeeklyAutomation
        
        automation = WeeklyAutomation()
        
        result = await automation.run_full_weekly_cycle()
        
        assert "success" in result
        assert "reflection" in result
        assert "plan" in result
        assert "summary" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
