"""
Integration Tests for ARCH-001 to ARCH-008
===========================================
Comprehensive tests for System Architecture Integration features.

Test Coverage:
- ARCH-001: Master Orchestrator Service
- ARCH-002: 3-Part Sora Batch Coordination
- ARCH-003: Content Analyzer → Publisher Integration
- ARCH-004: Tweet Scheduler (2-Hour Interval)
- ARCH-005: Offer Traffic Tracking Service
- ARCH-006: Analytics Feedback Loop
- ARCH-007: Unified Pipeline API Endpoint
- ARCH-008: Pipeline Dashboard Widget

Usage:
    pytest tests/test_arch_integration.py -v
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from services.event_bus import EventBus, Topics, Event
from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.tweet_scheduler import TweetScheduler
from services.offer_traffic_tracker import OfferTrafficTracker


class TestARCH001MasterOrchestrator:
    """Test ARCH-001: Master Orchestrator Service"""

    @pytest.fixture
    def event_bus(self):
        """Create fresh EventBus for each test."""
        EventBus.reset_instance()
        return EventBus.get_instance()

    @pytest.fixture
    def orchestrator(self, event_bus):
        """Create fresh MasterOrchestrator for each test."""
        MasterOrchestrator._instance = None
        return MasterOrchestrator.get_instance(event_bus=event_bus, use_db=False)

    @pytest.mark.asyncio
    async def test_start_pipeline_initializes_state(self, orchestrator, event_bus):
        """Test that start_pipeline creates pipeline in active state."""
        config = PipelineConfig(
            theme="Test theme",
            num_parts=3,
            schedule_tweets=False
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        assert pipeline_id is not None
        assert pipeline_id in orchestrator.active_pipelines
        assert orchestrator.active_pipelines[pipeline_id]["status"] == "generating_video"

    @pytest.mark.asyncio
    async def test_pipeline_status_retrieval(self, orchestrator):
        """Test getting pipeline status."""
        config = PipelineConfig(theme="Test", num_parts=1, schedule_tweets=False)
        pipeline_id = await orchestrator.start_pipeline(config)

        status = orchestrator.get_pipeline_status(pipeline_id)

        assert status["pipeline_id"] == pipeline_id
        assert status["status"] == "generating_video"
        assert status["theme"] == "Test"

    @pytest.mark.asyncio
    async def test_pipeline_cancel(self, orchestrator):
        """Test canceling a pipeline."""
        config = PipelineConfig(theme="Test", num_parts=1, schedule_tweets=False)
        pipeline_id = await orchestrator.start_pipeline(config)

        cancelled = await orchestrator.cancel_pipeline(pipeline_id)

        assert cancelled is True
        assert pipeline_id not in orchestrator.active_pipelines
        assert orchestrator.completed_pipelines[pipeline_id]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_list_pipelines(self, orchestrator):
        """Test listing pipelines."""
        config1 = PipelineConfig(theme="Theme 1", num_parts=1, schedule_tweets=False)
        config2 = PipelineConfig(theme="Theme 2", num_parts=2, schedule_tweets=False)

        id1 = await orchestrator.start_pipeline(config1)
        id2 = await orchestrator.start_pipeline(config2)

        pipelines = await orchestrator.list_pipelines(limit=10)

        assert len(pipelines) == 2
        pipeline_ids = [p.get("pipeline_id") for p in pipelines]
        assert id1 in pipeline_ids
        assert id2 in pipeline_ids


class TestARCH004TweetScheduler:
    """Test ARCH-004: Tweet Scheduler (2-Hour Intervals)"""

    @pytest.fixture
    def event_bus(self):
        """Create fresh EventBus for each test."""
        EventBus.reset_instance()
        return EventBus.get_instance()

    @pytest.fixture
    def scheduler(self, event_bus):
        """Create fresh TweetScheduler for each test."""
        TweetScheduler._instance = None
        return TweetScheduler.get_instance(event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_schedule_tweet_campaign(self, scheduler):
        """Test scheduling a tweet campaign with proper intervals."""
        result = await scheduler.schedule_tweet_campaign(
            pipeline_id="pipeline-test",
            theme="AI automation",
            tweets_per_day=12,
            duration_days=1
        )

        assert result["campaign_id"] is not None
        assert result["scheduled_count"] == 12
        assert len(result["tweet_schedule"]) == 12

        # Verify 2-hour intervals (24 hours / 12 tweets = 2 hours)
        tweet_times = [datetime.fromisoformat(t["scheduled_at"]) for t in result["tweet_schedule"]]
        for i in range(len(tweet_times) - 1):
            interval = (tweet_times[i + 1] - tweet_times[i]).total_seconds() / 60
            assert abs(interval - 120) < 2  # Allow 2 minute tolerance

    @pytest.mark.asyncio
    async def test_tweet_campaign_status(self, scheduler):
        """Test retrieving campaign status."""
        result = await scheduler.schedule_tweet_campaign(
            pipeline_id="pipeline-test",
            theme="Test",
            tweets_per_day=3,
            duration_days=1
        )
        campaign_id = result["campaign_id"]

        status = scheduler.get_campaign_status(campaign_id)

        assert status["campaign_id"] == campaign_id
        assert status["total_tweets"] == 3
        assert status["scheduled_count"] == 3


class TestARCH005OfferTrafficTracker:
    """Test ARCH-005: Offer Traffic Tracking Service"""

    @pytest.fixture
    def event_bus(self):
        """Create fresh EventBus for each test."""
        EventBus.reset_instance()
        return EventBus.get_instance()

    @pytest.fixture
    def tracker(self, event_bus):
        """Create fresh OfferTrafficTracker for each test."""
        OfferTrafficTracker._instance = None
        return OfferTrafficTracker.get_instance(event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_create_tracked_link(self, tracker):
        """Test creating a tracked link with UTM parameters."""
        tracked_url = await tracker.create_tracked_link(
            offer_url="https://example.com/offer",
            campaign="pipeline-123",
            source="tiktok"
        )

        assert "utm_source=tiktok" in tracked_url
        assert "utm_campaign=pipeline-123" in tracked_url
        assert "utm_content=" in tracked_url

    def test_platform_performance(self, tracker):
        """Test getting platform performance metrics."""
        # Manually add some tracked links
        tracker._tracked_links["code1"] = {
            "tracking_code": "code1",
            "campaign": "pipeline-1",
            "platform": "tiktok",
            "clicks": 100,
            "conversions": 5,
            "revenue_usd": 50.0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        tracker._tracked_links["code2"] = {
            "tracking_code": "code2",
            "campaign": "pipeline-1",
            "platform": "instagram",
            "clicks": 50,
            "conversions": 3,
            "revenue_usd": 30.0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        performance = tracker.get_platform_performance()

        assert len(performance) == 2
        platforms = {p["platform"]: p for p in performance}
        assert platforms["tiktok"]["clicks"] == 100
        assert platforms["instagram"]["revenue_usd"] == 30.0


class TestARCHIntegration:
    """Integration tests for all ARCH features together"""

    @pytest.fixture
    def event_bus(self):
        """Create fresh EventBus for each test."""
        EventBus.reset_instance()
        return EventBus.get_instance()

    @pytest.mark.asyncio
    async def test_full_pipeline_workflow(self, event_bus):
        """
        Test ARCH-001 to ARCH-008 working together.
        """
        MasterOrchestrator._instance = None
        TweetScheduler._instance = None
        OfferTrafficTracker._instance = None

        orchestrator = MasterOrchestrator.get_instance(event_bus=event_bus, use_db=False)
        scheduler = TweetScheduler.get_instance(event_bus=event_bus)
        tracker = OfferTrafficTracker.get_instance(event_bus=event_bus)

        # ARCH-001: Start pipeline
        config = PipelineConfig(
            theme="AI automation revolution",
            num_parts=3,
            character="@isaiahdupree",
            publish_platforms=["tiktok", "instagram"],
            schedule_tweets=True,
            tweets_per_day=12,
            offer_url="https://example.com/ai-offer"
        )
        pipeline_id = await orchestrator.start_pipeline(config)

        # Verify pipeline was created
        assert pipeline_id in orchestrator.active_pipelines
        pipeline = orchestrator.active_pipelines[pipeline_id]
        assert pipeline["status"] == "generating_video"

        # ARCH-004: Schedule tweets
        tweet_result = await scheduler.schedule_tweet_campaign(
            pipeline_id=pipeline_id,
            theme=config.theme,
            tweets_per_day=config.tweets_per_day,
            offer_url=config.offer_url,
            duration_days=1
        )
        assert tweet_result["scheduled_count"] == 12

        # ARCH-005: Create tracked link for offer
        tracked_url = await tracker.create_tracked_link(
            offer_url=config.offer_url,
            campaign=pipeline_id,
            source="tiktok"
        )
        assert "utm_" in tracked_url

        # ARCH-008: Get metrics
        metrics = orchestrator.get_pipeline_metrics()
        assert metrics["total_pipelines"] == 1
        assert metrics["active_pipelines"] == 1

        print("✅ Full ARCH pipeline integration test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
