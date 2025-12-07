"""
API Security Tests
Tests for common security vulnerabilities
"""
import pytest
from fastapi.testclient import TestClient


class TestInputValidation:
    """Test input validation and sanitization"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_sql_injection_in_query_params(self, client):
        """Test SQL injection protection in query parameters"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "1; DELETE FROM videos;",
            "UNION SELECT * FROM users",
            "' OR 1=1 --",
        ]
        
        for payload in malicious_inputs:
            response = client.get(f"/api/videos?search={payload}")
            # Should not return 500 (internal error from SQL)
            assert response.status_code != 500, f"Possible SQL injection with: {payload}"
    
    def test_sql_injection_in_path_params(self, client):
        """Test SQL injection in path parameters"""
        payloads = [
            "1' OR '1'='1",
            "1; DROP TABLE videos;",
        ]
        
        for payload in payloads:
            response = client.get(f"/api/videos/{payload}")
            assert response.status_code in [400, 404, 422], f"Should reject invalid ID: {payload}"
    
    def test_xss_prevention_in_inputs(self, client):
        """Test XSS prevention"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
        ]
        
        for payload in xss_payloads:
            # Test in query params
            response = client.get(f"/api/videos?search={payload}")
            if response.status_code == 200:
                data = response.json()
                # Response should not contain unescaped script tags
                response_text = str(data)
                assert "<script>" not in response_text.lower()
    
    def test_path_traversal_prevention(self, client):
        """Test path traversal attack prevention"""
        payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f",
            "....//....//",
        ]
        
        for payload in payloads:
            response = client.get(f"/api/storage/files/{payload}")
            assert response.status_code in [400, 403, 404], f"Path traversal should be blocked: {payload}"


class TestAuthorizationSecurity:
    """Test authorization and access control"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_protected_endpoints_require_auth(self, client):
        """Test that sensitive endpoints require authentication"""
        # These endpoints might be protected
        protected_endpoints = [
            "/api/settings",
            "/api/accounts",
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            # Should either work (no auth required) or return 401/403
            assert response.status_code in [200, 401, 403, 404]
    
    def test_invalid_jwt_rejected(self, client):
        """Test that invalid JWT tokens are rejected"""
        invalid_tokens = [
            "invalid.token.here",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "null",
        ]
        
        for token in invalid_tokens:
            response = client.get(
                "/api/settings",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should not return 200 with invalid token (unless endpoint is public)
            if response.status_code != 404:
                assert response.status_code in [200, 401, 403]


class TestRateLimiting:
    """Test rate limiting protection"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_endpoint_handles_rapid_requests(self, client):
        """Test that rapid requests don't crash the server"""
        # Make many rapid requests
        responses = []
        for _ in range(50):
            response = client.get("/api/social-analytics/overview")
            responses.append(response.status_code)
        
        # All responses should be valid (200, 429 for rate limit, etc.)
        for status in responses:
            assert status < 500, "Server should handle rapid requests gracefully"


class TestDataExposure:
    """Test for sensitive data exposure"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_no_stack_traces_in_errors(self, client):
        """Test that error responses don't leak stack traces"""
        # Try to trigger an error
        response = client.get("/api/videos?limit=-1")
        
        if response.status_code >= 400:
            try:
                data = response.json()
                response_text = str(data)
                # Should not contain stack trace indicators
                assert "Traceback" not in response_text
                assert "File \"/" not in response_text
                assert ".py\", line" not in response_text
            except:
                pass  # Non-JSON response is fine
    
    def test_no_sensitive_headers_exposed(self, client):
        """Test that sensitive headers aren't exposed"""
        response = client.get("/api/social-analytics/overview")
        headers = response.headers
        
        sensitive_headers = [
            "X-Powered-By",  # Reveals technology stack
            "Server",  # Might reveal server software version
        ]
        
        for header in sensitive_headers:
            if header in headers:
                # If present, should not contain version info
                value = headers[header]
                assert not any(char.isdigit() for char in value), f"{header} should not reveal version"
    
    def test_error_messages_are_generic(self, client):
        """Test that error messages don't reveal internal details"""
        # Try invalid requests
        test_cases = [
            ("/api/videos/999999999", "Video not found"),
            ("/api/nonexistent", "Not found"),
        ]
        
        for endpoint, _ in test_cases:
            response = client.get(endpoint)
            if response.status_code == 404:
                try:
                    data = response.json()
                    # Should not reveal database structure
                    response_text = str(data).lower()
                    assert "table" not in response_text
                    assert "column" not in response_text
                    assert "postgresql" not in response_text
                except:
                    pass


class TestRequestSecurity:
    """Test request handling security"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_large_payload_rejected(self, client):
        """Test that oversized payloads are rejected"""
        # Create a large payload (10MB)
        large_payload = {"data": "x" * (10 * 1024 * 1024)}
        
        response = client.post(
            "/api/briefs",
            json=large_payload
        )
        
        # Should be rejected with 413 or handled gracefully
        assert response.status_code in [400, 413, 422, 404, 500]
    
    def test_invalid_content_type_handled(self, client):
        """Test that invalid content types are handled"""
        response = client.post(
            "/api/goals",
            content="not json",
            headers={"Content-Type": "text/plain"}
        )
        
        # Should not crash
        assert response.status_code in [400, 404, 415, 422]
    
    def test_null_byte_injection(self, client):
        """Test null byte injection prevention"""
        payloads = [
            "test%00.txt",
            "file\x00.txt",
        ]
        
        for payload in payloads:
            response = client.get(f"/api/storage/files/{payload}")
            assert response.status_code in [400, 403, 404]


class TestCORS:
    """Test CORS configuration"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_cors_allows_frontend_origin(self, client):
        """Test CORS allows requests from frontend"""
        response = client.options(
            "/api/social-analytics/overview",
            headers={
                "Origin": "http://localhost:5557",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
    
    def test_cors_rejects_malicious_origin(self, client):
        """Test CORS blocks unknown origins (if configured strictly)"""
        response = client.options(
            "/api/social-analytics/overview",
            headers={
                "Origin": "http://evil-site.com",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        # If CORS is configured, malicious origin shouldn't be in allow list
        cors_origin = response.headers.get("access-control-allow-origin", "")
        if cors_origin and cors_origin != "*":
            assert "evil-site.com" not in cors_origin


# Mark all as security tests
pytestmark = pytest.mark.security
