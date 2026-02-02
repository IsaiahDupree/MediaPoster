"""
Tests for TikTok Scraper Integration
Tests API rate limiting, caching, and trending content discovery
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from services.api_rate_limiter import APIRateLimiter, CachedTikTokScraperAPI, APICallLog
from services.trending_content import TrendingContentService


@pytest.fixture
def db_session():
    """Create a mock database session for testing.

    Sets up query chain mocks to simulate SQLAlchemy's fluent API.
    """
    session = MagicMock(spec=Session)
    # Setup default query chain: query().filter().count() returns 0
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.count.return_value = 0
    filter_mock.all.return_value = []
    filter_mock.delete.return_value = 0
    query_mock.filter.return_value = filter_mock
    session.query.return_value = query_mock
    return session


@pytest.fixture
def rate_limiter(db_session):
    """Create rate limiter for testing"""
    return APIRateLimiter(db_session, "tiktok_scraper")


class TestAPIRateLimiter:
    """Test API rate limiting and budget management"""

    def test_can_make_call_within_budget(self, rate_limiter, db_session):
        """Test that calls are allowed within budget"""
        # Default mock returns count=0, so budget is available
        allowed, reason = rate_limiter.can_make_call("test_endpoint")

        assert allowed is True
        assert "remaining" in reason.lower()

    def test_budget_exceeded(self, rate_limiter, db_session):
        """Test budget enforcement when limit exceeded"""
        # Mock the query chain to return count > 225 (the 90% threshold)
        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.count.return_value = 230  # Exceeds 225 limit
        query_mock.filter.return_value = filter_mock
        db_session.query.return_value = query_mock

        allowed, reason = rate_limiter.can_make_call("test_endpoint")

        assert allowed is False
        assert "exceeded" in reason.lower()

    def test_cache_hit_and_miss(self, rate_limiter):
        """Test caching functionality"""
        cache_key = "test_key"
        test_data = {"result": "test"}

        # Cache miss
        cached = rate_limiter.get_cached(cache_key)
        assert cached is None

        # Set cache
        rate_limiter.set_cache(cache_key, test_data)

        # Cache hit
        cached = rate_limiter.get_cached(cache_key, ttl_hours=24)
        assert cached == test_data

    def test_cache_expiration(self, rate_limiter):
        """Test that cache expires after TTL"""
        cache_key = "test_key"
        test_data = {"result": "test"}

        rate_limiter.set_cache(cache_key, test_data)

        # Manually set old timestamp
        rate_limiter.cache[cache_key] = (test_data, datetime.now() - timedelta(hours=25))

        # Should be expired
        cached = rate_limiter.get_cached(cache_key, ttl_hours=24)
        assert cached is None

    def test_log_call(self, rate_limiter, db_session):
        """Test API call logging"""
        rate_limiter.log_call(
            endpoint="test_endpoint",
            success=True,
            cache_hit=False,
            response_time_ms=150.5,
            call_metadata={"test": "data"}
        )

        # Verify db.add was called with an APICallLog
        assert db_session.add.called
        log_entry = db_session.add.call_args[0][0]
        assert isinstance(log_entry, APICallLog)
        assert log_entry.endpoint == "test_endpoint"
        assert log_entry.success is True
        assert log_entry.response_time_ms == 150.5
        assert db_session.commit.called

    def test_usage_stats(self, rate_limiter, db_session):
        """Test usage statistics calculation"""
        # Mock three different query chains for total_calls, api_calls, cache_hits
        call_counts = [10, 6, 4]  # total, api, cache
        counter = {"idx": 0}

        def make_filter_mock(*args, **kwargs):
            mock = MagicMock()
            # Each chained .filter() returns a new mock with the right count
            mock.filter.return_value = mock
            mock.count.return_value = call_counts[min(counter["idx"], len(call_counts) - 1)]
            counter["idx"] += 1
            return mock

        db_session.query.side_effect = lambda *a: make_filter_mock()

        stats = rate_limiter.get_usage_stats()

        assert stats["api_name"] == "tiktok_scraper"
        assert stats["total_requests"] == 10
        assert stats["cache_hits"] == 4
        assert stats["monthly_limit"] == 225  # 90% of 250


@pytest.mark.asyncio
class TestCachedTikTokScraperAPI:
    """Test cached TikTok Scraper API wrapper"""

    async def test_trending_feed_caching(self, db_session):
        """Test that trending feed results are cached"""
        api = CachedTikTokScraperAPI(db_session)

        # Mock the underlying API
        mock_result = [{"id": "123", "description": "Test"}]
        api.api.get_trending_feed = AsyncMock(return_value=mock_result)

        # First call - should hit API
        result1 = await api.get_trending_feed(region="US", count=10)
        assert result1 == mock_result
        assert api.api.get_trending_feed.call_count == 1

        # Second call - should use cache
        result2 = await api.get_trending_feed(region="US", count=10)
        assert result2 == mock_result
        assert api.api.get_trending_feed.call_count == 1  # Still 1

    async def test_rate_limit_enforcement(self, db_session):
        """Test that rate limits are enforced"""
        api = CachedTikTokScraperAPI(db_session)

        # Mock the rate limiter to report budget exceeded
        api.rate_limiter.can_make_call = MagicMock(
            return_value=(False, "Monthly budget exceeded (230/225 calls used)")
        )

        # Mock API
        api.api.get_trending_feed = AsyncMock(return_value=[])

        # Should be blocked
        result = await api.get_trending_feed()

        # Should return empty or cached result
        assert isinstance(result, list)
        # API should not have been called
        assert api.api.get_trending_feed.call_count == 0

    async def test_hashtag_search_caching(self, db_session):
        """Test hashtag search caching"""
        api = CachedTikTokScraperAPI(db_session)

        mock_result = {"videos": [{"id": "123"}], "cursor": None}
        api.api.search_hashtag = AsyncMock(return_value=mock_result)

        # First call
        result1 = await api.search_hashtag("viral", count=20)
        assert api.api.search_hashtag.call_count == 1

        # Second call - should be cached
        result2 = await api.search_hashtag("viral", count=20)
        assert api.api.search_hashtag.call_count == 1


class TestTrendingContentService:
    """Test trending content discovery service"""

    @pytest.mark.asyncio
    async def test_discover_trending_topics(self, db_session):
        """Test trending topics discovery"""
        service = TrendingContentService(db_session)

        # Mock the API
        mock_topics = [
            {
                "hashtag": "viral",
                "video_count": 50,
                "total_views": 1000000,
                "total_likes": 50000,
                "avg_engagement_rate": 0.05
            }
        ]

        service.tiktok_api.analyze_trending_topics = AsyncMock(return_value=mock_topics)

        result = await service.discover_trending_topics(region="US")

        assert len(result) > 0
        assert result[0]["hashtag"] == "viral"

    @pytest.mark.asyncio
    async def test_competitor_analysis(self, db_session):
        """Test competitor content analysis"""
        service = TrendingContentService(db_session)

        # Mock API response
        mock_response = {
            "videos": [
                {
                    "id": "123",
                    "description": "Test video",
                    "stats": {"views": 10000, "likes": 500, "shares": 100},
                    "hashtags": ["viral", "trending"]
                }
            ],
            "user": {"username": "testuser"}
        }

        service.tiktok_api.get_user_posts = AsyncMock(return_value=mock_response)

        result = await service.analyze_competitor_content("testuser")

        assert "username" in result
        assert "avg_views_per_video" in result
        assert "top_hashtags" in result

    @pytest.mark.asyncio
    async def test_hashtag_insights(self, db_session):
        """Test hashtag insights analysis"""
        service = TrendingContentService(db_session)

        mock_videos = {
            "videos": [
                {
                    "id": "123",
                    "description": "Test",
                    "stats": {"views": 10000, "likes": 500, "shares": 100},
                    "create_time": datetime.now().timestamp()
                }
            ]
        }

        service.tiktok_api.search_hashtag = AsyncMock(return_value=mock_videos)

        result = await service.get_hashtag_insights("viral")

        assert "hashtag" in result
        assert "avg_views" in result
        assert "engagement_rate" in result
        assert "recommendation" in result


def test_clear_old_logs(rate_limiter, db_session):
    """Test clearing old API logs"""
    # Mock the delete query chain
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.delete.return_value = 5  # 5 deleted
    query_mock.filter.return_value = filter_mock
    db_session.query.return_value = query_mock

    # Clear logs older than 90 days
    rate_limiter.clear_old_logs(days=90)

    # Verify delete was called
    assert filter_mock.delete.called
    assert db_session.commit.called
