"""
TikTok Full Engagement Test - Like, Comment, Scroll
====================================================

Complete automation for:
- Like videos (with state confirmation to avoid unlike)
- Comment on videos (with verification)
- Scroll to next video (with URL verification)

Prerequisites:
- Safari open with TikTok logged in
- Safari > Settings > Advanced > Allow JavaScript from Apple Events ✓
- pyautogui installed: pip install pyautogui

Run with: pytest test_tiktok_engagement_full.py -v -s

IMPORTANT: For best results, run from Terminal (not IDE) to avoid focus issues.
"""

import pytest
import subprocess
import time
import json
import pyautogui
from datetime import datetime
from pathlib import Path

# Configure pyautogui safety
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def screenshot_dir():
    """Create directory for test screenshots."""
    dir_path = Path(__file__).parent / "screenshots" / f"engagement_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


@pytest.fixture
def safari():
    """Ensure Safari is active and return AppleScript helper."""
    class SafariHelper:
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
            time.sleep(3)
        
        def take_screenshot(self, name: str, screenshot_dir: Path) -> Path:
            """Take screenshot of Safari window."""
            path = screenshot_dir / f"{name}.png"
            subprocess.run(["screencapture", "-x", str(path)], capture_output=True)
            return path
    
    helper = SafariHelper()
    helper.activate()
    return helper


# =============================================================================
# FULL ENGAGEMENT TEST
# =============================================================================

