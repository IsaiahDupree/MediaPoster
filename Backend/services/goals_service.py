from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import PostingGoal, PlatformPost, ContentPerformanceAnalytics
from database.connection import get_db
from loguru import logger

class GoalsService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_goal(self, user_id: UUID, goal_data: Dict[str, Any]) -> PostingGoal:
        """Create a new posting goal"""
        try:
            goal = PostingGoal(
                user_id=user_id,
                goal_type=goal_data['goal_type'],
                goal_name=goal_data['goal_name'],
                target_metrics=goal_data['target_metrics'],
                priority=goal_data.get('priority', 1),
                start_date=goal_data.get('start_date'),
                end_date=goal_data.get('end_date'),
                status='active'
            )
            self.db.add(goal)
            await self.db.commit()
            await self.db.refresh(goal)
            return goal
        except Exception as e:
            logger.error(f"Error creating goal: {e}")
            await self.db.rollback()
            raise

    async def get_user_goals(self, user_id: UUID, status: Optional[str] = None) -> List[PostingGoal]:
        """Get all goals for a user"""
        try:
            query = select(PostingGoal).where(PostingGoal.user_id == user_id)
            if status:
                query = query.where(PostingGoal.status == status)
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching user goals: {e}")
            raise

    async def update_goal(self, goal_id: UUID, update_data: Dict[str, Any]) -> Optional[PostingGoal]:
        """Update a goal"""
        try:
            query = update(PostingGoal).where(PostingGoal.id == goal_id).values(**update_data).returning(PostingGoal)
            result = await self.db.execute(query)
            await self.db.commit()
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error updating goal: {e}")
            await self.db.rollback()
            raise

    async def delete_goal(self, goal_id: UUID) -> bool:
        """Delete a goal"""
        try:
            query = delete(PostingGoal).where(PostingGoal.id == goal_id)
            await self.db.execute(query)
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting goal: {e}")
            await self.db.rollback()
            raise

    async def update_goal_progress(self, goal_id: UUID) -> Dict[str, Any]:
        """Calculate and update progress for a specific goal"""
        try:
            goal = await self.db.get(PostingGoal, goal_id)
            if not goal:
                raise ValueError("Goal not found")

            # Logic to calculate progress based on goal_type and target_metrics
            # This is a simplified placeholder. Real logic would involve complex queries
            # aggregating data from PlatformPost and ContentPerformanceAnalytics
            
            current_metrics = {}
            
            if goal.goal_type == 'performance':
                # Example: Sum of views for posts within goal timeframe
                # This would require joining PlatformPost and ContentPerformanceAnalytics
                pass
            
            # For now, return current state (which might be updated by a background job)
            return {
                "goal_id": str(goal.id),
                "status": goal.status,
                "target": goal.target_metrics,
                "current": current_metrics # Placeholder
            }

        except Exception as e:
            logger.error(f"Error updating goal progress: {e}")
            raise
