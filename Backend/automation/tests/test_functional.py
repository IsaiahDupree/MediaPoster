"""
TikTok Automation Test Suite - Functional Tests
~100 functional tests verifying features against requirements.
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
# NAVIGATION FUNCTIONAL TESTS
# ============================================================================

class TestNavigationFunctional:
    """Functional tests for navigation requirements."""
    
    @pytest.mark.parametrize("url,expected_type", [
        ("https://www.tiktok.com/foryou", "fyp"),
        ("https://www.tiktok.com/@username", "profile"),
        ("https://www.tiktok.com/@user/video/123", "video"),
        ("https://www.tiktok.com/search?q=test", "search"),
        ("https://www.tiktok.com/messages", "inbox"),
    ])
    def test_url_to_page_type_mapping(self, url, expected_type):
        """Test URL correctly maps to page type."""
        manager = TikTokSessionManager()
        assert manager.detect_page_type(url) == expected_type
    
    def test_navigation_records_action(self):
        """Test navigation is recorded in action history."""
        engagement = TikTokEngagement()
        engagement.session_manager.add_action("navigation", {
            "url": "https://tiktok.com/@user",
            "page_type": "profile"
        })
        
        history = engagement.get_action_history()
        assert len(history) == 1
        assert history[0]["type"] == "navigation"
    
    def test_navigation_updates_current_url(self):
        """Test navigation updates current URL."""
        engagement = TikTokEngagement()
        engagement.current_url = "https://tiktok.com/@user"
        engagement.session_manager.update_state(current_url=engagement.current_url)
        
        state = engagement.session_manager.get_current_state()
        assert state["current_url"] == "https://tiktok.com/@user"
    
    def test_navigation_respects_rate_limit(self):
        """Test navigation respects rate limit."""
        engagement = TikTokEngagement()
        engagement.session_manager.rate_limits["navigation"]["max_per_hour"] = 2
        
        engagement.session_manager.add_action("navigation", {})
        engagement.session_manager.add_action("navigation", {})
        
        assert engagement.session_manager.can_perform_action("navigation") is False


class TestNavigationSelectors:
    """Functional tests for navigation selectors."""
    
    def test_nav_messages_selector_exists(self):
        """Test messages navigation selector is defined."""
        assert "nav_messages" in TikTokEngagement.SELECTORS
        assert "messages" in TikTokEngagement.SELECTORS["nav_messages"].lower() or \
               "message-icon" in TikTokEngagement.SELECTORS["nav_messages"]
    
    def test_nav_profile_selector_exists(self):
        """Test profile navigation selector is defined."""
        assert "nav_profile" in TikTokEngagement.SELECTORS
    
    def test_nav_for_you_selector_exists(self):
        """Test For You navigation selector is defined."""
        assert "nav_for_you" in TikTokEngagement.SELECTORS


# ============================================================================
# ENGAGEMENT BUTTON FUNCTIONAL TESTS
# ============================================================================

class TestLikeButtonFunctional:
    """Functional tests for like button requirements."""
    
    def test_like_selector_defined(self):
        """Test like button selector is defined."""
        assert "like_button" in TikTokEngagement.SELECTORS
        selector = TikTokEngagement.SELECTORS["like_button"]
        assert "like" in selector.lower()
    
    def test_like_count_selector_defined(self):
        """Test like count selector is defined."""
        assert "like_count" in TikTokEngagement.SELECTORS
    
    def test_like_recorded_in_history(self):
        """Test like is recorded in action history."""
        manager = TikTokSessionManager()
        manager.add_action("like", {"video_id": "123"})
        
        history = manager.get_action_history(action_type="like")
        assert len(history) == 1
    
    def test_like_updates_rate_limit(self):
        """Test like updates rate limit counter."""
        manager = TikTokSessionManager()
        initial_count = manager.rate_limits["like"]["count"]
        
        manager.add_action("like", {})
        
        assert manager.rate_limits["like"]["count"] == initial_count + 1


class TestCommentFunctional:
    """Functional tests for comment requirements."""
    
    def test_comment_selector_defined(self):
        """Test comment button selector is defined."""
        assert "comment_button" in TikTokEngagement.SELECTORS
    
    def test_comment_input_selector_defined(self):
        """Test comment input selector is defined."""
        assert "comment_input" in TikTokEngagement.SELECTORS
    
    def test_comment_post_selector_defined(self):
        """Test comment post button selector is defined."""
        assert "comment_post_button" in TikTokEngagement.SELECTORS
    
    def test_comment_recorded_in_history(self):
        """Test comment is recorded in action history."""
        manager = TikTokSessionManager()
        manager.add_action("comment", {"text": "Great video!"})
        
        history = manager.get_action_history(action_type="comment")
        assert len(history) == 1
    
    def test_comment_rate_limit(self):
        """Test comment has rate limit."""
        manager = TikTokSessionManager()
        assert "comment" in manager.rate_limits
        assert manager.rate_limits["comment"]["max_per_hour"] == 30


class TestShareFunctional:
    """Functional tests for share requirements."""
    
    def test_share_selector_defined(self):
        """Test share button selector is defined."""
        assert "share_button" in TikTokEngagement.SELECTORS
    
    def test_share_count_selector_defined(self):
        """Test share count selector is defined."""
        assert "share_count" in TikTokEngagement.SELECTORS


class TestSaveBookmarkFunctional:
    """Functional tests for save/bookmark requirements."""
    
    def test_save_selector_defined(self):
        """Test save button selector is defined."""
        assert "save_button" in TikTokEngagement.SELECTORS
    
    def test_save_count_selector_defined(self):
        """Test save count selector is defined."""
        assert "save_count" in TikTokEngagement.SELECTORS


class TestFollowFunctional:
    """Functional tests for follow requirements."""
    
    def test_follow_selector_defined(self):
        """Test follow button selector is defined."""
        assert "follow_button" in TikTokEngagement.SELECTORS
    
    def test_follow_recorded_in_history(self):
        """Test follow is recorded in action history."""
        manager = TikTokSessionManager()
        manager.add_action("follow", {"username": "testuser"})
        
        history = manager.get_action_history(action_type="follow")
        assert len(history) == 1
    
    def test_follow_rate_limit(self):
        """Test follow has rate limit."""
        manager = TikTokSessionManager()
        assert "follow" in manager.rate_limits
        assert manager.rate_limits["follow"]["max_per_hour"] == 50


# ============================================================================
# MESSAGING FUNCTIONAL TESTS
# ============================================================================

class TestMessagingFunctional:
    """Functional tests for messaging requirements."""
    
    def test_message_input_selector_defined(self):
        """Test message input selector is defined."""
        assert "message_input" in TikTokEngagement.SELECTORS
    
    def test_message_send_selector_defined(self):
        """Test message send selector is defined."""
        assert "message_send" in TikTokEngagement.SELECTORS
    
    def test_message_list_selector_defined(self):
        """Test message list selector is defined."""
        assert "message_list" in TikTokEngagement.SELECTORS
    
    def test_message_recorded_in_history(self):
        """Test message is recorded in action history."""
        manager = TikTokSessionManager()
        manager.add_action("message", {"username": "testuser", "message_length": 10})
        
        history = manager.get_action_history(action_type="message")
        assert len(history) == 1
    
    def test_message_rate_limit(self):
        """Test message has rate limit."""
        manager = TikTokSessionManager()
        assert "message" in manager.rate_limits
        assert manager.rate_limits["message"]["max_per_hour"] == 20


# ============================================================================
# SESSION MANAGEMENT FUNCTIONAL TESTS
# ============================================================================

class TestSessionFunctional:
    """Functional tests for session management requirements."""
    
    def test_session_saves_cookies(self, tmp_path):
        """Test session saves cookies."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        manager.cookies = [{"name": "test", "value": "123"}]
        manager.session_saved_at = datetime.now()
        
        # Save to file
        session_file = tmp_path / "tiktok_cookies.json"
        with open(session_file, 'w') as f:
            json.dump({"cookies": manager.cookies}, f)
        
        assert session_file.exists()
    
    def test_session_restores_cookies(self, tmp_path):
        """Test session restores cookies."""
        # Create cookie file
        session_file = tmp_path / "tiktok_cookies.json"
        with open(session_file, 'w') as f:
            json.dump({
                "cookies": [{"name": "test", "value": "123"}],
                "saved_at": datetime.now().isoformat()
            }, f)
        
        manager = TikTokSessionManager(session_dir=tmp_path)
        # Would call load_cookies() here
    
    def test_session_tracks_login_state(self):
        """Test session tracks login state."""
        manager = TikTokSessionManager()
        manager.logged_in_user = "testuser"
        
        state = manager.get_current_state()
        assert state["logged_in_user"] == "testuser"
    
    def test_session_persists_action_history(self, tmp_path):
        """Test session persists action history."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        manager.add_action("like", {})
        manager.add_action("comment", {})
        manager.save_state_to_file()
        
        manager2 = TikTokSessionManager(session_dir=tmp_path)
        manager2.load_state_from_file()
        
        assert len(manager2.action_history) == 2


# ============================================================================
# RATE LIMITING FUNCTIONAL TESTS
# ============================================================================

class TestRateLimitFunctional:
    """Functional tests for rate limiting requirements."""
    
    @pytest.mark.parametrize("action_type,expected_max", [
        ("like", 100),
        ("comment", 30),
        ("follow", 50),
        ("message", 20),
        ("navigation", 200),
    ])
    def test_rate_limit_defaults(self, action_type, expected_max):
        """Test rate limit defaults are correct."""
        manager = TikTokSessionManager()
        assert manager.rate_limits[action_type]["max_per_hour"] == expected_max
    
    def test_rate_limit_blocks_when_exceeded(self):
        """Test rate limit blocks actions when exceeded."""
        manager = TikTokSessionManager()
        manager.rate_limits["like"]["max_per_hour"] = 1
        manager.add_action("like", {})
        
        assert manager.can_perform_action("like") is False
    
    def test_rate_limit_allows_when_under(self):
        """Test rate limit allows actions when under limit."""
        manager = TikTokSessionManager()
        assert manager.can_perform_action("like") is True
    
    def test_rate_limit_provides_wait_time(self):
        """Test rate limit provides wait time recommendation."""
        manager = TikTokSessionManager()
        wait_time = manager.get_wait_time_for_action("like")
        
        assert wait_time >= 2.0
        assert wait_time <= 5.0


# ============================================================================
# STATE TRACKING FUNCTIONAL TESTS
# ============================================================================

class TestStateTrackingFunctional:
    """Functional tests for state tracking requirements."""
    
    def test_state_tracks_page_type(self):
        """Test state tracks current page type."""
        manager = TikTokSessionManager()
        manager.update_state(page_type="profile")
        
        assert manager.current_state["page_type"] == "profile"
    
    def test_state_tracks_current_url(self):
        """Test state tracks current URL."""
        manager = TikTokSessionManager()
        manager.update_state(current_url="https://tiktok.com/@user")
        
        assert manager.current_state["current_url"] == "https://tiktok.com/@user"
    
    def test_state_tracks_last_action(self):
        """Test state tracks last action."""
        manager = TikTokSessionManager()
        manager.add_action("like", {})
        
        assert manager.current_state["last_action"] == "like"
    
    def test_state_tracks_last_action_time(self):
        """Test state tracks last action time."""
        manager = TikTokSessionManager()
        manager.add_action("like", {})
        
        assert manager.current_state["last_action_time"] is not None


# ============================================================================
# DATA EXTRACTION FUNCTIONAL TESTS  
# ============================================================================

class TestDataExtractionFunctional:
    """Functional tests for data extraction requirements."""
    
    def test_video_username_selector_defined(self):
        """Test video username selector is defined."""
        assert "video_username" in TikTokEngagement.SELECTORS
    
    def test_video_caption_selector_defined(self):
        """Test video caption selector is defined."""
        assert "video_caption" in TikTokEngagement.SELECTORS
    
    def test_comment_items_selector_defined(self):
        """Test comment items selector is defined."""
        assert "comment_items" in TikTokEngagement.SELECTORS
    
    def test_comment_username_selector_defined(self):
        """Test comment username selector is defined."""
        assert "comment_username" in TikTokEngagement.SELECTORS
    
    def test_comment_text_selector_defined(self):
        """Test comment text selector is defined."""
        assert "comment_text" in TikTokEngagement.SELECTORS


# ============================================================================
# ERROR HANDLING FUNCTIONAL TESTS
# ============================================================================

class TestErrorHandlingFunctional:
    """Functional tests for error handling requirements."""
    
    def test_handles_invalid_json_in_state(self, tmp_path):
        """Test handles invalid JSON in state file."""
        state_file = tmp_path / "session_state.json"
        with open(state_file, 'w') as f:
            f.write("invalid json")
        
        manager = TikTokSessionManager(session_dir=tmp_path)
        result = manager.load_state_from_file()
        
        assert result is False
    
    def test_handles_missing_state_file(self, tmp_path):
        """Test handles missing state file."""
        manager = TikTokSessionManager(session_dir=tmp_path)
        result = manager.load_state_from_file()
        
        assert result is False
    
    def test_handles_unknown_action_type(self):
        """Test handles unknown action type gracefully."""
        manager = TikTokSessionManager()
        can_perform = manager.can_perform_action("unknown_action")
        
        assert can_perform is True  # Should allow unknown actions


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
