"""
Tests for Channel Router Service (HITL-007 / BM-011)
=====================================================
Comprehensive tests for the ChannelRouter service including:
- Service initialization and singleton pattern
- Route to single platform
- Route to multiple platforms
- Safari vs Blotato selection logic
- Fallback from Safari to Blotato
- Per-platform formatting (caption length differences)
- Optional approval gate integration
- Published URL tracking
- EventBus event emission

Total: 40+ tests
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock, PropertyMock
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.channel_router import (
    ChannelRouter,
    RouteResult,
    PlatformResult,
    PublishMethod,
    RoutePreference,
    ALL_PLATFORMS,
    SAFARI_SUPPORTED_PLATFORMS,
    BLOTATO_SUPPORTED_PLATFORMS,
    PLATFORM_LIMITS,
    get_channel_router,
)
from services.event_bus.bus import EventBus
from services.event_bus.event import Event
from services.event_bus.topics import Topics


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test."""
    ChannelRouter.reset_instance()
    EventBus.reset_instance()
    yield
    ChannelRouter.reset_instance()
    EventBus.reset_instance()


@pytest.fixture
def event_bus():
    """Create a fresh EventBus instance."""
    return EventBus.get_instance()


@pytest.fixture
def router(event_bus):
    """Create a ChannelRouter with EventBus."""
    return ChannelRouter.get_instance(event_bus=event_bus)


@pytest.fixture
def sample_analysis():
    """Sample AI analysis metadata."""
    return {
        "hook": "This changes everything about productivity",
        "description": "A deep dive into how AI tools can transform your daily workflow and boost your output by 10x.",
        "hashtags": ["productivity", "ai", "workflow", "tech", "motivation"],
        "viral_score": 8.5,
        "content_type": "educational",
        "tone": "inspirational",
        "topics": ["AI", "productivity", "workflow"],
    }


@pytest.fixture
def mock_blotato_service():
    """Create a mock BlotatoService."""
    mock = MagicMock()
    mock.get_accounts_by_platform.return_value = [
        MagicMock(id=710, platform="tiktok", username="test_user", is_active=True),
    ]
    mock.publish_content = AsyncMock(return_value={
        "success": True,
        "result": {"url": "https://tiktok.com/@test/video/123", "id": "123"},
    })
    return mock


@pytest.fixture
def mock_safari_poster():
    """Create a mock SafariTwitterPoster."""
    mock = MagicMock()
    mock.post_tweet.return_value = {
        "success": True,
        "url": "https://x.com/test/status/456",
        "tweet_id": "456",
    }
    return mock


# =============================================================================
# SERVICE INITIALIZATION AND SINGLETON TESTS
# =============================================================================

class TestChannelRouterInit:
    """Test service initialization and singleton pattern."""

    def test_singleton_instance(self, event_bus):
        """ChannelRouter should follow singleton pattern."""
        router1 = ChannelRouter.get_instance(event_bus=event_bus)
        router2 = ChannelRouter.get_instance()
        assert router1 is router2

    def test_singleton_reset(self, event_bus):
        """Singleton should be resettable for testing."""
        router1 = ChannelRouter.get_instance(event_bus=event_bus)
        ChannelRouter.reset_instance()
        router2 = ChannelRouter.get_instance(event_bus=event_bus)
        assert router1 is not router2

    def test_init_with_event_bus(self, event_bus):
        """Router should accept an EventBus instance."""
        router = ChannelRouter(event_bus=event_bus)
        assert router._event_bus is event_bus

    def test_init_without_event_bus(self):
        """Router should work without an explicit EventBus."""
        router = ChannelRouter()
        # Should auto-connect to EventBus singleton
        assert router._event_bus is not None

    def test_default_route_preference(self, router):
        """Default route preference should be AUTO."""
        assert router.get_route_preference() == RoutePreference.AUTO

    def test_set_route_preference(self, router):
        """Route preference should be configurable."""
        router.set_route_preference(RoutePreference.SAFARI_PREFERRED)
        assert router.get_route_preference() == RoutePreference.SAFARI_PREFERRED

    def test_get_channel_router_convenience(self, event_bus):
        """get_channel_router() should return the singleton."""
        router = get_channel_router(event_bus=event_bus)
        assert isinstance(router, ChannelRouter)
        assert router is ChannelRouter.get_instance()

    def test_initial_stats(self, router):
        """Initial stats should show zero routes."""
        stats = router.get_stats()
        assert stats["active_routes"] == 0
        assert stats["completed_routes"] == 0
        assert stats["total_platforms_published"] == 0
        assert stats["total_platforms_failed"] == 0


