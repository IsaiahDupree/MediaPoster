"""
TikTok Scroll Test - Testing different scroll methods
"""

import pytest
import subprocess
import time
import pyautogui
from datetime import datetime
from pathlib import Path

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3


@pytest.fixture
def safari():
    """Safari helper."""
    class SafariHelper:
        def activate(self):
            subprocess.run(["osascript", "-e", 'tell application "Safari" to activate'], capture_output=True)
            time.sleep(0.3)
        
        def run_js(self, js_code: str) -> str:
            escaped_js = js_code.replace('"', '\\"').replace('\n', ' ')
            result = subprocess.run(
                ["osascript", "-e", f'tell application "Safari" to do JavaScript "{escaped_js}" in current tab of front window'],
                capture_output=True, text=True
            )
            return result.stdout.strip()
        
        def get_url(self) -> str:
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Safari" to return URL of current tab of front window'],
                capture_output=True, text=True
            )
            return result.stdout.strip()
        
        def navigate(self, url: str):
            subprocess.run(
                ["osascript", "-e", f'tell application "Safari" to set URL of current tab of front window to "{url}"'],
                capture_output=True
            )
            time.sleep(3)
    
    helper = SafariHelper()
    helper.activate()
    return helper


class TestScroll:
    """Test scrolling to next video."""
    
    def test_scroll_methods(self, safari):
        """Try different scroll methods."""
        safari.activate()
        safari.navigate("https://www.tiktok.com/foryou")
        time.sleep(3)
        
        print("\n=== SCROLL TEST ===\n")
        
        # Get initial video info
        initial_info = safari.run_js(
            "var v = document.querySelector('[data-e2e=\"like-count\"]');"
            "v ? v.innerText : 'NO_COUNT';"
        )
        print(f"Initial like count: {initial_info}")
        
        url_before = safari.get_url()
        print(f"URL before: {url_before}")
        
        # Method 1: pyautogui.press('down')
        print("\n--- Method 1: pyautogui.press('down') ---")
        safari.activate()
        time.sleep(0.2)
        pyautogui.press('down')
        time.sleep(2)
        
        url_after_1 = safari.get_url()
        info_after_1 = safari.run_js(
            "var v = document.querySelector('[data-e2e=\"like-count\"]');"
            "v ? v.innerText : 'NO_COUNT';"
        )
        print(f"Like count after: {info_after_1}")
        print(f"URL after: {url_after_1}")
        print(f"Video changed: {info_after_1 != initial_info}")
        
        # Method 2: pyautogui.hotkey for down arrow
        print("\n--- Method 2: pyautogui key('down') again ---")
        safari.activate()
        time.sleep(0.2)
        pyautogui.press('down')
        time.sleep(2)
        
        url_after_2 = safari.get_url()
        info_after_2 = safari.run_js(
            "var v = document.querySelector('[data-e2e=\"like-count\"]');"
            "v ? v.innerText : 'NO_COUNT';"
        )
        print(f"Like count after: {info_after_2}")
        print(f"URL after: {url_after_2}")
        print(f"Video changed from previous: {info_after_2 != info_after_1}")
        
        # Method 3: JS scroll
        print("\n--- Method 3: JS window.scrollBy ---")
        safari.run_js("window.scrollBy(0, window.innerHeight);")
        time.sleep(2)
        
        info_after_3 = safari.run_js(
            "var v = document.querySelector('[data-e2e=\"like-count\"]');"
            "v ? v.innerText : 'NO_COUNT';"
        )
        print(f"Like count after: {info_after_3}")
        print(f"Video changed from previous: {info_after_3 != info_after_2}")
        
        # Method 4: Press 'j' key (TikTok shortcut for next video)
        print("\n--- Method 4: Press 'j' key (TikTok shortcut) ---")
        safari.activate()
        time.sleep(0.2)
        pyautogui.press('j')
        time.sleep(2)
        
        info_after_4 = safari.run_js(
            "var v = document.querySelector('[data-e2e=\"like-count\"]');"
            "v ? v.innerText : 'NO_COUNT';"
        )
        print(f"Like count after: {info_after_4}")
        print(f"Video changed from previous: {info_after_4 != info_after_3}")
        
        print("\n=== SUMMARY ===")
        print(f"Initial: {initial_info}")
        print(f"After down 1: {info_after_1} (changed: {info_after_1 != initial_info})")
        print(f"After down 2: {info_after_2} (changed: {info_after_2 != info_after_1})")
        print(f"After JS scroll: {info_after_3} (changed: {info_after_3 != info_after_2})")
        print(f"After 'j' key: {info_after_4} (changed: {info_after_4 != info_after_3})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
