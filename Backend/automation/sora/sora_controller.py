"""
Sora Controller - Service-oriented video generation controller.

Provides a high-level interface for controlling Sora video generation
through the service pipeline (not direct Safari automation).

For the pipeline-based generation flow, see pipeline.py.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SoraController:
    """
    High-level controller for Sora video generation.

    Manages generation queue, monitors progress, and coordinates
    with the pipeline for video creation.
    """

    MAX_CONCURRENT = 3  # Sora's concurrent generation limit
    BASE_URL = "https://sora.chatgpt.com"

    def __init__(self):
        self._queue: List[Dict[str, Any]] = []
        self._active: List[Dict[str, Any]] = []
        self._completed: List[Dict[str, Any]] = []
        self._is_running = False
        logger.info("SoraController initialized")

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self):
        """Start the controller."""
        self._is_running = True
        logger.info("SoraController started")

    def stop(self):
        """Stop the controller."""
        self._is_running = False
        logger.info("SoraController stopped")

    def enqueue(self, prompt: str, character: Optional[str] = None,
                duration: int = 15, aspect_ratio: str = "Portrait") -> str:
        """Add a video generation job to the queue."""
        job_id = f"sora-{len(self._queue) + len(self._completed) + 1}"
        job = {
            "id": job_id,
            "prompt": prompt,
            "character": character,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._queue.append(job)
        logger.info(f"Enqueued job {job_id}: {prompt[:50]}...")
        return job_id

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            "queued": len(self._queue),
            "active": len(self._active),
            "completed": len(self._completed),
            "max_concurrent": self.MAX_CONCURRENT,
        }

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific job by ID."""
        for job in self._queue + self._active + self._completed:
            if job["id"] == job_id:
                return job
        return None
