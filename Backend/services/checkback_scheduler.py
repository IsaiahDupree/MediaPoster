"""
Background Job Scheduler for Content Intelligence
Handles automated checkback metrics collection and comment analysis
"""
import logging
from datetime import datetime, timedelta
from typing import List, Callable, Dict, Any
from dataclasses import dataclass
import uuid
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class ScheduledCheckback:
    """Scheduled checkback job"""
    post_id: uuid.UUID
    checkback_hours: int
    scheduled_time: datetime
    job_id: str


class CheckbackScheduler:
    """
    Schedules and manages automated checkback jobs
    
    Uses APScheduler for background job management
    In production, consider using Celery for distributed task processing
    """
    
    def __init__(self):
        """Initialize scheduler"""
        self.scheduler = BackgroundScheduler(
            jobstores={'default': MemoryJobStore()},
            timezone='UTC'
        )
        self.scheduled_jobs: Dict[str, ScheduledCheckback] = {}
        logger.info("CheckbackScheduler initialized")
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("CheckbackScheduler started")
    
    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("CheckbackScheduler shutdown")
    
    def schedule_checkback(
        self,
        post_id: uuid.UUID,
        published_at: datetime,
        checkback_hours: int,
        callback: Callable[[uuid.UUID, int], None]
    ) -> str:
        """
        Schedule a checkback job
        
        Args:
            post_id: Platform post ID
            published_at: When the post was published
            checkback_hours: Hours after publishing to collect metrics
            callback: Function to call (should accept post_id and checkback_hours)
            
        Returns:
            Job ID
        """
        # Calculate when to run
        scheduled_time = published_at + timedelta(hours=checkback_hours)
        
        # Don't schedule if in the past
        if scheduled_time < datetime.now():
            logger.warning(f"Checkback time {scheduled_time} is in the past, skipping")
            return None
        
        # Create job ID
        job_id = f"checkback_{post_id}_{checkback_hours}h"
        
        # Schedule the job
        try:
            job = self.scheduler.add_job(
                func=callback,
                trigger=DateTrigger(run_date=scheduled_time),
                args=[post_id, checkback_hours],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=3600  # Allow 1 hour grace period
            )
            
            # Track scheduled job
            self.scheduled_jobs[job_id] = ScheduledCheckback(
                post_id=post_id,
                checkback_hours=checkback_hours,
                scheduled_time=scheduled_time,
                job_id=job_id
            )
            
            logger.info(f"Scheduled checkback: {job_id} at {scheduled_time}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error scheduling checkback: {e}")
            return None
    
    def schedule_standard_checkbacks(
        self,
        post_id: uuid.UUID,
        published_at: datetime,
        callback: Callable,
        checkback_hours: List[int] = [1, 6, 24, 72, 168]
    ) -> List[str]:
        """
        Schedule standard set of checkbacks
        
        Args:
            post_id: Platform post ID
            published_at: When post was published
            callback: Callback function
            checkback_hours: List of hours (default: 1, 6, 24, 72, 168)
            
        Returns:
            List of job IDs
        """
        job_ids = []
        
        for hours in checkback_hours:
            job_id = self.schedule_checkback(
                post_id=post_id,
                published_at=published_at,
                checkback_hours=hours,
                callback=callback
            )
            
            if job_id:
                job_ids.append(job_id)
        
        logger.info(f"Scheduled {len(job_ids)} checkbacks for post {post_id}")
        return job_ids
    
    def cancel_checkback(self, job_id: str) -> bool:
        """
        Cancel a scheduled checkback
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if cancelled
        """
        try:
            self.scheduler.remove_job(job_id)
            
            if job_id in self.scheduled_jobs:
                del self.scheduled_jobs[job_id]
            
            logger.info(f"Cancelled checkback: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling checkback {job_id}: {e}")
            return False
    
    def cancel_all_for_post(self, post_id: uuid.UUID) -> int:
        """
        Cancel all checkbacks for a post
        
        Args:
            post_id: Post ID
            
        Returns:
            Number of jobs cancelled
        """
        cancelled = 0
        
        # Find all jobs for this post
        jobs_to_cancel = [
            job_id for job_id, checkback in self.scheduled_jobs.items()
            if checkback.post_id == post_id
        ]
        
        for job_id in jobs_to_cancel:
            if self.cancel_checkback(job_id):
                cancelled += 1
        
        return cancelled
    
    def get_scheduled_checkbacks(self, post_id: Optional[uuid.UUID] = None) -> List[ScheduledCheckback]:
        """
        Get list of scheduled checkbacks
        
        Args:
            post_id: Optional post ID to filter by
            
        Returns:
            List of scheduled checkbacks
        """
        if post_id:
            return [
                checkback for checkback in self.scheduled_jobs.values()
                if checkback.post_id == post_id
            ]
        
        return list(self.scheduled_jobs.values())
    
    def get_next_checkback_time(self, post_id: uuid.UUID) -> Optional[datetime]:
        """
        Get the next scheduled checkback time for a post
        
        Args:
            post_id: Post ID
            
        Returns:
            Next scheduled time or None
        """
        checkbacks = self.get_scheduled_checkbacks(post_id)
        
        if not checkbacks:
            return None
        
        # Sort by scheduled time
        checkbacks.sort(key=lambda x: x.scheduled_time)
        
        # Return first future checkback
        now = datetime.now()
        for checkback in checkbacks:
            if checkback.scheduled_time > now:
                return checkback.scheduled_time
        
        return None


# Global scheduler instance
_scheduler: Optional[CheckbackScheduler] = None


def get_scheduler() -> CheckbackScheduler:
    """Get or create global scheduler instance"""
    global _scheduler
    
    if _scheduler is None:
        _scheduler = CheckbackScheduler()
        _scheduler.start()
    
    return _scheduler


def shutdown_scheduler():
    """Shutdown global scheduler"""
    global _scheduler
    
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
