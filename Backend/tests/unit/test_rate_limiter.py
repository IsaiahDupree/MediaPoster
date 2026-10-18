"""
Tests for Rate Limiter Service (OPS-019)
"""

import pytest
import asyncio
from datetime import datetime, timezone

from services.rate_limiter import (
    RateLimiterService,
    Platform,
    RateLimitEndpoint,
    TokenBucket,
    BackoffState,
)


@pytest.fixture
def rate_limiter():
    """Get fresh rate limiter instance for each test"""
    # Reset singleton
    RateLimiterService._instance = None
    return RateLimiterService.get_instance()


def test_singleton_pattern():
    """Test that RateLimiterService follows singleton pattern"""
    RateLimiterService._instance = None
    service1 = RateLimiterService.get_instance()
    service2 = RateLimiterService.get_instance()
    assert service1 is service2


def test_token_bucket_refill():
    """Test token bucket refills at correct rate"""
    bucket = TokenBucket(capacity=100, refill_rate=10.0, tokens=0.0)

    # Wait for refill
    import time
    time.sleep(0.5)  # 0.5s * 10 tokens/s = 5 tokens

    bucket.refill()
    assert bucket.tokens >= 4.5  # Allow some timing variance
    assert bucket.tokens <= 5.5


def test_token_bucket_consume():
    """Test token bucket consumes tokens correctly"""
    bucket = TokenBucket(capacity=10, refill_rate=1.0, tokens=10.0)

    # Consume 3 tokens
    assert bucket.consume(3) is True
    assert bucket.get_remaining() == 7

    # Try to consume more than available
    assert bucket.consume(10) is False
    assert bucket.get_remaining() == 7


def test_token_bucket_capacity_limit():
    """Test token bucket doesn't exceed capacity"""
    bucket = TokenBucket(capacity=100, refill_rate=100.0, tokens=50.0)

    # Wait and refill
    import time
    time.sleep(2.0)  # Should refill to capacity

    bucket.refill()
    assert bucket.tokens == 100  # Capped at capacity


def test_backoff_exponential():
    """Test exponential backoff calculation"""
    backoff = BackoffState()

    # First failure: 1s
    delay1 = backoff.record_failure(base_delay=1.0)
    assert delay1 == 1.0
    assert backoff.failures == 1

    # Second failure: 2s
    delay2 = backoff.record_failure(base_delay=1.0)
    assert delay2 == 2.0
    assert backoff.failures == 2

    # Third failure: 4s
    delay3 = backoff.record_failure(base_delay=1.0)
    assert delay3 == 4.0
    assert backoff.failures == 3


def test_backoff_max_delay():
    """Test backoff respects maximum delay"""
    backoff = BackoffState()

    # Simulate many failures
    for _ in range(10):
        delay = backoff.record_failure(base_delay=1.0, max_delay=60.0)

    # Should be capped at max_delay
    assert delay == 60.0


def test_backoff_reset_on_success():
    """Test backoff resets after success"""
    backoff = BackoffState()

    # Record failures
    backoff.record_failure()
    backoff.record_failure()
    assert backoff.failures == 2

    # Record success
    backoff.record_success()
    assert backoff.failures == 0
    assert backoff.last_failure is None
    assert backoff.backoff_until is None


@pytest.mark.asyncio
async def test_rate_limiter_basic(rate_limiter):
    """Test basic rate limiting"""
    # Should allow first request
    allowed, wait = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is True
    assert wait == 0.0


@pytest.mark.asyncio
async def test_rate_limiter_exhaustion(rate_limiter):
    """Test rate limiter blocks when tokens exhausted"""
    # Get the bucket
    bucket = rate_limiter._get_or_create_bucket(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )

    # Exhaust all tokens
    bucket.tokens = 0.0

    # Should be rate limited
    allowed, wait = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is False
    assert wait > 0.0


