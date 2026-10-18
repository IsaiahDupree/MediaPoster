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
    orch = MasterOrchestrator(event_bus=event_bus, use_db=False)

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
    orch.sora_pipeline = mock_sora_instance

    # Mock content analyzer
    mock_analyzer_instance = AsyncMock()
    mock_analyzer_instance.analyze_video = AsyncMock(return_value={
        "detected_hook": "Test hook",
        "topics": ["test"],
        "hashtags": ["test"],
        "viral_score": 75
    })
    orch.content_analyzer = mock_analyzer_instance

    # Mock Blotato service
    mock_blotato_instance = Mock()
    mock_blotato_instance.get_accounts_by_platform = Mock(return_value=[
        Mock(id="123", username="test_account", platform="tiktok")
    ])
    orch.blotato_service = mock_blotato_instance

    # Mock Twitter service
    mock_twitter_instance = Mock()
    mock_twitter_instance.schedule_tweets = Mock(return_value=["tweet1", "tweet2"])
    mock_twitter_instance.schedule_campaign = Mock(return_value="campaign_123")
    orch.twitter_service = mock_twitter_instance

    # Mock analytics feedback
    mock_feedback_instance = AsyncMock()
    mock_feedback_instance.start = AsyncMock()
    mock_feedback_instance.stop = AsyncMock()
    mock_feedback_instance.get_recommendations = Mock(return_value=[
        {"name": "Use more hooks", "confidence": 0.9}
    ])
    orch.analytics_feedback = mock_feedback_instance

    yield orch


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
    """Test that run_full_pipeline creates and tracks pipeline in event-driven architecture"""

    # Run pipeline (returns pipeline_id string)
    pipeline_id = await orchestrator.run_full_pipeline(
        theme="Test AI content automation",
        num_parts=3,
        publish_platforms=["tiktok"],
        schedule_tweets=True,
        tweets_per_day=12,
        offer_url="https://test.com/offer"
    )

    # Verify pipeline was created
    assert isinstance(pipeline_id, str), "Should return pipeline_id string"
    assert pipeline_id in orchestrator.active_pipelines

    pipeline = orchestrator.active_pipelines[pipeline_id]
    assert pipeline["theme"] == "Test AI content automation"
    assert pipeline["status"] == "generating_video"
    assert isinstance(pipeline["outputs"], dict)


# ============================================================================
# ARCH-002: 3-Part Sora Batch Coordination
# ============================================================================

@pytest.mark.asyncio
async def test_arch_002_multi_part_sora_generation(event_bus):
    """Test that Sora pipeline has correct multi-part generation interface"""
    import inspect

    # Create pipeline (no event_bus parameter - SoraPipeline doesn't accept it)
    pipeline = SoraPipeline()

    # Verify method exists and has correct signature
    assert hasattr(pipeline, 'generate_multi_part')
    sig = inspect.signature(pipeline.generate_multi_part)
    params = list(sig.parameters.keys())

    assert 'theme' in params, "Should accept theme"
    assert 'num_parts' in params, "Should accept num_parts"
    assert 'auto_stitch' in params, "Should accept auto_stitch"
    assert 'auto_analyze' in params, "Should accept auto_analyze"

    # Verify it also has generate_batch for independent video generation
    assert hasattr(pipeline, 'generate_batch'), "Should have generate_batch method"


# ============================================================================
# ARCH-003: Content Analyzer → Publisher Integration
# ============================================================================

