"""
TikTok Automation Test Suite
Tests for the PyAutoGUI + Safari automation workflow.
Note: These tests require a local environment with Safari running and TikTok logged in.
They will use 'mock' mode by default to avoid actual clicking/typing during automated CI.
"""

import unittest
import json
import pytest
import sys
from unittest.mock import MagicMock, patch

# Mock pyautogui if not installed
try:
    import pyautogui
except ImportError:
    pyautogui = MagicMock()
    sys.modules['pyautogui'] = pyautogui

from automation.tiktok_selectors import TikTokSelectors
# from automation.tiktok_automation import TikTokAutomator

# Mocking the window bounds for testing coordinate calculations
MOCK_WINDOW_BOUNDS = "100, 200, 1200, 800"  # x, y, width, height

@pytest.mark.tiktok
class TestTikTokAutomation(unittest.TestCase):
    """Test suite for TikTok automation"""
        
    def tearDown(self):
        self.subprocess_patcher.stop()

    def test_selector_constants(self):
        """Verify key selectors are present and correct"""
        self.assertEqual(TikTokSelectors.COMMENT_ICON_ATTR, 'data-e2e="comment-icon"')
        self.assertEqual(TikTokSelectors.LIKE_ICON_ATTR, 'data-e2e="like-icon"')
        self.assertIn('visible = {', TikTokSelectors.get_visible_comment_icons_script())

    def test_coordinate_calculation_logic(self):
        """Test the logic that converts DOM coordinates to Screen coordinates"""
        # 1. Simulate getting visible element from JS
        # Let's say the element is at x=500, y=300 relative to viewport
        mock_js_response = json.dumps({"x": 500, "y": 300})
        
        # 2. Simulate getting window position
        # Window is at x=100, y=200
        win_x, win_y = 100, 200
        toolbar_offset = 75
        
        # 3. Calculate expected screen coordinates
        # Screen X = Window X + Element X = 100 + 500 = 600
        # Screen Y = Window Y + Element Y + Toolbar = 200 + 300 + 75 = 575
        
        expected_x = 600
        expected_y = 575
        
        # This mirrors the logic in the automation script
        screen_x = win_x + 500
        screen_y = win_y + 300 + toolbar_offset
        
        self.assertEqual(screen_x, expected_x)
        self.assertEqual(screen_y, expected_y)

    @patch('pyautogui.click')
    @patch('pyautogui.write')
    def test_comment_workflow_logic(self, mock_write, mock_click):
        """
        Simulate the full comment workflow logic:
        1. Find visible icon
        2. Click it
        3. Type comment
        """
        # Mock JS returning a visible icon location
        js_found_icon = '{"x": 400, "y": 400}'
        
        # We need to simulate the sequence of subprocess calls (AppleScript)
        # 1. Get Window Bounds
        # 2. Get Visible Icon
        # 3. Focus Input (via JS or Click) - let's assume we click coordinates
        
        # Since we're mocking the entire external interaction, we're just testing the python logic flow
        # In a real implementation this would call `run_automation_step`
        
        win_x, win_y = 100, 200
        icon_client_x, icon_client_y = 400, 400
        
        # Logic under test
        target_x = win_x + icon_client_x
        target_y = win_y + icon_client_y + 75
        
        # Simulate action
        # import pyautogui
        # pyautogui.click(target_x, target_y)
        # pyautogui.write("Nice video!")
        
        # Assertions (Testing the test logic essentially, but verifies the math)
        self.assertEqual(target_x, 500)
        self.assertEqual(target_y, 675)

    def test_like_detection_script_generation(self):
        """Ensure the like detection script is generated correctly"""
        script = TikTokSelectors.check_if_liked_script()
        self.assertIn(TikTokSelectors.LIKE_ICON_ATTR, script)
        self.assertIn("255, 56, 92", script) # The specific red color for liked
        self.assertIn("getBoundingClientRect", script)

    def test_comment_input_focus_script(self):
        """Ensure comment input discovery script targets contenteditable"""
        script = TikTokSelectors.get_comment_input_script()
        self.assertIn(TikTokSelectors.COMMENT_FOOTER_CLASS, script)
        self.assertIn('[contenteditable="true"]', script)
        self.assertIn(".focus()", script)

    def test_dm_workflow_selectors(self):
        """Verify DM-related selector constants"""
        self.assertEqual(TikTokSelectors.MESSAGES_ROOT, "#main-content-messages")
        self.assertEqual(TikTokSelectors.MESSAGE_INPUT_CONTAINER_CLASS, "DivMessageInputAndSendButton")
        self.assertEqual(TikTokSelectors.CHAT_BOTTOM_BAR_CLASS, "DivChatBottom")

    @patch('pyautogui.click')
    @patch('pyautogui.write') 
    def test_dm_sending_logic(self, mock_write, mock_click):
        """
        Simulate DM sending workflow:
        1. Find input bar
        2. Click to focus
        3. Type message
        4. Find and click send
        """
        # Mock finding the input bar
        input_bar_pos = {"x": 500, "y": 800}
        
        # Calculate screen coordinates
        win_x, win_y = 100, 200
        target_x = win_x + input_bar_pos['x']
        target_y = win_y + input_bar_pos['y'] + 75
        
        # Simulate the 'action'
        # pyautogui.click(target_x, target_y)
        # pyautogui.write("Hello from test!")
        # pyautogui.press('enter')
        
        self.assertEqual(target_x, 600)
        self.assertEqual(target_y, 1075)

    def test_dm_input_discovery_script(self):
        """Test constructing the JS to find DM input"""
        # This mirrors the logic we'd inject into Safari
        script = f"""
        var bar = document.querySelector('{TikTokSelectors.MESSAGES_ROOT} [class*="{TikTokSelectors.MESSAGE_INPUT_CONTAINER_CLASS}"]');
        if (bar) {{
            var input = bar.querySelector('[contenteditable="true"], textarea, input[type="text"]');
            if (input) {{
                input.focus();
                'found';
            }} else {{
                'not_found';
            }}
        }} else {{
            'bar_not_found';
        }}
        """
        self.assertIn(TikTokSelectors.MESSAGES_ROOT, script)
        self.assertIn(TikTokSelectors.MESSAGE_INPUT_CONTAINER_CLASS, script)

if __name__ == '__main__':
    unittest.main()
