"""
Media Processing API Endpoints
Supports iOS, Android, and web clients for media ingestion and analysis.
"""
import os
import uuid
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/media", tags=["Media Processing"])

# =============================================================================
# MODELS
# =============================================================================

class MediaStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    INGESTING = "ingesting"
    INGESTED = "ingested"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class MediaType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"


class UploadInitRequest(BaseModel):
    """Request to initialize an upload session."""
    filename: str
    file_size: int
    content_type: str
    client_type: str = Field(default="web", description="ios, android, or web")
    checksum: Optional[str] = Field(None, description="MD5 or SHA256 for verification")


class UploadInitResponse(BaseModel):
    """Response with upload session details."""
    upload_id: str
    upload_url: str
    chunk_size: int
    expires_at: str


class MediaUploadResponse(BaseModel):
    """Response after successful upload."""
    media_id: str
    filename: str
    status: MediaStatus
    file_size: int
    media_type: MediaType
    created_at: str


class MediaStatusResponse(BaseModel):
    """Current status of media processing."""
    media_id: str
    filename: str
    status: MediaStatus
    progress: float = Field(description="0.0 to 1.0")
    error_message: Optional[str] = None
    analysis_result: Optional[dict] = None
    created_at: str
    updated_at: str


class AnalysisResult(BaseModel):
    """AI analysis results."""
    media_id: str
    pre_social_score: Optional[float] = None
    hook_strength: Optional[int] = None
    pacing_score: Optional[int] = None
    transcript: Optional[str] = None
    topics: Optional[List[str]] = None
    suggested_captions: Optional[List[str]] = None
    analyzed_at: str


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


class JobStatusResponse(BaseModel):
    """Status of a background job."""
    job_id: str
    status: str
    total_files: int
    processed_count: int
    success_count: int
    failed_count: int
    progress: float
    started_at: str
    updated_at: str
    can_resume: bool


# =============================================================================
# IN-MEMORY STATE (Replace with Redis/DB in production)
# =============================================================================

upload_sessions = {}  # upload_id -> session data
media_items = {}  # media_id -> media data
background_jobs = {}  # job_id -> job state


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_media_type(filename: str) -> MediaType:
    """Determine media type from filename."""
    ext = Path(filename).suffix.lower()
    video_exts = {'.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm'}
    if ext in video_exts:
        return MediaType.VIDEO
    return MediaType.IMAGE


def compute_file_hash(data: bytes) -> str:
    """Compute MD5 hash of file data."""
    return hashlib.md5(data).hexdigest()


async def run_analysis(media_id: str, file_path: str):
    """Run AI analysis on uploaded media."""
    try:
        media = media_items.get(media_id)
        if not media:
            return
        
        media["status"] = MediaStatus.ANALYZING
        media["updated_at"] = datetime.now().isoformat()
        
        # Simulate analysis (replace with real AI service)
        await asyncio.sleep(2)
        
        import random
        media["analysis_result"] = {
            "pre_social_score": random.randint(65, 95),
            "hook_strength": random.randint(6, 10),
            "pacing_score": random.randint(6, 10),
            "transcript": "Sample transcript from AI analysis...",
            "topics": ["tech", "tutorial", "DIY"],
            "suggested_captions": [
                "This changed everything 🔥 #tech",
                "Wait for it... #viral",
                "You won't believe this trick 💡"
            ],
            "analyzed_at": datetime.now().isoformat()
        }
        
        media["status"] = MediaStatus.ANALYZED
        media["progress"] = 1.0
        media["updated_at"] = datetime.now().isoformat()
        
    except Exception as e:
        media["status"] = MediaStatus.FAILED
        media["error_message"] = str(e)
        media["updated_at"] = datetime.now().isoformat()


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/upload/init", response_model=UploadInitResponse)
async def init_upload(request: UploadInitRequest):
    """
    Initialize an upload session for large file uploads.
    Supports chunked uploads for mobile clients.
    """
    upload_id = str(uuid.uuid4())
    
    # Determine chunk size based on client type
    chunk_sizes = {
        "ios": 5 * 1024 * 1024,      # 5MB for iOS
        "android": 5 * 1024 * 1024,   # 5MB for Android
        "web": 10 * 1024 * 1024       # 10MB for web
    }
    chunk_size = chunk_sizes.get(request.client_type, 10 * 1024 * 1024)
    
    expires_at = datetime.now().isoformat()
    
    upload_sessions[upload_id] = {
        "filename": request.filename,
        "file_size": request.file_size,
        "content_type": request.content_type,
        "client_type": request.client_type,
        "checksum": request.checksum,
        "chunks_received": 0,
        "total_chunks": (request.file_size + chunk_size - 1) // chunk_size,
        "created_at": datetime.now().isoformat()
    }
    
    return UploadInitResponse(
        upload_id=upload_id,
        upload_url=f"/api/media/upload/{upload_id}",
        chunk_size=chunk_size,
        expires_at=expires_at
    )


