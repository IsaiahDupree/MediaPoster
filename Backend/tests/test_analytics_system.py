"""
Phase 5: Comprehensive Analytics & Optimization Tests
Tests for real-time metrics, posted content tracking, performance analytics.
Target: ~100 tests
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4, UUID
from typing import Dict, Any, List, Optional
from enum import Enum
from collections import defaultdict
import json


# ==================== MODELS ====================

class Platform(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"


class MetricType(str, Enum):
    VIEWS = "views"
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    SAVES = "saves"
    FOLLOWERS = "followers"
    ENGAGEMENT_RATE = "engagement_rate"
    REACH = "reach"
    IMPRESSIONS = "impressions"
    CLICK_THROUGH_RATE = "ctr"
    WATCH_TIME = "watch_time"


class PostMetrics:
    """Metrics for a single post"""
    def __init__(
        self,
        post_id: str = None,
        platform: Platform = Platform.TIKTOK,
        views: int = 0,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        saves: int = 0,
        engagement_rate: float = 0.0,
        reach: int = 0,
        impressions: int = 0,
        watch_time_seconds: int = 0,
        fetched_at: datetime = None,
        is_stale: bool = False,
    ):
        self.post_id = post_id or str(uuid4())
        self.platform = platform
        self.views = views
        self.likes = likes
        self.comments = comments
        self.shares = shares
        self.saves = saves
        self.engagement_rate = engagement_rate
        self.reach = reach
        self.impressions = impressions
        self.watch_time_seconds = watch_time_seconds
        self.fetched_at = fetched_at or datetime.now(timezone.utc)
        self.is_stale = is_stale
    
    def calculate_engagement_rate(self) -> float:
        """Calculate engagement rate"""
        if self.views == 0:
            return 0.0
        total_engagement = self.likes + self.comments + self.shares + self.saves
        return (total_engagement / self.views) * 100
    
    def to_dict(self) -> Dict:
        return {
            "post_id": self.post_id,
            "platform": self.platform,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "saves": self.saves,
            "engagement_rate": self.engagement_rate,
        }


class ProfileMetrics:
    """Metrics for a profile/account"""
    def __init__(
        self,
        username: str = "test_user",
        platform: Platform = Platform.TIKTOK,
        follower_count: int = 0,
        following_count: int = 0,
        post_count: int = 0,
        avg_views: float = 0.0,
        avg_likes: float = 0.0,
        avg_comments: float = 0.0,
        engagement_rate: float = 0.0,
        fetched_at: datetime = None,
        is_stale: bool = False,
    ):
        self.username = username
        self.platform = platform
        self.follower_count = follower_count
        self.following_count = following_count
        self.post_count = post_count
        self.avg_views = avg_views
        self.avg_likes = avg_likes
        self.avg_comments = avg_comments
        self.engagement_rate = engagement_rate
        self.fetched_at = fetched_at or datetime.now(timezone.utc)
        self.is_stale = is_stale


class PostedContent:
    """Tracked posted content"""
    def __init__(
        self,
        id: UUID = None,
        platform: Platform = Platform.TIKTOK,
        platform_post_id: str = None,
        platform_url: str = None,
        local_content_id: UUID = None,
        account_username: str = "@test_user",
        title: str = "Test Post",
        description: str = "Test description",
        posted_at: datetime = None,
        metrics: PostMetrics = None,
    ):
        self.id = id or uuid4()
        self.platform = platform
        self.platform_post_id = platform_post_id or str(uuid4())
        self.platform_url = platform_url or f"https://{platform.value if hasattr(platform, 'value') else platform}.com/post/{self.platform_post_id}"
        self.local_content_id = local_content_id
        self.account_username = account_username
        self.title = title
        self.description = description
        self.posted_at = posted_at or datetime.now(timezone.utc)
        self.metrics = metrics or PostMetrics()
    
    @property
    def is_linked_to_local(self) -> bool:
        return self.local_content_id is not None


class AnalyticsPeriod(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    ALL_TIME = "all_time"


# ==================== ANALYTICS SERVICES ====================

class MetricsCache:
    """Cache for metrics to avoid excessive API calls"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict] = {}
    
    def get(self, key: str) -> Optional[Dict]:
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if datetime.now(timezone.utc) > entry["expires_at"]:
            del self._cache[key]
            return None
        
        return entry["data"]
    
    def set(self, key: str, data: Dict):
        self._cache[key] = {
            "data": data,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds),
        }
    
    def invalidate(self, key: str):
        if key in self._cache:
            del self._cache[key]
    
    def clear(self):
        self._cache = {}
    
    def size(self) -> int:
        return len(self._cache)


