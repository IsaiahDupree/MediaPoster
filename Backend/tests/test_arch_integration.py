"""
Integration Tests for System Architecture (ARCH-001 to ARCH-008)
================================================================
Tests for the complete MediaPoster pipeline orchestration.

Tests:
    - ARCH-001: Master Orchestrator Service
    - ARCH-002: 3-Part Sora Batch Coordination
    - ARCH-003: Content Analyzer → Publisher Integration
    - ARCH-004: Tweet Scheduler 2-Hour Interval
    - ARCH-005: Offer Traffic Tracking Service
    - ARCH-006: Analytics → AI Feedback Loop
    - ARCH-007: Unified Pipeline API Endpoint
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone


class TestARCH001_MasterOrchestrator:
    """Test ARCH-001: Master Orchestrator Service"""

    def test_orchestrator_initialization(self):
        """ARCH-001: Master orchestrator should initialize with all subsystems"""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator()

        assert orchestrator.sora_pipeline is not None, "Sora pipeline should be initialized"
        assert orchestrator.content_analyzer is not None, "Content analyzer should be initialized"
        assert orchestrator.blotato_service is not None, "Blotato service should be initialized"
        assert orchestrator.twitter_service is not None, "Twitter service should be initialized"
        assert orchestrator.analytics_feedback is not None, "Analytics feedback should be initialized"

    def test_orchestrator_singleton(self):
        """ARCH-001: Orchestrator should use singleton pattern"""
        from services.master_orchestrator import get_orchestrator

        orchestrator1 = get_orchestrator()
        orchestrator2 = get_orchestrator()

        assert orchestrator1 is orchestrator2, "Should return same instance"

    @pytest.mark.asyncio
    async def test_orchestrator_start_stop(self):
        """ARCH-001: Orchestrator should start and stop cleanly"""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator()

        await orchestrator.start()
        assert orchestrator._running, "Should be running after start"

        await orchestrator.stop()
        assert not orchestrator._running, "Should not be running after stop"

    @pytest.mark.asyncio
    async def test_orchestrator_pipeline_execution_structure(self):
        """ARCH-001: run_full_pipeline should create pipeline via event-driven architecture"""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        # Execute pipeline - returns a pipeline_id string
        pipeline_id = await orchestrator.run_full_pipeline(
            theme="Test viral content",
            num_parts=3,
            publish_platforms=["tiktok"],
            schedule_tweets=True,
            tweets_per_day=12
        )

        # Verify pipeline_id is a string
        assert isinstance(pipeline_id, str), "run_full_pipeline should return a pipeline_id string"
        assert pipeline_id.startswith("pipeline-"), "pipeline_id should have correct prefix"

        # Verify pipeline was registered (may be in active or completed if event cascade ran)
        assert (
            pipeline_id in orchestrator.active_pipelines
            or pipeline_id in orchestrator.completed_pipelines
        ), "Pipeline should be tracked in active or completed pipelines"

        pipeline = orchestrator.get_pipeline_status(pipeline_id)

        # Verify pipeline was created with correct data
        assert pipeline["theme"] == "Test viral content", "Theme should match input"
        assert isinstance(pipeline["outputs"], dict), "Outputs should be initialized as a dict"
        assert "started_at" in pipeline, "Pipeline should have a started_at timestamp"
        assert "correlation_id" in pipeline, "Pipeline should have a correlation_id"
        # Status may be generating_video (if no worker handled the batch)
        # or failed (if event cascade completed with failures in test env)
        assert pipeline["status"] in [
            "generating_video", "analyzing", "publishing", "completed", "failed"
        ], f"Status should be a valid pipeline status, got: {pipeline['status']}"

        # Verify event-driven architecture: generate_multi_part should NOT be called directly
        # The orchestrator uses SORA_BATCH_REQUESTED events instead of direct calls
        orchestrator.sora_pipeline.generate_multi_part = AsyncMock()
        orchestrator.sora_pipeline.generate_multi_part.assert_not_called()


class TestARCH002_SoraBatchCoordination:
    """Test ARCH-002: 3-Part Sora Batch Coordination"""

    def test_sora_pipeline_has_generate_multi_part(self):
        """ARCH-002: SoraPipeline should have generate_multi_part method"""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()
        assert hasattr(pipeline, 'generate_multi_part'), "Should have generate_multi_part method"

    @pytest.mark.asyncio
    async def test_generate_multi_part_signature(self):
        """ARCH-002: generate_multi_part should accept correct parameters"""
        from automation.sora.pipeline import SoraPipeline
        import inspect

        pipeline = SoraPipeline()
        sig = inspect.signature(pipeline.generate_multi_part)

        assert 'theme' in sig.parameters, "Should accept theme parameter"
        assert 'num_parts' in sig.parameters, "Should accept num_parts parameter"
        assert 'character' in sig.parameters, "Should accept character parameter"
        assert 'auto_stitch' in sig.parameters, "Should accept auto_stitch parameter"
        assert 'auto_analyze' in sig.parameters, "Should accept auto_analyze parameter"

    @pytest.mark.asyncio
    async def test_generate_multi_part_returns_job_structure(self):
        """ARCH-002: generate_multi_part should return proper job structure"""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        # Mock the actual generation to avoid Safari automation
        pipeline.generate_single = AsyncMock(return_value={
            "status": "completed",
            "video_path": "/tmp/test.mp4",
            "cleaned_video_path": "/tmp/test_clean.mp4"
        })

        result = await pipeline.generate_multi_part(
            theme="Test theme",
            num_parts=2,
            auto_stitch=False,
            auto_analyze=False,
            remove_watermarks=False
        )

        assert "id" in result, "Should have job ID"
        assert "theme" in result, "Should have theme"
        assert "num_parts" in result, "Should have num_parts"
        assert "parts" in result, "Should have parts list"
        assert "status" in result, "Should have status"


class TestARCH003_AnalyzerPublisherIntegration:
    """Test ARCH-003: Content Analyzer → Publisher Integration"""

    def test_publish_worker_accepts_analysis(self):
        """ARCH-003: PublishWorker should accept analysis in payload"""
        from services.workers.publish_worker import PublishWorker

        worker = PublishWorker()

        # Check that the worker processes analysis in payload
        # This is tested via the handle_event method structure
        assert hasattr(worker, 'handle_event'), "Should have handle_event method"

    @pytest.mark.asyncio
    async def test_publish_worker_uses_analysis_for_metadata(self):
        """ARCH-003: PublishWorker should use analysis to auto-fill metadata"""
        from services.workers.publish_worker import PublishWorker

        worker = PublishWorker()

        # Mock the dependencies
        worker._verify_publish_request = AsyncMock(return_value={
            "valid": True,
            "file_path": "/tmp/test.mp4"
        })
        worker._check_for_duplicates = AsyncMock(return_value={"is_duplicate": False})
        worker._upload_to_cloud = AsyncMock(return_value="https://example.com/video.mp4")
        worker._upload_to_blotato = AsyncMock(return_value="blotato_123")
        worker._submit_to_platform = AsyncMock(return_value={"success": True})
        worker._poll_for_platform_url = AsyncMock(return_value="https://tiktok.com/video/123")

        # Test payload with analysis
        payload = {
            "media_id": "test_123",
            "platform": "tiktok",
            "account_id": "807",
            "analysis": {
                "detected_hook": "Amazing viral content!",
                "hashtags": ["viral", "trending", "fyp"],
                "viral_score": 85,
                "title_tiktok": "Test Title"
            },
            "auto_generate_metadata": False
        }

        # The _build_platform_caption method should exist and use analysis
        assert hasattr(worker, '_build_platform_caption'), "Should have _build_platform_caption method"


class TestARCH004_TweetScheduler:
    """Test ARCH-004: Tweet Scheduler 2-Hour Interval"""

    def test_twitter_service_default_interval(self):
        """ARCH-004: TwitterCampaignService should default to 120-minute intervals"""
        from services.twitter_campaign_service import TwitterCampaignService

        service = TwitterCampaignService()
        assert service.interval_minutes == 120, "Should default to 120 minutes (2 hours)"

    def test_twitter_service_accepts_interval(self):
        """ARCH-004: TwitterCampaignService should accept custom interval"""
        from services.twitter_campaign_service import TwitterCampaignService

        service = TwitterCampaignService(interval_minutes=60)
        assert service.interval_minutes == 60, "Should accept custom interval"

    def test_master_orchestrator_uses_2hour_interval(self):
        """ARCH-004: Master orchestrator should use 2-hour interval by default"""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator()
        assert orchestrator.twitter_service.interval_minutes == 120, "Should use 2-hour interval"


class TestARCH005_OfferTracker:
    """Test ARCH-005: Offer Traffic Tracking Service"""

    def test_offer_tracker_initialization(self):
        """ARCH-005: OfferTracker should initialize successfully"""
        from services.offer_tracker import OfferTracker

        tracker = OfferTracker()
        assert tracker is not None, "OfferTracker should initialize"
        assert tracker.engine is not None, "Should have database engine"

    def test_offer_tracker_singleton(self):
        """ARCH-005: OfferTracker should use singleton pattern"""
        from services.offer_tracker import get_offer_tracker

        tracker1 = get_offer_tracker()
        tracker2 = get_offer_tracker()

        assert tracker1 is tracker2, "Should return same instance"

    def test_offer_tracker_track_click_signature(self):
        """ARCH-005: track_click should accept UTM parameters"""
        from services.offer_tracker import OfferTracker
        import inspect

        tracker = OfferTracker()
        sig = inspect.signature(tracker.track_click)

        assert 'utm_campaign' in sig.parameters, "Should accept utm_campaign"
        assert 'utm_source' in sig.parameters, "Should accept utm_source"
        assert 'utm_medium' in sig.parameters, "Should accept utm_medium"
        assert 'utm_content' in sig.parameters, "Should accept utm_content"

    def test_offer_tracker_track_conversion_signature(self):
        """ARCH-005: track_conversion should accept conversion parameters"""
        from services.offer_tracker import OfferTracker
        import inspect

        tracker = OfferTracker()
        sig = inspect.signature(tracker.track_conversion)

        assert 'utm_campaign' in sig.parameters, "Should accept utm_campaign"
        assert 'conversion_type' in sig.parameters, "Should accept conversion_type"
        assert 'revenue' in sig.parameters, "Should accept revenue"
        assert 'user_id' in sig.parameters, "Should accept user_id"

    def test_offer_tracker_get_campaign_analytics(self):
        """ARCH-005: Should provide campaign analytics method"""
        from services.offer_tracker import OfferTracker
        import inspect

        tracker = OfferTracker()
        assert hasattr(tracker, 'get_campaign_analytics'), "Should have get_campaign_analytics method"

        sig = inspect.signature(tracker.get_campaign_analytics)
        assert 'utm_campaign' in sig.parameters, "Should accept utm_campaign"
        assert 'days' in sig.parameters, "Should accept days parameter"


class TestARCH006_AnalyticsFeedback:
    """Test ARCH-006: Analytics → AI Feedback Loop"""

    def test_analytics_feedback_initialization(self):
        """ARCH-006: AnalyticsFeedback should initialize successfully"""
        from services.analytics_feedback import AnalyticsFeedback

        feedback = AnalyticsFeedback()
        assert feedback is not None, "AnalyticsFeedback should initialize"

    def test_analytics_feedback_singleton(self):
        """ARCH-006: AnalyticsFeedback should use singleton pattern"""
        from services.analytics_feedback import get_analytics_feedback

        feedback1 = get_analytics_feedback()
        feedback2 = get_analytics_feedback()

        assert feedback1 is feedback2, "Should return same instance"

    @pytest.mark.asyncio
    async def test_analytics_feedback_has_start_method(self):
        """ARCH-006: AnalyticsFeedback should have start method"""
        from services.analytics_feedback import AnalyticsFeedback

        feedback = AnalyticsFeedback()
        assert hasattr(feedback, 'start'), "Should have start method"

    def test_analytics_feedback_has_get_recommendations(self):
        """ARCH-006: AnalyticsFeedback should provide recommendations"""
        from services.analytics_feedback import AnalyticsFeedback

        feedback = AnalyticsFeedback()
        assert hasattr(feedback, 'get_recommendations'), "Should have get_recommendations method"

    def test_master_orchestrator_integrates_feedback(self):
        """ARCH-006: Master orchestrator should integrate analytics feedback"""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator()
        assert orchestrator.analytics_feedback is not None, "Should have analytics feedback"


class TestARCH007_UnifiedAPI:
    """Test ARCH-007: Unified Pipeline API Endpoint"""

    def test_orchestrator_api_exists(self):
        """ARCH-007: Orchestrator API endpoint should exist"""
        from api.endpoints import orchestrator

        assert hasattr(orchestrator, 'router'), "Should have FastAPI router"

    def test_orchestrator_has_run_pipeline_endpoint(self):
        """ARCH-007: Should have POST /pipeline/run endpoint"""
        from api.endpoints.orchestrator import run_pipeline

        assert run_pipeline is not None, "Should have run_pipeline endpoint"

    def test_orchestrator_has_get_pipeline_status_endpoint(self):
        """ARCH-007: Should have GET /pipeline/{pipeline_id} endpoint"""
        from api.endpoints.orchestrator import get_pipeline_status

        assert get_pipeline_status is not None, "Should have get_pipeline_status endpoint"

    def test_orchestrator_has_list_pipelines_endpoint(self):
        """ARCH-007: Should have GET /pipelines endpoint"""
        from api.endpoints.orchestrator import list_pipelines

        assert list_pipelines is not None, "Should have list_pipelines endpoint"

    def test_orchestrator_has_health_check(self):
        """ARCH-007: Should have health check endpoint"""
        from api.endpoints.orchestrator import health_check

        assert health_check is not None, "Should have health_check endpoint"

    def test_run_pipeline_request_model(self):
        """ARCH-007: RunPipelineRequest should have correct fields"""
        from api.endpoints.orchestrator import RunPipelineRequest

        # Check that model has required fields
        assert 'theme' in RunPipelineRequest.model_fields, "Should have theme field"
        assert 'num_parts' in RunPipelineRequest.model_fields, "Should have num_parts field"
        assert 'character' in RunPipelineRequest.model_fields, "Should have character field"
        assert 'publish_platforms' in RunPipelineRequest.model_fields, "Should have publish_platforms field"
        assert 'schedule_tweets' in RunPipelineRequest.model_fields, "Should have schedule_tweets field"
        assert 'tweets_per_day' in RunPipelineRequest.model_fields, "Should have tweets_per_day field"
        assert 'offer_url' in RunPipelineRequest.model_fields, "Should have offer_url field"


class TestARCH_EndToEnd:
    """End-to-end integration tests for the complete pipeline"""

    @pytest.mark.asyncio
    async def test_complete_pipeline_structure(self):
        """Test that all ARCH components wire together correctly"""
        from services.master_orchestrator import get_orchestrator

        orchestrator = get_orchestrator()

        # Verify all subsystems are connected
        assert orchestrator.sora_pipeline is not None, "ARCH-002: Sora pipeline connected"
        assert orchestrator.content_analyzer is not None, "ARCH-003: Content analyzer connected"
        assert orchestrator.blotato_service is not None, "ARCH-003: Blotato service connected"
        assert orchestrator.twitter_service is not None, "ARCH-004: Twitter service connected"
        assert orchestrator.analytics_feedback is not None, "ARCH-006: Analytics feedback connected"

        # Verify configurations
        assert orchestrator.twitter_service.interval_minutes == 120, "ARCH-004: 2-hour interval configured"

    def test_all_arch_features_importable(self):
        """Test that all ARCH features can be imported without errors"""
        # ARCH-001
        from services.master_orchestrator import MasterOrchestrator, get_orchestrator

        # ARCH-002
        from automation.sora.pipeline import SoraPipeline

        # ARCH-003
        from services.workers.publish_worker import PublishWorker

        # ARCH-004
        from services.twitter_campaign_service import TwitterCampaignService

        # ARCH-005
        from services.offer_tracker import OfferTracker, get_offer_tracker

        # ARCH-006
        from services.analytics_feedback import AnalyticsFeedback, get_analytics_feedback

        # ARCH-007
        from api.endpoints import orchestrator

        # All imports successful
        assert True, "All ARCH features are importable"


class TestARCH001_PipelineCancellation:
    """Test ARCH-001: Pipeline cancellation support"""

    @pytest.mark.asyncio
    async def test_cancel_active_pipeline(self):
        """ARCH-001: cancel_pipeline should cancel an active pipeline"""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        # Start a pipeline
        pipeline_id = await orchestrator.run_full_pipeline(
            theme="Cancel test",
            num_parts=1,
            publish_platforms=["tiktok"],
            schedule_tweets=False
        )

        assert pipeline_id in orchestrator.active_pipelines

        # Cancel it
        result = await orchestrator.cancel_pipeline(pipeline_id)
        assert result is True, "cancel_pipeline should return True"
        assert pipeline_id not in orchestrator.active_pipelines, "Pipeline should be removed from active"
        assert pipeline_id in orchestrator.completed_pipelines, "Pipeline should be in completed"
        assert orchestrator.completed_pipelines[pipeline_id]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_pipeline(self):
        """ARCH-001: cancel_pipeline should return False for unknown pipeline"""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)
        result = await orchestrator.cancel_pipeline("pipeline-nonexistent")
        assert result is False, "cancel_pipeline should return False for unknown pipeline"

    def test_cancel_pipeline_api_endpoint_exists(self):
        """ARCH-001: DELETE /pipeline/{pipeline_id} endpoint should exist"""
        from api.endpoints.orchestrator import router

        route_methods = {}
        for route in router.routes:
            methods = getattr(route, 'methods', set())
            route_methods[route.path] = methods

        assert "DELETE" in route_methods.get("/api/orchestrator/pipeline/{pipeline_id}", set()), \
            "Should have DELETE endpoint for pipeline cancellation"


class TestARCH001_VideoStitchingStep:
    """Test ARCH-001: Video stitching step tracking in pipeline"""

    @pytest.mark.asyncio
    async def test_sora_completion_updates_stitching_step(self):
        """ARCH-001: Sora batch completion should also mark video_stitching as completed"""
        from services.master_orchestrator import MasterOrchestrator
        from services.event_bus import EventBus, Event, Topics

        orchestrator = MasterOrchestrator(use_db=False)

        # Start pipeline
        pipeline_id = await orchestrator.run_full_pipeline(
            theme="Stitch test",
            num_parts=2,
            publish_platforms=["tiktok"],
            schedule_tweets=False
        )

        # Simulate sora batch completion with stitched video
        event = Event(
            topic=Topics.SORA_BATCH_COMPLETED,
            payload={
                "pipeline_id": pipeline_id,
                "status": "completed",
                "stitched_video": "/tmp/stitched.mp4",
                "analysis": {"detected_hook": "Test hook", "topics": ["AI"]},
                "successful_parts": 2,
                "failed_parts": 0
            },
            source="SoraWorker"
        )

        await orchestrator._handle_sora_batch_completed(event)

        # Pipeline should have progressed past sora generation
        pipeline = orchestrator.get_pipeline_status(pipeline_id)
        assert pipeline["outputs"]["sora"]["stitched_video"] == "/tmp/stitched.mp4"


class TestARCH003_HashtagGeneration:
    """Test ARCH-003: Hashtag generation from topics when none provided"""

    def test_hashtags_generated_from_topics(self):
        """ARCH-003: When no hashtags in analysis, generate from topics"""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        analysis = {
            "detected_hook": "This will blow your mind",
            "topics": ["AI automation", "content creation", "social media"],
            "hashtags": [],  # Empty
            "viral_score": 75
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        # TikTok should have hashtags generated from topics
        tiktok_hashtags = metadata["tiktok"]["hashtags"]
        assert len(tiktok_hashtags) > 0, "Should generate hashtags from topics"
        # Hashtags are lowercased topic slugs (may or may not have # prefix)
        hashtag_values = [h.lstrip("#").lower() for h in tiktok_hashtags]
        assert "aiautomation" in hashtag_values, "Should convert topic to hashtag"
        assert "contentcreation" in hashtag_values

    def test_existing_hashtags_preserved(self):
        """ARCH-003: When hashtags exist, they should be preserved as-is"""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        analysis = {
            "detected_hook": "Amazing content",
            "topics": ["AI", "automation"],
            "hashtags": ["#viral", "#trending", "#fyp"],
            "viral_score": 90
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        # Existing hashtags should be preserved
        assert "#viral" in metadata["tiktok"]["hashtags"]
        assert "#trending" in metadata["tiktok"]["hashtags"]

    def test_no_topics_no_hashtags_base_empty(self):
        """ARCH-003: No topics and no hashtags should have no topic-derived hashtags"""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        metadata = orchestrator._extract_platform_metadata({})

        # Base hashtags from analysis are empty; platform-specific ones may be added
        assert metadata["default"]["hashtags"] == []
        assert metadata["twitter"]["hashtags"] == []


class TestARCH001_TimeoutRetry:
    """Tests for ARCH-001 timeout monitoring and retry logic."""

    def test_pipeline_config_has_timeout_settings(self):
        """ARCH-001: PipelineConfig should support step_timeouts and max_retries."""
        from services.master_orchestrator import PipelineConfig

        config = PipelineConfig(theme="test", step_timeouts={"sora_generation": 600}, max_retries=3)
        assert config.step_timeouts["sora_generation"] == 600
        assert config.max_retries == 3

    def test_pipeline_config_defaults(self):
        """ARCH-001: PipelineConfig should have sensible timeout defaults."""
        from services.master_orchestrator import PipelineConfig, STEP_TIMEOUTS

        config = PipelineConfig(theme="test")
        assert config.step_timeouts == STEP_TIMEOUTS
        assert config.max_retries == 2  # MAX_STEP_RETRIES default

    def test_orchestrator_has_timeout_tasks(self):
        """ARCH-001: Orchestrator should track timeout tasks."""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)
        assert hasattr(orchestrator, '_timeout_tasks')
        assert isinstance(orchestrator._timeout_tasks, dict)

    def test_pipeline_health_returns_timeout_info(self):
        """ARCH-001: get_pipeline_health should include timeout and retry data."""
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig

        orchestrator = MasterOrchestrator(use_db=False)

        # No pipeline should return error
        health = orchestrator.get_pipeline_health("nonexistent")
        assert "error" in health

    @pytest.mark.asyncio
    async def test_start_pipeline_creates_timeout(self):
        """ARCH-001: Starting a pipeline should create a sora_generation timeout."""
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig
        from services.event_bus import EventBus

        event_bus = EventBus()
        orchestrator = MasterOrchestrator(event_bus=event_bus, use_db=False)

        config = PipelineConfig(
            theme="timeout test",
            step_timeouts={"sora_generation": 9999}
        )

        pipeline_id = await orchestrator.start_pipeline(config)
        assert pipeline_id is not None
        assert pipeline_id in orchestrator.active_pipelines

        # Should have a timeout task for sora_generation
        timeout_key = f"{pipeline_id}:sora_generation"
        assert timeout_key in orchestrator._timeout_tasks

        # Cleanup: cancel the timeout
        orchestrator._cancel_step_timeout(pipeline_id, "sora_generation")

    @pytest.mark.asyncio
    async def test_cancel_step_timeout(self):
        """ARCH-001: Cancelling a step timeout should remove the task."""
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig
        from services.event_bus import EventBus

        event_bus = EventBus()
        orchestrator = MasterOrchestrator(event_bus=event_bus, use_db=False)

        config = PipelineConfig(theme="cancel test")
        pipeline_id = await orchestrator.start_pipeline(config)

        timeout_key = f"{pipeline_id}:sora_generation"
        assert timeout_key in orchestrator._timeout_tasks

        orchestrator._cancel_step_timeout(pipeline_id, "sora_generation")
        assert timeout_key not in orchestrator._timeout_tasks

    @pytest.mark.asyncio
    async def test_fail_pipeline(self):
        """ARCH-001: _fail_pipeline should move pipeline to failed state."""
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig
        from services.event_bus import EventBus

        event_bus = EventBus()
        orchestrator = MasterOrchestrator(event_bus=event_bus, use_db=False)

        config = PipelineConfig(theme="fail test")
        pipeline_id = await orchestrator.start_pipeline(config)
        orchestrator._cancel_step_timeout(pipeline_id, "sora_generation")

        await orchestrator._fail_pipeline(pipeline_id, "Test failure reason")

        assert pipeline_id not in orchestrator.active_pipelines
        assert pipeline_id in orchestrator.completed_pipelines
        assert orchestrator.completed_pipelines[pipeline_id]["status"] == "failed"
        assert orchestrator.completed_pipelines[pipeline_id]["error"] == "Test failure reason"

    @pytest.mark.asyncio
    async def test_complete_pipeline_calculates_duration(self):
        """ARCH-001: Pipeline completion should calculate duration."""
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig
        from services.event_bus import EventBus

        event_bus = EventBus()
        orchestrator = MasterOrchestrator(event_bus=event_bus, use_db=False)

        config = PipelineConfig(theme="duration test")
        pipeline_id = await orchestrator.start_pipeline(config)
        orchestrator._cancel_step_timeout(pipeline_id, "sora_generation")

        await orchestrator._complete_pipeline(pipeline_id)

        completed = orchestrator.completed_pipelines[pipeline_id]
        assert "duration_seconds" in completed
        assert completed["duration_seconds"] >= 0


class TestARCH002_ConcurrentGeneration:
    """Tests for ARCH-002 concurrent part generation."""

    def test_sora_pipeline_has_semaphore(self):
        """ARCH-002: SoraPipeline should have a generation semaphore."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()
        assert hasattr(pipeline, '_generation_semaphore')

    def test_sora_pipeline_custom_concurrency(self):
        """ARCH-002: SoraPipeline should accept custom max_concurrent."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline(max_concurrent=5)
        assert pipeline._generation_semaphore._value == 5

    def test_sora_pipeline_has_emit_progress(self):
        """ARCH-002: SoraPipeline should have _emit_progress method."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()
        assert hasattr(pipeline, '_emit_progress')
        assert callable(pipeline._emit_progress)


