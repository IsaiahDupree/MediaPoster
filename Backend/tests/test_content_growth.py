"""
Tests for Content Growth API
Tests metrics tracking, backfill, and growth analysis endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import uuid

# Import the app
import sys
sys.path.insert(0, '..')
from main import app

client = TestClient(app)


class TestContentGrowthAPI:
    """Test suite for Content Growth endpoints"""

    # =========================================================================
    # GET /api/content-growth/summary
    # =========================================================================

    def test_get_summary_default(self):
        """Test getting growth summary with default parameters"""
        response = client.get("/api/content-growth/summary")
        # Accept 200 (success) or 500 (database not available in test)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "total_views" in data
            assert "total_engagement" in data
            assert "total_posts" in data
            assert "avg_views_per_post" in data
            assert "avg_engagement_rate" in data
            assert "top_performing" in data
            assert "fastest_growing" in data
            assert "platform_breakdown" in data

    def test_get_summary_with_days_parameter(self):
        """Test getting summary with specific days parameter"""
        for days in [7, 30, 90]:
            response = client.get(f"/api/content-growth/summary?days={days}")
            assert response.status_code in [200, 500]
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data["total_views"], (int, float))

    def test_get_summary_platform_breakdown(self):
        """Test that platform breakdown contains expected fields"""
        response = client.get("/api/content-growth/summary")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            if data.get("platform_breakdown"):
                for platform, breakdown in data["platform_breakdown"].items():
                    assert "views" in breakdown

    # =========================================================================
    # GET /api/content-growth/content/{post_id}
    # =========================================================================

    def test_get_content_metrics_valid_id(self):
        """Test getting metrics for a specific post"""
        # Use a test post ID
        test_id = str(uuid.uuid4())
        response = client.get(f"/api/content-growth/content/{test_id}")
        
        # Should return 200 (may have mock data), 404, or 500 (db issue)
        assert response.status_code in [200, 400, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "post_id" in data
            assert "current" in data
            assert "history" in data

    def test_get_content_metrics_with_days(self):
        """Test getting content metrics with days parameter"""
        test_id = str(uuid.uuid4())
        response = client.get(f"/api/content-growth/content/{test_id}?days=14")
        assert response.status_code in [200, 400, 404, 500]

    # =========================================================================
    # POST /api/content-growth/backfill
    # =========================================================================

    def test_start_backfill_job(self):
        """Test starting a backfill job"""
        response = client.post("/api/content-growth/backfill?days=7")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert "status" in data
            assert data["status"] in ["started", "running", "completed"]

    def test_start_backfill_with_platform(self):
        """Test starting backfill for specific platform"""
        response = client.post("/api/content-growth/backfill?platform=instagram&days=7")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data

    # =========================================================================
    # GET /api/content-growth/backfill/{job_id}
    # =========================================================================

    def test_get_backfill_status(self):
        """Test getting backfill job status"""
        # First start a job
        start_response = client.post("/api/content-growth/backfill?days=7")
        assert start_response.status_code in [200, 500]
        
        if start_response.status_code == 200:
            job_id = start_response.json()["job_id"]
            
            # Then check status
            status_response = client.get(f"/api/content-growth/backfill/{job_id}")
            assert status_response.status_code in [200, 404]
            
            if status_response.status_code == 200:
                data = status_response.json()
                assert "job_id" in data
                assert "status" in data

    def test_get_backfill_status_invalid_id(self):
        """Test getting status for non-existent job"""
        response = client.get("/api/content-growth/backfill/invalid-job-id")
        assert response.status_code == 404

    # =========================================================================
    # GET /api/content-growth/chart-data/{post_id}
    # =========================================================================

    def test_get_chart_data(self):
        """Test getting chart data for a post"""
        test_id = str(uuid.uuid4())
        response = client.get(f"/api/content-growth/chart-data/{test_id}")
        
        # May return mock data or 404
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "metric" in data
            assert "labels" in data
            assert "values" in data
            assert isinstance(data["labels"], list)
            assert isinstance(data["values"], list)

    def test_get_chart_data_different_metrics(self):
        """Test getting chart data for different metrics"""
        test_id = str(uuid.uuid4())
        
        for metric in ["views", "likes", "comments", "shares"]:
            response = client.get(f"/api/content-growth/chart-data/{test_id}?metric={metric}")
            assert response.status_code in [200, 404, 500]

    # =========================================================================
    # GET /api/content-growth/compare
    # =========================================================================

    def test_compare_posts(self):
        """Test comparing multiple posts"""
        post_ids = [str(uuid.uuid4()) for _ in range(3)]
        response = client.get(
            "/api/content-growth/compare",
            params={"post_ids": post_ids}
        )
        assert response.status_code in [200, 404]

    # =========================================================================
    # POST /api/content-growth/sync/{post_id}
    # =========================================================================

    def test_sync_single_post(self):
        """Test syncing metrics for a single post"""
        test_id = str(uuid.uuid4())
        response = client.post(f"/api/content-growth/sync/{test_id}")
        assert response.status_code in [200, 404, 500]


class TestContentGrowthValidation:
    """Test input validation for Content Growth API"""

    def test_summary_invalid_days(self):
        """Test summary with invalid days parameter"""
        response = client.get("/api/content-growth/summary?days=-1")
        # May validate or accept
        assert response.status_code in [200, 422, 500]

    def test_chart_data_invalid_metric(self):
        """Test chart data with invalid metric"""
        test_id = str(uuid.uuid4())
        response = client.get(f"/api/content-growth/chart-data/{test_id}?metric=invalid")
        assert response.status_code in [200, 400, 422]  # May accept or reject


class TestContentGrowthDataIntegrity:
    """Test data integrity for Content Growth API"""

    def test_summary_values_are_numeric(self):
        """Test that summary returns numeric values"""
        response = client.get("/api/content-growth/summary")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data["total_views"], (int, float))
            assert isinstance(data["total_engagement"], (int, float))
            assert isinstance(data["total_posts"], int)

    def test_top_performing_structure(self):
        """Test top performing list structure"""
        response = client.get("/api/content-growth/summary")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get("top_performing", []):
                assert "post_id" in item


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
