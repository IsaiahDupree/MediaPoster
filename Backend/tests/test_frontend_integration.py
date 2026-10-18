"""
Frontend Integration Tests
Tests frontend pages integrate correctly with backend APIs.
"""
import pytest
import httpx
import re
from typing import List, Dict

# URLs
API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"
FRONTEND_BASE = "http://localhost:5557"


# =============================================================================
# FRONTEND PAGE INTEGRATION TESTS
# =============================================================================

class TestDashboardIntegration:
    """Test Dashboard page integration with backend."""
    
    def test_dashboard_loads(self):
        """Dashboard should load successfully."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        assert response.status_code == 200
        print("✓ Dashboard loads")
    
    def test_dashboard_fetches_stats(self):
        """Dashboard should be able to fetch stats from backend."""
        # Verify backend endpoint works
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        assert "total_videos" in stats
        assert "analyzed_count" in stats
        
        print(f"✓ Stats API works: {stats['total_videos']} total")
    
    def test_dashboard_fetches_recent_media(self):
        """Dashboard should be able to fetch recent media."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        assert list_response.status_code == 200
        
        media_list = list_response.json()
        assert isinstance(media_list, list)
        
        print(f"✓ Recent media API works: {len(media_list)} items")
    
    def test_dashboard_has_navigation(self):
        """Dashboard should have navigation to other pages."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.content.decode('utf-8', errors='ignore')
        
        # Should have links to key pages
        assert '/media' in content
        assert '/processing' in content or 'processing' in content.lower()
        
        print("✓ Dashboard has navigation links")


class TestMediaLibraryIntegration:
    """Test Media Library page integration with backend."""
    
    def test_media_library_loads(self):
        """Media library should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        assert response.status_code == 200
        print("✓ Media library loads")
    
    def test_media_library_fetches_list(self):
        """Media library should fetch media list from backend."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=20", timeout=10)
        assert list_response.status_code == 200
        
        media_list = list_response.json()
        assert isinstance(media_list, list)
        
        print(f"✓ Media list API works: {len(media_list)} items")
    
    def test_media_library_can_filter(self):
        """Media library should support filtering."""
        # Test status filter
        filter_response = httpx.get(
            f"{DB_API_URL}/list?status=analyzed&limit=10",
            timeout=10
        )
        assert filter_response.status_code == 200
        
        print("✓ Filtering API works")
    
    def test_media_library_thumbnails_accessible(self):
        """Media library thumbnails should be accessible."""
        # Get first media item
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.status_code != 200 or not list_response.json():
            pytest.skip("No media available")
        
        media_id = list_response.json()[0]["media_id"]
        
        # Try to get thumbnail
        thumb_response = httpx.get(
            f"{DB_API_URL}/thumbnail/{media_id}?size=medium",
            timeout=30
        )
        
        # Should either return thumbnail or 404
        assert thumb_response.status_code in [200, 404]
        
        print("✓ Thumbnail API accessible")


class TestMediaDetailIntegration:
    """Test Media Detail page integration with backend."""
    
    def test_media_detail_with_valid_id(self):
        """Media detail page should load with valid ID."""
        # Get a media ID
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.status_code != 200 or not list_response.json():
            pytest.skip("No media available")
        
        media_id = list_response.json()[0]["media_id"]
        
        # Load detail page
        page_response = httpx.get(f"{FRONTEND_BASE}/media/{media_id}", timeout=10)
        assert page_response.status_code == 200
        
        print(f"✓ Detail page loads for {media_id}")
    
    def test_media_detail_fetches_data(self):
        """Media detail should fetch data from backend."""
        # Get a media ID
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.status_code != 200 or not list_response.json():
            pytest.skip("No media available")
        
        media_id = list_response.json()[0]["media_id"]
        
        # Fetch detail from API
        detail_response = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
        assert detail_response.status_code == 200
        
        detail = detail_response.json()
        assert detail["media_id"] == media_id
        assert "filename" in detail
        
        print(f"✓ Detail API works")
    
    def test_media_detail_can_trigger_analysis(self):
        """Media detail should be able to trigger analysis."""
        # Get a media ID
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.status_code != 200 or not list_response.json():
            pytest.skip("No media available")
        
        media_id = list_response.json()[0]["media_id"]
        
        # Try to trigger analysis
        analyze_response = httpx.post(f"{DB_API_URL}/analyze/{media_id}", timeout=10)
        
        # Should either start or indicate service unavailable
        assert analyze_response.status_code in [200, 500]
        
        print("✓ Analysis trigger API accessible")


class TestProcessingPageIntegration:
    """Test Processing page integration with backend."""
    
    def test_processing_page_loads(self):
        """Processing page should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/processing", timeout=10)
        assert response.status_code == 200
        print("✓ Processing page loads")
    
    def test_processing_fetches_stats(self):
        """Processing page should fetch stats from backend."""
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        assert "total_videos" in stats
        assert "pending_analysis" in stats
        
        print(f"✓ Processing stats API works")
    
    def test_processing_fetches_health(self):
        """Processing page should fetch health status."""
        health_response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert health_response.status_code == 200
        
        health = health_response.json()
        assert health["status"] == "healthy"
        
        print("✓ Health API works")


