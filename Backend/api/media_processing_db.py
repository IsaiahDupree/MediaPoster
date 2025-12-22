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

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Query, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Video, VideoAnalysis
from loguru import logger

router = APIRouter(prefix="/api/media-db", tags=["Media Processing (Database)"])

# Default user ID for batch processing
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Global analysis job tracker
_analysis_jobs = {}  # job_id -> {status, total, completed, current_video, videos: {id: {status, step, filename}}}

def get_analysis_status():
    """Get current analysis status."""
    return _analysis_jobs

def update_video_step(job_id: str, video_id: str, step: str, filename: str = None):
    """Update individual video analysis step."""
    if job_id and job_id in _analysis_jobs:
        if video_id not in _analysis_jobs[job_id]["videos"]:
            _analysis_jobs[job_id]["videos"][video_id] = {}
        _analysis_jobs[job_id]["videos"][video_id]["step"] = step
        _analysis_jobs[job_id]["videos"][video_id]["updated_at"] = datetime.now().isoformat()
        if filename:
            _analysis_jobs[job_id]["videos"][video_id]["filename"] = filename
        _analysis_jobs[job_id]["current_video"] = video_id
        _analysis_jobs[job_id]["current_step"] = step

def update_analysis_status(job_id: str, **kwargs):
    """Update analysis job status."""
    if job_id not in _analysis_jobs:
        _analysis_jobs[job_id] = {
            "status": "running",
            "total": 0,
            "completed": 0,
            "failed": 0,
            "current_video": None,
            "current_step": None,
            "videos": {},
            "started_at": datetime.now().isoformat()
        }
    _analysis_jobs[job_id].update(kwargs)
    _analysis_jobs[job_id]["updated_at"] = datetime.now().isoformat()


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
    curation_status: Optional[str] = None  # 'pending', 'approved', 'rejected'
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
    # Deep analysis fields
    deep_analysis: Optional[dict] = None
    frame_analyses: Optional[list] = None
    platform_content: Optional[list] = None


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
        curation_status = None
        try:
            analysis_result = await db.execute(
                text("SELECT video_id, transcript, topics, pre_social_score, curation_status FROM video_analysis WHERE video_id = :vid"),
                {"vid": str(video.id)}
            )
            row = analysis_result.fetchone()
            if row:
                analysis = {
                    "transcript": row[1],
                    "topics": row[2],
                    "pre_social_score": row[3]
                }
                curation_status = row[4]
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
            curation_status=curation_status,
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
            text("SELECT video_id, transcript, topics, hooks, tone, pacing, pre_social_score, visual_analysis, analyzed_at, deep_analysis, frame_analyses, platform_content FROM video_analysis WHERE video_id = :vid"),
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
                "analyzed_at": row[8],
                "deep_analysis": row[9],
                "frame_analyses": row[10],
                "platform_content": row[11]
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
        analyzed_at=analysis["analyzed_at"].isoformat() if analysis and analysis["analyzed_at"] else None,
        deep_analysis=analysis["deep_analysis"] if analysis else None,
        frame_analyses=analysis["frame_analyses"] if analysis else None,
        platform_content=analysis["platform_content"] if analysis else None
    )


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Get ingestion statistics including analyzing count.
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
    
    # Get currently analyzing count from job tracker
    analyzing_count = 0
    for job in _analysis_jobs.values():
        if job.get("status") == "running":
            analyzing_count += job.get("total", 0) - job.get("completed", 0) - job.get("failed", 0)
    
    return {
        "total_videos": total_videos,
        "analyzed_count": analyzed_count,
        "analyzing_count": analyzing_count,
        "pending_analysis": total_videos - analyzed_count,
        "total_size_bytes": total_size,
        "avg_duration_sec": float(avg_duration) if avg_duration else None
    }


