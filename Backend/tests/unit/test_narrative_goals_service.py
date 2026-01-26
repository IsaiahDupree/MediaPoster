"""
Unit Tests for Narrative Goals Service
=======================================
Tests for NAR-001, NAR-002, NAR-003
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from services.narrative_goals_service import NarrativeGoalsService, get_narrative_goals_service


@pytest.fixture
def mock_database():
    """Mock database connection"""
    with patch('services.narrative_goals_service.create_engine') as mock_engine:
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        yield mock_conn


@pytest.fixture
def mock_event_bus():
    """Mock event bus"""
    with patch('services.narrative_goals_service.EventBus') as mock_bus:
        mock_instance = MagicMock()
        mock_bus.get_instance.return_value = mock_instance
        yield mock_instance


class TestNarrativeGoalsService:
    """Test suite for NarrativeGoalsService"""

    def test_singleton_pattern(self):
        """Test that service follows singleton pattern"""
        service1 = get_narrative_goals_service()
        service2 = get_narrative_goals_service()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_create_goal(self, mock_database, mock_event_bus):
        """Test creating a narrative goal (NAR-001)"""
        # Setup mock
        goal_id = str(uuid4())
        created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = (goal_id, created_at)
        mock_database.execute.return_value = mock_result

        # Create service and goal
        service = get_narrative_goals_service()
        goal = await service.create_goal(
            workspace_id="workspace-123",
            goal_statement="Position myself as the go-to expert for DIY electronics",
            primary_cta="Waitlist",
            target_audience="Beginner makers aged 25-45"
        )

        # Assertions
        assert goal["id"] == goal_id
        assert goal["workspace_id"] == "workspace-123"
        assert goal["goal_statement"] == "Position myself as the go-to expert for DIY electronics"
        assert goal["primary_cta"] == "Waitlist"
        assert goal["target_audience"] == "Beginner makers aged 25-45"
        assert goal["status"] == "active"

        # Verify database call was made
        assert mock_database.execute.called
        assert mock_database.commit.called

        # Verify event was published
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_create_goal_with_metrics(self, mock_database, mock_event_bus):
        """Test creating a goal with success metrics"""
        goal_id = str(uuid4())
        created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = (goal_id, created_at)
        mock_database.execute.return_value = mock_result

        service = get_narrative_goals_service()
        goal = await service.create_goal(
            workspace_id="workspace-123",
            goal_statement="Build authentic lifestyle brand",
            primary_cta="Follow",
            target_followers=10000,
            target_engagement_rate=5.0,
            target_conversions=100
        )

        assert goal["target_followers"] == 10000
        assert goal["target_engagement_rate"] == 5.0
        assert goal["target_conversions"] == 100

    @pytest.mark.asyncio
    async def test_create_pillar(self, mock_database, mock_event_bus):
        """Test creating a narrative pillar (NAR-002)"""
        pillar_id = str(uuid4())
        goal_id = str(uuid4())
        created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = (pillar_id, created_at)
        mock_database.execute.return_value = mock_result

        service = get_narrative_goals_service()
        pillar = await service.create_pillar(
            goal_id=goal_id,
            name="Pain Points",
            pillar_type="value",
            target_percentage=20.0,
            description="Address audience struggles",
            color="#FF6B6B",
            keywords=["problem", "struggle", "challenge"],
            min_posts_per_week=1,
            max_posts_per_week=3,
            priority=8
        )

        # Assertions
        assert pillar["id"] == pillar_id
        assert pillar["goal_id"] == goal_id
        assert pillar["name"] == "Pain Points"
        assert pillar["pillar_type"] == "value"
        assert pillar["target_percentage"] == 20.0
        assert pillar["description"] == "Address audience struggles"
        assert pillar["color"] == "#FF6B6B"
        assert pillar["keywords"] == ["problem", "struggle", "challenge"]
        assert pillar["min_posts_per_week"] == 1
        assert pillar["max_posts_per_week"] == 3
        assert pillar["priority"] == 8
        assert pillar["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_default_pillars(self, mock_database, mock_event_bus):
        """Test creating default narrative pillars"""
        goal_id = str(uuid4())

        # Mock fetchone to return different IDs for each pillar
        call_count = [0]

        def mock_fetchone():
            call_count[0] += 1
            return (str(uuid4()), datetime.now())

        mock_result = MagicMock()
        mock_result.fetchone = mock_fetchone
        mock_database.execute.return_value = mock_result

        service = get_narrative_goals_service()
        pillars = await service.create_default_pillars(goal_id)

        # Should create 7 default pillars
        assert len(pillars) == 7

        # Verify pillar names
        pillar_names = [p["name"] for p in pillars]
        expected_names = [
            "Pain Points",
            "Social Proof",
            "Process/How-To",
            "Personality",
            "Product/Service",
            "Promotion/CTA",
            "Education"
        ]
        assert pillar_names == expected_names

        # Verify total percentage adds up to 100%
        total_percentage = sum(p["target_percentage"] for p in pillars)
        assert total_percentage == 100.0

        # Verify pillar types
        value_pillars = [p for p in pillars if p["pillar_type"] == "value"]
        proof_pillars = [p for p in pillars if p["pillar_type"] == "proof"]
        cta_pillars = [p for p in pillars if p["pillar_type"] == "cta"]

        assert len(value_pillars) == 4  # Pain Points, Process, Personality, Education
        assert len(proof_pillars) == 1  # Social Proof
        assert len(cta_pillars) == 2  # Product/Service, Promotion/CTA

    @pytest.mark.asyncio
    async def test_create_constraints(self, mock_database, mock_event_bus):
        """Test creating scheduling constraints (NAR-003)"""
        constraint_id = str(uuid4())
        goal_id = str(uuid4())
        created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = (constraint_id, created_at)
        mock_database.execute.return_value = mock_result

        service = get_narrative_goals_service()
        constraints = await service.create_constraints(
            goal_id=goal_id,
            enabled_platforms=["tiktok", "instagram", "youtube"],
            max_posts_per_day=3,
            min_posts_per_day=1,
            posting_windows={"morning": "08:00-12:00", "evening": "18:00-21:00"},
            blackout_dates=["2026-12-25", "2026-01-01"],
            timezone="America/Los_Angeles",
            min_pre_social_score=70,
            require_analysis=True,
            max_same_pillar_consecutive=2
        )

        # Assertions
        assert constraints["id"] == constraint_id
        assert constraints["goal_id"] == goal_id
        assert constraints["enabled_platforms"] == ["tiktok", "instagram", "youtube"]
        assert constraints["max_posts_per_day"] == 3
        assert constraints["min_posts_per_day"] == 1
        assert constraints["posting_windows"] == {"morning": "08:00-12:00", "evening": "18:00-21:00"}
        assert constraints["blackout_dates"] == ["2026-12-25", "2026-01-01"]
        assert constraints["timezone"] == "America/Los_Angeles"
        assert constraints["min_pre_social_score"] == 70
        assert constraints["require_analysis"] is True
        assert constraints["max_same_pillar_consecutive"] == 2

    @pytest.mark.asyncio
    async def test_get_goal(self, mock_database, mock_event_bus):
        """Test retrieving a goal by ID"""
        goal_id = str(uuid4())

        # Mock database response
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": goal_id,
            "workspace_id": "workspace-123",
            "goal_statement": "Test goal",
            "primary_cta": "Waitlist",
            "status": "active"
        }

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_database.execute.return_value = mock_result

        service = get_narrative_goals_service()
        goal = await service.get_goal(goal_id)

        assert goal is not None
        assert goal["id"] == goal_id
        assert goal["workspace_id"] == "workspace-123"

    @pytest.mark.asyncio
    async def test_get_goal_not_found(self, mock_database, mock_event_bus):
        """Test retrieving a non-existent goal"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_database.execute.return_value = mock_result

        service = get_narrative_goals_service()
        goal = await service.get_goal("non-existent-id")

        assert goal is None

    @pytest.mark.asyncio
    async def test_get_pillars_for_goal(self, mock_database, mock_event_bus):
        """Test retrieving pillars for a goal"""
        goal_id = str(uuid4())

        # Mock multiple pillars
        mock_rows = [
            MagicMock(_mapping={"id": str(uuid4()), "name": "Pain Points", "priority": 8}),
            MagicMock(_mapping={"id": str(uuid4()), "name": "Social Proof", "priority": 7}),
            MagicMock(_mapping={"id": str(uuid4()), "name": "Process/How-To", "priority": 9})
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter(mock_rows)
        mock_database.execute.return_value = mock_result

        service = get_narrative_goals_service()
        pillars = await service.get_pillars_for_goal(goal_id)

        assert len(pillars) == 3
        assert pillars[0]["name"] == "Pain Points"
        assert pillars[1]["name"] == "Social Proof"
        assert pillars[2]["name"] == "Process/How-To"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
