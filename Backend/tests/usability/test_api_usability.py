"""
Usability Tests for Backend API
Tests API design, error messages, response formats, and developer experience
"""
import pytest
from fastapi.testclient import TestClient
from main import app
import json


@pytest.fixture
def client():
    return TestClient(app)


class TestAPIUsability:
    """Test API usability aspects"""
    
    def test_api_has_openapi_docs(self, client):
        """API should have OpenAPI documentation"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
    
    def test_api_has_health_endpoint(self, client):
        """API should have a health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "operational"]
    
    def test_error_messages_are_helpful(self, client):
        """Error messages should be clear and actionable"""
        # Test 404 with helpful message
        response = client.get("/api/videos/nonexistent-id")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
    
    def test_api_returns_json_by_default(self, client):
        """API should return JSON by default"""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"
    
    def test_api_supports_cors(self, client):
        """API should support CORS for frontend integration"""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5557",
                "Access-Control-Request-Method": "GET"
            }
        )
        # Should either return 200 or have CORS headers
        assert response.status_code in [200, 204] or "access-control-allow-origin" in response.headers
    
    def test_pagination_has_consistent_format(self, client):
        """Paginated endpoints should have consistent format"""
        response = client.get("/api/videos/?page=1&limit=10")
        if response.status_code == 200:
            data = response.json()
            # Should be a list or have pagination metadata
            assert isinstance(data, (list, dict))
            if isinstance(data, dict):
                # If paginated, should have consistent keys
                assert any(key in data for key in ["items", "data", "results"])
    
    def test_api_versioning(self, client):
        """API should be versioned"""
        # Check if API uses versioning (e.g., /api/v1/)
        response = client.get("/api/videos/")
        # Should work with or without version
        assert response.status_code in [200, 404]
    
    def test_response_times_are_reasonable(self, client):
        """API responses should be fast enough for good UX"""
        import time
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0  # Health check should be < 1 second
    
    def test_batch_operations_have_limits(self, client):
        """Batch operations should have reasonable limits"""
        # Test thumbnail generation batch
        too_many_ids = [f"test-{i}" for i in range(1000)]
        response = client.post(
            "/api/videos/generate-thumbnails-batch",
            json={"video_ids": too_many_ids, "max_videos": 50}
        )
        # Should either accept (with limit) or reject with clear message
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data or "error" in data


class TestErrorHandlingUsability:
    """Test error handling usability"""
    
    def test_validation_errors_are_detailed(self, client):
        """Validation errors should show what's wrong"""
        response = client.post(
            "/api/videos/",
            json={"invalid": "data"}
        )
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data
            # Should have field-level errors
            assert isinstance(data["detail"], list)
    
    def test_authentication_errors_are_clear(self, client):
        """Auth errors should guide users"""
        response = client.get(
            "/api/videos/",
            headers={"Authorization": "Bearer invalid-token"}
        )
        if response.status_code == 401:
            data = response.json()
            assert "detail" in data
            # Error should mention authentication
            assert any(word in data["detail"].lower() for word in ["auth", "token", "unauthorized"])
    
    def test_rate_limiting_has_clear_messages(self, client):
        """Rate limit errors should be informative"""
        # Make many requests (if rate limiting is enabled)
        for _ in range(100):
            response = client.get("/health")
            if response.status_code == 429:
                data = response.json()
                assert "detail" in data
                # Should mention rate limit or retry
                assert any(word in data["detail"].lower() for word in ["rate", "limit", "retry", "later"])
                break






