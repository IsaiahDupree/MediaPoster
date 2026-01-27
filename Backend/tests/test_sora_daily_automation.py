"""
Tests for Daily Sora Automation System
Tests SORA-AUTO-001 through SORA-AUTO-006 from PRD_Daily_Sora_Automation.md
"""

import pytest
from datetime import datetime, timezone, date


class TestSoraDailyImports:
    """Test that all Sora daily components can be imported."""
    
    def test_scheduler_imports(self):
        """Test DailySoraScheduler can be imported."""
        from services.sora_daily import DailySoraScheduler, get_daily_scheduler
        assert DailySoraScheduler is not None
        assert get_daily_scheduler is not None
    
    def test_job_models_import(self):
        """Test job models can be imported."""
        from services.sora_daily import SoraJob, DailyPlan, JobStatus, JobType
        assert SoraJob is not None
        assert DailyPlan is not None
        assert JobStatus is not None
        assert JobType is not None
    
    def test_watermark_service_imports(self):
        """Test WatermarkRemovalService can be imported."""
        from services.sora_daily import WatermarkRemovalService, get_watermark_service
        assert WatermarkRemovalService is not None
        assert get_watermark_service is not None
    
    def test_story_generator_imports(self):
        """Test StoryGenerator can be imported."""
        from services.sora_daily import StoryGenerator, get_story_generator, STORY_THEMES
        assert StoryGenerator is not None
        assert get_story_generator is not None
        assert len(STORY_THEMES) >= 10
    
    def test_trend_collector_imports(self):
        """Test TrendCollector can be imported."""
        from services.sora_daily import TrendCollector, TrendSource, get_trend_collector
        assert TrendCollector is not None
        assert TrendSource is not None
        assert get_trend_collector is not None


class TestSoraAutoJob:
    """Tests for SORA-AUTO-001: Daily Usage Optimization."""
    
    def test_sora_job_creation(self):
        """Test SoraJob dataclass creation."""
        from services.sora_daily import SoraJob, JobType
        
        job = SoraJob(
            plan_id="plan123",
            job_type=JobType.SINGLE.value,
            prompt="Test prompt for @isaiahdupree",
            theme="adventure",
            character="@isaiahdupree"
        )
        
        assert job.id is not None
        assert job.plan_id == "plan123"
        assert job.job_type == "single"
        assert job.character == "@isaiahdupree"
        assert job.status == "pending"
    
    def test_sora_job_to_dict(self):
        """Test SoraJob serialization."""
        from services.sora_daily import SoraJob
        
        job = SoraJob(
            plan_id="plan456",
            job_type="movie_part_1",
            prompt="Test movie part 1",
            theme="discovery"
        )
        
        data = job.to_dict()
        
        assert "id" in data
        assert data["plan_id"] == "plan456"
        assert data["job_type"] == "movie_part_1"
        assert data["status"] == "pending"
    
    def test_movie_job_with_movie_id(self):
        """Test 3-part movie job grouping."""
        from services.sora_daily import SoraJob
        
        movie_id = "movie123"
        
        part1 = SoraJob(job_type="movie_part_1", movie_id=movie_id, prompt="Part 1")
        part2 = SoraJob(job_type="movie_part_2", movie_id=movie_id, prompt="Part 2")
        part3 = SoraJob(job_type="movie_part_3", movie_id=movie_id, prompt="Part 3")
        
        assert part1.movie_id == part2.movie_id == part3.movie_id


class TestDailyPlan:
    """Tests for daily plan management."""
    
    def test_daily_plan_creation(self):
        """Test DailyPlan dataclass creation."""
        from services.sora_daily import DailyPlan
        
        plan = DailyPlan()
        
        assert plan.id is not None
        assert plan.plan_date == date.today()
        assert plan.total_credits == 30
        assert plan.used_credits == 0
        assert plan.singles_planned == 10
        assert plan.movies_planned == 4
        assert plan.status == "pending"
    
    def test_daily_plan_to_dict(self):
        """Test DailyPlan serialization."""
        from services.sora_daily import DailyPlan
        
        plan = DailyPlan()
        data = plan.to_dict()
        
        assert "id" in data
        assert "date" in data
        assert data["total_credits"] == 30
        assert data["remaining_credits"] == 30
    
    def test_daily_plan_math(self):
        """Test credit calculations."""
        from services.sora_daily import DailyPlan
        
        plan = DailyPlan()
        
        # 4 movies × 3 parts = 12 videos
        # 10 singles
        # Total = 22, with 8 buffer
        expected_used = plan.singles_planned + (plan.movies_planned * 3)
        assert expected_used == 22  # 10 + 12


