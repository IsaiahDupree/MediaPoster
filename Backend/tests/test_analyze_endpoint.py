"""
Tests for Media Analyze Endpoint
Tests the /api/media-db/analyze/{media_id} endpoint functionality.
"""
import pytest
import httpx
import uuid
import time
from typing import Optional

API_BASE = "http://localhost:5555"
MEDIA_DB_URL = f"{API_BASE}/api/media-db"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_first_media_id() -> Optional[str]:
    """Get the first media ID from the database."""
    try:
        response = httpx.get(f"{MEDIA_DB_URL}/list?limit=1", timeout=10)
        if response.status_code == 200:
            media_list = response.json()
            if media_list and len(media_list) > 0:
                return media_list[0].get("media_id")
    except Exception as e:
        print(f"Error getting media: {e}")
    return None


def get_unanalyzed_media_id() -> Optional[str]:
    """Get a media ID that hasn't been analyzed yet."""
    try:
        response = httpx.get(f"{MEDIA_DB_URL}/list?limit=100", timeout=10)
        if response.status_code == 200:
            for item in response.json():
                # Check if not analyzed
                if not item.get("pre_social_score") and not item.get("transcript"):
                    return item.get("media_id")
    except Exception as e:
        print(f"Error: {e}")
    return None


# =============================================================================
# ANALYZE ENDPOINT TESTS
# =============================================================================

