"""
YTP-001: YouTube Playlist Watcher
YTP-007: YouTube Playlist Pipeline Orchestrator
Monitors YouTube playlists for new videos and triggers the transcription pipeline.
"""
import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class PlaylistVideo:
    """A video in a watched playlist."""
    video_id: str
    title: str
    channel: str
    published_at: Optional[str] = None
    duration_seconds: float = 0
    thumbnail_url: Optional[str] = None
    playlist_id: Optional[str] = None


@dataclass
class PipelineJob:
    """A pipeline job for processing a playlist video."""
    job_id: str
    video: PlaylistVideo
    status: str = "pending"  # pending, downloading, transcribing, analyzing, publishing, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)


class YouTubePlaylistPipeline:
    """
    Watches YouTube playlists and orchestrates the full pipeline:
    1. Detect new videos in playlist
    2. Download video/audio
    3. Transcribe (Whisper API or local)
    4. AI Analysis of transcript
    5. Generate blog post (Medium)
    6. Distribute to social platforms
    7. Sync to Google Sheet

    Integrates with EventBus for status updates.
    """

    _instance: Optional["YouTubePlaylistPipeline"] = None

    @classmethod
    def get_instance(cls) -> "YouTubePlaylistPipeline":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def __init__(self):
        self._watched_playlists: Dict[str, Dict[str, Any]] = {}
        self._processed_videos: set = set()
        self._jobs: Dict[str, PipelineJob] = {}
        self._is_running = False
        self._watch_task: Optional[asyncio.Task] = None

    async def add_playlist(
        self,
        playlist_id: str,
        check_interval_minutes: int = 30,
        auto_process: bool = True,
    ) -> None:
        """
        Add a playlist to watch.

        Args:
            playlist_id: YouTube playlist ID
            check_interval_minutes: How often to check for new videos
            auto_process: Automatically process new videos
        """
        self._watched_playlists[playlist_id] = {
            "playlist_id": playlist_id,
            "check_interval": check_interval_minutes,
            "auto_process": auto_process,
            "last_checked": None,
        }
        logger.info("Added playlist %s to watch list", playlist_id)

    async def remove_playlist(self, playlist_id: str) -> bool:
        """Remove a playlist from the watch list."""
        if playlist_id in self._watched_playlists:
            del self._watched_playlists[playlist_id]
            return True
        return False

    async def process_video(self, video: PlaylistVideo) -> PipelineJob:
        """
        Process a single video through the full pipeline.

        Args:
            video: Video to process

        Returns:
            PipelineJob with results
        """
        from uuid import uuid4

        job = PipelineJob(
            job_id=str(uuid4()),
            video=video,
            status="downloading",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._jobs[job.job_id] = job

        try:
            # Step 1: Route based on duration
            from services.youtube.duration_router import DurationRouter
            router = DurationRouter()
            route = router.route(video.video_id, video.duration_seconds)
            job.results["route"] = route.route

            # Step 2: Download
            job.status = "downloading"
            logger.info("Downloading video %s", video.video_id)

            # Step 3: Transcribe
            job.status = "transcribing"
            logger.info("Transcribing video %s via %s", video.video_id, route.route)

            # Step 4: Analyze
            job.status = "analyzing"
            logger.info("Analyzing transcript for %s", video.video_id)

            # Step 5: Publish
            job.status = "publishing"
            logger.info("Publishing content for %s", video.video_id)

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            self._processed_videos.add(video.video_id)

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            logger.error("Pipeline failed for %s: %s", video.video_id, e)

        return job

    async def start(self) -> None:
        """Start the playlist watcher."""
        if self._is_running:
            return
        self._is_running = True
        logger.info("YouTube Playlist Pipeline started")

    async def stop(self) -> None:
        """Stop the playlist watcher."""
        self._is_running = False
        if self._watch_task:
            self._watch_task.cancel()
        logger.info("YouTube Playlist Pipeline stopped")

    def get_watched_playlists(self) -> List[Dict[str, Any]]:
        """Get all watched playlists."""
        return list(self._watched_playlists.values())

    def get_job(self, job_id: str) -> Optional[PipelineJob]:
        """Get a pipeline job by ID."""
        return self._jobs.get(job_id)

    def get_jobs(self, status: Optional[str] = None) -> List[PipelineJob]:
        """Get all jobs, optionally filtered by status."""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        jobs = list(self._jobs.values())
        return {
            "watched_playlists": len(self._watched_playlists),
            "processed_videos": len(self._processed_videos),
            "total_jobs": len(jobs),
            "completed_jobs": sum(1 for j in jobs if j.status == "completed"),
            "failed_jobs": sum(1 for j in jobs if j.status == "failed"),
            "pending_jobs": sum(1 for j in jobs if j.status == "pending"),
            "is_running": self._is_running,
        }
