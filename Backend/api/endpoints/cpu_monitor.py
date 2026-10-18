"""
CPU Monitor API Endpoints
==========================
API for monitoring CPU usage and auto-sleep configuration.

Endpoints:
- GET /api/cpu/status - Get current CPU metrics and status
- GET /api/cpu/metrics - Get CPU metrics history
- POST /api/cpu/auto-sleep/enable - Enable auto-sleep on idle
- POST /api/cpu/auto-sleep/disable - Disable auto-sleep on idle
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger

from services.cpu_monitor import get_cpu_monitor


router = APIRouter(prefix="/api/cpu", tags=["CPU Monitor"])


class EnableAutoSleepRequest(BaseModel):
    """Request to enable auto-sleep"""
    idle_threshold: float = Field(default=5.0, description="CPU percentage below which system is idle (default: 5%)")
    idle_timeout_seconds: int = Field(default=300, description="Seconds of idle time before sleep (default: 300)")


@router.get("/status")
async def get_cpu_status():
    """
    Get current CPU monitor status

    Returns:
        - Current CPU metrics (CPU %, memory %, etc.)
        - Average CPU over 1min and 5min
        - Idle status
        - Auto-sleep configuration
        - Metrics history size
    """
    try:
        cpu_monitor = get_cpu_monitor()
        status = cpu_monitor.get_status()

        return {
            "success": True,
            "data": status
        }

    except Exception as e:
        logger.error(f"Error getting CPU status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_cpu_metrics(limit: int = 50):
    """
    Get CPU metrics history

    Returns history of CPU usage readings.

    Args:
        limit: Maximum number of metrics to return (default: 50, max: 100)
    """
    try:
        cpu_monitor = get_cpu_monitor()

        # Limit to max 100
        limit = min(limit, 100)

        metrics = cpu_monitor.get_metrics_history(limit=limit)

        return {
            "success": True,
            "data": {
                "metrics": metrics,
                "count": len(metrics)
            }
        }

    except Exception as e:
        logger.error(f"Error getting CPU metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-sleep/enable")
async def enable_auto_sleep(request: EnableAutoSleepRequest = EnableAutoSleepRequest()):
    """
    Enable auto-sleep on idle

    System will automatically enter sleep mode when CPU usage
    stays below the threshold for the specified timeout period.

    Args:
        idle_threshold: CPU percentage below which system is idle (default: 5%)
        idle_timeout_seconds: Seconds of idle time before sleep (default: 300)
    """
    try:
        cpu_monitor = get_cpu_monitor()

        # Validate parameters
        if request.idle_threshold < 0 or request.idle_threshold > 100:
            raise HTTPException(
                status_code=400,
                detail="idle_threshold must be between 0 and 100"
            )

        if request.idle_timeout_seconds < 60:
            raise HTTPException(
                status_code=400,
                detail="idle_timeout_seconds must be at least 60 seconds"
            )

        cpu_monitor.enable_auto_sleep(
            idle_threshold=request.idle_threshold,
            idle_timeout_seconds=request.idle_timeout_seconds
        )

        return {
            "success": True,
            "message": "Auto-sleep enabled",
            "data": {
                "idle_threshold": request.idle_threshold,
                "idle_timeout_seconds": request.idle_timeout_seconds
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling auto-sleep: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-sleep/disable")
async def disable_auto_sleep():
    """
    Disable auto-sleep on idle

    System will no longer automatically enter sleep mode when idle.
    """
    try:
        cpu_monitor = get_cpu_monitor()
        cpu_monitor.disable_auto_sleep()

        return {
            "success": True,
            "message": "Auto-sleep disabled"
        }

    except Exception as e:
        logger.error(f"Error disabling auto-sleep: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def cpu_monitor_health():
    """
    Health check for CPU monitor service

    Returns whether service is running and operational.
    """
    try:
        cpu_monitor = get_cpu_monitor()

        return {
            "success": True,
            "data": {
                "is_running": cpu_monitor._is_running,
                "current_metrics_available": cpu_monitor._current_metrics is not None,
                "metrics_history_size": len(cpu_monitor._metrics_history)
            }
        }

    except Exception as e:
        logger.error(f"Error checking CPU monitor health: {e}")
        return {
            "success": False,
            "error": str(e)
        }
