"""
Safari Automation API Endpoints
===============================
Control and monitor the Safari browser automation system.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/safari", tags=["Safari Automation"])


# Request/Response Models
class SoraGenerationRequest(BaseModel):
    prompt: str
    trend_source: Optional[str] = None
    character: str = "@isaiahdupree"


class CommentRequest(BaseModel):
    platform: str  # twitter, tiktok, instagram, threads
    post_url: Optional[str] = None
    comment_text: Optional[str] = None  # If None, AI generates


class TweetRequest(BaseModel):
    tweet_text: Optional[str] = None  # If None, AI generates
    media_path: Optional[str] = None


class VideoProcessRequest(BaseModel):
    video_path: str


class StatusResponse(BaseModel):
    running: bool
    started_at: Optional[str]
    uptime_minutes: float
    today: Dict[str, Any]
    limits: Dict[str, int]
    queue: Dict[str, Any]
    services: Dict[str, bool]


# Helper to get orchestrator
def get_orchestrator():
    from services.safari_automation_orchestrator import SafariAutomationOrchestrator
    return SafariAutomationOrchestrator.get_instance()


# ============================================================================
# Lifecycle Endpoints
# ============================================================================

@router.post("/start")
async def start_orchestrator(background_tasks: BackgroundTasks):
    """Start the Safari automation orchestrator."""
    orchestrator = get_orchestrator()
    
    if orchestrator.running:
        return {"status": "already_running", "message": "Orchestrator is already running"}
    
    background_tasks.add_task(orchestrator.start)
    
    return {
        "status": "starting",
        "message": "Safari automation orchestrator starting...",
        "config": {
            "comments_per_hour": orchestrator.config.comments_per_hour,
            "tweets_per_day": orchestrator.config.tweets_per_day,
            "sora_per_day": orchestrator.config.sora_generations_per_day
        }
    }


@router.post("/stop")
async def stop_orchestrator():
    """Stop the Safari automation orchestrator."""
    orchestrator = get_orchestrator()
    
    if not orchestrator.running:
        return {"status": "already_stopped", "message": "Orchestrator is not running"}
    
    await orchestrator.stop()
    
    return {
        "status": "stopped",
        "message": "Safari automation orchestrator stopped",
        "stats": orchestrator.get_status()["today"]
    }


@router.post("/pause")
async def pause_orchestrator():
    """Pause the orchestrator (keeps queue, stops processing)."""
    orchestrator = get_orchestrator()
    orchestrator.pause()
    return {"status": "paused"}


@router.post("/resume")
async def resume_orchestrator():
    """Resume the paused orchestrator."""
    orchestrator = get_orchestrator()
    orchestrator.resume()
    return {"status": "resumed"}


# ============================================================================
# Status Endpoints
# ============================================================================

@router.get("/status")
async def get_status() -> StatusResponse:
    """Get current orchestrator status."""
    orchestrator = get_orchestrator()
    return orchestrator.get_status()


@router.get("/queue")
async def get_queue():
    """Get current task queue."""
    orchestrator = get_orchestrator()
    return {
        "queue_size": orchestrator.queue_manager.get_status()["queue_size"],
        "preview": orchestrator.queue_manager.get_queue_preview(20),
        "current_task": orchestrator.queue_manager.current_task.task_type.value if orchestrator.queue_manager.current_task else None
    }


@router.get("/stats/today")
async def get_today_stats():
    """Get today's automation statistics."""
    orchestrator = get_orchestrator()
    status = orchestrator.get_status()
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "stats": status["today"],
        "limits": status["limits"],
        "utilization": {
            "comments": f"{status['today']['comments']}/{status['limits']['comments_per_hour'] * 24}",
            "tweets": f"{status['today']['tweets']}/{status['limits']['tweets_per_day']}",
            "sora": f"{status['today']['sora_generations']}/{status['limits']['sora_per_day']}"
        }
    }


# ============================================================================
# Manual Task Endpoints
# ============================================================================

