"""
Nightly Analysis Scheduler
==========================
Runs automated analysis jobs on a schedule with detailed logging and health reports.

Configuration:
- 30 videos per batch
- Every 2 hours
- Continues until target count or all videos analyzed
- Detailed progress logging
- Health reports during runs
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import json
from pathlib import Path


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class AnalysisJobReport:
    """Report for a single analysis job run"""
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    videos_processed: int = 0
    videos_succeeded: int = 0
    videos_failed: int = 0
    videos_skipped: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "videos_processed": self.videos_processed,
            "videos_succeeded": self.videos_succeeded,
            "videos_failed": self.videos_failed,
            "videos_skipped": self.videos_skipped,
            "errors": self.errors[:10],  # Limit errors in report
            "duration_seconds": self.duration_seconds
        }


@dataclass
class SchedulerConfig:
    """Configuration for the analysis scheduler"""
    batch_size: int = 30
    interval_hours: float = 2.0
    max_total_videos: Optional[int] = None  # None = unlimited
    max_runs: Optional[int] = None  # None = unlimited
    start_hour: int = 0  # 24-hour format, 0 = midnight
    end_hour: int = 24  # 24-hour format, 24 = run all day
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_size": self.batch_size,
            "interval_hours": self.interval_hours,
            "max_total_videos": self.max_total_videos,
            "max_runs": self.max_runs,
            "start_hour": self.start_hour,
            "end_hour": self.end_hour,
            "enabled": self.enabled
        }


class NightlyAnalysisScheduler:
    """
    Manages scheduled analysis jobs with comprehensive logging and health monitoring.
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        self.is_running = False
        self.current_job: Optional[AnalysisJobReport] = None
        self.job_history: List[AnalysisJobReport] = []
        self.total_videos_analyzed = 0
        self.runs_completed = 0
        self.started_at: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
        # Report file for persistence
        self.report_dir = Path("/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/data/analysis_reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("📅 Nightly Analysis Scheduler initialized")
        logger.info(f"   Batch size: {self.config.batch_size}")
        logger.info(f"   Interval: {self.config.interval_hours} hours")
    
    async def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        self.is_running = True
        self.started_at = datetime.now()
        self._stop_event.clear()
        
        logger.info("🚀 Starting Nightly Analysis Scheduler")
        self._log_status("STARTED")
        
        self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self):
        """Stop the scheduler gracefully"""
        if not self.is_running:
            return
        
        logger.info("🛑 Stopping Nightly Analysis Scheduler...")
        self._stop_event.set()
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self._log_status("STOPPED")
        self._save_report()
    
    async def run_single_batch(self) -> AnalysisJobReport:
        """Run a single batch of analysis jobs"""
        job_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report = AnalysisJobReport(
            job_id=job_id,
            started_at=datetime.now(),
            status=JobStatus.RUNNING
        )
        self.current_job = report
        
        logger.info(f"📊 Starting analysis batch: {job_id}")
        logger.info(f"   Target: {self.config.batch_size} videos")
        
        try:
            # Get videos needing analysis
            videos = await self._get_videos_for_analysis(self.config.batch_size)
            
            if not videos:
                logger.info("✅ No videos need analysis - all complete!")
                report.status = JobStatus.COMPLETED
                report.completed_at = datetime.now()
                return report
            
            logger.info(f"   Found {len(videos)} videos to analyze")
            
            # Process each video
            for i, video in enumerate(videos, 1):
                if self._stop_event.is_set():
                    logger.warning("Batch interrupted by stop signal")
                    break
                
                try:
                    logger.info(f"   [{i}/{len(videos)}] Analyzing: {video.get('filename', 'unknown')}")
                    
                    success = await self._analyze_video(video)
                    
                    if success:
                        report.videos_succeeded += 1
                        logger.info(f"   ✓ Completed: {video.get('filename', 'unknown')}")
                    else:
                        report.videos_skipped += 1
                        logger.warning(f"   ⚠ Skipped: {video.get('filename', 'unknown')}")
                    
                    report.videos_processed += 1
                    
                except Exception as e:
                    report.videos_failed += 1
                    report.errors.append({
                        "video_id": video.get("id"),
                        "filename": video.get("filename"),
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.error(f"   ✗ Failed: {video.get('filename', 'unknown')} - {e}")
            
            report.status = JobStatus.COMPLETED
            
        except Exception as e:
            report.status = JobStatus.FAILED
            report.errors.append({
                "type": "batch_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            logger.error(f"❌ Batch failed: {e}")
        
        report.completed_at = datetime.now()
        report.duration_seconds = (report.completed_at - report.started_at).total_seconds()
        
        self.job_history.append(report)
        self.total_videos_analyzed += report.videos_succeeded
        self.runs_completed += 1
        
        self._log_batch_summary(report)
        self._save_report()
        
        return report
    
    async def _run_loop(self):
        """Main scheduler loop"""
        while self.is_running and not self._stop_event.is_set():
            # Check if within operating hours
            current_hour = datetime.now().hour
            if not (self.config.start_hour <= current_hour < self.config.end_hour):
                logger.info(f"⏰ Outside operating hours ({self.config.start_hour}-{self.config.end_hour}), sleeping...")
                await asyncio.sleep(300)  # Check again in 5 minutes
                continue
            
            # Check max runs
            if self.config.max_runs and self.runs_completed >= self.config.max_runs:
                logger.info(f"🏁 Reached max runs ({self.config.max_runs}), stopping scheduler")
                break
            
            # Check max videos
            if self.config.max_total_videos and self.total_videos_analyzed >= self.config.max_total_videos:
                logger.info(f"🏁 Reached max videos ({self.config.max_total_videos}), stopping scheduler")
                break
            
            # Run a batch
            await self.run_single_batch()
            
            # Wait for next interval
            if self.is_running and not self._stop_event.is_set():
                wait_seconds = self.config.interval_hours * 3600
                logger.info(f"⏳ Next batch in {self.config.interval_hours} hours...")
                
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=wait_seconds
                    )
                except asyncio.TimeoutError:
                    pass  # Normal timeout, continue to next batch
        
        self.is_running = False
        logger.info("📅 Scheduler loop ended")
    
    async def _get_videos_for_analysis(self, limit: int) -> List[Dict]:
        """Get videos that need analysis"""
        try:
            from database.connection import get_db
            from sqlalchemy import text
            
            async for db in get_db():
                # Get videos without complete analysis
                # Filter by video file extensions since media_type column doesn't exist
                query = text("""
                    SELECT v.id, v.file_name, v.source_uri, v.source_type
                    FROM videos v
                    LEFT JOIN video_analysis va ON v.id = va.video_id
                    WHERE (LOWER(v.file_name) LIKE '%.mp4'
                           OR LOWER(v.file_name) LIKE '%.mov'
                           OR LOWER(v.file_name) LIKE '%.m4v'
                           OR LOWER(v.file_name) LIKE '%.avi'
                           OR LOWER(v.file_name) LIKE '%.mkv'
                           OR LOWER(v.file_name) LIKE '%.webm')
                      AND (va.video_id IS NULL 
                           OR va.transcript IS NULL 
                           OR va.pre_social_score IS NULL)
                    ORDER BY v.created_at DESC
                    LIMIT :limit
                """)
                result = await db.execute(query, {"limit": limit})
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(row[0]),
                        "filename": row[1],
                        "source_uri": row[2],
                        "source_type": row[3]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error fetching videos for analysis: {e}")
            return []
    
    async def _analyze_video(self, video: Dict) -> bool:
        """Analyze a single video - calls the analysis service"""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    "http://localhost:5555/api/media-db/analyze",
                    json={"video_id": video["id"]}
                )
                
                if response.status_code == 200:
                    return True
                else:
                    logger.warning(f"Analysis returned {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Analysis error for {video['filename']}: {e}")
            raise
    
    def _log_status(self, event: str):
        """Log scheduler status"""
        status = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "total_analyzed": self.total_videos_analyzed,
            "runs_completed": self.runs_completed,
            "config": self.config.to_dict()
        }
        logger.info(f"📅 SCHEDULER {event}: {json.dumps(status, indent=2)}")
    
    def _log_batch_summary(self, report: AnalysisJobReport):
        """Log batch completion summary"""
        logger.info("=" * 60)
        logger.info(f"📊 BATCH COMPLETE: {report.job_id}")
        logger.info(f"   Status: {report.status.value}")
        logger.info(f"   Duration: {report.duration_seconds:.1f}s")
        logger.info(f"   Processed: {report.videos_processed}")
        logger.info(f"   Succeeded: {report.videos_succeeded}")
        logger.info(f"   Failed: {report.videos_failed}")
        logger.info(f"   Skipped: {report.videos_skipped}")
        logger.info(f"   Total analyzed (all batches): {self.total_videos_analyzed}")
        logger.info("=" * 60)
    
    def _save_report(self):
        """Save current state to report file"""
        report = {
            "scheduler_started": self.started_at.isoformat() if self.started_at else None,
            "is_running": self.is_running,
            "total_videos_analyzed": self.total_videos_analyzed,
            "runs_completed": self.runs_completed,
            "config": self.config.to_dict(),
            "job_history": [j.to_dict() for j in self.job_history[-20:]],  # Last 20 jobs
            "last_updated": datetime.now().isoformat()
        }
        
        report_file = self.report_dir / "scheduler_status.json"
        report_file.write_text(json.dumps(report, indent=2))
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            "is_running": self.is_running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "total_videos_analyzed": self.total_videos_analyzed,
            "runs_completed": self.runs_completed,
            "current_job": self.current_job.to_dict() if self.current_job else None,
            "recent_jobs": [j.to_dict() for j in self.job_history[-5:]],
            "config": self.config.to_dict()
        }


# Singleton instance
_scheduler: Optional[NightlyAnalysisScheduler] = None


def get_scheduler(config: Optional[SchedulerConfig] = None) -> NightlyAnalysisScheduler:
    """Get the singleton scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = NightlyAnalysisScheduler(config)
    return _scheduler
