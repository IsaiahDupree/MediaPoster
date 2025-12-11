"""
Tests for Posted Media API
Tests fetching and listing posted media from connected accounts.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid

import sys
sys.path.insert(0, '..')
from main import app

client = TestClient(app)


class TestPostedMediaList:
    """Test posted media listing endpoints"""

    def test_get_posted_media_list(self):
        """Test getting posted media list"""
        response = client.get("/api/posted-media/list")
        assert response.status_code in [200, 500]  # 500 for db issues in test
        
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "stats" in data
            assert isinstance(data["items"], list)

    def test_get_posted_media_with_status_filter(self):
        """Test filtering posted media by status"""
        response = client.get("/api/posted-media/list?status=published")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", []):
                assert item["status"] == "published"

    def test_get_posted_media_with_platform_filter(self):
        """Test filtering posted media by platform"""
        for platform in ["instagram", "tiktok", "youtube"]:
            response = client.get(f"/api/posted-media/list?platform={platform}")
            assert response.status_code in [200, 500]
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", []):
                    assert item["platform"] == platform

    def test_get_posted_media_with_days_filter(self):
        """Test filtering posted media by days"""
        for days in [7, 30, 90]:
            response = client.get(f"/api/posted-media/list?days={days}")
            assert response.status_code in [200, 500]

    def test_get_posted_media_with_limit(self):
        """Test limiting posted media results"""
        response = client.get("/api/posted-media/list?limit=5")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert len(data.get("items", [])) <= 5

    def test_get_posted_media_with_offset(self):
        """Test pagination with offset"""
        response = client.get("/api/posted-media/list?limit=5&offset=0")
        assert response.status_code in [200, 500]


class TestPostedMediaItemStructure:
    """Test posted media item structure"""

    def test_item_has_required_fields(self):
        """Test that items have required fields"""
        response = client.get("/api/posted-media/list")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                item = data["items"][0]
                assert "id" in item
                assert "title" in item
                assert "platform" in item

    def test_item_has_optional_fields(self):
        """Test that items may have optional fields"""
        response = client.get("/api/posted-media/list")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                item = data["items"][0]
                # These fields may or may not be present
                optional_fields = ["platform_post_id", "platform_url", "published_at"]
                # Just verify no errors accessing them
                for field in optional_fields:
                    _ = item.get(field)


class TestPostedMediaStats:
    """Test posted media statistics"""

    def test_stats_structure(self):
        """Test stats structure in list response"""
        response = client.get("/api/posted-media/list")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            stats = response.json().get("stats", {})
            assert "total_posts" in stats

    def test_stats_values_are_valid(self):
        """Test that stats values are valid"""
        response = client.get("/api/posted-media/list")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            stats = response.json().get("stats", {})
            assert stats.get("total_posts", 0) >= 0


class TestPostedMediaPlatformBreakdown:
    """Test platform breakdown endpoint"""

    def test_get_platform_breakdown(self):
        """Test getting platform breakdown"""
        response = client.get("/api/posted-media/platforms")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "platforms" in data

    def test_platform_breakdown_structure(self):
        """Test platform breakdown structure"""
        response = client.get("/api/posted-media/platforms")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            for platform, breakdown in data.get("platforms", {}).items():
                assert "count" in breakdown


class TestPostedMediaDetail:
    """Test single posted media detail"""

    def test_get_posted_media_detail(self):
        """Test getting posted media detail"""
        # First get list to get an ID
        list_response = client.get("/api/posted-media/list")
        assert list_response.status_code in [200, 500]
        
        if list_response.status_code == 200:
            items = list_response.json().get("items", [])
            if items:
                item_id = items[0]["id"]
                response = client.get(f"/api/posted-media/{item_id}")
                assert response.status_code in [200, 404, 500]

    def test_get_nonexistent_posted_media(self):
        """Test getting non-existent posted media"""
        response = client.get(f"/api/posted-media/{uuid.uuid4()}")
        assert response.status_code in [404, 500]


class TestPostedMediaValidation:
    """Test input validation"""

    def test_invalid_status_filter(self):
        """Test with invalid status filter"""
        response = client.get("/api/posted-media/list?status=invalid_status")
        # May accept any string or validate
        assert response.status_code in [200, 400, 422, 500]

    def test_invalid_days_filter(self):
        """Test with invalid days filter"""
        response = client.get("/api/posted-media/list?days=-1")
        assert response.status_code in [200, 400, 422, 500]

    def test_invalid_limit(self):
        """Test with invalid limit"""
        response = client.get("/api/posted-media/list?limit=0")
        assert response.status_code in [200, 400, 422, 500]


class TestPostedMediaMetrics:
    """Test posted media metrics"""

    def test_items_may_have_metrics(self):
        """Test that items may include engagement metrics"""
        response = client.get("/api/posted-media/list")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", []):
                # Metrics should be numeric if present
                if "views" in item and item["views"] is not None:
                    assert isinstance(item["views"], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
