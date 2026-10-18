"""
YTP-021: Transcript Caching
Caches transcription results to avoid re-processing identical videos.
"""
import logging
import json
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = "/tmp/mediaposter/transcript_cache"


class TranscriptCache:
    """
    File-based transcript cache.

    Stores transcription results keyed by video ID or content hash.
    Avoids re-transcribing videos that have already been processed.
    """

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # In-memory index for fast lookups
        self._index: Dict[str, str] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load cache index from disk."""
        index_file = self.cache_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file) as f:
                    self._index = json.load(f)
                logger.info("Loaded transcript cache index: %d entries", len(self._index))
            except Exception as e:
                logger.warning("Failed to load cache index: %s", e)
                self._index = {}

    def _save_index(self) -> None:
        """Save cache index to disk."""
        index_file = self.cache_dir / "index.json"
        try:
            with open(index_file, "w") as f:
                json.dump(self._index, f)
        except Exception as e:
            logger.error("Failed to save cache index: %s", e)

    def get(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached transcript for a video.

        Args:
            video_id: Video identifier

        Returns:
            Cached transcript data dict, or None if not cached
        """
        cache_file = self._get_cache_path(video_id)
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                logger.debug("Cache hit for video %s", video_id)
                return data
            except Exception as e:
                logger.warning("Failed to read cache for %s: %s", video_id, e)
        return None

    def put(
        self,
        video_id: str,
        transcript_data: Dict[str, Any],
    ) -> None:
        """
        Cache a transcript result.

        Args:
            video_id: Video identifier
            transcript_data: Transcript data to cache
        """
        cache_file = self._get_cache_path(video_id)
        try:
            transcript_data["cached_at"] = datetime.now(timezone.utc).isoformat()
            with open(cache_file, "w") as f:
                json.dump(transcript_data, f, indent=2)
            self._index[video_id] = str(cache_file)
            self._save_index()
            logger.info("Cached transcript for video %s", video_id)
        except Exception as e:
            logger.error("Failed to cache transcript for %s: %s", video_id, e)

    def has(self, video_id: str) -> bool:
        """Check if a transcript is cached."""
        return self._get_cache_path(video_id).exists()

    def invalidate(self, video_id: str) -> bool:
        """
        Remove a cached transcript.

        Returns:
            True if entry was found and removed
        """
        cache_file = self._get_cache_path(video_id)
        if cache_file.exists():
            cache_file.unlink()
            self._index.pop(video_id, None)
            self._save_index()
            logger.info("Invalidated cache for video %s", video_id)
            return True
        return False

    def clear(self) -> int:
        """
        Clear all cached transcripts.

        Returns:
            Number of entries cleared
        """
        count = 0
        for f in self.cache_dir.glob("*.json"):
            if f.name != "index.json":
                f.unlink()
                count += 1
        self._index.clear()
        self._save_index()
        logger.info("Cleared %d cached transcripts", count)
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        return {
            "entries": len(self._index),
            "files": len(cache_files) - 1,  # Exclude index.json
            "total_size_bytes": total_size,
            "cache_dir": str(self.cache_dir),
        }

    def _get_cache_path(self, video_id: str) -> Path:
        """Get the cache file path for a video ID."""
        safe_id = hashlib.md5(video_id.encode()).hexdigest()
        return self.cache_dir / f"{safe_id}.json"
