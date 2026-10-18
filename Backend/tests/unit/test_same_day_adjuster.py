"""
Unit tests for Same-Day Adjuster Service (AUTO-007)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from services.same_day_adjuster import SameDayAdjuster, PerformanceThreshold, SlotAdjustment


class TestSameDayAdjusterCore:
    """Test core same-day adjuster functionality"""

    @pytest.fixture
    async def adjuster(self):
        """Create a test adjuster instance"""
        # Reset singleton
        SameDayAdjuster._instance = None

        with patch('services.same_day_adjuster.create_engine'):
            adjuster = SameDayAdjuster.get_instance()
            yield adjuster

            # Cleanup
            if adjuster._is_running:
                await adjuster.stop()
            SameDayAdjuster._instance = None

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that SameDayAdjuster follows singleton pattern"""
        SameDayAdjuster._instance = None

        with patch('services.same_day_adjuster.create_engine'):
            adjuster1 = SameDayAdjuster.get_instance()
            adjuster2 = SameDayAdjuster.get_instance()

            assert adjuster1 is adjuster2
            assert SameDayAdjuster._instance is adjuster1

        SameDayAdjuster._instance = None

    @pytest.mark.asyncio
    async def test_service_start_stop(self, adjuster):
        """Test service lifecycle"""
        assert not adjuster._is_running

        # Start service
        await adjuster.start()
        assert adjuster._is_running
        assert adjuster._task is not None

        # Stop service
        await adjuster.stop()
        assert not adjuster._is_running

    @pytest.mark.asyncio
    async def test_post_published_event(self, adjuster):
        """Test handling of post published events"""
        mock_event = Mock()
        mock_event.payload = {"post_id": "post123"}

        initial_count = len(adjuster._monitored_posts)

        await adjuster._on_post_published(mock_event)

        assert len(adjuster._monitored_posts) == initial_count + 1
        assert "post123" in adjuster._monitored_posts


class TestPerformanceAnalysis:
    """Test performance analysis logic"""

    @pytest.fixture
    async def adjuster(self):
        """Create a test adjuster instance"""
        SameDayAdjuster._instance = None

        with patch('services.same_day_adjuster.create_engine'):
            adjuster = SameDayAdjuster.get_instance()
            yield adjuster

            SameDayAdjuster._instance = None

    @pytest.mark.asyncio
    async def test_analyze_patterns_winners_and_losers(self, adjuster):
        """Test pattern analysis identifies winners and losers"""
        posts = [
            {
                "id": "1",
                "views": 10000,
                "engagement_rate": 5.0,
                "template_id": "tpl-001",
                "topic": "productivity",
                "awareness_level": "problem_aware"
            },
            {
                "id": "2",
                "views": 5000,
                "engagement_rate": 2.5,
                "template_id": "tpl-002",
                "topic": "fitness",
                "awareness_level": "solution_aware"
            },
            {
                "id": "3",
                "views": 1000,
                "engagement_rate": 0.5,
                "template_id": "tpl-003",
                "topic": "coding",
                "awareness_level": "product_aware"
            }
        ]

        patterns = await adjuster._analyze_patterns(posts)

        assert patterns["total_analyzed"] == 3
        assert patterns["winner_count"] >= 1  # High performer should be identified
        assert patterns["loser_count"] >= 1   # Low performer should be identified
        assert "winning_templates" in patterns
        assert "losing_templates" in patterns

    @pytest.mark.asyncio
    async def test_analyze_patterns_empty_list(self, adjuster):
        """Test pattern analysis with empty post list"""
        patterns = await adjuster._analyze_patterns([])

        assert patterns == {}

    @pytest.mark.asyncio
    async def test_analyze_patterns_extracts_topics(self, adjuster):
        """Test that pattern analysis extracts winning topics"""
        posts = [
            {
                "id": "1",
                "views": 10000,
                "engagement_rate": 5.0,
                "template_id": "tpl-001",
                "topic": "productivity",
                "awareness_level": "problem_aware"
            },
            {
                "id": "2",
                "views": 9000,
                "engagement_rate": 4.5,
                "template_id": "tpl-002",
                "topic": "productivity",
                "awareness_level": "solution_aware"
            }
        ]

        patterns = await adjuster._analyze_patterns(posts)

        assert "winning_topics" in patterns
        assert "productivity" in patterns["winning_topics"] or patterns["winner_count"] > 0


