"""
YTP-002: RapidAPI Transcript Service
YTP-011: Multi-Language Transcript Support
Fetches YouTube video transcripts via RapidAPI as a fallback/alternative.
"""
import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class RapidAPITranscriptSegment:
    """A segment from RapidAPI transcript."""
    start: float
    duration: float
    text: str


@dataclass
class RapidAPITranscriptResult:
    """Transcript result from RapidAPI."""
    video_id: str
    language: str
    segments: List[RapidAPITranscriptSegment] = field(default_factory=list)
    full_text: str = ""
    available_languages: List[str] = field(default_factory=list)
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RapidAPITranscriptService:
    """
    Fetches YouTube transcripts via RapidAPI.

    Supports:
    - Multiple languages (YTP-011)
    - Auto-generated and manual captions
    - Fallback when direct transcript is unavailable
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_host: str = "youtube-transcriptor.p.rapidapi.com",
    ):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY", "")
        self.api_host = api_host

    async def get_transcript(
        self,
        video_id: str,
        language: str = "en",
    ) -> RapidAPITranscriptResult:
        """
        Fetch transcript for a YouTube video.

        Args:
            video_id: YouTube video ID
            language: Language code (ISO 639-1)

        Returns:
            RapidAPITranscriptResult
        """
        try:
            import aiohttp

            url = f"https://{self.api_host}/transcript"
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": self.api_host,
            }
            params = {"video_id": video_id, "lang": language}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        logger.error("RapidAPI error: %s", await resp.text())
                        return RapidAPITranscriptResult(video_id=video_id, language=language)

                    data = await resp.json()

            segments = []
            for item in data.get("transcription", []):
                segments.append(RapidAPITranscriptSegment(
                    start=float(item.get("start", 0)),
                    duration=float(item.get("duration", 0)),
                    text=item.get("text", ""),
                ))

            full_text = " ".join(seg.text for seg in segments)

            return RapidAPITranscriptResult(
                video_id=video_id,
                language=language,
                segments=segments,
                full_text=full_text,
                available_languages=data.get("available_languages", [language]),
            )

        except ImportError:
            logger.warning("aiohttp not available for RapidAPI requests")
            return RapidAPITranscriptResult(video_id=video_id, language=language)
        except Exception as e:
            logger.error("Failed to fetch transcript from RapidAPI: %s", e)
            raise

    async def get_available_languages(self, video_id: str) -> List[str]:
        """Get available transcript languages for a video."""
        result = await self.get_transcript(video_id, language="en")
        return result.available_languages

    async def get_multi_language_transcripts(
        self,
        video_id: str,
        languages: List[str],
    ) -> Dict[str, RapidAPITranscriptResult]:
        """
        Fetch transcripts in multiple languages.

        Args:
            video_id: YouTube video ID
            languages: List of language codes

        Returns:
            Dict mapping language code to transcript result
        """
        import asyncio
        tasks = {lang: self.get_transcript(video_id, lang) for lang in languages}
        results = {}
        for lang, task in tasks.items():
            try:
                results[lang] = await task
            except Exception as e:
                logger.warning("Failed to fetch %s transcript: %s", lang, e)
        return results
