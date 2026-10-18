"""
Deezer Adapter
==============
Music search and 30s preview download via Deezer's public API on RapidAPI.
Host: deezerdevs-deezer.p.rapidapi.com  (uses RAPIDAPI_KEY — no extra subscription)

Confirmed working endpoints:
  GET /search?q={query}  → returns tracks with preview MP3 URLs, duration, artist, album
"""

import logging
import os
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import MusicAdapter
from services.music.models import MusicSearchCriteria, MusicResponse

logger = logging.getLogger(__name__)

RAPIDAPI_HOST = "deezerdevs-deezer.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}"

# Maps mood/vibe keywords to search queries that return good Deezer results
MOOD_QUERY_MAP = {
    "upbeat": "upbeat motivational",
    "motivational": "upbeat motivational",
    "energetic": "energetic workout",
    "hype": "energetic workout",
    "calm": "calm ambient",
    "ambient": "calm ambient",
    "chill": "lofi chill",
    "lofi": "lofi chill",
    "dramatic": "dramatic cinematic",
    "cinematic": "dramatic cinematic",
    "emotional": "emotional piano",
    "sad": "sad emotional",
    "happy": "happy upbeat pop",
    "focus": "focus deep work",
}


class DeezerAdapter(MusicAdapter):
    """
    Music search + preview download via Deezer / RapidAPI.

    Returns 30-second preview clips (MP3) — royalty-free for preview purposes.
    Full tracks require a Deezer subscription link.
    """

    def __init__(self, rapidapi_key: Optional[str] = None):
        self.rapidapi_key = rapidapi_key or os.getenv("RAPIDAPI_KEY")
        if not self.rapidapi_key:
            logger.warning("RAPIDAPI_KEY not set — DeezerAdapter will not work")

    def get_source_name(self) -> str:
        return "deezer"

    def supports_search(self) -> bool:
        return True

    def _headers(self) -> Dict[str, str]:
        return {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST,
        }

    def _mood_to_query(self, criteria: MusicSearchCriteria) -> str:
        """Build a Deezer search query from criteria."""
        if criteria.search_query:
            return criteria.search_query
        mood = (criteria.mood or "").lower()
        genre = (criteria.genre or "").lower()
        query = MOOD_QUERY_MAP.get(mood) or MOOD_QUERY_MAP.get(genre)
        if query:
            return query
        parts = [p for p in [mood, genre] if p]
        return " ".join(parts) if parts else "chill background music"

    async def search_music(
        self,
        criteria: MusicSearchCriteria,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search Deezer and return track metadata list."""
        if not self.rapidapi_key:
            raise RuntimeError("RAPIDAPI_KEY not configured — DeezerAdapter cannot search")

        query = self._mood_to_query(criteria)
        logger.info(f"[DeezerAdapter] Searching: q={query!r} limit={limit}")

        try:
            r = requests.get(
                f"{BASE_URL}/search",
                headers=self._headers(),
                params={"q": query},
                timeout=15,
            )
            r.raise_for_status()
            raw = r.json().get("data", [])
        except Exception as e:
            raise RuntimeError(f"Deezer search failed for query {query!r}: {e}") from e

        results = []
        for track in raw[:limit]:
            duration = track.get("duration", 0)
            # Apply duration filters if set
            if criteria.duration_min and duration < criteria.duration_min:
                continue
            if criteria.duration_max and duration > criteria.duration_max:
                continue

            results.append({
                "track_id": str(track.get("id")),
                "title": track.get("title", "Unknown"),
                "artist": track.get("artist", {}).get("name", "Unknown"),
                "album": track.get("album", {}).get("title", ""),
                "duration": duration,
                "preview_url": track.get("preview"),  # 30s MP3
                "link": track.get("link"),
                "explicit": track.get("explicit_lyrics", False),
                "genre": criteria.genre or "",
                "mood": criteria.mood or "",
                "source": "deezer",
                "rank": track.get("rank", 0),
            })

        logger.info(f"[DeezerAdapter] Found {len(results)} tracks for {query!r}")
        return results

    async def get_music(
        self,
        track_id: str,
        output_path: Optional[Path] = None,
    ) -> MusicResponse:
        """
        Download the 30s preview MP3 for a Deezer track ID.

        Args:
            track_id: Deezer numeric track ID
            output_path: Destination file path (default: data/music/deezer/{id}.mp3)
        """
        if not self.rapidapi_key:
            raise RuntimeError("RAPIDAPI_KEY not configured — DeezerAdapter cannot download")

        # 1. Fetch track metadata to get preview URL
        try:
            r = requests.get(
                f"{BASE_URL}/track/{track_id}",
                headers=self._headers(),
                timeout=15,
            )
            r.raise_for_status()
            track = r.json()
        except Exception as e:
            raise RuntimeError(f"Deezer track/{track_id} metadata fetch failed: {e}") from e

        preview_url = track.get("preview")
        if not preview_url:
            raise RuntimeError(f"Deezer track {track_id} has no preview URL")

        # 2. Download the MP3
        if output_path is None:
            output_dir = Path("data/music/deezer")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{track_id}.mp3"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            r2 = requests.get(preview_url, timeout=30, stream=True)
            r2.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r2.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            raise RuntimeError(f"Deezer preview download failed for track {track_id}: {e}") from e

        logger.info(f"[DeezerAdapter] Downloaded preview → {output_path}")
        return MusicResponse(
            job_id=track_id,
            success=True,
            music_path=str(output_path),
            duration_seconds=float(track.get("duration", 30)),
            genre=track.get("genre_id", ""),
            source="deezer",
            metadata={
                "title": track.get("title"),
                "artist": track.get("artist", {}).get("name"),
                "album": track.get("album", {}).get("title"),
                "preview_url": preview_url,
                "link": track.get("link"),
                "explicit": track.get("explicit_lyrics", False),
            },
        )