class MetricsFetcher:
    """Fetches metrics from platforms"""
    
    def __init__(self, cache: MetricsCache = None):
        self.cache = cache or MetricsCache()
        self.api_calls = 0
    
    async def fetch_post_metrics(
        self, 
        platform: Platform, 
        post_id: str,
        use_cache: bool = True,
    ) -> PostMetrics:
        """Fetch metrics for a single post"""
        cache_key = f"{platform}:{post_id}"
        
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return PostMetrics(**cached)
        
        # Simulate API call
        self.api_calls += 1
        
        # Mock data
        metrics = PostMetrics(
            post_id=post_id,
            platform=platform,
            views=1000 + self.api_calls * 100,
            likes=50 + self.api_calls * 5,
            comments=10 + self.api_calls,
            shares=5,
            saves=20,
        )
        metrics.engagement_rate = metrics.calculate_engagement_rate()
        
        self.cache.set(cache_key, metrics.to_dict())
        return metrics
    
    async def fetch_profile_metrics(
        self,
        platform: Platform,
        username: str,
    ) -> ProfileMetrics:
        """Fetch metrics for a profile"""
        self.api_calls += 1
        
        return ProfileMetrics(
            username=username,
            platform=platform,
            follower_count=10000,
            following_count=500,
            post_count=100,
            avg_views=5000,
            avg_likes=250,
            engagement_rate=5.0,
        )
    
    async def fetch_batch_metrics(
        self,
        platform: Platform,
        post_ids: List[str],
    ) -> List[PostMetrics]:
        """Fetch metrics for multiple posts"""
        metrics = []
        for post_id in post_ids:
            m = await self.fetch_post_metrics(platform, post_id)
            metrics.append(m)
        return metrics


class AnalyticsAggregator:
    """Aggregates analytics across posts and platforms"""
    
    def __init__(self):
        self.posted_content: List[PostedContent] = []
    
    def add_content(self, content: PostedContent):
        self.posted_content.append(content)
    
    def get_total_views(self, platform: Platform = None) -> int:
        """Get total views across all content"""
        content = self.posted_content
        if platform:
            content = [c for c in content if c.platform == platform]
        return sum(c.metrics.views for c in content)
    
    def get_total_engagement(self, platform: Platform = None) -> Dict:
        """Get total engagement metrics"""
        content = self.posted_content
        if platform:
            content = [c for c in content if c.platform == platform]
        
        return {
            "likes": sum(c.metrics.likes for c in content),
            "comments": sum(c.metrics.comments for c in content),
            "shares": sum(c.metrics.shares for c in content),
            "saves": sum(c.metrics.saves for c in content),
        }
    
    def get_average_engagement_rate(self, platform: Platform = None) -> float:
        """Get average engagement rate"""
        content = self.posted_content
        if platform:
            content = [c for c in content if c.platform == platform]
        
        if not content:
            return 0.0
        
        rates = [c.metrics.engagement_rate for c in content]
        return sum(rates) / len(rates)
    
    def get_top_performing(
        self, 
        metric: MetricType = MetricType.VIEWS, 
        limit: int = 10
    ) -> List[PostedContent]:
        """Get top performing content by metric"""
        metric_map = {
            MetricType.VIEWS: lambda c: c.metrics.views,
            MetricType.LIKES: lambda c: c.metrics.likes,
            MetricType.COMMENTS: lambda c: c.metrics.comments,
            MetricType.ENGAGEMENT_RATE: lambda c: c.metrics.engagement_rate,
        }
        
        key_func = metric_map.get(metric, lambda c: c.metrics.views)
        sorted_content = sorted(self.posted_content, key=key_func, reverse=True)
        return sorted_content[:limit]
    
    def get_performance_by_platform(self) -> Dict[Platform, Dict]:
        """Get aggregated performance by platform"""
        by_platform = defaultdict(list)
        for content in self.posted_content:
            by_platform[content.platform].append(content)
        
        result = {}
        for platform, contents in by_platform.items():
            result[platform] = {
                "post_count": len(contents),
                "total_views": sum(c.metrics.views for c in contents),
                "total_likes": sum(c.metrics.likes for c in contents),
                "avg_engagement": sum(c.metrics.engagement_rate for c in contents) / len(contents) if contents else 0,
            }
        
        return result
    
    def get_daily_metrics(self, days: int = 7) -> Dict[str, Dict]:
        """Get daily aggregated metrics"""
        daily = defaultdict(lambda: {"views": 0, "likes": 0, "posts": 0})
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        for content in self.posted_content:
            if content.posted_at >= cutoff:
                date_str = content.posted_at.strftime("%Y-%m-%d")
                daily[date_str]["views"] += content.metrics.views
                daily[date_str]["likes"] += content.metrics.likes
                daily[date_str]["posts"] += 1
        
        return dict(daily)
    
    def get_linked_vs_unlinked(self) -> Dict:
        """Get stats for linked vs unlinked content"""
        linked = [c for c in self.posted_content if c.is_linked_to_local]
        unlinked = [c for c in self.posted_content if not c.is_linked_to_local]
        
        return {
            "linked_count": len(linked),
            "unlinked_count": len(unlinked),
            "linked_views": sum(c.metrics.views for c in linked),
            "unlinked_views": sum(c.metrics.views for c in unlinked),
        }