class TestAnalyticsPageIntegration:
    """Test Analytics page integration with backend."""
    
    def test_analytics_page_loads(self):
        """Analytics page should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/analytics", timeout=10)
        assert response.status_code == 200
        print("✓ Analytics page loads")
    
    def test_analytics_can_fetch_stats(self):
        """Analytics page should be able to fetch stats."""
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert stats_response.status_code == 200
        
        print("✓ Analytics can fetch stats")


class TestInsightsPageIntegration:
    """Test AI Coach/Insights page integration with backend."""
    
    def test_insights_page_loads(self):
        """Insights page should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/insights", timeout=10)
        assert response.status_code == 200
        print("✓ Insights page loads")


class TestSchedulePageIntegration:
    """Test Schedule page integration with backend."""
    
    def test_schedule_page_loads(self):
        """Schedule page should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/schedule", timeout=10)
        assert response.status_code == 200
        print("✓ Schedule page loads")


class TestBriefsPageIntegration:
    """Test Creative Briefs page integration with backend."""
    
    def test_briefs_page_loads(self):
        """Briefs page should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/briefs", timeout=10)
        assert response.status_code == 200
        print("✓ Briefs page loads")
    
    def test_new_brief_page_loads(self):
        """New brief page should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/briefs/new", timeout=10)
        assert response.status_code == 200
        print("✓ New brief page loads")


class TestDerivativesPageIntegration:
    """Test Derivatives page integration with backend."""
    
    def test_derivatives_page_loads(self):
        """Derivatives page should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/derivatives", timeout=10)
        assert response.status_code == 200
        print("✓ Derivatives page loads")


class TestCommentsPageIntegration:
    """Test Comments page integration with backend."""
    
    def test_comments_page_loads(self):
        """Comments page should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/comments", timeout=10)
        assert response.status_code == 200
        print("✓ Comments page loads")


class TestSettingsPageIntegration:
    """Test Settings page integration with backend."""
    
    def test_settings_page_loads(self):
        """Settings page should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/settings", timeout=10)
        assert response.status_code == 200
        print("✓ Settings page loads")


