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
# TREND-AWARE PROMPT ENDPOINTS
# =============================================================================

@router.get("/trend-prompts")
async def get_trend_prompts(
    month: Optional[str] = None,
    category: Optional[str] = None,
    trend_name: Optional[str] = None,
    series_id: Optional[str] = None,
):
    """
    Get curated trend-aware Sora prompts for @isaiahdupree.
    
    Filters:
    - month: e.g. "2026-02" (defaults to current month)
    - category: "single", "series_part_1", "series_part_2", "series_part_3"
    - trend_name: partial match on trend name
    - series_id: exact match on series ID
    """
    try:
        from services.sora_daily.trend_prompts import get_trend_prompt_library
        
        library = get_trend_prompt_library()
        prompts = library.get_prompts(
            month=month,
            category=category,
            series_id=series_id,
            trend_name=trend_name,
        )
        
        return {
            "prompts": [p.to_dict() for p in prompts],
            "count": len(prompts),
            "month": month or library.get_current_month(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get trend prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend-prompts/trends")
async def list_available_trends(month: Optional[str] = None):
    """List unique trend names available for the given month."""
    try:
        from services.sora_daily.trend_prompts import get_trend_prompt_library
        
        library = get_trend_prompt_library()
        trends = library.list_trends(month=month)
        
        return {
            "trends": trends,
            "count": len(trends),
            "month": month or library.get_current_month(),
        }
        
    except Exception as e:
        logger.error(f"Failed to list trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend-prompts/series")
async def get_trend_series(month: Optional[str] = None):
    """Get all multi-part series grouped by series_id."""
    try:
        from services.sora_daily.trend_prompts import get_trend_prompt_library
        
        library = get_trend_prompt_library()
        series = library.get_series(month=month)
        
        result = {}
        for sid, parts in series.items():
            result[sid] = {
                "series_id": sid,
                "trend_name": parts[0].trend_name if parts else "",
                "part_count": len(parts),
                "parts": [p.to_dict() for p in parts],
            }
        
        return {
            "series": result,
            "count": len(result),
            "month": month or library.get_current_month(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get trend series: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend-prompts/{prompt_id}")
async def get_trend_prompt_by_id(prompt_id: str):
    """Get a specific trend prompt by its ID."""
    try:
        from services.sora_daily.trend_prompts import get_trend_prompt_library
        
        library = get_trend_prompt_library()
        prompt = library.get_prompt_by_id(prompt_id)
        
        if not prompt:
            raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")
        
        return prompt.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trend prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trend-prompts/random")
async def get_random_trend_content(
    content_type: str = "single",
    trend_name: Optional[str] = None,
):
    """
    Get a random trend prompt or series for quick generation.
    
    Args:
        content_type: "single" for standalone, "series" for 3-part
        trend_name: optional filter by trend
    """
    try:
        from services.sora_daily.story_generator import get_story_generator
        
        generator = get_story_generator()
        
        if content_type == "series":
            result = await generator.generate_trend_series(
                trend_name=trend_name,
                character="@isaiahdupree",
            )
        else:
            result = await generator.generate_trend_prompt(
                trend_name=trend_name,
                character="@isaiahdupree",
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate trend content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CustomTrendRequest(BaseModel):
    """Request to generate a custom trend-based Sora prompt."""
    trend_description: str = Field(..., description="Description of the trend to incorporate")
    style: str = Field(default="cinematic 4K", description="Visual style")


@router.post("/trend-prompts/generate-custom")
async def generate_custom_trend_prompt(request: CustomTrendRequest):
    """Generate a custom Sora prompt based on a trend description using AI."""
    try:
        from services.sora_daily.trend_prompts import get_trend_prompt_library
        
        library = get_trend_prompt_library()
        prompt = await library.generate_custom_trend_prompt(
            trend_description=request.trend_description,
            character="@isaiahdupree",
            style=request.style,
        )
        
        return {
            "sora_prompt": prompt,
            "trend_description": request.trend_description,
            "style": request.style,
            "character": "@isaiahdupree",
            "source": "ai_generated",
        }
        
    except Exception as e:
        logger.error(f"Failed to generate custom trend prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


# =============================================================================
# DYNAMIC SCRIPT GENERATION ENDPOINTS
# =============================================================================

class GenerateScriptsRequest(BaseModel):
    """Request to generate new Sora scripts."""
    source: str = Field(
        default="live",
        description="Trend source: 'live' (fetch from web), 'internal' (from collected trends), 'manual' (provide descriptions)"
    )
    count: int = Field(default=5, ge=1, le=15, description="Number of scripts to generate")
    include_series: bool = Field(default=True, description="Include multi-part series")
    descriptions: Optional[List[str]] = Field(
        default=None,
        description="Manual trend descriptions (required when source='manual')"
    )


@router.post("/scripts/generate")
async def generate_scripts(request: GenerateScriptsRequest, background_tasks: BackgroundTasks):
    """
    Generate new Sora script packages from trend data.

    Sources:
    - **live**: Fetches current trends from web sources, then generates scripts via AI
    - **internal**: Uses trends already collected by TrendCollector (comments, DMs, CRM)
    - **manual**: You provide trend descriptions, AI generates scripts from them

    Returns immediately with a job_id; scripts are generated in the background.
    """
    from services.sora_daily.script_generator import get_script_generator

    job_id = str(__import__("uuid").uuid4())

    background_tasks.add_task(
        _run_script_generation,
        job_id,
        request.source,
        request.count,
        request.include_series,
        request.descriptions,
    )

    return {
        "job_id": job_id,
        "status": "generating",
        "source": request.source,
        "count": request.count,
        "message": f"Generating {request.count} scripts from '{request.source}' trends in background. Poll GET /sora-daily/scripts to see results.",
    }


async def _run_script_generation(
    job_id: str,
    source: str,
    count: int,
    include_series: bool,
    descriptions: Optional[List[str]],
):
    """Background task that runs the script generation pipeline."""
    try:
        from services.sora_daily.script_generator import get_script_generator

        gen = get_script_generator()

        if source == "manual" and descriptions:
            scripts = await gen.generate_from_descriptions(descriptions, include_series)
        elif source == "internal":
            scripts = await gen.generate_from_collected_trends(count, include_series)
        else:  # "live" or default
            scripts = await gen.generate_from_live_trends(count, include_series)

        logger.info(f"🎬 Script generation job {job_id}: produced {len(scripts)} scripts")

    except Exception as e:
        logger.error(f"Script generation job {job_id} failed: {e}")


@router.post("/scripts/generate-sync")
async def generate_scripts_sync(request: GenerateScriptsRequest):
    """
    Same as /scripts/generate but waits for completion and returns results directly.
    Use for small batches (count <= 5) or when you need results immediately.
    """
    try:
        from services.sora_daily.script_generator import get_script_generator

        gen = get_script_generator()

        if request.source == "manual" and request.descriptions:
            scripts = await gen.generate_from_descriptions(
                request.descriptions, request.include_series
            )
        elif request.source == "internal":
            scripts = await gen.generate_from_collected_trends(
                request.count, request.include_series
            )
        else:
            scripts = await gen.generate_from_live_trends(
                request.count, request.include_series
            )

        return {
            "scripts": [s.to_dict() for s in scripts],
            "count": len(scripts),
            "source": request.source,
        }

    except Exception as e:
        logger.error(f"Sync script generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scripts")
async def list_scripts(
    month: Optional[str] = None,
    status: Optional[str] = None,
    format_type: Optional[str] = None,
    limit: int = 50,
):
    """
    List saved generated scripts.

    Filters:
    - month: e.g. "2026-02"
    - status: generated | approved | queued | used | archived
    - format_type: single | series
    """
    try:
        from services.sora_daily.script_generator import get_script_generator

        gen = get_script_generator()
        scripts = gen.get_scripts(
            month=month, status=status, format_type=format_type, limit=limit
        )

        return {
            "scripts": [s.to_dict() for s in scripts],
            "count": len(scripts),
        }

    except Exception as e:
        logger.error(f"Failed to list scripts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scripts/{script_id}")
async def get_script(script_id: str):
    """Get a single generated script by ID."""
    try:
        from services.sora_daily.script_generator import get_script_generator

        gen = get_script_generator()
        script = gen.get_script_by_id(script_id)

        if not script:
            raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")

        return script.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateScriptStatusRequest(BaseModel):
    """Request to update a script's status."""
    status: str = Field(..., description="New status: generated | approved | queued | used | archived")


@router.patch("/scripts/{script_id}/status")
async def update_script_status(script_id: str, request: UpdateScriptStatusRequest):
    """Update a script's workflow status."""
    valid = {"generated", "approved", "queued", "used", "archived"}
    if request.status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid}")

    try:
        from services.sora_daily.script_generator import get_script_generator

        gen = get_script_generator()
        ok = gen.update_script_status(script_id, request.status)

        if not ok:
            raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")

        return {"script_id": script_id, "status": request.status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update script status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scripts/{script_id}")
async def delete_script(script_id: str):
    """Delete a generated script."""
    try:
        from services.sora_daily.script_generator import get_script_generator

        gen = get_script_generator()
        ok = gen.delete_script(script_id)

        if not ok:
            raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")

        return {"deleted": True, "script_id": script_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete script: {e}")
        raise HTTPException(status_code=500, detail=str(e))
