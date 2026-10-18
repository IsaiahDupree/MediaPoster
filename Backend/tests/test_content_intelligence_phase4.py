"""
Tests for Content Intelligence Phase 4: Platform Integration
Tests multi-platform publishing, metrics collection, and comment analysis
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, PlatformPost, PlatformCheckback, PostComment
from services.platform_adapters.base import (
    PlatformType, PublishRequest, PublishResult,
    MetricsSnapshot, CommentData, MockPlatformAdapter
)
from services.multi_platform_publisher import MultiPlatformPublisher


@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestMockPlatformAdapter:
    """Test mock platform adapter"""
    
    def test_initialization(self):
        """Test adapter initialization"""
        adapter = MockPlatformAdapter(PlatformType.TIKTOK)
        
        assert adapter.platform_type == PlatformType.TIKTOK
        assert adapter.is_authenticated() is True
    
    def test_publish_video(self):
        """Test video publishing"""
        adapter = MockPlatformAdapter(PlatformType.INSTAGRAM)
        
        request = PublishRequest(
            video_path="/fake/video.mp4",
            title="Test Video",
            caption="Check this out!",
            hashtags=["viral", "content"]
        )
        
        result = adapter.publish_video(request)
        
        assert result.success is True
        assert result.platform == "instagram"
        assert result.platform_post_id is not None
        assert result.post_url is not None
        assert "instagram.com" in result.post_url
    
    def test_get_post_url(self):
        """Test post URL retrieval"""
        adapter = MockPlatformAdapter(PlatformType.YOUTUBE)
        
        url = adapter.get_post_url("video123")
        
        assert url is not None
        assert "youtube.com" in url
        assert "video123" in url
    
    def test_fetch_metrics(self):
        """Test metrics fetching"""
        adapter = MockPlatformAdapter(PlatformType.TIKTOK)
        
        metrics = adapter.fetch_metrics("post123")
        
        assert metrics is not None
        assert metrics.platform_post_id == "post123"
        assert metrics.views > 0
        assert metrics.likes > 0
        assert metrics.comments >= 0
    
    def test_fetch_comments(self):
        """Test comment fetching"""
        adapter = MockPlatformAdapter(PlatformType.INSTAGRAM)
        
        comments = adapter.fetch_comments("post456", limit=10)
        
        assert isinstance(comments, list)
        assert len(comments) <= 10
        
        if comments:
            comment = comments[0]
            assert comment.platform_comment_id is not None
            assert comment.author_handle is not None
            assert comment.text is not None


class TestMultiPlatformPublisher:
    """Test multi-platform publisher"""
    
    def test_initialization(self, db_session):
        """Test publisher initialization"""
        publisher = MultiPlatformPublisher(db=db_session)
        
        assert publisher.db == db_session
        assert isinstance(publisher.adapters, dict)
        assert len(publisher.adapters) == 0
    
    def test_register_adapter(self, db_session):
        """Test adapter registration"""
        publisher = MultiPlatformPublisher(db=db_session)
        adapter = MockPlatformAdapter(PlatformType.TIKTOK)
        
        publisher.register_adapter(adapter)
        
        assert "tiktok" in publisher.adapters
        assert publisher.adapters["tiktok"] == adapter
    
    def test_get_available_platforms(self, db_session):
        """Test getting available platforms"""
        publisher = MultiPlatformPublisher(db=db_session)
        
        publisher.register_adapter(MockPlatformAdapter(PlatformType.TIKTOK))
        publisher.register_adapter(MockPlatformAdapter(PlatformType.INSTAGRAM))
        
        platforms = publisher.get_available_platforms()
        
        assert len(platforms) == 2
        assert "tiktok" in platforms
        assert "instagram" in platforms
    
    def test_publish_to_platform_success(self, db_session):
        """Test successful platform publishing"""
        publisher = MultiPlatformPublisher(db=db_session)
        adapter = MockPlatformAdapter(PlatformType.TIKTOK)
        publisher.register_adapter(adapter)
        
        request = PublishRequest(
            video_path="/fake/video.mp4",
            title="Test Video",
            caption="Amazing content!",
            hashtags=["test", "viral"]
        )
        
        result = publisher.publish_to_platform(
            platform="tiktok",
            request=request
        )
        
        assert result["success"] is True
        assert result["platform"] == "tiktok"
        assert result["post_url"] is not None
        
        # Verify database record
        post = db_session.query(PlatformPost).first()
        assert post is not None
        assert post.platform == "tiktok"
        assert post.status == "published"
        assert post.title == "Test Video"
    
    def test_publish_to_platform_not_registered(self, db_session):
        """Test publishing to unregistered platform"""
        publisher = MultiPlatformPublisher(db=db_session)
        
        request = PublishRequest(
            video_path="/fake/video.mp4",
            title="Test",
            caption="Test",
            hashtags=[]
        )
        
        result = publisher.publish_to_platform(
            platform="youtube",
            request=request
        )
        
        assert result["success"] is False
        assert "not registered" in result["error"]
    
    def test_publish_to_multiple_platforms(self, db_session):
        """Test publishing to multiple platforms"""
        publisher = MultiPlatformPublisher(db=db_session)
        
        # Register multiple adapters
        publisher.register_adapter(MockPlatformAdapter(PlatformType.TIKTOK))
        publisher.register_adapter(MockPlatformAdapter(PlatformType.INSTAGRAM))
        publisher.register_adapter(MockPlatformAdapter(PlatformType.YOUTUBE))
        
        request = PublishRequest(
            video_path="/fake/video.mp4",
            title="Multi-Platform Test",
            caption="Goes everywhere!",
            hashtags=["multiplatform"]
        )
        
        result = publisher.publish_to_multiple_platforms(
            platforms=["tiktok", "instagram", "youtube"],
            request=request
        )
        
        assert result["total_platforms"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0
        
        # Verify all posts in database
        posts = db_session.query(PlatformPost).all()
        assert len(posts) == 3
        
        platforms = {p.platform for p in posts}
        assert platforms == {"tiktok", "instagram", "youtube"}
    
    def test_collect_metrics(self, db_session):
        """Test metrics collection"""
        publisher = MultiPlatformPublisher(db=db_session)
        adapter = MockPlatformAdapter(PlatformType.TIKTOK)
        publisher.register_adapter(adapter)
        
        # Create a post
        post = PlatformPost(
            platform="tiktok",
            platform_post_id="post123",
            platform_url="https://tiktok.com/post123",
            status="published",
            published_at=datetime.now()
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        # Collect metrics
        result = publisher.collect_metrics(
            post_id=post.id,
            checkback_hours=24
        )
        
        assert result["success"] is True
        assert result["checkback_hours"] == 24
        assert "metrics" in result
        assert result["metrics"]["views"] > 0
        
        # Verify checkback in database
        checkback = db_session.query(PlatformCheckback).first()
        assert checkback is not None
        assert checkback.platform_post_id == post.id
        assert checkback.checkback_h == 24
        assert checkback.views > 0
    
    def test_collect_metrics_post_not_found(self, db_session):
        """Test metrics collection for non-existent post"""
        publisher = MultiPlatformPublisher(db=db_session)
        
        fake_id = uuid.uuid4()
        result = publisher.collect_metrics(
            post_id=fake_id,
            checkback_hours=1
        )
        
        assert "error" in result
        assert "not found" in result["error"]
    
    @patch('services.psychology_tagger.PsychologyTagger.is_enabled')
    @patch('services.psychology_tagger.PsychologyTagger.analyze_sentiment_emotion')
    def test_collect_comments_with_sentiment(
        self, mock_sentiment, mock_enabled, db_session
    ):
        """Test comment collection with sentiment analysis"""
        mock_enabled.return_value = True
        mock_sentiment.return_value = {
            "sentiment_score": 0.8,
            "primary_emotion": "excited",
            "tone": "hype_coach"
        }
        
        publisher = MultiPlatformPublisher(db=db_session)
        adapter = MockPlatformAdapter(PlatformType.INSTAGRAM)
        publisher.register_adapter(adapter)
        
        # Create a post
        post = PlatformPost(
            platform="instagram",
            platform_post_id="post456",
            status="published"
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        # Collect comments
        result = publisher.collect_comments(
            post_id=post.id,
            limit=10,
            analyze_sentiment=True
        )
        
        assert result["success"] is True
        assert result["comments_collected"] > 0
        assert result["sentiment_analyzed"] > 0
        
        # Verify comments in database
        comments = db_session.query(PostComment).all()
        assert len(comments) > 0
        
        comment = comments[0]
        assert comment.platform_post_id == post.id
        assert comment.sentiment_score is not None
        assert comment.emotion_tags is not None
    
    def test_collect_comments_without_sentiment(self, db_session):
        """Test comment collection without sentiment analysis"""
        publisher = MultiPlatformPublisher(db=db_session)
        adapter = MockPlatformAdapter(PlatformType.YOUTUBE)
        publisher.register_adapter(adapter)
        
        # Create a post
        post = PlatformPost(
            platform="youtube",
            platform_post_id="post789",
            status="published"
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        # Collect comments without sentiment
        result = publisher.collect_comments(
            post_id=post.id,
            limit=5,
            analyze_sentiment=False
        )
        
        assert result["success"] is True
        assert result["sentiment_analyzed"] == 0
        
        # Comments should still be stored
        comments = db_session.query(PostComment).all()
        assert len(comments) > 0
    
    def test_schedule_checkbacks(self, db_session):
        """Test checkback scheduling"""
        publisher = MultiPlatformPublisher(db=db_session)
        
        # Create a post
        post = PlatformPost(
            platform="tiktok",
            platform_post_id="post999",
            published_at=datetime.now(),
            status="published"
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        # Schedule checkbacks (this is a placeholder in current implementation)
        checkback_hours = [1, 6, 24, 72, 168]
        publisher.schedule_checkbacks(
            post_id=post.id,
            checkback_hours=checkback_hours
        )
        
        # For now, just verify it doesn't error
        # In production, would verify scheduled jobs


class TestPublishRequestDataclass:
    """Test PublishRequest dataclass"""
    
    def test_create_publish_request(self):
        """Test creating publish request"""
        request = PublishRequest(
            video_path="/path/to/video.mp4",
            title="My Video",
            caption="Check this out!",
            hashtags=["cool", "video"]
        )
        
        assert request.video_path == "/path/to/video.mp4"
        assert request.title == "My Video"
        assert len(request.hashtags) == 2
        assert request.scheduled_time is None
    
    def test_publish_request_with_options(self):
        """Test publish request with platform-specific options"""
        scheduled = datetime.now() + timedelta(hours=2)
        
        request = PublishRequest(
            video_path="/video.mp4",
            title="Scheduled Video",
            caption="Coming soon!",
            hashtags=[],
            scheduled_time=scheduled,
            platform_specific_options={"allow_comments": True, "allow_duet": False}
        )
        
        assert request.scheduled_time == scheduled
        assert request.platform_specific_options["allow_comments"] is True


class TestMetricsSnapshot:
    """Test MetricsSnapshot dataclass"""
    
    def test_create_metrics_snapshot(self):
        """Test creating metrics snapshot"""
        snapshot = MetricsSnapshot(
            platform_post_id="post123",
            collected_at=datetime.now(),
            views=5000,
            likes=350,
            comments=45,
            shares=78
        )
        
        assert snapshot.platform_post_id == "post123"
        assert snapshot.views == 5000
        assert snapshot.likes == 350
    
    def test_metrics_snapshot_with_retention(self):
        """Test metrics with retention curve"""
        retention_curve = [
            {"t_pct": 0.1, "retention": 0.95},
            {"t_pct": 0.5, "retention": 0.72},
            {"t_pct": 1.0, "retention": 0.45}
        ]
        
        snapshot = MetricsSnapshot(
            platform_post_id="post456",
            collected_at=datetime.now(),
            views=10000,
            avg_watch_pct=0.68,
            retention_curve=retention_curve
        )
        
        assert snapshot.avg_watch_pct == 0.68
        assert len(snapshot.retention_curve) == 3
        assert snapshot.retention_curve[0]["retention"] == 0.95


class TestCommentData:
    """Test CommentData dataclass"""
    
    def test_create_comment_data(self):
        """Test creating comment data"""
        comment = CommentData(
            platform_comment_id="comment123",
            author_handle="@user",
            author_name="John Doe",
            text="Great video!",
            created_at=datetime.now()
        )
        
        assert comment.platform_comment_id == "comment123"
        assert comment.author_handle == "@user"
        assert comment.text == "Great video!"
        assert comment.is_reply is False
    
    def test_comment_data_reply(self):
        """Test comment as reply"""
        comment = CommentData(
            platform_comment_id="reply456",
            author_handle="@replier",
            author_name="Jane Smith",
            text="Thanks for sharing!",
            created_at=datetime.now(),
            is_reply=True,
            parent_comment_id="comment123"
        )
        
        assert comment.is_reply is True
        assert comment.parent_comment_id == "comment123"
