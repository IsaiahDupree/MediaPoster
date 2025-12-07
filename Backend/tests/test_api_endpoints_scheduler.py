"""
Tests for API Endpoints and Background Scheduler
Tests platform publishing APIs and checkback scheduler
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, PlatformPost, PlatformCheckback, PostComment
from services.checkback_scheduler import CheckbackScheduler
from main import app

client = TestClient(app)


@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestPlatformPublishingEndpoints:
    """Test platform publishing API endpoints"""
    
    def test_get_available_platforms(self):
        """Test GET /api/platform/platforms"""
        response = client.get("/api/platform/platforms")
        
        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data
        assert "total" in data
        assert isinstance(data["platforms"], list)
    
    @patch('services.multi_platform_publisher.MultiPlatformPublisher.publish_to_multiple_platforms')
    def test_publish_video(self, mock_publish):
        """Test POST /api/platform/publish"""
        mock_publish.return_value = {
            "total_platforms": 2,
            "successful": 2,
            "failed": 0,
            "results": {
                "tiktok": {"success": True, "post_url": "https://tiktok.com/post123"},
                "instagram": {"success": True, "post_url": "https://instagram.com/p/abc"}
            }
        }
        
        request_data = {
            "video_path": "/path/to/video.mp4",
            "title": "Test Video",
            "caption": "Amazing content!",
            "hashtags": ["viral", "test"],
            "platforms": ["tiktok", "instagram"]
        }
        
        response = client.post("/api/platform/publish", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["successful"] == 2
    
    def test_list_posts(self, db_session):
        """Test GET /api/platform/posts"""
        # Create test posts
        post1 = PlatformPost(
            platform="tiktok",
            platform_post_id="post123",
            title="Test 1",
            caption="Caption 1",
            status="published",
            published_at=datetime.now()
        )
        post2 = PlatformPost(
            platform="instagram",
            platform_post_id="post456",
            title="Test 2",
            caption="Caption 2",
            status="published",
            published_at=datetime.now()
        )
        
        db_session.add_all([post1, post2])
        db_session.commit()
        
        response = client.get("/api/platform/posts")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_posts_with_platform_filter(self):
        """Test GET /api/platform/posts with platform filter"""
        response = client.get("/api/platform/posts?platform=tiktok")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestCheckbackScheduler:
    """Test background checkback scheduler"""
    
    def test_scheduler_initialization(self):
        """Test scheduler creation"""
        scheduler = CheckbackScheduler()
        
        assert scheduler is not None
        assert not scheduler.scheduler.running
    
    def test_start_and_shutdown(self):
        """Test scheduler lifecycle"""
        scheduler = CheckbackScheduler()
        
        # Start
        scheduler.start()
        assert scheduler.scheduler.running
        
        # Shutdown
        scheduler.shutdown()
        assert not scheduler.scheduler.running
    
    def test_schedule_checkback(self):
        """Test scheduling a checkback"""
        scheduler = CheckbackScheduler()
        scheduler.start()
        
        post_id = uuid.uuid4()
        published_at = datetime.now()
        
        # Mock callback
        callback = Mock()
        
        # Schedule 1 hour checkback
        job_id = scheduler.schedule_checkback(
            post_id=post_id,
            published_at=published_at,
            checkback_hours=1,
            callback=callback
        )
        
        assert job_id is not None
        assert job_id in scheduler.scheduled_jobs
        
        scheduler.shutdown()
    
    def test_schedule_standard_checkbacks(self):
        """Test scheduling standard set of checkbacks"""
        scheduler = CheckbackScheduler()
        scheduler.start()
        
        post_id = uuid.uuid4()
        published_at = datetime.now()
        callback = Mock()
        
        job_ids = scheduler.schedule_standard_checkbacks(
            post_id=post_id,
            published_at=published_at,
            callback=callback,
            checkback_hours=[1, 6, 24]
        )
        
        assert len(job_ids) == 3
        
        scheduler.shutdown()
    
    def test_cancel_checkback(self):
        """Test cancelling a checkback"""
        scheduler = CheckbackScheduler()
        scheduler.start()
        
        post_id = uuid.uuid4()
        published_at = datetime.now()
        callback = Mock()
        
        job_id = scheduler.schedule_checkback(
            post_id=post_id,
            published_at=published_at,
            checkback_hours=1,
            callback=callback
        )
        
        # Cancel
        result = scheduler.cancel_checkback(job_id)
        
        assert result is True
        assert job_id not in scheduler.scheduled_jobs
        
        scheduler.shutdown()
    
    def test_cancel_all_for_post(self):
        """Test cancelling all checkbacks for a post"""
        scheduler = CheckbackScheduler()
        scheduler.start()
        
        post_id = uuid.uuid4()
        published_at = datetime.now()
        callback = Mock()
        
        # Schedule multiple
        scheduler.schedule_standard_checkbacks(
            post_id=post_id,
            published_at=published_at,
            callback=callback,
            checkback_hours=[1, 6, 24]
        )
        
        # Cancel all
        cancelled = scheduler.cancel_all_for_post(post_id)
        
        assert cancelled == 3
        
        # Verify none remain
        remaining = scheduler.get_scheduled_checkbacks(post_id)
        assert len(remaining) == 0
        
        scheduler.shutdown()
    
    def test_get_scheduled_checkbacks(self):
        """Test retrieving scheduled checkbacks"""
        scheduler = CheckbackScheduler()
        scheduler.start()
        
        post_id = uuid.uuid4()
        published_at = datetime.now()
        callback = Mock()
        
        scheduler.schedule_standard_checkbacks(
            post_id=post_id,
            published_at=published_at,
            callback=callback,
            checkback_hours=[1, 6]
        )
        
        # Get for specific post
        checkbacks = scheduler.get_scheduled_checkbacks(post_id)
        assert len(checkbacks) == 2
        
        # Get all
        all_checkbacks = scheduler.get_scheduled_checkbacks()
        assert len(all_checkbacks) == 2
        
        scheduler.shutdown()
    
    def test_get_next_checkback_time(self):
        """Test getting next checkback time"""
        scheduler = CheckbackScheduler()
        scheduler.start()
        
        post_id = uuid.uuid4()
        published_at = datetime.now()
        callback = Mock()
        
        scheduler.schedule_standard_checkbacks(
            post_id=post_id,
            published_at=published_at,
            callback=callback,
            checkback_hours=[1, 6, 24]
        )
        
        next_time = scheduler.get_next_checkback_time(post_id)
        
        assert next_time is not None
        assert next_time > datetime.now()
        
        scheduler.shutdown()
    
    def test_skip_past_checkbacks(self):
        """Test that past checkbacks are skipped"""
        scheduler = CheckbackScheduler()
        scheduler.start()
        
        post_id = uuid.uuid4()
        # Published 2 hours ago
        published_at = datetime.now() - timedelta(hours=2)
        callback = Mock()
        
        # Try to schedule 1 hour checkback (in the past)
        job_id = scheduler.schedule_checkback(
            post_id=post_id,
            published_at=published_at,
            checkback_hours=1,
            callback=callback
        )
        
        # Should be None (skipped)
        assert job_id is None
        
        scheduler.shutdown()


class TestBackgroundTasks:
    """Test background task functions"""
    
    @patch('services.multi_platform_publisher.MultiPlatformPublisher.collect_metrics')
    def test_collect_checkback_metrics_task(self, mock_collect, db_session):
        """Test checkback metrics collection task"""
        from services.background_tasks import collect_checkback_metrics_task
        
        mock_collect.return_value = {
            "success": True,
            "metrics": {"views": 1000, "likes": 50}
        }
        
        post_id = uuid.uuid4()
        
        # Create session factory
        def session_factory():
            return db_session
        
        # Run task
        collect_checkback_metrics_task(
            post_id=post_id,
            checkback_hours=24,
            db_session_factory=session_factory
        )
        
        # Verify it ran (mock was called)
        assert mock_collect.called
