"""
BM-015: Caption Generation
Generates styled captions/subtitles for video clips.
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CaptionStyle:
    """Style configuration for captions."""
    font_family: str = "Arial"
    font_size: int = 48
    font_color: str = "white"
    background_color: str = "black@0.5"
    position: str = "bottom"  # top, center, bottom
    max_chars_per_line: int = 35
    animation: str = "word"  # none, word, line


@dataclass
class CaptionSegment:
    """A caption segment with timing."""
    start: float
    end: float
    text: str


@dataclass
class CaptionResult:
    """Result of caption generation."""
    input_video: str
    output_video: str
    srt_file: Optional[str] = None
    ass_file: Optional[str] = None
    segment_count: int = 0


class CaptionGenerator:
    """
    Generates and burns captions into video clips.

    Supports:
    - SRT/ASS subtitle file generation
    - Styled caption overlays via FFmpeg
    - Word-by-word animation
    - Multiple position options
    """

    def __init__(
        self,
        style: Optional[CaptionStyle] = None,
        output_dir: str = "/tmp/mediaposter/captioned",
    ):
        self.style = style or CaptionStyle()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_srt(
        self,
        segments: List[CaptionSegment],
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate an SRT subtitle file from segments.

        Args:
            segments: Caption segments with timing
            output_path: Output file path

        Returns:
            Path to the SRT file
        """
        if output_path is None:
            output_path = str(self.output_dir / "captions.srt")

        lines = []
        for i, seg in enumerate(segments, 1):
            start_tc = self._seconds_to_timecode(seg.start)
            end_tc = self._seconds_to_timecode(seg.end)
            lines.append(f"{i}")
            lines.append(f"{start_tc} --> {end_tc}")
            lines.append(seg.text)
            lines.append("")

        Path(output_path).write_text("\n".join(lines), encoding="utf-8")
        return output_path

    async def burn_captions(
        self,
        video_path: str,
        segments: List[CaptionSegment],
        output_path: Optional[str] = None,
    ) -> CaptionResult:
        """
        Burn captions into a video using FFmpeg.

        Args:
            video_path: Input video path
            segments: Caption segments
            output_path: Output video path

        Returns:
            CaptionResult
        """
        import asyncio

        # Generate SRT file
        srt_path = str(self.output_dir / f"{Path(video_path).stem}_captions.srt")
        self.generate_srt(segments, srt_path)

        if output_path is None:
            output_path = str(self.output_dir / f"{Path(video_path).stem}_captioned.mp4")

        style_str = (
            f"FontSize={self.style.font_size},"
            f"PrimaryColour=&H00FFFFFF,"
            f"BackColour=&H80000000,"
            f"Alignment=2"
        )

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"subtitles={srt_path}:force_style='{style_str}'",
            "-c:a", "copy",
            "-y",
            output_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        return CaptionResult(
            input_video=video_path,
            output_video=output_path,
            srt_file=srt_path,
            segment_count=len(segments),
        )

    def _seconds_to_timecode(self, seconds: float) -> str:
        """Convert seconds to SRT timecode format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
