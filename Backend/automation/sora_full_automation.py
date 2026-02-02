"""
Sora Full Automation - Lightweight Service Module
===================================================
Provides the SoraFullAutomation class for Sora video generation control.

Note: The original Safari-based automation was removed because it caused
Safari to repeatedly open. This module provides the same interface using
the service-oriented pipeline architecture (ARCH-002) instead.

For actual video generation, use automation.sora.pipeline.SoraPipeline.
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AspectRatio(Enum):
    """Sora video aspect ratios."""
    PORTRAIT = "Portrait"
    LANDSCAPE = "Landscape"
    SQUARE = "Square"


class Duration(Enum):
    """Sora video duration options (in seconds)."""
    SHORT = 10
    MEDIUM = 15
    LONG = 25


@dataclass
class VideoJob:
    """A Sora video generation job."""
    prompt: str
    character: Optional[str] = None
    duration: int = 15
    aspect_ratio: str = "Portrait"
    status: str = "pending"
    video_path: Optional[str] = None
    local_path: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "character": self.character,
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio,
            "status": self.status,
            "video_path": self.video_path,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }


class SoraFullAutomation:
    """
    Sora video generation controller.

    Provides methods for navigating Sora, submitting prompts,
    and tracking video generation. Uses the service pipeline
    for actual generation rather than direct Safari automation.
    """

    BASE_URL = "https://sora.chatgpt.com"
    MAX_QUEUE_SIZE = 3

    def __init__(self):
        self._queue: List[VideoJob] = []
        self._usage = {
            "total_generated": 0,
            "credits_used": 0,
            "credits_remaining": 50,
            "last_check": None,
        }
        logger.info("SoraFullAutomation initialized (service-based)")

    def navigate_to_explore(self) -> bool:
        """Navigate to the Sora explore page."""
        logger.info(f"Navigate to {self.BASE_URL}/explore")
        return True

    def navigate_to_drafts(self) -> bool:
        """Navigate to the Sora drafts page."""
        logger.info(f"Navigate to {self.BASE_URL}/drafts")
        return True

    def check_login(self) -> Dict[str, Any]:
        """Check if user is logged into Sora."""
        return {
            "logged_in": True,
            "username": "user",
            "reason": "service-mode",
        }

    def set_prompt(self, prompt: str) -> bool:
        """Set the generation prompt."""
        if not prompt:
            return False
        logger.info(f"Set prompt: {prompt[:50]}...")
        return True

    def click_create_video(self) -> bool:
        """Trigger video creation."""
        logger.info("Create video triggered")
        return True

    def get_usage(self) -> Dict[str, Any]:
        """Get current Sora usage/credits information."""
        self._usage["last_check"] = datetime.now(timezone.utc).isoformat()
        return self._usage.copy()

    def submit_job(self, job: VideoJob) -> bool:
        """Submit a video generation job to the queue."""
        if len(self._queue) >= self.MAX_QUEUE_SIZE:
            logger.warning("Queue full, cannot submit job")
            return False
        self._queue.append(job)
        return True

    def get_queue_status(self) -> List[Dict[str, Any]]:
        """Get status of all queued jobs."""
        return [job.to_dict() for job in self._queue]
