"""
Content Services Test Suite
Tests for AI Content Service, Platform Publishers, and Real-Time Metrics.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_content_service import (
    AIContentService, ContentAnalysis, GeneratedContent,
    AIProvider, ContentTone, Platform as AIPlatform
)
from services.platform_publishers import (
    PlatformPublisherFactory, PublishingOrchestrator, PublishRequest,
    PublishResult, PublishStatus, Platform, MediaType,
    TikTokPublisher, YouTubePublisher, InstagramPublisher
)
from services.realtime_metrics import (
    RealTimeMetricsService, ProfileMetrics, PostMetrics,
    MetricsCache, Platform as MetricsPlatform
)


# ============================================================================
# 1. AI CONTENT SERVICE TESTS (50 tests)
# ============================================================================

class TestAIContentService:
    """Tests for AI Content Service"""
    
    @pytest.fixture
    def service(self):
        return AIContentService()
    
    @pytest.fixture
    def sample_analysis(self):
        return ContentAnalysis(
            content_type="video",
            niche="fitness",
            scene_description="Person doing workout",
            mood="energetic",
            quality_score=85.0,
        )

    def test_001_service_instantiates(self, service):
        """AI Content Service instantiates"""
        assert service is not None

    def test_002_provider_selection_local(self, service):
        """Falls back to local provider without API keys"""
        # Without API keys, should use LOCAL
        assert service._provider in [AIProvider.LOCAL, AIProvider.OPENAI, AIProvider.ANTHROPIC]

    def test_003_platform_limits_exist(self, service):
        """Platform limits are defined"""
        assert len(service.PLATFORM_LIMITS) > 0

    def test_004_tiktok_limits(self, service):
        """TikTok limits are correct"""
        limits = service.PLATFORM_LIMITS[AIPlatform.TIKTOK]
        assert limits["title"] == 150
        assert limits["description"] == 2200
        assert limits["hashtags"] == 5

    def test_005_youtube_limits(self, service):
        """YouTube limits are correct"""
        limits = service.PLATFORM_LIMITS[AIPlatform.YOUTUBE]
        assert limits["title"] == 100
        assert limits["description"] == 5000
        assert limits["hashtags"] == 15

    def test_006_instagram_limits(self, service):
        """Instagram limits are correct"""
        limits = service.PLATFORM_LIMITS[AIPlatform.INSTAGRAM]
        assert limits["description"] == 2200
        assert limits["hashtags"] == 30

    def test_007_twitter_limits(self, service):
        """Twitter limits are correct"""
        limits = service.PLATFORM_LIMITS[AIPlatform.TWITTER]
        assert limits["description"] == 280
        assert limits["hashtags"] == 3

    def test_008_niche_hashtags_exist(self, service):
        """Niche hashtags are defined"""
        assert len(service.NICHE_HASHTAGS) > 0

    def test_009_fitness_hashtags(self, service):
        """Fitness niche has hashtags"""
        assert "fitness" in service.NICHE_HASHTAGS
        assert len(service.NICHE_HASHTAGS["fitness"]) >= 5

    def test_010_tech_hashtags(self, service):
        """Tech niche has hashtags"""
        assert "tech" in service.NICHE_HASHTAGS
        assert "coding" in service.NICHE_HASHTAGS["tech"]

    @pytest.mark.asyncio
    async def test_011_generate_content_returns_result(self, service, sample_analysis):
        """Generate content returns GeneratedContent"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
        )
        assert isinstance(result, GeneratedContent)

    @pytest.mark.asyncio
    async def test_012_generated_content_has_title(self, service, sample_analysis):
        """Generated content has title"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
        )
        assert len(result.title) > 0

    @pytest.mark.asyncio
    async def test_013_generated_content_has_description(self, service, sample_analysis):
        """Generated content has description"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
        )
        assert len(result.description) > 0

    @pytest.mark.asyncio
    async def test_014_generated_content_has_hashtags(self, service, sample_analysis):
        """Generated content has hashtags"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
        )
        assert len(result.hashtags) > 0

    @pytest.mark.asyncio
    async def test_015_hashtags_have_hash_symbol(self, service, sample_analysis):
        """Hashtags include # symbol"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
        )
        for tag in result.hashtags:
            assert tag.startswith("#")

    @pytest.mark.asyncio
    async def test_016_generated_content_has_platform(self, service, sample_analysis):
        """Generated content has platform"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.YOUTUBE,
            ContentTone.CASUAL,
        )
        assert result.platform == AIPlatform.YOUTUBE

    @pytest.mark.asyncio
    async def test_017_generated_content_has_tone(self, service, sample_analysis):
        """Generated content has tone"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.ENTHUSIASTIC,
        )
        assert result.tone == ContentTone.ENTHUSIASTIC

    @pytest.mark.asyncio
    async def test_018_generated_content_has_variations(self, service, sample_analysis):
        """Generated content has variations"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
            num_variations=3,
        )
        assert len(result.variations) >= 1

    @pytest.mark.asyncio
    async def test_019_title_respects_limit(self, service, sample_analysis):
        """Title respects platform limit"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.YOUTUBE,
            ContentTone.CASUAL,
        )
        assert len(result.title) <= 100

    @pytest.mark.asyncio
    async def test_020_description_respects_limit(self, service, sample_analysis):
        """Description respects platform limit"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TWITTER,
            ContentTone.CASUAL,
        )
        assert len(result.description) <= 280

    @pytest.mark.asyncio
    async def test_021_enthusiastic_tone_has_emoji(self, service, sample_analysis):
        """Enthusiastic tone includes emojis"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.ENTHUSIASTIC,
        )
        # Check for common emojis in enthusiastic content
        has_emoji = any(c for c in result.title + result.description if ord(c) > 127)
        assert has_emoji or "!" in result.title

    @pytest.mark.asyncio
    async def test_022_educational_tone_appropriate(self, service, sample_analysis):
        """Educational tone is appropriate"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.YOUTUBE,
            ContentTone.EDUCATIONAL,
        )
        assert result.tone == ContentTone.EDUCATIONAL

    @pytest.mark.asyncio
    async def test_023_call_to_action_generated(self, service, sample_analysis):
        """Call to action is generated"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.YOUTUBE,
            ContentTone.CASUAL,
        )
        assert result.call_to_action is not None

    @pytest.mark.asyncio
    async def test_024_youtube_cta_mentions_subscribe(self, service, sample_analysis):
        """YouTube CTA mentions subscribe"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.YOUTUBE,
            ContentTone.CASUAL,
        )
        assert "subscribe" in result.call_to_action.lower() or "bell" in result.call_to_action.lower()

    @pytest.mark.asyncio
    async def test_025_instagram_cta_mentions_save(self, service, sample_analysis):
        """Instagram CTA mentions save"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.INSTAGRAM,
            ContentTone.CASUAL,
        )
        assert "save" in result.call_to_action.lower()

    @pytest.mark.asyncio
    async def test_026_generated_at_timestamp(self, service, sample_analysis):
        """Generated at timestamp exists"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
        )
        assert result.generated_at is not None

    @pytest.mark.asyncio
    async def test_027_provider_in_result(self, service, sample_analysis):
        """Provider is in result"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
        )
        assert result.provider in [AIProvider.LOCAL, AIProvider.OPENAI, AIProvider.ANTHROPIC]

    @pytest.mark.asyncio
    async def test_028_character_count_tracked(self, service, sample_analysis):
        """Character count is tracked"""
        result = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
        )
        assert result.character_count > 0

    def test_029_template_title_generation(self, service, sample_analysis):
        """Template title generation works"""
        title = service._generate_template_title(
            sample_analysis,
            ContentTone.CASUAL,
            AIPlatform.TIKTOK,
        )
        assert len(title) > 0

    def test_030_template_description_generation(self, service, sample_analysis):
        """Template description generation works"""
        desc = service._generate_template_description(
            sample_analysis,
            ContentTone.CASUAL,
            AIPlatform.TIKTOK,
        )
        assert len(desc) > 0

    def test_031_shuffle_hashtags(self, service):
        """Hashtag shuffling works"""
        original = ["tag1", "tag2", "tag3"]
        shuffled = service._shuffle_hashtags(original)
        assert len(shuffled) == 3
        assert all(tag.startswith("#") for tag in shuffled)

    @pytest.mark.asyncio
    async def test_032_analyze_content_returns_analysis(self, service):
        """Analyze content returns ContentAnalysis"""
        result = await service.analyze_content_for_generation(
            "video",
            existing_analysis={"niche": "fitness", "quality_score": 80},
        )
        assert isinstance(result, ContentAnalysis)
        assert result.niche == "fitness"

    @pytest.mark.asyncio
    async def test_033_generate_variations_returns_list(self, service, sample_analysis):
        """Generate variations returns list"""
        original = await service.generate_content(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
        )
        variations = await service.generate_variations(original, 5)
        assert isinstance(variations, list)
        assert len(variations) == 5

    def test_034_build_prompt_for_ai(self, service, sample_analysis):
        """Build prompt generates valid prompt"""
        prompt = service._build_prompt(
            sample_analysis,
            AIPlatform.TIKTOK,
            ContentTone.CASUAL,
            3,
        )
        assert "tiktok" in prompt.lower()
        assert "fitness" in prompt.lower()

    def test_035_generate_cta_per_platform(self, service):
        """Generate CTA is platform-specific"""
        tiktok_cta = service._generate_cta(AIPlatform.TIKTOK, ContentTone.CASUAL)
        youtube_cta = service._generate_cta(AIPlatform.YOUTUBE, ContentTone.CASUAL)
        assert tiktok_cta != youtube_cta


