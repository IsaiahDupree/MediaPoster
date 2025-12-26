"""
Trend Ingestion Service - Instagram Looter API Integration
"""
import os
import asyncio
import httpx
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from loguru import logger

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "instagram-looter2.p.rapidapi.com"


@dataclass
class IngestedMedia:
    media_id: str
    platform: str
    author_id: str
    author_username: str
    caption: str
    hashtags: List[str]
    music_id: Optional[str]
    music_title: Optional[str]
    play_count: int
    like_count: int
    comment_count: int
    posted_at: datetime
    raw_data: Dict[str, Any]


class TrendIngestionService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or RAPIDAPI_KEY
        self.base_url = f"https://{RAPIDAPI_HOST}"
    
    def _headers(self) -> Dict[str, str]:
        return {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": RAPIDAPI_HOST}
    
    async def _request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.get(f"{self.base_url}{endpoint}", params=params, headers=self._headers())
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logger.error(f"Request failed: {e}")
                return None
    
    async def ingest_hashtag(self, tag: str, limit: int = 50) -> List[IngestedMedia]:
        """Ingest from hashtag feed."""
        data = await self._request("/v1.2/tag/medias", {"tag": tag.lstrip("#"), "page_size": limit})
        if not data:
            return []
        items = data.get("data", {}).get("items", data.get("items", []))
        return [m for m in (self._normalize(i) for i in items[:limit]) if m]
    
    async def ingest_account(self, username: str, limit: int = 20) -> List[IngestedMedia]:
        """Ingest reels from account."""
        data = await self._request("/v1/reels", {"username_or_id_or_url": username, "amount": limit})
        if not data:
            return []
        items = data.get("data", {}).get("items", data.get("items", []))
        return [m for m in (self._normalize(i) for i in items[:limit]) if m]
    
    def _normalize(self, item: Dict) -> Optional[IngestedMedia]:
        try:
            media_id = str(item.get("id", item.get("pk", "")))
            user = item.get("user", {})
            caption = item.get("caption", {})
            caption_text = caption.get("text", "") if isinstance(caption, dict) else str(caption or "")
            music = item.get("clips_metadata", {}).get("music_info", {}).get("music_asset_info", {})
            taken_at = item.get("taken_at", 0)
            
            return IngestedMedia(
                media_id=media_id,
                platform="instagram",
                author_id=str(user.get("pk", "")),
                author_username=user.get("username", ""),
                caption=caption_text,
                hashtags=re.findall(r'#(\w+)', caption_text.lower()),
                music_id=str(music.get("audio_cluster_id", "")) or None,
                music_title=music.get("title"),
                play_count=item.get("play_count", 0) or 0,
                like_count=item.get("like_count", 0) or 0,
                comment_count=item.get("comment_count", 0) or 0,
                posted_at=datetime.fromtimestamp(taken_at) if taken_at else datetime.utcnow(),
                raw_data=item
            )
        except Exception as e:
            logger.warning(f"Normalize failed: {e}")
            return None
    
    def extract_entities(self, media: List[IngestedMedia]) -> Dict[str, List]:
        """Extract sounds and hashtags from media."""
        sounds, hashtags = {}, {}
        for m in media:
            if m.music_id:
                sounds[m.music_id] = {"id": m.music_id, "title": m.music_title, "count": sounds.get(m.music_id, {}).get("count", 0) + 1}
            for tag in m.hashtags:
                hashtags[tag] = {"tag": tag, "count": hashtags.get(tag, {}).get("count", 0) + 1}
        return {
            "sounds": sorted(sounds.values(), key=lambda x: x["count"], reverse=True),
            "hashtags": sorted(hashtags.values(), key=lambda x: x["count"], reverse=True)
        }
