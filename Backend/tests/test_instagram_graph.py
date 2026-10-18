"""
Tests for Instagram Graph API Service (IGAPI-001 through IGAPI-005)
===================================================================
Comprehensive test coverage for OAuth, Graph API client, insights,
publishing, and comments management features.
"""
import pytest
import time
from datetime import datetime, timedelta, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.instagram_graph_service import (
    InstagramGraphService,
    IGOAuthConfig,
    IGMediaType,
    IGInsight,
    get_instagram_graph_service,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def oauth_config():
    """Provide a pre-configured IGOAuthConfig for testing."""
    return IGOAuthConfig(
        client_id="test_client_123",
        client_secret="test_secret_456",
        redirect_uri="https://example.com/callback",
    )


@pytest.fixture
def service(oauth_config):
    """Provide a fresh InstagramGraphService instance per test."""
    return InstagramGraphService(config=oauth_config)


@pytest.fixture
def authenticated_service(service):
    """Provide a service that already has an access token set."""
    service.config.access_token = "test_token_abc123"
    service.config.token_expires_at = datetime.now(timezone.utc) + timedelta(days=60)
    return service


# ===========================================================================
# IGAPI-001: OAuth Flow
# ===========================================================================

class TestIGAPI001_OAuthFlow:
    """Tests for Instagram OAuth flow: auth URL generation, code exchange,
    token refresh, and authentication state."""

    def test_auth_url_contains_client_id(self, service):
        """Auth URL must include the configured client_id."""
        url = service.get_auth_url()
        assert "client_id=test_client_123" in url

    def test_auth_url_contains_redirect_uri(self, service):
        """Auth URL must include the configured redirect_uri."""
        url = service.get_auth_url()
        assert "redirect_uri=https://example.com/callback" in url

    def test_auth_url_contains_scopes(self, service):
        """Auth URL must include all default scopes."""
        url = service.get_auth_url()
        assert "instagram_basic" in url
        assert "instagram_content_publish" in url
        assert "instagram_manage_comments" in url
        assert "instagram_manage_insights" in url

    def test_auth_url_response_type_code(self, service):
        """Auth URL must request response_type=code."""
        url = service.get_auth_url()
        assert "response_type=code" in url

    @pytest.mark.asyncio
    async def test_exchange_code_returns_token(self, service):
        """Exchanging a code must return a dict with an access_token."""
        result = await service.exchange_code("auth_code_xyz")
        assert "access_token" in result
        assert len(result["access_token"]) == 40
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == 5184000

    @pytest.mark.asyncio
    async def test_exchange_code_sets_service_token(self, service):
        """After exchanging a code, the service must be authenticated."""
        assert not service.is_authenticated()
        await service.exchange_code("auth_code_xyz")
        assert service.is_authenticated()
        assert service.config.access_token is not None

    @pytest.mark.asyncio
    async def test_refresh_token_updates_token(self, authenticated_service):
        """Refreshing must produce a new, different token."""
        old_token = authenticated_service.config.access_token
        result = await authenticated_service.refresh_token()
        assert result["access_token"] != old_token
        assert authenticated_service.config.access_token == result["access_token"]

    @pytest.mark.asyncio
    async def test_refresh_token_without_token_raises(self, service):
        """Refreshing without an existing token must raise ValueError."""
        with pytest.raises(ValueError, match="No access token"):
            await service.refresh_token()

    def test_is_authenticated_false_initially(self, service):
        """A fresh service with no token is not authenticated."""
        assert not service.is_authenticated()

    def test_oauth_config_to_dict(self, oauth_config):
        """to_dict must expose expected keys without leaking the secret."""
        d = oauth_config.to_dict()
        assert d["client_id"] == "test_client_123"
        assert "client_secret" not in d
        assert d["has_token"] is False
        assert d["token_valid"] is False

    def test_token_validity_expired(self, oauth_config):
        """A token with an expiry in the past must not be valid."""
        oauth_config.access_token = "tok"
        oauth_config.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert not oauth_config.is_token_valid

    def test_token_validity_future(self, oauth_config):
        """A token with a future expiry must be valid."""
        oauth_config.access_token = "tok"
        oauth_config.token_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        assert oauth_config.is_token_valid


# ===========================================================================
# IGAPI-002: Graph API Client
# ===========================================================================

class TestIGAPI002_GraphAPIClient:
    """Tests for the core Graph API client: requests, rate limiting,
    account info retrieval."""

    @pytest.mark.asyncio
    async def test_api_request_returns_success(self, service):
        """A basic API request must return a success response."""
        result = await service.api_request("/me", method="GET")
        assert result["success"] is True
        assert result["endpoint"] == "/me"
        assert result["method"] == "GET"

    @pytest.mark.asyncio
    async def test_api_request_increments_count(self, service):
        """Each API request must increment the request counter."""
        assert service._request_count == 0
        await service.api_request("/me")
        assert service._request_count == 1
        await service.api_request("/me/media")
        assert service._request_count == 2

    @pytest.mark.asyncio
    async def test_api_request_decrements_rate_limit(self, service):
        """Each API request must decrement the remaining rate-limit counter."""
        initial = service._rate_limit_remaining
        await service.api_request("/me")
        assert service._rate_limit_remaining == initial - 1

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_raises(self, service):
        """Exceeding the rate limit must raise RuntimeError."""
        service._rate_limit_remaining = 0
        service._rate_limit_reset = time.time() + 3600  # reset in the future
        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            await service.api_request("/me")

    def test_get_rate_limit_status(self, service):
        """Rate limit status must report remaining, reset_at, total_requests."""
        status = service.get_rate_limit_status()
        assert "remaining" in status
        assert "reset_at" in status
        assert "total_requests" in status
        assert status["remaining"] == 200
        assert status["total_requests"] == 0

    @pytest.mark.asyncio
    async def test_get_account_info_default(self, service):
        """get_account_info with default arg must return 'me' id."""
        info = await service.get_account_info()
        assert info["id"] == "me"
        assert "username" in info
        assert "followers_count" in info

    @pytest.mark.asyncio
    async def test_get_account_info_specific_user(self, service):
        """get_account_info must reflect the provided user id."""
        info = await service.get_account_info("12345")
        assert info["id"] == "12345"


# ===========================================================================
# IGAPI-003: Official Insights
# ===========================================================================

class TestIGAPI003_OfficialInsights:
    """Tests for insights retrieval: account insights, media insights,
    follower demographics, and metric filtering."""

    @pytest.mark.asyncio
    async def test_account_insights_returns_requested_metrics(self, service):
        """Only valid requested metrics should be returned."""
        insights = await service.get_account_insights(
            "user1", ["impressions", "reach", "profile_views"]
        )
        assert len(insights) == 3
        names = [i.name for i in insights]
        assert "impressions" in names
        assert "reach" in names
        assert "profile_views" in names

    @pytest.mark.asyncio
    async def test_account_insights_filters_invalid_metrics(self, service):
        """Invalid metric names must be silently excluded."""
        insights = await service.get_account_insights(
            "user1", ["impressions", "fake_metric", "nonexistent"]
        )
        assert len(insights) == 1
        assert insights[0].name == "impressions"

    @pytest.mark.asyncio
    async def test_account_insights_period(self, service):
        """Each insight must carry the requested period."""
        insights = await service.get_account_insights(
            "user1", ["reach"], period="week"
        )
        assert insights[0].period == "week"

    @pytest.mark.asyncio
    async def test_account_insights_stored_internally(self, service):
        """Insights must be cached in the service's internal store."""
        await service.get_account_insights("user1", ["reach"])
        assert "user1" in service._insights_data

    @pytest.mark.asyncio
    async def test_media_insights_default_metrics(self, service):
        """media insights with no explicit metrics uses the default set."""
        insights = await service.get_media_insights("media_001")
        assert len(insights) == 5
        names = [i.name for i in insights]
        assert "impressions" in names
        assert "engagement" in names
        assert "saved" in names

    @pytest.mark.asyncio
    async def test_media_insights_custom_metrics(self, service):
        """Custom metric list must be respected."""
        insights = await service.get_media_insights(
            "media_001", metrics=["likes", "comments"]
        )
        assert len(insights) == 2
        assert insights[0].name == "likes"
        assert insights[1].name == "comments"

    @pytest.mark.asyncio
    async def test_media_insights_lifetime_period(self, service):
        """Media-level insights must have period='lifetime'."""
        insights = await service.get_media_insights("media_001")
        for insight in insights:
            assert insight.period == "lifetime"

    @pytest.mark.asyncio
    async def test_follower_demographics_structure(self, service):
        """Demographics must contain age_gender, cities, countries keys."""
        demo = await service.get_follower_demographics("user1")
        assert "age_gender" in demo
        assert "cities" in demo
        assert "countries" in demo

    @pytest.mark.asyncio
    async def test_insight_dataclass_fields(self, service):
        """IGInsight instances must have all expected fields."""
        insights = await service.get_account_insights("user1", ["reach"])
        insight = insights[0]
        assert isinstance(insight, IGInsight)
        assert insight.title == "Reach"
        assert isinstance(insight.values, list)
        assert len(insight.values) > 0


# ===========================================================================
# IGAPI-004: Publishing via API
# ===========================================================================

class TestIGAPI004_PublishingViaAPI:
    """Tests for publishing images, videos/reels, and carousels."""

    @pytest.mark.asyncio
    async def test_publish_image_returns_media_id(self, service):
        """Publishing an image must return a result with an id and status."""
        result = await service.publish_image(
            "user1", "https://cdn.example.com/photo.jpg", caption="Hello IG"
        )
        assert "id" in result
        assert result["status"] == "published"
        assert result["media_type"] == "IMAGE"
        assert result["caption"] == "Hello IG"

    @pytest.mark.asyncio
    async def test_publish_image_permalink(self, service):
        """Published image must have an instagram.com permalink."""
        result = await service.publish_image(
            "user1", "https://cdn.example.com/photo.jpg"
        )
        assert result["permalink"].startswith("https://www.instagram.com/p/")

    @pytest.mark.asyncio
    async def test_publish_image_stored_internally(self, service):
        """Published images must appear in the internal media store."""
        result = await service.publish_image(
            "user1", "https://cdn.example.com/photo.jpg"
        )
        assert result["id"] in service._published_media

    @pytest.mark.asyncio
    async def test_publish_video_reel(self, service):
        """Publishing a reel must set media_type to REEL."""
        result = await service.publish_video(
            "user1", "https://cdn.example.com/video.mp4",
            caption="My reel", media_type="REEL"
        )
        assert result["media_type"] == "REEL"
        assert result["status"] == "published"
        assert result["permalink"].startswith("https://www.instagram.com/reel/")

    @pytest.mark.asyncio
    async def test_publish_carousel_success(self, service):
        """Publishing a carousel with 2-10 items must succeed."""
        urls = [
            "https://cdn.example.com/img1.jpg",
            "https://cdn.example.com/img2.jpg",
            "https://cdn.example.com/img3.jpg",
        ]
        result = await service.publish_carousel("user1", urls, caption="Swipe!")
        assert result["media_type"] == "CAROUSEL_ALBUM"
        assert result["children_count"] == 3
        assert result["status"] == "published"

    @pytest.mark.asyncio
    async def test_publish_carousel_too_few_items(self, service):
        """A carousel with fewer than 2 items must raise ValueError."""
        with pytest.raises(ValueError, match="at least 2"):
            await service.publish_carousel("user1", ["https://cdn.example.com/img1.jpg"])

    @pytest.mark.asyncio
    async def test_publish_carousel_too_many_items(self, service):
        """A carousel with more than 10 items must raise ValueError."""
        urls = [f"https://cdn.example.com/img{i}.jpg" for i in range(11)]
        with pytest.raises(ValueError, match="maximum 10"):
            await service.publish_carousel("user1", urls)

    @pytest.mark.asyncio
    async def test_get_published_media_after_multiple_publishes(self, service):
        """get_published_media must return all items published so far."""
        await service.publish_image("user1", "https://cdn.example.com/a.jpg")
        await service.publish_video("user1", "https://cdn.example.com/b.mp4")
        media_list = await service.get_published_media()
        assert len(media_list) == 2

    @pytest.mark.asyncio
    async def test_publish_image_deterministic_id(self, service):
        """Same image URL must produce the same media id (deterministic hash)."""
        r1 = await service.publish_image("user1", "https://cdn.example.com/same.jpg")
        r2 = await service.publish_image("user1", "https://cdn.example.com/same.jpg")
        assert r1["id"] == r2["id"]

    @pytest.mark.asyncio
    async def test_publish_video_different_media_types(self, service):
        """publish_video must accept arbitrary media_type strings."""
        result = await service.publish_video(
            "user1", "https://cdn.example.com/v.mp4", media_type="VIDEO"
        )
        assert result["media_type"] == "VIDEO"


# ===========================================================================
# IGAPI-005: Comments API
# ===========================================================================

class TestIGAPI005_CommentsAPI:
    """Tests for reading, replying to, deleting, and moderating comments."""

    @pytest.mark.asyncio
    async def test_get_comments_empty(self, service):
        """Getting comments on a media with no comments returns empty list."""
        comments = await service.get_comments("media_no_comments")
        assert comments == []

    @pytest.mark.asyncio
    async def test_get_comments_with_data(self, service):
        """Pre-populated comments must be retrievable."""
        service._comments["media_42"] = [
            {"id": "c1", "text": "Nice photo!", "timestamp": "2025-01-01T00:00:00Z"},
            {"id": "c2", "text": "Love it", "timestamp": "2025-01-01T01:00:00Z"},
        ]
        comments = await service.get_comments("media_42")
        assert len(comments) == 2
        assert comments[0]["id"] == "c1"

    @pytest.mark.asyncio
    async def test_get_comments_limit(self, service):
        """The limit parameter must cap the number of returned comments."""
        service._comments["media_99"] = [
            {"id": f"c{i}", "text": f"Comment {i}"} for i in range(100)
        ]
        comments = await service.get_comments("media_99", limit=5)
        assert len(comments) == 5

    @pytest.mark.asyncio
    async def test_reply_to_comment(self, service):
        """Replying to a comment must return a reply with parent_id."""
        reply = await service.reply_to_comment("c1", "Thanks!")
        assert reply["parent_id"] == "c1"
        assert reply["text"] == "Thanks!"
        assert "id" in reply
        assert reply["id"].startswith("reply_")

    @pytest.mark.asyncio
    async def test_reply_deterministic_id(self, service):
        """Same comment+message must produce the same reply id."""
        r1 = await service.reply_to_comment("c1", "Thanks!")
        r2 = await service.reply_to_comment("c1", "Thanks!")
        assert r1["id"] == r2["id"]

    @pytest.mark.asyncio
    async def test_delete_comment(self, service):
        """Deleting a comment must return True."""
        result = await service.delete_comment("c1")
        assert result is True

    @pytest.mark.asyncio
    async def test_moderate_comments_flags_matching(self, service):
        """Comments containing flagged keywords must be identified."""
        service._comments["media_mod"] = [
            {"id": "c1", "text": "Great post!"},
            {"id": "c2", "text": "Buy cheap followers now"},
            {"id": "c3", "text": "Love the content"},
            {"id": "c4", "text": "Free followers click here"},
        ]
        result = await service.moderate_comments("media_mod", ["followers", "cheap"])
        assert result["total_comments"] == 4
        assert result["flagged"] == 2
        flagged_ids = [c["id"] for c in result["flagged_comments"]]
        assert "c2" in flagged_ids
        assert "c4" in flagged_ids

    @pytest.mark.asyncio
    async def test_moderate_comments_no_matches(self, service):
        """When no keywords match, flagged count must be zero."""
        service._comments["media_clean"] = [
            {"id": "c1", "text": "Beautiful sunset"},
        ]
        result = await service.moderate_comments("media_clean", ["spam", "scam"])
        assert result["flagged"] == 0
        assert result["flagged_comments"] == []

    @pytest.mark.asyncio
    async def test_moderate_comments_case_insensitive(self, service):
        """Keyword matching must be case-insensitive."""
        service._comments["media_case"] = [
            {"id": "c1", "text": "BUY FOLLOWERS NOW"},
        ]
        result = await service.moderate_comments("media_case", ["followers"])
        assert result["flagged"] == 1

    @pytest.mark.asyncio
    async def test_moderate_empty_media(self, service):
        """Moderating a media with no comments returns zeroes."""
        result = await service.moderate_comments("nonexistent", ["spam"])
        assert result["total_comments"] == 0
        assert result["flagged"] == 0


# ===========================================================================
# Singleton / Factory
# ===========================================================================

class TestSingletonFactory:
    """Tests for the module-level singleton factory function."""

    def test_get_instagram_graph_service_returns_instance(self):
        """Factory must return an InstagramGraphService instance."""
        import services.instagram_graph_service as mod
        mod._instance = None  # reset singleton
        svc = get_instagram_graph_service()
        assert isinstance(svc, InstagramGraphService)

    def test_get_instagram_graph_service_singleton(self):
        """Repeated calls must return the same object."""
        import services.instagram_graph_service as mod
        mod._instance = None
        svc1 = get_instagram_graph_service()
        svc2 = get_instagram_graph_service()
        assert svc1 is svc2

    def test_get_instagram_graph_service_with_config(self):
        """Factory must accept and apply a custom config."""
        import services.instagram_graph_service as mod
        mod._instance = None
        cfg = IGOAuthConfig(client_id="custom_id")
        svc = get_instagram_graph_service(cfg)
        assert svc.config.client_id == "custom_id"
        mod._instance = None  # cleanup


# ===========================================================================
# IGMediaType Enum
# ===========================================================================

class TestIGMediaType:
    """Tests for the IGMediaType enumeration."""

    def test_image_value(self):
        assert IGMediaType.IMAGE.value == "IMAGE"

    def test_video_value(self):
        assert IGMediaType.VIDEO.value == "VIDEO"

    def test_carousel_value(self):
        assert IGMediaType.CAROUSEL.value == "CAROUSEL_ALBUM"

    def test_reel_value(self):
        assert IGMediaType.REEL.value == "REEL"

    def test_story_value(self):
        assert IGMediaType.STORY.value == "STORY"
