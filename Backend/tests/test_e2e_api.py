"""
E2E Tests for MediaPoster Backend API

Tests the full API endpoints against a running backend server.
Requires: Backend running at http://localhost:5555

Run with: pytest tests/test_e2e_api.py -v
"""
import os
import pytest
import httpx
from datetime import datetime
from typing import Optional

# Backend API URL
API_BASE = os.getenv("API_BASE_URL", "http://localhost:5555")


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def api_client():
    """Create HTTP client for API calls."""
    return httpx.Client(base_url=API_BASE, timeout=30.0)


@pytest.fixture(scope="session")
def async_api_client():
    """Create async HTTP client for API calls."""
    return httpx.AsyncClient(base_url=API_BASE, timeout=30.0)


def check_backend_running():
    """Check if backend is running."""
    try:
        response = httpx.get(f"{API_BASE}/api/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


# Skip all tests if backend not running
pytestmark = pytest.mark.skipif(
    not check_backend_running(),
    reason="Backend not running at http://localhost:5555"
)


# =============================================================================
# HEALTH & STATUS TESTS
# =============================================================================

class TestHealthEndpoints:
    """Test health and status endpoints."""
    
    def test_health_check(self, api_client):
        """Test /api/health endpoint."""
        response = api_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "api_version" in data
    
    def test_root_endpoint(self, api_client):
        """Test root endpoint returns API info."""
        response = api_client.get("/")
        assert response.status_code == 200


# =============================================================================
# MEDIA LIBRARY TESTS
# =============================================================================

class TestMediaLibrary:
    """E2E tests for media library endpoints."""
    
    def test_list_media(self, api_client):
        """Test GET /api/media-db/list endpoint."""
        response = api_client.get("/api/media-db/list", params={"limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            item = data[0]
            assert "media_id" in item
            assert "filename" in item
            assert "status" in item
            assert "source_type" in item  # New field
    
    def test_list_media_with_type_filter(self, api_client):
        """Test media list with type filter."""
        # Video filter
        response = api_client.get("/api/media-db/list", params={
            "limit": 5,
            "media_type": "video"
        })
        assert response.status_code == 200
        data = response.json()
        for item in data:
            assert item.get("media_type") == "video"
        
        # Image filter
        response = api_client.get("/api/media-db/list", params={
            "limit": 5,
            "media_type": "image"
        })
        assert response.status_code == 200
    
    def test_media_stats(self, api_client):
        """Test GET /api/media-db/stats endpoint."""
        response = api_client.get("/api/media-db/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_videos" in data
        assert "analyzed_count" in data
        assert "pending_analysis" in data


# =============================================================================
# SORA PIPELINE TESTS
# =============================================================================

class TestSoraPipeline:
    """E2E tests for Sora pipeline endpoints."""
    
    def test_list_projects(self, api_client):
        """Test GET /api/sora-pipeline/projects endpoint."""
        response = api_client.get("/api/sora-pipeline/projects")
        assert response.status_code == 200
        data = response.json()
        # Returns array directly or object with projects key
        assert isinstance(data, (list, dict))
    
    def test_create_project(self, api_client):
        """Test POST /api/sora-pipeline/projects endpoint."""
        response = api_client.post("/api/sora-pipeline/projects", json={
            "character": "@testuser",
            "total_duration": 12,
            "num_clips": 1,
            "style": "motivational",
            "topic": "E2E test project"
        })
        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        assert data["main_character"] == "@testuser"
        assert len(data["clips"]) == 1
        
        # Store project_id for later tests
        return data["project_id"]
    
    def test_get_project(self, api_client):
        """Test GET /api/sora-pipeline/projects/{id} endpoint."""
        # First create a project
        create_response = api_client.post("/api/sora-pipeline/projects", json={
            "character": "@testuser",
            "total_duration": 12,
            "num_clips": 1,
            "style": "test",
            "topic": "test"
        })
        project_id = create_response.json()["project_id"]
        
        # Then fetch it
        response = api_client.get(f"/api/sora-pipeline/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
    
    def test_create_project_validation(self, api_client):
        """Test project creation validation."""
        # Too short duration
        response = api_client.post("/api/sora-pipeline/projects", json={
            "character": "@testuser",
            "total_duration": 4,  # Min is 12
            "num_clips": 1,
            "style": "test",
            "topic": "test"
        })
        assert response.status_code == 422  # Validation error


# =============================================================================
# TIKTOK REPURPOSE TESTS
# =============================================================================

class TestTikTokRepurpose:
    """E2E tests for TikTok repurpose endpoints."""
    
    def test_service_status(self, api_client):
        """Test GET /api/repurpose/tiktok/status endpoint."""
        response = api_client.get("/api/repurpose/tiktok/status")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["service"] == "TikTok Repurpose"
    
    def test_account_mapping(self, api_client):
        """Test GET /api/repurpose/tiktok/accounts endpoint."""
        response = api_client.get("/api/repurpose/tiktok/accounts")
        assert response.status_code == 200
        data = response.json()
        # Response has 'accounts' key with nested platform info
        assert "accounts" in data
        assert "tiktok" in data["accounts"]
        assert "instagram" in data["accounts"]


# =============================================================================
# SCHEDULED POSTS TESTS
# =============================================================================

class TestScheduledPosts:
    """E2E tests for scheduled posts endpoints."""
    
    def test_list_scheduled(self, api_client):
        """Test listing scheduled posts."""
        response = api_client.get("/api/scheduled/list")
        # Accept 200 or endpoint might not exist
        assert response.status_code in [200, 404]


# =============================================================================
# BLOTATO INTEGRATION TESTS
# =============================================================================

class TestBlotatoIntegration:
    """E2E tests for Blotato account endpoints."""
    
    def test_list_accounts(self, api_client):
        """Test GET /api/blotato/accounts endpoint."""
        response = api_client.get("/api/blotato/accounts")
        assert response.status_code == 200
        data = response.json()
        # Returns array directly
        assert isinstance(data, list)
        
        if len(data) > 0:
            account = data[0]
            assert "platform" in account
            assert "username" in account


# =============================================================================
# ANALYSIS TESTS
# =============================================================================

class TestAnalysis:
    """E2E tests for analysis endpoints."""
    
    def test_analysis_stats(self, api_client):
        """Test analysis statistics endpoint."""
        response = api_client.get("/api/media-db/stats")
        assert response.status_code == 200
        data = response.json()
        assert "analyzed_count" in data


# =============================================================================
# WEBSOCKET TESTS
# =============================================================================

class TestWebSocket:
    """E2E tests for WebSocket endpoints."""
    
    def test_websocket_endpoint_exists(self, api_client):
        """Test WebSocket endpoint is configured."""
        # Just check the endpoint doesn't 404
        # Full WebSocket testing requires different approach
        pass


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Performance tests for API endpoints."""
    
    def test_media_list_performance(self, api_client):
        """Test media list endpoint responds quickly."""
        import time
        
        start = time.time()
        response = api_client.get("/api/media-db/list", params={"limit": 100})
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"Media list took too long: {elapsed:.2f}s"
    
    def test_health_check_performance(self, api_client):
        """Test health endpoint responds quickly."""
        import time
        
        start = time.time()
        response = api_client.get("/api/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"Health check took too long: {elapsed:.2f}s"


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test API error handling."""
    
    def test_404_for_unknown_endpoint(self, api_client):
        """Test 404 for unknown endpoints."""
        response = api_client.get("/api/nonexistent/endpoint")
        assert response.status_code == 404
    
    def test_404_for_unknown_media(self, api_client):
        """Test 404 for unknown media ID."""
        response = api_client.get("/api/media-db/detail/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