# =============================================================================
# ROUTE TO SINGLE PLATFORM TESTS
# =============================================================================

class TestRouteSinglePlatform:
    """Test routing to a single platform."""

    @pytest.mark.asyncio
    async def test_route_to_single_platform_blotato(self, router, mock_blotato_service):
        """Route to a single platform via Blotato."""
        router._blotato_service = mock_blotato_service

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test hook", "hashtags": ["test"]},
        )

        assert isinstance(result, RouteResult)
        assert result.status == "completed"
        assert "tiktok" in result.platform_results
        assert result.platform_results["tiktok"].success
        assert result.platform_results["tiktok"].method == PublishMethod.BLOTATO

    @pytest.mark.asyncio
    async def test_route_invalid_platform(self, router):
        """Route with invalid platform should return failed status."""
        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["nonexistent_platform"],
        )

        assert result.status == "failed"
        assert len(result.platform_results) == 0

    @pytest.mark.asyncio
    async def test_route_tracks_published_url(self, router, mock_blotato_service):
        """Route should track the published URL."""
        router._blotato_service = mock_blotato_service

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test"},
        )

        assert "tiktok" in result.published_urls
        assert "tiktok.com" in result.published_urls["tiktok"]

    @pytest.mark.asyncio
    async def test_route_single_failure(self, router):
        """Route to a platform that fails should record the error."""
        # No blotato service set - will fail
        router._blotato_service = None

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test"},
        )

        assert result.status == "completed"
        assert "tiktok" in result.platform_results
        assert not result.platform_results["tiktok"].success
        assert result.platform_results["tiktok"].error is not None


# =============================================================================
# ROUTE TO MULTIPLE PLATFORMS TESTS
# =============================================================================

class TestRouteMultiplePlatforms:
    """Test routing to multiple platforms simultaneously."""

    @pytest.mark.asyncio
    async def test_route_to_multiple_platforms(self, router, mock_blotato_service):
        """Route to multiple platforms."""
        # Configure mock to handle different platforms
        mock_blotato_service.get_accounts_by_platform.side_effect = lambda p: [
            MagicMock(id=100, platform=p, username=f"test_{p}", is_active=True)
        ]
        router._blotato_service = mock_blotato_service

        platforms = ["tiktok", "instagram", "youtube"]
        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=platforms,
            analysis={"hook": "Multi-platform test", "hashtags": ["test"]},
        )

        assert result.status == "completed"
        assert len(result.platform_results) == 3
        assert result.success_count == 3
        assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_route_partial_success(self, router, mock_blotato_service):
        """Some platforms succeed, some fail."""
        call_count = 0

        async def publish_sometimes(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                return {"success": False, "error": "API rate limit"}
            return {"success": True, "result": {"url": f"https://example.com/{call_count}"}}

        mock_blotato_service.publish_content = publish_sometimes
        mock_blotato_service.get_accounts_by_platform.side_effect = lambda p: [
            MagicMock(id=100, platform=p, username=f"test_{p}", is_active=True)
        ]
        router._blotato_service = mock_blotato_service

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok", "instagram", "youtube"],
            analysis={"hook": "Test"},
        )

        assert result.status == "completed"
        assert result.success_count + result.failure_count == 3
        assert result.success_count >= 1
        assert result.failure_count >= 1

    @pytest.mark.asyncio
    async def test_route_filters_invalid_platforms(self, router, mock_blotato_service):
        """Invalid platforms should be filtered out."""
        mock_blotato_service.get_accounts_by_platform.side_effect = lambda p: [
            MagicMock(id=100, platform=p, username=f"test_{p}", is_active=True)
        ]
        router._blotato_service = mock_blotato_service

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok", "fakebook", "instagram"],
            analysis={"hook": "Test"},
        )

        # Should only route to valid platforms
        assert len(result.platforms_requested) == 2
        assert "tiktok" in result.platforms_requested
        assert "instagram" in result.platforms_requested
        assert "fakebook" not in result.platforms_requested

    @pytest.mark.asyncio
    async def test_route_all_nine_platforms(self, router, mock_blotato_service):
        """Should support routing to all 9 Blotato platforms."""
        mock_blotato_service.get_accounts_by_platform.side_effect = lambda p: [
            MagicMock(id=100, platform=p, username=f"test_{p}", is_active=True)
        ]
        router._blotato_service = mock_blotato_service

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=ALL_PLATFORMS,
            analysis={"hook": "Test all platforms", "hashtags": ["test"]},
        )

        assert result.status == "completed"
        assert len(result.platform_results) == 9
        assert result.success_count == 9


