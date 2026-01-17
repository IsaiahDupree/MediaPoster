#!/usr/bin/env python3
"""
Threads Safari Automation - Full posting capabilities via Safari browser.

Features:
- Post text threads
- Attach images/videos
- Reply to existing threads
- URL/ID capture after posting
- Session manager integration

Uses AppleScript to control Safari browser for threads.net automation.
"""

import subprocess
import time
import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from loguru import logger

# Import centralized Safari session manager
try:
    from automation.safari_session_manager import SafariSessionManager, Platform
    HAS_SESSION_MANAGER = True
except ImportError:
    try:
        from safari_session_manager import SafariSessionManager, Platform
        HAS_SESSION_MANAGER = True
    except ImportError:
        HAS_SESSION_MANAGER = False
        logger.warning("Safari session manager not available")

THREADS_URL = "https://www.threads.net"
THREADS_COMPOSE_URL = "https://www.threads.net/compose"


@dataclass
class ThreadsPost:
    """Represents a posted thread."""
    post_id: str
    post_url: str
    text: str
    media_count: int = 0
    posted_at: str = ""
    is_reply: bool = False
    reply_to_id: Optional[str] = None


class SafariThreadsPoster:
    """
    Safari-based Threads automation using AppleScript.
    Similar architecture to SafariTwitterPoster.
    """
    
    def __init__(self):
        self.session_manager = SafariSessionManager() if HAS_SESSION_MANAGER else None
        self.last_post_url = None
        self.last_post_id = None
    
    def _run_applescript(self, script: str) -> Tuple[bool, str]:
        """Execute AppleScript and return (success, output)."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Script timed out"
        except Exception as e:
            return False, str(e)
    
    def _escape_for_js(self, text: str) -> str:
        """Escape text for JavaScript injection."""
        return (text
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("'", "\\'")
                .replace("\n", "\\n")
                .replace("\r", ""))
    
    def require_login(self) -> bool:
        """Check if logged into Threads before automation."""
        if self.session_manager:
            return self.session_manager.require_login(Platform.THREADS)
        logger.warning("Session manager not available, assuming logged in")
        return True
    
    def open_threads(self, url: str = THREADS_URL) -> bool:
        """Open Safari and navigate to Threads."""
        script = f'''
        tell application "Safari"
            activate
            if (count of windows) = 0 then
                make new document
            end if
            set URL of front document to "{url}"
        end tell
        
        delay 3
        return "opened"
        '''
        success, output = self._run_applescript(script)
        logger.info(f"Open Threads: {success}")
        return success
    
    def open_compose(self) -> bool:
        """Open the compose modal on Threads."""
        # First try clicking the compose button
        script = '''
        tell application "Safari"
            activate
            tell front document
                do JavaScript "
                    (function() {
                        // Look for compose/new post button
                        var composeBtn = document.querySelector('[aria-label*=\"Create\"], [aria-label*=\"New thread\"], [aria-label*=\"Post\"], svg[aria-label*=\"New\"]');
                        if (!composeBtn) {
                            // Try finding by role
                            var buttons = document.querySelectorAll('div[role=\"button\"], button');
                            for (var i = 0; i < buttons.length; i++) {
                                var text = buttons[i].innerText || '';
                                var label = buttons[i].getAttribute('aria-label') || '';
                                if (text.includes('Post') || text.includes('Create') || label.includes('Create') || label.includes('New')) {
                                    composeBtn = buttons[i];
                                    break;
                                }
                            }
                        }
                        if (composeBtn) {
                            composeBtn.click();
                            return 'clicked';
                        }
                        return 'not_found';
                    })();
                "
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        
        if success and result == 'clicked':
            time.sleep(2)
            return True
        
        # Fallback: navigate directly to compose URL
        logger.info("Compose button not found, navigating directly...")
        return self.open_threads(THREADS_COMPOSE_URL)
    
    def type_thread_text(self, text: str) -> bool:
        """Type text into the Threads compose area using JS injection."""
        escaped_text = self._escape_for_js(text)
        
        script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "
                    (function() {{
                        // Find the text input area
                        var input = document.querySelector('[contenteditable=\"true\"], textarea[placeholder*=\"thread\"], textarea[placeholder*=\"Start\"], div[data-contents=\"true\"]');
                        if (!input) {{
                            // Try finding by role
                            input = document.querySelector('[role=\"textbox\"]');
                        }}
                        if (input) {{
                            input.focus();
                            if (input.tagName === 'TEXTAREA') {{
                                input.value = '{escaped_text}';
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            }} else {{
                                // contenteditable div
                                input.innerText = '{escaped_text}';
                                input.dispatchEvent(new InputEvent('input', {{ bubbles: true, data: '{escaped_text}' }}));
                            }}
                            return 'typed';
                        }}
                        return 'input_not_found';
                    }})();
                "
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        
        if success and result == 'typed':
            logger.info("✅ Text entered via JS injection")
            return True
        
        # Fallback: use keyboard typing
        logger.warning(f"JS typing failed ({result}), using keyboard...")
        return self._type_via_keyboard(text)
    
    def _type_via_keyboard(self, text: str) -> bool:
        """Type text using keyboard simulation."""
        escaped_text = text.replace('"', '\\"').replace("\\", "\\\\")
        
        script = f'''
        tell application "System Events"
            tell process "Safari"
                keystroke "{escaped_text}"
            end tell
        end tell
        return "typed"
        '''
        success, result = self._run_applescript(script)
        return success
    
    def attach_media(self, media_path: str) -> bool:
        """Attach an image or video to the thread."""
        if not os.path.exists(media_path):
            logger.error(f"Media file not found: {media_path}")
            return False
        
        # Click media/attach button
        script = '''
        tell application "Safari"
            tell front document
                do JavaScript "
                    (function() {
                        var mediaBtn = document.querySelector('[aria-label*=\"Add media\"], [aria-label*=\"Photo\"], [aria-label*=\"image\"], input[type=\"file\"]');
                        if (!mediaBtn) {
                            // Look for SVG icons that might be media buttons
                            var svgs = document.querySelectorAll('svg');
                            for (var i = 0; i < svgs.length; i++) {
                                var label = svgs[i].getAttribute('aria-label') || '';
                                if (label.toLowerCase().includes('photo') || label.toLowerCase().includes('media') || label.toLowerCase().includes('image')) {
                                    mediaBtn = svgs[i].closest('div[role=\"button\"], button') || svgs[i];
                                    break;
                                }
                            }
                        }
                        if (mediaBtn) {
                            if (mediaBtn.tagName === 'INPUT') {
                                return 'file_input';
                            }
                            mediaBtn.click();
                            return 'clicked';
                        }
                        return 'not_found';
                    })();
                "
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        
        if not success or result == 'not_found':
            logger.warning("Could not find media button")
            return False
        
        time.sleep(1)
        
        # Handle file picker
        abs_path = os.path.abspath(media_path)
        directory = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)
        
        file_picker_script = f'''
        tell application "System Events"
            tell process "Safari"
                delay 1
                keystroke "g" using {{command down, shift down}}
                delay 0.5
                keystroke "{directory}"
                delay 0.3
                keystroke return
                delay 1
                keystroke "{filename}"
                delay 0.3
                keystroke return
            end tell
        end tell
        return "selected"
        '''
        success, result = self._run_applescript(file_picker_script)
        
        if success:
            time.sleep(3)  # Wait for upload
            logger.info(f"✅ Media attached: {filename}")
            return True
        
        return False
    
    def click_post_button(self) -> bool:
        """Click the Post button to publish the thread."""
        script = '''
        tell application "Safari"
            tell front document
                do JavaScript "
                    (function() {
                        // Find post button
                        var postBtn = document.querySelector('div[role=\"button\"]:not([aria-disabled=\"true\"])[tabindex=\"0\"]');
                        if (!postBtn) {
                            var buttons = document.querySelectorAll('div[role=\"button\"], button');
                            for (var i = 0; i < buttons.length; i++) {
                                var text = buttons[i].innerText || '';
                                if (text.trim() === 'Post' || text.trim() === 'Reply') {
                                    if (!buttons[i].getAttribute('aria-disabled')) {
                                        postBtn = buttons[i];
                                        break;
                                    }
                                }
                            }
                        }
                        if (postBtn) {
                            postBtn.click();
                            return 'clicked';
                        }
                        return 'not_found';
                    })();
                "
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        
        if success and result == 'clicked':
            logger.info("✅ Post button clicked")
            return True
        
        # Fallback: keyboard shortcut
        logger.warning("Post button not found, trying keyboard...")
        shortcut_script = '''
        tell application "System Events"
            tell process "Safari"
                keystroke return using {command down}
            end tell
        end tell
        return "sent"
        '''
        success, _ = self._run_applescript(shortcut_script)
        return success
    
    def verify_post_success(self) -> Dict[str, Any]:
        """Verify the thread was posted and capture URL/ID."""
        time.sleep(3)
        
        # Check for success indicators and capture URL
        for attempt in range(10):
            script = '''
            tell application "Safari"
                set currentURL to URL of front document
                tell front document
                    set result to do JavaScript "
                        (function() {
                            var url = window.location.href;
                            // Check if we're on a post page
                            if (url.includes('/post/') || url.includes('/t/')) {
                                return 'posted:' + url;
                            }
                            // Check for success toast/notification
                            var toast = document.querySelector('[role=\"status\"], [role=\"alert\"]');
                            if (toast && toast.innerText.toLowerCase().includes('posted')) {
                                return 'success_toast';
                            }
                            // Check if compose modal closed
                            var compose = document.querySelector('[aria-label*=\"Create\"][aria-modal=\"true\"], [role=\"dialog\"]');
                            if (!compose) {
                                return 'modal_closed';
                            }
                            return 'waiting';
                        })();
                    "
                end tell
                return result
            end tell
            '''
            success, result = self._run_applescript(script)
            
            if 'posted:' in result:
                post_url = result.split('posted:')[1].strip()
                # Extract post ID from URL
                match = re.search(r'/post/([A-Za-z0-9_-]+)', post_url)
                if not match:
                    match = re.search(r'/t/([A-Za-z0-9_-]+)', post_url)
                
                post_id = match.group(1) if match else None
                
                self.last_post_url = post_url
                self.last_post_id = post_id
                
                logger.success(f"✅ Thread posted: {post_id}")
                return {
                    'success': True,
                    'post_url': post_url,
                    'post_id': post_id
                }
            
            if result in ['success_toast', 'modal_closed']:
                # Try to find the post on profile
                return self._find_recent_post_on_profile()
            
            logger.debug(f"Waiting for post confirmation... ({attempt+1}/10)")
            time.sleep(1)
        
        # Fallback: check profile
        return self._find_recent_post_on_profile()
    
    def _find_recent_post_on_profile(self) -> Dict[str, Any]:
        """Find the most recent post on the user's profile."""
        logger.info("Checking profile for recently posted thread...")
        
        # Navigate to profile
        script = '''
        tell application "Safari"
            tell front document
                do JavaScript "
                    (function() {
                        // Find profile link
                        var profileLink = document.querySelector('a[href*=\"/@\"]');
                        if (profileLink) {
                            window.location.href = profileLink.href;
                            return 'navigating';
                        }
                        return 'profile_not_found';
                    })();
                "
            end tell
        end tell
        '''
        self._run_applescript(script)
        time.sleep(3)
        
        # Find most recent post
        script = '''
        tell application "Safari"
            tell front document
                do JavaScript "
                    (function() {
                        var posts = document.querySelectorAll('article, [data-pressable-container=\"true\"]');
                        if (posts.length > 0) {
                            var firstPost = posts[0];
                            var link = firstPost.querySelector('a[href*=\"/post/\"], a[href*=\"/t/\"]');
                            if (link) {
                                return 'found:' + link.href;
                            }
                        }
                        return 'not_found';
                    })();
                "
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        
        if success and 'found:' in result:
            post_url = result.split('found:')[1].strip()
            match = re.search(r'/post/([A-Za-z0-9_-]+)', post_url)
            if not match:
                match = re.search(r'/t/([A-Za-z0-9_-]+)', post_url)
            
            post_id = match.group(1) if match else None
            
            self.last_post_url = post_url
            self.last_post_id = post_id
            
            logger.success(f"✅ Found recent thread: {post_id}")
            return {
                'success': True,
                'post_url': post_url,
                'post_id': post_id
            }
        
        return {
            'success': False,
            'error': 'Could not verify post'
        }
    
    def post_thread(self, 
                    text: str, 
                    media_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Post a new thread with optional media.
        
        Args:
            text: Thread text (up to 500 characters)
            media_paths: Optional list of image/video paths
        
        Returns:
            Dict with success status and post URL/ID
        """
        logger.info(f"Posting thread: {text[:50]}...")
        
        # Validate text length
        if len(text) > 500:
            return {'success': False, 'error': 'Thread text exceeds 500 character limit'}
        
        # Step 1: Check login
        if HAS_SESSION_MANAGER:
            if not self.require_login():
                return {
                    'success': False,
                    'error': 'Not logged in to Threads. Please log in manually first.',
                    'requires_login': True
                }
            logger.info("✅ Login verified via session manager")
        
        # Step 2: Open compose
        logger.info("Opening compose...")
        if not self.open_compose():
            return {'success': False, 'error': 'Failed to open compose'}
        time.sleep(2)
        
        # Step 3: Attach media if provided
        if media_paths:
            logger.info(f"Attaching {len(media_paths)} media files...")
            for path in media_paths:
                if not self.attach_media(path):
                    logger.warning(f"Failed to attach: {path}")
            time.sleep(2)
        
        # Step 4: Type text
        logger.info("Typing thread...")
        if not self.type_thread_text(text):
            return {'success': False, 'error': 'Failed to type thread text'}
        time.sleep(1)
        
        # Step 5: Post
        logger.info("Clicking post button...")
        if not self.click_post_button():
            return {'success': False, 'error': 'Failed to click post button'}
        
        # Step 6: Verify
        result = self.verify_post_success()
        
        if result.get('success'):
            result['platform'] = 'threads'
            result['method'] = 'safari_automation'
            result['text'] = text
            result['media_count'] = len(media_paths) if media_paths else 0
        
        return result
    
    def reply_to_thread(self,
                        thread_url: str,
                        reply_text: str,
                        media_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Reply to an existing thread.
        
        Args:
            thread_url: URL of the thread to reply to
            reply_text: Reply text
            media_paths: Optional media attachments
        
        Returns:
            Dict with success status and reply URL/ID
        """
        # Extract thread ID from URL
        match = re.search(r'/post/([A-Za-z0-9_-]+)', thread_url)
        if not match:
            match = re.search(r'/t/([A-Za-z0-9_-]+)', thread_url)
        
        thread_id = match.group(1) if match else None
        logger.info(f"Replying to thread {thread_id}...")
        
        # Check login
        if HAS_SESSION_MANAGER:
            if not self.require_login():
                return {'success': False, 'error': 'Not logged in', 'requires_login': True}
        
        # Navigate to thread
        if not self.open_threads(thread_url):
            return {'success': False, 'error': 'Failed to open thread'}
        time.sleep(3)
        
        # Find and click reply button
        script = '''
        tell application "Safari"
            tell front document
                do JavaScript "
                    (function() {
                        var replyBtn = document.querySelector('[aria-label*=\"Reply\"], [aria-label*=\"Comment\"]');
                        if (!replyBtn) {
                            var svgs = document.querySelectorAll('svg');
                            for (var i = 0; i < svgs.length; i++) {
                                var label = svgs[i].getAttribute('aria-label') || '';
                                if (label.toLowerCase().includes('reply') || label.toLowerCase().includes('comment')) {
                                    replyBtn = svgs[i].closest('div[role=\"button\"]') || svgs[i];
                                    break;
                                }
                            }
                        }
                        if (replyBtn) {
                            replyBtn.click();
                            return 'clicked';
                        }
                        return 'not_found';
                    })();
                "
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        
        if not success or result != 'clicked':
            return {'success': False, 'error': 'Could not find reply button'}
        
        time.sleep(2)
        
        # Type reply
        if not self.type_thread_text(reply_text):
            return {'success': False, 'error': 'Failed to type reply'}
        time.sleep(0.5)
        
        # Attach media if provided
        if media_paths:
            for path in media_paths:
                self.attach_media(path)
            time.sleep(2)
        
        # Post reply
        if not self.click_post_button():
            return {'success': False, 'error': 'Failed to post reply'}
        
        # Verify
        result = self.verify_post_success()
        
        if result.get('success'):
            result['reply'] = True
            result['in_reply_to'] = thread_id
            logger.success("✅ Reply posted!")
        
        return result


