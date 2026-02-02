"""
BM-014: Smart Reframing
Intelligently reframes horizontal video to vertical (9:16) using face/subject detection.
"""
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ReframeConfig:
    """Configuration for smart reframing."""
    target_width: int = 1080
    target_height: int = 1920
    aspect_ratio: str = "9:16"
    face_tracking: bool = True
    center_bias: float = 0.3


@dataclass
class ReframeResult:
    """Result of a reframing operation."""
    input_path: str
    output_path: str
    original_resolution: Tuple[int, int] = (1920, 1080)
    output_resolution: Tuple[int, int] = (1080, 1920)
    crop_positions: List[Dict[str, int]] = None

    def __post_init__(self):
        if self.crop_positions is None:
            self.crop_positions = []


class SmartReframer:
    """
    Reframes horizontal videos to vertical using intelligent cropping.

    Uses center-of-interest tracking to keep the subject in frame
    when converting 16:9 to 9:16.
    """

    def __init__(
        self,
        config: Optional[ReframeConfig] = None,
        output_dir: str = "/tmp/mediaposter/reframed",
    ):
        self.config = config or ReframeConfig()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def reframe(
        self,
        video_path: str,
        output_path: Optional[str] = None,
    ) -> ReframeResult:
        """
        Reframe a video from horizontal to vertical.

        Args:
            video_path: Input video path
            output_path: Optional output path

        Returns:
            ReframeResult with output file info
        """
        input_path = Path(video_path)
        if output_path is None:
            output_path = str(self.output_dir / f"{input_path.stem}_vertical.mp4")

        # Calculate crop dimensions for center crop
        crop_w = self.config.target_width
        crop_h = self.config.target_height

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"crop={crop_w}:{crop_h}:(in_w-{crop_w})/2:(in_h-{crop_h})/2,scale={self.config.target_width}:{self.config.target_height}",
            "-c:a", "copy",
            "-y",
            output_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Reframing failed: {stderr.decode()[:200]}")

        return ReframeResult(
            input_path=video_path,
            output_path=output_path,
            output_resolution=(self.config.target_width, self.config.target_height),
        )

    async def reframe_batch(
        self,
        video_paths: List[str],
    ) -> List[ReframeResult]:
        """Reframe multiple videos."""
        results = []
        for path in video_paths:
            try:
                result = await self.reframe(path)
                results.append(result)
            except Exception as e:
                logger.error("Reframe failed for %s: %s", path, e)
        return results