@router.post("/comment")
async def queue_comment(request: CommentRequest):
    """Manually queue a comment task."""
    orchestrator = get_orchestrator()
    
    if request.platform not in ['twitter', 'tiktok', 'instagram', 'threads']:
        raise HTTPException(status_code=400, detail="Invalid platform")
    
    await orchestrator.queue_manager.add_comment_task(
        platform=request.platform,
        post_url=request.post_url or f"https://{request.platform}.com/feed",
        comment_text=request.comment_text or "AI will generate"
    )
    
    return {
        "status": "queued",
        "platform": request.platform,
        "queue_size": orchestrator.queue_manager.get_status()["queue_size"]
    }


@router.post("/tweet")
async def queue_tweet(request: TweetRequest):
    """Manually queue a tweet task."""
    orchestrator = get_orchestrator()
    
    await orchestrator.queue_manager.add_tweet_task(
        tweet_text=request.tweet_text or "AI will generate offer tweet",
        media_path=request.media_path
    )
    
    return {
        "status": "queued",
        "queue_size": orchestrator.queue_manager.get_status()["queue_size"]
    }


@router.post("/sora/generate")
async def queue_sora_generation(request: SoraGenerationRequest):
    """Queue a Sora video generation."""
    orchestrator = get_orchestrator()
    
    if orchestrator.sora_generations_today >= orchestrator.config.sora_generations_per_day:
        raise HTTPException(
            status_code=429,
            detail=f"Daily Sora limit reached ({orchestrator.config.sora_generations_per_day})"
        )
    
    success = await orchestrator.queue_sora_generation(
        prompt=request.prompt,
        trend_source=request.trend_source
    )
    
    return {
        "status": "queued" if success else "failed",
        "prompt": request.prompt[:100],
        "generations_today": orchestrator.sora_generations_today,
        "remaining": orchestrator.config.sora_generations_per_day - orchestrator.sora_generations_today
    }


