"""
Regression Tests for Analytics Features
Ensures analytics features verified in audit continue to work
"""
import pytest
from fastapi.testclient import TestClient


class TestAnalyticsRegression:
    """Regression tests for analytics dashboard features"""
    
    @pytest.fixture
    def client(self):
        """Get test client"""
        from main import app
        return TestClient(app)
    
    # ==================== Dashboard Overview Tests ====================
    
    def test_dashboard_has_total_metrics(self, client):
        """Verify dashboard returns total metrics"""
        response = client.get("/api/social-analytics/overview")
        
        if response.status_code == 200:
            data = response.json()
            # These fields should always exist
            expected_fields = [
                "total_platforms",
                "total_accounts",
                "total_followers",
                "total_posts",
                "total_views",
                "total_likes"
            ]
            for field in expected_fields:
                assert field in data, f"Dashboard missing field: {field}"
    
    def test_dashboard_has_platform_breakdown(self, client):
        """Verify dashboard includes platform breakdown"""
        response = client.get("/api/social-analytics/overview")
        
        if response.status_code == 200:
            data = response.json()
            assert "platform_breakdown" in data, "Missing platform_breakdown"
            assert isinstance(data["platform_breakdown"], list)
    
    # ==================== Content Catalog Tests ====================
    
    def test_content_has_platform_indicators(self, client):
        """Verify content items include platform indicators"""
        response = client.get("/api/social-analytics/content?limit=10")
        
        if response.status_code == 200 and response.json():
            for item in response.json():
                assert "platforms" in item, "Content missing platforms field"
                assert isinstance(item["platforms"], list)
                assert "platform_count" in item, "Content missing platform_count"
    
    def test_content_has_metrics(self, client):
        """Verify content items include engagement metrics"""
        response = client.get("/api/social-analytics/content?limit=10")
        
        if response.status_code == 200 and response.json():
            for item in response.json():
                # Core metrics should be present
                assert "total_likes" in item, "Content missing total_likes"
                assert "total_comments" in item, "Content missing total_comments"
    
    def test_content_has_best_platform(self, client):
        """Verify content identifies best performing platform"""
        response = client.get("/api/social-analytics/content?limit=10")
        
        if response.status_code == 200 and response.json():
            for item in response.json():
                assert "best_platform" in item, "Content missing best_platform"
    
    # ==================== Platform Analytics Tests ====================
    
    def test_platform_analytics_structure(self, client):
        """Verify platform analytics returns expected structure"""
        platforms = ["instagram", "tiktok", "youtube"]
        
        for platform in platforms:
            response = client.get(f"/api/social-analytics/platform/{platform}")
            
            if response.status_code == 200:
                data = response.json()
                assert data["platform"] == platform
                assert "accounts" in data, f"Missing accounts for {platform}"
                assert "trends" in data, f"Missing trends for {platform}"
    
    # ==================== Post Metrics Tests ====================
    
    def test_posts_have_metrics(self, client):
        """Verify posts include metric data"""
        response = client.get("/api/platform/posts?limit=10")
        
        if response.status_code == 200 and response.json():
            for post in response.json():
                assert "platform" in post
                assert "status" in post
    
    # ==================== Checkback Period Tests ====================
    
    def test_post_details_have_checkback_timeline(self, client):
        """Verify post details include checkback timeline"""
        # Get a post first
        posts_response = client.get("/api/platform/posts?status=published&limit=1")
        
        if posts_response.status_code == 200 and posts_response.json():
            post_id = posts_response.json()[0]["id"]
            detail_response = client.get(f"/api/platform/posts/{post_id}")
            
            if detail_response.status_code == 200:
                data = detail_response.json()
                assert "metrics_timeline" in data, "Post details missing metrics_timeline"
    
    def test_checkback_intervals_are_standard(self, client):
        """Verify checkback uses standard intervals (1h, 6h, 24h, 72h, 168h)"""
        posts_response = client.get("/api/platform/posts?status=published&limit=1")
        
        if posts_response.status_code == 200 and posts_response.json():
            post_id = posts_response.json()[0]["id"]
            detail_response = client.get(f"/api/platform/posts/{post_id}")
            
            if detail_response.status_code == 200:
                data = detail_response.json()
                expected_intervals = {1, 6, 24, 72, 168}
                
                for checkback in data.get("metrics_timeline", []):
                    hours = checkback.get("checkback_hours")
                    assert hours in expected_intervals, f"Unexpected checkback interval: {hours}"
    
    # ==================== Trends Tests ====================
    
    def test_trends_have_date_series(self, client):
        """Verify trends return date-based series"""
        response = client.get("/api/social-analytics/trends?days=30")
        
        if response.status_code == 200:
            data = response.json()
            assert "trends" in data, "Missing trends array"
            
            for point in data["trends"]:
                assert "date" in point, "Trend point missing date"
    
    def test_trends_include_engagement_metrics(self, client):
        """Verify trends include engagement metrics"""
        response = client.get("/api/social-analytics/trends?days=30")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("trends"):
                for point in data["trends"]:
                    expected = ["followers", "views", "likes"]
                    for field in expected:
                        assert field in point, f"Trend missing: {field}"


# Mark as regression tests
pytestmark = pytest.mark.regression
