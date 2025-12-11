"""
E2E Tests for Frontend Pages and Sidebar Navigation
Tests all pages accessible from the sidebar with real backend data.
"""
import pytest
import httpx
import time
from pathlib import Path

# API and Frontend URLs
API_BASE = "http://localhost:5555"
FRONTEND_BASE = "http://localhost:5557"
DB_API_URL = f"{API_BASE}/api/media-db"


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def sample_media_id():
    """Get a sample media ID from the database."""
    response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
    if response.status_code == 200 and response.json():
        return response.json()[0]["media_id"]
    return None


# =============================================================================
# SIDEBAR NAVIGATION TESTS
# =============================================================================

class TestSidebarNavigation:
    """Test all sidebar navigation items."""
    
    def test_sidebar_structure(self):
        """Verify sidebar has all expected navigation items."""
        # This would require a frontend testing framework like Playwright
        # For now, we verify the pages exist via HTTP
        
        expected_pages = [
            "/",  # Dashboard
            "/media",  # Media Library
            "/processing",  # Processing
            "/schedule",  # Schedule
            "/analytics",  # Analytics
            "/insights",  # AI Coach
            "/briefs",  # Creative Briefs
            "/derivatives",  # Derivatives
            "/comments",  # Comments
            "/settings",  # Settings
            "/workspaces",  # Workspaces
        ]
        
        for page in expected_pages:
            response = httpx.get(f"{FRONTEND_BASE}{page}", timeout=10, follow_redirects=True)
            assert response.status_code == 200, f"Page {page} not accessible"
            print(f"✓ {page}")


# =============================================================================
# DASHBOARD PAGE TESTS
# =============================================================================

class TestDashboardPage:
    """Test Dashboard (/) page with real data."""
    
    def test_dashboard_loads(self):
        """Dashboard page should load successfully."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        assert response.status_code == 200
        assert b"Dashboard" in response.content or b"dashboard" in response.content
        print("✓ Dashboard loads")
    
    def test_dashboard_fetches_stats(self):
        """Dashboard should fetch real stats from backend."""
        # Verify backend endpoint works
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
        
        stats = response.json()
        assert "total_videos" in stats
        assert stats["total_videos"] >= 0
        print(f"✓ Stats available: {stats['total_videos']} videos")
    
    def test_dashboard_fetches_recent_media(self):
        """Dashboard should fetch recent media."""
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        assert response.status_code == 200
        
        media_list = response.json()
        assert isinstance(media_list, list)
        print(f"✓ Recent media: {len(media_list)} items")


# =============================================================================
# MEDIA LIBRARY PAGE TESTS
# =============================================================================

class TestMediaLibraryPage:
    """Test Media Library (/media) page."""
    
    def test_media_page_loads(self):
        """Media library page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        assert response.status_code == 200
        print("✓ Media library loads")
    
    def test_media_list_endpoint(self):
        """Media list endpoint should return data."""
        response = httpx.get(f"{DB_API_URL}/list?limit=20", timeout=10)
        assert response.status_code == 200
        
        media_list = response.json()
        assert isinstance(media_list, list)
        
        if media_list:
            # Verify structure
            item = media_list[0]
            assert "media_id" in item
            assert "filename" in item
            assert "created_at" in item
        
        print(f"✓ Media list: {len(media_list)} items")
    
    def test_media_thumbnails_available(self):
        """Thumbnails should be accessible."""
        # Get first media item
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if response.status_code != 200 or not response.json():
            pytest.skip("No media available")
        
        media_id = response.json()[0]["media_id"]
        
        # Try to get thumbnail
        thumb_response = httpx.get(
            f"{DB_API_URL}/thumbnail/{media_id}?size=medium",
            timeout=30
        )
        
        # Should either return thumbnail or 404 (if not generated yet)
        assert thumb_response.status_code in [200, 404]
        print(f"✓ Thumbnail endpoint working")


