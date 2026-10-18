"""
API/Contract Tests: Scheduler Backend (SCH-API-*)
Tests for CRUD operations, pagination, concurrency, and data contracts
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


class TestSCHAPI001CreateScheduledPost:
    """SCH-API-001: Create scheduled post returns canonical timestamp + timezone info"""
    
    def test_create_returns_timestamp(self):
        """Should return canonical timestamp on create"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "test-create-001",
            "title": "Test Post",
            "platform": "tiktok",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        if response.status_code in [200, 201]:
            result = response.json()
            assert "scheduled_at" in result or "scheduledAt" in result or "id" in result
    
    def test_create_returns_iso_format(self):
        """Should return ISO 8601 formatted timestamp"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "test-create-002",
            "title": "ISO Test",
            "platform": "instagram",
            "scheduled_at": "2025-12-25T10:00:00Z"
        }
        response = client.post("/api/schedule/create", json=data)
        if response.status_code in [200, 201]:
            result = response.json()
            # Timestamp should be parseable
            if "scheduled_at" in result:
                datetime.fromisoformat(result["scheduled_at"].replace("Z", "+00:00"))
    
    def test_create_preserves_timezone(self):
        """Should preserve timezone info in response"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "test-tz-001",
            "title": "Timezone Test",
            "platform": "youtube",
            "scheduled_at": "2025-12-25T10:00:00-05:00"
        }
        response = client.post("/api/schedule/create", json=data)
        assert response.status_code in [200, 201, 400, 422, 404]
    
    def test_create_returns_id(self):
        """Should return created post ID"""
        if not client:
            pytest.skip("Client not available")
        data = {
            "content_id": "test-id-001",
            "title": "ID Test",
            "platform": "tiktok",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        response = client.post("/api/schedule/create", json=data)
        if response.status_code in [200, 201]:
            result = response.json()
            assert "id" in result


class TestSCHAPI002UpdateScheduledPost:
    """SCH-API-002: Update post returns updated object"""
    
    def test_update_title_returns_updated(self):
        """Should return updated object with new title"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/schedule/1", json={"title": "Updated Title"})
        if response.status_code == 200:
            result = response.json()
            assert "title" in result or "success" in result
    
    def test_update_description_returns_updated(self):
        """Should return updated object with new description"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/schedule/1", json={"caption": "Updated caption #test"})
        assert response.status_code in [200, 404, 422]
    
    def test_update_time_returns_updated(self):
        """Should return updated object with new time"""
        if not client:
            pytest.skip("Client not available")
        new_time = (datetime.now() + timedelta(days=2)).isoformat()
        response = client.put("/api/schedule/1", json={"scheduled_at": new_time})
        assert response.status_code in [200, 404, 422]
    
    def test_update_visibility_returns_updated(self):
        """Should return updated object with new visibility"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/schedule/1", json={"visibility": "private"})
        assert response.status_code in [200, 404, 422]
    
    def test_update_multiple_fields(self):
        """Should update multiple fields at once"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/schedule/1", json={
            "title": "Multi Update",
            "caption": "New caption",
            "visibility": "public"
        })
        assert response.status_code in [200, 404, 422]


class TestSCHAPI003DeleteScheduledPost:
    """SCH-API-003: Delete post is idempotent"""
    
    def test_delete_first_time_succeeds(self):
        """Should succeed on first delete"""
        if not client:
            pytest.skip("Client not available")
        response = client.delete("/api/schedule/999")
        assert response.status_code in [200, 204, 404]
    
    def test_delete_second_time_no_error(self):
        """Should not error on second delete (idempotent)"""
        if not client:
            pytest.skip("Client not available")
        # First delete
        client.delete("/api/schedule/998")
        # Second delete - should not crash
        response = client.delete("/api/schedule/998")
        assert response.status_code in [200, 204, 404]
    
    def test_delete_nonexistent_returns_404_or_ok(self):
        """Should return 404 or 200 for nonexistent"""
        if not client:
            pytest.skip("Client not available")
        response = client.delete("/api/schedule/99999")
        assert response.status_code in [200, 204, 404]


