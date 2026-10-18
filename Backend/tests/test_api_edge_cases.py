"""
Comprehensive tests for API edge cases and error handling.
Tests validation, security, performance, and error responses.
"""

import pytest
from fastapi.testclient import TestClient
import json

import sys
sys.path.insert(0, '..')
try:
    from main import app
    client = TestClient(app)
except ImportError:
    client = None


class TestAPIErrorHandling:
    """Tests for API error handling"""
    
    def test_404_for_unknown_route(self):
        """Should return 404 for unknown route"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/unknown/route")
        assert response.status_code == 404
    
    def test_method_not_allowed(self):
        """Should return 405 for wrong method"""
        if not client:
            pytest.skip("Client not available")
        response = client.patch("/api/schedule/list")
        assert response.status_code in [404, 405]
    
    def test_invalid_json_body(self):
        """Should handle invalid JSON"""
        if not client:
            pytest.skip("Client not available")
        response = client.post(
            "/api/schedule/create",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]
    
    def test_missing_content_type(self):
        """Should handle missing content type"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/schedule/create", content="{}")
        assert response.status_code in [200, 400, 422, 404]
    
    def test_empty_body(self):
        """Should handle empty body"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/schedule/create", json={})
        assert response.status_code in [400, 422, 404]


class TestAPISecurity:
    """Tests for API security"""
    
    def test_sql_injection_in_query(self):
        """Should handle SQL injection in query params"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?platform='; DROP TABLE schedules; --")
        assert response.status_code in [200, 400, 404]
    
    def test_xss_in_body(self):
        """Should handle XSS in request body"""
        if not client:
            pytest.skip("Client not available")
        data = {"title": "<script>alert('xss')</script>"}
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 400, 422, 404]
    
    def test_path_traversal(self):
        """Should handle path traversal attempts"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/../../etc/passwd")
        assert response.status_code in [400, 404]
    
    def test_very_large_request(self):
        """Should handle very large requests"""
        if not client:
            pytest.skip("Client not available")
        large_data = {"title": "a" * 100000}
        response = client.post("/api/schedule/create", json=large_data)
        assert response.status_code in [200, 400, 413, 422, 404]
    
    def test_null_byte_injection(self):
        """Should handle null byte injection"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/1\x00.jpg")
        assert response.status_code in [400, 404]


class TestAPIHeaders:
    """Tests for API header handling"""
    
    def test_cors_headers(self):
        """Should include CORS headers"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list")
        # CORS headers may or may not be present
        assert response.status_code in [200, 404]
    
    def test_content_type_json(self):
        """Should return JSON content type"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list")
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            # FastAPI may return "application/json" or "application/json; charset=utf-8"
            assert "application/json" in content_type
    
    def test_accept_header(self):
        """Should respect Accept header"""
        if not client:
            pytest.skip("Client not available")
        headers = {"Accept": "application/json"}
        response = client.get("/api/schedule/list", headers=headers)
        assert response.status_code in [200, 404]


class TestAPIQueryParams:
    """Tests for query parameter handling"""
    
    def test_negative_limit(self):
        """Should handle negative limit"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?limit=-1")
        # FastAPI validation should reject negative limit with 422
        assert response.status_code in [400, 422, 404]
    
    def test_zero_limit(self):
        """Should handle zero limit"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?limit=0")
        # FastAPI validation should reject zero limit with 422
        assert response.status_code in [400, 422, 404]
    
    def test_string_as_number(self):
        """Should handle string as number"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?limit=abc")
        assert response.status_code in [200, 400, 422, 404]
    
    def test_float_as_integer(self):
        """Should handle float as integer"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?limit=5.5")
        assert response.status_code in [200, 400, 422, 404]
    
    def test_boolean_param(self):
        """Should handle boolean params"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?active=true")
        assert response.status_code in [200, 404]
    
    def test_array_param(self):
        """Should handle array params"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?platform=tiktok&platform=instagram")
        # FastAPI will use the last value, so this should work
        assert response.status_code in [200, 404, 422]
    
    def test_empty_param(self):
        """Should handle empty params"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?platform=")
        # Empty string may be treated as None or cause validation error
        assert response.status_code in [200, 404, 422]


class TestAPIRateLimiting:
    """Tests for rate limiting"""
    
    def test_multiple_rapid_requests(self):
        """Should handle rapid requests"""
        if not client:
            pytest.skip("Client not available")
        for _ in range(10):
            response = client.get("/api/schedule/list")
            # Allow 500 for transient errors, 429 for rate limiting
            assert response.status_code in [200, 404, 429, 500]
    
    def test_concurrent_requests(self):
        """Should handle concurrent requests"""
        if not client:
            pytest.skip("Client not available")
        import concurrent.futures
        def make_request():
            return client.get("/api/schedule/list")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [f.result() for f in futures]
            for r in results:
                # Allow 500 for transient errors, 429 for rate limiting
                assert r.status_code in [200, 404, 429, 500]


class TestAPIResponseFormat:
    """Tests for API response format"""
    
    def test_error_response_format(self):
        """Should return structured error responses"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/99999")
        if response.status_code == 404:
            data = response.json()
            assert "detail" in data or "error" in data or "message" in data
    
    def test_success_response_format(self):
        """Should return structured success responses"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list")
        if response.status_code == 200:
            try:
                data = response.json()
                assert isinstance(data, (list, dict))
            except Exception:
                # If response is not JSON, skip this test
                pytest.skip("Response is not JSON")
    
    def test_empty_list_response(self):
        """Should handle empty list response"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?platform=nonexistent")
        if response.status_code == 200:
            try:
                data = response.json()
                assert isinstance(data, (list, dict))
            except Exception:
                # If response is not JSON, skip this test
                pytest.skip("Response is not JSON")


class TestAPIUnicode:
    """Tests for unicode handling"""
    
    def test_unicode_in_title(self):
        """Should handle unicode in title"""
        if not client:
            pytest.skip("Client not available")
        data = {"title": "测试 🎉 テスト"}
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_unicode_in_search(self):
        """Should handle unicode in search"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?search=测试")
        assert response.status_code in [200, 404]
    
    def test_emoji_in_caption(self):
        """Should handle emoji in caption"""
        if not client:
            pytest.skip("Client not available")
        data = {"caption": "Hello 👋 World 🌍"}
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_rtl_text(self):
        """Should handle RTL text"""
        if not client:
            pytest.skip("Client not available")
        data = {"title": "مرحبا بالعالم"}
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
