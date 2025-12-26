"""
Audio API Endpoints
Fetch, store, and serve Instagram audio files.
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
from loguru import logger

from services.audio_service import get_audio_service, AudioMetadata

router = APIRouter(prefix="/api/audio", tags=["Audio Service"])


class FetchAudioRequest(BaseModel):
    """Request to fetch audio from a reel"""
    reel_url: str


class AudioResponse(BaseModel):
    """Audio metadata response"""
    audio_id: str
    title: str
    artist: str
    duration_ms: Optional[int] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    stream_url: Optional[str] = None
    download_url: Optional[str] = None
    cover_url: Optional[str] = None
    source: str = "instagram"


@router.get("/health")
async def health_check():
    """Health check for audio service"""
    service = get_audio_service()
    stored = service.list_stored_audio()
    return {
        "status": "healthy",
        "service": "audio",
        "stored_files": len(stored),
        "storage_dir": str(service.storage_dir)
    }


@router.post("/fetch")
async def fetch_audio_from_reel(request: FetchAudioRequest):
    """
    Fetch and download audio from an Instagram reel.
    
    The audio will be stored locally and can be streamed/downloaded.
    """
    service = get_audio_service()
    
    try:
        audio_metadata = await service.fetch_and_store_audio(request.reel_url)
        
        if not audio_metadata:
            raise HTTPException(
                status_code=404,
                detail="Could not extract audio from the provided reel"
            )
        
        return AudioResponse(
            audio_id=audio_metadata.audio_id,
            title=audio_metadata.title,
            artist=audio_metadata.artist,
            duration_ms=audio_metadata.duration_ms,
            file_path=audio_metadata.file_path,
            file_size=audio_metadata.file_size,
            stream_url=f"/api/audio/stream/{audio_metadata.audio_id}",
            download_url=f"/api/audio/download/{audio_metadata.audio_id}",
            cover_url=audio_metadata.cover_url,
            source=audio_metadata.source
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/{audio_id}")
async def stream_audio(audio_id: str):
    """
    Stream audio file for playback.
    
    Returns audio file with proper headers for browser playback.
    """
    service = get_audio_service()
    
    file_path = service.get_stored_audio_path(audio_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600"
        }
    )


@router.get("/download/{audio_id}")
async def download_audio(audio_id: str):
    """
    Download audio file.
    
    Returns audio file as attachment for download.
    """
    service = get_audio_service()
    
    file_path = service.get_stored_audio_path(audio_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg",
        filename=file_path.name,
        headers={
            "Content-Disposition": f'attachment; filename="{file_path.name}"'
        }
    )


@router.get("/list")
async def list_stored_audio():
    """
    List all locally stored audio files.
    """
    service = get_audio_service()
    audio_files = service.list_stored_audio()
    
    return {
        "count": len(audio_files),
        "storage_dir": str(service.storage_dir),
        "files": audio_files
    }


@router.get("/info/{audio_id}")
async def get_audio_info(audio_id: str):
    """
    Get metadata for a stored audio file.
    """
    service = get_audio_service()
    
    # Check if file exists
    file_path = service.get_stored_audio_path(audio_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    # Get cached metadata or build from file
    metadata = service.get_audio_metadata(audio_id)
    
    if metadata:
        return AudioResponse(
            audio_id=metadata.audio_id,
            title=metadata.title,
            artist=metadata.artist,
            duration_ms=metadata.duration_ms,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            stream_url=f"/api/audio/stream/{audio_id}",
            download_url=f"/api/audio/download/{audio_id}",
            cover_url=metadata.cover_url,
            source=metadata.source
        )
    
    # Build basic info from file
    return {
        "audio_id": audio_id,
        "filename": file_path.name,
        "file_path": str(file_path),
        "file_size": file_path.stat().st_size,
        "stream_url": f"/api/audio/stream/{audio_id}",
        "download_url": f"/api/audio/download/{audio_id}"
    }


@router.delete("/{audio_id}")
async def delete_audio(audio_id: str):
    """
    Delete a stored audio file.
    """
    service = get_audio_service()
    
    file_path = service.get_stored_audio_path(audio_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    try:
        file_path.unlink()
        logger.info(f"Deleted audio file: {file_path}")
        return {"status": "deleted", "audio_id": audio_id}
    except Exception as e:
        logger.error(f"Error deleting audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
