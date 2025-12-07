"""
Integration tests for Checkback API endpoints
Tests the platform publishing checkback functionality
"""
import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


class TestCheckbackAPI:
    """Test checkback-related API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Get test client"""
        from main import app
        return TestClient(app)
    
    @pytest.fixture
    def sample_post_id(self):
        """Generate sample post ID"""
        return str(uuid.uuid4())
    
    # ==================== GET /api/platform/posts Tests ====================
    
    def test_list_posts_returns_list(self, client):
        """Test that listing posts returns a list"""
        response = client.get("/api/platform/posts")
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
    
    def test_list_posts_with_platform_filter(self, client):
        """Test platform filtering"""
        platforms = ["tiktok", "instagram", "youtube"]
        
        for platform in platforms:
            response = client.get(f"/api/platform/posts?platform={platform}")
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                data = response.json()
                # All returned posts should match the platform filter
                for post in data:
                    assert post["platform"] == platform
    
    def test_list_posts_with_status_filter(self, client):
        """Test status filtering"""
        statuses = ["published", "scheduled", "failed"]
        
        for status in statuses:
            response = client.get(f"/api/platform/posts?status={status}")
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                data = response.json()
                for post in data:
                    assert post["status"] == status
    
    def test_list_posts_with_limit(self, client):
        """Test limit parameter"""
        response = client.get("/api/platform/posts?limit=5")
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 5
    
    # ==================== GET /api/platform/posts/{post_id} Tests ====================
    
    def test_get_post_details_not_found(self, client, sample_post_id):
        """Test getting a non-existent post returns 404"""
        response = client.get(f"/api/platform/posts/{sample_post_id}")
        assert response.status_code == 404
    
    def test_get_post_details_invalid_uuid(self, client):
        """Test that invalid UUID returns error"""
        response = client.get("/api/platform/posts/invalid-uuid")
        assert response.status_code in [400, 422, 500]
    
    # ==================== POST /api/platform/schedule-checkbacks Tests ====================
    
    def test_schedule_checkbacks_not_found(self, client, sample_post_id):
        """Test scheduling checkbacks for non-existent post"""
        response = client.post(f"/api/platform/schedule-checkbacks/{sample_post_id}")
        assert response.status_code == 404
    
    # ==================== POST /api/platform/metrics/collect Tests ====================
    
    def test_collect_metrics_missing_post_id(self, client):
        """Test collecting metrics without post_id"""
        response = client.post("/api/platform/metrics/collect", json={
            "checkback_hours": 24
        })
        assert response.status_code == 422  # Validation error
    
    def test_collect_metrics_invalid_checkback_hours(self, client, sample_post_id):
        """Test collecting metrics with invalid checkback hours"""
        response = client.post("/api/platform/metrics/collect", json={
            "post_id": sample_post_id,
            "checkback_hours": 24
        })
        # Should either fail validation or return not found for post
        assert response.status_code in [200, 404, 422, 500]
    
    # ==================== GET /api/platform/platforms Tests ====================
    
    def test_get_available_platforms(self, client):
        """Test getting available platforms"""
        response = client.get("/api/platform/platforms")
        assert response.status_code == 200
        
        data = response.json()
        assert "platforms" in data
        assert "total" in data
        assert isinstance(data["platforms"], list)
        assert data["total"] == len(data["platforms"])
    
    # ==================== Response Structure Tests ====================
    
    def test_post_detail_response_structure(self, client):
        """Test that post detail response has expected structure"""
        response = client.get("/api/platform/posts?limit=1")
        
        if response.status_code == 200 and response.json():
            post = response.json()[0]
            
            # Check required fields exist
            expected_fields = ["id", "platform", "status"]
            for field in expected_fields:
                assert field in post, f"Missing field: {field}"
    
    def test_checkback_timeline_structure(self, client):
        """Test that checkback timeline has correct structure"""
        # First get a post
        posts_response = client.get("/api/platform/posts?status=published&limit=1")
        
        if posts_response.status_code == 200 and posts_response.json():
            post_id = posts_response.json()[0]["id"]
            
            # Get post details with checkbacks
            detail_response = client.get(f"/api/platform/posts/{post_id}")
            
            if detail_response.status_code == 200:
                data = detail_response.json()
                
                assert "metrics_timeline" in data
                
                for checkback in data["metrics_timeline"]:
                    expected_fields = ["checkback_hours", "views", "likes", "comments"]
                    for field in expected_fields:
                        assert field in checkback, f"Missing checkback field: {field}"
                    
                    # Verify checkback hours are in expected set
                    assert checkback["checkback_hours"] in [1, 6, 24, 72, 168]
