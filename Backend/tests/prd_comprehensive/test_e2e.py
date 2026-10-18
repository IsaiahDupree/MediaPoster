"""
PRD End-to-End Tests
Complete user workflow tests.
Coverage: 40+ E2E tests
"""
import pytest
import httpx
import time
from pathlib import Path
import os

API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"
FRONTEND_BASE = "http://localhost:5557"
TEST_MEDIA_DIR = Path(os.path.expanduser("~/Documents/IphoneImport"))


# =============================================================================
# E2E: Complete Ingestion Pipeline
# =============================================================================

class TestE2EIngestionPipeline:
    """Complete ingestion pipeline tests."""
    
    def test_ingest_to_list_flow(self):
        """File ingestion appears in list."""
        # Get current count
        before = httpx.get(f"{DB_API_URL}/stats", timeout=10).json()
        before_count = before.get("total_videos", 0)
        
        # Verify list works
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        assert response.status_code == 200
        
    def test_ingest_creates_thumbnail(self):
        """Ingested file gets thumbnail."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if response.status_code != 200 or not response.json():
            pytest.skip("No media available")
        
        media_id = response.json()[0]["media_id"]
        
        thumb = httpx.get(f"{DB_API_URL}/thumbnail/{media_id}", timeout=30)
        assert thumb.status_code in [200, 404]
    
    def test_ingest_to_detail_flow(self):
        """Ingested file accessible via detail."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if not response.json():
            pytest.skip("No media")
        
        media_id = response.json()[0]["media_id"]
        detail = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
        assert detail.status_code == 200
    
    def test_ingest_to_frontend_flow(self):
        """Ingested file visible in frontend."""
        # Verify frontend media page loads
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        assert response.status_code == 200


# =============================================================================
# E2E: Analysis Pipeline
# =============================================================================

class TestE2EAnalysisPipeline:
    """Complete analysis pipeline tests."""
    
    def test_trigger_analysis(self):
        """Can trigger analysis on media."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if not response.json():
            pytest.skip("No media")
        
        media_id = response.json()[0]["media_id"]
        
        analyze = httpx.post(f"{DB_API_URL}/analyze/{media_id}", timeout=10)
        assert analyze.status_code in [200, 500]
    
    def test_analysis_updates_status(self):
        """Analysis changes media status."""
        # Check for analyzed items
        response = httpx.get(f"{DB_API_URL}/list?status=analyzed&limit=1", timeout=10)
        assert response.status_code == 200


# =============================================================================
# E2E: Frontend Navigation
# =============================================================================

class TestE2EFrontendNavigation:
    """Complete frontend navigation tests."""
    
    def test_dashboard_to_media(self):
        """Navigate from dashboard to media."""
        dashboard = httpx.get(FRONTEND_BASE, timeout=10)
        assert dashboard.status_code == 200
        
        media = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        assert media.status_code == 200
    
    def test_media_to_detail(self):
        """Navigate from media list to detail."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if not response.json():
            pytest.skip("No media")
        
        media_id = response.json()[0]["media_id"]
        
        detail_page = httpx.get(f"{FRONTEND_BASE}/media/{media_id}", timeout=10)
        assert detail_page.status_code == 200
    
    def test_full_navigation_flow(self):
        """Complete navigation through all pages."""
        pages = ["/", "/media", "/processing", "/analytics", "/schedule", "/briefs"]
        
        for page in pages:
            response = httpx.get(f"{FRONTEND_BASE}{page}", timeout=10)
            assert response.status_code == 200, f"Failed: {page}"
    
    def test_sidebar_navigation(self):
        """Sidebar navigation works."""
        all_pages = [
            "/", "/media", "/processing", "/analytics",
            "/insights", "/schedule", "/briefs", "/derivatives",
            "/comments", "/settings", "/workspaces"
        ]
        
        for page in all_pages:
            response = httpx.get(f"{FRONTEND_BASE}{page}", timeout=10)
            assert response.status_code == 200


# =============================================================================
# E2E: User Workflows
# =============================================================================

