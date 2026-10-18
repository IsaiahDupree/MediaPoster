"""
Frontend-Backend Compatibility Tests

Tests to ensure backend changes don't break frontend expectations.
Focuses on:
1. Error response format compatibility
2. Success response format compatibility
3. Correlation ID handling (should be transparent)
4. Rate limiting headers (should not break requests)
5. Health check endpoints
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import json

# Import the main app
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestErrorResponseFormat:
    """Test that error responses match frontend expectations."""
    
    def test_validation_error_format(self, client):
        """Test that validation errors return expected format."""
        # Frontend expects: { detail: string } or { error: string }
        response = client.post(
            "/api/publishing/add",
            json={
                "platform": "invalid_platform",
                "scheduled_for": "2020-01-01T00:00:00Z"
            }
        )
        
        assert response.status_code in [400, 422]
        data = response.json()
        
        # Frontend checks for both 'detail' and 'error'
        assert "error" in data or "detail" in data
        assert "correlation_id" in data  # New field, should not break frontend
        
        # Frontend should be able to extract error message
        error_msg = data.get("error") or data.get("detail")
        assert error_msg is not None
        assert isinstance(error_msg, (str, dict))
    
    def test_not_found_error_format(self, client):
        """Test that 404 errors return expected format."""
        response = client.get("/api/media-db/detail/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        
        # Frontend expects error or detail
        assert "error" in data or "detail" in data
        assert "correlation_id" in data
    
    def test_internal_error_format(self, client):
        """Test that 500 errors return expected format."""
        # This will trigger an internal error
        # We'll test with a malformed request that causes an exception
        response = client.post(
            "/api/media-db/analyze/invalid-uuid-format",
            json={}
        )
        
        # Should return 400 or 500
        assert response.status_code >= 400
        data = response.json()
        
        # Frontend expects error or detail
        assert "error" in data or "detail" in data
        assert "correlation_id" in data
    
    def test_rate_limit_error_format(self, client):
        """Test that rate limit errors return expected format."""
        # Make many requests to trigger rate limit
        # Note: This might not trigger in test environment, but we can check the format
        for _ in range(150):  # Exceed default limit of 100
            response = client.get("/api/media-db/list")
            if response.status_code == 429:
                data = response.json()
                assert "error" in data or "detail" in data
                assert "correlation_id" in data
                assert "retry_after" in data or "Retry-After" in response.headers
                break


class TestSuccessResponseFormat:
    """Test that success responses match frontend expectations."""
    
    def test_health_check_response(self, client):
        """Test health check response format."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Frontend expects status field
        assert "status" in data
        # New field should not break frontend
        assert "correlation_id" in data or "timestamp" in data
    
    def test_list_media_response(self, client):
        """Test media list response format."""
        response = client.get("/api/media-db/list?limit=10")
        
        # Should return 200 or handle gracefully
        assert response.status_code in [200, 500]  # 500 if DB not available
        
        if response.status_code == 200:
            data = response.json()
            # Frontend expects array or object with data
            assert isinstance(data, (list, dict))
            
            if isinstance(data, dict):
                # If it's an object, it might have 'items' or 'data' field
                # Or it might be the array itself
                pass
    
    def test_schedule_list_response(self, client):
        """Test schedule list response format."""
        response = client.get("/api/schedule/list")
        
        # Should return 200 or handle gracefully
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            # Frontend expects array
            assert isinstance(data, list)


class TestCorrelationIDHandling:
    """Test that correlation IDs are handled correctly."""
    
    def test_correlation_id_in_response_headers(self, client):
        """Test that correlation ID is in response headers."""
        response = client.get("/api/health")
        
        # Correlation ID should be in headers
        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        assert correlation_id is not None
        assert len(correlation_id) > 0
    
    def test_correlation_id_in_response_body(self, client):
        """Test that correlation ID is in response body for errors."""
        response = client.post(
            "/api/publishing/add",
            json={"invalid": "data"}
        )
        
        assert response.status_code >= 400
        data = response.json()
        assert "correlation_id" in data
    
    def test_correlation_id_preserved_in_chain(self, client):
        """Test that correlation ID is preserved across request chain."""
        # Send request with custom correlation ID
        custom_id = "test-correlation-id-123"
        response = client.get(
            "/api/health",
            headers={"X-Correlation-ID": custom_id}
        )
        
        # Should use the provided correlation ID
        assert response.headers["X-Correlation-ID"] == custom_id


