"""
Unit tests for Weekly Planner Service (AUTO-008)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from services.weekly_planner import WeeklyPlanner, WeeklyPlanConfig, LearningWeights, WeeklyPlan


class TestWeeklyPlannerCore:
    """Test core weekly planner functionality"""

    @pytest.fixture
    async def planner(self):
        """Create a test planner instance"""
        # Reset singleton
        WeeklyPlanner._instance = None

        with patch('services.weekly_planner.create_engine'):
            planner = WeeklyPlanner.get_instance()
            yield planner

            # Cleanup
            if planner._is_running:
                await planner.stop()
            WeeklyPlanner._instance = None

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that WeeklyPlanner follows singleton pattern"""
        WeeklyPlanner._instance = None

        with patch('services.weekly_planner.create_engine'):
            planner1 = WeeklyPlanner.get_instance()
            planner2 = WeeklyPlanner.get_instance()

            assert planner1 is planner2
            assert WeeklyPlanner._instance is planner1

        WeeklyPlanner._instance = None

    @pytest.mark.asyncio
    async def test_service_start_stop(self, planner):
        """Test service lifecycle"""
        assert not planner._is_running

        # Start service
        await planner.start()
        assert planner._is_running
        assert planner._task is not None

        # Stop service
        await planner.stop()
        assert not planner._is_running

    def test_default_configuration(self, planner):
        """Test default configuration values"""
        assert planner.config.posts_per_day == 2
        assert planner.config.platforms == ["tiktok", "instagram"]
        assert planner.config.learning_window_days == 30
        assert planner.config.min_data_points == 10
        assert planner.config.diversity_factor == 0.3