def test_login_status() -> Dict[str, Any]:
    """Test Threads login status."""
    poster = SafariThreadsPoster()
    if poster.require_login():
        return {'logged_in': True, 'platform': 'threads'}
    return {'logged_in': False, 'platform': 'threads'}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Threads Safari Automation - Full Posting')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Test login
    parser.add_argument('--test-login', action='store_true', help='Test login status')
    
    # Post command
    post_parser = subparsers.add_parser('post', help='Post a thread')
    post_parser.add_argument('text', nargs='+', help='Thread text')
    post_parser.add_argument('--media', '-m', action='append', help='Media file path(s)')
    
    # Reply command
    reply_parser = subparsers.add_parser('reply', help='Reply to a thread')
    reply_parser.add_argument('url', help='Thread URL to reply to')
    reply_parser.add_argument('text', nargs='+', help='Reply text')
    reply_parser.add_argument('--media', '-m', action='append', help='Media file path(s)')
    
    # Open command
    open_parser = subparsers.add_parser('open', help='Open Threads in Safari')
    
    args = parser.parse_args()
    poster = SafariThreadsPoster()
    
    if args.test_login:
        print("=" * 50)
        print("Testing Threads Login Status")
        print("=" * 50)
        result = test_login_status()
        print(f"\nResult: {json.dumps(result, indent=2)}")
    
    elif args.command == 'post':
        text = " ".join(args.text)
        media_paths = args.media if args.media else None
        print("=" * 50)
        print(f"Posting Thread: {text[:50]}...")
        if media_paths:
            print(f"With media: {media_paths}")
        print("=" * 50)
        result = poster.post_thread(text, media_paths)
        print(f"\nResult: {json.dumps(result, indent=2)}")
    
    elif args.command == 'reply':
        text = " ".join(args.text)
        media_paths = args.media if args.media else None
        print("=" * 50)
        print(f"Replying to: {args.url}")
        print(f"Reply: {text[:50]}...")
        print("=" * 50)
        result = poster.reply_to_thread(args.url, text, media_paths)
        print(f"\nResult: {json.dumps(result, indent=2)}")
    
    elif args.command == 'open':
        print("Opening Threads in Safari...")
        if poster.open_threads():
            print("✅ Threads opened")
        else:
            print("❌ Failed to open Threads")
    
    else:
        parser.print_help()
        print("\n" + "=" * 50)
        print("EXAMPLES")
        print("=" * 50)
        print("\n🔍 Check login:")
        print("  python safari_threads_poster.py --test-login")
        print("\n📝 Post thread:")
        print("  python safari_threads_poster.py post 'Hello Threads!'")
        print("\n🖼️  Post with media:")
        print("  python safari_threads_poster.py post 'Check this out!' -m /path/to/image.jpg")
        print("\n💬 Reply:")
        print("  python safari_threads_poster.py reply https://threads.net/@user/post/abc123 'Great thread!'")
        print("\n🌐 Open Threads:")
        print("  python safari_threads_poster.py open")
