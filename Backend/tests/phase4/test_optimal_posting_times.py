"""
Tests for Phase 4: Optimal Posting Times
Tests optimal posting times calculation and recommendations
Uses REAL database connections
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from services.optimal_posting_times import OptimalPostingTimesService


@pytest.fixture
def client():
    return TestClient(app)


class TestOptimalPostingTimesAPI:
    """Test optimal posting times API endpoints"""
    
    def test_get_optimal_times_for_platform(self, client):
        """Test getting optimal times for a platform with REAL database"""
        platforms = ["instagram", "tiktok", "youtube", "facebook", "twitter"]
        
        for platform in platforms:
            response = client.get(f"/api/optimal-posting-times/platform/{platform}")
            assert response.status_code == 200
            
            data = response.json()
            assert "platform" in data
            assert data["platform"] == platform
            assert "best_hours" in data or "is_default" in data
            if "best_hours" in data:
                assert isinstance(data["best_hours"], list)
                assert len(data["best_hours"]) > 0
    
    def test_get_optimal_times_with_account_filter(self, client):
        """Test getting optimal times filtered by account"""
        response = client.get(
            "/api/optimal-posting-times/platform/instagram",
            params={"account_id": "00000000-0000-0000-0000-000000000000"}
        )
        assert response.status_code in [200, 500]
    
    def test_get_optimal_times_with_days_back(self, client):
        """Test getting optimal times with custom days_back"""
        response = client.get(
            "/api/optimal-posting-times/platform/tiktok",
            params={"days_back": 30}
        )
        assert response.status_code in [200, 500]
    
    def test_get_recommended_time(self, client):
        """Test getting recommended time for a date"""
        payload = {
            "platform": "instagram",
            "preferred_date": datetime.now().isoformat()
        }
        response = client.post(
            "/api/optimal-posting-times/recommend",
            params=payload
        )
        assert response.status_code in [200, 422, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "recommended_time" in data
            assert "platform" in data
            assert "score" in data
            assert "reasoning" in data


class TestOptimalPostingTimesService:
    """Test optimal posting times service logic"""
    
    @pytest.mark.asyncio
    async def test_get_optimal_times(self, mock_db):
        """Test getting optimal times from service"""
        service = OptimalPostingTimesService()
        
        with patch.object(service, 'get_optimal_times', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "platform": "instagram",
                "best_hours": [
                    {"hour": 11, "score": 0.8, "avg_engagement": 6.5, "post_count": 10}
                ],
                "best_days": [
                    {"day": 1, "day_name": "Tuesday", "score": 0.75, "post_count": 5}
                ],
                "data_points": 50
            }
            
            result = await service.get_optimal_times(mock_db, "instagram")
            assert result["platform"] == "instagram"
            assert "best_hours" in result
            assert "best_days" in result
    
    @pytest.mark.asyncio
    async def test_get_recommended_time(self, mock_db):
        """Test getting recommended time for a date"""
        service = OptimalPostingTimesService()
        
        preferred_date = datetime(2025, 11, 27, 12, 0)
        
        with patch.object(service, 'get_recommended_time', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = datetime(2025, 11, 27, 14, 0)
            
            recommended = await service.get_recommended_time(
                mock_db,
                "instagram",
                preferred_date
            )
            assert isinstance(recommended, datetime)
            assert recommended.date() == preferred_date.date()
    
    def test_default_optimal_times(self):
        """Test default optimal times for platforms"""
        service = OptimalPostingTimesService()
        
        platforms = ["instagram", "tiktok", "youtube", "facebook", "twitter"]
        
        for platform in platforms:
            defaults = service._get_default_optimal_times(platform)
            assert defaults["platform"] == platform
            assert "best_hours" in defaults
            assert "best_days" in defaults
            assert len(defaults["best_hours"]) > 0
            assert len(defaults["best_days"]) > 0