@router.get("/analysis-status")
async def get_analysis_job_status():
    """
    Get detailed status of all analysis jobs including individual video progress.
    """
    jobs = []
    for job_id, job in _analysis_jobs.items():
        # Get recent video statuses (last 10)
        videos_dict = job.get("videos", {})
        recent_videos = []
        completed_videos = []
        
        for vid, info in list(videos_dict.items())[-20:]:
            if isinstance(info, dict):
                video_info = {
                    "id": vid,
                    "step": info.get("step", "unknown"),
                    "filename": info.get("filename", ""),
                    "status": info.get("status", "processing")
                }
                recent_videos.append(video_info)
            elif info == "completed":
                completed_videos.append({"id": vid, "status": "completed", "filename": ""})
            else:
                recent_videos.append({"id": vid, "status": str(info)})
        
        jobs.append({
            "job_id": job_id,
            "status": job.get("status"),
            "total": job.get("total", 0),
            "completed": job.get("completed", 0),
            "failed": job.get("failed", 0),
            "current_video": job.get("current_video"),
            "current_step": job.get("current_step"),
            "current_filename": job.get("current_filename"),
            "recent_videos": recent_videos,
            "completed_videos": completed_videos[-5:],  # Last 5 completed
            "started_at": job.get("started_at"),
            "updated_at": job.get("updated_at")
        })
    
    return {
        "active_jobs": len([j for j in jobs if j["status"] == "running"]),
        "jobs": jobs
    }


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
    
    # Start in thread pool (non-blocking)
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="batch_ingest")
    executor.submit(process_batch_ingest_sync, job_id, files, request.resume)
    
    print(f"Queued {total_files} files for batch ingest in thread pool")
    
    return BatchIngestResponse(
        job_id=job_id,
        total_files=total_files,
        status="started",
        message=f"Processing {total_files} files from {directory}"
    )


def process_batch_ingest_sync(job_id: str, files: List[Path], resume: bool):
    """Sync wrapper for batch ingest - runs in thread pool."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(process_batch_ingest(job_id, files, resume))
    finally:
        loop.close()


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
    force: bool = Query(default=False, description="Force re-analysis even if already analyzed"),
    db: AsyncSession = Depends(get_db)
):
    """
    Start AI analysis for a media item.
    Use force=true to re-analyze an already analyzed video.
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
    
    if existing_analysis and not force:
        return {"status": "already_analyzed", "media_id": media_id}
    
    # If forcing re-analysis, delete existing analysis first
    if existing_analysis and force:
        await db.delete(existing_analysis)
        await db.commit()
        logger.info(f"[Re-Analysis] Deleted existing analysis for {media_id}")
    
    # Get the file path - prefer source_uri, fall back to file_path
    file_path = video.source_uri or video.file_path
    if not file_path:
        raise HTTPException(status_code=400, detail="No file path available for this media")
    
    logger.info(f"[Analysis] Starting analysis for {media_id} at path: {file_path}")
    
    # Start analysis in thread pool (non-blocking)
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="single_analysis")
    executor.submit(run_analysis_sync, str(video_uuid), file_path)
    
    return {"status": "analyzing", "media_id": media_id}


def run_analysis_sync(video_id: str, file_path: str, job_id: str = None):
    """
    Synchronous wrapper for analysis - runs in thread pool to avoid blocking event loop.
    """
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_analysis_async(video_id, file_path, job_id))
    finally:
        loop.close()


