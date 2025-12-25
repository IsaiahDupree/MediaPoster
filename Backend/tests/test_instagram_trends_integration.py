"""
Integration Tests for Instagram Trends API
Tests complete API workflows end-to-end
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from main import app

client = TestClient(app)


class TestTrendsAPIIntegration:
    """Integration tests for trends endpoints"""
    
    def test_get_trending_audio(self):
        """Test GET /api/trends/audio endpoint"""
        response = client.get("/api/trends/audio?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "audio" in data
        assert isinstance(data["audio"], list)
    
    def test_get_trending_hashtags(self):
        """Test GET /api/trends/hashtags endpoint"""
        response = client.get("/api/trends/hashtags?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "hashtags" in data
        assert isinstance(data["hashtags"], list)
    
    def test_get_trending_formats(self):
        """Test GET /api/trends/formats endpoint"""
        response = client.get("/api/trends/formats?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "formats" in data
        assert isinstance(data["formats"], list)
    
    def test_get_trend_cards(self):
        """Test GET /api/trends/cards endpoint"""
        response = client.get("/api/trends/cards")
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "cards" in data
        assert isinstance(data["cards"], list)
    
    def test_seed_trend_cards(self):
        """Test POST /api/trends/cards/seed endpoint"""
        with patch('services.instagram.trend_cards_library.TrendCardsLibrary.seed_initial_cards') as mock_seed:
            mock_seed.return_value = 20
            
            response = client.post("/api/trends/cards/seed")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["cards_seeded"] == 20
    
    def test_get_trend_stats(self):
        """Test GET /api/trends/stats endpoint"""
        response = client.get("/api/trends/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_audio" in data
        assert "total_hashtags" in data
        assert "total_formats" in data


class TestPostingOptimizerIntegration:
    """Integration tests for posting optimizer endpoints"""
    
    def test_get_best_times(self):
        """Test GET /api/posting-optimizer/best-times endpoint"""
        response = client.get("/api/posting-optimizer/best-times?top_n=5")
        
        assert response.status_code == 200
        data = response.json()
        assert "best_times" in data
        assert isinstance(data["best_times"], list)
        assert len(data["best_times"]) <= 5
    
    def test_get_hourly_performance(self):
        """Test GET /api/posting-optimizer/performance/hourly endpoint"""
        response = client.get("/api/posting-optimizer/performance/hourly")
        
        assert response.status_code == 200
        data = response.json()
        assert "hours" in data
        assert isinstance(data["hours"], list)
        assert len(data["hours"]) == 24
    
    def test_get_daily_performance(self):
        """Test GET /api/posting-optimizer/performance/daily endpoint"""
        response = client.get("/api/posting-optimizer/performance/daily")
        
        assert response.status_code == 200
        data = response.json()
        assert "days" in data
        assert isinstance(data["days"], list)
        assert len(data["days"]) == 7
    
    def test_suggest_posting_schedule(self):
        """Test GET /api/posting-optimizer/schedule/suggest endpoint"""
        response = client.get("/api/posting-optimizer/schedule/suggest?posts_per_week=7")
        
        assert response.status_code == 200
        data = response.json()
        assert "schedule" in data
        assert isinstance(data["schedule"], list)


class TestHashtagGeneratorIntegration:
    """Integration tests for hashtag generator endpoints"""
    
    @patch('services.instagram.hashtag_generator.openai.ChatCompletion.acreate')
    def test_generate_hashtags(self, mock_openai):
        """Test POST /api/hashtags/generate endpoint"""
        # Mock OpenAI response for niche detection
        mock_openai.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="fitness"))]
        )
        
        payload = {
            "content": "Morning workout routine at home",
            "niche": "fitness"
        }
        
        response = client.post("/api/hashtags/generate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "trending" in data
        assert "niche" in data
        assert "long_tail" in data
        assert "detected_niche" in data
        assert "total_count" in data
    
    def test_analyze_hashtag(self):
        """Test GET /api/hashtags/analyze/{hashtag} endpoint"""
        response = client.get("/api/hashtags/analyze/fitness")
        
        assert response.status_code == 200
        data = response.json()
        assert "tag" in data
        assert "found" in data
        assert "competition" in data
        assert "recommendation" in data
    
    def test_get_hashtag_suggestions(self):
        """Test GET /api/hashtags/suggestions/{category} endpoint"""
        response = client.get("/api/hashtags/suggestions/fitness?limit=30")
        
        assert response.status_code == 200
        data = response.json()
        assert "category" in data
        assert "hashtags" in data
        assert isinstance(data["hashtags"], list)


class TestContentAnalyzerIntegration:
    """Integration tests for content analyzer endpoints"""
    
    @patch('services.instagram.content_analyzer.openai.ChatCompletion.acreate')
    def test_quick_analyze(self, mock_openai):
        """Test POST /api/content-analyzer/analyze/quick endpoint"""
        # Mock OpenAI responses
        mock_openai.side_effect = [
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content="curiosity"))]),  # Hook type
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content="positive"))]),   # Sentiment
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content='[{"title":"Test","description":"Test rec","priority":"high","category":"hook"}]'))])  # Recommendations
        ]
        
        form_data = {
            "transcript": "Check out this amazing workout routine!",
            "caption": "Morning fitness",
            "duration_sec": "30"
        }
        
        response = client.post("/api/content-analyzer/analyze/quick", data=form_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "hook_type" in data
        assert "pacing" in data
        assert "recommendations" in data
    
    def test_get_analyzer_stats(self):
        """Test GET /api/content-analyzer/stats endpoint"""
        response = client.get("/api/content-analyzer/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "completed" in data
        assert "failed" in data


class TestInstagramDataIntegration:
    """Integration tests for Instagram data endpoints"""
    
    @patch('services.instagram.instagram_service.InstagramService.fetch_and_save_profile')
    def test_get_instagram_profile(self, mock_fetch):
        """Test GET /api/instagram/profile/{identifier} endpoint"""
        from services.instagram.adapters import Profile
        
        mock_fetch.return_value = Profile(
            id="123",
            username="testuser",
            full_name="Test User",
            bio="Test bio",
            followers_count=1000,
            following_count=500,
            media_count=100,
            is_verified=False,
            profile_pic_url="https://example.com/pic.jpg",
            provider="rapidapi"
        )
        
        response = client.get("/api/instagram/profile/testuser")
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["followers_count"] == 1000
    
    def test_instagram_health_check(self):
        """Test GET /api/instagram/health endpoint"""
        with patch('services.instagram.adapters.RapidApiInstagramAdapter.is_healthy') as mock_health:
            mock_health.return_value = True
            
            response = client.get("/api/instagram/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "provider" in data


class TestEndToEndWorkflow:
    """End-to-end tests for complete workflows"""
    
    @patch('services.instagram.content_analyzer.openai.ChatCompletion.acreate')
    @patch('services.instagram.hashtag_generator.openai.ChatCompletion.acreate')
    def test_complete_content_optimization_workflow(self, mock_hashtag_ai, mock_analyzer_ai):
        """Test complete workflow: analyze content -> generate hashtags -> get best time"""
        
        # Mock AI responses
        mock_analyzer_ai.side_effect = [
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content="text-based"))]),
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content="positive"))]),
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content='[{"title":"Improve Hook","description":"Add question","priority":"high","category":"hook"}]'))])
        ]
        
        mock_hashtag_ai.side_effect = [
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content="fitness"))]),
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content="morningworkout,homefitness,quickexercise"))])
        ]
        
        # Step 1: Analyze content
        analysis_data = {
            "transcript": "Here's my morning workout routine!",
            "caption": "Quick fitness tips",
            "duration_sec": "30"
        }
        
        analysis_response = client.post("/api/content-analyzer/analyze/quick", data=analysis_data)
        assert analysis_response.status_code == 200
        analysis_result = analysis_response.json()
        
        # Step 2: Generate hashtags
        hashtag_payload = {
            "content": "Morning workout routine",
            "niche": "fitness"
        }
        
        hashtag_response = client.post("/api/hashtags/generate", json=hashtag_payload)
        assert hashtag_response.status_code == 200
        hashtag_result = hashtag_response.json()
        assert hashtag_result["total_count"] > 0
        
        # Step 3: Get best posting time
        time_response = client.get("/api/posting-optimizer/best-times?top_n=1")
        assert time_response.status_code == 200
        time_result = time_response.json()
        assert len(time_result["best_times"]) > 0
        
        # Verify complete workflow
        assert analysis_result["hook_type"] is not None
        assert len(analysis_result["recommendations"]) > 0
        assert hashtag_result["detected_niche"] == "fitness"
        assert time_result["best_times"][0]["hour"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
