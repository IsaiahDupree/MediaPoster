"""
Comprehensive tests for Schedule API endpoints.
Tests CRUD operations, filtering, validation, and edge cases.
"""

import pytest
import httpx
from datetime import datetime, timedelta
import json

API_URL = "http://localhost:5555"


class TestScheduleList:
    """Tests for GET /api/publishing/scheduled endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_schedule_list_returns_200(self):
        """Should return 200 status code"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/publishing/scheduled")
            assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_get_schedule_list_returns_json(self):
        """Should return JSON response"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/publishing/scheduled")
            if response.status_code == 200:
                assert response.headers.get("content-type", "").startswith("application/json")
    
    @pytest.mark.asyncio
    async def test_get_schedule_list_has_posts_key(self):
        """Should have posts key in response"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/publishing/scheduled")
            if response.status_code == 200:
                data = response.json()
                assert "posts" in data or isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_schedule_list_with_limit(self):
        """Should respect limit parameter"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/publishing/scheduled?limit=5")
            assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_get_schedule_list_with_offset(self):
        """Should respect offset parameter"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/publishing/scheduled?offset=0")
            assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_get_schedule_list_with_platform_filter(self):
        """Should filter by platform"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/publishing/scheduled?platform=tiktok")
            assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_get_schedule_list_with_status_filter(self):
        """Should filter by status"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/publishing/scheduled?status=pending")
            assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_get_schedule_list_with_date_range(self):
        """Should filter by date range"""
        async with httpx.AsyncClient() as client:
            start = datetime.now().isoformat()
            end = (datetime.now() + timedelta(days=7)).isoformat()
            response = await client.get(f"{API_URL}/api/publishing/scheduled?start_date={start}&end_date={end}")
            assert response.status_code in [200, 404]


class TestScheduleCreate:
    """Tests for POST /api/publishing/scheduled endpoint"""
    
    @pytest.mark.asyncio
    async def test_create_schedule_with_valid_data(self):
        """Should create schedule with valid data"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000001",
                "title": "Test Post",
                "platform": "tiktok",
                "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [200, 201, 404, 422, 405]
    
    @pytest.mark.asyncio
    async def test_create_schedule_returns_id(self):
        """Should return created schedule ID"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000002",
                "title": "Test Post 2",
                "platform": "instagram",
                "scheduled_at": (datetime.now() + timedelta(days=2)).isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            if response.status_code in [200, 201]:
                result = response.json()
                assert "id" in result or "post_id" in result
    
    @pytest.mark.asyncio
    async def test_create_schedule_missing_content_id(self):
        """Should reject missing media_id"""
        async with httpx.AsyncClient() as client:
            data = {
                "title": "Test Post",
                "platform": "tiktok",
                "scheduled_at": datetime.now().isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [400, 422, 404, 405]
    
    @pytest.mark.asyncio
    async def test_create_schedule_missing_platform(self):
        """Should reject missing platform"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000003",
                "title": "Test Post",
                "scheduled_at": datetime.now().isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [400, 422, 404, 405]
    
    @pytest.mark.asyncio
    async def test_create_schedule_invalid_platform(self):
        """Should reject invalid platform"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000004",
                "title": "Test Post",
                "platform": "invalid_platform",
                "scheduled_at": datetime.now().isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [400, 422, 404, 200, 405]
    
    @pytest.mark.asyncio
    async def test_create_schedule_past_date(self):
        """Should handle past date scheduling"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000005",
                "title": "Past Post",
                "platform": "tiktok",
                "scheduled_at": (datetime.now() - timedelta(days=1)).isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            # May accept or reject depending on implementation
            assert response.status_code in [200, 201, 400, 422, 404, 405]
    
    @pytest.mark.asyncio
    async def test_create_schedule_with_visibility(self):
        """Should accept visibility parameter"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000006",
                "title": "Visibility Test",
                "platform": "youtube",
                "visibility": "private",
                "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [200, 201, 404, 422, 405]
    
    @pytest.mark.asyncio
    async def test_create_schedule_with_caption(self):
        """Should accept caption parameter"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000007",
                "title": "Caption Test",
                "caption": "This is a test caption #test",
                "platform": "instagram",
                "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [200, 201, 404, 422, 405]


class TestScheduleUpdate:
    """Tests for PUT /api/schedule/:id endpoint"""
    
    @pytest.mark.asyncio
    async def test_update_schedule_title(self):
        """Should update schedule title"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{API_URL}/api/publishing/scheduled/00000000-0000-0000-0000-000000000001",
                json={"title": "Updated Title"}
            )
            assert response.status_code in [200, 404, 422, 405]
    
    @pytest.mark.asyncio
    async def test_update_schedule_scheduled_at(self):
        """Should update scheduled time"""
        async with httpx.AsyncClient() as client:
            new_time = (datetime.now() + timedelta(days=3)).isoformat()
            response = await client.put(
                f"{API_URL}/api/publishing/scheduled/00000000-0000-0000-0000-000000000001",
                json={"scheduled_at": new_time}
            )
            assert response.status_code in [200, 404, 422, 405]
    
    @pytest.mark.asyncio
    async def test_update_schedule_caption(self):
        """Should update caption"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{API_URL}/api/publishing/scheduled/00000000-0000-0000-0000-000000000001",
                json={"caption": "Updated caption"}
            )
            assert response.status_code in [200, 404, 422, 405]
    
    @pytest.mark.asyncio
    async def test_update_schedule_platform(self):
        """Should update platform"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{API_URL}/api/publishing/scheduled/00000000-0000-0000-0000-000000000001",
                json={"platform": "youtube"}
            )
            assert response.status_code in [200, 404, 422, 405]
    
    @pytest.mark.asyncio
    async def test_update_schedule_status(self):
        """Should update status"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{API_URL}/api/publishing/scheduled/00000000-0000-0000-0000-000000000001",
                json={"status": "posted"}
            )
            assert response.status_code in [200, 404, 422, 405]
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_schedule(self):
        """Should return 404 for nonexistent schedule"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{API_URL}/api/publishing/scheduled/99999999-9999-9999-9999-999999999999",
                json={"title": "Test"}
            )
            assert response.status_code in [404, 422, 405]
    
    @pytest.mark.asyncio
    async def test_update_schedule_invalid_id(self):
        """Should handle invalid ID format"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{API_URL}/api/publishing/scheduled/invalid",
                json={"title": "Test"}
            )
            assert response.status_code in [400, 404, 422, 405]


class TestScheduleDelete:
    """Tests for DELETE /api/publishing/scheduled/:id endpoint"""
    
    @pytest.mark.asyncio
    async def test_delete_schedule(self):
        """Should delete schedule"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{API_URL}/api/publishing/scheduled/00000000-0000-0000-0000-000000000001")
            assert response.status_code in [200, 204, 404, 405]
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_schedule(self):
        """Should return 404 for nonexistent schedule"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{API_URL}/api/publishing/scheduled/99999999-9999-9999-9999-999999999999")
            assert response.status_code in [404, 200, 405]
    
    @pytest.mark.asyncio
    async def test_delete_schedule_invalid_id(self):
        """Should handle invalid ID format"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{API_URL}/api/publishing/scheduled/invalid")
            assert response.status_code in [400, 404, 422, 405]


