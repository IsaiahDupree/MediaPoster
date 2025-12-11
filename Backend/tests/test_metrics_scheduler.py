"""
Tests for Metrics Scheduler API
Tests check-back periods, sync scheduling, and line graph data.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid

import sys
sys.path.insert(0, '..')
from main import app

client = TestClient(app)


class TestMetricsSchedulerStatus:
    """Test scheduler status endpoints"""

    def test_get_scheduler_status(self):
        """Test getting scheduler status"""
        response = client.get("/api/metrics-scheduler/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "is_running" in data
        assert "platforms" in data
        assert "next_syncs" in data
        assert "recent_syncs" in data
        assert isinstance(data["platforms"], dict)

    def test_status_contains_all_platforms(self):
        """Test that status contains expected platforms"""
        response = client.get("/api/metrics-scheduler/status")
        assert response.status_code == 200
        
        data = response.json()
        expected_platforms = ["instagram", "tiktok", "youtube", "facebook", "linkedin", "twitter"]
        
        for platform in expected_platforms:
            assert platform in data["platforms"]

    def test_platform_config_structure(self):
        """Test platform configuration structure"""
        response = client.get("/api/metrics-scheduler/status")
        assert response.status_code == 200
        
        data = response.json()
        for platform, config in data["platforms"].items():
            assert "enabled" in config
            assert "interval" in config
            assert "last_sync" in config
            assert "next_sync" in config
            assert "sync_count" in config
            assert "error_count" in config


class TestMetricsSchedulerPlatformConfig:
    """Test platform configuration updates"""

    def test_update_platform_interval(self):
        """Test updating platform sync interval"""
        response = client.put(
            "/api/metrics-scheduler/platform/instagram",
            json={"interval": "6h"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["platform"] == "instagram"
        assert data["config"]["interval"] == "6h"

    def test_update_platform_enabled(self):
        """Test enabling/disabling platform sync"""
        # Disable
        response = client.put(
            "/api/metrics-scheduler/platform/pinterest",
            json={"enabled": False}
        )
        assert response.status_code == 200
        assert response.json()["config"]["enabled"] == False
        
        # Re-enable
        response = client.put(
            "/api/metrics-scheduler/platform/pinterest",
            json={"enabled": True}
        )
        assert response.status_code == 200
        assert response.json()["config"]["enabled"] == True

    def test_update_platform_invalid_interval(self):
        """Test updating with invalid interval"""
        response = client.put(
            "/api/metrics-scheduler/platform/instagram",
            json={"interval": "invalid_interval"}
        )
        assert response.status_code == 400

    def test_update_nonexistent_platform(self):
        """Test updating non-existent platform"""
        response = client.put(
            "/api/metrics-scheduler/platform/nonexistent",
            json={"interval": "6h"}
        )
        assert response.status_code == 404


class TestMetricsSchedulerSync:
    """Test sync trigger endpoints"""

    def test_trigger_sync_all(self):
        """Test triggering sync for all platforms"""
        response = client.post("/api/metrics-scheduler/sync-now")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "platforms" in data
        assert isinstance(data["platforms"], list)
        assert len(data["platforms"]) > 0

    def test_trigger_sync_specific_platform(self):
        """Test triggering sync for specific platform"""
        response = client.post("/api/metrics-scheduler/sync-now?platform=instagram")
        assert response.status_code == 200
        
        data = response.json()
        assert "instagram" in data["platforms"]

    def test_trigger_sync_invalid_platform(self):
        """Test triggering sync for invalid platform"""
        response = client.post("/api/metrics-scheduler/sync-now?platform=invalid_platform")
        assert response.status_code == 404


class TestMetricsSchedulerHistory:
    """Test sync history endpoints"""

    def test_get_sync_history(self):
        """Test getting sync history"""
        response = client.get("/api/metrics-scheduler/history")
        assert response.status_code == 200
        
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)

    def test_get_sync_history_with_limit(self):
        """Test getting sync history with limit"""
        response = client.get("/api/metrics-scheduler/history?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["history"]) <= 5

    def test_get_sync_history_by_platform(self):
        """Test getting sync history filtered by platform"""
        response = client.get("/api/metrics-scheduler/history?platform=instagram")
        assert response.status_code == 200
        
        data = response.json()
        for entry in data["history"]:
            assert entry["platform"] == "instagram"


class TestMetricsSchedulerIntervals:
    """Test interval information endpoint"""

    def test_get_available_intervals(self):
        """Test getting available intervals"""
        response = client.get("/api/metrics-scheduler/intervals")
        assert response.status_code == 200
        
        data = response.json()
        assert "intervals" in data
        assert "recommended" in data
        
        # Check interval structure
        for interval in data["intervals"]:
            assert "value" in interval
            assert "label" in interval
            assert "seconds" in interval

    def test_interval_values(self):
        """Test that interval values are valid"""
        response = client.get("/api/metrics-scheduler/intervals")
        assert response.status_code == 200
        
        data = response.json()
        expected_values = ["hourly", "4h", "6h", "12h", "daily", "weekly"]
        
        actual_values = [i["value"] for i in data["intervals"]]
        for expected in expected_values:
            assert expected in actual_values


class TestLineGraphData:
    """Test line graph data endpoints"""

    def test_get_line_graph_single_post(self):
        """Test getting line graph data for a single post"""
        test_id = str(uuid.uuid4())
        response = client.get(f"/api/metrics-scheduler/line-graph/{test_id}")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "post_id" in data
            assert "metrics" in data

    def test_get_line_graph_with_days(self):
        """Test getting line graph with days parameter"""
        test_id = str(uuid.uuid4())
        
        for days in [7, 30, 90]:
            response = client.get(f"/api/metrics-scheduler/line-graph/{test_id}?days={days}")
            assert response.status_code in [200, 404]

    def test_get_aggregate_line_graph(self):
        """Test getting aggregated line graph data"""
        response = client.get("/api/metrics-scheduler/line-graph-aggregate")
        assert response.status_code == 200
        
        data = response.json()
        assert "metric" in data
        assert "data" in data
        assert "summary" in data
        assert isinstance(data["data"], list)

    def test_get_aggregate_line_graph_different_metrics(self):
        """Test aggregated line graph with different metrics"""
        for metric in ["views", "likes", "comments", "shares"]:
            response = client.get(f"/api/metrics-scheduler/line-graph-aggregate?metric={metric}")
            assert response.status_code == 200
            assert response.json()["metric"] == metric

    def test_get_aggregate_line_graph_aggregations(self):
        """Test aggregated line graph with different aggregation types"""
        for agg in ["sum", "avg", "max"]:
            response = client.get(f"/api/metrics-scheduler/line-graph-aggregate?aggregation={agg}")
            assert response.status_code == 200
            assert response.json()["aggregation"] == agg

    def test_compare_posts_line_graph(self):
        """Test comparing multiple posts on line graph"""
        post_ids = [str(uuid.uuid4()) for _ in range(3)]
        response = client.get(
            "/api/metrics-scheduler/compare-posts",
            params={"post_ids": post_ids, "metric": "views"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "metric" in data
        assert "posts" in data
        assert isinstance(data["posts"], list)


class TestLineGraphDataIntegrity:
    """Test line graph data integrity"""

    def test_aggregate_summary_structure(self):
        """Test aggregate summary has correct structure"""
        response = client.get("/api/metrics-scheduler/line-graph-aggregate")
        assert response.status_code == 200
        
        summary = response.json()["summary"]
        assert "total" in summary
        assert "average" in summary
        assert "min" in summary
        assert "max" in summary
        assert "trend" in summary

    def test_aggregate_data_point_structure(self):
        """Test aggregate data points have correct structure"""
        response = client.get("/api/metrics-scheduler/line-graph-aggregate")
        assert response.status_code == 200
        
        data = response.json()["data"]
        if data:
            point = data[0]
            assert "date" in point
            assert "value" in point


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
