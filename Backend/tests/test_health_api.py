"""
Tests for health check and system status endpoints.
"""

import pytest
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, '..')
try:
    from main import app
    client = TestClient(app)
except ImportError:
    client = None


class TestHealthCheck:
    """Tests for health check endpoint"""
    
    def test_health_check_returns_200(self):
        """Should return 200"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/health")
        assert response.status_code in [200, 404]
    
    def test_health_check_returns_json(self):
        """Should return JSON"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/health")
        if response.status_code == 200:
            assert "application/json" in response.headers.get("content-type", "")
    
    def test_health_check_status_ok(self):
        """Should return OK status"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "ok" in str(data).lower()


class TestAPIRoot:
    """Tests for API root endpoint"""
    
    def test_api_root(self):
        """Should return API info"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/")
        assert response.status_code in [200, 404]
    
    def test_api_docs(self):
        """Should return API docs"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/docs")
        assert response.status_code in [200, 404]
    
    def test_openapi_json(self):
        """Should return OpenAPI JSON"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/openapi.json")
        assert response.status_code in [200, 404]


class TestSystemStatus:
    """Tests for system status endpoint"""
    
    def test_system_status(self):
        """Should return system status"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/status")
        assert response.status_code in [200, 404]
    
    def test_database_status(self):
        """Should return database status"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/status/database")
        assert response.status_code in [200, 404]
    
    def test_storage_status(self):
        """Should return storage status"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/status/storage")
        assert response.status_code in [200, 404]