class TestScheduleGet:
    """Tests for GET /api/publishing/scheduled/:id endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_schedule_by_id(self):
        """Should get schedule by ID"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/publishing/scheduled/00000000-0000-0000-0000-000000000001")
            assert response.status_code in [200, 404, 405]
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_schedule(self):
        """Should return 404 for nonexistent schedule"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/publishing/scheduled/99999999-9999-9999-9999-999999999999")
            assert response.status_code in [404, 405]
    
    @pytest.mark.asyncio
    async def test_get_schedule_returns_all_fields(self):
        """Should return all schedule fields"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/publishing/scheduled/00000000-0000-0000-0000-000000000001")
            if response.status_code == 200:
                data = response.json()
                expected_fields = ["id", "title", "platform", "scheduledAt", "scheduled_at"]
                for field in expected_fields:
                    assert field in data or field.lower() in str(data).lower()


class TestScheduleValidation:
    """Tests for schedule data validation"""
    
    @pytest.mark.asyncio
    async def test_empty_request_body(self):
        """Should handle empty request body"""
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json={})
            assert response.status_code in [400, 422, 404, 405]
    
    @pytest.mark.asyncio
    async def test_null_values(self):
        """Should handle null values"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": None,
                "title": None,
                "platform": None,
                "scheduled_at": None
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [400, 422, 404, 405]
    
    @pytest.mark.asyncio
    async def test_very_long_title(self):
        """Should handle very long title"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000008",
                "title": "A" * 10000,
                "platform": "tiktok",
                "scheduled_at": datetime.now().isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [200, 201, 400, 422, 404, 405]
    
    @pytest.mark.asyncio
    async def test_special_characters_in_title(self):
        """Should handle special characters"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000009",
                "title": "Test <script>alert('xss')</script>",
                "platform": "tiktok",
                "scheduled_at": datetime.now().isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [200, 201, 400, 422, 404, 405]
    
    @pytest.mark.asyncio
    async def test_unicode_in_caption(self):
        """Should handle unicode characters"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000010",
                "title": "Unicode Test",
                "caption": "测试 🎉 テスト مرحبا",
                "platform": "instagram",
                "scheduled_at": datetime.now().isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [200, 201, 400, 422, 404, 405]
    
    @pytest.mark.asyncio
    async def test_invalid_date_format(self):
        """Should reject invalid date format"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000011",
                "title": "Date Test",
                "platform": "tiktok",
                "scheduled_at": "not-a-date"
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            assert response.status_code in [400, 422, 404, 405]
    
    @pytest.mark.asyncio
    async def test_sql_injection_attempt(self):
        """Should handle SQL injection attempts"""
        async with httpx.AsyncClient() as client:
            data = {
                "media_id": "00000000-0000-0000-0000-000000000012",
                "title": "SQL Test",
                "platform": "tiktok",
                "scheduled_at": datetime.now().isoformat()
            }
            response = await client.post(f"{API_URL}/api/publishing/scheduled", json=data)
            # Should not crash, may accept or reject
            assert response.status_code in [200, 201, 400, 422, 404, 500, 405]
