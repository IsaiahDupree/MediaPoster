"""
Optimal Posting Times API Endpoints
Phase 4: Publishing & Scheduling
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from database.connection import get_db
from services.optimal_posting_times import OptimalPostingTimesService
from loguru import logger

router = APIRouter(prefix="/api/optimal-posting-times", tags=["Optimal Posting Times"])


class RecommendedTimeResponse(BaseModel):
    """Response for recommended posting time"""
    recommended_time: datetime
    platform: str
    score: float
    reasoning: str


@router.get("/platform/{platform}")
async def get_optimal_times_for_platform(
    platform: str,
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    days_back: int = Query(90, ge=7, le=365, description="Days of historical data to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get optimal posting times for a platform
    
    Returns best hours and days based on historical performance
    """
    try:
        service = OptimalPostingTimesService()
        optimal = await service.get_optimal_times(
            db=db,
            platform=platform,
            account_id=account_id,
            days_back=days_back
        )
        
        return optimal
        
    except Exception as e:
        logger.error(f"Error getting optimal posting times: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend")
async def get_recommended_time(
    platform: str,
    preferred_date: datetime,
    account_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommended posting time for a specific date and platform
    """
    try:
        service = OptimalPostingTimesService()
        recommended = await service.get_recommended_time(
            db=db,
            platform=platform,
            preferred_date=preferred_date,
            account_id=account_id
        )
        
        # Get optimal times for score calculation
        optimal = await service.get_optimal_times(db, platform, account_id)
        hour = recommended.hour
        day = recommended.weekday()
        
        hour_score = optimal['all_hour_scores'].get(hour, 0.5)
        day_score = optimal['all_day_scores'].get(day, 0.5)
        overall_score = (hour_score + day_score) / 2
        
        reasoning = f"Best time based on historical performance: {hour_score:.1%} hour score, {day_score:.1%} day score"
        if optimal.get('is_default'):
            reasoning += " (using platform defaults - no historical data available)"
        
        return RecommendedTimeResponse(
            recommended_time=recommended,
            platform=platform,
            score=overall_score,
            reasoning=reasoning
        )
        
    except Exception as e:
        logger.error(f"Error getting recommended time: {e}")
        raise HTTPException(status_code=500, detail=str(e))