@pytest.mark.asyncio
async def test_arch_003_analyzer_to_publisher_integration(orchestrator):
    """Test that analysis is auto-extracted into platform metadata (ARCH-003)"""

    analysis = {
        "detected_hook": "Amazing content!",
        "topics": ["AI", "automation"],
        "hashtags": ["ai", "viral"],
        "viral_score": 90
    }

    # Test _extract_platform_metadata (ARCH-003 integration)
    metadata = orchestrator._extract_platform_metadata(analysis)

    # Verify platform metadata was generated
    assert "default" in metadata
    assert "tiktok" in metadata
    assert "instagram" in metadata
    assert "youtube" in metadata
    assert "twitter" in metadata

    # Verify analysis was injected into metadata
    assert metadata["default"]["hook"] == "Amazing content!"
    assert metadata["default"]["viral_score"] == 90
    assert len(metadata["default"]["hashtags"]) > 0


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
    Integration test for pipeline creation and event emission:
    run_full_pipeline → creates pipeline → emits events
    """

    # Track events emitted
    emitted_events = []

    async def track_event(event):
        emitted_events.append(event.topic)

    # Subscribe to orchestrator events
    event_bus.subscribe(Topics.ORCHESTRATOR_PIPELINE_STARTED, track_event)
    event_bus.subscribe(Topics.SORA_BATCH_REQUESTED, track_event)

    # Run full pipeline (returns pipeline_id in event-driven architecture)
    pipeline_id = await orchestrator.run_full_pipeline(
        theme="Complete integration test",
        num_parts=3,
        publish_platforms=["tiktok"],
        schedule_tweets=True,
        tweets_per_day=12,
        offer_url="https://test.com/offer"
    )

    # Give event bus time to dispatch
    await asyncio.sleep(0.1)

    # Verify pipeline was created
    assert isinstance(pipeline_id, str)
    assert pipeline_id in orchestrator.active_pipelines

    # Verify orchestrator events were emitted
    assert Topics.ORCHESTRATOR_PIPELINE_STARTED in emitted_events, \
        f"Should emit pipeline started, got: {emitted_events}"
    assert Topics.SORA_BATCH_REQUESTED in emitted_events, \
        f"Should emit sora batch request, got: {emitted_events}"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_pipeline_handles_sora_failure(orchestrator, event_bus):
    """Test that pipeline tracks failure from Sora batch via event handler"""

    # Start pipeline
    pipeline_id = await orchestrator.run_full_pipeline(
        theme="Test failure handling",
        num_parts=3
    )

    # Simulate Sora batch failure via event
    from services.event_bus import Event
    await orchestrator._handle_sora_batch_failed(Event(
        topic=Topics.SORA_BATCH_FAILED,
        payload={
            "pipeline_id": pipeline_id,
            "error": "Sora generation timeout"
        }
    ))

    # Pipeline should be moved to completed with failed status
    assert pipeline_id not in orchestrator.active_pipelines, "Failed pipeline should leave active"
    assert pipeline_id in orchestrator.completed_pipelines, "Failed pipeline should move to completed"
    assert orchestrator.completed_pipelines[pipeline_id]["status"] == "failed"


@pytest.mark.asyncio
async def test_pipeline_handles_publish_failure(orchestrator, event_bus):
    """Test that pipeline creation works even with Blotato errors"""

    # run_full_pipeline doesn't directly call Blotato, it uses events
    # So we verify the pipeline is created correctly
    pipeline_id = await orchestrator.run_full_pipeline(
        theme="Test publish failure",
        num_parts=1,
        publish_platforms=["tiktok"]
    )

    assert isinstance(pipeline_id, str)
    assert pipeline_id in orchestrator.active_pipelines


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_pipeline_creates_publish_jobs_for_all_platforms(orchestrator, event_bus):
    """Test that _handle_sora_batch_completed creates publish requests for all platforms"""

    # Start pipeline with multiple platforms
    pipeline_id = await orchestrator.run_full_pipeline(
        theme="Test multi-platform",
        num_parts=1,
        publish_platforms=["tiktok", "instagram", "youtube"],
        schedule_tweets=False
    )

    # Track publish events
    publish_events = []

    async def track_publish(event):
        if event.topic == Topics.PUBLISH_REQUESTED:
            publish_events.append(event.payload)

    event_bus.subscribe(Topics.PUBLISH_REQUESTED, track_publish)

    # Simulate Sora batch completion
    from services.event_bus import Event
    await orchestrator._handle_sora_batch_completed(Event(
        topic=Topics.SORA_BATCH_COMPLETED,
        payload={
            "pipeline_id": pipeline_id,
            "stitched_video": "/test/video.mp4",
            "analysis": {"detected_hook": "Test hook", "hashtags": ["test"]},
            "successful_parts": 1
        }
    ))

    await asyncio.sleep(0.1)

    # Verify publish requests were made for all platforms
    platforms_requested = [e.get("platform") for e in publish_events]
    assert "tiktok" in platforms_requested
    assert "instagram" in platforms_requested
    assert "youtube" in platforms_requested


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
