"""
Platform-specific analytics collectors
Fetch engagement metrics from each platform via their real APIs.

NOMOCK-008: Real API implementations for YouTube, TikTok, Instagram, Twitter.
"""

import os
import re
from typing import Dict, Any, Optional, List
from loguru import logger
import httpx


class BaseAnalyticsCollector:
    """Base class for platform analytics"""

    def get_video_stats(self, url: str) -> Optional[Dict[str, Any]]:
        """Get video statistics"""
        raise NotImplementedError

    def get_comments(self, url: str, max_results: int = 100) -> list:
        """Get comments"""
        raise NotImplementedError


class YouTubeAnalytics(BaseAnalyticsCollector):
    """
    YouTube analytics collector using YouTube Data API v3.

    Requires: YOUTUBE_API_KEY environment variable.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.base_url = "https://www.googleapis.com/youtube/v3"
        if not self.api_key:
            logger.warning("YOUTUBE_API_KEY not set; YouTube analytics will fail on API calls")
        else:
            logger.info("YouTube Analytics initialized with API key")

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
            r"(?:embed/|shorts/)([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_stats(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get YouTube video statistics via Data API v3.

        Endpoint: youtube.videos().list(part="statistics,snippet")
        """
        if not self.api_key:
            raise RuntimeError("YOUTUBE_API_KEY not configured")

        video_id = self._extract_video_id(url)
        if not video_id:
            logger.error(f"Could not extract video ID from URL: {url}")
            return None

        params = {
            "part": "statistics,snippet",
            "id": video_id,
            "key": self.api_key,
        }

        with httpx.Client(timeout=15) as client:
            response = client.get(f"{self.base_url}/videos", params=params)
            response.raise_for_status()
            data = response.json()

        items = data.get("items", [])
        if not items:
            logger.warning(f"No data found for video ID {video_id}")
            return None

        item = items[0]
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})

        return {
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments_count": int(stats.get("commentCount", 0)),
            "favorites": int(stats.get("favoriteCount", 0)),
            "title": snippet.get("title", ""),
            "published_at": snippet.get("publishedAt", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "video_id": video_id,
        }

    def get_comments(self, url: str, max_results: int = 100) -> list:
        """
        Get YouTube comments via commentThreads().list().

        Endpoint: youtube/v3/commentThreads
        """
        if not self.api_key:
            raise RuntimeError("YOUTUBE_API_KEY not configured")

        video_id = self._extract_video_id(url)
        if not video_id:
            return []

        params = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": min(max_results, 100),
            "order": "relevance",
            "key": self.api_key,
        }

        comments = []
        with httpx.Client(timeout=15) as client:
            response = client.get(f"{self.base_url}/commentThreads", params=params)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                comments.append({
                    "author": top.get("authorDisplayName", ""),
                    "text": top.get("textDisplay", ""),
                    "likes": top.get("likeCount", 0),
                    "published_at": top.get("publishedAt", ""),
                    "reply_count": item.get("snippet", {}).get("totalReplyCount", 0),
                })

        return comments


