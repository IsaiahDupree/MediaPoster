"""
Engagement Control API
======================
API endpoints for controlling engagement automation with start/stop functionality.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/engagement-control", tags=["Engagement Control"])


class ConfigUpdate(BaseModel):
    auto_resume_enabled: Optional[bool] = None
    auto_resume_hours: Optional[float] = None
    comments_per_hour: Optional[int] = None


def get_controller():
    from services.engagement.engagement_controller import get_engagement_controller
    return get_engagement_controller()


@router.get("/status")
async def get_status():
    try:
        controller = get_controller()
        status = controller.get_status()
        return {"success": True, "timestamp": datetime.utcnow().isoformat(), "status": status.to_dict()}
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_automation():
    try:
        controller = get_controller()
        result = await controller.start()
        return {"success": result.get("success", False), "message": "Engagement automation started" if result.get("success") else result.get("error"), "status": controller.get_status().to_dict()}
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_automation():
    try:
        controller = get_controller()
        result = await controller.stop()
        return {"success": result.get("success", False), "message": "Engagement automation stopped" if result.get("success") else result.get("error"), "status": controller.get_status().to_dict()}
    except Exception as e:
        logger.error(f"Failed to stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause_automation():
    try:
        controller = get_controller()
        result = await controller.pause()
        return {"success": result.get("success", False), "message": "Engagement paused" if result.get("success") else result.get("error"), "status": controller.get_status().to_dict()}
    except Exception as e:
        logger.error(f"Failed to pause: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
async def resume_automation():
    try:
        controller = get_controller()
        result = await controller.resume()
        return {"success": result.get("success", False), "message": "Engagement resumed" if result.get("success") else result.get("error"), "status": controller.get_status().to_dict()}
    except Exception as e:
        logger.error(f"Failed to resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/{platform}/enable")
async def enable_platform(platform: str):
    try:
        controller = get_controller()
        controller.enable_platform(platform, enabled=True)
        return {"success": True, "message": f"{platform} enabled", "status": controller.get_status().to_dict()}
    except Exception as e:
        logger.error(f"Failed to enable platform: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/{platform}/disable")
async def disable_platform(platform: str):
    try:
        controller = get_controller()
        controller.enable_platform(platform, enabled=False)
        return {"success": True, "message": f"{platform} disabled", "status": controller.get_status().to_dict()}
    except Exception as e:
        logger.error(f"Failed to disable platform: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_config(config: ConfigUpdate):
    try:
        controller = get_controller()
        if config.auto_resume_enabled is not None or config.auto_resume_hours is not None:
            controller.set_auto_resume(
                enabled=config.auto_resume_enabled if config.auto_resume_enabled is not None else controller.auto_resume_enabled,
                hours=config.auto_resume_hours if config.auto_resume_hours is not None else controller.auto_resume_after_hours
            )
        if config.comments_per_hour is not None:
            controller.COMMENTS_PER_HOUR_PER_PLATFORM = config.comments_per_hour
        return {"success": True, "message": "Configuration updated", "status": controller.get_status().to_dict()}
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
