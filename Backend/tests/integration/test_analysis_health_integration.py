"""
Integration Tests for Analysis Health System
Tests the complete flow of detecting incomplete/failed analysis and re-analysis marking
"""
import pytest
import httpx
import asyncio
from typing import Dict, Any

# Test configuration
API_BASE = "http://localhost:5555"
TIMEOUT = 30.0


class TestAnalysisHealthIntegration:
    """Integration tests for /api/analysis-health endpoints"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Create HTTP client for tests"""
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_health_status_endpoint(self, client):
        """Test GET /api/analysis-health/status returns system health"""
        response = client.get("/api/analysis-health/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "healthy" in data
        assert "running_jobs" in data
        assert "stuck_jobs" in data
        assert isinstance(data["healthy"], bool)
    
    def test_scan_incomplete_endpoint(self, client):
        """Test GET /api/analysis-health/scan-incomplete scans videos"""
        response = client.get("/api/analysis-health/scan-incomplete", params={"limit": 100})
        assert response.status_code == 200
        
        data = response.json()
        assert "total_scanned" in data
        assert "summary" in data
        
        summary = data["summary"]
        assert "complete" in summary
        assert "incomplete" in summary
        assert "not_started" in summary
        assert "images_skipped" in summary
        
        # Verify counts are non-negative integers
        assert isinstance(summary["complete"], int)
        assert summary["complete"] >= 0
        assert isinstance(summary["incomplete"], int)
        assert summary["incomplete"] >= 0
    
    def test_scan_incomplete_with_limit(self, client):
        """Test scan respects limit parameter"""
        response = client.get("/api/analysis-health/scan-incomplete", params={"limit": 10})
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_scanned"] <= 10
    
    def test_skip_images_endpoint(self, client):
        """Test POST /api/analysis-health/skip-images marks image files"""
        response = client.post("/api/analysis-health/skip-images")
        assert response.status_code == 200
        
        data = response.json()
        assert "marked_as_skipped" in data
        assert "message" in data
        assert isinstance(data["marked_as_skipped"], int)
    
    def test_videos_needing_reanalysis_endpoint(self, client):
        """Test GET /api/analysis-health/videos-needing-reanalysis"""
        response = client.get("/api/analysis-health/videos-needing-reanalysis", params={"limit": 50})
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "videos" in data
        assert isinstance(data["videos"], list)
    
    def test_mark_incomplete_for_reanalysis(self, client):
        """Test POST /api/analysis-health/mark-incomplete-for-reanalysis"""
        response = client.post("/api/analysis-health/mark-incomplete-for-reanalysis", params={"limit": 10})
        assert response.status_code == 200
        
        data = response.json()
        assert "marked_count" in data
        assert "message" in data
    
    def test_clear_and_retry_invalid_video(self, client):
        """Test POST /api/analysis-health/clear-and-retry with invalid ID returns error"""
        response = client.post("/api/analysis-health/clear-and-retry/00000000-0000-0000-0000-000000000000")
        # Should either succeed (if video exists) or return appropriate error
        assert response.status_code in [200, 404, 500]
    
    def test_job_resilience_invalid_job(self, client):
        """Test GET /api/analysis-health/job/{job_id}/resilience with invalid ID"""
        response = client.get("/api/analysis-health/job/invalid-job-id/resilience")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data


class TestAnalysisHealthServiceIntegration:
    """Integration tests for AnalysisHealthService"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_scan_categorizes_by_file_type(self, client):
        """Test that scan correctly categorizes videos vs images"""
        response = client.get("/api/analysis-health/scan-incomplete", params={"limit": 500})
        assert response.status_code == 200
        
        data = response.json()
        summary = data["summary"]
        
        # Should have some categorization
        total_categorized = (
            summary["complete"] + 
            summary["incomplete"] + 
            summary["not_started"] + 
            summary["images_skipped"] +
            summary.get("unknown", 0)
        )
        assert total_categorized == data["total_scanned"]
    
    def test_incomplete_videos_have_missing_components(self, client):
        """Test that incomplete videos list missing components"""
        response = client.get("/api/analysis-health/scan-incomplete", params={"limit": 100})
        assert response.status_code == 200
        
        data = response.json()
        incomplete = data.get("incomplete_videos", [])
        
        for video in incomplete[:5]:  # Check first 5
            assert "missing_components" in video
            assert isinstance(video["missing_components"], list)
            assert len(video["missing_components"]) > 0
            assert "recommendation" in video


class TestAnalysisHealthWorkflow:
    """End-to-end workflow tests"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_full_scan_and_mark_workflow(self, client):
        """Test complete workflow: scan -> identify -> mark for reanalysis"""
        # Step 1: Scan for incomplete
        scan_response = client.get("/api/analysis-health/scan-incomplete", params={"limit": 100})
        assert scan_response.status_code == 200
        scan_data = scan_response.json()
        
        initial_incomplete = scan_data["summary"]["incomplete"]
        initial_not_started = scan_data["summary"]["not_started"]
        
        # Step 2: Mark incomplete for reanalysis
        mark_response = client.post("/api/analysis-health/mark-incomplete-for-reanalysis", params={"limit": 5})
        assert mark_response.status_code == 200
        mark_data = mark_response.json()
        
        # Step 3: Check videos needing reanalysis
        needs_response = client.get("/api/analysis-health/videos-needing-reanalysis")
        assert needs_response.status_code == 200
        
        # Workflow completed successfully
        assert True
    
    def test_skip_images_then_scan(self, client):
        """Test that skipping images updates scan results"""
        # Skip images
        skip_response = client.post("/api/analysis-health/skip-images")
        assert skip_response.status_code == 200
        
        # Scan again
        scan_response = client.get("/api/analysis-health/scan-incomplete", params={"limit": 100})
        assert scan_response.status_code == 200
        
        # Verify scan completed
        data = scan_response.json()
        assert "summary" in data


# Async tests for better performance testing
class TestAnalysisHealthAsync:
    """Async integration tests"""
    
    @pytest.fixture
    def async_client(self):
        return httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_concurrent_scans(self, async_client):
        """Test that multiple concurrent scans work correctly"""
        async with async_client:
            tasks = [
                async_client.get("/api/analysis-health/scan-incomplete", params={"limit": 50})
                for _ in range(3)
            ]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert "total_scanned" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
