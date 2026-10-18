from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
import logging

from database.connection import get_db
from services.goals_service import GoalsService
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/goals", tags=["Goals"])

class GoalCreate(BaseModel):
    goal_type: str
    goal_name: str
    target_metrics: dict
    priority: Optional[int] = 1
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class GoalUpdate(BaseModel):
    goal_name: Optional[str] = None
    target_metrics: Optional[dict] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    end_date: Optional[datetime] = None

class GoalResponse(BaseModel):
    id: UUID
    user_id: UUID
    goal_type: str
    goal_name: str
    target_metrics: dict
    priority: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

@router.post("/", response_model=GoalResponse)
async def create_goal(
    goal: GoalCreate,
    db: AsyncSession = Depends(get_db),
    # user_id: UUID4 = Depends(get_current_user_id) # TODO: Add auth
):
    # Mock user_id for now
    import uuid
    user_id = uuid.UUID('00000000-0000-0000-0000-000000000000') 
    
    service = GoalsService(db)
    result = await service.create_goal(user_id, goal.dict())
    
    # Emit GOAL_CREATED event
    try:
        event_bus = EventBus.get_instance()
        await event_bus.publish(Topics.GOAL_CREATED, {
            "goal_id": str(result.id),
            "goal_type": goal.goal_type,
            "goal_name": goal.goal_name,
            "target_metrics": goal.target_metrics,
        })
        logger.info(f"[PubSub] Emitted GOAL_CREATED for {result.id}")
    except Exception as e:
        logger.warning(f"[PubSub] Failed to emit GOAL_CREATED: {e}")
    
    return result

@router.get("/", response_model=List[GoalResponse])
async def get_goals(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    # Mock user_id for now
    import uuid
    user_id = uuid.UUID('00000000-0000-0000-0000-000000000000')
    
    service = GoalsService(db)
    return await service.get_user_goals(user_id, status)

@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: UUID,
    goal_update: GoalUpdate,
    db: AsyncSession = Depends(get_db)
):
    service = GoalsService(db)
    updated_goal = await service.update_goal(goal_id, goal_update.dict(exclude_unset=True))
    if not updated_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Emit GOAL_UPDATED event
    try:
        event_bus = EventBus.get_instance()
        topic = Topics.GOAL_COMPLETED if goal_update.status == "completed" else Topics.GOAL_UPDATED
        await event_bus.publish(topic, {
            "goal_id": str(goal_id),
            "status": goal_update.status,
            "updated_fields": list(goal_update.dict(exclude_unset=True).keys()),
        })
        logger.info(f"[PubSub] Emitted {topic} for {goal_id}")
    except Exception as e:
        logger.warning(f"[PubSub] Failed to emit goal event: {e}")
    
    return updated_goal

@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = GoalsService(db)
    await service.delete_goal(goal_id)
    return {"message": "Goal deleted"}

@router.post("/{goal_id}/refresh-progress")
async def refresh_goal_progress(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = GoalsService(db)
    return await service.update_goal_progress(goal_id)
