"""
ASSET-003: Unsplash Integration
Search and retrieve high-quality photos from Unsplash.
"""
import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UnsplashPhoto:
    """A photo from Unsplash."""
    photo_id: str
    description: str
    photographer: str
    url_raw: str
    url_full: str
    url_regular: str
    url_small: str
    url_thumb: str
    width: int = 0
    height: int = 0
    download_url: str = ""


class UnsplashService:
    """
    Integration with Unsplash API for high-quality stock photos.

    Provides free high-resolution photos for content creation,
    blog posts, and social media.
    """

    def __init__(self, access_key: Optional[str] = None):
        self.access_key = access_key or os.getenv("UNSPLASH_ACCESS_KEY", "")
        self.base_url = "https://api.unsplash.com"

    async def search(
        self,
        query: str,
        per_page: int = 10,
        orientation: Optional[str] = None,
    ) -> List[UnsplashPhoto]:
        """
        Search for photos.

        Args:
            query: Search query
            per_page: Results per page
            orientation: landscape, portrait, squarish

        Returns:
            List of UnsplashPhoto
        """
        try:
            import aiohttp
            headers = {"Authorization": f"Client-ID {self.access_key}"}
            params = {"query": query, "per_page": per_page}
            if orientation:
                params["orientation"] = orientation

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/search/photos",
                    headers=headers,
                    params=params,
                ) as resp:
                    data = await resp.json()

            return [
                UnsplashPhoto(
                    photo_id=p["id"],
                    description=p.get("description") or p.get("alt_description") or "",
                    photographer=p.get("user", {}).get("name", ""),
                    url_raw=p.get("urls", {}).get("raw", ""),
                    url_full=p.get("urls", {}).get("full", ""),
                    url_regular=p.get("urls", {}).get("regular", ""),
                    url_small=p.get("urls", {}).get("small", ""),
                    url_thumb=p.get("urls", {}).get("thumb", ""),
                    width=p.get("width", 0),
                    height=p.get("height", 0),
                    download_url=p.get("links", {}).get("download", ""),
                )
                for p in data.get("results", [])
            ]
        except Exception as e:
            logger.error("Unsplash search failed: %s", e)
            return []

    async def get_random(
        self,
        query: Optional[str] = None,
        count: int = 1,
    ) -> List[UnsplashPhoto]:
        """Get random photos."""
        try:
            import aiohttp
            headers = {"Authorization": f"Client-ID {self.access_key}"}
            params = {"count": count}
            if query:
                params["query"] = query

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/photos/random",
                    headers=headers,
                    params=params,
                ) as resp:
                    data = await resp.json()

            if not isinstance(data, list):
                data = [data]

            return [
                UnsplashPhoto(
                    photo_id=p["id"],
                    description=p.get("description") or "",
                    photographer=p.get("user", {}).get("name", ""),
                    url_raw=p.get("urls", {}).get("raw", ""),
                    url_full=p.get("urls", {}).get("full", ""),
                    url_regular=p.get("urls", {}).get("regular", ""),
                    url_small=p.get("urls", {}).get("small", ""),
                    url_thumb=p.get("urls", {}).get("thumb", ""),
                    width=p.get("width", 0),
                    height=p.get("height", 0),
                )
                for p in data
            ]
        except Exception as e:
            logger.error("Unsplash random failed: %s", e)
            return []