# =============================================================================
# SAFARI VS BLOTATO SELECTION LOGIC TESTS
# =============================================================================

class TestMethodSelection:
    """Test Safari vs Blotato selection logic."""

    def test_auto_mode_twitter_safari_healthy(self, router):
        """AUTO mode should prefer Safari for Twitter when healthy."""
        # Mock Safari as healthy for Twitter
        mock_session_manager = MagicMock()
        from automation.safari_session_manager import Platform as SafariPlatform
        mock_state = MagicMock()
        mock_state.is_logged_in = True
        mock_session_manager.sessions = {SafariPlatform.TWITTER: mock_state}
        router._safari_session_manager = mock_session_manager

        primary, fallback = router._select_method("twitter", RoutePreference.AUTO)
        assert primary == PublishMethod.SAFARI
        assert fallback == PublishMethod.BLOTATO

    def test_auto_mode_twitter_safari_unhealthy(self, router):
        """AUTO mode should fall back to Blotato when Safari is unhealthy."""
        # No Safari session manager
        router._safari_session_manager = None

        primary, fallback = router._select_method("twitter", RoutePreference.AUTO)
        assert primary == PublishMethod.BLOTATO

    def test_auto_mode_non_twitter_platform(self, router):
        """AUTO mode should use Blotato for non-Twitter platforms."""
        primary, fallback = router._select_method("tiktok", RoutePreference.AUTO)
        assert primary == PublishMethod.BLOTATO

    def test_safari_preferred_twitter(self, router):
        """SAFARI_PREFERRED should try Safari first for Twitter."""
        mock_session_manager = MagicMock()
        from automation.safari_session_manager import Platform as SafariPlatform
        mock_state = MagicMock()
        mock_state.is_logged_in = True
        mock_session_manager.sessions = {SafariPlatform.TWITTER: mock_state}
        router._safari_session_manager = mock_session_manager

        primary, fallback = router._select_method("twitter", RoutePreference.SAFARI_PREFERRED)
        assert primary == PublishMethod.SAFARI
        assert fallback == PublishMethod.BLOTATO

    def test_safari_preferred_non_safari_platform(self, router):
        """SAFARI_PREFERRED should use Blotato for unsupported platforms."""
        primary, fallback = router._select_method("tiktok", RoutePreference.SAFARI_PREFERRED)
        assert primary == PublishMethod.BLOTATO

    def test_blotato_preferred(self, router):
        """BLOTATO_PREFERRED should use Blotato as primary."""
        primary, fallback = router._select_method("twitter", RoutePreference.BLOTATO_PREFERRED)
        assert primary == PublishMethod.BLOTATO

    def test_blotato_only(self, router):
        """BLOTATO_ONLY should never fall back to Safari."""
        primary, fallback = router._select_method("twitter", RoutePreference.BLOTATO_ONLY)
        assert primary == PublishMethod.BLOTATO
        assert fallback is None

    def test_safari_only_supported(self, router):
        """SAFARI_ONLY should use Safari for supported platforms."""
        primary, fallback = router._select_method("twitter", RoutePreference.SAFARI_ONLY)
        assert primary == PublishMethod.SAFARI
        assert fallback is None

    def test_safari_only_unsupported(self, router):
        """SAFARI_ONLY for unsupported platform should use Blotato."""
        primary, fallback = router._select_method("tiktok", RoutePreference.SAFARI_ONLY)
        assert primary == PublishMethod.BLOTATO
        assert fallback is None

    def test_safari_supported_platforms(self):
        """Safari should support Twitter."""
        assert "twitter" in SAFARI_SUPPORTED_PLATFORMS

    def test_blotato_supports_all(self):
        """Blotato should support all 9 platforms."""
        for platform in ALL_PLATFORMS:
            assert platform in BLOTATO_SUPPORTED_PLATFORMS


