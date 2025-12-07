"""
API Integration Tests for Calendar Endpoints
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from main import app
from database.models import Base, ScheduledPost, VideoClip, ContentVariant
from database.connection import get_db


# Test fixtures
@pytest.fixture
async def test_db():
    """Create test database session"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=NullPool)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def override_get_db(test_db):
    """Override database dependency for testing"""
    async def _override():
        yield test_db
    return _override


@pytest.fixture
async def client(override_get_db):
    """Create test client"""
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_clip(test_db):
    """Create sample clip"""
    clip = VideoClip(
        id=uuid4(),
        title="Test Clip",
        file_path="/test/video.mp4",
        duration_seconds=60.0,
        original_video_id=uuid4()
    )
    test_db.add(clip)
    await test_db.commit()
    await test_db.refresh(clip)
    return clip


@pytest.fixture
def user_id():
    """Sample user ID"""
    return uuid4()


class TestCalendarAPIEndpoints:
    """Test calendar API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_calendar_posts_empty(self, client, user_id):
        """Test getting calendar posts when none exist"""
        response = await client.get(f"/api/calendar/posts?user_id={user_id}")
        
        assert response.status_code == 200
        assert response.json() == []
    
    @pytest.mark.asyncio
    async def test_schedule_post(self, client, sample_clip):
        """Test scheduling a post via API"""
        scheduled_time = (datetime.now() + timedelta(days=1)).isoformat()
        
        response = await client.post(
            "/api/calendar/schedule",
            json={
                "clip_id": str(sample_clip.id),
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
    async def test_schedule_post_past_time(self, client, sample_clip):
        """Test that scheduling in past fails"""
        past_time = (datetime.now() - timedelta(hours=1)).isoformat()
        
        response = await client.post(
            "/api/calendar/schedule",
            json={
                "clip_id": str(sample_clip.id),
                "platform": "tiktok",
                "scheduled_time": past_time
            }
        )
        
        assert response.status_code == 400
        assert "future" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_calendar_posts_with_data(self, client, test_db, sample_clip, user_id):
        """Test getting calendar posts after scheduling"""
        # Schedule a post
        scheduled_time = datetime.now() + timedelta(days=1)
        post = ScheduledPost(
            clip_id=sample_clip.id,
            platform="tiktok",
            scheduled_time=scheduled_time,
            status="scheduled"
        )
        test_db.add(post)
        await test_db.commit()
        
        # Get posts
        response = await client.get(f"/api/calendar/posts?user_id={user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["platform"] == "tiktok"
        assert data[0]["status"] == "scheduled"
    
    @pytest.mark.asyncio
    async def test_get_calendar_posts_with_filters(self, client, test_db, sample_clip, user_id):
        """Test filtering calendar posts"""
        # Schedule posts on different platforms
        scheduled_time = datetime.now() + timedelta(days=1)
        
        post1 = ScheduledPost(
            clip_id=sample_clip.id,
            platform="tiktok",
            scheduled_time=scheduled_time,
            status="scheduled"
        )
        post2 = ScheduledPost(
            clip_id=sample_clip.id,
            platform="instagram",
            scheduled_time=scheduled_time + timedelta(hours=1),
            status="scheduled"
        )
        test_db.add_all([post1, post2])
        await test_db.commit()
        
        # Filter for TikTok only
        response = await client.get(
            f"/api/calendar/posts?user_id={user_id}&platforms=tiktok"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["platform"] == "tiktok"
    
    @pytest.mark.asyncio
    async def test_reschedule_post(self, client, test_db, sample_clip):
        """Test rescheduling a post"""
        # Create a scheduled post
        original_time = datetime.now() + timedelta(days=1)
        post = ScheduledPost(
            clip_id=sample_clip.id,
            platform="tiktok",
            scheduled_time=original_time,
            status="scheduled"
        )
        test_db.add(post)
        await test_db.commit()
        await test_db.refresh(post)
        
        # Reschedule it
        new_time = (datetime.now() + timedelta(days=2)).isoformat()
        response = await client.patch(
            f"/api/calendar/posts/{post.id}",
            json={"scheduled_time": new_time}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["post_id"] == str(post.id)
    
    @pytest.mark.asyncio
    async def test_reschedule_nonexistent_post(self, client):
        """Test rescheduling non-existent post"""
        fake_id = uuid4()
        new_time = (datetime.now() + timedelta(days=1)).isoformat()
        
        response = await client.patch(
            f"/api/calendar/posts/{fake_id}",
            json={"scheduled_time": new_time}
        )
        
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_cancel_post(self, client, test_db, sample_clip):
        """Test cancelling a scheduled post"""
        # Create a scheduled post
        scheduled_time = datetime.now() + timedelta(days=1)
        post = ScheduledPost(
            clip_id=sample_clip.id,
            platform="tiktok",
            scheduled_time=scheduled_time,
            status="scheduled"
        )
        test_db.add(post)
        await test_db.commit()
        await test_db.refresh(post)
        
        # Cancel it
        response = await client.delete(f"/api/calendar/posts/{post.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cancelled" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_post(self, client):
        """Test cancelling non-existent post"""
        fake_id = uuid4()
        
        response = await client.delete(f"/api/calendar/posts/{fake_id}")
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_bulk_schedule(self, client, sample_clip):
        """Test bulk scheduling multiple posts"""
        base_time = datetime.now() + timedelta(days=1)
        
        posts_data = {
            "posts": [
                {
                    "clip_id": str(sample_clip.id),
                    "platform": "tiktok",
                    "scheduled_time": base_time.isoformat()
                },
                {
                    "clip_id": str(sample_clip.id),
                    "platform": "instagram",
                    "scheduled_time": (base_time + timedelta(hours=2)).isoformat()
                },
                {
                    "clip_id": str(sample_clip.id),
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
    async def test_get_posting_gaps(self, client, test_db, sample_clip, user_id):
        """Test identifying posting gaps"""
        # Schedule posts with gaps
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        
        # Post on day 1, skip day 2, post on day 3
        post1 = ScheduledPost(
            clip_id=sample_clip.id,
            platform="tiktok",
            scheduled_time=today + timedelta(days=1),
            status="scheduled"
        )
        post2 = ScheduledPost(
            clip_id=sample_clip.id,
            platform="instagram",
            scheduled_time=today + timedelta(days=3),
            status="scheduled"
        )
        test_db.add_all([post1, post2])
        await test_db.commit()
        
        # Get gaps
        start_date = (today + timedelta(days=1)).isoformat()
        end_date = (today + timedelta(days=5)).isoformat()
        
        response = await client.get(
            f"/api/calendar/gaps?user_id={user_id}&start_date={start_date}&end_date={end_date}"
        )
        
        assert response.status_code == 200
        gaps = response.json()
        # Should have gaps on days 2, 4, and 5
        assert len(gaps) >= 2
    
    @pytest.mark.asyncio
    async def test_date_range_filtering(self, client, test_db, sample_clip, user_id):
        """Test filtering by date range"""
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        
        # Create posts on different dates
        post1 = ScheduledPost(
            clip_id=sample_clip.id,
            platform="tiktok",
            scheduled_time=today + timedelta(days=1),
            status="scheduled"
        )
        post2 = ScheduledPost(
            clip_id=sample_clip.id,
            platform="instagram",
            scheduled_time=today + timedelta(days=7),
            status="scheduled"
        )
        test_db.add_all([post1, post2])
        await test_db.commit()
        
        # Get posts for next 3 days only
        start_date = today.isoformat()
        end_date = (today + timedelta(days=3)).isoformat()
        
        response = await client.get(
            f"/api/calendar/posts?user_id={user_id}&start_date={start_date}&end_date={end_date}"
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should only get the first post
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
        """Test handling of missing required query parameters"""
        # Missing user_id
        response = await client.get("/api/calendar/posts")
        
        assert response.status_code == 422
    
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
        scheduled_time = (datetime.now() + timedelta(days=1)).isoformat()
        
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
    async def test_schedule_with_ai_metadata(self, client, sample_clip):
        """Test scheduling with AI recommendation metadata"""
        scheduled_time = (datetime.now() + timedelta(days=1)).isoformat()
        
        response = await client.post(
            "/api/calendar/schedule",
            json={
                "clip_id": str(sample_clip.id),
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
    async def test_get_ai_recommended_posts(self, client, test_db, sample_clip, user_id):
        """Test retrieving AI recommended posts"""
        scheduled_time = datetime.now() + timedelta(days=1)
        
        # Create AI recommended post
        post = ScheduledPost(
            clip_id=sample_clip.id,
            platform="tiktok",
            scheduled_time=scheduled_time,
            status="scheduled",
            is_ai_recommended=True,
            recommendation_score=0.88,
            recommendation_reasoning="High engagement predicted"
        )
        test_db.add(post)
        await test_db.commit()
        
        # Get posts
        response = await client.get(f"/api/calendar/posts?user_id={user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_ai_recommended"] is True
        assert data[0]["recommendation_score"] == 0.88
