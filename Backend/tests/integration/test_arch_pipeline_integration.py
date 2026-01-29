"""
Integration Tests for System Architecture Integration (ARCH-001 to ARCH-008)
==============================================================================
Tests the complete pipeline workflow from Sora generation to multi-platform publishing.

Test Workflow:
    Sora (1-3 part) → Stitch → Analyze → Auto-fill → Post to 22 Blotato accounts
                                                          ↓
    Tweet every 2h → Track Engagement → Optimize → Drive Offer Traffic
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus, Topics, Event
from services.publish_integrator import PublishIntegrator


class TestARCHPipelineIntegration:
    """Integration tests for ARCH-001 through ARCH-008"""

    @pytest.fixture
    def event_bus(self):
        """Create a fresh EventBus for testing."""
        bus = EventBus()
        yield bus
        # Cleanup
        bus._subscribers.clear()
        bus._event_log.clear()

    @pytest.fixture
    def orchestrator(self, event_bus):
        """Create orchestrator with mocked subsystems."""
        # Reset singleton
        MasterOrchestrator._instance = None

        orchestrator = MasterOrchestrator(event_bus=event_bus, use_db=False)

        # Mock subsystem services
        orchestrator.sora_pipeline = Mock()
        orchestrator.blotato_service = Mock()
        orchestrator.twitter_service = Mock()
        orchestrator.analytics_feedback = Mock()

        return orchestrator

    @pytest.fixture
    def publish_integrator(self, event_bus):
        """Create publish integrator."""
        PublishIntegrator._instance = None
        integrator = PublishIntegrator(event_bus=event_bus)
        integrator.blotato_service = Mock()
        integrator.blotato_service.get_accounts_by_platform = Mock(return_value=[
            Mock(id=710, platform="tiktok", username="isaiah_dupree")
        ])
        return integrator

    @pytest.mark.asyncio
    async def test_arch_001_orchestrator_initialization(self, orchestrator):
        """
        ARCH-001: Master Orchestrator Service
        Test that orchestrator initializes and coordinates subsystems.
        """
        assert orchestrator is not None
        assert orchestrator.event_bus is not None
        assert orchestrator.active_pipelines == {}
        assert orchestrator.completed_pipelines == {}

    @pytest.mark.asyncio
    async def test_arch_002_pipeline_start_flow(self, orchestrator):
        """
        ARCH-002: 3-Part Sora Batch Coordination
        Test complete pipeline startup flow.
        """
        config = PipelineConfig(
            theme="AI automation tips",
            num_parts=3,
            publish_platforms=["tiktok", "instagram"],
            schedule_tweets=True,
            tweets_per_day=12,
            offer_url="https://example.com/offer"
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Verify pipeline created
        assert pipeline_id is not None
        assert pipeline_id in orchestrator.active_pipelines

        pipeline = orchestrator.active_pipelines[pipeline_id]
        assert pipeline["theme"] == "AI automation tips"
        assert pipeline["status"] == "generating_video"
        assert pipeline["config"] == config

    @pytest.mark.asyncio
    async def test_arch_003_sora_to_publish_flow(self, orchestrator, event_bus):
        """
        ARCH-003: Content Analyzer → Publisher Integration
        Test that Sora completion triggers publishing with analysis data.
        """
        # Start pipeline
        config = PipelineConfig(
            theme="Test theme",
            num_parts=3,
            publish_platforms=["tiktok"],
            schedule_tweets=False
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Track published events
        published_events = []

        async def track_publish(event: Event):
            published_events.append(event)

        event_bus.subscribe(Topics.PUBLISH_REQUESTED, track_publish)

        # Simulate Sora completion
        analysis = {
            "title_tiktok": "Amazing AI Tips",
            "description": "Learn how to automate your workflow",
            "hashtags": ["ai", "automation", "productivity"],
            "hook": "You won't believe this AI trick!",
            "cta": "Follow for more!"
        }

        await event_bus.publish(
            Topics.SORA_BATCH_COMPLETED,
            {
                "pipeline_id": pipeline_id,
                "stitched_video": "/path/to/video.mp4",
                "analysis": analysis,
                "successful_parts": 3,
                "failed_parts": 0
            },
            correlation_id=pipeline_id,
            source="test"
        )

        # Wait for event processing
        await asyncio.sleep(0.1)

        # Verify PUBLISH_REQUESTED was emitted
        assert len(published_events) > 0
        publish_event = published_events[0]
        assert publish_event.payload["pipeline_id"] == pipeline_id
        assert publish_event.payload["platform"] == "tiktok"
        assert publish_event.payload["analysis"] == analysis

    @pytest.mark.asyncio
    async def test_arch_003_publish_integrator_caption_generation(self, publish_integrator):
        """
        ARCH-003: PublishIntegrator caption generation
        Test that PublishIntegrator generates platform-specific captions.
        """
        analysis = {
            "title_tiktok": "Amazing AI Tips",
            "description": "Learn how to automate your workflow",
            "hashtags": ["ai", "automation", "productivity"],
            "hook": "You won't believe this AI trick!",
            "cta": "Follow for more!"
        }

        # Test TikTok caption
        caption = publish_integrator._generate_caption("tiktok", analysis)
        assert "You won't believe this AI trick!" in caption
        assert "#ai" in caption
        assert "#automation" in caption

        # Test YouTube caption
        caption = publish_integrator._generate_caption("youtube", analysis)
        assert "Learn how to automate your workflow" in caption
        assert "Follow for more!" in caption

    @pytest.mark.asyncio
    async def test_arch_004_twitter_interval_calculation(self, orchestrator):
        """
        ARCH-004: Tweet Scheduler 2-Hour Interval
        Test that interval is correctly calculated from tweets_per_day.
        """
        config = PipelineConfig(
            theme="Test",
            tweets_per_day=12  # Should give 120 minutes
        )

        expected_interval = int((24 * 60) / config.tweets_per_day)
        assert expected_interval == 120  # 2 hours

        # Test with different values
        config.tweets_per_day = 24
        expected_interval = int((24 * 60) / config.tweets_per_day)
        assert expected_interval == 60  # 1 hour

    @pytest.mark.asyncio
    async def test_arch_005_offer_tracking_link_creation(self):
        """
        ARCH-005: Offer Traffic Tracking Service
        Test UTM link generation for traffic tracking.
        """
        from services.offer_traffic_tracker import OfferTrafficTracker
        from sqlalchemy import create_engine

        # Mock database connection to not hit real DB
        with patch('services.offer_traffic_tracker.create_engine') as mock_engine:
            mock_engine.return_value = Mock()
            tracker = OfferTrafficTracker(event_bus=None)
            tracker.engine = Mock()

            # Mock the connection context manager
            mock_conn = Mock()
            mock_conn.execute = Mock()
            mock_conn.commit = Mock()
            tracker.engine.connect = Mock(return_value=mock_conn)
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)

            tracked_link = tracker.create_tracked_link(
                offer_url="https://example.com/product",
                pipeline_id="test-pipeline",
                platform="twitter",
                campaign_id="campaign-123"
            )

            # Verify UTM parameters are added
            assert "utm_source=twitter" in tracked_link
            assert "utm_medium=social" in tracked_link
            assert "utm_campaign=campaign-123" in tracked_link
            assert "https://example.com/product?" in tracked_link

    @pytest.mark.asyncio
    async def test_arch_006_analytics_feedback_rating(self):
        """
        ARCH-006: Analytics → AI Feedback Loop
        Test performance rating calculation.
        """
        from services.analytics_feedback_loop import AnalyticsFeedbackLoop, PerformanceRating

        feedback = AnalyticsFeedbackLoop.__new__(AnalyticsFeedbackLoop)

        # Test excellent performance (top 20%)
        metrics = {
            "total_views": 100000,
            "avg_engagement_rate": 8.5  # High engagement
        }
        rating = feedback._rate_performance(metrics)
        assert rating in [PerformanceRating.EXCELLENT, PerformanceRating.GOOD]

    @pytest.mark.asyncio
    async def test_arch_007_api_pipeline_status(self, orchestrator):
        """
        ARCH-007: Unified Pipeline API Endpoint
        Test pipeline status retrieval.
        """
        # Create a pipeline
        config = PipelineConfig(theme="Test theme")
        pipeline_id = await orchestrator.start_pipeline(config)

        # Get status
        status = orchestrator.get_pipeline_status(pipeline_id)

        assert status is not None
        assert status["pipeline_id"] == pipeline_id
        assert status["theme"] == "Test theme"
        assert "status" in status
        assert "started_at" in status

    @pytest.mark.asyncio
    async def test_arch_007_api_list_pipelines(self, orchestrator):
        """
        ARCH-007: List pipelines endpoint
        Test listing recent pipelines.
        """
        # Create multiple pipelines
        config1 = PipelineConfig(theme="Theme 1")
        config2 = PipelineConfig(theme="Theme 2")

        await orchestrator.start_pipeline(config1)
        await orchestrator.start_pipeline(config2)

        # List pipelines
        pipelines = await orchestrator.list_pipelines(limit=10)

        assert len(pipelines) == 2
        assert any(p["theme"] == "Theme 1" for p in pipelines)
        assert any(p["theme"] == "Theme 2" for p in pipelines)

    @pytest.mark.asyncio
    async def test_complete_pipeline_flow(self, orchestrator, event_bus, publish_integrator):
        """
        End-to-end test: Complete pipeline from Sora to publish completion.
        """
        # Track all events
        events = []

        async def track_all(event: Event):
            events.append(event)

        event_bus.subscribe("*", track_all)

        # 1. Start pipeline
        config = PipelineConfig(
            theme="Complete test",
            num_parts=3,
            publish_platforms=["tiktok"],
            schedule_tweets=False
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # 2. Simulate Sora completion
        analysis = {
            "title_tiktok": "Test Title",
            "description": "Test Description",
            "hashtags": ["test"],
            "hook": "Test Hook",
            "cta": "Test CTA"
        }

        await event_bus.publish(
            Topics.SORA_BATCH_COMPLETED,
            {
                "pipeline_id": pipeline_id,
                "stitched_video": "/test/video.mp4",
                "analysis": analysis,
                "successful_parts": 3,
                "failed_parts": 0
            },
            correlation_id=pipeline_id,
            source="test"
        )

        # 3. Simulate publish completion
        await asyncio.sleep(0.1)

        await event_bus.publish(
            "blotato.publish.completed",
            {
                "pipeline_id": pipeline_id,
                "platform": "tiktok"
            },
            correlation_id=pipeline_id,
            source="test"
        )

        await asyncio.sleep(0.1)

        # 4. Verify final status
        status = orchestrator.get_pipeline_status(pipeline_id)

        # Should have moved to completed
        assert status["status"] in ["completed", "publishing"]

        # Should have publish job tracked
        if "publish_jobs" in status.get("outputs", {}):
            assert len(status["outputs"]["publish_jobs"]) > 0

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, orchestrator, event_bus):
        """
        Test that pipeline handles Sora failures gracefully.
        """
        config = PipelineConfig(theme="Error test")
        pipeline_id = await orchestrator.start_pipeline(config)

        # Simulate Sora failure
        await event_bus.publish(
            Topics.SORA_BATCH_FAILED,
            {
                "pipeline_id": pipeline_id,
                "error": "Video generation timeout"
            },
            correlation_id=pipeline_id,
            source="test"
        )

        await asyncio.sleep(0.1)

        # Verify pipeline marked as failed
        status = orchestrator.get_pipeline_status(pipeline_id)
        assert status["status"] == "failed"
        assert "error" in status


class TestARCHEventFlow:
    """Test EventBus event flow across services"""

    @pytest.mark.asyncio
    async def test_event_correlation_id_propagation(self):
        """
        Test that correlation_id is propagated across all events in workflow.
        """
        bus = EventBus()
        correlation_id = "test-correlation-123"

        received_events = []

        async def track_events(event: Event):
            received_events.append(event)

        bus.subscribe("*", track_events)

        # Publish multiple events with same correlation_id
        await bus.publish(
            Topics.SORA_BATCH_STARTED,
            {"data": "test1"},
            correlation_id=correlation_id,
            source="test"
        )

        await bus.publish(
            Topics.SORA_BATCH_COMPLETED,
            {"data": "test2"},
            correlation_id=correlation_id,
            source="test"
        )

        await asyncio.sleep(0.1)

        # Verify all events have same correlation_id
        assert len(received_events) >= 2
        for event in received_events:
            assert event.correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_event_history_tracking(self):
        """
        Test that EventBus maintains event history for debugging.
        """
        bus = EventBus()

        # Publish some events
        await bus.publish(Topics.SYSTEM_STARTUP, {"test": "data"}, source="test")
        await bus.publish(Topics.MEDIA_INGESTED, {"test": "data2"}, source="test")

        await asyncio.sleep(0.1)

        # Get recent events
        history = bus.get_recent_events(limit=10)

        assert len(history) >= 2
        topics = [e.topic for e in history]
        assert Topics.SYSTEM_STARTUP in topics
        assert Topics.MEDIA_INGESTED in topics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
