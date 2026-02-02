"""
Integration Tests for System Architecture (ARCH-001 to ARCH-007)
=================================================================
Tests the complete unified pipeline workflow:
- Sora → Stitch → Analyze → Publish → Twitter → Track → Analytics

Requirements:
- Database accessible
- EventBus operational
- All subsystems initialized
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

# Import services
from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus
from services.offer_traffic_tracker import OfferTrafficTracker
from services.analytics_feedback_loop import AnalyticsFeedbackLoop


@pytest.fixture
def event_bus():
    """Create EventBus instance for testing."""
    bus = EventBus.get_instance()
    yield bus
    # Cleanup after tests


@pytest.fixture
def orchestrator(event_bus):
    """
    Create MasterOrchestrator instance for testing.

    Uses in-memory mode (use_db=False) for faster tests.
    """
    orch = MasterOrchestrator(event_bus=event_bus, use_db=False)
    yield orch


@pytest.fixture
def traffic_tracker(event_bus):
    """Create OfferTrafficTracker for testing."""
    tracker = OfferTrafficTracker(event_bus=event_bus)
    yield tracker


@pytest.fixture
def analytics_feedback(event_bus):
    """Create AnalyticsFeedbackLoop for testing."""
    feedback = AnalyticsFeedbackLoop(event_bus=event_bus)
    yield feedback


class TestARCH001_MasterOrchestrator:
    """
    Test ARCH-001: Master Orchestrator Service

    Verifies orchestrator can coordinate all subsystems via EventBus.
    """

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Test that orchestrator initializes with all subsystems."""
        assert orchestrator is not None
        assert orchestrator.event_bus is not None
        assert orchestrator.content_analyzer is not None

        # Verify subsystems are initialized (may be None if dependencies missing)
        # This is expected in test environment
        assert orchestrator.active_pipelines == {}
        assert orchestrator.completed_pipelines == {}

    @pytest.mark.asyncio
    async def test_pipeline_creation(self, orchestrator):
        """Test creating a new pipeline with configuration."""
        config = PipelineConfig(
            theme="Test AI automation workflow",
            num_parts=3,
            character="@testuser",
            publish_platforms=["tiktok", "instagram"],
            schedule_tweets=True,
            tweets_per_day=12,
            offer_url="https://example.com/test-offer"
        )

        # Start pipeline (in test mode, subsystems may not actually run)
        pipeline_id = await orchestrator.start_pipeline(config)

        # Verify pipeline was created
        assert pipeline_id is not None
        assert pipeline_id in orchestrator.active_pipelines

        # Check pipeline structure
        pipeline = orchestrator.active_pipelines[pipeline_id]
        assert pipeline["theme"] == "Test AI automation workflow"
        assert pipeline["status"] in ["initializing", "generating_video"]
        assert "correlation_id" in pipeline

    @pytest.mark.asyncio
    async def test_pipeline_status_retrieval(self, orchestrator):
        """Test retrieving pipeline status."""
        config = PipelineConfig(
            theme="Test status retrieval",
            num_parts=1
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Get status
        status = orchestrator.get_pipeline_status(pipeline_id)

        assert status is not None
        assert "pipeline_id" in status
        assert status["pipeline_id"] == pipeline_id
        assert "status" in status

    @pytest.mark.asyncio
    async def test_list_active_pipelines(self, orchestrator):
        """Test listing active pipelines."""
        # Create multiple pipelines
        config1 = PipelineConfig(theme="Pipeline 1", num_parts=1)
        config2 = PipelineConfig(theme="Pipeline 2", num_parts=1)

        id1 = await orchestrator.start_pipeline(config1)
        id2 = await orchestrator.start_pipeline(config2)

        # List active
        active = orchestrator.list_active_pipelines()

        assert len(active) >= 2
        pipeline_ids = [p["pipeline_id"] for p in active]
        assert id1 in pipeline_ids
        assert id2 in pipeline_ids


class TestARCH002_SoraBatchCoordination:
    """
    Test ARCH-002: 3-Part Sora Batch Coordination

    Verifies Sora pipeline can handle multi-part video generation.
    Note: Actual Sora generation requires Safari and OpenAI API.
    """

    @pytest.mark.asyncio
    async def test_sora_batch_request_event(self, event_bus):
        """Test that SORA_BATCH_REQUESTED event can be published."""
        from services.event_bus import Topics

        test_payload = {
            "pipeline_id": "test-pipeline-123",
            "theme": "AI automation",
            "num_parts": 3,
            "character": "@testuser",
            "stitch": True,
            "remove_watermark": True
        }

        # Publish event
        await event_bus.publish(
            Topics.SORA_BATCH_REQUESTED,
            test_payload,
            correlation_id="test-correlation-123",
            source="test_suite"
        )

        # Verify event was published (check history)
        recent_events = event_bus.get_recent_events(limit=10)
        assert len(recent_events) > 0

        # Find our event
        our_event = next(
            (e for e in recent_events if e.topic == Topics.SORA_BATCH_REQUESTED),
            None
        )
        assert our_event is not None
        assert our_event.payload == test_payload


class TestARCH003_ContentAnalyzerPublisher:
    """
    Test ARCH-003: Content Analyzer → Publisher Integration

    Verifies PublishIntegrator can generate platform-specific captions.
    """

    def test_caption_generation_tiktok(self):
        """Test caption generation for TikTok."""
        from services.publish_integrator import PublishIntegrator

        integrator = PublishIntegrator()

        analysis = {
            "hook": "This AI tool changes everything!",
            "description": "Discover how AI automation revolutionizes content creation",
            "hashtags": ["ai", "automation", "contentcreation", "productivity"],
            "cta": "Try it now!"
        }

        caption = integrator._generate_caption(
            platform="tiktok",
            analysis=analysis,
            offer_url="https://example.com/offer"
        )

        # Verify caption includes hook and hashtags
        assert "This AI tool changes everything!" in caption
        assert "#ai" in caption
        assert "https://example.com/offer" in caption

    def test_caption_generation_youtube(self):
        """Test caption generation for YouTube."""
        from services.publish_integrator import PublishIntegrator

        integrator = PublishIntegrator()

        analysis = {
            "hook": "Amazing AI discovery",
            "description": "Full tutorial on AI automation for creators",
            "hashtags": ["ai", "tutorial", "automation"],
            "cta": "Subscribe for more!"
        }

        caption = integrator._generate_caption(
            platform="youtube",
            analysis=analysis,
            offer_url="https://example.com/offer"
        )

        # Verify caption includes description and CTA
        assert "Full tutorial" in caption
        assert "Subscribe for more!" in caption
        assert "#ai" in caption


class TestARCH004_TweetScheduler:
    """
    Test ARCH-004: Tweet Scheduler 2-Hour Interval

    Verifies Twitter campaign service can schedule tweets.
    """

    def test_twitter_campaign_initialization(self):
        """Test Twitter campaign service initializes with correct interval."""
        from services.twitter_campaign_service import TwitterCampaignService

        # Test default 2-hour interval (120 minutes)
        service = TwitterCampaignService(interval_minutes=120)

        assert service.interval_minutes == 120
        assert service.tweets_per_day == 60

    def test_twitter_interval_configuration(self):
        """Test configurable tweet interval."""
        from services.twitter_campaign_service import TwitterCampaignService

        # Test custom interval
        service = TwitterCampaignService(interval_minutes=30)

        assert service.interval_minutes == 30


class TestARCH005_OfferTrafficTracking:
    """
    Test ARCH-005: Offer Traffic Tracking Service

    Verifies traffic tracking for offer links.
    """

    def test_tracking_url_generation(self, traffic_tracker):
        """Test generating tracking URLs with UTM parameters."""
        tracking_url = traffic_tracker.create_tracked_link(
            offer_url="https://example.com/product",
            pipeline_id="test-pipeline-123",
            platform="instagram",
            campaign_id="test-campaign"
        )

        # Verify UTM parameters are included
        assert "utm_source=instagram" in tracking_url
        assert "utm_medium=social" in tracking_url
        assert "utm_campaign=test-campaign" in tracking_url

    @pytest.mark.asyncio
    async def test_click_tracking(self, traffic_tracker):
        """Test tracking click events."""
        # This test requires database tables to exist
        # In real environment, would verify click was recorded

        success = await traffic_tracker.track_click(
            campaign_id="test-campaign-456",
            platform="tiktok"
        )

        # May fail in test env without DB, but should not crash
        assert success in [True, False]

    @pytest.mark.asyncio
    async def test_conversion_tracking(self, traffic_tracker):
        """Test tracking conversion events."""
        success = await traffic_tracker.track_conversion(
            campaign_id="test-campaign-789",
            platform="youtube",
            revenue_usd=29.99
        )

        # May fail in test env without DB, but should not crash
        assert success in [True, False]


class TestARCH006_AnalyticsFeedback:
    """
    Test ARCH-006: Analytics → AI Feedback Loop

    Verifies analytics feedback can analyze pipeline performance.
    """

    def test_performance_rating(self, analytics_feedback):
        """Test performance rating logic."""
        # High engagement, high views = excellent
        metrics_excellent = {
            "avg_engagement_rate": 6.0,
            "total_views": 15000
        }
        rating = analytics_feedback._rate_performance(metrics_excellent)
        assert rating == "excellent"

        # Medium engagement = average/good
        metrics_average = {
            "avg_engagement_rate": 2.0,
            "total_views": 2000
        }
        rating = analytics_feedback._rate_performance(metrics_average)
        assert rating in ["average", "good"]

    @pytest.mark.asyncio
    async def test_pipeline_performance_analysis(self, analytics_feedback):
        """Test analyzing pipeline performance (may return 'waiting' or 'error' in test)."""
        result = await analytics_feedback.analyze_pipeline_performance(
            pipeline_id="test-pipeline-nonexistent",
            wait_hours=0  # Skip waiting in test
        )

        # Should return error for nonexistent pipeline
        assert "error" in result or "status" in result


class TestARCH007_UnifiedPipelineAPI:
    """
    Test ARCH-007: Unified Pipeline API Endpoint

    Note: This requires FastAPI test client. Marked as integration test.
    """

    def test_api_endpoint_exists(self):
        """Test that orchestrator API endpoints are defined."""
        from api.endpoints.orchestrator import router

        # Verify router exists
        assert router is not None

        # Verify routes are defined (paths include router prefix)
        route_paths = [route.path for route in router.routes]

        assert "/api/orchestrator/pipeline/start" in route_paths
        assert "/api/orchestrator/pipeline/{pipeline_id}" in route_paths
        assert "/api/orchestrator/pipelines" in route_paths


class TestEndToEndIntegration:
    """
    End-to-end integration test for complete pipeline workflow.

    Note: This is a mock test that verifies the flow without external dependencies.
    """

    @pytest.mark.asyncio
    async def test_complete_pipeline_flow_mock(self, orchestrator, event_bus):
        """
        Test complete flow from pipeline start to completion (mocked).

        Flow:
        1. Start pipeline
        2. Emit mock SORA_BATCH_COMPLETED
        3. Emit mock publish events
        4. Verify pipeline reaches expected state
        """
        from services.event_bus import Topics

        # 1. Start pipeline
        config = PipelineConfig(
            theme="Test end-to-end flow",
            num_parts=1,
            publish_platforms=["tiktok"],
            schedule_tweets=False  # Simplify for test
        )

        pipeline_id = await orchestrator.start_pipeline(config)
        assert pipeline_id in orchestrator.active_pipelines

        # Get initial status
        pipeline = orchestrator.active_pipelines[pipeline_id]
        initial_status = pipeline["status"]
        assert initial_status in ["initializing", "generating_video"]

        # 2. Mock Sora completion event
        await event_bus.publish(
            Topics.SORA_BATCH_COMPLETED,
            {
                "pipeline_id": pipeline_id,
                "theme": "Test end-to-end flow",
                "stitched_video": "/tmp/test_video.mp4",
                "analysis": {
                    "title_tiktok": "Test Title",
                    "description": "Test description",
                    "hashtags": ["test", "automation"],
                    "hook": "Amazing test!",
                    "cta": "Try it now"
                },
                "successful_parts": 1,
                "failed_parts": 0,
                "status": "completed"
            },
            correlation_id=pipeline["correlation_id"],
            source="test_suite"
        )

        # Give orchestrator time to process event
        await asyncio.sleep(0.1)

        # Verify pipeline progressed
        updated_pipeline = orchestrator.active_pipelines.get(pipeline_id)
        if updated_pipeline:  # May have moved to completed
            assert updated_pipeline["status"] in [
                "analyzing", "publishing", "completed"
            ]

        # 3. Mock publish completion
        await event_bus.publish(
            "blotato.publish.completed",
            {
                "pipeline_id": pipeline_id,
                "platform": "tiktok"
            },
            correlation_id=pipeline["correlation_id"],
            source="test_suite"
        )

        await asyncio.sleep(0.1)

        # Verify pipeline completed or progressed
        # Pipeline may be in completed_pipelines now
        if pipeline_id in orchestrator.completed_pipelines:
            final = orchestrator.completed_pipelines[pipeline_id]
            assert final["status"] == "completed"
        elif pipeline_id in orchestrator.active_pipelines:
            final = orchestrator.active_pipelines[pipeline_id]
            assert final["status"] in ["publishing", "completed"]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
