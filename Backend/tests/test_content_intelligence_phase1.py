"""
Tests for Content Intelligence Phase 1: Database Models
Tests all Content Intelligence database models and relationships
"""
import pytest
from datetime import datetime
from decimal import Decimal
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import (
    Base,
    AnalyzedVideo, VideoSegment, VideoWord, VideoFrame,
    VideoCaption, VideoHeadline,
    PlatformPost, PlatformCheckback, PostComment,
    WeeklyMetric, ContentInsight
)


@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestAnalyzedVideoModel:
    """Test AnalyzedVideo model"""
    
    def test_create_analyzed_video(self, db_session):
        """Test creating an analyzed video record"""
        video = AnalyzedVideo(
            duration_seconds=120.5,
            transcript_full="This is a test transcript"
        )
        
        db_session.add(video)
        db_session.commit()
        
        assert video.id is not None
        assert video.duration_seconds == 120.5
        assert video.transcript_full == "This is a test transcript"
        assert video.created_at is not None
    
    def test_analyzed_video_relationships(self, db_session):
        """Test AnalyzedVideo relationships"""
        video = AnalyzedVideo(duration_seconds=60.0)
        db_session.add(video)
        db_session.commit()
        
        # Add segments
        segment = VideoSegment(
            video_id=video.id,
            segment_type="hook",
            start_s=0.0,
            end_s=5.0
        )
        db_session.add(segment)
        
        # Add words
        word = VideoWord(
            video_id=video.id,
            word_index=0,
            word="Test",
            start_s=0.0,
            end_s=0.5
        )
        db_session.add(word)
        
        # Add frames
        frame = VideoFrame(
            video_id=video.id,
            frame_time_s=1.0,
            shot_type="close_up"
        )
        db_session.add(frame)
        
        db_session.commit()
        
        # Verify relationships
        assert len(video.segments) == 1
        assert len(video.words) == 1
        assert len(video.frames) == 1


class TestVideoSegmentModel:
    """Test VideoSegment model"""
    
    def test_create_video_segment(self, db_session):
        """Test creating a video segment"""
        video = AnalyzedVideo(duration_seconds=60.0)
        db_session.add(video)
        db_session.commit()
        
        segment = VideoSegment(
            video_id=video.id,
            segment_type="hook",
            start_s=0.0,
            end_s=5.0,
            hook_type="pain",
            focus="automation overwhelm",
            emotion="frustration"
        )
        
        db_session.add(segment)
        db_session.commit()
        
        assert segment.id is not None
        assert segment.segment_type == "hook"
        assert segment.hook_type == "pain"
        assert segment.focus == "automation overwhelm"
    
    def test_segment_time_validation(self, db_session):
        """Test that end_s >= start_s constraint works"""
        video = AnalyzedVideo(duration_seconds=60.0)
        db_session.add(video)
        db_session.commit()
        
        # This should work
        segment = VideoSegment(
            video_id=video.id,
            segment_type="hook",
            start_s=0.0,
            end_s=5.0
        )
        db_session.add(segment)
        db_session.commit()
        
        assert segment.start_s <= segment.end_s


class TestVideoWordModel:
    """Test VideoWord model"""
    
    def test_create_video_word(self, db_session):
        """Test creating word with timestamp"""
        video = AnalyzedVideo(duration_seconds=60.0)
        db_session.add(video)
        db_session.commit()
        
        word = VideoWord(
            video_id=video.id,
            word_index=0,
            word="Hello",
            start_s=0.0,
            end_s=0.5,
            is_emphasis=True,
            sentiment_score=0.8
        )
        
        db_session.add(word)
        db_session.commit()
        
        assert word.word == "Hello"
        assert word.is_emphasis is True
        assert word.sentiment_score == 0.8
    
    def test_word_with_segment(self, db_session):
        """Test word linked to segment"""
        video = AnalyzedVideo(duration_seconds=60.0)
        db_session.add(video)
        db_session.commit()
        
        segment = VideoSegment(
            video_id=video.id,
            segment_type="hook",
            start_s=0.0,
            end_s=5.0
        )
        db_session.add(segment)
        db_session.commit()
        
        word = VideoWord(
            video_id=video.id,
            segment_id=segment.id,
            word_index=0,
            word="Test",
            start_s=0.0,
            end_s=0.5
        )
        
        db_session.add(word)
        db_session.commit()
        
        assert word.segment_id == segment.id


class TestVideoFrameModel:
    """Test VideoFrame model"""
    
    def test_create_video_frame(self, db_session):
        """Test creating frame with analysis"""
        video = AnalyzedVideo(duration_seconds=60.0)
        db_session.add(video)
        db_session.commit()
        
        frame = VideoFrame(
            video_id=video.id,
            frame_time_s=1.5,
            frame_url="/tmp/frame_001.jpg",
            shot_type="close_up",
            presence=["face", "laptop"],
            text_on_screen="Subscribe now!",
            is_hook_frame=True,
            visual_clutter_score=0.3
        )
        
        db_session.add(frame)
        db_session.commit()
        
        assert frame.shot_type == "close_up"
        assert "face" in frame.presence
        assert frame.is_hook_frame is True
        assert frame.visual_clutter_score == 0.3