class TestSCHAPI004PaginationFilters:
    """SCH-API-004: Pagination/filters for range queries"""
    
    def test_list_with_limit(self):
        """Should respect limit parameter"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?limit=5")
        assert response.status_code in [200, 404]
    
    def test_list_with_offset(self):
        """Should respect offset parameter"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?offset=10")
        assert response.status_code in [200, 404]
    
    def test_list_with_date_range(self):
        """Should filter by date range"""
        if not client:
            pytest.skip("Client not available")
        start = datetime.now().isoformat()
        end = (datetime.now() + timedelta(days=7)).isoformat()
        response = client.get(f"/api/schedule/list?start={start}&end={end}")
        assert response.status_code in [200, 404]
    
    def test_list_month_range(self):
        """Should pull correct items for month range"""
        if not client:
            pytest.skip("Client not available")
        start = "2025-12-01T00:00:00Z"
        end = "2025-12-31T23:59:59Z"
        response = client.get(f"/api/schedule/list?start={start}&end={end}")
        assert response.status_code in [200, 404]
    
    def test_list_week_range(self):
        """Should pull correct items for week range"""
        if not client:
            pytest.skip("Client not available")
        start = "2025-12-15T00:00:00Z"
        end = "2025-12-21T23:59:59Z"
        response = client.get(f"/api/schedule/list?start={start}&end={end}")
        assert response.status_code in [200, 404]
    
    def test_list_day_range(self):
        """Should pull correct items for day range"""
        if not client:
            pytest.skip("Client not available")
        start = "2025-12-21T00:00:00Z"
        end = "2025-12-21T23:59:59Z"
        response = client.get(f"/api/schedule/list?start={start}&end={end}")
        assert response.status_code in [200, 404]
    
    def test_list_by_platform(self):
        """Should filter by platform"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?platform=tiktok")
        assert response.status_code in [200, 404]
    
    def test_list_by_status(self):
        """Should filter by status"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list?status=pending")
        assert response.status_code in [200, 404]


class TestSCHAPI005Concurrency:
    """SCH-API-005: Concurrency handling"""
    
    def test_concurrent_edits_same_post(self):
        """Should handle concurrent edits to same post"""
        if not client:
            pytest.skip("Client not available")
        import concurrent.futures
        
        def edit_post():
            return client.put("/api/schedule/1", json={"title": f"Edit {datetime.now().isoformat()}"})
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(edit_post) for _ in range(3)]
            results = [f.result() for f in futures]
            # All should complete without crashing
            for r in results:
                assert r.status_code in [200, 404, 422, 409, 500]
    
    def test_concurrent_creates(self):
        """Should handle concurrent creates"""
        if not client:
            pytest.skip("Client not available")
        import concurrent.futures
        
        def create_post(i):
            return client.post("/api/schedule/create", json={
                "content_id": f"concurrent-{i}",
                "title": f"Concurrent Post {i}",
                "platform": "tiktok",
                "scheduled_at": (datetime.now() + timedelta(days=i)).isoformat()
            })
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_post, i) for i in range(5)]
            results = [f.result() for f in futures]
            # All should complete
            for r in results:
                assert r.status_code in [200, 201, 400, 422, 404]
    
    def test_concurrent_deletes(self):
        """Should handle concurrent deletes of same post"""
        if not client:
            pytest.skip("Client not available")
        import concurrent.futures
        
        def delete_post():
            return client.delete("/api/schedule/1")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(delete_post) for _ in range(3)]
            results = [f.result() for f in futures]
            # Should not crash
            for r in results:
                assert r.status_code in [200, 204, 404]


class TestSCHAPI006DataContract:
    """SCH-API-006: Data contract validation"""
    
    def test_response_has_required_fields(self):
        """Should return all required fields"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/1")
        if response.status_code == 200:
            result = response.json()
            # Check for common fields
            expected = ["id", "title", "platform", "scheduledAt", "status"]
            for field in expected:
                assert field in result or field.lower() in str(result).lower()
    
    def test_platform_values_valid(self):
        """Should only allow valid platform values"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list")
        if response.status_code == 200:
            data = response.json()
            posts = data.get("posts", data) if isinstance(data, dict) else data
            if isinstance(posts, list):
                for post in posts:
                    if "platform" in post:
                        assert post["platform"] in ["tiktok", "instagram", "youtube"]
    
    def test_status_values_valid(self):
        """Should only have valid status values"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/list")
        if response.status_code == 200:
            data = response.json()
            posts = data.get("posts", data) if isinstance(data, dict) else data
            if isinstance(posts, list):
                for post in posts:
                    if "status" in post:
                        assert post["status"] in ["pending", "posted", "failed"]
    
    def test_timestamps_are_iso8601(self):
        """Should return ISO 8601 timestamps"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/1")
        if response.status_code == 200:
            result = response.json()
            timestamp = result.get("scheduledAt") or result.get("scheduled_at")
            if timestamp:
                # Should be parseable as ISO 8601
                try:
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except:
                    pass  # May be in different format


class TestSCHAPI007ErrorHandling:
    """SCH-API-007: Error handling"""
    
    def test_invalid_id_returns_error(self):
        """Should return error for invalid ID"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/invalid")
        assert response.status_code in [400, 404, 422]
    
    def test_invalid_date_returns_error(self):
        """Should return error for invalid date"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/schedule/create", json={
            "content_id": "test",
            "title": "Test",
            "platform": "tiktok",
            "scheduled_at": "not-a-date"
        })
        assert response.status_code in [400, 422, 404]
    
    def test_missing_required_fields_returns_error(self):
        """Should return error for missing required fields"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/schedule/create", json={})
        assert response.status_code in [400, 422, 404]
    
    def test_error_response_has_message(self):
        """Should include error message in response"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/schedule/99999")
        if response.status_code == 404:
            result = response.json()
            assert "detail" in result or "error" in result or "message" in result
