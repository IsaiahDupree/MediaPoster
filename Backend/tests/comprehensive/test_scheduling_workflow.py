"""
Comprehensive Scheduling Workflow Tests
Tests complete scheduling workflow from creation to publishing
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
import uuid
from datetime import datetime, timedelta

from main import app
from database.models import ScheduledPost, VideoClip


@pytest.fixture
def client():
    return TestClient(app)


class TestSchedulingWorkflow:
    """Comprehensive scheduling workflow tests"""
    
    @pytest.mark.asyncio
    async def test_schedule_and_reschedule_post(self, client, db_session, clean_db):
        """Test scheduling a post and then rescheduling it"""
        # Create a test clip
        from database.models import Video
        
        video = Video(
            id=uuid.uuid4(),
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            source_type="local",
            source_uri="/tmp/test.mp4",
            file_name="test.mp4",
            duration_sec=60
        )
        db_session.add(video)
        await db_session.flush()
        
        clip = VideoClip(
            id=uuid.uuid4(),
            video_id=video.id,
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            title="Test Clip",
            start_time=0.0,
            end_time=30.0
        )
        db_session.add(clip)
        await db_session.commit()
        
        # Schedule post
        schedule_time = datetime.now() + timedelta(days=1)
        schedule_response = client.post("/api/publishing/schedule", json={
            "clip_id": str(clip.id),
            "platforms": ["instagram"],
            "scheduled_time": schedule_time.isoformat(),
            "caption": "Test post"
        })
        assert schedule_response.status_code in [200, 201]
        post_data = schedule_response.json()
        post_id = uuid.UUID(post_data["post_id"])
        
        # Verify scheduled post exists
        result = await db_session.execute(
            select(ScheduledPost).where(ScheduledPost.id == post_id)
        )
        scheduled_post = result.scalar_one_or_none()
        assert scheduled_post is not None
        assert scheduled_post.status == "scheduled"
        
        # Reschedule (update scheduled_time)
        new_schedule_time = schedule_time + timedelta(hours=2)
        scheduled_post.scheduled_time = new_schedule_time
        await db_session.commit()
        await db_session.refresh(scheduled_post)
        
        assert scheduled_post.scheduled_time == new_schedule_time
    
    @pytest.mark.asyncio
    async def test_multi_platform_scheduling(self, client, db_session, clean_db):
        """Test scheduling the same content to multiple platforms"""
        # Create test clip
        from database.models import Video
        
        video = Video(
            id=uuid.uuid4(),
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            source_type="local",
            source_uri="/tmp/test.mp4",
            file_name="test.mp4",
            duration_sec=60
        )
        db_session.add(video)
        await db_session.flush()
        
        clip = VideoClip(
            id=uuid.uuid4(),
            video_id=video.id,
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            title="Multi-platform Clip",
            start_time=0.0,
            end_time=30.0
        )
        db_session.add(clip)
        await db_session.commit()
        
        # Schedule to multiple platforms
        platforms = ["instagram", "tiktok", "youtube"]
        schedule_time = datetime.now() + timedelta(days=1)
        
        schedule_response = client.post("/api/publishing/schedule", json={
            "clip_id": str(clip.id),
            "platforms": platforms,
            "scheduled_time": schedule_time.isoformat(),
            "caption": "Multi-platform post"
        })
        assert schedule_response.status_code in [200, 201]
        
        # Verify posts created for each platform
        result = await db_session.execute(
            select(ScheduledPost).where(ScheduledPost.clip_id == clip.id)
        )
        scheduled_posts = result.scalars().all()
        assert len(scheduled_posts) >= len(platforms)
        
        scheduled_platforms = {post.platform for post in scheduled_posts}
        assert scheduled_platforms.issuperset(set(platforms))
    
    @pytest.mark.asyncio
    async def test_calendar_view_with_filters(self, client, db_session, clean_db):
        """Test calendar view with date range filters"""
        # Create multiple scheduled posts
        from database.models import Video
        
        video = Video(
            id=uuid.uuid4(),
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            source_type="local",
            source_uri="/tmp/test.mp4",
            file_name="test.mp4",
            duration_sec=60
        )
        db_session.add(video)
        await db_session.flush()
        
        posts = []
        for i in range(5):
            clip = VideoClip(
                id=uuid.uuid4(),
                video_id=video.id,
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                title=f"Clip {i}",
                start_time=0.0,
                end_time=30.0
            )
            db_session.add(clip)
            await db_session.flush()
            
            post = ScheduledPost(
                id=uuid.uuid4(),
                clip_id=clip.id,
                platform="instagram",
                scheduled_time=datetime.now() + timedelta(days=i),
                status="scheduled"
            )
            db_session.add(post)
            posts.append(post)
        
        await db_session.commit()
        
        # Get calendar posts
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        
        response = client.get(
            "/api/publishing/calendar",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        assert response.status_code == 200
        calendar_posts = response.json()
        assert isinstance(calendar_posts, list)
        assert len(calendar_posts) >= 5

