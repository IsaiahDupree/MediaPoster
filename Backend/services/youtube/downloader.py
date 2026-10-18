"""
YTP-018: yt-dlp Video Downloader
Downloads YouTube videos using yt-dlp with configurable quality and format options.
"""
import logging
import subprocess
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = "/tmp/mediaposter/downloads"


@dataclass
class DownloadResult:
    """Result of a video download."""
    video_id: str
    title: str
    file_path: str
    duration_seconds: float
    file_size_bytes: int
    format_id: str
    resolution: Optional[str] = None
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    upload_date: Optional[str] = None
    channel: Optional[str] = None
    downloaded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class YTDLPDownloader:
    """
    Downloads YouTube videos using yt-dlp.

    Features:
    - Configurable output directory and format
    - Video metadata extraction
    - Progress callback support
    - Audio-only download option for transcription
    """

    def __init__(
        self,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        yt_dlp_path: str = "yt-dlp",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.yt_dlp_path = yt_dlp_path

    async def download(
        self,
        url: str,
        format_spec: str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        audio_only: bool = False,
    ) -> DownloadResult:
        """
        Download a YouTube video.

        Args:
            url: YouTube URL
            format_spec: yt-dlp format specification
            audio_only: If True, download audio only

        Returns:
            DownloadResult with file path and metadata
        """
        if audio_only:
            format_spec = "bestaudio[ext=m4a]/bestaudio"

        output_template = str(self.output_dir / "%(id)s.%(ext)s")

        cmd = [
            self.yt_dlp_path,
            "-f", format_spec,
            "-o", output_template,
            "--write-info-json",
            "--no-playlist",
            url,
        ]

        logger.info("Downloading: %s", url)

        import asyncio
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            logger.error("yt-dlp failed: %s", error_msg)
            raise RuntimeError(f"yt-dlp download failed: {error_msg}")

        # Parse info json
        info = await self.get_video_info(url)

        video_id = info.get("id", "unknown")
        ext = info.get("ext", "mp4")
        file_path = str(self.output_dir / f"{video_id}.{ext}")

        return DownloadResult(
            video_id=video_id,
            title=info.get("title", ""),
            file_path=file_path,
            duration_seconds=float(info.get("duration", 0)),
            file_size_bytes=info.get("filesize", 0) or 0,
            format_id=info.get("format_id", ""),
            resolution=info.get("resolution"),
            thumbnail_url=info.get("thumbnail"),
            description=info.get("description"),
            upload_date=info.get("upload_date"),
            channel=info.get("channel"),
        )

    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video metadata without downloading.

        Args:
            url: YouTube URL

        Returns:
            Dict with video metadata
        """
        cmd = [
            self.yt_dlp_path,
            "--dump-json",
            "--no-download",
            "--no-playlist",
            url,
        ]

        import asyncio
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Failed to get video info: {stderr.decode().strip()}")

        return json.loads(stdout.decode())

    async def download_audio(self, url: str) -> DownloadResult:
        """Download audio only (for transcription)."""
        return await self.download(url, audio_only=True)

    def get_downloaded_files(self) -> List[Path]:
        """List all downloaded files."""
        return sorted(self.output_dir.glob("*.*"))