# =============================================================================
# FALLBACK HANDLING TESTS
# =============================================================================

class TestFallbackHandling:
    """Test fallback from Safari to Blotato and vice versa."""

    @pytest.mark.asyncio
    async def test_safari_to_blotato_fallback(self, router, mock_blotato_service, mock_safari_poster):
        """When Safari fails, should fallback to Blotato for Twitter."""
        # Mock Safari as failing
        mock_safari_poster.post_tweet.return_value = {
            "success": False,
            "error": "Safari session expired",
        }
        router._safari_twitter_poster = mock_safari_poster
        router._blotato_service = mock_blotato_service

        # Configure Blotato for Twitter
        mock_blotato_service.get_accounts_by_platform.return_value = [
            MagicMock(id=4151, platform="twitter", username="IsaiahDupree7", is_active=True),
        ]
        mock_blotato_service.publish_content = AsyncMock(return_value={
            "success": True,
            "result": {"url": "https://x.com/test/status/789", "id": "789"},
        })

        # Set preference to Safari preferred (will fallback)
        # Mock Safari health as True so it tries Safari first
        mock_session_manager = MagicMock()
        from automation.safari_session_manager import Platform as SafariPlatform
        mock_state = MagicMock()
        mock_state.is_logged_in = True
        mock_session_manager.sessions = {SafariPlatform.TWITTER: mock_state}
        router._safari_session_manager = mock_session_manager

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["twitter"],
            analysis={"hook": "Test fallback"},
            preference=RoutePreference.SAFARI_PREFERRED,
        )

        assert result.status == "completed"
        twitter_result = result.platform_results["twitter"]
        assert twitter_result.success
        assert twitter_result.method == PublishMethod.BLOTATO
        assert twitter_result.fallback_used

    @pytest.mark.asyncio
    async def test_no_fallback_when_primary_succeeds(self, router, mock_safari_poster):
        """Should not use fallback when primary method succeeds."""
        router._safari_twitter_poster = mock_safari_poster

        mock_session_manager = MagicMock()
        from automation.safari_session_manager import Platform as SafariPlatform
        mock_state = MagicMock()
        mock_state.is_logged_in = True
        mock_session_manager.sessions = {SafariPlatform.TWITTER: mock_state}
        router._safari_session_manager = mock_session_manager

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["twitter"],
            analysis={"hook": "Test no fallback"},
            preference=RoutePreference.SAFARI_PREFERRED,
        )

        twitter_result = result.platform_results["twitter"]
        assert twitter_result.success
        assert twitter_result.method == PublishMethod.SAFARI
        assert not twitter_result.fallback_used

    @pytest.mark.asyncio
    async def test_no_fallback_with_only_mode(self, router, mock_safari_poster):
        """SAFARI_ONLY should not attempt Blotato fallback."""
        mock_safari_poster.post_tweet.return_value = {
            "success": False,
            "error": "Failed",
        }
        router._safari_twitter_poster = mock_safari_poster

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["twitter"],
            analysis={"hook": "Test"},
            preference=RoutePreference.SAFARI_ONLY,
        )

        twitter_result = result.platform_results["twitter"]
        assert not twitter_result.success
        assert not twitter_result.fallback_used


