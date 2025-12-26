"""
Audio Service
Fetches, stores, and serves Instagram audio/music files via RapidAPI.
"""
import os
import hashlib
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from pydantic import BaseModel


# Audio storage directory
AUDIO_STORAGE_DIR = Path("/tmp/mediaposter/audio")
AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class AudioMetadata(BaseModel):
    """Audio file metadata"""
    audio_id: str
    title: str
    artist: str
    duration_ms: Optional[int] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    audio_url: Optional[str] = None
    cover_url: Optional[str] = None
    source: str = "instagram"
    downloaded_at: Optional[str] = None


class AudioService:
    """
    Service for fetching and storing Instagram audio files.
    Uses RapidAPI instagram-looter2 or similar APIs.
    """
    
    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.host = "instagram-looter2.p.rapidapi.com"
        self.base_url = f"https://{self.host}"
        self.timeout = 30.0
        self.storage_dir = AUDIO_STORAGE_DIR
        
        # Cache for audio metadata
        self._audio_cache: Dict[str, AudioMetadata] = {}
        
        if not self.api_key:
            logger.warning("RAPIDAPI_KEY not set - audio fetching will fail")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get RapidAPI headers"""
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host
        }
    
    def _get_audio_filename(self, audio_id: str, title: str) -> str:
        """Generate safe filename for audio file"""
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))[:50]
        return f"{audio_id}_{safe_title}.mp3"
    
    def _get_audio_path(self, audio_id: str, title: str = "audio") -> Path:
        """Get local storage path for audio file"""
        filename = self._get_audio_filename(audio_id, title)
        return self.storage_dir / filename
    
    def get_stored_audio_path(self, audio_id: str) -> Optional[Path]:
        """Check if audio is already stored locally"""
        # Search for any file starting with this audio_id
        for file in self.storage_dir.glob(f"{audio_id}_*"):
            if file.is_file():
                return file
        return None
    
    async def fetch_audio_from_reel(self, reel_url: str) -> Optional[AudioMetadata]:
        """
        Fetch audio information and URL from an Instagram reel.
        
        Args:
            reel_url: Instagram reel URL or shortcode
            
        Returns:
            AudioMetadata with audio_url if available
        """
        if not self.api_key:
            logger.error("Cannot fetch audio: RAPIDAPI_KEY not configured")
            return None
            
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Fetch reel/post info which includes audio data
                response = await client.get(
                    f"{self.base_url}/v1/post",
                    params={"code_or_id_or_url": reel_url},
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                
                post_data = data.get("data", {})
                
                # Extract audio info from the response
                audio_info = self._extract_audio_from_post(post_data)
                
                if audio_info:
                    logger.info(f"Found audio: {audio_info.title} by {audio_info.artist}")
                    return audio_info
                    
                logger.warning(f"No audio found in reel: {reel_url}")
                return None
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching reel audio: {e}")
                return None
            except Exception as e:
                logger.error(f"Error fetching reel audio: {e}")
                return None
    
    def _extract_audio_from_post(self, post_data: Dict[str, Any]) -> Optional[AudioMetadata]:
        """Extract audio metadata from post/reel data"""
        # Try different paths for audio data in Instagram API response
        clips_metadata = post_data.get("clips_metadata", {})
        music_info = clips_metadata.get("music_info", {})
        audio_asset = clips_metadata.get("audio_asset_id")
        original_sound = clips_metadata.get("original_sound_info", {})
        
        # Check for music track
        if music_info:
            music_asset = music_info.get("music_asset_info", {})
            return AudioMetadata(
                audio_id=str(music_asset.get("audio_id", music_asset.get("id", ""))),
                title=music_asset.get("title", "Unknown Track"),
                artist=music_asset.get("display_artist", music_asset.get("artist", "Unknown")),
                duration_ms=music_asset.get("duration_in_ms"),
                audio_url=music_asset.get("progressive_download_url") or music_asset.get("dash_manifest"),
                cover_url=music_asset.get("cover_artwork_uri") or music_asset.get("cover_artwork_thumbnail_uri")
            )
        
        # Check for original sound
        if original_sound:
            audio_asset_info = original_sound.get("audio_asset_info", {})
            return AudioMetadata(
                audio_id=str(original_sound.get("audio_id", audio_asset_info.get("audio_id", ""))),
                title=original_sound.get("original_audio_title", "Original Sound"),
                artist=original_sound.get("ig_artist", {}).get("username", "Unknown"),
                duration_ms=audio_asset_info.get("duration_in_ms"),
                audio_url=audio_asset_info.get("progressive_download_url")
            )
        
        # Check video URL as fallback for audio
        video_versions = post_data.get("video_versions", [])
        if video_versions:
            return AudioMetadata(
                audio_id=str(post_data.get("id", post_data.get("pk", ""))),
                title=post_data.get("caption", {}).get("text", "Video Audio")[:50] if post_data.get("caption") else "Video Audio",
                artist="Instagram",
                audio_url=video_versions[0].get("url")
            )
        
        return None
    
    async def download_audio(self, audio_metadata: AudioMetadata) -> Optional[Path]:
        """
        Download audio file and store locally.
        
        Args:
            audio_metadata: Audio metadata with audio_url
            
        Returns:
            Path to downloaded file or None if failed
        """
        if not audio_metadata.audio_url:
            logger.error("No audio URL provided")
            return None
        
        # Check if already downloaded
        existing = self.get_stored_audio_path(audio_metadata.audio_id)
        if existing:
            logger.info(f"Audio already downloaded: {existing}")
            return existing
        
        file_path = self._get_audio_path(audio_metadata.audio_id, audio_metadata.title)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                logger.info(f"Downloading audio: {audio_metadata.title}")
                response = await client.get(audio_metadata.audio_url)
                response.raise_for_status()
                
                # Write to file
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                # Update metadata
                audio_metadata.file_path = str(file_path)
                audio_metadata.file_size = len(response.content)
                audio_metadata.downloaded_at = datetime.now().isoformat()
                
                # Cache the metadata
                self._audio_cache[audio_metadata.audio_id] = audio_metadata
                
                logger.info(f"Audio downloaded: {file_path} ({audio_metadata.file_size} bytes)")
                return file_path
                
            except Exception as e:
                logger.error(f"Error downloading audio: {e}")
                return None
    
    async def fetch_and_store_audio(self, reel_url: str) -> Optional[AudioMetadata]:
        """
        Complete flow: fetch audio info from reel and download it.
        
        Args:
            reel_url: Instagram reel URL
            
        Returns:
            AudioMetadata with local file_path if successful
        """
        audio_info = await self.fetch_audio_from_reel(reel_url)
        if not audio_info:
            return None
        
        # Check if already downloaded
        existing = self.get_stored_audio_path(audio_info.audio_id)
        if existing:
            audio_info.file_path = str(existing)
            audio_info.file_size = existing.stat().st_size
            return audio_info
        
        # Download the audio
        file_path = await self.download_audio(audio_info)
        if file_path:
            audio_info.file_path = str(file_path)
            return audio_info
        
        return None
    
    def get_audio_metadata(self, audio_id: str) -> Optional[AudioMetadata]:
        """Get cached audio metadata"""
        return self._audio_cache.get(audio_id)
    
    def list_stored_audio(self) -> List[Dict[str, Any]]:
        """List all locally stored audio files"""
        audio_files = []
        for file in self.storage_dir.glob("*.mp3"):
            audio_files.append({
                "filename": file.name,
                "path": str(file),
                "size": file.stat().st_size,
                "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
        return audio_files


# Singleton instance
_audio_service: Optional[AudioService] = None


def get_audio_service() -> AudioService:
    """Get singleton audio service instance"""
    global _audio_service
    if _audio_service is None:
        _audio_service = AudioService()
    return _audio_service
