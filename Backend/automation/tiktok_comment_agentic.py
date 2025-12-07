#!/usr/bin/env python3
"""
TikTok Agentic Comment Automation Cycle

Agentic approach:
1. AppleScript: Find Safari with TikTok, navigate to FYP
2. AppleScript: Scroll to video, center it, open comments
3. Python: Type comment with pyautogui
4. AppleScript: Click Post, verify, move to next video
5. Repeat cycle

Integrates with existing:
- safari_app_controller.py (AppleScript automation)
- tiktok_engagement.py (TikTok selectors)
"""

import subprocess
import time
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# Screenshot directory
SCREENSHOT_DIR = Path(__file__).parent / "comment_screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


class TikTokState:
    """Track TikTok state for agentic awareness."""
    
    def __init__(self):
        self.current_url: str = ""
        self.current_video_id: str = ""
        self.is_on_fyp: bool = False
        self.comments_open: bool = False
        self.input_focused: bool = False
        self.comments_posted: List[str] = []
        self.videos_visited: List[str] = []
        
    def update(self, url: str):
        """Update state based on URL."""
        self.current_url = url
        self.is_on_fyp = "/foryou" in url or url.endswith("/en/")
        if "/video/" in url:
            self.current_video_id = url.split("/video/")[-1].split("?")[0]
        else:
            self.current_video_id = ""
    
    def log(self):
        """Log current state."""
        print(f"📊 State: FYP={self.is_on_fyp}, Video={self.current_video_id[:10] if self.current_video_id else 'none'}, Comments={'open' if self.comments_open else 'closed'}")