# =============================================================================
# PER-PLATFORM FORMATTING TESTS
# =============================================================================

class TestPlatformFormatting:
    """Test per-platform content formatting."""

    def test_twitter_caption_limit(self, router):
        """Twitter captions should be limited to 280 characters."""
        long_text = "A" * 500
        caption = router.format_for_platform(
            platform="twitter",
            analysis={"hook": long_text, "hashtags": []},
        )
        assert len(caption) <= 280

    def test_tiktok_caption_limit(self, router):
        """TikTok captions should be limited to 2200 characters."""
        assert PLATFORM_LIMITS["tiktok"]["caption_max_length"] == 2200

    def test_instagram_caption_limit(self, router):
        """Instagram captions should be limited to 2200 characters."""
        assert PLATFORM_LIMITS["instagram"]["caption_max_length"] == 2200

    def test_youtube_caption_limit(self, router):
        """YouTube descriptions should allow up to 5000 characters."""
        assert PLATFORM_LIMITS["youtube"]["caption_max_length"] == 5000

    def test_twitter_hashtag_count(self, router):
        """Twitter should use max 3 hashtags."""
        many_hashtags = [f"tag{i}" for i in range(20)]
        caption = router.format_for_platform(
            platform="twitter",
            analysis={"hook": "Test", "hashtags": many_hashtags},
        )
        # Count actual # characters
        hashtag_count = caption.count("#")
        assert hashtag_count <= 3

    def test_instagram_hashtag_count(self, router):
        """Instagram should support up to 30 hashtags."""
        assert PLATFORM_LIMITS["instagram"]["hashtag_max_count"] == 30

    def test_tiktok_hashtag_count(self, router):
        """TikTok should support up to 10 hashtags."""
        assert PLATFORM_LIMITS["tiktok"]["hashtag_max_count"] == 10

    def test_linkedin_hashtag_count(self, router):
        """LinkedIn should use max 5 hashtags."""
        assert PLATFORM_LIMITS["linkedin"]["hashtag_max_count"] == 5

    def test_hashtag_style_inline(self, router):
        """Twitter hashtags should be inline (after text on same line)."""
        caption = router.format_for_platform(
            platform="twitter",
            analysis={"hook": "Test tweet", "hashtags": ["ai", "tech"]},
        )
        # Inline: text and hashtags on same logical block
        assert "#ai" in caption
        assert "#tech" in caption

    def test_hashtag_style_appended(self, router):
        """TikTok hashtags should be appended (on new line)."""
        caption = router.format_for_platform(
            platform="tiktok",
            analysis={"hook": "Test video", "hashtags": ["fyp", "viral"]},
        )
        assert "#fyp" in caption
        assert "#viral" in caption

    def test_offer_url_appended(self, router):
        """Offer URL should be appended when space allows."""
        caption = router.format_for_platform(
            platform="tiktok",
            analysis={"hook": "Check this out", "hashtags": []},
            offer_url="https://example.com/offer",
        )
        assert "https://example.com/offer" in caption

    def test_offer_url_omitted_when_too_long(self, router):
        """Offer URL should be omitted if it would exceed the character limit."""
        long_hook = "A" * 270
        caption = router.format_for_platform(
            platform="twitter",
            analysis={"hook": long_hook, "hashtags": []},
            offer_url="https://example.com/offer",
        )
        # Twitter limit is 280, the hook is 270 + URL would exceed
        assert len(caption) <= 280

    def test_caption_override(self, router):
        """Caption override should replace generated caption."""
        caption = router.format_for_platform(
            platform="tiktok",
            analysis={"hook": "Original hook", "hashtags": ["test"]},
            caption_override="Custom caption text",
        )
        assert "Custom caption text" in caption

    def test_all_platforms_have_limits(self):
        """All platforms should have defined formatting limits."""
        for platform in ALL_PLATFORMS:
            assert platform in PLATFORM_LIMITS, f"Missing limits for {platform}"
            limits = PLATFORM_LIMITS[platform]
            assert "caption_max_length" in limits
            assert "hashtag_max_count" in limits
            assert "hashtag_style" in limits

    def test_hashtag_prefix_handling(self, router):
        """Hashtags should get # prefix regardless of input format."""
        caption = router.format_for_platform(
            platform="twitter",
            analysis={"hook": "Test", "hashtags": ["#already_prefixed", "no_prefix"]},
        )
        # Should not get double ##
        assert "##" not in caption
        assert "#already_prefixed" in caption or "#no_prefix" in caption


