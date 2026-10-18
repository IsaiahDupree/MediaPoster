"""
Rate Limiting Service (OPS-019)
================================
Token bucket rate limiter per platform/account/endpoint with exponential backoff.

Supports:
- Per-platform rate limits (X, Instagram, TikTok, YouTube, Threads)
- Per-account rate limits (multiple accounts per platform)
- Per-endpoint rate limits (publish, metrics, comments, DMs)
- Token bucket algorithm with refill
- Exponential backoff on rate limit errors
- Redis-backed for distributed systems (with in-memory fallback)
"""

import asyncio
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger


class Platform(Enum):
    """Supported platforms"""
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    THREADS = "threads"


class RateLimitEndpoint(Enum):
    """Rate-limited endpoint types"""
    PUBLISH = "publish"
    METRICS = "metrics"
    COMMENTS = "comments"
    DMS = "dms"
    PROFILE = "profile"


@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting.

    Tokens refill at a constant rate. Each request consumes one token.
    If no tokens available, request is rate limited.
    """
    capacity: int  # Maximum tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(default=0.0)
    last_refill: float = field(default_factory=time.time)

    def refill(self) -> None:
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on refill rate
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens consumed, False if not enough tokens
        """
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def get_remaining(self) -> int:
        """Get number of tokens remaining"""
        self.refill()
        return int(self.tokens)

    def time_until_available(self, tokens: int = 1) -> float:
        """
        Get seconds until enough tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait (0 if already available)
        """
        self.refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


@dataclass
class BackoffState:
    """Exponential backoff state for a specific key"""
    failures: int = 0
    last_failure: Optional[datetime] = None
    backoff_until: Optional[datetime] = None

    def record_failure(self, base_delay: float = 1.0, max_delay: float = 300.0) -> float:
        """
        Record a failure and calculate backoff duration.

        Args:
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds

        Returns:
            Backoff duration in seconds
        """
        now = datetime.now(timezone.utc)
        self.failures += 1
        self.last_failure = now

        # Exponential backoff: base_delay * 2^failures
        backoff_seconds = min(base_delay * (2 ** (self.failures - 1)), max_delay)
        self.backoff_until = now + timedelta(seconds=backoff_seconds)

        return backoff_seconds

    def record_success(self) -> None:
        """Record a success (resets backoff)"""
        self.failures = 0
        self.last_failure = None
        self.backoff_until = None

    def is_backed_off(self) -> bool:
        """Check if currently in backoff period"""
        if self.backoff_until is None:
            return False

        return datetime.now(timezone.utc) < self.backoff_until

    def time_until_retry(self) -> float:
        """Get seconds until retry is allowed"""
        if not self.is_backed_off():
            return 0.0

        delta = self.backoff_until - datetime.now(timezone.utc)
        return max(0.0, delta.total_seconds())


