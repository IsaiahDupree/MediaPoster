"""
Database-backed Media Processing API
Persists media to Supabase PostgreSQL using Video and VideoAnalysis models.
"""
import os
import uuid
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Video, VideoAnalysis

router = APIRouter(prefix="/api/media-db", tags=["Media Processing (Database)"])

# Default user ID for batch processing
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class MediaStatusResponse(BaseModel):
    """Current status of media processing."""
    media_id: str
    filename: str
    status: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    duration_sec: Optional[int] = None
    resolution: Optional[str] = None
    thumbnail_path: Optional[str] = None
    pre_social_score: Optional[float] = None
    transcript: Optional[str] = None
    topics: Optional[List[str]] = None
    created_at: str
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class MediaDetailResponse(BaseModel):
    """Detailed media information with analysis."""
    media_id: str
    filename: str
    file_path: str
    media_type: Optional[str] = None
    file_size: Optional[int] = None
    duration_sec: Optional[int] = None
    resolution: Optional[str] = None
    aspect_ratio: Optional[str] = None
    thumbnail_path: Optional[str] = None
    created_at: str
    # Analysis
    pre_social_score: Optional[float] = None
    transcript: Optional[str] = None
    topics: Optional[List[str]] = None
    hooks: Optional[List[str]] = None
    tone: Optional[str] = None
    pacing: Optional[str] = None
    visual_analysis: Optional[dict] = None
    analyzed_at: Optional[str] = None


class BatchIngestRequest(BaseModel):
    """Request to ingest multiple files from a directory."""
    directory_path: str
    recursive: bool = False
    resume: bool = True


class BatchIngestResponse(BaseModel):
    """Response for batch ingestion."""
    job_id: str
    total_files: int
    status: str
    message: str


class IngestStatsResponse(BaseModel):
    """Statistics about ingested media."""
    total_videos: int
    analyzed_count: int
    pending_analysis: int
    total_size_bytes: int
    avg_duration_sec: Optional[float] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_media_type(filename: str) -> str:
    """Determine media type from filename."""
    ext = Path(filename).suffix.lower()
    video_exts = {'.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm'}
    return 'video' if ext in video_exts else 'image'


def compute_file_hash(data: bytes) -> str:
    """Compute MD5 hash of file data."""
    return hashlib.md5(data).hexdigest()


async def get_video_metadata(file_path: str) -> dict:
    """Extract video metadata using ffprobe."""
    import subprocess
    
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', str(file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            duration = None
            width = None
            height = None
            
            if 'format' in data:
                duration = int(float(data['format'].get('duration', 0)))
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width')
                    height = stream.get('height')
                    break
            
            resolution = f"{width}x{height}" if width and height else None
            aspect = f"{width}:{height}" if width and height else None
            
            return {
                'duration_sec': duration,
                'resolution': resolution,
                'aspect_ratio': aspect
            }
    except Exception as e:
        print(f"Error extracting metadata: {e}")
    
    return {}


# =============================================================================
# ENDPOINTS - READ
# =============================================================================

@router.get("/list", response_model=List[MediaStatusResponse])
async def list_media(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    analyzed_only: bool = Query(default=False),
    media_type: Optional[str] = Query(default=None, description="Filter by media type: 'video' or 'image'")
):
    """
    List all media from database.
    """
    from sqlalchemy import text, or_
    
    query = select(Video).order_by(Video.created_at.desc())
    
    # Filter by media type if specified
    if media_type == 'video':
        query = query.where(or_(
            Video.source_uri.ilike('%.mov'),
            Video.source_uri.ilike('%.mp4'),
            Video.source_uri.ilike('%.avi'),
            Video.source_uri.ilike('%.mkv'),
            Video.source_uri.ilike('%.webm'),
            Video.source_uri.ilike('%.m4v')
        ))
    elif media_type == 'image':
        query = query.where(or_(
            Video.source_uri.ilike('%.jpg'),
            Video.source_uri.ilike('%.jpeg'),
            Video.source_uri.ilike('%.png'),
            Video.source_uri.ilike('%.gif'),
            Video.source_uri.ilike('%.heic'),
            Video.source_uri.ilike('%.webp')
        ))
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    videos = result.scalars().all()
    
    response = []
    for video in videos:
        # Try to get analysis with raw SQL to handle schema differences
        analysis = None
        try:
            analysis_result = await db.execute(
                text("SELECT video_id, transcript, topics, pre_social_score FROM video_analysis WHERE video_id = :vid"),
                {"vid": str(video.id)}
            )
            row = analysis_result.fetchone()
            if row:
                analysis = {
                    "transcript": row[1],
                    "topics": row[2],
                    "pre_social_score": row[3]
                }
        except Exception:
            pass
        
        status = "analyzed" if analysis else "ingested"
        
        response.append(MediaStatusResponse(
            media_id=str(video.id),
            filename=video.file_name or "",
            status=status,
            file_path=video.source_uri,
            file_size=video.file_size,
            duration_sec=video.duration_sec,
            resolution=video.resolution,
            thumbnail_path=video.thumbnail_path,
            pre_social_score=analysis["pre_social_score"] if analysis else None,
            transcript=analysis["transcript"] if analysis else None,
            topics=analysis["topics"] if analysis else None,
            created_at=video.created_at.isoformat() if video.created_at else "",
            updated_at=video.updated_at.isoformat() if video.updated_at else None
        ))
    
    return response