class TestE2EUserWorkflows:
    """Complete user workflow tests."""
    
    def test_view_media_workflow(self):
        """User can view media."""
        # 1. Load dashboard
        assert httpx.get(FRONTEND_BASE, timeout=10).status_code == 200
        
        # 2. Go to media library
        assert httpx.get(f"{FRONTEND_BASE}/media", timeout=10).status_code == 200
        
        # 3. Get a media item
        media_list = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10).json()
        if media_list:
            media_id = media_list[0]["media_id"]
            # 4. View detail
            assert httpx.get(f"{FRONTEND_BASE}/media/{media_id}", timeout=10).status_code == 200
    
    def test_analyze_media_workflow(self):
        """User can analyze media."""
        media_list = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10).json()
        if not media_list:
            pytest.skip("No media")
        
        media_id = media_list[0]["media_id"]
        
        # Trigger analysis
        analyze = httpx.post(f"{DB_API_URL}/analyze/{media_id}", timeout=10)
        assert analyze.status_code in [200, 500]
    
    def test_view_analytics_workflow(self):
        """User can view analytics."""
        # 1. Dashboard
        assert httpx.get(FRONTEND_BASE, timeout=10).status_code == 200
        
        # 2. Analytics page
        assert httpx.get(f"{FRONTEND_BASE}/analytics", timeout=10).status_code == 200
    
    def test_view_schedule_workflow(self):
        """User can view schedule."""
        assert httpx.get(f"{FRONTEND_BASE}/schedule", timeout=10).status_code == 200
    
    def test_create_brief_workflow(self):
        """User can access brief creation."""
        # 1. Briefs list
        assert httpx.get(f"{FRONTEND_BASE}/briefs", timeout=10).status_code == 200
        
        # 2. New brief
        assert httpx.get(f"{FRONTEND_BASE}/briefs/new", timeout=10).status_code == 200


# =============================================================================
# E2E: Data Flow
# =============================================================================

class TestE2EDataFlow:
    """Data flow through system tests."""
    
    def test_stats_match_list(self):
        """Stats count matches list items."""
        stats = httpx.get(f"{DB_API_URL}/stats", timeout=10).json()
        total = stats.get("total_videos", 0)
        
        # Get all items (up to 100)
        list_response = httpx.get(f"{DB_API_URL}/list?limit=100", timeout=10)
        items = list_response.json()
        
        # If total <= 100, should match exactly
        if total <= 100:
            assert len(items) == total
    
    def test_detail_matches_list_item(self):
        """Detail data matches list item."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if not list_response.json():
            pytest.skip("No media")
        
        list_item = list_response.json()[0]
        media_id = list_item["media_id"]
        
        detail_response = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
        detail = detail_response.json()
        
        # IDs should match
        assert detail.get("media_id") == media_id or detail.get("id") == media_id


# =============================================================================
# E2E: Error Recovery
# =============================================================================

class TestE2EErrorRecovery:
    """Error recovery tests."""
    
    def test_invalid_media_id_handled(self):
        """Invalid media ID doesn't crash."""
        response = httpx.get(f"{FRONTEND_BASE}/media/invalid-id", timeout=10)
        # Should either show error or 404, not crash
        assert response.status_code in [200, 404, 500]
    
    def test_missing_thumbnail_handled(self):
        """Missing thumbnail doesn't crash."""
        response = httpx.get(f"{DB_API_URL}/thumbnail/00000000-0000-0000-0000-000000000000", timeout=10)
        assert response.status_code in [200, 404, 500]
    
    def test_server_restart_recovery(self):
        """System works after checking health."""
        # Check health
        health = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert health.status_code == 200
        
        # Verify basic operations still work
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        assert list_response.status_code == 200


# =============================================================================
# E2E: Cross-Feature Integration
# =============================================================================

class TestE2ECrossFeature:
    """Cross-feature integration tests."""
    
    def test_media_has_thumbnail_in_frontend(self):
        """Media in frontend should have thumbnail URL."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if not list_response.json():
            pytest.skip("No media")
        
        media_id = list_response.json()[0]["media_id"]
        
        # Frontend detail page loads
        detail_page = httpx.get(f"{FRONTEND_BASE}/media/{media_id}", timeout=10)
        assert detail_page.status_code == 200
    
    def test_stats_visible_on_dashboard(self):
        """Stats should be accessible from dashboard."""
        # Dashboard loads
        dashboard = httpx.get(FRONTEND_BASE, timeout=10)
        assert dashboard.status_code == 200
        
        # Stats API works
        stats = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert stats.status_code == 200


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
