"""
Batch Video Processing Service
==============================
Handles batch processing of multiple videos for:
- Analysis
- Clip extraction
- Subtitle generation
- Scheduling
"""

import os
import logging
import asyncio
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field
from uuid import uuid4
from pathlib import Path
from enum import Enum

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


class BatchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingStage(str, Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    EXTRACTING_CLIPS = "extracting_clips"
    GENERATING_SUBTITLES = "generating_subtitles"
    CLASSIFYING = "classifying"
    SCHEDULING = "scheduling"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class VideoJob:
    """A single video processing job."""
    id: str = field(default_factory=lambda: str(uuid4()))
    video_path: str = ""
    video_id: Optional[str] = None
    status: BatchStatus = BatchStatus.PENDING
    stage: ProcessingStage = ProcessingStage.QUEUED
    progress: int = 0
    
    # Results
    analysis_id: Optional[str] = None
    clips_extracted: int = 0
    clips_with_subtitles: int = 0
    scheduled_posts: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Errors
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "video_path": self.video_path,
            "video_id": self.video_id,
            "status": self.status.value,
            "stage": self.stage.value,
            "progress": self.progress,
            "analysis_id": self.analysis_id,
            "clips_extracted": self.clips_extracted,
            "clips_with_subtitles": self.clips_with_subtitles,
            "scheduled_posts": self.scheduled_posts,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }


