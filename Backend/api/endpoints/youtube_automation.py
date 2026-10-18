"""
YTP-001/007: YouTube Automation API Endpoints
REST API for the YouTube playlist pipeline.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/youtube", tags=["YouTube Automation"])


class AddPlaylistRequest(BaseModel):
    playlist_id: str
    check_interval_minutes: int = 30
    auto_process: bool = True


class ProcessVideoRequest(BaseModel):
    video_id: str
    title: str = ""
    channel: str = ""
    duration_seconds: float = 0


@router.post("/playlists")
async def add_playlist(request: AddPlaylistRequest):
    """Add a YouTube playlist to watch."""
    from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
    pipeline = YouTubePlaylistPipeline.get_instance()
    await pipeline.add_playlist(
        playlist_id=request.playlist_id,
        check_interval_minutes=request.check_interval_minutes,
        auto_process=request.auto_process,
    )
    return {"status": "added", "playlist_id": request.playlist_id}


@router.get("/playlists")
async def list_playlists():
    """List all watched playlists."""
    from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
    pipeline = YouTubePlaylistPipeline.get_instance()
    return {"playlists": pipeline.get_watched_playlists()}


@router.delete("/playlists/{playlist_id}")
async def remove_playlist(playlist_id: str):
    """Remove a playlist from the watch list."""
    from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
    pipeline = YouTubePlaylistPipeline.get_instance()
    removed = await pipeline.remove_playlist(playlist_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return {"status": "removed"}


@router.post("/process")
async def process_video(request: ProcessVideoRequest):
    """Manually trigger processing of a video."""
    from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline, PlaylistVideo
    pipeline = YouTubePlaylistPipeline.get_instance()
    video = PlaylistVideo(
        video_id=request.video_id,
        title=request.title,
        channel=request.channel,
        duration_seconds=request.duration_seconds,
    )
    job = await pipeline.process_video(video)
    return {"job_id": job.job_id, "status": job.status}


@router.get("/jobs")
async def list_jobs(status: Optional[str] = None):
    """List pipeline jobs."""
    from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
    pipeline = YouTubePlaylistPipeline.get_instance()
    jobs = pipeline.get_jobs(status=status)
    return {"jobs": [{"job_id": j.job_id, "status": j.status, "video_id": j.video.video_id} for j in jobs]}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get pipeline job status."""
    from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
    pipeline = YouTubePlaylistPipeline.get_instance()
    job = pipeline.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "video_id": job.video.video_id,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error": job.error,
    }


@router.get("/stats")
async def get_stats():
    """Get pipeline statistics."""
    from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
    pipeline = YouTubePlaylistPipeline.get_instance()
    return pipeline.get_stats()
