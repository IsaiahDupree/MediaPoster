"""
Goal-Based Recommendations API Endpoints
Phase 3: Pre/Post Social Score + Coaching
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
from pydantic import BaseModel
import uuid

from database.connection import get_db
from database.models import PostingGoal
from services.goal_recommendations import GoalRecommendationsService
from loguru import logger

router = APIRouter(prefix="/api/goals", tags=["Goal Recommendations"])


@router.get("/{goal_id}/recommendations")
async def get_goal_recommendations(
    goal_id: str,
    limit: int = Query(5, le=20),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommendations for a specific goal
    
    Returns:
    - Similar high-performing content ("Post 3 more videos like these")
    - Format recommendations ("Try 9:16 + talking head")
    - Content strategy recommendations
    """
    try:
        # Get goal
        result = await db.execute(
            select(PostingGoal).where(PostingGoal.id == uuid.UUID(goal_id))
        )
        # Convert to list to ensure generator is fully consumed
        goals = list(result.scalars().all())
        goal = goals[0] if goals else None
        
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Get recommendations
        service = GoalRecommendationsService()
        recommendations = await service.get_recommendations_for_goal(
            db=db,
            goal_id=goal_id,
            goal_type=goal.goal_type,
            target_metrics=goal.target_metrics if isinstance(goal.target_metrics, dict) else {},
            limit=limit
        )
        
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting goal recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

