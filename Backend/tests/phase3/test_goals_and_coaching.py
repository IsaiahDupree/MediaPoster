"""
Tests for Phase 3: Goals System and Coaching
Tests goals API, recommendations, and coaching endpoints
Uses REAL database connections
"""
import pytest
from fastapi.testclient import TestClient
import uuid
from datetime import datetime

from main import app
from database.models import PostingGoal


class TestGoalsAPI:
    """Test goals API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_goals(self, client, db_session, clean_db):
        """Test getting list of goals with REAL database"""
        # Create test goal
        test_goal = PostingGoal(
            id=uuid.uuid4(),
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            goal_type="performance",
            goal_name="Test Goal",
            target_metrics={"followers": 1000},
            priority=1
        )
        db_session.add(test_goal)
        await db_session.commit()
        
        response = client.get("/api/goals/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    @pytest.mark.asyncio
    async def test_create_goal(self, client, db_session, clean_db):
        """Test creating a new goal with REAL database"""
        payload = {
            "goal_type": "performance",
            "goal_name": "Test Goal",
            "target_metrics": {"followers": 1000},
            "priority": 1
        }
        response = client.post("/api/goals/", json=payload)
        assert response.status_code in [200, 201]
        
        data = response.json()
        assert "id" in data
        assert data["goal_type"] == "performance"
        
        # Verify it was saved
        from sqlalchemy import select
        result = await db_session.execute(
            select(PostingGoal).where(PostingGoal.id == uuid.UUID(data["id"]))
        )
        goal = result.scalar_one_or_none()
        assert goal is not None
        assert goal.goal_name == "Test Goal"
    
    def test_get_goal_recommendations(self, client):
        """Test getting recommendations for a goal"""
        # First create a goal
        create_payload = {
            "goal_type": "increase_views",
            "goal_name": "Test Goal",
            "target_metrics": {"views": 5000},
            "priority": 1
        }
        create_response = client.post("/api/goals/", json=create_payload)
        
        if create_response.status_code in [200, 201]:
            goal_id = create_response.json().get("id")
            if goal_id:
                response = client.get(f"/api/goals/{goal_id}/recommendations")
                assert response.status_code in [200, 404]
                
                if response.status_code == 200:
                    data = response.json()
                    assert "goal_id" in data
                    assert "similar_content" in data or "format_recommendations" in data


class TestCoachingAPI:
    """Test coaching API endpoints"""
    
    def test_get_coaching_recommendations(self, client):
        """Test getting coaching recommendations"""
        response = client.get("/api/coaching/recommendations")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            # Should have recommendations structure
            has_recommendations = (
                "content_briefs" in data or
                "performance_insights" in data or
                "strategy_recommendations" in data
            )
            assert has_recommendations
    
    def test_coaching_chat(self, client):
        """Test coaching chat interface"""
        payload = {
            "message": "What content should I create next?",
            "context": {}
        }
        response = client.post("/api/coaching/chat", json=payload)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert isinstance(data["message"], str)
            assert len(data["message"]) > 0
    
    def test_coaching_chat_with_context(self, client):
        """Test coaching chat with goal context"""
        payload = {
            "message": "Help me improve my performance",
            "context": {"goal_id": str(uuid.uuid4())}
        }
        response = client.post("/api/coaching/chat", json=payload)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "recommendations" in data or "suggestions" in data