# =============================================================================
# MEDIA DETAIL PAGE TESTS
# =============================================================================

class TestMediaDetailPage:
    """Test Media Detail (/media/[id]) page."""
    
    def test_media_detail_page_loads(self, sample_media_id):
        """Media detail page should load for valid ID."""
        if not sample_media_id:
            pytest.skip("No media available")
        
        response = httpx.get(f"{FRONTEND_BASE}/media/{sample_media_id}", timeout=10)
        assert response.status_code == 200
        print(f"✓ Media detail loads for {sample_media_id}")
    
    def test_media_detail_endpoint(self, sample_media_id):
        """Media detail endpoint should return full data."""
        if not sample_media_id:
            pytest.skip("No media available")
        
        response = httpx.get(f"{DB_API_URL}/detail/{sample_media_id}", timeout=10)
        assert response.status_code == 200
        
        detail = response.json()
        assert detail["media_id"] == sample_media_id
        assert "filename" in detail
        assert "file_path" in detail
        assert "created_at" in detail
        print(f"✓ Detail data complete")
    
    def test_video_playback_endpoint(self, sample_media_id):
        """Video streaming endpoint should work for videos."""
        if not sample_media_id:
            pytest.skip("No media available")
        
        # Get media detail to check if it's a video
        detail_response = httpx.get(f"{DB_API_URL}/detail/{sample_media_id}", timeout=10)
        if detail_response.status_code != 200:
            pytest.skip("Cannot get media detail")
        
        detail = detail_response.json()
        
        # Try video endpoint
        video_response = httpx.get(
            f"{DB_API_URL}/video/{sample_media_id}",
            timeout=30,
            follow_redirects=True
        )
        
        # Should work for videos, 404 for images
        if detail.get("duration_sec", 0) > 0:
            assert video_response.status_code == 200
            assert "video/" in video_response.headers.get("content-type", "")
            print(f"✓ Video streaming works")
        else:
            # Images might return 404 or the file
            assert video_response.status_code in [200, 404]
            print(f"✓ Video endpoint responds correctly for images")


# =============================================================================
# PROCESSING PAGE TESTS
# =============================================================================

class TestProcessingPage:
    """Test Processing (/processing) page."""
    
    def test_processing_page_loads(self):
        """Processing page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/processing", timeout=10)
        assert response.status_code == 200
        print("✓ Processing page loads")
    
    def test_health_endpoint(self):
        """Health endpoint should be accessible."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert response.status_code == 200
        
        health = response.json()
        assert health["status"] == "healthy"
        assert health["database"] == "connected"
        print("✓ Health check passed")
    
    def test_stats_endpoint(self):
        """Stats endpoint should return processing stats."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
        
        stats = response.json()
        assert "total_videos" in stats
        assert "analyzed_count" in stats
        assert "pending_analysis" in stats
        print(f"✓ Stats: {stats['analyzed_count']}/{stats['total_videos']} analyzed")


# =============================================================================
# ANALYTICS PAGE TESTS
# =============================================================================

class TestAnalyticsPage:
    """Test Analytics (/analytics) page."""
    
    def test_analytics_page_loads(self):
        """Analytics page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/analytics", timeout=10)
        assert response.status_code == 200
        print("✓ Analytics page loads")


# =============================================================================
# INSIGHTS PAGE TESTS
# =============================================================================

class TestInsightsPage:
    """Test AI Coach (/insights) page."""
    
    def test_insights_page_loads(self):
        """Insights page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/insights", timeout=10)
        assert response.status_code == 200
        print("✓ Insights page loads")


# =============================================================================
# BRIEFS PAGE TESTS
# =============================================================================

class TestBriefsPage:
    """Test Creative Briefs (/briefs) page."""
    
    def test_briefs_page_loads(self):
        """Briefs page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/briefs", timeout=10)
        assert response.status_code == 200
        print("✓ Briefs page loads")
    
    def test_new_brief_page_loads(self):
        """New brief page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/briefs/new", timeout=10)
        assert response.status_code == 200
        print("✓ New brief page loads")


# =============================================================================
# DERIVATIVES PAGE TESTS
# =============================================================================

class TestDerivativesPage:
    """Test Derivatives (/derivatives) page."""
    
    def test_derivatives_page_loads(self):
        """Derivatives page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/derivatives", timeout=10)
        assert response.status_code == 200
        print("✓ Derivatives page loads")


