"""
BM-016: Title Card Overlay
Generates title card overlays for video clips using text rendering.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TitleCardConfig:
    """Configuration for title card generation."""
    width: int = 1080
    height: int = 1920
    background_color: str = "#000000"
    text_color: str = "#FFFFFF"
    font_size: int = 72
    font_family: str = "Arial"
    duration_seconds: float = 3.0
    fade_in: float = 0.5
    fade_out: float = 0.5


class TitleCardGenerator:
    """
    Generates title card overlays for video clips.

    Creates intro/outro title cards with:
    - Text rendering on solid/gradient backgrounds
    - Fade in/out transitions
    - Configurable fonts and colors
    """

    def __init__(
        self,
        config: Optional[TitleCardConfig] = None,
        output_dir: str = "/tmp/mediaposter/title_cards",
    ):
        self.config = config or TitleCardConfig()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        title: str,
        subtitle: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate a title card video.

        Args:
            title: Main title text
            subtitle: Optional subtitle text
            output_path: Output video file path

        Returns:
            Path to the generated title card video
        """
        import asyncio

        if output_path is None:
            safe_name = "".join(c for c in title[:20] if c.isalnum() or c == "_")
            output_path = str(self.output_dir / f"title_{safe_name}.mp4")

        c = self.config
        text_filter = f"drawtext=text='{title}':fontsize={c.font_size}:fontcolor={c.text_color}:x=(w-text_w)/2:y=(h-text_h)/2"

        if subtitle:
            text_filter += f",drawtext=text='{subtitle}':fontsize={c.font_size // 2}:fontcolor={c.text_color}:x=(w-text_w)/2:y=(h+text_h)/2+20"

        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"color={c.background_color}:size={c.width}x{c.height}:duration={c.duration_seconds}:rate=30",
            "-vf", f"{text_filter},fade=in:st=0:d={c.fade_in},fade=out:st={c.duration_seconds - c.fade_out}:d={c.fade_out}",
            "-c:v", "libx264",
            "-y",
            output_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        return output_path

    async def prepend_to_video(
        self,
        video_path: str,
        title: str,
        subtitle: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate a title card and prepend it to a video.

        Args:
            video_path: Input video path
            title: Title text
            subtitle: Optional subtitle
            output_path: Output path

        Returns:
            Path to the output video
        """
        import asyncio

        title_card = await self.generate(title, subtitle)

        if output_path is None:
            output_path = str(self.output_dir / f"{Path(video_path).stem}_with_title.mp4")

        # Use FFmpeg concat
        concat_file = str(self.output_dir / "concat.txt")
        Path(concat_file).write_text(
            f"file '{title_card}'\nfile '{video_path}'\n"
        )

        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            "-y",
            output_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        return output_path
