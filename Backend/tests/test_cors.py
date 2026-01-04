"""
CORS Configuration Tests
========================
Tests to verify CORS is properly configured for frontend access.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app


class TestCORSConfiguration:
    """Test CORS middleware configuration."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_cors_allows_localhost_5557(self, client):
        """Frontend dev server should be allowed."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5557",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code in [200, 204]
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5557"
    
    def test_cors_allows_localhost_3000(self, client):
        """Alternative frontend port should be allowed."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code in [200, 204]
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    
    def test_cors_allows_127_0_0_1_5557(self, client):
        """127.0.0.1 variant should be allowed."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://127.0.0.1:5557",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code in [200, 204]
        assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5557"
    
    def test_cors_allows_production_domain(self, client):
        """Production domain should be allowed."""
        response = client.options(
            "/health",
            headers={
                "Origin": "https://mediaposter.vercel.app",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code in [200, 204]
        assert response.headers.get("access-control-allow-origin") == "https://mediaposter.vercel.app"
    
    def test_cors_blocks_unknown_origin(self, client):
        """Unknown origins should not get CORS headers."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://malicious-site.com",
                "Access-Control-Request-Method": "GET",
            }
        )
        # FastAPI CORS middleware doesn't add header for disallowed origins
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin is None or allow_origin != "http://malicious-site.com"
    
    def test_cors_allows_all_methods(self, client):
        """All HTTP methods should be allowed."""
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]:
            response = client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:5557",
                    "Access-Control-Request-Method": method,
                }
            )
            assert response.status_code in [200, 204]
            allowed_methods = response.headers.get("access-control-allow-methods", "")
            # With allow_methods=["*"], it echoes back the requested method
            assert method in allowed_methods or "*" in allowed_methods
    
    def test_cors_allows_credentials(self, client):
        """Credentials should be allowed for cookie-based auth."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5557",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.headers.get("access-control-allow-credentials") == "true"
    
    def test_cors_allows_common_headers(self, client):
        """Common headers like Content-Type and Authorization should be allowed."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5557",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization, X-Requested-With",
            }
        )
        assert response.status_code in [200, 204]
        allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
        # With allow_headers=["*"], it should allow any header
        assert "content-type" in allowed_headers or "*" in allowed_headers
    
    def test_cors_on_actual_get_request(self, client):
        """Actual GET request should include CORS headers."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5557"}
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5557"
    
    def test_cors_on_api_endpoint(self, client):
        """API endpoints should have CORS headers."""
        response = client.options(
            "/api/schedule/list",
            headers={
                "Origin": "http://localhost:5557",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code in [200, 204]
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5557"


class TestCORSAudit:
    """Audit CORS configuration for security issues."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_no_wildcard_origin(self, client):
        """CORS should NOT use wildcard origin in production."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5557",
                "Access-Control-Request-Method": "GET",
            }
        )
        # Should be specific origin, not wildcard
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin != "*", "Wildcard origin is insecure when credentials are allowed"
    
    def test_credentials_with_specific_origin(self, client):
        """When credentials are allowed, origin must be specific."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5557",
                "Access-Control-Request-Method": "GET",
            }
        )
        allow_credentials = response.headers.get("access-control-allow-credentials")
        allow_origin = response.headers.get("access-control-allow-origin")
        
        if allow_credentials == "true":
            # Origin must be specific, not wildcard
            assert allow_origin != "*", "Cannot use wildcard origin with credentials"
            assert allow_origin is not None, "Origin must be set when credentials allowed"


# Run directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