@router.post("/upload", response_model=MediaUploadResponse)
async def upload_media(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_analyze: bool = Form(default=True),
    client_type: str = Form(default="web")
):
    """
    Upload a media file directly (for smaller files).
    Automatically triggers analysis if auto_analyze is True.
    """
    media_id = str(uuid.uuid4())
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    file_hash = compute_file_hash(content)
    
    # Check for duplicates
    for existing_id, existing in media_items.items():
        if existing.get("file_hash") == file_hash:
            return MediaUploadResponse(
                media_id=existing_id,
                filename=existing["filename"],
                status=existing["status"],
                file_size=existing["file_size"],
                media_type=existing["media_type"],
                created_at=existing["created_at"]
            )
    
    # Save file
    upload_dir = Path(os.getenv("TEMP_DIR", "/tmp/mediaposter")) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / f"{media_id}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)
    
    media_type = get_media_type(file.filename)
    now = datetime.now().isoformat()
    
    media_items[media_id] = {
        "media_id": media_id,
        "filename": file.filename,
        "file_path": str(file_path),
        "file_size": file_size,
        "file_hash": file_hash,
        "media_type": media_type,
        "status": MediaStatus.UPLOADED,
        "progress": 0.0,
        "client_type": client_type,
        "created_at": now,
        "updated_at": now,
        "analysis_result": None,
        "error_message": None
    }
    
    # Start analysis in background
    if auto_analyze:
        media_items[media_id]["status"] = MediaStatus.INGESTED
        media_items[media_id]["progress"] = 0.3
        background_tasks.add_task(run_analysis, media_id, str(file_path))
    
    return MediaUploadResponse(
        media_id=media_id,
        filename=file.filename,
        status=media_items[media_id]["status"],
        file_size=file_size,
        media_type=media_type,
        created_at=now
    )