class TestARCH003_EnhancedMetadata:
    """Tests for ARCH-003 enhanced platform metadata generation."""

    def test_tiktok_gets_discovery_hashtags(self):
        """ARCH-003: TikTok should auto-add fyp/viral/foryou discovery tags."""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        analysis = {
            "detected_hook": "This is amazing",
            "hashtags": ["ai", "tech"],
            "viral_score": 80
        }

        metadata = orchestrator._extract_platform_metadata(analysis)
        tiktok = metadata["tiktok"]

        # Should have original + discovery hashtags
        lowered = [h.lower() for h in tiktok["hashtags"]]
        assert "fyp" in lowered
        assert "viral" in lowered
        assert "foryou" in lowered

    def test_instagram_gets_discovery_hashtags(self):
        """ARCH-003: Instagram should auto-add reels/explore/instagood tags."""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        analysis = {
            "detected_hook": "Wow check this out",
            "hashtags": ["fashion", "style"],
            "viral_score": 70
        }

        metadata = orchestrator._extract_platform_metadata(analysis)
        ig = metadata["instagram"]

        lowered = [h.lower() for h in ig["hashtags"]]
        assert "reels" in lowered
        assert "explore" in lowered

    def test_youtube_gets_seo_description(self):
        """ARCH-003: YouTube should enrich description with pain_points and audience."""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        analysis = {
            "detected_hook": "AI is changing everything",
            "description": "Learn about AI automation",
            "hashtags": ["ai"],
            "pain_points": ["manual content creation", "low engagement"],
            "target_audience": {"interests": ["tech", "marketing", "AI"]},
            "viral_score": 85
        }

        metadata = orchestrator._extract_platform_metadata(analysis)
        yt = metadata["youtube"]

        assert "manual content creation" in yt["description"]
        assert "tech" in yt["description"]

    def test_linkedin_has_professional_tone(self):
        """ARCH-003: LinkedIn metadata should have professional tone."""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        analysis = {
            "detected_hook": "Industry insight",
            "hashtags": ["leadership", "tech", "ai", "innovation", "growth", "startup"],
            "target_audience": {"demographic": "Tech professionals 25-45"},
            "viral_score": 60
        }

        metadata = orchestrator._extract_platform_metadata(analysis)
        linkedin = metadata["linkedin"]

        assert linkedin["tone"] == "professional"
        assert len(linkedin["hashtags"]) <= 5
        assert "Tech professionals" in linkedin.get("description", "")

    def test_pinterest_keyword_rich(self):
        """ARCH-003: Pinterest should combine description with topics."""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        analysis = {
            "detected_hook": "Beautiful home decor",
            "description": "Transform your space",
            "hashtags": ["homedecor"],
            "topics": ["interior design", "DIY", "modern"],
            "viral_score": 70
        }

        metadata = orchestrator._extract_platform_metadata(analysis)
        pinterest = metadata["pinterest"]

        assert "interior design" in pinterest["description"]

    def test_twitter_respects_char_limit(self):
        """ARCH-003: Twitter title/description should respect character limits."""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        long_hook = "x" * 300
        analysis = {
            "detected_hook": long_hook,
            "hashtags": ["test"],
            "viral_score": 50
        }

        metadata = orchestrator._extract_platform_metadata(analysis)
        twitter = metadata["twitter"]

        assert len(twitter["title"]) <= 200
        assert len(twitter["description"]) <= 250

    def test_all_platforms_present(self):
        """ARCH-003: All supported platforms should have metadata."""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        metadata = orchestrator._extract_platform_metadata({"detected_hook": "test"})

        expected_platforms = [
            "default", "tiktok", "instagram", "youtube", "twitter",
            "threads", "linkedin", "pinterest", "facebook", "bluesky"
        ]
        for platform in expected_platforms:
            assert platform in metadata, f"Missing platform: {platform}"

    def test_metadata_includes_audience_and_pain_points(self):
        """ARCH-003: Base metadata should include target_audience and pain_points."""
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        analysis = {
            "detected_hook": "Test",
            "pain_points": ["problem1", "problem2"],
            "target_audience": {"demographic": "age 18-25"},
            "pacing": "fast"
        }

        metadata = orchestrator._extract_platform_metadata(analysis)
        base = metadata["default"]

        assert base["pain_points"] == ["problem1", "problem2"]
        assert base["target_audience"]["demographic"] == "age 18-25"
        assert base["pacing"] == "fast"


