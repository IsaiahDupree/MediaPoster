"""
Media Provider API Endpoints
Centralized endpoints for serving and streaming media.
"""
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from typing import Optional
from loguru import logger

from services.media_provider import get_media_provider, MediaType

router = APIRouter(prefix="/api/media-provider", tags=["Media Provider"])


@router.get("/health")
async def health_check():
    """Health check for media provider service."""
    provider = get_media_provider()
    stats = await provider.get_stats()
    return {
        "status": "healthy",
        "service": "media_provider",
        "stats": stats
    }


@router.get("/info/{media_id}")
async def get_media_info(media_id: str):
    """Get detailed information about a media file."""
    provider = get_media_provider()
    media_info = await provider.get_media_info(media_id)
    
    if not media_info:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return {
        "id": media_info.id,
        "filename": media_info.filename,
        "file_path": media_info.file_path,
        "media_type": media_info.media_type.value,
        "file_size": media_info.file_size,
        "duration_sec": media_info.duration_sec,
        "resolution": media_info.resolution,
        "thumbnail_path": media_info.thumbnail_path,
        "mime_type": media_info.mime_type,
        "file_exists": provider.validate_file_exists(media_info.file_path)
    }


@router.get("/thumbnail/{media_id}")
async def get_thumbnail(
    media_id: str,
    size: str = Query("medium", regex="^(small|medium|large)$")
):
    """
    Get thumbnail for a media file.
    Sizes: small (160px), medium (320px), large (640px)
    """
    provider = get_media_provider()
    return await provider.get_thumbnail_response(media_id, size)


@router.get("/stream/{media_id}")
async def stream_video(media_id: str, request: Request):
    """
    Stream video with range request support for seeking.
    Supports partial content (HTTP 206) for video players.
    """
    provider = get_media_provider()
    range_header = request.headers.get("Range")
    return await provider.get_video_stream(media_id, range_header)


@router.get("/image/{media_id}")
async def get_image(media_id: str):
    """Serve an image file."""
    provider = get_media_provider()
    return await provider.get_image_response(media_id)


@router.get("/file/{media_id}")
async def get_file(media_id: str, request: Request):
    """
    Get any media file - auto-detects type and serves appropriately.
    """
    provider = get_media_provider()
    media_info = await provider.get_media_info(media_id)
    
    if not media_info:
        raise HTTPException(status_code=404, detail="Media not found")
    
    if media_info.media_type == MediaType.VIDEO:
        range_header = request.headers.get("Range")
        return await provider.get_video_stream(media_id, range_header)
    elif media_info.media_type == MediaType.IMAGE:
        return await provider.get_image_response(media_id)
    else:
        # Generic file response
        if not provider.validate_file_exists(media_info.file_path):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(
            media_info.file_path,
            media_type=media_info.mime_type or "application/octet-stream"
        )


@router.get("/list")
async def list_media(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    type: Optional[str] = Query(None, regex="^(video|image|audio)$")
):
    """List media files with optional filtering."""
    provider = get_media_provider()
    
    media_type = None
    if type:
        media_type = MediaType(type)
    
    media_list = await provider.list_media(limit, offset, media_type)
    
    return {
        "items": [
            {
                "id": m.id,
                "filename": m.filename,
                "media_type": m.media_type.value,
                "duration_sec": m.duration_sec,
                "resolution": m.resolution,
                "has_thumbnail": m.thumbnail_path is not None,
                "thumbnail_url": f"/api/media-provider/thumbnail/{m.id}" if m.thumbnail_path else None,
                "stream_url": f"/api/media-provider/stream/{m.id}"
            }
            for m in media_list
        ],
        "count": len(media_list),
        "limit": limit,
        "offset": offset
    }


@router.get("/stats")
async def get_stats():
    """Get media library statistics."""
    provider = get_media_provider()
    return await provider.get_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear the media provider cache."""
    provider = get_media_provider()
    provider.clear_cache()
    return {"status": "cache_cleared"}


@router.get("/by-filename/{filename}")
async def get_by_filename(filename: str, request: Request):
    """Get media by filename and stream it."""
    provider = get_media_provider()
    media_info = await provider.get_media_by_filename(filename)
    
    if not media_info:
        raise HTTPException(status_code=404, detail="Media not found")
    
    if media_info.media_type == MediaType.VIDEO:
        range_header = request.headers.get("Range")
        return await provider.get_video_stream(media_info.id, range_header)
    else:
        return await provider.get_image_response(media_info.id)