class PerformanceTracker:
    """Tracks content performance over time"""
    
    def __init__(self):
        self.snapshots: List[Dict] = []
    
    def record_snapshot(self, content: PostedContent):
        """Record a metrics snapshot"""
        self.snapshots.append({
            "content_id": str(content.id),
            "timestamp": datetime.now(timezone.utc),
            "views": content.metrics.views,
            "likes": content.metrics.likes,
            "comments": content.metrics.comments,
            "engagement_rate": content.metrics.engagement_rate,
        })
    
    def get_growth_rate(self, content_id: str, metric: str = "views") -> float:
        """Calculate growth rate for a metric"""
        content_snapshots = [
            s for s in self.snapshots 
            if s["content_id"] == content_id
        ]
        
        if len(content_snapshots) < 2:
            return 0.0
        
        oldest = content_snapshots[0][metric]
        newest = content_snapshots[-1][metric]
        
        if oldest == 0:
            return 100.0 if newest > 0 else 0.0
        
        return ((newest - oldest) / oldest) * 100
    
    def get_snapshot_history(
        self, 
        content_id: str, 
        limit: int = None
    ) -> List[Dict]:
        """Get snapshot history for content"""
        history = [
            s for s in self.snapshots 
            if s["content_id"] == content_id
        ]
        
        if limit:
            history = history[-limit:]
        
        return history


class ContentReporter:
    """Generates analytics reports"""
    
    def __init__(self, aggregator: AnalyticsAggregator):
        self.aggregator = aggregator
    
    def generate_summary_report(self) -> Dict:
        """Generate summary report"""
        return {
            "total_posts": len(self.aggregator.posted_content),
            "total_views": self.aggregator.get_total_views(),
            "total_engagement": self.aggregator.get_total_engagement(),
            "avg_engagement_rate": self.aggregator.get_average_engagement_rate(),
            "by_platform": self.aggregator.get_performance_by_platform(),
        }
    
    def generate_platform_report(self, platform: Platform) -> Dict:
        """Generate platform-specific report"""
        content = [
            c for c in self.aggregator.posted_content 
            if c.platform == platform
        ]
        
        return {
            "platform": platform,
            "post_count": len(content),
            "total_views": sum(c.metrics.views for c in content),
            "total_likes": sum(c.metrics.likes for c in content),
            "total_comments": sum(c.metrics.comments for c in content),
            "avg_engagement": self.aggregator.get_average_engagement_rate(platform),
        }
    
    def generate_top_content_report(self, limit: int = 10) -> Dict:
        """Generate top content report"""
        top_by_views = self.aggregator.get_top_performing(MetricType.VIEWS, limit)
        top_by_engagement = self.aggregator.get_top_performing(MetricType.ENGAGEMENT_RATE, limit)
        
        return {
            "top_by_views": [c.to_dict() if hasattr(c, 'to_dict') else {"id": str(c.id)} for c in top_by_views],
            "top_by_engagement": [{"id": str(c.id)} for c in top_by_engagement],
        }


# ==================== TESTS ====================

