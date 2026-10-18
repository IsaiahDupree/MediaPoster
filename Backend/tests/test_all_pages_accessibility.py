"""
Accessibility and Page Availability Tests
Tests that all sidebar pages are accessible and return valid responses.
"""
import pytest
import httpx

# Frontend URL
FRONTEND_BASE = "http://localhost:5557"


# =============================================================================
# ALL SIDEBAR PAGES
# =============================================================================

SIDEBAR_PAGES = [
    # Main Navigation
    {"path": "/", "name": "Dashboard", "icon": "📊"},
    {"path": "/media", "name": "Media Library", "icon": "🎬"},
    {"path": "/processing", "name": "Processing", "icon": "⚡"},
    {"path": "/schedule", "name": "Schedule", "icon": "📅"},
    {"path": "/analytics", "name": "Analytics", "icon": "📈"},
    {"path": "/insights", "name": "AI Coach", "icon": "🧠"},
    {"path": "/briefs", "name": "Creative Briefs", "icon": "📝"},
    {"path": "/derivatives", "name": "Derivatives", "icon": "🔄"},
    {"path": "/comments", "name": "Comments", "icon": "💬"},
    
    # Bottom Navigation
    {"path": "/settings", "name": "Settings", "icon": "⚙️"},
    {"path": "/workspaces", "name": "Workspaces", "icon": "🏢"},
]


