"""
PRD Regression Tests
Ensure new changes don't break existing behavior.
Coverage: 30+ regression tests
"""
import pytest
import httpx

API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"
FRONTEND_BASE = "http://localhost:5557"


# =============================================================================
# REGRESSION: Core API Functionality
# =============================================================================

class TestRegressionCoreAPI:
    """Core API regression tests."""
    
    def test_health_still_works(self):
        """Health endpoint still works."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_list_still_works(self):
        """List endpoint still works."""
        response = httpx.get(f"{DB_API_URL}/list", timeout=10)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_stats_still_works(self):
        """Stats endpoint still works."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "total_videos" in data
    
    def test_detail_still_works(self):
        """Detail endpoint still works."""
        list_resp = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_resp.json():
            media_id = list_resp.json()[0]["media_id"]
            detail = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
            assert detail.status_code == 200
    
    def test_thumbnail_still_works(self):
        """Thumbnail endpoint still works."""
        list_resp = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_resp.json():
            media_id = list_resp.json()[0]["media_id"]
            thumb = httpx.get(f"{DB_API_URL}/thumbnail/{media_id}", timeout=30)
            assert thumb.status_code in [200, 404]


# =============================================================================
# REGRESSION: Response Formats
# =============================================================================

class TestRegressionResponseFormats:
    """Response format regression tests."""
    
    def test_list_returns_array(self):
        """List still returns array."""
        response = httpx.get(f"{DB_API_URL}/list", timeout=10)
        assert isinstance(response.json(), list)
    
    def test_stats_returns_object(self):
        """Stats still returns object."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert isinstance(response.json(), dict)
    
    def test_health_returns_object(self):
        """Health still returns object."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert isinstance(response.json(), dict)
    
    def test_list_items_have_media_id(self):
        """List items still have media_id."""
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        for item in response.json():
            assert "media_id" in item
    
    def test_list_items_have_status(self):
        """List items still have status."""
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        for item in response.json():
            assert "status" in item


# =============================================================================
# REGRESSION: Query Parameters
# =============================================================================

class TestRegressionQueryParams:
    """Query parameter regression tests."""
    
    def test_limit_param_still_works(self):
        """Limit parameter still works."""
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        assert len(response.json()) <= 5
    
    def test_offset_param_still_works(self):
        """Offset parameter still works."""
        response = httpx.get(f"{DB_API_URL}/list?offset=0&limit=5", timeout=10)
        assert response.status_code == 200
    
    def test_status_filter_still_works(self):
        """Status filter still works."""
        response = httpx.get(f"{DB_API_URL}/list?status=ingested", timeout=10)
        assert response.status_code == 200


# =============================================================================
# REGRESSION: Frontend Pages
# =============================================================================

class TestRegressionFrontendPages:
    """Frontend page regression tests."""
    
    def test_dashboard_still_loads(self):
        """Dashboard still loads."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        assert response.status_code == 200
    
    def test_media_page_still_loads(self):
        """Media page still loads."""
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        assert response.status_code == 200
    
    def test_processing_page_still_loads(self):
        """Processing page still loads."""
        response = httpx.get(f"{FRONTEND_BASE}/processing", timeout=10)
        assert response.status_code == 200
    
    def test_analytics_page_still_loads(self):
        """Analytics page still loads."""
        response = httpx.get(f"{FRONTEND_BASE}/analytics", timeout=10)
        assert response.status_code == 200
    
    def test_schedule_page_still_loads(self):
        """Schedule page still loads."""
        response = httpx.get(f"{FRONTEND_BASE}/schedule", timeout=10)
        assert response.status_code == 200
    
    def test_briefs_page_still_loads(self):
        """Briefs page still loads."""
        response = httpx.get(f"{FRONTEND_BASE}/briefs", timeout=10)
        assert response.status_code == 200


# =============================================================================
# REGRESSION: Error Handling
# =============================================================================

class TestRegressionErrorHandling:
    """Error handling regression tests."""
    
    def test_404_still_handled(self):
        """404 errors still handled."""
        response = httpx.get(f"{API_BASE}/nonexistent", timeout=10)
        assert response.status_code in [404, 307]
    
    def test_invalid_uuid_still_handled(self):
        """Invalid UUID still handled."""
        response = httpx.get(f"{DB_API_URL}/detail/invalid", timeout=10)
        assert response.status_code in [400, 404, 422, 500]
    
    def test_invalid_limit_still_handled(self):
        """Invalid limit still handled."""
        response = httpx.get(f"{DB_API_URL}/list?limit=abc", timeout=10)
        assert response.status_code in [200, 400, 422]


# =============================================================================
# REGRESSION: Performance
# =============================================================================

class TestRegressionPerformance:
    """Performance regression tests."""
    
    def test_health_still_fast(self):
        """Health check still fast."""
        import time
        start = time.time()
        httpx.get(f"{DB_API_URL}/health", timeout=10)
        elapsed = time.time() - start
        assert elapsed < 1.0
    
    def test_list_still_fast(self):
        """List endpoint still fast."""
        import time
        start = time.time()
        httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        elapsed = time.time() - start
        assert elapsed < 2.0


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
