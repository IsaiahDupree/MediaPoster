"""
System Architecture Integration Tests (ARCH-001 to ARCH-008)
=============================================================
Integration tests for the complete MediaPoster pipeline:
    Sora → Stitch → Analyze → Publish → Tweet → Track

Tests:
    - ARCH-001: Master Orchestrator Service
    - ARCH-002: 3-Part Sora Batch Coordination
    - ARCH-003: Content Analyzer → Publisher Integration
    - ARCH-004: Tweet Scheduler 2-Hour Interval
    - ARCH-005: Offer Traffic Tracking Service
    - ARCH-006: Analytics → AI Feedback Loop
    - ARCH-007: Unified Pipeline API Endpoint
    - ARCH-008: Pipeline Dashboard Widget (UI tests)
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from pathlib import Path

# Import the services to test
from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.offer_tracker import OfferTracker
from services.analytics_feedback import AnalyticsFeedback, get_analytics_feedback
from services.event_bus import EventBus, Topics
from automation.sora.pipeline import SoraPipeline


@pytest.fixture
def event_bus():
    """Create a fresh EventBus instance for testing"""
    return EventBus()


@pytest.fixture
def orchestrator(event_bus):
    """Create MasterOrchestrator with mocked subsystems"""
    with patch('services.master_orchestrator.SoraPipeline') as mock_sora, \
         patch('services.master_orchestrator.ContentAnalyzer') as mock_analyzer, \
         patch('services.master_orchestrator.BlotatoService') as mock_blotato, \
         patch('services.master_orchestrator.TwitterCampaignService') as mock_twitter, \
         patch('services.master_orchestrator.get_analytics_feedback') as mock_feedback, \
         patch('services.master_orchestrator.create_engine') as mock_engine:

        # Mock database engine
        mock_engine.return_value = Mock()

        orchestrator = MasterOrchestrator(event_bus=event_bus)

        # Mock Sora pipeline methods
        mock_sora_instance = AsyncMock()
        mock_sora_instance.generate_multi_part = AsyncMock(return_value={
            "status": "completed",
            "stitched_video": "/path/to/video.mp4",
            "analysis": {
                "detected_hook": "Amazing AI content!",
                "topics": ["AI", "content", "automation"],
                "hashtags": ["ai", "viral", "content"],
                "viral_score": 85
            }
        })
        orchestrator.sora_pipeline = mock_sora_instance

        # Mock content analyzer
        mock_analyzer_instance = AsyncMock()
        mock_analyzer_instance.analyze_video = AsyncMock(return_value={
            "detected_hook": "Test hook",
            "topics": ["test"],
            "hashtags": ["test"],
            "viral_score": 75
        })
        orchestrator.content_analyzer = mock_analyzer_instance

        # Mock Blotato service
        mock_blotato_instance = Mock()
        mock_blotato_instance.get_accounts_by_platform = Mock(return_value=[
            Mock(id="123", username="test_account", platform="tiktok")
        ])
        orchestrator.blotato_service = mock_blotato_instance

        # Mock Twitter service
        mock_twitter_instance = Mock()
        mock_twitter_instance.schedule_tweets = Mock(return_value=["tweet1", "tweet2"])
        mock_twitter_instance.schedule_campaign = Mock(return_value="campaign_123")
        orchestrator.twitter_service = mock_twitter_instance

        # Mock analytics feedback
        mock_feedback_instance = AsyncMock()
        mock_feedback_instance.start = AsyncMock()
        mock_feedback_instance.get_recommendations = Mock(return_value=[
            {"name": "Use more hooks", "confidence": 0.9}
        ])
        orchestrator.analytics_feedback = mock_feedback_instance

        # Mock database operations
        orchestrator._save_pipeline_to_db = Mock()
        orchestrator._save_pipeline_step_to_db = Mock()

        yield orchestrator


# ============================================================================
# ARCH-001: Master Orchestrator Service
# ============================================================================

@pytest.mark.asyncio
async def test_arch_001_master_orchestrator_initialization(orchestrator):
    """Test that Master Orchestrator initializes with all subsystems"""
    assert orchestrator.sora_pipeline is not None
    assert orchestrator.content_analyzer is not None
    assert orchestrator.blotato_service is not None
    assert orchestrator.twitter_service is not None
    assert orchestrator.analytics_feedback is not None


@pytest.mark.asyncio
async def test_arch_001_master_orchestrator_start(orchestrator):
    """Test that orchestrator starts and subscribes to events"""
    await orchestrator.start()

    assert orchestrator._running is True
    assert orchestrator.analytics_feedback.start.called


@pytest.mark.asyncio
async def test_arch_001_full_pipeline_execution(orchestrator):
    """Test complete pipeline execution from Sora to publishing"""

    # Configure pipeline
    config = PipelineConfig(
        theme="Test AI content automation",
        num_parts=3,
        accounts="all",
        enable_tweets=True,
        tweet_interval_minutes=120,
        offer_url="https://test.com/offer"
    )

    # Run pipeline
    result = await orchestrator.run_full_pipeline(
        theme=config.theme,
        num_parts=config.num_parts,
        publish_platforms=["tiktok"],
        schedule_tweets=True,
        tweets_per_day=12,
        offer_url=config.offer_url
    )

    # Verify pipeline completed
    assert result["status"] in ["completed", "partial"]
    assert "video_generated" in result["steps"]
    assert "content_analyzed" in result["steps"]
    assert "published_to_platforms" in result["steps"]

    # Verify Sora was called
    assert orchestrator.sora_pipeline.generate_multi_part.called

    # Verify publishing was attempted
    assert len(result["outputs"]["published"]["results"]) > 0


# ============================================================================
# ARCH-002: 3-Part Sora Batch Coordination
# ============================================================================

@pytest.mark.asyncio
async def test_arch_002_multi_part_sora_generation(event_bus):
    """Test that Sora pipeline generates and stitches 3-part videos"""

    with patch('automation.sora.pipeline.SoraController') as mock_controller, \
         patch('automation.sora.pipeline.GenerationMonitor') as mock_monitor, \
         patch('automation.sora.pipeline.VideoDownloader') as mock_downloader:

        # Mock Sora controller
        mock_controller_instance = AsyncMock()
        mock_controller_instance.launch_sora = AsyncMock(return_value=True)
        mock_controller_instance.check_login_status = AsyncMock(return_value={"logged_in": True})
        mock_controller_instance.submit_prompt = AsyncMock(return_value=True)
        mock_controller.return_value = mock_controller_instance

        # Mock monitor
        mock_monitor_instance = AsyncMock()
        mock_monitor_instance.start_monitoring = AsyncMock(return_value={"status": "completed"})
        mock_monitor.return_value = mock_monitor_instance

        # Mock downloader
        mock_downloader_instance = AsyncMock()
        mock_downloader_instance.download_current_video = AsyncMock(return_value=Path("/test/video.mp4"))
        mock_downloader.return_value = mock_downloader_instance

        # Create pipeline
        pipeline = SoraPipeline(event_bus=event_bus)

        # Mock video stitching
        pipeline.stitch_videos = AsyncMock(return_value=Path("/test/stitched.mp4"))

        # Mock AI prompt generation
        pipeline._generate_part_prompts = AsyncMock(return_value=[
            "Part 1 prompt",
            "Part 2 prompt",
            "Part 3 prompt"
        ])

        # Mock analysis
        pipeline._analyze_video_content = AsyncMock(return_value={
            "hook": "Test hook",
            "viral_score": 80
        })

        # Generate 3-part video
        result = await pipeline.generate_multi_part(
            theme="Test multi-part video",
            num_parts=3,
            auto_stitch=True,
            auto_analyze=True
        )

        # Verify multi-part generation
        assert result["type"] == "multi_part"
        assert result["num_parts"] == 3
        assert len(result["prompts"]) == 3

        # Verify stitching was called
        assert pipeline.stitch_videos.called

        # Verify analysis was called
        assert pipeline._analyze_video_content.called


# ============================================================================
# ARCH-003: Content Analyzer → Publisher Integration
# ============================================================================

@pytest.mark.asyncio
async def test_arch_003_analyzer_to_publisher_integration(orchestrator):
    """Test that analysis is auto-injected into publish payload"""

    analysis = {
        "detected_hook": "Amazing content!",
        "topics": ["AI", "automation"],
        "hashtags": ["ai", "viral"],
        "viral_score": 90
    }

    # Build publish payload with analysis
    payload = await orchestrator._build_publish_payload(
        video_path="/test/video.mp4",
        account={"id": "123", "platform": "tiktok"},
        config=PipelineConfig(
            theme="Test",
            auto_title=True,
            auto_description=True,
            auto_hashtags=True
        ),
        analysis=analysis
    )

    # Verify analysis was injected
    assert payload["title"] == "Amazing content!"
    assert "AI" in payload["description"] or "automation" in payload["description"]
    assert len(payload["hashtags"]) > 0


# ============================================================================
# ARCH-004: Tweet Scheduler 2-Hour Interval
# ============================================================================

def test_arch_004_tweet_scheduler_interval():
    """Test that TwitterCampaignService uses 2-hour intervals"""
    from services.twitter_campaign_service import TwitterCampaignService

    # Create service with 2-hour interval
    service = TwitterCampaignService(interval_minutes=120)

    # Verify interval is set
    assert service.interval_minutes == 120


# ============================================================================
# ARCH-005: Offer Traffic Tracking Service
# ============================================================================

@pytest.mark.asyncio
async def test_arch_005_offer_tracker_create_link():
    """Test that OfferTracker creates tracked links with UTM params"""

    with patch('services.offer_tracker.create_engine') as mock_engine:
        mock_engine.return_value = Mock()

        tracker = OfferTracker()

        # Create tracked link
        tracked_url = await tracker.create_tracked_link(
            offer_url="https://test.com/offer",
            campaign="test_campaign",
            source="mediaposter",
            medium="social"
        )

        # Verify UTM parameters are included
        assert "utm_campaign=test_campaign" in tracked_url
        assert "utm_source=mediaposter" in tracked_url
        assert "utm_medium=social" in tracked_url


def test_arch_005_offer_tracker_track_click():
    """Test that OfferTracker tracks clicks"""

    with patch('services.offer_tracker.create_engine') as mock_engine:
        # Mock database connection
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchone = Mock(return_value=["click_123"])
        mock_conn.execute = Mock(return_value=mock_result)
        mock_conn.commit = Mock()
        mock_engine.return_value.connect = Mock(return_value=mock_conn)
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        tracker = OfferTracker()

        # Track click
        click_id = tracker.track_click(
            utm_campaign="test_campaign",
            utm_source="twitter",
            utm_content="v1"
        )

        # Verify click was tracked
        assert click_id == "click_123"
        assert mock_conn.execute.called
        assert mock_conn.commit.called


# ============================================================================
# ARCH-006: Analytics → AI Feedback Loop
# ============================================================================

@pytest.mark.asyncio
async def test_arch_006_analytics_feedback_service():
    """Test that AnalyticsFeedback service processes analytics events"""

    event_bus = EventBus()
    feedback = AnalyticsFeedback(event_bus=event_bus)

    # Start service
    await feedback.start()

    assert feedback._running is True
    assert Topics.CHECKBACK_COMPLETED in feedback._subscriptions
    assert Topics.PUBLISH_COMPLETED in feedback._subscriptions


# ============================================================================
# ARCH-007: Unified Pipeline API Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_arch_007_pipeline_api_endpoint():
    """Test that API endpoint triggers full pipeline"""
    from fastapi.testclient import TestClient
    from api.endpoints.orchestrator import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    with TestClient(app) as client:
        # Make request to pipeline endpoint
        response = client.post(
            "/api/orchestrator/pipeline/run",
            json={
                "theme": "Test pipeline execution",
                "num_parts": 3,
                "schedule_tweets": True,
                "tweets_per_day": 12
            }
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "initializing"


# ============================================================================
# INTEGRATION TEST: Complete Pipeline Flow
# ============================================================================

@pytest.mark.asyncio
async def test_complete_pipeline_flow(orchestrator, event_bus):
    """
    Integration test for complete pipeline:
    Sora → Stitch → Analyze → Publish → Tweet → Track
    """

    # Track events emitted
    emitted_events = []

    def track_event(event):
        emitted_events.append(event.topic)

    # Subscribe to all orchestrator events
    event_bus.subscribe("orchestrator.*", track_event)

    # Run full pipeline
    result = await orchestrator.run_full_pipeline(
        theme="Complete integration test",
        num_parts=3,
        publish_platforms=["tiktok"],
        schedule_tweets=True,
        tweets_per_day=12,
        offer_url="https://test.com/offer"
    )

    # Verify pipeline completed
    assert result["status"] in ["completed", "partial"]

    # Verify all steps executed
    expected_steps = [
        "video_generated",
        "content_analyzed",
        "published_to_platforms"
    ]
    for step in expected_steps:
        assert step in result["steps"], f"Missing step: {step}"

    # Verify orchestrator events were emitted
    assert Topics.ORCHESTRATOR_PIPELINE_STARTED in emitted_events
    assert Topics.ORCHESTRATOR_PIPELINE_COMPLETED in emitted_events or \
           Topics.ORCHESTRATOR_PIPELINE_FAILED in emitted_events

    # Verify outputs
    assert "video" in result["outputs"]
    assert "analysis" in result["outputs"]
    assert "published" in result["outputs"]

    # Verify publishing
    published_results = result["outputs"]["published"]["results"]
    assert len(published_results) > 0

    # Verify tweet scheduling
    if result.get("outputs", {}).get("tweets"):
        assert result["outputs"]["tweets"]["scheduled_count"] > 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_pipeline_handles_sora_failure(orchestrator):
    """Test that pipeline gracefully handles Sora generation failures"""

    # Mock Sora to fail
    orchestrator.sora_pipeline.generate_multi_part = AsyncMock(return_value={
        "status": "failed",
        "error": "Sora generation timeout"
    })

    # Run pipeline and expect it to handle the error
    with pytest.raises(Exception) as exc_info:
        await orchestrator.run_full_pipeline(
            theme="Test failure handling",
            num_parts=3
        )

    assert "Sora generation timeout" in str(exc_info.value) or \
           "Video generation failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_pipeline_handles_publish_failure(orchestrator):
    """Test that pipeline continues when individual publishes fail"""

    # Mock Blotato to raise exception
    orchestrator.blotato_service.get_accounts_by_platform = Mock(side_effect=Exception("API error"))

    # Run pipeline - should not crash
    result = await orchestrator.run_full_pipeline(
        theme="Test publish failure",
        num_parts=1,
        publish_platforms=["tiktok"]
    )

    # Pipeline should complete with errors
    assert result["status"] in ["partial", "failed"]
    assert len(result.get("errors", [])) > 0


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_pipeline_parallel_publishing(orchestrator):
    """Test that publishing to multiple accounts happens in parallel"""
    import time

    # Mock multiple accounts
    orchestrator.blotato_service.get_accounts_by_platform = Mock(return_value=[
        Mock(id=f"{i}", username=f"account_{i}", platform="tiktok")
        for i in range(5)
    ])

    # Track publish call times
    publish_times = []

    async def mock_publish(*args, **kwargs):
        publish_times.append(time.time())
        await asyncio.sleep(0.1)  # Simulate API call

    orchestrator.event_bus.publish = mock_publish

    start_time = time.time()

    # Run publishing step
    await orchestrator._step_publish_to_platforms(
        pipeline_id="test",
        video_result={"stitched_video": "/test/video.mp4"},
        analysis_result={},
        platforms=["tiktok"]
    )

    total_time = time.time() - start_time

    # Verify parallel execution (should be much faster than sequential)
    # 5 accounts × 0.1s = 0.5s sequential, but should be ~0.1s parallel
    assert total_time < 0.3, "Publishing should happen in parallel"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