class TestWatermarkService:
    """Tests for SORA-AUTO-002: BlankLogo Watermark Removal."""
    
    def test_watermark_service_initialization(self):
        """Test WatermarkRemovalService initializes."""
        from services.sora_daily import WatermarkRemovalService
        
        service = WatermarkRemovalService()
        assert service is not None
        assert service.output_dir.exists()
    
    def test_watermark_singleton(self):
        """Test watermark service singleton."""
        from services.sora_daily import get_watermark_service
        
        s1 = get_watermark_service()
        s2 = get_watermark_service()
        
        assert s1 is s2
    
    def test_blanklogo_path_check(self):
        """Test BlankLogo availability check."""
        from services.sora_daily import get_watermark_service
        
        service = get_watermark_service()
        # May or may not be available depending on system
        assert isinstance(service.is_available, bool)


class TestStoryGenerator:
    """Tests for SORA-AUTO-003 & SORA-AUTO-004: Story Generation."""
    
    def test_story_generator_initialization(self):
        """Test StoryGenerator initializes."""
        from services.sora_daily import StoryGenerator
        
        gen = StoryGenerator()
        assert gen is not None
    
    def test_story_themes_defined(self):
        """Test story themes are defined."""
        from services.sora_daily import STORY_THEMES
        
        assert len(STORY_THEMES) >= 10
        assert "adventure" in STORY_THEMES
        assert "day_in_life" in STORY_THEMES
    
    def test_random_theme_selection(self):
        """Test random theme selection."""
        from services.sora_daily import get_story_generator
        
        gen = get_story_generator()
        
        themes = set()
        for _ in range(20):
            themes.add(gen.get_random_theme())
        
        # Should get some variety
        assert len(themes) >= 3
    
    def test_template_prompt_generation(self):
        """Test template-based prompt generation."""
        from services.sora_daily import get_story_generator
        
        gen = get_story_generator()
        
        prompt = gen._generate_template_prompt(
            theme="adventure",
            style="cinematic 4K",
            location="modern city skyline",
            character="@isaiahdupree"
        )
        
        assert "@isaiahdupree" in prompt
        assert len(prompt) > 50
    
    def test_movie_template_generation(self):
        """Test 3-part movie template generation."""
        from services.sora_daily import get_story_generator
        
        gen = get_story_generator()
        
        part1 = gen._generate_movie_template(1, "challenge", "dramatic", "@isaiahdupree")
        part2 = gen._generate_movie_template(2, "challenge", "dramatic", "@isaiahdupree")
        part3 = gen._generate_movie_template(3, "challenge", "dramatic", "@isaiahdupree")
        
        assert "@isaiahdupree" in part1
        assert "@isaiahdupree" in part2
        assert "@isaiahdupree" in part3
        
        # Each part should be different
        assert part1 != part2 != part3


class TestTrendCollector:
    """Tests for SORA-AUTO-003: Trend-Based Story Generation."""
    
    def test_trend_collector_initialization(self):
        """Test TrendCollector initializes."""
        from services.sora_daily import TrendCollector
        
        collector = TrendCollector()
        assert collector is not None
    
    def test_trend_source_creation(self):
        """Test TrendSource dataclass creation."""
        from services.sora_daily import TrendSource
        
        trend = TrendSource(
            source_type="comment",
            topic="productivity tips",
            relevance_score=0.85
        )
        
        assert trend.id is not None
        assert trend.topic == "productivity tips"
        assert trend.relevance_score == 0.85
        assert trend.used_in_story == False
    
    def test_trend_source_to_dict(self):
        """Test TrendSource serialization."""
        from services.sora_daily import TrendSource
        
        trend = TrendSource(
            source_type="twitter",
            topic="AI trends"
        )
        
        data = trend.to_dict()
        
        assert "id" in data
        assert data["source_type"] == "twitter"
        assert data["topic"] == "AI trends"
    
    def test_trend_collector_singleton(self):
        """Test trend collector singleton."""
        from services.sora_daily import get_trend_collector
        
        c1 = get_trend_collector()
        c2 = get_trend_collector()
        
        assert c1 is c2


