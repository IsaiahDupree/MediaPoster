"""
API Integration Tests for Calendar Endpoints

Tests the calendar API endpoints using mocked CalendarService to avoid
database dependency. Tests verify correct routing, request validation,
and response formatting.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from main import app
from database.connection import get_db
from services.exceptions import ServiceError


# Mock DB dependency
async def override_get_db():
    yield MagicMock()


@pytest.fixture(autouse=True)
def setup_app():
    """Override DB dependency for all tests"""
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    """Create test client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def user_id():
    """Sample user ID"""
    return uuid4()


@pytest.fixture
def sample_clip_id():
    """Sample clip UUID"""
    return uuid4()


def _make_mock_post(
    post_id=None, platform="tiktok", status="scheduled",
    scheduled_time=None, is_ai_recommended=False,
    recommendation_score=None, recommendation_reasoning=None,
    clip_id=None
):
    """Create a mock ScheduledPost-like object."""
    post = MagicMock()
    post.id = post_id or uuid4()
    post.platform = platform
    post.status = status
    post.scheduled_time = scheduled_time or (datetime.now(timezone.utc) + timedelta(days=1))
    post.is_ai_recommended = is_ai_recommended
    post.recommendation_score = recommendation_score
    post.recommendation_reasoning = recommendation_reasoning
    post.published_at = None
    post.error_message = None
    post.created_at = datetime.now(timezone.utc)
    post.clip_id = clip_id
    post.content_variant_id = None
    return post


