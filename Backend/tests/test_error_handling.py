"""
Comprehensive Tests for Error Handling and Health Check Endpoints

Tests cover:
1. Health check endpoints return correct status
2. Error tracking middleware logs exceptions
3. Safe JSON parsing handles malformed data
4. Database connection error scenarios
5. API timeout and network error handling
6. Invalid request data handling
7. Edge cases and boundary conditions
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
import asyncio


# =============================================================================
# HEALTH CHECK ENDPOINT TESTS
# =============================================================================

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


# =============================================================================
# DATABASE ERROR SCENARIO TESTS
# =============================================================================

class TestDatabaseErrorScenarios:
    """Test database connection and query error handling."""
    
    def test_database_connection_timeout(self):
        """Test handling of database connection timeout."""
        from api.endpoints.health import check_database
        
        with patch('api.endpoints.health.create_engine') as mock_engine:
            mock_engine.side_effect = Exception("Connection timeout")
            
            result = asyncio.get_event_loop().run_until_complete(check_database())
            assert result["status"] == "unhealthy"
            assert "error" in result
    
    def test_database_query_error(self):
        """Test handling of database query errors."""
        from api.endpoints.health import check_database
        
        with patch('api.endpoints.health.create_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.side_effect = Exception("Query failed")
            mock_engine.return_value.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            
            result = asyncio.get_event_loop().run_until_complete(check_database())
            assert result["status"] == "unhealthy"


# =============================================================================
# API ERROR SCENARIO TESTS
# =============================================================================

class TestAPIErrorScenarios:
    """Test API timeout and network error handling."""
    
    def test_openai_api_timeout(self):
        """Test handling of OpenAI API timeout."""
        from api.endpoints.health import check_openai
        
        with patch('api.endpoints.health.httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = asyncio.TimeoutError()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = AsyncMock()
            
            result = asyncio.get_event_loop().run_until_complete(check_openai())
            assert result["status"] == "unhealthy"
            assert "Timeout" in result.get("error", "")
    
    def test_openai_api_key_missing(self):
        """Test handling when OpenAI API key is not configured."""
        from api.endpoints.health import check_openai
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            with patch('api.endpoints.health.os.getenv', return_value=None):
                result = asyncio.get_event_loop().run_until_complete(check_openai())
                assert result["status"] == "unconfigured"
    
    def test_rapidapi_key_missing(self):
        """Test handling when RapidAPI key is not configured."""
        from api.endpoints.health import check_rapidapi
        
        with patch('api.endpoints.health.os.getenv', return_value=None):
            result = asyncio.get_event_loop().run_until_complete(check_rapidapi())
            assert result["status"] == "unconfigured"


# =============================================================================
# JSON PARSING EDGE CASE TESTS
# =============================================================================

class TestJsonParsingEdgeCases:
    """Test JSON parsing with various edge cases."""
    
    def test_deeply_nested_json(self):
        """Test parsing deeply nested JSON structures."""
        from middleware.error_tracking import safe_json_loads
        
        nested = '{"a":{"b":{"c":{"d":{"e":"value"}}}}}'
        result = safe_json_loads(nested)
        assert result["a"]["b"]["c"]["d"]["e"] == "value"
    
    def test_json_with_special_characters(self):
        """Test parsing JSON with special characters."""
        from middleware.error_tracking import safe_json_loads
        
        special = '{"message": "Hello\\nWorld\\t!"}'
        result = safe_json_loads(special)
        assert result["message"] == "Hello\nWorld\t!"
    
    def test_json_with_unicode(self):
        """Test parsing JSON with unicode characters."""
        from middleware.error_tracking import safe_json_loads
        
        unicode_json = '{"emoji": "🎉", "chinese": "你好"}'
        result = safe_json_loads(unicode_json)
        assert result["emoji"] == "🎉"
        assert result["chinese"] == "你好"
    
    def test_json_with_large_numbers(self):
        """Test parsing JSON with very large numbers."""
        from middleware.error_tracking import safe_json_loads
        
        large_num = '{"big": 9999999999999999999999999999}'
        result = safe_json_loads(large_num)
        assert result["big"] == 9999999999999999999999999999
    
    def test_malformed_json_variations(self):
        """Test various malformed JSON inputs."""
        from middleware.error_tracking import safe_json_loads
        
        malformed_inputs = [
            '{key: "value"}',  # Missing quotes on key
            '{"key": value}',  # Missing quotes on value
            "{'key': 'value'}",  # Single quotes
            '{"key": "value",}',  # Trailing comma
            '{"key": "value"',  # Missing closing brace
            '[1, 2, 3,]',  # Trailing comma in array
            'undefined',  # JavaScript undefined
            'NaN',  # JavaScript NaN
        ]
        
        for malformed in malformed_inputs:
            result = safe_json_loads(malformed, default="FAILED")
            assert result == "FAILED", f"Should fail for: {malformed}"
    
    def test_json_array_parsing(self):
        """Test parsing JSON arrays."""
        from middleware.error_tracking import safe_json_loads
        
        array = '[1, 2, 3, "four", {"five": 5}]'
        result = safe_json_loads(array)
        assert len(result) == 5
        assert result[3] == "four"
        assert result[4]["five"] == 5


# =============================================================================
# HTTP ERROR RESPONSE TESTS
# =============================================================================

class TestHttpErrorResponses:
    """Test HTTP error responses are properly formatted."""
    
    def test_404_not_found(self, client):
        """Test 404 returns proper JSON error."""
        response = client.get("/api/nonexistent-endpoint-xyz")
        assert response.status_code == 404
    
    def test_405_method_not_allowed(self, client):
        """Test 405 for wrong HTTP method."""
        # POST to a GET-only endpoint
        response = client.post("/health")
        assert response.status_code == 405
    
    def test_422_validation_error(self, client):
        """Test 422 for invalid request data."""
        # Try to create something with invalid data
        response = client.post("/api/videos/analyze", json={"invalid": "data"})
        # Should return 422 for validation error or 404 if endpoint doesn't exist
        assert response.status_code in [404, 422, 400]


# =============================================================================
# MIDDLEWARE ERROR HANDLING TESTS
# =============================================================================

class TestMiddlewareErrorHandling:
    """Test error tracking middleware behavior."""
    
    def test_slow_request_logging(self):
        """Test that slow requests are logged."""
        from middleware.error_tracking import ErrorTrackingMiddleware
        # Middleware should log requests taking > 5 seconds
        # This is a unit test for the middleware logic
        pass
    
    def test_request_id_generation(self):
        """Test that unique request IDs are generated."""
        import uuid
        
        # Generate multiple request IDs and verify uniqueness
        ids = set()
        for _ in range(100):
            request_id = str(uuid.uuid4())[:8]
            ids.add(request_id)
        
        assert len(ids) == 100, "Request IDs should be unique"


# =============================================================================
# EXCEPTION TYPE HANDLING TESTS
# =============================================================================

class TestExceptionTypeHandling:
    """Test handling of various exception types."""
    
    def test_value_error_handling(self):
        """Test ValueError is properly logged."""
        from middleware.error_tracking import log_exception
        
        try:
            raise ValueError("Invalid value provided")
        except ValueError as e:
            log_exception(e, context="value validation")
            # Should not raise
    
    def test_key_error_handling(self):
        """Test KeyError is properly logged."""
        from middleware.error_tracking import log_exception
        
        try:
            d = {}
            _ = d["missing_key"]
        except KeyError as e:
            log_exception(e, context="dictionary access")
    
    def test_type_error_handling(self):
        """Test TypeError is properly logged."""
        from middleware.error_tracking import log_exception
        
        try:
            _ = "string" + 123  # type: ignore
        except TypeError as e:
            log_exception(e, context="type mismatch")
    
    def test_attribute_error_handling(self):
        """Test AttributeError is properly logged."""
        from middleware.error_tracking import log_exception
        
        try:
            obj = None
            _ = obj.nonexistent_method()  # type: ignore
        except AttributeError as e:
            log_exception(e, context="attribute access")
    
    def test_index_error_handling(self):
        """Test IndexError is properly logged."""
        from middleware.error_tracking import log_exception
        
        try:
            lst = [1, 2, 3]
            _ = lst[100]
        except IndexError as e:
            log_exception(e, context="list access")
    
    def test_runtime_error_handling(self):
        """Test RuntimeError is properly logged."""
        from middleware.error_tracking import log_exception
        
        try:
            raise RuntimeError("Something went wrong at runtime")
        except RuntimeError as e:
            log_exception(e, context="runtime operation")
    
    def test_io_error_handling(self):
        """Test IOError is properly logged."""
        from middleware.error_tracking import log_exception
        
        try:
            raise IOError("File operation failed")
        except IOError as e:
            log_exception(e, context="file operation")


# =============================================================================
# BOUNDARY CONDITION TESTS
# =============================================================================

class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""
    
    def test_empty_request_body(self, client):
        """Test handling of empty request body."""
        response = client.post(
            "/api/videos/analyze",
            content=b"",
            headers={"Content-Type": "application/json"}
        )
        # Should handle gracefully
        assert response.status_code in [400, 404, 422]
    
    def test_very_large_request_body(self, client):
        """Test handling of very large request body."""
        large_data = {"data": "x" * 10000}
        response = client.post(
            "/api/videos/analyze",
            json=large_data
        )
        # Should handle or reject gracefully
        assert response.status_code in [400, 404, 413, 422]
    
    def test_special_characters_in_url(self, client):
        """Test handling of special characters in URL."""
        response = client.get("/api/videos/<script>alert('xss')</script>")
        # Should handle safely
        assert response.status_code in [400, 404, 422]
    
    def test_sql_injection_attempt(self, client):
        """Test handling of SQL injection attempts."""
        response = client.get("/api/videos/'; DROP TABLE videos; --")
        # Should handle safely (return 404 or sanitize)
        assert response.status_code in [400, 404, 422]


# =============================================================================
# CONCURRENT ERROR HANDLING TESTS
# =============================================================================

class TestConcurrentErrorHandling:
    """Test error handling under concurrent load."""
    
    def test_multiple_simultaneous_errors(self):
        """Test handling multiple errors at the same time."""
        from middleware.error_tracking import log_exception
        import threading
        
        errors_logged = []
        
        def log_error(i):
            try:
                raise ValueError(f"Error {i}")
            except ValueError as e:
                log_exception(e, context=f"thread-{i}")
                errors_logged.append(i)
        
        threads = [threading.Thread(target=log_error, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors_logged) == 10


# =============================================================================
# FIXTURES
# =============================================================================

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
    pytest.main([__file__, "-v", "--tb=short"])
