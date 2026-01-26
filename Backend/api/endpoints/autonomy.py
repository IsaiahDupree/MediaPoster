"""
Autonomy API Endpoints
======================
API endpoints for autonomous content operations:
- Same-Day Adjustment (AUTO-007)
- Weekly Plan Generation (AUTO-008)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

router = APIRouter(prefix="/api/autonomy", tags=["Autonomy"])


# ===== REQUEST/RESPONSE MODELS =====

class GenerateWeeklyPlanRequest(BaseModel):
    """Request to generate a weekly plan"""
    start_date: Optional[str] = Field(None, description="Start date (ISO format, defaults to next Monday)")
    posts_per_day: Optional[int] = Field(2, description="Posts per day")
    platforms: Optional[List[str]] = Field(["tiktok", "instagram"], description="Platforms to schedule for")
    learning_window_days: Optional[int] = Field(30, description="Days to look back for learnings")


class AdjustmentThresholdsRequest(BaseModel):
    """Request to update same-day adjustment thresholds"""
    winner_multiplier: Optional[float] = Field(1.5, description="Multiplier for winner identification")
    loser_multiplier: Optional[float] = Field(0.6, description="Multiplier for loser identification")
    min_impressions: Optional[int] = Field(100, description="Minimum impressions to evaluate")


# ===== SAME-DAY ADJUSTER ENDPOINTS =====

@router.get("/same-day-adjuster/status")
async def get_same_day_adjuster_status():
    """Get same-day adjuster service status"""
    try:
        from services.same_day_adjuster import SameDayAdjuster

        adjuster = SameDayAdjuster.get_instance()
        status = adjuster.get_status()

        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting same-day adjuster status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/same-day-adjuster/check-now")
async def trigger_same_day_check():
    """Manually trigger a same-day adjustment check"""
    try:
        from services.same_day_adjuster import SameDayAdjuster

        adjuster = SameDayAdjuster.get_instance()

        # Trigger check
        await adjuster._check_and_adjust()

        return {
            "success": True,
            "message": "Same-day adjustment check triggered"
        }
    except Exception as e:
        logger.error(f"Error triggering same-day check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/same-day-adjuster/thresholds")
async def update_thresholds(request: AdjustmentThresholdsRequest):
    """Update same-day adjustment thresholds"""
    try:
        from services.same_day_adjuster import SameDayAdjuster, PerformanceThreshold

        adjuster = SameDayAdjuster.get_instance()

        # Update thresholds
        if request.winner_multiplier is not None:
            adjuster.thresholds.winner_multiplier = request.winner_multiplier
        if request.loser_multiplier is not None:
            adjuster.thresholds.loser_multiplier = request.loser_multiplier
        if request.min_impressions is not None:
            adjuster.thresholds.min_impressions = request.min_impressions

        return {
            "success": True,
            "message": "Thresholds updated",
            "data": {
                "winner_multiplier": adjuster.thresholds.winner_multiplier,
                "loser_multiplier": adjuster.thresholds.loser_multiplier,
                "min_impressions": adjuster.thresholds.min_impressions
            }
        }
    except Exception as e:
        logger.error(f"Error updating thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== WEEKLY PLANNER ENDPOINTS =====

@router.get("/weekly-planner/status")
async def get_weekly_planner_status():
    """Get weekly planner service status"""
    try:
        from services.weekly_planner import WeeklyPlanner

        planner = WeeklyPlanner.get_instance()
        status = planner.get_status()

        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting weekly planner status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/weekly-planner/generate")
async def generate_weekly_plan(request: GenerateWeeklyPlanRequest):
    """Generate a new weekly content plan"""
    try:
        from services.weekly_planner import WeeklyPlanner, WeeklyPlanConfig

        planner = WeeklyPlanner.get_instance()

        # Parse start date if provided
        start_date = None
        if request.start_date:
            start_date = datetime.fromisoformat(request.start_date)

        # Create config
        config = WeeklyPlanConfig(
            posts_per_day=request.posts_per_day,
            platforms=request.platforms,
            learning_window_days=request.learning_window_days
        )

        # Generate plan
        plan = await planner.generate_weekly_plan(
            start_date=start_date,
            config=config
        )

        if not plan:
            return {
                "success": False,
                "error": "Failed to generate plan (insufficient data?)"
            }

        return {
            "success": True,
            "data": {
                "plan_id": plan.id,
                "start_date": plan.start_date.isoformat(),
                "end_date": plan.end_date.isoformat(),
                "slot_count": len(plan.slots),
                "learnings_summary": {
                    "total_posts_analyzed": plan.learnings.get("total_posts", 0),
                    "top_templates": plan.learnings.get("top_templates", [])[:5],
                    "top_topics": plan.learnings.get("top_topics", [])[:5],
                    "best_posting_hours": plan.learnings.get("best_posting_hours", [])
                }
            }
        }
    except Exception as e:
        logger.error(f"Error generating weekly plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly-planner/plans")
async def get_weekly_plans(limit: int = 10):
    """Get recent weekly plans"""
    try:
        from services.weekly_planner import WeeklyPlanner
        import os
        from sqlalchemy import create_engine, text

        DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        )
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    id,
                    start_date,
                    end_date,
                    learnings,
                    metadata,
                    created_at,
                    (SELECT COUNT(*) FROM scheduled_posts WHERE weekly_plan_id = wp.id) as slot_count
                FROM weekly_plans wp
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": limit})

            plans = []
            for row in result:
                plans.append({
                    "id": row[0],
                    "start_date": row[1].isoformat() if row[1] else None,
                    "end_date": row[2].isoformat() if row[2] else None,
                    "learnings": row[3] if row[3] else {},
                    "metadata": row[4] if row[4] else {},
                    "created_at": row[5].isoformat() if row[5] else None,
                    "slot_count": row[6]
                })

            return {
                "success": True,
                "data": {
                    "plans": plans,
                    "count": len(plans)
                }
            }
    except Exception as e:
        logger.error(f"Error getting weekly plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly-planner/plans/{plan_id}")
async def get_weekly_plan(plan_id: str):
    """Get a specific weekly plan with slots"""
    try:
        import os
        from sqlalchemy import create_engine, text

        DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        )
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            # Get plan
            plan_result = conn.execute(text("""
                SELECT
                    id,
                    start_date,
                    end_date,
                    learnings,
                    metadata,
                    created_at
                FROM weekly_plans
                WHERE id = :plan_id
            """), {"plan_id": plan_id})

            plan_row = plan_result.fetchone()
            if not plan_row:
                raise HTTPException(status_code=404, detail="Plan not found")

            # Get slots
            slots_result = conn.execute(text("""
                SELECT
                    id,
                    scheduled_at,
                    platform,
                    template_id,
                    topic,
                    content_type,
                    awareness_level,
                    origin_type,
                    status
                FROM scheduled_posts
                WHERE weekly_plan_id = :plan_id
                ORDER BY scheduled_at ASC
            """), {"plan_id": plan_id})

            slots = []
            for row in slots_result:
                slots.append({
                    "id": str(row[0]),
                    "scheduled_at": row[1].isoformat() if row[1] else None,
                    "platform": row[2],
                    "template_id": str(row[3]) if row[3] else None,
                    "topic": row[4],
                    "content_type": row[5],
                    "awareness_level": row[6],
                    "origin_type": row[7],
                    "status": row[8]
                })

            return {
                "success": True,
                "data": {
                    "id": plan_row[0],
                    "start_date": plan_row[1].isoformat() if plan_row[1] else None,
                    "end_date": plan_row[2].isoformat() if plan_row[2] else None,
                    "learnings": plan_row[3] if plan_row[3] else {},
                    "metadata": plan_row[4] if plan_row[4] else {},
                    "created_at": plan_row[5].isoformat() if plan_row[5] else None,
                    "slots": slots,
                    "slot_count": len(slots)
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weekly plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== AUTONOMY OVERVIEW =====

@router.get("/status")
async def get_autonomy_status():
    """Get overall autonomy system status"""
    try:
        from services.same_day_adjuster import SameDayAdjuster
        from services.weekly_planner import WeeklyPlanner

        adjuster = SameDayAdjuster.get_instance()
        planner = WeeklyPlanner.get_instance()

        return {
            "success": True,
            "data": {
                "same_day_adjuster": adjuster.get_status(),
                "weekly_planner": planner.get_status(),
                "system_health": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Error getting autonomy status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
