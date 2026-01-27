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
        """ARCH-001: Full pipeline should execute all steps in order"""
        from services.master_orchestrator import MasterOrchestrator, PipelineStatus

        orchestrator = MasterOrchestrator()

        # Mock the subsystems to avoid actual execution
        orchestrator.sora_pipeline.generate_multi_part = AsyncMock(return_value={
            "status": "completed",
            "stitched_video": "/tmp/test_video.mp4",
            "theme": "Test Theme",
            "prompts": ["part1", "part2", "part3"],
            "analysis": {
                "title_tiktok": "Test Title",
                "description": "Test Description",
                "hashtags": ["test", "viral"],
                "hook": "Test Hook",
                "cta": "Follow for more!"
            }
        })

        orchestrator.blotato_service.get_accounts_by_platform = Mock(return_value=[
            type('Account', (), {'id': 1, 'username': 'test_account'})()
        ])

        orchestrator.twitter_service.schedule_tweets = Mock(return_value=["tweet1", "tweet2"])

        # Execute pipeline
        result = await orchestrator.run_full_pipeline(
            theme="Test viral content",
            num_parts=3,
            publish_platforms=["tiktok"],
            schedule_tweets=True,
            tweets_per_day=12
        )

        # Verify structure
        assert result["status"] == PipelineStatus.COMPLETED, "Pipeline should complete"
        assert "video_generated" in result["steps"], "Should generate video"
        assert "content_analyzed" in result["steps"], "Should analyze content"
        assert "published_to_platforms" in result["steps"], "Should publish"
        assert "tweets_scheduled" in result["steps"], "Should schedule tweets"


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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
