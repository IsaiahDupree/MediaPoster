"""
YouTube Analytics Service
Fetches channel and video metrics using YouTube Data API v3
Uses the API key from environment (YOUTUBE_API_KEY)
"""
import os
import logging
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class YouTubeVideoMetrics(BaseModel):
    """Metrics for a single YouTube video"""
    video_id: str
    title: str
    description: str
    published_at: str
    channel_id: str
    channel_title: str
    thumbnail_url: Optional[str] = None
    duration_seconds: int = 0
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    favorite_count: int = 0
    tags: List[str] = []
    is_short: bool = False


class YouTubeChannelMetrics(BaseModel):
    """Metrics for a YouTube channel"""
    channel_id: str
    title: str
    description: str
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: int = 0
    video_count: int = 0
    view_count: int = 0
    country: Optional[str] = None
    published_at: Optional[str] = None


class YouTubeAnalyticsService:
    """
    Service for fetching YouTube analytics using YouTube Data API v3
    
    Requires YOUTUBE_API_KEY in environment
    Free tier: 10,000 units/day
    - videos.list: 1 unit per request (up to 50 videos)
    - channels.list: 1 unit per request
    - search.list: 100 units per request
    """
    
    API_BASE = "https://www.googleapis.com/youtube/v3"
    
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.channel_id = os.getenv("YOUTUBE_CHANNEL_ID")
        
        if not self.api_key:
            logger.warning("YOUTUBE_API_KEY not set - YouTube analytics will not work")
    
    def _parse_duration(self, duration_iso: str) -> int:
        """Parse ISO 8601 duration (PT1H2M30S) to seconds"""
        import re
        if not duration_iso:
            return 0
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds
    
    async def get_channel_metrics(self, channel_id: Optional[str] = None) -> Optional[YouTubeChannelMetrics]:
        """
        Fetch metrics for a YouTube channel
        
        Args:
            channel_id: YouTube channel ID (uses env var if not provided)
            
        Returns:
            YouTubeChannelMetrics or None if error
        """
        if not self.api_key:
            logger.error("YOUTUBE_API_KEY not configured")
            return None
        
        channel_id = channel_id or self.channel_id
        if not channel_id:
            logger.error("No channel_id provided and YOUTUBE_CHANNEL_ID not set")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.API_BASE}/channels",
                    params={
                        "part": "snippet,statistics,brandingSettings",
                        "id": channel_id,
                        "key": self.api_key,
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                    return None
                
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    logger.warning(f"Channel not found: {channel_id}")
                    return None
                
                channel = items[0]
                snippet = channel.get("snippet", {})
                stats = channel.get("statistics", {})
                
                return YouTubeChannelMetrics(
                    channel_id=channel_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", "")[:500],
                    custom_url=snippet.get("customUrl"),
                    thumbnail_url=snippet.get("thumbnails", {}).get("default", {}).get("url"),
                    subscriber_count=int(stats.get("subscriberCount", 0)),
                    video_count=int(stats.get("videoCount", 0)),
                    view_count=int(stats.get("viewCount", 0)),
                    country=snippet.get("country"),
                    published_at=snippet.get("publishedAt"),
                )
                
        except Exception as e:
            logger.error(f"Error fetching channel metrics: {e}")
            return None
    
    async def get_video_metrics(self, video_id: str) -> Optional[YouTubeVideoMetrics]:
        """
        Fetch metrics for a single YouTube video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            YouTubeVideoMetrics or None if error
        """
        if not self.api_key:
            logger.error("YOUTUBE_API_KEY not configured")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.API_BASE}/videos",
                    params={
                        "part": "snippet,statistics,contentDetails",
                        "id": video_id,
                        "key": self.api_key,
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                    return None
                
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    logger.warning(f"Video not found: {video_id}")
                    return None
                
                video = items[0]
                snippet = video.get("snippet", {})
                stats = video.get("statistics", {})
                content = video.get("contentDetails", {})
                
                duration = self._parse_duration(content.get("duration", "PT0S"))
                
                return YouTubeVideoMetrics(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", "")[:500],
                    published_at=snippet.get("publishedAt", ""),
                    channel_id=snippet.get("channelId", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    thumbnail_url=snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                    duration_seconds=duration,
                    view_count=int(stats.get("viewCount", 0)),
                    like_count=int(stats.get("likeCount", 0)),
                    comment_count=int(stats.get("commentCount", 0)),
                    favorite_count=int(stats.get("favoriteCount", 0)),
                    tags=snippet.get("tags", [])[:10],
                    is_short=duration <= 60,
                )
                
        except Exception as e:
            logger.error(f"Error fetching video metrics: {e}")
            return None
    
    async def get_channel_videos(
        self, 
        channel_id: Optional[str] = None,
        max_results: int = 50,
        order: str = "date"
    ) -> List[YouTubeVideoMetrics]:
        """
        Fetch all videos from a YouTube channel with their metrics
        
        Args:
            channel_id: YouTube channel ID (uses env var if not provided)
            max_results: Maximum number of videos to fetch (default 50)
            order: Sort order - 'date', 'viewCount', 'rating' (default 'date')
            
        Returns:
            List of YouTubeVideoMetrics
        """
        if not self.api_key:
            logger.error("YOUTUBE_API_KEY not configured")
            return []
        
        channel_id = channel_id or self.channel_id
        if not channel_id:
            logger.error("No channel_id provided and YOUTUBE_CHANNEL_ID not set")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # First, search for videos from the channel
                # Note: search.list costs 100 units, so we limit usage
                search_response = await client.get(
                    f"{self.API_BASE}/search",
                    params={
                        "part": "id",
                        "channelId": channel_id,
                        "type": "video",
                        "order": order,
                        "maxResults": min(max_results, 50),
                        "key": self.api_key,
                    }
                )
                
                if search_response.status_code != 200:
                    logger.error(f"YouTube search API error: {search_response.status_code}")
                    return []
                
                search_data = search_response.json()
                video_ids = [item["id"]["videoId"] for item in search_data.get("items", [])]
                
                if not video_ids:
                    logger.info(f"No videos found for channel: {channel_id}")
                    return []
                
                # Fetch detailed metrics for all videos in one request
                # videos.list costs 1 unit and can fetch up to 50 videos
                videos_response = await client.get(
                    f"{self.API_BASE}/videos",
                    params={
                        "part": "snippet,statistics,contentDetails",
                        "id": ",".join(video_ids),
                        "key": self.api_key,
                    }
                )
                
                if videos_response.status_code != 200:
                    logger.error(f"YouTube videos API error: {videos_response.status_code}")
                    return []
                
                videos_data = videos_response.json()
                videos = []
                
                for video in videos_data.get("items", []):
                    snippet = video.get("snippet", {})
                    stats = video.get("statistics", {})
                    content = video.get("contentDetails", {})
                    
                    duration = self._parse_duration(content.get("duration", "PT0S"))
                    
                    videos.append(YouTubeVideoMetrics(
                        video_id=video["id"],
                        title=snippet.get("title", ""),
                        description=snippet.get("description", "")[:500],
                        published_at=snippet.get("publishedAt", ""),
                        channel_id=snippet.get("channelId", ""),
                        channel_title=snippet.get("channelTitle", ""),
                        thumbnail_url=snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                        duration_seconds=duration,
                        view_count=int(stats.get("viewCount", 0)),
                        like_count=int(stats.get("likeCount", 0)),
                        comment_count=int(stats.get("commentCount", 0)),
                        favorite_count=int(stats.get("favoriteCount", 0)),
                        tags=snippet.get("tags", [])[:10],
                        is_short=duration <= 60,
                    ))
                
                logger.info(f"✓ Fetched {len(videos)} videos from YouTube channel {channel_id}")
                return videos
                
        except Exception as e:
            logger.error(f"Error fetching channel videos: {e}")
            return []
    
    async def get_all_metrics_summary(self, channel_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a complete summary of YouTube metrics for a channel
        
        Returns:
            Dict with channel info, video list, and aggregated stats
        """
        channel_id = channel_id or self.channel_id
        
        # Fetch channel and videos in parallel
        channel_metrics = await self.get_channel_metrics(channel_id)
        videos = await self.get_channel_videos(channel_id, max_results=50)
        
        # Calculate aggregated stats from videos
        total_views = sum(v.view_count for v in videos)
        total_likes = sum(v.like_count for v in videos)
        total_comments = sum(v.comment_count for v in videos)
        shorts_count = sum(1 for v in videos if v.is_short)
        
        return {
            "channel": channel_metrics.model_dump() if channel_metrics else None,
            "videos": [v.model_dump() for v in videos],
            "summary": {
                "total_videos_fetched": len(videos),
                "total_views": total_views,
                "total_likes": total_likes,
                "total_comments": total_comments,
                "shorts_count": shorts_count,
                "regular_videos_count": len(videos) - shorts_count,
                "avg_views_per_video": total_views // len(videos) if videos else 0,
                "avg_likes_per_video": total_likes // len(videos) if videos else 0,
            },
            "fetched_at": datetime.now().isoformat(),
        }


# Singleton instance
_youtube_service: Optional[YouTubeAnalyticsService] = None


def get_youtube_analytics_service() -> YouTubeAnalyticsService:
    """Get singleton instance of YouTubeAnalyticsService"""
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeAnalyticsService()
    return _youtube_service