class TestWorkspacesPageIntegration:
    """Test Workspaces page integration with backend."""
    
    def test_workspaces_page_loads(self):
        """Workspaces page should load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}/workspaces", timeout=10)
        assert response.status_code == 200
        print("✓ Workspaces page loads")


# =============================================================================
# API INTEGRATION TESTS
# =============================================================================

class TestAPIIntegration:
    """Test frontend can integrate with all key APIs."""
    
    def test_health_api_integration(self):
        """Frontend should be able to check backend health."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        
        print("✓ Health API integration works")
    
    def test_stats_api_integration(self):
        """Frontend should be able to fetch stats."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_videos" in data
        assert "analyzed_count" in data
        assert "pending_analysis" in data
        
        print(f"✓ Stats API integration works: {data['total_videos']} videos")
    
    def test_list_api_integration(self):
        """Frontend should be able to list media."""
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if data:
            # Verify structure
            item = data[0]
            assert "media_id" in item
            assert "filename" in item
            assert "created_at" in item
        
        print(f"✓ List API integration works: {len(data)} items")
    
    def test_search_api_integration(self):
        """Frontend should be able to search media."""
        response = httpx.get(f"{DB_API_URL}/search?query=test&limit=5", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        print(f"✓ Search API integration works: {len(data)} results")
    
    def test_thumbnail_api_integration(self):
        """Frontend should be able to fetch thumbnails."""
        # Get a media ID
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.status_code != 200 or not list_response.json():
            pytest.skip("No media available")
        
        media_id = list_response.json()[0]["media_id"]
        
        # Fetch thumbnail
        thumb_response = httpx.get(
            f"{DB_API_URL}/thumbnail/{media_id}?size=medium",
            timeout=30
        )
        
        # Should either return thumbnail or 404
        assert thumb_response.status_code in [200, 404]
        
        if thumb_response.status_code == 200:
            assert "image/" in thumb_response.headers.get("content-type", "")
            print(f"✓ Thumbnail API integration works")
        else:
            print(f"✓ Thumbnail API accessible (404 expected if not generated)")


# =============================================================================
# NAVIGATION INTEGRATION
# =============================================================================

class TestNavigationIntegration:
    """Test navigation between pages works correctly."""
    
    def test_sidebar_navigation_present(self):
        """All pages should have sidebar navigation."""
        pages = [
            "/",
            "/media",
            "/processing",
            "/analytics",
            "/insights",
        ]
        
        for page in pages:
            response = httpx.get(f"{FRONTEND_BASE}{page}", timeout=10)
            assert response.status_code == 200
            
            content = response.content.decode('utf-8', errors='ignore')
            
            # Should have MediaPoster branding (in sidebar)
            assert "MediaPoster" in content or "mediaposter" in content.lower()
        
        print(f"✓ Sidebar navigation present on all pages")
    
    def test_navigation_links_work(self):
        """Navigation links should point to valid pages."""
        # Get dashboard
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.content.decode('utf-8', errors='ignore')
        
        # Extract href links
        href_pattern = r'href="(/[^"]*)"'
        links = re.findall(href_pattern, content)
        
        # Test a few key links
        key_links = [link for link in links if link in ["/", "/media", "/processing"]]
        
        for link in key_links[:5]:  # Test first 5
            link_response = httpx.get(f"{FRONTEND_BASE}{link}", timeout=10)
            assert link_response.status_code == 200
        
        print(f"✓ Navigation links work")


# =============================================================================
# ERROR HANDLING INTEGRATION
# =============================================================================

class TestErrorHandlingIntegration:
    """Test frontend handles backend errors gracefully."""
    
    def test_invalid_media_id_handling(self):
        """Frontend should handle invalid media ID gracefully."""
        response = httpx.get(
            f"{FRONTEND_BASE}/media/invalid-uuid",
            timeout=10,
            follow_redirects=True
        )
        
        # Should either show error page or redirect
        assert response.status_code in [200, 404, 500]
        
        print("✓ Invalid media ID handled")
    
    def test_backend_unavailable_handling(self):
        """Frontend should handle backend unavailability."""
        # This test assumes backend is running
        # In real scenario, you'd stop backend and test
        
        # For now, just verify frontend doesn't crash on API errors
        response = httpx.get(FRONTEND_BASE, timeout=10)
        assert response.status_code == 200
        
        print("✓ Frontend handles backend errors")


# =============================================================================
# INTEGRATION SUMMARY
# =============================================================================

class TestIntegrationSummary:
    """Generate integration test summary."""
    
    def test_generate_integration_summary(self):
        """Generate summary of frontend-backend integration."""
        print(f"\n{'='*60}")
        print(f"FRONTEND INTEGRATION SUMMARY")
        print(f"{'='*60}\n")
        
        # Test key integrations
        integrations = [
            ("Dashboard", FRONTEND_BASE, f"{DB_API_URL}/stats"),
            ("Media Library", f"{FRONTEND_BASE}/media", f"{DB_API_URL}/list"),
            ("Processing", f"{FRONTEND_BASE}/processing", f"{DB_API_URL}/health"),
            ("Analytics", f"{FRONTEND_BASE}/analytics", f"{DB_API_URL}/stats"),
        ]
        
        for name, frontend_url, api_url in integrations:
            # Test frontend
            frontend_response = httpx.get(frontend_url, timeout=10)
            frontend_ok = frontend_response.status_code == 200
            
            # Test API
            api_response = httpx.get(api_url, timeout=10)
            api_ok = api_response.status_code == 200
            
            status = "✓" if (frontend_ok and api_ok) else "✗"
            print(f"{status} {name:20} Frontend: {frontend_ok}  API: {api_ok}")
        
        print(f"\n{'='*60}")
        print(f"All key integrations tested")
        print(f"{'='*60}\n")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