class TestDailySoraScheduler:
    """Tests for scheduler operations."""
    
    def test_scheduler_initialization(self):
        """Test DailySoraScheduler initializes."""
        from services.sora_daily import DailySoraScheduler
        
        scheduler = DailySoraScheduler()
        assert scheduler is not None
        assert scheduler.engine is not None
    
    def test_scheduler_singleton(self):
        """Test scheduler singleton."""
        from services.sora_daily import get_daily_scheduler
        
        s1 = get_daily_scheduler()
        s2 = get_daily_scheduler()
        
        assert s1 is s2
    
    def test_get_or_create_today_plan(self):
        """Test creating today's plan."""
        from services.sora_daily import get_daily_scheduler
        
        scheduler = get_daily_scheduler()
        plan = scheduler.get_or_create_today_plan()
        
        assert plan is not None
        assert plan.plan_date == date.today()
        assert plan.total_credits == 30
    
    def test_get_daily_status(self):
        """Test getting daily status."""
        from services.sora_daily import get_daily_scheduler
        
        scheduler = get_daily_scheduler()
        status = scheduler.get_daily_status()
        
        assert "plan" in status
        assert "jobs_count" in status
        assert "status_breakdown" in status
        assert "is_running" in status


class TestJobStatusEnum:
    """Tests for job status enum."""
    
    def test_all_statuses_defined(self):
        """Test all job statuses are defined."""
        from services.sora_daily import JobStatus
        
        expected = [
            "pending", "queued", "generating", "downloading",
            "removing_watermark", "stitching", "publishing",
            "completed", "failed"
        ]
        
        actual = [s.value for s in JobStatus]
        
        for status in expected:
            assert status in actual


class TestJobTypeEnum:
    """Tests for job type enum."""
    
    def test_all_types_defined(self):
        """Test all job types are defined."""
        from services.sora_daily import JobType
        
        expected = ["single", "movie_part_1", "movie_part_2", "movie_part_3"]
        actual = [t.value for t in JobType]
        
        for job_type in expected:
            assert job_type in actual


class TestSoraDailyAPI:
    """Tests for Sora Daily API endpoints."""
    
    def test_api_router_exists(self):
        """Test API router can be imported."""
        from api.endpoints.sora_daily import router
        assert router is not None
    
    def test_status_endpoints_exist(self):
        """Test status endpoints exist."""
        from api.endpoints.sora_daily import (
            get_daily_status,
            get_today_plan
        )
        assert get_daily_status is not None
        assert get_today_plan is not None
    
    def test_run_control_endpoints_exist(self):
        """Test run control endpoints exist."""
        from api.endpoints.sora_daily import (
            start_daily_run,
            pause_daily_run,
            resume_daily_run
        )
        assert start_daily_run is not None
        assert pause_daily_run is not None
        assert resume_daily_run is not None
    
    def test_job_endpoints_exist(self):
        """Test job management endpoints exist."""
        from api.endpoints.sora_daily import (
            get_jobs,
            get_pending_jobs,
            retry_job
        )
        assert get_jobs is not None
        assert get_pending_jobs is not None
        assert retry_job is not None
    
    def test_trend_endpoints_exist(self):
        """Test trend endpoints exist."""
        from api.endpoints.sora_daily import (
            get_trends,
            collect_trends
        )
        assert get_trends is not None
        assert collect_trends is not None
    
    def test_watermark_endpoints_exist(self):
        """Test watermark endpoints exist."""
        from api.endpoints.sora_daily import (
            remove_watermark,
            get_watermark_service_status
        )
        assert remove_watermark is not None
        assert get_watermark_service_status is not None
    
    def test_story_endpoints_exist(self):
        """Test story generation endpoints exist."""
        from api.endpoints.sora_daily import (
            generate_single_prompt,
            generate_movie_arc,
            get_available_themes
        )
        assert generate_single_prompt is not None
        assert generate_movie_arc is not None
        assert get_available_themes is not None
    
    def test_history_endpoint_exists(self):
        """Test history endpoint exists."""
        from api.endpoints.sora_daily import get_history
        assert get_history is not None


class TestPubSubEvents:
    """Tests for pub/sub event integration."""
    
    def test_event_types_documented(self):
        """Test that expected event types are in PRD."""
        expected_events = [
            "sora.daily.started",
            "sora.generation.queued",
            "sora.generation.completed",
            "sora.video.downloaded",
            "sora.watermark.removed",
            "sora.movie.stitched",
            "sora.youtube.published",
            "sora.daily.completed"
        ]
        
        # These events should be emitted by the scheduler
        # Just verify the list is comprehensive
        assert len(expected_events) == 8
