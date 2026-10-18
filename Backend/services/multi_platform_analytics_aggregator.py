"""
Multi-Platform Analytics Aggregator (ANALYTICS-001)
====================================================
Aggregates analytics from Instagram, TikTok, YouTube, Twitter/X, and other platforms
into a unified view with cross-platform comparison capabilities.

Features:
- Unified metrics across all platforms
- Cross-platform performance comparison
- Normalized engagement rates
- Platform-specific metric collection
- Real-time and historical data aggregation
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

# Import platform-specific analytics services
from services.instagram_analytics import InstagramAnalytics
from services.tiktok_analytics_service import get_tiktok_analytics_service
from services.youtube_analytics_service import get_youtube_analytics_service
from services.fetch_social_analytics import SocialAnalyticsFetcher
from services.strategic_analysis_service import (
    YouTubeCollector, TikTokCollector, InstagramCollector,
    InstagramGraphCollector, FacebookAdsCollector,
)


class Platform(Enum):
    """Supported platforms"""
    INSTAGRAM = "instagram"
    INSTAGRAM_GRAPH = "instagram_graph"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    THREADS = "threads"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    FACEBOOK_ADS = "facebook_ads"


@dataclass
class UnifiedMetrics:
    """Unified metrics across all platforms"""
    # Engagement metrics (normalized)
    total_views: int = 0
    total_impressions: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_saves: int = 0
    total_clicks: int = 0

    # Follower/subscriber metrics
    total_followers: int = 0
    follower_growth: int = 0

    # Performance metrics
    avg_engagement_rate: float = 0.0
    avg_watch_time_seconds: float = 0.0
    avg_completion_rate: float = 0.0

    # Content metrics
    total_posts: int = 0
    posts_last_7d: int = 0
    posts_last_30d: int = 0

    # Best performers
    best_platform: Optional[str] = None
    best_platform_engagement_rate: float = 0.0
    top_post_id: Optional[str] = None
    top_post_views: int = 0

    # Timestamps
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_freshness_minutes: int = 0


@dataclass
class PlatformMetrics:
    """Platform-specific metrics"""
    platform: str
    account_id: str
    account_username: str

    # Core metrics
    views: int = 0
    impressions: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0

    # Account metrics
    followers: int = 0
    follower_growth_7d: int = 0
    follower_growth_30d: int = 0

    # Engagement metrics
    engagement_rate: float = 0.0
    avg_watch_time_seconds: float = 0.0
    completion_rate: float = 0.0

    # Content metrics
    total_posts: int = 0
    posts_last_7d: int = 0
    posts_last_30d: int = 0

    # Metadata
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "platform": self.platform,
            "account_id": self.account_id,
            "account_username": self.account_username,
            "views": self.views,
            "impressions": self.impressions,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "saves": self.saves,
            "clicks": self.clicks,
            "followers": self.followers,
            "follower_growth_7d": self.follower_growth_7d,
            "follower_growth_30d": self.follower_growth_30d,
            "engagement_rate": self.engagement_rate,
            "avg_watch_time_seconds": self.avg_watch_time_seconds,
            "completion_rate": self.completion_rate,
            "total_posts": self.total_posts,
            "posts_last_7d": self.posts_last_7d,
            "posts_last_30d": self.posts_last_30d,
            "last_updated": self.last_updated.isoformat(),
            "errors": self.errors
        }


@dataclass
class CrossPlatformComparison:
    """Cross-platform performance comparison"""
    platform_rankings: List[Dict[str, Any]] = field(default_factory=list)
    best_platform_for_views: Optional[str] = None
    best_platform_for_engagement: Optional[str] = None
    most_consistent_platform: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)


class MultiPlatformAnalyticsAggregator:
    """
    Multi-Platform Analytics Aggregator (ANALYTICS-001)

    Aggregates analytics from multiple social platforms into a unified view.

    Usage:
        aggregator = MultiPlatformAnalyticsAggregator()

        # Get unified metrics for all configured accounts
        unified = await aggregator.get_unified_metrics()

        # Get platform-specific metrics
        platform_metrics = await aggregator.get_platform_metrics("instagram")

        # Compare performance across platforms
        comparison = await aggregator.compare_platforms()
    """

    _instance: Optional["MultiPlatformAnalyticsAggregator"] = None

    def __init__(self):
        """Initialize the aggregator"""
        if MultiPlatformAnalyticsAggregator._instance is not None:
            raise RuntimeError("Use MultiPlatformAnalyticsAggregator.get_instance()")

        # Initialize platform-specific services (legacy)
        self.instagram_service = InstagramAnalytics()
        self.tiktok_service = get_tiktok_analytics_service()
        self.youtube_service = get_youtube_analytics_service()
        self.social_fetcher = SocialAnalyticsFetcher()

        # Live API collectors (real data)
        self._youtube_collector = YouTubeCollector()
        self._tiktok_collector = TikTokCollector()
        self._instagram_collector = InstagramCollector()
        self._instagram_graph_collector = InstagramGraphCollector()
        self._facebook_ads_collector = FacebookAdsCollector()

        # Event bus integration
        self._bus = None
        try:
            from services.event_bus import EventBus, Topics
            self._bus = EventBus.get_instance()
            self._topics = Topics
            self._bus.subscribe(Topics.STRATEGY_PLATFORM_DATA_READY, self._on_strategy_data)
            self._bus.subscribe(Topics.METRICS_FETCH_REQUESTED, self._on_metrics_requested)
        except Exception as e:
            logger.warning(f"Event bus not available for aggregator: {e}")

        # Cache for aggregated data
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes

        logger.info("📊 Multi-Platform Analytics Aggregator initialized (live API collectors)")

    @classmethod
    def get_instance(cls) -> "MultiPlatformAnalyticsAggregator":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_unified_metrics(
        self,
        time_range_days: int = 30,
        force_refresh: bool = False
    ) -> UnifiedMetrics:
        """
        Get unified metrics across all platforms

        Args:
            time_range_days: Number of days to include in the aggregation
            force_refresh: Skip cache and fetch fresh data

        Returns:
            UnifiedMetrics object with aggregated data
        """
        cache_key = f"unified_metrics_{time_range_days}"

        # Check cache
        if not force_refresh and cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if (datetime.now(timezone.utc) - cached_data["timestamp"]).seconds < self._cache_ttl:
                logger.debug(f"Returning cached unified metrics")
                return cached_data["data"]

        logger.info(f"Aggregating metrics from all platforms (last {time_range_days} days)")

        # Fetch metrics from all platforms in parallel
        tasks = [
            self._get_youtube_metrics(time_range_days),
            self._get_tiktok_metrics(time_range_days),
            self._get_instagram_metrics(time_range_days),
            self._get_instagram_graph_metrics(time_range_days),
            self._get_facebook_ads_metrics(time_range_days),
        ]

        platform_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        unified = UnifiedMetrics()
        platform_metrics_list = []

        for result in platform_results:
            if isinstance(result, Exception):
                logger.error(f"Error fetching platform metrics: {result}")
                continue

            if result is None:
                continue

            platform_metrics_list.append(result)

            # Aggregate totals
            unified.total_views += result.views
            unified.total_impressions += result.impressions
            unified.total_likes += result.likes
            unified.total_comments += result.comments
            unified.total_shares += result.shares
            unified.total_saves += result.saves
            unified.total_clicks += result.clicks
            unified.total_followers += result.followers
            unified.total_posts += result.total_posts
            unified.posts_last_7d += result.posts_last_7d
            unified.posts_last_30d += result.posts_last_30d

        # Calculate averages and best performers
        if platform_metrics_list:
            unified.avg_engagement_rate = sum(
                m.engagement_rate for m in platform_metrics_list
            ) / len(platform_metrics_list)

            unified.avg_watch_time_seconds = sum(
                m.avg_watch_time_seconds for m in platform_metrics_list
            ) / len(platform_metrics_list)

            unified.avg_completion_rate = sum(
                m.completion_rate for m in platform_metrics_list
            ) / len(platform_metrics_list)

            # Find best platform
            best_platform = max(
                platform_metrics_list,
                key=lambda m: m.engagement_rate
            )
            unified.best_platform = best_platform.platform
            unified.best_platform_engagement_rate = best_platform.engagement_rate

            # Find top post
            top_platform = max(
                platform_metrics_list,
                key=lambda m: m.views
            )
            unified.top_post_id = f"{top_platform.platform}:latest"
            unified.top_post_views = top_platform.views

        unified.last_updated = datetime.now(timezone.utc)

        # Cache the result
        self._cache[cache_key] = {
            "timestamp": datetime.now(timezone.utc),
            "data": unified
        }

        logger.success(
            f"✓ Unified metrics aggregated | "
            f"{unified.total_views:,} views | "
            f"{unified.total_likes:,} likes | "
            f"Best: {unified.best_platform}"
        )

        return unified

    async def get_platform_metrics(
        self,
        platform: str,
        account_id: Optional[str] = None,
        time_range_days: int = 30
    ) -> Optional[PlatformMetrics]:
        """
        Get metrics for a specific platform

        Args:
            platform: Platform name (instagram, tiktok, youtube, instagram_graph, facebook_ads)
            account_id: Specific account ID (optional)
            time_range_days: Number of days to include

        Returns:
            PlatformMetrics object or None if platform not supported
        """
        platform = platform.lower()

        fetchers = {
            "instagram": self._get_instagram_metrics,
            "tiktok": self._get_tiktok_metrics,
            "youtube": self._get_youtube_metrics,
            "instagram_graph": self._get_instagram_graph_metrics,
            "facebook_ads": self._get_facebook_ads_metrics,
        }

        fetcher = fetchers.get(platform)
        if not fetcher:
            logger.warning(f"Platform '{platform}' not supported")
            return None

        return await fetcher(time_range_days, account_id)

    async def compare_platforms(
        self,
        time_range_days: int = 30
    ) -> CrossPlatformComparison:
        """
        Compare performance across platforms

        Args:
            time_range_days: Number of days to include in comparison

        Returns:
            CrossPlatformComparison with rankings and recommendations
        """
        logger.info("Comparing platform performance...")

        # Get metrics for all platforms
        platforms = ["youtube", "tiktok", "instagram", "instagram_graph", "facebook_ads"]
        metrics_list = []

        for platform in platforms:
            metrics = await self.get_platform_metrics(platform, time_range_days=time_range_days)
            if metrics:
                metrics_list.append(metrics)

        if not metrics_list:
            return CrossPlatformComparison()

        # Rank platforms by engagement rate
        ranked_by_engagement = sorted(
            metrics_list,
            key=lambda m: m.engagement_rate,
            reverse=True
        )

        # Rank platforms by views
        ranked_by_views = sorted(
            metrics_list,
            key=lambda m: m.views,
            reverse=True
        )

        # Calculate consistency (lower variance = more consistent)
        engagement_rates = [m.engagement_rate for m in metrics_list]
        avg_engagement = sum(engagement_rates) / len(engagement_rates)
        variance = sum((r - avg_engagement) ** 2 for r in engagement_rates) / len(engagement_rates)

        most_consistent = min(
            metrics_list,
            key=lambda m: abs(m.engagement_rate - avg_engagement)
        )

        # Build rankings
        platform_rankings = [
            {
                "platform": m.platform,
                "views": m.views,
                "engagement_rate": m.engagement_rate,
                "followers": m.followers,
                "rank_by_engagement": ranked_by_engagement.index(m) + 1,
                "rank_by_views": ranked_by_views.index(m) + 1
            }
            for m in metrics_list
        ]

        # Generate recommendations
        recommendations = []

        # Best platform recommendation
        if ranked_by_engagement:
            best = ranked_by_engagement[0]
            recommendations.append(
                f"{best.platform.title()} has the highest engagement rate ({best.engagement_rate:.2%}). "
                f"Consider posting more frequently there."
            )

        # Growth opportunity recommendation
        if len(ranked_by_engagement) >= 2:
            worst = ranked_by_engagement[-1]
            if worst.engagement_rate < avg_engagement * 0.5:
                recommendations.append(
                    f"{worst.platform.title()} is underperforming (engagement: {worst.engagement_rate:.2%}). "
                    f"Consider A/B testing different content formats."
                )

        # Consistency recommendation
        if variance > 0.01:
            recommendations.append(
                f"Performance varies significantly across platforms (variance: {variance:.4f}). "
                f"Consider tailoring content to each platform's audience."
            )

        comparison = CrossPlatformComparison(
            platform_rankings=platform_rankings,
            best_platform_for_views=ranked_by_views[0].platform if ranked_by_views else None,
            best_platform_for_engagement=ranked_by_engagement[0].platform if ranked_by_engagement else None,
            most_consistent_platform=most_consistent.platform,
            recommendations=recommendations
        )

        logger.success(
            f"✓ Platform comparison complete | "
            f"Best for views: {comparison.best_platform_for_views} | "
            f"Best for engagement: {comparison.best_platform_for_engagement}"
        )

        return comparison

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    async def _on_strategy_data(self, event):
        """Auto-update cache when strategic analysis produces fresh platform data."""
        platform = event.payload.get("platform", "unknown")
        logger.debug(f"📊 Aggregator received strategy data for {platform}")
        # Invalidate cache so next request fetches fresh
        self._cache.clear()

    async def _on_metrics_requested(self, event):
        """Handle metrics.fetch.requested — trigger a fresh aggregation."""
        platforms = event.payload.get("platforms")
        logger.info(f"📊 Metrics fetch requested via event bus: {platforms}")
        await self.get_unified_metrics(force_refresh=True)

    async def _publish_metrics_event(self, topic: str, payload: Dict[str, Any]):
        """Publish a metrics event to the event bus if available."""
        if self._bus:
            try:
                await self._bus.publish(topic, payload, source="multi-platform-aggregator")
            except Exception as e:
                logger.debug(f"Could not publish {topic}: {e}")

    # =========================================================================
    # LIVE PLATFORM DATA FETCHERS
    # =========================================================================

    async def _get_youtube_metrics(
        self,
        time_range_days: int,
        account_id: Optional[str] = None
    ) -> Optional[PlatformMetrics]:
        """Fetch YouTube metrics via YouTube Data API v3"""
        try:
            snap = await self._youtube_collector.collect()

            metrics = PlatformMetrics(
                platform="youtube",
                account_id=account_id or snap.account_id or "youtube",
                account_username=snap.account_username,
                views=snap.total_views,
                likes=snap.total_likes,
                comments=snap.total_comments,
                shares=snap.total_shares,
                followers=snap.followers,
                engagement_rate=snap.engagement_rate,
                avg_views_per_post=snap.avg_views_per_post if hasattr(snap, 'avg_views_per_post') else 0,
                total_posts=snap.total_posts,
            )
            if snap.error:
                metrics.errors.append(snap.error)

            await self._publish_metrics_event(
                self._topics.METRICS_FETCH_COMPLETED if self._bus else "metrics.fetch.completed",
                {"platform": "youtube", "followers": snap.followers, "views": snap.total_views},
            )

            logger.debug(f"YouTube live: {metrics.views:,} views, {metrics.followers:,} subs")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching YouTube metrics: {e}")
            return None

    async def _get_tiktok_metrics(
        self,
        time_range_days: int,
        account_id: Optional[str] = None
    ) -> Optional[PlatformMetrics]:
        """Fetch TikTok metrics via RapidAPI tiktok-scraper7"""
        try:
            snap = await self._tiktok_collector.collect()

            metrics = PlatformMetrics(
                platform="tiktok",
                account_id=account_id or "tiktok",
                account_username=snap.account_username,
                views=snap.total_views,
                likes=snap.total_likes,
                comments=snap.total_comments,
                shares=snap.total_shares,
                saves=snap.total_saves,
                followers=snap.followers,
                engagement_rate=snap.engagement_rate,
                total_posts=snap.total_posts,
            )
            if snap.error:
                metrics.errors.append(snap.error)

            await self._publish_metrics_event(
                self._topics.METRICS_FETCH_COMPLETED if self._bus else "metrics.fetch.completed",
                {"platform": "tiktok", "followers": snap.followers, "likes": snap.total_likes},
            )

            logger.debug(f"TikTok live: {metrics.likes:,} likes, {metrics.followers:,} followers")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching TikTok metrics: {e}")
            return None

    async def _get_instagram_metrics(
        self,
        time_range_days: int,
        account_id: Optional[str] = None
    ) -> Optional[PlatformMetrics]:
        """Fetch Instagram metrics via RapidAPI instagram-looter2 (public data)"""
        try:
            snap = await self._instagram_collector.collect()

            metrics = PlatformMetrics(
                platform="instagram",
                account_id=account_id or "instagram",
                account_username=snap.account_username,
                views=snap.total_views,
                likes=snap.total_likes,
                comments=snap.total_comments,
                followers=snap.followers,
                engagement_rate=snap.engagement_rate,
                total_posts=snap.total_posts,
            )
            if snap.error:
                metrics.errors.append(snap.error)

            logger.debug(f"Instagram (RapidAPI): {metrics.followers:,} followers, {metrics.total_posts} posts")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching Instagram metrics: {e}")
            return None

    async def _get_instagram_graph_metrics(
        self,
        time_range_days: int,
        account_id: Optional[str] = None
    ) -> Optional[PlatformMetrics]:
        """Fetch Instagram metrics via official Graph API (IGAA token)

        Returns per-post insights: likes, comments, shares, saves, total_interactions.
        """
        try:
            snap = await self._instagram_graph_collector.collect()

            metrics = PlatformMetrics(
                platform="instagram_graph",
                account_id=account_id or snap.account_id or "instagram_graph",
                account_username=snap.account_username,
                views=snap.total_views,
                impressions=snap.raw_data.get("total_impressions_25_posts", 0),
                likes=snap.total_likes,
                comments=snap.total_comments,
                shares=snap.total_shares,
                saves=snap.total_saves,
                followers=snap.followers,
                engagement_rate=snap.engagement_rate,
                total_posts=snap.total_posts,
            )
            if snap.error:
                metrics.errors.append(snap.error)

            await self._publish_metrics_event(
                self._topics.METRICS_FETCH_COMPLETED if self._bus else "metrics.fetch.completed",
                {
                    "platform": "instagram_graph",
                    "followers": snap.followers,
                    "interactions": snap.raw_data.get("total_interactions_25_posts", 0),
                    "saves": snap.total_saves,
                    "shares": snap.total_shares,
                },
            )

            logger.debug(
                f"Instagram Graph: {metrics.followers:,} followers, "
                f"{metrics.saves} saves, {metrics.shares} shares, "
                f"{snap.raw_data.get('total_interactions_25_posts', 0)} interactions"
            )
            return metrics

        except Exception as e:
            logger.error(f"Error fetching Instagram Graph metrics: {e}")
            return None

    async def _get_facebook_ads_metrics(
        self,
        time_range_days: int,
        account_id: Optional[str] = None
    ) -> Optional[PlatformMetrics]:
        """Fetch Facebook Ads metrics via Marketing API (30-day campaign data)"""
        try:
            snap = await self._facebook_ads_collector.collect()

            metrics = PlatformMetrics(
                platform="facebook_ads",
                account_id=account_id or snap.account_id or "facebook_ads",
                account_username=snap.raw_data.get("account_name", "Facebook Ads"),
                views=snap.total_views,  # impressions
                impressions=snap.raw_data.get("total_impressions_30d", 0),
                clicks=snap.raw_data.get("total_clicks_30d", 0),
                engagement_rate=snap.engagement_rate,  # CTR
            )
            if snap.error:
                metrics.errors.append(snap.error)

            # Attach ad-specific data
            metrics.ad_spend_30d = snap.raw_data.get("total_spend_30d", 0)
            metrics.ad_ctr = snap.raw_data.get("ctr_30d", "0%")
            metrics.ad_campaigns = snap.raw_data.get("campaign_count", 0)

            await self._publish_metrics_event(
                self._topics.METRICS_FETCH_COMPLETED if self._bus else "metrics.fetch.completed",
                {
                    "platform": "facebook_ads",
                    "spend": snap.raw_data.get("total_spend_30d", 0),
                    "impressions": snap.raw_data.get("total_impressions_30d", 0),
                    "clicks": snap.raw_data.get("total_clicks_30d", 0),
                },
            )

            logger.debug(
                f"Facebook Ads: ${snap.raw_data.get('total_spend_30d', 0)} spend, "
                f"{snap.raw_data.get('total_impressions_30d', 0):,} impressions"
            )
            return metrics

        except Exception as e:
            logger.error(f"Error fetching Facebook Ads metrics: {e}")
            return None


# Singleton accessor
def get_multi_platform_analytics_aggregator() -> MultiPlatformAnalyticsAggregator:
    """Get the singleton MultiPlatformAnalyticsAggregator instance"""
    return MultiPlatformAnalyticsAggregator.get_instance()
