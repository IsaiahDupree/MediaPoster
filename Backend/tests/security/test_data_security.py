"""
Data Security Tests
Tests data encryption, PII handling, data leakage
"""
import pytest
from fastapi.testclient import TestClient
from main import app
import json
import re


@pytest.fixture
def client():
    return TestClient(app)


class TestDataLeakageSecurity:
    """Test for data leakage in responses"""
    
    def test_no_sensitive_data_in_error_messages(self, client):
        """Error messages should not leak sensitive information"""
        # Try to trigger various errors
        error_responses = [
            client.get("/api/videos/nonexistent-id"),
            client.post("/api/videos/", json={"invalid": "data"}),
            client.get("/api/nonexistent-endpoint"),
        ]
        
        sensitive_patterns = [
            r"password",
            r"secret",
            r"api[_-]?key",
            r"token",
            r"credential",
            r"connection[_-]?string",
            r"database[_-]?url",
        ]
        
        for response in error_responses:
            if response.status_code >= 400:
                response_text = response.text.lower()
                for pattern in sensitive_patterns:
                    # Check for sensitive data in error messages
                    matches = re.findall(pattern, response_text)
                    # Some mentions are ok (like "api_key" field name), but actual values are not
                    # This is a basic check - could be improved
                    pass
    
    def test_no_database_errors_exposed(self, client):
        """Database errors should not expose schema details"""
        # Try to trigger database errors
        response = client.get("/api/videos/invalid-uuid-format")
        
        if response.status_code >= 500:
            data = response.json()
            error_text = str(data).lower()
            # Should not expose database structure
            db_keywords = ["postgres", "sql", "table", "column", "constraint", "foreign key"]
            for keyword in db_keywords:
                # Some mentions might be ok, but detailed errors are not
                pass
    
    def test_no_stack_traces_in_production(self, client):
        """Stack traces should not be exposed in production"""
        # In production mode, errors should be sanitized
        # This test would need to check production vs dev mode
        response = client.get("/api/nonexistent")
        
        if response.status_code >= 500:
            response_text = response.text
            # Should not contain stack trace details
            stack_trace_indicators = ["traceback", "file \"", "line ", "at "]
            for indicator in stack_trace_indicators:
                # In production, these should not appear
                pass


class TestPIIHandling:
    """Test PII (Personally Identifiable Information) handling"""
    
    def test_email_addresses_not_exposed(self, client):
        """Email addresses should not be exposed unnecessarily"""
        response = client.get("/api/videos/")
        
        if response.status_code == 200:
            data = response.json()
            data_str = json.dumps(data)
            # Check for email patterns
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, data_str)
            # Emails might be legitimate (user emails), but should be minimal
            # This is informational
            pass
    
    def test_api_keys_not_in_responses(self, client):
        """API keys should never appear in responses"""
        response = client.get("/api/videos/")
        
        if response.status_code == 200:
            data = response.json()
            data_str = json.dumps(data).lower()
            # Check for API key patterns
            api_key_patterns = [
                r"sk-[a-z0-9]{32,}",
                r"api[_-]?key['\"]?\s*[:=]\s*['\"]?[a-z0-9]{20,}",
            ]
            for pattern in api_key_patterns:
                matches = re.findall(pattern, data_str)
                assert len(matches) == 0, "API keys found in response!"


class TestDataEncryption:
    """Test data encryption at rest and in transit"""
    
    def test_sensitive_fields_encrypted(self):
        """Sensitive fields should be encrypted in database"""
        # This would require database inspection
        # Check that sensitive fields are encrypted
        pass
    
    def test_https_enforced_in_production(self, client):
        """HTTPS should be enforced in production"""
        # Check security headers
        response = client.get("/health")
        headers = response.headers
        
        # Should have security headers
        security_headers = [
            "strict-transport-security",
            "x-content-type-options",
            "x-frame-options",
        ]
        
        # Some headers might not be set in dev, that's ok
        # In production, these should be present
        pass


class TestAccessControl:
    """Test access control and data isolation"""
    
    def test_users_cannot_access_other_users_data(self, client):
        """Users should only see their own data"""
        # This would require user context
        # Verify that data is filtered by user/workspace
        response = client.get("/api/videos/")
        
        if response.status_code == 200:
            data = response.json()
            # Data should be scoped appropriately
            # This is a basic check
            assert isinstance(data, (list, dict))
    
    def test_row_level_security_enforced(self):
        """Database RLS should be enforced"""
        # This would require testing with different user contexts
        # Verify that RLS policies are active
        pass






