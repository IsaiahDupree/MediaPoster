"""
Storage Service - Unified interface for media storage
Automatically uses Supabase Storage (content bucket) when available
"""
import os
from typing import Optional
from loguru import logger

# Import based on configuration
USE_SUPABASE = os.getenv('USE_SUPABASE_STORAGE', 'true').lower() == 'true'

if USE_SUPABASE:
    from services.supabase_storage import supabase_storage as _storage
    logger.info("📦 Using Supabase Storage (content bucket)")
else:
    from services.local_storage import local_storage as _storage
    logger.info("📁 Using Local File Storage")


class StorageService:
    """Unified storage interface - delegates to Supabase or local storage"""
    
    def __init__(self):
        self.backend = _storage
        self.using_supabase = USE_SUPABASE
    
    def upload_video(self, file_path: str, video_id: str, extension: str = 'mp4') -> Optional[str]:
        """Upload a video and return its URL/path"""
        if self.using_supabase:
            return self.backend.upload_video(file_path, video_id, extension)
        else:
            return self.backend.save_video(file_path, video_id, extension)
    
    def upload_thumbnail(self, file_path: str, video_id: str) -> Optional[str]:
        """Upload a thumbnail and return its URL/path"""
        if self.using_supabase:
            return self.backend.upload_thumbnail(file_path, video_id)
        else:
            return self.backend.save_thumbnail(file_path, video_id)
    
    def upload_clip(self, file_path: str, clip_id: str) -> Optional[str]:
        """Upload a clip and return its URL/path"""
        if self.using_supabase:
            return self.backend.upload_clip(file_path, clip_id)
        else:
            return self.backend.save_clip(file_path, clip_id)
    
    def get_video_url(self, video_id: str, extension: str = 'mp4') -> Optional[str]:
        """Get the URL/path for a video"""
        if self.using_supabase:
            return self.backend.get_video_url(video_id, extension)
        else:
            path = self.backend.get_video_path(video_id, extension)
            return str(path) if path else None
    
    def get_thumbnail_url(self, video_id: str) -> Optional[str]:
        """Get the URL/path for a thumbnail"""
        if self.using_supabase:
            return self.backend.get_thumbnail_url(video_id)
        else:
            path = self.backend.get_thumbnail_path(video_id)
            return str(path) if path else None
    
    def get_clip_url(self, clip_id: str) -> Optional[str]:
        """Get the URL/path for a clip"""
        if self.using_supabase:
            return self.backend.get_clip_url(clip_id)
        else:
            path = self.backend.get_clip_path(clip_id)
            return str(path) if path else None
    
    def delete_video(self, video_id: str, extension: str = 'mp4') -> bool:
        """Delete a video"""
        return self.backend.delete_video(video_id, extension)
    
    def delete_thumbnail(self, video_id: str) -> bool:
        """Delete a thumbnail"""
        return self.backend.delete_thumbnail(video_id)
    
    def delete_clip(self, clip_id: str) -> bool:
        """Delete a clip"""
        return self.backend.delete_clip(clip_id)


# Global storage instance - use this throughout the app
storage = StorageService()
