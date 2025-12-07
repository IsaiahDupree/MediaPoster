from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, UUID4
from datetime import datetime

from database.connection import get_db
from services.goals_service import GoalsService

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
    id: UUID4
    user_id: UUID4
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
    return await service.create_goal(user_id, goal.dict())

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
    goal_id: UUID4,
    goal_update: GoalUpdate,
    db: AsyncSession = Depends(get_db)
):
    service = GoalsService(db)
    updated_goal = await service.update_goal(goal_id, goal_update.dict(exclude_unset=True))
    if not updated_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return updated_goal

@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: UUID4,
    db: AsyncSession = Depends(get_db)
):
    service = GoalsService(db)
    await service.delete_goal(goal_id)
    return {"message": "Goal deleted"}

@router.post("/{goal_id}/refresh-progress")
async def refresh_goal_progress(
    goal_id: UUID4,
    db: AsyncSession = Depends(get_db)
):
    service = GoalsService(db)
    return await service.update_goal_progress(goal_id)