# =============================================================================
# APPROVAL GATE TESTS
# =============================================================================

class TestApprovalGate:
    """Test optional HITL approval gate integration."""

    @pytest.mark.asyncio
    async def test_approval_required_pauses_routing(self, router):
        """When approval_required=True, routing should pause and await approval."""
        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok", "instagram"],
            analysis={"hook": "Needs approval"},
            approval_required=True,
        )

        assert result.status == "awaiting_approval"
        assert result.approval_status == "pending"
        assert result.approval_required is True
        # No platform results yet
        assert len(result.platform_results) == 0

    @pytest.mark.asyncio
    async def test_approval_not_required_routes_immediately(self, router, mock_blotato_service):
        """When approval_required=False, routing should proceed immediately."""
        mock_blotato_service.get_accounts_by_platform.return_value = [
            MagicMock(id=100, platform="tiktok", username="test", is_active=True),
        ]
        router._blotato_service = mock_blotato_service

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "No approval needed"},
            approval_required=False,
        )

        assert result.status == "completed"
        assert result.approval_required is False
        assert len(result.platform_results) == 1

    @pytest.mark.asyncio
    async def test_approval_rejection(self, router):
        """Rejected approval should mark route as rejected."""
        # First submit for approval
        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test"},
            approval_required=True,
        )

        route_id = result.route_id

        # Then reject it
        updated = await router.handle_approval_response(
            route_id=route_id,
            approved=False,
            feedback="Content needs more work",
        )

        assert updated is not None
        assert updated.approval_status == "rejected"
        assert updated.status == "rejected"

    @pytest.mark.asyncio
    async def test_approval_approved(self, router):
        """Approved approval should mark the route as approved."""
        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test"},
            approval_required=True,
        )

        route_id = result.route_id

        updated = await router.handle_approval_response(
            route_id=route_id,
            approved=True,
        )

        assert updated is not None
        assert updated.approval_status == "approved"

    @pytest.mark.asyncio
    async def test_approval_response_unknown_route(self, router):
        """Handling approval for unknown route should return None."""
        updated = await router.handle_approval_response(
            route_id="nonexistent-route",
            approved=True,
        )
        assert updated is None


# =============================================================================
# PUBLISHED URL TRACKING TESTS
# =============================================================================

class TestPublishedUrlTracking:
    """Test published URL tracking per platform."""

    @pytest.mark.asyncio
    async def test_track_urls_across_platforms(self, router, mock_blotato_service):
        """Published URLs should be tracked per platform."""
        call_count = 0

        async def publish_with_urls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "success": True,
                "result": {"url": f"https://platform{call_count}.com/post/{call_count}"},
            }

        mock_blotato_service.publish_content = publish_with_urls
        mock_blotato_service.get_accounts_by_platform.side_effect = lambda p: [
            MagicMock(id=100, platform=p, username=f"test_{p}", is_active=True)
        ]
        router._blotato_service = mock_blotato_service

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok", "instagram"],
            analysis={"hook": "Test"},
        )

        assert len(result.published_urls) == 2

    @pytest.mark.asyncio
    async def test_get_published_urls_by_route_id(self, router, mock_blotato_service):
        """Should be able to retrieve published URLs by route ID."""
        mock_blotato_service.get_accounts_by_platform.return_value = [
            MagicMock(id=100, platform="tiktok", username="test", is_active=True),
        ]
        router._blotato_service = mock_blotato_service

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test"},
        )

        urls = router.get_published_urls(result.route_id)
        assert isinstance(urls, dict)
        assert "tiktok" in urls

    def test_get_published_urls_unknown_route(self, router):
        """Unknown route should return empty dict."""
        urls = router.get_published_urls("nonexistent-route-id")
        assert urls == {}


