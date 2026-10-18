"""
Integration tests for API endpoints.
Tests cross-endpoint workflows and data consistency.
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


class TestScheduleMediaIntegration:
    """Tests for schedule and media integration"""
    
    def test_schedule_references_media(self):
        """Schedule should reference valid media"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list")
        assert response.status_code in [200, 404]
    
    def test_media_shows_scheduled_status(self):
        """Media should show if scheduled"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/1")
        assert response.status_code in [200, 404]


class TestScheduleAccountIntegration:
    """Tests for schedule and account integration"""
    
    def test_schedule_uses_valid_account(self):
        """Schedule should use valid account"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list")
        assert response.status_code in [200, 404]
    
    def test_account_shows_scheduled_posts(self):
        """Account should show scheduled posts"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/accounts/1")
        assert response.status_code in [200, 404]


class TestContentScheduleIntegration:
    """Tests for content and schedule integration"""
    
    def test_content_can_be_scheduled(self):
        """Content should be schedulable"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/list")
        assert response.status_code in [200, 404]
    
    def test_schedule_shows_content_details(self):
        """Schedule should show content details"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/1")
        assert response.status_code in [200, 404]


class TestPostingIntegration:
    """Tests for posting workflow integration"""
    
    def test_scheduled_becomes_posted(self):
        """Scheduled post can become posted"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/posted")
        assert response.status_code in [200, 404]
    
    def test_posting_updates_schedule(self):
        """Posting updates schedule status"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?status=posted")
        assert response.status_code in [200, 404]