class TestPlatformPostModel:
    """Test PlatformPost model"""
    
    def test_create_platform_post(self, db_session):
        """Test creating platform post"""
        post = PlatformPost(
            platform="tiktok",
            platform_post_id="123456789",
            platform_url="https://tiktok.com/@user/video/123456789",
            status="published",
            title="Test video",
            caption="Check this out!",
            hashtags=["viral", "content"]
        )
        
        db_session.add(post)
        db_session.commit()
        
        assert post.platform == "tiktok"
        assert post.platform_post_id == "123456789"
        assert "viral" in post.hashtags
    
    def test_platform_post_with_checkbacks(self, db_session):
        """Test post with checkback metrics"""
        post = PlatformPost(
            platform="instagram",
            platform_post_id="987654321",
            status="published"
        )
        db_session.add(post)
        db_session.commit()
        
        # Add checkback at 1 hour
        checkback = PlatformCheckback(
            platform_post_id=post.id,
            checkback_h=1,
            views=1200,
            likes=85,
            comments=12,
            like_rate=0.071
        )
        
        db_session.add(checkback)
        db_session.commit()
        
        assert len(post.checkbacks) == 1
        assert post.checkbacks[0].views == 1200


class TestPlatformCheckbackModel:
    """Test PlatformCheckback model"""
    
    def test_create_checkback(self, db_session):
        """Test creating checkback metrics"""
        post = PlatformPost(platform="youtube", platform_post_id="abc123")
        db_session.add(post)
        db_session.commit()
        
        checkback = PlatformCheckback(
            platform_post_id=post.id,
            checkback_h=24,
            views=5000,
            unique_viewers=4200,
            likes=320,
            comments=45,
            shares=78,
            saves=92,
            like_rate=0.064,
            save_rate=0.018,
            engaged_users=450
        )
        
        db_session.add(checkback)
        db_session.commit()
        
        assert checkback.checkback_h == 24
        assert checkback.views == 5000
        assert checkback.engaged_users == 450
    
    def test_unique_checkback_constraint(self, db_session):
        """Test that (post_id, checkback_h) is unique"""
        post = PlatformPost(platform="tiktok", platform_post_id="test123")
        db_session.add(post)
        db_session.commit()
        
        checkback1 = PlatformCheckback(
            platform_post_id=post.id,
            checkback_h=1,
            views=100
        )
        db_session.add(checkback1)
        db_session.commit()
        
        # This should work - different checkback time
        checkback2 = PlatformCheckback(
            platform_post_id=post.id,
            checkback_h=6,
            views=500
        )
        db_session.add(checkback2)
        db_session.commit()
        
        assert len(post.checkbacks) == 2


class TestPostCommentModel:
    """Test PostComment model"""
    
    def test_create_comment(self, db_session):
        """Test creating comment with sentiment"""
        post = PlatformPost(platform="instagram", platform_post_id="post123")
        db_session.add(post)
        db_session.commit()
        
        comment = PostComment(
            platform_post_id=post.id,
            platform_comment_id="comment456",
            author_handle="@user",
            text="This is amazing! Love it",
            sentiment_score=0.9,
            emotion_tags=["excited", "grateful"],
            intent="praise"
        )
        
        db_session.add(comment)
        db_session.commit()
        
        assert comment.sentiment_score == 0.9
        assert "excited" in comment.emotion_tags
        assert comment.intent == "praise"
    
    def test_cta_response_tracking(self, db_session):
        """Test CTA response tracking"""
        post = PlatformPost(platform="tiktok", platform_post_id="post789")
        db_session.add(post)
        db_session.commit()
        
        comment = PostComment(
            platform_post_id=post.id,
            platform_comment_id="cmt123",
            author_handle="@follower",
            text="Tech",
            is_cta_response=True,
            cta_keyword="Tech"
        )
        
        db_session.add(comment)
        db_session.commit()
        
        assert comment.is_cta_response is True
        assert comment.cta_keyword == "Tech"


class TestWeeklyMetricModel:
    """Test WeeklyMetric model"""
    
    def test_create_weekly_metric(self, db_session):
        """Test creating weekly North Star metrics"""
        from datetime import date
        
        metric = WeeklyMetric(
            week_start_date=date(2025, 11, 18),
            engaged_reach=2500,
            content_leverage_score=12.5,
            warm_lead_flow=85,
            total_posts=15,
            total_views=35000
        )
        
        db_session.add(metric)
        db_session.commit()
        
        assert metric.engaged_reach == 2500
        assert metric.content_leverage_score == 12.5
        assert metric.total_posts == 15


class TestContentInsightModel:
    """Test ContentInsight model"""
    
    def test_create_insight(self, db_session):
        """Test creating AI insight"""
        insight = ContentInsight(
            insight_type="hook",
            title="Pain hooks perform 23% better",
            description="Videos starting with a pain-point hook have higher retention",
            metric_impact="+23% retention",
            sample_size=45,
            confidence_score=0.85,
            pattern_data={"hook_type": "pain", "avg_retention": 0.78}
        )
        
        db_session.add(insight)
        db_session.commit()
        
        assert insight.insight_type == "hook"
        assert insight.confidence_score == 0.85
        assert insight.pattern_data["hook_type"] == "pain"


class TestCascadeDeletes:
    """Test cascade delete behavior"""
    
    def test_delete_video_cascades(self, db_session):
        """Test that deleting video deletes related records"""
        video = AnalyzedVideo(duration_seconds=60.0)
        db_session.add(video)
        db_session.commit()
        
        # Add related records
        segment = VideoSegment(video_id=video.id, segment_type="hook", start_s=0, end_s=5)
        word = VideoWord(video_id=video.id, word_index=0, word="Test", start_s=0, end_s=0.5)
        frame = VideoFrame(video_id=video.id, frame_time_s=1.0)
        
        db_session.add_all([segment, word, frame])
        db_session.commit()
        
        video_id = video.id
        
        # Delete video
        db_session.delete(video)
        db_session.commit()
        
        # Verify cascaded deletes
        assert db_session.query(VideoSegment).filter_by(video_id=video_id).count() == 0
        assert db_session.query(VideoWord).filter_by(video_id=video_id).count() == 0
        assert db_session.query(VideoFrame).filter_by(video_id=video_id).count() == 0
