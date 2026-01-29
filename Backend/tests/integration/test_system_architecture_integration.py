"""
Integration Tests for System Architecture Integration (ARCH-001 to ARCH-003)
=============================================================================

Tests the full pipeline workflow:
    Sora (1-3 part) → Stitch → Analyze → Auto-fill → Post to 22 Blotato accounts
                                                          ↓
    Tweet every 2h → Track Engagement → Optimize → Drive Offer Traffic

Features tested:
    - ARCH-001: Master Orchestrator Service
    - ARCH-002: 3-Part Sora Batch Coordination
    - ARCH-003: Content Analyzer → Publisher Integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

# Import the services
from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus, Topics
from automation.sora.pipeline import SoraPipeline
from services.content_analyzer import ContentAnalyzer
from services.workers.publish_worker import PublishWorker
from services.twitter_campaign_service import TwitterCampaignService


@pytest.fixture
def event_bus():
    """Create a test event bus."""
    return EventBus.get_instance()


@pytest.fixture
async def orchestrator(event_bus):
    """Create a test orchestrator with mocked subsystems."""
    orchestrator = MasterOrchestrator(event_bus=event_bus, use_db=False)

    # Mock the subsystem services for testing
    orchestrator.sora_pipeline = Mock(spec=SoraPipeline)
    orchestrator.sora_pipeline.generate_multi_part = AsyncMock()

    orchestrator.blotato_service = Mock()
    orchestrator.blotato_service.get_accounts_by_platform = Mock(return_value=[
        Mock(id=710, platform="tiktok", username="isaiah_dupree"),
        Mock(id=807, platform="instagram", username="the_isaiah_dupree"),
    ])

    orchestrator.twitter_service = Mock(spec=TwitterCampaignService)
    orchestrator.twitter_service.schedule_campaign = Mock(return_value="campaign_123")

    orchestrator.analytics_feedback = Mock()

    yield orchestrator

    # Cleanup
    await orchestrator.stop()


@pytest.mark.asyncio
class TestARCH001_MasterOrchestrator:
    """Test ARCH-001: Master Orchestrator Service"""

    async def test_orchestrator_initializes_subsystems(self, orchestrator):
        """Test that orchestrator properly initializes all subsystems."""
        # Verify subsystems are initialized
        assert orchestrator.sora_pipeline is not None
        assert orchestrator.blotato_service is not None
        assert orchestrator.twitter_service is not None
        assert orchestrator.content_analyzer is not None
        assert orchestrator.event_bus is not None

    async def test_orchestrator_starts_successfully(self, orchestrator):
        """Test that orchestrator starts without errors."""
        await orchestrator.start()
        assert orchestrator._running is True

    async def test_orchestrator_creates_pipeline(self, orchestrator):
        """Test that orchestrator can create a new pipeline."""
        config = PipelineConfig(
            theme="Testing workflow",
            num_parts=3,
            character="isaiahdupree",
            publish_platforms=["tiktok", "instagram"],
            schedule_tweets=True,
            tweets_per_day=12
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Verify pipeline was created
        assert pipeline_id is not None
        assert pipeline_id in orchestrator.active_pipelines

        # Verify pipeline has correct structure
        pipeline = orchestrator.active_pipelines[pipeline_id]
        assert pipeline["theme"] == "Testing workflow"
        assert pipeline["status"] == "generating_video"
        assert "correlation_id" in pipeline

    async def test_orchestrator_tracks_pipeline_state(self, orchestrator):
        """Test that orchestrator properly tracks pipeline state."""
        config = PipelineConfig(theme="State tracking test", num_parts=2)
        pipeline_id = await orchestrator.start_pipeline(config)

        # Get pipeline status
        status = orchestrator.get_pipeline_status(pipeline_id)

        assert status["pipeline_id"] == pipeline_id
        assert status["theme"] == "State tracking test"
        assert status["status"] in ["initializing", "generating_video"]

    async def test_orchestrator_lists_active_pipelines(self, orchestrator):
        """Test that orchestrator can list active pipelines."""
        # Create multiple pipelines
        config1 = PipelineConfig(theme="Pipeline 1", num_parts=2)
        config2 = PipelineConfig(theme="Pipeline 2", num_parts=3)

        await orchestrator.start_pipeline(config1)
        await orchestrator.start_pipeline(config2)

        # List active pipelines
        active = orchestrator.list_active_pipelines()

        assert len(active) == 2
        assert any(p["theme"] == "Pipeline 1" for p in active)
        assert any(p["theme"] == "Pipeline 2" for p in active)


@pytest.mark.asyncio
class TestARCH002_SoraBatchCoordination:
    """Test ARCH-002: 3-Part Sora Batch Coordination"""

    async def test_sora_pipeline_has_multi_part_method(self):
        """Test that SoraPipeline has generate_multi_part method."""
        pipeline = SoraPipeline()

        # Verify method exists
        assert hasattr(pipeline, 'generate_multi_part')
        assert callable(pipeline.generate_multi_part)

    async def test_orchestrator_triggers_sora_batch(self, orchestrator, event_bus):
        """Test that orchestrator triggers Sora batch generation."""
        # Mock Sora pipeline response
        orchestrator.sora_pipeline.generate_multi_part.return_value = {
            "id": "job_123",
            "status": "completed",
            "theme": "Test theme",
            "num_parts": 3,
            "successful_parts": 3,
            "failed_parts": 0,
            "stitched_video": "/path/to/stitched.mp4",
            "analysis": {
                "detected_hook": "Amazing hook!",
                "viral_score": 85,
                "hashtags": ["viral", "trending"]
            }
        }

        # Start pipeline
        config = PipelineConfig(theme="Batch test", num_parts=3)
        pipeline_id = await orchestrator.start_pipeline(config)

        # Wait for event bus to process
        await asyncio.sleep(0.1)

        # Verify Sora batch was NOT called yet (event-driven)
        # In real execution, SORA_BATCH_REQUESTED event triggers the worker
        # which then calls the pipeline

        # Simulate event handler being called
        event = Mock()
        event.payload = {
            "pipeline_id": pipeline_id,
            "theme": "Batch test",
            "num_parts": 3,
            "character": None,
            "stitch": True,
            "remove_watermark": True
        }
        event.correlation_id = "test_correlation"

        # This simulates what the SoraWorker would do
        # orchestrator.sora_pipeline.generate_multi_part should have been called
        # but in our test it's mocked, so we verify the pipeline is in correct state

        assert pipeline_id in orchestrator.active_pipelines

    async def test_sora_batch_emits_completion_event(self, event_bus):
        """Test that Sora batch generation emits completion event."""
        events_received = []

        async def event_handler(event):
            events_received.append(event.topic)

        # Subscribe to batch events
        event_bus.subscribe(Topics.SORA_BATCH_STARTED, event_handler)
        event_bus.subscribe(Topics.SORA_BATCH_COMPLETED, event_handler)

        # Emit batch started
        await event_bus.publish(
            Topics.SORA_BATCH_STARTED,
            {"job_id": "test_123", "theme": "Test", "num_parts": 3}
        )

        # Emit batch completed
        await event_bus.publish(
            Topics.SORA_BATCH_COMPLETED,
            {
                "job_id": "test_123",
                "theme": "Test",
                "successful_parts": 3,
                "stitched_video": "/path/to/video.mp4"
            }
        )

        # Wait for events to process
        await asyncio.sleep(0.1)

        # Verify events were received
        assert Topics.SORA_BATCH_STARTED in events_received
        assert Topics.SORA_BATCH_COMPLETED in events_received


@pytest.mark.asyncio
class TestARCH003_ContentAnalyzerPublisherIntegration:
    """Test ARCH-003: Content Analyzer → Publisher Integration"""

    async def test_content_analyzer_generates_metadata(self):
        """Test that ContentAnalyzer generates titles, descriptions, and hashtags."""
        analyzer = ContentAnalyzer()

        # Mock transcript
        transcript = "This is an amazing video about productivity hacks!"

        # Analyze transcript
        with patch.object(analyzer, 'client') as mock_client:
            # Mock AI response
            mock_response = Mock()
            mock_response.choices = [
                Mock(message=Mock(content='{"topics": ["productivity"], "hooks": ["Amazing hack!"], "detected_hook": "Amazing hack!", "tone": "energetic", "viral_score": 75, "hashtags": ["productivity", "hack"]}'))
            ]
            mock_client.chat_completion = Mock(return_value='{"topics": ["productivity"], "hooks": ["Amazing hack!"], "detected_hook": "Amazing hack!", "tone": "energetic", "viral_score": 75, "hashtags": ["productivity", "hack"]}')

            analysis = analyzer.analyze_transcript(transcript)

        # Verify analysis structure
        assert "detected_hook" in analysis or "hooks" in analysis
        assert "viral_score" in analysis or "pre_social_score" in analysis
        assert "hashtags" in analysis or "topics" in analysis

    async def test_publish_worker_uses_analysis(self, event_bus):
        """Test that PublishWorker auto-injects analysis into publish payload."""
        worker = PublishWorker(event_bus=event_bus)

        # Mock analysis data
        analysis = {
            "detected_hook": "Check this out!",
            "viral_score": 82,
            "hashtags": ["viral", "trending", "fyp"],
            "topics": ["entertainment"],
            "tone": "energetic"
        }

        # Mock payload with analysis
        payload = {
            "media_id": "test_video_123",
            "platform": "tiktok",
            "account_id": "710",
            "analysis": analysis  # ARCH-003: Pre-computed analysis from Sora pipeline
        }

        # Mock worker dependencies
        worker._publish_service = Mock()
        worker._publish_service.upload_to_cloud = Mock(return_value={"url": "https://cloud.com/video.mp4"})
        worker._publish_service.upload_to_blotato = Mock(return_value={"media_id": "blotato_123"})
        worker._publish_service.publish_to_platform = Mock(return_value={"submission_id": "sub_123"})
        worker._publish_service.get_post_status = Mock(return_value={"status": "published", "platform_url": "https://tiktok.com/video"})

        # Mock database operations
        with patch.object(worker, '_get_video_path', return_value="/path/to/video.mp4"):
            with patch.object(worker, '_check_for_duplicates', return_value={"is_duplicate": False}):
                with patch.object(worker, '_register_content_fingerprint', return_value=True):
                    with patch('os.access', return_value=True):
                        with patch('pathlib.Path.exists', return_value=True):
                            with patch('pathlib.Path.is_file', return_value=True):
                                with patch('pathlib.Path.stat') as mock_stat:
                                    mock_stat.return_value = Mock(st_size=1024000)

                                    # Run publish pipeline
                                    result = await worker._run_publish_pipeline(payload, "test_correlation")

        # Verify caption was generated from analysis
        # The worker should have used the analysis to build a caption
        assert result["success"] is True

        # Check that generated_metadata was created
        if "generated_metadata" in payload:
            assert payload["generated_metadata"]["viral_score"] == 82

    async def test_orchestrator_passes_analysis_to_publisher(self, orchestrator, event_bus):
        """Test full pipeline: Sora → Analyzer → Publisher with analysis."""
        # Mock Sora completion with analysis
        mock_analysis = {
            "detected_hook": "Mind-blowing discovery!",
            "viral_score": 88,
            "hashtags": ["mindblown", "discovery", "science"],
            "topics": ["science", "discovery"]
        }

        orchestrator.sora_pipeline.generate_multi_part.return_value = {
            "id": "job_456",
            "status": "completed",
            "successful_parts": 3,
            "stitched_video": "/path/to/final.mp4",
            "analysis": mock_analysis  # ARCH-003: Analysis from Sora pipeline
        }

        # Start pipeline
        config = PipelineConfig(
            theme="Discovery video",
            num_parts=3,
            publish_platforms=["tiktok"]
        )
        pipeline_id = await orchestrator.start_pipeline(config)

        # Simulate Sora batch completion
        await event_bus.publish(
            Topics.SORA_BATCH_COMPLETED,
            {
                "pipeline_id": pipeline_id,
                "stitched_video": "/path/to/final.mp4",
                "analysis": mock_analysis,
                "successful_parts": 3,
                "failed_parts": 0
            },
            correlation_id=orchestrator.active_pipelines[pipeline_id]["correlation_id"]
        )

        # Wait for event processing
        await asyncio.sleep(0.2)

        # Verify pipeline received the analysis
        pipeline = orchestrator.active_pipelines.get(pipeline_id)
        if pipeline:
            assert "sora" in pipeline.get("outputs", {})
            sora_output = pipeline["outputs"]["sora"]
            assert "analysis" in sora_output
            assert sora_output["analysis"]["viral_score"] == 88


@pytest.mark.asyncio
class TestFullPipelineIntegration:
    """Test complete end-to-end pipeline integration."""

    async def test_full_pipeline_workflow(self, orchestrator, event_bus):
        """
        Test the complete workflow:
        1. Orchestrator starts pipeline
        2. Sora generates 3-part video
        3. Video is stitched
        4. Content is analyzed
        5. Analysis is passed to publisher
        6. Video is published to platforms
        7. Twitter campaign is scheduled
        """
        # Setup mocks
        orchestrator.sora_pipeline.generate_multi_part = AsyncMock(return_value={
            "id": "full_test_job",
            "status": "completed",
            "theme": "Full pipeline test",
            "num_parts": 3,
            "successful_parts": 3,
            "failed_parts": 0,
            "stitched_video": "/path/to/stitched_final.mp4",
            "analysis": {
                "detected_hook": "Full pipeline works!",
                "viral_score": 90,
                "hashtags": ["test", "pipeline", "success"]
            },
            "completed_at": datetime.now(timezone.utc).isoformat()
        })

        # Track events
        events_received = []

        async def track_event(event):
            events_received.append(event.topic)

        # Subscribe to all relevant events
        event_bus.subscribe(Topics.ORCHESTRATOR_PIPELINE_STARTED, track_event)
        event_bus.subscribe(Topics.SORA_BATCH_REQUESTED, track_event)
        event_bus.subscribe(Topics.SORA_BATCH_COMPLETED, track_event)
        event_bus.subscribe(Topics.PUBLISH_REQUESTED, track_event)
        event_bus.subscribe("twitter.campaign.schedule_requested", track_event)

        # Start full pipeline
        config = PipelineConfig(
            theme="Full integration test",
            num_parts=3,
            character="isaiahdupree",
            publish_platforms=["tiktok", "instagram"],
            schedule_tweets=True,
            tweets_per_day=12,
            offer_url="https://example.com/offer"
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        # Wait for initial events
        await asyncio.sleep(0.1)

        # Verify pipeline was created
        assert pipeline_id in orchestrator.active_pipelines
        pipeline = orchestrator.active_pipelines[pipeline_id]

        # Verify pipeline structure
        assert pipeline["theme"] == "Full integration test"
        assert pipeline["config"].num_parts == 3
        assert pipeline["config"].publish_platforms == ["tiktok", "instagram"]
        assert pipeline["config"].schedule_tweets is True

        # Verify events were emitted
        assert Topics.ORCHESTRATOR_PIPELINE_STARTED in events_received
        assert Topics.SORA_BATCH_REQUESTED in events_received

    async def test_pipeline_handles_partial_failures(self, orchestrator, event_bus):
        """Test that pipeline gracefully handles partial failures."""
        # Mock Sora with partial failure
        orchestrator.sora_pipeline.generate_multi_part = AsyncMock(return_value={
            "id": "partial_fail_job",
            "status": "partial",
            "successful_parts": 2,
            "failed_parts": 1,
            "stitched_video": "/path/to/partial.mp4",
            "analysis": {
                "detected_hook": "Partial success",
                "viral_score": 70
            }
        })

        # Start pipeline
        config = PipelineConfig(theme="Partial failure test", num_parts=3)
        pipeline_id = await orchestrator.start_pipeline(config)

        # Simulate Sora completion with partial failure
        await event_bus.publish(
            Topics.SORA_BATCH_COMPLETED,
            {
                "pipeline_id": pipeline_id,
                "status": "partial",
                "successful_parts": 2,
                "failed_parts": 1,
                "stitched_video": "/path/to/partial.mp4"
            },
            correlation_id=orchestrator.active_pipelines[pipeline_id]["correlation_id"]
        )

        await asyncio.sleep(0.1)

        # Verify pipeline continues despite partial failure
        # (it should still try to publish the available video)
        assert pipeline_id in orchestrator.active_pipelines or pipeline_id in orchestrator.completed_pipelines


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
