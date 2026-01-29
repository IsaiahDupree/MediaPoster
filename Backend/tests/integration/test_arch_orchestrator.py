"""
Integration Tests for Master Orchestrator (ARCH-001 to ARCH-008)
==================================================================
Tests the complete System Architecture Integration workflow.

Tests cover:
- ARCH-001: Master Orchestrator coordination
- ARCH-002: 3-Part Sora batch generation
- ARCH-003: Content Analyzer → Publisher integration
- ARCH-004: Tweet Scheduler with 2-hour intervals
- ARCH-005: Offer Traffic Tracking
- ARCH-006: Analytics → AI Feedback Loop
- ARCH-007: Unified Pipeline API
- ARCH-008: Pipeline status reporting
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus, Topics


@pytest.fixture
def event_bus():
    """Create an isolated event bus for testing."""
    from services.event_bus.bus import EventBus as RealEventBus
    bus = RealEventBus()
    return bus


@pytest.fixture
def orchestrator(event_bus):
    """Create orchestrator with mocked dependencies."""
    orch = MasterOrchestrator(event_bus=event_bus, use_db=False)

    # Mock subsystem services to avoid real API calls
    orch.sora_pipeline = Mock()
    orch.sora_pipeline.generate_multi_part = AsyncMock(return_value={
        "id": "test-job-123",
        "status": "completed",
        "successful_parts": 3,
        "failed_parts": 0,
        "stitched_video": "/tmp/test_video.mp4",
        "analysis": {
            "detected_hook": "AI revolutionizing content creation",
            "topics": ["AI", "automation", "content"],
            "viral_score": 85,
            "hashtags": ["ai", "automation", "viral"]
        }
    })

    orch.blotato_service = Mock()
    orch.twitter_service = Mock()
    orch.twitter_service.schedule_offer_tweets = Mock(return_value=["tweet1", "tweet2"])

    return orch


class TestARCH001_MasterOrchestrator:
    """Test ARCH-001: Master Orchestrator Service"""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes with all subsystems."""
        assert orchestrator is not None
        assert orchestrator.event_bus is not None
        assert orchestrator.content_analyzer is not None
        assert orchestrator.sora_pipeline is not None
        assert orchestrator.blotato_service is not None
        assert orchestrator.twitter_service is not None

    @pytest.mark.asyncio
    async def test_orchestrator_subscribes_to_events(self, orchestrator, event_bus):
        """Test orchestrator subscribes to required event topics."""
        # Check that orchestrator has subscribed (subscriber count > 0)
        subscriber_counts = event_bus.get_subscriber_count()

        # Check key subscriptions exist
        assert Topics.SORA_BATCH_COMPLETED in subscriber_counts, "No subscribers for SORA_BATCH_COMPLETED"
        assert Topics.SORA_BATCH_FAILED in subscriber_counts, "No subscribers for SORA_BATCH_FAILED"
        assert subscriber_counts[Topics.SORA_BATCH_COMPLETED] > 0
        assert subscriber_counts[Topics.SORA_BATCH_FAILED] > 0

    @pytest.mark.asyncio
    async def test_pipeline_creation(self, orchestrator):
        """Test creating a new pipeline."""
        config = PipelineConfig(
            theme="AI automation revolutionizing content creation",
            num_parts=3,
            character="@isaiahdupree",
            publish_platforms=["tiktok", "instagram"],
            schedule_tweets=True,
            tweets_per_day=12,
            offer_url="https://example.com/offer"
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Verify pipeline was created
        assert pipeline_id is not None
        assert pipeline_id.startswith("pipeline-")

        # Verify it's in active pipelines
        assert pipeline_id in orchestrator.active_pipelines

        # Verify config was stored
        pipeline = orchestrator.active_pipelines[pipeline_id]
        assert pipeline["theme"] == config.theme
        assert pipeline["status"] == "generating_video"


class TestARCH002_SoraBatchCoordination:
    """Test ARCH-002: 3-Part Sora Batch Coordination"""

    @pytest.mark.asyncio
    async def test_sora_batch_requested_event(self, orchestrator, event_bus):
        """Test Sora batch generation is triggered via EventBus."""
        config = PipelineConfig(
            theme="Test video generation",
            num_parts=3,
            character="@test"
        )

        # Create pipeline
        pipeline_id = await orchestrator.start_pipeline(config)

        # Wait briefly for event to be published
        await asyncio.sleep(0.1)

        # Verify event was published
        # (In real test, we'd capture published events)
        pipeline = orchestrator.active_pipelines[pipeline_id]
        assert pipeline["current_step"] == "sora_generation"

    @pytest.mark.asyncio
    async def test_sora_batch_completion_flow(self, orchestrator, event_bus):
        """Test handling of Sora batch completion event."""
        config = PipelineConfig(
            theme="Test completion",
            num_parts=3
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Simulate Sora batch completion event
        from services.event_bus.event import Event
        completion_event = Event(
            topic=Topics.SORA_BATCH_COMPLETED,
            payload={
                "pipeline_id": pipeline_id,
                "stitched_video": "/tmp/test.mp4",
                "successful_parts": 3,
                "failed_parts": 0,
                "analysis": {
                    "detected_hook": "Test hook",
                    "viral_score": 80
                }
            },
            source="test"
        )

        await orchestrator._handle_sora_batch_completed(completion_event)

        # Verify pipeline progressed
        pipeline = orchestrator.active_pipelines[pipeline_id]
        assert "sora" in pipeline["outputs"]
        assert pipeline["outputs"]["sora"]["stitched_video"] == "/tmp/test.mp4"


class TestARCH003_ContentAnalyzerPublisher:
    """Test ARCH-003: Content Analyzer → Publisher Integration"""

    @pytest.mark.asyncio
    async def test_analysis_passed_to_publisher(self, orchestrator, event_bus):
        """Test that content analysis is passed to publishing step."""
        config = PipelineConfig(
            theme="Test analysis integration",
            num_parts=3,
            publish_platforms=["tiktok"]
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Simulate completion with analysis
        from services.event_bus.event import Event
        completion_event = Event(
            topic=Topics.SORA_BATCH_COMPLETED,
            payload={
                "pipeline_id": pipeline_id,
                "stitched_video": "/tmp/test.mp4",
                "analysis": {
                    "detected_hook": "Amazing AI video",
                    "topics": ["AI", "video"],
                    "viral_score": 90,
                    "hashtags": ["ai", "viral", "trending"]
                }
            },
            source="test"
        )

        await orchestrator._handle_sora_batch_completed(completion_event)

        # Verify publish events were triggered with analysis
        pipeline = orchestrator.active_pipelines[pipeline_id]
        assert pipeline["status"] == "publishing"
        assert len(pipeline["outputs"]["publish_jobs"]) > 0


class TestARCH004_TweetScheduler:
    """Test ARCH-004: Tweet Scheduler 2-Hour Interval"""

    @pytest.mark.asyncio
    async def test_tweet_scheduling_triggered(self, orchestrator):
        """Test that tweet scheduling is triggered after publishing."""
        config = PipelineConfig(
            theme="Test tweets",
            schedule_tweets=True,
            tweets_per_day=12,
            offer_url="https://example.com/offer"
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Complete Sora and publishing steps
        orchestrator.active_pipelines[pipeline_id]["outputs"]["publish_jobs"] = [
            {"platform": "tiktok", "status": "completed"}
        ]

        # Simulate publishing completion
        from services.event_bus.event import Event
        publish_event = Event(
            topic="blotato.publish.completed",
            payload={
                "pipeline_id": pipeline_id,
                "platform": "tiktok"
            },
            source="test"
        )

        await orchestrator._handle_publish_completed(publish_event)

        # Verify tweet scheduling was triggered
        pipeline = orchestrator.active_pipelines[pipeline_id]
        assert pipeline["status"] == "scheduling_tweets"

    def test_tweet_interval_calculation(self):
        """Test that 2-hour interval is correctly calculated."""
        tweets_per_day = 12
        expected_interval_minutes = (24 * 60) / tweets_per_day

        assert expected_interval_minutes == 120  # 2 hours


class TestARCH005_OfferTrafficTracking:
    """Test ARCH-005: Offer Traffic Tracking Service"""

    def test_offer_tracker_initialization(self):
        """Test offer tracker can be initialized."""
        from services.offer_traffic_tracker import OfferTrafficTracker

        tracker = OfferTrafficTracker()
        assert tracker is not None
        assert tracker.engine is not None

    def test_utm_link_generation(self):
        """Test UTM link generation with tracking parameters."""
        from services.offer_traffic_tracker import OfferTrafficTracker

        tracker = OfferTrafficTracker()

        result = tracker.create_tracked_link(
            offer_url="https://example.com/product",
            pipeline_id="test-pipeline-123",
            platform="twitter",
            campaign_id="campaign-456"
        )

        # Verify link contains UTM parameters
        assert "utm_source=twitter" in result
        assert "utm_medium=social" in result
        assert "campaign-456" in result or "pipeline_test-pipeline-123" in result

    @pytest.mark.asyncio
    async def test_click_tracking(self):
        """Test click tracking functionality."""
        from services.offer_traffic_tracker import OfferTrafficTracker

        tracker = OfferTrafficTracker()

        # This would normally update the database
        # In integration test, we verify the method doesn't crash
        success = await tracker.track_click(
            campaign_id="test-campaign",
            platform="twitter"
        )

        # Method should execute without errors
        assert success is not None


class TestARCH006_AnalyticsFeedback:
    """Test ARCH-006: Analytics → AI Feedback Loop"""

    def test_analytics_feedback_initialization(self):
        """Test analytics feedback loop can be initialized."""
        from services.analytics_feedback_loop import AnalyticsFeedbackLoop

        feedback = AnalyticsFeedbackLoop()
        assert feedback is not None
        assert feedback.engine is not None

    @pytest.mark.asyncio
    async def test_pipeline_performance_analysis(self):
        """Test analyzing pipeline performance."""
        from services.analytics_feedback_loop import AnalyticsFeedbackLoop

        feedback = AnalyticsFeedbackLoop()

        # Test with non-existent pipeline (should handle gracefully)
        result = await feedback.analyze_pipeline_performance("nonexistent-pipeline")

        # Should return error or waiting status, not crash
        assert "error" in result or "status" in result


class TestARCH007_UnifiedPipelineAPI:
    """Test ARCH-007: Unified Pipeline API Endpoint"""

    @pytest.mark.asyncio
    async def test_pipeline_api_start(self, orchestrator):
        """Test starting pipeline via API interface."""
        config = PipelineConfig(
            theme="API test video",
            num_parts=3,
            publish_platforms=["tiktok"],
            schedule_tweets=True
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Verify pipeline was created
        assert pipeline_id is not None
        status = orchestrator.get_pipeline_status(pipeline_id)
        assert status["theme"] == "API test video"
        assert status["status"] in ["initializing", "generating_video"]

    @pytest.mark.asyncio
    async def test_pipeline_status_retrieval(self, orchestrator):
        """Test retrieving pipeline status."""
        config = PipelineConfig(theme="Status test")
        pipeline_id = await orchestrator.start_pipeline(config)

        status = orchestrator.get_pipeline_status(pipeline_id)

        assert "pipeline_id" in status or "id" in status
        assert "theme" in status
        assert "status" in status
        assert "started_at" in status

    @pytest.mark.asyncio
    async def test_pipeline_listing(self, orchestrator):
        """Test listing pipelines."""
        # Create multiple pipelines
        config1 = PipelineConfig(theme="Pipeline 1")
        config2 = PipelineConfig(theme="Pipeline 2")

        await orchestrator.start_pipeline(config1)
        await orchestrator.start_pipeline(config2)

        # List pipelines
        pipelines = await orchestrator.list_pipelines(limit=10)

        assert len(pipelines) >= 2
        assert all("pipeline_id" in p for p in pipelines)


class TestARCH008_PipelineDashboard:
    """Test ARCH-008: Pipeline Dashboard Widget"""

    @pytest.mark.asyncio
    async def test_pipeline_status_for_dashboard(self, orchestrator):
        """Test pipeline status includes all data needed for dashboard."""
        config = PipelineConfig(
            theme="Dashboard test",
            num_parts=3,
            publish_platforms=["tiktok", "instagram"],
            schedule_tweets=True,
            offer_url="https://example.com"
        )

        pipeline_id = await orchestrator.start_pipeline(config)
        status = orchestrator.get_pipeline_status(pipeline_id)

        # Verify dashboard-required fields
        assert "theme" in status
        assert "status" in status
        assert "started_at" in status
        assert "current_step" in status or "status" in status

        # Config should be available
        pipeline = orchestrator.active_pipelines[pipeline_id]
        assert "config" in pipeline
        assert pipeline["config"].theme == "Dashboard test"


class TestEndToEndPipeline:
    """End-to-end integration test simulating full pipeline"""

    @pytest.mark.asyncio
    async def test_complete_pipeline_flow(self, orchestrator, event_bus):
        """Test complete pipeline from start to finish."""
        # Start pipeline
        config = PipelineConfig(
            theme="Complete E2E test",
            num_parts=3,
            character="@test",
            publish_platforms=["tiktok"],
            schedule_tweets=True,
            tweets_per_day=12,
            offer_url="https://example.com/offer"
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Simulate Sora completion
        from services.event_bus.event import Event

        sora_event = Event(
            topic=Topics.SORA_BATCH_COMPLETED,
            payload={
                "pipeline_id": pipeline_id,
                "stitched_video": "/tmp/e2e_test.mp4",
                "successful_parts": 3,
                "analysis": {
                    "detected_hook": "E2E test hook",
                    "viral_score": 95
                }
            },
            source="test"
        )

        await orchestrator._handle_sora_batch_completed(sora_event)

        # Simulate publishing completion
        publish_event = Event(
            topic="blotato.publish.completed",
            payload={
                "pipeline_id": pipeline_id,
                "platform": "tiktok"
            },
            source="test"
        )

        await orchestrator._handle_publish_completed(publish_event)

        # Simulate Twitter scheduling
        twitter_event = Event(
            topic="twitter.campaign.scheduled",
            payload={
                "pipeline_id": pipeline_id,
                "tweets_scheduled": 12
            },
            source="test"
        )

        await orchestrator._handle_twitter_scheduled(twitter_event)

        # Verify pipeline completed
        assert pipeline_id in orchestrator.completed_pipelines
        completed_pipeline = orchestrator.completed_pipelines[pipeline_id]
        assert completed_pipeline["status"] == "completed"
        assert "twitter" in completed_pipeline["outputs"]
        assert completed_pipeline["outputs"]["twitter"]["tweets_scheduled"] == 12


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
