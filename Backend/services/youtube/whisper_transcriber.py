"""
YTP-020: Whisper API Integration
Transcribes audio files using OpenAI's Whisper API.
"""
import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """A segment of transcribed text with timing."""
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    """Result of a transcription."""
    audio_file: str
    text: str
    segments: List[TranscriptSegment] = field(default_factory=list)
    language: str = "en"
    duration_seconds: float = 0.0
    model: str = "whisper-1"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WhisperAPITranscriber:
    """
    Transcribes audio using OpenAI's Whisper API.

    Features:
    - Automatic language detection
    - Timestamped segments
    - Support for multiple audio formats
    - Configurable model and response format
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "whisper-1",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        response_format: str = "verbose_json",
    ) -> TranscriptionResult:
        """
        Transcribe an audio file using Whisper API.

        Args:
            audio_path: Path to audio file
            language: ISO language code (optional, auto-detected)
            response_format: API response format

        Returns:
            TranscriptionResult with text and segments
        """
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            with open(audio_path, "rb") as audio_file:
                params: Dict[str, Any] = {
                    "model": self.model,
                    "file": audio_file,
                    "response_format": response_format,
                }
                if language:
                    params["language"] = language

                response = await client.audio.transcriptions.create(**params)

            segments = []
            if hasattr(response, "segments") and response.segments:
                for seg in response.segments:
                    segments.append(TranscriptSegment(
                        start=seg.get("start", 0) if isinstance(seg, dict) else getattr(seg, "start", 0),
                        end=seg.get("end", 0) if isinstance(seg, dict) else getattr(seg, "end", 0),
                        text=seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", ""),
                    ))

            text = response.text if hasattr(response, "text") else str(response)
            detected_language = getattr(response, "language", language or "en")

            result = TranscriptionResult(
                audio_file=audio_path,
                text=text,
                segments=segments,
                language=detected_language,
                duration_seconds=getattr(response, "duration", 0.0),
                model=self.model,
            )

            logger.info(
                "Transcribed %s: %d chars, %d segments",
                audio_path,
                len(text),
                len(segments),
            )
            return result

        except ImportError:
            logger.warning("openai package not available, returning empty transcription")
            return TranscriptionResult(
                audio_file=audio_path,
                text="",
                language=language or "en",
            )
        except Exception as e:
            logger.error("Whisper API transcription failed for %s: %s", audio_path, e)
            raise

    async def transcribe_chunks(
        self,
        chunk_paths: List[str],
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe multiple audio chunks and merge results.

        Args:
            chunk_paths: List of audio chunk file paths
            language: ISO language code

        Returns:
            Merged TranscriptionResult
        """
        import asyncio

        tasks = [self.transcribe(chunk, language) for chunk in chunk_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_text = []
        all_segments = []
        total_duration = 0.0
        offset = 0.0

        for result in results:
            if isinstance(result, Exception):
                logger.error("Chunk transcription failed: %s", result)
                continue

            all_text.append(result.text)
            for seg in result.segments:
                all_segments.append(TranscriptSegment(
                    start=seg.start + offset,
                    end=seg.end + offset,
                    text=seg.text,
                ))
            offset += result.duration_seconds
            total_duration += result.duration_seconds

        return TranscriptionResult(
            audio_file=chunk_paths[0] if chunk_paths else "",
            text=" ".join(all_text),
            segments=all_segments,
            language=language or "en",
            duration_seconds=total_duration,
            model=self.model,
        )
