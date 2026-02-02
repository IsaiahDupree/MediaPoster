"""
Sora Generation Monitor - Tracks video generation progress.

Monitors ongoing Sora video generation jobs, tracks completion status,
and provides progress reporting.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class GenerationMonitor:
    """
    Monitors Sora video generation progress.

    Tracks active generations, estimated completion times,
    and provides real-time status updates.
    """

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._is_monitoring = False
        logger.info("GenerationMonitor initialized")

    def start_monitoring(self, job_id: str, prompt: str) -> None:
        """Start monitoring a generation job."""
        self._jobs[job_id] = {
            "id": job_id,
            "prompt": prompt,
            "status": "generating",
            "progress": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "video_path": None,
        }
        self._is_monitoring = True
        logger.info(f"Monitoring job {job_id}")

    def update_progress(self, job_id: str, progress: int) -> None:
        """Update generation progress (0-100)."""
        if job_id in self._jobs:
            self._jobs[job_id]["progress"] = min(100, max(0, progress))

    def mark_completed(self, job_id: str, video_path: str) -> None:
        """Mark a generation job as completed."""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = "completed"
            self._jobs[job_id]["progress"] = 100
            self._jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            self._jobs[job_id]["video_path"] = video_path
            logger.info(f"Job {job_id} completed: {video_path}")

    def mark_failed(self, job_id: str, error: str) -> None:
        """Mark a generation job as failed."""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = "failed"
            self._jobs[job_id]["error"] = error
            logger.error(f"Job {job_id} failed: {error}")

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job."""
        return self._jobs.get(job_id)

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get all active (non-completed) jobs."""
        return [j for j in self._jobs.values() if j["status"] == "generating"]

    def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get all monitored jobs."""
        return dict(self._jobs)
