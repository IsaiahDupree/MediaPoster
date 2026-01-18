"""
Video Downloader - Downloads generated videos from Sora

Handles video URL extraction, download, and local storage.
"""
import asyncio
import aiohttp
import subprocess
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from .sora_controller import SoraController


class VideoDownloader:
    """Downloads videos from Sora and manages local storage."""
    
    DEFAULT_OUTPUT_DIR = Path("output/sora_downloads")
    
    def __init__(
        self,
        controller: Optional[SoraController] = None,
        output_dir: Optional[Path] = None
    ):
        self.controller = controller or SoraController()
        self.output_dir = output_dir or self.DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_current_video(self, filename: Optional[str] = None) -> Optional[Path]:
        """
        Download the currently displayed video in Safari.
        
        Args:
            filename: Optional filename (without extension)
            
        Returns:
            Path to downloaded file or None
        """
        # Get video URL
        video_url = await self.controller.get_video_download_url()
        
        if not video_url:
            logger.error("❌ No video URL found")
            return None
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sora_video_{timestamp}"
        
        # Download the video
        return await self.download_from_url(video_url, filename)
    
    async def download_from_url(self, url: str, filename: str) -> Optional[Path]:
        """
        Download video from URL.
        
        Args:
            url: Video URL
            filename: Filename (without extension)
            
        Returns:
            Path to downloaded file or None
        """
        # Determine extension from URL or default to mp4
        ext = ".mp4"
        if ".webm" in url.lower():
            ext = ".webm"
        elif ".mov" in url.lower():
            ext = ".mov"
        
        output_path = self.output_dir / f"{filename}{ext}"
        
        logger.info(f"📥 Downloading video to {output_path}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Download failed with status {response.status}")
                        return None
                    
                    total_size = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    
                    with open(output_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                if percent % 20 < 1:  # Log every ~20%
                                    logger.debug(f"Download progress: {percent:.0f}%")
            
            file_size = output_path.stat().st_size
            logger.success(f"✅ Downloaded {output_path.name} ({file_size / 1024 / 1024:.1f} MB)")
            return output_path
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            if output_path.exists():
                output_path.unlink()
            return None
    
    async def trigger_safari_download(self) -> bool:
        """
        Trigger download through Safari's native download mechanism.
        This uses the download button if available.
        """
        success = await self.controller.click_download_button()
        
        if success:
            logger.info("⏳ Waiting for Safari download to complete...")
            # Wait for download - Safari handles this natively
            await asyncio.sleep(5)
            return True
        
        return False
    
    def get_safari_downloads_folder(self) -> Path:
        """Get Safari's default downloads folder."""
        # Default macOS downloads folder
        return Path.home() / "Downloads"
    
    async def move_from_downloads(
        self,
        filename_pattern: str = "sora",
        max_wait: int = 60
    ) -> Optional[Path]:
        """
        Wait for and move a file from Downloads folder.
        
        Args:
            filename_pattern: Pattern to match in filename
            max_wait: Maximum seconds to wait
            
        Returns:
            Path to moved file or None
        """
        downloads = self.get_safari_downloads_folder()
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < max_wait:
            # Look for recent files matching pattern
            for f in downloads.iterdir():
                if filename_pattern.lower() in f.name.lower():
                    if f.suffix.lower() in [".mp4", ".webm", ".mov"]:
                        # Check if file is still being downloaded
                        if f.name.endswith(".download"):
                            continue
                        
                        # Move to output directory
                        dest = self.output_dir / f.name
                        f.rename(dest)
                        logger.success(f"✅ Moved {f.name} to {self.output_dir}")
                        return dest
            
            await asyncio.sleep(2)
        
        logger.warning(f"⚠️ No matching file found in Downloads after {max_wait}s")
        return None
    
    def list_downloaded_videos(self) -> list:
        """List all downloaded videos in output directory."""
        videos = []
        for f in self.output_dir.iterdir():
            if f.suffix.lower() in [".mp4", ".webm", ".mov"]:
                videos.append({
                    "path": str(f),
                    "name": f.name,
                    "size_mb": f.stat().st_size / 1024 / 1024,
                    "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat()
                })
        return sorted(videos, key=lambda x: x["created"], reverse=True)
    
    def get_video_info(self, video_path: Path) -> Dict:
        """Get video metadata using ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(video_path)
                ],
                capture_output=True,
                text=True,
                check=True
            )
            import json
            data = json.loads(result.stdout)
            
            # Extract key info
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {}
            )
            
            return {
                "path": str(video_path),
                "duration": float(data.get("format", {}).get("duration", 0)),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "codec": video_stream.get("codec_name"),
                "fps": eval(video_stream.get("r_frame_rate", "0/1")),
                "size_mb": video_path.stat().st_size / 1024 / 1024
            }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {"path": str(video_path), "error": str(e)}
