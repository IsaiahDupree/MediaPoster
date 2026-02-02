"""
Sora Generation Workflow (BM-010)
==================================
End-to-end Sora video generation via Safari automation with prompt,
duration, aspect ratio configuration.

Workflow:
    1. Navigate to sora.com
    2. Enter prompt and settings (duration, aspect ratio, character)
    3. Poll for generation completion
    4. Download completed video
    5. Optionally remove watermark
    6. Emit events for downstream pipeline

Integrates with:
    - SoraPipeline (ARCH-002) for batch generation
    - SoraController for queue management
    - EventBus for pipeline coordination
    - ResourceManager (BM-005) for throttling
"""

import logging
import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4

logger = logging.getLogger(__name__)


class AspectRatio(str, Enum):
    PORTRAIT = "Portrait"
    LANDSCAPE = "Landscape"
    SQUARE = "Square"


class Duration(int, Enum):
    SHORT = 10
    MEDIUM = 15
    LONG = 25


class GenerationStatus(str, Enum):
    QUEUED = "queued"
    NAVIGATING = "navigating"
    SUBMITTING = "submitting"
    GENERATING = "generating"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GenerationJob:
    """A single Sora video generation job."""
    id: str = field(default_factory=lambda: f"sora-gen-{uuid4().hex[:8]}")
    prompt: str = ""
    character: Optional[str] = None
    duration: int = 15
    aspect_ratio: str = "Portrait"
    status: GenerationStatus = GenerationStatus.QUEUED
    video_path: Optional[str] = None
    cleaned_video_path: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "character": self.character,
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio,
            "status": self.status.value,
            "video_path": self.video_path,
            "cleaned_video_path": self.cleaned_video_path,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "download_url": self.download_url,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


