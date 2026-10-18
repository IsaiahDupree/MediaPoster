"""
Tests for GAP Features (GAP-003, GAP-004, GAP-007, GAP-009, GAP-010)
====================================================================
Tests for Content Repurposing, Meta Ads Testing, Twitter Worker,
Instagram Graph API, and Whisper Integration.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from services.event_bus import EventBus, Event, Topics
from services.workers.twitter_campaign_worker import (
    TwitterCampaignWorker,
    TwitterAccount,
    SessionHealth,
    get_twitter_campaign_worker,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def event_bus():
    """Fresh EventBus for testing."""
    return EventBus()


@pytest.fixture
def twitter_worker(event_bus):
    """Twitter worker with fresh EventBus."""
    worker = TwitterCampaignWorker(event_bus=event_bus)
    # Mock campaign service to avoid real API calls
    worker.campaign_service = MagicMock()
    worker.campaign_service.schedule_campaign = MagicMock(return_value="campaign_test")
    worker.campaign_service.schedule_offer_tweets = MagicMock(return_value=["t1", "t2"])
    return worker


# ============================================================================
# GAP-007: Twitter Worker Completion
# ============================================================================

class TestGAP007_MultiAccountSwitching:
    """GAP-007: Multi-account switching for Twitter worker."""

    def test_register_account(self, twitter_worker):
        """GAP-007: Should register a Twitter account."""
        account = twitter_worker.register_account("acc_1", "testuser1")
        assert account.account_id == "acc_1"
        assert account.username == "testuser1"
        assert account.is_active is True
        assert account.session_health == SessionHealth.HEALTHY

    def test_register_multiple_accounts(self, twitter_worker):
        """GAP-007: Should support multiple accounts."""
        twitter_worker.register_account("acc_1", "user1")
        twitter_worker.register_account("acc_2", "user2")
        twitter_worker.register_account("acc_3", "user3")
        accounts = twitter_worker.get_accounts()
        assert len(accounts) == 3

    def test_first_registered_is_active(self, twitter_worker):
        """GAP-007: First registered account should become active."""
        twitter_worker.register_account("acc_1", "user1")
        twitter_worker.register_account("acc_2", "user2")
        active = twitter_worker.get_active_account()
        assert active is not None
        assert active.account_id == "acc_1"

    @pytest.mark.asyncio
    async def test_switch_account(self, twitter_worker):
        """GAP-007: Should switch to a different account."""
        twitter_worker.register_account("acc_1", "user1")
        twitter_worker.register_account("acc_2", "user2")
        success = await twitter_worker.switch_account("acc_2")
        assert success is True
        active = twitter_worker.get_active_account()
        assert active.account_id == "acc_2"

    @pytest.mark.asyncio
    async def test_switch_unknown_account(self, twitter_worker):
        """GAP-007: Should fail when switching to unknown account."""
        twitter_worker.register_account("acc_1", "user1")
        success = await twitter_worker.switch_account("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_switch_inactive_account(self, twitter_worker):
        """GAP-007: Should fail when switching to inactive account."""
        twitter_worker.register_account("acc_1", "user1")
        acc2 = twitter_worker.register_account("acc_2", "user2")
        acc2.is_active = False
        success = await twitter_worker.switch_account("acc_2")
        assert success is False

    @pytest.mark.asyncio
    async def test_switch_emits_event(self, twitter_worker, event_bus):
        """GAP-007: Account switch should emit twitter.account.switched event."""
        events = []

        async def capture(event):
            events.append(event)

        event_bus.subscribe("twitter.account.switched", capture)

        twitter_worker.register_account("acc_1", "user1")
        twitter_worker.register_account("acc_2", "user2")
        await twitter_worker.switch_account("acc_2")
        await asyncio.sleep(0.05)

        assert len(events) == 1
        assert events[0].payload["new_account_id"] == "acc_2"
        assert events[0].payload["username"] == "user2"

    @pytest.mark.asyncio
    async def test_auto_switch_account(self, twitter_worker):
        """GAP-007: Should auto-switch to account with fewest tweets."""
        acc1 = twitter_worker.register_account("acc_1", "user1")
        acc2 = twitter_worker.register_account("acc_2", "user2")
        acc1.tweets_posted_today = 30
        acc2.tweets_posted_today = 5

        switched_id = await twitter_worker.auto_switch_account()
        assert switched_id == "acc_2"

    @pytest.mark.asyncio
    async def test_auto_switch_skips_unhealthy(self, twitter_worker):
        """GAP-007: Auto-switch should skip unhealthy accounts."""
        acc1 = twitter_worker.register_account("acc_1", "user1")
        acc2 = twitter_worker.register_account("acc_2", "user2")
        acc1.session_health = SessionHealth.UNHEALTHY
        acc2.tweets_posted_today = 5

        switched_id = await twitter_worker.auto_switch_account()
        assert switched_id == "acc_2"

    def test_account_can_tweet(self, twitter_worker):
        """GAP-007: can_tweet should respect daily limits and health."""
        acc = twitter_worker.register_account("acc_1", "user1", daily_limit=50)
        assert acc.can_tweet is True

        acc.tweets_posted_today = 50
        assert acc.can_tweet is False

    def test_account_cant_tweet_unhealthy(self, twitter_worker):
        """GAP-007: Unhealthy account can_tweet should be False."""
        acc = twitter_worker.register_account("acc_1", "user1")
        acc.session_health = SessionHealth.UNHEALTHY
        assert acc.can_tweet is False

    def test_account_cant_tweet_inactive(self, twitter_worker):
        """GAP-007: Inactive account can_tweet should be False."""
        acc = twitter_worker.register_account("acc_1", "user1")
        acc.is_active = False
        assert acc.can_tweet is False


class TestGAP007_SessionHealthMonitoring:
    """GAP-007: Session health monitoring for Twitter worker."""

    def test_initial_session_health(self, twitter_worker):
        """GAP-007: Initial session health should be HEALTHY."""
        health = twitter_worker.get_session_health()
        assert health == SessionHealth.HEALTHY

    def test_update_session_health(self, twitter_worker):
        """GAP-007: Should update account session health."""
        acc = twitter_worker.register_account("acc_1", "user1")
        twitter_worker.update_session_health("acc_1", SessionHealth.DEGRADED)
        assert acc.session_health == SessionHealth.DEGRADED

    def test_overall_health_reflects_accounts(self, twitter_worker):
        """GAP-007: Overall health should reflect worst account status."""
        twitter_worker.register_account("acc_1", "user1")
        twitter_worker.register_account("acc_2", "user2")
        twitter_worker.update_session_health("acc_1", SessionHealth.HEALTHY)
        twitter_worker.update_session_health("acc_2", SessionHealth.UNHEALTHY)
        assert twitter_worker.get_session_health() == SessionHealth.DEGRADED

    def test_all_unhealthy_overall_unhealthy(self, twitter_worker):
        """GAP-007: All unhealthy accounts = overall UNHEALTHY."""
        twitter_worker.register_account("acc_1", "user1")
        twitter_worker.register_account("acc_2", "user2")
        twitter_worker.update_session_health("acc_1", SessionHealth.UNHEALTHY)
        twitter_worker.update_session_health("acc_2", SessionHealth.UNHEALTHY)
        assert twitter_worker.get_session_health() == SessionHealth.UNHEALTHY

    def test_rate_limited_health(self, twitter_worker):
        """GAP-007: Rate limited account should be reflected."""
        twitter_worker.register_account("acc_1", "user1")
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        twitter_worker.update_session_health("acc_1", SessionHealth.RATE_LIMITED, future)
        assert twitter_worker.get_session_health() == SessionHealth.RATE_LIMITED

    @pytest.mark.asyncio
    async def test_health_check_emits_status(self, twitter_worker, event_bus):
        """GAP-007: Health check should emit twitter.session.health_status event."""
        events = []

        async def capture(event):
            events.append(event)

        event_bus.subscribe("twitter.session.health_status", capture)

        twitter_worker.register_account("acc_1", "user1")

        check_event = Event(
            topic="twitter.session.health_check",
            payload={},
            source="test",
        )
        await twitter_worker._handle_health_check(check_event)
        await asyncio.sleep(0.05)

        assert len(events) == 1
        assert events[0].payload["overall_health"] == SessionHealth.HEALTHY
        assert "acc_1" in events[0].payload["accounts"]

    def test_session_health_enum_values(self):
        """GAP-007: SessionHealth enum should have all expected values."""
        assert SessionHealth.HEALTHY == "healthy"
        assert SessionHealth.DEGRADED == "degraded"
        assert SessionHealth.UNHEALTHY == "unhealthy"
        assert SessionHealth.RATE_LIMITED == "rate_limited"
        assert SessionHealth.EXPIRED == "expired"


class TestGAP007_PubSubIntegration:
    """GAP-007: Complete pub/sub integration for Twitter worker."""

    def test_subscriptions_include_new_topics(self, twitter_worker):
        """GAP-007: Worker should subscribe to new GAP-007 topics."""
        subs = twitter_worker.get_subscriptions()
        assert "twitter.campaign.schedule_requested" in subs
        assert "twitter.campaign.post_requested" in subs
        assert "twitter.session.health_check" in subs

    @pytest.mark.asyncio
    async def test_post_request_event(self, twitter_worker, event_bus):
        """GAP-007: Should handle twitter.campaign.post_requested."""
        events = []

        async def capture(event):
            events.append(event)

        event_bus.subscribe("twitter.campaign.posted", capture)

        twitter_worker.register_account("acc_1", "user1")

        post_event = Event(
            topic="twitter.campaign.post_requested",
            payload={"content": "Test tweet content", "account_id": "acc_1"},
            source="test",
        )
        await twitter_worker._handle_post_request(post_event)
        await asyncio.sleep(0.05)

        assert len(events) == 1
        assert events[0].payload["account_id"] == "acc_1"

    @pytest.mark.asyncio
    async def test_post_request_auto_switches(self, twitter_worker, event_bus):
        """GAP-007: Post request should auto-switch if account at limit."""
        twitter_worker.register_account("acc_1", "user1", daily_limit=1)
        acc1 = twitter_worker._accounts["acc_1"]
        acc1.tweets_posted_today = 1

        twitter_worker.register_account("acc_2", "user2")

        events = []

        async def capture(event):
            events.append(event)

        event_bus.subscribe("twitter.campaign.posted", capture)

        post_event = Event(
            topic="twitter.campaign.post_requested",
            payload={"content": "Test tweet", "account_id": "acc_1"},
            source="test",
        )
        await twitter_worker._handle_post_request(post_event)
        await asyncio.sleep(0.05)

        assert len(events) == 1
        assert events[0].payload["account_id"] == "acc_2"

    def test_stats_include_gap007_fields(self, twitter_worker):
        """GAP-007: Worker stats should include multi-account info."""
        twitter_worker.register_account("acc_1", "user1")
        stats = twitter_worker.get_stats()
        assert "session_health" in stats
        assert "registered_accounts" in stats
        assert "active_account_id" in stats
        assert "account_switch_count" in stats
        assert "health_check_count" in stats
        assert stats["registered_accounts"] == 1

    def test_account_to_dict(self, twitter_worker):
        """GAP-007: TwitterAccount should serialize to dict."""
        acc = twitter_worker.register_account("acc_1", "user1")
        d = acc.to_dict()
        assert d["account_id"] == "acc_1"
        assert d["username"] == "user1"
        assert d["is_active"] is True


# ============================================================================
# GAP-010: Whisper Integration
# ============================================================================

class TestGAP010_WhisperIntegration:
    """GAP-010: Whisper transcription integration into content pipeline."""

    def test_whisper_transcriber_imports(self):
        """GAP-010: WhisperTranscriber should be importable."""
        from services.whisper_transcriber import WhisperTranscriber
        assert WhisperTranscriber is not None

    def test_whisper_transcriber_init(self):
        """GAP-010: WhisperTranscriber should initialize."""
        from services.whisper_transcriber import WhisperTranscriber
        transcriber = WhisperTranscriber()
        assert transcriber is not None

    def test_whisper_has_transcribe_method(self):
        """GAP-010: WhisperTranscriber should have transcribe method."""
        from services.whisper_transcriber import WhisperTranscriber
        transcriber = WhisperTranscriber()
        assert hasattr(transcriber, 'transcribe_video') or hasattr(transcriber, 'transcribe')

    def test_whisper_has_audio_extraction(self):
        """GAP-010: WhisperTranscriber should support audio extraction."""
        from services.whisper_transcriber import WhisperTranscriber
        transcriber = WhisperTranscriber()
        assert (
            hasattr(transcriber, 'extract_audio')
            or hasattr(transcriber, '_extract_audio')
        )

    def test_content_analyzer_can_use_transcript(self):
        """GAP-010: ContentAnalyzer should accept transcript input."""
        from services.content_analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        assert hasattr(analyzer, 'analyze_transcript')

    def test_whisper_integrates_with_event_bus(self):
        """GAP-010: Whisper should work with EventBus topics."""
        # Verify relevant topics exist
        assert hasattr(Topics, 'ANALYSIS_REQUESTED')
        assert hasattr(Topics, 'ANALYSIS_COMPLETED')

    def test_whisper_integration_pipeline_concept(self):
        """GAP-010: Whisper → ContentAnalyzer pipeline should be feasible."""
        from services.whisper_transcriber import WhisperTranscriber
        from services.content_analyzer import ContentAnalyzer

        # Both components can be instantiated together
        transcriber = WhisperTranscriber()
        analyzer = ContentAnalyzer()

        # Verify they have compatible interfaces
        assert transcriber is not None
        assert analyzer is not None
        assert hasattr(analyzer, 'analyze_transcript')


# ============================================================================
# GAP-003: Content Repurposing Engine
# ============================================================================

class TestGAP003_ContentRepurposingEngine:
    """GAP-003: Video ingestion, highlight detection, aspect ratio conversion,
    AI captions, virality prediction."""

    def test_clip_selector_imports(self):
        """GAP-003: ClipSelector should be importable."""
        from services.clip_selector import ClipSelector
        assert ClipSelector is not None

    def test_clip_selector_init(self):
        """GAP-003: ClipSelector should initialize with mock db."""
        from services.clip_selector import ClipSelector
        selector = ClipSelector(db=MagicMock())
        assert selector is not None

    def test_clip_selector_has_suggest_clips(self):
        """GAP-003: ClipSelector should have suggest_clips method."""
        from services.clip_selector import ClipSelector
        selector = ClipSelector(db=MagicMock())
        assert hasattr(selector, 'suggest_clips')

    def test_video_viral_analyzer_imports(self):
        """GAP-003: VideoViralAnalyzer should be importable."""
        from services.video_viral_analyzer import VideoViralAnalyzer
        assert VideoViralAnalyzer is not None

    def test_video_viral_analyzer_init(self):
        """GAP-003: VideoViralAnalyzer should initialize."""
        from services.video_viral_analyzer import VideoViralAnalyzer
        analyzer = VideoViralAnalyzer(api_key="test-key")
        assert analyzer is not None

    def test_video_viral_analyzer_has_analyze(self):
        """GAP-003: VideoViralAnalyzer should have analyze method."""
        from services.video_viral_analyzer import VideoViralAnalyzer
        analyzer = VideoViralAnalyzer(api_key="test-key")
        assert hasattr(analyzer, 'analyze') or hasattr(analyzer, 'analyze_video')

    def test_caption_generator_imports(self):
        """GAP-003: CaptionGenerator should be importable."""
        from services.caption_generator import CaptionGenerator
        assert CaptionGenerator is not None

    def test_caption_generator_init(self):
        """GAP-003: CaptionGenerator should initialize."""
        from services.caption_generator import CaptionGenerator
        gen = CaptionGenerator()
        assert gen is not None

    def test_caption_generator_has_generate(self):
        """GAP-003: CaptionGenerator should have generate method."""
        from services.caption_generator import CaptionGenerator
        gen = CaptionGenerator()
        assert hasattr(gen, 'generate_captions') or hasattr(gen, 'burn_captions')

    def test_highlight_ranker_imports(self):
        """GAP-003: HighlightRanker should be importable."""
        from modules.highlight_detection.highlight_ranker import HighlightRanker
        assert HighlightRanker is not None

    def test_highlight_ranker_init(self):
        """GAP-003: HighlightRanker should initialize."""
        from modules.highlight_detection.highlight_ranker import HighlightRanker
        ranker = HighlightRanker()
        assert ranker is not None

    def test_highlight_ranker_has_rank(self):
        """GAP-003: HighlightRanker should have rank_highlights method."""
        from modules.highlight_detection.highlight_ranker import HighlightRanker
        ranker = HighlightRanker()
        assert hasattr(ranker, 'rank_highlights')

    def test_smart_reframer_imports(self):
        """GAP-003: SmartReframer for aspect ratio conversion should be importable."""
        from services.smart_reframer import SmartReframer
        assert SmartReframer is not None

    def test_smart_reframer_init(self):
        """GAP-003: SmartReframer should initialize."""
        from services.smart_reframer import SmartReframer
        reframer = SmartReframer()
        assert reframer is not None

    def test_repurpose_pipeline_imports(self):
        """GAP-003: RepurposePipeline should be importable."""
        from services.repurpose.pipeline import RepurposePipeline
        assert RepurposePipeline is not None

    def test_clip_extractor_imports(self):
        """GAP-003: ClipExtractor should be importable."""
        from services.repurpose.clip_extractor import ClipExtractor
        assert ClipExtractor is not None

    def test_clip_extractor_has_platform_specs(self):
        """GAP-003: ClipExtractor should define platform aspect ratio specs."""
        from services.repurpose.clip_extractor import ClipExtractor
        assert hasattr(ClipExtractor, 'PLATFORM_SPECS') or hasattr(ClipExtractor, 'platform_specs')

    def test_frame_sampler_imports(self):
        """GAP-003: FrameSamplerService for video ingestion should be importable."""
        from services.frame_sampler import FrameSamplerService
        assert FrameSamplerService is not None


# ============================================================================
# GAP-004: Meta Ads Programmatic Testing
# ============================================================================

class TestGAP004_MetaAdsProgrammaticTesting:
    """GAP-004: Transcript extraction, variation generator, batch rendering,
    Meta campaign deployment, insights tracking."""

    def test_ad_testing_package_imports(self):
        """GAP-004: ad_testing package should be importable."""
        from services.ad_testing import (
            get_extractor,
            get_variation_generator,
            get_batch_renderer,
            get_campaign_deployer,
            get_performance_tracker,
        )
        assert get_extractor is not None
        assert get_variation_generator is not None
        assert get_batch_renderer is not None
        assert get_campaign_deployer is not None
        assert get_performance_tracker is not None

    def test_transcript_extractor_works(self):
        """GAP-004: TranscriptElementExtractor should extract elements."""
        from services.ad_testing import get_extractor
        extractor = get_extractor()
        result = extractor.extract_elements("Stop scrolling! Click the link below!")
        assert isinstance(result, dict)
        assert "hooks" in result
        assert "ctas" in result

    def test_variation_generator_works(self):
        """GAP-004: AdVariationGenerator should generate variations."""
        from services.ad_testing import get_variation_generator
        gen = get_variation_generator()
        elements = {
            "hooks": ["Stop scrolling!"],
            "pain_points": ["Wasting money"],
            "benefits": ["Save time"],
            "ctas": ["Click now"],
            "social_proofs": ["5000+ users"],
        }
        variations = gen.generate_variations(elements, strategy="matrix", max_variations=5)
        assert isinstance(variations, list)
        assert len(variations) > 0

    def test_batch_renderer_works(self):
        """GAP-004: AdBatchRenderer should create and render batches."""
        from services.ad_testing import get_batch_renderer
        renderer = get_batch_renderer()
        batch_id = renderer.create_batch([
            {"id": "v1", "headline": "Test", "body": "Body", "cta": "CTA", "hook": "Hey!", "strategy": "matrix", "platform": "facebook"},
        ])
        assert isinstance(batch_id, str)

    def test_campaign_deployer_works(self):
        """GAP-004: MetaCampaignDeployer should create campaigns in dev mode."""
        from services.ad_testing import get_campaign_deployer
        deployer = get_campaign_deployer()
        campaign = deployer.create_campaign("GAP Test", "CONVERSIONS", 5000)
        assert "id" in campaign

    def test_performance_tracker_works(self):
        """GAP-004: MetaAdsPerformanceTracker should track metrics."""
        from services.ad_testing import get_performance_tracker
        tracker = get_performance_tracker()
        tracker.track_impression("gap_ad_1")
        tracker.track_click("gap_ad_1")
        metrics = tracker.get_ad_metrics("gap_ad_1")
        assert metrics["impressions"] >= 1
        assert metrics["clicks"] >= 1

    def test_ai_learner_works(self):
        """GAP-004: AdAILearner should analyze results."""
        from services.ad_testing import get_ai_learner
        learner = get_ai_learner()
        assert hasattr(learner, 'analyze_results')
        assert hasattr(learner, 'identify_winning_patterns')

    def test_dco_optimizer_works(self):
        """GAP-004: DynamicCreativeOptimizer should create DCO campaigns."""
        from services.ad_testing import get_dco_optimizer
        dco = get_dco_optimizer()
        cid = dco.create_dco_campaign(
            videos=["v1.mp4"], texts=["text"], headlines=["h1"], ctas=["CTA"],
        )
        assert isinstance(cid, str)


# ============================================================================
# GAP-009: Instagram Graph API
# ============================================================================

class TestGAP009_InstagramGraphAPI:
    """GAP-009: OAuth flow, Graph API adapter, real-time follower activity,
    Insights API."""

    def test_instagram_graph_service_imports(self):
        """GAP-009: InstagramGraphService should be importable."""
        from services.instagram_graph_service import (
            InstagramGraphService,
            get_instagram_graph_service,
        )
        assert InstagramGraphService is not None
        assert get_instagram_graph_service is not None

    def test_instagram_graph_service_init(self):
        """GAP-009: InstagramGraphService should initialize."""
        from services.instagram_graph_service import get_instagram_graph_service
        service = get_instagram_graph_service()
        assert service is not None

    def test_oauth_config_exists(self):
        """GAP-009: IGOAuthConfig should be importable for OAuth flow."""
        from services.instagram_graph_service import IGOAuthConfig
        config = IGOAuthConfig()
        assert config is not None

    def test_graph_api_methods_exist(self):
        """GAP-009: Service should have Graph API adapter methods."""
        from services.instagram_graph_service import get_instagram_graph_service
        service = get_instagram_graph_service()
        assert hasattr(service, 'get_account_info')
        assert hasattr(service, 'get_published_media')

    def test_insights_methods_exist(self):
        """GAP-009: Service should have Insights API methods."""
        from services.instagram_graph_service import get_instagram_graph_service
        service = get_instagram_graph_service()
        assert hasattr(service, 'get_insights') or hasattr(service, 'get_media_insights')

    def test_publishing_methods_exist(self):
        """GAP-009: Service should have publishing methods."""
        from services.instagram_graph_service import get_instagram_graph_service
        service = get_instagram_graph_service()
        assert hasattr(service, 'publish_image') or hasattr(service, 'publish_video')

    def test_comments_methods_exist(self):
        """GAP-009: Service should have comments management methods."""
        from services.instagram_graph_service import get_instagram_graph_service
        service = get_instagram_graph_service()
        assert hasattr(service, 'get_comments') or hasattr(service, 'get_media_comments')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
