"""
TikTok Scraper Integration (RapidAPI)
Enables trending content discovery, hashtag analysis, and competitive research
"""
import logging
import os
from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class TikTokScraperAPI:
    """
    Integration with TikTok Scraper API from RapidAPI
    https://rapidapi.com/tikwm-tikwm-default/api/tiktok-scraper7
    
    Provides:
    - Trending content discovery
    - Hashtag analysis
    - User/creator insights
    - Video metadata retrieval
    - Comment extraction
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize TikTok Scraper API client
        
        Args:
            api_key: RapidAPI key (defaults to RAPIDAPI_KEY env var)
        """
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        self.base_url = "https://tiktok-scraper7.p.rapidapi.com"
        
        if not self.api_key:
            logger.warning("RAPIDAPI_KEY not configured - TikTok Scraper disabled")
        
        self.headers = {
            "X-RapidAPI-Key": self.api_key or "",
            "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
        }
    
    async def get_trending_feed(
        self,
        region: str = "US",
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get trending TikTok videos
        
        Args:
            region: Region code (US, GB, etc.)
            count: Number of videos to fetch
            
        Returns:
            List of trending video data
        """
        if not self.api_key:
            return []
        
        url = f"{self.base_url}/feed/trending"
        params = {
            "region": region,
            "count": count
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Parse and normalize response
                videos = []
                for item in data.get("data", {}).get("itemList", []):
                    videos.append(self._parse_video(item))
                
                logger.info(f"Fetched {len(videos)} trending videos")
                return videos
                
        except Exception as e:
            logger.error(f"Error fetching trending feed: {e}")
            return []
    
    async def search_hashtag(
        self,
        hashtag: str,
        count: int = 20,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search videos by hashtag
        
        Args:
            hashtag: Hashtag to search (without #)
            count: Number of results
            cursor: Pagination cursor
            
        Returns:
            Dict with videos and pagination info
        """
        if not self.api_key:
            return {"videos": [], "cursor": None}
        
        url = f"{self.base_url}/hashtag/posts"
        params = {
            "hashtag": hashtag.lstrip("#"),
            "count": count
        }
        
        if cursor:
            params["cursor"] = cursor
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                videos = []
                for item in data.get("data", {}).get("itemList", []):
                    videos.append(self._parse_video(item))
                
                return {
                    "videos": videos,
                    "cursor": data.get("data", {}).get("cursor"),
                    "has_more": data.get("data", {}).get("hasMore", False)
                }
                
        except Exception as e:
            logger.error(f"Error searching hashtag {hashtag}: {e}")
            return {"videos": [], "cursor": None}
    
    async def get_video_info(
        self,
        video_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific video
        
        Args:
            video_id: TikTok video ID or URL
            
        Returns:
            Video metadata
        """
        if not self.api_key:
            return None
        
        url = f"{self.base_url}/video/info"
        params = {"video_id": video_id}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                return self._parse_video(data.get("data", {}))
                
        except Exception as e:
            logger.error(f"Error fetching video {video_id}: {e}")
            return None
    
    async def get_user_posts(
        self,
        username: str,
        count: int = 20,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get posts from a specific user
        
        Args:
            username: TikTok username
            count: Number of posts
            cursor: Pagination cursor
            
        Returns:
            Dict with videos and user info
        """
        if not self.api_key:
            return {"videos": [], "user": None}
        
        url = f"{self.base_url}/user/posts"
        params = {
            "username": username.lstrip("@"),
            "count": count
        }
        
        if cursor:
            params["cursor"] = cursor
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                videos = []
                for item in data.get("data", {}).get("itemList", []):
                    videos.append(self._parse_video(item))
                
                return {
                    "videos": videos,
                    "user": data.get("data", {}).get("userInfo"),
                    "cursor": data.get("data", {}).get("cursor"),
                    "has_more": data.get("data", {}).get("hasMore", False)
                }
                
        except Exception as e:
            logger.error(f"Error fetching user {username} posts: {e}")
            return {"videos": [], "user": None}
    
    async def get_video_comments(
        self,
        video_id: str,
        count: int = 20,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comments from a specific video
        
        Args:
            video_id: TikTok video ID
            count: Number of comments
            cursor: Pagination cursor
            
        Returns:
            Dict with comments and pagination
        """
        if not self.api_key:
            return {"comments": [], "cursor": None}
        
        url = f"{self.base_url}/video/comments"
        params = {
            "video_id": video_id,
            "count": count
        }
        
        if cursor:
            params["cursor"] = cursor
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "comments": data.get("data", {}).get("comments", []),
                    "cursor": data.get("data", {}).get("cursor"),
                    "has_more": data.get("data", {}).get("hasMore", False)
                }
                
        except Exception as e:
            logger.error(f"Error fetching comments for video {video_id}: {e}")
            return {"comments": [], "cursor": None}
    
    def _parse_video(self, item: Dict) -> Dict[str, Any]:
        """
        Parse and normalize video data from TikTok API response
        
        Args:
            item: Raw video data from API
            
        Returns:
            Normalized video metadata
        """
        try:
            stats = item.get("stats", {})
            video_data = item.get("video", {})
            author = item.get("author", {})
            music = item.get("music", {})
            
            return {
                "id": item.get("id"),
                "description": item.get("desc", ""),
                "create_time": item.get("createTime"),
                "author": {
                    "id": author.get("id"),
                    "username": author.get("uniqueId"),
                    "nickname": author.get("nickname"),
                    "avatar": author.get("avatarThumb"),
                    "verified": author.get("verified", False),
                    "followers": author.get("followerCount", 0)
                },
                "music": {
                    "id": music.get("id"),
                    "title": music.get("title"),
                    "author": music.get("authorName"),
                    "original": music.get("original", False)
                },
                "stats": {
                    "views": stats.get("playCount", 0),
                    "likes": stats.get("diggCount", 0),
                    "comments": stats.get("commentCount", 0),
                    "shares": stats.get("shareCount", 0),
                    "saves": stats.get("collectCount", 0)
                },
                "video": {
                    "duration": video_data.get("duration"),
                    "ratio": video_data.get("ratio"),
                    "cover": video_data.get("cover"),
                    "download_url": video_data.get("downloadAddr"),
                    "play_url": video_data.get("playAddr")
                },
                "hashtags": [
                    tag.get("name") for tag in item.get("textExtra", [])
                    if tag.get("hashtagName")
                ],
                "url": f"https://www.tiktok.com/@{author.get('uniqueId')}/video/{item.get('id')}"
            }
        except Exception as e:
            logger.error(f"Error parsing video data: {e}")
            return item
    
    async def analyze_trending_topics(
        self,
        region: str = "US",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Analyze trending content to identify popular topics/hashtags
        
        Args:
            region: Region to analyze
            limit: Number of videos to analyze
            
        Returns:
            List of trending topics with metrics
        """
        videos = await self.get_trending_feed(region=region, count=limit)
        
        if not videos:
            return []
        
        # Aggregate hashtag usage and performance
        hashtag_stats = {}
        
        for video in videos:
            for hashtag in video.get("hashtags", []):
                if hashtag not in hashtag_stats:
                    hashtag_stats[hashtag] = {
                        "hashtag": hashtag,
                        "video_count": 0,
                        "total_views": 0,
                        "total_likes": 0,
                        "total_shares": 0,
                        "avg_engagement_rate": 0
                    }
                
                stats = video.get("stats", {})
                hashtag_stats[hashtag]["video_count"] += 1
                hashtag_stats[hashtag]["total_views"] += stats.get("views", 0)
                hashtag_stats[hashtag]["total_likes"] += stats.get("likes", 0)
                hashtag_stats[hashtag]["total_shares"] += stats.get("shares", 0)
        
        # Calculate engagement rates
        topics = []
        for topic_data in hashtag_stats.values():
            if topic_data["total_views"] > 0:
                topic_data["avg_engagement_rate"] = (
                    (topic_data["total_likes"] + topic_data["total_shares"]) /
                    topic_data["total_views"]
                )
            topics.append(topic_data)
        
        # Sort by engagement rate
        topics.sort(key=lambda x: x["avg_engagement_rate"], reverse=True)
        
        return topics