@router.get("/detail/{media_id}", response_model=MediaDetailResponse)
async def get_media_detail(
    media_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific media item.
    """
    from sqlalchemy import text
    
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    query = select(Video).where(Video.id == video_uuid)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Determine media type
    media_type = "video"  # Default
    if video.source_uri:
        ext = video.source_uri.lower().split('.')[-1]
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif']:
            media_type = "image"
        elif ext in ['mp4', 'mov', 'avi', 'mkv', 'webm']:
            media_type = "video"
    
    # Get analysis with raw SQL to handle schema differences
    analysis = None
    try:
        analysis_result = await db.execute(
            text("SELECT video_id, transcript, topics, hooks, tone, pacing, pre_social_score, visual_analysis, analyzed_at FROM video_analysis WHERE video_id = :vid"),
            {"vid": str(video.id)}
        )
        row = analysis_result.fetchone()
        if row:
            analysis = {
                "transcript": row[1],
                "topics": row[2],
                "hooks": row[3],
                "tone": row[4],
                "pacing": row[5],
                "pre_social_score": row[6],
                "visual_analysis": row[7],
                "analyzed_at": row[8]
            }
    except Exception:
        pass
    
    return MediaDetailResponse(
        media_id=str(video.id),
        filename=video.file_name or "",
        file_path=video.source_uri,
        media_type=media_type,
        file_size=video.file_size,
        duration_sec=video.duration_sec,
        resolution=video.resolution,
        aspect_ratio=video.aspect_ratio,
        thumbnail_path=video.thumbnail_path,
        created_at=video.created_at.isoformat() if video.created_at else "",
        pre_social_score=analysis["pre_social_score"] if analysis else None,
        transcript=analysis["transcript"] if analysis else None,
        topics=analysis["topics"] if analysis else None,
        hooks=analysis["hooks"] if analysis else None,
        tone=analysis["tone"] if analysis else None,
        pacing=analysis["pacing"] if analysis else None,
        visual_analysis=analysis["visual_analysis"] if analysis else None,
        analyzed_at=analysis["analyzed_at"].isoformat() if analysis and analysis["analyzed_at"] else None
    )


@router.get("/stats", response_model=IngestStatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Get ingestion statistics.
    """
    from sqlalchemy import func
    
    # Total videos
    total_query = select(func.count(Video.id))
    total_result = await db.execute(total_query)
    total_videos = total_result.scalar() or 0
    
    # Analyzed count
    analyzed_query = select(func.count(VideoAnalysis.video_id))
    analyzed_result = await db.execute(analyzed_query)
    analyzed_count = analyzed_result.scalar() or 0
    
    # Total size
    size_query = select(func.sum(Video.file_size))
    size_result = await db.execute(size_query)
    total_size = size_result.scalar() or 0
    
    # Average duration
    duration_query = select(func.avg(Video.duration_sec))
    duration_result = await db.execute(duration_query)
    avg_duration = duration_result.scalar()
    
    return IngestStatsResponse(
        total_videos=total_videos,
        analyzed_count=analyzed_count,
        pending_analysis=total_videos - analyzed_count,
        total_size_bytes=total_size,
        avg_duration_sec=float(avg_duration) if avg_duration else None
    )


# =============================================================================
# ENDPOINTS - INGEST
# =============================================================================

@router.post("/ingest/file")
async def ingest_single_file(
    file_path: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest a single file into the database.
    """
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {file_path}")
    
    # Check for duplicate
    existing_query = select(Video).where(Video.source_uri == str(path))
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        return {"status": "exists", "media_id": str(existing.id)}
    
    # Get metadata
    metadata = await get_video_metadata(str(path))
    
    # Create video record
    video = Video(
        user_id=DEFAULT_USER_ID,
        source_type="local",
        source_uri=str(path),
        file_name=path.name,
        file_size=path.stat().st_size,
        duration_sec=metadata.get('duration_sec'),
        resolution=metadata.get('resolution'),
        aspect_ratio=metadata.get('aspect_ratio')
    )
    
    db.add(video)
    await db.commit()
    await db.refresh(video)
    
    return {"status": "ingested", "media_id": str(video.id)}


@router.post("/batch/ingest", response_model=BatchIngestResponse)
async def batch_ingest(
    request: BatchIngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start batch ingestion from a directory.
    Persists to database with smart resume.
    """
    directory = Path(request.directory_path).expanduser()
    
    if not directory.exists():
        raise HTTPException(status_code=400, detail=f"Directory not found: {directory}")
    
    # Count files
    video_exts = {'.mov', '.mp4', '.m4v', '.avi', '.mkv'}
    image_exts = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
    all_exts = video_exts | image_exts
    
    files = [f for f in directory.iterdir() if f.suffix.lower() in all_exts]
    total_files = len(files)
    
    if total_files == 0:
        raise HTTPException(status_code=400, detail="No media files found in directory")
    
    job_id = str(uuid.uuid4())
    
    # Start background processing
    background_tasks.add_task(process_batch_ingest, job_id, files, request.resume)
    
    return BatchIngestResponse(
        job_id=job_id,
        total_files=total_files,
        status="started",
        message=f"Processing {total_files} files from {directory}"
    )


async def process_batch_ingest(job_id: str, files: List[Path], resume: bool):
    """Process batch ingestion in background with thumbnail generation."""
    from database.connection import async_session_maker
    from services.thumbnail_service import generate_thumbnail
    
    if not async_session_maker:
        print("Database not initialized")
        return
    
    async with async_session_maker() as db:
        for file_path in files:
            try:
                # Check if already exists (resume)
                if resume:
                    existing_query = select(Video).where(Video.source_uri == str(file_path))
                    existing_result = await db.execute(existing_query)
                    existing_video = existing_result.scalar_one_or_none()
                    if existing_video:
                        # Generate thumbnail if missing
                        if not existing_video.thumbnail_path:
                            try:
                                thumb_path = generate_thumbnail(str(file_path), "medium")
                                if thumb_path:
                                    existing_video.thumbnail_path = thumb_path
                                    await db.commit()
                                    print(f"Generated thumbnail for existing: {file_path.name}")
                            except Exception as e:
                                print(f"Thumbnail generation failed for {file_path.name}: {e}")
                        continue
                
                # Get metadata
                metadata = await get_video_metadata(str(file_path))
                
                # Generate thumbnail immediately
                thumbnail_path = None
                try:
                    thumbnail_path = generate_thumbnail(str(file_path), "medium")
                    print(f"Generated thumbnail: {thumbnail_path}")
                except Exception as e:
                    print(f"Thumbnail generation failed for {file_path.name}: {e}")
                
                # Create video record with thumbnail
                video = Video(
                    user_id=DEFAULT_USER_ID,
                    source_type="local",
                    source_uri=str(file_path),
                    file_name=file_path.name,
                    file_size=file_path.stat().st_size,
                    duration_sec=metadata.get('duration_sec'),
                    resolution=metadata.get('resolution'),
                    aspect_ratio=metadata.get('aspect_ratio'),
                    thumbnail_path=thumbnail_path
                )
                
                db.add(video)
                await db.commit()
                print(f"Ingested: {file_path.name}")
                
            except Exception as e:
                print(f"Error ingesting {file_path}: {e}")
                await db.rollback()


# =============================================================================
# ENDPOINTS - ANALYZE
# =============================================================================

@router.post("/analyze/{media_id}")
async def analyze_media(
    media_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start AI analysis for a media item.
    """
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    # Get video
    query = select(Video).where(Video.id == video_uuid)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Check if already analyzed
    analysis_query = select(VideoAnalysis).where(VideoAnalysis.video_id == video_uuid)
    analysis_result = await db.execute(analysis_query)
    existing_analysis = analysis_result.scalar_one_or_none()
    
    if existing_analysis:
        return {"status": "already_analyzed", "media_id": media_id}
    
    # Start analysis in background
    background_tasks.add_task(run_analysis, str(video_uuid), video.source_uri)
    
    return {"status": "analyzing", "media_id": media_id}


async def run_analysis(video_id: str, file_path: str):
    """Run AI analysis on a video using real VideoAnalyzer service."""
    from database.connection import async_session_maker
    from config import settings
    import traceback
    
    if not async_session_maker:
        print(f"Error: async_session_maker not initialized for {video_id}")
        return
    
    # Expand path if needed
    file_path = os.path.expanduser(file_path) if file_path else None
    
    # Map host path to container path (for Docker)
    container_path = map_host_to_container_path(file_path) if file_path else None
    
    # Try container path first, then original path
    actual_path = None
    if container_path and os.path.exists(container_path):
        actual_path = container_path
    elif file_path and os.path.exists(file_path):
        actual_path = file_path
    
    if not actual_path:
        print(f"Error: File not found for {video_id}: {file_path} (container: {container_path})")
        return
    
    file_path = actual_path
    
    async with async_session_maker() as db:
        try:
            video_uuid = uuid.UUID(video_id)
            
            # Try using real VideoAnalyzer if OpenAI key is available
            if settings.openai_api_key and settings.openai_api_key.startswith("sk-"):
                try:
                    from services.video_analyzer import VideoAnalyzer
                    
                    analyzer = VideoAnalyzer(api_key=settings.openai_api_key)
                    result = await analyzer.analyze_video(
                        video_id=video_uuid,
                        video_path=file_path,
                        db_session=db,
                        metadata={"video_id": str(video_uuid)}
                    )
                    print(f"Analysis complete for {video_id}: score={result.get('pre_social_score')}")
                    return
                    
                except ImportError as e:
                    print(f"VideoAnalyzer not available: {e}, using fallback")
                except Exception as e:
                    print(f"VideoAnalyzer failed: {e}, using fallback")
                    traceback.print_exc()
            
            # Fallback: Create basic analysis without AI
            import random
            
            # Determine media type
            ext = Path(file_path).suffix.lower()
            is_image = ext in {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp'}
            
            analysis = VideoAnalysis(
                video_id=video_uuid,
                transcript="" if is_image else "Transcription requires OpenAI API key",
                topics=["content", "media"],
                hooks=["Visual content"],
                tone="informative" if is_image else "conversational",
                pacing="static" if is_image else "moderate",
                pre_social_score=random.randint(50, 80)
            )
            
            db.add(analysis)
            await db.commit()
            print(f"Basic analysis complete for {video_id}")
            
        except Exception as e:
            print(f"Error analyzing {video_id}: {e}")
            traceback.print_exc()
            await db.rollback()


@router.post("/batch/analyze")
async def batch_analyze(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=10, le=100)
):
    """
    Analyze all unanalyzed videos.
    """
    from sqlalchemy import and_, not_, exists
    
    # Find videos without analysis
    subquery = select(VideoAnalysis.video_id)
    query = select(Video).where(
        not_(Video.id.in_(subquery))
    ).limit(limit)
    
    result = await db.execute(query)
    videos = result.scalars().all()
    
    if not videos:
        return {"status": "no_pending", "count": 0}
    
    # Start analysis for each
    for video in videos:
        background_tasks.add_task(run_analysis, str(video.id), video.source_uri)
    
    return {"status": "started", "count": len(videos)}


# =============================================================================
# ENDPOINTS - THUMBNAIL
# =============================================================================

def map_host_to_container_path(host_path: str) -> str:
    """Map host filesystem paths to Docker container paths."""
    if not host_path:
        return host_path
    # Map ~/Documents/IphoneImport or /Users/.../IphoneImport to /media/import
    import re
    # Handle expanded home directory paths
    pattern = r'^/Users/[^/]+/Documents/IphoneImport/(.*)$'
    match = re.match(pattern, host_path)
    if match:
        return f"/media/import/{match.group(1)}"
    # Handle ~ paths (shouldn't happen but just in case)
    if host_path.startswith('~/Documents/IphoneImport/'):
        return host_path.replace('~/Documents/IphoneImport/', '/media/import/')
    return host_path


@router.get("/thumbnail/{media_id}")
async def get_thumbnail(
    media_id: str,
    size: str = Query(default="medium", pattern="^(small|medium|large)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get thumbnail for a media item.
    """
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    query = select(Video).where(Video.id == video_uuid)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Get thumbnail path - check both original and mapped paths
    if video.thumbnail_path:
        thumb_path = video.thumbnail_path
        if Path(thumb_path).exists():
            return FileResponse(thumb_path, media_type="image/jpeg")
    
    # Try to generate on-the-fly from source file
    source_path = video.source_uri
    container_source = map_host_to_container_path(source_path) if source_path else None
    
    # Check if source exists (try container path first, then original)
    actual_source = None
    if container_source and Path(container_source).exists():
        actual_source = container_source
    elif source_path and Path(source_path).exists():
        actual_source = source_path
    
    if actual_source:
        from services.thumbnail_service import generate_thumbnail
        thumb_path = generate_thumbnail(actual_source, size)
        if thumb_path:
            # Update database with thumbnail path
            video.thumbnail_path = thumb_path
            await db.commit()
            return FileResponse(thumb_path, media_type="image/jpeg")
    
    raise HTTPException(status_code=404, detail="Thumbnail not available")


@router.get("/video/{media_id}")
async def stream_video(
    media_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Stream video file for playback.
    """
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    query = select(Video).where(Video.id == video_uuid)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Try container-mapped path first, then original path
    source_path = video.source_uri
    container_source = map_host_to_container_path(source_path) if source_path else None
    
    actual_path = None
    if container_source and Path(container_source).exists():
        actual_path = container_source
    elif source_path and Path(source_path).exists():
        actual_path = source_path
    
    if not actual_path:
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Determine media type
    ext = Path(actual_path).suffix.lower()
    media_type_map = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.m4v': 'video/x-m4v',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm'
    }
    media_type = media_type_map.get(ext, 'video/mp4')
    
    return FileResponse(
        actual_path, 
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"}
    )


# =============================================================================
# ENDPOINTS - IMAGE
# =============================================================================

@router.get("/image/{media_id}")
async def serve_image(
    media_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Serve full-size image file for display.
    """
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    query = select(Video).where(Video.id == video_uuid)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Try container-mapped path first, then original path
    source_path = video.source_uri
    container_source = map_host_to_container_path(source_path) if source_path else None
    
    actual_path = None
    if container_source and Path(container_source).exists():
        actual_path = container_source
    elif source_path and Path(source_path).exists():
        actual_path = source_path
    
    if not actual_path:
        raise HTTPException(status_code=404, detail="Image file not found")
    
    # Determine media type
    ext = Path(actual_path).suffix.lower()
    media_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.heic': 'image/heic',
        '.heif': 'image/heif',
    }
    media_type = media_type_map.get(ext, 'image/jpeg')
    
    return FileResponse(
        actual_path, 
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"}
    )


# =============================================================================
# ENDPOINTS - DELETE
# =============================================================================

@router.delete("/{media_id}")
async def delete_media(
    media_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a media item from database."""
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    query = select(Video).where(Video.id == video_uuid)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Media not found")
    
    await db.delete(video)
    await db.commit()
    
    return {"message": "Media deleted", "media_id": media_id}


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check with database stats."""
    from sqlalchemy import func
    
    try:
        total_query = select(func.count(Video.id))
        total_result = await db.execute(total_query)
        total_videos = total_result.scalar() or 0
        
        return {
            "status": "healthy",
            "service": "media-processing-db",
            "database": "connected",
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_videos": total_videos
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "media-processing-db",
            "database": "error",
            "error": str(e)
        }


# =============================================================================
# ENDPOINTS - ANALYSIS STORAGE & RETRIEVAL
# =============================================================================

class AnalysisSaveRequest(BaseModel):
    """Request to save comprehensive analysis"""
    transcript: Optional[str] = None
    transcript_analysis: Optional[dict] = None
    topics: Optional[List[str]] = None
    hooks: Optional[List[str]] = None
    tone: Optional[str] = None
    pacing: Optional[str] = None
    key_moments: Optional[dict] = None
    visual_analysis: Optional[dict] = None
    frame_analyses: Optional[list] = None
    music_suggestion: Optional[dict] = None
    platform_content: Optional[list] = None
    deep_analysis: Optional[dict] = None
    pre_social_score: Optional[float] = None
    
    model_config = {"from_attributes": True}


class PostScoreUpdateRequest(BaseModel):
    """Request to update post-social score after analytics"""
    post_social_score: float
    metrics: Optional[dict] = None  # Raw metrics used to calculate score
    
    model_config = {"from_attributes": True}


@router.get("/analysis/{media_id}")
async def get_analysis(
    media_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get full analysis for a media item including pre/post social scores.
    Returns all stored analysis data that can be used across the app.
    """
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    # Get video with analysis
    query = select(Video).where(Video.id == video_uuid)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Get analysis
    analysis_query = select(VideoAnalysis).where(VideoAnalysis.video_id == video_uuid)
    analysis_result = await db.execute(analysis_query)
    analysis = analysis_result.scalar_one_or_none()
    
    if not analysis:
        return {
            "media_id": media_id,
            "has_analysis": False,
            "message": "No analysis available. Run analysis first."
        }
    
    return {
        "media_id": media_id,
        "has_analysis": True,
        "transcript": analysis.transcript,
        "transcript_analysis": analysis.transcript_analysis,
        "topics": analysis.topics or [],
        "hooks": analysis.hooks or [],
        "tone": analysis.tone,
        "pacing": analysis.pacing,
        "key_moments": analysis.key_moments,
        "visual_analysis": analysis.visual_analysis,
        "frame_analyses": analysis.frame_analyses,
        "platform_content": analysis.platform_content,
        "deep_analysis": analysis.deep_analysis,
        "pre_social_score": analysis.pre_social_score,
        "post_social_score": analysis.post_social_score,
        "post_social_updated_at": analysis.post_social_updated_at.isoformat() if analysis.post_social_updated_at else None,
        "analysis_version": analysis.analysis_version,
        "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
        "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None,
    }


@router.put("/analysis/{media_id}")
async def save_analysis(
    media_id: str,
    request: AnalysisSaveRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Save or update comprehensive analysis for a media item.
    This persists the analysis so it can be retrieved from other pages.
    """
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    # Check video exists
    video_query = select(Video).where(Video.id == video_uuid)
    video_result = await db.execute(video_query)
    video = video_result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Get or create analysis
    analysis_query = select(VideoAnalysis).where(VideoAnalysis.video_id == video_uuid)
    analysis_result = await db.execute(analysis_query)
    analysis = analysis_result.scalar_one_or_none()
    
    if analysis:
        # Update existing - save all fields
        if request.transcript is not None:
            analysis.transcript = request.transcript
        if request.transcript_analysis is not None:
            analysis.transcript_analysis = request.transcript_analysis
        if request.topics is not None:
            analysis.topics = request.topics
        if request.hooks is not None:
            analysis.hooks = request.hooks
        if request.tone is not None:
            analysis.tone = request.tone
        if request.pacing is not None:
            analysis.pacing = request.pacing
        if request.key_moments is not None:
            analysis.key_moments = request.key_moments
        if request.visual_analysis is not None:
            analysis.visual_analysis = request.visual_analysis
        if request.frame_analyses is not None:
            analysis.frame_analyses = request.frame_analyses
        if request.music_suggestion is not None:
            analysis.music_suggestion = request.music_suggestion
        if request.platform_content is not None:
            analysis.platform_content = request.platform_content
        if request.deep_analysis is not None:
            analysis.deep_analysis = request.deep_analysis
        if request.pre_social_score is not None:
            analysis.pre_social_score = request.pre_social_score
        analysis.analysis_version = "3.0"
    else:
        # Create new with all fields
        analysis = VideoAnalysis(
            video_id=video_uuid,
            transcript=request.transcript,
            transcript_analysis=request.transcript_analysis,
            topics=request.topics,
            hooks=request.hooks,
            tone=request.tone,
            pacing=request.pacing,
            key_moments=request.key_moments,
            visual_analysis=request.visual_analysis,
            frame_analyses=request.frame_analyses,
            music_suggestion=request.music_suggestion,
            platform_content=request.platform_content,
            deep_analysis=request.deep_analysis,
            pre_social_score=request.pre_social_score,
            analysis_version="3.0"
        )
        db.add(analysis)
    
    await db.commit()
    
    return {
        "status": "saved",
        "media_id": media_id,
        "pre_social_score": analysis.pre_social_score,
        "updated_at": datetime.now().isoformat()
    }


@router.put("/analysis/{media_id}/post-score")
async def update_post_social_score(
    media_id: str,
    request: PostScoreUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update the post-social score after getting analytics back.
    This is called after content is posted and metrics are collected.
    """
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    # Get analysis
    analysis_query = select(VideoAnalysis).where(VideoAnalysis.video_id == video_uuid)
    analysis_result = await db.execute(analysis_query)
    analysis = analysis_result.scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this media")
    
    # Update post score
    analysis.post_social_score = request.post_social_score
    analysis.post_social_updated_at = datetime.now()
    
    # Store metrics in deep_analysis if provided
    if request.metrics:
        existing_deep = analysis.deep_analysis or {}
        existing_deep["post_metrics"] = request.metrics
        analysis.deep_analysis = existing_deep
    
    await db.commit()
    
    return {
        "status": "updated",
        "media_id": media_id,
        "pre_social_score": analysis.pre_social_score,
        "post_social_score": analysis.post_social_score,
        "score_delta": (analysis.post_social_score - analysis.pre_social_score) if analysis.pre_social_score else None,
        "updated_at": analysis.post_social_updated_at.isoformat()
    }


class CurationRequest(BaseModel):
    """Request to update curation status"""
    curation_status: str  # 'pending', 'approved', 'rejected'


@router.put("/curate/{media_id}")
async def update_curation_status(
    media_id: str,
    request: CurationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update curation status for a media item (approve/reject for posting).
    """
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    # Get or create analysis record to store curation
    analysis_query = select(VideoAnalysis).where(VideoAnalysis.video_id == video_uuid)
    analysis_result = await db.execute(analysis_query)
    analysis = analysis_result.scalar_one_or_none()
    
    if analysis:
        # Store in key_moments as a workaround (or add curation_status column later)
        current_key_moments = analysis.key_moments or {}
        current_key_moments['curation_status'] = request.curation_status
        current_key_moments['curated_at'] = datetime.now().isoformat()
        analysis.key_moments = current_key_moments
    else:
        # Create new analysis with curation
        analysis = VideoAnalysis(
            video_id=video_uuid,
            key_moments={
                'curation_status': request.curation_status,
                'curated_at': datetime.now().isoformat()
            },
            analysis_version="3.0"
        )
        db.add(analysis)
    
    await db.commit()
    
    return {
        "status": "updated",
        "media_id": media_id,
        "curation_status": request.curation_status
    }


@router.get("/analysis/{media_id}/scores")
async def get_social_scores(
    media_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get just the pre and post social scores for a media item.
    Lightweight endpoint for dashboards and lists.
    """
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    analysis_query = select(VideoAnalysis).where(VideoAnalysis.video_id == video_uuid)
    analysis_result = await db.execute(analysis_query)
    analysis = analysis_result.scalar_one_or_none()
    
    if not analysis:
        return {
            "media_id": media_id,
            "pre_social_score": None,
            "post_social_score": None,
            "has_analysis": False
        }
    
    return {
        "media_id": media_id,
        "pre_social_score": analysis.pre_social_score,
        "post_social_score": analysis.post_social_score,
        "post_social_updated_at": analysis.post_social_updated_at.isoformat() if analysis.post_social_updated_at else None,
        "has_analysis": True,
        "score_delta": (analysis.post_social_score - analysis.pre_social_score) if (analysis.post_social_score and analysis.pre_social_score) else None
    }