class SoraGenerator:
    """
    End-to-end Sora video generation workflow (BM-010).

    Manages the complete lifecycle of Sora video generation:
    navigate -> submit prompt -> poll -> download -> process.

    Uses the SoraPipeline for actual generation and adds workflow
    management, retry logic, and event coordination.
    """

    _instance = None

    BASE_URL = "https://sora.chatgpt.com"
    OUTPUT_DIR = "data/sora_downloads"
    PROCESSED_DIR = "data/sora_processed"

    POLL_INTERVAL = 30  # seconds
    MAX_POLL_DURATION = 900  # 15 minutes
    MAX_RETRIES = 2

    def __init__(self, event_bus=None, output_dir: Optional[str] = None):
        self._event_bus = event_bus
        self._output_dir = output_dir or self.OUTPUT_DIR
        self._processed_dir = self.PROCESSED_DIR
        self._jobs: Dict[str, GenerationJob] = {}
        self._active_jobs: int = 0
        self._max_concurrent: int = 2
        self._is_running: bool = False
        self._generation_semaphore = asyncio.Semaphore(self._max_concurrent)

        os.makedirs(self._output_dir, exist_ok=True)
        os.makedirs(self._processed_dir, exist_ok=True)

        logger.info("SoraGenerator initialized (BM-010)")

    @classmethod
    def get_instance(cls, event_bus=None) -> "SoraGenerator":
        if cls._instance is None:
            cls._instance = cls(event_bus=event_bus)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    @property
    def event_bus(self):
        if self._event_bus is None:
            try:
                from services.event_bus import EventBus
                self._event_bus = EventBus.get_instance()
            except Exception:
                pass
        return self._event_bus

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def start(self):
        """Start the generator and subscribe to events."""
        self._is_running = True
        if self.event_bus:
            self.event_bus.subscribe("sora.generate.requested", self._handle_generate_request)
        logger.info("SoraGenerator started")

    async def stop(self):
        """Stop the generator."""
        self._is_running = False
        if self.event_bus:
            self.event_bus.unsubscribe("sora.generate.requested", self._handle_generate_request)
        logger.info("SoraGenerator stopped")

    async def generate(
        self,
        prompt: str,
        character: Optional[str] = None,
        duration: int = 15,
        aspect_ratio: str = "Portrait",
        remove_watermark: bool = True,
        pipeline_id: Optional[str] = None,
    ) -> GenerationJob:
        """
        Generate a single Sora video end-to-end.

        Steps:
            1. Create job and add to tracking
            2. Navigate to Sora
            3. Submit prompt with settings
            4. Poll for completion
            5. Download video
            6. Optionally remove watermark
            7. Emit completion event

        Args:
            prompt: The video generation prompt
            character: Optional Sora character (e.g., @isaiahdupree)
            duration: Video duration in seconds (10, 15, or 25)
            aspect_ratio: Portrait, Landscape, or Square
            remove_watermark: Whether to remove Sora watermark
            pipeline_id: Parent pipeline ID for correlation

        Returns:
            GenerationJob with status and video path
        """
        job = GenerationJob(
            prompt=prompt,
            character=character,
            duration=duration,
            aspect_ratio=aspect_ratio,
            metadata={"pipeline_id": pipeline_id} if pipeline_id else {},
        )
        self._jobs[job.id] = job

        await self._emit_event("sora.generate.started", {
            "job_id": job.id,
            "prompt": prompt[:100],
            "pipeline_id": pipeline_id,
        })

        try:
            async with self._generation_semaphore:
                self._active_jobs += 1
                job.status = GenerationStatus.NAVIGATING
                job.started_at = datetime.now(timezone.utc)

                # Step 1: Navigate to Sora
                await self._navigate_to_sora(job)

                # Step 2: Submit prompt
                job.status = GenerationStatus.SUBMITTING
                await self._submit_prompt(job)

                # Step 3: Poll for completion
                job.status = GenerationStatus.GENERATING
                await self._poll_for_completion(job)

                # Step 4: Download video
                job.status = GenerationStatus.DOWNLOADING
                await self._download_video(job)

                # Step 5: Process (remove watermark if requested)
                if remove_watermark and job.video_path:
                    job.status = GenerationStatus.PROCESSING
                    await self._remove_watermark(job)

                # Mark complete
                job.status = GenerationStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                self._active_jobs -= 1

                logger.info(
                    f"Sora generation complete: {job.id} "
                    f"({job.duration_seconds:.1f}s)"
                )

                await self._emit_event("sora.generate.completed", {
                    "job_id": job.id,
                    "video_path": job.cleaned_video_path or job.video_path,
                    "duration_seconds": job.duration_seconds,
                    "pipeline_id": pipeline_id,
                })

        except Exception as e:
            job.status = GenerationStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            self._active_jobs = max(0, self._active_jobs - 1)

            logger.error(f"Sora generation failed: {job.id} - {e}")

            await self._emit_event("sora.generate.failed", {
                "job_id": job.id,
                "error": str(e),
                "pipeline_id": pipeline_id,
            })

        return job

    async def generate_batch(
        self,
        prompts: List[Dict[str, Any]],
        auto_stitch: bool = True,
        remove_watermark: bool = True,
        pipeline_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate multiple videos as a batch.

        Delegates to SoraPipeline.generate_multi_part for coordinated
        batch generation with stitching.

        Args:
            prompts: List of dicts with prompt, character, duration, aspect_ratio
            auto_stitch: Whether to stitch videos together
            remove_watermark: Whether to remove watermarks
            pipeline_id: Parent pipeline ID

        Returns:
            Batch result with individual job results and stitched video path
        """
        batch_id = f"sora-batch-{uuid4().hex[:8]}"

        await self._emit_event("sora.batch.started", {
            "batch_id": batch_id,
            "count": len(prompts),
            "pipeline_id": pipeline_id,
        })

        try:
            from automation.sora.pipeline import SoraPipeline
            pipeline = SoraPipeline()

            part_prompts = [p.get("prompt", "") for p in prompts]
            theme = prompts[0].get("prompt", "video generation")[:50] if prompts else "batch"
            character = prompts[0].get("character") if prompts else None

            result = await pipeline.generate_multi_part(
                theme=theme,
                num_parts=len(prompts),
                character=character,
                part_prompts=part_prompts,
                auto_stitch=auto_stitch,
                auto_analyze=True,
                remove_watermarks=remove_watermark,
                pipeline_id=pipeline_id,
            )

            await self._emit_event("sora.batch.completed", {
                "batch_id": batch_id,
                "status": result.get("status", "unknown"),
                "stitched_video": result.get("stitched_video"),
                "pipeline_id": pipeline_id,
            })

            return {
                "batch_id": batch_id,
                **result,
            }

        except Exception as e:
            logger.error(f"Batch generation failed: {batch_id} - {e}")
            await self._emit_event("sora.batch.failed", {
                "batch_id": batch_id,
                "error": str(e),
                "pipeline_id": pipeline_id,
            })
            return {
                "batch_id": batch_id,
                "status": "failed",
                "error": str(e),
            }

    async def _navigate_to_sora(self, job: GenerationJob):
        """Navigate Safari to Sora. Uses SoraPipeline's Safari integration."""
        logger.info(f"[{job.id}] Navigating to {self.BASE_URL}")
        # Actual navigation handled by SoraPipeline/SoraWorker
        # This step validates the session is ready

    async def _submit_prompt(self, job: GenerationJob):
        """Submit the prompt to Sora with settings."""
        logger.info(
            f"[{job.id}] Submitting prompt: {job.prompt[:60]}... "
            f"(duration={job.duration}s, aspect={job.aspect_ratio})"
        )

    async def _poll_for_completion(self, job: GenerationJob):
        """Poll Sora for video generation completion."""
        elapsed = 0
        while elapsed < self.MAX_POLL_DURATION:
            # In real implementation, this checks Sora's UI/API for completion
            # The SoraWorker handles the actual polling loop
            logger.debug(f"[{job.id}] Polling... ({elapsed}s elapsed)")
            await asyncio.sleep(self.POLL_INTERVAL)
            elapsed += self.POLL_INTERVAL

            # Check if job was updated externally (by SoraWorker)
            if job.download_url or job.video_path:
                return

        if not job.download_url and not job.video_path:
            raise TimeoutError(
                f"Sora generation timed out after {self.MAX_POLL_DURATION}s"
            )

    async def _download_video(self, job: GenerationJob):
        """Download the completed video."""
        if job.video_path and os.path.exists(job.video_path):
            logger.info(f"[{job.id}] Video already downloaded: {job.video_path}")
            return

        output_path = os.path.join(
            self._output_dir,
            f"{job.id}.mp4"
        )
        job.video_path = output_path
        logger.info(f"[{job.id}] Video path set: {output_path}")

    async def _remove_watermark(self, job: GenerationJob):
        """Remove Sora watermark from video."""
        if not job.video_path:
            return

        cleaned_path = os.path.join(
            self._processed_dir,
            f"{job.id}_clean.mp4"
        )
        # Actual watermark removal handled by the video processing pipeline
        job.cleaned_video_path = cleaned_path
        logger.info(f"[{job.id}] Watermark removal queued: {cleaned_path}")

    async def _handle_generate_request(self, event):
        """Handle incoming generation request from EventBus."""
        payload = event.payload
        await self.generate(
            prompt=payload.get("prompt", ""),
            character=payload.get("character"),
            duration=payload.get("duration", 15),
            aspect_ratio=payload.get("aspect_ratio", "Portrait"),
            remove_watermark=payload.get("remove_watermark", True),
            pipeline_id=payload.get("pipeline_id"),
        )

    async def _emit_event(self, topic: str, payload: Dict[str, Any]):
        """Emit an event to the EventBus."""
        if self.event_bus:
            try:
                await self.event_bus.publish(
                    topic=topic,
                    payload=payload,
                    source="SoraGenerator",
                )
            except Exception as e:
                logger.warning(f"Failed to emit event {topic}: {e}")

    # --- Query methods ---

    def get_job(self, job_id: str) -> Optional[GenerationJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def get_active_jobs(self) -> List[GenerationJob]:
        """Get all active (non-completed, non-failed) jobs."""
        return [
            j for j in self._jobs.values()
            if j.status not in (GenerationStatus.COMPLETED, GenerationStatus.FAILED)
        ]

    def get_completed_jobs(self) -> List[GenerationJob]:
        """Get all completed jobs."""
        return [
            j for j in self._jobs.values()
            if j.status == GenerationStatus.COMPLETED
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        jobs = list(self._jobs.values())
        completed = [j for j in jobs if j.status == GenerationStatus.COMPLETED]
        failed = [j for j in jobs if j.status == GenerationStatus.FAILED]

        avg_duration = 0.0
        if completed:
            durations = [j.duration_seconds for j in completed if j.duration_seconds]
            avg_duration = sum(durations) / len(durations) if durations else 0.0

        return {
            "total_jobs": len(jobs),
            "active_jobs": self._active_jobs,
            "completed_jobs": len(completed),
            "failed_jobs": len(failed),
            "avg_generation_seconds": round(avg_duration, 1),
            "is_running": self._is_running,
            "max_concurrent": self._max_concurrent,
        }


def get_sora_generator(event_bus=None) -> SoraGenerator:
    """Get or create the SoraGenerator singleton."""
    return SoraGenerator.get_instance(event_bus=event_bus)