class TikTokAnalytics(BaseAnalyticsCollector):
    """
    TikTok analytics collector.

    Note: TikTok's Research API requires special access approval.
    The Display API and Content Posting API have limited analytics.
    Stats collection uses the TikTok Display API where available;
    full analytics require approved Research API access.
    """

    def __init__(self):
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
        self.base_url = "https://open.tiktokapis.com/v2"
        if not self.access_token:
            logger.warning(
                "TIKTOK_ACCESS_TOKEN not set; TikTok analytics require API access approval. "
                "See https://developers.tiktok.com/doc/research-api-get-started"
            )
        else:
            logger.info("TikTok Analytics initialized with access token")

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract TikTok video ID from URL."""
        match = re.search(r"/video/(\d+)", url)
        return match.group(1) if match else None

    def get_video_stats(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get TikTok video statistics.

        Uses TikTok Display API: GET /v2/video/query/
        Requires approved app with video.list scope.
        """
        if not self.access_token:
            raise RuntimeError(
                "TIKTOK_ACCESS_TOKEN not configured. "
                "TikTok API access requires developer application approval. "
                "Apply at https://developers.tiktok.com"
            )

        video_id = self._extract_video_id(url)
        if not video_id:
            logger.error(f"Could not extract TikTok video ID from URL: {url}")
            return None

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "filters": {"video_ids": [video_id]},
            "fields": ["id", "title", "like_count", "comment_count", "share_count", "view_count"],
        }

        with httpx.Client(timeout=15) as client:
            response = client.post(
                f"{self.base_url}/video/query/",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        videos = data.get("data", {}).get("videos", [])
        if not videos:
            return None

        video = videos[0]
        return {
            "views": video.get("view_count", 0),
            "likes": video.get("like_count", 0),
            "comments_count": video.get("comment_count", 0),
            "shares": video.get("share_count", 0),
            "title": video.get("title", ""),
            "video_id": video_id,
        }

    def get_comments(self, url: str, max_results: int = 100) -> list:
        """
        Get TikTok comments.

        Note: TikTok comment API access requires Research API approval.
        """
        if not self.access_token:
            raise RuntimeError(
                "TIKTOK_ACCESS_TOKEN not configured. "
                "TikTok comment access requires Research API approval."
            )

        video_id = self._extract_video_id(url)
        if not video_id:
            return []

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "video_id": video_id,
            "max_count": min(max_results, 100),
        }

        with httpx.Client(timeout=15) as client:
            response = client.post(
                f"{self.base_url}/comment/list/",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        comments = []
        for item in data.get("data", {}).get("comments", []):
            comments.append({
                "author": item.get("user", {}).get("display_name", ""),
                "text": item.get("text", ""),
                "likes": item.get("like_count", 0),
                "published_at": item.get("create_time", ""),
            })

        return comments


class InstagramAnalytics(BaseAnalyticsCollector):
    """
    Instagram analytics collector using Instagram Graph API.

    Requires: META_ACCESS_TOKEN and INSTAGRAM_USER_ID environment variables.
    """

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("META_ACCESS_TOKEN")
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        if not self.access_token:
            logger.warning("META_ACCESS_TOKEN not set; Instagram analytics will fail on API calls")
        else:
            logger.info("Instagram Analytics initialized with Graph API token")

    def _extract_media_id(self, post_url: str) -> Optional[str]:
        """Extract media shortcode from Instagram URL (requires API lookup)."""
        match = re.search(r"instagram\.com/(?:p|reel|reels)/([A-Za-z0-9_-]+)", post_url)
        return match.group(1) if match else None

    def get_reel_stats(self, post_url: str) -> Optional[Dict[str, Any]]:
        """
        Get Instagram Reel/Post statistics via Graph API.

        Endpoint: GET /{media-id}?fields=like_count,comments_count,insights.metric(...)
        Note: Requires the media ID, not the shortcode. For shortcode lookup,
        use the oembed endpoint first.
        """
        if not self.access_token:
            raise RuntimeError("META_ACCESS_TOKEN not configured for Instagram analytics")

        shortcode = self._extract_media_id(post_url)
        if not shortcode:
            logger.error(f"Could not extract media shortcode from URL: {post_url}")
            return None

        # Use oEmbed to get media info from shortcode
        with httpx.Client(timeout=15) as client:
            # Get media ID from shortcode via Graph API search
            params = {
                "fields": "id,like_count,comments_count,media_type,permalink,timestamp",
                "access_token": self.access_token,
            }

            # For business/creator accounts, use the media endpoint with the media ID
            # The shortcode needs to be resolved via the account's media list
            ig_user_id = os.getenv("INSTAGRAM_USER_ID")
            if ig_user_id:
                # Search recent media for matching shortcode
                media_params = {
                    "fields": "id,shortcode,like_count,comments_count,media_type,permalink,timestamp",
                    "limit": "50",
                    "access_token": self.access_token,
                }
                response = client.get(
                    f"{self.base_url}/{ig_user_id}/media",
                    params=media_params,
                )
                response.raise_for_status()
                media_list = response.json().get("data", [])

                target_media = None
                for media in media_list:
                    if media.get("shortcode") == shortcode or shortcode in media.get("permalink", ""):
                        target_media = media
                        break

                if not target_media:
                    logger.warning(f"Media with shortcode {shortcode} not found in recent posts")
                    return None

                return {
                    "views": 0,  # Views require insights endpoint
                    "likes": target_media.get("like_count", 0),
                    "comments_count": target_media.get("comments_count", 0),
                    "media_type": target_media.get("media_type", ""),
                    "permalink": target_media.get("permalink", ""),
                    "published_at": target_media.get("timestamp", ""),
                    "media_id": target_media.get("id", ""),
                }

        return None

    # Alias for consistent interface
    get_video_stats = get_reel_stats

    def get_comments(self, post_url: str, max_results: int = 100) -> list:
        """
        Get Instagram comments via Graph API.

        Endpoint: GET /{media-id}/comments?fields=text,username,timestamp,like_count
        """
        if not self.access_token:
            raise RuntimeError("META_ACCESS_TOKEN not configured for Instagram analytics")

        # First get the media stats to find the media_id
        stats = self.get_reel_stats(post_url)
        if not stats or not stats.get("media_id"):
            return []

        media_id = stats["media_id"]

        params = {
            "fields": "text,username,timestamp,like_count",
            "limit": str(min(max_results, 100)),
            "access_token": self.access_token,
        }

        with httpx.Client(timeout=15) as client:
            response = client.get(
                f"{self.base_url}/{media_id}/comments",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        comments = []
        for item in data.get("data", []):
            comments.append({
                "author": item.get("username", ""),
                "text": item.get("text", ""),
                "likes": item.get("like_count", 0),
                "published_at": item.get("timestamp", ""),
            })

        return comments


class TwitterAnalytics(BaseAnalyticsCollector):
    """
    Twitter/X analytics collector using Twitter API v2.

    Requires: TWITTER_BEARER_TOKEN environment variable.
    """

    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        self.base_url = "https://api.twitter.com/2"
        if not self.bearer_token:
            logger.warning("TWITTER_BEARER_TOKEN not set; Twitter analytics will fail on API calls")
        else:
            logger.info("Twitter Analytics initialized with bearer token")

    def _extract_tweet_id(self, url: str) -> Optional[str]:
        """Extract tweet ID from Twitter/X URL."""
        match = re.search(r"(?:twitter|x)\.com/.+/status/(\d+)", url)
        return match.group(1) if match else None

    def get_tweet_stats(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get Tweet statistics via Twitter API v2.

        Endpoint: GET /tweets?ids={id}&tweet.fields=public_metrics
        """
        if not self.bearer_token:
            raise RuntimeError("TWITTER_BEARER_TOKEN not configured for Twitter analytics")

        tweet_id = self._extract_tweet_id(url)
        if not tweet_id:
            logger.error(f"Could not extract tweet ID from URL: {url}")
            return None

        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params = {
            "ids": tweet_id,
            "tweet.fields": "public_metrics,created_at,author_id,text",
        }

        with httpx.Client(timeout=15) as client:
            response = client.get(f"{self.base_url}/tweets", headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        tweets = data.get("data", [])
        if not tweets:
            return None

        tweet = tweets[0]
        metrics = tweet.get("public_metrics", {})

        return {
            "views": metrics.get("impression_count", 0),
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "bookmarks": metrics.get("bookmark_count", 0),
            "text": tweet.get("text", ""),
            "published_at": tweet.get("created_at", ""),
            "tweet_id": tweet_id,
        }

    # Alias for consistent interface
    get_video_stats = get_tweet_stats

    def get_comments(self, url: str, max_results: int = 100) -> list:
        """
        Get Tweet replies (comments) via Twitter API v2 search.

        Endpoint: GET /tweets/search/recent?query=conversation_id:{tweet_id}
        """
        if not self.bearer_token:
            raise RuntimeError("TWITTER_BEARER_TOKEN not configured for Twitter analytics")

        tweet_id = self._extract_tweet_id(url)
        if not tweet_id:
            return []

        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params = {
            "query": f"conversation_id:{tweet_id}",
            "tweet.fields": "author_id,created_at,public_metrics,text",
            "max_results": str(min(max_results, 100)),
        }

        with httpx.Client(timeout=15) as client:
            response = client.get(
                f"{self.base_url}/tweets/search/recent",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        comments = []
        for tweet in data.get("data", []):
            pm = tweet.get("public_metrics", {})
            comments.append({
                "author": tweet.get("author_id", ""),
                "text": tweet.get("text", ""),
                "likes": pm.get("like_count", 0),
                "published_at": tweet.get("created_at", ""),
                "retweets": pm.get("retweet_count", 0),
            })

        return comments


# Factory function
def get_analytics_collector(platform: str):
    """
    Get the appropriate analytics collector for a platform.

    Args:
        platform: Platform name (youtube, tiktok, instagram, twitter)

    Returns:
        Analytics collector instance

    Raises:
        ValueError: If platform is not supported
    """
    collectors = {
        "youtube": YouTubeAnalytics,
        "tiktok": TikTokAnalytics,
        "instagram": InstagramAnalytics,
        "twitter": TwitterAnalytics,
    }

    collector_class = collectors.get(platform.lower())

    if not collector_class:
        raise ValueError(f"Unsupported analytics platform: {platform}. Supported: {list(collectors.keys())}")

    return collector_class()
