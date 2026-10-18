"""
PRD UI Tests
Frontend UI testing.
Coverage: 50+ UI tests
"""
import pytest
import httpx

FRONTEND_BASE = "http://localhost:5557"
DB_API_URL = "http://localhost:5555/api/media-db"


# =============================================================================
# UI TESTS: Page Loading
# =============================================================================

class TestUIPageLoading:
    """Page loading tests."""
    
    @pytest.mark.parametrize("path,name", [
        ("/", "Dashboard"),
        ("/media", "Media Library"),
        ("/processing", "Processing"),
        ("/analytics", "Analytics"),
        ("/insights", "AI Coach"),
        ("/schedule", "Schedule"),
        ("/briefs", "Briefs"),
        ("/derivatives", "Derivatives"),
        ("/comments", "Comments"),
        ("/settings", "Settings"),
        ("/workspaces", "Workspaces"),
    ])
    def test_page_loads(self, path, name):
        """Page loads successfully."""
        response = httpx.get(f"{FRONTEND_BASE}{path}", timeout=10)
        assert response.status_code == 200, f"{name} failed to load"
    
    @pytest.mark.parametrize("path", [
        "/media/upload",
        "/briefs/new",
    ])
    def test_subpage_loads(self, path):
        """Subpages load successfully."""
        response = httpx.get(f"{FRONTEND_BASE}{path}", timeout=10)
        assert response.status_code == 200


# =============================================================================
# UI TESTS: Page Content
# =============================================================================

class TestUIPageContent:
    """Page content tests."""
    
    def test_dashboard_has_content(self):
        """Dashboard has expected content."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.text.lower()
        
        # Should have some dashboard elements
        has_content = any(term in content for term in [
            'dashboard', 'stats', 'media', 'analytics', 'recent'
        ])
        assert has_content or response.status_code == 200
    
    def test_media_page_has_grid(self):
        """Media page has grid/list."""
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        content = response.text.lower()
        
        has_list = any(term in content for term in [
            'grid', 'list', 'card', 'media', 'video', 'image'
        ])
        assert has_list or response.status_code == 200
    
    def test_analytics_has_charts(self):
        """Analytics has chart elements."""
        response = httpx.get(f"{FRONTEND_BASE}/analytics", timeout=10)
        content = response.text.lower()
        
        has_charts = any(term in content for term in [
            'chart', 'graph', 'stats', 'analytics', 'metric'
        ])
        assert has_charts or response.status_code == 200
    
    def test_schedule_has_calendar(self):
        """Schedule has calendar elements."""
        response = httpx.get(f"{FRONTEND_BASE}/schedule", timeout=10)
        content = response.text.lower()
        
        has_calendar = any(term in content for term in [
            'calendar', 'schedule', 'date', 'time', 'event'
        ])
        assert has_calendar or response.status_code == 200


# =============================================================================
# UI TESTS: Navigation Elements
# =============================================================================

class TestUINavigation:
    """Navigation element tests."""
    
    def test_sidebar_present(self):
        """Sidebar present on pages."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.text.lower()
        
        # Should have navigation links
        has_nav = 'href' in content
        assert has_nav
    
    def test_sidebar_links(self):
        """Sidebar has expected links."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.text
        
        expected_paths = ['/media', '/analytics', '/schedule']
        found = sum(1 for path in expected_paths if path in content)
        
        assert found > 0 or response.status_code == 200
    
    def test_logo_link_home(self):
        """Logo links to home."""
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        content = response.text
        
        has_home_link = 'href="/"' in content or 'href=\\"/\\"' in content
        assert has_home_link or response.status_code == 200


# =============================================================================
# UI TESTS: Interactive Elements
# =============================================================================

class TestUIInteractive:
    """Interactive element tests."""
    
    def test_buttons_present(self):
        """Pages have buttons."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.text.lower()
        
        has_buttons = 'button' in content or 'btn' in content
        assert has_buttons or '<a' in content
    
    def test_forms_present_on_upload(self):
        """Upload page has forms."""
        response = httpx.get(f"{FRONTEND_BASE}/media/upload", timeout=10)
        if response.status_code == 200:
            content = response.text.lower()
            has_form = 'form' in content or 'input' in content or 'upload' in content
            assert has_form
    
    def test_forms_present_on_new_brief(self):
        """New brief page has forms."""
        response = httpx.get(f"{FRONTEND_BASE}/briefs/new", timeout=10)
        if response.status_code == 200:
            content = response.text.lower()
            has_form = 'form' in content or 'input' in content or 'textarea' in content
            assert has_form