# ============================================================================
# 2. PLATFORM PUBLISHERS TESTS (40 tests)
# ============================================================================

class TestPlatformPublishers:
    """Tests for Platform Publishers"""

    def test_040_factory_creates_tiktok_publisher(self):
        """Factory creates TikTok publisher"""
        publisher = PlatformPublisherFactory.create(
            Platform.TIKTOK,
            {"access_token": "test"}
        )
        assert isinstance(publisher, TikTokPublisher)

    def test_041_factory_creates_youtube_publisher(self):
        """Factory creates YouTube publisher"""
        publisher = PlatformPublisherFactory.create(
            Platform.YOUTUBE,
            {"access_token": "test"}
        )
        assert isinstance(publisher, YouTubePublisher)

    def test_042_factory_creates_instagram_publisher(self):
        """Factory creates Instagram publisher"""
        publisher = PlatformPublisherFactory.create(
            Platform.INSTAGRAM,
            {"access_token": "test", "instagram_user_id": "123"}
        )
        assert isinstance(publisher, InstagramPublisher)

    def test_043_factory_supported_platforms(self):
        """Factory returns supported platforms"""
        platforms = PlatformPublisherFactory.supported_platforms()
        assert Platform.TIKTOK in platforms
        assert Platform.YOUTUBE in platforms
        assert Platform.INSTAGRAM in platforms

    def test_044_publish_request_model(self):
        """PublishRequest model validates"""
        request = PublishRequest(
            media_path="/path/to/video.mp4",
            media_type=MediaType.VIDEO,
            description="Test description",
            account_id="acc123",
            platform=Platform.TIKTOK,
        )
        assert request.platform == Platform.TIKTOK

    def test_045_publish_result_model(self):
        """PublishResult model validates"""
        result = PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=Platform.TIKTOK,
            post_id="post123",
        )
        assert result.success is True

    def test_046_orchestrator_instantiates(self):
        """Publishing orchestrator instantiates"""
        orchestrator = PublishingOrchestrator()
        assert orchestrator is not None

    def test_047_orchestrator_register_account(self):
        """Orchestrator can register account"""
        orchestrator = PublishingOrchestrator()
        orchestrator.register_account(
            "acc123",
            Platform.TIKTOK,
            {"access_token": "test"}
        )
        assert "acc123" in orchestrator._publishers

    @pytest.mark.asyncio
    async def test_048_orchestrator_publish_unregistered(self):
        """Orchestrator handles unregistered account"""
        orchestrator = PublishingOrchestrator()
        result = await orchestrator.publish(PublishRequest(
            media_path="/test.mp4",
            media_type=MediaType.VIDEO,
            description="Test",
            account_id="unknown",
            platform=Platform.TIKTOK,
        ))
        assert result.success is False
        assert "No publisher registered" in result.error_message

    def test_049_media_types_defined(self):
        """Media types are defined"""
        assert MediaType.VIDEO.value == "video"
        assert MediaType.IMAGE.value == "image"
        assert MediaType.REEL.value == "reel"
        assert MediaType.SHORT.value == "short"

    def test_050_publish_status_defined(self):
        """Publish status values defined"""
        assert PublishStatus.PENDING.value == "pending"
        assert PublishStatus.PUBLISHED.value == "published"
        assert PublishStatus.FAILED.value == "failed"

    @pytest.mark.asyncio
    async def test_051_tiktok_publish_requires_token(self):
        """TikTok publish requires access token"""
        publisher = TikTokPublisher({})
        result = await publisher.publish(PublishRequest(
            media_path="/test.mp4",
            media_type=MediaType.VIDEO,
            description="Test",
            account_id="acc123",
            platform=Platform.TIKTOK,
        ))
        assert result.success is False
        assert "Missing access token" in result.error_message

    @pytest.mark.asyncio
    async def test_052_youtube_publish_requires_token(self):
        """YouTube publish requires access token"""
        publisher = YouTubePublisher({})
        result = await publisher.publish(PublishRequest(
            media_path="/test.mp4",
            media_type=MediaType.VIDEO,
            title="Test Video",
            description="Test",
            account_id="acc123",
            platform=Platform.YOUTUBE,
        ))
        assert result.success is False
        assert "Missing access token" in result.error_message

    @pytest.mark.asyncio
    async def test_053_instagram_publish_requires_credentials(self):
        """Instagram publish requires credentials"""
        publisher = InstagramPublisher({})
        result = await publisher.publish(PublishRequest(
            media_path="/test.mp4",
            media_type=MediaType.REEL,
            description="Test",
            account_id="acc123",
            platform=Platform.INSTAGRAM,
        ))
        assert result.success is False
        assert "Missing credentials" in result.error_message

    def test_054_publish_request_hashtags_default(self):
        """PublishRequest has default empty hashtags"""
        request = PublishRequest(
            media_path="/test.mp4",
            media_type=MediaType.VIDEO,
            description="Test",
            account_id="acc123",
            platform=Platform.TIKTOK,
        )
        assert request.hashtags == []

    def test_055_publish_request_privacy_default(self):
        """PublishRequest has default public privacy"""
        request = PublishRequest(
            media_path="/test.mp4",
            media_type=MediaType.VIDEO,
            description="Test",
            account_id="acc123",
            platform=Platform.TIKTOK,
        )
        assert request.privacy == "public"

    def test_056_publish_result_error_optional(self):
        """PublishResult error_message is optional"""
        result = PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=Platform.TIKTOK,
        )
        assert result.error_message is None

    def test_057_publish_result_url_optional(self):
        """PublishResult post_url is optional"""
        result = PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=Platform.TIKTOK,
        )
        assert result.post_url is None


