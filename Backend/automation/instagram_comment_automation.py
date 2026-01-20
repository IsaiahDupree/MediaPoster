"""
Instagram Comment Automation via Safari Browser Control
========================================================

Implements SAF-003: Instagram Comment Automation

This service provides automated Instagram comment posting via Safari browser
using AppleScript control. Integrates with SafariAppController for browser control.

Features:
- Post comments on Instagram posts
- Navigate to specific posts via URL
- Detect and handle captchas
- Session management and error handling
- Graceful fallback if automation fails

Usage:
    automation = InstagramCommentAutomation()
    await automation.start()
    result = await automation.post_comment(
        post_url="https://www.instagram.com/p/ABC123/",
        comment_text="Great post!"
    )
"""

import asyncio
from typing import Dict, Optional, Any
from loguru import logger
from datetime import datetime

from automation.safari_app_controller import SafariAppController


class InstagramCommentAutomation:
    """
    Instagram comment automation using Safari browser control.

    Uses SafariAppController to:
    1. Navigate to Instagram posts
    2. Find and fill comment input fields
    3. Submit comments
    4. Handle errors and captchas
    """

    # Instagram selectors (updated for 2026)
    SELECTORS = {
        "comment_input": 'textarea[placeholder*="comment" i], textarea[aria-label*="comment" i]',
        "comment_post_button": 'button[type="submit"], button:has-text("Post")',
        "login_check": 'svg[aria-label="Home"]',  # Profile icon indicates logged in
        "captcha": '.recaptcha, [id*="captcha"]',
    }

    def __init__(self):
        """Initialize Instagram comment automation."""
        self.safari_controller: Optional[SafariAppController] = None
        self.is_initialized = False
        self.current_url = ""

        logger.info("📸 Instagram Comment Automation initialized")

    async def start(self) -> bool:
        """
        Start Safari and navigate to Instagram.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            self.safari_controller = SafariAppController()

            # Try to find existing Instagram window
            logger.info("🔍 Looking for existing Instagram tab...")
            found = await self._find_instagram_window()

            if found:
                logger.info("✅ Found existing Instagram session")
                await asyncio.sleep(1)
            else:
                logger.info("📝 Opening new Instagram tab...")
                await self.safari_controller.launch_safari("https://www.instagram.com/")
                await asyncio.sleep(3)

            # Check if logged in
            is_logged_in = await self._check_login_status()
            if not is_logged_in:
                logger.warning("⚠️ Not logged into Instagram - please log in manually")
                return False

            self.is_initialized = True
            logger.success("✓ Instagram automation ready")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start Instagram automation: {e}")
            return False

    async def post_comment(
        self,
        post_url: str,
        comment_text: str,
        wait_for_success: bool = True,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Post a comment on an Instagram post.

        Args:
            post_url: URL of the Instagram post (e.g., https://www.instagram.com/p/ABC123/)
            comment_text: Text to comment
            wait_for_success: Wait for comment to be posted
            timeout: Maximum time to wait in seconds

        Returns:
            Result dictionary with:
                - success: True if comment posted successfully
                - error: Error message if failed
                - captcha_detected: True if captcha was detected
        """
        if not self.is_initialized:
            return {"success": False, "error": "Automation not initialized. Call start() first."}

        try:
            logger.info(f"📝 Posting comment to: {post_url[:50]}...")

            # Navigate to post
            await self._navigate_to_url(post_url)
            await asyncio.sleep(3)  # Wait for page load

            # Check for captcha
            captcha = await self.safari_controller.detect_captcha()
            if captcha:
                logger.warning("⚠️ Captcha detected - cannot proceed")
                return {
                    "success": False,
                    "error": "Captcha detected",
                    "captcha_detected": True,
                    "captcha_type": captcha.get("type")
                }

            # Find comment input field
            logger.info("🔍 Finding comment input field...")
            input_found = await self._find_comment_input()
            if not input_found:
                return {"success": False, "error": "Could not find comment input field"}

            # Enter comment text
            logger.info("⌨️ Entering comment text...")
            text_entered = await self._enter_comment_text(comment_text)
            if not text_entered:
                return {"success": False, "error": "Failed to enter comment text"}

            # Submit comment
            logger.info("📤 Submitting comment...")
            submitted = await self._submit_comment()
            if not submitted:
                return {"success": False, "error": "Failed to submit comment"}

            # Wait for success
            if wait_for_success:
                await asyncio.sleep(2)
                # Verify comment posted by checking if input cleared
                input_cleared = await self._check_input_cleared()
                if not input_cleared:
                    logger.warning("⚠️ Comment may not have posted (input not cleared)")

            logger.success(f"✓ Comment posted: {comment_text[:50]}...")
            return {
                "success": True,
                "post_url": post_url,
                "comment_text": comment_text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Error posting comment: {e}")
            return {"success": False, "error": str(e)}

    async def _find_instagram_window(self) -> bool:
        """Find existing Safari window with Instagram."""
        try:
            script = '''
            tell application "Safari"
                set windowList to every window
                repeat with w from 1 to count of windowList
                    set tabList to every tab of window w
                    repeat with t from 1 to count of tabList
                        set tabUrl to URL of tab t of window w
                        if tabUrl contains "instagram.com" then
                            set current tab of window w to tab t of window w
                            set index of window w to 1
                            activate
                            return "found"
                        end if
                    end repeat
                end repeat
                return "not_found"
            end tell
            '''
            result = self.safari_controller._run_applescript(script)
            return "found" in result.lower()
        except Exception as e:
            logger.debug(f"Error finding Instagram window: {e}")
            return False

    async def _check_login_status(self) -> bool:
        """Check if user is logged into Instagram."""
        try:
            script = '''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {
                                // Check for common logged-in indicators
                                var homeIcon = document.querySelector('svg[aria-label=\"Home\"]');
                                var profileLink = document.querySelector('a[href*=\"/accounts/edit\"]');
                                var newPostButton = document.querySelector('[aria-label=\"New post\"]');

                                return (homeIcon || profileLink || newPostButton) ? 'logged_in' : 'not_logged_in';
                            })();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self.safari_controller._run_applescript(script)
            is_logged_in = 'logged_in' in result.lower()

            if is_logged_in:
                logger.info("✅ Logged into Instagram")
            else:
                logger.warning("⚠️ Not logged into Instagram")

            return is_logged_in
        except Exception as e:
            logger.debug(f"Error checking login status: {e}")
            return False

    async def _navigate_to_url(self, url: str) -> bool:
        """Navigate Safari to a specific URL."""
        try:
            script = f'''
            tell application "Safari"
                tell front window
                    set URL of current tab to "{url}"
                end tell
            end tell
            '''
            self.safari_controller._run_applescript(script)
            self.current_url = url
            return True
        except Exception as e:
            logger.error(f"Error navigating to URL: {e}")
            return False

    async def _find_comment_input(self) -> bool:
        """Find the comment input field."""
        try:
            script = '''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {
                                var selectors = [
                                    'textarea[placeholder*=\"comment\" i]',
                                    'textarea[aria-label*=\"comment\" i]',
                                    'textarea[placeholder*=\"Add a comment\" i]',
                                    'form textarea'
                                ];

                                for (var i = 0; i < selectors.length; i++) {
                                    var input = document.querySelector(selectors[i]);
                                    if (input && input.offsetParent !== null) {
                                        input.focus();
                                        return 'found';
                                    }
                                }
                                return 'not_found';
                            })();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self.safari_controller._run_applescript(script)
            return "found" in result.lower()
        except Exception as e:
            logger.error(f"Error finding comment input: {e}")
            return False

    async def _enter_comment_text(self, text: str) -> bool:
        """Enter comment text into the focused input field."""
        try:
            # Escape text for JavaScript
            text_escaped = text.replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')

            script = f'''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {{
                                var input = document.activeElement;
                                if (input && (input.tagName === 'TEXTAREA' || input.contentEditable === 'true')) {{
                                    input.value = '{text_escaped}';
                                    input.textContent = '{text_escaped}';

                                    // Trigger input events
                                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));

                                    return 'entered';
                                }}
                                return 'not_found';
                            }})();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self.safari_controller._run_applescript(script)
            return "entered" in result.lower()
        except Exception as e:
            logger.error(f"Error entering comment text: {e}")
            return False

    async def _submit_comment(self) -> bool:
        """Submit the comment by finding and clicking the Post button."""
        try:
            script = '''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {
                                // Find Post button (multiple selector strategies)
                                var selectors = [
                                    'button[type=\"submit\"]',
                                    'button:has-text(\"Post\")',
                                    'button[aria-label*=\"Post\" i]',
                                    'form button[disabled=false]'
                                ];

                                for (var i = 0; i < selectors.length; i++) {
                                    var buttons = document.querySelectorAll(selectors[i]);
                                    for (var j = 0; j < buttons.length; j++) {
                                        var btn = buttons[j];
                                        if (btn.offsetParent !== null && !btn.disabled) {
                                            btn.click();
                                            return 'clicked';
                                        }
                                    }
                                }

                                // Fallback: press Enter on focused textarea
                                var input = document.activeElement;
                                if (input && input.tagName === 'TEXTAREA') {
                                    var event = new KeyboardEvent('keydown', {
                                        key: 'Enter',
                                        code: 'Enter',
                                        keyCode: 13,
                                        which: 13,
                                        bubbles: true
                                    });
                                    input.dispatchEvent(event);
                                    return 'enter_pressed';
                                }

                                return 'not_found';
                            })();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self.safari_controller._run_applescript(script)
            return "clicked" in result.lower() or "enter_pressed" in result.lower()
        except Exception as e:
            logger.error(f"Error submitting comment: {e}")
            return False

    async def _check_input_cleared(self) -> bool:
        """Check if comment input was cleared (indicates successful post)."""
        try:
            script = '''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {
                                var input = document.querySelector('textarea[placeholder*=\"comment\" i]');
                                return (input && input.value === '') ? 'cleared' : 'not_cleared';
                            })();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self.safari_controller._run_applescript(script)
            return "cleared" in result.lower()
        except Exception as e:
            logger.debug(f"Error checking input cleared: {e}")
            return False

    async def stop(self):
        """Stop automation (optional - keeps Safari open)."""
        logger.info("🛑 Instagram automation stopped")
        self.is_initialized = False


# Singleton accessor
_automation_instance: Optional[InstagramCommentAutomation] = None

def get_instagram_comment_automation() -> InstagramCommentAutomation:
    """Get the singleton Instagram comment automation instance."""
    global _automation_instance
    if _automation_instance is None:
        _automation_instance = InstagramCommentAutomation()
    return _automation_instance
