"""
Posting Optimizer API Endpoints
Best time to post recommendations based on historical engagement
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from loguru import logger

from services.instagram.posting_optimizer import get_posting_optimizer

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class BestTimeResponse(BaseModel):
    hour: int
    time_display: str
    score: float
    engagement_rate: float
    best_days: List[str]
    recommendation: str


class HourlyPerformanceResponse(BaseModel):
    hour: int
    time_display: str
    engagement_rate: float
    relative_score: float


class DailyPerformanceResponse(BaseModel):
    day: str
    day_number: int
    engagement_rate: float
    relative_score: float


class ScheduleSlotResponse(BaseModel):
    day: str
    hour: int
    time_display: str
    score: float
    recommendation: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/best-times")
async def get_best_times(
    profile_id: Optional[str] = Query(None, description="Instagram profile ID"),
    content_type: str = Query("REEL", description="Content type: REEL, IMAGE, CAROUSEL"),
    timezone: str = Query("UTC", description="Timezone for results"),
    top_n: int = Query(5, ge=1, le=10, description="Number of time slots")
):
    """
    Get best times to post based on historical engagement.
    
    Returns top N optimal posting times with engagement scores.
    """
    try:
        optimizer = get_posting_optimizer()
        best_times = optimizer.get_best_times(profile_id, content_type, timezone, top_n)
        
        return {
            "profile_id": profile_id,
            "content_type": content_type,
            "timezone": timezone,
            "count": len(best_times),
            "best_times": [BestTimeResponse(**time) for time in best_times]
        }
    except Exception as e:
        logger.error(f"Failed to get best times: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/hourly")
async def get_hourly_performance(
    profile_id: Optional[str] = Query(None, description="Instagram profile ID"),
    content_type: str = Query("REEL", description="Content type")
):
    """
    Get detailed performance metrics for each hour of the day.
    
    Returns 24-hour breakdown with engagement rates.
    """
    try:
        optimizer = get_posting_optimizer()
        performance = optimizer.get_performance_by_hour(profile_id, content_type)
        
        return {
            "profile_id": profile_id,
            "content_type": content_type,
            "hours": [HourlyPerformanceResponse(**hour) for hour in performance]
        }
    except Exception as e:
        logger.error(f"Failed to get hourly performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/daily")
async def get_daily_performance(
    profile_id: Optional[str] = Query(None, description="Instagram profile ID"),
    content_type: str = Query("REEL", description="Content type")
):
    """
    Get detailed performance metrics for each day of the week.
    
    Returns 7-day breakdown with engagement rates.
    """
    try:
        optimizer = get_posting_optimizer()
        performance = optimizer.get_performance_by_day(profile_id, content_type)
        
        return {
            "profile_id": profile_id,
            "content_type": content_type,
            "days": [DailyPerformanceResponse(**day) for day in performance]
        }
    except Exception as e:
        logger.error(f"Failed to get daily performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule/suggest")
async def suggest_posting_schedule(
    posts_per_week: int = Query(7, ge=1, le=14, description="Posts per week"),
    profile_id: Optional[str] = Query(None, description="Instagram profile ID"),
    content_type: str = Query("REEL", description="Content type")
):
    """
    Generate a complete posting schedule for the week.
    
    Returns optimized schedule with day/time recommendations.
    """
    try:
        optimizer = get_posting_optimizer()
        schedule = optimizer.suggest_posting_schedule(posts_per_week, profile_id, content_type)
        
        return {
            "posts_per_week": posts_per_week,
            "profile_id": profile_id,
            "content_type": content_type,
            "schedule": [ScheduleSlotResponse(**slot) for slot in schedule]
        }
    except Exception as e:
        logger.error(f"Failed to suggest schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
