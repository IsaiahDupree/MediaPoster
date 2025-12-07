#!/usr/bin/env python3
"""
TikTok Comment - Hybrid AppleScript + Python Approach

Uses AppleScript for navigation and clicking (true browser focus),
then pyautogui for typing, then AppleScript for verification.

PROVEN WORKING: YAUTO2111p posted at #1 position
"""

import subprocess
import time
import json
import sys
from datetime import datetime
from pathlib import Path

# Screenshot directory
SCREENSHOT_DIR = Path(__file__).parent / "comment_screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


def log(msg: str):
    """Print timestamped log message."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def screenshot(name: str) -> str:
    """Capture screenshot."""
    ts = datetime.now().strftime("%H%M%S")
    path = SCREENSHOT_DIR / f"{ts}_{name}.png"
    subprocess.run(['screencapture', '-x', str(path)], capture_output=True)
    log(f"📸 Screenshot: {path.name}")
    return str(path)


def applescript(script: str) -> str:
    """Run AppleScript and return result."""
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def js(code: str) -> str:
    """Run JavaScript in Safari."""
    escaped = code.replace('"', '\\"')
    return applescript(f'''
tell application "Safari"
    set r to do JavaScript "{escaped}" in current tab of front window
end tell
return r
''')


# ============================================
# STEP 1: APPLESCRIPT - Navigate & Open Comments
# ============================================
def step1_navigate_and_open_comments(video_url: str = None) -> bool:
    """Use AppleScript to navigate to video and open comments panel."""
    log("=== STEP 1: AppleScript Navigation ===")
    
    # Activate Safari
    applescript('tell application "Safari" to activate')
    time.sleep(0.5)
    
    # Navigate if URL provided
    if video_url:
        log(f"Navigating to: {video_url[:50]}...")
        applescript(f'''
tell application "Safari"
    tell front window
        set URL of current tab to "{video_url}"
    end tell
end tell
''')
        time.sleep(5)
    
    screenshot("01_page_loaded")
    
    # Click comment button using JavaScript
    log("Opening comments...")
    result = js("var btn=document.querySelector('button[data-e2e=comment-icon]');if(btn){btn.click();'clicked';}else{'not_found';}")
    log(f"Comment button: {result}")
    time.sleep(2)
    
    # Check if comments opened
    has_input = js("!!document.querySelector('[data-e2e=comment-input]')")
    log(f"Comment input found: {has_input}")
    
    screenshot("02_comments_open")
    return has_input == 'true'


# ============================================
# STEP 2: APPLESCRIPT - Click Comment Input (TRUE FOCUS)
# ============================================
def step2_click_comment_input() -> bool:
    """Use AppleScript to physically click on comment input for true browser focus."""
    log("=== STEP 2: AppleScript Click for True Focus ===")
    
    # Get input coordinates
    coords_json = js("var el=document.querySelector('[data-e2e=comment-input]');if(el){var r=el.getBoundingClientRect();JSON.stringify({x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)});}else{'not_found';}")
    
    if 'not_found' in coords_json:
        log("❌ Comment input not found!")
        return False
    
    coords = json.loads(coords_json)
    x, y = coords['x'], coords['y']
    log(f"Input coordinates: ({x}, {y})")
    
    # Use cliclick for physical mouse click
    log("Physical click with cliclick...")
    subprocess.run(['cliclick', f'c:{x},{y}'], capture_output=True)
    time.sleep(0.5)
    
    screenshot("03_input_clicked")
    return True


# ============================================
# STEP 3: PYTHON - Type Comment with pyautogui
# ============================================
def step3_type_comment(text: str) -> bool:
    """Use pyautogui to type the comment."""
    log(f"=== STEP 3: Python pyautogui Typing ===")
    log(f"Typing: {text}")
    
    try:
        import pyautogui
        pyautogui.typewrite(text, interval=0.03)
        time.sleep(0.5)
        screenshot("04_text_typed")
        return True
    except Exception as e:
        log(f"❌ Typing error: {e}")
        return False


# ============================================
# STEP 4: PYTHON - Check Button Status
# ============================================
def step4_check_button() -> tuple:
    """Check if Post button is active (red)."""
    log("=== STEP 4: Python Check Button ===")
    
    result = js("var btn=document.querySelector('[class*=DivPostButton]');var c=btn?window.getComputedStyle(btn).color:'none';var t=document.querySelector('[data-e2e=comment-input]');JSON.stringify({color:c,text:t?t.textContent.substring(0,40):'none'})")
    
    data = json.loads(result)
    color = data.get('color', '')
    text = data.get('text', '')
    is_red = "255, 87, 111" in color
    
    log(f"Button color: {color}")
    log(f"Input text: {text}")
    log(f"Button active: {'✅ YES' if is_red else '❌ NO'}")
    
    screenshot("05_button_check")
    return is_red, text


# ============================================
# STEP 5: APPLESCRIPT - Click Post Button
# ============================================
def step5_click_post() -> bool:
    """Use AppleScript to click the Post button."""
    log("=== STEP 5: AppleScript Click Post ===")
    
    result = js("var btn=document.querySelector('[class*=DivPostButton]');if(btn){btn.click();'clicked';}else{'not_found';}")
    log(f"Post button: {result}")
    
    time.sleep(3)
    screenshot("06_after_post")
    return result == 'clicked'


# ============================================
# STEP 6: APPLESCRIPT - Verify Comment Posted
# ============================================
def step6_verify(comment_text: str) -> dict:
    """Use AppleScript/JS to verify comment was posted."""
    log("=== STEP 6: AppleScript Verify ===")
    
    result = js("var t=document.querySelectorAll('[data-e2e=comment-level-1]');var f=[];for(var i=0;i<Math.min(5,t.length);i++){f.push(t[i].textContent.substring(0,50));}JSON.stringify({count:t.length,comments:f})")
    
    data = json.loads(result)
    comments = data.get('comments', [])
    found = any(comment_text[:8] in c for c in comments)
    
    log(f"Total comments: {data.get('count', 0)}")
    log(f"First 3: {comments[:3]}")
    log(f"Our comment found: {'✅ YES' if found else '❌ NO'}")
    
    screenshot("07_verification")
    return {'found': found, 'comments': comments}


# ============================================
# MAIN: Run Full Hybrid Flow
# ============================================
def post_comment_hybrid(comment_text: str, video_url: str = None) -> dict:
    """
    Full hybrid comment posting flow.
    
    Uses AppleScript for navigation/clicking, pyautogui for typing.
    """
    result = {
        'success': False,
        'comment': comment_text,
        'screenshots': []
    }
    
    log(f"\n{'='*60}")
    log(f"📝 HYBRID COMMENT FLOW: {comment_text}")
    log(f"{'='*60}\n")
    
    # Step 1: Navigate (AppleScript)
    if not step1_navigate_and_open_comments(video_url):
        if video_url:
            log("⚠️ Trying without navigation...")
            if not step1_navigate_and_open_comments(None):
                result['error'] = 'Comments not available'
                return result
    
    # Step 2: Click input (AppleScript/cliclick)
    if not step2_click_comment_input():
        result['error'] = 'Could not click input'
        return result
    
    # Step 3: Type (pyautogui)
    if not step3_type_comment(comment_text):
        result['error'] = 'Typing failed'
        return result
    
    # Step 4: Check button (Python)
    is_red, input_text = step4_check_button()
    result['button_active'] = is_red
    result['input_text'] = input_text
    
    if not is_red:
        log("⚠️ Button not active - text may not have reached input")
        result['error'] = 'Button not active'
        return result
    
    # Step 5: Click Post (AppleScript)
    if not step5_click_post():
        result['error'] = 'Post click failed'
        return result
    
    # Step 6: Verify (AppleScript)
    verify = step6_verify(comment_text)
    result['verification'] = verify
    result['success'] = verify.get('found', False)
    
    log(f"\n{'='*60}")
    if result['success']:
        log(f"🎉 SUCCESS! Comment '{comment_text}' posted!")
    else:
        log(f"⚠️ Comment may not be visible yet")
    log(f"{'='*60}\n")
    
    return result


def main():
    """Main entry point."""
    # Parse args
    if len(sys.argv) > 1:
        comment = ' '.join(sys.argv[1:])
    else:
        ts = datetime.now().strftime("%H%M%S")
        comment = f"HYBRID_{ts}"
    
    # Video URL (optional)
    video_url = "https://www.tiktok.com/@lil1zzyvert/video/7576036641458949407"
    
    # Run hybrid flow
    result = post_comment_hybrid(comment, video_url=None)  # Use current page
    
    # Print result
    print(f"\n{'='*40}")
    print("FINAL RESULT:")
    print(f"  Success: {result['success']}")
    print(f"  Comment: {result['comment']}")
    if result.get('error'):
        print(f"  Error: {result['error']}")
    print(f"{'='*40}")
    
    return 0 if result['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
