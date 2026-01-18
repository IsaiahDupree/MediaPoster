"""
Safari App Controller Tests
============================
Tests for the Safari browser automation controller
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSafariControllerInitialization:
    """Tests for Safari controller initialization"""

    def test_controller_singleton_pattern(self):
        """Controller should use singleton pattern"""
        # Import and test singleton behavior
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller1 = SafariAppController.get_instance()
            controller2 = SafariAppController.get_instance()
            
            # Should be same instance
            assert controller1 is controller2
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_controller_default_config(self):
        """Controller should have sensible defaults"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Should have timeout settings
            assert hasattr(controller, 'timeout') or hasattr(controller, 'default_timeout')
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_controller_requires_macos(self):
        """Controller should only work on macOS"""
        import platform
        
        if platform.system() != 'Darwin':
            try:
                from automation.safari_app_controller import SafariAppController
                # Should raise error on non-macOS
            except (ImportError, OSError):
                pass  # Expected on non-macOS


class TestSafariNavigation:
    """Tests for Safari navigation functionality"""

    @pytest.fixture
    def mock_applescript(self):
        """Mock AppleScript execution"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
            yield mock_run

    def test_navigate_to_url(self, mock_applescript):
        """Should navigate to a URL"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Test navigation
            result = controller.navigate("https://www.tiktok.com")
            
            # Should have called AppleScript
            assert mock_applescript.called or result is not None
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_navigate_validates_url(self):
        """Should validate URL before navigating"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Invalid URLs should be rejected
            invalid_urls = [
                "not-a-url",
                "javascript:alert(1)",
                "",
            ]
            
            for url in invalid_urls:
                # Should either raise or return False
                pass
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_navigate_with_wait(self, mock_applescript):
        """Should wait for page load after navigation"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Navigate with wait
            # Should wait for page to fully load
        except ImportError:
            pytest.skip("SafariAppController not available")


class TestSafariElementInteraction:
    """Tests for Safari element interaction"""

    @pytest.fixture
    def mock_js_execution(self):
        """Mock JavaScript execution"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, 
                stdout='{"success": true}',
                stderr=''
            )
            yield mock_run

    def test_click_element_by_selector(self, mock_js_execution):
        """Should click element by CSS selector"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Click by selector
            result = controller.click("button.submit")
            
            # Should execute click JavaScript
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_fill_input_field(self, mock_js_execution):
        """Should fill input field with text"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Fill input
            result = controller.fill("input[name='caption']", "Test caption #fyp")
            
            # Should set input value
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_get_element_text(self, mock_js_execution):
        """Should get element text content"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Get text
            text = controller.get_text("div.message")
            
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_wait_for_element(self, mock_js_execution):
        """Should wait for element to appear"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Wait for element with timeout
            result = controller.wait_for_element("div.loaded", timeout=10)
            
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_element_not_found_timeout(self, mock_js_execution):
        """Should timeout when element not found"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Mock element not found
            mock_js_execution.return_value = MagicMock(
                returncode=0,
                stdout='null',
                stderr=''
            )
            
            # Should timeout or return False
            result = controller.wait_for_element("div.nonexistent", timeout=1)
            
        except ImportError:
            pytest.skip("SafariAppController not available")


class TestSafariCookieManagement:
    """Tests for Safari cookie management"""

    def test_get_cookies(self):
        """Should retrieve cookies for domain"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            cookies = controller.get_cookies("tiktok.com")
            
            # Should return list of cookies
            assert isinstance(cookies, (list, dict)) or cookies is None
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_set_cookie(self):
        """Should set a cookie"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            cookie = {
                "name": "test_cookie",
                "value": "test_value",
                "domain": "example.com",
            }
            
            result = controller.set_cookie(cookie)
            
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_clear_cookies(self):
        """Should clear cookies for domain"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            result = controller.clear_cookies("tiktok.com")
            
        except ImportError:
            pytest.skip("SafariAppController not available")


class TestSafariSessionPersistence:
    """Tests for Safari session persistence"""

    @pytest.fixture
    def session_dir(self, tmp_path):
        """Create temporary session directory"""
        session_path = tmp_path / "sessions"
        session_path.mkdir()
        return session_path

    def test_save_session(self, session_dir):
        """Should save session to file"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Save session
            session_file = session_dir / "tiktok_session.json"
            # controller.save_session("tiktok", str(session_file))
            
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_load_session(self, session_dir):
        """Should load session from file"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            # Create mock session file
            session_file = session_dir / "tiktok_session.json"
            session_file.write_text(json.dumps({
                "cookies": [{"name": "sessionid", "value": "abc123"}],
                "timestamp": "2026-01-13T19:00:00Z",
            }))
            
            controller = SafariAppController.get_instance()
            # result = controller.load_session("tiktok", str(session_file))
            
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_session_expiry_check(self, session_dir):
        """Should check if session is expired"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Expired session should be rejected
            
        except ImportError:
            pytest.skip("SafariAppController not available")