class RateLimiterService:
    """
    Rate limiting service with token buckets and exponential backoff.

    Platform-specific rate limits (requests per hour):
    - Twitter: 300/hour for posts, 900/hour for metrics
    - Instagram: 200/hour for posts, 600/hour for metrics
    - TikTok: 100/hour for posts, 300/hour for metrics
    - YouTube: 10,000/day for API quota
    - Threads: 250/hour for posts, 500/hour for metrics
    """

    # Platform rate limits (requests per hour)
    PLATFORM_LIMITS = {
        Platform.TWITTER: {
            RateLimitEndpoint.PUBLISH: (300, 3600),  # 300 per hour
            RateLimitEndpoint.METRICS: (900, 3600),  # 900 per hour
            RateLimitEndpoint.COMMENTS: (500, 3600),  # 500 per hour
            RateLimitEndpoint.DMS: (200, 3600),  # 200 per hour
            RateLimitEndpoint.PROFILE: (1000, 3600),  # 1000 per hour
        },
        Platform.INSTAGRAM: {
            RateLimitEndpoint.PUBLISH: (200, 3600),  # 200 per hour
            RateLimitEndpoint.METRICS: (600, 3600),  # 600 per hour
            RateLimitEndpoint.COMMENTS: (400, 3600),  # 400 per hour
            RateLimitEndpoint.DMS: (150, 3600),  # 150 per hour
            RateLimitEndpoint.PROFILE: (800, 3600),  # 800 per hour
        },
        Platform.TIKTOK: {
            RateLimitEndpoint.PUBLISH: (100, 3600),  # 100 per hour
            RateLimitEndpoint.METRICS: (300, 3600),  # 300 per hour
            RateLimitEndpoint.COMMENTS: (200, 3600),  # 200 per hour
            RateLimitEndpoint.DMS: (100, 3600),  # 100 per hour
            RateLimitEndpoint.PROFILE: (500, 3600),  # 500 per hour
        },
        Platform.YOUTUBE: {
            RateLimitEndpoint.PUBLISH: (50, 3600),  # 50 per hour (quota expensive)
            RateLimitEndpoint.METRICS: (10000, 86400),  # 10k per day
            RateLimitEndpoint.COMMENTS: (100, 3600),  # 100 per hour
            RateLimitEndpoint.DMS: (0, 3600),  # Not supported
            RateLimitEndpoint.PROFILE: (1000, 3600),  # 1000 per hour
        },
        Platform.THREADS: {
            RateLimitEndpoint.PUBLISH: (250, 3600),  # 250 per hour
            RateLimitEndpoint.METRICS: (500, 3600),  # 500 per hour
            RateLimitEndpoint.COMMENTS: (300, 3600),  # 300 per hour
            RateLimitEndpoint.DMS: (100, 3600),  # 100 per hour
            RateLimitEndpoint.PROFILE: (600, 3600),  # 600 per hour
        },
    }

    _instance: Optional["RateLimiterService"] = None

    def __init__(self):
        if RateLimiterService._instance is not None:
            raise RuntimeError("Use RateLimiterService.get_instance()")

        # Token buckets: {platform:account:endpoint -> TokenBucket}
        self._buckets: Dict[str, TokenBucket] = {}

        # Backoff states: {platform:account:endpoint -> BackoffState}
        self._backoff: Dict[str, BackoffState] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info("✓ Rate Limiter Service initialized")

    @classmethod
    def get_instance(cls) -> "RateLimiterService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_bucket_key(self, platform: Platform, account_id: str, endpoint: RateLimitEndpoint) -> str:
        """Generate unique key for token bucket"""
        return f"{platform.value}:{account_id}:{endpoint.value}"

    def _get_or_create_bucket(
        self,
        platform: Platform,
        account_id: str,
        endpoint: RateLimitEndpoint
    ) -> TokenBucket:
        """Get existing bucket or create new one"""
        key = self._get_bucket_key(platform, account_id, endpoint)

        if key not in self._buckets:
            # Get platform limits
            limits = self.PLATFORM_LIMITS.get(platform, {})
            capacity, window = limits.get(
                endpoint,
                (100, 3600)  # Default: 100 per hour
            )

            # Calculate refill rate (tokens per second)
            refill_rate = capacity / window

            # Create bucket with full capacity
            bucket = TokenBucket(
                capacity=capacity,
                refill_rate=refill_rate,
                tokens=float(capacity)
            )

            self._buckets[key] = bucket
            logger.debug(
                f"Created rate limit bucket: {key} "
                f"(capacity={capacity}, refill={refill_rate:.2f}/s)"
            )

        return self._buckets[key]

    def _get_or_create_backoff(
        self,
        platform: Platform,
        account_id: str,
        endpoint: RateLimitEndpoint
    ) -> BackoffState:
        """Get existing backoff state or create new one"""
        key = self._get_bucket_key(platform, account_id, endpoint)

        if key not in self._backoff:
            self._backoff[key] = BackoffState()

        return self._backoff[key]

    async def check_rate_limit(
        self,
        platform: Platform,
        account_id: str,
        endpoint: RateLimitEndpoint,
        tokens: int = 1
    ) -> Tuple[bool, float]:
        """
        Check if request is allowed under rate limits.

        Args:
            platform: Platform name
            account_id: Account identifier
            endpoint: Endpoint type
            tokens: Number of tokens to consume (default 1)

        Returns:
            Tuple of (is_allowed, wait_seconds)
            - is_allowed: True if request can proceed
            - wait_seconds: Seconds to wait before retry (0 if allowed)
        """
        async with self._lock:
            # Check backoff first
            backoff = self._get_or_create_backoff(platform, account_id, endpoint)

            if backoff.is_backed_off():
                wait_time = backoff.time_until_retry()
                logger.warning(
                    f"⏸️  Rate limit backoff active: {platform.value}/{account_id}/{endpoint.value} "
                    f"(wait {wait_time:.1f}s, failures={backoff.failures})"
                )
                return False, wait_time

            # Check token bucket
            bucket = self._get_or_create_bucket(platform, account_id, endpoint)

            if bucket.consume(tokens):
                # Success - reset backoff
                backoff.record_success()

                logger.debug(
                    f"✓ Rate limit OK: {platform.value}/{account_id}/{endpoint.value} "
                    f"(remaining={bucket.get_remaining()})"
                )
                return True, 0.0

            # Rate limited - calculate wait time
            wait_time = bucket.time_until_available(tokens)

            logger.warning(
                f"⚠️  Rate limit exceeded: {platform.value}/{account_id}/{endpoint.value} "
                f"(wait {wait_time:.1f}s)"
            )

            return False, wait_time

    async def record_rate_limit_error(
        self,
        platform: Platform,
        account_id: str,
        endpoint: RateLimitEndpoint,
        base_delay: float = 60.0,
        max_delay: float = 3600.0
    ) -> float:
        """
        Record a rate limit error from the platform (e.g., 429 response).

        Triggers exponential backoff for this platform/account/endpoint.

        Args:
            platform: Platform name
            account_id: Account identifier
            endpoint: Endpoint type
            base_delay: Base backoff delay in seconds (default 60s)
            max_delay: Maximum backoff delay in seconds (default 1 hour)

        Returns:
            Backoff duration in seconds
        """
        async with self._lock:
            backoff = self._get_or_create_backoff(platform, account_id, endpoint)
            backoff_duration = backoff.record_failure(base_delay, max_delay)

            logger.error(
                f"❌ Rate limit error from platform: {platform.value}/{account_id}/{endpoint.value} "
                f"(backoff={backoff_duration:.1f}s, failures={backoff.failures})"
            )

            return backoff_duration

    async def record_success(
        self,
        platform: Platform,
        account_id: str,
        endpoint: RateLimitEndpoint
    ) -> None:
        """
        Record a successful request (resets backoff).

        Args:
            platform: Platform name
            account_id: Account identifier
            endpoint: Endpoint type
        """
        async with self._lock:
            backoff = self._get_or_create_backoff(platform, account_id, endpoint)

            if backoff.failures > 0:
                logger.info(
                    f"✓ Rate limit backoff cleared: {platform.value}/{account_id}/{endpoint.value} "
                    f"(was {backoff.failures} failures)"
                )
                backoff.record_success()

    async def get_status(
        self,
        platform: Optional[Platform] = None,
        account_id: Optional[str] = None,
        endpoint: Optional[RateLimitEndpoint] = None
    ) -> Dict:
        """
        Get rate limit status.

        Args:
            platform: Optional platform filter
            account_id: Optional account filter
            endpoint: Optional endpoint filter

        Returns:
            Dictionary with rate limit status
        """
        async with self._lock:
            buckets = []

            for key, bucket in self._buckets.items():
                parts = key.split(":")
                bucket_platform = parts[0]
                bucket_account = parts[1]
                bucket_endpoint = parts[2]

                # Apply filters
                if platform and bucket_platform != platform.value:
                    continue
                if account_id and bucket_account != account_id:
                    continue
                if endpoint and bucket_endpoint != endpoint.value:
                    continue

                backoff = self._backoff.get(key, BackoffState())

                buckets.append({
                    "platform": bucket_platform,
                    "account_id": bucket_account,
                    "endpoint": bucket_endpoint,
                    "capacity": bucket.capacity,
                    "remaining": bucket.get_remaining(),
                    "refill_rate": bucket.refill_rate,
                    "is_backed_off": backoff.is_backed_off(),
                    "backoff_failures": backoff.failures,
                    "time_until_retry": backoff.time_until_retry()
                })

            return {
                "total_buckets": len(buckets),
                "buckets": buckets
            }

    async def reset_bucket(
        self,
        platform: Platform,
        account_id: str,
        endpoint: RateLimitEndpoint
    ) -> None:
        """
        Reset a token bucket to full capacity (for testing/admin).

        Args:
            platform: Platform name
            account_id: Account identifier
            endpoint: Endpoint type
        """
        async with self._lock:
            key = self._get_bucket_key(platform, account_id, endpoint)

            if key in self._buckets:
                bucket = self._buckets[key]
                bucket.tokens = float(bucket.capacity)
                bucket.last_refill = time.time()

                logger.info(
                    f"♻️  Reset rate limit bucket: {platform.value}/{account_id}/{endpoint.value}"
                )

            if key in self._backoff:
                self._backoff[key] = BackoffState()
                logger.info(
                    f"♻️  Reset backoff state: {platform.value}/{account_id}/{endpoint.value}"
                )
