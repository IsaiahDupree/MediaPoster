"""
Real-Time Metrics Fetching Service
Fetches live metrics from social media platforms using RapidAPI and native APIs.
Supports automatic refresh, caching, and aggregation.
"""

import os
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"


class MetricType(str, Enum):
    PROFILE = "profile"
    POST = "post"
    ENGAGEMENT = "engagement"
    GROWTH = "growth"


class ProfileMetrics(BaseModel):
    """Real-time profile metrics"""
    platform: Platform
    username: str
    account_id: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    engagement_rate: float = 0.0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    avg_views: float = 0.0
    profile_views: int = 0
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_stale: bool = False


class PostMetrics(BaseModel):
    """Real-time post metrics"""
    platform: Platform
    post_id: str
    post_url: Optional[str] = None
    likes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    saves: int = 0
    reach: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0
    posted_at: Optional[str] = None
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class GrowthMetrics(BaseModel):
    """Growth metrics over time"""
    platform: Platform
    username: str
    period_days: int = 7
    follower_change: int = 0
    follower_change_percent: float = 0.0
    post_change: int = 0
    engagement_change_percent: float = 0.0
    best_performing_post_id: Optional[str] = None
    worst_performing_post_id: Optional[str] = None
    calculated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class MetricsCache:
    """In-memory cache for metrics with TTL"""
    
    def __init__(self, default_ttl_seconds: int = 300):
        self._cache: Dict[str, Dict] = {}
        self._ttl = default_ttl_seconds
    
    def _make_key(self, platform: str, identifier: str, metric_type: str) -> str:
        return f"{platform}:{identifier}:{metric_type}"
    
    def get(self, platform: str, identifier: str, metric_type: str) -> Optional[Dict]:
        key = self._make_key(platform, identifier, metric_type)
        if key in self._cache:
            entry = self._cache[key]
            if datetime.fromisoformat(entry["cached_at"]) + timedelta(seconds=self._ttl) > datetime.now():
                return entry["data"]
            else:
                del self._cache[key]
        return None
    
    def set(self, platform: str, identifier: str, metric_type: str, data: Dict):
        key = self._make_key(platform, identifier, metric_type)
        self._cache[key] = {
            "data": data,
            "cached_at": datetime.now().isoformat(),
        }
    
    def invalidate(self, platform: str = None, identifier: str = None):
        if platform and identifier:
            keys_to_delete = [k for k in self._cache if k.startswith(f"{platform}:{identifier}:")]
        elif platform:
            keys_to_delete = [k for k in self._cache if k.startswith(f"{platform}:")]
        else:
            keys_to_delete = list(self._cache.keys())
        
        for key in keys_to_delete:
            del self._cache[key]


