"""
ASSET-002: Pexels Integration
Search and retrieve stock photos/videos from Pexels.
"""
import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PexelsPhoto:
    """A photo from Pexels."""
    photo_id: int
    photographer: str
    url: str
    src_original: str
    src_large: str
    src_medium: str
    width: int = 0
    height: int = 0
    alt: str = ""


@dataclass
class PexelsVideo:
    """A video from Pexels."""
    video_id: int
    user: str
    url: str
    video_files: List[Dict[str, Any]] = field(default_factory=list)
    duration: int = 0
    width: int = 0
    height: int = 0


class PexelsService:
    """
    Integration with Pexels API for stock photos and videos.

    Provides free stock content for use in social media posts,
    blog articles, and video production.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY", "")
        self.base_url = "https://api.pexels.com/v1"
        self.video_url = "https://api.pexels.com/videos"

    async def search_photos(
        self,
        query: str,
        per_page: int = 10,
        orientation: str = "landscape",
    ) -> List[PexelsPhoto]:
        """Search for photos."""
        try:
            import aiohttp
            headers = {"Authorization": self.api_key}
            params = {"query": query, "per_page": per_page, "orientation": orientation}

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/search", headers=headers, params=params) as resp:
                    data = await resp.json()

            return [
                PexelsPhoto(
                    photo_id=p["id"],
                    photographer=p.get("photographer", ""),
                    url=p.get("url", ""),
                    src_original=p.get("src", {}).get("original", ""),
                    src_large=p.get("src", {}).get("large", ""),
                    src_medium=p.get("src", {}).get("medium", ""),
                    width=p.get("width", 0),
                    height=p.get("height", 0),
                    alt=p.get("alt", ""),
                )
                for p in data.get("photos", [])
            ]
        except Exception as e:
            logger.error("Pexels photo search failed: %s", e)
            return []

    async def search_videos(
        self,
        query: str,
        per_page: int = 10,
    ) -> List[PexelsVideo]:
        """Search for videos."""
        try:
            import aiohttp
            headers = {"Authorization": self.api_key}
            params = {"query": query, "per_page": per_page}

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.video_url}/search", headers=headers, params=params) as resp:
                    data = await resp.json()

            return [
                PexelsVideo(
                    video_id=v["id"],
                    user=v.get("user", {}).get("name", ""),
                    url=v.get("url", ""),
                    video_files=v.get("video_files", []),
                    duration=v.get("duration", 0),
                    width=v.get("width", 0),
                    height=v.get("height", 0),
                )
                for v in data.get("videos", [])
            ]
        except Exception as e:
            logger.error("Pexels video search failed: %s", e)
            return []
