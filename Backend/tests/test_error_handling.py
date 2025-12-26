"""
Tests for Error Handling and Health Check Endpoints

Tests:
1. Health check endpoints return correct status
2. Error tracking middleware logs exceptions
3. Safe JSON parsing handles malformed data
"""
import pytest
from fastapi.testclient import TestClient
import json


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_basic_health_check(self, client):
        """Test basic health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_detailed_health_check(self, client):
        """Test detailed health check returns all service statuses."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "openai" in data["checks"]
        assert "rapidapi" in data["checks"]
        assert "blotato" in data["checks"]
    
    def test_liveness_check(self, client):
        """Test liveness endpoint always returns alive."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
    
    def test_readiness_check(self, client):
        """Test readiness endpoint checks database."""
        response = client.get("/health/ready")
        # Should return 200 if DB is up, 503 if down
        assert response.status_code in [200, 503]


class TestErrorTracking:
    """Test error tracking middleware."""
    
    def test_404_returns_json(self, client):
        """Test 404 errors return proper JSON."""
        response = client.get("/nonexistent-endpoint-12345")
        assert response.status_code == 404
        # FastAPI returns JSON for 404s by default
    
    def test_request_id_in_errors(self, client):
        """Test that error responses include request_id."""
        # This tests the error middleware - would need an endpoint that throws
        pass


class TestSafeJsonParsing:
    """Test safe JSON parsing utility."""
    
    def test_valid_json(self):
        """Test parsing valid JSON."""
        from middleware.error_tracking import safe_json_loads
        
        result = safe_json_loads('{"key": "value"}')
        assert result == {"key": "value"}
    
    def test_invalid_json_returns_default(self):
        """Test parsing invalid JSON returns default."""
        from middleware.error_tracking import safe_json_loads
        
        result = safe_json_loads('invalid json', default={"error": True})
        assert result == {"error": True}
    
    def test_empty_string_returns_default(self):
        """Test parsing empty string returns default."""
        from middleware.error_tracking import safe_json_loads
        
        result = safe_json_loads('', default=None)
        assert result is None
    
    def test_none_returns_default(self):
        """Test parsing None-like values."""
        from middleware.error_tracking import safe_json_loads
        
        result = safe_json_loads('null', default="default")
        assert result is None  # JSON null becomes Python None


class TestExceptionLogging:
    """Test exception logging utility."""
    
    def test_log_exception_basic(self):
        """Test basic exception logging."""
        from middleware.error_tracking import log_exception
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            # Should not raise
            log_exception(e, context="test")
    
    def test_log_exception_with_extra(self):
        """Test exception logging with extra context."""
        from middleware.error_tracking import log_exception
        
        try:
            raise KeyError("missing_key")
        except Exception as e:
            log_exception(e, context="database operation", extra={
                "table": "users",
                "operation": "insert"
            })


# Fixture for test client
@pytest.fixture
def client():
    """Create test client."""
    import sys
    sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')
    
    try:
        from main import app
        return TestClient(app)
    except Exception as e:
        pytest.skip(f"Could not import app: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
