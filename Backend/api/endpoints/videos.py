"""
Videos API Endpoints
Manage original videos and clips
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
import os
from pathlib import Path

from database.connection import get_db
from database.models import OriginalVideo, Clip
from config import settings
from services.thumbnail_generator import ThumbnailGenerator
from loguru import logger

router = APIRouter()


# Pydantic models
class VideoResponse(BaseModel):
    id: uuid.UUID
    file_name: Optional[str] = None
    duration_sec: Optional[float] = None
    source_type: str
    source_uri: str
    created_at: datetime
    thumbnail_path: Optional[str] = None
    thumbnail_generated_at: Optional[datetime] = None
    resolution: Optional[str] = None
    aspect_ratio: Optional[str] = None
    
    class Config:
        from_attributes = True


class ClipResponse(BaseModel):
    clip_id: uuid.UUID
    parent_video_id: uuid.UUID
    segment_start_seconds: float
    segment_end_seconds: float
    clip_duration_seconds: float
    hook_text: Optional[str]
    caption_text: Optional[str]
    clip_status: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[VideoResponse])
async def list_videos(
    skip: int = 0,
    limit: int = 50,  # Default page size
    search: Optional[str] = None,
    source_type: Optional[str] = None,
    media_type: Optional[str] = None,  # video, image
    sort_by: Optional[str] = "created_at",  # created_at, file_size, duration_sec, file_name
    sort_order: Optional[str] = "desc",  # asc, desc
    min_duration: Optional[int] = None,  # seconds
    max_duration: Optional[int] = None,  # seconds
    min_size: Optional[int] = None,  # bytes
    max_size: Optional[int] = None,  # bytes
    has_thumbnail: Optional[bool] = None,
    has_analysis: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List videos with advanced pagination, filtering, and sorting
    
    Filters:
    - search: Search in file_name and source_uri
    - source_type: Filter by source (local, gdrive, supabase)
    - media_type: Filter by type (video, image)
    - min_duration/max_duration: Duration range in seconds
    - min_size/max_size: File size range in bytes
    - has_thumbnail: Only files with/without thumbnails
    - has_analysis: Only files with/without AI analysis
    
    Sorting:
    - sort_by: created_at, file_size, duration_sec, file_name, updated_at
    - sort_order: asc or desc
    """
    from sqlalchemy import select, func, or_, and_, asc, desc
    from database.models import Video, VideoAnalysis
    
    # Base query
    query = select(Video)
    
    # Search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Video.file_name.ilike(search_pattern),
                Video.source_uri.ilike(search_pattern)
            )
        )
    
    # Source type filter
    if source_type:
        query = query.filter(Video.source_type == source_type)
    
    # Media type filter (video vs image based on extension)
    if media_type:
        if media_type == "video":
            video_extensions = ('.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm')
            conditions = [Video.file_name.ilike(f'%{ext}') for ext in video_extensions]
            query = query.filter(or_(*conditions))
        elif media_type == "image":
            image_extensions = ('.jpg', '.jpeg', '.png', '.heic', '.heif', '.gif', '.webp', '.bmp')
            conditions = [Video.file_name.ilike(f'%{ext}') for ext in image_extensions]
            query = query.filter(or_(*conditions))
    
    # Duration range filters
    if min_duration is not None:
        query = query.filter(Video.duration_sec >= min_duration)
    if max_duration is not None:
        query = query.filter(Video.duration_sec <= max_duration)
    
    # File size range filters
    if min_size is not None:
        query = query.filter(Video.file_size >= min_size)
    if max_size is not None:
        query = query.filter(Video.file_size <= max_size)
    
    # Thumbnail filter
    if has_thumbnail is not None:
        if has_thumbnail:
            query = query.filter(Video.thumbnail_path.isnot(None))
        else:
            query = query.filter(Video.thumbnail_path.is_(None))
    
    # Analysis filter (join with VideoAnalysis)
    if has_analysis is not None:
        from sqlalchemy.orm import selectinload
        if has_analysis:
            query = query.join(VideoAnalysis, Video.id == VideoAnalysis.video_id, isouter=False)
        else:
            # Left join and filter where analysis is null
            query = query.outerjoin(VideoAnalysis, Video.id == VideoAnalysis.video_id)
            query = query.filter(VideoAnalysis.video_id.is_(None))
    
    # Sorting
    valid_sort_fields = {
        'created_at': Video.created_at,
        'updated_at': Video.updated_at,
        'file_name': Video.file_name,
        'file_size': Video.file_size,
        'duration_sec': Video.duration_sec
    }
    
    sort_field = valid_sort_fields.get(sort_by, Video.created_at)
    
    if sort_order == "asc":
        query = query.order_by(asc(sort_field))
    else:
        query = query.order_by(desc(sort_field))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    videos = result.scalars().all()
    
    return videos