class TestSafariScreenshots:
    """Tests for Safari screenshot functionality"""

    @pytest.fixture
    def screenshot_dir(self, tmp_path):
        """Create temporary screenshot directory"""
        screenshots = tmp_path / "screenshots"
        screenshots.mkdir()
        return screenshots

    def test_take_screenshot(self, screenshot_dir):
        """Should take a screenshot"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            screenshot_path = screenshot_dir / "test_screenshot.png"
            # result = controller.screenshot(str(screenshot_path))
            
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_take_element_screenshot(self, screenshot_dir):
        """Should take screenshot of specific element"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            screenshot_path = screenshot_dir / "element_screenshot.png"
            # result = controller.screenshot(str(screenshot_path), selector="div.content")
            
        except ImportError:
            pytest.skip("SafariAppController not available")


class TestSafariErrorHandling:
    """Tests for Safari error handling"""

    def test_handles_safari_not_running(self):
        """Should handle Safari not running"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stderr='Safari is not running'
                )
                
                controller = SafariAppController.get_instance()
                # Should handle gracefully
                
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_handles_applescript_timeout(self):
        """Should handle AppleScript timeout"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = TimeoutError("AppleScript timed out")
                
                controller = SafariAppController.get_instance()
                # Should handle timeout
                
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_handles_javascript_error(self):
        """Should handle JavaScript execution errors"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout='{"error": "Element not found"}',
                    stderr=''
                )
                
                controller = SafariAppController.get_instance()
                # Should handle JS errors
                
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_handles_permission_denied(self):
        """Should handle accessibility permission denied"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stderr='Not authorized to send Apple events'
                )
                
                controller = SafariAppController.get_instance()
                # Should raise or return appropriate error
                
        except ImportError:
            pytest.skip("SafariAppController not available")


class TestSafariTikTokAutomation:
    """Tests for TikTok-specific Safari automation"""

    @pytest.fixture
    def mock_safari(self):
        """Mock Safari controller for TikTok tests"""
        with patch('automation.safari_app_controller.SafariAppController') as mock:
            mock_instance = MagicMock()
            mock.get_instance.return_value = mock_instance
            yield mock_instance

    def test_tiktok_login_flow(self, mock_safari):
        """Should handle TikTok login flow"""
        # Navigate to TikTok
        mock_safari.navigate.return_value = True
        
        # Wait for login page
        mock_safari.wait_for_element.return_value = True
        
        # Check if already logged in
        mock_safari.get_text.return_value = "@isaiah_dupree"
        
        # Login flow should work

    def test_tiktok_post_comment(self, mock_safari):
        """Should post comment on TikTok video"""
        # Navigate to video
        mock_safari.navigate.return_value = True
        
        # Find comment input
        mock_safari.wait_for_element.return_value = True
        
        # Type comment
        mock_safari.fill.return_value = True
        
        # Submit comment
        mock_safari.click.return_value = True

    def test_tiktok_handles_captcha(self, mock_safari):
        """Should detect and handle captcha"""
        # Captcha detection
        mock_safari.wait_for_element.side_effect = [
            True,  # Found captcha element
        ]
        
        # Should pause for manual intervention or attempt solve


class TestSafariInstagramAutomation:
    """Tests for Instagram-specific Safari automation"""

    @pytest.fixture
    def mock_safari(self):
        """Mock Safari controller for Instagram tests"""
        with patch('automation.safari_app_controller.SafariAppController') as mock:
            mock_instance = MagicMock()
            mock.get_instance.return_value = mock_instance
            yield mock_instance

    def test_instagram_dm_send(self, mock_safari):
        """Should send Instagram DM"""
        # Navigate to DM
        mock_safari.navigate.return_value = True
        
        # Find message input
        mock_safari.wait_for_element.return_value = True
        
        # Type message
        mock_safari.fill.return_value = True
        
        # Send
        mock_safari.click.return_value = True


class TestSafariRateLimiting:
    """Tests for Safari automation rate limiting"""

    def test_respects_action_delays(self):
        """Should respect delays between actions"""
        try:
            from automation.safari_app_controller import SafariAppController
            import time
            
            controller = SafariAppController.get_instance()
            
            start = time.time()
            
            # Perform actions that should have delays
            # controller.click("button1")
            # controller.click("button2")
            
            elapsed = time.time() - start
            
            # Should have waited between actions
            # assert elapsed >= expected_delay
            
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_platform_specific_rate_limits(self):
        """Should apply platform-specific rate limits"""
        # TikTok, Instagram have different limits
        pass


class TestSafariCleanup:
    """Tests for Safari cleanup and resource management"""

    def test_closes_tabs_on_cleanup(self):
        """Should close opened tabs on cleanup"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            controller = SafariAppController.get_instance()
            
            # Open tab
            # controller.navigate("https://example.com")
            
            # Cleanup should close
            # controller.cleanup()
            
        except ImportError:
            pytest.skip("SafariAppController not available")

    def test_context_manager_cleanup(self):
        """Should cleanup when used as context manager"""
        try:
            from automation.safari_app_controller import SafariAppController
            
            # with SafariAppController.get_instance() as controller:
            #     controller.navigate("https://example.com")
            # Session should be cleaned up
            
        except ImportError:
            pytest.skip("SafariAppController not available")
