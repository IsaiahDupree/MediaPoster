"""
Sora Controller - Safari automation for sora.chatgpt.com

Controls Safari.app to navigate Sora, input prompts, and manage video generation.
"""
import asyncio
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger


class SoraController:
    """Controls Safari.app to interact with Sora video generation."""
    
    SORA_URL = "https://sora.com"
    SORA_CREATE_URL = "https://sora.com/create"
    
    def __init__(self):
        self.session_active = False
        self.last_prompt = None
        self.generation_start_time = None
    
    def _run_applescript(self, script: str, timeout: int = 30) -> str:
        """Execute AppleScript and return output."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"AppleScript error: {e.stderr}")
            if "not allowed assistive access" in e.stderr.lower():
                logger.error("⚠️  Safari automation requires permissions!")
                logger.info("Go to: System Settings > Privacy & Security > Automation")
                logger.info("Enable Terminal/IDE to control Safari")
            raise
        except subprocess.TimeoutExpired:
            logger.warning(f"AppleScript timeout after {timeout}s")
            raise
    
    async def launch_sora(self) -> bool:
        """Launch Safari and navigate to Sora."""
        logger.info("🚀 Launching Safari with Sora...")
        
        # First check if Sora tab already exists
        existing = await self.find_sora_tab()
        if existing:
            logger.info("✅ Found existing Sora tab, activating...")
            await self.activate_sora_tab(existing)
            return True
        
        # Open Safari and navigate to Sora
        try:
            script = '''
            tell application "Safari"
                activate
                delay 1
                if (count of windows) = 0 then
                    make new document
                end if
                set URL of current tab of front window to "https://sora.com"
            end tell
            '''
            self._run_applescript(script, timeout=15)
            await asyncio.sleep(3)
            logger.success("✅ Safari opened with Sora")
            return True
        except Exception as e:
            logger.error(f"Failed to launch Sora: {e}")
            return False
    
    async def find_sora_tab(self) -> Optional[Dict]:
        """Find existing Sora tab in Safari."""
        try:
            script = '''
            tell application "Safari"
                set windowList to every window
                repeat with w from 1 to count of windowList
                    set tabList to every tab of window w
                    repeat with t from 1 to count of tabList
                        set tabUrl to URL of tab t of window w
                        if tabUrl contains "sora.com" or tabUrl contains "sora.chatgpt.com" then
                            return w & "," & t & "," & tabUrl
                        end if
                    end repeat
                end repeat
                return "not_found"
            end tell
            '''
            result = self._run_applescript(script, timeout=10)
            
            if "not_found" in result or not result:
                return None
            
            parts = result.split(",", 2)
            if len(parts) >= 3:
                return {
                    "window_index": int(parts[0]),
                    "tab_index": int(parts[1]),
                    "url": parts[2]
                }
            return None
        except Exception as e:
            logger.debug(f"Error finding Sora tab: {e}")
            return None
    
    async def activate_sora_tab(self, tab_info: Dict) -> bool:
        """Activate a specific Sora tab."""
        try:
            script = f'''
            tell application "Safari"
                activate
                set current tab of window {tab_info["window_index"]} to tab {tab_info["tab_index"]} of window {tab_info["window_index"]}
                set index of window {tab_info["window_index"]} to 1
            end tell
            '''
            self._run_applescript(script, timeout=10)
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Failed to activate Sora tab: {e}")
            return False
    
    async def check_login_status(self) -> Dict:
        """Check if user is logged into Sora."""
        try:
            script = '''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {
                                try {
                                    // Check for user avatar or profile elements
                                    var avatar = document.querySelector('[data-testid=\\"user-avatar\\"], [class*=\\"avatar\\"], [class*=\\"profile\\"], img[alt*=\\"profile\\"]');
                                    var createButton = document.querySelector('button[class*=\\"create\\"], [data-testid=\\"create-button\\"]');
                                    var loginButton = document.querySelector('button:contains(\\'Log in\\'), a[href*=\\'login\\'], [data-testid=\\"login-button\\"]');
                                    
                                    // Check page content for login indicators
                                    var pageText = document.body.innerText || '';
                                    var hasLoginPrompt = pageText.includes('Log in') || pageText.includes('Sign in');
                                    var hasCreateUI = pageText.includes('Create') && (pageText.includes('video') || pageText.includes('prompt'));
                                    
                                    return JSON.stringify({
                                        logged_in: !!avatar || hasCreateUI,
                                        has_login_button: !!loginButton || hasLoginPrompt,
                                        has_create_ui: hasCreateUI,
                                        url: window.location.href
                                    });
                                } catch(e) {
                                    return JSON.stringify({error: e.toString(), url: window.location.href});
                                }
                            })();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self._run_applescript(script, timeout=10)
            return json.loads(result)
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return {"logged_in": False, "error": str(e)}
    
    async def navigate_to_create(self) -> bool:
        """Navigate to the create/prompt page."""
        try:
            script = f'''
            tell application "Safari"
                tell front window
                    set URL of current tab to "{self.SORA_CREATE_URL}"
                end tell
            end tell
            '''
            self._run_applescript(script, timeout=10)
            await asyncio.sleep(2)
            logger.info("📍 Navigated to Sora create page")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to create: {e}")
            return False
    
    async def get_page_state(self) -> Dict:
        """Get current page state including UI elements."""
        try:
            script = '''
            tell application "Safari"
                tell front window
                    tell current tab
                        set pageURL to URL
                        set pageTitle to name
                        
                        set jsResult to do JavaScript "
                            (function() {
                                try {
                                    // Find prompt input
                                    var promptInput = document.querySelector('textarea, [contenteditable=\\"true\\"], input[type=\\"text\\"][placeholder*=\\"prompt\\"]');
                                    var generateBtn = document.querySelector('button[class*=\\"generate\\"], button[class*=\\"create\\"], button[type=\\"submit\\"]');
                                    
                                    // Find video elements
                                    var videos = document.querySelectorAll('video');
                                    var videoCards = document.querySelectorAll('[class*=\\"video-card\\"], [class*=\\"generation\\"]');
                                    
                                    // Find progress indicators
                                    var progress = document.querySelector('[class*=\\"progress\\"], [class*=\\"loading\\"], [role=\\"progressbar\\"]');
                                    
                                    return JSON.stringify({
                                        url: window.location.href,
                                        title: document.title,
                                        has_prompt_input: !!promptInput,
                                        prompt_input_selector: promptInput ? (promptInput.tagName + (promptInput.className ? '.' + promptInput.className.split(' ')[0] : '')) : null,
                                        has_generate_button: !!generateBtn,
                                        video_count: videos.length,
                                        video_cards: videoCards.length,
                                        has_progress: !!progress,
                                        body_text_sample: (document.body.innerText || '').substring(0, 500)
                                    });
                                } catch(e) {
                                    return JSON.stringify({error: e.toString()});
                                }
                            })();
                        "
                        
                        return jsResult
                    end tell
                end tell
            end tell
            '''
            result = self._run_applescript(script, timeout=15)
            return json.loads(result)
        except Exception as e:
            logger.error(f"Error getting page state: {e}")
            return {"error": str(e)}
    
    async def input_prompt(self, prompt: str, character: Optional[str] = None) -> bool:
        """Input a prompt into the Sora text field.
        
        Args:
            prompt: The video generation prompt
            character: Optional @ character to use (e.g., "@isaiahdupree")
        """
        full_prompt = prompt
        if character and not character.startswith("@"):
            character = f"@{character}"
        if character and character not in prompt:
            full_prompt = f"{character} {prompt}"
        
        # Escape special characters for JavaScript
        escaped_prompt = full_prompt.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
        
        try:
            script = f'''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {{
                                try {{
                                    // Find the prompt input - try multiple selectors
                                    var input = document.querySelector('textarea') ||
                                               document.querySelector('[contenteditable=\\"true\\"]') ||
                                               document.querySelector('input[type=\\"text\\"]');
                                    
                                    if (!input) {{
                                        return JSON.stringify({{success: false, error: 'No prompt input found'}});
                                    }}
                                    
                                    // Focus and clear
                                    input.focus();
                                    
                                    // Set the value
                                    if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {{
                                        input.value = '{escaped_prompt}';
                                        // Trigger input event
                                        input.dispatchEvent(new Event('input', {{bubbles: true}}));
                                        input.dispatchEvent(new Event('change', {{bubbles: true}}));
                                    }} else {{
                                        // For contenteditable
                                        input.innerText = '{escaped_prompt}';
                                        input.dispatchEvent(new Event('input', {{bubbles: true}}));
                                    }}
                                    
                                    return JSON.stringify({{success: true, prompt_length: '{escaped_prompt}'.length}});
                                }} catch(e) {{
                                    return JSON.stringify({{success: false, error: e.toString()}});
                                }}
                            }})();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self._run_applescript(script, timeout=10)
            result_data = json.loads(result)
            
            if result_data.get("success"):
                logger.info(f"✅ Prompt entered ({len(full_prompt)} chars)")
                self.last_prompt = full_prompt
                return True
            else:
                logger.error(f"Failed to input prompt: {result_data.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error inputting prompt: {e}")
            return False
    
    async def click_generate(self) -> bool:
        """Click the generate/create button."""
        try:
            script = '''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {
                                try {
                                    // Find generate button - try multiple selectors
                                    var btn = document.querySelector('button[class*=\\"generate\\"]') ||
                                             document.querySelector('button[class*=\\"create\\"]') ||
                                             document.querySelector('button[type=\\"submit\\"]') ||
                                             Array.from(document.querySelectorAll('button')).find(b => 
                                                 b.textContent.toLowerCase().includes('generate') ||
                                                 b.textContent.toLowerCase().includes('create')
                                             );
                                    
                                    if (!btn) {
                                        return JSON.stringify({success: false, error: 'Generate button not found'});
                                    }
                                    
                                    // Check if button is disabled
                                    if (btn.disabled) {
                                        return JSON.stringify({success: false, error: 'Button is disabled'});
                                    }
                                    
                                    btn.click();
                                    return JSON.stringify({success: true, button_text: btn.textContent.trim()});
                                } catch(e) {
                                    return JSON.stringify({success: false, error: e.toString()});
                                }
                            })();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self._run_applescript(script, timeout=10)
            result_data = json.loads(result)
            
            if result_data.get("success"):
                logger.info(f"✅ Clicked generate button: {result_data.get('button_text')}")
                self.generation_start_time = datetime.now()
                return True
            else:
                logger.error(f"Failed to click generate: {result_data.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error clicking generate: {e}")
            return False
    
    async def submit_prompt(self, prompt: str, character: Optional[str] = None) -> bool:
        """Submit a prompt for video generation (input + click generate)."""
        # Input the prompt
        if not await self.input_prompt(prompt, character):
            return False
        
        await asyncio.sleep(0.5)
        
        # Click generate
        if not await self.click_generate():
            return False
        
        logger.info("🎬 Video generation started!")
        return True
    
    async def get_generation_status(self) -> Dict:
        """Check the status of current video generation."""
        try:
            script = '''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {
                                try {
                                    // Look for progress indicators
                                    var progress = document.querySelector('[class*=\\"progress\\"]');
                                    var loading = document.querySelector('[class*=\\"loading\\"], [class*=\\"spinner\\"]');
                                    var progressBar = document.querySelector('[role=\\"progressbar\\"]');
                                    
                                    // Look for completed video
                                    var video = document.querySelector('video[src]');
                                    var videoCard = document.querySelector('[class*=\\"video-card\\"][class*=\\"complete\\"]');
                                    
                                    // Look for error messages
                                    var error = document.querySelector('[class*=\\"error\\"]');
                                    
                                    // Check for percentage in text
                                    var percentMatch = (document.body.innerText || '').match(/(\\d+)%/);
                                    var percent = percentMatch ? parseInt(percentMatch[1]) : null;
                                    
                                    var status = 'unknown';
                                    if (video && video.src) {
                                        status = 'completed';
                                    } else if (error) {
                                        status = 'failed';
                                    } else if (loading || progress || progressBar) {
                                        status = 'generating';
                                    }
                                    
                                    return JSON.stringify({
                                        status: status,
                                        progress_percent: percent,
                                        has_video: !!(video && video.src),
                                        video_src: video ? video.src : null,
                                        has_error: !!error,
                                        error_text: error ? error.textContent.trim() : null
                                    });
                                } catch(e) {
                                    return JSON.stringify({status: 'error', error: e.toString()});
                                }
                            })();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self._run_applescript(script, timeout=10)
            return json.loads(result)
        except Exception as e:
            logger.error(f"Error getting generation status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def wait_for_generation(self, timeout_minutes: int = 10, poll_interval: int = 10) -> Dict:
        """Wait for video generation to complete.
        
        Args:
            timeout_minutes: Maximum time to wait
            poll_interval: Seconds between status checks
            
        Returns:
            Final status dict with video_src if successful
        """
        logger.info(f"⏳ Waiting for video generation (timeout: {timeout_minutes}min)...")
        
        start_time = datetime.now()
        max_seconds = timeout_minutes * 60
        
        while True:
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if elapsed > max_seconds:
                logger.error(f"❌ Generation timeout after {timeout_minutes} minutes")
                return {"status": "timeout", "elapsed_seconds": elapsed}
            
            status = await self.get_generation_status()
            
            if status.get("status") == "completed":
                logger.success(f"✅ Video generation completed in {elapsed:.0f}s")
                return status
            
            if status.get("status") == "failed":
                logger.error(f"❌ Generation failed: {status.get('error_text')}")
                return status
            
            progress = status.get("progress_percent")
            if progress:
                logger.info(f"📊 Generation progress: {progress}% ({elapsed:.0f}s elapsed)")
            else:
                logger.debug(f"⏳ Still generating... ({elapsed:.0f}s elapsed)")
            
            await asyncio.sleep(poll_interval)
    
    async def get_video_download_url(self) -> Optional[str]:
        """Get the download URL for the generated video."""
        try:
            script = '''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {
                                try {
                                    // Find video element with source
                                    var video = document.querySelector('video[src]');
                                    if (video && video.src) {
                                        return video.src;
                                    }
                                    
                                    // Look for download button
                                    var downloadBtn = document.querySelector('[class*=\\"download\\"], button[download], a[download]');
                                    if (downloadBtn && downloadBtn.href) {
                                        return downloadBtn.href;
                                    }
                                    
                                    // Check source elements
                                    var source = document.querySelector('video source[src]');
                                    if (source) {
                                        return source.src;
                                    }
                                    
                                    return '';
                                } catch(e) {
                                    return '';
                                }
                            })();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self._run_applescript(script, timeout=10)
            
            if result and result.startswith("http"):
                logger.info(f"📥 Found video URL: {result[:80]}...")
                return result
            return None
        except Exception as e:
            logger.error(f"Error getting video URL: {e}")
            return None
    
    async def click_download_button(self) -> bool:
        """Click the download button if available."""
        try:
            script = '''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "
                            (function() {
                                try {
                                    // Find download button
                                    var btn = document.querySelector('[class*=\\"download\\"]') ||
                                             document.querySelector('button[download]') ||
                                             document.querySelector('a[download]') ||
                                             Array.from(document.querySelectorAll('button')).find(b =>
                                                 b.textContent.toLowerCase().includes('download')
                                             );
                                    
                                    if (!btn) {
                                        return JSON.stringify({success: false, error: 'Download button not found'});
                                    }
                                    
                                    btn.click();
                                    return JSON.stringify({success: true});
                                } catch(e) {
                                    return JSON.stringify({success: false, error: e.toString()});
                                }
                            })();
                        "
                    end tell
                end tell
            end tell
            '''
            result = self._run_applescript(script, timeout=10)
            result_data = json.loads(result)
            
            if result_data.get("success"):
                logger.info("✅ Clicked download button")
                return True
            else:
                logger.warning(f"Download button not found: {result_data.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Error clicking download: {e}")
            return False


async def test_sora_controller():
    """Test the Sora controller functionality."""
    controller = SoraController()
    
    print("\n🧪 Testing Sora Controller...")
    
    # Launch Sora
    print("\n1. Launching Sora...")
    success = await controller.launch_sora()
    print(f"   Launch: {'✅' if success else '❌'}")
    
    if not success:
        print("   Cannot continue without launching Sora")
        return
    
    await asyncio.sleep(3)
    
    # Check login status
    print("\n2. Checking login status...")
    login_status = await controller.check_login_status()
    print(f"   Logged in: {login_status.get('logged_in')}")
    print(f"   Has create UI: {login_status.get('has_create_ui')}")
    
    # Get page state
    print("\n3. Getting page state...")
    state = await controller.get_page_state()
    print(f"   URL: {state.get('url')}")
    print(f"   Has prompt input: {state.get('has_prompt_input')}")
    print(f"   Has generate button: {state.get('has_generate_button')}")
    
    print("\n✅ Sora Controller test complete!")
    print("   To submit a prompt, call: controller.submit_prompt('Your prompt here', '@isaiahdupree')")


if __name__ == "__main__":
    asyncio.run(test_sora_controller())