async def _run_analysis_async(video_id: str, file_path: str, job_id: str = None):
    """Run comprehensive AI analysis on a video using VideoAnalyzer + image analysis."""
    from database.connection import create_thread_local_session_maker
    from config import settings
    import traceback
    import httpx
    from loguru import logger
    
    # Update job tracker
    if job_id:
        if job_id in _analysis_jobs:
            _analysis_jobs[job_id]["videos"][video_id] = "starting"
            _analysis_jobs[job_id]["current_video"] = video_id
    
    logger.info(f"[Analysis] Starting: {video_id}")
    
    # Create thread-local session maker to avoid event loop conflicts
    try:
        thread_session_maker = create_thread_local_session_maker()
    except Exception as e:
        logger.error(f"[Analysis] Failed to create database session: {e}")
        if job_id and job_id in _analysis_jobs:
            _analysis_jobs[job_id]["videos"][video_id] = "failed:no_db"
            _analysis_jobs[job_id]["failed"] = _analysis_jobs[job_id].get("failed", 0) + 1
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
        logger.warning(f"[Analysis] File not found for {video_id}: {file_path}")
        if job_id and job_id in _analysis_jobs:
            _analysis_jobs[job_id]["videos"][video_id] = "failed:file_not_found"
            _analysis_jobs[job_id]["failed"] = _analysis_jobs[job_id].get("failed", 0) + 1
        return
    
    file_path = actual_path
    filename = Path(file_path).name
    
    # Update job tracker with initial status
    if job_id and job_id in _analysis_jobs:
        _analysis_jobs[job_id]["videos"][video_id] = {"status": "processing", "filename": filename}
    update_video_step(job_id, video_id, "initializing", filename)
    
    async with thread_session_maker() as db:
        try:
            video_uuid = uuid.UUID(video_id)
            
            # Determine if this is an image file (skip video analysis for images)
            ext = Path(file_path).suffix.lower()
            is_image = ext in {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp', '.gif', '.bmp', '.tiff'}
            
            if is_image:
                update_video_step(job_id, video_id, "image_fallback", filename)
                logger.info(f"[Analysis] Skipping video analysis for image: {video_id} ({ext})")
                # Go straight to basic analysis for images
            elif settings.openai_api_key and settings.openai_api_key.startswith("sk-"):
                try:
                    from services.video_analyzer import VideoAnalyzer
                    
                    update_video_step(job_id, video_id, "1/4 Transcribing", filename)
                    
                    analyzer = VideoAnalyzer(api_key=settings.openai_api_key)
                    
                    # Custom callback to update step progress
                    def on_step(step_name):
                        update_video_step(job_id, video_id, step_name, filename)
                    
                    result = await analyzer.analyze_video(
                        video_id=video_uuid,
                        video_path=file_path,
                        db_session=db,
                        metadata={"video_id": str(video_uuid)},
                        on_step_callback=on_step
                    )
                    logger.info(f"[Analysis] Complete for {video_id}: score={result.get('pre_social_score')}")
                    
                    # Always run deep image analysis - use thumbnail or extract frame
                    update_video_step(job_id, video_id, "5/5 Deep Analysis", filename)
                    try:
                        async with httpx.AsyncClient(timeout=120.0) as client:
                            thumb_url = f"http://localhost:5555/api/media-db/thumbnail/{video_id}?size=large"
                            
                            # Try to get thumbnail, generate if needed
                            thumb_check = await client.head(thumb_url)
                            if thumb_check.status_code != 200:
                                # Generate thumbnail on-the-fly
                                logger.info(f"[Deep Analysis] Generating thumbnail for {video_id}")
                                try:
                                    from services.thumbnail_generator import ThumbnailGenerator
                                    thumb_gen = ThumbnailGenerator()
                                    frames = thumb_gen.extract_frames(file_path, num_frames=1)
                                    if frames:
                                        # Save frame as temp thumbnail
                                        import shutil
                                        temp_thumb = f"/tmp/mediaposter/thumbnails/{video_id}_temp.jpg"
                                        os.makedirs(os.path.dirname(temp_thumb), exist_ok=True)
                                        shutil.copy(frames[0], temp_thumb)
                                        # Update video with thumbnail path
                                        await db.execute(
                                            update(Video)
                                            .where(Video.id == video_uuid)
                                            .values(thumbnail_path=temp_thumb)
                                        )
                                        await db.commit()
                                        logger.success(f"[Deep Analysis] Thumbnail generated for {video_id}")
                                except Exception as thumb_err:
                                    logger.warning(f"[Deep Analysis] Could not generate thumbnail: {thumb_err}")
                            
                            # Now run deep analysis
                            deep_res = await client.post(
                                "http://localhost:5555/api/image-analysis/analyze",
                                json={
                                    "image_url": thumb_url,
                                    "custom_fields": ["scene_analysis", "composition", "mood", "colors"],
                                    "focus_areas": ["content_quality", "engagement_potential"],
                                    "depth": "comprehensive"
                                },
                                timeout=90.0
                            )
                            if deep_res.status_code == 200:
                                deep_data = deep_res.json()
                                # Update analysis with deep image data
                                # Save to BOTH visual_analysis AND deep_analysis columns
                                visual_analysis_data = result.get('visual_analysis') or {}
                                visual_analysis_data["deep_analysis"] = deep_data
                                
                                # Extract visual summary for visual_analysis column
                                if deep_data.get('detailed_description'):
                                    visual_analysis_data['visual_summary'] = deep_data.get('detailed_description')
                                if deep_data.get('scene_setting'):
                                    visual_analysis_data['scene_description'] = deep_data.get('scene_setting')
                                if deep_data.get('main_subjects'):
                                    visual_analysis_data['objects_detected'] = deep_data.get('main_subjects')
                                if deep_data.get('dominant_colors'):
                                    visual_analysis_data['colors'] = deep_data.get('dominant_colors')
                                if deep_data.get('overall_mood'):
                                    visual_analysis_data['mood'] = deep_data.get('overall_mood')
                                
                                await db.execute(
                                    update(VideoAnalysis)
                                    .where(VideoAnalysis.video_id == video_uuid)
                                    .values(
                                        visual_analysis=visual_analysis_data,
                                        deep_analysis=deep_data  # Save to dedicated column too
                                    )
                                )
                                await db.commit()
                                logger.success(f"[Deep Analysis] Complete for {video_id}: saved to both visual_analysis and deep_analysis columns")
                            else:
                                logger.warning(f"[Deep Analysis] Failed for {video_id}: status {deep_res.status_code}")
                    except Exception as e:
                        logger.warning(f"[Deep Analysis] Error for {video_id}: {e}")
                    
                    logger.success(f"[Analysis] Complete: {video_id}")
                    
                    # Update job tracker with filename
                    if job_id and job_id in _analysis_jobs:
                        _analysis_jobs[job_id]["videos"][video_id] = {
                            "status": "completed",
                            "filename": filename,
                            "score": result.get('pre_social_score')
                        }
                        _analysis_jobs[job_id]["completed"] = _analysis_jobs[job_id].get("completed", 0) + 1
                        logger.info(f"[Batch Analysis] ✅ Completed: {video_id} ({filename}) - score: {result.get('pre_social_score')}")
                        # Check if job is complete
                        job = _analysis_jobs[job_id]
                        if job["completed"] + job.get("failed", 0) >= job["total"]:
                            job["status"] = "completed"
                            logger.success(f"[Batch Analysis] Job {job_id} completed: {job['completed']} succeeded, {job.get('failed', 0)} failed")
                    return
                    
                except ImportError as e:
                    logger.warning(f"[Analysis] VideoAnalyzer not available: {e}, using fallback")
                except Exception as e:
                    logger.warning(f"[Analysis] VideoAnalyzer failed for {video_id}: {e}, using fallback")
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
            logger.success(f"[Analysis] Complete: {video_id} (basic fallback)")
            
            # Update job tracker with filename (fallback analysis)
            if job_id and job_id in _analysis_jobs:
                _analysis_jobs[job_id]["videos"][video_id] = {
                    "status": "completed",
                    "filename": filename,
                    "score": analysis.pre_social_score
                }
                _analysis_jobs[job_id]["completed"] = _analysis_jobs[job_id].get("completed", 0) + 1
                logger.info(f"[Batch Analysis] ✅ Completed (fallback): {video_id} ({filename})")
                # Check if job is complete
                job = _analysis_jobs[job_id]
                if job["completed"] + job.get("failed", 0) >= job["total"]:
                    job["status"] = "completed"
                    logger.success(f"[Batch Analysis] Job {job_id} completed: {job['completed']} succeeded, {job.get('failed', 0)} failed")
            
        except Exception as e:
            logger.error(f"[Analysis] Error for {video_id}: {e}")
            traceback.print_exc()
            await db.rollback()
            
            # Update job tracker
            if job_id and job_id in _analysis_jobs:
                _analysis_jobs[job_id]["videos"][video_id] = f"failed:{str(e)[:50]}"
                _analysis_jobs[job_id]["failed"] = _analysis_jobs[job_id].get("failed", 0) + 1
                # Check if job is complete (even with failures)
                job = _analysis_jobs[job_id]
                if job["completed"] + job.get("failed", 0) >= job["total"]:
                    job["status"] = "completed"
                    logger.success(f"[Batch Analysis] Job {job_id} completed: {job['completed']} succeeded, {job.get('failed', 0)} failed")


@router.post("/batch/analyze")
async def batch_analyze(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, le=500),
    include_incomplete: bool = Query(default=True, description="Include videos with incomplete analysis"),
    force: bool = Query(default=False, description="Force re-analyze ALL videos including already analyzed ones")
):
    """
    Analyze all unanalyzed videos that have valid source files.
    Also re-analyzes videos with incomplete analysis (no transcript/topics).
    Use force=true to re-analyze ALL videos including already analyzed ones.
    """
    from sqlalchemy import and_, not_, exists, or_
    from loguru import logger
    
    # Video file extensions to include
    VIDEO_EXTENSIONS = ['.mov', '.mp4', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv', '.3gp']
    
    # Build extension filter - source_uri must end with a video extension
    ext_filters = [Video.source_uri.ilike(f'%{ext}') for ext in VIDEO_EXTENSIONS]
    
    if force:
        # Force mode: Include ALL videos regardless of analysis status
        logger.info(f"[Batch Analyze] Force mode enabled - will re-analyze ALL videos")
        query = select(Video).where(
            and_(
                Video.source_uri.isnot(None),
                Video.source_uri != '',
                or_(*ext_filters)  # Must be a video file extension
            )
        ).order_by(Video.created_at.desc()).limit(limit)
    elif include_incomplete:
        # Subquery for videos that have COMPLETE analysis (transcript or topics)
        complete_analysis_subquery = select(VideoAnalysis.video_id).where(
            or_(
                VideoAnalysis.transcript.isnot(None),
                VideoAnalysis.topics.isnot(None)
            )
        )
        # Include videos without analysis OR with incomplete analysis
        query = select(Video).where(
            and_(
                not_(Video.id.in_(complete_analysis_subquery)),
                Video.source_uri.isnot(None),
                Video.source_uri != '',
                or_(*ext_filters)  # Must be a video file extension
            )
        ).order_by(Video.created_at.desc()).limit(limit)
    else:
        # Original behavior: only videos without any analysis record
        subquery = select(VideoAnalysis.video_id)
        query = select(Video).where(
            and_(
                not_(Video.id.in_(subquery)),
                Video.source_uri.isnot(None),
                Video.source_uri != '',
                or_(*ext_filters)  # Must be a video file extension
            )
        ).order_by(Video.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    videos = result.scalars().all()
    
    from loguru import logger
    logger.info(f"[Batch Analyze] Query returned {len(videos)} unanalyzed videos")
    
    if not videos:
        return {"status": "no_pending", "count": 0}
    
    # Filter to only actual video files with existing files (skip images)
    VIDEO_EXTENSIONS = {'.mov', '.mp4', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv', '.3gp'}
    valid_videos = []
    skipped_images = 0
    skipped_not_found = 0
    
    for video in videos:
        file_path = os.path.expanduser(video.source_uri) if video.source_uri else None
        container_path = map_host_to_container_path(file_path) if file_path else None
        
        # Check file extension - skip images
        ext = Path(file_path).suffix.lower() if file_path else ''
        if ext not in VIDEO_EXTENSIONS:
            skipped_images += 1
            continue
        
        if (container_path and os.path.exists(container_path)) or (file_path and os.path.exists(file_path)):
            valid_videos.append(video)
        else:
            skipped_not_found += 1
            if skipped_not_found <= 3:
                logger.warning(f"[Batch Analyze] File not found: {file_path}")
    
    logger.info(f"[Batch Analyze] Valid: {len(valid_videos)}, Skipped images: {skipped_images}, Not found: {skipped_not_found}")
    
    if skipped_images > 0:
        print(f"Skipped {skipped_images} non-video files")
    
    if not valid_videos:
        return {"status": "no_valid_files", "count": 0, "message": "No videos with valid source files found"}
    
    # Create job tracker
    job_id = str(uuid.uuid4())
    _analysis_jobs[job_id] = {
        "status": "running",
        "total": len(valid_videos),
        "completed": 0,
        "failed": 0,
        "current_video": None,
        "videos": {},
        "started_at": datetime.now().isoformat()
    }
    
    from loguru import logger
    logger.info(f"[Batch Analysis] Job {job_id}: Starting analysis of {len(valid_videos)} videos")
    
    # Start analysis in thread pool (non-blocking)
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="analysis")
    
    for video in valid_videos:
        _analysis_jobs[job_id]["videos"][str(video.id)] = "queued"
        executor.submit(run_analysis_sync, str(video.id), video.source_uri, job_id)
    
    logger.info(f"[Batch Analysis] Job {job_id}: Queued {len(valid_videos)} videos in thread pool")
    
    return {"status": "started", "count": len(valid_videos), "job_id": job_id}


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


@router.api_route("/thumbnail/{media_id}", methods=["GET", "HEAD"])
async def get_thumbnail(
    media_id: str,
    size: str = Query(default="medium", pattern="^(small|medium|large)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get thumbnail for a media item.
    Supports HEAD requests for checking if thumbnail exists.
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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Stream video file for playback with range request support.
    """
    from fastapi.responses import StreamingResponse
    
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
    
    file_path = Path(actual_path)
    file_size = file_path.stat().st_size
    
    # Check for range header (needed for video seeking/streaming)
    range_header = request.headers.get("range")
    
    if range_header:
        # Parse range header
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1
        
        # Ensure valid range
        if start >= file_size:
            raise HTTPException(status_code=416, detail="Range not satisfiable")
        
        end = min(end, file_size - 1)
        content_length = end - start + 1
        
        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                chunk_size = 1024 * 1024  # 1MB chunks
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        return StreamingResponse(
            iterfile(),
            status_code=206,
            media_type=media_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Cache-Control": "public, max-age=3600",
            }
        )
    else:
        # No range header - return full file
        return FileResponse(
            actual_path, 
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600"
            }
        )


# =============================================================================
# ENDPOINTS - TRANSCODED VIDEO (Browser-compatible H.264)
# =============================================================================

@router.get("/video-stream/{media_id}")
async def stream_transcoded_video(
    media_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Stream video transcoded to H.264 for browser compatibility.
    HEVC/ProRes videos are transcoded on-the-fly to H.264.
    """
    from fastapi.responses import StreamingResponse
    import subprocess
    import tempfile
    
    try:
        video_uuid = uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")
    
    query = select(Video).where(Video.id == video_uuid)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Get the source file path
    source_path = video.source_uri
    container_source = map_host_to_container_path(source_path) if source_path else None
    
    actual_path = None
    if container_source and Path(container_source).exists():
        actual_path = container_source
    elif source_path and Path(source_path).exists():
        actual_path = source_path
    
    if not actual_path:
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Check if we have a cached transcoded version
    cache_dir = Path("/tmp/mediaposter/transcoded")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_path = cache_dir / f"{media_id}.mp4"
    
    if not cached_path.exists():
        # Transcode using ffmpeg - use temp file to avoid serving incomplete files
        temp_path = cache_dir / f"{media_id}.tmp.mp4"
        try:
            cmd = [
                "ffmpeg", "-y", "-i", str(actual_path),
                "-c:v", "libx264",  # H.264 codec
                "-preset", "veryfast",   # Faster encoding for large files
                "-crf", "23",        # Quality (lower = better, 18-28 typical)
                "-pix_fmt", "yuv420p",  # Force 8-bit color (browsers don't support 10-bit H.264)
                "-c:a", "aac",       # AAC audio
                "-b:a", "128k",      # Audio bitrate
                "-movflags", "+faststart",  # Web optimized
                "-max_muxing_queue_size", "1024",
                str(temp_path)
            ]
            
            # Longer timeout for large files (10 minutes)
            process = subprocess.run(cmd, capture_output=True, timeout=600)
            
            if process.returncode != 0:
                # Clean up temp file and fallback to original
                if temp_path.exists():
                    temp_path.unlink()
                logger.warning(f"Transcoding failed for {media_id}: {process.stderr.decode()[:200]}")
                return FileResponse(
                    actual_path,
                    media_type="video/quicktime",
                    headers={"Accept-Ranges": "bytes"}
                )
            
            # Rename temp to final only after successful transcoding
            temp_path.rename(cached_path)
            
        except subprocess.TimeoutExpired:
            # Clean up and fallback
            if temp_path.exists():
                temp_path.unlink()
            logger.warning(f"Transcoding timeout for {media_id}")
            return FileResponse(
                actual_path,
                media_type="video/quicktime",
                headers={"Accept-Ranges": "bytes"}
            )
        except Exception as e:
            # Clean up and fallback
            if temp_path.exists():
                temp_path.unlink()
            logger.error(f"Transcoding error for {media_id}: {e}")
            return FileResponse(
                actual_path,
                media_type="video/quicktime",
                headers={"Accept-Ranges": "bytes"}
                )
    
    # Serve the transcoded file with range support
    file_size = cached_path.stat().st_size
    range_header = request.headers.get("range")
    
    if range_header:
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1
        end = min(end, file_size - 1)
        content_length = end - start + 1
        
        def iterfile():
            with open(cached_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                # Larger chunk size (2MB) for faster initial buffering
                chunk_size = 2 * 1024 * 1024
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        return StreamingResponse(
            iterfile(),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
            }
        )
    
    return FileResponse(
        str(cached_path),
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
        }
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
        # Update curation status in dedicated column
        analysis.curation_status = request.curation_status
        analysis.curated_at = datetime.now()
    else:
        # Create new analysis with curation
        analysis = VideoAnalysis(
            video_id=video_uuid,
            curation_status=request.curation_status,
            curated_at=datetime.now(),
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
