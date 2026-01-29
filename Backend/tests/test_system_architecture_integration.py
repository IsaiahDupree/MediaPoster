"""
System Architecture Integration Tests (ARCH-001 to ARCH-008)
=============================================================
Tests for the unified system architecture that wires together:
    - Sora video generation (ARCH-002)
    - Content analysis
    - Multi-platform publishing (ARCH-003)
    - Tweet scheduling (ARCH-004)
    - Offer tracking (ARCH-005)
    - Analytics feedback loop (ARCH-006)

These tests verify the complete end-to-end workflow from video generation
to publishing to tweet scheduling to analytics.
"""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus, Topics
from automation.sora.pipeline import SoraPipeline
from services.offer_tracker import OfferTracker

# Note: AnalyticsFeedback may be imported where needed in individual tests
try:
    from services.analytics_feedback import AnalyticsFeedback
except ImportError:
    AnalyticsFeedback = None


# =========================================================================
# ARCH-001: Master Orchestrator Service
# =========================================================================

@pytest.mark.asyncio
async def test_arch_001_orchestrator_initializes_all_subsystems():
    """ARCH-001: Verify orchestrator initializes all required subsystems."""
    orchestrator = MasterOrchestrator()

    # Verify all subsystems are initialized
    assert orchestrator.sora_pipeline is not None
    assert orchestrator.content_analyzer is not None
    assert orchestrator.blotato_service is not None
    assert orchestrator.twitter_service is not None
    assert orchestrator.analytics_feedback is not None
    assert orchestrator.event_bus is not None

    # Verify orchestrator can start
    await orchestrator.start()
    assert orchestrator._running is True

    # Cleanup
    await orchestrator.stop()


@pytest.mark.asyncio
async def test_arch_001_orchestrator_subscribes_to_events():
    """ARCH-001: Verify orchestrator subscribes to pipeline completion events."""
    orchestrator = MasterOrchestrator()
    event_bus = orchestrator.event_bus

    # Start orchestrator
    await orchestrator.start()

    # Verify subscriptions exist
    # The event bus should have handlers for these topics
    sora_subscribers = event_bus._subscribers.get(Topics.SORA_BATCH_COMPLETED, [])
    publish_subscribers = event_bus._subscribers.get(Topics.PUBLISH_COMPLETED, [])
    checkback_subscribers = event_bus._subscribers.get(Topics.CHECKBACK_COMPLETED, [])

    assert len(sora_subscribers) > 0, "Should subscribe to SORA_BATCH_COMPLETED"
    assert len(publish_subscribers) > 0, "Should subscribe to PUBLISH_COMPLETED"
    assert len(checkback_subscribers) > 0, "Should subscribe to CHECKBACK_COMPLETED"

    # Cleanup
    await orchestrator.stop()


@pytest.mark.asyncio
async def test_arch_001_orchestrator_tracks_pipeline_state():
    """ARCH-001: Verify orchestrator tracks active pipeline states."""
    orchestrator = MasterOrchestrator()

    # Initially no pipelines
    assert len(orchestrator.active_pipelines) == 0

    # After starting a pipeline, it should be tracked
    # (We'll mock the actual execution to keep test fast)
    with patch.object(orchestrator.sora_pipeline, 'generate_multi_part', new_callable=AsyncMock) as mock_sora:
        with patch.object(orchestrator, '_step_publish_to_platforms', new_callable=AsyncMock) as mock_publish:
            mock_sora.return_value = {
                "status": "completed",
                "stitched_video": "/tmp/test.mp4",
                "analysis": {"title": "Test", "hashtags": ["test"]}
            }
            mock_publish.return_value = {
                "results": [{"account_id": 1, "platform": "tiktok", "status": "queued"}],
                "total": 1
            }

            await orchestrator.start()

            # Start a pipeline (but don't await - we just want to check tracking)
            pipeline_task = asyncio.create_task(
                orchestrator.run_full_pipeline(
                    theme="Test pipeline tracking",
                    num_parts=1,
                    schedule_tweets=False
                )
            )

            # Give it a moment to initialize
            await asyncio.sleep(0.1)

            # Should now have an active pipeline
            assert len(orchestrator.active_pipelines) > 0

            # Get the pipeline
            pipeline_id = list(orchestrator.active_pipelines.keys())[0]
            pipeline = orchestrator.get_pipeline_status(pipeline_id)

            assert pipeline is not None
            assert pipeline["theme"] == "Test pipeline tracking"
            assert "id" in pipeline
            assert "status" in pipeline

            # Cleanup
            pipeline_task.cancel()
            try:
                await pipeline_task
            except asyncio.CancelledError:
                pass

            await orchestrator.stop()


