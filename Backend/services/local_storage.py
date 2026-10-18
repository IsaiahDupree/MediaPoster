"""
Local Storage Service for MediaPoster
Handles local file storage for videos, thumbnails, and clips during development
"""
import os
import shutil
from pathlib import Path
from typing import Optional
from loguru import logger

class LocalStorageService:
    """Manages local file storage for media files"""
    
    def __init__(self):
        self.enabled = os.getenv('LOCAL_STORAGE_ENABLED', 'false').lower() == 'true'
        self.base_path = Path(os.getenv('LOCAL_STORAGE_PATH', '../local_storage'))
        self.videos_path = Path(os.getenv('LOCAL_VIDEOS_PATH', '../local_storage/videos'))
        self.thumbnails_path = Path(os.getenv('LOCAL_THUMBNAILS_PATH', '../local_storage/thumbnails'))
        self.clips_path = Path(os.getenv('LOCAL_CLIPS_PATH', '../local_storage/clips'))
        self.temp_path = Path(os.getenv('LOCAL_TEMP_PATH', '../local_storage/temp'))
        
        # Create directories if they don't exist
        if self.enabled:
            for path in [self.videos_path, self.thumbnails_path, self.clips_path, self.temp_path]:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Local storage directory ensured: {path}")
    
    def save_video(self, source_path: str, video_id: str, extension: str = 'mp4') -> Optional[str]:
        """
        Save a video file to local storage
        
        Args:
            source_path: Path to the source video file
            video_id: Unique identifier for the video
            extension: File extension (without dot)
            
        Returns:
            Path to the saved file or None if disabled
        """
        if not self.enabled:
            return None
            
        dest_path = self.videos_path / f"{video_id}.{extension}"
        
        try:
            shutil.copy2(source_path, dest_path)
            logger.success(f"Video saved to local storage: {dest_path}")
            return str(dest_path)
        except Exception as e:
            logger.error(f"Failed to save video to local storage: {e}")
            return None
    
    def save_thumbnail(self, source_path: str, video_id: str) -> Optional[str]:
        """
        Save a thumbnail to local storage
        
        Args:
            source_path: Path to the source thumbnail file
            video_id: Unique identifier for the video
            
        Returns:
            Path to the saved file or None if disabled
        """
        if not self.enabled:
            return None
            
        dest_path = self.thumbnails_path / f"{video_id}_thumb.jpg"
        
        try:
            shutil.copy2(source_path, dest_path)
            logger.success(f"Thumbnail saved to local storage: {dest_path}")
            return str(dest_path)
        except Exception as e:
            logger.error(f"Failed to save thumbnail to local storage: {e}")
            return None
    
    def save_clip(self, source_path: str, clip_id: str) -> Optional[str]:
        """
        Save a clip to local storage
        
        Args:
            source_path: Path to the source clip file
            clip_id: Unique identifier for the clip
            
        Returns:
            Path to the saved file or None if disabled
        """
        if not self.enabled:
            return None
            
        dest_path = self.clips_path / f"{clip_id}.mp4"
        
        try:
            shutil.copy2(source_path, dest_path)
            logger.success(f"Clip saved to local storage: {dest_path}")
            return str(dest_path)
        except Exception as e:
            logger.error(f"Failed to save clip to local storage: {e}")
            return None
    
    def get_video_path(self, video_id: str, extension: str = 'mp4') -> Optional[Path]:
        """Get the local path for a video"""
        if not self.enabled:
            return None
        path = self.videos_path / f"{video_id}.{extension}"
        return path if path.exists() else None
    
    def get_thumbnail_path(self, video_id: str) -> Optional[Path]:
        """Get the local path for a thumbnail"""
        if not self.enabled:
            return None
        path = self.thumbnails_path / f"{video_id}_thumb.jpg"
        return path if path.exists() else None
    
    def get_clip_path(self, clip_id: str) -> Optional[Path]:
        """Get the local path for a clip"""
        if not self.enabled:
            return None
        path = self.clips_path / f"{clip_id}.mp4"
        return path if path.exists() else None
    
    def delete_video(self, video_id: str, extension: str = 'mp4') -> bool:
        """Delete a video from local storage"""
        if not self.enabled:
            return False
            
        path = self.videos_path / f"{video_id}.{extension}"
        try:
            if path.exists():
                path.unlink()
                logger.info(f"Deleted video from local storage: {path}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete video: {e}")
        return False
    
    def delete_thumbnail(self, video_id: str) -> bool:
        """Delete a thumbnail from local storage"""
        if not self.enabled:
            return False
            
        path = self.thumbnails_path / f"{video_id}_thumb.jpg"
        try:
            if path.exists():
                path.unlink()
                logger.info(f"Deleted thumbnail from local storage: {path}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete thumbnail: {e}")
        return False
    
    def delete_clip(self, clip_id: str) -> bool:
        """Delete a clip from local storage"""
        if not self.enabled:
            return False
            
        path = self.clips_path / f"{clip_id}.mp4"
        try:
            if path.exists():
                path.unlink()
                logger.info(f"Deleted clip from local storage: {path}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete clip: {e}")
        return False
    
    def cleanup_temp(self) -> int:
        """Clean up temporary files"""
        if not self.enabled:
            return 0
            
        count = 0
        try:
            for file in self.temp_path.glob('*'):
                if file.is_file():
                    file.unlink()
                    count += 1
            logger.info(f"Cleaned up {count} temporary files")
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
        return count


# Global instance
local_storage = LocalStorageService()
