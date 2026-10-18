"""
YTP-012: Video Clip Extraction
Extracts short clips from long-form videos at specified timestamps.
"""
import logging
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ClipSpec:
    """Specification for a clip to extract."""
    start_seconds: float
    end_seconds: float
    label: Optional[str] = None


@dataclass
class ExtractedClip:
    """An extracted video clip."""
    file_path: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    label: Optional[str] = None
    file_size_bytes: int = 0


class VideoClipper:
    """
    Extracts short-form clips from long-form videos using FFmpeg.

    Used in the YouTube pipeline to create clips for social distribution.
    """

    def __init__(self, output_dir: str = "/tmp/mediaposter/clips"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def extract_clip(
        self,
        video_path: str,
        start_seconds: float,
        end_seconds: float,
        label: Optional[str] = None,
    ) -> ExtractedClip:
        """
        Extract a clip from a video.

        Args:
            video_path: Source video path
            start_seconds: Start time in seconds
            end_seconds: End time in seconds
            label: Optional label for the clip

        Returns:
            ExtractedClip with output file path
        """
        duration = end_seconds - start_seconds
        stem = Path(video_path).stem
        suffix = label or f"{int(start_seconds)}_{int(end_seconds)}"
        output_path = self.output_dir / f"{stem}_clip_{suffix}.mp4"

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", str(start_seconds),
            "-t", str(duration),
            "-c", "copy",
            "-y",
            str(output_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Clip extraction failed: {stderr.decode()[:200]}")

        file_size = output_path.stat().st_size

        return ExtractedClip(
            file_path=str(output_path),
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            duration_seconds=duration,
            label=label,
            file_size_bytes=file_size,
        )

    async def extract_clips(
        self,
        video_path: str,
        specs: List[ClipSpec],
    ) -> List[ExtractedClip]:
        """
        Extract multiple clips from a video.

        Args:
            video_path: Source video path
            specs: List of clip specifications

        Returns:
            List of ExtractedClip results
        """
        results = []
        for spec in specs:
            try:
                clip = await self.extract_clip(
                    video_path,
                    spec.start_seconds,
                    spec.end_seconds,
                    spec.label,
                )
                results.append(clip)
            except Exception as e:
                logger.error("Failed to extract clip %s: %s", spec.label, e)

        return results

    async def extract_highlights(
        self,
        video_path: str,
        transcript_segments: List[Dict[str, Any]],
        max_clips: int = 5,
        clip_duration: int = 60,
    ) -> List[ExtractedClip]:
        """
        Auto-extract highlight clips based on transcript segments.

        Finds the most content-dense segments for clip extraction.

        Args:
            video_path: Source video path
            transcript_segments: Transcript segments with start/end/text
            max_clips: Maximum number of clips
            clip_duration: Target clip duration in seconds

        Returns:
            List of extracted highlight clips
        """
        # Score segments by text density (words per second)
        scored = []
        for seg in transcript_segments:
            words = len(seg.get("text", "").split())
            duration = seg.get("end", 0) - seg.get("start", 0)
            if duration > 0:
                density = words / duration
                scored.append((density, seg))

        # Sort by density and take top N
        scored.sort(key=lambda x: x[0], reverse=True)
        top_segments = scored[:max_clips]

        specs = []
        for _, seg in top_segments:
            start = max(0, seg["start"] - 2)
            end = min(seg["end"] + clip_duration, seg["start"] + clip_duration)
            specs.append(ClipSpec(
                start_seconds=start,
                end_seconds=end,
                label=seg.get("text", "")[:30].replace(" ", "_"),
            ))

        return await self.extract_clips(video_path, specs)