class TestPlanGeneration:
    """Test plan generation logic"""

    @pytest.fixture
    async def planner(self):
        """Create a test planner instance"""
        WeeklyPlanner._instance = None

        with patch('services.weekly_planner.create_engine'):
            planner = WeeklyPlanner.get_instance()
            yield planner

            WeeklyPlanner._instance = None

    @pytest.mark.asyncio
    async def test_should_generate_plan_no_previous(self, planner):
        """Test that plan should be generated if none exist"""
        assert planner._last_plan_date is None

        should_generate = await planner._should_generate_plan()

        assert should_generate is True

    @pytest.mark.asyncio
    async def test_should_generate_plan_recent(self, planner):
        """Test that plan should not be generated if recent"""
        # Set last plan date to yesterday
        planner._last_plan_date = datetime.now(timezone.utc) - timedelta(days=1)

        should_generate = await planner._should_generate_plan()

        # Should not generate if last plan was recent
        assert should_generate is False

    @pytest.mark.asyncio
    async def test_generate_slots_correct_count(self, planner):
        """Test that correct number of slots are generated"""
        start_date = datetime(2026, 1, 20, 0, 0, 0, tzinfo=timezone.utc)  # Monday
        end_date = start_date + timedelta(days=7)

        learnings = {
            "total_posts": 50,
            "top_templates": ["tpl-001", "tpl-002"],
            "top_topics": ["productivity", "fitness"],
            "best_posting_hours": [9, 18],
            "top_formats": ["ugc"],
            "top_awareness_levels": ["problem_aware"]
        }

        allocation = {"exploit": 0.70, "explore": 0.20, "experiment": 0.10}
        experiment_learnings = {"total_experiments": 0}

        config = WeeklyPlanConfig(posts_per_day=2)

        slots = await planner._generate_slots(
            start_date=start_date,
            end_date=end_date,
            learnings=learnings,
            allocation=allocation,
            experiment_learnings=experiment_learnings,
            config=config
        )

        # 2 posts per day * 7 days = 14 slots
        assert len(slots) == 14

    @pytest.mark.asyncio
    async def test_generate_slots_respects_allocation(self, planner):
        """Test that slot types respect bandit allocation"""
        start_date = datetime(2026, 1, 20, 0, 0, 0, tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=7)

        learnings = {
            "total_posts": 50,
            "top_templates": ["tpl-001", "tpl-002", "tpl-003"],
            "top_topics": ["productivity"],
            "best_posting_hours": [9, 18],
            "top_formats": ["ugc"],
            "top_awareness_levels": ["problem_aware"]
        }

        allocation = {"exploit": 0.70, "explore": 0.20, "experiment": 0.10}
        experiment_learnings = {"total_experiments": 0}

        config = WeeklyPlanConfig(posts_per_day=2)

        slots = await planner._generate_slots(
            start_date=start_date,
            end_date=end_date,
            learnings=learnings,
            allocation=allocation,
            experiment_learnings=experiment_learnings,
            config=config
        )

        # Count slot types
        exploit_count = sum(1 for s in slots if s.get("origin_type") == "exploit")
        explore_count = sum(1 for s in slots if s.get("origin_type") == "explore")
        experiment_count = sum(1 for s in slots if s.get("origin_type") == "experiment")

        total = len(slots)

        # Verify allocation is roughly correct (within 1 slot tolerance)
        assert abs(exploit_count / total - 0.70) < 0.1
        assert abs(explore_count / total - 0.20) < 0.1
        assert abs(experiment_count / total - 0.10) < 0.15  # More tolerance for small counts

    @pytest.mark.asyncio
    async def test_generate_slots_uses_best_posting_times(self, planner):
        """Test that slots use learned best posting times"""
        start_date = datetime(2026, 1, 20, 0, 0, 0, tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=7)

        learnings = {
            "total_posts": 50,
            "top_templates": ["tpl-001"],
            "top_topics": ["productivity"],
            "best_posting_hours": [10, 16],  # Custom hours
            "top_formats": ["ugc"],
            "top_awareness_levels": ["problem_aware"]
        }

        allocation = {"exploit": 1.0, "explore": 0.0, "experiment": 0.0}
        experiment_learnings = {"total_experiments": 0}

        config = WeeklyPlanConfig(posts_per_day=2)

        slots = await planner._generate_slots(
            start_date=start_date,
            end_date=end_date,
            learnings=learnings,
            allocation=allocation,
            experiment_learnings=experiment_learnings,
            config=config
        )

        # Check that slots use the learned posting hours
        posting_hours = []
        for slot in slots:
            scheduled_dt = datetime.fromisoformat(slot["scheduled_at"])
            posting_hours.append(scheduled_dt.hour)

        # Should contain hours 10 and 16
        assert 10 in posting_hours
        assert 16 in posting_hours


class TestPerformanceAnalysis:
    """Test performance analysis and learning"""

    @pytest.fixture
    async def planner(self):
        """Create a test planner instance"""
        WeeklyPlanner._instance = None

        with patch('services.weekly_planner.create_engine'):
            planner = WeeklyPlanner.get_instance()
            yield planner

            WeeklyPlanner._instance = None

    @pytest.mark.asyncio
    async def test_get_bandit_allocation_default(self, planner):
        """Test that default allocation is returned if service unavailable"""
        with patch('services.weekly_planner.BanditAllocator') as mock_allocator:
            mock_allocator.side_effect = ImportError("Service not available")

            allocation = await planner._get_bandit_allocation()

            # Should return default 70/20/10 split
            assert allocation["exploit"] == 0.70
            assert allocation["explore"] == 0.20
            assert allocation["experiment"] == 0.10


class TestConfiguration:
    """Test configuration and settings"""

    def test_weekly_plan_config_defaults(self):
        """Test default configuration"""
        config = WeeklyPlanConfig()

        assert config.posts_per_day == 2
        assert config.platforms == ["tiktok", "instagram"]
        assert config.default_posting_times == ["09:00", "18:00"]
        assert config.learning_window_days == 30
        assert config.min_data_points == 10
        assert config.diversity_factor == 0.3

    def test_weekly_plan_config_custom(self):
        """Test custom configuration"""
        config = WeeklyPlanConfig(
            posts_per_day=3,
            platforms=["tiktok", "instagram", "twitter"],
            learning_window_days=60
        )

        assert config.posts_per_day == 3
        assert len(config.platforms) == 3
        assert config.learning_window_days == 60

    def test_learning_weights(self):
        """Test learning weights configuration"""
        weights = LearningWeights()

        # Weights should sum to 1.0
        total = (
            weights.template_performance +
            weights.topic_performance +
            weights.time_slot_performance +
            weights.format_performance +
            weights.experiment_insights
        )

        assert abs(total - 1.0) < 0.01  # Allow small floating point error