class TestTikTokEngagement:
    """Full TikTok engagement test: Like, Comment, Scroll."""
    
    def test_engage_videos(self, safari, screenshot_dir):
        """Like, comment, and scroll through videos."""
        safari.activate()
        safari.navigate("https://www.tiktok.com/foryou")
        time.sleep(3)  # Let FYP load
        
        num_videos = 3  # Number of videos to engage with
        results = []
        
        for i in range(1, num_videos + 1):
            print(f"\n{'='*50}")
            print(f"=== PROCESSING VIDEO {i} of {num_videos} ===")
            print(f"{'='*50}")
            
            video_result = {
                'video': i,
                'like': None,
                'comment': None,
                'scroll': None
            }
            
            safari.take_screenshot(f"video_{i}_start", screenshot_dir)
            
            # -----------------------------------------------------------------
            # 1. LIKE VIDEO (with state confirmation)
            # -----------------------------------------------------------------
            print("\n--- LIKE ---")
            like_result = safari.run_js(
                "(function() {"
                "var likeBtn = document.querySelector('[data-e2e=\"like-icon\"]');"
                "if (!likeBtn) return 'NOT_FOUND';"
                "var svg = likeBtn.querySelector('svg');"
                "var fill = svg ? window.getComputedStyle(svg).fill : '';"
                "var isLiked = fill.includes('255, 56, 92');"
                "if (isLiked) return 'ALREADY_LIKED';"
                "likeBtn.click();"
                "return 'CLICKED';"
                "})();"
            )
            print(f"Like action: {like_result}")
            
            # Verify like state after click
            if like_result == 'CLICKED':
                time.sleep(0.5)
                verify_like = safari.run_js(
                    "(function() {"
                    "var svg = document.querySelector('[data-e2e=\"like-icon\"] svg');"
                    "if (!svg) return 'SVG_NOT_FOUND';"
                    "var fill = window.getComputedStyle(svg).fill;"
                    "return fill.includes('255, 56, 92') ? 'CONFIRMED_LIKED' : 'NOT_LIKED';"
                    "})();"
                )
                print(f"Like verification: {verify_like}")
                video_result['like'] = verify_like
            else:
                video_result['like'] = like_result
            
            safari.take_screenshot(f"video_{i}_liked", screenshot_dir)
            
            # -----------------------------------------------------------------
            # 2. COMMENT ON VIDEO
            # -----------------------------------------------------------------
            print("\n--- COMMENT ---")
            
            # Check if comment panel is already open
            panel_open = safari.run_js(
                "var container = document.querySelector('[class*=\"DivInputEditorContainer\"]');"
                "var footer = document.querySelector('[class*=\"DivCommentFooter\"]');"
                "(!!container || !!footer) ? 'OPEN' : 'CLOSED';"
            )
            print(f"Comment panel status: {panel_open}")
            
            if "OPEN" not in panel_open:
                # Open comment panel via JS click
                print("Opening comment panel...")
                safari.run_js(
                    "var span = document.querySelector('span[data-e2e=\"comment-icon\"]');"
                    "if(span) span.click();"
                )
                
                # Wait for panel to open
                for wait_try in range(5):
                    time.sleep(1)
                    panel_check = safari.run_js(
                        "var editor = document.querySelector('.public-DraftEditor-content');"
                        "editor ? 'READY' : 'WAITING';"
                    )
                    if 'READY' in panel_check:
                        print(f"Comment panel opened after {wait_try+1}s")
                        break
                else:
                    print("Comment panel did not open!")
                    video_result['comment'] = 'PANEL_FAILED'
                    continue
            
            # Type comment
            comment_text = f"Nice{i}{int(time.time()) % 1000}"
            print(f"Typing: {comment_text}")
            
            # Focus editor via JS
            safari.run_js(
                "var e = document.querySelector('.public-DraftEditor-content');"
                "if(e) { e.focus(); e.click(); }"
            )
            time.sleep(0.2)
            
            # Activate Safari and type immediately (critical timing)
            safari.activate()
            time.sleep(0.1)
            pyautogui.write(comment_text, interval=0.02)
            time.sleep(0.3)
            
            # Verify text was typed
            typed = safari.run_js(
                "var e = document.querySelector('.public-DraftEditor-content');"
                "e ? e.innerText.trim() : '';"
            )
            print(f"Text in editor: '{typed}'")
            
            safari.take_screenshot(f"video_{i}_typed", screenshot_dir)
            
            # Click Post button
            post_result = safari.run_js(
                "(function() {"
                "var btn = document.querySelector('[class*=DivPostButton]');"
                "if (!btn) btn = document.querySelector('[data-e2e=comment-post]');"
                "if (btn) { btn.click(); return 'CLICKED'; }"
                "return 'NOT_FOUND';"
                "})();"
            )
            print(f"Post action: {post_result}")
            
            if 'CLICKED' in post_result:
                time.sleep(3)  # Wait for comment to post
                
                # Verify comment was posted
                verify_comment = safari.run_js(
                    "(function() {"
                    "var comments = document.querySelectorAll('[class*=DivCommentItemWrapper]');"
                    "for(var i=0; i<Math.min(comments.length, 5); i++) {"
                    "var text = comments[i].innerText.toLowerCase();"
                    "if(text.includes('isaiah_dupree') || text.includes('nice')) {"
                    "return 'VERIFIED';"
                    "}}"
                    "return 'NOT_FOUND';"
                    "})();"
                )
                print(f"Comment verification: {verify_comment}")
                video_result['comment'] = verify_comment
            else:
                video_result['comment'] = 'POST_FAILED'
            
            safari.take_screenshot(f"video_{i}_commented", screenshot_dir)
            
            # -----------------------------------------------------------------
            # 3. SCROLL TO NEXT VIDEO
            # -----------------------------------------------------------------
            print("\n--- SCROLL ---")
            
            # Get current URL before scroll
            url_before = safari.get_url()
            print(f"URL before: {url_before[:50]}...")
            
            # Scroll to next video
            print("Scrolling to next video...")
            safari.activate()
            time.sleep(0.2)
            pyautogui.press('down')
            time.sleep(3)  # Wait for scroll and load
            
            # Verify scroll worked
            url_after = safari.get_url()
            print(f"URL after: {url_after[:50]}...")
            
            if url_after != url_before:
                print("Scroll: SUCCESS - URL changed")
                video_result['scroll'] = 'SUCCESS'
            else:
                # Check if video index changed in DOM
                video_check = safari.run_js(
                    "var active = document.querySelector('[class*=DivVideoContainer]');"
                    "active ? 'VIDEO_PRESENT' : 'NO_VIDEO';"
                )
                video_result['scroll'] = 'URL_SAME_BUT_' + video_check
            
            safari.take_screenshot(f"video_{i}_scrolled", screenshot_dir)
            
            # Store result
            results.append(video_result)
            print(f"\nVideo {i} result: {video_result}")
        
        # -----------------------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------------------
        print(f"\n{'='*50}")
        print("=== ENGAGEMENT SUMMARY ===")
        print(f"{'='*50}")
        
        for r in results:
            print(f"Video {r['video']}: Like={r['like']}, Comment={r['comment']}, Scroll={r['scroll']}")
        
        # Assertions
        likes_ok = sum(1 for r in results if r['like'] in ['CONFIRMED_LIKED', 'ALREADY_LIKED'])
        comments_ok = sum(1 for r in results if r['comment'] == 'VERIFIED')
        scrolls_ok = sum(1 for r in results if r['scroll'] == 'SUCCESS')
        
        print(f"\nLikes successful: {likes_ok}/{num_videos}")
        print(f"Comments verified: {comments_ok}/{num_videos}")
        print(f"Scrolls successful: {scrolls_ok}/{num_videos}")
        
        # At least 1 of each should succeed
        assert likes_ok >= 1, "No likes succeeded"
        assert comments_ok >= 1, "No comments verified"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
