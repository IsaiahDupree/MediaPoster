"""
ASSET-001: Giphy Integration
Search and retrieve GIFs from Giphy for content creation.
"""
import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GiphyResult:
    """A GIF result from Giphy."""
    gif_id: str
    title: str
    url: str
    embed_url: str
    width: int = 0
    height: int = 0
    preview_url: str = ""


class GiphyService:
    """
    Integration with Giphy API for GIF search and retrieval.

    Used for:
    - Content enrichment
    - Social media posts
    - Blog embeds
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GIPHY_API_KEY", "")
        self.base_url = "https://api.giphy.com/v1"

    async def search(
        self,
        query: str,
        limit: int = 10,
        rating: str = "g",
    ) -> List[GiphyResult]:
        """
        Search for GIFs.

        Args:
            query: Search query
            limit: Max results
            rating: Content rating (g, pg, pg-13, r)

        Returns:
            List of GiphyResult
        """
        try:
            import aiohttp
            params = {
                "api_key": self.api_key,
                "q": query,
                "limit": limit,
                "rating": rating,
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/gifs/search", params=params) as resp:
                    data = await resp.json()

            results = []
            for item in data.get("data", []):
                images = item.get("images", {})
                original = images.get("original", {})
                results.append(GiphyResult(
                    gif_id=item["id"],
                    title=item.get("title", ""),
                    url=original.get("url", ""),
                    embed_url=item.get("embed_url", ""),
                    width=int(original.get("width", 0)),
                    height=int(original.get("height", 0)),
                    preview_url=images.get("preview_gif", {}).get("url", ""),
                ))
            return results

        except Exception as e:
            logger.error("Giphy search failed: %s", e)
            return []

    async def get_trending(self, limit: int = 10) -> List[GiphyResult]:
        """Get trending GIFs."""
        try:
            import aiohttp
            params = {"api_key": self.api_key, "limit": limit}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/gifs/trending", params=params) as resp:
                    data = await resp.json()

            return [
                GiphyResult(
                    gif_id=item["id"],
                    title=item.get("title", ""),
                    url=item.get("images", {}).get("original", {}).get("url", ""),
                    embed_url=item.get("embed_url", ""),
                )
                for item in data.get("data", [])
            ]
        except Exception as e:
            logger.error("Giphy trending failed: %s", e)
            return []
