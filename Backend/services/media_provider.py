"""
Media Provider Service
Centralized service for serving, streaming, and managing media files.
Used by frontend and other backend services.
"""
import os
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import hashlib

from fastapi import HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import create_engine, text
from loguru import logger


class MediaType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
    UNKNOWN = "unknown"


@dataclass
class MediaInfo:
    """Media file information."""
    id: str
    filename: str
    file_path: str
    media_type: MediaType
    file_size: Optional[int] = None
    duration_sec: Optional[int] = None
    resolution: Optional[str] = None
    thumbnail_path: Optional[str] = None
    mime_type: Optional[str] = None


class MediaProviderService:
    """
    Centralized media provider for the application.
    Handles:
    - Video/image file streaming
    - Thumbnail serving
    - Media metadata lookup
    - File validation
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        )
        self.engine = create_engine(self.database_url)
        
        # Default directories
        self.thumbnail_dir = Path(__file__).parent.parent / "thumbnails"
        self.thumbnail_dir.mkdir(exist_ok=True)
        
        # Supported formats
        self.video_extensions = {'.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm'}
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.webp', '.gif'}
        
        # Cache for frequently accessed media info
        self._cache: Dict[str, MediaInfo] = {}
        self._cache_ttl = 300  # 5 minutes
        
        self._initialized = True
        logger.info("MediaProviderService initialized")
    
    def get_media_type(self, filename: str) -> MediaType:
        """Determine media type from filename."""
        ext = Path(filename).suffix.lower()
        if ext in self.video_extensions:
            return MediaType.VIDEO
        elif ext in self.image_extensions:
            return MediaType.IMAGE
        elif ext in {'.mp3', '.wav', '.aac', '.m4a'}:
            return MediaType.AUDIO
        return MediaType.UNKNOWN
    
    def get_mime_type(self, file_path: str) -> str:
        """Get MIME type for a file."""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"
    
    async def get_media_info(self, media_id: str) -> Optional[MediaInfo]:
        """Get media information by ID."""
        # Check cache first
        if media_id in self._cache:
            return self._cache[media_id]
        
        with self.engine.connect() as conn:
            # Handle UUID properly - PostgreSQL requires explicit casting
            try:
                import uuid as uuid_lib
                # Validate UUID format
                try:
                    uuid_lib.UUID(media_id)  # Validate UUID format
                    # Use UUID casting for proper comparison
                    result = conn.execute(text("""
                        SELECT id, file_name, source_uri, file_size, duration_sec, 
                               resolution, thumbnail_path
                        FROM videos WHERE id = CAST(:id AS uuid)
                    """), {"id": media_id})
                except ValueError:
                    # Not a valid UUID format, try as text match (for backwards compatibility)
                    logger.warning(f"Media ID is not a valid UUID format, trying text match: {media_id}")
                    result = conn.execute(text("""
                        SELECT id, file_name, source_uri, file_size, duration_sec, 
                               resolution, thumbnail_path
                        FROM videos WHERE id::text = :id OR file_name = :id
                    """), {"id": media_id})
                
                row = result.fetchone()
            except Exception as e:
                # Database query errors should be logged as errors, not warnings
                logger.error(f"Database error querying media {media_id}: {e}", exc_info=True)
                return None
            
            if not row:
                # Media not found - this is expected in some cases (e.g., deleted media)
                # But we should log it as a warning so we know when thumbnails fail
                logger.warning(f"Media not found in videos table: {media_id} - thumbnail requests will fail")
                return None
            
            media_info = MediaInfo(
                id=str(row[0]),
                filename=row[1],
                file_path=row[2],
                media_type=self.get_media_type(row[1]),
                file_size=row[3],
                duration_sec=row[4],
                resolution=row[5],
                thumbnail_path=row[6],
                mime_type=self.get_mime_type(row[2]) if row[2] else None
            )
            
            # Cache it
            self._cache[media_id] = media_info
            return media_info
    
    async def get_media_by_filename(self, filename: str) -> Optional[MediaInfo]:
        """Get media information by filename."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, file_name, source_uri, file_size, duration_sec, 
                       resolution, thumbnail_path
                FROM videos WHERE file_name = :filename
            """), {"filename": filename})
            row = result.fetchone()
            
            if not row:
                return None
            
            return MediaInfo(
                id=str(row[0]),
                filename=row[1],
                file_path=row[2],
                media_type=self.get_media_type(row[1]),
                file_size=row[3],
                duration_sec=row[4],
                resolution=row[5],
                thumbnail_path=row[6],
                mime_type=self.get_mime_type(row[2]) if row[2] else None
            )
    
    def validate_file_exists(self, file_path: str) -> bool:
        """Check if a file exists and is readable."""
        if not file_path:
            return False
        path = Path(file_path)
        return path.exists() and path.is_file()
    
    async def get_thumbnail_response(
        self, 
        media_id: str, 
        size: str = "medium"
    ) -> FileResponse:
        """
        Get thumbnail for a media file.
        Sizes: small (160px), medium (320px), large (640px)
        Supports on-the-fly generation if thumbnail doesn't exist.
        """
        media_info = await self.get_media_info(media_id)
        
        if not media_info:
            raise HTTPException(status_code=404, detail="Media not found")
        
        # Check if thumbnail exists (try both container and host paths)
        if media_info.thumbnail_path:
            thumb_path_str = self._map_to_container_path(media_info.thumbnail_path)
            actual_thumb_path = None
            if thumb_path_str and Path(thumb_path_str).exists():
                actual_thumb_path = thumb_path_str
            elif Path(media_info.thumbnail_path).exists():
                actual_thumb_path = media_info.thumbnail_path
            
            if actual_thumb_path:
                return FileResponse(
                    actual_thumb_path,
                    media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"}
                )
        
        # Try to find thumbnail by ID
        thumb_path = self.thumbnail_dir / f"{media_id}.jpg"
        if thumb_path.exists():
            return FileResponse(
                str(thumb_path),
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=86400"}
            )
        
        # Try to generate on-the-fly from source file (like media-db does)
        if media_info.file_path:
            try:
                from services.thumbnail_service import generate_thumbnail
                # Try original path first (host), then mapped path (container)
                file_path = media_info.file_path
                if not Path(file_path).exists():
                    # Try container mapping as fallback
                    file_path = self._map_to_container_path(media_info.file_path)
                
                if file_path and Path(file_path).exists():
                    logger.info(f"Generating thumbnail on-the-fly for media {media_id} from {file_path}")
                    generated_thumb = generate_thumbnail(file_path, size)
                    if generated_thumb and Path(generated_thumb).exists():
                        # Update database with thumbnail path
                        await self._update_thumbnail_path(media_id, generated_thumb)
                        return FileResponse(
                            generated_thumb,
                            media_type="image/jpeg",
                            headers={"Cache-Control": "public, max-age=86400"}
                        )
                    else:
                        logger.warning(f"Thumbnail generation returned no file for media {media_id}")
                else:
                    logger.warning(f"Source file not found for media {media_id}: {media_info.file_path}")
            except Exception as e:
                # Log error with full context - thumbnail generation failures should be visible
                logger.error(f"Failed to generate thumbnail on-the-fly for media {media_id}: {e}", exc_info=True)
                # Continue to try other methods or return 404
        
        # No thumbnail found - log this as a warning so we know when thumbnails are missing
        logger.warning(f"Thumbnail not found for media {media_id} - tried: stored path, thumbnail dir, and on-the-fly generation")
        raise HTTPException(status_code=404, detail=f"Thumbnail not found for media {media_id}")
    
    def _map_to_container_path(self, host_path: str) -> str:
        """Map host filesystem paths to Docker container paths.
        
        Maps various host paths to Docker volume mounts:
        - ~/Documents/IphoneImport -> /media/IphoneImport
        - /Volumes/My Passport/MediaPoster/workspace1/iphone_import -> /media/IphoneImport
        """
        if not host_path:
            return host_path
        import re
        
        # Map My Passport path to container path
        passport_pattern = r'^/Volumes/My Passport/MediaPoster/workspace1/iphone_import/(.*)$'
        match = re.match(passport_pattern, host_path)
        if match:
            return f"/media/IphoneImport/{match.group(1)}"
        
        # Map old ~/Documents/IphoneImport path (legacy)
        pattern = r'^/Users/[^/]+/Documents/IphoneImport/(.*)$'
        match = re.match(pattern, host_path)
        if match:
            return f"/media/IphoneImport/{match.group(1)}"
        if host_path.startswith('~/Documents/IphoneImport/'):
            return host_path.replace('~/Documents/IphoneImport/', '/media/IphoneImport/')
        return host_path
    
    async def _update_thumbnail_path(self, media_id: str, thumbnail_path: str):
        """Update thumbnail path in database."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE videos 
                    SET thumbnail_path = :thumb_path 
                    WHERE id = :id
                """), {"thumb_path": thumbnail_path, "id": media_id})
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update thumbnail path in database: {e}")
    
    async def get_video_stream(
        self, 
        media_id: str,
        range_header: Optional[str] = None
    ) -> StreamingResponse:
        """
        Stream video file with range request support for seeking.
        """
        media_info = await self.get_media_info(media_id)
        
        if not media_info:
            raise HTTPException(status_code=404, detail="Media not found")
        
        # Map host paths to container paths if needed
        file_path_str = self._map_to_container_path(media_info.file_path) if media_info.file_path else None
        
        # Try container path first, then original path
        actual_path = None
        if file_path_str and Path(file_path_str).exists():
            actual_path = file_path_str
        elif media_info.file_path and Path(media_info.file_path).exists():
            actual_path = media_info.file_path
        
        if not actual_path:
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        file_path = Path(actual_path)
        file_size = file_path.stat().st_size
        
        # Handle range requests for video seeking
        start = 0
        end = file_size - 1
        
        if range_header:
            range_match = range_header.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1
        
        chunk_size = min(1024 * 1024, end - start + 1)  # 1MB chunks max
        
        async def file_iterator():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": media_info.mime_type or "video/mp4",
        }
        
        status_code = 206 if range_header else 200
        
        return StreamingResponse(
            file_iterator(),
            status_code=status_code,
            headers=headers,
            media_type=media_info.mime_type or "video/mp4"
        )
    
    async def get_image_response(self, media_id: str) -> FileResponse:
        """Serve an image file."""
        media_info = await self.get_media_info(media_id)
        
        if not media_info:
            raise HTTPException(status_code=404, detail="Media not found")
        
        if not self.validate_file_exists(media_info.file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            media_info.file_path,
            media_type=media_info.mime_type or "image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"}
        )
    
    async def list_media(
        self, 
        limit: int = 100, 
        offset: int = 0,
        media_type: Optional[MediaType] = None
    ) -> List[MediaInfo]:
        """List media with optional type filter."""
        with self.engine.connect() as conn:
            query = """
                SELECT id, file_name, source_uri, file_size, duration_sec, 
                       resolution, thumbnail_path
                FROM videos 
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """
            result = conn.execute(text(query), {"limit": limit, "offset": offset})
            
            media_list = []
            for row in result:
                info = MediaInfo(
                    id=str(row[0]),
                    filename=row[1],
                    file_path=row[2],
                    media_type=self.get_media_type(row[1]),
                    file_size=row[3],
                    duration_sec=row[4],
                    resolution=row[5],
                    thumbnail_path=row[6],
                    mime_type=self.get_mime_type(row[2]) if row[2] else None
                )
                
                # Filter by type if specified
                if media_type and info.media_type != media_type:
                    continue
                    
                media_list.append(info)
            
            return media_list
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get media library statistics."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN thumbnail_path IS NOT NULL THEN 1 END) as with_thumbnails,
                    SUM(COALESCE(file_size, 0)) as total_size,
                    AVG(duration_sec) as avg_duration
                FROM videos
            """))
            row = result.fetchone()
            
            return {
                "total_media": row[0],
                "with_thumbnails": row[1],
                "total_size_bytes": row[2] or 0,
                "avg_duration_sec": float(row[3]) if row[3] else None
            }
    
    def clear_cache(self):
        """Clear the media info cache."""
        self._cache.clear()
        logger.info("MediaProviderService cache cleared")


# Singleton instance
_media_provider: Optional[MediaProviderService] = None


def get_media_provider() -> MediaProviderService:
    """Get the singleton MediaProviderService instance."""
    global _media_provider
    if _media_provider is None:
        _media_provider = MediaProviderService()
    return _media_provider
