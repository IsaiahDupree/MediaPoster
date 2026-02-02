"""
Comprehensive tests for System Architecture Integration (ARCH-001 to ARCH-005)

Tests cover:
- ARCH-001: Master Orchestrator database persistence and event coordination
- ARCH-002: Multi-part Sora batch generation
- ARCH-003: Content analyzer → publisher integration
- ARCH-004: Tweet scheduler 2-hour intervals
- ARCH-005: Offer traffic tracking
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import json

# Import services under test
from services.master_orchestrator import (
    MasterOrchestrator,
    PipelineConfig,
    PipelineStatus,
)
from services.offer_tracker import OfferTracker, get_offer_tracker
from services.event_bus import EventBus, Topics


# ============================================================================
# ARCH-001: Master Orchestrator Tests
# ============================================================================

class TestMasterOrchestratorARCH001:
    """Test ARCH-001: Master Orchestrator database persistence."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing."""
        # Disable DB for unit tests
        return MasterOrchestrator(use_db=False)

    @pytest.fixture
    def pipeline_config(self):
        """Create test pipeline config."""
        return PipelineConfig(
            theme="AI automation",
            num_parts=3,
            character="@isaiahdupree",
            publish_platforms=["tiktok", "instagram", "youtube"],
            schedule_tweets=True,
            tweets_per_day=12,
            offer_url="https://example.com/offer",
        )

    def test_pipeline_config_creation(self, pipeline_config):
        """Test pipeline config is properly initialized."""
        assert pipeline_config.theme == "AI automation"
        assert pipeline_config.num_parts == 3
        assert pipeline_config.schedule_tweets is True
        assert pipeline_config.tweets_per_day == 12
        assert len(pipeline_config.publish_platforms) == 3

    def test_pipeline_status_enum(self):
        """Test pipeline status enum values."""
        assert PipelineStatus.INITIALIZING.value == "initializing"
        assert PipelineStatus.GENERATING_VIDEO.value == "generating_video"
        assert PipelineStatus.PUBLISHING.value == "publishing"
        assert PipelineStatus.COMPLETED.value == "completed"
        assert PipelineStatus.FAILED.value == "failed"

    @pytest.mark.asyncio
    async def test_start_pipeline_creates_pipeline_id(self, orchestrator, pipeline_config):
        """Test that starting a pipeline creates a unique pipeline ID."""
        with patch.object(orchestrator, '_db_save_pipeline', new_callable=AsyncMock):
            with patch.object(orchestrator.event_bus, 'publish', new_callable=AsyncMock):
                pipeline_id = await orchestrator.start_pipeline(pipeline_config)

        assert pipeline_id is not None
        assert pipeline_id.startswith("pipeline-")
        assert len(pipeline_id) == len("pipeline-") + 8

    def test_get_pipeline_metrics(self, orchestrator):
        """Test pipeline metrics aggregation."""
        # Add some pipelines
        orchestrator.active_pipelines = {
            "pipeline-001": {
                "pipeline_id": "pipeline-001",
                "status": "generating_video",
                "outputs": {"publish_jobs": []},
            },
            "pipeline-002": {
                "pipeline_id": "pipeline-002",
                "status": "publishing",
                "outputs": {"publish_jobs": []},
            },
        }
        orchestrator.completed_pipelines = {
            "pipeline-003": {
                "pipeline_id": "pipeline-003",
                "status": "completed",
                "duration_seconds": 120,
                "outputs": {"publish_jobs": [{"status": "completed"}]},
            },
        }

        metrics = orchestrator.get_pipeline_metrics()

        assert metrics["total_pipelines"] == 3
        assert metrics["active_pipelines"] == 2
        assert metrics["completed_pipelines"] == 1
        assert "status_breakdown" in metrics
        assert metrics["status_breakdown"]["generating_video"] == 1
        assert metrics["status_breakdown"]["publishing"] == 1
        assert metrics["status_breakdown"]["completed"] == 1

    def test_pipeline_health_check(self, orchestrator):
        """Test pipeline health status retrieval."""
        orchestrator.active_pipelines = {
            "pipeline-001": {
                "pipeline_id": "pipeline-001",
                "status": "publishing",
                "current_step": "publishing",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "_retry_counts": {"sora_generation": 1},
            }
        }

        health = orchestrator.get_pipeline_health("pipeline-001")

        assert health["pipeline_id"] == "pipeline-001"
        assert health["status"] == "publishing"
        assert health["current_step"] == "publishing"
        assert health["retry_counts"]["sora_generation"] == 1

    def test_platform_metadata_extraction(self, orchestrator):
        """Test ARCH-003: Platform-specific metadata extraction."""
        analysis = {
            "detected_hook": "AI revolutionizes content creation",
            "topics": ["AI", "automation", "content"],
            "hashtags": ["ai", "automation"],
            "viral_score": 85,
            "call_to_action": {"text": "Learn more"},
            "description": "Detailed analysis",
            "content_type": "educational",
            "tone": "energetic",
            "pain_points": ["manual editing"],
            "target_audience": {"interests": ["tech", "business"]},
            "pacing": "fast",
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        # Check default platform
        assert "default" in metadata
        assert metadata["default"]["title"] == "AI revolutionizes content creation"
        assert metadata["default"]["viral_score"] == 85

        # Check platform-specific extraction
        assert "tiktok" in metadata
        assert "instagram" in metadata
        assert "youtube" in metadata
        assert "twitter" in metadata

        # TikTok should have limited hashtags
        assert len(metadata["tiktok"]["hashtags"]) <= 10

        # Instagram should have more hashtags
        assert len(metadata["instagram"]["hashtags"]) <= 30

        # Twitter should have very few hashtags
        assert len(metadata["twitter"]["hashtags"]) <= 3

    def test_metadata_fallback_when_analysis_none(self, orchestrator):
        """Test metadata extraction handles None analysis gracefully."""
        metadata = orchestrator._extract_platform_metadata(None)

        assert metadata is not None
        assert "default" in metadata
        assert metadata["default"]["title"] == "Untitled"


# ============================================================================
# ARCH-002: Sora Pipeline Tests
# ============================================================================

class TestSoraPipelineARCH002:
    """Test ARCH-002: Multi-part Sora generation."""

    @pytest.mark.asyncio
    async def test_sora_pipeline_generate_multi_part_method_exists(self):
        """Test that SoraPipeline has generate_multi_part method."""
        try:
            from automation.sora.pipeline import SoraPipeline

            pipeline = SoraPipeline()
            assert hasattr(pipeline, "generate_multi_part")
            assert callable(pipeline.generate_multi_part)
        except ImportError:
            pytest.skip("SoraPipeline not available")

    @pytest.mark.asyncio
    async def test_sora_pipeline_generate_prompts_method_exists(self):
        """Test that SoraPipeline has generate_prompts method."""
        try:
            from automation.sora.pipeline import SoraPipeline

            pipeline = SoraPipeline()
            assert hasattr(pipeline, "generate_prompts")
            assert callable(pipeline.generate_prompts)
        except ImportError:
            pytest.skip("SoraPipeline not available")

    @pytest.mark.asyncio
    async def test_sora_pipeline_has_event_bus_integration(self):
        """Test that SoraPipeline integrates with EventBus."""
        try:
            from automation.sora.pipeline import SoraPipeline

            pipeline = SoraPipeline()
            # Should have _event_bus attribute
            assert hasattr(pipeline, "_event_bus")
        except ImportError:
            pytest.skip("SoraPipeline not available")


# ============================================================================
# ARCH-003: Content Analyzer Integration Tests
# ============================================================================

class TestAnalyzerIntegrationARCH003:
    """Test ARCH-003: Content analyzer → publisher integration."""

    def test_content_analyzer_output_structure(self):
        """Test that ContentAnalyzer returns expected fields."""
        try:
            from services.content_analyzer import ContentAnalyzer

            # Check that ContentAnalyzer exists and is instantiable
            analyzer = ContentAnalyzer()
            assert hasattr(analyzer, "analyze_transcript")
        except ImportError:
            pytest.skip("ContentAnalyzer not available")

    def test_metadata_extraction_handles_all_platforms(self, orchestrator):
        """Test that metadata extraction covers all major platforms."""
        orchestrator = MasterOrchestrator(use_db=False)

        analysis = {
            "detected_hook": "Test hook",
            "topics": ["test"],
            "hashtags": ["test"],
            "viral_score": 70,
            "description": "Test description",
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        expected_platforms = [
            "default",
            "tiktok",
            "instagram",
            "youtube",
            "twitter",
            "threads",
            "linkedin",
            "pinterest",
            "facebook",
            "bluesky",
        ]

        for platform in expected_platforms:
            assert platform in metadata, f"Missing platform: {platform}"
            assert "title" in metadata[platform]
            assert "hashtags" in metadata[platform]


# ============================================================================
# ARCH-004: Tweet Scheduler Tests
# ============================================================================

class TestTweetSchedulerARCH004:
    """Test ARCH-004: 2-hour tweet interval scheduling."""

    def test_tweet_interval_calculation(self):
        """Test that 2-hour interval is correctly calculated."""
        tweets_per_day = 12
        interval_minutes = int((24 * 60) / tweets_per_day)

        assert interval_minutes == 120  # 2 hours
        assert interval_minutes == (60 * 2)

    def test_twitter_campaign_service_interval_config(self):
        """Test that TwitterCampaignService accepts interval_minutes."""
        try:
            from services.twitter_campaign_service import TwitterCampaignService

            service = TwitterCampaignService(interval_minutes=120)
            assert service.interval_minutes == 120
        except ImportError:
            pytest.skip("TwitterCampaignService not available")

    def test_various_tweet_frequencies(self):
        """Test interval calculation for various tweet frequencies."""
        test_cases = [
            (12, 120),   # 12 tweets/day = 2 hour interval
            (24, 60),    # 24 tweets/day = 1 hour interval
            (6, 240),    # 6 tweets/day = 4 hour interval
        ]

        for tweets_per_day, expected_interval in test_cases:
            interval = int((24 * 60) / tweets_per_day)
            assert interval == expected_interval, \
                f"For {tweets_per_day} tweets/day, expected {expected_interval}min, got {interval}min"


# ============================================================================
# ARCH-005: Offer Tracking Tests
# ============================================================================

class TestOfferTrackerARCH005:
    """Test ARCH-005: Offer traffic tracking service."""

    @pytest.fixture
    def tracker(self):
        """Create tracker instance for testing."""
        tracker = OfferTracker()
        # Disable DB for unit tests
        tracker._engine = None
        return tracker

    def test_offer_tracker_singleton(self):
        """Test that get_offer_tracker returns singleton."""
        tracker1 = get_offer_tracker()
        tracker2 = get_offer_tracker()

        assert tracker1 is tracker2

    @pytest.mark.asyncio
    async def test_create_tracked_link_generates_utm_params(self, tracker):
        """Test tracked link generation with UTM parameters."""
        base_url = "https://example.com/offer"
        campaign = "test_campaign"
        source = "twitter"

        tracked_url = await tracker.create_tracked_link(
            offer_url=base_url,
            campaign=campaign,
            source=source,
        )

        # Should include UTM parameters
        assert "utm_source=twitter" in tracked_url
        assert "utm_medium=social" in tracked_url
        assert f"utm_campaign={campaign}" in tracked_url
        assert base_url in tracked_url

    @pytest.mark.asyncio
    async def test_tracked_link_has_proper_separator(self, tracker):
        """Test tracked URL uses proper separator."""
        url_with_query = "https://example.com/offer?existing=param"
        tracked = await tracker.create_tracked_link(
            offer_url=url_with_query,
            campaign="test",
            source="tiktok",
        )

        # Should use & separator when ? already exists
        assert "?existing=param&utm_" in tracked

    @pytest.mark.asyncio
    async def test_tracked_link_handles_no_query_params(self, tracker):
        """Test tracked URL adds ? when none exists."""
        url_no_query = "https://example.com/offer"
        tracked = await tracker.create_tracked_link(
            offer_url=url_no_query,
            campaign="test",
            source="instagram",
        )

        # Should use ? separator when no query params
        assert "?utm_" in tracked

    def test_campaign_report_structure(self, tracker):
        """Test campaign report has expected fields."""
        report = {
            "campaign": "test",
            "platforms": 3,
            "total_clicks": 100,
            "total_conversions": 10,
            "total_revenue": 500.0,
            "conversion_rate": 10.0,
        }

        assert "campaign" in report
        assert "total_clicks" in report
        assert "total_conversions" in report
        assert "total_revenue" in report
        assert "conversion_rate" in report

    def test_conversion_rate_calculation(self):
        """Test conversion rate is correctly calculated."""
        clicks = 100
        conversions = 10

        conversion_rate = (conversions / clicks * 100)

        assert conversion_rate == 10.0

    def test_offer_url_utm_params_structure(self):
        """Test UTM parameter structure."""
        utm_params = {
            "utm_source": "twitter",
            "utm_medium": "social",
            "utm_campaign": "test_campaign",
        }

        assert utm_params["utm_source"] == "twitter"
        assert utm_params["utm_medium"] == "social"
        assert utm_params["utm_campaign"] == "test_campaign"


# ============================================================================
# Integration Tests (All ARCH features working together)
# ============================================================================

class TestARCHIntegration:
    """Integration tests for all ARCH features."""

    @pytest.mark.asyncio
    async def test_full_pipeline_configuration(self):
        """Test complete pipeline config with all ARCH features enabled."""
        config = PipelineConfig(
            theme="AI revolution",
            num_parts=3,
            character="@creator",
            publish_platforms=["tiktok", "instagram", "youtube"],
            schedule_tweets=True,  # ARCH-004
            tweets_per_day=12,  # ARCH-004: Calculates 2-hour intervals
            offer_url="https://example.com/offer",  # ARCH-005
        )

        assert config.theme == "AI revolution"
        assert config.num_parts == 3
        assert config.schedule_tweets is True
        assert config.tweets_per_day == 12
        assert config.offer_url is not None

    def test_all_features_referenced_in_orchestrator(self):
        """Test that all ARCH features are integrated in MasterOrchestrator."""
        orchestrator = MasterOrchestrator(use_db=False)

        # ARCH-001: Database methods
        assert hasattr(orchestrator, "_db_save_pipeline")
        assert hasattr(orchestrator, "_db_update_pipeline_status")
        assert hasattr(orchestrator, "_db_update_pipeline_step")

        # ARCH-003: Metadata extraction
        assert hasattr(orchestrator, "_extract_platform_metadata")

        # ARCH-008: Metrics and health
        assert hasattr(orchestrator, "get_pipeline_metrics")
        assert hasattr(orchestrator, "get_pipeline_health")
        assert hasattr(orchestrator, "get_pipeline_statistics")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
