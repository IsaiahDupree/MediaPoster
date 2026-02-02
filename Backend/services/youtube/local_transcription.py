"""
YTP-017: Local Transcription Service
Provides local transcription using Whisper model for long videos.
Falls back gracefully when model is not available.
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class LocalTranscriptSegment:
    """A segment of locally transcribed text."""
    start: float
    end: float
    text: str


@dataclass
class LocalTranscriptionResult:
    """Result from local transcription."""
    audio_file: str
    text: str
    segments: List[LocalTranscriptSegment] = field(default_factory=list)
    language: str = "en"
    duration_seconds: float = 0.0
    model_size: str = "base"
    processing_time_seconds: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LocalTranscriptionService:
    """
    Local transcription using Whisper model.

    Used for long videos that would be expensive via the API.
    Supports chunked transcription for memory-efficient processing.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
    ):
        self.model_size = model_size
        self.device = device
        self._model = None

    def _load_model(self):
        """Load the Whisper model lazily."""
        if self._model is not None:
            return

        try:
            import whisper
            logger.info("Loading Whisper model: %s on %s", self.model_size, self.device)
            self._model = whisper.load_model(self.model_size, device=self.device)
            logger.info("Whisper model loaded successfully")
        except ImportError:
            logger.warning("whisper package not available for local transcription")
            self._model = None

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> LocalTranscriptionResult:
        """
        Transcribe an audio file locally.

        Args:
            audio_path: Path to audio file
            language: Language code (optional, auto-detected)

        Returns:
            LocalTranscriptionResult
        """
        import time
        start_time = time.time()

        self._load_model()

        if self._model is None:
            logger.warning("No local model available, returning empty result")
            return LocalTranscriptionResult(
                audio_file=audio_path,
                text="",
                language=language or "en",
                model_size=self.model_size,
            )

        try:
            options = {}
            if language:
                options["language"] = language

            result = self._model.transcribe(audio_path, **options)

            segments = []
            for seg in result.get("segments", []):
                segments.append(LocalTranscriptSegment(
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip(),
                ))

            processing_time = time.time() - start_time

            return LocalTranscriptionResult(
                audio_file=audio_path,
                text=result.get("text", "").strip(),
                segments=segments,
                language=result.get("language", language or "en"),
                duration_seconds=segments[-1].end if segments else 0,
                model_size=self.model_size,
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            logger.error("Local transcription failed for %s: %s", audio_path, e)
            raise

    async def transcribe_chunks(
        self,
        chunk_paths: List[str],
        language: Optional[str] = None,
    ) -> LocalTranscriptionResult:
        """
        Transcribe multiple audio chunks and merge.

        Args:
            chunk_paths: Audio chunk file paths
            language: Language code

        Returns:
            Merged LocalTranscriptionResult
        """
        all_text = []
        all_segments = []
        total_processing = 0.0
        offset = 0.0

        for chunk_path in chunk_paths:
            result = await self.transcribe(chunk_path, language)
            all_text.append(result.text)

            for seg in result.segments:
                all_segments.append(LocalTranscriptSegment(
                    start=seg.start + offset,
                    end=seg.end + offset,
                    text=seg.text,
                ))

            offset += result.duration_seconds
            total_processing += result.processing_time_seconds

        return LocalTranscriptionResult(
            audio_file=chunk_paths[0] if chunk_paths else "",
            text=" ".join(all_text),
            segments=all_segments,
            language=language or "en",
            duration_seconds=offset,
            model_size=self.model_size,
            processing_time_seconds=total_processing,
        )

    @property
    def is_available(self) -> bool:
        """Check if local transcription is available."""
        try:
            import whisper
            return True
        except ImportError:
            return False