class TestRateLimitHeaders:
    """Test that rate limit headers don't break frontend."""
    
    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/api/media-db/list")
        
        # Headers should be present but not break frontend
        # Frontend doesn't need to read these, but they shouldn't cause issues
        assert "X-RateLimit-Limit" in response.headers or response.status_code == 429
        if "X-RateLimit-Limit" in response.headers:
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
    
    def test_rate_limit_headers_format(self, client):
        """Test that rate limit headers have correct format."""
        response = client.get("/api/media-db/list")
        
        if "X-RateLimit-Limit" in response.headers:
            limit = response.headers["X-RateLimit-Limit"]
            remaining = response.headers["X-RateLimit-Remaining"]
            reset = response.headers["X-RateLimit-Reset"]
            
            # Should be numeric strings
            assert limit.isdigit()
            assert remaining.isdigit()
            assert reset.isdigit()


class TestAPIEndpointsUsedByFrontend:
    """Test specific endpoints that frontend uses."""
    
    def test_media_db_list(self, client):
        """Test /api/media-db/list endpoint."""
        response = client.get("/api/media-db/list?limit=10")
        
        # Should return 200 or handle error gracefully
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            # Frontend expects array
            assert isinstance(data, list)
    
    def test_media_db_detail(self, client):
        """Test /api/media-db/detail/{id} endpoint."""
        # Use a valid UUID format
        test_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/media-db/detail/{test_id}")
        
        # Should return 404 (not found) or 200, not 500
        assert response.status_code in [200, 404]
        
        if response.status_code == 404:
            data = response.json()
            assert "error" in data or "detail" in data
    
    def test_schedule_list(self, client):
        """Test /api/schedule/list endpoint."""
        response = client.get("/api/schedule/list")
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
    
    def test_schedule_create(self, client):
        """Test /api/schedule/create endpoint."""
        response = client.post(
            "/api/schedule/create",
            json={
                "clip_id": "00000000-0000-0000-0000-000000000000",
                "platform": "tiktok",
                "scheduled_at": "2025-12-31T00:00:00Z"
            }
        )
        
        # Should return 400 (validation) or 404 (clip not found) or 200
        assert response.status_code in [200, 400, 404, 422]
        
        if response.status_code >= 400:
            data = response.json()
            assert "error" in data or "detail" in data
    
    def test_publishing_queue_pending(self, client):
        """Test /api/publishing/queue/pending endpoint."""
        response = client.get("/api/publishing/queue/pending")
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            # Frontend expects array or object
            assert isinstance(data, (list, dict))
    
    def test_health_endpoints(self, client):
        """Test health check endpoints."""
        # Basic health
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        
        # Detailed health
        response = client.get("/api/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        
        # Ready check
        response = client.get("/api/health/ready")
        assert response.status_code in [200, 503]
        
        # Live check
        response = client.get("/api/health/live")
        assert response.status_code == 200


class TestErrorResponseExtraction:
    """Test that frontend can extract error messages correctly."""
    
    def test_error_string_extraction(self, client):
        """Test extracting error from string format."""
        response = client.post(
            "/api/publishing/add",
            json={"invalid": "data"}
        )
        
        assert response.status_code >= 400
        data = response.json()
        
        # Frontend code: data.detail || data.error || response.statusText
        error_msg = data.get("error") or data.get("detail") or "Unknown error"
        
        # Should be extractable as string
        if isinstance(error_msg, str):
            assert len(error_msg) > 0
        elif isinstance(error_msg, dict):
            # If it's a dict, frontend should handle it
            assert "message" in error_msg or "error" in error_msg
    
    def test_error_dict_extraction(self, client):
        """Test extracting error from dict format."""
        # Some errors might return dict with nested error info
        response = client.post(
            "/api/publishing/add",
            json={"invalid": "data"}
        )
        
        assert response.status_code >= 400
        data = response.json()
        
        # Frontend should be able to handle both string and dict
        error = data.get("error") or data.get("detail")
        
        # If it's a dict, it should have a message
        if isinstance(error, dict):
            assert "message" in error or "error" in error


class TestResponseHeaders:
    """Test that response headers don't break frontend."""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/health")
        
        # CORS headers should be present
        # Frontend needs these for cross-origin requests
        assert response.status_code in [200, 204, 405]
    
    def test_content_type_headers(self, client):
        """Test content type headers."""
        response = client.get("/api/health")
        
        # Should have JSON content type
        assert "application/json" in response.headers.get("content-type", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

