"""
RapidAPI Social Media Data Fetcher
Fetches real data from YouTube, Instagram, TikTok, Twitter, LinkedIn, Threads, Pinterest, Medium
Supports multiple accounts per platform
"""
import httpx
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    THREADS = "threads"
    PINTEREST = "pinterest"
    MEDIUM = "medium"


@dataclass
class SocialAccount:
    platform: Platform
    username: str
    account_id: Optional[str] = None
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    avatar_url: Optional[str] = None


@dataclass
class AccountAnalytics:
    platform: Platform
    username: str
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    engagement_rate: float = 0.0
    is_verified: bool = False
    bio: str = ""
    profile_pic_url: str = ""
    recent_posts: List[Dict] = None
    
    def __post_init__(self):
        if self.recent_posts is None:
            self.recent_posts = []


class RapidAPISocialFetcher:
    """
    Unified fetcher for social media data via RapidAPI
    """
    
    def __init__(self):
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.timeout = 30
        
        # RapidAPI endpoints for each platform
        self.api_configs = {
            Platform.YOUTUBE: {
                "host": "youtube-v31.p.rapidapi.com",
                "base_url": "https://youtube-v31.p.rapidapi.com",
            },
            Platform.INSTAGRAM: {
                "host": "instagram-scraper-api2.p.rapidapi.com",
                "base_url": "https://instagram-scraper-api2.p.rapidapi.com",
            },
            Platform.TIKTOK: {
                "host": "tiktok-scraper7.p.rapidapi.com",
                "base_url": "https://tiktok-scraper7.p.rapidapi.com",
            },
            Platform.TWITTER: {
                "host": "twitter241.p.rapidapi.com",
                "base_url": "https://twitter241.p.rapidapi.com",
            },
            Platform.LINKEDIN: {
                "host": "linkedin-data-api.p.rapidapi.com",
                "base_url": "https://linkedin-data-api.p.rapidapi.com",
            },
            Platform.THREADS: {
                "host": "threads-api4.p.rapidapi.com",
                "base_url": "https://threads-api4.p.rapidapi.com",
            },
            Platform.PINTEREST: {
                "host": "pinterest-scraper.p.rapidapi.com",
                "base_url": "https://pinterest-scraper.p.rapidapi.com",
            },
            Platform.MEDIUM: {
                "host": "medium2.p.rapidapi.com",
                "base_url": "https://medium2.p.rapidapi.com",
            },
        }
    
    def _get_headers(self, platform: Platform) -> Dict[str, str]:
        """Get headers for RapidAPI request"""
        config = self.api_configs.get(platform, {})
        return {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": config.get("host", ""),
        }
    
    async def fetch_youtube_analytics(self, channel_id: str) -> AccountAnalytics:
        """Fetch YouTube channel analytics using direct YouTube Data API"""
        youtube_api_key = os.getenv("YOUTUBE_API_KEY", "")
        
        # Try direct YouTube Data API v3 first (more reliable)
        if youtube_api_key:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        "https://www.googleapis.com/youtube/v3/channels",
                        params={
                            "part": "snippet,statistics",
                            "id": channel_id,
                            "key": youtube_api_key
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("items"):
                            channel = data["items"][0]
                            snippet = channel.get("snippet", {})
                            stats = channel.get("statistics", {})
                            
                            return AccountAnalytics(
                                platform=Platform.YOUTUBE,
                                username=snippet.get("customUrl", snippet.get("title", channel_id)),
                                followers_count=int(stats.get("subscriberCount", 0)),
                                posts_count=int(stats.get("videoCount", 0)),
                                total_views=int(stats.get("viewCount", 0)),
                                bio=snippet.get("description", "")[:500] if snippet.get("description") else "",
                                profile_pic_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                            )
                    
                    logger.warning(f"YouTube Data API returned {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error with YouTube Data API: {e}")
        
        # Fallback to RapidAPI
        try:
            config = self.api_configs[Platform.YOUTUBE]
            headers = self._get_headers(Platform.YOUTUBE)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{config['base_url']}/channels",
                    headers=headers,
                    params={
                        "part": "snippet,statistics",
                        "id": channel_id
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("items"):
                        channel = data["items"][0]
                        snippet = channel.get("snippet", {})
                        stats = channel.get("statistics", {})
                        
                        return AccountAnalytics(
                            platform=Platform.YOUTUBE,
                            username=snippet.get("customUrl", channel_id),
                            followers_count=int(stats.get("subscriberCount", 0)),
                            posts_count=int(stats.get("videoCount", 0)),
                            total_views=int(stats.get("viewCount", 0)),
                            bio=snippet.get("description", ""),
                            profile_pic_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                        )
                
                logger.warning(f"YouTube RapidAPI returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching YouTube analytics: {e}")
        
        return AccountAnalytics(platform=Platform.YOUTUBE, username=channel_id)
    
    async def fetch_instagram_analytics(self, username: str) -> AccountAnalytics:
        """Fetch Instagram profile analytics"""
        try:
            config = self.api_configs[Platform.INSTAGRAM]
            headers = self._get_headers(Platform.INSTAGRAM)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{config['base_url']}/v1/info",
                    headers=headers,
                    params={"username_or_id_or_url": username}
                )
                
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    
                    return AccountAnalytics(
                        platform=Platform.INSTAGRAM,
                        username=data.get("username", username),
                        followers_count=data.get("follower_count", 0),
                        following_count=data.get("following_count", 0),
                        posts_count=data.get("media_count", 0),
                        is_verified=data.get("is_verified", False),
                        bio=data.get("biography", ""),
                        profile_pic_url=data.get("profile_pic_url_hd", ""),
                    )
                
                logger.warning(f"Instagram API returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching Instagram analytics: {e}")
        
        return AccountAnalytics(platform=Platform.INSTAGRAM, username=username)
    
    async def fetch_tiktok_analytics(self, username: str) -> AccountAnalytics:
        """Fetch TikTok profile analytics"""
        try:
            config = self.api_configs[Platform.TIKTOK]
            headers = self._get_headers(Platform.TIKTOK)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{config['base_url']}/user/info",
                    headers=headers,
                    params={"unique_id": username}
                )
                
                if response.status_code == 200:
                    data = response.json().get("data", {}).get("user", {})
                    stats = response.json().get("data", {}).get("stats", {})
                    
                    return AccountAnalytics(
                        platform=Platform.TIKTOK,
                        username=data.get("uniqueId", username),
                        followers_count=stats.get("followerCount", 0),
                        following_count=stats.get("followingCount", 0),
                        posts_count=stats.get("videoCount", 0),
                        total_likes=stats.get("heartCount", 0),
                        is_verified=data.get("verified", False),
                        bio=data.get("signature", ""),
                        profile_pic_url=data.get("avatarLarger", ""),
                    )
                
                logger.warning(f"TikTok API returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching TikTok analytics: {e}")
        
        return AccountAnalytics(platform=Platform.TIKTOK, username=username)
    
    async def fetch_twitter_analytics(self, username: str) -> AccountAnalytics:
        """Fetch Twitter/X profile analytics"""
        try:
            config = self.api_configs[Platform.TWITTER]
            headers = self._get_headers(Platform.TWITTER)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{config['base_url']}/user",
                    headers=headers,
                    params={"username": username}
                )
                
                if response.status_code == 200:
                    data = response.json().get("result", {}).get("data", {}).get("user", {}).get("result", {})
                    legacy = data.get("legacy", {})
                    
                    return AccountAnalytics(
                        platform=Platform.TWITTER,
                        username=legacy.get("screen_name", username),
                        followers_count=legacy.get("followers_count", 0),
                        following_count=legacy.get("friends_count", 0),
                        posts_count=legacy.get("statuses_count", 0),
                        total_likes=legacy.get("favourites_count", 0),
                        is_verified=legacy.get("verified", False),
                        bio=legacy.get("description", ""),
                        profile_pic_url=legacy.get("profile_image_url_https", "").replace("_normal", ""),
                    )
                
                logger.warning(f"Twitter API returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching Twitter analytics: {e}")
        
        return AccountAnalytics(platform=Platform.TWITTER, username=username)
    
    async def fetch_linkedin_analytics(self, profile_url: str) -> AccountAnalytics:
        """Fetch LinkedIn profile analytics"""
        try:
            config = self.api_configs[Platform.LINKEDIN]
            headers = self._get_headers(Platform.LINKEDIN)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{config['base_url']}/get-profile-data-by-url",
                    headers=headers,
                    params={"url": profile_url}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return AccountAnalytics(
                        platform=Platform.LINKEDIN,
                        username=data.get("username", profile_url),
                        followers_count=data.get("followerCount", 0),
                        posts_count=data.get("postsCount", 0),
                        bio=data.get("headline", ""),
                        profile_pic_url=data.get("profilePicture", ""),
                    )
                
                logger.warning(f"LinkedIn API returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching LinkedIn analytics: {e}")
        
        return AccountAnalytics(platform=Platform.LINKEDIN, username=profile_url)
    
    async def fetch_threads_analytics(self, username: str) -> AccountAnalytics:
        """Fetch Threads profile analytics"""
        try:
            config = self.api_configs[Platform.THREADS]
            headers = self._get_headers(Platform.THREADS)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{config['base_url']}/user/info",
                    headers=headers,
                    params={"username": username}
                )
                
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    
                    return AccountAnalytics(
                        platform=Platform.THREADS,
                        username=data.get("username", username),
                        followers_count=data.get("follower_count", 0),
                        posts_count=data.get("thread_count", 0),
                        is_verified=data.get("is_verified", False),
                        bio=data.get("biography", ""),
                        profile_pic_url=data.get("profile_pic_url", ""),
                    )
                
                logger.warning(f"Threads API returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching Threads analytics: {e}")
        
        return AccountAnalytics(platform=Platform.THREADS, username=username)
    
    async def fetch_pinterest_analytics(self, username: str) -> AccountAnalytics:
        """Fetch Pinterest profile analytics"""
        try:
            config = self.api_configs[Platform.PINTEREST]
            headers = self._get_headers(Platform.PINTEREST)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{config['base_url']}/user/profile",
                    headers=headers,
                    params={"username": username}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return AccountAnalytics(
                        platform=Platform.PINTEREST,
                        username=data.get("username", username),
                        followers_count=data.get("follower_count", 0),
                        following_count=data.get("following_count", 0),
                        posts_count=data.get("pin_count", 0),
                        bio=data.get("about", ""),
                        profile_pic_url=data.get("image_url", ""),
                    )
                
                logger.warning(f"Pinterest API returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching Pinterest analytics: {e}")
        
        return AccountAnalytics(platform=Platform.PINTEREST, username=username)
    
    async def fetch_medium_analytics(self, username: str) -> AccountAnalytics:
        """Fetch Medium profile analytics"""
        try:
            config = self.api_configs[Platform.MEDIUM]
            headers = self._get_headers(Platform.MEDIUM)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{config['base_url']}/user/{username}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return AccountAnalytics(
                        platform=Platform.MEDIUM,
                        username=data.get("username", username),
                        followers_count=data.get("followers_count", 0),
                        following_count=data.get("following_count", 0),
                        bio=data.get("bio", ""),
                        profile_pic_url=data.get("image_url", ""),
                    )
                
                logger.warning(f"Medium API returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching Medium analytics: {e}")
        
        return AccountAnalytics(platform=Platform.MEDIUM, username=username)
    
    async def fetch_all_accounts(self, accounts: List[SocialAccount]) -> List[AccountAnalytics]:
        """
        Fetch analytics for all provided accounts
        Supports multiple accounts per platform
        """
        results = []
        
        for account in accounts:
            try:
                if account.platform == Platform.YOUTUBE:
                    analytics = await self.fetch_youtube_analytics(account.account_id or account.username)
                elif account.platform == Platform.INSTAGRAM:
                    analytics = await self.fetch_instagram_analytics(account.username)
                elif account.platform == Platform.TIKTOK:
                    analytics = await self.fetch_tiktok_analytics(account.username)
                elif account.platform == Platform.TWITTER:
                    analytics = await self.fetch_twitter_analytics(account.username)
                elif account.platform == Platform.LINKEDIN:
                    analytics = await self.fetch_linkedin_analytics(account.profile_url or account.username)
                elif account.platform == Platform.THREADS:
                    analytics = await self.fetch_threads_analytics(account.username)
                elif account.platform == Platform.PINTEREST:
                    analytics = await self.fetch_pinterest_analytics(account.username)
                elif account.platform == Platform.MEDIUM:
                    analytics = await self.fetch_medium_analytics(account.username)
                else:
                    continue
                
                results.append(analytics)
                logger.info(f"Fetched analytics for {account.platform.value}/@{account.username}")
                
            except Exception as e:
                logger.error(f"Error fetching {account.platform.value}/@{account.username}: {e}")
                # Add empty analytics on error
                results.append(AccountAnalytics(
                    platform=account.platform,
                    username=account.username
                ))
        
        return results
    
    def analytics_to_dict(self, analytics: AccountAnalytics) -> Dict[str, Any]:
        """Convert AccountAnalytics to dictionary"""
        return {
            "platform": analytics.platform.value,
            "username": analytics.username,
            "followers_count": analytics.followers_count,
            "following_count": analytics.following_count,
            "posts_count": analytics.posts_count,
            "total_views": analytics.total_views,
            "total_likes": analytics.total_likes,
            "total_comments": analytics.total_comments,
            "total_shares": analytics.total_shares,
            "engagement_rate": analytics.engagement_rate,
            "is_verified": analytics.is_verified,
            "bio": analytics.bio,
            "profile_pic_url": analytics.profile_pic_url,
            "recent_posts": analytics.recent_posts,
        }


# Singleton instance
_fetcher: Optional[RapidAPISocialFetcher] = None


def get_social_fetcher() -> RapidAPISocialFetcher:
    """Get or create social fetcher instance"""
    global _fetcher
    if _fetcher is None:
        _fetcher = RapidAPISocialFetcher()
    return _fetcher