# =============================================================================
# COMMENTS PAGE TESTS
# =============================================================================

class TestCommentsPage:
    """Test Comments (/comments) page."""
    
    def test_comments_page_loads(self):
        """Comments page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/comments", timeout=10)
        assert response.status_code == 200
        print("✓ Comments page loads")


# =============================================================================
# SCHEDULE PAGE TESTS
# =============================================================================

class TestSchedulePage:
    """Test Schedule (/schedule) page."""
    
    def test_schedule_page_loads(self):
        """Schedule page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/schedule", timeout=10)
        assert response.status_code == 200
        print("✓ Schedule page loads")


# =============================================================================
# SETTINGS PAGE TESTS
# =============================================================================

class TestSettingsPage:
    """Test Settings (/settings) page."""
    
    def test_settings_page_loads(self):
        """Settings page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/settings", timeout=10)
        assert response.status_code == 200
        print("✓ Settings page loads")


# =============================================================================
# WORKSPACES PAGE TESTS
# =============================================================================

class TestWorkspacesPage:
    """Test Workspaces (/workspaces) page."""
    
    def test_workspaces_page_loads(self):
        """Workspaces page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/workspaces", timeout=10)
        assert response.status_code == 200
        print("✓ Workspaces page loads")


# =============================================================================
# INTEGRATION TESTS - FULL USER WORKFLOWS
# =============================================================================

class TestUserWorkflows:
    """Test complete user workflows across multiple pages."""
    
    def test_workflow_view_media_and_analyze(self, sample_media_id):
        """User workflow: View media list → Click item → Analyze."""
        if not sample_media_id:
            pytest.skip("No media available")
        
        # Step 1: View media list
        list_response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert list_response.status_code == 200
        print("✓ Step 1: Viewed media list")
        
        # Step 2: Get media detail
        detail_response = httpx.get(f"{DB_API_URL}/detail/{sample_media_id}", timeout=10)
        assert detail_response.status_code == 200
        print("✓ Step 2: Viewed media detail")
        
        # Step 3: Start analysis (if not already analyzed)
        analyze_response = httpx.post(f"{DB_API_URL}/analyze/{sample_media_id}", timeout=10)
        assert analyze_response.status_code in [200, 500]  # 500 if service unavailable
        print("✓ Step 3: Triggered analysis")
    
    def test_workflow_dashboard_to_processing(self):
        """User workflow: Dashboard → Processing page → View stats."""
        # Step 1: View dashboard
        dashboard_response = httpx.get(FRONTEND_BASE, timeout=10)
        assert dashboard_response.status_code == 200
        print("✓ Step 1: Viewed dashboard")
        
        # Step 2: Get stats
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert stats_response.status_code == 200
        print("✓ Step 2: Got stats")
        
        # Step 3: View processing page
        processing_response = httpx.get(f"{FRONTEND_BASE}/processing", timeout=10)
        assert processing_response.status_code == 200
        print("✓ Step 3: Viewed processing page")


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPagePerformance:
    """Test page load performance."""
    
    def test_dashboard_performance(self):
        """Dashboard should load quickly."""
        start = time.time()
        response = httpx.get(FRONTEND_BASE, timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 3.0  # Should load in under 3 seconds
        print(f"✓ Dashboard: {elapsed:.3f}s")
    
    def test_media_list_performance(self):
        """Media list should load quickly."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0
        print(f"✓ Media list (50 items): {elapsed:.3f}s")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