class TestSlotAdjustment:
    """Test slot adjustment generation and application"""

    @pytest.fixture
    async def adjuster(self):
        """Create a test adjuster instance"""
        SameDayAdjuster._instance = None

        with patch('services.same_day_adjuster.create_engine'):
            adjuster = SameDayAdjuster.get_instance()
            yield adjuster

            SameDayAdjuster._instance = None

    @pytest.mark.asyncio
    async def test_generate_adjustments_replaces_losers(self, adjuster):
        """Test that adjustments replace losing templates with winners"""
        patterns = {
            "winning_templates": ["tpl-winner"],
            "losing_templates": ["tpl-loser"],
            "winning_topics": ["productivity"],
            "losing_topics": ["random"]
        }

        slots = [
            {
                "id": "slot1",
                "template_id": "tpl-loser",
                "topic": "random",
                "scheduled_at": datetime.now(timezone.utc) + timedelta(hours=2)
            },
            {
                "id": "slot2",
                "template_id": "tpl-other",
                "topic": "fitness",
                "scheduled_at": datetime.now(timezone.utc) + timedelta(hours=4)
            }
        ]

        adjustments = await adjuster._generate_adjustments(patterns, slots)

        assert len(adjustments) >= 1
        # First slot with losing template should be adjusted
        assert any(adj.slot_id == "slot1" and adj.new_template_id == "tpl-winner"
                  for adj in adjustments)

    @pytest.mark.asyncio
    async def test_generate_adjustments_no_winners(self, adjuster):
        """Test that no adjustments are made without clear winners"""
        patterns = {
            "winning_templates": [],
            "losing_templates": ["tpl-loser"],
            "winning_topics": [],
            "losing_topics": []
        }

        slots = [
            {
                "id": "slot1",
                "template_id": "tpl-loser",
                "topic": "random",
                "scheduled_at": datetime.now(timezone.utc) + timedelta(hours=2)
            }
        ]

        adjustments = await adjuster._generate_adjustments(patterns, slots)

        # Should return empty list when no winners to promote
        assert len(adjustments) == 0

    @pytest.mark.asyncio
    async def test_adjustment_has_reason_and_confidence(self, adjuster):
        """Test that adjustments include reason and confidence"""
        patterns = {
            "winning_templates": ["tpl-winner"],
            "losing_templates": ["tpl-loser"],
            "winning_topics": [],
            "losing_topics": []
        }

        slots = [
            {
                "id": "slot1",
                "template_id": "tpl-loser",
                "topic": "random",
                "scheduled_at": datetime.now(timezone.utc) + timedelta(hours=2)
            }
        ]

        adjustments = await adjuster._generate_adjustments(patterns, slots)

        assert len(adjustments) > 0
        adj = adjustments[0]
        assert adj.reason is not None and len(adj.reason) > 0
        assert 0 <= adj.confidence <= 1.0


class TestConfiguration:
    """Test configuration and thresholds"""

    @pytest.fixture
    async def adjuster(self):
        """Create a test adjuster instance"""
        SameDayAdjuster._instance = None

        with patch('services.same_day_adjuster.create_engine'):
            adjuster = SameDayAdjuster.get_instance()
            yield adjuster

            SameDayAdjuster._instance = None

    def test_default_thresholds(self, adjuster):
        """Test default threshold values"""
        assert adjuster.thresholds.winner_multiplier == 1.5
        assert adjuster.thresholds.loser_multiplier == 0.6
        assert adjuster.thresholds.min_impressions == 100

    def test_get_status(self, adjuster):
        """Test status reporting"""
        status = adjuster.get_status()

        assert "is_running" in status
        assert "check_interval" in status
        assert "monitored_posts_count" in status
        assert "thresholds" in status
        assert status["thresholds"]["winner_multiplier"] == 1.5


class TestIntegration:
    """Integration tests with mocked database"""

    @pytest.fixture
    async def adjuster(self):
        """Create a test adjuster instance"""
        SameDayAdjuster._instance = None

        with patch('services.same_day_adjuster.create_engine'):
            adjuster = SameDayAdjuster.get_instance()
            yield adjuster

            SameDayAdjuster._instance = None

    @pytest.mark.asyncio
    async def test_check_and_adjust_full_flow(self, adjuster):
        """Test full check and adjust flow with mocked data"""
        # Mock database queries
        with patch.object(adjuster, '_get_early_performance') as mock_performance, \
             patch.object(adjuster, '_get_remaining_slots') as mock_slots, \
             patch.object(adjuster, '_apply_adjustments') as mock_apply:

            # Setup mock data
            mock_performance.return_value = [
                {
                    "id": "1",
                    "views": 10000,
                    "engagement_rate": 5.0,
                    "template_id": "tpl-winner",
                    "topic": "productivity",
                    "awareness_level": "problem_aware",
                    "hours_since_posted": 2.0
                },
                {
                    "id": "2",
                    "views": 500,
                    "engagement_rate": 0.3,
                    "template_id": "tpl-loser",
                    "topic": "random",
                    "awareness_level": "solution_aware",
                    "hours_since_posted": 1.5
                }
            ]

            mock_slots.return_value = [
                {
                    "id": "slot1",
                    "template_id": "tpl-loser",
                    "topic": "random",
                    "scheduled_at": datetime.now(timezone.utc) + timedelta(hours=2),
                    "awareness_level": "problem_aware",
                    "content_type": "ugc",
                    "platform": "tiktok"
                }
            ]

            # Run check and adjust
            await adjuster._check_and_adjust()

            # Verify mocks were called
            mock_performance.assert_called_once()
            mock_slots.assert_called_once()
            mock_apply.assert_called_once()

            # Verify adjustments were generated
            call_args = mock_apply.call_args
            adjustments = call_args[0][0]
            assert len(adjustments) > 0