def log(msg: str):
    """Timestamped logging."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def screenshot(name: str) -> str:
    """Capture screenshot."""
    ts = datetime.now().strftime("%H%M%S")
    path = SCREENSHOT_DIR / f"{ts}_{name}.png"
    subprocess.run(['screencapture', '-x', str(path)], capture_output=True)
    log(f"📸 {path.name}")
    return str(path)


# ============================================
# APPLESCRIPT FUNCTIONS
# ============================================

def applescript(script: str, timeout: int = 30) -> str:
    """Run AppleScript."""
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except Exception as e:
        log(f"⚠️ AppleScript error: {e}")
        return ""


def js(code: str) -> str:
    """Execute JavaScript in Safari."""
    escaped = code.replace('"', '\\"').replace('\n', ' ')
    return applescript(f'''
tell application "Safari"
    set r to do JavaScript "{escaped}" in current tab of front window
end tell
return r
''')


def find_safari_with_tiktok() -> bool:
    """Find Safari window with TikTok and bring to front."""
    log("🔍 Finding Safari with TikTok...")
    
    result = applescript('''
tell application "Safari"
    activate
    set windowList to every window
    repeat with w in windowList
        set tabList to every tab of w
        repeat with t in tabList
            if URL of t contains "tiktok.com" then
                set current tab of w to t
                set index of w to 1
                return URL of t
            end if
        end repeat
    end repeat
    return "not_found"
end tell
''')
    
    if "not_found" in result or result == "":
        log("❌ No TikTok tab found in Safari")
        return False
    
    log(f"✅ Found TikTok: {result[:50]}...")
    return True


def navigate_to_fyp() -> bool:
    """Navigate to For You page."""
    log("🏠 Navigating to For You page...")
    
    applescript('''
tell application "Safari"
    activate
    tell front window
        set URL of current tab to "https://www.tiktok.com/foryou"
    end tell
end tell
''')
    time.sleep(5)
    
    # Verify we're on FYP
    url = js("window.location.href")
    return "/foryou" in url


def scroll_to_video() -> bool:
    """Scroll down to center on a video."""
    log("📜 Scrolling to video...")
    
    # Scroll a bit
    js("window.scrollBy(0, 300)")
    time.sleep(1)
    
    # Check for video player
    has_video = js("!!document.querySelector('video')")
    log(f"Video player: {has_video}")
    return has_video == "true"


def click_video_to_open() -> bool:
    """Click on video to open full view (if in grid)."""
    log("🎬 Opening video...")
    
    result = js("var v=document.querySelector('[data-e2e=recommend-list-item-container] a, a[href*=\"/video/\"]');if(v){v.click();'clicked';}else{'not_found';}")
    
    if result == "clicked":
        time.sleep(3)
        return True
    return False


def open_comments() -> bool:
    """Click comment button to open comments panel."""
    log("💬 Opening comments...")
    
    result = js("var btn=document.querySelector('button[data-e2e=comment-icon]');if(btn){btn.click();'clicked';}else{'not_found';}")
    log(f"Comment button: {result}")
    
    if result == "clicked":
        time.sleep(2)
        return True
    
    # Check if comments already visible
    has_input = js("!!document.querySelector('[data-e2e=comment-input]')")
    return has_input == "true"


def focus_comment_input_gui() -> tuple:
    """Use GUI automation to click and focus comment input. Returns (success, x, y)."""
    log("🎯 Focusing comment input with GUI click...")
    
    # Get coordinates
    coords = js("var el=document.querySelector('[data-e2e=comment-input]');if(el){var r=el.getBoundingClientRect();JSON.stringify({x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)});}else{'not_found';}")
    
    if "not_found" in coords or coords == "":
        log("❌ Comment input not found")
        return False, 0, 0
    
    data = json.loads(coords)
    x, y = data['x'], data['y']
    log(f"Input at ({x}, {y})")
    
    # Physical click with cliclick
    subprocess.run(['cliclick', f'c:{x},{y}'], capture_output=True)
    time.sleep(0.3)
    
    return True, x, y


def goto_next_video() -> bool:
    """Navigate to next video using Down arrow key."""
    log("⬇️ Going to next video...")
    
    applescript('''
tell application "Safari"
    activate
end tell
delay 0.3
tell application "System Events"
    key code 125 -- Down arrow
end tell
''')
    time.sleep(2)
    return True


def close_comments() -> bool:
    """Close comments panel."""
    log("❎ Closing comments...")
    
    result = js("var btn=document.querySelector('[class*=CloseButton], button[aria-label*=close]');if(btn){btn.click();'clicked';}else{'not_found';}")
    time.sleep(0.5)
    return True


def check_button_status() -> tuple:
    """Check if Post button is active (red)."""
    result = js("var btn=document.querySelector('[class*=DivPostButton]');var c=btn?window.getComputedStyle(btn).color:'none';var t=document.querySelector('[data-e2e=comment-input]');JSON.stringify({color:c,text:t?t.textContent.substring(0,40):'none'})")
    
    try:
        data = json.loads(result)
        color = data.get('color', '')
        text = data.get('text', '')
        is_red = "255, 87, 111" in color
        return is_red, text, color
    except:
        return False, "", ""


def click_post_button() -> bool:
    """Click the Post button."""
    log("📤 Clicking Post...")
    result = js("var btn=document.querySelector('[class*=DivPostButton]');if(btn){btn.click();'clicked';}else{'not_found';}")
    time.sleep(3)
    return result == "clicked"


def verify_comment(comment_text: str) -> dict:
    """Verify comment was posted."""
    result = js("var t=document.querySelectorAll('[data-e2e=comment-level-1]');var f=[];for(var i=0;i<Math.min(5,t.length);i++){f.push(t[i].textContent.substring(0,40));}JSON.stringify({count:t.length,comments:f})")
    
    try:
        data = json.loads(result)
        data['found'] = any(comment_text[:8] in c for c in data.get('comments', []))
        return data
    except:
        return {'found': False, 'comments': []}


# ============================================
# PYTHON TYPING FUNCTION
# ============================================

def type_comment_python(text: str) -> bool:
    """Type comment using pyautogui (requires input to be focused)."""
    log(f"⌨️ Typing: {text}")
    
    try:
        import pyautogui
        pyautogui.typewrite(text, interval=0.03)
        time.sleep(0.5)
        return True
    except Exception as e:
        log(f"❌ Typing error: {e}")
        return False


# ============================================
# AGENTIC COMMENT CYCLE
# ============================================

def comment_on_video(comment_text: str, state: TikTokState) -> dict:
    """
    Complete comment cycle on current video.
    
    Flow:
    1. AppleScript: Ensure comments open
    2. AppleScript: Click input for focus
    3. Python: Type comment
    4. AppleScript: Check button, click Post
    5. AppleScript: Verify
    """
    result = {'success': False, 'comment': comment_text}
    
    log(f"\n{'='*50}")
    log(f"📝 COMMENT CYCLE: {comment_text}")
    log(f"{'='*50}\n")
    
    screenshot("01_start")
    
    # Step 1: Open comments if needed
    if not state.comments_open:
        if not open_comments():
            result['error'] = 'Could not open comments'
            screenshot("01_error_no_comments")
            return result
        state.comments_open = True
    
    screenshot("02_comments_open")
    
    # Step 2: Focus input with GUI click
    success, x, y = focus_comment_input_gui()
    if not success:
        result['error'] = 'Could not find input'
        return result
    
    state.input_focused = True
    screenshot("03_input_focused")
    
    # Step 3: Type with Python/pyautogui
    if not type_comment_python(comment_text):
        result['error'] = 'Typing failed'
        return result
    
    screenshot("04_typed")
    
    # Step 4: Check button
    is_red, input_text, color = check_button_status()
    log(f"Button: {color}")
    log(f"Input text: {input_text}")
    
    result['button_active'] = is_red
    result['input_text'] = input_text
    
    if not is_red:
        log("⚠️ Button not RED")
        result['error'] = 'Button not active'
        screenshot("05_button_not_active")
        return result
    
    log("✅ Button is RED!")
    screenshot("05_button_red")
    
    # Step 5: Click Post
    if not click_post_button():
        result['error'] = 'Post failed'
        return result
    
    screenshot("06_posted")
    
    # Step 6: Verify
    verify = verify_comment(comment_text)
    result['verification'] = verify
    result['success'] = verify.get('found', False)
    
    if result['success']:
        state.comments_posted.append(comment_text)
        log(f"🎉 SUCCESS! Comment posted!")
    else:
        log(f"⚠️ Comment may not be visible")
    
    screenshot("07_verified")
    
    return result


def run_comment_cycle(num_videos: int = 3, comment_template: str = "Nice video! 🔥"):
    """
    Run the full agentic comment cycle on multiple videos.
    
    Args:
        num_videos: Number of videos to comment on
        comment_template: Comment text template (timestamp will be added)
    """
    log(f"\n{'='*60}")
    log(f"🚀 AGENTIC COMMENT CYCLE")
    log(f"   Videos: {num_videos}")
    log(f"   Template: {comment_template}")
    log(f"{'='*60}\n")
    
    state = TikTokState()
    results = []
    
    # Step 1: Find Safari with TikTok
    if not find_safari_with_tiktok():
        log("Opening TikTok...")
        navigate_to_fyp()
        time.sleep(5)
    
    # Update state
    url = js("window.location.href")
    state.update(url)
    state.log()
    
    # Main cycle
    for i in range(num_videos):
        log(f"\n{'='*40}")
        log(f"📹 VIDEO {i+1}/{num_videos}")
        log(f"{'='*40}\n")
        
        # Generate unique comment
        ts = datetime.now().strftime("%H%M%S")
        comment = f"{comment_template}_{ts}"
        
        # Comment on this video
        result = comment_on_video(comment, state)
        results.append(result)
        
        if i < num_videos - 1:
            # Go to next video
            close_comments()
            state.comments_open = False
            state.input_focused = False
            goto_next_video()
            time.sleep(2)
            
            # Update state
            url = js("window.location.href")
            state.update(url)
            state.log()
    
    # Summary
    log(f"\n{'='*60}")
    log(f"📊 CYCLE COMPLETE")
    log(f"{'='*60}")
    
    success_count = sum(1 for r in results if r.get('success'))
    log(f"Success: {success_count}/{num_videos}")
    
    for i, r in enumerate(results):
        status = "✅" if r.get('success') else "❌"
        log(f"  Video {i+1}: {status} - {r.get('comment', 'unknown')}")
        if r.get('error'):
            log(f"           Error: {r['error']}")
    
    return results


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--cycle":
            num = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            results = run_comment_cycle(num_videos=num)
        else:
            # Single comment
            comment = ' '.join(sys.argv[1:])
            state = TikTokState()
            find_safari_with_tiktok()
            url = js("window.location.href")
            state.update(url)
            result = comment_on_video(comment, state)
            print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")
    else:
        # Default: single comment with timestamp
        ts = datetime.now().strftime("%H%M%S")
        comment = f"AGENTIC_{ts}"
        state = TikTokState()
        find_safari_with_tiktok()
        url = js("window.location.href")
        state.update(url)
        result = comment_on_video(comment, state)
        print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")


if __name__ == '__main__':
    main()
