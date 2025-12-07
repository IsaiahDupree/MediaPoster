"""
Storage Management Endpoints
Manage local storage directories and files
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from pathlib import Path
import os
from datetime import datetime

from database.connection import get_db
from services.local_storage import local_storage

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.get("/stats")
async def get_storage_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get storage usage statistics"""
    stats = {
        "local_storage_enabled": local_storage.enabled,
        "directories": {}
    }
    
    if local_storage.enabled:
        for name, path in [
            ("videos", local_storage.videos_path),
            ("thumbnails", local_storage.thumbnails_path),
            ("clips", local_storage.clips_path),
            ("temp", local_storage.temp_path)
        ]:
            if path.exists():
                files = list(path.glob("*"))
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                stats["directories"][name] = {
                    "path": str(path),
                    "file_count": len([f for f in files if f.is_file()]),
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2)
                }
            else:
                stats["directories"][name] = {
                    "path": str(path),
                    "file_count": 0,
                    "total_size_bytes": 0,
                    "total_size_mb": 0,
                    "exists": False
                }
    
    return stats


@router.get("/videos")
async def list_storage_videos(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List videos in local storage"""
    if not local_storage.enabled:
        return {"videos": [], "total": 0}
    
    videos = []
    if local_storage.videos_path.exists():
        video_files = sorted(
            [f for f in local_storage.videos_path.iterdir() if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[offset:offset+limit]
        
        for video_file in video_files:
            stat = video_file.stat()
            videos.append({
                "filename": video_file.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(video_file)
            })
    
    return {
        "videos": videos,
        "total": len(videos),
        "limit": limit,
        "offset": offset
    }


@router.get("/thumbnails")
async def list_storage_thumbnails(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List thumbnails in local storage"""
    if not local_storage.enabled:
        return {"thumbnails": [], "total": 0}
    
    thumbnails = []
    if local_storage.thumbnails_path.exists():
        thumb_files = sorted(
            [f for f in local_storage.thumbnails_path.iterdir() if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[offset:offset+limit]
        
        for thumb_file in thumb_files:
            stat = thumb_file.stat()
            thumbnails.append({
                "filename": thumb_file.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(thumb_file)
            })
    
    return {
        "thumbnails": thumbnails,
        "total": len(thumbnails),
        "limit": limit,
        "offset": offset
    }


@router.get("/clips")
async def list_storage_clips(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List clips in local storage"""
    if not local_storage.enabled:
        return {"clips": [], "total": 0}
    
    clips = []
    if local_storage.clips_path.exists():
        clip_files = sorted(
            [f for f in local_storage.clips_path.iterdir() if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[offset:offset+limit]
        
        for clip_file in clip_files:
            stat = clip_file.stat()
            clips.append({
                "filename": clip_file.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(clip_file)
            })
    
    return {
        "clips": clips,
        "total": len(clips),
        "limit": limit,
        "offset": offset
    }


@router.get("/files/videos/{video_id}")
async def get_storage_video(
    video_id: str,
    extension: str = Query("mp4", description="File extension"),
    db: AsyncSession = Depends(get_db)
):
    """Get video file from local storage"""
    if not local_storage.enabled:
        raise HTTPException(status_code=503, detail="Local storage is disabled")
    
    video_path = local_storage.get_video_path(video_id, extension)
    if not video_path or not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found in local storage")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{video_id}.{extension}"
    )


@router.get("/files/thumbnails/{video_id}")
async def get_storage_thumbnail(
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get thumbnail file from local storage"""
    if not local_storage.enabled:
        raise HTTPException(status_code=503, detail="Local storage is disabled")
    
    thumb_path = local_storage.get_thumbnail_path(video_id)
    if not thumb_path or not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found in local storage")
    
    return FileResponse(
        thumb_path,
        media_type="image/jpeg",
        filename=f"{video_id}_thumb.jpg"
    )


@router.get("/files/clips/{clip_id}")
async def get_storage_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get clip file from local storage"""
    if not local_storage.enabled:
        raise HTTPException(status_code=503, detail="Local storage is disabled")
    
    clip_path = local_storage.get_clip_path(clip_id)
    if not clip_path or not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found in local storage")
    
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        filename=f"{clip_id}.mp4"
    )


@router.post("/cleanup")
async def cleanup_storage(
    cleanup_temp: bool = Query(True, description="Clean up temp files"),
    older_than_days: Optional[int] = Query(None, description="Delete files older than N days"),
    db: AsyncSession = Depends(get_db)
):
    """Clean up storage files"""
    if not local_storage.enabled:
        return {"message": "Local storage is disabled", "cleaned": 0}
    
    cleaned = 0
    
    if cleanup_temp:
        cleaned += local_storage.cleanup_temp()
    
    if older_than_days:
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=older_than_days)
        
        for directory in [local_storage.videos_path, local_storage.thumbnails_path, local_storage.clips_path]:
            if directory.exists():
                for file in directory.iterdir():
                    if file.is_file():
                        mtime = datetime.fromtimestamp(file.stat().st_mtime)
                        if mtime < cutoff:
                            try:
                                file.unlink()
                                cleaned += 1
                            except Exception as e:
                                pass
    
    return {
        "message": f"Cleaned up {cleaned} files",
        "cleaned": cleaned
    }


@router.delete("/videos/{video_id}")
async def delete_storage_video(
    video_id: str,
    extension: str = Query("mp4", description="File extension"),
    db: AsyncSession = Depends(get_db)
):
    """Delete video from local storage"""
    if not local_storage.enabled:
        raise HTTPException(status_code=503, detail="Local storage is disabled")
    
    deleted = local_storage.delete_video(video_id, extension)
    if not deleted:
        raise HTTPException(status_code=404, detail="Video not found in local storage")
    
    return {"message": "Video deleted from local storage", "video_id": video_id}


@router.delete("/thumbnails/{video_id}")
async def delete_storage_thumbnail(
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete thumbnail from local storage"""
    if not local_storage.enabled:
        raise HTTPException(status_code=503, detail="Local storage is disabled")
    
    deleted = local_storage.delete_thumbnail(video_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Thumbnail not found in local storage")
    
    return {"message": "Thumbnail deleted from local storage", "video_id": video_id}


@router.delete("/clips/{clip_id}")
async def delete_storage_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete clip from local storage"""
    if not local_storage.enabled:
        raise HTTPException(status_code=503, detail="Local storage is disabled")
    
    deleted = local_storage.delete_clip(clip_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Clip not found in local storage")
    
    return {"message": "Clip deleted from local storage", "clip_id": clip_id}






