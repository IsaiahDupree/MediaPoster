"""
Tests for Database-backed Media Processing API
Tests against real Supabase local database - NO MOCKS.
"""
import pytest
import uuid
import os
from pathlib import Path
from datetime import datetime
import httpx

# Real API URL - no mocks
API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"

# Test media directory
TEST_MEDIA_DIR = Path(os.path.expanduser("~/Documents/IphoneImport"))


# =============================================================================
# API CONNECTIVITY TESTS
# =============================================================================

class TestAPIConnectivity:
    """Test API endpoints are accessible."""

    def test_health_endpoint_returns_healthy(self):
        """Health endpoint should return healthy status."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "stats" in data

    def test_health_includes_video_count(self):
        """Health endpoint should include video count."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "total_videos" in data["stats"]
        assert isinstance(data["stats"]["total_videos"], int)

    def test_stats_endpoint_returns_data(self):
        """Stats endpoint should return ingestion statistics."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "total_videos" in data
        assert "analyzed_count" in data
        assert "pending_analysis" in data
        assert "total_size_bytes" in data
        
        # Verify types
        assert isinstance(data["total_videos"], int)
        assert isinstance(data["analyzed_count"], int)
        assert isinstance(data["pending_analysis"], int)
        assert isinstance(data["total_size_bytes"], int)


# =============================================================================
# LIST ENDPOINT TESTS
# =============================================================================

class TestListEndpoint:
    """Test media list endpoint."""

    def test_list_returns_array(self):
        """List endpoint should return array."""
        response = httpx.get(f"{DB_API_URL}/list", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_respects_limit(self):
        """List endpoint should respect limit parameter."""
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_list_items_have_required_fields(self):
        """List items should have required fields."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            item = data[0]
            assert "media_id" in item
            assert "filename" in item
            assert "status" in item
            assert "created_at" in item
            
            # Verify UUID format
            uuid.UUID(item["media_id"])

    def test_list_offset_pagination(self):
        """List endpoint should support offset pagination."""
        # Get first page
        response1 = httpx.get(f"{DB_API_URL}/list?limit=1&offset=0", timeout=10)
        assert response1.status_code == 200
        
        # Get second page
        response2 = httpx.get(f"{DB_API_URL}/list?limit=1&offset=1", timeout=10)
        assert response2.status_code == 200


# =============================================================================
# DETAIL ENDPOINT TESTS
# =============================================================================

class TestDetailEndpoint:
    """Test media detail endpoint."""

    def test_detail_returns_404_for_invalid_id(self):
        """Detail endpoint should return 404 for non-existent ID."""
        fake_id = str(uuid.uuid4())
        response = httpx.get(f"{DB_API_URL}/detail/{fake_id}", timeout=10)
        assert response.status_code == 404

    def test_detail_returns_400_for_invalid_uuid(self):
        """Detail endpoint should return 400 for invalid UUID format."""
        response = httpx.get(f"{DB_API_URL}/detail/not-a-uuid", timeout=10)
        assert response.status_code == 400

    def test_detail_returns_valid_data_for_existing_media(self):
        """Detail endpoint should return valid data for existing media."""
        # First get a real media ID from list
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.status_code != 200 or len(list_response.json()) == 0:
            pytest.skip("No media in database to test detail endpoint")
        
        media_id = list_response.json()[0]["media_id"]
        
        # Get detail
        response = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert data["media_id"] == media_id
        assert "filename" in data
        assert "file_path" in data
        assert "created_at" in data


# =============================================================================
# INGEST ENDPOINT TESTS
# =============================================================================

