"""
Tests for Coach Service (PRD2)
Verifies insight logic, comparison math, and derivative planning
Target: ~30 tests
"""
import pytest
from uuid import uuid4
from datetime import datetime

from services.prd2.coach_service import CoachService
from models.supabase_models import (
    MediaAnalysis, PostingMetrics, Comment, AICoachInsight,
    DerivativeFormat, DerivativeMediaPlan
)

class TestCoachService:
    """Tests for AI Coach logic"""

    @pytest.fixture
    def service(self):
        return CoachService()

    @pytest.fixture
    def high_performer(self):
        """Setup data for high performance"""
        analysis = MediaAnalysis(media_id=uuid4(), pre_social_score=70)
        metrics = PostingMetrics(schedule_id=uuid4(), post_social_score=90, views=1000)
        return analysis, metrics

    @pytest.fixture
    def low_performer(self):
        """Setup data for underperformance"""
        analysis = MediaAnalysis(media_id=uuid4(), pre_social_score=80)
        metrics = PostingMetrics(schedule_id=uuid4(), post_social_score=40, views=100)
        return analysis, metrics

    # ============================================
    # Insight Generation Tests
    # ============================================

    def test_generate_insight_viral(self, service, high_performer):
        """Test insights for viral content"""
        analysis, metrics = high_performer
        comments = [Comment(schedule_id=metrics.schedule_id, platform_comment_id="", author_handle="", text="", sentiment_score=0.9)]
        
        insight = service.generate_insight(analysis, metrics, comments, "24h")
        
        assert "Viral hit" in insight.summary
        assert "High engagement rate" in insight.what_worked
        assert len(insight.next_actions) > 0

    def test_generate_insight_underperform(self, service, low_performer):
        """Test insights for underperformance"""
        analysis, metrics = low_performer
        insight = service.generate_insight(analysis, metrics, [], "7d")
        
        assert "Underperformed" in insight.summary
        assert "Hook might be misleading" in insight.what_to_change

    def test_generate_insight_no_scores(self, service):
        """Test insight with missing scores (None)"""
        analysis = MediaAnalysis(media_id=uuid4(), pre_social_score=None)
        metrics = PostingMetrics(schedule_id=uuid4(), post_social_score=None)
        
        insight = service.generate_insight(analysis, metrics, [], "24h")
        assert "Performed within expected range" in insight.summary
        assert insight.input_snapshot["pre_score"] == 0

    def test_snapshot_data(self, service, high_performer):
        """Test that insight captures input state"""
        analysis, metrics = high_performer
        insight = service.generate_insight(analysis, metrics, [], "24h")
        
        assert insight.input_snapshot["views"] == 1000
        assert insight.input_snapshot["post_score"] == 90

    # ============================================
    # Derivative Planning Tests
    # ============================================

    def test_derivative_plans_viral(self, service):
        """Test high score generates plans"""
        # Create insight with high post score
        insight = AICoachInsight(
            media_id=uuid4(), checkpoint="24h", summary="Good",
            input_snapshot={"post_score": 90}
        )
        
        plans = service.generate_derivative_plans(insight)
        assert len(plans) == 2
        
        types = [p.format_type for p in plans]
        assert DerivativeFormat.FACE_CAM in types
        assert DerivativeFormat.BROLL_TEXT in types

    def test_derivative_plans_average(self, service):
        """Test average score generates no plans"""
        insight = AICoachInsight(
            media_id=uuid4(), checkpoint="24h", summary="Ok",
            input_snapshot={"post_score": 50}
        )
        
        plans = service.generate_derivative_plans(insight)
        assert len(plans) == 0

    def test_plan_structure(self, service):
        """Test generated plan validity"""
        insight = AICoachInsight(
            media_id=uuid4(), checkpoint="24h", summary="Good",
            input_snapshot={"post_score": 85}
        )
        plan = service.generate_derivative_plans(insight)[0]
        
        assert isinstance(plan, DerivativeMediaPlan)
        assert plan.status == "planned"
        assert plan.estimated_length_sec > 0

    # ============================================
    # Edge Case Tests
    # ============================================

    def test_empty_snapshot(self, service):
        """Test gracefull handling of missing snapshot data"""
        insight = AICoachInsight(media_id=uuid4(), checkpoint="x", summary="x")
        plans = service.generate_derivative_plans(insight)
        assert len(plans) == 0