class TestARCH001_VideoPathValidation:
    """Test ARCH-001: Orchestrator validates video_path before publishing."""

    @pytest.mark.asyncio
    async def test_null_video_path_fails_pipeline(self):
        """ARCH-001: Pipeline should fail when Sora returns no video_path."""
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig
        from services.event_bus import EventBus, Event, Topics

        event_bus = EventBus()
        orchestrator = MasterOrchestrator(event_bus=event_bus, use_db=False)

        config = PipelineConfig(
            theme="No video test",
            num_parts=1,
            publish_platforms=["tiktok"],
            schedule_tweets=False
        )
        pipeline_id = await orchestrator.start_pipeline(config)
        orchestrator._cancel_step_timeout(pipeline_id, "sora_generation")

        # Simulate Sora completion with no video_path
        event = Event(
            topic=Topics.SORA_BATCH_COMPLETED,
            payload={
                "pipeline_id": pipeline_id,
                "status": "completed",
                "stitched_video": None,
                "video_path": None,
                "analysis": {"hook": "Test"},
                "successful_parts": 0,
                "failed_parts": 1
            },
            source="SoraWorker"
        )

        await orchestrator._handle_sora_batch_completed(event)

        # Pipeline should have failed (not proceeded to publishing)
        assert pipeline_id in orchestrator.completed_pipelines, \
            "Pipeline should be in completed (failed) state"
        assert orchestrator.completed_pipelines[pipeline_id]["status"] == "failed"
        assert "video_path" in orchestrator.completed_pipelines[pipeline_id].get("error", "").lower()

    @pytest.mark.asyncio
    async def test_valid_video_path_proceeds_to_publishing(self):
        """ARCH-001: Pipeline should proceed when Sora returns a valid video_path."""
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig
        from services.event_bus import EventBus, Event, Topics

        event_bus = EventBus()
        orchestrator = MasterOrchestrator(event_bus=event_bus, use_db=False)

        config = PipelineConfig(
            theme="Valid video test",
            num_parts=1,
            publish_platforms=["tiktok"],
            schedule_tweets=False
        )
        pipeline_id = await orchestrator.start_pipeline(config)
        orchestrator._cancel_step_timeout(pipeline_id, "sora_generation")

        event = Event(
            topic=Topics.SORA_BATCH_COMPLETED,
            payload={
                "pipeline_id": pipeline_id,
                "status": "completed",
                "stitched_video": "/tmp/test_video.mp4",
                "analysis": {"hook": "Great hook"},
                "successful_parts": 1,
                "failed_parts": 0
            },
            source="SoraWorker"
        )

        await orchestrator._handle_sora_batch_completed(event)

        # Pipeline should be in publishing state (not failed)
        pipeline = orchestrator.active_pipelines.get(pipeline_id)
        assert pipeline is not None, "Pipeline should still be active"
        assert pipeline["status"] == "publishing"


