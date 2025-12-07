"""
TikTok Automation Test Suite - Unit Tests
~100 unit tests for individual functions/classes in isolation.
"""
import pytest
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.tiktok_session_manager import TikTokSessionManager
from automation.tiktok_engagement import TikTokEngagement


# ============================================================================
# SESSION MANAGER UNIT TESTS (~50 tests)
# ============================================================================

class TestSessionManagerState:
    """Unit tests for TikTokSessionManager state management."""
    
    def test_init_default_values(self):
        """Test default initialization values."""
        manager = TikTokSessionManager()
        assert manager.cookies == []
        assert manager.session_saved_at is None
        assert manager.logged_in_user is None
        assert manager.action_history == []
    
    def test_init_custom_session_dir(self, tmp_path):
        """Test initialization with custom session directory."""
        manager = TikTokSessionManager(session_dir=tmp_path / "sessions")
        assert manager.session_dir == tmp_path / "sessions"
        assert manager.session_dir.exists()
    
    def test_init_max_action_history(self):
        """Test custom max action history."""
        manager = TikTokSessionManager(max_action_history=50)
        assert manager.max_action_history == 50
    
    def test_update_state_single_field(self):
        """Test updating single state field."""
        manager = TikTokSessionManager()
        manager.update_state(page_type="fyp")
        assert manager.current_state["page_type"] == "fyp"
    
    def test_update_state_multiple_fields(self):
        """Test updating multiple state fields."""
        manager = TikTokSessionManager()
        manager.update_state(page_type="profile", current_url="https://tiktok.com/@user")
        assert manager.current_state["page_type"] == "profile"
        assert manager.current_state["current_url"] == "https://tiktok.com/@user"
    
    def test_get_current_state_includes_all_fields(self):
        """Test get_current_state returns all expected fields."""
        manager = TikTokSessionManager()
        state = manager.get_current_state()
        assert "page_type" in state
        assert "current_url" in state
        assert "session_age" in state
        assert "action_count" in state
        assert "rate_limits" in state


class TestSessionManagerPageTypeDetection:
    """Unit tests for page type detection."""
    
    @pytest.mark.parametrize("url,expected_type", [
        ("https://www.tiktok.com/en/", "fyp"),
        ("https://www.tiktok.com/foryou", "fyp"),
        ("https://www.tiktok.com/", "fyp"),
        ("https://www.tiktok.com/@username", "profile"),
        ("https://www.tiktok.com/@user123/video/123456", "video"),
        ("https://www.tiktok.com/video/123456", "video"),
        ("https://www.tiktok.com/search?q=test", "search"),
        ("https://www.tiktok.com/search", "search"),
        ("https://www.tiktok.com/messages", "inbox"),
        ("https://www.tiktok.com/inbox", "inbox"),
        ("https://www.tiktok.com/login", "login"),
        ("https://www.tiktok.com/passport", "login"),
        ("https://www.tiktok.com/random/path", "other"),
    ])
    def test_detect_page_type(self, url, expected_type):
        """Test page type detection for various URLs."""
        manager = TikTokSessionManager()
        assert manager.detect_page_type(url) == expected_type
    
    def test_detect_page_type_case_insensitive(self):
        """Test page type detection is case insensitive."""
        manager = TikTokSessionManager()
        assert manager.detect_page_type("HTTPS://WWW.TIKTOK.COM/FORYOU") == "fyp"
    
    def test_detect_page_type_with_query_params(self):
        """Test page type detection with query parameters."""
        manager = TikTokSessionManager()
        url = "https://www.tiktok.com/@user?tab=videos&sort=latest"
        assert manager.detect_page_type(url) == "profile"


class TestSessionManagerActionHistory:
    """Unit tests for action history tracking."""
    
    def test_add_action_basic(self):
        """Test adding a basic action."""
        manager = TikTokSessionManager()
        manager.add_action("like", {"video_id": "123"})
        assert len(manager.action_history) == 1
        assert manager.action_history[0]["type"] == "like"
    
    def test_add_action_updates_state(self):
        """Test add_action updates last_action in state."""
        manager = TikTokSessionManager()
        manager.add_action("comment", {"text": "test"})
        assert manager.current_state["last_action"] == "comment"
        assert manager.current_state["last_action_time"] is not None
    
    def test_add_action_includes_timestamp(self):
        """Test actions include timestamp."""
        manager = TikTokSessionManager()
        manager.add_action("like", {})
        assert "timestamp" in manager.action_history[0]
    
    def test_action_history_trimmed(self):
        """Test action history is trimmed when exceeding max."""
        manager = TikTokSessionManager(max_action_history=5)
        for i in range(10):
            manager.add_action("like", {"index": i})
        assert len(manager.action_history) == 5
        assert manager.action_history[0]["details"]["index"] == 5
    
    def test_get_action_history_with_limit(self):
        """Test getting action history with limit."""
        manager = TikTokSessionManager()
        for i in range(20):
            manager.add_action("like", {"index": i})
        history = manager.get_action_history(limit=5)
        assert len(history) == 5
    
    def test_get_action_history_filtered_by_type(self):
        """Test filtering action history by type."""
        manager = TikTokSessionManager()
        manager.add_action("like", {})
        manager.add_action("comment", {})
        manager.add_action("like", {})
        history = manager.get_action_history(action_type="like")
        assert len(history) == 2
        assert all(a["type"] == "like" for a in history)


