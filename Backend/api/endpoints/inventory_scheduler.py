"""
Inventory-Aware Scheduler API Endpoints
Manages automatic scheduling based on inventory
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid

from database.connection import get_db, async_session_maker
from services.inventory_aware_scheduler import (
    InventoryAwareScheduler,
    SchedulerConfig,
    ContentInventory
)

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


# ==================== Request Models ====================

class SchedulerConfigRequest(BaseModel):
    """Request model for scheduler configuration"""
    horizon_months: Optional[int] = 2
    min_posts_per_day_short: Optional[float] = 1.0
    max_posts_per_day_short: Optional[float] = 3.0
    min_posts_per_day_long: Optional[float] = 0.2
    max_posts_per_day_long: Optional[float] = 1.0
    short_form_duration_max: Optional[float] = 60.0
    long_form_duration_min: Optional[float] = 60.0
    preferred_posting_times: Optional[list[int]] = None
    platforms: Optional[list[str]] = None


class AutoScheduleRequest(BaseModel):
    """Request model for auto-scheduling"""
    force_reschedule: Optional[bool] = False
    config: Optional[SchedulerConfigRequest] = None


# ==================== Endpoints ====================

@router.get("/inventory")
async def get_inventory(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current content inventory
    """
    try:
        scheduler = InventoryAwareScheduler()
        user_uuid = uuid.UUID(user_id) if user_id else None
        inventory = await scheduler.get_available_inventory(user_uuid)
        
        return {
            "short_form": {
                "count": inventory.short_form_count,
                "items": inventory.short_form_items[:10]  # Limit to 10 for response
            },
            "long_form": {
                "count": inventory.long_form_count,
                "items": inventory.long_form_items[:10]
            },
            "total": inventory.total_count
        }
    except Exception as e:
        from loguru import logger
        logger.error(f"Error getting inventory: {e}")
        return {
            "short_form": {"count": 0, "items": []},
            "long_form": {"count": 0, "items": []},
            "total": 0
        }


@router.get("/plan")
async def get_schedule_plan(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get optimal schedule plan based on current inventory
    """
    try:
        scheduler = InventoryAwareScheduler()
        user_uuid = uuid.UUID(user_id) if user_id else None
        inventory = await scheduler.get_available_inventory(user_uuid)
        plan = scheduler.calculate_optimal_schedule(inventory)
        
        return {
            "posts_per_day_short": plan.posts_per_day_short,
            "posts_per_day_long": plan.posts_per_day_long,
            "total_days": plan.total_days,
            "total_posts_short": plan.total_posts_short,
            "total_posts_long": plan.total_posts_long,
            "schedule_start": plan.schedule_start.isoformat(),
            "schedule_end": plan.schedule_end.isoformat(),
            "can_extend_horizon": plan.can_extend_horizon
        }
    except Exception as e:
        from loguru import logger
        logger.error(f"Error getting schedule plan: {e}")
        return {
            "posts_per_day_short": 0.0,
            "posts_per_day_long": 0.0,
            "total_days": 0,
            "total_posts_short": 0,
            "total_posts_long": 0,
            "schedule_start": None,
            "schedule_end": None,
            "can_extend_horizon": False
        }


@router.post("/auto-schedule")
async def auto_schedule(
    request: AutoScheduleRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None
):
    """
    Automatically schedule content based on inventory
    """
    try:
        # Create scheduler with custom config if provided
        config = None
        if request.config:
            config = SchedulerConfig(
                horizon_months=request.config.horizon_months or 2,
                min_posts_per_day_short=request.config.min_posts_per_day_short or 1.0,
                max_posts_per_day_short=request.config.max_posts_per_day_short or 3.0,
                min_posts_per_day_long=request.config.min_posts_per_day_long or 0.2,
                max_posts_per_day_long=request.config.max_posts_per_day_long or 1.0,
                short_form_duration_max=request.config.short_form_duration_max or 60.0,
                long_form_duration_min=request.config.long_form_duration_min or 60.0,
                preferred_posting_times=request.config.preferred_posting_times,
                platforms=request.config.platforms
            )
        
        scheduler = InventoryAwareScheduler(config)
        user_uuid = uuid.UUID(user_id) if user_id else None
        
        result = await scheduler.auto_schedule(
            user_id=user_uuid,
            force_reschedule=request.force_reschedule
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-on-new-content")
async def update_on_new_content(
    user_id: Optional[str] = None
):
    """
    Update schedule when new content is added to resource folder
    """
    try:
        scheduler = InventoryAwareScheduler()
        user_uuid = uuid.UUID(user_id) if user_id else None
        
        result = await scheduler.update_schedule_on_new_content(user_uuid)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_scheduler_status(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current scheduler status and statistics
    """
    try:
        scheduler = InventoryAwareScheduler()
        user_uuid = uuid.UUID(user_id) if user_id else None
        
        # Get inventory
        inventory = await scheduler.get_available_inventory(user_uuid)
        
        # Get schedule plan
        plan = scheduler.calculate_optimal_schedule(inventory)
        
        # Get existing scheduled posts count
        from database.models import ScheduledPost
        from sqlalchemy import select, func
        
        scheduled_count_query = select(func.count(ScheduledPost.id)).where(
            ScheduledPost.status == 'scheduled'
        )
        scheduled_result = await db.execute(scheduled_count_query)
        scheduled_count = scheduled_result.scalar() or 0
        
        return {
            "inventory": {
                "short_form": inventory.short_form_count,
                "long_form": inventory.long_form_count,
                "total": inventory.total_count
            },
            "plan": {
                "posts_per_day_short": plan.posts_per_day_short,
                "posts_per_day_long": plan.posts_per_day_long,
                "total_days": plan.total_days,
                "schedule_end": plan.schedule_end.isoformat()
            },
            "scheduled_count": scheduled_count,
            "config": {
                "horizon_months": scheduler.config.horizon_months,
                "platforms": scheduler.config.platforms
            }
        }
    except Exception as e:
        from loguru import logger
        logger.error(f"Error getting scheduler status: {e}")
        return {
            "inventory": {
                "short_form": 0,
                "long_form": 0,
                "total": 0
            },
            "plan": {
                "posts_per_day_short": 0.0,
                "posts_per_day_long": 0.0,
                "total_days": 0,
                "schedule_end": None
            },
            "scheduled_count": 0,
            "config": {
                "horizon_months": 2,
                "platforms": []
            },
            "status": "error",
            "error": str(e)
        }

