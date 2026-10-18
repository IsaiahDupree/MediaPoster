"""
Analysis Scheduler API Endpoints
Control and monitor the nightly analysis scheduler
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger

from services.nightly_analysis_scheduler import (
    get_scheduler,
    SchedulerConfig,
    NightlyAnalysisScheduler
)

router = APIRouter(prefix="/api/scheduler", tags=["Analysis Scheduler"])


class SchedulerConfigRequest(BaseModel):
    """Configuration for the scheduler"""
    batch_size: int = Field(default=30, ge=1, le=100)
    interval_hours: float = Field(default=2.0, ge=0.1, le=24)
    max_total_videos: Optional[int] = Field(default=None, ge=1)
    max_runs: Optional[int] = Field(default=None, ge=1)
    start_hour: int = Field(default=0, ge=0, le=23)
    end_hour: int = Field(default=24, ge=1, le=24)


@router.get("/status")
async def get_scheduler_status():
    """Get current scheduler status and recent job history"""
    scheduler = get_scheduler()
    return scheduler.get_status()


@router.post("/start")
async def start_scheduler(
    config: Optional[SchedulerConfigRequest] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Start the nightly analysis scheduler.
    
    Default: 30 videos every 2 hours, runs 24/7
    """
    scheduler = get_scheduler()
    
    if scheduler.is_running:
        return {
            "message": "Scheduler already running",
            "status": scheduler.get_status()
        }
    
    # Update config if provided
    if config:
        scheduler.config = SchedulerConfig(
            batch_size=config.batch_size,
            interval_hours=config.interval_hours,
            max_total_videos=config.max_total_videos,
            max_runs=config.max_runs,
            start_hour=config.start_hour,
            end_hour=config.end_hour,
            enabled=True
        )
    
    # Start in background
    background_tasks.add_task(scheduler.start)
    
    logger.info("📅 Scheduler start requested")
    
    return {
        "message": "Scheduler starting",
        "config": scheduler.config.to_dict()
    }


@router.post("/stop")
async def stop_scheduler():
    """Stop the scheduler gracefully"""
    scheduler = get_scheduler()
    
    if not scheduler.is_running:
        return {"message": "Scheduler not running"}
    
    await scheduler.stop()
    
    return {
        "message": "Scheduler stopped",
        "final_status": scheduler.get_status()
    }


@router.post("/run-batch")
async def run_single_batch():
    """
    Run a single batch of analysis immediately.
    Useful for testing or manual runs.
    """
    scheduler = get_scheduler()
    
    logger.info("📊 Manual batch run requested")
    report = await scheduler.run_single_batch()
    
    return {
        "message": "Batch completed",
        "report": report.to_dict()
    }


@router.get("/history")
async def get_job_history(limit: int = 20):
    """Get recent job history"""
    scheduler = get_scheduler()
    
    return {
        "total_jobs": len(scheduler.job_history),
        "total_videos_analyzed": scheduler.total_videos_analyzed,
        "jobs": [j.to_dict() for j in scheduler.job_history[-limit:]]
    }


@router.get("/config")
async def get_scheduler_config():
    """Get current scheduler configuration"""
    scheduler = get_scheduler()
    return scheduler.config.to_dict()


@router.put("/config")
async def update_scheduler_config(config: SchedulerConfigRequest):
    """Update scheduler configuration (takes effect on next run)"""
    scheduler = get_scheduler()
    
    scheduler.config = SchedulerConfig(
        batch_size=config.batch_size,
        interval_hours=config.interval_hours,
        max_total_videos=config.max_total_videos,
        max_runs=config.max_runs,
        start_hour=config.start_hour,
        end_hour=config.end_hour,
        enabled=True
    )
    
    logger.info(f"📅 Scheduler config updated: {scheduler.config.to_dict()}")
    
    return {
        "message": "Configuration updated",
        "config": scheduler.config.to_dict()
    }
