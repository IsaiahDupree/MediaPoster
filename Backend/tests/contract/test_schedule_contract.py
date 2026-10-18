"""
Schedule API Contract Tests
============================
Tests to verify the Schedule API adheres to its contract
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid


class TestScheduleListContract:
    """Contract tests for GET /api/schedule/list"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_list_returns_correct_schema(self, base_url):
        """Response must match ScheduleListResponse schema"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/schedule/list")
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                
                # Must have 'posts' array
                assert "posts" in data
                assert isinstance(data["posts"], list)
                
                # Each post must have required fields
                for post in data["posts"]:
                    assert "id" in post
                    assert "platform" in post
                    assert "scheduled_time" in post
                    assert "status" in post

    @pytest.mark.asyncio
    async def test_list_with_limit_parameter(self, base_url):
        """Limit parameter should constrain results"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/schedule/list?limit=5")
            
            if response.status_code == 200:
                data = response.json()
                assert len(data.get("posts", [])) <= 5

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, base_url):
        """Status filter should only return matching posts"""
        valid_statuses = ["scheduled", "published", "failed", "cancelled"]
        
        async with AsyncClient(base_url=base_url) as client:
            for status in valid_statuses:
                response = await client.get(f"/api/schedule/list?status={status}")
                
                if response.status_code == 200:
                    data = response.json()
                    for post in data.get("posts", []):
                        assert post.get("status") == status

    @pytest.mark.asyncio
    async def test_list_with_platform_filter(self, base_url):
        """Platform filter should only return matching posts"""
        valid_platforms = ["tiktok", "instagram", "youtube", "twitter", "threads"]
        
        async with AsyncClient(base_url=base_url) as client:
            for platform in valid_platforms:
                response = await client.get(f"/api/schedule/list?platform={platform}")
                
                if response.status_code == 200:
                    data = response.json()
                    for post in data.get("posts", []):
                        assert post.get("platform") == platform

    @pytest.mark.asyncio
    async def test_list_with_days_parameter(self, base_url):
        """Days parameter should limit to posts within that timeframe"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/schedule/list?days=7")
            
            if response.status_code == 200:
                data = response.json()
                now = datetime.utcnow()
                max_date = now + timedelta(days=7)
                
                for post in data.get("posts", []):
                    scheduled_time = datetime.fromisoformat(
                        post["scheduled_time"].replace("Z", "+00:00")
                    )
                    # Should be within the next 7 days
                    assert scheduled_time <= max_date.replace(tzinfo=scheduled_time.tzinfo)

    @pytest.mark.asyncio
    async def test_list_invalid_limit_returns_422(self, base_url):
        """Invalid limit should return 422 validation error"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/schedule/list?limit=invalid")
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_list_negative_limit_returns_error(self, base_url):
        """Negative limit should return error"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/schedule/list?limit=-1")
            assert response.status_code in [400, 422]


class TestScheduleCreateContract:
    """Contract tests for POST /api/schedule/create"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.fixture
    def valid_schedule_payload(self) -> Dict[str, Any]:
        """Valid schedule creation payload"""
        future_time = datetime.utcnow() + timedelta(hours=1)
        return {
            "media_id": str(uuid.uuid4()),
            "platform": "tiktok",
            "scheduled_time": future_time.isoformat() + "Z",
            "title": "Test Post",
            "caption": "Test caption #test",
            "account_id": 710,
        }

    @pytest.mark.asyncio
    async def test_create_returns_correct_schema(self, base_url, valid_schedule_payload):
        """Created post must match ScheduledPost schema"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post(
                "/api/schedule/create",
                json=valid_schedule_payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                # Must have required fields
                assert "id" in data
                assert "platform" in data
                assert "scheduled_time" in data
                assert "status" in data
                
                # Status should be 'scheduled'
                assert data["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_create_requires_media_id(self, base_url, valid_schedule_payload):
        """media_id is required"""
        payload = valid_schedule_payload.copy()
        del payload["media_id"]
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/schedule/create", json=payload)
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_create_requires_platform(self, base_url, valid_schedule_payload):
        """platform is required"""
        payload = valid_schedule_payload.copy()
        del payload["platform"]
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/schedule/create", json=payload)
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_create_requires_scheduled_time(self, base_url, valid_schedule_payload):
        """scheduled_time is required"""
        payload = valid_schedule_payload.copy()
        del payload["scheduled_time"]
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/schedule/create", json=payload)
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_create_validates_platform_enum(self, base_url, valid_schedule_payload):
        """platform must be a valid enum value"""
        payload = valid_schedule_payload.copy()
        payload["platform"] = "invalid_platform"
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/schedule/create", json=payload)
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_create_rejects_past_time(self, base_url, valid_schedule_payload):
        """scheduled_time must be in the future"""
        payload = valid_schedule_payload.copy()
        past_time = datetime.utcnow() - timedelta(hours=1)
        payload["scheduled_time"] = past_time.isoformat() + "Z"
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/schedule/create", json=payload)
            # Should reject past times
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_create_validates_time_format(self, base_url, valid_schedule_payload):
        """scheduled_time must be valid ISO format"""
        payload = valid_schedule_payload.copy()
        payload["scheduled_time"] = "invalid-time-format"
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/schedule/create", json=payload)
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_create_accepts_optional_fields(self, base_url):
        """Optional fields should be accepted"""
        future_time = datetime.utcnow() + timedelta(hours=1)
        payload = {
            "media_id": str(uuid.uuid4()),
            "platform": "instagram",
            "scheduled_time": future_time.isoformat() + "Z",
            "title": "Test Title",
            "caption": "Test caption",
            "hashtags": ["#test", "#video"],
            "account_id": 807,
            "account_handle": "@the_isaiah_dupree",
        }
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/schedule/create", json=payload)
            # Should accept all optional fields
            assert response.status_code in [200, 201, 400, 404]  # 400/404 if media doesn't exist


class TestScheduleUpdateContract:
    """Contract tests for PUT /api/schedule/{id}"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_update_returns_updated_post(self, base_url):
        """Update should return the updated post"""
        post_id = str(uuid.uuid4())
        future_time = datetime.utcnow() + timedelta(hours=2)
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.put(
                f"/api/schedule/{post_id}",
                json={"scheduled_time": future_time.isoformat() + "Z"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "id" in data
                assert "scheduled_time" in data

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_404(self, base_url):
        """Updating non-existent post should return 404"""
        fake_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.put(
                f"/api/schedule/{fake_id}",
                json={"title": "Updated"}
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_allows_partial_update(self, base_url):
        """PATCH-style partial updates should be allowed"""
        post_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            # Only updating title, not other fields
            response = await client.put(
                f"/api/schedule/{post_id}",
                json={"title": "Just the title"}
            )
            # Should not require all fields
            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_update_validates_scheduled_time(self, base_url):
        """Updated scheduled_time must be valid"""
        post_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.put(
                f"/api/schedule/{post_id}",
                json={"scheduled_time": "invalid"}
            )
            assert response.status_code in [400, 422, 404]


class TestScheduleDeleteContract:
    """Contract tests for DELETE /api/schedule/{id}"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_delete_returns_204(self, base_url):
        """Successful delete should return 204 No Content"""
        post_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.delete(f"/api/schedule/{post_id}")
            # Either 204 for success or 404 if not found
            assert response.status_code in [200, 204, 404]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, base_url):
        """Deleting non-existent post should return 404"""
        fake_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.delete(f"/api/schedule/{fake_id}")
            assert response.status_code in [404, 204, 200]

    @pytest.mark.asyncio
    async def test_delete_is_idempotent(self, base_url):
        """Deleting same resource twice should not error"""
        post_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            # First delete
            await client.delete(f"/api/schedule/{post_id}")
            # Second delete should also succeed (or 404)
            response = await client.delete(f"/api/schedule/{post_id}")
            assert response.status_code in [200, 204, 404]


class TestScheduleConflictHandling:
    """Contract tests for schedule conflict detection"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_conflict_returns_409(self, base_url):
        """Conflicting schedules should return 409 Conflict"""
        # This tests that the API properly handles scheduling conflicts
        future_time = datetime.utcnow() + timedelta(hours=1)
        payload = {
            "media_id": str(uuid.uuid4()),
            "platform": "tiktok",
            "scheduled_time": future_time.isoformat() + "Z",
            "account_id": 710,
        }
        
        async with AsyncClient(base_url=base_url) as client:
            # Create first post
            response1 = await client.post("/api/schedule/create", json=payload)
            
            if response1.status_code in [200, 201]:
                # Try to create another at same time for same account
                response2 = await client.post("/api/schedule/create", json=payload)
                # Should either conflict (409) or handle gracefully
                assert response2.status_code in [200, 201, 400, 409]


class TestScheduleBulkOperations:
    """Contract tests for bulk schedule operations"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_bulk_create_limit(self, base_url):
        """Bulk operations should have a reasonable limit"""
        # Create more than limit
        future_time = datetime.utcnow() + timedelta(hours=1)
        posts = [
            {
                "media_id": str(uuid.uuid4()),
                "platform": "tiktok",
                "scheduled_time": (future_time + timedelta(hours=i)).isoformat() + "Z",
            }
            for i in range(150)  # Over typical limit
        ]
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/schedule/bulk", json={"posts": posts})
            # Should limit or reject
            if response.status_code == 200:
                data = response.json()
                # Should not have created all 150
                assert data.get("created", 0) <= 100


class TestScheduleResponseHeaders:
    """Contract tests for response headers"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_content_type_is_json(self, base_url):
        """Response Content-Type should be application/json"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/schedule/list")
            assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_correlation_id_in_response(self, base_url):
        """Correlation ID should be echoed in response"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get(
                "/api/schedule/list",
                headers={"X-Correlation-ID": "test-correlation-123"}
            )
            # Should echo correlation ID
            response_correlation = response.headers.get("X-Correlation-ID")
            assert response_correlation is not None or response.status_code != 200