class TestPostMetrics:
    """Test PostMetrics model"""
    
    def test_create_metrics(self):
        """Should create post metrics"""
        metrics = PostMetrics()
        assert metrics.post_id is not None
        assert metrics.views == 0
    
    def test_create_with_values(self):
        """Should accept custom values"""
        metrics = PostMetrics(
            views=1000,
            likes=100,
            comments=50,
        )
        assert metrics.views == 1000
        assert metrics.likes == 100
    
    def test_calculate_engagement_rate(self):
        """Should calculate engagement rate"""
        metrics = PostMetrics(
            views=1000,
            likes=50,
            comments=20,
            shares=10,
            saves=20,
        )
        rate = metrics.calculate_engagement_rate()
        assert rate == 10.0  # (50+20+10+20)/1000 * 100
    
    def test_engagement_rate_zero_views(self):
        """Should return 0 for zero views"""
        metrics = PostMetrics(views=0, likes=100)
        rate = metrics.calculate_engagement_rate()
        assert rate == 0.0
    
    def test_to_dict(self):
        """Should convert to dict"""
        metrics = PostMetrics(views=500)
        d = metrics.to_dict()
        assert d["views"] == 500
        assert "post_id" in d
    
    def test_fetched_at_default(self):
        """Should set fetched_at"""
        metrics = PostMetrics()
        assert metrics.fetched_at is not None
    
    def test_is_stale_default(self):
        """Should default to not stale"""
        metrics = PostMetrics()
        assert metrics.is_stale is False


class TestProfileMetrics:
    """Test ProfileMetrics model"""
    
    def test_create_profile_metrics(self):
        """Should create profile metrics"""
        metrics = ProfileMetrics()
        assert metrics.username == "test_user"
    
    def test_follower_count(self):
        """Should track follower count"""
        metrics = ProfileMetrics(follower_count=10000)
        assert metrics.follower_count == 10000
    
    def test_platform_field(self):
        """Should store platform"""
        metrics = ProfileMetrics(platform=Platform.YOUTUBE)
        assert metrics.platform == Platform.YOUTUBE
    
    def test_average_metrics(self):
        """Should store average metrics"""
        metrics = ProfileMetrics(
            avg_views=5000,
            avg_likes=250,
        )
        assert metrics.avg_views == 5000
        assert metrics.avg_likes == 250


class TestPostedContent:
    """Test PostedContent model"""
    
    def test_create_posted_content(self):
        """Should create posted content"""
        content = PostedContent()
        assert content.id is not None
        assert content.platform == Platform.TIKTOK
    
    def test_platform_url_generated(self):
        """Should generate platform URL"""
        content = PostedContent(platform=Platform.YOUTUBE)
        assert "youtube.com" in content.platform_url
    
    def test_is_linked_to_local(self):
        """Should detect linked content"""
        linked = PostedContent(local_content_id=uuid4())
        unlinked = PostedContent(local_content_id=None)
        
        assert linked.is_linked_to_local is True
        assert unlinked.is_linked_to_local is False
    
    def test_posted_at_default(self):
        """Should set posted_at"""
        content = PostedContent()
        assert content.posted_at is not None
    
    def test_metrics_default(self):
        """Should create default metrics"""
        content = PostedContent()
        assert content.metrics is not None


class TestMetricsCache:
    """Test metrics cache"""
    
    def test_create_cache(self):
        """Should create cache"""
        cache = MetricsCache()
        assert cache.ttl_seconds == 300
    
    def test_set_and_get(self):
        """Should set and get values"""
        cache = MetricsCache()
        cache.set("key1", {"views": 100})
        
        result = cache.get("key1")
        
        assert result["views"] == 100
    
    def test_get_missing_key(self):
        """Should return None for missing key"""
        cache = MetricsCache()
        result = cache.get("nonexistent")
        assert result is None
    
    def test_invalidate(self):
        """Should invalidate cache entry"""
        cache = MetricsCache()
        cache.set("key1", {"data": 1})
        cache.invalidate("key1")
        
        assert cache.get("key1") is None
    
    def test_clear(self):
        """Should clear all cache"""
        cache = MetricsCache()
        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})
        cache.clear()
        
        assert cache.size() == 0
    
    def test_size(self):
        """Should return cache size"""
        cache = MetricsCache()
        cache.set("key1", {})
        cache.set("key2", {})
        
        assert cache.size() == 2
    
    def test_expired_entry(self):
        """Should return None for expired entry"""
        cache = MetricsCache(ttl_seconds=0)
        cache.set("key1", {"data": 1})
        
        # Entry should be expired immediately
        import time
        time.sleep(0.01)
        
        result = cache.get("key1")
        assert result is None