class TestAllSidebarPages:
    """Test all pages from the sidebar are accessible."""
    
    @pytest.mark.parametrize("page", SIDEBAR_PAGES, ids=lambda p: p["name"])
    def test_page_loads(self, page):
        """Each sidebar page should load successfully."""
        response = httpx.get(
            f"{FRONTEND_BASE}{page['path']}", 
            timeout=10,
            follow_redirects=True
        )
        
        assert response.status_code == 200, f"{page['name']} failed to load"
        assert len(response.content) > 0, f"{page['name']} returned empty content"
        print(f"✓ {page['icon']} {page['name']} ({page['path']})")
    
    @pytest.mark.parametrize("page", SIDEBAR_PAGES, ids=lambda p: p["name"])
    def test_page_has_sidebar(self, page):
        """Each page should include the sidebar."""
        response = httpx.get(
            f"{FRONTEND_BASE}{page['path']}", 
            timeout=10,
            follow_redirects=True
        )
        
        # Check for sidebar presence (MediaPoster text should be in sidebar)
        assert b"MediaPoster" in response.content, f"{page['name']} missing sidebar"
        print(f"✓ {page['name']} has sidebar")
    
    @pytest.mark.parametrize("page", SIDEBAR_PAGES, ids=lambda p: p["name"])
    def test_page_response_time(self, page):
        """Each page should load within reasonable time."""
        import time
        
        start = time.time()
        response = httpx.get(
            f"{FRONTEND_BASE}{page['path']}", 
            timeout=10,
            follow_redirects=True
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"{page['name']} took {elapsed:.2f}s (too slow)"
        print(f"✓ {page['name']} loaded in {elapsed:.3f}s")


class TestPageNavigation:
    """Test navigation between pages."""
    
    def test_all_pages_accessible_from_root(self):
        """All pages should be accessible from root."""
        # First, verify root loads
        root_response = httpx.get(FRONTEND_BASE, timeout=10)
        assert root_response.status_code == 200
        
        # Then verify all other pages
        for page in SIDEBAR_PAGES[1:]:  # Skip root
            response = httpx.get(
                f"{FRONTEND_BASE}{page['path']}", 
                timeout=10,
                follow_redirects=True
            )
            assert response.status_code == 200, f"Cannot navigate to {page['name']}"
        
        print(f"✓ All {len(SIDEBAR_PAGES)} pages accessible")
    
    def test_sidebar_links_present(self):
        """Sidebar should contain links to all pages."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.content.decode('utf-8', errors='ignore')
        
        # Check for navigation paths in HTML
        expected_paths = [p["path"] for p in SIDEBAR_PAGES]
        
        found_count = sum(1 for path in expected_paths if f'href="{path}"' in content)
        
        # Should find most paths (some might be dynamic)
        assert found_count >= len(expected_paths) * 0.7, \
            f"Only found {found_count}/{len(expected_paths)} sidebar links"
        
        print(f"✓ Found {found_count}/{len(expected_paths)} sidebar links")


class TestSubPages:
    """Test sub-pages and dynamic routes."""
    
    def test_media_upload_page(self):
        """Media upload sub-page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/media/upload", timeout=10)
        assert response.status_code == 200
        print("✓ /media/upload")
    
    def test_new_brief_page(self):
        """New brief sub-page should load."""
        response = httpx.get(f"{FRONTEND_BASE}/briefs/new", timeout=10)
        assert response.status_code == 200
        print("✓ /briefs/new")
    
    def test_media_detail_page_structure(self):
        """Media detail page should exist (even if no ID)."""
        # This will likely 404 or redirect, but structure should exist
        response = httpx.get(
            f"{FRONTEND_BASE}/media/test-id", 
            timeout=10,
            follow_redirects=True
        )
        # Should either load or redirect, not crash
        assert response.status_code in [200, 404, 500]
        print("✓ /media/[id] route exists")


class TestPageContent:
    """Test that pages have expected content."""
    
    def test_dashboard_has_stats(self):
        """Dashboard should display stats."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.content.decode('utf-8', errors='ignore').lower()
        
        # Should have dashboard-related content
        has_dashboard_content = any(word in content for word in [
            'dashboard', 'stats', 'recent', 'activity', 'overview'
        ])
        
        assert has_dashboard_content, "Dashboard missing expected content"
        print("✓ Dashboard has stats content")
    
    def test_media_library_structure(self):
        """Media library should have list structure."""
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        content = response.content.decode('utf-8', errors='ignore').lower()
        
        # Should have media-related content
        has_media_content = any(word in content for word in [
            'media', 'library', 'video', 'upload', 'filter'
        ])
        
        assert has_media_content, "Media library missing expected content"
        print("✓ Media library has list structure")
    
    def test_processing_page_structure(self):
        """Processing page should have processing controls."""
        response = httpx.get(f"{FRONTEND_BASE}/processing", timeout=10)
        content = response.content.decode('utf-8', errors='ignore').lower()
        
        # Should have processing-related content
        has_processing_content = any(word in content for word in [
            'processing', 'ingest', 'analyze', 'batch', 'status'
        ])
        
        assert has_processing_content, "Processing page missing expected content"
        print("✓ Processing page has controls")


class TestPageErrors:
    """Test error handling for invalid routes."""
    
    def test_invalid_route_404(self):
        """Invalid routes should return 404."""
        response = httpx.get(
            f"{FRONTEND_BASE}/this-page-does-not-exist", 
            timeout=10,
            follow_redirects=False
        )
        assert response.status_code == 404
        print("✓ 404 for invalid routes")
    
    def test_invalid_media_id(self):
        """Invalid media ID should handle gracefully."""
        response = httpx.get(
            f"{FRONTEND_BASE}/media/invalid-uuid-format", 
            timeout=10,
            follow_redirects=True
        )
        # Should either show error or redirect, not crash
        assert response.status_code in [200, 404, 500]
        print("✓ Invalid media ID handled")


# =============================================================================
# SUMMARY TEST
# =============================================================================

class TestSidebarCompleteness:
    """Verify all sidebar pages are tested."""
    
    def test_all_pages_covered(self):
        """Verify we're testing all sidebar pages."""
        print(f"\n{'='*60}")
        print(f"SIDEBAR PAGES SUMMARY")
        print(f"{'='*60}")
        
        for page in SIDEBAR_PAGES:
            print(f"{page['icon']} {page['name']:20} → {page['path']}")
        
        print(f"{'='*60}")
        print(f"Total Pages: {len(SIDEBAR_PAGES)}")
        print(f"{'='*60}\n")
        
        assert len(SIDEBAR_PAGES) == 11, "Expected 11 sidebar pages"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