class RealTimeMetricsService:
    """Service for fetching real-time metrics from platforms"""
    
    # RapidAPI configurations
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
    
    RAPIDAPI_HOSTS = {
        Platform.INSTAGRAM: "instagram-looter2.p.rapidapi.com",
        Platform.TIKTOK: "tiktok-scraper7.p.rapidapi.com",
        Platform.YOUTUBE: "youtube-v31.p.rapidapi.com",
        Platform.TWITTER: "twitter241.p.rapidapi.com",
    }
    
    def __init__(self, cache_ttl_seconds: int = 300):
        self._cache = MetricsCache(cache_ttl_seconds)
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limits: Dict[Platform, Dict] = defaultdict(lambda: {
            "calls_per_minute": 60,
            "calls_this_minute": 0,
            "minute_start": datetime.now(),
        })
    
    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def _check_rate_limit(self, platform: Platform) -> bool:
        """Check and update rate limit"""
        limits = self._rate_limits[platform]
        now = datetime.now()
        
        # Reset counter if minute has passed
        if (now - limits["minute_start"]).total_seconds() >= 60:
            limits["calls_this_minute"] = 0
            limits["minute_start"] = now
        
        if limits["calls_this_minute"] >= limits["calls_per_minute"]:
            return False
        
        limits["calls_this_minute"] += 1
        return True
    
    # =========================================================================
    # INSTAGRAM METRICS
    # =========================================================================
    
    async def get_instagram_profile(self, username: str, use_cache: bool = True) -> ProfileMetrics:
        """Fetch Instagram profile metrics"""
        if use_cache:
            cached = self._cache.get(Platform.INSTAGRAM.value, username, MetricType.PROFILE.value)
            if cached:
                return ProfileMetrics(**cached)
        
        try:
            if not await self._check_rate_limit(Platform.INSTAGRAM):
                logger.warning("Instagram rate limit exceeded")
                return ProfileMetrics(platform=Platform.INSTAGRAM, username=username, is_stale=True)
            
            client = await self._get_client()
            response = await client.get(
                f"https://{self.RAPIDAPI_HOSTS[Platform.INSTAGRAM]}/profile",
                headers={
                    "X-RapidAPI-Key": self.RAPIDAPI_KEY,
                    "X-RapidAPI-Host": self.RAPIDAPI_HOSTS[Platform.INSTAGRAM],
                },
                params={"username": username},
            )
            
            if response.status_code == 200:
                data = response.json().get("data", response.json())
                metrics = ProfileMetrics(
                    platform=Platform.INSTAGRAM,
                    username=username,
                    account_id=str(data.get("pk", data.get("id"))),
                    follower_count=data.get("follower_count", 0),
                    following_count=data.get("following_count", 0),
                    post_count=data.get("media_count", 0),
                    engagement_rate=data.get("engagement_rate", 0),
                )
                
                self._cache.set(Platform.INSTAGRAM.value, username, MetricType.PROFILE.value, metrics.model_dump())
                return metrics
            
        except Exception as e:
            logger.error(f"Instagram profile fetch error: {e}")
        
        return ProfileMetrics(platform=Platform.INSTAGRAM, username=username, is_stale=True)
    
    async def get_instagram_post(self, post_id: str, use_cache: bool = True) -> PostMetrics:
        """Fetch Instagram post metrics"""
        if use_cache:
            cached = self._cache.get(Platform.INSTAGRAM.value, post_id, MetricType.POST.value)
            if cached:
                return PostMetrics(**cached)
        
        try:
            if not await self._check_rate_limit(Platform.INSTAGRAM):
                return PostMetrics(platform=Platform.INSTAGRAM, post_id=post_id)
            
            client = await self._get_client()
            response = await client.get(
                f"https://{self.RAPIDAPI_HOSTS[Platform.INSTAGRAM]}/post",
                headers={
                    "X-RapidAPI-Key": self.RAPIDAPI_KEY,
                    "X-RapidAPI-Host": self.RAPIDAPI_HOSTS[Platform.INSTAGRAM],
                },
                params={"id": post_id},
            )
            
            if response.status_code == 200:
                data = response.json().get("data", response.json())
                metrics = PostMetrics(
                    platform=Platform.INSTAGRAM,
                    post_id=post_id,
                    post_url=data.get("url"),
                    likes=data.get("like_count", 0),
                    comments=data.get("comment_count", 0),
                    views=data.get("view_count", data.get("play_count", 0)),
                    shares=data.get("share_count", 0),
                    saves=data.get("save_count", 0),
                    posted_at=data.get("taken_at"),
                )
                
                self._cache.set(Platform.INSTAGRAM.value, post_id, MetricType.POST.value, metrics.model_dump())
                return metrics
            
        except Exception as e:
            logger.error(f"Instagram post fetch error: {e}")
        
        return PostMetrics(platform=Platform.INSTAGRAM, post_id=post_id)
    
    # =========================================================================
    # TIKTOK METRICS
    # =========================================================================
    
    async def get_tiktok_profile(self, username: str, use_cache: bool = True) -> ProfileMetrics:
        """Fetch TikTok profile metrics"""
        if use_cache:
            cached = self._cache.get(Platform.TIKTOK.value, username, MetricType.PROFILE.value)
            if cached:
                return ProfileMetrics(**cached)
        
        try:
            if not await self._check_rate_limit(Platform.TIKTOK):
                return ProfileMetrics(platform=Platform.TIKTOK, username=username, is_stale=True)
            
            client = await self._get_client()
            response = await client.get(
                f"https://{self.RAPIDAPI_HOSTS[Platform.TIKTOK]}/user/info",
                headers={
                    "X-RapidAPI-Key": self.RAPIDAPI_KEY,
                    "X-RapidAPI-Host": self.RAPIDAPI_HOSTS[Platform.TIKTOK],
                },
                params={"unique_id": username},
            )
            
            if response.status_code == 200:
                data = response.json().get("data", {}).get("user", response.json())
                stats = response.json().get("data", {}).get("stats", {})
                
                metrics = ProfileMetrics(
                    platform=Platform.TIKTOK,
                    username=username,
                    account_id=data.get("id"),
                    follower_count=stats.get("followerCount", 0),
                    following_count=stats.get("followingCount", 0),
                    post_count=stats.get("videoCount", 0),
                    avg_likes=stats.get("heartCount", 0) / max(stats.get("videoCount", 1), 1),
                )
                
                self._cache.set(Platform.TIKTOK.value, username, MetricType.PROFILE.value, metrics.model_dump())
                return metrics
            
        except Exception as e:
            logger.error(f"TikTok profile fetch error: {e}")
        
        return ProfileMetrics(platform=Platform.TIKTOK, username=username, is_stale=True)
    
    async def get_tiktok_post(self, video_id: str, use_cache: bool = True) -> PostMetrics:
        """Fetch TikTok video metrics"""
        if use_cache:
            cached = self._cache.get(Platform.TIKTOK.value, video_id, MetricType.POST.value)
            if cached:
                return PostMetrics(**cached)
        
        try:
            if not await self._check_rate_limit(Platform.TIKTOK):
                return PostMetrics(platform=Platform.TIKTOK, post_id=video_id)
            
            client = await self._get_client()
            response = await client.get(
                f"https://{self.RAPIDAPI_HOSTS[Platform.TIKTOK]}/video/info",
                headers={
                    "X-RapidAPI-Key": self.RAPIDAPI_KEY,
                    "X-RapidAPI-Host": self.RAPIDAPI_HOSTS[Platform.TIKTOK],
                },
                params={"video_id": video_id},
            )
            
            if response.status_code == 200:
                data = response.json().get("data", response.json())
                stats = data.get("stats", data)
                
                metrics = PostMetrics(
                    platform=Platform.TIKTOK,
                    post_id=video_id,
                    likes=stats.get("diggCount", stats.get("likes", 0)),
                    comments=stats.get("commentCount", stats.get("comments", 0)),
                    shares=stats.get("shareCount", stats.get("shares", 0)),
                    views=stats.get("playCount", stats.get("views", 0)),
                )
                
                self._cache.set(Platform.TIKTOK.value, video_id, MetricType.POST.value, metrics.model_dump())
                return metrics
            
        except Exception as e:
            logger.error(f"TikTok video fetch error: {e}")
        
        return PostMetrics(platform=Platform.TIKTOK, post_id=video_id)
    
    # =========================================================================
    # YOUTUBE METRICS
    # =========================================================================
    
    async def get_youtube_channel(self, channel_id: str, use_cache: bool = True) -> ProfileMetrics:
        """Fetch YouTube channel metrics"""
        if use_cache:
            cached = self._cache.get(Platform.YOUTUBE.value, channel_id, MetricType.PROFILE.value)
            if cached:
                return ProfileMetrics(**cached)
        
        try:
            if not await self._check_rate_limit(Platform.YOUTUBE):
                return ProfileMetrics(platform=Platform.YOUTUBE, username=channel_id, is_stale=True)
            
            client = await self._get_client()
            response = await client.get(
                f"https://{self.RAPIDAPI_HOSTS[Platform.YOUTUBE]}/channels",
                headers={
                    "X-RapidAPI-Key": self.RAPIDAPI_KEY,
                    "X-RapidAPI-Host": self.RAPIDAPI_HOSTS[Platform.YOUTUBE],
                },
                params={
                    "part": "snippet,statistics",
                    "id": channel_id,
                },
            )
            
            if response.status_code == 200:
                items = response.json().get("items", [])
                if items:
                    data = items[0]
                    stats = data.get("statistics", {})
                    snippet = data.get("snippet", {})
                    
                    metrics = ProfileMetrics(
                        platform=Platform.YOUTUBE,
                        username=snippet.get("title", channel_id),
                        account_id=channel_id,
                        follower_count=int(stats.get("subscriberCount", 0)),
                        post_count=int(stats.get("videoCount", 0)),
                        avg_views=int(stats.get("viewCount", 0)) / max(int(stats.get("videoCount", 1)), 1),
                    )
                    
                    self._cache.set(Platform.YOUTUBE.value, channel_id, MetricType.PROFILE.value, metrics.model_dump())
                    return metrics
            
        except Exception as e:
            logger.error(f"YouTube channel fetch error: {e}")
        
        return ProfileMetrics(platform=Platform.YOUTUBE, username=channel_id, is_stale=True)
    
    async def get_youtube_video(self, video_id: str, use_cache: bool = True) -> PostMetrics:
        """Fetch YouTube video metrics"""
        if use_cache:
            cached = self._cache.get(Platform.YOUTUBE.value, video_id, MetricType.POST.value)
            if cached:
                return PostMetrics(**cached)
        
        try:
            if not await self._check_rate_limit(Platform.YOUTUBE):
                return PostMetrics(platform=Platform.YOUTUBE, post_id=video_id)
            
            client = await self._get_client()
            response = await client.get(
                f"https://{self.RAPIDAPI_HOSTS[Platform.YOUTUBE]}/videos",
                headers={
                    "X-RapidAPI-Key": self.RAPIDAPI_KEY,
                    "X-RapidAPI-Host": self.RAPIDAPI_HOSTS[Platform.YOUTUBE],
                },
                params={
                    "part": "statistics,snippet",
                    "id": video_id,
                },
            )
            
            if response.status_code == 200:
                items = response.json().get("items", [])
                if items:
                    data = items[0]
                    stats = data.get("statistics", {})
                    snippet = data.get("snippet", {})
                    
                    metrics = PostMetrics(
                        platform=Platform.YOUTUBE,
                        post_id=video_id,
                        post_url=f"https://youtube.com/watch?v={video_id}",
                        views=int(stats.get("viewCount", 0)),
                        likes=int(stats.get("likeCount", 0)),
                        comments=int(stats.get("commentCount", 0)),
                        posted_at=snippet.get("publishedAt"),
                    )
                    
                    self._cache.set(Platform.YOUTUBE.value, video_id, MetricType.POST.value, metrics.model_dump())
                    return metrics
            
        except Exception as e:
            logger.error(f"YouTube video fetch error: {e}")
        
        return PostMetrics(platform=Platform.YOUTUBE, post_id=video_id)
    
    # =========================================================================
    # AGGREGATION & BATCH METHODS
    # =========================================================================
    
    async def get_all_profile_metrics(
        self,
        accounts: List[Dict[str, str]],
        use_cache: bool = True,
    ) -> List[ProfileMetrics]:
        """Fetch metrics for multiple accounts across platforms"""
        tasks = []
        
        for account in accounts:
            platform = Platform(account.get("platform", "instagram"))
            username = account.get("username", "")
            
            if platform == Platform.INSTAGRAM:
                tasks.append(self.get_instagram_profile(username, use_cache))
            elif platform == Platform.TIKTOK:
                tasks.append(self.get_tiktok_profile(username, use_cache))
            elif platform == Platform.YOUTUBE:
                tasks.append(self.get_youtube_channel(account.get("channel_id", username), use_cache))
        
        return await asyncio.gather(*tasks)
    
    async def get_post_metrics_batch(
        self,
        posts: List[Dict[str, str]],
        use_cache: bool = True,
    ) -> List[PostMetrics]:
        """Fetch metrics for multiple posts"""
        tasks = []
        
        for post in posts:
            platform = Platform(post.get("platform", "instagram"))
            post_id = post.get("post_id", "")
            
            if platform == Platform.INSTAGRAM:
                tasks.append(self.get_instagram_post(post_id, use_cache))
            elif platform == Platform.TIKTOK:
                tasks.append(self.get_tiktok_post(post_id, use_cache))
            elif platform == Platform.YOUTUBE:
                tasks.append(self.get_youtube_video(post_id, use_cache))
        
        return await asyncio.gather(*tasks)
    
    async def calculate_growth_metrics(
        self,
        platform: Platform,
        username: str,
        period_days: int = 7,
    ) -> GrowthMetrics:
        """Calculate growth metrics over a period (requires historical data)"""
        # This would typically use stored historical data
        # For now, return a placeholder
        return GrowthMetrics(
            platform=platform,
            username=username,
            period_days=period_days,
        )
    
    def invalidate_cache(self, platform: str = None, identifier: str = None):
        """Invalidate cached metrics"""
        self._cache.invalidate(platform, identifier)
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
realtime_metrics_service = RealTimeMetricsService()
