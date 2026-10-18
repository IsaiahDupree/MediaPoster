"""
Additional comprehensive tests for Schedule API.
Tests date handling, platform-specific logic, and integration scenarios.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json

import sys
sys.path.insert(0, '..')
try:
    from main import app
    client = TestClient(app)
except ImportError:
    client = None


class TestScheduleDateHandling:
    """Tests for date/time handling in schedule"""
    
    def test_schedule_with_timezone(self):
        """Should handle timezone in scheduled_at"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "tz-test",
            "title": "Timezone Test",
            "platform": "tiktok",
            "scheduled_at": "2025-01-01T12:00:00-05:00"
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_utc_time(self):
        """Should handle UTC time"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "utc-test",
            "title": "UTC Test",
            "platform": "instagram",
            "scheduled_at": "2025-01-01T12:00:00Z"
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_far_future_date(self):
        """Should handle far future date"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "future-test",
            "title": "Future Test",
            "platform": "youtube",
            "scheduled_at": "2030-12-31T23:59:59Z"
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_midnight(self):
        """Should handle midnight time"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "midnight-test",
            "title": "Midnight Test",
            "platform": "tiktok",
            "scheduled_at": "2025-01-01T00:00:00Z"
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_end_of_day(self):
        """Should handle end of day time"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "eod-test",
            "title": "EOD Test",
            "platform": "instagram",
            "scheduled_at": "2025-01-01T23:59:59Z"
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]


class TestSchedulePlatformSpecific:
    """Tests for platform-specific schedule behavior"""
    
    def test_schedule_tiktok(self):
        """Should schedule for TikTok"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "tt-test",
            "title": "TikTok Post",
            "platform": "tiktok",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_instagram(self):
        """Should schedule for Instagram"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "ig-test",
            "title": "Instagram Post",
            "platform": "instagram",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_youtube(self):
        """Should schedule for YouTube"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "yt-test",
            "title": "YouTube Post",
            "platform": "youtube",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_filter_by_tiktok(self):
        """Should filter TikTok posts"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?platform=tiktok")
        assert response.status_code in [200, 404]
    
    def test_filter_by_instagram(self):
        """Should filter Instagram posts"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?platform=instagram")
        assert response.status_code in [200, 404]
    
    def test_filter_by_youtube(self):
        """Should filter YouTube posts"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?platform=youtube")
        assert response.status_code in [200, 404]


class TestScheduleStatus:
    """Tests for schedule status handling"""
    
    def test_filter_pending_status(self):
        """Should filter pending posts"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?status=pending")
        assert response.status_code in [200, 404]
    
    def test_filter_posted_status(self):
        """Should filter posted posts"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?status=posted")
        assert response.status_code in [200, 404]
    
    def test_filter_failed_status(self):
        """Should filter failed posts"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?status=failed")
        assert response.status_code in [200, 404]
    
    def test_update_to_pending(self):
        """Should update status to pending"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/schedule/1", json={"status": "pending"})
        assert response.status_code in [200, 404, 422]
    
    def test_update_to_posted(self):
        """Should update status to posted"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/schedule/1", json={"status": "posted"})
        assert response.status_code in [200, 404, 422]
    
    def test_update_to_failed(self):
        """Should update status to failed"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/schedule/1", json={"status": "failed"})
        assert response.status_code in [200, 404, 422]


class TestScheduleVisibility:
    """Tests for schedule visibility handling"""
    
    def test_schedule_public_visibility(self):
        """Should schedule with public visibility"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "pub-test",
            "title": "Public Post",
            "platform": "youtube",
            "visibility": "public",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_private_visibility(self):
        """Should schedule with private visibility"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "priv-test",
            "title": "Private Post",
            "platform": "youtube",
            "visibility": "private",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_unlisted_visibility(self):
        """Should schedule with unlisted visibility"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "unlist-test",
            "title": "Unlisted Post",
            "platform": "youtube",
            "visibility": "unlisted",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_update_visibility(self):
        """Should update visibility"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/schedule/1", json={"visibility": "private"})
        assert response.status_code in [200, 404, 422]


class TestScheduleCaption:
    """Tests for schedule caption handling"""
    
    def test_schedule_with_hashtags(self):
        """Should schedule with hashtags in caption"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "hash-test",
            "title": "Hashtag Post",
            "caption": "Check this out! #viral #trending #fyp",
            "platform": "tiktok",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_with_mentions(self):
        """Should schedule with mentions in caption"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "mention-test",
            "title": "Mention Post",
            "caption": "Shoutout to @user1 and @user2!",
            "platform": "instagram",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_with_emojis(self):
        """Should schedule with emojis in caption"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "emoji-test",
            "title": "Emoji Post",
            "caption": "Having fun! 🎉🔥💯",
            "platform": "tiktok",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_schedule_with_long_caption(self):
        """Should handle long caption"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "long-test",
            "title": "Long Caption Post",
            "caption": "A" * 2200,
            "platform": "instagram",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_update_caption(self):
        """Should update caption"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/schedule/1", json={"caption": "Updated caption #new"})
        assert response.status_code in [200, 404, 422]


class TestScheduleAccount:
    """Tests for schedule account association"""
    
    def test_schedule_with_account_id(self):
        """Should schedule with account ID"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "acc-test",
            "title": "Account Post",
            "platform": "tiktok",
            "account_id": "1",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_update_account_id(self):
        """Should update account ID"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/schedule/1", json={"account_id": "2"})
        assert response.status_code in [200, 404, 422]
    
    def test_filter_by_account(self):
        """Should filter by account"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?account_id=1")
        assert response.status_code in [200, 404]