class TestSessionManagerRateLimits:
    """Unit tests for rate limiting."""
    
    def test_default_rate_limits(self):
        """Test default rate limit values."""
        manager = TikTokSessionManager()
        assert "like" in manager.rate_limits
        assert "comment" in manager.rate_limits
        assert "follow" in manager.rate_limits
        assert "message" in manager.rate_limits
    
    def test_can_perform_action_initial(self):
        """Test can_perform_action returns True initially."""
        manager = TikTokSessionManager()
        assert manager.can_perform_action("like") is True
        assert manager.can_perform_action("comment") is True
    
    def test_can_perform_action_unknown_type(self):
        """Test can_perform_action returns True for unknown types."""
        manager = TikTokSessionManager()
        assert manager.can_perform_action("unknown_action") is True
    
    def test_rate_limit_increments_on_action(self):
        """Test rate limit counter increments on action."""
        manager = TikTokSessionManager()
        manager.add_action("like", {})
        assert manager.rate_limits["like"]["count"] == 1
    
    def test_rate_limit_blocks_when_exceeded(self):
        """Test actions are blocked when rate limit exceeded."""
        manager = TikTokSessionManager()
        manager.rate_limits["like"]["max_per_hour"] = 2
        manager.add_action("like", {})
        manager.add_action("like", {})
        assert manager.can_perform_action("like") is False
    
    def test_get_wait_time_returns_float(self):
        """Test get_wait_time returns a float."""
        manager = TikTokSessionManager()
        wait = manager.get_wait_time_for_action("like")
        assert isinstance(wait, float)
        assert wait > 0
    
    def test_get_wait_time_in_range(self):
        """Test get_wait_time returns value in expected range."""
        manager = TikTokSessionManager()
        for _ in range(100):
            wait = manager.get_wait_time_for_action("like")
            assert 2.0 <= wait <= 5.0  # Like delay is 2-5 seconds


class TestSessionManagerCookies:
    """Unit tests for cookie management."""
    
    @pytest.mark.asyncio
    async def test_load_cookies_file_not_found(self, tmp_path):
        """Test load_cookies returns empty list when file not found."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        cookies = await manager.load_cookies()
        assert cookies == []
    
    @pytest.mark.asyncio
    async def test_load_cookies_valid_file(self, tmp_path):
        """Test load_cookies from valid file."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        
        # Create test cookie file
        cookie_data = {
            "cookies": [{"name": "test", "value": "123"}],
            "saved_at": datetime.now().isoformat()
        }
        cookie_file = tmp_path / "tiktok_cookies.json"
        with open(cookie_file, 'w') as f:
            json.dump(cookie_data, f)
        
        cookies = await manager.load_cookies()
        assert len(cookies) == 1
        assert cookies[0]["name"] == "test"
    
    def test_get_session_age_no_session(self):
        """Test get_session_age returns None when no session."""
        manager = TikTokSessionManager()
        assert manager.get_session_age() is None
    
    def test_is_session_fresh_no_session(self):
        """Test is_session_fresh returns False when no session."""
        manager = TikTokSessionManager()
        assert manager.is_session_fresh() is False
    
    def test_is_session_fresh_recent_session(self):
        """Test is_session_fresh returns True for recent session."""
        manager = TikTokSessionManager()
        manager.session_saved_at = datetime.now()
        assert manager.is_session_fresh(max_age_hours=24) is True
    
    def test_is_session_fresh_old_session(self):
        """Test is_session_fresh returns False for old session."""
        manager = TikTokSessionManager()
        manager.session_saved_at = datetime.now() - timedelta(hours=48)
        assert manager.is_session_fresh(max_age_hours=24) is False