@pytest.mark.asyncio
async def test_rate_limiter_different_endpoints(rate_limiter):
    """Test rate limiter treats endpoints separately"""
    # Exhaust publish endpoint
    bucket = rate_limiter._get_or_create_bucket(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    bucket.tokens = 0.0

    # Publish should be blocked
    allowed, _ = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is False

    # Metrics should still work
    allowed, _ = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.METRICS
    )
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_different_accounts(rate_limiter):
    """Test rate limiter treats accounts separately"""
    # Exhaust account1
    bucket = rate_limiter._get_or_create_bucket(
        Platform.TWITTER,
        "account1",
        RateLimitEndpoint.PUBLISH
    )
    bucket.tokens = 0.0

    # Account1 should be blocked
    allowed, _ = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "account1",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is False

    # Account2 should still work
    allowed, _ = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "account2",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_different_platforms(rate_limiter):
    """Test rate limiter treats platforms separately"""
    # Exhaust Twitter
    bucket = rate_limiter._get_or_create_bucket(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    bucket.tokens = 0.0

    # Twitter should be blocked
    allowed, _ = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is False

    # Instagram should still work
    allowed, _ = await rate_limiter.check_rate_limit(
        Platform.INSTAGRAM,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limit_error_triggers_backoff(rate_limiter):
    """Test recording rate limit error triggers backoff"""
    # Record error
    backoff_duration = await rate_limiter.record_rate_limit_error(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH,
        base_delay=1.0
    )
    assert backoff_duration == 1.0

    # Should be backed off
    allowed, wait = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is False
    assert wait > 0.0


@pytest.mark.asyncio
async def test_success_resets_backoff(rate_limiter):
    """Test success resets backoff state"""
    # Record error
    await rate_limiter.record_rate_limit_error(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH,
        base_delay=0.1
    )

    # Wait for backoff to expire
    await asyncio.sleep(0.2)

    # Record success (should allow request)
    allowed, _ = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is True

    # Record success to reset backoff
    await rate_limiter.record_success(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )

    # Backoff should be reset
    backoff = rate_limiter._get_or_create_backoff(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    assert backoff.failures == 0


@pytest.mark.asyncio
async def test_get_status(rate_limiter):
    """Test getting rate limit status"""
    # Create some buckets
    await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "account1",
        RateLimitEndpoint.PUBLISH
    )
    await rate_limiter.check_rate_limit(
        Platform.INSTAGRAM,
        "account2",
        RateLimitEndpoint.METRICS
    )

    # Get status
    status = await rate_limiter.get_status()
    assert status["total_buckets"] == 2
    assert len(status["buckets"]) == 2


@pytest.mark.asyncio
async def test_get_status_filtered(rate_limiter):
    """Test getting filtered rate limit status"""
    # Create buckets
    await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "account1",
        RateLimitEndpoint.PUBLISH
    )
    await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "account1",
        RateLimitEndpoint.METRICS
    )
    await rate_limiter.check_rate_limit(
        Platform.INSTAGRAM,
        "account2",
        RateLimitEndpoint.PUBLISH
    )

    # Filter by platform
    status = await rate_limiter.get_status(platform=Platform.TWITTER)
    assert status["total_buckets"] == 2

    # Filter by endpoint
    status = await rate_limiter.get_status(endpoint=RateLimitEndpoint.PUBLISH)
    assert status["total_buckets"] == 2


@pytest.mark.asyncio
async def test_reset_bucket(rate_limiter):
    """Test resetting bucket to full capacity"""
    # Exhaust bucket
    bucket = rate_limiter._get_or_create_bucket(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    bucket.tokens = 0.0

    # Should be rate limited
    allowed, _ = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is False

    # Reset bucket
    await rate_limiter.reset_bucket(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )

    # Should now be allowed
    allowed, _ = await rate_limiter.check_rate_limit(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )
    assert allowed is True


@pytest.mark.asyncio
async def test_platform_specific_limits(rate_limiter):
    """Test that platforms have different rate limits"""
    # Get Twitter publish bucket
    twitter_bucket = rate_limiter._get_or_create_bucket(
        Platform.TWITTER,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )

    # Get Instagram publish bucket
    instagram_bucket = rate_limiter._get_or_create_bucket(
        Platform.INSTAGRAM,
        "test_account",
        RateLimitEndpoint.PUBLISH
    )

    # Twitter: 300/hour, Instagram: 200/hour
    assert twitter_bucket.capacity == 300
    assert instagram_bucket.capacity == 200