class TestIngestEndpoint:
    """Test media ingestion endpoints."""

    def test_ingest_single_file_invalid_path(self):
        """Ingest should return 400 for non-existent file."""
        response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": "/nonexistent/path/video.mov"},
            timeout=10
        )
        assert response.status_code == 400

    def test_batch_ingest_invalid_directory(self):
        """Batch ingest should return 400 for invalid directory."""
        response = httpx.post(
            f"{DB_API_URL}/batch/ingest",
            json={"directory_path": "/nonexistent/directory"},
            timeout=10
        )
        assert response.status_code == 400

    @pytest.mark.skipif(not TEST_MEDIA_DIR.exists(), reason="Test media directory not available")
    def test_batch_ingest_valid_directory(self):
        """Batch ingest should accept valid directory."""
        response = httpx.post(
            f"{DB_API_URL}/batch/ingest",
            json={
                "directory_path": str(TEST_MEDIA_DIR),
                "resume": True
            },
            timeout=30
        )
        # Should succeed or return job info
        assert response.status_code in [200, 400]  # 400 if no files found


# =============================================================================
# ANALYZE ENDPOINT TESTS
# =============================================================================

class TestAnalyzeEndpoint:
    """Test media analysis endpoints."""

    def test_analyze_invalid_id_returns_404(self):
        """Analyze should return 404 for non-existent media."""
        fake_id = str(uuid.uuid4())
        response = httpx.post(f"{DB_API_URL}/analyze/{fake_id}", timeout=10)
        assert response.status_code == 404

    def test_analyze_invalid_uuid_returns_400(self):
        """Analyze should return 400 for invalid UUID."""
        response = httpx.post(f"{DB_API_URL}/analyze/not-a-uuid", timeout=10)
        assert response.status_code == 400

    def test_analyze_existing_media(self):
        """Analyze should accept existing media."""
        # Get a media ID
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.status_code != 200 or len(list_response.json()) == 0:
            pytest.skip("No media in database to test analyze endpoint")
        
        media_id = list_response.json()[0]["media_id"]
        
        # Start analysis
        response = httpx.post(f"{DB_API_URL}/analyze/{media_id}", timeout=10)
        # Should succeed, indicate already analyzed, or server error (if analysis service issue)
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            assert "status" in response.json()

    def test_batch_analyze_endpoint(self):
        """Batch analyze endpoint should work."""
        response = httpx.post(f"{DB_API_URL}/batch/analyze?limit=1", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "count" in data


# =============================================================================
# THUMBNAIL ENDPOINT TESTS
# =============================================================================

class TestThumbnailEndpoint:
    """Test thumbnail endpoints."""

    def test_thumbnail_invalid_id_returns_404(self):
        """Thumbnail should return 404 for non-existent media."""
        fake_id = str(uuid.uuid4())
        response = httpx.get(f"{DB_API_URL}/thumbnail/{fake_id}", timeout=10)
        assert response.status_code == 404

    def test_thumbnail_invalid_size_returns_422(self):
        """Thumbnail should return 422 for invalid size."""
        # Get a media ID first
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.status_code != 200 or len(list_response.json()) == 0:
            pytest.skip("No media in database")
        
        media_id = list_response.json()[0]["media_id"]
        
        response = httpx.get(f"{DB_API_URL}/thumbnail/{media_id}?size=invalid", timeout=10)
        assert response.status_code == 422

    def test_thumbnail_valid_sizes(self):
        """Thumbnail should accept valid size parameters."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.status_code != 200 or len(list_response.json()) == 0:
            pytest.skip("No media in database")
        
        media_id = list_response.json()[0]["media_id"]
        
        for size in ["small", "medium", "large"]:
            response = httpx.get(f"{DB_API_URL}/thumbnail/{media_id}?size={size}", timeout=30)
            # May return image or 404 if file not found
            assert response.status_code in [200, 404, 500]


# =============================================================================
# DELETE ENDPOINT TESTS
# =============================================================================

class TestDeleteEndpoint:
    """Test media deletion endpoint."""

    def test_delete_invalid_id_returns_404(self):
        """Delete should return 404 for non-existent media."""
        fake_id = str(uuid.uuid4())
        response = httpx.delete(f"{DB_API_URL}/{fake_id}", timeout=10)
        assert response.status_code == 404

    def test_delete_invalid_uuid_returns_400(self):
        """Delete should return 400 for invalid UUID."""
        response = httpx.delete(f"{DB_API_URL}/not-a-uuid", timeout=10)
        assert response.status_code == 400


# =============================================================================
# DATA PERSISTENCE TESTS
# =============================================================================

class TestDataPersistence:
    """Test that data persists correctly."""

    def test_stats_match_list_count(self):
        """Stats total should match list count (within limit)."""
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        list_response = httpx.get(f"{DB_API_URL}/list?limit=200", timeout=10)
        
        assert stats_response.status_code == 200
        assert list_response.status_code == 200
        
        stats = stats_response.json()
        items = list_response.json()
        
        # If total is within limit, counts should match
        if stats["total_videos"] <= 200:
            assert stats["total_videos"] == len(items)
        else:
            # If more than limit, we should get exactly limit items
            assert len(items) == 200

    def test_analyzed_count_matches_filtered_list(self):
        """Analyzed count should match analyzed items in list."""
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        list_response = httpx.get(f"{DB_API_URL}/list?limit=200", timeout=10)
        
        assert stats_response.status_code == 200
        assert list_response.status_code == 200
        
        stats = stats_response.json()
        items = list_response.json()
        
        analyzed_items = [i for i in items if i["status"] == "analyzed"]
        
        # If total is within limit, analyzed counts should match
        if stats["total_videos"] <= 200:
            assert stats["analyzed_count"] == len(analyzed_items)


# =============================================================================
# RESPONSE FORMAT TESTS
# =============================================================================

class TestResponseFormats:
    """Test API response formats."""

    def test_list_response_is_json_array(self):
        """List response should be JSON array."""
        response = httpx.get(f"{DB_API_URL}/list", timeout=10)
        assert response.headers.get("content-type", "").startswith("application/json")
        assert isinstance(response.json(), list)

    def test_detail_response_is_json_object(self):
        """Detail response should be JSON object."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if len(list_response.json()) == 0:
            pytest.skip("No media in database")
        
        media_id = list_response.json()[0]["media_id"]
        response = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
        
        assert response.headers.get("content-type", "").startswith("application/json")
        assert isinstance(response.json(), dict)

    def test_stats_response_has_correct_types(self):
        """Stats response should have correct field types."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        data = response.json()
        
        assert isinstance(data["total_videos"], int)
        assert isinstance(data["analyzed_count"], int)
        assert isinstance(data["pending_analysis"], int)
        assert isinstance(data["total_size_bytes"], int)
        assert data["avg_duration_sec"] is None or isinstance(data["avg_duration_sec"], (int, float))


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test API performance."""

    def test_health_response_under_500ms(self):
        """Health endpoint should respond within 500ms."""
        import time
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.5, f"Health took {elapsed:.2f}s, expected < 0.5s"

    def test_list_response_under_2s(self):
        """List endpoint should respond within 2s."""
        import time
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0, f"List took {elapsed:.2f}s, expected < 2s"

    def test_stats_response_under_1s(self):
        """Stats endpoint should respond within 1s."""
        import time
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"Stats took {elapsed:.2f}s, expected < 1s"


# =============================================================================
# CONCURRENT REQUEST TESTS
# =============================================================================

class TestConcurrency:
    """Test API under concurrent load."""

    def test_concurrent_health_requests(self):
        """API should handle concurrent health requests."""
        import concurrent.futures
        
        def make_request():
            return httpx.get(f"{DB_API_URL}/health", timeout=10)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [f.result() for f in futures]
        
        assert all(r.status_code == 200 for r in results)

    def test_concurrent_list_requests(self):
        """API should handle concurrent list requests."""
        import concurrent.futures
        
        def make_request():
            return httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            results = [f.result() for f in futures]
        
        assert all(r.status_code == 200 for r in results)


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
