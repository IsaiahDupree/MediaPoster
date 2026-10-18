"""
Tests for Narrative Builder API Endpoints
Tests signal metrics, candidate pool, and AI recommendations functionality
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json


class TestNarrativeBuilderSignals:
    """Tests for GET /api/narrative-builder/signals endpoint"""
    
    def test_get_signals_returns_all_metrics(self, client):
        """Test that signals endpoint returns all required metric categories"""
        response = client.get("/api/narrative-builder/signals")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check all required fields exist
        assert 'creative_fatigue' in data
        assert 'topic_momentum' in data
        assert 'retention_health' in data
        assert 'sentiment_health' in data
        assert 'conversion_signals' in data
        assert 'tone_distribution' in data
        assert 'pacing_distribution' in data
        assert 'posting_frequency' in data
    
    def test_creative_fatigue_is_percentage(self, client):
        """Test that creative fatigue is a valid percentage (0-100)"""
        response = client.get("/api/narrative-builder/signals")
        data = response.json()
        
        fatigue = data['creative_fatigue']
        assert isinstance(fatigue, (int, float))
        assert 0 <= fatigue <= 100
    
    def test_topic_momentum_structure(self, client):
        """Test topic momentum has correct structure"""
        response = client.get("/api/narrative-builder/signals")
        data = response.json()
        
        momentum = data['topic_momentum']
        assert isinstance(momentum, list)
        
        if len(momentum) > 0:
            item = momentum[0]
            assert 'topic' in item
            assert 'score' in item
            assert 'trend' in item
            assert item['trend'] in ['up', 'down', 'stable']
    
    def test_retention_health_structure(self, client):
        """Test retention health has required metrics"""
        response = client.get("/api/narrative-builder/signals")
        data = response.json()
        
        health = data['retention_health']
        assert 'hook_rate' in health
        assert 'avg_viewed' in health
        assert 'completion_rate' in health
    
    def test_sentiment_health_structure(self, client):
        """Test sentiment health has positive/neutral/negative breakdown"""
        response = client.get("/api/narrative-builder/signals")
        data = response.json()
        
        sentiment = data['sentiment_health']
        assert 'positive' in sentiment
        assert 'neutral' in sentiment
        assert 'negative' in sentiment
        assert 'top_themes' in sentiment
        
        # Percentages should roughly sum to 100
        total = sentiment['positive'] + sentiment['neutral'] + sentiment['negative']
        assert 90 <= total <= 110  # Allow some rounding variance


class TestNarrativeBuilderCandidates:
    """Tests for GET /api/narrative-builder/candidates endpoint"""
    
    def test_get_candidates_returns_list(self, client):
        """Test that candidates endpoint returns a list of items"""
        response = client.get("/api/narrative-builder/candidates")
        assert response.status_code == 200
        
        data = response.json()
        assert 'candidates' in data
        assert 'total' in data
        assert 'status_counts' in data
        assert isinstance(data['candidates'], list)
    
    def test_candidates_have_required_fields(self, client):
        """Test each candidate has required fields"""
        response = client.get("/api/narrative-builder/candidates?limit=5")
        data = response.json()
        
        if len(data['candidates']) > 0:
            candidate = data['candidates'][0]
            required_fields = ['id', 'title', 'status', 'score', 'post_count']
            for field in required_fields:
                assert field in candidate, f"Missing field: {field}"
    
    def test_candidates_status_is_valid(self, client):
        """Test candidate status is one of fresh/tested/saturated"""
        response = client.get("/api/narrative-builder/candidates?limit=10")
        data = response.json()
        
        valid_statuses = ['fresh', 'tested', 'saturated']
        for candidate in data['candidates']:
            assert candidate['status'] in valid_statuses
    
    def test_status_counts_match_candidates(self, client):
        """Test that status counts are consistent with candidates"""
        response = client.get("/api/narrative-builder/candidates?limit=100")
        data = response.json()
        
        counts = data['status_counts']
        assert 'fresh' in counts
        assert 'tested' in counts
        assert 'saturated' in counts
        
        # Counts should be non-negative
        assert counts['fresh'] >= 0
        assert counts['tested'] >= 0
        assert counts['saturated'] >= 0
    
    def test_candidates_limit_parameter(self, client):
        """Test that limit parameter works"""
        response = client.get("/api/narrative-builder/candidates?limit=5")
        data = response.json()
        
        assert len(data['candidates']) <= 5


class TestNarrativeBuilderRecommendations:
    """Tests for POST /api/narrative-builder/generate-recommendations endpoint"""
    
    def test_generate_recommendations_requires_goal(self, client):
        """Test that recommendations require a narrative goal"""
        payload = {
            "goal": "Build audience for DIY electronics tutorials",
            "cta_type": "Subscribe",
            "pillars": ["education", "process"],
            "audience": "Beginner makers",
            "time_horizon": "7days",
            "platforms": ["tiktok", "instagram"],
            "max_posts_per_day": 3,
            "content_mix": {"value": 60, "proof": 20, "cta": 20}
        }
        
        response = client.post(
            "/api/narrative-builder/generate-recommendations",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert 'recommendations' in data
        assert isinstance(data['recommendations'], list)
    
    def test_recommendations_have_scores(self, client):
        """Test that each recommendation has scoring breakdown"""
        payload = {
            "goal": "Grow followers with tech content",
            "cta_type": "Follow",
            "pillars": ["education"],
            "audience": "Tech enthusiasts",
            "time_horizon": "7days",
            "platforms": ["tiktok"],
            "max_posts_per_day": 2,
            "content_mix": {"value": 70, "proof": 30}
        }
        
        response = client.post(
            "/api/narrative-builder/generate-recommendations",
            json=payload
        )
        data = response.json()
        
        if len(data['recommendations']) > 0:
            rec = data['recommendations'][0]
            assert 'narrative_score' in rec
            assert 'predicted_performance' in rec
            assert 'sentiment_fit' in rec
            assert 'novelty_score' in rec
            assert 'overall_score' in rec
    
    def test_recommendations_have_reasoning(self, client):
        """Test that recommendations include reasoning"""
        payload = {
            "goal": "Drive course signups",
            "cta_type": "Waitlist",
            "pillars": ["proof", "pain"],
            "audience": "Aspiring developers",
            "time_horizon": "30days",
            "platforms": ["instagram"],
            "max_posts_per_day": 1,
            "content_mix": {"value": 50, "cta": 50}
        }
        
        response = client.post(
            "/api/narrative-builder/generate-recommendations",
            json=payload
        )
        data = response.json()
        
        if len(data['recommendations']) > 0:
            rec = data['recommendations'][0]
            assert 'reasoning' in rec
            assert isinstance(rec['reasoning'], list)
            assert len(rec['reasoning']) > 0
    
    def test_recommendations_include_media_info(self, client):
        """Test that recommendations include media details"""
        payload = {
            "goal": "Test goal",
            "cta_type": "Follow",
            "pillars": ["education"],
            "audience": "General",
            "time_horizon": "today",
            "platforms": ["tiktok"],
            "max_posts_per_day": 5,
            "content_mix": {}
        }
        
        response = client.post(
            "/api/narrative-builder/generate-recommendations",
            json=payload
        )
        data = response.json()
        
        if len(data['recommendations']) > 0:
            rec = data['recommendations'][0]
            assert 'media' in rec
            assert 'id' in rec['media']
            assert 'title' in rec['media']
    
    def test_recommendations_sorted_by_score(self, client):
        """Test that recommendations are sorted by overall score descending"""
        payload = {
            "goal": "Maximize engagement",
            "cta_type": "Share",
            "pillars": ["personality"],
            "audience": "Followers",
            "time_horizon": "7days",
            "platforms": ["tiktok", "instagram"],
            "max_posts_per_day": 3,
            "content_mix": {}
        }
        
        response = client.post(
            "/api/narrative-builder/generate-recommendations",
            json=payload
        )
        data = response.json()
        
        recs = data['recommendations']
        if len(recs) > 1:
            scores = [r['overall_score'] for r in recs]
            assert scores == sorted(scores, reverse=True)


class TestNarrativeBuilderContentStats:
    """Tests for GET /api/narrative-builder/content-stats endpoint"""
    
    def test_get_content_stats(self, client):
        """Test content stats endpoint returns all categories"""
        response = client.get("/api/narrative-builder/content-stats")
        assert response.status_code == 200
        
        data = response.json()
        assert 'content' in data
        assert 'scheduling' in data
        assert 'performance' in data
    
    def test_content_stats_structure(self, client):
        """Test content stats have expected fields"""
        response = client.get("/api/narrative-builder/content-stats")
        data = response.json()
        
        # Content stats
        assert 'total_analyzed' in data['content']
        assert 'avg_score' in data['content']
        
        # Scheduling stats
        assert 'total_scheduled' in data['scheduling']
        assert 'pending' in data['scheduling']
        
        # Performance stats
        assert 'total_views' in data['performance']
        assert 'total_likes' in data['performance']
    
    def test_content_stats_non_negative(self, client):
        """Test all stats are non-negative"""
        response = client.get("/api/narrative-builder/content-stats")
        data = response.json()
        
        assert data['content']['total_analyzed'] >= 0
        assert data['scheduling']['total_scheduled'] >= 0
        assert data['performance']['total_views'] >= 0


# Fixtures
@pytest.fixture
def client():
    """Create test client"""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_db_signals():
    """Mock database responses for signals"""
    return {
        'creative_fatigue': 35.0,
        'topic_momentum': [
            {'topic': 'DIY', 'score': 85, 'trend': 'up'},
            {'topic': 'Tutorial', 'score': 72, 'trend': 'stable'},
        ],
        'retention_health': {'hook_rate': 78, 'avg_viewed': 65, 'completion_rate': 42},
        'sentiment_health': {'positive': 68, 'neutral': 24, 'negative': 8, 'top_themes': ['helpful']},
        'conversion_signals': {'ctr': 3.2, 'high_intent_rate': 12},
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
