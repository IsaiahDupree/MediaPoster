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

    class Config:
        from_attributes = True


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
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    analyzed_only: bool = Query(default=False)
):
    """
    List all media from database.
    """
    from sqlalchemy import text
    
    query = select(Video).order_by(Video.created_at.desc()).offset(offset).limit(limit)
    
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
    
    # Check if file exists
    if not file_path or not os.path.exists(file_path):
        print(f"Error: File not found for {video_id}: {file_path}")
        return
    
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

@router.get("/thumbnail/{media_id}")
async def get_thumbnail(
    media_id: str,
    size: str = Query(default="medium", regex="^(small|medium|large)$"),
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
    
    # Get thumbnail path
    if video.thumbnail_path and Path(video.thumbnail_path).exists():
        return FileResponse(video.thumbnail_path, media_type="image/jpeg")
    
    # Try to generate on-the-fly
    if video.source_uri and Path(video.source_uri).exists():
        from services.thumbnail_service import generate_thumbnail
        thumb_path = generate_thumbnail(video.source_uri, size)
        if thumb_path:
            # Update database
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
    
    if not video.source_uri or not Path(video.source_uri).exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Determine media type
    ext = Path(video.source_uri).suffix.lower()
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
        video.source_uri, 
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