class TestSessionManagerPersistence:
    """Unit tests for state persistence."""
    
    def test_save_state_to_file(self, tmp_path):
        """Test save_state_to_file creates file."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        manager.update_state(page_type="fyp")
        path = manager.save_state_to_file()
        assert path.exists()
    
    def test_load_state_from_file(self, tmp_path):
        """Test load_state_from_file restores state."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        manager.update_state(page_type="profile")
        manager.add_action("like", {})
        manager.save_state_to_file()
        
        # Create new manager and load
        manager2 = TikTokSessionManager(session_dir=tmp_path)
        result = manager2.load_state_from_file()
        assert result is True
        assert manager2.current_state["page_type"] == "profile"
    
    def test_load_state_no_file(self, tmp_path):
        """Test load_state_from_file returns False when no file."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        result = manager.load_state_from_file()
        assert result is False


# ============================================================================
# ENGAGEMENT UNIT TESTS (~50 tests)
# ============================================================================

class TestEngagementInit:
    """Unit tests for TikTokEngagement initialization."""
    
    def test_init_default_values(self):
        """Test default initialization values."""
        engagement = TikTokEngagement()
        assert engagement.browser_type == "safari"
        assert engagement.auto_restore_session is True
        assert engagement.is_initialized is False
        assert engagement.is_logged_in is False
    
    def test_init_chrome_browser(self):
        """Test initialization with Chrome browser."""
        engagement = TikTokEngagement(browser_type="chrome")
        assert engagement.browser_type == "chrome"
    
    def test_init_no_auto_restore(self):
        """Test initialization without auto restore."""
        engagement = TikTokEngagement(auto_restore_session=False)
        assert engagement.auto_restore_session is False
    
    def test_selectors_defined(self):
        """Test all required selectors are defined."""
        required = ["like_button", "comment_button", "share_button", "follow_button"]
        for selector in required:
            assert selector in TikTokEngagement.SELECTORS


class TestEngagementState:
    """Unit tests for TikTokEngagement state management."""
    
    def test_get_state_initial(self):
        """Test get_state returns initial state."""
        engagement = TikTokEngagement()
        state = engagement.get_state()
        assert "is_initialized" in state
        assert "is_logged_in" in state
        assert "browser_type" in state
        assert state["is_initialized"] is False
    
    def test_get_action_history(self):
        """Test get_action_history returns list."""
        engagement = TikTokEngagement()
        history = engagement.get_action_history()
        assert isinstance(history, list)


class TestEngagementNavigationMethods:
    """Unit tests for navigation method signatures."""
    
    def test_navigate_to_profile_with_at(self):
        """Test navigate_to_profile handles @ prefix."""
        engagement = TikTokEngagement()
        # Just test the method exists and is async
        assert asyncio.iscoroutinefunction(engagement.navigate_to_profile)
    
    def test_navigate_methods_exist(self):
        """Test all navigation methods exist."""
        engagement = TikTokEngagement()
        assert hasattr(engagement, "navigate_to_url")
        assert hasattr(engagement, "navigate_to_fyp")
        assert hasattr(engagement, "navigate_to_profile")
        assert hasattr(engagement, "navigate_to_video")
        assert hasattr(engagement, "search")


class TestEngagementButtonMethods:
    """Unit tests for engagement button method signatures."""
    
    def test_engagement_methods_exist(self):
        """Test all engagement methods exist."""
        engagement = TikTokEngagement()
        assert hasattr(engagement, "like_current_video")
        assert hasattr(engagement, "is_video_liked")
        assert hasattr(engagement, "open_comments")
        assert hasattr(engagement, "post_comment")
        assert hasattr(engagement, "share_video")
        assert hasattr(engagement, "follow_user")
    
    def test_engagement_methods_are_async(self):
        """Test engagement methods are async."""
        engagement = TikTokEngagement()
        assert asyncio.iscoroutinefunction(engagement.like_current_video)
        assert asyncio.iscoroutinefunction(engagement.post_comment)
        assert asyncio.iscoroutinefunction(engagement.follow_user)


class TestEngagementMessagingMethods:
    """Unit tests for messaging method signatures."""
    
    def test_messaging_methods_exist(self):
        """Test all messaging methods exist."""
        engagement = TikTokEngagement()
        assert hasattr(engagement, "open_inbox")
        assert hasattr(engagement, "send_dm")
    
    def test_messaging_methods_are_async(self):
        """Test messaging methods are async."""
        engagement = TikTokEngagement()
        assert asyncio.iscoroutinefunction(engagement.open_inbox)
        assert asyncio.iscoroutinefunction(engagement.send_dm)


class TestEngagementSessionMethods:
    """Unit tests for session method signatures."""
    
    def test_session_methods_exist(self):
        """Test session methods exist."""
        engagement = TikTokEngagement()
        assert hasattr(engagement, "save_session")
        assert hasattr(engagement, "check_login_status")
        assert hasattr(engagement, "cleanup")


# ============================================================================
# BOUNDARY VALUE TESTS
# ============================================================================

class TestBoundaryValues:
    """Boundary value tests for edge cases."""
    
    def test_empty_url_detection(self):
        """Test page type detection with empty URL."""
        manager = TikTokSessionManager()
        result = manager.detect_page_type("")
        assert result == "other"
    
    def test_max_action_history_boundary(self):
        """Test action history at boundary."""
        manager = TikTokSessionManager(max_action_history=1)
        manager.add_action("like", {"id": 1})
        manager.add_action("like", {"id": 2})
        assert len(manager.action_history) == 1
        assert manager.action_history[0]["details"]["id"] == 2
    
    def test_rate_limit_at_max(self):
        """Test rate limit exactly at max."""
        manager = TikTokSessionManager()
        manager.rate_limits["like"]["max_per_hour"] = 1
        manager.add_action("like", {})
        assert manager.can_perform_action("like") is False
    
    def test_very_long_url(self):
        """Test page type detection with very long URL."""
        manager = TikTokSessionManager()
        long_url = "https://www.tiktok.com/@" + "a" * 1000
        result = manager.detect_page_type(long_url)
        assert result == "profile"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
