"""
Supabase Storage Service for MediaPoster
Handles media file storage using Supabase Storage buckets
"""
import os
from pathlib import Path
from typing import Optional, BinaryIO
from loguru import logger
from supabase import create_client, Client

class SupabaseStorageService:
    """Manages media file storage in Supabase Storage"""
    
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL', 'http://127.0.0.1:54321')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
        self.bucket_name = os.getenv('SUPABASE_STORAGE_BUCKET', 'content')
        
        # Initialize Supabase client
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        
        logger.info(f"Supabase Storage initialized - Bucket: {self.bucket_name}")
    
    def upload_video(self, file_path: str, video_id: str, extension: str = 'mp4') -> Optional[str]:
        """
        Upload a video file to Supabase Storage
        
        Args:
            file_path: Path to the source video file
            video_id: Unique identifier for the video
            extension: File extension (without dot)
            
        Returns:
            Public URL to the uploaded file or None if failed
        """
        try:
            storage_path = f"videos/{video_id}.{extension}"
            
            with open(file_path, 'rb') as f:
                result = self.client.storage.from_(self.bucket_name).upload(
                    path=storage_path,
                    file=f,
                    file_options={"content-type": f"video/{extension}"}
                )
            
            # Get public URL
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(storage_path)
            
            logger.success(f"Video uploaded to Supabase Storage: {storage_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload video to Supabase Storage: {e}")
            return None
    
    def upload_thumbnail(self, file_path: str, video_id: str) -> Optional[str]:
        """
        Upload a thumbnail to Supabase Storage
        
        Args:
            file_path: Path to the source thumbnail file
            video_id: Unique identifier for the video
            
        Returns:
            Public URL to the uploaded file or None if failed
        """
        try:
            storage_path = f"thumbnails/{video_id}_thumb.jpg"
            
            with open(file_path, 'rb') as f:
                result = self.client.storage.from_(self.bucket_name).upload(
                    path=storage_path,
                    file=f,
                    file_options={"content-type": "image/jpeg"}
                )
            
            # Get public URL
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(storage_path)
            
            logger.success(f"Thumbnail uploaded to Supabase Storage: {storage_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload thumbnail to Supabase Storage: {e}")
            return None
    
    def upload_clip(self, file_path: str, clip_id: str) -> Optional[str]:
        """
        Upload a clip to Supabase Storage
        
        Args:
            file_path: Path to the source clip file
            clip_id: Unique identifier for the clip
            
        Returns:
            Public URL to the uploaded file or None if failed
        """
        try:
            storage_path = f"clips/{clip_id}.mp4"
            
            with open(file_path, 'rb') as f:
                result = self.client.storage.from_(self.bucket_name).upload(
                    path=storage_path,
                    file=f,
                    file_options={"content-type": "video/mp4"}
                )
            
            # Get public URL
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(storage_path)
            
            logger.success(f"Clip uploaded to Supabase Storage: {storage_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload clip to Supabase Storage: {e}")
            return None
    
    def get_video_url(self, video_id: str, extension: str = 'mp4') -> Optional[str]:
        """Get the public URL for a video"""
        storage_path = f"videos/{video_id}.{extension}"
        return self.client.storage.from_(self.bucket_name).get_public_url(storage_path)
    
    def get_thumbnail_url(self, video_id: str) -> Optional[str]:
        """Get the public URL for a thumbnail"""
        storage_path = f"thumbnails/{video_id}_thumb.jpg"
        return self.client.storage.from_(self.bucket_name).get_public_url(storage_path)
    
    def get_clip_url(self, clip_id: str) -> Optional[str]:
        """Get the public URL for a clip"""
        storage_path = f"clips/{clip_id}.mp4"
        return self.client.storage.from_(self.bucket_name).get_public_url(storage_path)
    
    def delete_video(self, video_id: str, extension: str = 'mp4') -> bool:
        """Delete a video from Supabase Storage"""
        try:
            storage_path = f"videos/{video_id}.{extension}"
            self.client.storage.from_(self.bucket_name).remove([storage_path])
            logger.info(f"Deleted video from Supabase Storage: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete video: {e}")
            return False
    
    def delete_thumbnail(self, video_id: str) -> bool:
        """Delete a thumbnail from Supabase Storage"""
        try:
            storage_path = f"thumbnails/{video_id}_thumb.jpg"
            self.client.storage.from_(self.bucket_name).remove([storage_path])
            logger.info(f"Deleted thumbnail from Supabase Storage: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete thumbnail: {e}")
            return False
    
    def delete_clip(self, clip_id: str) -> bool:
        """Delete a clip from Supabase Storage"""
        try:
            storage_path = f"clips/{clip_id}.mp4"
            self.client.storage.from_(self.bucket_name).remove([storage_path])
            logger.info(f"Deleted clip from Supabase Storage: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete clip: {e}")
            return False
    
    def list_videos(self, limit: int = 100) -> list:
        """List all videos in storage"""
        try:
            result = self.client.storage.from_(self.bucket_name).list('videos', {
                'limit': limit,
                'sortBy': {'column': 'created_at', 'order': 'desc'}
            })
            return result
        except Exception as e:
            logger.error(f"Failed to list videos: {e}")
            return []


# Global instance
supabase_storage = SupabaseStorageService()
