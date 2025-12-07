#!/usr/bin/env python3
"""
TikTok Comment Automation Script
Based on verified working flow that posted YAUTO2111p at #1 position.

USAGE:
    python3 tiktok_comment_script.py "Your comment text here"
    
REQUIREMENTS:
    - pyautogui (pip install pyautogui)
    - Safari with TikTok logged in
    - Video page with comments panel already open
    
VERIFIED WORKING:
    - YAUTO2111p posted at #1 position
    - 5t3g3 (manual) posted at #1 position
"""

import pyautogui
import subprocess
import time
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Screenshot output directory
SCREENSHOT_DIR = Path(__file__).parent / "comment_screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


def capture_screenshot(name: str) -> str:
    """Capture screenshot of entire screen."""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{timestamp}_{name}.png"
    filepath = SCREENSHOT_DIR / filename
    subprocess.run([
        'screencapture', '-x', str(filepath)
    ], capture_output=True)
    print(f"       📸 Screenshot: {filename}")
    return str(filepath)


def run_js(script: str) -> str:
    """Run JavaScript in Safari and return result."""
    result = subprocess.run([
        'osascript', '-e', f'''
tell application "Safari"
    set r to do JavaScript "{script}" in current tab of front window
end tell
return r
'''
    ], capture_output=True, text=True)
    return result.stdout.strip()


def activate_safari():
    """Bring Safari to front."""
    subprocess.run(['osascript', '-e', 'tell application "Safari" to activate'])
    time.sleep(0.5)


def open_comments() -> bool:
    """Click comment button to open comments panel."""
    result = run_js("var btn=document.querySelector('button[data-e2e=comment-icon]');if(btn){btn.click();'clicked';}else{'not_found';}")
    return result == 'clicked'


def focus_comment_input() -> bool:
    """Focus the comment input field."""
    result = run_js("var el=document.querySelector('[data-e2e=comment-input]');if(el){el.click();el.focus();'focused';}else{'not_found';}")
    return result == 'focused'


def get_input_coordinates() -> tuple:
    """Get screen coordinates of comment input."""
    result = run_js("var el=document.querySelector('[data-e2e=comment-input]');if(el){var r=el.getBoundingClientRect();JSON.stringify({x:r.left+r.width/2,y:r.top+r.height/2});}else{'not_found';}")
    if 'not_found' in result:
        return None, None
    data = json.loads(result)
    return int(data['x']), int(data['y'])


def check_button_active() -> tuple:
    """Check if Post button is active (red) and get input text."""
    result = run_js("var btn=document.querySelector('[class*=DivPostButton]');var c=btn?window.getComputedStyle(btn).color:'none';var t=document.querySelector('[data-e2e=comment-input]');JSON.stringify({color:c,text:t?t.textContent.substring(0,50):'none'})")
    data = json.loads(result)
    is_red = "255, 87, 111" in data.get('color', '')
    return is_red, data.get('text', ''), data.get('color', '')


def click_post_button() -> bool:
    """Click the Post button."""
    result = run_js("var btn=document.querySelector('[class*=DivPostButton]');if(btn){btn.click();'clicked';}else{'not_found';}")
    return result == 'clicked'


def verify_comment_posted(comment_text: str) -> dict:
    """Verify comment was posted."""
    result = run_js("var t=document.querySelectorAll('[data-e2e=comment-level-1]');var f=[];for(var i=0;i<Math.min(5,t.length);i++){f.push(t[i].textContent.substring(0,50));}JSON.stringify({count:t.length,comments:f})")
    data = json.loads(result)
    data['found'] = any(comment_text[:10] in c for c in data.get('comments', []))
    return data


def post_comment(comment_text: str, use_cliclick: bool = False) -> dict:
    """
    Post a comment to the current TikTok video.
    
    Args:
        comment_text: The text to post as a comment
        use_cliclick: Use physical mouse click (requires cliclick installed)
        
    Returns:
        dict with success status and details
    """
    result = {
        'success': False,
        'comment': comment_text,
        'steps': [],
        'screenshots': []
    }
    
    print(f"\n{'='*50}")
    print(f"📝 Posting comment: {comment_text}")
    print('='*50)
    
    # Step 1: Activate Safari
    print("\n[1/6] Activating Safari...")
    activate_safari()
    result['steps'].append('safari_activated')
    result['screenshots'].append(capture_screenshot("01_safari_activated"))
    
    # Step 2: Open comments if needed
    print("[2/6] Checking comments panel...")
    if not focus_comment_input():
        print("       Opening comments...")
        if open_comments():
            time.sleep(2)
            result['steps'].append('comments_opened')
        else:
            print("       ⚠️ Could not open comments")
    result['screenshots'].append(capture_screenshot("02_comments_open"))
    
    # Step 3: Focus input
    print("[3/6] Focusing input...")
    if focus_comment_input():
        result['steps'].append('input_focused')
    else:
        result['error'] = 'Input not found'
        print("       ❌ Input not found!")
        result['screenshots'].append(capture_screenshot("03_error_no_input"))
        return result
    
    time.sleep(0.5)
    
    # Optional: Physical click with cliclick
    if use_cliclick:
        x, y = get_input_coordinates()
        if x and y:
            print(f"       Clicking at ({x}, {y})...")
            subprocess.run(['cliclick', f'c:{x},{y}'])
            time.sleep(0.3)
    
    result['screenshots'].append(capture_screenshot("03_input_focused"))
    
    # Step 4: Type with pyautogui
    print(f"[4/6] Typing: {comment_text}")
    pyautogui.typewrite(comment_text, interval=0.03)
    result['steps'].append('text_typed')
    time.sleep(0.5)
    result['screenshots'].append(capture_screenshot("04_text_typed"))
    
    # Step 5: Check button
    print("[5/6] Checking button status...")
    is_red, input_text, color = check_button_active()
    result['button_color'] = color
    result['input_text'] = input_text
    
    if is_red:
        print(f"       ✅ Button is RED!")
        result['steps'].append('button_active')
        result['screenshots'].append(capture_screenshot("05_button_red"))
        
        # Post
        print("[6/6] Clicking Post...")
        if click_post_button():
            result['steps'].append('posted')
            time.sleep(3)
            result['screenshots'].append(capture_screenshot("06_after_post"))
            
            # Verify
            verify = verify_comment_posted(comment_text)
            result['verification'] = verify
            
            if verify.get('found'):
                result['success'] = True
                print(f"\n🎉 SUCCESS! Comment posted!")
                print(f"   First comments: {verify.get('comments', [])[:3]}")
            else:
                print(f"\n⚠️ Comment may not be visible yet")
                print(f"   First comments: {verify.get('comments', [])[:3]}")
        else:
            result['error'] = 'Post button click failed'
    else:
        print(f"       ⚠️ Button not RED (color: {color})")
        print(f"       Input text: {input_text}")
        result['error'] = 'Button not active - text may not have reached input'
        result['screenshots'].append(capture_screenshot("05_button_not_active"))
    
    result['screenshots'].append(capture_screenshot("07_final"))
    return result


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        comment = ' '.join(sys.argv[1:])
    else:
        # Generate unique comment
        timestamp = datetime.now().strftime("%H%M%S")
        comment = f"TEST_{timestamp}"
    
    result = post_comment(comment, use_cliclick=True)
    
    print(f"\n{'='*50}")
    print("RESULT:")
    print(f"  Success: {result['success']}")
    print(f"  Comment: {result['comment']}")
    print(f"  Steps completed: {result['steps']}")
    if result.get('error'):
        print(f"  Error: {result['error']}")
    print('='*50)
    
    return 0 if result['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
