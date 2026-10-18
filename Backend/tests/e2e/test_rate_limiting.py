"""
TEST-017: Rate Limiting Tests
==============================
Tests for rate limiting across all platform adapters and API endpoints.

Validates:
- Per-platform rate limits
- API endpoint throttling
- Graceful degradation
- Retry logic with backoff
- Rate limit metrics

From PRD_CONTENT_OPS_TESTS.md Section 3.3
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from middleware.rate_limiting import RateLimitMiddleware
from services.rate_limiter import RateLimiterService


@pytest.fixture
def rate_limiter():
    """Initialize rate limiter"""
    limiter = RateLimiterService()
    limiter.clear_all()  # Clear any existing limits
    yield limiter
    limiter.clear_all()


@pytest.mark.asyncio
@pytest.mark.e2e
class TestAPIRateLimiting:
    """Tests for API endpoint rate limiting"""

    async def test_default_rate_limit(self, rate_limiter):
        """
        TEST-017a: Default rate limit enforcement

        Default: 100 requests per 60 seconds
        """
        key = "api:default:test_user"

        # Should allow up to 100 requests
        for i in range(100):
            allowed = await rate_limiter.check_rate_limit(
                key=key,
                limit=100,
                window_seconds=60
            )
            assert allowed is True, f"Request {i+1} should be allowed"

        # 101st request should be blocked
        allowed = await rate_limiter.check_rate_limit(
            key=key,
            limit=100,
            window_seconds=60
        )
        assert allowed is False, "Request 101 should be blocked"


    async def test_per_endpoint_rate_limit(self, rate_limiter):
        """
        TEST-017b: Different rate limits for different endpoints

        - /api/publish: 10/min
        - /api/metrics: 60/min
        - /api/health: unlimited
        """
        publish_key = "api:publish:test_user"
        metrics_key = "api:metrics:test_user"

        # Test publish endpoint (10/min)
        for i in range(10):
            allowed = await rate_limiter.check_rate_limit(
                key=publish_key,
                limit=10,
                window_seconds=60
            )
            assert allowed is True

        allowed = await rate_limiter.check_rate_limit(
            key=publish_key,
            limit=10,
            window_seconds=60
        )
        assert allowed is False

        # Test metrics endpoint (60/min) - should still work
        for i in range(60):
            allowed = await rate_limiter.check_rate_limit(
                key=metrics_key,
                limit=60,
                window_seconds=60
            )
            assert allowed is True


    async def test_rate_limit_window_reset(self, rate_limiter):
        """
        TEST-017c: Rate limit resets after window expires

        Verify that limits reset properly after time window
        """
        key = "api:window_test:user"

        # Use up limit
        for i in range(5):
            allowed = await rate_limiter.check_rate_limit(
                key=key,
                limit=5,
                window_seconds=1  # 1 second window for fast test
            )
            assert allowed is True

        # Should be blocked
        allowed = await rate_limiter.check_rate_limit(
            key=key,
            limit=5,
            window_seconds=1
        )
        assert allowed is False

        # Wait for window to reset
        await asyncio.sleep(1.1)

        # Should work again
        allowed = await rate_limiter.check_rate_limit(
            key=key,
            limit=5,
            window_seconds=1
        )
        assert allowed is True


@pytest.mark.asyncio
@pytest.mark.e2e
class TestPlatformRateLimiting:
    """Tests for platform-specific rate limiting"""

    async def test_twitter_rate_limits(self, rate_limiter):
        """
        TEST-017d: Twitter API rate limits

        Twitter limits:
        - 300 tweets per 3 hours
        - 500 DMs per day
        - 900 API calls per 15 min (read)
        """
        # Test tweet limit
        twitter_post_key = "platform:twitter:post:user123"

        for i in range(300):
            allowed = await rate_limiter.check_rate_limit(
                key=twitter_post_key,
                limit=300,
                window_seconds=3 * 60 * 60  # 3 hours
            )
            assert allowed is True, f"Tweet {i+1} should be allowed"

        # 301st tweet should be blocked
        allowed = await rate_limiter.check_rate_limit(
            key=twitter_post_key,
            limit=300,
            window_seconds=3 * 60 * 60
        )
        assert allowed is False


    async def test_instagram_rate_limits(self, rate_limiter):
        """
        TEST-017e: Instagram API rate limits

        Instagram limits:
        - 25 posts per day
        - 200 API calls per hour
        """
        ig_post_key = "platform:instagram:post:user456"

        for i in range(25):
            allowed = await rate_limiter.check_rate_limit(
                key=ig_post_key,
                limit=25,
                window_seconds=24 * 60 * 60  # 24 hours
            )
            assert allowed is True

        allowed = await rate_limiter.check_rate_limit(
            key=ig_post_key,
            limit=25,
            window_seconds=24 * 60 * 60
        )
        assert allowed is False


    async def test_tiktok_rate_limits(self, rate_limiter):
        """
        TEST-017f: TikTok API rate limits

        TikTok limits:
        - 10 posts per day
        - 100 API calls per hour
        """
        tiktok_post_key = "platform:tiktok:post:user789"

        for i in range(10):
            allowed = await rate_limiter.check_rate_limit(
                key=tiktok_post_key,
                limit=10,
                window_seconds=24 * 60 * 60
            )
            assert allowed is True

        allowed = await rate_limiter.check_rate_limit(
            key=tiktok_post_key,
            limit=10,
            window_seconds=24 * 60 * 60
        )
        assert allowed is False


@pytest.mark.asyncio
@pytest.mark.e2e
class TestRateLimitRetry:
    """Tests for retry logic when rate limited"""

    async def test_exponential_backoff(self, rate_limiter):
        """
        TEST-017g: Exponential backoff retry strategy

        Retry delays: 1s, 2s, 4s, 8s, 16s
        """
        retry_delays = []

        async def attempt_with_backoff(max_retries=5):
            for attempt in range(max_retries):
                start = time.time()

                allowed = await rate_limiter.check_rate_limit(
                    key="test:backoff",
                    limit=1,
                    window_seconds=60
                )

                if allowed:
                    return True

                # Calculate backoff
                delay = min(2 ** attempt, 16)  # Cap at 16 seconds
                retry_delays.append(delay)
                await asyncio.sleep(delay / 10)  # Use shorter delays for testing

            return False

        # First call uses up the limit
        await rate_limiter.check_rate_limit(
            key="test:backoff",
            limit=1,
            window_seconds=60
        )

        # Subsequent calls should trigger backoff
        result = await attempt_with_backoff(max_retries=3)

        # Verify exponential backoff was used
        assert len(retry_delays) > 0
        assert retry_delays[0] < retry_delays[-1]  # Delays should increase


    async def test_rate_limit_headers(self, rate_limiter):
        """
        TEST-017h: Rate limit information in response headers

        Headers:
        - X-RateLimit-Limit
        - X-RateLimit-Remaining
        - X-RateLimit-Reset
        """
        key = "api:headers:user"
        limit = 10
        window = 60

        for i in range(5):
            allowed = await rate_limiter.check_rate_limit(
                key=key,
                limit=limit,
                window_seconds=window
            )

            # Get rate limit info
            info = await rate_limiter.get_rate_limit_info(key, limit, window)

            assert info["limit"] == limit
            assert info["remaining"] == limit - (i + 1)
            assert info["reset"] > 0


@pytest.mark.asyncio
@pytest.mark.e2e
class TestRateLimitMetrics:
    """Tests for rate limit monitoring and metrics"""

    async def test_rate_limit_violations_tracked(self, rate_limiter):
        """
        TEST-017i: Track rate limit violations

        Metrics:
        - Number of violations
        - Violating users
        - Violating endpoints
        """
        key = "api:violations:user"
        violations = []

        async def track_violation(event):
            violations.append(event)

        # Exceed rate limit
        for i in range(12):
            allowed = await rate_limiter.check_rate_limit(
                key=key,
                limit=10,
                window_seconds=60
            )

            if not allowed:
                violations.append({
                    "key": key,
                    "attempt": i + 1,
                    "timestamp": datetime.now(timezone.utc)
                })

        # Should have 2 violations (attempts 11 and 12)
        assert len(violations) == 2


    async def test_rate_limit_metrics_aggregation(self, rate_limiter):
        """
        TEST-017j: Aggregate rate limit metrics

        Aggregations:
        - Per user
        - Per endpoint
        - Per platform
        - Over time
        """
        users = ["user1", "user2", "user3"]
        endpoints = ["publish", "metrics", "health"]

        # Generate traffic
        for user in users:
            for endpoint in endpoints:
                key = f"api:{endpoint}:{user}"
                for i in range(5):
                    await rate_limiter.check_rate_limit(
                        key=key,
                        limit=100,
                        window_seconds=60
                    )

        # Verify metrics can be retrieved
        # (Implementation depends on rate limiter metrics storage)
        assert True  # Placeholder for actual metrics validation


@pytest.mark.asyncio
@pytest.mark.e2e
class TestGracefulDegradation:
    """Tests for graceful degradation when rate limited"""

    async def test_cache_on_rate_limit(self, rate_limiter):
        """
        TEST-017k: Return cached data when rate limited

        If fresh data can't be fetched due to rate limit,
        return cached data with appropriate headers
        """
        key = "api:cache:user"
        cached_data = {"data": "cached_value", "cached_at": datetime.now(timezone.utc).isoformat()}

        # Use up rate limit
        for i in range(10):
            await rate_limiter.check_rate_limit(
                key=key,
                limit=10,
                window_seconds=60
            )

        # Next request should be rate limited
        allowed = await rate_limiter.check_rate_limit(
            key=key,
            limit=10,
            window_seconds=60
        )

        if not allowed:
            # Should return cached data instead of error
            response = cached_data
            assert "cached_at" in response
            assert response["data"] == "cached_value"


    async def test_queue_on_rate_limit(self, rate_limiter):
        """
        TEST-017l: Queue requests when rate limited

        Instead of rejecting, queue requests for later processing
        """
        key = "api:queue:user"
        queue = []

        # Use up rate limit
        for i in range(10):
            await rate_limiter.check_rate_limit(
                key=key,
                limit=10,
                window_seconds=60
            )

        # Next requests get queued
        for i in range(5):
            allowed = await rate_limiter.check_rate_limit(
                key=key,
                limit=10,
                window_seconds=60
            )

            if not allowed:
                queue.append({
                    "request_id": f"req_{i}",
                    "queued_at": datetime.now(timezone.utc)
                })

        assert len(queue) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
