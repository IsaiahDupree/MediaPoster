"""
Tests for Metrics Service (PRD2)
Verifies polling logic, score calculation, and sentiment analysis
Target: ~30 tests
"""
import pytest
from uuid import uuid4
from services.prd2.metrics_service import MetricsService
from models.supabase_models import PostingMetrics, SentimentLabel, Platform

class TestMetricsService:
    """Tests for metrics tracking"""

    @pytest.fixture
    def service(self):
        return MetricsService()

    @pytest.fixture
    def empty_metrics(self):
        return PostingMetrics(schedule_id=uuid4())

    # ============================================
    # Polling Logic Tests
    # ============================================

    def test_poll_metrics_viral(self, service, empty_metrics):
        """Test polling high-performing content"""
        service.poll_metrics(empty_metrics, "viral_123", Platform.TIKTOK)
        
        assert empty_metrics.views == 1000000
        assert empty_metrics.likes == 100000
        assert empty_metrics.post_social_score > 50.0

    def test_poll_metrics_average(self, service, empty_metrics):
        """Test polling average content"""
        service.poll_metrics(empty_metrics, "avg_123", Platform.TIKTOK)
        
        assert empty_metrics.views == 100
        assert empty_metrics.post_social_score < 100.0

    def test_calculate_score_logic(self, service, empty_metrics):
        """Test exact score formula"""
        # 100 views, 10 likes = 10% engagement => 100 score
        empty_metrics.views = 100
        empty_metrics.likes = 10
        empty_metrics.comments_count = 0
        empty_metrics.shares = 0
        
        score = service._calculate_post_social_score(empty_metrics)
        assert score == 100.0

    def test_calculate_score_zero_views(self, service, empty_metrics):
        """Test zero division safety"""
        empty_metrics.views = 0
        score = service._calculate_post_social_score(empty_metrics)
        assert score == 0.0

    def test_calculate_score_cap(self, service, empty_metrics):
        """Test score cap at 100"""
        empty_metrics.views = 100
        empty_metrics.likes = 200 # Impossible normally, but testing logic cap
        score = service._calculate_post_social_score(empty_metrics)
        assert score == 100.0

    # ============================================
    # Comment Processing Tests
    # ============================================

    def test_process_comments_positive(self, service):
        """Test handling positive comments"""
        raw = [{"id": "c1", "author": "u1", "text": "Love this video", "likes": 5}]
        comments = service.process_comments(uuid4(), raw)
        
        assert len(comments) == 1
        assert comments[0].sentiment_label == SentimentLabel.POSITIVE
        assert "praise" in comments[0].topic_tags

    def test_process_comments_negative(self, service):
        """Test handling negative comments"""
        raw = [{"id": "c2", "author": "u2", "text": "Worst content ever", "likes": 0}]
        comments = service.process_comments(uuid4(), raw)
        
        assert comments[0].sentiment_label == SentimentLabel.NEGATIVE
        assert comments[0].sentiment_score < 0

    def test_process_comments_neutral(self, service):
        """Test handling neutral comments"""
        raw = [{"id": "c3", "author": "u3", "text": "Just ok", "likes": 1}]
        comments = service.process_comments(uuid4(), raw)
        
        assert comments[0].sentiment_label == SentimentLabel.NEUTRAL
        assert comments[0].topic_tags == []

    def test_process_comments_structure(self, service):
        """Test comment object mapping"""
        raw = [{"id": "c1", "author": "foo", "text": "bar", "likes": 99}]
        sid = uuid4()
        c = service.process_comments(sid, raw)[0]
        
        assert c.schedule_id == sid
        assert c.platform_comment_id == "c1"
        assert c.author_handle == "foo"
        assert c.like_count == 99

    def test_process_empty_comments(self, service):
        """Test processing no comments"""
        assert service.process_comments(uuid4(), []) == []