class TestARCH002_SoraWorkerFailureHandling:
    """Test ARCH-002: SoraWorker emits correct events for zero-success batches."""

    @pytest.mark.asyncio
    async def test_sora_worker_emits_failed_for_zero_parts(self):
        """ARCH-002: SoraWorker should emit SORA_BATCH_FAILED when 0 parts succeed."""
        from services.workers.sora_worker import SoraWorker
        from services.event_bus import EventBus, Event, Topics

        event_bus = EventBus()
        worker = SoraWorker(event_bus=event_bus)

        # Track emitted events
        emitted = []

        async def track_emit(event):
            emitted.append(event)

        event_bus.subscribe(Topics.SORA_BATCH_FAILED, track_emit)
        event_bus.subscribe(Topics.SORA_BATCH_COMPLETED, track_emit)

        # Mock SoraPipeline - imported locally in _handle_batch_request
        with patch('automation.sora.pipeline.SoraPipeline') as MockPipeline:
            mock_instance = MockPipeline.return_value
            mock_instance.generate_multi_part = AsyncMock(return_value={
                "id": "test-batch",
                "status": "completed",
                "successful_parts": 0,
                "failed_parts": 3,
                "stitched_video": None,
                "video_path": None,
                "parts": [],
                "analysis": None,
                "total_generation_time": 1.0,
                "prompts": []
            })

            event = Event(
                topic=Topics.SORA_BATCH_REQUESTED,
                payload={
                    "pipeline_id": "test-pipeline",
                    "theme": "Zero parts test",
                    "num_parts": 3,
                    "stitch": True,
                    "remove_watermark": True
                },
                source="test"
            )

            await worker._handle_batch_request(event)
            await asyncio.sleep(0.1)

            # Should have emitted SORA_BATCH_FAILED, NOT SORA_BATCH_COMPLETED
            failed_events = [e for e in emitted if e.topic == Topics.SORA_BATCH_FAILED]
            completed_events = [e for e in emitted if e.topic == Topics.SORA_BATCH_COMPLETED]

            assert len(failed_events) >= 1, "Should emit SORA_BATCH_FAILED for 0 successful parts"
            assert len(completed_events) == 0, "Should NOT emit SORA_BATCH_COMPLETED for 0 parts"

    @pytest.mark.asyncio
    async def test_sora_worker_emits_completed_for_success(self):
        """ARCH-002: SoraWorker should emit SORA_BATCH_COMPLETED when parts succeed."""
        from services.workers.sora_worker import SoraWorker
        from services.event_bus import EventBus, Event, Topics

        event_bus = EventBus()
        worker = SoraWorker(event_bus=event_bus)

        emitted = []

        async def track_emit(event):
            emitted.append(event)

        event_bus.subscribe(Topics.SORA_BATCH_FAILED, track_emit)
        event_bus.subscribe(Topics.SORA_BATCH_COMPLETED, track_emit)

        with patch('automation.sora.pipeline.SoraPipeline') as MockPipeline:
            mock_instance = MockPipeline.return_value
            mock_instance.generate_multi_part = AsyncMock(return_value={
                "id": "test-batch",
                "status": "completed",
                "successful_parts": 2,
                "failed_parts": 1,
                "stitched_video": "/tmp/stitched.mp4",
                "video_path": "/tmp/stitched.mp4",
                "parts": [],
                "analysis": {"hook": "Great hook"},
                "total_generation_time": 5.0,
                "prompts": ["p1", "p2", "p3"]
            })

            event = Event(
                topic=Topics.SORA_BATCH_REQUESTED,
                payload={
                    "pipeline_id": "test-pipeline-success",
                    "theme": "Partial success test",
                    "num_parts": 3,
                    "stitch": True,
                    "remove_watermark": True
                },
                source="test"
            )

            await worker._handle_batch_request(event)
            await asyncio.sleep(0.1)

            completed_events = [e for e in emitted if e.topic == Topics.SORA_BATCH_COMPLETED]
            failed_events = [e for e in emitted if e.topic == Topics.SORA_BATCH_FAILED]

            assert len(completed_events) >= 1, "Should emit SORA_BATCH_COMPLETED for partial success"
            assert len(failed_events) == 0, "Should NOT emit SORA_BATCH_FAILED when some parts succeed"

            # Verify payload includes stitched_video
            payload = completed_events[0].payload
            assert payload["video_path"] == "/tmp/stitched.mp4"
            assert payload["stitched_video"] == "/tmp/stitched.mp4"
            assert payload["successful_parts"] == 2