# =============================================================================
# EVENT BUS INTEGRATION TESTS
# =============================================================================

class TestEventBusIntegration:
    """Test EventBus event emission."""

    @pytest.mark.asyncio
    async def test_route_started_event(self, router, event_bus, mock_blotato_service):
        """Should emit route.started event."""
        events_received = []

        async def capture_event(event):
            events_received.append(event)

        event_bus.subscribe("route.started", capture_event)
        mock_blotato_service.get_accounts_by_platform.return_value = [
            MagicMock(id=100, platform="tiktok", username="test", is_active=True),
        ]
        router._blotato_service = mock_blotato_service

        await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test"},
        )

        assert len(events_received) == 1
        assert events_received[0].payload["platforms"] == ["tiktok"]

    @pytest.mark.asyncio
    async def test_route_completed_event(self, router, event_bus, mock_blotato_service):
        """Should emit route.completed event."""
        events_received = []

        async def capture_event(event):
            events_received.append(event)

        event_bus.subscribe("route.completed", capture_event)
        mock_blotato_service.get_accounts_by_platform.return_value = [
            MagicMock(id=100, platform="tiktok", username="test", is_active=True),
        ]
        router._blotato_service = mock_blotato_service

        await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test"},
        )

        assert len(events_received) == 1
        assert "success_count" in events_received[0].payload

    @pytest.mark.asyncio
    async def test_platform_started_and_completed_events(self, router, event_bus, mock_blotato_service):
        """Should emit route.platform.started and route.platform.completed for each platform."""
        started_events = []
        completed_events = []

        async def capture_started(event):
            started_events.append(event)

        async def capture_completed(event):
            completed_events.append(event)

        event_bus.subscribe("route.platform.started", capture_started)
        event_bus.subscribe("route.platform.completed", capture_completed)
        mock_blotato_service.get_accounts_by_platform.side_effect = lambda p: [
            MagicMock(id=100, platform=p, username=f"test_{p}", is_active=True)
        ]
        router._blotato_service = mock_blotato_service

        await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok", "instagram"],
            analysis={"hook": "Test"},
        )

        assert len(started_events) == 2
        assert len(completed_events) == 2

    @pytest.mark.asyncio
    async def test_approval_pending_event(self, router, event_bus):
        """Should emit route.approval.pending when approval is required."""
        events_received = []

        async def capture_event(event):
            events_received.append(event)

        event_bus.subscribe("route.approval.pending", capture_event)

        await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test"},
            approval_required=True,
        )

        assert len(events_received) == 1
        assert events_received[0].payload["route_id"] is not None


# =============================================================================
# STATUS AND TRACKING TESTS
# =============================================================================

