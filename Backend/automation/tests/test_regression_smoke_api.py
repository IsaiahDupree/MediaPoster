"""
TikTok Automation Test Suite - Regression, Smoke & API Tests
~100 additional tests for regression, smoke testing, and API validation.
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.tiktok_session_manager import TikTokSessionManager
from automation.tiktok_engagement import TikTokEngagement


# ============================================================================
# SMOKE TESTS - Quick "does it run" checks
# ============================================================================

class TestSmoke:
    """Smoke tests - quick sanity checks."""
    
    def test_session_manager_imports(self):
        """Smoke: TikTokSessionManager imports correctly."""
        from automation.tiktok_session_manager import TikTokSessionManager
        assert TikTokSessionManager is not None
    
    def test_engagement_imports(self):
        """Smoke: TikTokEngagement imports correctly."""
        from automation.tiktok_engagement import TikTokEngagement
        assert TikTokEngagement is not None
    
    def test_safari_controller_imports(self):
        """Smoke: SafariAppController imports correctly."""
        from automation.safari_app_controller import SafariAppController
        assert SafariAppController is not None
    
    def test_session_manager_creates(self):
        """Smoke: TikTokSessionManager creates successfully."""
        manager = TikTokSessionManager()
        assert manager is not None
    
    def test_engagement_creates(self):
        """Smoke: TikTokEngagement creates successfully."""
        engagement = TikTokEngagement()
        assert engagement is not None
    
    def test_session_manager_basic_ops(self):
        """Smoke: Session manager basic operations work."""
        manager = TikTokSessionManager()
        manager.update_state(page_type="fyp")
        manager.add_action("like", {})
        state = manager.get_current_state()
        assert state is not None
    
    def test_engagement_basic_ops(self):
        """Smoke: Engagement basic operations work."""
        engagement = TikTokEngagement()
        state = engagement.get_state()
        history = engagement.get_action_history()
        assert state is not None
        assert isinstance(history, list)
    
    def test_selectors_not_empty(self):
        """Smoke: Selectors are defined."""
        assert len(TikTokEngagement.SELECTORS) > 0
    
    def test_rate_limits_defined(self):
        """Smoke: Rate limits are defined."""
        manager = TikTokSessionManager()
        assert len(manager.rate_limits) > 0


# ============================================================================
# SANITY TESTS - Specific functionality checks
# ============================================================================

class TestSanity:
    """Sanity tests for specific new/changed functionality."""
    
    def test_page_type_detection_works(self):
        """Sanity: Page type detection works."""
        manager = TikTokSessionManager()
        result = manager.detect_page_type("https://tiktok.com/foryou")
        assert result == "fyp"
    
    def test_action_history_works(self):
        """Sanity: Action history recording works."""
        manager = TikTokSessionManager()
        manager.add_action("test", {"data": "value"})
        assert len(manager.action_history) == 1
    
    def test_rate_limit_check_works(self):
        """Sanity: Rate limit checking works."""
        manager = TikTokSessionManager()
        result = manager.can_perform_action("like")
        assert isinstance(result, bool)
    
    def test_state_update_works(self):
        """Sanity: State update works."""
        manager = TikTokSessionManager()
        manager.update_state(page_type="test")
        assert manager.current_state["page_type"] == "test"
    
    def test_wait_time_calculation_works(self):
        """Sanity: Wait time calculation works."""
        manager = TikTokSessionManager()
        wait = manager.get_wait_time_for_action("like")
        assert wait > 0


# ============================================================================
# REGRESSION TESTS - Ensure existing behavior not broken
# ============================================================================

class TestRegressionSessionManager:
    """Regression tests for session manager."""
    
    def test_regression_init_not_logged_in(self):
        """Regression: New session starts not logged in."""
        manager = TikTokSessionManager()
        assert manager.logged_in_user is None
    
    def test_regression_init_empty_cookies(self):
        """Regression: New session starts with empty cookies."""
        manager = TikTokSessionManager()
        assert manager.cookies == []
    
    def test_regression_init_empty_history(self):
        """Regression: New session starts with empty history."""
        manager = TikTokSessionManager()
        assert manager.action_history == []
    
    def test_regression_page_type_unknown_url(self):
        """Regression: Unknown URL returns 'other' page type."""
        manager = TikTokSessionManager()
        assert manager.detect_page_type("https://example.com") == "other"
    
    def test_regression_action_has_timestamp(self):
        """Regression: Actions include timestamp."""
        manager = TikTokSessionManager()
        manager.add_action("like", {})
        assert "timestamp" in manager.action_history[0]
    
    def test_regression_history_trimmed_to_max(self):
        """Regression: History is trimmed when exceeding max."""
        manager = TikTokSessionManager(max_action_history=5)
        for i in range(10):
            manager.add_action("like", {"i": i})
        assert len(manager.action_history) == 5
    
    def test_regression_session_age_none_initially(self):
        """Regression: Session age is None initially."""
        manager = TikTokSessionManager()
        assert manager.get_session_age() is None


class TestRegressionEngagement:
    """Regression tests for engagement."""
    
    def test_regression_init_not_initialized(self):
        """Regression: New engagement starts not initialized."""
        engagement = TikTokEngagement()
        assert engagement.is_initialized is False
    
    def test_regression_init_not_logged_in(self):
        """Regression: New engagement starts not logged in."""
        engagement = TikTokEngagement()
        assert engagement.is_logged_in is False
    
    def test_regression_init_empty_url(self):
        """Regression: New engagement starts with empty URL."""
        engagement = TikTokEngagement()
        assert engagement.current_url == ""
    
    def test_regression_has_session_manager(self):
        """Regression: Engagement has session manager."""
        engagement = TikTokEngagement()
        assert engagement.session_manager is not None
    
    def test_regression_default_browser_safari(self):
        """Regression: Default browser is Safari."""
        engagement = TikTokEngagement()
        assert engagement.browser_type == "safari"


# ============================================================================
# API TESTS - Validate method signatures and return types
# ============================================================================

class TestAPISessionManager:
    """API tests for session manager interface."""
    
    def test_api_update_state_accepts_kwargs(self):
        """API: update_state accepts keyword arguments."""
        manager = TikTokSessionManager()
        manager.update_state(page_type="fyp", current_url="https://test.com")
    
    def test_api_get_current_state_returns_dict(self):
        """API: get_current_state returns dict."""
        manager = TikTokSessionManager()
        result = manager.get_current_state()
        assert isinstance(result, dict)
    
    def test_api_detect_page_type_returns_str(self):
        """API: detect_page_type returns string."""
        manager = TikTokSessionManager()
        result = manager.detect_page_type("https://tiktok.com")
        assert isinstance(result, str)
    
    def test_api_add_action_accepts_details(self):
        """API: add_action accepts action type and details."""
        manager = TikTokSessionManager()
        manager.add_action("like", {"video_id": "123"})
    
    def test_api_get_action_history_accepts_params(self):
        """API: get_action_history accepts filter parameters."""
        manager = TikTokSessionManager()
        manager.get_action_history(action_type="like", limit=10)
    
    def test_api_can_perform_action_returns_bool(self):
        """API: can_perform_action returns boolean."""
        manager = TikTokSessionManager()
        result = manager.can_perform_action("like")
        assert isinstance(result, bool)
    
    def test_api_get_wait_time_returns_float(self):
        """API: get_wait_time_for_action returns float."""
        manager = TikTokSessionManager()
        result = manager.get_wait_time_for_action("like")
        assert isinstance(result, float)
    
    def test_api_save_state_returns_path(self, tmp_path):
        """API: save_state_to_file returns Path."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        result = manager.save_state_to_file()
        assert isinstance(result, Path)
    
    def test_api_load_state_returns_bool(self, tmp_path):
        """API: load_state_from_file returns bool."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        result = manager.load_state_from_file()
        assert isinstance(result, bool)


class TestAPIEngagement:
    """API tests for engagement interface."""
    
    def test_api_get_state_returns_dict(self):
        """API: get_state returns dict."""
        engagement = TikTokEngagement()
        result = engagement.get_state()
        assert isinstance(result, dict)
    
    def test_api_get_action_history_returns_list(self):
        """API: get_action_history returns list."""
        engagement = TikTokEngagement()
        result = engagement.get_action_history()
        assert isinstance(result, list)
    
    def test_api_navigate_methods_are_async(self):
        """API: Navigate methods are coroutines."""
        engagement = TikTokEngagement()
        assert asyncio.iscoroutinefunction(engagement.navigate_to_url)
        assert asyncio.iscoroutinefunction(engagement.navigate_to_fyp)
        assert asyncio.iscoroutinefunction(engagement.navigate_to_profile)
        assert asyncio.iscoroutinefunction(engagement.navigate_to_video)
        assert asyncio.iscoroutinefunction(engagement.search)
    
    def test_api_engagement_methods_are_async(self):
        """API: Engagement methods are coroutines."""
        engagement = TikTokEngagement()
        assert asyncio.iscoroutinefunction(engagement.like_current_video)
        assert asyncio.iscoroutinefunction(engagement.is_video_liked)
        assert asyncio.iscoroutinefunction(engagement.open_comments)
        assert asyncio.iscoroutinefunction(engagement.post_comment)
        assert asyncio.iscoroutinefunction(engagement.share_video)
        assert asyncio.iscoroutinefunction(engagement.follow_user)
    
    def test_api_messaging_methods_are_async(self):
        """API: Messaging methods are coroutines."""
        engagement = TikTokEngagement()
        assert asyncio.iscoroutinefunction(engagement.open_inbox)
        assert asyncio.iscoroutinefunction(engagement.send_dm)
    
    def test_api_session_methods_are_async(self):
        """API: Session methods are coroutines."""
        engagement = TikTokEngagement()
        assert asyncio.iscoroutinefunction(engagement.save_session)
        assert asyncio.iscoroutinefunction(engagement.check_login_status)
        assert asyncio.iscoroutinefunction(engagement.cleanup)


# ============================================================================
# DATABASE TESTS - Data integrity
# ============================================================================

class TestDataIntegrity:
    """Tests for data integrity."""
    
    def test_action_data_preserved(self):
        """Test action data is preserved correctly."""
        manager = TikTokSessionManager()
        original_data = {"video_id": "123", "timestamp": "2024-01-01"}
        manager.add_action("like", original_data)
        
        history = manager.get_action_history()
        assert history[0]["details"]["video_id"] == "123"
    
    def test_state_data_preserved(self, tmp_path):
        """Test state data is preserved across save/load."""
        manager1 = TikTokSessionManager(session_dir=tmp_path)
        manager1.update_state(page_type="profile", current_url="https://test.com")
        manager1.save_state_to_file()
        
        manager2 = TikTokSessionManager(session_dir=tmp_path)
        manager2.load_state_from_file()
        
        assert manager2.current_state["page_type"] == "profile"
        assert manager2.current_state["current_url"] == "https://test.com"
    
    def test_history_order_preserved(self):
        """Test action history order is preserved."""
        manager = TikTokSessionManager()
        for i in range(5):
            manager.add_action("like", {"index": i})
        
        history = manager.get_action_history()
        for i, action in enumerate(history):
            assert action["details"]["index"] == i


# ============================================================================
# COMPATIBILITY TESTS
# ============================================================================

class TestCompatibility:
    """Tests for compatibility scenarios."""
    
    def test_safari_browser_type(self):
        """Test Safari browser type is supported."""
        engagement = TikTokEngagement(browser_type="safari")
        assert engagement.browser_type == "safari"
    
    def test_chrome_browser_type(self):
        """Test Chrome browser type is supported."""
        engagement = TikTokEngagement(browser_type="chrome")
        assert engagement.browser_type == "chrome"
    
    def test_custom_session_dir(self, tmp_path):
        """Test custom session directory is supported."""
        custom_dir = tmp_path / "custom_sessions"
        manager = TikTokSessionManager(session_dir=custom_dir)
        assert manager.session_dir == custom_dir


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

class TestConfiguration:
    """Tests for configuration options."""
    
    def test_max_action_history_configurable(self):
        """Test max action history is configurable."""
        manager = TikTokSessionManager(max_action_history=25)
        assert manager.max_action_history == 25
    
    def test_auto_restore_session_configurable(self):
        """Test auto restore session is configurable."""
        engagement = TikTokEngagement(auto_restore_session=False)
        assert engagement.auto_restore_session is False
    
    def test_default_max_action_history(self):
        """Test default max action history."""
        manager = TikTokSessionManager()
        assert manager.max_action_history == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