class TestMetricsFetcher:
    """Test metrics fetcher"""
    
    @pytest.fixture
    def fetcher(self):
        return MetricsFetcher()
    
    @pytest.mark.asyncio
    async def test_fetch_post_metrics(self, fetcher):
        """Should fetch post metrics"""
        metrics = await fetcher.fetch_post_metrics(Platform.TIKTOK, "post_123")
        
        assert metrics.post_id == "post_123"
        assert metrics.views > 0
    
    @pytest.mark.asyncio
    async def test_cache_used(self, fetcher):
        """Should use cache on second call"""
        await fetcher.fetch_post_metrics(Platform.TIKTOK, "post_123")
        initial_calls = fetcher.api_calls
        
        await fetcher.fetch_post_metrics(Platform.TIKTOK, "post_123")
        
        assert fetcher.api_calls == initial_calls  # No additional API call
    
    @pytest.mark.asyncio
    async def test_bypass_cache(self, fetcher):
        """Should bypass cache when requested"""
        await fetcher.fetch_post_metrics(Platform.TIKTOK, "post_123")
        initial_calls = fetcher.api_calls
        
        await fetcher.fetch_post_metrics(Platform.TIKTOK, "post_123", use_cache=False)
        
        assert fetcher.api_calls > initial_calls
    
    @pytest.mark.asyncio
    async def test_fetch_profile_metrics(self, fetcher):
        """Should fetch profile metrics"""
        metrics = await fetcher.fetch_profile_metrics(Platform.INSTAGRAM, "@test")
        
        assert metrics.username == "@test"
        assert metrics.follower_count > 0
    
    @pytest.mark.asyncio
    async def test_fetch_batch_metrics(self, fetcher):
        """Should fetch batch metrics"""
        post_ids = ["post_1", "post_2", "post_3"]
        metrics = await fetcher.fetch_batch_metrics(Platform.TIKTOK, post_ids)
        
        assert len(metrics) == 3


class TestAnalyticsAggregator:
    """Test analytics aggregator"""
    
    @pytest.fixture
    def aggregator(self):
        agg = AnalyticsAggregator()
        # Add sample content
        agg.add_content(PostedContent(
            platform=Platform.TIKTOK,
            metrics=PostMetrics(views=1000, likes=100, engagement_rate=10.0)
        ))
        agg.add_content(PostedContent(
            platform=Platform.TIKTOK,
            metrics=PostMetrics(views=2000, likes=200, engagement_rate=10.0)
        ))
        agg.add_content(PostedContent(
            platform=Platform.YOUTUBE,
            metrics=PostMetrics(views=5000, likes=500, engagement_rate=10.0)
        ))
        return agg
    
    def test_get_total_views(self, aggregator):
        """Should get total views"""
        total = aggregator.get_total_views()
        assert total == 8000
    
    def test_get_total_views_by_platform(self, aggregator):
        """Should get views by platform"""
        tiktok_views = aggregator.get_total_views(Platform.TIKTOK)
        assert tiktok_views == 3000
    
    def test_get_total_engagement(self, aggregator):
        """Should get total engagement"""
        engagement = aggregator.get_total_engagement()
        assert engagement["likes"] == 800
    
    def test_get_average_engagement_rate(self, aggregator):
        """Should calculate average engagement rate"""
        avg = aggregator.get_average_engagement_rate()
        assert avg == 10.0
    
    def test_get_top_performing(self, aggregator):
        """Should get top performing content"""
        top = aggregator.get_top_performing(MetricType.VIEWS, 2)
        
        assert len(top) == 2
        assert top[0].metrics.views >= top[1].metrics.views
    
    def test_get_performance_by_platform(self, aggregator):
        """Should aggregate by platform"""
        by_platform = aggregator.get_performance_by_platform()
        
        assert Platform.TIKTOK in by_platform
        assert by_platform[Platform.TIKTOK]["post_count"] == 2
    
    def test_get_linked_vs_unlinked(self, aggregator):
        """Should separate linked and unlinked"""
        # Add linked content
        aggregator.add_content(PostedContent(
            local_content_id=uuid4(),
            metrics=PostMetrics(views=1000)
        ))
        
        stats = aggregator.get_linked_vs_unlinked()
        
        assert stats["linked_count"] == 1
        assert stats["unlinked_count"] == 3