class TestCalendarAPIEndpoints:
    """Test calendar API endpoints"""

    @pytest.mark.asyncio
    async def test_get_calendar_posts_empty(self, client, user_id):
        """Test getting calendar posts when none exist"""
        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.get_calendar_posts = AsyncMock(return_value=[])

            response = await client.get(f"/api/calendar/posts?user_id={user_id}")

            assert response.status_code == 200
            assert response.json() == []

    @pytest.mark.asyncio
    async def test_schedule_post(self, client, sample_clip_id):
        """Test scheduling a post via API"""
        scheduled_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        post_id = uuid4()

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            mock_post = _make_mock_post(
                post_id=post_id, platform="tiktok",
                scheduled_time=datetime.now(timezone.utc) + timedelta(days=1)
            )
            instance = MockService.return_value
            instance.schedule_post = AsyncMock(return_value=mock_post)

            response = await client.post(
                "/api/calendar/schedule",
                json={
                    "clip_id": str(sample_clip_id),
                    "platform": "tiktok",
                    "scheduled_time": scheduled_time,
                    "is_ai_recommended": False
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "post_id" in data
            assert data["platform"] == "tiktok"

    @pytest.mark.asyncio
    async def test_schedule_post_invalid_data(self, client):
        """Test scheduling with invalid data"""
        # Missing required fields
        response = await client.post(
            "/api/calendar/schedule",
            json={
                "platform": "tiktok"
                # Missing clip_id and scheduled_time
            }
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_schedule_post_past_time(self, client, sample_clip_id):
        """Test that scheduling in past fails"""
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.schedule_post = AsyncMock(
                side_effect=ServiceError("Scheduled time must be in the future")
            )

            response = await client.post(
                "/api/calendar/schedule",
                json={
                    "clip_id": str(sample_clip_id),
                    "platform": "tiktok",
                    "scheduled_time": past_time
                }
            )

            assert response.status_code == 400
            assert "future" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_calendar_posts_with_data(self, client, user_id):
        """Test getting calendar posts after scheduling"""
        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.get_calendar_posts = AsyncMock(return_value=[
                {
                    "id": str(uuid4()),
                    "platform": "tiktok",
                    "scheduled_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                    "status": "scheduled",
                    "is_ai_recommended": False,
                    "recommendation_score": None,
                    "recommendation_reasoning": None,
                    "published_at": None,
                    "error_message": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "content": None,
                    "clip": None
                }
            ])

            response = await client.get(f"/api/calendar/posts?user_id={user_id}")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["platform"] == "tiktok"
            assert data[0]["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_get_calendar_posts_with_filters(self, client, user_id):
        """Test filtering calendar posts"""
        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.get_calendar_posts = AsyncMock(return_value=[
                {
                    "id": str(uuid4()),
                    "platform": "tiktok",
                    "scheduled_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                    "status": "scheduled",
                    "is_ai_recommended": False,
                    "recommendation_score": None,
                    "recommendation_reasoning": None,
                    "published_at": None,
                    "error_message": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "content": None,
                    "clip": None
                }
            ])

            response = await client.get(
                f"/api/calendar/posts?user_id={user_id}&platforms=tiktok"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["platform"] == "tiktok"

    @pytest.mark.asyncio
    async def test_reschedule_post(self, client, sample_clip_id):
        """Test rescheduling a post"""
        post_id = uuid4()
        new_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            mock_post = _make_mock_post(post_id=post_id)
            instance = MockService.return_value
            instance.reschedule_post = AsyncMock(return_value=mock_post)

            response = await client.patch(
                f"/api/calendar/posts/{post_id}",
                json={"scheduled_time": new_time}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["post_id"] == str(post_id)

    @pytest.mark.asyncio
    async def test_reschedule_nonexistent_post(self, client):
        """Test rescheduling non-existent post"""
        fake_id = uuid4()
        new_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.reschedule_post = AsyncMock(
                side_effect=ServiceError("Post not found")
            )

            response = await client.patch(
                f"/api/calendar/posts/{fake_id}",
                json={"scheduled_time": new_time}
            )

            assert response.status_code == 400
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cancel_post(self, client, sample_clip_id):
        """Test cancelling a scheduled post"""
        post_id = uuid4()

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.cancel_scheduled_post = AsyncMock(return_value=True)

            response = await client.delete(f"/api/calendar/posts/{post_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "cancelled" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_post(self, client):
        """Test cancelling non-existent post"""
        fake_id = uuid4()

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.cancel_scheduled_post = AsyncMock(
                side_effect=ServiceError("Post not found")
            )

            response = await client.delete(f"/api/calendar/posts/{fake_id}")

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_bulk_schedule(self, client, sample_clip_id):
        """Test bulk scheduling multiple posts"""
        base_time = datetime.now(timezone.utc) + timedelta(days=1)

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            mock_posts = [
                _make_mock_post(platform="tiktok"),
                _make_mock_post(platform="instagram"),
                _make_mock_post(platform="youtube"),
            ]
            instance = MockService.return_value
            instance.bulk_schedule = AsyncMock(return_value=mock_posts)

            posts_data = {
                "posts": [
                    {
                        "clip_id": str(sample_clip_id),
                        "platform": "tiktok",
                        "scheduled_time": base_time.isoformat()
                    },
                    {
                        "clip_id": str(sample_clip_id),
                        "platform": "instagram",
                        "scheduled_time": (base_time + timedelta(hours=2)).isoformat()
                    },
                    {
                        "clip_id": str(sample_clip_id),
                        "platform": "youtube",
                        "scheduled_time": (base_time + timedelta(hours=4)).isoformat()
                    }
                ]
            }

            response = await client.post("/api/calendar/bulk-schedule", json=posts_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["scheduled_count"] == 3
            assert len(data["post_ids"]) == 3

    @pytest.mark.asyncio
    async def test_get_posting_gaps(self, client, user_id):
        """Test identifying posting gaps"""
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        end_date = (today + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.get_posting_gaps = AsyncMock(return_value=[
                {"date": (today + timedelta(days=2)).strftime("%Y-%m-%d"), "platforms": ["tiktok", "instagram"]},
                {"date": (today + timedelta(days=4)).strftime("%Y-%m-%d"), "platforms": ["tiktok", "instagram"]},
                {"date": (today + timedelta(days=5)).strftime("%Y-%m-%d"), "platforms": ["tiktok", "instagram"]},
            ])

            response = await client.get(
                f"/api/calendar/gaps?user_id={user_id}&start_date={start_date}&end_date={end_date}"
            )

            assert response.status_code == 200
            gaps = response.json()
            assert len(gaps) >= 2

    @pytest.mark.asyncio
    async def test_date_range_filtering(self, client, user_id):
        """Test filtering by date range"""
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        start_date = today.strftime("%Y-%m-%dT%H:%M:%S")
        end_date = (today + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.get_calendar_posts = AsyncMock(return_value=[
                {
                    "id": str(uuid4()),
                    "platform": "tiktok",
                    "scheduled_time": (today + timedelta(days=1)).isoformat(),
                    "status": "scheduled",
                    "is_ai_recommended": False,
                    "recommendation_score": None,
                    "recommendation_reasoning": None,
                    "published_at": None,
                    "error_message": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "content": None,
                    "clip": None
                }
            ])

            response = await client.get(
                f"/api/calendar/posts?user_id={user_id}&start_date={start_date}&end_date={end_date}"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["platform"] == "tiktok"


class TestCalendarAPIErrorHandling:
    """Test error handling in calendar API"""

    @pytest.mark.asyncio
    async def test_invalid_uuid_format(self, client):
        """Test handling of invalid UUID format"""
        response = await client.delete("/api/calendar/posts/not-a-uuid")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_missing_required_query_param(self, client):
        """Test handling of missing required query parameters - user_id has default"""
        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.get_calendar_posts = AsyncMock(return_value=[])

            # user_id has a default value in the endpoint, so this should still work
            response = await client.get("/api/calendar/posts")

            # Should return 200 since user_id has a default
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_date_format(self, client, user_id):
        """Test handling of invalid date format"""
        response = await client.get(
            f"/api/calendar/posts?user_id={user_id}&start_date=invalid-date"
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_schedule_without_content(self, client):
        """Test scheduling without clip_id or content_variant_id"""
        scheduled_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.schedule_post = AsyncMock(
                side_effect=ServiceError("Either clip_id or content_variant_id must be provided")
            )

            response = await client.post(
                "/api/calendar/schedule",
                json={
                    "platform": "tiktok",
                    "scheduled_time": scheduled_time
                    # Missing both clip_id and content_variant_id
                }
            )

            assert response.status_code == 400
            assert "clip_id or content_variant_id" in response.json()["detail"].lower()


class TestCalendarAPIWithAIRecommendations:
    """Test AI recommendation features in calendar API"""

    @pytest.mark.asyncio
    async def test_schedule_with_ai_metadata(self, client, sample_clip_id):
        """Test scheduling with AI recommendation metadata"""
        scheduled_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        with patch("api.endpoints.calendar.CalendarService") as MockService:
            mock_post = _make_mock_post(
                platform="youtube", is_ai_recommended=True,
                recommendation_score=0.92,
                recommendation_reasoning="Optimal posting time"
            )
            instance = MockService.return_value
            instance.schedule_post = AsyncMock(return_value=mock_post)

            response = await client.post(
                "/api/calendar/schedule",
                json={
                    "clip_id": str(sample_clip_id),
                    "platform": "youtube",
                    "scheduled_time": scheduled_time,
                    "is_ai_recommended": True,
                    "recommendation_score": 0.92,
                    "recommendation_reasoning": "Optimal posting time based on historical data"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_ai_recommended_posts(self, client, user_id):
        """Test retrieving AI recommended posts"""
        with patch("api.endpoints.calendar.CalendarService") as MockService:
            instance = MockService.return_value
            instance.get_calendar_posts = AsyncMock(return_value=[
                {
                    "id": str(uuid4()),
                    "platform": "tiktok",
                    "scheduled_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                    "status": "scheduled",
                    "is_ai_recommended": True,
                    "recommendation_score": 0.88,
                    "recommendation_reasoning": "High engagement predicted",
                    "published_at": None,
                    "error_message": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "content": None,
                    "clip": None
                }
            ])

            response = await client.get(f"/api/calendar/posts?user_id={user_id}")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["is_ai_recommended"] is True
            assert data[0]["recommendation_score"] == 0.88
