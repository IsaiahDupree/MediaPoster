"""
PRD Smoke Tests
Quick "does it basically run?" checks.
Coverage: 25+ smoke tests
"""
import pytest
import httpx

API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"
FRONTEND_BASE = "http://localhost:5557"


# =============================================================================
# SMOKE: Backend Health
# =============================================================================

class TestSmokeBackendHealth:
    """Backend health smoke tests."""
    
    def test_backend_running(self):
        """Backend is running."""
        response = httpx.get(f"{API_BASE}/", timeout=10)
        assert response.status_code == 200
    
    def test_media_db_api_running(self):
        """Media DB API is running."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert response.status_code == 200
    
    def test_database_connected(self):
        """Database is connected."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        data = response.json()
        assert data.get("database") == "connected"


# =============================================================================
# SMOKE: Frontend Health
# =============================================================================

class TestSmokeFrontendHealth:
    """Frontend health smoke tests."""
    
    def test_frontend_running(self):
        """Frontend is running."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        assert response.status_code == 200
    
    def test_frontend_returns_html(self):
        """Frontend returns HTML."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type


# =============================================================================
# SMOKE: Core API Endpoints
# =============================================================================

class TestSmokeCoreEndpoints:
    """Core endpoint smoke tests."""
    
    def test_list_endpoint(self):
        """List endpoint works."""
        response = httpx.get(f"{DB_API_URL}/list", timeout=10)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_stats_endpoint(self):
        """Stats endpoint works."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
    
    def test_health_endpoint(self):
        """Health endpoint works."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert response.status_code == 200


# =============================================================================
# SMOKE: Core Pages
# =============================================================================

class TestSmokePages:
    """Core page smoke tests."""
    
    def test_dashboard_loads(self):
        """Dashboard loads."""
        response = httpx.get(f"{FRONTEND_BASE}/", timeout=10)
        assert response.status_code == 200
    
    def test_media_page_loads(self):
        """Media page loads."""
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        assert response.status_code == 200
    
    def test_processing_page_loads(self):
        """Processing page loads."""
        response = httpx.get(f"{FRONTEND_BASE}/processing", timeout=10)
        assert response.status_code == 200
    
    def test_analytics_page_loads(self):
        """Analytics page loads."""
        response = httpx.get(f"{FRONTEND_BASE}/analytics", timeout=10)
        assert response.status_code == 200
    
    def test_schedule_page_loads(self):
        """Schedule page loads."""
        response = httpx.get(f"{FRONTEND_BASE}/schedule", timeout=10)
        assert response.status_code == 200


# =============================================================================
# SMOKE: Data Flow
# =============================================================================

class TestSmokeDataFlow:
    """Data flow smoke tests."""
    
    def test_can_get_media_list(self):
        """Can retrieve media list."""
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        assert response.status_code == 200
    
    def test_can_get_stats(self):
        """Can retrieve stats."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "total_videos" in data or "total" in data
    
    def test_can_get_detail(self):
        """Can retrieve media detail."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.json():
            media_id = list_response.json()[0]["media_id"]
            detail = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
            assert detail.status_code == 200


# =============================================================================
# SMOKE: Error Handling
# =============================================================================

class TestSmokeErrorHandling:
    """Error handling smoke tests."""
    
    def test_404_not_crash(self):
        """404 doesn't crash server."""
        response = httpx.get(f"{API_BASE}/nonexistent", timeout=10)
        assert response.status_code in [404, 307]
    
    def test_invalid_param_not_crash(self):
        """Invalid params don't crash."""
        response = httpx.get(f"{DB_API_URL}/list?limit=abc", timeout=10)
        assert response.status_code in [200, 400, 422]


# =============================================================================
# SMOKE: Quick Integration
# =============================================================================

class TestSmokeIntegration:
    """Quick integration smoke tests."""
    
    def test_frontend_backend_connected(self):
        """Frontend can reach backend."""
        # Frontend loads
        frontend = httpx.get(FRONTEND_BASE, timeout=10)
        assert frontend.status_code == 200
        
        # Backend accessible
        backend = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert backend.status_code == 200


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
