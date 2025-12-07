"""
Comprehensive Goal Lifecycle Tests
Tests complete goal management workflow with real database
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
import uuid
from datetime import datetime, timedelta

from main import app
from database.models import PostingGoal


@pytest.fixture
def client():
    return TestClient(app)


class TestGoalLifecycle:
    """Comprehensive goal lifecycle management"""
    
    @pytest.mark.asyncio
    async def test_goal_creation_and_progress_tracking(self, client, db_session, clean_db):
        """Test creating a goal and tracking its progress"""
        # Create goal
        payload = {
            "goal_type": "performance",
            "goal_name": "Grow Followers",
            "target_metrics": {"followers": 10000},
            "priority": 3,
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=30)).isoformat()
        }
        response = client.post("/api/goals/", json=payload)
        assert response.status_code in [200, 201]
        goal_data = response.json()
        goal_id = uuid.UUID(goal_data["id"])
        
        # Verify goal was created
        result = await db_session.execute(
            select(PostingGoal).where(PostingGoal.id == goal_id)
        )
        goal = result.scalar_one_or_none()
        assert goal is not None
        assert goal.goal_name == "Grow Followers"
        assert goal.status == "active"
        
        # Update goal progress
        refresh_response = client.post(f"/api/goals/{goal_id}/refresh-progress")
        assert refresh_response.status_code in [200, 201]
        
        # Update goal status
        update_response = client.patch(f"/api/goals/{goal_id}", json={
            "status": "completed"
        })
        assert update_response.status_code == 200
        updated_goal = update_response.json()
        assert updated_goal["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_multiple_goals_different_types(self, client, db_session, clean_db):
        """Test managing multiple goals of different types"""
        goal_types = ["performance", "campaign", "fulfillment"]
        created_goals = []
        
        for goal_type in goal_types:
            payload = {
                "goal_type": goal_type,
                "goal_name": f"Test {goal_type.title()} Goal",
                "target_metrics": {"metric": 1000},
                "priority": 2
            }
            response = client.post("/api/goals/", json=payload)
            assert response.status_code in [200, 201]
            created_goals.append(uuid.UUID(response.json()["id"]))
        
        # Verify all goals exist
        response = client.get("/api/goals/")
        assert response.status_code == 200
        goals = response.json()
        assert len(goals) >= 3
        
        # Verify each goal type
        for goal_id in created_goals:
            result = await db_session.execute(
                select(PostingGoal).where(PostingGoal.id == goal_id)
            )
            goal = result.scalar_one_or_none()
            assert goal is not None
            assert goal.goal_type in goal_types
    
    @pytest.mark.asyncio
    async def test_goal_priority_ordering(self, client, db_session, clean_db):
        """Test that goals can be ordered by priority"""
        priorities = [1, 3, 5, 2, 4]
        for priority in priorities:
            payload = {
                "goal_type": "performance",
                "goal_name": f"Priority {priority} Goal",
                "target_metrics": {"metric": 100},
                "priority": priority
            }
            response = client.post("/api/goals/", json=payload)
            assert response.status_code in [200, 201]
        
        # Get all goals
        response = client.get("/api/goals/")
        assert response.status_code == 200
        goals = response.json()
        assert len(goals) >= 5
        
        # Verify priorities are set correctly
        priorities_set = {g["priority"] for g in goals if g["goal_name"].startswith("Priority")}
        assert priorities_set == set(priorities)






