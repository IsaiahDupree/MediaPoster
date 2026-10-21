"""
YouTube Publisher for Sora Daily Automation
Publishes processed videos to YouTube with AI-generated metadata.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger


YOUTUBE_ACCOUNT_ID = "228"  # Isaiah Dupree YouTube


@dataclass
class YouTubeUploadJob:
    """YouTube upload job details."""
    video_path: str
    title: str
    description: str
    tags: List[str]
    playlist_id: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    is_short: bool = False
    category_id: str = "22"  # People & Blogs


class YouTubePublisher:
    """
    Publishes Sora videos to YouTube.
    
    Uses Blotato for actual upload via account ID 228.
    """
    
    def __init__(self):
        self.account_id = YOUTUBE_ACCOUNT_ID
        logger.info(f"✅ YouTubePublisher initialized (Account: {self.account_id})")
    
    async def generate_metadata(
        self,
        prompt: str,
        theme: str,
        is_movie_part: bool = False,
        part_number: int = 0,
        trend: Optional[str] = None
    ) -> Dict:
        return {"error": "script_hub_required", "message": "Content metadata must be generated through ScriptHub."}
    
    async def publish_single(
        self,
        video_path: str,
        prompt: str,
        theme: str,
        trend: Optional[str] = None,
        scheduled_time: Optional[datetime] = None
    ) -> Dict:
        return {"success": False, "error": "airtime_required", "message": "YouTube delivery must be scheduled through Airtime."}
    
    async def publish_movie(
        self,
        video_paths: List[str],
        prompts: List[str],
        theme: str,
        trend: Optional[str] = None,
        scheduled_time: Optional[datetime] = None
    ) -> Dict:
        return {"success": False, "error": "airtime_required", "message": "YouTube delivery must be scheduled through Airtime."}
    
    async def _upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: List[str],
        scheduled_time: Optional[datetime] = None,
        playlist_id: Optional[str] = None
    ) -> Dict:
        return {"success": False, "error": "airtime_required", "message": "Direct Blotato uploads are disabled; use Airtime."}
    
    def get_publishing_schedule(self, singles_count: int, movies_count: int) -> List[Dict]:
        """
        Generate optimal publishing schedule for the day.
        
        Singles: Spread throughout day
        Movies: 3-part bunches at peak times
        """
        from datetime import time
        
        schedule = []
        
        # Peak times for YouTube
        single_times = [
            time(6, 0), time(8, 0), time(10, 0), time(12, 0),
            time(14, 0), time(16, 0), time(18, 0), time(20, 0),
            time(21, 0), time(22, 0)
        ]
        
        movie_times = [
            time(9, 0), time(13, 0), time(17, 0), time(19, 0)
        ]
        
        # Schedule singles
        for i in range(min(singles_count, len(single_times))):
            schedule.append({
                "type": "single",
                "index": i,
                "time": single_times[i].isoformat()
            })
        
        # Schedule movies
        for i in range(min(movies_count, len(movie_times))):
            schedule.append({
                "type": "movie",
                "index": i,
                "time": movie_times[i].isoformat()
            })
        
        return schedule


# =============================================================================
# SINGLETON
# =============================================================================

_publisher_instance: Optional[YouTubePublisher] = None

def get_youtube_publisher() -> YouTubePublisher:
    """Get singleton instance of YouTubePublisher."""
    global _publisher_instance
    if _publisher_instance is None:
        _publisher_instance = YouTubePublisher()
    return _publisher_instance
