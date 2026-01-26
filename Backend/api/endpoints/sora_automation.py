"""
Sora Automation API
====================
API endpoints for Sora video generation and usage tracking.

Uses pub/sub event architecture:
    - Emits events to EventBus for all operations
    - SoraWorker subscribes to handle requests
    - All operations are event-driven and can be monitored
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging
import asyncio

from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sora", tags=["Sora Automation"])

def get_event_bus() -> EventBus:
    """Get the singleton EventBus instance."""
    return EventBus.get_instance()


class VideoGenerateRequest(BaseModel):
    prompt: str
    character: Optional[str] = "isaiahdupree"
    style: Optional[str] = None
    duration: int = 15
    aspect_ratio: str = "Portrait"


class BatchGenerateRequest(BaseModel):
    prompts: List[str]
    character: Optional[str] = "isaiahdupree"
    auto_download: bool = True


@router.get("/usage")
async def get_usage():
    """Get current Sora usage (video gens left, resets date)"""
    try:
        from services.sora import get_sora_usage_tracker
        
        tracker = get_sora_usage_tracker()
        
        # Use cached if recent, otherwise check
        if not tracker.should_check() and tracker.get_cached_usage():
            usage = tracker.get_cached_usage()
            return {
                "success": True,
                "cached": True,
                "usage": usage.to_dict()
            }
        
        # Fresh check
        usage = await tracker.check_and_store()
        return {
            "success": True,
            "cached": False,
            "usage": usage.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to get Sora usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/cached")
async def get_cached_usage():
    """Get cached usage without checking (fast)"""
    from services.sora import get_sora_usage_tracker
    
    tracker = get_sora_usage_tracker()
    usage = tracker.get_cached_usage()
    
    if usage:
        return {"success": True, "usage": usage.to_dict()}
    else:
        return {"success": False, "message": "No cached usage available"}


@router.get("/timeouts")
async def get_timeouts():
    """Get all Sora automation timeouts"""
    from services.sora import SORA_TIMEOUTS
    return {"success": True, "timeouts": SORA_TIMEOUTS}


@router.post("/usage/check")
async def force_usage_check():
    """Force a fresh usage check"""
    try:
        from services.sora import get_sora_usage_tracker
        
        tracker = get_sora_usage_tracker()
        usage = await tracker.check_and_store()
        
        return {
            "success": True,
            "usage": usage.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to check Sora usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_video(request: VideoGenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate a single video with Sora.
    
    Emits: sora.video.requested → SoraWorker handles generation
    """
    try:
        bus = get_event_bus()
        
        # Emit event for SoraWorker to handle
        event_id = await bus.publish(
            Topics.SORA_VIDEO_REQUESTED,
            {
                "prompt": request.prompt,
                "character": request.character,
                "style": request.style,
                "duration": request.duration,
                "aspect_ratio": request.aspect_ratio
            },
            source="sora-api"
        )
        
        return {
            "success": True,
            "message": "Video generation requested",
            "event_id": event_id,
            "topic": Topics.SORA_VIDEO_REQUESTED,
            "prompt": request.prompt,
            "character": request.character
        }
        
    except Exception as e:
        logger.error(f"Failed to generate video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/batch")
async def generate_batch(request: BatchGenerateRequest):
    """
    Generate multiple videos as a batch.
    
    Emits: sora.batch.requested → SoraWorker handles batch
    """
    try:
        bus = get_event_bus()
        
        # Emit batch request event
        event_id = await bus.publish(
            Topics.SORA_BATCH_REQUESTED,
            {
                "prompts": request.prompts,
                "character": request.character,
                "auto_download": request.auto_download
            },
            source="sora-api"
        )
        
        return {
            "success": True,
            "message": "Batch generation requested",
            "event_id": event_id,
            "topic": Topics.SORA_BATCH_REQUESTED,
            "jobs_count": len(request.prompts)
        }
        
    except Exception as e:
        logger.error(f"Failed to generate batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/periodic-checks/start")
async def start_periodic_checks(interval_minutes: int = 30):
    """Start periodic Sora usage checks"""
    try:
        from services.sora import get_sora_usage_tracker
        
        tracker = get_sora_usage_tracker()
        await tracker.start_periodic_checks(interval_minutes)
        
        return {
            "success": True,
            "message": f"Started periodic checks every {interval_minutes} minutes"
        }
        
    except Exception as e:
        logger.error(f"Failed to start periodic checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/periodic-checks/stop")
async def stop_periodic_checks():
    """Stop periodic Sora usage checks"""
    try:
        from services.sora import get_sora_usage_tracker
        
        tracker = get_sora_usage_tracker()
        tracker.stop_periodic_checks()
        
        return {"success": True, "message": "Stopped periodic checks"}
        
    except Exception as e:
        logger.error(f"Failed to stop periodic checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# VIDEO POLLING & AUTO-DOWNLOAD
# =============================================================================

@router.post("/poll/start")
async def start_video_polling(timeout_minutes: int = 15):
    """
    Start polling /drafts for completed videos and auto-download them.
    
    Typical video generation takes 8-12 minutes.
    Default timeout: 15 minutes.
    """
    try:
        from services.sora import get_sora_video_poller
        
        poller = get_sora_video_poller()
        
        if poller.is_polling():
            return {"success": False, "message": "Already polling"}
        
        await poller.start_background_polling(timeout_minutes)
        
        return {
            "success": True,
            "message": f"Started video polling (timeout: {timeout_minutes} min)",
            "poll_interval_seconds": poller.POLL_INTERVAL_SECONDS
        }
        
    except Exception as e:
        logger.error(f"Failed to start polling: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/poll/stop")
async def stop_video_polling():
    """Stop video polling"""
    try:
        from services.sora import get_sora_video_poller
        
        poller = get_sora_video_poller()
        poller.stop_polling()
        
        return {"success": True, "message": "Stopped video polling"}
        
    except Exception as e:
        logger.error(f"Failed to stop polling: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/poll/status")
async def get_polling_status():
    """Get current polling status"""
    try:
        from services.sora import get_sora_video_poller
        
        poller = get_sora_video_poller()
        
        return {
            "success": True,
            "is_polling": poller.is_polling(),
            "downloaded_count": len(poller._downloaded_ids),
            "poll_interval_seconds": poller.POLL_INTERVAL_SECONDS
        }
        
    except Exception as e:
        logger.error(f"Failed to get polling status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/poll/download-now")
async def poll_and_download_now(timeout_minutes: int = 15):
    """
    Poll and download completed videos synchronously (blocking).
    Returns list of downloaded video paths.
    """
    try:
        from services.sora import get_sora_video_poller
        
        poller = get_sora_video_poller()
        downloaded = await poller.poll_and_download(timeout_minutes)
        
        return {
            "success": True,
            "downloaded_count": len(downloaded),
            "downloaded_paths": downloaded
        }
        
    except Exception as e:
        logger.error(f"Failed to poll/download: {e}")
        raise HTTPException(status_code=500, detail=str(e))