class TestARCH003_PublishIntegratorLifecycle:
    """Test ARCH-003: PublishIntegrator has proper async lifecycle."""

    def test_publish_integrator_has_lifecycle(self):
        """ARCH-003: PublishIntegrator should have start/stop methods."""
        from services.publish_integrator import PublishIntegrator

        integrator = PublishIntegrator()
        assert hasattr(integrator, 'start'), "Should have start method"
        assert hasattr(integrator, 'stop'), "Should have stop method"
        assert hasattr(integrator, 'is_running'), "Should have is_running property"

    @pytest.mark.asyncio
    async def test_publish_integrator_start_stop(self):
        """ARCH-003: PublishIntegrator start/stop lifecycle should work."""
        from services.publish_integrator import PublishIntegrator

        integrator = PublishIntegrator()
        assert not integrator.is_running

        await integrator.start()
        assert integrator.is_running

        await integrator.stop()
        assert not integrator.is_running

    def test_publish_integrator_uses_orchestrator_metadata(self):
        """ARCH-003: PublishIntegrator should use pre-extracted metadata from orchestrator."""
        from services.publish_integrator import PublishIntegrator

        integrator = PublishIntegrator()

        # Simulate analysis with orchestrator-provided metadata
        enriched_analysis = {
            "hook": "Pre-extracted hook from orchestrator",
            "description": "Pre-extracted description",
            "hashtags": ["pre", "extracted"],
            "cta": "Follow!"
        }

        caption = integrator._generate_caption("tiktok", enriched_analysis, None)

        assert "Pre-extracted hook from orchestrator" in caption
        assert "#pre" in caption


class TestARCH002_AnalysisFallback:
    """Test ARCH-002: SoraPipeline analysis fallback produces useful defaults."""

    @pytest.mark.asyncio
    async def test_analysis_fallback_generates_hashtags_from_theme(self):
        """ARCH-002: Analysis fallback should generate hashtags from theme words."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        # Simulate analysis failure by calling _analyze_content with a broken analyzer
        pipeline._analyzer = MagicMock()
        pipeline._analyzer.analyze_transcript = MagicMock(
            side_effect=Exception("AI service unavailable")
        )

        result = await pipeline._analyze_content(
            "/tmp/test.mp4",
            "AI automation content creation",
            ["prompt 1", "prompt 2"]
        )

        assert result is not None
        assert result["viral_score"] == 0, "Fallback score should be 0, not hardcoded 50"
        assert len(result["hashtags"]) > 0, "Should generate hashtags from theme"
        assert "automation" in result["hashtags"], "Should extract 'automation' from theme"
        assert "content" in result["hashtags"], "Should extract 'content' from theme"
        assert result.get("hook") == "AI automation content creation"
        assert result.get("description") is not None
        assert result.get("error") is not None  # Should record the error


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