@router.get("/status/{media_id}", response_model=MediaStatusResponse)
async def get_media_status(media_id: str):
    """
    Get current processing status of a media item.
    Clients should poll this endpoint for progress updates.
    """
    media = media_items.get(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return MediaStatusResponse(
        media_id=media["media_id"],
        filename=media["filename"],
        status=media["status"],
        progress=media["progress"],
        error_message=media.get("error_message"),
        analysis_result=media.get("analysis_result"),
        created_at=media["created_at"],
        updated_at=media["updated_at"]
    )


@router.get("/analysis/{media_id}", response_model=AnalysisResult)
async def get_analysis(media_id: str):
    """
    Get AI analysis results for a media item.
    Returns 404 if not found, 202 if still processing.
    """
    media = media_items.get(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    if media["status"] != MediaStatus.ANALYZED:
        raise HTTPException(
            status_code=202, 
            detail=f"Analysis in progress. Status: {media['status']}"
        )
    
    result = media.get("analysis_result", {})
    return AnalysisResult(
        media_id=media_id,
        pre_social_score=result.get("pre_social_score"),
        hook_strength=result.get("hook_strength"),
        pacing_score=result.get("pacing_score"),
        transcript=result.get("transcript"),
        topics=result.get("topics"),
        suggested_captions=result.get("suggested_captions"),
        analyzed_at=result.get("analyzed_at", datetime.now().isoformat())
    )


@router.get("/list", response_model=List[MediaStatusResponse])
async def list_media(
    status: Optional[MediaStatus] = None,
    media_type: Optional[MediaType] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    List all media items with optional filtering.
    """
    items = list(media_items.values())
    
    if status:
        items = [i for i in items if i["status"] == status]
    if media_type:
        items = [i for i in items if i["media_type"] == media_type]
    
    # Sort by created_at descending
    items.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Paginate
    items = items[offset:offset + limit]
    
    return [
        MediaStatusResponse(
            media_id=i["media_id"],
            filename=i["filename"],
            status=i["status"],
            progress=i["progress"],
            error_message=i.get("error_message"),
            analysis_result=i.get("analysis_result"),
            created_at=i["created_at"],
            updated_at=i["updated_at"]
        )
        for i in items
    ]


@router.post("/batch/ingest", response_model=BatchIngestResponse)
async def batch_ingest(request: BatchIngestRequest, background_tasks: BackgroundTasks):
    """
    Start batch ingestion from a directory.
    Supports smart resume - will skip already processed files.
    """
    job_id = str(uuid.uuid4())
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
    
    # Initialize job state
    background_jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "directory": str(directory),
        "total_files": total_files,
        "processed_count": 0,
        "success_count": 0,
        "failed_count": 0,
        "progress": 0.0,
        "resume": request.resume,
        "started_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "can_resume": True,
        "files_state": {}
    }
    
    # Start background processing
    background_tasks.add_task(process_batch_job, job_id, files)
    
    return BatchIngestResponse(
        job_id=job_id,
        total_files=total_files,
        status="started",
        message=f"Processing {total_files} files from {directory}"
    )


async def process_batch_job(job_id: str, files: List[Path]):
    """Process files in a batch job."""
    job = background_jobs.get(job_id)
    if not job:
        return
    
    for i, file_path in enumerate(files):
        try:
            # Check if already processed (for resume)
            file_hash = compute_file_hash(file_path.read_bytes()[:1024*1024])
            
            if job["resume"]:
                existing = next(
                    (m for m in media_items.values() if m.get("file_hash") == file_hash),
                    None
                )
                if existing:
                    job["processed_count"] += 1
                    job["success_count"] += 1
                    continue
            
            # Create media entry
            media_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            media_items[media_id] = {
                "media_id": media_id,
                "filename": file_path.name,
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "file_hash": file_hash,
                "media_type": get_media_type(file_path.name),
                "status": MediaStatus.INGESTED,
                "progress": 0.5,
                "client_type": "batch",
                "created_at": now,
                "updated_at": now,
                "analysis_result": None,
                "error_message": None
            }
            
            # Run analysis
            await run_analysis(media_id, str(file_path))
            
            job["processed_count"] += 1
            job["success_count"] += 1
            
        except Exception as e:
            job["processed_count"] += 1
            job["failed_count"] += 1
            job["files_state"][str(file_path)] = {"error": str(e)}
        
        # Update progress
        job["progress"] = job["processed_count"] / job["total_files"]
        job["updated_at"] = datetime.now().isoformat()
    
    job["status"] = "completed"
    job["can_resume"] = False


@router.get("/batch/status/{job_id}", response_model=JobStatusResponse)
async def get_batch_status(job_id: str):
    """
    Get status of a batch ingestion job.
    Clients can poll this to track progress.
    """
    job = background_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        total_files=job["total_files"],
        processed_count=job["processed_count"],
        success_count=job["success_count"],
        failed_count=job["failed_count"],
        progress=job["progress"],
        started_at=job["started_at"],
        updated_at=job["updated_at"],
        can_resume=job["can_resume"]
    )


@router.post("/batch/resume/{job_id}", response_model=BatchIngestResponse)
async def resume_batch(job_id: str, background_tasks: BackgroundTasks):
    """
    Resume a failed or stopped batch job.
    """
    job = background_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job["can_resume"]:
        raise HTTPException(status_code=400, detail="Job cannot be resumed")
    
    directory = Path(job["directory"])
    video_exts = {'.mov', '.mp4', '.m4v', '.avi', '.mkv'}
    image_exts = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
    all_exts = video_exts | image_exts
    
    files = [f for f in directory.iterdir() if f.suffix.lower() in all_exts]
    
    job["status"] = "running"
    job["updated_at"] = datetime.now().isoformat()
    
    background_tasks.add_task(process_batch_job, job_id, files)
    
    return BatchIngestResponse(
        job_id=job_id,
        total_files=job["total_files"],
        status="resumed",
        message=f"Resumed processing. {job['processed_count']}/{job['total_files']} already done."
    )


@router.post("/retry/{media_id}", response_model=MediaStatusResponse)
async def retry_analysis(media_id: str, background_tasks: BackgroundTasks):
    """
    Retry analysis for a failed media item.
    """
    media = media_items.get(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    if media["status"] != MediaStatus.FAILED:
        raise HTTPException(status_code=400, detail="Media is not in failed state")
    
    media["status"] = MediaStatus.INGESTED
    media["error_message"] = None
    media["progress"] = 0.3
    media["updated_at"] = datetime.now().isoformat()
    
    background_tasks.add_task(run_analysis, media_id, media["file_path"])
    
    return MediaStatusResponse(
        media_id=media["media_id"],
        filename=media["filename"],
        status=media["status"],
        progress=media["progress"],
        error_message=None,
        analysis_result=None,
        created_at=media["created_at"],
        updated_at=media["updated_at"]
    )


@router.delete("/{media_id}")
async def delete_media(media_id: str):
    """Delete a media item."""
    if media_id not in media_items:
        raise HTTPException(status_code=404, detail="Media not found")
    
    media = media_items.pop(media_id)
    
    # Delete file if exists
    file_path = Path(media.get("file_path", ""))
    if file_path.exists():
        file_path.unlink()
    
    return {"message": "Media deleted", "media_id": media_id}


@router.get("/thumbnail/{media_id}")
async def get_thumbnail(
    media_id: str,
    size: str = Query(default="medium", pattern="^(small|medium|large)$")
):
    """
    Get thumbnail for a media item.
    Generates thumbnail on-the-fly if not cached.
    
    Sizes: small (200px), medium (400px), large (800px)
    """
    media = media_items.get(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    file_path = media.get("file_path")
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Media file not found")
    
    try:
        from services.thumbnail_service import generate_thumbnail
        
        thumbnail_path = generate_thumbnail(file_path, size)
        
        if thumbnail_path and Path(thumbnail_path).exists():
            return FileResponse(
                thumbnail_path,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                    "X-Media-ID": media_id
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate thumbnail")
            
    except ImportError:
        # Fallback: return a placeholder or the original file
        raise HTTPException(status_code=501, detail="Thumbnail service not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thumbnail error: {str(e)}")


# =============================================================================
# THUMBNAIL GENERATION
# =============================================================================

thumbnail_jobs = {}  # job_id -> job state


class ThumbnailJobResponse(BaseModel):
    """Response for thumbnail generation job."""
    job_id: str
    status: str
    total_files: int
    processed_count: int
    success_count: int
    failed_count: int
    progress: float
    message: str


@router.post("/thumbnails/generate", response_model=ThumbnailJobResponse)
async def generate_thumbnails(
    background_tasks: BackgroundTasks,
    sizes: List[str] = ["small", "medium", "large"]
):
    """
    Generate thumbnails for all processed media.
    Uses smart resume - skips already generated thumbnails.
    """
    # Get all media with file paths
    files_to_process = [
        media["file_path"]
        for media in media_items.values()
        if media.get("file_path") and Path(media["file_path"]).exists()
    ]
    
    if not files_to_process:
        raise HTTPException(status_code=400, detail="No media files available for thumbnail generation")
    
    job_id = str(uuid.uuid4())
    
    thumbnail_jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "total_files": len(files_to_process),
        "processed_count": 0,
        "success_count": 0,
        "failed_count": 0,
        "progress": 0.0,
        "sizes": sizes,
        "started_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(process_thumbnail_job, job_id, files_to_process, sizes)
    
    return ThumbnailJobResponse(
        job_id=job_id,
        status="started",
        total_files=len(files_to_process),
        processed_count=0,
        success_count=0,
        failed_count=0,
        progress=0.0,
        message=f"Generating thumbnails for {len(files_to_process)} files"
    )


async def process_thumbnail_job(job_id: str, files: List[str], sizes: List[str]):
    """Process thumbnail generation job."""
    job = thumbnail_jobs.get(job_id)
    if not job:
        return
    
    try:
        from services.thumbnail_service import generate_thumbnail_smart, get_thumbnail_state
        
        state = get_thumbnail_state()
        total_tasks = len(files) * len(sizes)
        completed = 0
        
        for file_path in files:
            for size in sizes:
                try:
                    # Check if already exists (smart resume)
                    existing = state.get_thumb_path(file_path, size)
                    if existing:
                        job["success_count"] += 1
                    else:
                        result = generate_thumbnail_smart(file_path, size)
                        if result:
                            job["success_count"] += 1
                        else:
                            job["failed_count"] += 1
                except Exception:
                    job["failed_count"] += 1
                
                completed += 1
                job["processed_count"] = completed // len(sizes)
                job["progress"] = completed / total_tasks
                job["updated_at"] = datetime.now().isoformat()
        
        job["status"] = "completed"
        
    except ImportError:
        job["status"] = "failed"
        job["updated_at"] = datetime.now().isoformat()


@router.get("/thumbnails/status/{job_id}", response_model=ThumbnailJobResponse)
async def get_thumbnail_job_status(job_id: str):
    """Get status of a thumbnail generation job."""
    job = thumbnail_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return ThumbnailJobResponse(
        job_id=job["job_id"],
        status=job["status"],
        total_files=job["total_files"],
        processed_count=job["processed_count"],
        success_count=job["success_count"],
        failed_count=job["failed_count"],
        progress=job["progress"],
        message=f"{job['status'].title()}: {job['processed_count']}/{job['total_files']} files"
    )


@router.get("/thumbnails/stats")
async def get_thumbnail_stats():
    """Get thumbnail generation statistics."""
    try:
        from services.thumbnail_service import get_thumbnail_state
        state = get_thumbnail_state()
        return state.get_stats()
    except ImportError:
        return {"error": "Thumbnail service not available"}


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for media processing service."""
    return {
        "status": "healthy",
        "service": "media-processing",
        "timestamp": datetime.now().isoformat(),
        "stats": {
            "total_media": len(media_items),
            "active_jobs": len([j for j in background_jobs.values() if j["status"] == "running"]),
            "pending_uploads": len(upload_sessions),
            "thumbnail_jobs": len([j for j in thumbnail_jobs.values() if j["status"] == "running"])
        }
    }
