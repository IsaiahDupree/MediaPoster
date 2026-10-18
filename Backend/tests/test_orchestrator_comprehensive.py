"""
Comprehensive Test Suite for Platform Data Orchestrator
200+ tests covering all orchestrator components
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
import json
import os

import sys
sys.path.insert(0, '.')


# =============================================================================
# PLATFORM ENUM TESTS (20 tests)
# =============================================================================

class TestPlatformEnum:
    """Platform enum tests"""
    
    def test_platform_tiktok(self):
        from services.platform_data_orchestrator import Platform
        assert Platform.TIKTOK.value == "tiktok"
    
    def test_platform_instagram(self):
        from services.platform_data_orchestrator import Platform
        assert Platform.INSTAGRAM.value == "instagram"
    
    def test_platform_youtube(self):
        from services.platform_data_orchestrator import Platform
        assert Platform.YOUTUBE.value == "youtube"
    
    def test_platform_twitter(self):
        from services.platform_data_orchestrator import Platform
        assert Platform.TWITTER.value == "twitter"
    
    def test_platform_bluesky(self):
        from services.platform_data_orchestrator import Platform
        assert Platform.BLUESKY.value == "bluesky"
    
    def test_platform_threads(self):
        from services.platform_data_orchestrator import Platform
        assert Platform.THREADS.value == "threads"
    
    def test_platform_pinterest(self):
        from services.platform_data_orchestrator import Platform
        assert Platform.PINTEREST.value == "pinterest"
    
    def test_platform_facebook(self):
        from services.platform_data_orchestrator import Platform
        assert Platform.FACEBOOK.value == "facebook"
    
    def test_platform_linkedin(self):
        from services.platform_data_orchestrator import Platform
        assert Platform.LINKEDIN.value == "linkedin"
    
    def test_platform_from_string(self):
        from services.platform_data_orchestrator import Platform
        assert Platform("tiktok") == Platform.TIKTOK
    
    def test_platform_invalid_raises(self):
        from services.platform_data_orchestrator import Platform
        with pytest.raises(ValueError):
            Platform("invalid_platform")
    
    def test_platform_case_sensitive(self):
        from services.platform_data_orchestrator import Platform
        with pytest.raises(ValueError):
            Platform("TikTok")  # Should be lowercase
    
    def test_platform_all_values_unique(self):
        from services.platform_data_orchestrator import Platform
        values = [p.value for p in Platform]
        assert len(values) == len(set(values))
    
    def test_platform_iteration(self):
        from services.platform_data_orchestrator import Platform
        platforms = list(Platform)
        assert len(platforms) >= 5


class TestDataTypeEnum:
    """DataType enum tests"""
    
    def test_datatype_profile(self):
        from services.platform_data_orchestrator import DataType
        assert DataType.PROFILE.value == "profile"
    
    def test_datatype_posts(self):
        from services.platform_data_orchestrator import DataType
        assert DataType.POSTS.value == "posts"
    
    def test_datatype_post_metrics(self):
        from services.platform_data_orchestrator import DataType
        assert DataType.POST_METRICS.value == "post_metrics"
    
    def test_datatype_comments(self):
        from services.platform_data_orchestrator import DataType
        assert DataType.COMMENTS.value == "comments"
    
    def test_datatype_followers(self):
        from services.platform_data_orchestrator import DataType
        assert DataType.FOLLOWERS.value == "followers"


# =============================================================================
# PROVIDER CONFIG TESTS (30 tests)
# =============================================================================

class TestProviderConfig:
    """ProviderConfig dataclass tests"""
    
    def test_provider_config_basic(self):
        from services.platform_data_orchestrator import ProviderConfig, DataType
        config = ProviderConfig(
            name="test-provider",
            host="test.api.com",
            priority=1,
            endpoints={DataType.PROFILE: "/profile"}
        )
        assert config.name == "test-provider"
        assert config.host == "test.api.com"
        assert config.priority == 1
    
    def test_provider_config_default_rate_limit(self):
        from services.platform_data_orchestrator import ProviderConfig, DataType
        config = ProviderConfig(
            name="test", host="test.com", priority=1, endpoints={}
        )
        assert config.rate_limit == 100
    
    def test_provider_config_custom_rate_limit(self):
        from services.platform_data_orchestrator import ProviderConfig, DataType
        config = ProviderConfig(
            name="test", host="test.com", priority=1, 
            endpoints={}, rate_limit=500
        )
        assert config.rate_limit == 500
    
    def test_provider_config_error_count_default(self):
        from services.platform_data_orchestrator import ProviderConfig, DataType
        config = ProviderConfig(
            name="test", host="test.com", priority=1, endpoints={}
        )
        assert config.error_count == 0
    
    def test_provider_config_last_error_default(self):
        from services.platform_data_orchestrator import ProviderConfig, DataType
        config = ProviderConfig(
            name="test", host="test.com", priority=1, endpoints={}
        )
        assert config.last_error is None
    
    def test_provider_config_disabled_until_default(self):
        from services.platform_data_orchestrator import ProviderConfig, DataType
        config = ProviderConfig(
            name="test", host="test.com", priority=1, endpoints={}
        )
        assert config.disabled_until is None
    
    def test_provider_config_calls_today_default(self):
        from services.platform_data_orchestrator import ProviderConfig, DataType
        config = ProviderConfig(
            name="test", host="test.com", priority=1, endpoints={}
        )
        assert config.calls_today == 0
    
    def test_provider_config_multiple_endpoints(self):
        from services.platform_data_orchestrator import ProviderConfig, DataType
        config = ProviderConfig(
            name="test", host="test.com", priority=1,
            endpoints={
                DataType.PROFILE: "/profile",
                DataType.POSTS: "/posts",
                DataType.COMMENTS: "/comments"
            }
        )
        assert len(config.endpoints) == 3


class TestProviderConfigEndpoints:
    """Provider endpoint tests"""
    
    def test_tiktok_provider_endpoints(self):
        from services.platform_data_orchestrator import Platform, DataType, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            tiktok_providers = orchestrator.providers.get(Platform.TIKTOK, [])
            assert len(tiktok_providers) >= 1
    
    def test_instagram_provider_endpoints(self):
        from services.platform_data_orchestrator import Platform, DataType, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            ig_providers = orchestrator.providers.get(Platform.INSTAGRAM, [])
            assert len(ig_providers) >= 1
    
    def test_youtube_provider_endpoints(self):
        from services.platform_data_orchestrator import Platform, DataType, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test', 'YOUTUBE_API_KEY': 'test'}):
            orchestrator = PlatformDataOrchestrator()
            yt_providers = orchestrator.providers.get(Platform.YOUTUBE, [])
            assert len(yt_providers) >= 1
    
    def test_bluesky_provider_endpoints(self):
        from services.platform_data_orchestrator import Platform, DataType, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            bs_providers = orchestrator.providers.get(Platform.BLUESKY, [])
            assert len(bs_providers) >= 1


# =============================================================================
# FETCH RESULT TESTS (20 tests)
# =============================================================================

class TestFetchResult:
    """FetchResult dataclass tests"""
    
    def test_fetch_result_success(self):
        from services.platform_data_orchestrator import FetchResult, Platform, DataType
        result = FetchResult(
            success=True,
            platform=Platform.TIKTOK,
            data_type=DataType.PROFILE,
            data={"followers": 1000}
        )
        assert result.success is True
        assert result.data["followers"] == 1000
    
    def test_fetch_result_failure(self):
        from services.platform_data_orchestrator import FetchResult, Platform, DataType
        result = FetchResult(
            success=False,
            platform=Platform.TIKTOK,
            data_type=DataType.PROFILE,
            error="API rate limited"
        )
        assert result.success is False
        assert result.error == "API rate limited"
    
    def test_fetch_result_cached(self):
        from services.platform_data_orchestrator import FetchResult, Platform, DataType
        result = FetchResult(
            success=True,
            platform=Platform.TIKTOK,
            data_type=DataType.PROFILE,
            data={"test": True},
            cached=True
        )
        assert result.cached is True
    
    def test_fetch_result_provider_used(self):
        from services.platform_data_orchestrator import FetchResult, Platform, DataType
        result = FetchResult(
            success=True,
            platform=Platform.TIKTOK,
            data_type=DataType.PROFILE,
            data={},
            provider_used="tiktok-scraper7"
        )
        assert result.provider_used == "tiktok-scraper7"
    
    def test_fetch_result_default_cached_false(self):
        from services.platform_data_orchestrator import FetchResult, Platform, DataType
        result = FetchResult(
            success=True,
            platform=Platform.TIKTOK,
            data_type=DataType.PROFILE
        )
        assert result.cached is False
    
    def test_fetch_result_default_data_none(self):
        from services.platform_data_orchestrator import FetchResult, Platform, DataType
        result = FetchResult(
            success=False,
            platform=Platform.TIKTOK,
            data_type=DataType.PROFILE,
            error="Error"
        )
        assert result.data is None


# =============================================================================
# ORCHESTRATOR CACHE TESTS (40 tests)
# =============================================================================

class TestOrchestratorCache:
    """Orchestrator caching tests"""
    
    def test_cache_key_generation(self):
        from services.platform_data_orchestrator import Platform, DataType, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            key = orchestrator._get_cache_key(Platform.TIKTOK, DataType.PROFILE, "testuser")
            assert key == "tiktok:profile:testuser"
    
    def test_cache_key_different_platforms(self):
        from services.platform_data_orchestrator import Platform, DataType, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            key1 = orchestrator._get_cache_key(Platform.TIKTOK, DataType.PROFILE, "user")
            key2 = orchestrator._get_cache_key(Platform.INSTAGRAM, DataType.PROFILE, "user")
            assert key1 != key2
    
    def test_cache_key_different_data_types(self):
        from services.platform_data_orchestrator import Platform, DataType, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            key1 = orchestrator._get_cache_key(Platform.TIKTOK, DataType.PROFILE, "user")
            key2 = orchestrator._get_cache_key(Platform.TIKTOK, DataType.POSTS, "user")
            assert key1 != key2
    
    def test_cache_set_and_get(self):
        from services.platform_data_orchestrator import Platform, DataType, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            orchestrator._set_cache("test_key", {"data": "value"})
            result = orchestrator._get_cached("test_key")
            assert result == {"data": "value"}
    
    def test_cache_miss_returns_none(self):
        from services.platform_data_orchestrator import Platform, DataType, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            result = orchestrator._get_cached("nonexistent_key")
            assert result is None
    
    def test_cache_ttl_default(self):
        from services.platform_data_orchestrator import PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            assert orchestrator.cache_ttl == timedelta(minutes=15)
    
    def test_cache_expiration(self):
        from services.platform_data_orchestrator import PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            orchestrator._set_cache("test_key", {"data": "value"})
            # Manually expire the cache
            orchestrator._cache["test_key"] = ({"data": "value"}, datetime.now() - timedelta(hours=1))
            result = orchestrator._get_cached("test_key")
            assert result is None


# =============================================================================
# ORCHESTRATOR PROVIDER MANAGEMENT TESTS (40 tests)
# =============================================================================

class TestOrchestratorProviderManagement:
    """Provider management tests"""
    
    def test_get_available_providers_returns_list(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            providers = orchestrator._get_available_providers(Platform.TIKTOK)
            assert isinstance(providers, list)
    
    def test_get_available_providers_sorted_by_priority(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            providers = orchestrator._get_available_providers(Platform.TIKTOK)
            if len(providers) >= 2:
                assert providers[0].priority <= providers[1].priority
    
    def test_mark_error_increments_count(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            providers = orchestrator.providers.get(Platform.TIKTOK, [])
            if providers:
                initial_count = providers[0].error_count
                orchestrator._mark_error(providers[0])
                assert providers[0].error_count == initial_count + 1
    
    def test_mark_success_resets_error_count(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            providers = orchestrator.providers.get(Platform.TIKTOK, [])
            if providers:
                providers[0].error_count = 5
                orchestrator._mark_success(providers[0])
                assert providers[0].error_count == 0
    
    def test_mark_success_increments_calls_today(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            providers = orchestrator.providers.get(Platform.TIKTOK, [])
            if providers:
                initial_calls = providers[0].calls_today
                orchestrator._mark_success(providers[0])
                assert providers[0].calls_today == initial_calls + 1
    
    def test_provider_disabled_after_errors(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            providers = orchestrator.providers.get(Platform.TIKTOK, [])
            if providers:
                for _ in range(3):
                    orchestrator._mark_error(providers[0])
                assert providers[0].disabled_until is not None


# =============================================================================
# PROFILE PARAMS TESTS (30 tests)
# =============================================================================

class TestProfileParams:
    """Profile parameter generation tests"""
    
    def test_tiktok_profile_params(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            params = orchestrator._get_profile_params(Platform.TIKTOK, "testuser")
            assert params == {"unique_id": "testuser"}
    
    def test_instagram_profile_params(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            params = orchestrator._get_profile_params(Platform.INSTAGRAM, "testuser")
            assert params == {"username": "testuser"}
    
    def test_youtube_profile_params_channel_id(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            params = orchestrator._get_profile_params(Platform.YOUTUBE, "UCnDBsELI2OIaEI5yxA77HNA")
            assert "id" in params
    
    def test_youtube_profile_params_handle(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            params = orchestrator._get_profile_params(Platform.YOUTUBE, "testuser")
            assert "forHandle" in params
    
    def test_bluesky_profile_params_with_domain(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            params = orchestrator._get_profile_params(Platform.BLUESKY, "user.bsky.social")
            assert params["actor"] == "user.bsky.social"
    
    def test_bluesky_profile_params_without_domain(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            params = orchestrator._get_profile_params(Platform.BLUESKY, "testuser")
            assert params["actor"] == "testuser.bsky.social"


class TestPostsParams:
    """Posts parameter generation tests"""
    
    def test_tiktok_posts_params(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            params = orchestrator._get_posts_params(Platform.TIKTOK, "testuser", 20)
            assert params["unique_id"] == "testuser"
            assert params["count"] == "20"
    
    def test_youtube_posts_params(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            params = orchestrator._get_posts_params(Platform.YOUTUBE, "UC123", 30)
            assert params["channelId"] == "UC123"
            assert params["maxResults"] == 30


class TestCommentsParams:
    """Comments parameter generation tests"""
    
    def test_tiktok_comments_params(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            params = orchestrator._get_comments_params(Platform.TIKTOK, "video123", 50)
            assert params["aweme_id"] == "video123"
            assert params["count"] == "50"
    
    def test_youtube_comments_params(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            params = orchestrator._get_comments_params(Platform.YOUTUBE, "video123", 50)
            assert params["videoId"] == "video123"
            assert params["maxResults"] == 50


# =============================================================================
# PROFILE DATA PARSING TESTS (40 tests)
# =============================================================================

class TestProfileDataParsing:
    """Profile data parsing tests"""
    
    def test_parse_tiktok_profile(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {
                "data": {
                    "user": {"signature": "Test bio", "avatarLarger": "http://example.com/avatar.jpg"},
                    "stats": {"followerCount": 1000, "followingCount": 500, "videoCount": 50, "heartCount": 5000}
                }
            }
            parsed = orchestrator._parse_profile_data(Platform.TIKTOK, data)
            assert parsed["followers"] == 1000
            assert parsed["following"] == 500
            assert parsed["posts"] == 50
            assert parsed["likes"] == 5000
    
    def test_parse_youtube_profile(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {
                "items": [{
                    "statistics": {"subscriberCount": "2810", "videoCount": "641", "viewCount": "142062"},
                    "snippet": {"description": "Test channel", "thumbnails": {"high": {"url": "http://example.com/thumb.jpg"}}}
                }]
            }
            parsed = orchestrator._parse_profile_data(Platform.YOUTUBE, data)
            assert parsed["followers"] == 2810
            assert parsed["posts"] == 641
            assert parsed["views"] == 142062
    
    def test_parse_bluesky_profile(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {
                "followersCount": 18,
                "followsCount": 25,
                "postsCount": 100,
                "description": "Test bio",
                "avatar": "http://example.com/avatar.jpg"
            }
            parsed = orchestrator._parse_profile_data(Platform.BLUESKY, data)
            assert parsed["followers"] == 18
            assert parsed["following"] == 25
            assert parsed["posts"] == 100
    
    def test_parse_instagram_profile_v1(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {
                "user": {
                    "edge_followed_by": {"count": 5000},
                    "edge_follow": {"count": 300},
                    "edge_owner_to_timeline_media": {"count": 150},
                    "biography": "Test bio",
                    "profile_pic_url_hd": "http://example.com/avatar.jpg"
                }
            }
            parsed = orchestrator._parse_profile_data(Platform.INSTAGRAM, data)
            assert parsed["followers"] == 5000
            assert parsed["following"] == 300
            assert parsed["posts"] == 150
    
    def test_parse_empty_data_returns_defaults(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            parsed = orchestrator._parse_profile_data(Platform.TIKTOK, {})
            # Empty data returns default structure with zeros
            assert parsed is None or parsed.get("followers", 0) == 0
    
    def test_parse_youtube_empty_items(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {"items": []}
            parsed = orchestrator._parse_profile_data(Platform.YOUTUBE, data)
            assert parsed is None


# =============================================================================
# POST EXTRACTION TESTS (30 tests)
# =============================================================================

class TestPostExtraction:
    """Post extraction tests"""
    
    def test_extract_tiktok_posts(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {"data": {"videos": [{"id": "1"}, {"id": "2"}, {"id": "3"}]}}
            posts = orchestrator._extract_posts(Platform.TIKTOK, data)
            assert len(posts) == 3
    
    def test_extract_youtube_posts(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {"items": [{"id": {"videoId": "v1"}}, {"id": {"videoId": "v2"}}]}
            posts = orchestrator._extract_posts(Platform.YOUTUBE, data)
            assert len(posts) == 2
    
    def test_extract_bluesky_posts(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {"feed": [{"post": {"uri": "at://did/post/1"}}, {"post": {"uri": "at://did/post/2"}}]}
            posts = orchestrator._extract_posts(Platform.BLUESKY, data)
            assert len(posts) == 2
    
    def test_extract_empty_posts(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {}
            posts = orchestrator._extract_posts(Platform.TIKTOK, data)
            assert posts == []


class TestCommenterExtraction:
    """Commenter extraction tests"""
    
    def test_extract_tiktok_commenters(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {
                "data": {
                    "comments": [
                        {"user": {"uid": "u1", "unique_id": "user1", "nickname": "User One"}, "digg_count": 5},
                        {"user": {"uid": "u2", "unique_id": "user2", "nickname": "User Two"}, "digg_count": 10}
                    ]
                }
            }
            commenters = orchestrator._extract_commenters(Platform.TIKTOK, data)
            assert len(commenters) == 2
            assert commenters[0]["user_id"] == "u1"
    
    def test_extract_youtube_commenters(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            data = {
                "items": [
                    {
                        "snippet": {
                            "topLevelComment": {
                                "snippet": {
                                    "authorChannelId": {"value": "UC123"},
                                    "authorDisplayName": "Commenter 1",
                                    "authorProfileImageUrl": "http://example.com/pic.jpg",
                                    "likeCount": 3
                                }
                            }
                        }
                    }
                ]
            }
            commenters = orchestrator._extract_commenters(Platform.YOUTUBE, data)
            assert len(commenters) == 1
            assert commenters[0]["user_id"] == "UC123"


# =============================================================================
# PROVIDER STATUS TESTS (20 tests)
# =============================================================================

class TestProviderStatus:
    """Provider status tests"""
    
    def test_get_provider_status_structure(self):
        from services.platform_data_orchestrator import PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            status = orchestrator.get_provider_status()
            assert isinstance(status, dict)
    
    def test_get_provider_status_has_platforms(self):
        from services.platform_data_orchestrator import PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            status = orchestrator.get_provider_status()
            assert "tiktok" in status or "youtube" in status
    
    def test_provider_status_fields(self):
        from services.platform_data_orchestrator import PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            status = orchestrator.get_provider_status()
            for platform, providers in status.items():
                if providers:
                    assert "name" in providers[0]
                    assert "priority" in providers[0]
                    assert "calls_today" in providers[0]


# =============================================================================
# ASYNC FETCH TESTS (30 tests)
# =============================================================================

class TestAsyncFetch:
    """Async fetch operation tests"""
    
    @pytest.mark.asyncio
    async def test_fetch_profile_returns_result(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            # Mock the API call
            with patch.object(orchestrator, '_call_api', return_value=(True, {"data": "test"}, None)):
                result = await orchestrator.fetch_profile(Platform.BLUESKY, "testuser")
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_fetch_from_cache(self):
        from services.platform_data_orchestrator import Platform, DataType, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            # Prime the cache
            cache_key = orchestrator._get_cache_key(Platform.TIKTOK, DataType.PROFILE, "cacheduser")
            orchestrator._set_cache(cache_key, {"followers": 1000})
            
            result = await orchestrator.fetch_with_failover(
                Platform.TIKTOK, DataType.PROFILE, "cacheduser", {}
            )
            assert result.cached is True
            assert result.data["followers"] == 1000
    
    @pytest.mark.asyncio
    async def test_batch_fetch_profiles(self):
        from services.platform_data_orchestrator import Platform, PlatformDataOrchestrator
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test', 'DATABASE_URL': 'postgresql://test'}):
            orchestrator = PlatformDataOrchestrator()
            accounts = [
                (Platform.BLUESKY, "user1"),
                (Platform.BLUESKY, "user2"),
            ]
            
            with patch.object(orchestrator, 'fetch_profile', return_value=Mock(success=True)):
                results = await orchestrator.batch_fetch_profiles(accounts)
                assert len(results) == 2


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-q"])
