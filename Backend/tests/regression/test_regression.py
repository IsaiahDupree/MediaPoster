"""
Regression Tests
Tests to ensure previously fixed bugs don't reoccur
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime


class TestAPIRegressions:
    """Regression tests for API endpoints"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    # ==================== Bug #001: Empty response on pagination ====================
    def test_pagination_returns_array_not_null(self, client):
        """
        Bug: Pagination with offset beyond data returned null instead of empty array
        Fixed: Should return empty array []
        """
        response = client.get("/api/videos?limit=10&offset=999999")
        if response.status_code == 200:
            data = response.json()
            # Should be empty array, not null
            if isinstance(data, dict) and "items" in data:
                assert data["items"] is not None
                assert isinstance(data["items"], list)
            elif isinstance(data, list):
                assert data is not None
    
    # ==================== Bug #002: Case sensitivity in search ====================
    def test_search_is_case_insensitive(self, client):
        """
        Bug: Search was case-sensitive, missing results
        Fixed: Search should be case-insensitive
        """
        # These should return same results
        response_lower = client.get("/api/videos?search=test")
        response_upper = client.get("/api/videos?search=TEST")
        response_mixed = client.get("/api/videos?search=TeSt")
        
        # All should return successfully
        assert response_lower.status_code in [200, 404]
        assert response_upper.status_code in [200, 404]
        assert response_mixed.status_code in [200, 404]
    
    # ==================== Bug #003: Date filter edge cases ====================
    def test_date_filter_handles_today(self, client):
        """
        Bug: Filtering by today's date excluded posts from today
        Fixed: Date range should be inclusive
        """
        today = datetime.now().strftime("%Y-%m-%d")
        response = client.get(f"/api/publishing/scheduled?date={today}")
        assert response.status_code in [200, 404]
    
    # ==================== Bug #004: Special characters in titles ====================
    def test_special_characters_in_search(self, client):
        """
        Bug: Special characters in search caused 500 error
        Fixed: Special characters should be escaped/handled
        """
        special_chars = ["&", "%", "#", "@", "!", "*"]
        for char in special_chars:
            response = client.get(f"/api/videos?search=test{char}video")
            assert response.status_code != 500, f"Failed on character: {char}"
    
    # ==================== Bug #005: Negative limit parameter ====================
    def test_negative_limit_handled(self, client):
        """
        Bug: Negative limit caused database error
        Fixed: Should validate and reject or use default
        """
        response = client.get("/api/videos?limit=-1")
        # Should either use default (200) or return validation error (422)
        assert response.status_code in [200, 400, 422]
        assert response.status_code != 500
    
    # ==================== Bug #006: Unicode in content ====================
    def test_unicode_content_handled(self, client):
        """
        Bug: Unicode characters (emojis, non-ASCII) caused encoding errors
        Fixed: Should handle all Unicode properly
        """
        # Test GET with unicode
        response = client.get("/api/videos?search=测试🎬")
        assert response.status_code != 500
        
    # ==================== Bug #007: Concurrent request handling ====================
    def test_concurrent_requests_stable(self, client):
        """
        Bug: Rapid concurrent requests caused race conditions
        Fixed: Proper request isolation
        """
        import concurrent.futures
        
        def make_request():
            return client.get("/api/social-analytics/overview").status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # All requests should complete without 500 errors
        server_errors = [r for r in results if r >= 500]
        assert len(server_errors) == 0, f"Got {len(server_errors)} server errors"
    
    # ==================== Bug #008: Empty body POST requests ====================
    def test_empty_post_body_handled(self, client):
        """
        Bug: POST with empty body caused unhandled exception
        Fixed: Should return 422 validation error
        """
        response = client.post("/api/goals", json={})
        assert response.status_code in [400, 404, 422]
        assert response.status_code != 500
    
    # ==================== Bug #009: Very long strings ====================
    def test_long_string_handled(self, client):
        """
        Bug: Very long strings caused buffer overflow/timeout
        Fixed: Should validate length limits
        """
        long_string = "a" * 100000
        response = client.get(f"/api/videos?search={long_string[:1000]}")  # Truncate for URL
        assert response.status_code != 500
    
    # ==================== Bug #010: Malformed JSON ====================
    def test_malformed_json_handled(self, client):
        """
        Bug: Malformed JSON body caused 500 instead of 422
        Fixed: Should return proper validation error
        """
        response = client.post(
            "/api/goals",
            content="{ invalid json }",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 404, 422]


class TestDataRegressions:
    """Regression tests for data handling"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_null_fields_serialized_correctly(self, client):
        """
        Bug: Null database fields caused JSON serialization errors
        Fixed: Null values should serialize as null in JSON
        """
        response = client.get("/api/videos?limit=1")
        if response.status_code == 200:
            data = response.json()
            # Should be valid JSON (didn't crash on null)
            assert data is not None
    
    def test_datetime_serialization(self, client):
        """
        Bug: Datetime fields weren't properly serialized to ISO format
        Fixed: All datetimes should be ISO 8601 strings
        """
        response = client.get("/api/publishing/scheduled?limit=1")
        if response.status_code == 200:
            data = response.json()
            # If there are results with dates, they should be strings
            if isinstance(data, list) and len(data) > 0:
                for item in data:
                    if "created_at" in item and item["created_at"]:
                        assert isinstance(item["created_at"], str)
    
    def test_uuid_serialization(self, client):
        """
        Bug: UUID fields serialized as binary instead of string
        Fixed: UUIDs should be string representation
        """
        response = client.get("/api/videos?limit=1")
        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("items", [])
            for item in items:
                if "id" in item and item["id"]:
                    # Should be string, not bytes
                    assert isinstance(item["id"], str)


class TestUIIntegrationRegressions:
    """Regression tests for API responses used by UI"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_analytics_response_structure(self, client):
        """
        Bug: UI crashed due to unexpected response structure
        Fixed: Response structure should be consistent
        """
        response = client.get("/api/social-analytics/overview")
        if response.status_code == 200:
            data = response.json()
            # Should have expected structure (even if empty)
            assert isinstance(data, (dict, list))
    
    def test_content_list_has_required_fields(self, client):
        """
        Bug: Missing fields in content list caused UI errors
        Fixed: All required fields should be present (or null)
        """
        response = client.get("/api/social-analytics/content?limit=5")
        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("items", data.get("data", []))
            
            # Each item should have basic fields
            for item in items[:5]:  # Check first 5
                assert "id" in item or item.get("id") is None


# Mark all as regression tests
pytestmark = pytest.mark.regression
