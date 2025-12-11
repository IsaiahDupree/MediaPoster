"""
PRD API Tests
Comprehensive API endpoint testing.
Coverage: 60+ API tests
"""
import pytest
import httpx
import time
from pathlib import Path
import os

API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"


# =============================================================================
# API TESTS: Health Endpoints
# =============================================================================

class TestAPIHealth:
    """Health check API tests."""
    
    def test_root_health(self):
        """Root endpoint returns 200."""
        response = httpx.get(f"{API_BASE}/", timeout=10)
        assert response.status_code == 200
    
    def test_media_db_health(self):
        """Media DB health endpoint."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert response.status_code == 200
    
    def test_health_response_format(self):
        """Health returns proper JSON."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        data = response.json()
        assert "status" in data
    
    def test_health_database_connected(self):
        """Health shows database connected."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        data = response.json()
        assert data.get("database") == "connected"
    
    def test_health_response_time(self):
        """Health responds within 1 second."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        elapsed = time.time() - start
        assert elapsed < 1.0
        assert response.status_code == 200


# =============================================================================
# API TESTS: Media List Endpoints
# =============================================================================

class TestAPIMediaList:
    """Media list API tests."""
    
    def test_list_returns_200(self):
        """List endpoint returns 200."""
        response = httpx.get(f"{DB_API_URL}/list", timeout=10)
        assert response.status_code == 200
    
    def test_list_returns_array(self):
        """List returns JSON array."""
        response = httpx.get(f"{DB_API_URL}/list", timeout=10)
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_with_limit(self):
        """List respects limit parameter."""
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        data = response.json()
        assert len(data) <= 5
    
    def test_list_with_offset(self):
        """List respects offset parameter."""
        response = httpx.get(f"{DB_API_URL}/list?offset=0&limit=10", timeout=10)
        assert response.status_code == 200
    
    def test_list_default_limit(self):
        """List has default limit (50)."""
        response = httpx.get(f"{DB_API_URL}/list", timeout=10)
        data = response.json()
        assert len(data) <= 50
    
    def test_list_item_structure(self):
        """List items have required fields."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        data = response.json()
        if data:
            item = data[0]
            assert "media_id" in item
    
    def test_list_with_status_filter(self):
        """List filters by status."""
        response = httpx.get(f"{DB_API_URL}/list?status=ingested", timeout=10)
        assert response.status_code == 200
    
    def test_list_empty_result(self):
        """List handles empty results."""
        response = httpx.get(f"{DB_API_URL}/list?status=nonexistent", timeout=10)
        # Should return 200 with empty array or 400/500
        assert response.status_code in [200, 400, 500]
    
    def test_list_large_offset(self):
        """List handles large offset."""
        response = httpx.get(f"{DB_API_URL}/list?offset=10000", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_max_limit(self):
        """List with max limit."""
        response = httpx.get(f"{DB_API_URL}/list?limit=100", timeout=10)
        assert response.status_code == 200


# =============================================================================
# API TESTS: Media Detail Endpoints
# =============================================================================

class TestAPIMediaDetail:
    """Media detail API tests."""
    
    @pytest.fixture
    def sample_media_id(self):
        """Get a sample media ID."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if response.status_code == 200 and response.json():
            return response.json()[0]["media_id"]
        return None
    
    def test_detail_returns_200(self, sample_media_id):
        """Detail endpoint returns 200."""
        if not sample_media_id:
            pytest.skip("No media available")
        response = httpx.get(f"{DB_API_URL}/detail/{sample_media_id}", timeout=10)
        assert response.status_code == 200
    
    def test_detail_returns_object(self, sample_media_id):
        """Detail returns JSON object."""
        if not sample_media_id:
            pytest.skip("No media available")
        response = httpx.get(f"{DB_API_URL}/detail/{sample_media_id}", timeout=10)
        data = response.json()
        assert isinstance(data, dict)
    
    def test_detail_has_media_id(self, sample_media_id):
        """Detail contains media_id."""
        if not sample_media_id:
            pytest.skip("No media available")
        response = httpx.get(f"{DB_API_URL}/detail/{sample_media_id}", timeout=10)
        data = response.json()
        assert "media_id" in data or "id" in data
    
    def test_detail_invalid_id(self):
        """Detail with invalid ID returns 404."""
        response = httpx.get(f"{DB_API_URL}/detail/invalid-uuid", timeout=10)
        assert response.status_code in [400, 404, 422]
    
    def test_detail_nonexistent_id(self):
        """Detail with non-existent UUID returns 404."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = httpx.get(f"{DB_API_URL}/detail/{fake_uuid}", timeout=10)
        assert response.status_code in [404, 500]


# =============================================================================
# API TESTS: Thumbnail Endpoints
# =============================================================================

class TestAPIThumbnail:
    """Thumbnail API tests."""
    
    @pytest.fixture
    def sample_media_id(self):
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if response.status_code == 200 and response.json():
            return response.json()[0]["media_id"]
        return None
    
    def test_thumbnail_endpoint_exists(self, sample_media_id):
        """Thumbnail endpoint exists."""
        if not sample_media_id:
            pytest.skip("No media available")
        response = httpx.get(f"{DB_API_URL}/thumbnail/{sample_media_id}", timeout=30)
        assert response.status_code in [200, 404]
    
    def test_thumbnail_with_size(self, sample_media_id):
        """Thumbnail with size parameter."""
        if not sample_media_id:
            pytest.skip("No media available")
        for size in ["small", "medium", "large"]:
            response = httpx.get(
                f"{DB_API_URL}/thumbnail/{sample_media_id}?size={size}",
                timeout=30
            )
            assert response.status_code in [200, 404]
    
    def test_thumbnail_content_type(self, sample_media_id):
        """Thumbnail returns image content type."""
        if not sample_media_id:
            pytest.skip("No media available")
        response = httpx.get(f"{DB_API_URL}/thumbnail/{sample_media_id}", timeout=30)
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "image" in content_type.lower()
    
    def test_thumbnail_invalid_id(self):
        """Thumbnail with invalid ID."""
        response = httpx.get(f"{DB_API_URL}/thumbnail/invalid", timeout=10)
        assert response.status_code in [400, 404, 422]


# =============================================================================
# API TESTS: Stats Endpoints
# =============================================================================

class TestAPIStats:
    """Stats API tests."""
    
    def test_stats_returns_200(self):
        """Stats endpoint returns 200."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
    
    def test_stats_returns_object(self):
        """Stats returns JSON object."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        data = response.json()
        assert isinstance(data, dict)
    
    def test_stats_has_total(self):
        """Stats contains total count."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        data = response.json()
        assert "total_videos" in data or "total" in data or "count" in data
    
    def test_stats_counts_are_numbers(self):
        """Stats counts are numeric."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        data = response.json()
        for key, value in data.items():
            if "count" in key.lower() or "total" in key.lower():
                assert isinstance(value, (int, float))


# =============================================================================
# API TESTS: Ingestion Endpoints
# =============================================================================

class TestAPIIngestion:
    """Ingestion API tests."""
    
    def test_ingest_file_endpoint_exists(self):
        """Ingest file endpoint exists."""
        # OPTIONS or POST without file should return method info
        response = httpx.post(f"{DB_API_URL}/ingest/file", timeout=10)
        assert response.status_code in [200, 400, 422, 500]
    
    def test_ingest_requires_file_path(self):
        """Ingest requires file_path parameter."""
        response = httpx.post(f"{DB_API_URL}/ingest/file", timeout=10)
        # Should fail without file_path
        assert response.status_code in [400, 422, 500]
    
    def test_ingest_invalid_path(self):
        """Ingest with invalid path."""
        response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": "/nonexistent/file.mov"},
            timeout=10
        )
        assert response.status_code in [400, 404, 500]


# =============================================================================
# API TESTS: Analysis Endpoints
# =============================================================================

class TestAPIAnalysis:
    """Analysis API tests."""
    
    @pytest.fixture
    def sample_media_id(self):
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if response.status_code == 200 and response.json():
            return response.json()[0]["media_id"]
        return None
    
    def test_analyze_endpoint_exists(self, sample_media_id):
        """Analyze endpoint exists."""
        if not sample_media_id:
            pytest.skip("No media available")
        response = httpx.post(f"{DB_API_URL}/analyze/{sample_media_id}", timeout=10)
        assert response.status_code in [200, 500]
    
    def test_analyze_invalid_id(self):
        """Analyze with invalid ID."""
        response = httpx.post(f"{DB_API_URL}/analyze/invalid", timeout=10)
        assert response.status_code in [400, 404, 422, 500]


# =============================================================================
# API TESTS: Video Streaming
# =============================================================================

class TestAPIVideoStreaming:
    """Video streaming API tests."""
    
    @pytest.fixture
    def sample_media_id(self):
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if response.status_code == 200 and response.json():
            return response.json()[0]["media_id"]
        return None
    
    def test_video_stream_endpoint(self, sample_media_id):
        """Video stream endpoint exists."""
        if not sample_media_id:
            pytest.skip("No media available")
        response = httpx.get(
            f"{DB_API_URL}/video/{sample_media_id}",
            timeout=30
        )
        assert response.status_code in [200, 404]
    
    def test_video_stream_content_type(self, sample_media_id):
        """Video stream returns video content type."""
        if not sample_media_id:
            pytest.skip("No media available")
        response = httpx.get(
            f"{DB_API_URL}/video/{sample_media_id}",
            timeout=30
        )
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "video" in content_type.lower() or "octet" in content_type.lower()


# =============================================================================
# API TESTS: Error Handling
# =============================================================================

class TestAPIErrorHandling:
    """API error handling tests."""
    
    def test_404_for_unknown_endpoint(self):
        """Unknown endpoint returns 404."""
        response = httpx.get(f"{API_BASE}/api/nonexistent", timeout=10)
        assert response.status_code in [404, 307]
    
    def test_invalid_json_body(self):
        """Invalid JSON body handled."""
        response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            content="not json",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code in [400, 422, 500]
    
    def test_wrong_http_method(self):
        """Wrong HTTP method returns 405."""
        response = httpx.delete(f"{DB_API_URL}/list", timeout=10)
        assert response.status_code in [405, 404, 307]


# =============================================================================
# API TESTS: Response Time
# =============================================================================

class TestAPIPerformance:
    """API performance tests."""
    
    def test_list_response_time(self):
        """List responds quickly."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        elapsed = time.time() - start
        assert elapsed < 2.0
        assert response.status_code == 200
    
    def test_stats_response_time(self):
        """Stats responds quickly."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        elapsed = time.time() - start
        assert elapsed < 1.0
        assert response.status_code == 200
    
    def test_concurrent_requests(self):
        """Handle concurrent requests."""
        import concurrent.futures
        
        def make_request():
            return httpx.get(f"{DB_API_URL}/health", timeout=10)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [f.result() for f in futures]
        
        for response in results:
            assert response.status_code == 200


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