class TestPerformanceTracker:
    """Test performance tracker"""
    
    @pytest.fixture
    def tracker(self):
        return PerformanceTracker()
    
    def test_record_snapshot(self, tracker):
        """Should record snapshot"""
        content = PostedContent(metrics=PostMetrics(views=100))
        tracker.record_snapshot(content)
        
        assert len(tracker.snapshots) == 1
    
    def test_multiple_snapshots(self, tracker):
        """Should record multiple snapshots"""
        content = PostedContent()
        
        content.metrics.views = 100
        tracker.record_snapshot(content)
        
        content.metrics.views = 200
        tracker.record_snapshot(content)
        
        assert len(tracker.snapshots) == 2
    
    def test_get_growth_rate(self, tracker):
        """Should calculate growth rate"""
        content_id = str(uuid4())
        
        tracker.snapshots.append({
            "content_id": content_id,
            "timestamp": datetime.now(timezone.utc),
            "views": 100,
            "likes": 10,
            "comments": 5,
            "engagement_rate": 5.0,
        })
        tracker.snapshots.append({
            "content_id": content_id,
            "timestamp": datetime.now(timezone.utc),
            "views": 200,
            "likes": 20,
            "comments": 10,
            "engagement_rate": 5.0,
        })
        
        growth = tracker.get_growth_rate(content_id, "views")
        assert growth == 100.0  # 100% growth
    
    def test_growth_rate_insufficient_data(self, tracker):
        """Should return 0 for insufficient data"""
        growth = tracker.get_growth_rate("unknown_id", "views")
        assert growth == 0.0
    
    def test_get_snapshot_history(self, tracker):
        """Should return snapshot history"""
        content_id = str(uuid4())
        
        for i in range(5):
            tracker.snapshots.append({
                "content_id": content_id,
                "timestamp": datetime.now(timezone.utc),
                "views": i * 100,
                "likes": i * 10,
                "comments": i,
                "engagement_rate": 5.0,
            })
        
        history = tracker.get_snapshot_history(content_id, limit=3)
        assert len(history) == 3


class TestContentReporter:
    """Test content reporter"""
    
    @pytest.fixture
    def reporter(self):
        agg = AnalyticsAggregator()
        agg.add_content(PostedContent(
            platform=Platform.TIKTOK,
            metrics=PostMetrics(views=1000, likes=100)
        ))
        agg.add_content(PostedContent(
            platform=Platform.YOUTUBE,
            metrics=PostMetrics(views=5000, likes=500)
        ))
        return ContentReporter(agg)
    
    def test_generate_summary_report(self, reporter):
        """Should generate summary report"""
        report = reporter.generate_summary_report()
        
        assert "total_posts" in report
        assert report["total_posts"] == 2
        assert report["total_views"] == 6000
    
    def test_generate_platform_report(self, reporter):
        """Should generate platform report"""
        report = reporter.generate_platform_report(Platform.TIKTOK)
        
        assert report["platform"] == Platform.TIKTOK
        assert report["post_count"] == 1
    
    def test_generate_top_content_report(self, reporter):
        """Should generate top content report"""
        report = reporter.generate_top_content_report(5)
        
        assert "top_by_views" in report
        assert "top_by_engagement" in report


class TestMetricTypes:
    """Test metric type enum"""
    
    def test_views_metric(self):
        """Should have views metric"""
        assert MetricType.VIEWS == "views"
    
    def test_likes_metric(self):
        """Should have likes metric"""
        assert MetricType.LIKES == "likes"
    
    def test_engagement_rate_metric(self):
        """Should have engagement rate metric"""
        assert MetricType.ENGAGEMENT_RATE == "engagement_rate"
    
    def test_all_metric_types(self):
        """Should have all expected types"""
        types = list(MetricType)
        assert len(types) >= 10


class TestAnalyticsPeriod:
    """Test analytics period enum"""
    
    def test_day_period(self):
        """Should have day period"""
        assert AnalyticsPeriod.DAY == "day"
    
    def test_week_period(self):
        """Should have week period"""
        assert AnalyticsPeriod.WEEK == "week"
    
    def test_month_period(self):
        """Should have month period"""
        assert AnalyticsPeriod.MONTH == "month"
    
    def test_all_time_period(self):
        """Should have all time period"""
        assert AnalyticsPeriod.ALL_TIME == "all_time"


