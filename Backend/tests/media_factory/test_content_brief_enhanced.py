"""
Enhanced Content Brief Tests
============================
Tests for enhanced content brief service.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from services.content_brief_enhanced.models import (
    TrendCard, TrendCluster, BriefAngle, EnhancedBrief, BriefScore
)
from services.content_brief_enhanced.scoring import BriefScorer
from services.content_brief_enhanced.clustering import TrendClusterer
from services.content_brief_enhanced.angle_generator import AngleGenerator
from services.content_brief_enhanced.service import EnhancedBriefService


class TestBriefScoring:
    """Test brief scoring system."""
    
    @pytest.fixture
    def scorer(self):
        """Create brief scorer."""
        return BriefScorer()
    
    def test_score_trend_card(self, scorer):
        """Test scoring a trend card."""
        card = TrendCard(
            trend_id="test_123",
            trend_type="hashtag",
            trend_name="testtrend",
            platform="instagram",
            views_growth=100.0,
            shares_save_rate=0.15,
            comment_rate=0.10,
            top_comments=["how do i", "what tool", "template"],
            repeated_questions=["how to", "link"]
        )
        
        score = scorer.score_trend_card(card)
        
        assert score.total >= 0.0
        assert score.total <= 100.0
        assert score.velocity >= 0.0
        assert score.intent >= 0.0
        assert score.product_fit >= 0.0
    
    def test_is_worth_covering(self, scorer):
        """Test worth covering check."""
        high_score = BriefScore(total=85.0)
        low_score = BriefScore(total=50.0)
        
        assert scorer.is_worth_covering(high_score, threshold=70.0) is True
        assert scorer.is_worth_covering(low_score, threshold=70.0) is False
        assert scorer.is_worth_covering(low_score, threshold=70.0, strategic_threshold=60.0, is_strategic=True) is False
        assert scorer.is_worth_covering(BriefScore(total=65.0), threshold=70.0, strategic_threshold=60.0, is_strategic=True) is True


class TestTrendClustering:
    """Test trend clustering."""
    
    @pytest.fixture
    def clusterer(self):
        """Create trend clusterer."""
        return TrendClusterer()
    
    def test_cluster_trends(self, clusterer):
        """Test clustering trends."""
        trends = [
            TrendCard(
                trend_id="1",
                trend_type="hashtag",
                trend_name="test trend",
                platform="instagram"
            ),
            TrendCard(
                trend_id="2",
                trend_type="hashtag",
                trend_name="test trend",
                platform="tiktok"
            ),
            TrendCard(
                trend_id="3",
                trend_type="hashtag",
                trend_name="different trend",
                platform="instagram"
            )
        ]
        
        clusters = clusterer.cluster_trends(trends)
        
        assert len(clusters) > 0
        # Similar trends should be clustered together
        assert any(len(cluster.trends) > 1 for cluster in clusters)


class TestAngleGenerator:
    """Test angle generator."""
    
    @pytest.fixture
    def generator(self):
        """Create angle generator."""
        return AngleGenerator()
    
    def test_generate_angles(self, generator):
        """Test angle generation."""
        cluster = TrendCluster(
            cluster_id="test_cluster",
            name="test trend",
            trends=[]
        )
        
        angles = generator.generate_angles(cluster, count=8)
        
        assert len(angles) == 8
        assert all(angle.cluster_id == cluster.cluster_id for angle in angles)
        assert all(angle.promise for angle in angles)
        assert all(angle.unique_lens for angle in angles)


class TestEnhancedBriefService:
    """Test enhanced brief service."""
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        bus = Mock()
        bus.publish = AsyncMock()
        return bus
    
    @pytest.fixture
    def service(self, event_bus):
        """Create enhanced brief service."""
        return EnhancedBriefService(event_bus)
    
    @pytest.mark.asyncio
    async def test_process_trends_to_briefs(self, service, event_bus):
        """Test processing trends to briefs."""
        trends = [
            TrendCard(
                trend_id="1",
                trend_type="hashtag",
                trend_name="test trend",
                platform="instagram",
                views_growth=100.0,
                shares_save_rate=0.15,
                comment_rate=0.10,
                top_comments=["how do i", "what tool", "template"],
                repeated_questions=["how to", "link"]
            )
        ]
        
        briefs = await service.process_trends_to_briefs(trends, min_score=70.0)
        
        # Should generate briefs if trends score high enough
        assert isinstance(briefs, list)
        # All briefs should meet the threshold
        assert all(brief.score.total >= 70.0 for brief in briefs if brief.score)

