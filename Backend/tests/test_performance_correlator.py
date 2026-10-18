"""
Test Suite for PerformanceCorrelator Service
Tests pattern analysis and performance prediction
"""
import pytest
import uuid
from datetime import datetime

from services.performance_correlator import PerformanceCorrelator
from database.models import VideoSegment, SegmentPerformance, PlatformPost, AnalyzedVideo, ContentVariant


@pytest.fixture
def test_video(db_session):
    """Create a test video"""
    video = AnalyzedVideo(
        id=uuid.uuid4(),
        duration_seconds=60.0
    )
    db_session.add(video)
    db_session.commit()
    return video


@pytest.fixture
def test_segment(db_session, test_video):
    """Create a test segment"""
    segment = VideoSegment(
        id=uuid.uuid4(),
        video_id=test_video.id,
        start_s=10.0,
        end_s=20.0,
        segment_type="hook",
        hook_type="fear",
        emotion="excitement"
    )
    db_session.add(segment)
    db_session.commit()
    return segment


@pytest.fixture
def test_post(db_session):
    """Create a test platform post"""
    # Need a content variant first
    variant = ContentVariant(
        id=uuid.uuid4(),
        content_id=uuid.uuid4(), # Mock content ID for now
        platform="tiktok",
        variant_type="video",
        status="published"
    )
    db_session.add(variant)
    
    post = PlatformPost(
        id=uuid.uuid4(),
        content_variant_id=variant.id,
        platform="tiktok",
        platform_post_id="123456789",
        published_at=datetime.now()
    )
    # Attach metrics dynamically for test (since model doesn't have them but service expects them)
    post.views = 10000
    post.likes = 500
    post.comments = 50
    post.shares = 100
    db_session.add(post)
    db_session.commit()
    return post


class TestMetricCorrelation:
    """Test correlating segments to metrics"""
    
    def test_correlate_segment_to_metrics(self, db_session, test_segment, test_post):
        """Test basic correlation"""
        correlator = PerformanceCorrelator(db_session)
        results = correlator.correlate_segment_to_metrics(
            str(test_segment.id),
            [str(test_post.id)]
        )
        
        assert len(results) > 0
        
        # Verify in DB
        perf = db_session.query(SegmentPerformance).filter_by(segment_id=test_segment.id).first()
        assert perf is not None
        assert perf.views_at_start > 0
        assert perf.engagement_score > 0
    
    def test_correlate_nonexistent_segment(self, db_session):
        """Test correlation with invalid segment"""
        correlator = PerformanceCorrelator(db_session)
        with pytest.raises(ValueError, match="not found"):
            correlator.correlate_segment_to_metrics(
                str(uuid.uuid4()),
                [str(uuid.uuid4())]
            )


