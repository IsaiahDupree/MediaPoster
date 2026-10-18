"""
Sleep Mode API Endpoints
=========================
API for monitoring and controlling sleep/wake mode.

Endpoints:
- GET /api/sleep/status - Get current sleep mode status
- POST /api/sleep/enter - Manually enter sleep mode
- POST /api/sleep/wake - Manually wake from sleep mode
- POST /api/sleep/schedule-wake - Schedule a wake event
- DELETE /api/sleep/wake/{trigger_id} - Cancel scheduled wake
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from loguru import logger

from services.sleep_mode_service import (
    SleepModeService,
    WakeTriggerType,
    SleepState
)


router = APIRouter(prefix="/api/sleep", tags=["Sleep Mode"])


class ScheduleWakeRequest(BaseModel):
    """Request to schedule a wake event"""
    wake_time: datetime = Field(..., description="When to wake (UTC)")
    trigger_type: str = Field(..., description="Trigger type (scheduled_post, checkback_period, manual, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional wake context")


class WakeRequest(BaseModel):
    """Request to wake manually"""
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Wake context")


@router.get("/status")
async def get_sleep_status():
    """
    Get current sleep mode status

    Returns:
        - Current state (awake, sleeping, waking)
        - Sleep metrics (count, duration, etc.)
        - Upcoming wake triggers
        - Next wake time
    """
    try:
        sleep_service = SleepModeService.get_instance()
        status = sleep_service.get_status()

        return {
            "success": True,
            "data": status
        }

    except Exception as e:
        logger.error(f"Error getting sleep status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enter")
async def enter_sleep_mode():
    """
    Manually enter sleep mode

    Pauses workers and reduces CPU usage.
    System will wake automatically for scheduled events.
    """
    try:
        sleep_service = SleepModeService.get_instance()

        if sleep_service.state == SleepState.SLEEPING:
            return {
                "success": False,
                "message": "Already in sleep mode",
                "data": sleep_service.get_status()
            }

        await sleep_service.enter_sleep()

        return {
            "success": True,
            "message": "Entered sleep mode",
            "data": sleep_service.get_status()
        }

    except Exception as e:
        logger.error(f"Error entering sleep mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wake")
async def wake_from_sleep(request: WakeRequest = WakeRequest()):
    """
    Manually wake from sleep mode

    Resumes workers and restores normal operation.
    """
    try:
        sleep_service = SleepModeService.get_instance()

        if sleep_service.state == SleepState.AWAKE:
            return {
                "success": False,
                "message": "Already awake",
                "data": sleep_service.get_status()
            }

        await sleep_service.wake(
            trigger_type=WakeTriggerType.MANUAL,
            metadata=request.metadata
        )

        return {
            "success": True,
            "message": "Woke from sleep",
            "data": sleep_service.get_status()
        }

    except Exception as e:
        logger.error(f"Error waking from sleep: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule-wake")
async def schedule_wake(request: ScheduleWakeRequest):
    """
    Schedule a future wake event

    Args:
        wake_time: When to wake (UTC datetime)
        trigger_type: Why to wake (scheduled_post, checkback_period, etc.)
        metadata: Additional context
    """
    try:
        # Parse trigger type
        try:
            trigger_type = WakeTriggerType(request.trigger_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid trigger_type: {request.trigger_type}. "
                       f"Valid types: {[t.value for t in WakeTriggerType]}"
            )

        # Ensure wake_time is in the future
        now = datetime.now(timezone.utc)
        if request.wake_time <= now:
            raise HTTPException(
                status_code=400,
                detail="wake_time must be in the future"
            )

        sleep_service = SleepModeService.get_instance()
        trigger_id = sleep_service.schedule_wake(
            wake_time=request.wake_time,
            trigger_type=trigger_type,
            metadata=request.metadata
        )

        return {
            "success": True,
            "message": "Wake scheduled",
            "data": {
                "trigger_id": trigger_id,
                "wake_time": request.wake_time.isoformat(),
                "trigger_type": trigger_type.value,
                "seconds_until_wake": (request.wake_time - now).total_seconds()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling wake: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/wake/{trigger_id}")
async def cancel_wake(trigger_id: str):
    """
    Cancel a scheduled wake event

    Args:
        trigger_id: ID of wake trigger to cancel
    """
    try:
        sleep_service = SleepModeService.get_instance()
        cancelled = sleep_service.cancel_wake(trigger_id)

        if not cancelled:
            raise HTTPException(
                status_code=404,
                detail=f"Wake trigger not found: {trigger_id}"
            )

        return {
            "success": True,
            "message": "Wake cancelled",
            "data": {
                "trigger_id": trigger_id
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling wake: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def sleep_mode_health():
    """
    Health check for sleep mode service

    Returns whether service is running and operational.
    """
    try:
        sleep_service = SleepModeService.get_instance()

        return {
            "success": True,
            "data": {
                "is_running": sleep_service._is_running,
                "state": sleep_service.state.value,
                "wake_triggers_count": len(sleep_service.wake_triggers)
            }
        }

    except Exception as e:
        logger.error(f"Error checking sleep mode health: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/wake-events")
async def get_wake_events(limit: int = 50):
    """
    Get wake event log (SLEEP-012)

    Returns history of wake events with trigger types and durations.

    Args:
        limit: Maximum number of events to return (default: 50, max: 100)
    """
    try:
        sleep_service = SleepModeService.get_instance()

        # Limit to max 100
        limit = min(limit, 100)

        wake_events = sleep_service.get_wake_event_log(limit=limit)

        return {
            "success": True,
            "data": {
                "wake_events": wake_events,
                "count": len(wake_events),
                "total_wake_count": sleep_service.wake_count
            }
        }

    except Exception as e:
        logger.error(f"Error getting wake events: {e}")
        raise HTTPException(status_code=500, detail=str(e))