class TestStatusTracking:
    """Test route status and tracking."""

    @pytest.mark.asyncio
    async def test_get_route_status(self, router, mock_blotato_service):
        """Should retrieve route status by route_id."""
        mock_blotato_service.get_accounts_by_platform.return_value = [
            MagicMock(id=100, platform="tiktok", username="test", is_active=True),
        ]
        router._blotato_service = mock_blotato_service

        result = await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test"},
        )

        status = router.get_route_status(result.route_id)
        assert status is not None
        assert status["status"] == "completed"
        assert status["route_id"] == result.route_id

    def test_get_route_status_unknown(self, router):
        """Unknown route should return None."""
        status = router.get_route_status("nonexistent-id")
        assert status is None

    @pytest.mark.asyncio
    async def test_list_completed_routes(self, router, mock_blotato_service):
        """Should list completed routes."""
        mock_blotato_service.get_accounts_by_platform.return_value = [
            MagicMock(id=100, platform="tiktok", username="test", is_active=True),
        ]
        router._blotato_service = mock_blotato_service

        await router.route_content(
            video_path="/video1.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test 1"},
        )
        await router.route_content(
            video_path="/video2.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test 2"},
        )

        completed = router.list_completed_routes()
        assert len(completed) == 2

    @pytest.mark.asyncio
    async def test_stats_updated_after_routing(self, router, mock_blotato_service):
        """Stats should be updated after routing."""
        mock_blotato_service.get_accounts_by_platform.return_value = [
            MagicMock(id=100, platform="tiktok", username="test", is_active=True),
        ]
        router._blotato_service = mock_blotato_service

        await router.route_content(
            video_path="/path/to/video.mp4",
            platforms=["tiktok"],
            analysis={"hook": "Test"},
        )

        stats = router.get_stats()
        assert stats["completed_routes"] == 1
        assert stats["total_platforms_published"] >= 1


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestDataClasses:
    """Test RouteResult and PlatformResult data classes."""

    def test_platform_result_to_dict(self):
        """PlatformResult should serialize to dict."""
        result = PlatformResult(
            platform="twitter",
            success=True,
            method=PublishMethod.SAFARI,
            published_url="https://x.com/test/status/123",
            post_id="123",
        )
        d = result.to_dict()
        assert d["platform"] == "twitter"
        assert d["success"] is True
        assert d["method"] == "safari"
        assert d["published_url"] == "https://x.com/test/status/123"

    def test_route_result_to_dict(self):
        """RouteResult should serialize to dict."""
        result = RouteResult(
            route_id="test-route-123",
            status="completed",
            platforms_requested=["twitter", "tiktok"],
        )
        result.platform_results["twitter"] = PlatformResult(
            platform="twitter", success=True,
        )
        result.published_urls["twitter"] = "https://x.com/test/status/123"

        d = result.to_dict()
        assert d["route_id"] == "test-route-123"
        assert d["success_count"] == 1
        assert d["failure_count"] == 0
        assert "twitter" in d["published_urls"]

    def test_route_result_all_completed(self):
        """all_completed should be True when all platforms have results."""
        result = RouteResult(
            route_id="test",
            platforms_requested=["twitter", "tiktok"],
        )
        result.platform_results["twitter"] = PlatformResult(platform="twitter", success=True)
        assert not result.all_completed

        result.platform_results["tiktok"] = PlatformResult(platform="tiktok", success=False)
        assert result.all_completed

    def test_route_result_counts(self):
        """success_count and failure_count should be accurate."""
        result = RouteResult(route_id="test", platforms_requested=["a", "b", "c"])
        result.platform_results["a"] = PlatformResult(platform="a", success=True)
        result.platform_results["b"] = PlatformResult(platform="b", success=False)
        result.platform_results["c"] = PlatformResult(platform="c", success=True)

        assert result.success_count == 2
        assert result.failure_count == 1


# =============================================================================
# CONSTANTS TESTS
# =============================================================================

class TestConstants:
    """Test module-level constants."""

    def test_all_platforms_count(self):
        """Should have exactly 9 platforms."""
        assert len(ALL_PLATFORMS) == 9

    def test_all_platforms_list(self):
        """Should include all expected platforms."""
        expected = {
            "tiktok", "instagram", "youtube", "twitter",
            "threads", "pinterest", "linkedin", "facebook", "bluesky",
        }
        assert set(ALL_PLATFORMS) == expected

    def test_safari_supports_twitter(self):
        """Safari should support at least Twitter."""
        assert "twitter" in SAFARI_SUPPORTED_PLATFORMS

    def test_blotato_supports_all(self):
        """Blotato should support all 9 platforms."""
        assert BLOTATO_SUPPORTED_PLATFORMS == set(ALL_PLATFORMS)

    def test_platform_limits_all_have_video_support(self):
        """All platforms should indicate video support."""
        for platform, limits in PLATFORM_LIMITS.items():
            assert limits.get("supports_video") is True, f"{platform} missing video support"
