import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta
from services.goals_service import GoalsService
from database.models import PostingGoal

@pytest.mark.asyncio
async def test_create_goal():
    mock_db = AsyncMock()
    service = GoalsService(mock_db)
    
    user_id = uuid4()
    goal_data = {
        "goal_type": "performance",
        "goal_name": "Test Goal",
        "target_metrics": {"views": 1000},
        "priority": 1,
        "start_date": datetime.now(),
        "end_date": datetime.now() + timedelta(days=30)
    }
    
    # Mock db.add and db.commit
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    result = await service.create_goal(user_id, goal_data)
    
    assert result.goal_name == "Test Goal"
    assert result.user_id == user_id
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_goals():
    mock_db = AsyncMock()
    service = GoalsService(mock_db)
    user_id = uuid4()
    
    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        PostingGoal(id=uuid4(), user_id=user_id, goal_name="Goal 1"),
        PostingGoal(id=uuid4(), user_id=user_id, goal_name="Goal 2")
    ]
    mock_db.execute.return_value = mock_result
    
    goals = await service.get_user_goals(user_id)
    
    assert len(goals) == 2
    assert goals[0].goal_name == "Goal 1"

@pytest.mark.asyncio
async def test_update_goal():
    mock_db = AsyncMock()
    service = GoalsService(mock_db)
    goal_id = uuid4()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = PostingGoal(id=goal_id, goal_name="Updated Goal")
    mock_db.execute.return_value = mock_result
    
    result = await service.update_goal(goal_id, {"goal_name": "Updated Goal"})
    
    assert result.goal_name == "Updated Goal"
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_delete_goal():
    mock_db = AsyncMock()
    service = GoalsService(mock_db)
    goal_id = uuid4()
    
    await service.delete_goal(goal_id)
    
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
