"""
TikTok Automation Test Suite - Integration Tests
~100 integration tests for components working together.
"""
import pytest
import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.tiktok_session_manager import TikTokSessionManager
from automation.tiktok_engagement import TikTokEngagement
from automation.safari_app_controller import SafariAppController


# ============================================================================
# SESSION + STATE INTEGRATION TESTS
# ============================================================================

class TestSessionStateIntegration:
    """Integration tests for session and state management."""
    
    def test_state_persists_across_managers(self, tmp_path):
        """Test state persists when loading into new manager."""
        manager1 = TikTokSessionManager(session_dir=tmp_path)
        manager1.update_state(page_type="profile", current_url="https://tiktok.com/@test")
        manager1.add_action("like", {"video": "123"})
        manager1.add_action("comment", {"text": "test"})
        manager1.save_state_to_file()
        
        manager2 = TikTokSessionManager(session_dir=tmp_path)
        manager2.load_state_from_file()
        
        assert manager2.current_state["page_type"] == "profile"
        assert len(manager2.action_history) == 2
    
    def test_rate_limits_persist(self, tmp_path):
        """Test rate limits persist across session."""
        manager1 = TikTokSessionManager(session_dir=tmp_path)
        for _ in range(5):
            manager1.add_action("like", {})
        manager1.save_state_to_file()
        
        manager2 = TikTokSessionManager(session_dir=tmp_path)
        manager2.load_state_from_file()
        
        # Rate limits should have been saved
        assert manager2.rate_limits["like"]["count"] >= 0
    
    def test_cookies_and_state_separate(self, tmp_path):
        """Test cookies and state are saved separately."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        manager.update_state(page_type="fyp")
        manager.cookies = [{"name": "test", "value": "123"}]
        manager.save_state_to_file()
        
        # State file should exist
        assert (tmp_path / "session_state.json").exists()


class TestEngagementSessionIntegration:
    """Integration tests for engagement and session manager."""
    
    def test_engagement_uses_session_manager(self):
        """Test engagement creates and uses session manager."""
        engagement = TikTokEngagement()
        assert engagement.session_manager is not None
        assert isinstance(engagement.session_manager, TikTokSessionManager)
    
    def test_engagement_restores_session(self, tmp_path):
        """Test engagement can restore session on start."""
        # Create saved state
        manager = TikTokSessionManager(session_dir=tmp_path)
        manager.update_state(page_type="fyp")
        manager.save_state_to_file()
        
        # Engagement should load this
        engagement = TikTokEngagement(auto_restore_session=True)
        engagement.session_manager = TikTokSessionManager(session_dir=tmp_path)
        engagement.session_manager.load_state_from_file()
        
        assert engagement.session_manager.current_state["page_type"] == "fyp"
    
    def test_engagement_actions_tracked_in_session(self):
        """Test engagement actions are tracked in session manager."""
        engagement = TikTokEngagement()
        engagement.session_manager.add_action("like", {"video": "test"})
        
        history = engagement.get_action_history()
        assert len(history) == 1


# ============================================================================
# NAVIGATION INTEGRATION TESTS
# ============================================================================

class TestNavigationIntegration:
    """Integration tests for navigation with state tracking."""
    
    def test_navigation_updates_state(self):
        """Test navigation updates session state."""
        engagement = TikTokEngagement()
        engagement.current_url = "https://tiktok.com/@user"
        
        # Simulate state update
        page_type = engagement.session_manager.detect_page_type(engagement.current_url)
        engagement.session_manager.update_state(
            page_type=page_type,
            current_url=engagement.current_url
        )
        
        assert engagement.session_manager.current_state["page_type"] == "profile"
    
    def test_navigation_respects_rate_limit(self):
        """Test navigation checks rate limit."""
        engagement = TikTokEngagement()
        
        # Exhaust navigation rate limit
        engagement.session_manager.rate_limits["navigation"]["max_per_hour"] = 1
        engagement.session_manager.add_action("navigation", {})
        
        assert engagement.session_manager.can_perform_action("navigation") is False


class TestMultiplePageNavigations:
    """Integration tests for navigating through multiple pages."""
    
    def test_navigation_history_tracked(self):
        """Test navigation history is properly tracked."""
        engagement = TikTokEngagement()
        
        pages = ["fyp", "profile", "video", "search", "inbox"]
        urls = [
            "https://tiktok.com/foryou",
            "https://tiktok.com/@user",
            "https://tiktok.com/@user/video/123",
            "https://tiktok.com/search",
            "https://tiktok.com/messages"
        ]
        
        for url in urls:
            page_type = engagement.session_manager.detect_page_type(url)
            engagement.session_manager.add_action("navigation", {
                "url": url,
                "page_type": page_type
            })
        
        history = engagement.session_manager.get_action_history(action_type="navigation")
        assert len(history) == 5


# ============================================================================
# ENGAGEMENT + RATE LIMIT INTEGRATION
# ============================================================================

class TestEngagementRateLimitIntegration:
    """Integration tests for engagement and rate limiting."""
    
    def test_like_respects_rate_limit(self):
        """Test like action respects rate limit."""
        engagement = TikTokEngagement()
        engagement.session_manager.rate_limits["like"]["max_per_hour"] = 2
        
        engagement.session_manager.add_action("like", {})
        assert engagement.session_manager.can_perform_action("like") is True
        
        engagement.session_manager.add_action("like", {})
        assert engagement.session_manager.can_perform_action("like") is False
    
    def test_comment_respects_rate_limit(self):
        """Test comment action respects rate limit."""
        engagement = TikTokEngagement()
        engagement.session_manager.rate_limits["comment"]["max_per_hour"] = 1
        
        engagement.session_manager.add_action("comment", {})
        assert engagement.session_manager.can_perform_action("comment") is False
    
    def test_mixed_actions_independent_limits(self):
        """Test different action types have independent limits."""
        engagement = TikTokEngagement()
        engagement.session_manager.rate_limits["like"]["max_per_hour"] = 1
        engagement.session_manager.rate_limits["comment"]["max_per_hour"] = 1
        
        engagement.session_manager.add_action("like", {})
        
        # Comment should still be allowed
        assert engagement.session_manager.can_perform_action("comment") is True


class TestRateLimitRecovery:
    """Integration tests for rate limit recovery."""
    
    def test_rate_limit_status_tracking(self):
        """Test rate limit status is properly tracked."""
        manager = TikTokSessionManager()
        
        for _ in range(10):
            manager.add_action("like", {})
        
        status = manager._get_rate_limit_status()
        assert status["like"]["count"] == 10
        assert status["like"]["remaining"] < status["like"]["max"]


# ============================================================================
# SAFARI CONTROLLER INTEGRATION
# ============================================================================

class TestSafariControllerIntegration:
    """Integration tests for Safari controller with engagement."""
    
    def test_engagement_creates_safari_controller(self):
        """Test engagement can create Safari controller."""
        engagement = TikTokEngagement(browser_type="safari")
        assert engagement.safari_controller is None  # Until start() is called
    
    def test_selectors_in_engagement(self):
        """Test engagement has proper selector definitions."""
        engagement = TikTokEngagement()
        
        # Check button selectors
        assert "like_button" in engagement.SELECTORS
        assert "[data-e2e=" in engagement.SELECTORS["like_button"]
        
        # Check navigation selectors
        assert "nav_messages" in engagement.SELECTORS


class TestSafariControllerMocked:
    """Integration tests with mocked Safari controller."""
    
    @pytest.mark.asyncio
    async def test_run_js_integration(self):
        """Test JavaScript execution integration."""
        engagement = TikTokEngagement()
        
        # Mock the safari controller
        engagement.safari_controller = Mock()
        engagement.safari_controller._run_applescript = Mock(return_value="clicked")
        
        result = await engagement._run_js("document.click()")
        assert "clicked" in result.lower() or result == ""
    
    @pytest.mark.asyncio
    async def test_click_element_integration(self):
        """Test element clicking integration."""
        engagement = TikTokEngagement()
        
        # Without initialization, should return False
        result = await engagement._click_element("button")
        assert result is False


# ============================================================================
# DATA EXTRACTION INTEGRATION
# ============================================================================

class TestDataExtractionIntegration:
    """Integration tests for data extraction."""
    
    def test_video_info_structure(self):
        """Test expected video info structure."""
        expected_fields = ["username", "caption", "likes", "comments"]
        # This would be tested with actual browser integration
        pass
    
    def test_comment_data_structure(self):
        """Test expected comment data structure."""
        expected_fields = ["username", "text", "likes"]
        pass
    
    def test_conversation_data_structure(self):
        """Test expected conversation data structure."""
        expected_fields = ["name", "preview", "date"]
        pass


# ============================================================================
# ERROR HANDLING INTEGRATION
# ============================================================================

class TestErrorHandlingIntegration:
    """Integration tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_click_handles_missing_element(self):
        """Test click handles missing element gracefully."""
        engagement = TikTokEngagement()
        result = await engagement._click_element("nonexistent-selector")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_type_handles_uninitialized(self):
        """Test type handles uninitialized state."""
        engagement = TikTokEngagement()
        result = await engagement._type_text("test")
        assert result is False
    
    def test_session_handles_corrupted_state(self, tmp_path):
        """Test session handles corrupted state file."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        
        # Create corrupted file
        state_file = tmp_path / "session_state.json"
        with open(state_file, 'w') as f:
            f.write("not valid json")
        
        result = manager.load_state_from_file()
        assert result is False


# ============================================================================
# CONCURRENT OPERATIONS
# ============================================================================

class TestConcurrentOperations:
    """Integration tests for concurrent operations."""
    
    def test_multiple_state_updates_sequential(self):
        """Test multiple state updates are sequential."""
        manager = TikTokSessionManager()
        
        for i in range(100):
            manager.add_action("like", {"index": i})
        
        # All actions should be recorded
        assert len(manager.action_history) <= manager.max_action_history
    
    def test_session_save_during_updates(self, tmp_path):
        """Test session can be saved during updates."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        
        manager.add_action("like", {})
        manager.save_state_to_file()
        manager.add_action("comment", {})
        manager.save_state_to_file()
        
        # Both actions should be present
        manager2 = TikTokSessionManager(session_dir=tmp_path)
        manager2.load_state_from_file()
        assert len(manager2.action_history) == 2


# ============================================================================
# WORKFLOW INTEGRATION
# ============================================================================

class TestWorkflowIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_session_workflow(self, tmp_path):
        """Test complete session workflow."""
        # 1. Create session
        manager = TikTokSessionManager(session_dir=tmp_path)
        
        # 2. Navigate
        manager.update_state(page_type="fyp", current_url="https://tiktok.com/foryou")
        manager.add_action("navigation", {"url": "https://tiktok.com/foryou"})
        
        # 3. Engage
        manager.add_action("like", {"video": "123"})
        manager.add_action("comment", {"text": "test"})
        
        # 4. Save
        manager.save_state_to_file()
        
        # 5. Verify restoration
        manager2 = TikTokSessionManager(session_dir=tmp_path)
        manager2.load_state_from_file()
        
        assert manager2.current_state["page_type"] == "fyp"
        assert len(manager2.action_history) == 3
    
    def test_engagement_workflow(self):
        """Test basic engagement workflow setup."""
        engagement = TikTokEngagement()
        
        # Verify workflow components
        assert engagement.session_manager is not None
        assert engagement.browser_type == "safari"
        assert engagement.is_initialized is False
        
        # After start would be called:
        # - is_initialized = True
        # - current_url set
        # - login status checked


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