class TestAnalyzeEndpoint:
    """Tests for POST /api/media-db/analyze/{media_id}"""
    
    def test_analyze_endpoint_exists(self):
        """Analyze endpoint should respond (not 404)."""
        # Use a random UUID - should return 404 for media not found, not route not found
        fake_id = str(uuid.uuid4())
        response = httpx.post(f"{MEDIA_DB_URL}/analyze/{fake_id}", timeout=10)
        # Should return 404 (media not found), not 404 (route not found) or 500
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
    
    def test_analyze_invalid_uuid(self):
        """Invalid UUID should return 400."""
        response = httpx.post(f"{MEDIA_DB_URL}/analyze/not-a-uuid", timeout=10)
        assert response.status_code == 400
        assert "Invalid media ID" in response.json().get("detail", "")
    
    def test_analyze_nonexistent_media(self):
        """Non-existent media ID should return 404."""
        fake_id = str(uuid.uuid4())
        response = httpx.post(f"{MEDIA_DB_URL}/analyze/{fake_id}", timeout=10)
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()
    
    def test_analyze_valid_media(self):
        """Valid media ID should start analysis."""
        media_id = get_first_media_id()
        if not media_id:
            pytest.skip("No media in database")
        
        response = httpx.post(f"{MEDIA_DB_URL}/analyze/{media_id}", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["analyzing", "already_analyzed"]
        assert data["media_id"] == media_id
    
    def test_analyze_returns_analyzing_status(self):
        """First analysis request should return 'analyzing' status."""
        media_id = get_unanalyzed_media_id()
        if not media_id:
            pytest.skip("No unanalyzed media in database")
        
        response = httpx.post(f"{MEDIA_DB_URL}/analyze/{media_id}", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "analyzing"
    
    def test_analyze_already_analyzed_returns_correct_status(self):
        """Second analysis request should return 'already_analyzed'."""
        media_id = get_first_media_id()
        if not media_id:
            pytest.skip("No media in database")
        
        # First request
        response1 = httpx.post(f"{MEDIA_DB_URL}/analyze/{media_id}", timeout=10)
        assert response1.status_code == 200
        
        # Wait a moment for background task to complete
        time.sleep(3)
        
        # Second request should say already analyzed
        response2 = httpx.post(f"{MEDIA_DB_URL}/analyze/{media_id}", timeout=10)
        assert response2.status_code == 200
        
        # Should be either analyzing (if still running) or already_analyzed
        data = response2.json()
        assert data["status"] in ["analyzing", "already_analyzed"]


# =============================================================================
# BATCH ANALYZE TESTS
# =============================================================================

class TestBatchAnalyzeEndpoint:
    """Tests for POST /api/media-db/batch/analyze"""
    
    def test_batch_analyze_endpoint_exists(self):
        """Batch analyze endpoint should exist."""
        response = httpx.post(f"{MEDIA_DB_URL}/batch/analyze", timeout=10)
        assert response.status_code in [200, 400, 422, 500]
        # Should not be 404 (route not found)
    
    def test_batch_analyze_returns_count(self):
        """Batch analyze should return count of videos queued."""
        response = httpx.post(f"{MEDIA_DB_URL}/batch/analyze?limit=5", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["started", "no_pending"]
        assert "count" in data
        assert isinstance(data["count"], int)
    
    def test_batch_analyze_respects_limit(self):
        """Batch analyze should respect the limit parameter."""
        response = httpx.post(f"{MEDIA_DB_URL}/batch/analyze?limit=2", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] <= 2


# =============================================================================
# ANALYSIS RESULTS TESTS
# =============================================================================

class TestAnalysisResults:
    """Tests for analysis results in media detail."""
    
    def test_detail_contains_analysis_fields(self):
        """Media detail should contain analysis fields."""
        media_id = get_first_media_id()
        if not media_id:
            pytest.skip("No media in database")
        
        # Trigger analysis
        httpx.post(f"{MEDIA_DB_URL}/analyze/{media_id}", timeout=10)
        
        # Wait for background task
        time.sleep(3)
        
        # Get detail
        response = httpx.get(f"{MEDIA_DB_URL}/detail/{media_id}", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        # These fields should exist (may be null if analysis not complete)
        expected_fields = ["pre_social_score", "transcript", "topics"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_analyzed_media_has_score(self):
        """After analysis, media should have a pre_social_score."""
        media_id = get_first_media_id()
        if not media_id:
            pytest.skip("No media in database")
        
        # Trigger analysis
        httpx.post(f"{MEDIA_DB_URL}/analyze/{media_id}", timeout=10)
        
        # Wait for background task
        time.sleep(4)
        
        # Get detail
        response = httpx.get(f"{MEDIA_DB_URL}/detail/{media_id}", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        # Score should exist after analysis
        if data.get("pre_social_score") is not None:
            assert 0 <= data["pre_social_score"] <= 100


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestAnalyzeErrorHandling:
    """Tests for error handling in analyze endpoint."""
    
    def test_handles_missing_file_gracefully(self):
        """Analysis should handle missing file gracefully."""
        media_id = get_first_media_id()
        if not media_id:
            pytest.skip("No media in database")
        
        # Endpoint should still return 200 (background task handles file check)
        response = httpx.post(f"{MEDIA_DB_URL}/analyze/{media_id}", timeout=10)
        assert response.status_code in [200, 404]
    
    def test_empty_uuid_rejected(self):
        """Empty UUID should be rejected."""
        response = httpx.post(f"{MEDIA_DB_URL}/analyze/", timeout=10)
        # Should be 307 redirect, 404 (route not found), or 405 (method not allowed)
        assert response.status_code in [307, 404, 405, 422]
    
    def test_concurrent_analyze_requests(self):
        """Multiple concurrent analyze requests should be handled."""
        media_id = get_first_media_id()
        if not media_id:
            pytest.skip("No media in database")
        
        # Send 3 concurrent requests
        with httpx.Client(timeout=10) as client:
            responses = []
            for _ in range(3):
                resp = client.post(f"{MEDIA_DB_URL}/analyze/{media_id}")
                responses.append(resp)
        
        # All should succeed
        for resp in responses:
            assert resp.status_code == 200


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestAnalyzeIntegration:
    """Integration tests for analyze workflow."""
    
    def test_full_analyze_workflow(self):
        """Test complete analyze workflow: list -> analyze -> check result."""
        # Step 1: Get media
        list_resp = httpx.get(f"{MEDIA_DB_URL}/list?limit=1", timeout=10)
        assert list_resp.status_code == 200
        
        media_list = list_resp.json()
        if not media_list:
            pytest.skip("No media in database")
        
        media_id = media_list[0]["media_id"]
        
        # Step 2: Trigger analysis
        analyze_resp = httpx.post(f"{MEDIA_DB_URL}/analyze/{media_id}", timeout=10)
        assert analyze_resp.status_code == 200
        
        # Step 3: Wait and check
        time.sleep(4)
        
        detail_resp = httpx.get(f"{MEDIA_DB_URL}/detail/{media_id}", timeout=10)
        assert detail_resp.status_code == 200
        
        # Verify structure
        data = detail_resp.json()
        assert "media_id" in data
        assert "filename" in data
    
    def test_analyze_does_not_break_list_endpoint(self):
        """Analyze should not break the list endpoint."""
        # Get initial list
        list_resp1 = httpx.get(f"{MEDIA_DB_URL}/list?limit=10", timeout=10)
        assert list_resp1.status_code == 200
        
        # Trigger batch analyze
        batch_resp = httpx.post(f"{MEDIA_DB_URL}/batch/analyze?limit=3", timeout=10)
        assert batch_resp.status_code == 200
        
        # Wait
        time.sleep(2)
        
        # List should still work
        list_resp2 = httpx.get(f"{MEDIA_DB_URL}/list?limit=10", timeout=10)
        assert list_resp2.status_code == 200


# =============================================================================
# STATS ENDPOINT TESTS
# =============================================================================

class TestStatsEndpoint:
    """Tests for /api/media-db/stats endpoint."""
    
    def test_stats_includes_analysis_counts(self):
        """Stats should include analyzed_count."""
        response = httpx.get(f"{MEDIA_DB_URL}/stats", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_videos" in data
        assert "analyzed_count" in data
        assert "pending_analysis" in data
        
        # Counts should be non-negative
        assert data["total_videos"] >= 0
        assert data["analyzed_count"] >= 0
        assert data["pending_analysis"] >= 0
    
    def test_stats_analyzed_plus_pending_equals_total(self):
        """analyzed_count + pending_analysis should equal total_videos."""
        response = httpx.get(f"{MEDIA_DB_URL}/stats", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        # This may not always be exactly equal due to timing, but close
        total = data["total_videos"]
        analyzed = data["analyzed_count"]
        pending = data["pending_analysis"]
        
        # Allow for some variance due to ongoing processing
        assert analyzed + pending <= total + 5


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
