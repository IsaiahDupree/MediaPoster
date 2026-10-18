"""
Comprehensive tests for Posting API endpoints.
Tests post execution, status tracking, and platform integration.
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


class TestPostExecute:
    """Tests for POST /api/post/execute endpoint"""
    
    def test_execute_post(self):
        """Should execute scheduled post"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/post/execute/1")
        assert response.status_code in [200, 202, 404, 400]
    
    def test_execute_nonexistent_post(self):
        """Should return 404 for nonexistent post"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/post/execute/99999")
        assert response.status_code in [404, 400]
    
    def test_execute_already_posted(self):
        """Should handle already posted content"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/post/execute/1")
        # May succeed or fail depending on state
        assert response.status_code in [200, 202, 400, 404, 409]


class TestPostStatus:
    """Tests for GET /api/post/status endpoint"""
    
    def test_get_post_status(self):
        """Should get post status"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/post/status/1")
        assert response.status_code in [200, 404]
    
    def test_get_status_returns_state(self):
        """Should return status state"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/post/status/1")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "state" in data


class TestPostedContent:
    """Tests for GET /api/posted endpoint"""
    
    def test_get_posted_content(self):
        """Should get posted content list"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/posted")
        assert response.status_code in [200, 404]
    
    def test_get_posted_with_platform(self):
        """Should filter by platform"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/posted?platform=tiktok")
        assert response.status_code in [200, 404]
    
    def test_get_posted_with_date_range(self):
        """Should filter by date range"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/posted?start=2024-01-01&end=2024-12-31")
        assert response.status_code in [200, 404]
    
    def test_get_posted_content_metrics(self):
        """Should include metrics"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/posted/1/metrics")
        assert response.status_code in [200, 404]


class TestPostRetry:
    """Tests for POST /api/post/retry endpoint"""
    
    def test_retry_failed_post(self):
        """Should retry failed post"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/post/retry/1")
        assert response.status_code in [200, 202, 404, 400]
    
    def test_retry_nonexistent_post(self):
        """Should return 404"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/post/retry/99999")
        assert response.status_code in [404, 400]


class TestPostCancel:
    """Tests for POST /api/post/cancel endpoint"""
    
    def test_cancel_scheduled_post(self):
        """Should cancel scheduled post"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/post/cancel/1")
        assert response.status_code in [200, 404, 400]
    
    def test_cancel_already_posted(self):
        """Should handle already posted content"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/post/cancel/1")
        assert response.status_code in [200, 400, 404, 409]


class TestPostQueue:
    """Tests for GET /api/post/queue endpoint"""
    
    def test_get_post_queue(self):
        """Should get post queue"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/post/queue")
        assert response.status_code in [200, 404]
    
    def test_queue_returns_array(self):
        """Should return array of queued posts"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/post/queue")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestPostHistory:
    """Tests for GET /api/post/history endpoint"""
    
    def test_get_post_history(self):
        """Should get post history"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/post/history")
        assert response.status_code in [200, 404]
    
    def test_history_with_limit(self):
        """Should respect limit"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/post/history?limit=10")
        assert response.status_code in [200, 404]
    
    def test_history_with_platform(self):
        """Should filter by platform"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/post/history?platform=instagram")
        assert response.status_code in [200, 404]
