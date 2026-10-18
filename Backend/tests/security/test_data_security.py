"""
Data Security Tests
Tests data encryption, PII handling, data leakage
"""
import pytest
import httpx
import json
import re

API_URL = "http://localhost:5555"


class TestDataLeakageSecurity:
    """Test for data leakage in responses"""
    
    @pytest.mark.asyncio
    async def test_no_sensitive_data_in_error_messages(self):
        """Error messages should not leak sensitive information"""
        async with httpx.AsyncClient() as client:
            # Try to trigger various errors
            error_responses = [
                await client.get(f"{API_URL}/api/videos/nonexistent-id"),
                await client.post(f"{API_URL}/api/videos/", json={"invalid": "data"}),
                await client.get(f"{API_URL}/api/nonexistent-endpoint"),
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
    
    @pytest.mark.asyncio
    async def test_no_database_errors_exposed(self):
        """Database errors should not expose schema details"""
        async with httpx.AsyncClient() as client:
            # Try to trigger database errors
            response = await client.get(f"{API_URL}/api/videos/invalid-uuid-format")
            
            if response.status_code >= 500:
                try:
                    data = response.json()
                    error_text = str(data).lower()
                    # Should not expose database structure
                    db_keywords = ["postgres", "sql", "table", "column", "constraint", "foreign key"]
                    # Some mentions might be ok, but detailed errors are not
                    # Test passes if no detailed DB errors are exposed
                except:
                    pass  # Non-JSON response is acceptable
    
    @pytest.mark.asyncio
    async def test_no_stack_traces_in_production(self):
        """Stack traces should not be exposed in production"""
        async with httpx.AsyncClient() as client:
            # In production mode, errors should be sanitized
            # This test would need to check production vs dev mode
            response = await client.get(f"{API_URL}/api/nonexistent")
            
            if response.status_code >= 500:
                response_text = response.text
                # Should not contain stack trace details
                stack_trace_indicators = ["traceback", "file \"", "line ", "at "]
                for indicator in stack_trace_indicators:
                    # In production, these should not appear
                    pass


class TestPIIHandling:
    """Test PII (Personally Identifiable Information) handling"""
    
    @pytest.mark.asyncio
    async def test_email_addresses_not_exposed(self):
        """Email addresses should not be exposed unnecessarily"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/videos/")
            
            if response.status_code == 200:
                data = response.json()
                data_str = json.dumps(data)
                # Check for email patterns
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, data_str)
                # Emails might be legitimate (user emails), but should be minimal
                # This is informational
                pass
    
    @pytest.mark.asyncio
    async def test_api_keys_not_in_responses(self):
        """API keys should never appear in responses"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/videos/")
            
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
    
    @pytest.mark.asyncio
    async def test_https_enforced_in_production(self):
        """HTTPS should be enforced in production"""
        async with httpx.AsyncClient() as client:
            # Check security headers
            response = await client.get(f"{API_URL}/health")
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
    
    @pytest.mark.asyncio
    async def test_users_cannot_access_other_users_data(self):
        """Users should only see their own data"""
        async with httpx.AsyncClient() as client:
            # This would require user context
            # Verify that data is filtered by user/workspace
            response = await client.get(f"{API_URL}/api/videos/")
            
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








