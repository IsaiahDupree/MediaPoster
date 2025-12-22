"""
Platform Data Orchestrator
Unified system for efficiently fetching data across all platforms with:
- Failover between API providers
- Batch processing to minimize API calls
- Caching to reduce redundant calls
- Automatic population of engagement scores, comments, and followers
"""
import os
import asyncio
import httpx
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    BLUESKY = "bluesky"
    THREADS = "threads"
    PINTEREST = "pinterest"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"


class DataType(str, Enum):
    PROFILE = "profile"
    POSTS = "posts"
    POST_METRICS = "post_metrics"
    COMMENTS = "comments"
    FOLLOWERS = "followers"


@dataclass
class ProviderConfig:
    name: str
    host: str
    priority: int
    endpoints: Dict[DataType, str]
    rate_limit: int = 100  # calls per day
    error_count: int = 0
    last_error: Optional[datetime] = None
    disabled_until: Optional[datetime] = None
    calls_today: int = 0
    last_reset: datetime = field(default_factory=datetime.now)


@dataclass
class FetchResult:
    success: bool
    platform: Platform
    data_type: DataType
    data: Optional[Dict] = None
    error: Optional[str] = None
    provider_used: Optional[str] = None
    cached: bool = False


class PlatformDataOrchestrator:
    """
    Unified orchestrator for fetching social media data efficiently.
    
    Features:
    - Multi-provider failover per platform
    - Smart batching to minimize API calls
    - In-memory caching with TTL
    - Rate limit awareness
    - Automatic data population to database
    """
    
    def __init__(self):
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY", "")
        self.db_url = os.getenv("DATABASE_URL", "")
        self.timeout = 30
        
        # Cache with TTL (data, timestamp)
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = timedelta(minutes=15)
        
        # Provider configurations per platform
        self.providers: Dict[Platform, List[ProviderConfig]] = {
            Platform.TIKTOK: [
                ProviderConfig(
                    name="tiktok-scraper7",
                    host="tiktok-scraper7.p.rapidapi.com",
                    priority=1,
                    rate_limit=500,
                    endpoints={
                        DataType.PROFILE: "/user/info",
                        DataType.POSTS: "/user/posts",
                        DataType.POST_METRICS: "/video/info",
                        DataType.COMMENTS: "/comment/list",
                    }
                ),
                ProviderConfig(
                    name="tiktok-feature-summary",
                    host="tiktok-video-feature-summary.p.rapidapi.com",
                    priority=2,
                    rate_limit=100,
                    endpoints={
                        DataType.PROFILE: "/user/details",
                        DataType.POSTS: "/user/videos",
                    }
                ),
            ],
            Platform.INSTAGRAM: [
                ProviderConfig(
                    name="instagram-looter2",
                    host="instagram-looter2.p.rapidapi.com",
                    priority=1,
                    rate_limit=100,
                    endpoints={
                        DataType.PROFILE: "/profile",
                        DataType.POSTS: "/posts",
                        DataType.POST_METRICS: "/media",
                    }
                ),
                ProviderConfig(
                    name="instagram-statistics",
                    host="instagram-statistics-api.p.rapidapi.com",
                    priority=2,
                    rate_limit=100,
                    endpoints={
                        DataType.PROFILE: "/community",
                        DataType.POSTS: "/posts",
                    }
                ),
            ],
            Platform.YOUTUBE: [
                ProviderConfig(
                    name="google-youtube-api",
                    host="www.googleapis.com",  # Direct Google API
                    priority=1,
                    rate_limit=10000,  # YouTube has generous limits
                    endpoints={
                        DataType.PROFILE: "/youtube/v3/channels",
                        DataType.POSTS: "/youtube/v3/search",
                        DataType.POST_METRICS: "/youtube/v3/videos",
                        DataType.COMMENTS: "/youtube/v3/commentThreads",
                    }
                ),
            ],
            Platform.TWITTER: [
                ProviderConfig(
                    name="twitter-api45",
                    host="twitter-api45.p.rapidapi.com",
                    priority=1,
                    rate_limit=100,
                    endpoints={
                        DataType.PROFILE: "/timeline.php",
                        DataType.POSTS: "/timeline.php",
                    }
                ),
            ],
            Platform.BLUESKY: [
                ProviderConfig(
                    name="bluesky-public",
                    host="public.api.bsky.app",  # Free public API
                    priority=1,
                    rate_limit=1000,
                    endpoints={
                        DataType.PROFILE: "/xrpc/app.bsky.actor.getProfile",
                        DataType.POSTS: "/xrpc/app.bsky.feed.getAuthorFeed",
                        DataType.POST_METRICS: "/xrpc/app.bsky.feed.getPosts",
                    }
                ),
            ],
        }
    
    def _get_cache_key(self, platform: Platform, data_type: DataType, identifier: str) -> str:
        return f"{platform.value}:{data_type.value}:{identifier}"
    
    def _get_cached(self, key: str) -> Optional[Any]:
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < self.cache_ttl:
                return data
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: Any):
        self._cache[key] = (data, datetime.now())
    
    def _get_available_providers(self, platform: Platform) -> List[ProviderConfig]:
        """Get providers sorted by priority, excluding disabled ones."""
        now = datetime.now()
        providers = self.providers.get(platform, [])
        
        # Reset daily counters if needed
        for p in providers:
            if (now - p.last_reset).days >= 1:
                p.calls_today = 0
                p.last_reset = now
        
        available = [
            p for p in providers
            if (p.disabled_until is None or p.disabled_until < now)
            and p.calls_today < p.rate_limit
        ]
        return sorted(available, key=lambda p: p.priority)
    
    def _mark_error(self, provider: ProviderConfig):
        provider.error_count += 1
        provider.last_error = datetime.now()
        if provider.error_count >= 3:
            provider.disabled_until = datetime.now() + timedelta(minutes=5 * provider.error_count)
            logger.warning(f"Provider {provider.name} disabled until {provider.disabled_until}")
    
    def _mark_success(self, provider: ProviderConfig):
        provider.error_count = 0
        provider.disabled_until = None
        provider.calls_today += 1
    
    async def _call_api(
        self,
        provider: ProviderConfig,
        endpoint: str,
        params: Dict[str, Any],
        is_google: bool = False
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Make API call to a specific provider."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if is_google:
                    # Google API uses API key in params
                    params["key"] = self.youtube_api_key
                    url = f"https://{provider.host}{endpoint}"
                    headers = {}
                elif provider.host == "public.api.bsky.app":
                    # Bluesky public API - no auth needed
                    url = f"https://{provider.host}{endpoint}"
                    headers = {}
                else:
                    # RapidAPI
                    url = f"https://{provider.host}{endpoint}"
                    headers = {
                        "X-RapidAPI-Key": self.rapidapi_key,
                        "X-RapidAPI-Host": provider.host,
                    }
                
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    self._mark_success(provider)
                    return True, response.json(), None
                elif response.status_code == 429:
                    self._mark_error(provider)
                    return False, None, f"Rate limited: {response.status_code}"
                elif response.status_code in (500, 502, 503, 504):
                    self._mark_error(provider)
                    return False, None, f"Server error: {response.status_code}"
                else:
                    return False, None, f"Error {response.status_code}: {response.text[:100]}"
                    
        except httpx.TimeoutException:
            self._mark_error(provider)
            return False, None, "Timeout"
        except Exception as e:
            self._mark_error(provider)
            return False, None, str(e)
    
    async def fetch_with_failover(
        self,
        platform: Platform,
        data_type: DataType,
        identifier: str,
        params: Dict[str, Any]
    ) -> FetchResult:
        """Fetch data with automatic failover between providers."""
        
        # Check cache first
        cache_key = self._get_cache_key(platform, data_type, identifier)
        cached = self._get_cached(cache_key)
        if cached:
            return FetchResult(
                success=True,
                platform=platform,
                data_type=data_type,
                data=cached,
                cached=True
            )
        
        providers = self._get_available_providers(platform)
        if not providers:
            return FetchResult(
                success=False,
                platform=platform,
                data_type=data_type,
                error=f"No available providers for {platform.value}"
            )
        
        last_error = None
        for provider in providers:
            endpoint = provider.endpoints.get(data_type)
            if not endpoint:
                continue
            
            is_google = provider.host == "www.googleapis.com"
            success, data, error = await self._call_api(provider, endpoint, params, is_google)
            
            if success:
                self._set_cache(cache_key, data)
                return FetchResult(
                    success=True,
                    platform=platform,
                    data_type=data_type,
                    data=data,
                    provider_used=provider.name
                )
            
            last_error = error
            logger.warning(f"Provider {provider.name} failed: {error}")
        
        return FetchResult(
            success=False,
            platform=platform,
            data_type=data_type,
            error=f"All providers failed: {last_error}"
        )
    
    # =========================================================================
    # HIGH-LEVEL FETCH METHODS
    # =========================================================================
    
    async def fetch_profile(self, platform: Platform, username: str) -> FetchResult:
        """Fetch user profile with platform-specific params."""
        params = self._get_profile_params(platform, username)
        return await self.fetch_with_failover(platform, DataType.PROFILE, username, params)
    
    async def fetch_posts(self, platform: Platform, username: str, count: int = 20) -> FetchResult:
        """Fetch user's recent posts."""
        params = self._get_posts_params(platform, username, count)
        return await self.fetch_with_failover(platform, DataType.POSTS, username, params)
    
    async def fetch_post_metrics(self, platform: Platform, post_id: str) -> FetchResult:
        """Fetch metrics for a specific post."""
        params = self._get_post_metrics_params(platform, post_id)
        return await self.fetch_with_failover(platform, DataType.POST_METRICS, post_id, params)
    
    async def fetch_comments(self, platform: Platform, post_id: str, count: int = 50) -> FetchResult:
        """Fetch comments for a post."""
        params = self._get_comments_params(platform, post_id, count)
        return await self.fetch_with_failover(platform, DataType.COMMENTS, post_id, params)
    
    def _get_profile_params(self, platform: Platform, username: str) -> Dict:
        if platform == Platform.TIKTOK:
            return {"unique_id": username}
        elif platform == Platform.INSTAGRAM:
            return {"username": username}
        elif platform == Platform.YOUTUBE:
            if username.startswith("UC") and len(username) == 24:
                return {"part": "snippet,statistics", "id": username}
            return {"part": "snippet,statistics", "forHandle": username}
        elif platform == Platform.BLUESKY:
            handle = username if username.endswith(".bsky.social") else f"{username}.bsky.social"
            return {"actor": handle}
        return {"username": username}
    
    def _get_posts_params(self, platform: Platform, username: str, count: int) -> Dict:
        if platform == Platform.TIKTOK:
            return {"unique_id": username, "count": str(count)}
        elif platform == Platform.INSTAGRAM:
            return {"username": username}
        elif platform == Platform.YOUTUBE:
            return {"part": "snippet", "channelId": username, "type": "video", "maxResults": count}
        elif platform == Platform.BLUESKY:
            handle = username if username.endswith(".bsky.social") else f"{username}.bsky.social"
            return {"actor": handle, "limit": count}
        return {"username": username, "count": count}
    
    def _get_post_metrics_params(self, platform: Platform, post_id: str) -> Dict:
        if platform == Platform.TIKTOK:
            return {"aweme_id": post_id}
        elif platform == Platform.INSTAGRAM:
            return {"shortcode": post_id}
        elif platform == Platform.YOUTUBE:
            return {"part": "statistics,snippet,contentDetails", "id": post_id}
        return {"id": post_id}
    
    def _get_comments_params(self, platform: Platform, post_id: str, count: int) -> Dict:
        if platform == Platform.TIKTOK:
            return {"aweme_id": post_id, "count": str(count)}
        elif platform == Platform.YOUTUBE:
            return {"part": "snippet", "videoId": post_id, "maxResults": count}
        return {"id": post_id, "count": count}
    
    # =========================================================================
    # BATCH OPERATIONS (EFFICIENT)
    # =========================================================================
    
    async def batch_fetch_profiles(self, accounts: List[Tuple[Platform, str]]) -> List[FetchResult]:
        """Fetch multiple profiles efficiently."""
        tasks = [self.fetch_profile(platform, username) for platform, username in accounts]
        return await asyncio.gather(*tasks)
    
    async def batch_fetch_post_metrics(self, posts: List[Tuple[Platform, str]]) -> List[FetchResult]:
        """Fetch metrics for multiple posts efficiently."""
        tasks = [self.fetch_post_metrics(platform, post_id) for platform, post_id in posts]
        return await asyncio.gather(*tasks)
    
    async def refresh_all_accounts(self) -> Dict[str, Any]:
        """Refresh data for all connected accounts."""
        engine = create_engine(self.db_url)
        results = {"success": 0, "failed": 0, "errors": []}
        
        with engine.connect() as conn:
            accounts = conn.execute(text("""
                SELECT id, platform, username, external_account_id
                FROM social_media_accounts WHERE is_active = TRUE
            """)).fetchall()
            
            for account in accounts:
                account_id, platform_str, username, external_id = account
                
                try:
                    platform = Platform(platform_str)
                except ValueError:
                    continue
                
                # Use external_id if available (e.g., YouTube channel ID)
                identifier = external_id or username
                result = await self.fetch_profile(platform, identifier)
                
                if result.success:
                    # Update database with fetched data
                    parsed = self._parse_profile_data(platform, result.data)
                    if parsed:
                        conn.execute(text("""
                            UPDATE social_media_accounts SET
                                followers_count = :followers,
                                following_count = :following,
                                posts_count = :posts,
                                total_views = :views,
                                total_likes = :likes,
                                bio = :bio,
                                profile_pic_url = :avatar,
                                last_fetched_at = NOW()
                            WHERE id = :id
                        """), {
                            "id": account_id,
                            "followers": parsed.get("followers", 0),
                            "following": parsed.get("following", 0),
                            "posts": parsed.get("posts", 0),
                            "views": parsed.get("views", 0),
                            "likes": parsed.get("likes", 0),
                            "bio": parsed.get("bio", "")[:500],
                            "avatar": parsed.get("avatar", ""),
                        })
                        conn.commit()
                        results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{platform_str}/@{username}: {result.error}")
                
                # Small delay between requests
                await asyncio.sleep(0.5)
        
        return results
    
    def _parse_profile_data(self, platform: Platform, data: Dict) -> Optional[Dict]:
        """Parse profile data from different API formats."""
        try:
            if platform == Platform.TIKTOK:
                user = data.get("data", {}).get("user", {})
                stats = data.get("data", {}).get("stats", {})
                return {
                    "followers": stats.get("followerCount", 0),
                    "following": stats.get("followingCount", 0),
                    "posts": stats.get("videoCount", 0),
                    "likes": stats.get("heartCount", 0),
                    "views": 0,
                    "bio": user.get("signature", ""),
                    "avatar": user.get("avatarLarger", ""),
                }
            elif platform == Platform.INSTAGRAM:
                user = data.get("user", data)
                return {
                    "followers": user.get("edge_followed_by", {}).get("count", 0) or user.get("follower_count", 0),
                    "following": user.get("edge_follow", {}).get("count", 0) or user.get("following_count", 0),
                    "posts": user.get("edge_owner_to_timeline_media", {}).get("count", 0) or user.get("media_count", 0),
                    "likes": 0,
                    "views": 0,
                    "bio": user.get("biography", ""),
                    "avatar": user.get("profile_pic_url_hd", user.get("profile_pic_url", "")),
                }
            elif platform == Platform.YOUTUBE:
                if data.get("items"):
                    channel = data["items"][0]
                    stats = channel.get("statistics", {})
                    snippet = channel.get("snippet", {})
                    return {
                        "followers": int(stats.get("subscriberCount", 0)),
                        "following": 0,
                        "posts": int(stats.get("videoCount", 0)),
                        "views": int(stats.get("viewCount", 0)),
                        "likes": 0,
                        "bio": snippet.get("description", ""),
                        "avatar": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                    }
            elif platform == Platform.BLUESKY:
                return {
                    "followers": data.get("followersCount", 0),
                    "following": data.get("followsCount", 0),
                    "posts": data.get("postsCount", 0),
                    "likes": 0,
                    "views": 0,
                    "bio": data.get("description", ""),
                    "avatar": data.get("avatar", ""),
                }
        except Exception as e:
            logger.error(f"Error parsing {platform} profile: {e}")
        return None
    
    # =========================================================================
    # ENGAGEMENT DATA POPULATION
    # =========================================================================
    
    async def populate_engagement_data(self, platform: Platform, username: str) -> Dict:
        """
        Fetch all engagement data for an account and populate database.
        This is the main method to call for comprehensive data collection.
        """
        results = {
            "profile": None,
            "posts_fetched": 0,
            "comments_fetched": 0,
            "followers_updated": 0,
        }
        
        engine = create_engine(self.db_url)
        
        # 1. Fetch profile
        profile_result = await self.fetch_profile(platform, username)
        if profile_result.success:
            results["profile"] = self._parse_profile_data(platform, profile_result.data)
        
        # 2. Fetch recent posts
        posts_result = await self.fetch_posts(platform, username, count=30)
        if posts_result.success:
            posts = self._extract_posts(platform, posts_result.data)
            results["posts_fetched"] = len(posts)
            
            # 3. For each post, fetch comments and extract commenters
            commenters = {}
            for post in posts[:10]:  # Limit to 10 most recent to save API calls
                post_id = post.get("id")
                if post_id:
                    comments_result = await self.fetch_comments(platform, post_id, count=50)
                    if comments_result.success:
                        extracted = self._extract_commenters(platform, comments_result.data)
                        for c in extracted:
                            user_id = c.get("user_id")
                            if user_id:
                                if user_id in commenters:
                                    commenters[user_id]["comment_count"] += 1
                                    commenters[user_id]["like_count"] += c.get("likes", 0)
                                else:
                                    commenters[user_id] = c
                        results["comments_fetched"] += len(extracted)
                
                await asyncio.sleep(0.3)  # Rate limit protection
            
            # 4. Save commenters as engaged followers
            if commenters:
                with engine.connect() as conn:
                    for user_id, c in commenters.items():
                        score = c.get("comment_count", 1) * 10 + c.get("like_count", 0) * 2
                        tier = "super_fan" if score >= 30 else "active" if score >= 15 else "lurker"
                        
                        conn.execute(text("""
                            INSERT INTO top_engaged_followers 
                            (follower_id, platform, username, display_name, avatar_url,
                             engagement_score, engagement_tier, comment_count, like_count,
                             total_interactions, last_interaction, rank, platform_rank)
                            VALUES (:fid, :platform, :username, :display_name, :avatar,
                                    :score, :tier, :comments, :likes, :interactions, NOW(), 0, 0)
                            ON CONFLICT (platform, follower_id) DO UPDATE SET
                                comment_count = top_engaged_followers.comment_count + :comments,
                                like_count = top_engaged_followers.like_count + :likes,
                                engagement_score = top_engaged_followers.engagement_score + :score,
                                total_interactions = top_engaged_followers.total_interactions + :interactions,
                                last_interaction = NOW()
                        """), {
                            "fid": user_id,
                            "platform": platform.value,
                            "username": c.get("username", ""),
                            "display_name": c.get("display_name", c.get("username", "")),
                            "avatar": c.get("avatar", ""),
                            "score": score,
                            "tier": tier,
                            "comments": c.get("comment_count", 1),
                            "likes": c.get("like_count", 0),
                            "interactions": c.get("comment_count", 1) + c.get("like_count", 0),
                        })
                    conn.commit()
                    results["followers_updated"] = len(commenters)
        
        return results
    
    def _extract_posts(self, platform: Platform, data: Dict) -> List[Dict]:
        """Extract posts from API response."""
        try:
            if platform == Platform.TIKTOK:
                return data.get("data", {}).get("videos", [])
            elif platform == Platform.INSTAGRAM:
                edges = data.get("user", {}).get("edge_owner_to_timeline_media", {}).get("edges", [])
                return [e.get("node", {}) for e in edges]
            elif platform == Platform.YOUTUBE:
                return [{"id": item["id"]["videoId"]} for item in data.get("items", [])]
            elif platform == Platform.BLUESKY:
                return [{"id": p.get("post", {}).get("uri")} for p in data.get("feed", [])]
        except Exception as e:
            logger.error(f"Error extracting posts: {e}")
        return []
    
    def _extract_commenters(self, platform: Platform, data: Dict) -> List[Dict]:
        """Extract commenter data from comments response."""
        commenters = []
        try:
            if platform == Platform.TIKTOK:
                for c in data.get("data", {}).get("comments", []):
                    user = c.get("user", {})
                    commenters.append({
                        "user_id": user.get("uid"),
                        "username": user.get("unique_id"),
                        "display_name": user.get("nickname"),
                        "avatar": user.get("avatar_thumb", {}).get("url_list", [""])[0] if user.get("avatar_thumb") else "",
                        "likes": c.get("digg_count", 0),
                        "comment_count": 1,
                    })
            elif platform == Platform.YOUTUBE:
                for item in data.get("items", []):
                    snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    commenters.append({
                        "user_id": snippet.get("authorChannelId", {}).get("value", ""),
                        "username": snippet.get("authorDisplayName", ""),
                        "display_name": snippet.get("authorDisplayName", ""),
                        "avatar": snippet.get("authorProfileImageUrl", ""),
                        "likes": snippet.get("likeCount", 0),
                        "comment_count": 1,
                    })
        except Exception as e:
            logger.error(f"Error extracting commenters: {e}")
        return commenters
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers for monitoring."""
        status = {}
        for platform, providers in self.providers.items():
            status[platform.value] = []
            for p in providers:
                status[platform.value].append({
                    "name": p.name,
                    "priority": p.priority,
                    "calls_today": p.calls_today,
                    "rate_limit": p.rate_limit,
                    "error_count": p.error_count,
                    "disabled": p.disabled_until is not None and p.disabled_until > datetime.now(),
                    "disabled_until": str(p.disabled_until) if p.disabled_until else None,
                })
        return status


# Singleton instance
_orchestrator: Optional[PlatformDataOrchestrator] = None


def get_orchestrator() -> PlatformDataOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PlatformDataOrchestrator()
    return _orchestrator
