"""
TikTok Analytics Service
Fetches video comments and metrics using Safari automation
"""
import os
import logging
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from pathlib import Path

logger = logging.getLogger(__name__)


class TikTokComment(BaseModel):
    """A single TikTok comment"""
    comment_id: str
    video_id: str
    author_name: str
    author_profile_url: Optional[str] = None
    text: str
    like_count: int = 0
    reply_count: int = 0
    published_at: Optional[str] = None
    is_reply: bool = False
    is_author: bool = False


class TikTokVideoInfo(BaseModel):
    """Info about a TikTok video"""
    video_id: str
    video_url: str
    author: str
    caption: Optional[str] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


class TikTokAnalyticsService:
    """
    Service for fetching TikTok analytics using Safari automation
    
    Uses the existing TikTokEngagement automation to fetch comments
    """
    
    def __init__(self):
        self.tiktok_username = os.getenv("TIKTOK_USERNAME", "")
        self._engagement = None
        self._initialized = False
    
    async def _get_engagement(self):
        """Get or create TikTokEngagement instance"""
        if self._engagement is None:
            try:
                from automation.tiktok_engagement import TikTokEngagement
                self._engagement = TikTokEngagement()
                await self._engagement.start()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize TikTok engagement: {e}")
                raise
        return self._engagement
    
    async def get_video_comments(
        self, 
        video_url: str,
        limit: int = 50
    ) -> List[TikTokComment]:
        """
        Fetch comments for a TikTok video
        
        Args:
            video_url: Full TikTok video URL
            limit: Maximum comments to fetch
            
        Returns:
            List of TikTokComment objects
        """
        try:
            engagement = await self._get_engagement()
            
            # Navigate to the video
            logger.info(f"Navigating to TikTok video: {video_url}")
            nav_result = await engagement.navigate_to(video_url)
            
            if not nav_result.get("success"):
                logger.error(f"Failed to navigate to video: {nav_result}")
                return []
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Get comments
            raw_comments = await engagement.get_comments(limit=limit)
            
            # Extract video ID from URL
            video_id = self._extract_video_id(video_url)
            
            # Transform to our format
            comments = []
            for i, c in enumerate(raw_comments):
                username = c.get("username", "")
                is_author = username.lower() == self.tiktok_username.lower() if self.tiktok_username else False
                
                comments.append(TikTokComment(
                    comment_id=f"tiktok_{video_id}_{i}",
                    video_id=video_id,
                    author_name=f"@{username}" if username and not username.startswith("@") else username,
                    author_profile_url=f"https://www.tiktok.com/@{username}" if username else None,
                    text=c.get("text", ""),
                    like_count=int(c.get("likes", "0").replace(",", "")) if c.get("likes") else 0,
                    is_reply=False,
                    is_author=is_author,
                ))
            
            logger.info(f"✓ Fetched {len(comments)} comments from TikTok video")
            return comments
            
        except Exception as e:
            logger.error(f"Error fetching TikTok comments: {e}")
            return []
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from TikTok URL"""
        # TikTok URL format: https://www.tiktok.com/@username/video/1234567890
        if "/video/" in url:
            video_id = url.split("/video/")[-1].split("?")[0]
            return video_id
        return url
    
    async def get_profile_videos(self, username: str = None, limit: int = 10) -> List[Dict]:
        """
        Get recent videos from a TikTok profile
        
        Args:
            username: TikTok username (without @)
            limit: Maximum videos to fetch
            
        Returns:
            List of video info dicts
        """
        username = username or self.tiktok_username
        if not username:
            logger.error("No TikTok username provided")
            return []
        
        try:
            engagement = await self._get_engagement()
            
            # Navigate to profile
            profile_url = f"https://www.tiktok.com/@{username}"
            logger.info(f"Navigating to TikTok profile: {profile_url}")
            
            await engagement.navigate_to(profile_url)
            await asyncio.sleep(3)
            
            # Get video URLs from profile
            js_code = f"""
(function(){{
var videos = [];
var items = document.querySelectorAll('[data-e2e="user-post-item"] a, [class*="DivItemContainer"] a');
items.forEach(function(a, i){{
    if(i >= {limit}) return;
    var href = a.href || a.getAttribute('href');
    if(href && href.includes('/video/')){{
        videos.push(href);
    }}
}});
return JSON.stringify([...new Set(videos)]);
}})();
            """
            
            result = await engagement._run_js(js_code)
            
            if result:
                video_urls = json.loads(result)
                return [{"url": url, "video_id": self._extract_video_id(url)} for url in video_urls[:limit]]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting profile videos: {e}")
            return []
    
    async def get_all_profile_comments(
        self,
        username: str = None,
        max_videos: int = 5,
        max_comments_per_video: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch comments for all recent videos from a TikTok profile
        
        Args:
            username: TikTok username
            max_videos: Maximum videos to check
            max_comments_per_video: Maximum comments per video
            
        Returns:
            Dict with all comments organized by video
        """
        username = username or self.tiktok_username
        
        # Get profile videos
        videos = await self.get_profile_videos(username, limit=max_videos)
        
        all_comments = []
        videos_with_comments = []
        
        for video in videos:
            video_url = video.get("url")
            if not video_url:
                continue
            
            comments = await self.get_video_comments(video_url, limit=max_comments_per_video)
            
            if comments:
                videos_with_comments.append({
                    "video_id": video.get("video_id"),
                    "video_url": video_url,
                    "comment_count": len(comments),
                    "comments": [c.model_dump() for c in comments]
                })
                all_comments.extend(comments)
            
            # Small delay between videos to avoid rate limiting
            await asyncio.sleep(2)
        
        return {
            "total_comments": len(all_comments),
            "videos_checked": len(videos),
            "videos_with_comments": len(videos_with_comments),
            "comments_by_video": videos_with_comments,
            "all_comments": [c.model_dump() for c in all_comments],
            "fetched_at": datetime.now().isoformat(),
        }
    
    async def close(self):
        """Close the automation session"""
        if self._engagement:
            try:
                await self._engagement.close()
            except:
                pass
            self._engagement = None
            self._initialized = False


# Singleton instance
_tiktok_service: Optional[TikTokAnalyticsService] = None


def get_tiktok_analytics_service() -> TikTokAnalyticsService:
    """Get singleton instance of TikTokAnalyticsService"""
    global _tiktok_service
    if _tiktok_service is None:
        _tiktok_service = TikTokAnalyticsService()
    return _tiktok_service