@dataclass
class BatchJob:
    """A batch processing job containing multiple videos."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    status: BatchStatus = BatchStatus.PENDING
    
    # Configuration
    extract_clips: bool = True
    add_subtitles: bool = True
    auto_schedule: bool = True
    max_clips_per_video: int = 5
    
    # Jobs
    video_jobs: List[VideoJob] = field(default_factory=list)
    
    # Progress
    total_videos: int = 0
    completed_videos: int = 0
    failed_videos: int = 0
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def progress(self) -> int:
        if self.total_videos == 0:
            return 0
        return int((self.completed_videos / self.total_videos) * 100)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "extract_clips": self.extract_clips,
            "add_subtitles": self.add_subtitles,
            "auto_schedule": self.auto_schedule,
            "total_videos": self.total_videos,
            "completed_videos": self.completed_videos,
            "failed_videos": self.failed_videos,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "video_jobs": [j.to_dict() for j in self.video_jobs]
        }


class BatchProcessor:
    """
    Processes multiple videos in batch.
    
    Supports:
    - Parallel processing with configurable concurrency
    - Progress tracking per video and overall
    - Error handling with continuation
    - Integration with clip extraction and scheduling
    """
    
    def __init__(
        self,
        max_concurrent: int = 3,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ):
        self.max_concurrent = max_concurrent
        self.progress_callback = progress_callback
        self.engine = create_engine(DATABASE_URL)
        self._active_batches: Dict[str, BatchJob] = {}
        self._cancelled: set = set()
    
    async def create_batch(
        self,
        video_paths: List[str],
        name: str = "Batch Processing",
        extract_clips: bool = True,
        add_subtitles: bool = True,
        auto_schedule: bool = True,
        max_clips_per_video: int = 5
    ) -> BatchJob:
        """Create a new batch job from video paths."""
        batch = BatchJob(
            name=name,
            extract_clips=extract_clips,
            add_subtitles=add_subtitles,
            auto_schedule=auto_schedule,
            max_clips_per_video=max_clips_per_video
        )
        
        # Create video jobs
        for path in video_paths:
            if Path(path).exists():
                job = VideoJob(video_path=path)
                batch.video_jobs.append(job)
        
        batch.total_videos = len(batch.video_jobs)
        self._active_batches[batch.id] = batch
        
        logger.info(f"Created batch {batch.id} with {batch.total_videos} videos")
        
        return batch
    
    async def create_batch_from_database(
        self,
        name: str = "Database Batch",
        min_score: int = 60,
        limit: int = 20,
        unprocessed_only: bool = True,
        **kwargs
    ) -> BatchJob:
        """Create batch from videos in database."""
        video_paths = []
        
        with self.engine.connect() as conn:
            query = """
                SELECT v.source_uri, v.id FROM videos v
                JOIN video_analysis va ON va.video_id = v.id
                WHERE va.pre_social_score >= :min_score
                AND v.source_uri IS NOT NULL
            """
            
            if unprocessed_only:
                query += """
                    AND NOT EXISTS (
                        SELECT 1 FROM video_clips vc 
                        WHERE vc.source_video_id = v.id
                    )
                """
            
            query += " ORDER BY va.pre_social_score DESC LIMIT :limit"
            
            result = conn.execute(text(query), {"min_score": min_score, "limit": limit})
            
            for row in result:
                if row[0] and Path(row[0]).exists():
                    video_paths.append(row[0])
        
        return await self.create_batch(video_paths, name=name, **kwargs)
    
    async def run_batch(self, batch_id: str) -> BatchJob:
        """Run a batch job."""
        batch = self._active_batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")
        
        batch.status = BatchStatus.RUNNING
        batch.started_at = datetime.now()
        
        logger.info(f"Starting batch {batch_id} with {batch.total_videos} videos")
        
        # Process videos with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(job: VideoJob):
            async with semaphore:
                if batch_id in self._cancelled:
                    job.status = BatchStatus.CANCELLED
                    return
                await self._process_video(batch, job)
        
        # Run all jobs concurrently (limited by semaphore)
        await asyncio.gather(
            *[process_with_semaphore(job) for job in batch.video_jobs],
            return_exceptions=True
        )
        
        # Update batch status
        if batch_id in self._cancelled:
            batch.status = BatchStatus.CANCELLED
        elif batch.failed_videos == batch.total_videos:
            batch.status = BatchStatus.FAILED
        else:
            batch.status = BatchStatus.COMPLETED
        
        batch.completed_at = datetime.now()
        
        logger.info(
            f"Batch {batch_id} completed: "
            f"{batch.completed_videos}/{batch.total_videos} successful, "
            f"{batch.failed_videos} failed"
        )
        
        return batch
    
    async def _process_video(self, batch: BatchJob, job: VideoJob):
        """Process a single video in the batch."""
        job.status = BatchStatus.RUNNING
        job.started_at = datetime.now()
        
        try:
            # Stage 1: Get video info
            job.stage = ProcessingStage.ANALYZING
            job.progress = 10
            self._notify_progress(batch.id, job.progress, f"Analyzing {Path(job.video_path).name}")
            
            # Look up video in database
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT v.id, va.id, va.transcript, va.topics, v.duration_sec
                    FROM videos v
                    LEFT JOIN video_analysis va ON va.video_id = v.id
                    WHERE v.source_uri = :path
                """), {"path": job.video_path}).fetchone()
                
                if result:
                    job.video_id = str(result[0])
                    job.analysis_id = str(result[1]) if result[1] else None
                    transcript = result[2] or ""
                    topics = result[3] or []
                    duration = float(result[4]) if result[4] else 60.0
                else:
                    job.video_id = str(uuid4())
                    transcript = ""
                    topics = []
                    duration = 60.0
            
            # Stage 2: Extract clips
            if batch.extract_clips:
                job.stage = ProcessingStage.EXTRACTING_CLIPS
                job.progress = 30
                self._notify_progress(batch.id, job.progress, "Extracting clips")
                
                from services.clip_extraction import ClipExtractor, ExtractionConfig
                
                config = ExtractionConfig(
                    target_clips=batch.max_clips_per_video,
                    min_clip_duration=10,
                    max_clip_duration=60
                )
                
                extractor = ClipExtractor(config=config)
                
                output_dir = f"/tmp/batch_clips/{batch.id}/{job.id}"
                os.makedirs(output_dir, exist_ok=True)
                
                clips = await extractor.extract_clips_from_video(
                    video_id=job.video_id,
                    video_path=job.video_path,
                    transcript=transcript,
                    video_duration=duration,
                    output_dir=output_dir,
                    topics=topics if isinstance(topics, list) else []
                )
                
                job.clips_extracted = len([c for c in clips if c.status == "completed"])
                job.progress = 50
            
            # Stage 3: Add subtitles
            if batch.add_subtitles and job.clips_extracted > 0:
                job.stage = ProcessingStage.GENERATING_SUBTITLES
                job.progress = 60
                self._notify_progress(batch.id, job.progress, "Adding subtitles")
                
                from services.clip_extraction import SubtitleGenerator, SubtitleConfig
                
                subtitle_config = SubtitleConfig(
                    words_per_subtitle=3,
                    font_size=48
                )
                generator = SubtitleGenerator(config=subtitle_config)
                
                # Add subtitles to each extracted clip
                for clip in clips:
                    if clip.status == "completed" and clip.output_path:
                        try:
                            success, _ = await generator.add_subtitles_to_clip(
                                video_path=clip.output_path,
                                text=clip.segment.text if clip.segment else "",
                                start_time=clip.segment.start_time if clip.segment else 0,
                                end_time=clip.segment.end_time if clip.segment else 30
                            )
                            if success:
                                job.clips_with_subtitles += 1
                        except Exception as e:
                            logger.warning(f"Subtitle generation failed for clip: {e}")
                
                job.progress = 80
            
            # Stage 4: Classify and schedule
            if batch.auto_schedule and job.clips_extracted > 0:
                job.stage = ProcessingStage.SCHEDULING
                job.progress = 90
                self._notify_progress(batch.id, job.progress, "Scheduling clips")
                
                # Clips are automatically saved to database by extractor
                # Schedule them using clip integration
                from services.narrative_scheduler.clip_integration import ClipSchedulingIntegration
                
                integration = ClipSchedulingIntegration()
                result = await integration.auto_schedule_clips()
                job.scheduled_posts = result.get("clips_scheduled", 0)
            
            # Complete
            job.stage = ProcessingStage.COMPLETE
            job.progress = 100
            job.status = BatchStatus.COMPLETED
            job.completed_at = datetime.now()
            
            batch.completed_videos += 1
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            job.stage = ProcessingStage.ERROR
            job.status = BatchStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()
            
            batch.failed_videos += 1
    
    def _notify_progress(self, batch_id: str, progress: int, message: str):
        """Notify progress via callback."""
        if self.progress_callback:
            try:
                self.progress_callback(batch_id, progress, message)
            except Exception:
                pass
    
    def cancel_batch(self, batch_id: str):
        """Cancel a running batch."""
        self._cancelled.add(batch_id)
        batch = self._active_batches.get(batch_id)
        if batch:
            batch.status = BatchStatus.CANCELLED
    
    def get_batch(self, batch_id: str) -> Optional[BatchJob]:
        """Get batch status."""
        return self._active_batches.get(batch_id)
    
    def list_batches(self, limit: int = 20) -> List[BatchJob]:
        """List recent batches."""
        batches = list(self._active_batches.values())
        batches.sort(key=lambda b: b.created_at, reverse=True)
        return batches[:limit]
