"""
YTP-019: FFmpeg Audio Extraction
Extracts audio from video files using FFmpeg for transcription.
"""
import logging
import asyncio
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AudioExtractionResult:
    """Result of audio extraction."""
    input_file: str
    output_file: str
    duration_seconds: float
    sample_rate: int
    channels: int
    format: str
    file_size_bytes: int


class FFmpegAudioExtractor:
    """
    Extracts audio from video files using FFmpeg.

    Outputs 16kHz mono WAV files optimized for Whisper transcription.
    """

    def __init__(self, output_dir: str = "/tmp/mediaposter/audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def extract(
        self,
        video_path: str,
        output_format: str = "wav",
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> AudioExtractionResult:
        """
        Extract audio from a video file.

        Args:
            video_path: Path to video file
            output_format: Output audio format (wav, mp3, m4a)
            sample_rate: Audio sample rate (16000 for Whisper)
            channels: Number of audio channels (1 for mono)

        Returns:
            AudioExtractionResult with output file path
        """
        input_path = Path(video_path)
        output_file = self.output_dir / f"{input_path.stem}.{output_format}"

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le" if output_format == "wav" else "libmp3lame",
            "-ar", str(sample_rate),
            "-ac", str(channels),
            "-y",  # Overwrite
            str(output_file),
        ]

        logger.info("Extracting audio from %s", video_path)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            logger.error("FFmpeg audio extraction failed: %s", error_msg)
            raise RuntimeError(f"Audio extraction failed: {error_msg}")

        # Get duration from output file
        duration = await self._get_duration(str(output_file))
        file_size = output_file.stat().st_size

        result = AudioExtractionResult(
            input_file=str(video_path),
            output_file=str(output_file),
            duration_seconds=duration,
            sample_rate=sample_rate,
            channels=channels,
            format=output_format,
            file_size_bytes=file_size,
        )

        logger.info(
            "Audio extracted: %s (%.1f min, %d bytes)",
            output_file,
            duration / 60,
            file_size,
        )
        return result

    async def split_audio(
        self,
        audio_path: str,
        chunk_duration_seconds: int = 600,
    ) -> list:
        """
        Split audio file into chunks for parallel transcription.

        Args:
            audio_path: Path to audio file
            chunk_duration_seconds: Duration of each chunk in seconds

        Returns:
            List of chunk file paths
        """
        total_duration = await self._get_duration(audio_path)
        chunks = []
        start = 0
        chunk_idx = 0

        input_path = Path(audio_path)

        while start < total_duration:
            output_file = self.output_dir / f"{input_path.stem}_chunk{chunk_idx:03d}.wav"
            cmd = [
                "ffmpeg",
                "-i", audio_path,
                "-ss", str(start),
                "-t", str(chunk_duration_seconds),
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-y",
                str(output_file),
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if proc.returncode == 0 and output_file.exists():
                chunks.append(str(output_file))

            start += chunk_duration_seconds
            chunk_idx += 1

        logger.info("Split %s into %d chunks", audio_path, len(chunks))
        return chunks

    async def _get_duration(self, file_path: str) -> float:
        """Get audio/video duration using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        try:
            return float(stdout.decode().strip())
        except (ValueError, AttributeError):
            return 0.0
