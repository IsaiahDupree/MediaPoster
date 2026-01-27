"""
Test Master Orchestrator Integration (ARCH-001 to ARCH-008)
===========================================================
Tests for the complete system architecture integration.

Tests:
- ARCH-001: Master Orchestrator Service
- ARCH-002: 3-Part Sora Batch Coordination
- ARCH-003: Content Analyzer → Publisher Integration
- ARCH-007: Unified Pipeline API Endpoint
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from services.master_orchestrator import MasterOrchestrator, PipelineStage
from services.event_bus import EventBus, Topics


@pytest.fixture
def event_bus():
    """Create a fresh event bus for each test."""
    EventBus.reset_instance()
    return EventBus.get_instance()


@pytest.fixture
def orchestrator(event_bus):
    """Create a master orchestrator instance."""
    return MasterOrchestrator(event_bus=event_bus)


@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    """Test ARCH-001: Master Orchestrator initializes correctly."""
    assert orchestrator is not None
    assert orchestrator.event_bus is not None
    assert orchestrator.sora_pipeline is not None
    assert orchestrator.content_analyzer is not None
    assert len(orchestrator.active_pipelines) == 0


@pytest.mark.asyncio
async def test_orchestrator_subscriptions(orchestrator, event_bus):
    """Test ARCH-001: Orchestrator subscribes to correct events."""
    # Check that orchestrator subscribed to key topics
    stats = event_bus.get_stats()
    subscribed_topics = stats["topics_with_subscribers"]

    assert Topics.SORA_BATCH_COMPLETED in subscribed_topics
    assert Topics.PUBLISH_COMPLETED in subscribed_topics
    assert Topics.CHECKBACK_COMPLETED in subscribed_topics


@pytest.mark.asyncio
@patch('services.master_orchestrator.SoraPipeline')
async def test_full_pipeline_execution(mock_sora_pipeline, orchestrator, event_bus):
    """Test ARCH-001: Full pipeline execution flow."""
    # Mock Sora pipeline result
    mock_sora_result = {
        "id": "test123",
        "status": "completed",
        "successful_parts": 3,
        "stitched_video": "/path/to/stitched.mp4",
        "analysis": {
            "viral_score": 85,
            "detected_hook": "Amazing AI productivity tip",
            "hashtags": ["AI", "productivity", "tips"]
        }
    }

    orchestrator.sora_pipeline.generate_multi_part = AsyncMock(return_value=mock_sora_result)

    # Mock video storage
    with patch.object(orchestrator, '_store_video', return_value="video_123"):
        # Mock publish
        with patch.object(orchestrator, '_publish_to_blotato_accounts', return_value={
            "successful": [{"account_id": 807, "media_id": "video_123"}],
            "failed": []
        }):
            # Mock Twitter campaign
            with patch.object(orchestrator, '_schedule_twitter_campaign', return_value={
                "posts_scheduled": 12
            }):
                # Run pipeline
                result = await orchestrator.run_full_pipeline(
                    theme="Test AI productivity",
                    num_parts=3,
                    blotato_accounts=[807]
                )

                # Verify result
                assert result["stage"] == PipelineStage.COMPLETED
                assert "sora_generation" in result["stages_completed"]
                assert "blotato_publishing" in result["stages_completed"]
                assert result["sora_result"]["successful_parts"] == 3


@pytest.mark.asyncio
async def test_orchestrator_event_emission(orchestrator, event_bus):
    """Test ARCH-001: Orchestrator emits correct events."""
    # Track emitted events
    emitted_events = []

    async def event_tracker(event):
        emitted_events.append(event)

    # Subscribe to all orchestrator events
    event_bus.subscribe(Topics.ORCHESTRATOR_PIPELINE_STARTED, event_tracker)
    event_bus.subscribe(Topics.ORCHESTRATOR_STEP_STARTED, event_tracker)
    event_bus.subscribe(Topics.ORCHESTRATOR_STEP_COMPLETED, event_tracker)

    # Mock all subsystems
    with patch.object(orchestrator.sora_pipeline, 'generate_multi_part', return_value={
        "id": "test", "status": "completed", "successful_parts": 3,
        "stitched_video": "/test.mp4", "analysis": {"viral_score": 80}
    }):
        with patch.object(orchestrator, '_store_video', return_value="vid123"):
            with patch.object(orchestrator, '_publish_to_blotato_accounts', return_value={
                "successful": [], "failed": []
            }):
                with patch.object(orchestrator, '_schedule_twitter_campaign', return_value={
                    "posts_scheduled": 0
                }):
                    await orchestrator.run_full_pipeline(
                        theme="Test",
                        num_parts=1,
                        blotato_accounts=[]
                    )

    # Verify events were emitted
    assert len(emitted_events) > 0
    topics = [e.topic for e in emitted_events]
    assert Topics.ORCHESTRATOR_PIPELINE_STARTED in topics


@pytest.mark.asyncio
async def test_sora_multi_part_integration(orchestrator):
    """Test ARCH-002: 3-Part Sora Batch Coordination."""
    # This test verifies that the Sora pipeline's generate_multi_part method
    # is correctly integrated into the orchestrator

    # Mock the Sora pipeline
    mock_result = {
        "id": "batch123",
        "type": "multi_part",
        "theme": "AI Tips",
        "num_parts": 3,
        "status": "completed",
        "successful_parts": 3,
        "parts": [
            {"part_number": 1, "result": {"status": "completed"}},
            {"part_number": 2, "result": {"status": "completed"}},
            {"part_number": 3, "result": {"status": "completed"}}
        ],
        "stitched_video": "/output/multipart_batch123_final.mp4",
        "analysis": {
            "viral_score": 90,
            "title_tiktok": "Amazing AI Productivity Tips",
            "hashtags": ["AI", "productivity"]
        }
    }

    with patch.object(orchestrator.sora_pipeline, 'generate_multi_part', return_value=mock_result):
        # The orchestrator should call generate_multi_part with correct params
        with patch.object(orchestrator, '_store_video', return_value="vid123"):
            with patch.object(orchestrator, '_publish_to_blotato_accounts', return_value={
                "successful": [], "failed": []
            }):
                result = await orchestrator.run_full_pipeline(
                    theme="AI Tips",
                    num_parts=3,
                    blotato_accounts=[]
                )

                # Verify Sora batch coordination worked
                assert result["sora_result"]["successful_parts"] == 3
                assert result["sora_result"]["type"] == "multi_part"
                assert result["stitched_video"] is not None


@pytest.mark.asyncio
async def test_content_analyzer_publisher_integration(orchestrator, event_bus):
    """Test ARCH-003: Content Analyzer → Publisher Integration."""
    # Track publish events to verify analysis is passed through
    publish_events = []

    async def track_publish(event):
        publish_events.append(event.payload)

    event_bus.subscribe(Topics.PUBLISH_REQUESTED, track_publish)

    # Mock Sora with analysis
    analysis = {
        "viral_score": 85,
        "detected_hook": "Amazing tip!",
        "title_tiktok": "AI Productivity Hack",
        "hashtags": ["AI", "productivity", "hack"]
    }

    with patch.object(orchestrator.sora_pipeline, 'generate_multi_part', return_value={
        "id": "test", "status": "completed", "successful_parts": 1,
        "stitched_video": "/test.mp4", "analysis": analysis
    }):
        with patch.object(orchestrator, '_store_video', return_value="vid123"):
            await orchestrator.run_full_pipeline(
                theme="Test",
                num_parts=1,
                blotato_accounts=[807]
            )

    # Verify that publish event includes the analysis (ARCH-003)
    assert len(publish_events) > 0
    publish_payload = publish_events[0]
    assert "analysis" in publish_payload
    assert publish_payload["analysis"]["viral_score"] == 85
    assert publish_payload["auto_generate_metadata"] == False  # Should use pre-computed analysis


@pytest.mark.asyncio
async def test_engagement_tracking_setup(orchestrator):
    """Test ARCH-005: Offer Traffic Tracking Service."""
    # Mock successful publish
    published_posts = [
        {"media_id": "vid1", "account_id": 807},
        {"media_id": "vid2", "account_id": 710}
    ]

    result = await orchestrator._setup_engagement_tracking(
        pipeline_id="test123",
        published_posts=published_posts,
        correlation_id="corr123"
    )

    # Verify checkbacks were scheduled
    # 2 posts × 5 checkback periods = 10 total
    assert result["checkbacks_scheduled"] == 10
    assert result["posts_tracked"] == 2
    assert result["checkback_periods"] == [1, 6, 24, 72, 168]


@pytest.mark.asyncio
async def test_pipeline_status_tracking(orchestrator):
    """Test ARCH-001: Pipeline status tracking."""
    # Mock all subsystems
    with patch.object(orchestrator.sora_pipeline, 'generate_multi_part', return_value={
        "id": "test", "status": "completed", "successful_parts": 1,
        "stitched_video": "/test.mp4", "analysis": {"viral_score": 80}
    }):
        with patch.object(orchestrator, '_store_video', return_value="vid123"):
            with patch.object(orchestrator, '_publish_to_blotato_accounts', return_value={
                "successful": [], "failed": []
            }):
                with patch.object(orchestrator, '_schedule_twitter_campaign', return_value={
                    "posts_scheduled": 0
                }):
                    result = await orchestrator.run_full_pipeline(
                        theme="Test",
                        num_parts=1,
                        blotato_accounts=[]
                    )

    # Verify pipeline is tracked
    pipeline_id = result["id"]
    status = orchestrator.get_pipeline_status(pipeline_id)

    assert status is not None
    assert status["id"] == pipeline_id
    assert status["stage"] == PipelineStage.COMPLETED

    # Verify it appears in list
    all_pipelines = orchestrator.list_active_pipelines()
    assert len(all_pipelines) > 0
    assert any(p["id"] == pipeline_id for p in all_pipelines)


@pytest.mark.asyncio
async def test_pipeline_error_handling(orchestrator):
    """Test ARCH-001: Pipeline error handling and recovery."""
    # Mock Sora failure
    with patch.object(orchestrator.sora_pipeline, 'generate_multi_part', side_effect=Exception("Sora failed")):
        with pytest.raises(Exception) as exc_info:
            await orchestrator.run_full_pipeline(
                theme="Test",
                num_parts=1,
                blotato_accounts=[]
            )

        assert "Sora failed" in str(exc_info.value)

    # Verify pipeline is marked as failed
    failed_pipelines = [p for p in orchestrator.list_active_pipelines() if p["stage"] == PipelineStage.FAILED]
    assert len(failed_pipelines) > 0


def test_get_platform_for_account(orchestrator):
    """Test platform mapping for Blotato accounts."""
    assert orchestrator._get_platform_for_account(807) == "instagram"
    assert orchestrator._get_platform_for_account(710) == "tiktok"
    assert orchestrator._get_platform_for_account(228) == "youtube"
    assert orchestrator._get_platform_for_account(4151) == "twitter"
    assert orchestrator._get_platform_for_account(99999) == "instagram"  # default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
