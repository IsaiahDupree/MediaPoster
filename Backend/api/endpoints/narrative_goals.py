"""
Narrative Goals API
===================
API endpoints for managing narrative goals and pillars.

NAR-001: Narrative Goals System
NAR-002: Narrative Pillars System
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from loguru import logger

from services.narrative_goals_service import get_narrative_goals_service


router = APIRouter(prefix="/api/narrative", tags=["Narrative Goals"])


# Pydantic models for request/response
class CreateGoalRequest(BaseModel):
    workspace_id: str
    goal_statement: str
    primary_cta: str
    target_audience: Optional[str] = None
    time_horizon: str = "next_7_days"
    target_followers: Optional[int] = None
    target_engagement_rate: Optional[float] = None
    target_conversions: Optional[int] = None


class CreatePillarRequest(BaseModel):
    goal_id: str
    name: str
    pillar_type: str
    target_percentage: float
    description: Optional[str] = None
    color: Optional[str] = None
    keywords: Optional[List[str]] = None
    min_posts_per_week: Optional[int] = None
    max_posts_per_week: Optional[int] = None
    priority: int = 5


class CreateConstraintsRequest(BaseModel):
    goal_id: str
    enabled_platforms: Optional[List[str]] = None
    max_posts_per_day: int = 3
    min_posts_per_day: int = 1
    posting_windows: Optional[Dict[str, Any]] = None
    blackout_dates: Optional[List[str]] = None
    timezone: str = "America/New_York"
    min_pre_social_score: int = 60
    require_analysis: bool = True
    max_same_pillar_consecutive: int = 2


@router.post("/goals")
async def create_goal(request: CreateGoalRequest) -> Dict[str, Any]:
    """
    Create a new narrative goal

    A narrative goal defines the overarching story the creator wants to tell.

    Example:
    ```json
    {
      "workspace_id": "abc123",
      "goal_statement": "Position myself as the go-to expert for DIY electronics",
      "primary_cta": "Waitlist",
      "target_audience": "Beginner makers aged 25-45",
      "time_horizon": "next_7_days",
      "target_followers": 1000,
      "target_engagement_rate": 5.0,
      "target_conversions": 50
    }
    ```

    Returns:
        Created goal with ID and timestamps
    """
    try:
        service = get_narrative_goals_service()

        goal = await service.create_goal(
            workspace_id=request.workspace_id,
            goal_statement=request.goal_statement,
            primary_cta=request.primary_cta,
            target_audience=request.target_audience,
            time_horizon=request.time_horizon,
            target_followers=request.target_followers,
            target_engagement_rate=request.target_engagement_rate,
            target_conversions=request.target_conversions
        )

        return {
            "success": True,
            "goal": goal
        }

    except Exception as e:
        logger.error(f"Error creating narrative goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goals/{goal_id}")
async def get_goal(goal_id: str) -> Dict[str, Any]:
    """
    Get a narrative goal by ID

    Returns the goal details including all metadata.
    """
    try:
        service = get_narrative_goals_service()
        goal = await service.get_goal(goal_id)

        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        return {
            "success": True,
            "goal": goal
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pillars")
async def create_pillar(request: CreatePillarRequest) -> Dict[str, Any]:
    """
    Create a narrative pillar for a goal

    Pillars are content themes that support the narrative goal.

    Example:
    ```json
    {
      "goal_id": "abc123",
      "name": "Pain Points",
      "pillar_type": "value",
      "target_percentage": 20.0,
      "description": "Address audience struggles",
      "color": "#FF6B6B",
      "keywords": ["problem", "struggle", "challenge"],
      "min_posts_per_week": 1,
      "max_posts_per_week": 3,
      "priority": 8
    }
    ```

    Returns:
        Created pillar with ID and timestamps
    """
    try:
        service = get_narrative_goals_service()

        pillar = await service.create_pillar(
            goal_id=request.goal_id,
            name=request.name,
            pillar_type=request.pillar_type,
            target_percentage=request.target_percentage,
            description=request.description,
            color=request.color,
            keywords=request.keywords,
            min_posts_per_week=request.min_posts_per_week,
            max_posts_per_week=request.max_posts_per_week,
            priority=request.priority
        )

        return {
            "success": True,
            "pillar": pillar
        }

    except Exception as e:
        logger.error(f"Error creating pillar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goals/{goal_id}/pillars")
async def get_pillars_for_goal(goal_id: str) -> Dict[str, Any]:
    """
    Get all pillars for a goal

    Returns pillars sorted by priority (descending) and target percentage.
    """
    try:
        service = get_narrative_goals_service()
        pillars = await service.get_pillars_for_goal(goal_id)

        return {
            "success": True,
            "goal_id": goal_id,
            "pillars": pillars,
            "count": len(pillars)
        }

    except Exception as e:
        logger.error(f"Error getting pillars: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/goals/{goal_id}/default-pillars")
async def create_default_pillars(goal_id: str) -> Dict[str, Any]:
    """
    Create default narrative pillars for a goal

    Creates the standard content mix:
    - 20% Pain Points (Value)
    - 15% Social Proof (Proof)
    - 25% Process/How-To (Value)
    - 15% Personality (Value)
    - 10% Product/Service (CTA)
    - 10% Promotion/CTA (CTA)
    - 5% Education (Value)

    Returns:
        List of created pillars
    """
    try:
        service = get_narrative_goals_service()

        # Verify goal exists
        goal = await service.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        # Create default pillars
        pillars = await service.create_default_pillars(goal_id)

        return {
            "success": True,
            "goal_id": goal_id,
            "pillars": pillars,
            "count": len(pillars)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating default pillars: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/constraints")
async def create_constraints(request: CreateConstraintsRequest) -> Dict[str, Any]:
    """
    Create scheduling constraints for a goal (NAR-003)

    Constraints define:
    - Which platforms to post on
    - How many posts per day (min/max)
    - Time windows for posting
    - Blackout dates
    - Content quality requirements

    Example:
    ```json
    {
      "goal_id": "abc123",
      "enabled_platforms": ["tiktok", "instagram", "youtube"],
      "max_posts_per_day": 3,
      "min_posts_per_day": 1,
      "posting_windows": {
        "morning": "08:00-12:00",
        "evening": "18:00-21:00"
      },
      "blackout_dates": ["2026-12-25", "2026-01-01"],
      "timezone": "America/Los_Angeles",
      "min_pre_social_score": 70,
      "require_analysis": true,
      "max_same_pillar_consecutive": 2
    }
    ```

    Returns:
        Created constraints with ID
    """
    try:
        service = get_narrative_goals_service()

        constraints = await service.create_constraints(
            goal_id=request.goal_id,
            enabled_platforms=request.enabled_platforms,
            max_posts_per_day=request.max_posts_per_day,
            min_posts_per_day=request.min_posts_per_day,
            posting_windows=request.posting_windows,
            blackout_dates=request.blackout_dates,
            timezone=request.timezone,
            min_pre_social_score=request.min_pre_social_score,
            require_analysis=request.require_analysis,
            max_same_pillar_consecutive=request.max_same_pillar_consecutive
        )

        return {
            "success": True,
            "constraints": constraints
        }

    except Exception as e:
        logger.error(f"Error creating constraints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goals/{goal_id}/constraints")
async def get_constraints_for_goal(goal_id: str) -> Dict[str, Any]:
    """
    Get scheduling constraints for a goal

    Returns the most recent constraints for the specified goal.
    """
    try:
        service = get_narrative_goals_service()
        constraints = await service.get_constraints_for_goal(goal_id)

        if not constraints:
            return {
                "success": True,
                "goal_id": goal_id,
                "constraints": None,
                "message": "No constraints found for this goal"
            }

        return {
            "success": True,
            "goal_id": goal_id,
            "constraints": constraints
        }

    except Exception as e:
        logger.error(f"Error getting constraints: {e}")
        raise HTTPException(status_code=500, detail=str(e))
