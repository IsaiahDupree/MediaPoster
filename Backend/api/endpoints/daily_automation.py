"""
Daily Automation API Endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from services.daily_automation import DailyAutomationManager

router = APIRouter(prefix="/api/daily-automation", tags=["daily-automation"])


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get current automation status."""
    manager = DailyAutomationManager.get_instance()
    return {"success": True, **manager.get_status()}


@router.post("/start")
async def start_automation() -> Dict[str, Any]:
    """Manually start/restart automation."""
    manager = DailyAutomationManager.get_instance()
    await manager.manual_start()
    return {"success": True, "message": "Automation started", **manager.get_status()}


@router.post("/stop")
async def stop_automation() -> Dict[str, Any]:
    """Stop all automation."""
    manager = DailyAutomationManager.get_instance()
    await manager.shutdown()
    return {"success": True, "message": "Automation stopped"}


@router.get("/sora")
async def get_sora_status() -> Dict[str, Any]:
    """Get Sora scheduler status."""
    manager = DailyAutomationManager.get_instance()
    return {"success": True, **manager.sora_scheduler.get_status()}


@router.post("/sora/check-credits")
async def check_sora_credits() -> Dict[str, Any]:
    """Manually trigger Sora credit check."""
    manager = DailyAutomationManager.get_instance()
    credits = await manager.sora_scheduler.check_credits()
    return {
        "success": True,
        "remaining": credits.remaining,
        "total": credits.total,
        "used": credits.used
    }


@router.get("/twitter")
async def get_twitter_status() -> Dict[str, Any]:
    """Get Twitter scheduler status."""
    manager = DailyAutomationManager.get_instance()
    return {"success": True, **manager.twitter_scheduler.get_status()}