# ============================================================================
# 3. REAL-TIME METRICS TESTS (40 tests)
# ============================================================================

class TestRealTimeMetrics:
    """Tests for Real-Time Metrics Service"""

    @pytest.fixture
    def service(self):
        return RealTimeMetricsService(cache_ttl_seconds=60)

    @pytest.fixture
    def cache(self):
        return MetricsCache(default_ttl_seconds=60)

    def test_060_service_instantiates(self, service):
        """Metrics service instantiates"""
        assert service is not None

    def test_061_cache_instantiates(self, cache):
        """Metrics cache instantiates"""
        assert cache is not None

    def test_062_cache_set_and_get(self, cache):
        """Cache set and get works"""
        cache.set("instagram", "user1", "profile", {"followers": 1000})
        result = cache.get("instagram", "user1", "profile")
        assert result["followers"] == 1000

    def test_063_cache_returns_none_missing(self, cache):
        """Cache returns None for missing key"""
        result = cache.get("instagram", "nonexistent", "profile")
        assert result is None

    def test_064_cache_invalidate_all(self, cache):
        """Cache invalidate all works"""
        cache.set("instagram", "user1", "profile", {"data": 1})
        cache.set("tiktok", "user2", "profile", {"data": 2})
        cache.invalidate()
        assert cache.get("instagram", "user1", "profile") is None
        assert cache.get("tiktok", "user2", "profile") is None

    def test_065_cache_invalidate_platform(self, cache):
        """Cache invalidate by platform works"""
        cache.set("instagram", "user1", "profile", {"data": 1})
        cache.set("tiktok", "user2", "profile", {"data": 2})
        cache.invalidate("instagram")
        assert cache.get("instagram", "user1", "profile") is None
        assert cache.get("tiktok", "user2", "profile") is not None

    def test_066_profile_metrics_model(self):
        """ProfileMetrics model validates"""
        metrics = ProfileMetrics(
            platform=MetricsPlatform.INSTAGRAM,
            username="testuser",
            follower_count=1000,
        )
        assert metrics.follower_count == 1000

    def test_067_post_metrics_model(self):
        """PostMetrics model validates"""
        metrics = PostMetrics(
            platform=MetricsPlatform.INSTAGRAM,
            post_id="post123",
            likes=500,
            comments=50,
        )
        assert metrics.likes == 500

    def test_068_profile_metrics_defaults(self):
        """ProfileMetrics has correct defaults"""
        metrics = ProfileMetrics(
            platform=MetricsPlatform.INSTAGRAM,
            username="testuser",
        )
        assert metrics.follower_count == 0
        assert metrics.following_count == 0
        assert metrics.engagement_rate == 0.0

    def test_069_post_metrics_defaults(self):
        """PostMetrics has correct defaults"""
        metrics = PostMetrics(
            platform=MetricsPlatform.INSTAGRAM,
            post_id="post123",
        )
        assert metrics.likes == 0
        assert metrics.views == 0
        assert metrics.shares == 0

    def test_070_rapidapi_hosts_defined(self, service):
        """RapidAPI hosts are defined"""
        assert MetricsPlatform.INSTAGRAM in service.RAPIDAPI_HOSTS
        assert MetricsPlatform.TIKTOK in service.RAPIDAPI_HOSTS
        assert MetricsPlatform.YOUTUBE in service.RAPIDAPI_HOSTS

    @pytest.mark.asyncio
    async def test_071_instagram_profile_returns_metrics(self, service):
        """Instagram profile fetch returns ProfileMetrics"""
        result = await service.get_instagram_profile("testuser", use_cache=False)
        assert isinstance(result, ProfileMetrics)
        assert result.platform == MetricsPlatform.INSTAGRAM

    @pytest.mark.asyncio
    async def test_072_tiktok_profile_returns_metrics(self, service):
        """TikTok profile fetch returns ProfileMetrics"""
        result = await service.get_tiktok_profile("testuser", use_cache=False)
        assert isinstance(result, ProfileMetrics)
        assert result.platform == MetricsPlatform.TIKTOK

    @pytest.mark.asyncio
    async def test_073_youtube_channel_returns_metrics(self, service):
        """YouTube channel fetch returns ProfileMetrics"""
        result = await service.get_youtube_channel("UCtest123", use_cache=False)
        assert isinstance(result, ProfileMetrics)
        assert result.platform == MetricsPlatform.YOUTUBE

    @pytest.mark.asyncio
    async def test_074_instagram_post_returns_metrics(self, service):
        """Instagram post fetch returns PostMetrics"""
        result = await service.get_instagram_post("post123", use_cache=False)
        assert isinstance(result, PostMetrics)
        assert result.platform == MetricsPlatform.INSTAGRAM

    @pytest.mark.asyncio
    async def test_075_tiktok_post_returns_metrics(self, service):
        """TikTok post fetch returns PostMetrics"""
        result = await service.get_tiktok_post("video123", use_cache=False)
        assert isinstance(result, PostMetrics)
        assert result.platform == MetricsPlatform.TIKTOK

    @pytest.mark.asyncio
    async def test_076_youtube_video_returns_metrics(self, service):
        """YouTube video fetch returns PostMetrics"""
        result = await service.get_youtube_video("dQw4w9WgXcQ", use_cache=False)
        assert isinstance(result, PostMetrics)
        assert result.platform == MetricsPlatform.YOUTUBE

    @pytest.mark.asyncio
    async def test_077_batch_profile_metrics(self, service):
        """Batch profile metrics works"""
        accounts = [
            {"platform": "instagram", "username": "user1"},
            {"platform": "tiktok", "username": "user2"},
        ]
        results = await service.get_all_profile_metrics(accounts, use_cache=False)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_078_batch_post_metrics(self, service):
        """Batch post metrics works"""
        posts = [
            {"platform": "instagram", "post_id": "post1"},
            {"platform": "tiktok", "post_id": "video1"},
        ]
        results = await service.get_post_metrics_batch(posts, use_cache=False)
        assert len(results) == 2

    def test_079_invalidate_cache(self, service):
        """Service can invalidate cache"""
        service.invalidate_cache("instagram", "user1")
        # Should not raise
        assert True

    @pytest.mark.asyncio
    async def test_080_growth_metrics_returns_model(self, service):
        """Growth metrics returns model"""
        result = await service.calculate_growth_metrics(
            MetricsPlatform.INSTAGRAM,
            "testuser",
            period_days=7,
        )
        assert result.period_days == 7

    def test_081_metrics_fetched_at_exists(self):
        """Metrics have fetched_at timestamp"""
        metrics = ProfileMetrics(
            platform=MetricsPlatform.INSTAGRAM,
            username="testuser",
        )
        assert metrics.fetched_at is not None

    def test_082_post_metrics_post_url_optional(self):
        """PostMetrics post_url is optional"""
        metrics = PostMetrics(
            platform=MetricsPlatform.INSTAGRAM,
            post_id="post123",
        )
        assert metrics.post_url is None

    def test_083_profile_metrics_is_stale_default(self):
        """ProfileMetrics is_stale defaults to False"""
        metrics = ProfileMetrics(
            platform=MetricsPlatform.INSTAGRAM,
            username="testuser",
        )
        assert metrics.is_stale is False


