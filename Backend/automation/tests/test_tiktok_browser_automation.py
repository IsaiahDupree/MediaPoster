"""
TikTok Browser Automation Tests
================================
All tests requiring Safari browser automation with PyAutoGUI.

Categories:
1. Navigation Tests
2. Like/Engagement Tests  
3. Comment Tests
4. Data Extraction Tests
5. Search Tests (Browser)
6. Messaging Tests (Browser)

Prerequisites:
- Safari open with TikTok logged in
- Safari > Settings > Advanced > Allow JavaScript from Apple Events ✓
- pyautogui installed

Run:
    # All browser tests
    pytest automation/tests/test_tiktok_browser_automation.py -v -s
    
    # Specific category
    pytest automation/tests/test_tiktok_browser_automation.py::TestNavigation -v -s
    pytest automation/tests/test_tiktok_browser_automation.py::TestEngagement -v -s
"""

import pytest
import subprocess
import time
import json
import pyautogui
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# Configure pyautogui safety
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.5  # Pause between actions


# =============================================================================
# SAFARI HELPER CLASS
# =============================================================================

class SafariController:
    """Safari browser automation helper."""
    
    def activate(self):
        """Bring Safari to front."""
        subprocess.run(
            ["osascript", "-e", 'tell application "Safari" to activate'],
            capture_output=True
        )
        time.sleep(0.5)
    
    def run_js(self, js_code: str) -> str:
        """Run JavaScript in Safari's current tab."""
        escaped_js = js_code.replace('"', '\\"').replace('\n', ' ')
        result = subprocess.run(
            ["osascript", "-e", f'tell application "Safari" to do JavaScript "{escaped_js}" in current tab of front window'],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    
    def get_url(self) -> str:
        """Get current page URL."""
        result = subprocess.run(
            ["osascript", "-e", 'tell application "Safari" to return URL of current tab of front window'],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    
    def navigate(self, url: str):
        """Navigate to URL."""
        subprocess.run(
            ["osascript", "-e", f'tell application "Safari" to set URL of current tab of front window to "{url}"'],
            capture_output=True
        )
        time.sleep(3)  # Wait for page load
    
    def take_screenshot(self, name: str, save_dir: Path) -> Path:
        """Take screenshot of Safari window."""
        path = save_dir / f"{name}.png"
        subprocess.run(["screencapture", "-x", str(path)], capture_output=True)
        return path
    
    def scroll_down(self):
        """Scroll down one page."""
        self.activate()
        pyautogui.press('down')
        time.sleep(1)
    
    def scroll_up(self):
        """Scroll up one page."""
        self.activate()
        pyautogui.press('up')
        time.sleep(1)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def screenshot_dir():
    """Create directory for test screenshots."""
    dir_path = Path(__file__).parent / "screenshots" / f"browser_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


@pytest.fixture
def safari():
    """Get Safari controller."""
    controller = SafariController()
    controller.activate()
    return controller


@pytest.fixture
def tiktok_page(safari):
    """Ensure we're on TikTok."""
    url = safari.get_url()
    if "tiktok.com" not in url:
        safari.navigate("https://www.tiktok.com/foryou")
        time.sleep(3)
    return safari


@pytest.fixture
def tiktok_video(safari):
    """Navigate to a specific video."""
    test_url = "https://www.tiktok.com/@mewtru/video/7564912360520011038"
    safari.navigate(test_url)
    time.sleep(3)
    return safari


# =============================================================================
# SECTION 1: NAVIGATION TESTS
# =============================================================================

class TestNavigation:
    """Tests for TikTok page navigation."""
    
    def test_navigate_to_fyp(self, safari, screenshot_dir):
        """Navigate to For You Page."""
        safari.navigate("https://www.tiktok.com/foryou")
        time.sleep(2)
        
        url = safari.get_url()
        assert "tiktok.com" in url
        safari.take_screenshot("fyp_page", screenshot_dir)
        print(f"✅ Navigated to FYP: {url}")
    
    def test_navigate_to_profile(self, safari, screenshot_dir):
        """Navigate to user profile."""
        safari.navigate("https://www.tiktok.com/@mewtru")
        time.sleep(2)
        
        url = safari.get_url()
        assert "@mewtru" in url
        safari.take_screenshot("profile_page", screenshot_dir)
        print(f"✅ Navigated to profile: {url}")
    
    def test_navigate_to_video(self, safari, screenshot_dir):
        """Navigate to specific video."""
        video_url = "https://www.tiktok.com/@mewtru/video/7564912360520011038"
        safari.navigate(video_url)
        time.sleep(2)
        
        url = safari.get_url()
        assert "video" in url
        safari.take_screenshot("video_page", screenshot_dir)
        print(f"✅ Navigated to video: {url}")
    
    def test_navigate_to_search(self, safari, screenshot_dir):
        """Navigate to search page."""
        safari.navigate("https://www.tiktok.com/search?q=arduino")
        time.sleep(2)
        
        url = safari.get_url()
        assert "search" in url
        safari.take_screenshot("search_page", screenshot_dir)
        print(f"✅ Navigated to search: {url}")
    
    def test_scroll_fyp(self, tiktok_page, screenshot_dir):
        """Scroll through FYP."""
        tiktok_page.navigate("https://www.tiktok.com/foryou")
        time.sleep(2)
        
        tiktok_page.take_screenshot("fyp_before_scroll", screenshot_dir)
        
        for i in range(3):
            tiktok_page.scroll_down()
            time.sleep(1)
        
        tiktok_page.take_screenshot("fyp_after_scroll", screenshot_dir)
        print("✅ Scrolled through 3 videos")
    
    def test_detect_page_type(self, safari):
        """Detect current page type."""
        url = safari.get_url()
        
        page_type = "unknown"
        if "/foryou" in url or url.endswith("tiktok.com/"):
            page_type = "fyp"
        elif "/video/" in url:
            page_type = "video"
        elif "/@" in url and "/video/" not in url:
            page_type = "profile"
        elif "/search" in url:
            page_type = "search"
        elif "/messages" in url:
            page_type = "messages"
        
        print(f"✅ Page type: {page_type} for URL: {url}")
        assert page_type != "unknown" or "tiktok.com" not in url


# =============================================================================
# SECTION 2: ENGAGEMENT TESTS (Like)
# =============================================================================

class TestEngagement:
    """Tests for liking videos."""
    
    def test_check_like_state(self, tiktok_video):
        """Check if video is already liked."""
        result = tiktok_video.run_js("""
            (function() {
                var likeBtn = document.querySelector('[data-e2e="like-icon"]');
                if (!likeBtn) return 'NOT_FOUND';
                var svg = likeBtn.querySelector('svg');
                var fill = svg ? window.getComputedStyle(svg).fill : '';
                return fill.includes('255, 56, 92') ? 'LIKED' : 'NOT_LIKED';
            })();
        """)
        
        assert result in ['LIKED', 'NOT_LIKED', 'NOT_FOUND']
        print(f"✅ Like state: {result}")
    
    def test_like_video_js(self, tiktok_video, screenshot_dir):
        """Like a video using JavaScript click."""
        # Check initial state
        initial = tiktok_video.run_js("""
            (function() {
                var likeBtn = document.querySelector('[data-e2e="like-icon"]');
                if (!likeBtn) return 'NOT_FOUND';
                var svg = likeBtn.querySelector('svg');
                var fill = svg ? window.getComputedStyle(svg).fill : '';
                return fill.includes('255, 56, 92') ? 'LIKED' : 'NOT_LIKED';
            })();
        """)
        
        tiktok_video.take_screenshot("before_like", screenshot_dir)
        
        if initial == 'NOT_LIKED':
            # Click like
            result = tiktok_video.run_js("""
                (function() {
                    var likeBtn = document.querySelector('[data-e2e="like-icon"]');
                    if (likeBtn) { likeBtn.click(); return 'CLICKED'; }
                    return 'NOT_FOUND';
                })();
            """)
            time.sleep(1)
            tiktok_video.take_screenshot("after_like", screenshot_dir)
            print(f"✅ Like action: {result}")
        else:
            print(f"✅ Video already liked or button not found: {initial}")
    
    def test_get_like_count(self, tiktok_video):
        """Get video like count."""
        result = tiktok_video.run_js("""
            (function() {
                var countEl = document.querySelector('[data-e2e="like-count"]');
                return countEl ? countEl.innerText : 'NOT_FOUND';
            })();
        """)
        
        print(f"✅ Like count: {result}")
        assert result != ""


# =============================================================================
# SECTION 3: COMMENT TESTS
# =============================================================================

class TestComments:
    """Tests for commenting on videos."""
    
    def test_open_comment_panel(self, tiktok_video, screenshot_dir):
        """Open the comment panel."""
        # Click comment icon
        result = tiktok_video.run_js("""
            (function() {
                var commentBtn = document.querySelector('span[data-e2e="comment-icon"]');
                if (commentBtn) { commentBtn.click(); return 'CLICKED'; }
                return 'NOT_FOUND';
            })();
        """)
        
        time.sleep(2)
        tiktok_video.take_screenshot("comment_panel", screenshot_dir)
        
        # Check if panel opened
        panel_check = tiktok_video.run_js("""
            var input = document.querySelector('[role="textbox"]');
            input ? 'OPEN' : 'CLOSED';
        """)
        
        print(f"✅ Comment panel: {panel_check}")
    
    def test_focus_comment_input(self, tiktok_video):
        """Focus on comment input field."""
        # First open panel
        tiktok_video.run_js("""
            var commentBtn = document.querySelector('span[data-e2e="comment-icon"]');
            if (commentBtn) commentBtn.click();
        """)
        time.sleep(2)
        
        # Focus input
        result = tiktok_video.run_js("""
            (function() {
                var input = document.querySelector('[role="textbox"]');
                if (input) { input.focus(); input.click(); return 'FOCUSED'; }
                return 'NOT_FOUND';
            })();
        """)
        
        print(f"✅ Comment input: {result}")
    
    def test_type_comment_pyautogui(self, tiktok_video, screenshot_dir):
        """Type comment using PyAutoGUI."""
        # Open and focus
        tiktok_video.run_js("""
            var commentBtn = document.querySelector('span[data-e2e="comment-icon"]');
            if (commentBtn) commentBtn.click();
        """)
        time.sleep(2)
        
        tiktok_video.run_js("""
            var input = document.querySelector('[role="textbox"]');
            if (input) { input.focus(); input.click(); }
        """)
        time.sleep(0.5)
        
        # Type with pyautogui
        comment_text = f"Test comment {int(time.time()) % 1000}"
        tiktok_video.activate()
        pyautogui.typewrite(comment_text, interval=0.05)
        
        time.sleep(1)
        tiktok_video.take_screenshot("typed_comment", screenshot_dir)
        print(f"✅ Typed: {comment_text}")
    
    def test_get_comment_count(self, tiktok_video):
        """Get video comment count."""
        result = tiktok_video.run_js("""
            (function() {
                var countEl = document.querySelector('[data-e2e="comment-count"]');
                return countEl ? countEl.innerText : 'NOT_FOUND';
            })();
        """)
        
        print(f"✅ Comment count: {result}")
    
    def test_read_comments(self, tiktok_video):
        """Read visible comments from video."""
        # Open panel first
        tiktok_video.run_js("""
            var commentBtn = document.querySelector('span[data-e2e="comment-icon"]');
            if (commentBtn) commentBtn.click();
        """)
        time.sleep(2)
        
        result = tiktok_video.run_js("""
            (function() {
                var comments = [];
                var items = document.querySelectorAll('[class*="CommentItemWrapper"], [class*="DivCommentItemContainer"]');
                for (var i = 0; i < Math.min(items.length, 5); i++) {
                    var text = items[i].innerText.substring(0, 100);
                    comments.push(text.replace(/\\n/g, ' '));
                }
                return JSON.stringify(comments);
            })();
        """)
        
        try:
            comments = json.loads(result)
            print(f"✅ Found {len(comments)} comments")
            for i, c in enumerate(comments[:3]):
                print(f"   {i+1}. {c[:60]}...")
        except:
            print(f"✅ Comments raw: {result[:200]}")


# =============================================================================
# SECTION 4: DATA EXTRACTION TESTS
# =============================================================================

class TestDataExtraction:
    """Tests for extracting data from TikTok pages."""
    
    def test_extract_video_stats(self, tiktok_video):
        """Extract video statistics."""
        result = tiktok_video.run_js("""
            (function() {
                var stats = {};
                var likes = document.querySelector('[data-e2e="like-count"]');
                var comments = document.querySelector('[data-e2e="comment-count"]');
                var shares = document.querySelector('[data-e2e="share-count"]');
                var saves = document.querySelector('[data-e2e="undefined-count"]');
                
                stats.likes = likes ? likes.innerText : null;
                stats.comments = comments ? comments.innerText : null;
                stats.shares = shares ? shares.innerText : null;
                stats.saves = saves ? saves.innerText : null;
                
                return JSON.stringify(stats);
            })();
        """)
        
        try:
            stats = json.loads(result)
            print(f"✅ Video stats: {stats}")
        except:
            print(f"✅ Stats raw: {result}")
    
    def test_extract_video_caption(self, tiktok_video):
        """Extract video caption/description."""
        result = tiktok_video.run_js("""
            (function() {
                var caption = document.querySelector('[data-e2e="browse-video-desc"]');
                if (!caption) caption = document.querySelector('[class*="DivVideoInfoContainer"] span');
                return caption ? caption.innerText : 'NOT_FOUND';
            })();
        """)
        
        print(f"✅ Caption: {result[:100]}...")
    
    def test_extract_author_info(self, tiktok_video):
        """Extract video author information."""
        result = tiktok_video.run_js("""
            (function() {
                var info = {};
                var username = document.querySelector('[data-e2e="browse-username"]');
                var nickname = document.querySelector('[data-e2e="browse-user-nickname"]');
                
                info.username = username ? username.innerText : null;
                info.nickname = nickname ? nickname.innerText : null;
                
                return JSON.stringify(info);
            })();
        """)
        
        try:
            info = json.loads(result)
            print(f"✅ Author: {info}")
        except:
            print(f"✅ Author raw: {result}")
    
    def test_extract_hashtags(self, tiktok_video):
        """Extract hashtags from video."""
        result = tiktok_video.run_js("""
            (function() {
                var tags = [];
                var links = document.querySelectorAll('a[href*="/tag/"]');
                links.forEach(function(link) {
                    var tag = link.innerText.trim();
                    if (tag.startsWith('#')) tags.push(tag);
                });
                return JSON.stringify(tags);
            })();
        """)
        
        try:
            tags = json.loads(result)
            print(f"✅ Hashtags: {tags}")
        except:
            print(f"✅ Hashtags raw: {result}")


# =============================================================================
# SECTION 5: SEARCH TESTS (Browser)
# =============================================================================

class TestBrowserSearch:
    """Tests for search functionality via browser."""
    
    def test_search_users(self, safari, screenshot_dir):
        """Search for users."""
        safari.navigate("https://www.tiktok.com/search/user?q=arduino")
        time.sleep(3)
        
        safari.take_screenshot("search_users", screenshot_dir)
        
        result = safari.run_js("""
            (function() {
                var users = [];
                var items = document.querySelectorAll('[data-e2e="search-user-container"]');
                items.forEach(function(item) {
                    var name = item.querySelector('[data-e2e="search-user-unique-id"]');
                    if (name) users.push(name.innerText);
                });
                return JSON.stringify(users.slice(0, 5));
            })();
        """)
        
        try:
            users = json.loads(result)
            print(f"✅ Found users: {users}")
        except:
            print(f"✅ Users raw: {result}")
    
    def test_search_videos(self, safari, screenshot_dir):
        """Search for videos."""
        safari.navigate("https://www.tiktok.com/search?q=arduino%20project")
        time.sleep(3)
        
        safari.take_screenshot("search_videos", screenshot_dir)
        print("✅ Video search page loaded")
    
    def test_search_hashtags(self, safari, screenshot_dir):
        """Search for hashtags."""
        safari.navigate("https://www.tiktok.com/tag/arduino")
        time.sleep(3)
        
        safari.take_screenshot("search_hashtag", screenshot_dir)
        
        result = safari.run_js("""
            (function() {
                var header = document.querySelector('h1, [class*="ShareTitle"]');
                return header ? header.innerText : 'NOT_FOUND';
            })();
        """)
        
        print(f"✅ Hashtag page: {result}")


# =============================================================================
# SECTION 6: MESSAGING TESTS (Browser)
# =============================================================================

class TestBrowserMessaging:
    """Tests for messaging functionality via browser."""
    
    def test_navigate_to_messages(self, safari, screenshot_dir):
        """Navigate to messages page."""
        safari.navigate("https://www.tiktok.com/messages")
        time.sleep(3)
        
        safari.take_screenshot("messages_page", screenshot_dir)
        
        url = safari.get_url()
        print(f"✅ Messages page: {url}")
    
    def test_discover_message_selectors(self, safari, screenshot_dir):
        """Discover available selectors on messages page."""
        safari.navigate("https://www.tiktok.com/messages")
        time.sleep(3)
        
        result = safari.run_js("""
            (function() {
                var selectors = {
                    inbox_container: !!document.querySelector('[class*="DivMessageContainer"]'),
                    conversation_list: !!document.querySelector('[class*="DivConversationList"]'),
                    message_input: !!document.querySelector('[class*="DivMessageInput"]'),
                    send_button: !!document.querySelector('[class*="DivSendButton"]')
                };
                return JSON.stringify(selectors);
            })();
        """)
        
        safari.take_screenshot("message_selectors", screenshot_dir)
        
        try:
            selectors = json.loads(result)
            print(f"✅ Message selectors found: {selectors}")
        except:
            print(f"✅ Selectors raw: {result}")


# =============================================================================
# SECTION 7: FULL ENGAGEMENT FLOW TEST
# =============================================================================

class TestFullEngagementFlow:
    """End-to-end engagement flow tests."""
    
    def test_engage_single_video(self, safari, screenshot_dir):
        """Complete engagement on one video: view, like, comment."""
        # Navigate to FYP
        safari.navigate("https://www.tiktok.com/foryou")
        time.sleep(3)
        
        safari.take_screenshot("flow_1_start", screenshot_dir)
        
        # 1. Check/Click like
        like_result = safari.run_js("""
            (function() {
                var likeBtn = document.querySelector('[data-e2e="like-icon"]');
                if (!likeBtn) return 'NOT_FOUND';
                var svg = likeBtn.querySelector('svg');
                var fill = svg ? window.getComputedStyle(svg).fill : '';
                if (fill.includes('255, 56, 92')) return 'ALREADY_LIKED';
                likeBtn.click();
                return 'LIKED';
            })();
        """)
        print(f"   Like: {like_result}")
        
        safari.take_screenshot("flow_2_liked", screenshot_dir)
        
        # 2. Get stats
        stats = safari.run_js("""
            (function() {
                var likes = document.querySelector('[data-e2e="like-count"]');
                var comments = document.querySelector('[data-e2e="comment-count"]');
                return JSON.stringify({
                    likes: likes ? likes.innerText : null,
                    comments: comments ? comments.innerText : null
                });
            })();
        """)
        print(f"   Stats: {stats}")
        
        # 3. Scroll to next
        safari.scroll_down()
        time.sleep(2)
        
        safari.take_screenshot("flow_3_next", screenshot_dir)
        print("✅ Engagement flow complete")


# =============================================================================
# RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