@router.post("/video/process")
async def process_video(request: VideoProcessRequest):
    """Manually trigger video processing (watermark removal + distribution)."""
    import os
    
    if not os.path.exists(request.video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    orchestrator = get_orchestrator()
    await orchestrator.process_downloaded_video(request.video_path)
    
    return {
        "status": "queued",
        "video": request.video_path,
        "pipeline": "watermark_removal -> blotato_distribution"
    }


# ============================================================================
# Service Status Endpoints
# ============================================================================

@router.get("/services")
async def check_services():
    """Check status of all integrated services."""
    results = {}
    
    # Twitter
    try:
        from automation.safari_twitter_poster import SafariTwitterPoster
        poster = SafariTwitterPoster(use_x_domain=True)
        login = poster.simple_login_check()
        results["twitter"] = {
            "available": True,
            "logged_in": login if isinstance(login, bool) else True
        }
    except Exception as e:
        results["twitter"] = {"available": False, "error": str(e)}
    
    # Watermark Service
    try:
        from services.sora_daily.watermark_service import WatermarkRemovalService
        service = WatermarkRemovalService()
        results["watermark_service"] = {
            "available": True,
            "blanklogo_available": service.is_available
        }
    except Exception as e:
        results["watermark_service"] = {"available": False, "error": str(e)}
    
    # Sora
    try:
        from automation.sora_full_automation import SoraFullAutomation
        sora = SoraFullAutomation()
        results["sora"] = {
            "available": True,
            "max_concurrent": sora.MAX_QUEUE_SIZE
        }
    except Exception as e:
        results["sora"] = {"available": False, "error": str(e)}
    
    # Blotato
    try:
        from connectors.blotato import BlotatoConnector
        connector = BlotatoConnector()
        results["blotato"] = {"available": True}
    except Exception as e:
        results["blotato"] = {"available": False, "error": str(e)}
    
    # Engagement Controller
    try:
        from services.engagement.engagement_controller import EngagementController
        ctrl = EngagementController.get_instance()
        results["engagement"] = {
            "available": True,
            "platforms": list(ctrl.get_status().platforms.keys())
        }
    except Exception as e:
        results["engagement"] = {"available": False, "error": str(e)}
    
    return results


# ============================================================================
# Script Generation Trigger (Dynamic Sora Script Pipeline)
# ============================================================================

class ScriptGenerationRequest(BaseModel):
    """Request to trigger dynamic Sora script generation."""
    source: str = "live"  # "live", "internal", "manual"
    count: int = 5
    include_series: bool = True
    descriptions: Optional[List[str]] = None  # required for source="manual"


@router.post("/scripts/generate")
async def trigger_script_generation(
    request: ScriptGenerationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger dynamic Sora script generation from the Safari automation server.

    Sources:
    - **live**: Scrapes current web trends and generates scripts via AI
    - **internal**: Uses trends from comments, DMs, CRM data
    - **manual**: Provide trend descriptions, AI generates scripts from them

    Scripts are saved to the DB and can be queued for the SoraScheduler.
    """
    import uuid

    job_id = str(uuid.uuid4())
    background_tasks.add_task(
        _run_safari_script_generation,
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
        "message": (
            f"Generating {request.count} Sora scripts from '{request.source}' trends. "
            f"Poll GET /api/sora-daily/scripts to see results."
        ),
    }


@router.post("/scripts/generate-now")
async def trigger_script_generation_sync(request: ScriptGenerationRequest):
    """
    Synchronous version — waits for generation to complete and returns scripts.
    Best for small batches (count <= 5).
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scripts")
async def list_generated_scripts(
    status: Optional[str] = None,
    limit: int = 50,
):
    """List generated scripts from the Safari automation pipeline."""
    try:
        from services.sora_daily.script_generator import get_script_generator

        gen = get_script_generator()
        scripts = gen.get_scripts(status=status, limit=limit)
        return {"scripts": [s.to_dict() for s in scripts], "count": len(scripts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scripts/{script_id}/queue")
async def queue_script_for_scheduler(script_id: str):
    """Approve a generated script and queue it for the SoraScheduler to pick up."""
    try:
        from services.sora_daily.script_generator import get_script_generator

        gen = get_script_generator()
        script = gen.get_script_by_id(script_id)
        if not script:
            raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")

        gen.update_script_status(script_id, "queued")
        return {
            "script_id": script_id,
            "title": script.title,
            "status": "queued",
            "message": "Script queued — SoraScheduler will use it for the next generation.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _run_safari_script_generation(
    job_id: str,
    source: str,
    count: int,
    include_series: bool,
    descriptions: Optional[List[str]],
):
    """Background task for script generation triggered from Safari automation."""
    from loguru import logger

    try:
        from services.sora_daily.script_generator import get_script_generator

        gen = get_script_generator()

        if source == "manual" and descriptions:
            scripts = await gen.generate_from_descriptions(descriptions, include_series)
        elif source == "internal":
            scripts = await gen.generate_from_collected_trends(count, include_series)
        else:
            scripts = await gen.generate_from_live_trends(count, include_series)

        logger.info(
            f"🎬 Safari script generation job {job_id}: produced {len(scripts)} scripts"
        )
    except Exception as e:
        logger.error(f"Safari script generation job {job_id} failed: {e}")


@router.get("/1hour-schedule")
async def get_hourly_schedule():
    """Get the 1-hour task schedule breakdown."""
    return {
        "schedule": {
            "comments": {
                "total_per_hour": 30,
                "interval_seconds": 120,
                "platforms": {
                    "twitter": 8,
                    "tiktok": 8,
                    "instagram": 7,
                    "threads": 7
                }
            },
            "tweets": {
                "interval_hours": 2,
                "per_day": 12
            },
            "sora": {
                "per_day": 30,
                "poll_interval_seconds": 30,
                "max_concurrent": 3
            },
            "stats": {
                "interval_minutes": 10
            }
        },
        "minute_breakdown": [
            {"minute": 0, "tasks": ["tweet (if 2hr mark)", "comment"]},
            {"minute": 2, "tasks": ["comment"]},
            {"minute": 4, "tasks": ["comment", "sora_poll"]},
            {"minute": 6, "tasks": ["comment"]},
            {"minute": 8, "tasks": ["comment"]},
            {"minute": 10, "tasks": ["comment", "stats_check"]},
            # ... pattern repeats
        ],
        "video_pipeline": [
            "1. Sora generates video",
            "2. Video downloaded to /sora_downloads/",
            "3. File watcher detects new .mp4",
            "4. BlankLogo removes watermark",
            "5. Processed video saved to /sora_processed/",
            "6. Video distributed via Blotato to 17+ accounts"
        ]
    }
