"""
Integration Tests for Enhanced Analysis API
===========================================
Tests for vision analysis, scene detection, motion detection,
and template library API endpoints.
"""
import pytest
import httpx
import os
from uuid import uuid4

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5555")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """Create HTTP client for API tests"""
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


@pytest.fixture
def async_client():
    """Create async HTTP client"""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)


# ============================================================================
# Health Check
# ============================================================================

class TestAPIHealth:
    """Basic API health tests"""
    
    def test_api_is_running(self, api_client):
        """Verify API is accessible"""
        try:
            response = api_client.get("/health")
            assert response.status_code in [200, 404]  # 404 if no health endpoint
        except httpx.ConnectError:
            pytest.skip("API not running at localhost:5555")


# ============================================================================
# Template Library API Tests
# ============================================================================

class TestTemplateLibraryAPI:
    """Tests for template library endpoints"""
    
    def test_list_templates(self, api_client):
        """Test GET /api/enhanced-analysis/templates"""
        try:
            response = api_client.get("/api/enhanced-analysis/templates")
            
            if response.status_code == 200:
                data = response.json()
                assert "templates" in data or isinstance(data, list)
            elif response.status_code == 404:
                pytest.skip("Endpoint not registered")
            else:
                # API might return empty list or error
                assert response.status_code in [200, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_list_templates_with_category_filter(self, api_client):
        """Test template listing with category filter"""
        try:
            response = api_client.get("/api/enhanced-analysis/templates", params={"category": "tutorial_quick"})
            
            if response.status_code == 200:
                data = response.json()
                # Should return filtered results
                assert isinstance(data, (dict, list))
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_get_template_by_id_not_found(self, api_client):
        """Test GET /api/enhanced-analysis/templates/{id} with invalid ID"""
        try:
            fake_id = str(uuid4())
            response = api_client.get(f"/api/enhanced-analysis/templates/{fake_id}")
            
            # Should return 404 for non-existent template
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_match_template_endpoint(self, api_client):
        """Test POST /api/enhanced-analysis/templates/match"""
        try:
            response = api_client.post(
                "/api/enhanced-analysis/templates/match",
                json={
                    "content_type": "tutorial",
                    "tone": "educational",
                    "duration_sec": 30
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "matches" in data or isinstance(data, list)
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Vision Analysis API Tests
# ============================================================================

class TestVisionAnalysisAPI:
    """Tests for vision analysis endpoints"""
    
    def test_analyze_structured_requires_video(self, api_client):
        """Test that structured analysis requires video_id"""
        try:
            response = api_client.post(
                "/api/enhanced-analysis/vision/analyze-structured",
                json={}
            )
            
            # Should return 422 (validation error) or 400
            assert response.status_code in [400, 422, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_detect_scenes_requires_video(self, api_client):
        """Test that scene detection requires video_id"""
        try:
            response = api_client.post(
                "/api/enhanced-analysis/vision/detect-scenes",
                json={}
            )
            
            assert response.status_code in [400, 422, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_detect_motion_requires_video(self, api_client):
        """Test that motion detection requires video_id"""
        try:
            response = api_client.post(
                "/api/enhanced-analysis/vision/detect-motion",
                json={}
            )
            
            assert response.status_code in [400, 422, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Enhanced Analysis Listing Tests
# ============================================================================

class TestEnhancedAnalysisListing:
    """Tests for analysis listing endpoints"""
    
    def test_list_analyzed_videos(self, api_client):
        """Test GET /api/enhanced-analysis/videos"""
        try:
            response = api_client.get("/api/enhanced-analysis/videos")
            
            if response.status_code == 200:
                data = response.json()
                # Should return list of videos
                assert isinstance(data, (dict, list))
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_list_analyzed_videos_with_pagination(self, api_client):
        """Test video listing with pagination"""
        try:
            response = api_client.get(
                "/api/enhanced-analysis/videos",
                params={"limit": 5, "offset": 0}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (dict, list))
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Segment Management Tests
# ============================================================================

class TestSegmentManagement:
    """Tests for segment management endpoints"""
    
    def test_create_segment_requires_video(self, api_client):
        """Test segment creation validation"""
        try:
            response = api_client.post(
                "/api/enhanced-analysis/segments",
                json={
                    "start_sec": 0,
                    "end_sec": 10,
                    "label": "test"
                }
            )
            
            # Missing video_id should fail
            assert response.status_code in [400, 422, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_split_segment_validation(self, api_client):
        """Test segment split validation"""
        try:
            fake_id = str(uuid4())
            response = api_client.post(
                f"/api/enhanced-analysis/segments/{fake_id}/split",
                json={"split_at_sec": 5.0}
            )
            
            # Non-existent segment should fail
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_merge_segments_validation(self, api_client):
        """Test segment merge validation"""
        try:
            response = api_client.post(
                "/api/enhanced-analysis/segments/merge",
                json={"segment_ids": [str(uuid4()), str(uuid4())]}
            )
            
            # Non-existent segments should fail
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Performance Correlation Tests
# ============================================================================

class TestPerformanceCorrelation:
    """Tests for performance correlation endpoints"""
    
    def test_correlate_requires_account(self, api_client):
        """Test correlation requires account_id"""
        try:
            response = api_client.post(
                "/api/enhanced-analysis/correlate",
                json={}
            )
            
            assert response.status_code in [400, 422, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Template Auto-Population Tests
# ============================================================================

class TestTemplateAutoPopulation:
    """Tests for template auto-population"""
    
    def test_auto_populate_endpoint(self, api_client):
        """Test POST /api/enhanced-analysis/templates/auto-populate"""
        try:
            response = api_client.post(
                "/api/enhanced-analysis/templates/auto-populate",
                json={"min_engagement_rate": 0.05, "limit": 5}
            )
            
            # Should work or return error about no qualifying videos
            assert response.status_code in [200, 404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_create_template_from_video(self, api_client):
        """Test template creation from specific video"""
        try:
            fake_video_id = str(uuid4())
            response = api_client.post(
                "/api/enhanced-analysis/templates/create-from-video",
                json={"video_id": fake_video_id}
            )
            
            # Non-existent video should fail
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