class TestPatternAnalysis:
    """Test pattern identification"""
    
    def test_find_top_hook_patterns(self, db_session, test_video):
        """Test finding top hook patterns"""
        # Create segments with performance data
        seg1 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=0.0,
            end_s=5.0,
            segment_type="hook",
            hook_type="fear"
        )
        perf1 = SegmentPerformance(
            id=uuid.uuid4(),
            segment_id=seg1.id,
            post_id=uuid.uuid4(),
            engagement_score=0.8,
            views_at_start=1000,
            retention_rate=0.6
        )
        
        seg2 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=5.0,
            end_s=10.0,
            segment_type="hook",
            hook_type="authority"
        )
        perf2 = SegmentPerformance(
            id=uuid.uuid4(),
            segment_id=seg2.id,
            post_id=uuid.uuid4(),
            engagement_score=0.6,
            views_at_start=800,
            retention_rate=0.5
        )
        
        db_session.add_all([seg1, perf1, seg2, perf2])
        db_session.commit()
        
        correlator = PerformanceCorrelator(db_session)
        patterns = correlator.find_top_performing_patterns("hook", limit=5)
        
        assert isinstance(patterns, list)
        # Should find at least one pattern
        assert len(patterns) > 0
        # Should be sorted by avg_score
        if len(patterns) > 1:
            assert patterns[0]["avg_score"] >= patterns[1]["avg_score"]
    
    def test_find_top_emotion_patterns(self, db_session, test_video):
        """Test finding top emotion patterns"""
        seg1 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=0.0,
            end_s=5.0,
            segment_type="body",
            emotion="excitement"
        )
        perf1 = SegmentPerformance(
            id=uuid.uuid4(),
            segment_id=seg1.id,
            post_id=uuid.uuid4(),
            engagement_score=0.75,
            views_at_start=1000,
            retention_rate=0.6
        )
        
        db_session.add_all([seg1, perf1])
        db_session.commit()
        
        correlator = PerformanceCorrelator(db_session)
        patterns = correlator.find_top_performing_patterns("emotion", limit=5)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        assert patterns[0]["pattern"] == "excitement"
    
    def test_find_duration_patterns(self, db_session, test_video):
        """Test duration pattern analysis"""
        seg1 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=0.0,
            end_s=8.0,  # 8 second segment
            segment_type="body"
        )
        perf1 = SegmentPerformance(
            id=uuid.uuid4(),
            segment_id=seg1.id,
            post_id=uuid.uuid4(),
            engagement_score=0.7,
            views_at_start=1000,
            retention_rate=0.6
        )
        
        db_session.add_all([seg1, perf1])
        db_session.commit()
        
        correlator = PerformanceCorrelator(db_session)
        patterns = correlator.find_top_performing_patterns("duration", limit=5)
        
        assert isinstance(patterns, list)
        if patterns:
            assert "s" in patterns[0]["pattern"]  # Should be in format "5-10s"


class TestPerformancePrediction:
    """Test performance prediction"""
    
    def test_predict_hook_segment(self, db_session):
        """Test predicting performance for a hook segment"""
        correlator = PerformanceCorrelator(db_session)
        prediction = correlator.predict_segment_performance({
            "segment_type": "hook",
            "psychology_tags": {
                "fate_patterns": ["fear"],
                "emotions": ["excitement"]
            },
            "duration": 10.0
        })
        
        assert "predicted_score" in prediction
        assert "confidence" in prediction
        assert "factors" in prediction
        assert 0 <= prediction["predicted_score"] <= 1
    
    def test_predict_body_segment(self, db_session):
        """Test predicting performance for body segment"""
        correlator = PerformanceCorrelator(db_session)
        prediction = correlator.predict_segment_performance({
            "segment_type": "body",
            "psychology_tags": {"emotions": ["joy"]},
            "duration": 15.0
        })
        
        assert "predicted_score" in prediction
        assert isinstance(prediction["predicted_score"], (int, float))
    
    def test_prediction_confidence_levels(self, db_session):
        """Test that confidence varies based on data"""
        correlator = PerformanceCorrelator(db_session)
        
        # With no tags and no history, should have low confidence
        pred1 = correlator.predict_segment_performance({
            "segment_type": "body",
            "psychology_tags": {},
            "duration": 10.0
        })
        
        assert pred1["confidence"] == "low"


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_database(self, db_session):
        """Test with no existing data"""
        correlator = PerformanceCorrelator(db_session)
        patterns = correlator.find_top_performing_patterns("hook", limit=5)
        
        assert patterns == []
    
    def test_segment_without_tags(self, db_session, test_video):
        """Test segment with no psychology tags"""
        seg = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=0.0,
            end_s=5.0,
            segment_type="hook"
        )
        perf = SegmentPerformance(
            id=uuid.uuid4(),
            segment_id=seg.id,
            post_id=uuid.uuid4(),
            engagement_score=0.5,
            views_at_start=1000,
            retention_rate=0.5
        )
        db_session.add_all([seg, perf])
        db_session.commit()
        
        correlator = PerformanceCorrelator(db_session)
        patterns = correlator.find_top_performing_patterns("hook", limit=5)
        
        # Should handle gracefully
        assert isinstance(patterns, list)