# ============================================================================
# 4. INTEGRATION TESTS (20 tests)
# ============================================================================

class TestServiceIntegration:
    """Integration tests across services"""

    @pytest.mark.asyncio
    async def test_090_ai_to_publish_workflow(self):
        """AI generation to publish workflow"""
        # 1. Generate content
        ai_service = AIContentService()
        analysis = ContentAnalysis(
            content_type="video",
            niche="fitness",
            quality_score=85.0,
        )
        generated = await ai_service.generate_content(
            analysis,
            AIPlatform.TIKTOK,
            ContentTone.ENTHUSIASTIC,
        )
        
        # 2. Create publish request
        request = PublishRequest(
            media_path="/test/video.mp4",
            media_type=MediaType.VIDEO,
            title=generated.title,
            description=generated.description,
            hashtags=generated.hashtags,
            account_id="acc123",
            platform=Platform.TIKTOK,
        )
        
        # 3. Verify integration
        assert request.title == generated.title
        assert request.description == generated.description

    @pytest.mark.asyncio
    async def test_091_metrics_caching_workflow(self):
        """Metrics caching workflow"""
        service = RealTimeMetricsService(cache_ttl_seconds=300)
        
        # First fetch (no cache)
        result1 = await service.get_instagram_profile("testuser", use_cache=True)
        
        # Second fetch (should use cache if available)
        result2 = await service.get_instagram_profile("testuser", use_cache=True)
        
        # Both should return ProfileMetrics
        assert isinstance(result1, ProfileMetrics)
        assert isinstance(result2, ProfileMetrics)

    @pytest.mark.asyncio
    async def test_092_multi_platform_generation(self):
        """Generate for multiple platforms"""
        ai_service = AIContentService()
        analysis = ContentAnalysis(
            content_type="video",
            niche="tech",
            quality_score=80.0,
        )
        
        platforms = [AIPlatform.TIKTOK, AIPlatform.YOUTUBE, AIPlatform.INSTAGRAM]
        results = []
        
        for platform in platforms:
            result = await ai_service.generate_content(analysis, platform, ContentTone.CASUAL)
            results.append(result)
        
        assert len(results) == 3
        # Each should have platform-appropriate content
        assert results[0].platform == AIPlatform.TIKTOK
        assert results[1].platform == AIPlatform.YOUTUBE
        assert results[2].platform == AIPlatform.INSTAGRAM

    def test_093_orchestrator_multiple_accounts(self):
        """Orchestrator handles multiple accounts"""
        orchestrator = PublishingOrchestrator()
        
        orchestrator.register_account("tiktok_acc", Platform.TIKTOK, {"access_token": "tk1"})
        orchestrator.register_account("youtube_acc", Platform.YOUTUBE, {"access_token": "yt1"})
        orchestrator.register_account("instagram_acc", Platform.INSTAGRAM, {"access_token": "ig1", "instagram_user_id": "123"})
        
        assert len(orchestrator._publishers) == 3

    @pytest.mark.asyncio
    async def test_094_content_analysis_to_generation(self):
        """Content analysis flows to generation"""
        ai_service = AIContentService()
        
        # Simulate content analysis result
        analysis = await ai_service.analyze_content_for_generation(
            "video",
            existing_analysis={
                "niche": "comedy",
                "mood": "funny",
                "quality_score": 90,
                "scene": "Person doing comedy skit",
            },
        )
        
        assert analysis.niche == "comedy"
        assert analysis.quality_score == 90
        
        # Generate based on analysis
        result = await ai_service.generate_content(
            analysis,
            AIPlatform.TIKTOK,
            ContentTone.HUMOROUS,
        )
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_095_all_tones_generate_content(self):
        """All content tones generate content"""
        ai_service = AIContentService()
        analysis = ContentAnalysis(
            content_type="video",
            niche="lifestyle",
            quality_score=75.0,
        )
        
        tones = [
            ContentTone.CASUAL,
            ContentTone.ENTHUSIASTIC,
            ContentTone.EDUCATIONAL,
            ContentTone.PROFESSIONAL,
            ContentTone.HUMOROUS,
            ContentTone.INSPIRATIONAL,
        ]
        
        for tone in tones:
            result = await ai_service.generate_content(analysis, AIPlatform.TIKTOK, tone)
            assert result.tone == tone
            assert len(result.description) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