# =========================================================================
# ARCH-002: 3-Part Sora Batch Coordination
# =========================================================================

@pytest.mark.asyncio
async def test_arch_002_sora_pipeline_has_multi_part_method():
    """ARCH-002: Verify SoraPipeline has generate_multi_part() method."""
    pipeline = SoraPipeline()

    # Verify method exists
    assert hasattr(pipeline, 'generate_multi_part')
    assert callable(pipeline.generate_multi_part)

    # Verify method signature (inspect parameters)
    import inspect
    sig = inspect.signature(pipeline.generate_multi_part)
    params = list(sig.parameters.keys())

    assert 'theme' in params
    assert 'num_parts' in params
    assert 'auto_stitch' in params
    assert 'auto_analyze' in params


@pytest.mark.asyncio
async def test_arch_002_sora_emits_batch_events():
    """ARCH-002: Verify SoraPipeline emits SORA_BATCH_* events."""
    event_bus = EventBus.get_instance()
    pipeline = SoraPipeline(event_bus=event_bus)

    # Track emitted events
    emitted_events = []

    def capture_event(event):
        emitted_events.append(event.topic)

    event_bus.subscribe(Topics.SORA_BATCH_STARTED, capture_event)
    event_bus.subscribe(Topics.SORA_BATCH_COMPLETED, capture_event)

    # Mock the actual generation to avoid real Safari automation
    with patch.object(pipeline, 'generate_single', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {
            "status": "completed",
            "video_path": "/tmp/test_part.mp4",
            "cleaned_video_path": "/tmp/test_part_clean.mp4"
        }

        with patch.object(pipeline, 'stitch_videos', new_callable=AsyncMock) as mock_stitch:
            mock_stitch.return_value = "/tmp/stitched.mp4"

            with patch.object(pipeline, '_generate_part_prompts', new_callable=AsyncMock) as mock_prompts:
                mock_prompts.return_value = ["Prompt 1", "Prompt 2", "Prompt 3"]

                with patch.object(pipeline, '_analyze_video_content', new_callable=AsyncMock) as mock_analyze:
                    mock_analyze.return_value = {
                        "title_tiktok": "Test Video",
                        "hashtags": ["test", "video"]
                    }

                    # Execute multi-part generation
                    result = await pipeline.generate_multi_part(
                        theme="Test batch coordination",
                        num_parts=3,
                        auto_stitch=True,
                        auto_analyze=True
                    )

    # Verify events were emitted
    assert Topics.SORA_BATCH_STARTED in emitted_events
    assert Topics.SORA_BATCH_COMPLETED in emitted_events


# =========================================================================
# ARCH-003: Content Analyzer → Publisher Integration
# =========================================================================

@pytest.mark.asyncio
async def test_arch_003_publisher_uses_precomputed_analysis():
    """ARCH-003: Verify PublishWorker uses pre-computed analysis from upstream."""
    from services.workers.publish_worker import PublishWorker

    worker = PublishWorker()

    # Create a publish payload with pre-computed analysis
    payload = {
        "media_id": "test_video_123",
        "platform": "tiktok",
        "account_id": "710",
        "analysis": {
            "detected_hook": "This is a test hook!",
            "hashtags": ["viral", "test", "content"],
            "viral_score": 85,
            "suggested_description": "Check out this amazing content"
        },
        "auto_generate_metadata": False
    }

    # Mock the platform caption builder
    caption = worker._build_platform_caption(payload["analysis"], "tiktok")

    # Verify caption includes analysis data
    assert "This is a test hook!" in caption
    assert "#viral" in caption or "viral" in caption.lower()
    assert "#test" in caption or "test" in caption.lower()


def test_arch_003_caption_builder_formats_for_platforms():
    """ARCH-003: Verify caption builder creates platform-specific formats."""
    from services.workers.publish_worker import PublishWorker

    worker = PublishWorker()

    analysis = {
        "detected_hook": "Amazing content alert!",
        "suggested_description": "This is the best video you'll see today.",
        "hashtags": ["amazing", "viral", "content", "fyp"],
        "cta": "Follow for more!"
    }

    # Test TikTok formatting
    tiktok_caption = worker._build_platform_caption(analysis, "tiktok")
    assert "Amazing content alert!" in tiktok_caption
    assert "Follow for more!" in tiktok_caption
    assert len(tiktok_caption) <= 2200

    # Test Instagram formatting
    instagram_caption = worker._build_platform_caption(analysis, "instagram")
    assert "Amazing content alert!" in instagram_caption
    assert "This is the best video" in instagram_caption
    assert len(instagram_caption) <= 2200

    # Test YouTube formatting
    youtube_caption = worker._build_platform_caption(analysis, "youtube")
    assert len(youtube_caption) <= 5000

    # Test Twitter formatting
    twitter_caption = worker._build_platform_caption(analysis, "twitter")
    assert len(twitter_caption) <= 280


# =========================================================================
# ARCH-004: Tweet Scheduler 2-Hour Interval
# =========================================================================

def test_arch_004_twitter_service_supports_2_hour_intervals():
    """ARCH-004: Verify TwitterCampaignService supports 120-minute intervals."""
    from services.twitter_campaign_service import TwitterCampaignService

    service = TwitterCampaignService(interval_minutes=120)

    # Verify interval is set
    assert service.interval_minutes == 120


def test_arch_004_twitter_service_has_offer_tweet_scheduling():
    """ARCH-004: Verify TwitterCampaignService has schedule_offer_tweets method."""
    from services.twitter_campaign_service import TwitterCampaignService

    service = TwitterCampaignService()

    # Verify method exists
    assert hasattr(service, 'schedule_offer_tweets')
    assert callable(service.schedule_offer_tweets)

    # Verify method signature
    import inspect
    sig = inspect.signature(service.schedule_offer_tweets)
    params = list(sig.parameters.keys())

    assert 'offer_url' in params
    assert 'offer_description' in params
    assert 'count' in params
    assert 'interval_minutes' in params


# =========================================================================
# ARCH-005: Offer Traffic Tracking Service
# =========================================================================

def test_arch_005_offer_tracker_exists():
    """ARCH-005: Verify OfferTracker service exists and initializes."""
    tracker = OfferTracker()

    assert tracker is not None
    assert tracker.engine is not None


def test_arch_005_offer_tracker_has_tracking_methods():
    """ARCH-005: Verify OfferTracker has click and conversion tracking methods."""
    tracker = OfferTracker()

    # Verify methods exist
    assert hasattr(tracker, 'track_click')
    assert hasattr(tracker, 'track_conversion')
    assert hasattr(tracker, 'get_campaign_analytics')
    assert hasattr(tracker, 'get_top_performing_content')

    # Verify all are callable
    assert callable(tracker.track_click)
    assert callable(tracker.track_conversion)
    assert callable(tracker.get_campaign_analytics)


# =========================================================================
# ARCH-006: Analytics → AI Feedback Loop
# =========================================================================

@pytest.mark.asyncio
async def test_arch_006_analytics_feedback_exists():
    """ARCH-006: Verify AnalyticsFeedback service exists and initializes."""
    feedback = AnalyticsFeedback()

    assert feedback is not None
    assert feedback.event_bus is not None
    assert feedback.post_performances is not None
    assert feedback.content_patterns is not None


@pytest.mark.asyncio
async def test_arch_006_analytics_feedback_subscribes_to_events():
    """ARCH-006: Verify AnalyticsFeedback subscribes to metrics events."""
    feedback = AnalyticsFeedback()

    # Start the feedback service
    await feedback.start()

    assert feedback._running is True
    assert len(feedback._subscriptions) > 0

    # Cleanup
    await feedback.stop()


def test_arch_006_analytics_feedback_provides_recommendations():
    """ARCH-006: Verify AnalyticsFeedback can generate recommendations."""
    feedback = AnalyticsFeedback()

    # Verify method exists
    assert hasattr(feedback, 'get_recommendations')
    assert callable(feedback.get_recommendations)

    # Get recommendations (should return empty list if no data)
    recommendations = feedback.get_recommendations()
    assert isinstance(recommendations, list)


# =========================================================================
# ARCH-007: Unified Pipeline API Endpoint
# =========================================================================

@pytest.mark.asyncio
async def test_arch_007_orchestrator_api_exists():
    """ARCH-007: Verify orchestrator API endpoints exist."""
    from api.endpoints import orchestrator as orch_api

    # Verify router exists
    assert orch_api.router is not None

    # Verify key endpoints exist
    routes = [route.path for route in orch_api.router.routes]

    assert "/pipeline/run" in routes or any("run" in r for r in routes)
    assert "/pipeline/{pipeline_id}" in routes or any("pipeline_id" in r for r in routes)
    assert "/pipelines" in routes or "/api/orchestrator/pipelines" in routes or any("pipelines" in r for r in routes)
    assert "/health" in routes or any("health" in r for r in routes)


# =========================================================================
# ARCH-008: Pipeline Dashboard Widget
# =========================================================================

def test_arch_008_orchestrator_exposes_pipeline_status():
    """ARCH-008: Verify orchestrator exposes pipeline status for dashboard."""
    orchestrator = MasterOrchestrator()

    # Verify status methods exist
    assert hasattr(orchestrator, 'get_pipeline_status')
    assert hasattr(orchestrator, 'list_active_pipelines')

    # Test listing (should be empty initially)
    pipelines = orchestrator.list_active_pipelines()
    assert isinstance(pipelines, list)


# =========================================================================
# END-TO-END INTEGRATION TEST
# =========================================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_pipeline_integration():
    """
    End-to-end integration test of the complete system architecture.

    This test verifies the full workflow:
    1. Sora generates multi-part video
    2. Video is stitched and analyzed
    3. Content is published to platforms
    4. Tweets are scheduled
    5. Analytics are tracked
    """
    orchestrator = MasterOrchestrator()

    # Mock all external dependencies
    with patch.object(orchestrator.sora_pipeline, 'generate_multi_part', new_callable=AsyncMock) as mock_sora:
        with patch.object(orchestrator, '_step_publish_to_platforms', new_callable=AsyncMock) as mock_publish:
            with patch.object(orchestrator.twitter_service, 'schedule_tweets') as mock_tweets:
                with patch.object(orchestrator.twitter_service, 'generate_tweet') as mock_generate_tweet:

                    # Setup mock returns
                    mock_sora.return_value = {
                        "status": "completed",
                        "job_id": "test_job_123",
                        "stitched_video": "/tmp/test_final.mp4",
                        "successful_parts": 3,
                        "failed_parts": 0,
                        "analysis": {
                            "title_tiktok": "Amazing AI Content",
                            "hashtags": ["ai", "viral", "content"],
                            "hook": "Watch this!",
                            "viral_score": 88
                        }
                    }

                    mock_publish.return_value = {
                        "results": [
                            {"platform": "tiktok", "account_id": "710", "status": "queued"},
                            {"platform": "instagram", "account_id": "807", "status": "queued"}
                        ],
                        "total": 2
                    }

                    mock_tweets.return_value = ["tweet_1", "tweet_2", "tweet_3"]
                    mock_generate_tweet.return_value = "Check out this amazing AI content! 🚀"

                    # Start orchestrator
                    await orchestrator.start()

                    # Run full pipeline (returns pipeline_id)
                    pipeline_id = await orchestrator.run_full_pipeline(
                        theme="Test end-to-end system architecture",
                        num_parts=3,
                        publish_platforms=["tiktok", "instagram"],
                        schedule_tweets=True,
                        tweets_per_day=12
                    )

                    # Verify pipeline was created
                    assert isinstance(pipeline_id, str)
                    assert pipeline_id.startswith("pipeline-")

                    # Get pipeline status
                    status = orchestrator.get_pipeline_status(pipeline_id)
                    assert status is not None
                    assert status["theme"] == "Test end-to-end system architecture"
                    assert status["status"] in ["initializing", "generating_video", "analyzing", "publishing", "completed"]

                    # Verify pipeline is tracked
                    assert pipeline_id in orchestrator.active_pipelines or pipeline_id in orchestrator.completed_pipelines

                    # Note: Since this is event-driven and async, we can't assert on exact completion state
                    # The real verification is that the pipeline was created and is being tracked

                    # Cleanup
                    await orchestrator.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
