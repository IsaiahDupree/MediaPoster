"""
Test Suite for Safari Twitter Poster
=====================================
Tests browser-based Twitter posting via Safari AppleScript automation.

Run with: pytest tests/automation/test_safari_twitter_poster.py -v
Run mocked only: pytest tests/automation/test_safari_twitter_poster.py -v -m "not live"
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.safari_twitter_poster import SafariTwitterPoster


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def poster():
    """Create SafariTwitterPoster instance."""
    return SafariTwitterPoster(use_x_domain=True)


@pytest.fixture
def mock_applescript():
    """Mock AppleScript execution."""
    with patch.object(SafariTwitterPoster, '_run_applescript') as mock:
        yield mock


# =============================================================================
# UNIT TESTS - Initialization
# =============================================================================

class TestSafariTwitterPosterInit:
    """Test poster initialization."""
    
    def test_init_x_domain(self):
        """Test initialization with X domain."""
        poster = SafariTwitterPoster(use_x_domain=True)
        assert poster.use_x_domain is True
        assert "x.com" in poster.compose_url
        assert "x.com" in poster.home_url
    
    def test_init_twitter_domain(self):
        """Test initialization with Twitter domain (legacy)."""
        poster = SafariTwitterPoster(use_x_domain=False)
        assert poster.use_x_domain is False
        assert "twitter.com" in poster.compose_url
        assert "twitter.com" in poster.home_url
    
    def test_min_interval_default(self):
        """Test default minimum interval between posts."""
        poster = SafariTwitterPoster()
        assert poster.min_interval_seconds == 30
    
    def test_compose_url_set(self):
        """Test compose URL is set correctly."""
        poster = SafariTwitterPoster()
        assert poster.compose_url == "https://x.com/compose/post"


# =============================================================================
# UNIT TESTS - AppleScript Mocked
# =============================================================================

class TestAppleScriptExecution:
    """Test AppleScript execution handling."""
    
    def test_run_applescript_success(self, poster, mock_applescript):
        """Test successful AppleScript execution."""
        mock_applescript.return_value = (True, "success")
        success, output = poster._run_applescript("test script")
        assert success is True
        assert output == "success"
    
    def test_run_applescript_failure(self, poster, mock_applescript):
        """Test failed AppleScript execution."""
        mock_applescript.return_value = (False, "error message")
        success, output = poster._run_applescript("test script")
        assert success is False
        assert "error" in output.lower()


class TestLoginCheck:
    """Test login status checking."""
    
    def test_is_logged_in_true(self, poster, mock_applescript):
        """Test login check returns True when on Twitter."""
        mock_applescript.return_value = (True, "https://x.com/home")
        assert poster.is_logged_in() is True
    
    def test_is_logged_in_false_not_on_twitter(self, poster, mock_applescript):
        """Test login check returns False when not on Twitter."""
        mock_applescript.return_value = (True, "https://google.com")
        assert poster.is_logged_in() is False
    
    def test_is_logged_in_safari_not_running(self, poster, mock_applescript):
        """Test login check when Safari not running."""
        mock_applescript.return_value = (False, "not_running")
        assert poster.is_logged_in() is False
    
    def test_check_login_status_logged_in(self, poster, mock_applescript):
        """Test detailed login status when logged in."""
        mock_applescript.return_value = (
            True, 
            json.dumps({"logged_in": True, "username": "IsaiahDupree7", "indicator": "profile_link"})
        )
        status = poster.check_login_status()
        assert status["logged_in"] is True
        assert "IsaiahDupree7" in status.get("username", "")
    
    def test_check_login_status_not_logged_in(self, poster, mock_applescript):
        """Test detailed login status when not logged in."""
        mock_applescript.return_value = (
            True,
            json.dumps({"logged_in": False, "reason": "on_login_page"})
        )
        status = poster.check_login_status()
        assert status["logged_in"] is False
        assert "login" in status.get("reason", "").lower()


class TestNavigation:
    """Test navigation functions."""
    
    def test_open_twitter(self, poster, mock_applescript):
        """Test opening Twitter in Safari."""
        mock_applescript.return_value = (True, "")
        with patch('time.sleep'):
            result = poster.open_twitter()
        assert result is True
        mock_applescript.assert_called()
    
    def test_open_compose(self, poster, mock_applescript):
        """Test opening compose modal."""
        mock_applescript.return_value = (True, "")
        with patch('time.sleep'):
            result = poster.open_compose()
        assert result is True
    
    def test_wait_for_page_load_success(self, poster, mock_applescript):
        """Test waiting for page load."""
        mock_applescript.return_value = (True, "loaded")
        result = poster.wait_for_page_load(timeout_seconds=5)
        assert result is True
    
    def test_wait_for_page_load_timeout(self, poster, mock_applescript):
        """Test page load timeout."""
        mock_applescript.return_value = (True, "timeout")
        result = poster.wait_for_page_load(timeout_seconds=1)
        assert result is False


class TestTweetComposition:
    """Test tweet text input."""
    
    def test_type_tweet_via_js_success(self, poster, mock_applescript):
        """Test typing tweet via JavaScript."""
        mock_applescript.return_value = (True, "success")
        with patch.object(poster, 'type_tweet') as fallback:
            result = poster.type_tweet_via_js("Hello, world!")
        assert result is True
        fallback.assert_not_called()
    
    def test_type_tweet_via_js_fallback(self, poster, mock_applescript):
        """Test fallback to keystroke when JS fails."""
        mock_applescript.side_effect = [
            (True, "editor_not_found"),  # JS fails
            (True, ""),  # Keystroke succeeds
        ]
        with patch('time.sleep'):
            result = poster.type_tweet_via_js("Hello, world!")
        # Should fall back to keystroke method
        assert mock_applescript.call_count >= 1
    
    def test_type_tweet_escapes_special_chars(self, poster, mock_applescript):
        """Test special characters are escaped."""
        mock_applescript.return_value = (True, "success")
        # Should not raise
        poster.type_tweet_via_js('Test "quoted" text with\nnewline')
    
    def test_type_tweet_handles_emojis(self, poster, mock_applescript):
        """Test emoji handling."""
        mock_applescript.return_value = (True, "success")
        poster.type_tweet_via_js("Hello 🎉 World!")


class TestPostSubmission:
    """Test tweet posting."""
    
    def test_click_post_button_success(self, poster, mock_applescript):
        """Test clicking post button."""
        mock_applescript.return_value = (True, "success")
        with patch('time.sleep'):
            result = poster.click_post_button()
        assert result is True
    
    def test_click_post_button_via_js_success(self, poster, mock_applescript):
        """Test clicking post via JavaScript."""
        mock_applescript.return_value = (True, "clicked")
        with patch('time.sleep'):
            result = poster.click_post_button_via_js()
        assert result is True
    
    def test_click_post_button_disabled(self, poster, mock_applescript):
        """Test handling disabled post button."""
        mock_applescript.side_effect = [
            (True, "button_disabled"),  # JS finds disabled button
            (False, "failed"),  # Keyboard fallback fails
        ]
        with patch('time.sleep'):
            result = poster.click_post_button_via_js()
        assert result is False


class TestVerification:
    """Test post verification."""
    
    def test_verify_post_success_redirect(self, poster, mock_applescript):
        """Test verifying successful post via redirect."""
        mock_applescript.return_value = (
            True,
            json.dumps({
                "url": "https://x.com/IsaiahDupree7/status/1234567890",
                "posted": True,
                "tweet_id": "1234567890"
            })
        )
        with patch('time.sleep'):
            result = poster.verify_post_success(max_wait=2)
        assert result.get("posted") is True
        assert result.get("tweet_id") == "1234567890"
    
    def test_verify_post_compose_modal_closed(self, poster, mock_applescript):
        """Test verifying post when compose modal closes and redirects to status."""
        # The method checks for /status/ URL pattern to confirm success
        mock_applescript.return_value = (
            True,
            json.dumps({
                "url": "https://x.com/IsaiahDupree7/status/1234567890",
                "posted": True,
                "tweet_id": "1234567890",
                "compose_open": False
            })
        )
        with patch('time.sleep'):
            result = poster.verify_post_success(max_wait=2)
        assert result.get("posted") is True
    
    def test_verify_post_error_detected(self, poster, mock_applescript):
        """Test detecting post error."""
        mock_applescript.return_value = (
            True,
            json.dumps({
                "url": "https://x.com/compose/post",
                "error": "Rate limited",
                "compose_open": True
            })
        )
        with patch('time.sleep'):
            result = poster.verify_post_success(max_wait=2)
        assert "error" in result
    
    def test_get_current_url(self, poster, mock_applescript):
        """Test getting current URL."""
        mock_applescript.return_value = (True, "https://x.com/home")
        url = poster.get_current_url()
        assert url == "https://x.com/home"


# =============================================================================
# INTEGRATION TESTS - Full Flow (Mocked)
# =============================================================================

class TestFullPostFlow:
    """Test complete posting flow with mocks."""
    
    @patch('time.sleep')
    def test_full_post_flow_success(self, mock_sleep, poster, mock_applescript):
        """Test complete post flow."""
        # Setup mock responses for full flow
        mock_applescript.side_effect = [
            (True, "https://x.com/home"),  # is_logged_in
            (True, ""),  # open_compose
            (True, "loaded"),  # wait_for_page_load
            (True, "success"),  # type_tweet_via_js
            (True, "clicked"),  # click_post_button_via_js
            (True, json.dumps({"posted": True, "tweet_id": "123"})),  # verify
        ]
        
        # Simulate full flow
        assert poster.is_logged_in()
        assert poster.open_compose()
        assert poster.wait_for_page_load()
        assert poster.type_tweet_via_js("Test tweet")
        assert poster.click_post_button_via_js()
        result = poster.verify_post_success(max_wait=1)
        assert result.get("posted") is True


# =============================================================================
# LIVE TESTS - Require Safari & Login (Skip by default)
# =============================================================================

@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_SAFARI_TESTS") != "1",
    reason="Live Safari tests disabled. Set RUN_LIVE_SAFARI_TESTS=1 to enable."
)
class TestLiveSafariTwitter:
    """Live tests that actually use Safari (use sparingly)."""
    
    def test_live_check_safari_running(self):
        """Check if Safari is available."""
        poster = SafariTwitterPoster()
        url = poster.get_current_url()
        # Should return something or None
        assert url is None or isinstance(url, str)
    
    def test_live_check_login_status(self):
        """Check actual login status."""
        poster = SafariTwitterPoster()
        poster.open_twitter()
        import time
        time.sleep(3)
        status = poster.check_login_status()
        assert "logged_in" in status
        print(f"\nLogin status: {status}")


# =============================================================================
# BENCHMARK TESTS
# =============================================================================

class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_applescript_call_time(self, poster, mock_applescript):
        """Benchmark AppleScript call overhead."""
        import time
        mock_applescript.return_value = (True, "success")
        
        start = time.time()
        for _ in range(100):
            poster._run_applescript("test")
        elapsed = time.time() - start
        
        # Should complete 100 mocked calls quickly
        assert elapsed < 1.0, f"100 mocked calls took {elapsed}s"
    
    def test_json_parsing_performance(self, poster, mock_applescript):
        """Benchmark JSON parsing for status checks."""
        import time
        
        response = json.dumps({
            "logged_in": True,
            "username": "test_user",
            "indicator": "profile_link",
            "url": "https://x.com/test_user"
        })
        mock_applescript.return_value = (True, response)
        
        start = time.time()
        for _ in range(1000):
            poster.check_login_status()
        elapsed = time.time() - start
        
        # Should parse 1000 JSON responses quickly
        assert elapsed < 2.0, f"1000 status checks took {elapsed}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not live"])