class TestDailyMetrics:
    """Test daily metrics aggregation"""
    
    def test_get_daily_metrics(self):
        """Should get daily metrics"""
        agg = AnalyticsAggregator()
        
        # Add content for today
        agg.add_content(PostedContent(
            posted_at=datetime.now(timezone.utc),
            metrics=PostMetrics(views=1000, likes=100)
        ))
        
        daily = agg.get_daily_metrics(7)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        assert today in daily
        assert daily[today]["views"] == 1000
    
    def test_daily_metrics_excludes_old(self):
        """Should exclude old content"""
        agg = AnalyticsAggregator()
        
        # Add old content
        agg.add_content(PostedContent(
            posted_at=datetime.now(timezone.utc) - timedelta(days=30),
            metrics=PostMetrics(views=1000)
        ))
        
        daily = agg.get_daily_metrics(7)
        
        # Old content should not be included
        assert len(daily) == 0


class TestPlatformComparison:
    """Test platform comparison"""
    
    def test_compare_platforms(self):
        """Should compare performance across platforms"""
        agg = AnalyticsAggregator()
        
        for _ in range(3):
            agg.add_content(PostedContent(
                platform=Platform.TIKTOK,
                metrics=PostMetrics(views=1000)
            ))
        
        for _ in range(2):
            agg.add_content(PostedContent(
                platform=Platform.YOUTUBE,
                metrics=PostMetrics(views=5000)
            ))
        
        by_platform = agg.get_performance_by_platform()
        
        assert by_platform[Platform.TIKTOK]["post_count"] == 3
        assert by_platform[Platform.YOUTUBE]["total_views"] == 10000


class TestEngagementCalculation:
    """Test engagement calculations"""
    
    def test_high_engagement(self):
        """Should identify high engagement"""
        metrics = PostMetrics(
            views=100,
            likes=10,
            comments=5,
            shares=3,
            saves=2,
        )
        rate = metrics.calculate_engagement_rate()
        assert rate == 20.0  # 20% engagement
    
    def test_low_engagement(self):
        """Should identify low engagement"""
        metrics = PostMetrics(
            views=10000,
            likes=10,
            comments=0,
            shares=0,
            saves=0,
        )
        rate = metrics.calculate_engagement_rate()
        assert rate == 0.1  # 0.1% engagement


class TestLocalContentTracking:
    """Test local content association tracking"""
    
    def test_count_linked_content(self):
        """Should count linked content"""
        agg = AnalyticsAggregator()
        
        # Add linked
        agg.add_content(PostedContent(local_content_id=uuid4()))
        agg.add_content(PostedContent(local_content_id=uuid4()))
        
        # Add unlinked
        agg.add_content(PostedContent(local_content_id=None))
        
        stats = agg.get_linked_vs_unlinked()
        
        assert stats["linked_count"] == 2
        assert stats["unlinked_count"] == 1
    
    def test_linked_content_views(self):
        """Should track linked content views"""
        agg = AnalyticsAggregator()
        
        agg.add_content(PostedContent(
            local_content_id=uuid4(),
            metrics=PostMetrics(views=1000)
        ))
        agg.add_content(PostedContent(
            local_content_id=None,
            metrics=PostMetrics(views=500)
        ))
        
        stats = agg.get_linked_vs_unlinked()
        
        assert stats["linked_views"] == 1000
        assert stats["unlinked_views"] == 500


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_aggregator(self):
        """Should handle empty aggregator"""
        agg = AnalyticsAggregator()
        
        assert agg.get_total_views() == 0
        assert agg.get_average_engagement_rate() == 0.0
        assert len(agg.get_top_performing()) == 0
    
    def test_single_post(self):
        """Should handle single post"""
        agg = AnalyticsAggregator()
        agg.add_content(PostedContent(metrics=PostMetrics(views=100)))
        
        top = agg.get_top_performing(limit=5)
        assert len(top) == 1
    
    def test_very_high_views(self):
        """Should handle very high view counts"""
        metrics = PostMetrics(views=1_000_000_000)  # 1 billion
        assert metrics.views == 1_000_000_000
    
    def test_zero_metrics(self):
        """Should handle zero metrics"""
        metrics = PostMetrics(
            views=0, likes=0, comments=0, shares=0, saves=0
        )
        rate = metrics.calculate_engagement_rate()
        assert rate == 0.0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
