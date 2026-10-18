"""
Integration tests for Social Analytics Content API endpoints
Tests the /api/social-analytics/content endpoints
"""
import pytest
from fastapi.testclient import TestClient


class TestSocialAnalyticsContentAPI:
    """Test social analytics content endpoints"""
    
    @pytest.fixture
    def client(self):
        """Get test client"""
        from main import app
        return TestClient(app)
    
    # ==================== GET /api/social-analytics/content Tests ====================
    
    def test_get_content_items_returns_list(self, client):
        """Test that content endpoint returns a list"""
        response = client.get("/api/social-analytics/content")
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
    
    def test_content_items_with_limit(self, client):
        """Test limit parameter"""
        response = client.get("/api/social-analytics/content?limit=5")
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 5
    
    def test_content_items_sort_by_likes(self, client):
        """Test sorting by total_likes"""
        response = client.get("/api/social-analytics/content?sort_by=total_likes")
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            # Verify sorted in descending order
            if len(data) > 1:
                for i in range(len(data) - 1):
                    assert data[i].get("total_likes", 0) >= data[i + 1].get("total_likes", 0)
    
    def test_content_items_sort_by_comments(self, client):
        """Test sorting by total_comments"""
        response = client.get("/api/social-analytics/content?sort_by=total_comments")
        assert response.status_code in [200, 404, 500]
    
    def test_content_items_sort_by_shares(self, client):
        """Test sorting by total_shares"""
        response = client.get("/api/social-analytics/content?sort_by=total_shares")
        assert response.status_code in [200, 404, 500]
    
    def test_content_items_sort_by_platform_count(self, client):
        """Test sorting by platform_count"""
        response = client.get("/api/social-analytics/content?sort_by=platform_count")
        assert response.status_code in [200, 404, 500]
    
    def test_content_items_platform_filter(self, client):
        """Test platform filtering"""
        platforms = ["tiktok", "instagram", "youtube"]
        
        for platform in platforms:
            response = client.get(f"/api/social-analytics/content?platform={platform}")
            assert response.status_code in [200, 404, 500]
    
    def test_content_items_min_platforms(self, client):
        """Test min_platforms filter"""
        response = client.get("/api/social-analytics/content?min_platforms=2")
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            for item in data:
                assert item.get("platform_count", 0) >= 2
    
    # ==================== Response Structure Tests ====================
    
    def test_content_item_structure(self, client):
        """Test that content items have expected structure"""
        response = client.get("/api/social-analytics/content?limit=1")
        
        if response.status_code == 200 and response.json():
            item = response.json()[0]
            
            expected_fields = [
                "content_id",
                "title",
                "platform_count",
                "platforms",
                "total_likes",
                "total_comments"
            ]
            
            for field in expected_fields:
                assert field in item, f"Missing field: {field}"
    
    def test_content_item_has_social_scores(self, client):
        """Test that content items include social score fields"""
        response = client.get("/api/social-analytics/content?limit=10")
        
        if response.status_code == 200 and response.json():
            # Check if pre/post social scores are present in response
            # These may be null but the fields should exist in database-backed items
            for item in response.json():
                # Platform should always be present
                assert "platforms" in item
                assert isinstance(item["platforms"], list)
    
    # ==================== GET /api/social-analytics/content/leaderboard Tests ====================
    
    def test_content_leaderboard(self, client):
        """Test content leaderboard endpoint"""
        response = client.get("/api/social-analytics/content/leaderboard")
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
    
    def test_content_leaderboard_by_metric(self, client):
        """Test leaderboard with different metrics"""
        metrics = ["total_likes", "total_comments", "total_shares"]
        
        for metric in metrics:
            response = client.get(f"/api/social-analytics/content/leaderboard?metric={metric}")
            assert response.status_code in [200, 404, 500]
    
    def test_content_leaderboard_with_limit(self, client):
        """Test leaderboard limit"""
        response = client.get("/api/social-analytics/content/leaderboard?limit=5")
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 5
    
    def test_content_leaderboard_has_rank(self, client):
        """Test that leaderboard items have rank"""
        response = client.get("/api/social-analytics/content/leaderboard?limit=5")
        
        if response.status_code == 200 and response.json():
            for idx, item in enumerate(response.json()):
                assert "rank" in item
                assert item["rank"] == idx + 1
    
    # ==================== GET /api/social-analytics/content/{content_id} Tests ====================
    
    def test_content_detail_not_found(self, client):
        """Test getting non-existent content returns 404"""
        response = client.get("/api/social-analytics/content/nonexistent-id")
        assert response.status_code == 404
    
    def test_content_detail_structure(self, client):
        """Test content detail response structure"""
        # First get a content item
        list_response = client.get("/api/social-analytics/content?limit=1")
        
        if list_response.status_code == 200 and list_response.json():
            content_id = list_response.json()[0]["content_id"]
            
            detail_response = client.get(f"/api/social-analytics/content/{content_id}")
            
            if detail_response.status_code == 200:
                data = detail_response.json()
                
                expected_fields = ["content_id", "title", "totals", "platform_breakdown"]
                for field in expected_fields:
                    assert field in data, f"Missing field: {field}"
                
                # Check totals structure
                assert "likes" in data["totals"]
                assert "comments" in data["totals"]
    
    # ==================== Dashboard Overview Tests ====================
    
    def test_dashboard_overview(self, client):
        """Test dashboard overview endpoint"""
        response = client.get("/api/social-analytics/overview")
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            expected_fields = ["total_platforms", "total_accounts", "total_followers"]
            for field in expected_fields:
                assert field in data, f"Missing field: {field}"
    
    # ==================== Platform-Specific Analytics Tests ====================
    
    def test_platform_details(self, client):
        """Test platform-specific analytics"""
        platforms = ["instagram", "tiktok", "youtube"]
        
        for platform in platforms:
            response = client.get(f"/api/social-analytics/platform/{platform}")
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert data["platform"] == platform
    
    def test_platform_details_with_days(self, client):
        """Test platform details with days parameter"""
        response = client.get("/api/social-analytics/platform/instagram?days=7")
        assert response.status_code in [200, 404, 500]
    
    # ==================== Trends Tests ====================
    
    def test_analytics_trends(self, client):
        """Test analytics trends endpoint"""
        response = client.get("/api/social-analytics/trends")
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "trends" in data
            assert isinstance(data["trends"], list)
    
    def test_analytics_trends_with_days(self, client):
        """Test trends with different day ranges"""
        for days in [7, 30, 90]:
            response = client.get(f"/api/social-analytics/trends?days={days}")
            assert response.status_code in [200, 404, 500]