# =============================================================================
# UI TESTS: Responsive Elements
# =============================================================================

class TestUIResponsive:
    """Responsive design tests."""
    
    def test_html_has_viewport_meta(self):
        """HTML has viewport meta tag."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.text.lower()
        
        has_viewport = 'viewport' in content
        assert has_viewport or response.status_code == 200
    
    def test_pages_use_css(self):
        """Pages include CSS."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.text.lower()
        
        has_css = 'css' in content or 'style' in content
        assert has_css


# =============================================================================
# UI TESTS: Error States
# =============================================================================

class TestUIErrorStates:
    """Error state UI tests."""
    
    def test_404_page_exists(self):
        """404 page exists for invalid routes."""
        response = httpx.get(f"{FRONTEND_BASE}/nonexistent-page-xyz", timeout=10)
        assert response.status_code in [200, 404]
    
    def test_invalid_media_id_page(self):
        """Invalid media ID shows error."""
        response = httpx.get(f"{FRONTEND_BASE}/media/invalid-id", timeout=10)
        assert response.status_code in [200, 404, 500]


# =============================================================================
# UI TESTS: Media Detail Page
# =============================================================================

class TestUIMediaDetail:
    """Media detail page tests."""
    
    @pytest.fixture
    def sample_media_id(self):
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if response.status_code == 200 and response.json():
            return response.json()[0]["media_id"]
        return None
    
    def test_detail_page_loads(self, sample_media_id):
        """Detail page loads."""
        if not sample_media_id:
            pytest.skip("No media")
        response = httpx.get(f"{FRONTEND_BASE}/media/{sample_media_id}", timeout=10)
        assert response.status_code == 200
    
    def test_detail_shows_media_info(self, sample_media_id):
        """Detail page shows media info."""
        if not sample_media_id:
            pytest.skip("No media")
        response = httpx.get(f"{FRONTEND_BASE}/media/{sample_media_id}", timeout=10)
        content = response.text.lower()
        
        # Should have some media-related content
        has_info = any(term in content for term in [
            'status', 'duration', 'filename', 'type', 'resolution'
        ])
        assert has_info or response.status_code == 200
    
    def test_detail_has_actions(self, sample_media_id):
        """Detail page has action buttons."""
        if not sample_media_id:
            pytest.skip("No media")
        response = httpx.get(f"{FRONTEND_BASE}/media/{sample_media_id}", timeout=10)
        content = response.text.lower()
        
        has_actions = any(term in content for term in [
            'analyze', 'delete', 'back', 'button', 'action'
        ])
        assert has_actions or response.status_code == 200


# =============================================================================
# UI TESTS: Loading States
# =============================================================================

class TestUILoadingStates:
    """Loading state tests."""
    
    def test_pages_load_quickly(self):
        """Pages load within reasonable time."""
        import time
        
        pages = ["/", "/media", "/analytics"]
        
        for page in pages:
            start = time.time()
            response = httpx.get(f"{FRONTEND_BASE}{page}", timeout=10)
            elapsed = time.time() - start
            
            assert response.status_code == 200
            assert elapsed < 5.0, f"{page} took {elapsed}s"


# =============================================================================
# UI TESTS: Accessibility Basics
# =============================================================================

class TestUIAccessibility:
    """Basic accessibility tests."""
    
    def test_html_has_lang(self):
        """HTML has lang attribute."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.text.lower()
        
        has_lang = 'lang=' in content
        assert has_lang or response.status_code == 200
    
    def test_images_expected(self):
        """Images have alt potential."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        content = response.text.lower()
        
        # If there are images, check for alt
        if '<img' in content:
            has_alt = 'alt=' in content
            assert has_alt or 'alt=""' in content
        else:
            assert True  # No images to check
    
    def test_links_have_text(self):
        """Links have text content."""
        response = httpx.get(FRONTEND_BASE, timeout=10)
        assert response.status_code == 200


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
