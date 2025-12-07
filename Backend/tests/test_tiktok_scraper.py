"""
Tests for TikTok Scraper Integration
Tests API rate limiting, caching, and trending content discovery
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from services.api_rate_limiter import APIRateLimiter, CachedTikTokScraperAPI, APICallLog
from services.trending_content import TrendingContentService
from database.db import SessionLocal


@pytest.fixture
def db_session():
    """Create a test database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def rate_limiter(db_session):
    """Create rate limiter for testing"""
    return APIRateLimiter(db_session, "tiktok_scraper")


class TestAPIRateLimiter:
    """Test API rate limiting and budget management"""
    
    def test_can_make_call_within_budget(self, rate_limiter, db_session):
        """Test that calls are allowed within budget"""
        allowed, reason = rate_limiter.can_make_call("test_endpoint")
        
        assert allowed is True
        assert "remaining" in reason.lower()
    
    def test_budget_exceeded(self, rate_limiter, db_session):
        """Test budget enforcement when limit exceeded"""
        # Create fake logs to exceed budget
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(230):  # Exceed 90% of 250 = 225
            log = APICallLog(
                api_name="tiktok_scraper",
                endpoint="test",
                timestamp=month_start + timedelta(hours=i),
                success=True,
                cache_hit=False
            )
            db_session.add(log)
        
        db_session.commit()
        
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
            metadata={"test": "data"}
        )
        
        # Verify log was created
        logs = db_session.query(APICallLog).filter(
            APICallLog.endpoint == "test_endpoint"
        ).all()
        
        assert len(logs) == 1
        assert logs[0].success is True
        assert logs[0].response_time_ms == 150.5
    
    def test_usage_stats(self, rate_limiter, db_session):
        """Test usage statistics calculation"""
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Create some test logs
        for i in range(10):
            log = APICallLog(
                api_name="tiktok_scraper",
                endpoint="test",
                timestamp=month_start + timedelta(hours=i),
                success=True,
                cache_hit=(i % 3 == 0)  # Every 3rd is cache hit
            )
            db_session.add(log)
        
        db_session.commit()
        
        stats = rate_limiter.get_usage_stats()
        
        assert stats["api_name"] == "tiktok_scraper"
        assert stats["total_requests"] >= 10
        assert stats["cache_hits"] >= 3
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
        
        # Fill up the budget
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for i in range(230):
            log = APICallLog(
                api_name="tiktok_scraper",
                endpoint="get_trending_feed",
                timestamp=month_start + timedelta(hours=i),
                success=True,
                cache_hit=False
            )
            db_session.add(log)
        db_session.commit()
        
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
    # Create old logs
    old_date = datetime.now() - timedelta(days=100)
    
    for i in range(5):
        log = APICallLog(
            api_name="tiktok_scraper",
            endpoint="test",
            timestamp=old_date,
            success=True
        )
        db_session.add(log)
    
    db_session.commit()
    
    # Clear logs older than 90 days
    rate_limiter.clear_old_logs(days=90)
    
    # Verify old logs are gone
    old_logs = db_session.query(APICallLog).filter(
        APICallLog.timestamp < datetime.now() - timedelta(days=90)
    ).count()
    
    assert old_logs == 0
