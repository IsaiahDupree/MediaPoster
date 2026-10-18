"""
Smart Scheduling API Endpoints (PIPE-006)
==========================================
REST API for intelligent content scheduling
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from services.smart_scheduler import get_smart_scheduler
from loguru import logger


router = APIRouter(prefix="/api/schedule/smart", tags=["Smart Scheduling"])


class ScheduleRequest(BaseModel):
    """Request to schedule approved posts"""
    days: int = Field(default=7, ge=1, le=30, description="Number of days to schedule into")
    max_posts: Optional[int] = Field(default=None, ge=1, description="Maximum posts to schedule")
    platforms: Optional[List[str]] = Field(default=None, description="Filter by platforms")


class TimeSlotResponse(BaseModel):
    """Available time slot information"""
    datetime_utc: str
    datetime_local: str
    is_available: bool
    reason: Optional[str] = None


class SchedulePreviewResponse(BaseModel):
    """Schedule preview for upcoming days"""
    period: dict
    slots: dict
    schedule: dict
    daily_breakdown: dict
    next_available_slots: List[dict]


@router.post("/auto-schedule")
async def auto_schedule_posts(request: ScheduleRequest):
    """
    Automatically schedule approved posts into optimal time slots

    - **days**: Number of days to schedule into (1-30)
    - **max_posts**: Maximum number of posts to schedule (optional)
    - **platforms**: Filter posts by specific platforms (optional)

    Returns list of scheduled posts with their assigned times.
    """
    try:
        scheduler = get_smart_scheduler()
        scheduled = await scheduler.schedule_approved_posts(
            days=request.days,
            max_posts=request.max_posts,
            platforms=request.platforms
        )

        return {
            "success": True,
            "scheduled_count": len(scheduled),
            "scheduled_posts": scheduled,
            "message": f"Successfully scheduled {len(scheduled)} posts"
        }

    except Exception as e:
        logger.error(f"Auto-schedule failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")


@router.get("/available-slots")
async def get_available_slots(
    days: int = Query(default=7, ge=1, le=30, description="Days to look ahead")
):
    """
    Get list of available time slots for the next N days

    Returns all potential posting times with their availability status.
    """
    try:
        scheduler = get_smart_scheduler()
        slots = await scheduler.get_available_slots(days=days)

        # Convert to response format
        slot_data = []
        for slot in slots:
            slot_data.append({
                "datetime_utc": slot.datetime.isoformat(),
                "datetime_local": slot.datetime.astimezone(scheduler.timezone).strftime('%Y-%m-%d %I:%M %p %Z'),
                "is_available": slot.is_available,
                "reason": slot.reason
            })

        return {
            "success": True,
            "total_slots": len(slot_data),
            "available_slots": sum(1 for s in slots if s.is_available),
            "filled_slots": sum(1 for s in slots if not s.is_available),
            "slots": slot_data
        }

    except Exception as e:
        logger.error(f"Failed to get available slots: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get slots: {str(e)}")


@router.get("/preview")
async def get_schedule_preview(
    days: int = Query(default=7, ge=1, le=30, description="Days to preview")
):
    """
    Get a preview of the scheduling landscape

    Shows statistics, daily breakdown, and next available slots.
    """
    try:
        scheduler = get_smart_scheduler()
        preview = await scheduler.get_schedule_preview(days=days)

        return {
            "success": True,
            **preview
        }

    except Exception as e:
        logger.error(f"Failed to get schedule preview: {e}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.get("/next-slots")
async def get_next_slots(
    count: int = Query(default=10, ge=1, le=100, description="Number of slots to return")
):
    """
    Get the next N available time slots

    Useful for quick scheduling decisions.
    """
    try:
        scheduler = get_smart_scheduler()
        slots = scheduler.get_next_n_slots(n=count)

        slot_data = [
            {
                "datetime_utc": slot.isoformat(),
                "datetime_local": slot.astimezone(scheduler.timezone).strftime('%Y-%m-%d %I:%M %p %Z')
            }
            for slot in slots
        ]

        return {
            "success": True,
            "count": len(slot_data),
            "timezone": str(scheduler.timezone),
            "interval_hours": scheduler.interval_hours,
            "active_hours": f"{scheduler.active_start_hour:02d}:00-{scheduler.active_end_hour:02d}:00",
            "slots": slot_data
        }

    except Exception as e:
        logger.error(f"Failed to get next slots: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get slots: {str(e)}")


@router.get("/config")
async def get_scheduler_config():
    """
    Get current scheduler configuration
    """
    scheduler = get_smart_scheduler()

    return {
        "success": True,
        "config": {
            "timezone": str(scheduler.timezone),
            "active_start_hour": scheduler.active_start_hour,
            "active_end_hour": scheduler.active_end_hour,
            "interval_hours": scheduler.interval_hours,
            "active_hours_display": f"{scheduler.active_start_hour:02d}:00-{scheduler.active_end_hour:02d}:00"
        }
    }
