"""
YTP-016: Video Duration Router
Routes videos to appropriate transcription pipelines based on duration.
Short videos (<= 25 minutes) go to Whisper API.
Long videos (> 25 minutes) are split into chunks for local transcription.
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Duration threshold in seconds (25 minutes)
SHORT_VIDEO_THRESHOLD = 25 * 60


@dataclass
class RouteDecision:
    """Routing decision for a video."""
    video_id: str
    duration_seconds: float
    route: str  # "whisper_api" or "local_chunked"
    chunk_count: int = 1
    chunk_duration: int = 600  # 10 min chunks for long videos
    metadata: Optional[Dict[str, Any]] = None


class DurationRouter:
    """
    Routes videos to the optimal transcription pipeline based on duration.

    - Short videos (<= 25 min): Whisper API (faster, costs per-minute)
    - Long videos (> 25 min): Local chunked transcription (slower, no API cost)
    """

    def __init__(self, threshold_seconds: int = SHORT_VIDEO_THRESHOLD):
        self.threshold_seconds = threshold_seconds
        logger.info(
            "DurationRouter initialized with threshold=%ds (%d min)",
            threshold_seconds,
            threshold_seconds // 60,
        )

    def route(self, video_id: str, duration_seconds: float) -> RouteDecision:
        """
        Determine the best transcription route for a video.

        Args:
            video_id: Unique video identifier
            duration_seconds: Video duration in seconds

        Returns:
            RouteDecision with routing information
        """
        if duration_seconds <= self.threshold_seconds:
            decision = RouteDecision(
                video_id=video_id,
                duration_seconds=duration_seconds,
                route="whisper_api",
                chunk_count=1,
            )
            logger.info(
                "Video %s routed to whisper_api (%.1f min)",
                video_id,
                duration_seconds / 60,
            )
        else:
            chunk_duration = 600  # 10-minute chunks
            chunk_count = int(duration_seconds // chunk_duration) + (
                1 if duration_seconds % chunk_duration > 0 else 0
            )
            decision = RouteDecision(
                video_id=video_id,
                duration_seconds=duration_seconds,
                route="local_chunked",
                chunk_count=chunk_count,
                chunk_duration=chunk_duration,
            )
            logger.info(
                "Video %s routed to local_chunked (%.1f min, %d chunks)",
                video_id,
                duration_seconds / 60,
                chunk_count,
            )

        return decision

    def get_duration_from_file(self, file_path: str) -> Optional[float]:
        """
        Get video duration using ffprobe.

        Args:
            file_path: Path to video file

        Returns:
            Duration in seconds, or None if unable to determine
        """
        import subprocess

        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception as e:
            logger.error("Failed to get duration for %s: %s", file_path, e)

        return None