@router.get("/count")
async def count_videos(
    search: Optional[str] = None,
    source_type: Optional[str] = None,
    media_type: Optional[str] = None,
    min_duration: Optional[int] = None,
    max_duration: Optional[int] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    has_thumbnail: Optional[bool] = None,
    has_analysis: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get total count of videos matching filters (for pagination)"""
    from sqlalchemy import select, func, or_
    from database.models import Video, VideoAnalysis
    
    # Base query
    query = select(func.count(Video.id))
    
    # Apply same filters as list_videos
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Video.file_name.ilike(search_pattern),
                Video.source_uri.ilike(search_pattern)
            )
        )
    
    if source_type:
        query = query.filter(Video.source_type == source_type)
    
    # Media type filter
    if media_type:
        if media_type == "video":
            video_extensions = ('.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm')
            conditions = [Video.file_name.ilike(f'%{ext}') for ext in video_extensions]
            query = query.filter(or_(*conditions))
        elif media_type == "image":
            image_extensions = ('.jpg', '.jpeg', '.png', '.heic', '.heif', '.gif', '.webp', '.bmp')
            conditions = [Video.file_name.ilike(f'%{ext}') for ext in image_extensions]
            query = query.filter(or_(*conditions))
    
    # Duration filters
    if min_duration is not None:
        query = query.filter(Video.duration_sec >= min_duration)
    if max_duration is not None:
        query = query.filter(Video.duration_sec <= max_duration)
    
    # Size filters
    if min_size is not None:
        query = query.filter(Video.file_size >= min_size)
    if max_size is not None:
        query = query.filter(Video.file_size <= max_size)
    
    # Thumbnail filter
    if has_thumbnail is not None:
        if has_thumbnail:
            query = query.filter(Video.thumbnail_path.isnot(None))
        else:
            query = query.filter(Video.thumbnail_path.is_(None))
    
    # Analysis filter
    if has_analysis is not None:
        if has_analysis:
            query = query.join(VideoAnalysis, Video.id == VideoAnalysis.video_id, isouter=False)
        else:
            query = query.outerjoin(VideoAnalysis, Video.id == VideoAnalysis.video_id)
            query = query.filter(VideoAnalysis.video_id.is_(None))
    
    result = await db.execute(query)
    total = result.scalar()
    
    return {"total": total}


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific video"""
    from sqlalchemy import select
    from database.models import Video
    
    result = await db.execute(
        select(Video).filter(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return video


@router.get("/{video_id}/summary")
async def get_video_summary(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get video summary including clip count and performance metrics
    Used for dashboard widgets and video library cards
    """
    from sqlalchemy import select, func, text
    from database.models import Video
    
    # Get clip count
    clip_count_query = text("""
        SELECT COUNT(*) 
        FROM clips
        WHERE parent_video_id = :video_id
    """)
    
    # Get performance across platforms (if content_items exist for this video)
    performance_query = text("""
        SELECT 
            COALESCE(SUM(cm.views), 0) as total_views,
            COALESCE(SUM(cm.likes + cm.comments + cm.shares), 0) as total_engagement,
            ARRAY_AGG(DISTINCT cv.platform) FILTER (WHERE cv.platform IS NOT NULL) as platforms
        FROM content_items ci
        JOIN content_variants cv ON ci.id = cv.content_id
        LEFT JOIN content_metrics cm ON cv.id = cm.variant_id
        WHERE ci.source_video_id = :video_id
    """)
    
    # Execute queries
    clip_count_result = await db.execute(clip_count_query, {"video_id": str(video_id)})
    clip_count = clip_count_result.scalar() or 0
    
    performance_result = await db.execute(performance_query, {"video_id": str(video_id)})
    performance = performance_result.first()
    
    total_views = int(performance.total_views) if performance and performance.total_views else 0
    total_engagement = int(performance.total_engagement) if performance and performance.total_engagement else 0
    platforms = performance.platforms if performance and performance.platforms else []
    
    # Calculate engagement rate
    engagement_rate = (total_engagement / total_views * 100) if total_views > 0 else 0
    
    return {
        "video_id": str(video_id),
        "clip_count": int(clip_count),
        "total_views": total_views,
        "total_engagement": total_engagement,
        "platforms": platforms,
        "engagement_rate": round(engagement_rate, 2)
    }


@router.get("/{video_id}/clips", response_model=List[ClipResponse])
async def get_video_clips(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all clips for a video"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Clip)
        .filter(Clip.parent_video_id == video_id)
        .order_by(Clip.segment_start_seconds)
    )
    clips = result.scalars().all()
    
    return clips


@router.delete("/{video_id}")
async def delete_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a video and all its clips"""
    from sqlalchemy import delete
    
    # Check if video exists
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete video (clips will be cascade deleted)
    await db.execute(
        delete(OriginalVideo).where(OriginalVideo.video_id == video_id)
    )
    await db.commit()
    
    return {"message": "Video deleted successfully"}


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    source: str = "manual_upload",
    db: AsyncSession = Depends(get_db)
):
    """Upload a video file"""
    from pathlib import Path
    import shutil
    from modules.video_ingestion.video_validator import VideoValidator
    
    # Validate file type
    if not file.filename.lower().endswith(('.mp4', '.mov', '.m4v', '.avi', '.mkv')):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    # Save uploaded file temporarily
    temp_path = Path(settings.temp_dir) / file.filename
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Validate video
        validator = VideoValidator()
        is_valid, error, metadata = validator.validate(temp_path)
        
        if not is_valid:
            temp_path.unlink()
            raise HTTPException(status_code=400, detail=f"Invalid video: {error}")
        
        # Create database record
        from database.models import Video
        import uuid
        
        # Use a placeholder user ID until auth is fully implemented
        # This matches the placeholder used in scan_directory
        current_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        
        # Map source to allowed values
        valid_source_type = source if source in ['local', 'gdrive', 'supabase', 's3', 'other'] else 'local'
        
        video = Video(
            id=uuid.uuid4(),
            user_id=current_user_id,
            source_type=valid_source_type,
            source_uri=str(temp_path),
            file_name=file.filename,
            duration_sec=int(metadata['duration']),
            resolution=f"{metadata.get('width')}x{metadata.get('height')}",
            aspect_ratio=str(metadata.get('width') / metadata.get('height')) if metadata.get('height') else None
        )
        
        db.add(video)
        await db.commit()
        await db.refresh(video)
        
        return {
            "message": "Video uploaded successfully",
            "video_id": str(video.id),
            "file_name": file.filename,
            "duration": metadata['duration']
        }
        
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

class ScanRequest(BaseModel):
    path: str

# Global scan state for cancellation support
_active_scans = {}

@router.post("/scan")
async def scan_directory(
    request: ScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000000") # Placeholder for auth
):
    """
    Scan a local directory for videos and images with detailed progress logging
    Supports duplicate detection and scan cancellation
    """
    import os
    from pathlib import Path
    from loguru import logger
    import time
    
    scan_id = str(uuid.uuid4())
    _active_scans[scan_id] = {"cancelled": False, "status": "starting"}
    
    try:
        # Expand user path
        scan_path = os.path.expanduser(request.path)
        path_obj = Path(scan_path)
        
        logger.info(f"[Video Scan] Starting scan with ID: {scan_id}")
        logger.info(f"[Video Scan] Target directory: {scan_path}")
        
        if not path_obj.exists() or not path_obj.is_dir():
            logger.error(f"[Video Scan] Invalid directory: {scan_path}")
            raise HTTPException(status_code=400, detail=f"Directory not found: {scan_path}")
        
        # Supported media extensions (videos and images)
        video_extensions = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.gif', '.webp', '.bmp'}
        supported_extensions = video_extensions | image_extensions
        
        logger.info(f"[Video Scan] Scanning for extensions: {', '.join(sorted(supported_extensions))}")
        
        # Phase 1: Discover files
        _active_scans[scan_id]["status"] = "discovering"
        logger.info(f"[Video Scan] Phase 1: Discovering media files...")
        
        found_files = []
        video_count = 0
        image_count = 0
        start_time = time.time()
        
        for root, dirs, files in os.walk(scan_path):
            # Check for cancellation
            if _active_scans[scan_id]["cancelled"]:
                logger.warning(f"[Video Scan] Scan cancelled by user")
                return {"message": "Scan cancelled", "scan_id": scan_id, "cancelled": True}
            
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                ext = Path(file).suffix.lower()
                if ext in supported_extensions:
                    full_path = os.path.join(root, file)
                    found_files.append(full_path)
                    
                    if ext in video_extensions:
                        video_count += 1
                    else:
                        image_count += 1
                    
                    # Log progress every 100 files
                    if len(found_files) % 100 == 0:
                        logger.info(f"[Video Scan] Progress: {len(found_files)} files discovered...")
        
        discovery_time = time.time() - start_time
        logger.success(f"[Video Scan] Discovery complete!")
        logger.info(f"[Video Scan] Results:")
        logger.info(f"  - Total files found: {len(found_files)}")
        logger.info(f"  - Videos: {video_count}")
        logger.info(f"  - Images: {image_count}")
        logger.info(f"  - Duration: {discovery_time:.2f}s")
        
        if not found_files:
            logger.warning(f"[Video Scan] No media files found in directory")
            return {
                "message": "No media files found in the specified directory",
                "scan_id": scan_id,
                "stats": {
                    "total_found": 0,
                    "videos": 0,
                    "images": 0,
                    "duplicates": 0,
                    "new_added": 0
                }
            }
        
        # Phase 2: Check for duplicates
        _active_scans[scan_id]["status"] = "checking_duplicates"
        logger.info(f"[Video Scan] Phase 2: Checking for duplicates...")
        
        from sqlalchemy import select
        from database.models import Video
        
        # Get all existing URIs for this user
        result = await db.execute(
            select(Video.source_uri).filter(Video.user_id == current_user_id)
        )
        existing_uris = set(result.scalars().all())
        logger.info(f"[Video Scan] Found {len(existing_uris)} existing media files in database")
        
        # Separate new vs duplicate files
        new_files = []
        duplicate_files = []
        
        for file_path in found_files:
            if _active_scans[scan_id]["cancelled"]:
                logger.warning(f"[Video Scan] Scan cancelled by user")
                return {"message": "Scan cancelled", "scan_id": scan_id, "cancelled": True}
            
            if file_path in existing_uris:
                duplicate_files.append(file_path)
            else:
                new_files.append(file_path)
        
        logger.info(f"[Video Scan] Duplicate check complete:")
        logger.info(f"  - New files: {len(new_files)}")
        logger.info(f"  - Duplicates (skipped): {len(duplicate_files)}")
        
        # Phase 3: Add new files to database
        if new_files:
            _active_scans[scan_id]["status"] = "importing"
            logger.info(f"[Video Scan] Phase 3: Adding {len(new_files)} new files to database...")
            
            # Create video objects
            new_videos = []
            for file_path in new_files:
                if _active_scans[scan_id]["cancelled"]:
                    logger.warning(f"[Video Scan] Scan cancelled by user")
                    return {"message": "Scan cancelled", "scan_id": scan_id, "cancelled": True}
                
                file_name = os.path.basename(file_path)
                try:
                    # Get file size if available
                    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
                    
                    new_videos.append(Video(
                        user_id=current_user_id,
                        source_type="local",
                        source_uri=file_path,
                        file_name=file_name,
                        file_size=file_size
                    ))
                except Exception as e:
                    logger.warning(f"[Video Scan] Could not process {file_name}: {e}")
            
            # Batch insert to avoid timeouts
            BATCH_SIZE = 500
            total_added = 0
            
            for i in range(0, len(new_videos), BATCH_SIZE):
                if _active_scans[scan_id]["cancelled"]:
                    logger.warning(f"[Video Scan] Scan cancelled by user")
                    await db.rollback()
                    return {"message": "Scan cancelled", "scan_id": scan_id, "cancelled": True}
                
                batch = new_videos[i:i + BATCH_SIZE]
                db.add_all(batch)
                await db.commit()
                total_added += len(batch)
                
                progress_pct = (total_added / len(new_videos)) * 100
                logger.info(f"[Video Scan] Import progress: {total_added}/{len(new_videos)} ({progress_pct:.1f}%)")
            
            logger.success(f"[Video Scan] Successfully added {total_added} new media files!")
        else:
            logger.info(f"[Video Scan] No new files to add - all files already in database")
        
        # Final summary
        total_time = time.time() - start_time
        logger.success(f"[Video Scan] Scan complete!")
        logger.info(f"[Video Scan] Summary:")
        logger.info(f"  - Total files found: {len(found_files)}")
        logger.info(f"  - New videos added: {len(new_files)}")
        logger.info(f"  - Duplicates skipped: {len(duplicate_files)}")
        logger.info(f"  - Duration: {total_time:.2f}s")
        
        return {
            "message": f"Scan complete! Found {len(found_files)} files, added {len(new_files)} new videos",
            "scan_id": scan_id,
            "stats": {
                "total_found": len(found_files),
                "videos": video_count,
                "images": image_count,
                "duplicates": len(duplicate_files),
                "new_added": len(new_files),
                "duration_seconds": round(total_time, 2)
            }
        }
    
    finally:
        # Clean up scan state
        if scan_id in _active_scans:
            del _active_scans[scan_id]


@router.post("/scan/cancel/{scan_id}")
async def cancel_scan(scan_id: str):
    """Cancel an active directory scan"""
    if scan_id not in _active_scans:
        raise HTTPException(status_code=404, detail="Scan not found or already completed")
    
    _active_scans[scan_id]["cancelled"] = True
    logger.warning(f"[Video Scan] Cancellation requested for scan {scan_id}")
    
    return {"message": "Scan cancellation requested", "scan_id": scan_id}


@router.get("/scan/status")
async def get_scan_status():
    """Get status of all active scans"""
    return {
        "active_scans": [
            {"scan_id": scan_id, **details} 
            for scan_id, details in _active_scans.items()
        ]
    }


# ==================== Thumbnail Generation ====================

@router.post("/{video_id}/generate-thumbnail")
async def generate_video_thumbnail(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate thumbnail for a video in the library
    
    Extracts the best frame and saves it as a thumbnail
    """
    from sqlalchemy import select, update
    from database.models import Video
    
    # Get video
    result = await db.execute(
        select(Video).filter(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Start thumbnail generation in background
    background_tasks.add_task(
        _generate_thumbnail_task,
        video_id=video_id,
        video_path=video.source_uri
    )
    
    return {
        "message": "Thumbnail generation started",
        "video_id": str(video_id)
    }


class BatchThumbnailRequest(BaseModel):
    video_ids: List[uuid.UUID]
    max_videos: int = 50


@router.post("/generate-thumbnails-batch")
async def generate_thumbnails_batch(
    request: BatchThumbnailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate thumbnails for multiple videos in batch
    
    Useful for processing newly scanned videos
    """
    from sqlalchemy import select
    from database.models import Video
    
    # Limit batch size
    video_ids = request.video_ids[:request.max_videos]
    
    # Get videos
    result = await db.execute(
        select(Video).filter(Video.id.in_(video_ids))
    )
    videos = result.scalars().all()
    
    # Queue thumbnail generation for each
    for video in videos:
        background_tasks.add_task(
            _generate_thumbnail_task,
            video_id=video.id,
            video_path=video.source_uri
        )
    
    return {
        "message": f"Queued {len(videos)} videos for thumbnail generation",
        "video_ids": [str(v.id) for v in videos]
    }


@router.api_route("/{video_id}/thumbnail", methods=["GET", "HEAD"])
async def get_video_thumbnail(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Serve the thumbnail image for a video
    
    Returns 404 if thumbnail hasn't been generated yet
    """
    from sqlalchemy import select
    from database.models import Video
    
    result = await db.execute(
        select(Video).filter(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.thumbnail_path or not os.path.exists(video.thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    
    return FileResponse(video.thumbnail_path, media_type="image/jpeg")


@router.api_route("/{video_id}/stream", methods=["GET", "HEAD"])
async def stream_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Stream the video or image file for playback
    
    Returns the media file via FileResponse for HTML5 video/image player
    For HEIC images, converts to JPEG for browser compatibility
    """
    from sqlalchemy import select
    from database.models import Video
    
    result = await db.execute(
        select(Video).filter(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Expand user path if needed
    video_path = os.path.expanduser(video.source_uri)
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    
    # Determine MIME type based on file extension
    ext = os.path.splitext(video_path)[1].lower()
    
    # Handle HEIC/HEIF conversion to JPEG for browser compatibility
    if ext in ['.heic', '.heif']:
        try:
            from PIL import Image
            import pillow_heif
            import tempfile
            
            # Register HEIF opener with Pillow
            pillow_heif.register_heif_opener()
            
            # Convert HEIC to JPEG in memory
            img = Image.open(video_path)
            
            # Create a temporary JPEG file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            
            # Convert and save as JPEG
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(temp_path, 'JPEG', quality=90)
            
            logger.info(f"Converted HEIC to JPEG: {video_path} -> {temp_path}")
            
            # Return the converted JPEG
            return FileResponse(
                temp_path, 
                media_type='image/jpeg',
                headers={
                    'Cache-Control': 'public, max-age=3600',
                    'X-Converted-From': 'HEIC'
                }
            )
        except Exception as e:
            logger.error(f"Failed to convert HEIC image: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to convert image: {str(e)}")
    
    # MIME types for videos and images
    mime_types = {
        # Video formats
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.m4v': 'video/mp4',
        # Image formats
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
    }
    media_type = mime_types.get(ext, 'application/octet-stream')
    
    return FileResponse(video_path, media_type=media_type)


@router.post("/{video_id}/analyze")
async def analyze_video(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger video analysis using Whisper + GPT-4
    
    This endpoint:
    - Extracts audio and transcribes with Whisper API
    - Analyzes content for viral patterns with GPT-4
    - Stores results in video_analysis table
    - Runs as a background task
    """
    from sqlalchemy import select
    from database.models import Video
    
    result = await db.execute(
        select(Video).filter(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Queue analysis as background task
    background_tasks.add_task(
        _analyze_video_task,
        video_id=video_id,
        video_path=video.source_uri,
        file_name=video.file_name
    )
    
    logger.info(f"Queued analysis for video {video_id}: {video.file_name}")
    
    return {
        "message": f"Video analysis queued for {video.file_name}",
        "video_id": str(video_id),
        "status": "processing"
    }


# Background task for video analysis
async def _analyze_video_task(
    video_id: uuid.UUID,
    video_path: str,
    file_name: str = None
):
    """
    Background task to analyze video
    """
    from database.connection import async_session_maker, init_db
    from services.video_analyzer import VideoAnalyzer
    
    # Ensure database is initialized
    if async_session_maker is None:
        logger.info("Initializing database for analysis task")
        await init_db()
    
    from database.connection import async_session_maker as session_maker
    
    try:
        # Initialize analyzer
        analyzer = VideoAnalyzer(api_key=settings.openai_api_key)
        
        # Run analysis
        async with session_maker() as session:
            metadata = {
                "file_name": file_name,
                "video_id": str(video_id)
            }
            
            result = await analyzer.analyze_video(
                video_id=video_id,
                video_path=video_path,
                db_session=session,
                metadata=metadata
            )
            
            logger.success(f"Analysis complete for {video_id}")
            return result
            
    except Exception as e:
        logger.error(f"Analysis task failed for {video_id}: {e}")
        import traceback
        traceback.print_exc()


# Background task for thumbnail generation
async def _generate_thumbnail_task(
    video_id: uuid.UUID,
    video_path: str
):
    """
    Background task to generate thumbnail
    """
    from database.connection import async_session_maker, init_db
    from sqlalchemy import update
    from database.models import Video
    
    # Ensure database is initialized
    if async_session_maker is None:
        logger.info("Initializing database for background task")
        await init_db()
    
    try:
        # Expand user path if needed
        video_path = os.path.expanduser(video_path)
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return
        
        logger.info(f"Generating thumbnail for video {video_id}")
        
        # Generate thumbnail
        generator = ThumbnailGenerator()
        best_frame_path, analysis = generator.select_best_frame(
            video_path=video_path,
            num_candidates=10
        )
        
        # Save to permanent location
        thumbnails_dir = Path("/tmp/mediaposter_thumbnails")
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        thumbnail_path = thumbnails_dir / f"{video_id}.jpg"
        
        # Copy best frame to thumbnail location
        import shutil
        shutil.copy(best_frame_path, thumbnail_path)
        
        logger.info(f"Thumbnail saved: {thumbnail_path} (score: {analysis['overall_score']})")
        
        # Update database
        try:
            logger.info(f"Updating database for video {video_id}")
            async with async_session_maker() as session:
                result = await session.execute(
                    update(Video)
                    .where(Video.id == video_id)
                    .values(
                        thumbnail_path=str(thumbnail_path),
                        thumbnail_generated_at=datetime.utcnow(),
                        best_frame_score=analysis['overall_score']
                    )
                )
                await session.commit()
                logger.success(f"Database updated! Rows affected: {result.rowcount}")
        except Exception as db_error:
            logger.error(f"Database update failed for {video_id}: {db_error}")
            import traceback
            traceback.print_exc()
        
        logger.success(f"Thumbnail generation complete for video {video_id}")
        
    except Exception as e:
        logger.error(f"Error generating thumbnail for {video_id}: {e}")
        import traceback
        traceback.print_exc()