class TestWeeklyPlan:
    """Test WeeklyPlan data class"""

    def test_weekly_plan_creation(self):
        """Test creating a weekly plan"""
        start_date = datetime(2026, 1, 20, 0, 0, 0, tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=7)

        plan = WeeklyPlan(
            id="plan-20260120",
            start_date=start_date,
            end_date=end_date,
            slots=[],
            learnings={},
            metadata={}
        )

        assert plan.id == "plan-20260120"
        assert plan.start_date == start_date
        assert plan.end_date == end_date
        assert isinstance(plan.slots, list)
        assert isinstance(plan.learnings, dict)
        assert isinstance(plan.metadata, dict)


class TestIntegration:
    """Integration tests with mocked database"""

    @pytest.fixture
    async def planner(self):
        """Create a test planner instance"""
        WeeklyPlanner._instance = None

        with patch('services.weekly_planner.create_engine'):
            planner = WeeklyPlanner.get_instance()
            yield planner

            WeeklyPlanner._instance = None

    @pytest.mark.asyncio
    async def test_generate_weekly_plan_full_flow(self, planner):
        """Test full plan generation flow with mocked data"""
        start_date = datetime(2026, 1, 20, 0, 0, 0, tzinfo=timezone.utc)

        # Mock dependencies
        with patch.object(planner, '_analyze_performance') as mock_analyze, \
             patch.object(planner, '_get_bandit_allocation') as mock_bandit, \
             patch.object(planner, '_get_experiment_learnings') as mock_experiments, \
             patch.object(planner, '_save_plan') as mock_save:

            # Setup mock data
            mock_analyze.return_value = {
                "total_posts": 50,
                "top_templates": ["tpl-001", "tpl-002"],
                "top_topics": ["productivity", "fitness"],
                "best_posting_hours": [9, 18],
                "top_formats": ["ugc"],
                "top_awareness_levels": ["problem_aware"]
            }

            mock_bandit.return_value = {
                "exploit": 0.70,
                "explore": 0.20,
                "experiment": 0.10
            }

            mock_experiments.return_value = {
                "total_experiments": 2,
                "passed_hypotheses": [],
                "failed_hypotheses": []
            }

            # Generate plan
            plan = await planner.generate_weekly_plan(start_date=start_date)

            # Verify plan was created
            assert plan is not None
            assert plan.start_date == start_date
            assert len(plan.slots) == 14  # 2 posts/day * 7 days

            # Verify mocks were called
            mock_analyze.assert_called_once()
            mock_bandit.assert_called_once()
            mock_experiments.assert_called_once()
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_weekly_plan_insufficient_data(self, planner):
        """Test that plan is not generated with insufficient data"""
        start_date = datetime(2026, 1, 20, 0, 0, 0, tzinfo=timezone.utc)

        # Mock insufficient data
        with patch.object(planner, '_analyze_performance') as mock_analyze:
            mock_analyze.return_value = {
                "total_posts": 5,  # Below min_data_points (10)
                "top_templates": [],
                "top_topics": []
            }

            # Generate plan
            plan = await planner.generate_weekly_plan(start_date=start_date)

            # Should return None due to insufficient data
            assert plan is None

    @pytest.mark.asyncio
    async def test_get_status(self, planner):
        """Test status reporting"""
        status = planner.get_status()

        assert "is_running" in status
        assert "check_interval" in status
        assert "last_plan_date" in status
        assert "config" in status
        assert status["config"]["posts_per_day"] == 2
        assert status["config"]["diversity_factor"] == 0.3
