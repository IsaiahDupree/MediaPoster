"""
API Endpoints for Daily Sora Automation
Manages automated daily video generation with @isaiahdupree character.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from loguru import logger

router = APIRouter(prefix="/sora-daily", tags=["Sora Daily Automation"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class StartDailyRunRequest(BaseModel):
    """Request to start daily run."""
    collect_trends: bool = Field(default=True, description="Collect trends before generating")


class RetryJobRequest(BaseModel):
    """Request to retry a failed job."""
    job_id: str = Field(..., description="Job ID to retry")


# =============================================================================
# STATUS ENDPOINTS
# =============================================================================

@router.get("/status")
async def get_daily_status():
    """Get today's generation status."""
    try:
        from services.sora_daily import get_daily_scheduler
        
        scheduler = get_daily_scheduler()
        status = scheduler.get_daily_status()
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get daily status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan")
async def get_today_plan():
    """Get today's generation plan details."""
    try:
        from services.sora_daily import get_daily_scheduler
        
        scheduler = get_daily_scheduler()
        plan = scheduler.get_or_create_today_plan()
        
        return plan.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to get plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RUN CONTROL ENDPOINTS
# =============================================================================

@router.post("/start")
async def start_daily_run(
    request: StartDailyRunRequest,
    background_tasks: BackgroundTasks
):
    """Start the daily Sora generation run."""
    try:
        from services.sora_daily import get_daily_scheduler, get_trend_collector
        
        scheduler = get_daily_scheduler()
        
        # Start the run
        result = await scheduler.start_daily_run()
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        # Collect trends and generate jobs in background
        if request.collect_trends:
            background_tasks.add_task(
                _generate_jobs_with_trends,
                scheduler
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start daily run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_jobs_with_trends(scheduler):
    """Background task to generate jobs with trends."""
    try:
        from services.sora_daily import get_trend_collector
        
        collector = get_trend_collector()
        
        # Collect trends
        trends = await collector.collect_all()
        trend_topics = [t.topic for t in trends[:20]]
        
        # Generate jobs
        await scheduler.generate_daily_jobs(trends=trend_topics)
        
    except Exception as e:
        logger.error(f"Background job generation failed: {e}")


@router.post("/pause")
async def pause_daily_run():
    """Pause the daily run."""
    try:
        from services.sora_daily import get_daily_scheduler
        
        scheduler = get_daily_scheduler()
        scheduler.is_running = False
        
        if scheduler.current_plan:
            scheduler.update_plan_status(scheduler.current_plan.id, "paused")
        
        return {"success": True, "message": "Daily run paused"}
        
    except Exception as e:
        logger.error(f"Failed to pause: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
async def resume_daily_run():
    """Resume a paused daily run."""
    try:
        from services.sora_daily import get_daily_scheduler
        
        scheduler = get_daily_scheduler()
        scheduler.is_running = True
        
        if scheduler.current_plan:
            scheduler.update_plan_status(scheduler.current_plan.id, "in_progress")
        
        return {"success": True, "message": "Daily run resumed"}
        
    except Exception as e:
        logger.error(f"Failed to resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# JOB ENDPOINTS
# =============================================================================

@router.get("/jobs")
async def get_jobs(limit: int = 50):
    """Get all jobs for today."""
    try:
        from services.sora_daily import get_daily_scheduler
        
        scheduler = get_daily_scheduler()
        plan = scheduler.get_or_create_today_plan()
        jobs = scheduler.get_jobs_for_plan(plan.id)
        
        return {
            "jobs": [j.to_dict() for j in jobs[:limit]],
            "count": len(jobs)
        }
        
    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/pending")
async def get_pending_jobs(limit: int = 20):
    """Get pending jobs ready for processing."""
    try:
        from services.sora_daily import get_daily_scheduler
        
        scheduler = get_daily_scheduler()
        jobs = scheduler.get_pending_jobs(limit=limit)
        
        return {
            "jobs": [j.to_dict() for j in jobs],
            "count": len(jobs)
        }
        
    except Exception as e:
        logger.error(f"Failed to get pending jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str, background_tasks: BackgroundTasks):
    """Retry a failed job."""
    try:
        from services.sora_daily import get_daily_scheduler, JobStatus
        
        scheduler = get_daily_scheduler()
        scheduler.update_job_status(job_id, JobStatus.PENDING.value)
        
        return {"success": True, "job_id": job_id, "status": "pending"}
        
    except Exception as e:
        logger.error(f"Failed to retry job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TREND ENDPOINTS
# =============================================================================

@router.get("/trends")
async def get_trends(limit: int = 20, unused_only: bool = True):
    """Get collected trends."""
    try:
        from services.sora_daily import get_trend_collector
        
        collector = get_trend_collector()
        
        if unused_only:
            trends = collector.get_unused_trends(limit=limit)
        else:
            # Get all recent trends
            trends = collector.get_unused_trends(limit=limit * 2)
        
        return {
            "trends": [t.to_dict() for t in trends],
            "count": len(trends)
        }
        
    except Exception as e:
        logger.error(f"Failed to get trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trends/collect")
async def collect_trends():
    """Manually trigger trend collection."""
    try:
        from services.sora_daily import get_trend_collector
        
        collector = get_trend_collector()
        trends = await collector.collect_all()
        
        return {
            "success": True,
            "trends_collected": len(trends),
            "trends": [t.to_dict() for t in trends[:10]]
        }
        
    except Exception as e:
        logger.error(f"Failed to collect trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WATERMARK ENDPOINTS
# =============================================================================

@router.post("/watermark/remove")
async def remove_watermark(input_path: str):
    """Remove watermark from a single video."""
    try:
        from services.sora_daily import get_watermark_service
        
        service = get_watermark_service()
        result = await service.remove_watermark(input_path)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to remove watermark: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watermark/status")
async def get_watermark_service_status():
    """Check if watermark removal service is available."""
    try:
        from services.sora_daily import get_watermark_service
        
        service = get_watermark_service()
        
        return {
            "available": service.is_available,
            "blanklogo_path": str(service.blanklogo_path),
            "output_dir": str(service.output_dir)
        }
        
    except Exception as e:
        logger.error(f"Failed to check watermark status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STORY GENERATION ENDPOINTS
# =============================================================================

@router.post("/story/generate-single")
async def generate_single_prompt(
    theme: Optional[str] = None,
    trend: Optional[str] = None
):
    """Generate a single video prompt."""
    try:
        from services.sora_daily import get_story_generator
        
        generator = get_story_generator()
        prompt = await generator.generate_single_prompt(
            theme=theme,
            trend=trend,
            character="@isaiahdupree"
        )
        
        return {
            "prompt": prompt,
            "theme": theme or generator.get_random_theme(),
            "trend": trend
        }
        
    except Exception as e:
        logger.error(f"Failed to generate prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/story/generate-movie")
async def generate_movie_arc(
    theme: Optional[str] = None,
    trend: Optional[str] = None
):
    """Generate a 3-part movie story arc."""
    try:
        from services.sora_daily import get_story_generator
        
        generator = get_story_generator()
        arc = await generator.generate_story_arc(
            theme=theme,
            trend=trend,
            character="@isaiahdupree"
        )
        
        return arc
        
    except Exception as e:
        logger.error(f"Failed to generate story arc: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/themes")
async def get_available_themes():
    """Get available story themes."""
    from services.sora_daily import STORY_THEMES
    
    return {"themes": STORY_THEMES}


# =============================================================================
# HISTORY ENDPOINTS
# =============================================================================

@router.get("/history")
async def get_history(days: int = 7):
    """Get past daily runs."""
    try:
        from services.sora_daily import get_daily_scheduler
        from datetime import date, timedelta
        from sqlalchemy import text
        
        scheduler = get_daily_scheduler()
        
        with scheduler.engine.connect() as conn:
            results = conn.execute(text("""
                SELECT * FROM sora_daily_plans
                WHERE plan_date >= :start_date
                ORDER BY plan_date DESC
            """), {"start_date": date.today() - timedelta(days=days)}).fetchall()
            
            plans = []
            for r in results:
                plans.append({
                    "id": r[0],
                    "date": r[1].isoformat() if r[1] else None,
                    "total_credits": r[2],
                    "used_credits": r[3],
                    "singles_planned": r[4],
                    "movies_planned": r[5],
                    "status": r[6]
                })
        
        return {"history": plans, "days": days}
        
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
