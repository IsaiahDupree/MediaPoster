"""
TikTok Login Action Recorder
Watches and records manual login actions for later analysis or automation.
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, BrowserContext
from loguru import logger
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from automation.browser_profile_manager import BrowserProfileManager, BrowserType
from services.tiktok_captcha_solver import TikTokCaptchaSolver
from automation.safari_app_controller import SafariAppController
from automation.sms_code_reader import SMSCodeReader
import browser_cookie3

# Import enhanced recorders (optional - graceful fallback)
try:
    from automation.global_input_recorder import GlobalInputRecorder, is_global_recording_available
    GLOBAL_INPUT_AVAILABLE = is_global_recording_available()
except ImportError:
    GLOBAL_INPUT_AVAILABLE = False
    GlobalInputRecorder = None

try:
    from automation.screenshot_recorder import ScreenshotRecorder
    SCREENSHOT_RECORDER_AVAILABLE = True
except ImportError:
    SCREENSHOT_RECORDER_AVAILABLE = False
    ScreenshotRecorder = None


class TikTokLoginRecorder:
    """Records manual login actions while watching for captchas."""
    
    def __init__(self, browser_type: BrowserType = "safari", profile_name: Optional[str] = None):
        """
        Initialize the recorder.
        
        Args:
            browser_type: "chrome" or "safari"
            profile_name: Profile name to use (e.g., "Default")
        """
        self.browser_manager = BrowserProfileManager()
        self.captcha_solver = TikTokCaptchaSolver()
        self.browser_type = browser_type
        self.profile_name = profile_name
        
        # Recording storage
        self.recorded_actions: List[Dict] = []
        self.start_time: Optional[datetime] = None
        
        # Browser components
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.temp_user_data_dir = None
        self.safari_controller: Optional[SafariAppController] = None
        self.using_actual_safari = False
        self.sms_reader: Optional[SMSCodeReader] = None
        
        # Session storage
        self.session_dir = Path(__file__).parent / "sessions"
        self.session_dir.mkdir(exist_ok=True)
        self.recordings_dir = Path(__file__).parent / "recordings"
        self.recordings_dir.mkdir(exist_ok=True)
        
        # Screenshots directory
        self.screenshots_dir = Path(__file__).parent / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)
        
        # Screenshot counter for sequential naming
        self.screenshot_counter = 0
        self.last_screenshot_time = None
        
        # Enhanced recorders
        self.global_input_recorder = None
        self.screenshot_recorder = None
    
    async def start_browser(self):
        """Start browser with selected profile (Chrome or Safari)."""
        logger.info(f"Starting {self.browser_type} browser...")
        self.playwright = await async_playwright().start()
        
        # Get profile
        profile = None
        if self.profile_name:
            profile = self.browser_manager.select_profile(self.browser_type, self.profile_name)
        else:
            saved_profile = self.browser_manager.get_saved_profile()
            if saved_profile and saved_profile.get("browser") == self.browser_type:
                profile = saved_profile
            else:
                profile = self.browser_manager.select_profile(self.browser_type, "Default")
        
        if not profile:
            raise RuntimeError(f"No {self.browser_type} profile available")
        
        logger.info(f"Using {self.browser_type} profile: {profile['name']}")
        
        # Save profile config for future use
        self.browser_manager.save_profile_config(profile)
        
        # Launch browser based on type
        if self.browser_type == "safari":
            # Launch actual Safari.app browser (not Playwright's WebKit)
            logger.info("Launching actual Safari.app browser...")
            await self._launch_actual_safari(profile)
            
        else:  # Chrome
            # Create profile snapshot
            import tempfile
            import shutil
            
            source_user_data_dir = Path(profile['full_path'])
            source_profile_dir = Path(profile['path'])
            self.temp_user_data_dir = Path(tempfile.mkdtemp())
            
            # Copy Local State
            if (source_user_data_dir / "Local State").exists():
                shutil.copy2(source_user_data_dir / "Local State", 
                            self.temp_user_data_dir / "Local State")
            
            # Copy profile files
            profile_dir_name = source_profile_dir.name
            target_profile_dir = self.temp_user_data_dir / profile_dir_name
            target_profile_dir.mkdir(exist_ok=True)
            
            files_to_copy = [
                "Cookies", "Login Data", "Web Data", 
                "Network Persistent State", "Preferences", 
                "Secure Preferences", "Extension Cookies"
            ]
            
            for filename in files_to_copy:
                src = source_profile_dir / filename
                dst = target_profile_dir / filename
                if src.exists():
                    try:
                        shutil.copy2(src, dst)
                    except Exception as e:
                        logger.warning(f"Could not copy {filename}: {e}")
            
            # Launch Chrome with persistent context
            self.context = await self.playwright.chromium.launch_persistent_context(
                str(self.temp_user_data_dir),
                channel="chrome",
                headless=False,
                viewport={'width': 1920, 'height': 1080},
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                ]
            )
            
            # Hide webdriver
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            self.page = self.context.pages[0]
        
        logger.success(f"{self.browser_type.capitalize()} browser started successfully")
        
        # Initialize SMS code reader if using Safari
        if self.browser_type == "safari":
            self.sms_reader = SMSCodeReader()
            logger.info("📱 SMS code reader initialized - will auto-detect verification codes")
    
    async def _import_safari_cookies(self, profile: Dict):
        """Import Safari cookies from your actual Safari profile."""
        logger.info("Importing cookies from your Safari browser...")
        try:
            # Extract cookies using browser_cookie3 (supports Safari)
            cookies_jar = browser_cookie3.safari(domain_name="")
            
            playwright_cookies = []
            domains_to_import = [
                ".google.com", "google.com", 
                ".tiktok.com", "tiktok.com", 
                "www.tiktok.com",
                ".youtube.com", "youtube.com"
            ]
            
            count = 0
            for cookie in cookies_jar:
                # Filter for relevant domains
                if any(d in cookie.domain for d in domains_to_import):
                    cookie_dict = {
                        'name': cookie.name,
                        'value': cookie.value,
                        'domain': cookie.domain,
                        'path': cookie.path,
                        'secure': bool(cookie.secure),
                        'httpOnly': getattr(cookie, 'rfc2109', False),
                    }
                    
                    # Add expires if available
                    if hasattr(cookie, 'expires') and cookie.expires:
                        cookie_dict['expires'] = cookie.expires
                    
                    # Remove None values
                    cookie_dict = {k: v for k, v in cookie_dict.items() if v is not None}
                    playwright_cookies.append(cookie_dict)
                    count += 1
            
            if playwright_cookies:
                logger.info(f"Found {count} Safari cookies. Injecting into browser context...")
                await self.context.add_cookies(playwright_cookies)
                logger.success("✅ Safari cookies imported successfully!")
                return True
            else:
                logger.warning("No relevant cookies found in Safari")
                return False
                
        except PermissionError as e:
            logger.warning("⚠️  Safari cookie access requires macOS permissions")
            logger.info("")
            logger.info("To enable Safari cookie access:")
            logger.info("  1. Open System Settings (System Preferences)")
            logger.info("  2. Go to Privacy & Security > Full Disk Access")
            logger.info("  3. Add Terminal (or iTerm2 if you use it)")
            logger.info("  4. Restart Terminal and try again")
            logger.info("")
            logger.info("Alternatively, you can manually log in and the session will be saved.")
            return False
        except browser_cookie3.BrowserCookieError as e:
            logger.warning(f"Safari cookie extraction error: {e}")
            logger.info("This may require macOS permissions - see instructions above")
            return False
        except Exception as e:
            logger.error(f"Failed to import Safari cookies: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    async def _launch_actual_safari(self, profile: Dict):
        """
        Launch the actual Safari.app browser (not Playwright's WebKit).
        Uses AppleScript to control Safari.app directly.
        """
        safari_path = Path("/Applications/Safari.app")
        
        if not safari_path.exists():
            raise RuntimeError("Safari.app not found at /Applications/Safari.app")
        
        logger.info("Launching actual Safari.app with your profile...")
        
        # Use SafariAppController to launch actual Safari
        self.safari_controller = SafariAppController()
        self.using_actual_safari = True
        
        # Launch Safari.app (this automatically uses your actual Safari profile)
        await self.safari_controller.launch_safari("https://www.tiktok.com/en/")
        
        logger.success("✅ Safari.app opened with your actual profile!")
        logger.info("")
        logger.info("=" * 60)
        logger.info("Using ACTUAL Safari.app (not Playwright WebKit)")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Your Safari profile includes:")
        logger.info("  ✓ All your bookmarks")
        logger.info("  ✓ All your saved passwords")
        logger.info("  ✓ All your extensions")
        logger.info("  ✓ All your cookies and sessions")
        logger.info("  ✓ Your browsing history")
        logger.info("")
        
        # Still initialize Playwright for recording infrastructure
        # (We'll use it for event monitoring, but Safari.app is the main browser)
        self.playwright = await async_playwright().start()
        browser = await self.playwright.webkit.launch(headless=True)  # Hidden for recording
        self.context = await browser.new_context()
        self.page = await self.context.new_page()
        
        # Import Safari cookies into the recorder context (for session saving later)
        await self._import_safari_cookies(profile)
    
    async def _copy_safari_preferences(self, profile: Dict):
        """Copy Safari preferences and other profile data if possible."""
        try:
            safari_dir = Path(profile['path'])
            
            # Safari stores preferences in a different location
            # Main preferences are in ~/Library/Preferences/com.apple.Safari.plist
            prefs_file = Path.home() / "Library/Preferences/com.apple.Safari.plist"
            
            if prefs_file.exists():
                logger.info("Safari preferences found (stored in system location)")
                # Note: We can't directly copy plist files to Playwright,
                # but the cookies import should handle most session data
        except Exception as e:
            logger.debug(f"Could not access Safari preferences: {e}")
    
    def _record_action(self, action_type: str, details: Dict):
        """Record an action with timestamp."""
        timestamp = datetime.now()
        relative_time = None
        
        if self.start_time:
            relative_time = (timestamp - self.start_time).total_seconds()
        
        action = {
            "type": action_type,
            "timestamp": timestamp.isoformat(),
            "relative_time": relative_time,
            "details": details
        }
        
        self.recorded_actions.append(action)
        logger.debug(f"Recorded: {action_type} - {details.get('description', '')}")
    
    async def screenshot(self, name: str) -> Optional[Path]:
        """Take a screenshot and save it with timestamp."""
        self.screenshot_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.screenshot_counter:03d}_{name}_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        
        if self.using_actual_safari and self.safari_controller:
            # Use screencapture for Safari
            try:
                import subprocess
                # Get Safari window ID
                script = '''
                tell application "Safari"
                    tell front window
                        return id
                    end tell
                end tell
                '''
                window_id = self.safari_controller._run_applescript(script)
                
                # Take screenshot of Safari window
                subprocess.run(
                    ["screencapture", "-l", window_id, str(filepath)],
                    check=True,
                    timeout=5
                )
                logger.info(f"📸 Screenshot saved: {filepath}")
                self.last_screenshot_time = datetime.now()
                return filepath
            except Exception as e:
                logger.debug(f"Error taking Safari screenshot: {e}")
                # Fallback to full screen
                try:
                    subprocess.run(
                        ["screencapture", str(filepath)],
                        check=True,
                        timeout=5
                    )
                    logger.info(f"📸 Screenshot saved (full screen): {filepath}")
                    return filepath
                except:
                    return None
        elif self.page:
            await self.page.screenshot(path=str(filepath), full_page=True)
            logger.info(f"📸 Screenshot saved: {filepath}")
            return filepath
        
        return None
    
    async def _setup_listeners(self):
        """Set up event listeners to record user actions."""
        
        # Record navigation
        self.page.on("framenavigated", lambda frame: asyncio.create_task(
            self._on_navigation(frame)
        ))
        
        # Record clicks
        self.page.on("click", lambda event: asyncio.create_task(
            self._on_click(event)
        ))
        
        # Record input
        self.page.on("input", lambda event: asyncio.create_task(
            self._on_input(event)
        ))
        
        # Record key presses (for special keys)
        self.page.on("keydown", lambda event: asyncio.create_task(
            self._on_keydown(event)
        ))
        
        logger.info("Event listeners set up - recording all actions")
    
    async def _on_navigation(self, frame):
        """Record page navigation."""
        if frame == self.page.main_frame:
            url = frame.url
            self._record_action("navigation", {
                "url": url,
                "description": f"Navigated to {url}"
            })
    
    async def _on_click(self, event):
        """Record click events."""
        try:
            element = event.target
            tag_name = await element.evaluate("el => el.tagName")
            text = await element.evaluate("el => el.textContent?.trim() || ''")
            selector = await self._get_selector(element)
            
            self._record_action("click", {
                "tag": tag_name,
                "text": text[:100],  # Limit text length
                "selector": selector,
                "description": f"Clicked {tag_name}: {text[:50]}"
            })
        except Exception as e:
            logger.debug(f"Error recording click: {e}")
    
    async def _on_input(self, event):
        """Record input events (but not the actual values for privacy)."""
        try:
            element = event.target
            tag_name = await element.evaluate("el => el.tagName")
            input_type = await element.evaluate("el => el.type || ''")
            selector = await self._get_selector(element)
            
            # Don't record actual input values for privacy
            self._record_action("input", {
                "tag": tag_name,
                "input_type": input_type,
                "selector": selector,
                "description": f"Input in {tag_name} ({input_type})"
            })
        except Exception as e:
            logger.debug(f"Error recording input: {e}")
    
    async def _on_keydown(self, event):
        """Record special key presses."""
        key = event.key
        if key in ["Enter", "Tab", "Escape", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"]:
            self._record_action("keypress", {
                "key": key,
                "description": f"Pressed {key}"
            })
    
    async def _get_selector(self, element) -> str:
        """Generate a selector for an element."""
        try:
            # Try ID first
            element_id = await element.evaluate("el => el.id")
            if element_id:
                return f"#{element_id}"
            
            # Try data attributes
            data_e2e = await element.evaluate("el => el.getAttribute('data-e2e')")
            if data_e2e:
                return f"[data-e2e='{data_e2e}']"
            
            # Try class
            classes = await element.evaluate("el => el.className")
            if classes and isinstance(classes, str):
                first_class = classes.split()[0] if classes.split() else None
                if first_class:
                    return f".{first_class}"
            
            # Fallback to tag
            tag = await element.evaluate("el => el.tagName")
            return tag.lower()
        except:
            return "unknown"
    
    async def detect_captcha(self) -> Optional[Dict]:
        """Detect if captcha is present."""
        # If using actual Safari, detect via Safari controller
        if self.using_actual_safari and self.safari_controller:
            captcha_info = await self.safari_controller.detect_captcha()
            if captcha_info:
                self._record_action("captcha_detected", {
                    "selector": captcha_info.get("selector"),
                    "type": captcha_info.get("type"),
                    "description": f"Captcha detected in Safari: {captcha_info.get('type')}"
                })
                return captcha_info
            return None
        
        # Otherwise use Playwright detection
        captcha_selectors = [
            'iframe[id*="captcha"]',
            'div[class*="captcha"]',
            '.secsdk-captcha-wrapper',
            '#secsdk-captcha-drag-wrapper',
            'canvas[class*="captcha"]'
        ]
        
        for selector in captcha_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    logger.warning(f"⚠️  CAPTCHA DETECTED: {selector}")
                    self._record_action("captcha_detected", {
                        "selector": selector,
                        "description": "Captcha appeared on page"
                    })
                    
                    # Take screenshot
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = self.screenshots_dir / f"captcha_{timestamp}.png"
                    await self.page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"Captcha screenshot saved: {screenshot_path}")
                    
                    return {
                        "detected": True,
                        "selector": selector,
                        "screenshot": str(screenshot_path)
                    }
            except:
                continue
        
        return None
    
    async def solve_captcha_in_safari(self, captcha_info: Dict) -> bool:
        """Solve captcha detected in Safari.app."""
        try:
            logger.info(f"Solving {captcha_info.get('type', 'unknown')} captcha in Safari...")
            
            # Get captcha images from Safari
            image_urls = await self.safari_controller.get_captcha_image_urls()
            
            if not image_urls.get("main"):
                logger.error("Could not extract captcha image from Safari")
                return False
            
            # Determine captcha type
            captcha_type = captcha_info.get("type", "3d")
            if captcha_type == "unknown":
                # Try to determine from image or context
                captcha_type = "3d"  # Default
            
            # Solve using captcha solver
            solution = await self.captcha_solver.solve_captcha(
                captcha_type=captcha_type,
                image_source=image_urls["main"],
                width=348,  # Default TikTok captcha size
                height=216,
                piece_url=image_urls.get("secondary") if captcha_type == "slide" else None,
                url2=image_urls.get("secondary") if captcha_type == "whirl" else None
            )
            
            logger.success(f"Captcha solution received: {solution}")
            
            # Apply solution to Safari
            await self.safari_controller.apply_captcha_solution(solution, captcha_type)
            
            # Wait and check if solved
            await asyncio.sleep(3)
            still_present = await self.safari_controller.detect_captcha()
            
            if still_present:
                logger.warning("Captcha still present after solution")
                return False
            
            logger.success("✅ Captcha solved successfully in Safari!")
            self._record_action("captcha_solved", {
                "type": captcha_type,
                "description": "Captcha solved automatically"
            })
            return True
            
        except Exception as e:
            logger.error(f"Error solving captcha in Safari: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    async def monitor_login(self):
        """Monitor the page and record actions while user logs in manually."""
        logger.info("=" * 60)
        logger.info("RECORDING MODE - Manual Login")
        logger.info("=" * 60)
        logger.info("")
        logger.info("📹 Recording all your actions...")
        logger.info("")
        logger.info("Instructions:")
        logger.info("  1. Perform your login manually in the browser")
        logger.info("  2. The system will record all your actions")
        logger.info("  3. If a captcha appears, we'll detect it")
        logger.info("  4. Press Ctrl+C when login is complete")
        logger.info("")
        logger.info("Monitoring for login completion and captchas...")
        logger.info("")
        
        self.start_time = datetime.now()
        
        # Set up listeners
        await self._setup_listeners()
        
        # Start enhanced recorders (for Safari.app)
        if self.using_actual_safari:
            # Start global input recorder (captures OS-level events)
            if GLOBAL_INPUT_AVAILABLE and GlobalInputRecorder:
                try:
                    self.global_input_recorder = GlobalInputRecorder(target_app="Safari")
                    if self.global_input_recorder.start():
                        logger.info("🎯 Global input recorder active (keyboard/mouse)")
                    else:
                        logger.warning("⚠️  Global input recorder failed to start")
                        logger.info("   Grant Terminal accessibility permissions:")
                        logger.info("   System Settings → Privacy & Security → Accessibility")
                        self.global_input_recorder = None
                except Exception as e:
                    logger.warning(f"Global input recorder error: {e}")
                    self.global_input_recorder = None
            else:
                logger.info("ℹ️  Global input recording not available")
            
            # Start screenshot recorder with change detection
            if SCREENSHOT_RECORDER_AVAILABLE and ScreenshotRecorder:
                try:
                    self.screenshot_recorder = ScreenshotRecorder(
                        output_dir=self.screenshots_dir,
                        interval=3.0,  # Every 3 seconds
                        change_threshold=8  # Moderate sensitivity
                    )
                    await self.screenshot_recorder.start()
                    logger.info("📸 Screenshot recorder active (change detection)")
                except Exception as e:
                    logger.warning(f"Screenshot recorder error: {e}")
                    self.screenshot_recorder = None
        
        # Navigate to TikTok
        if self.using_actual_safari:
            logger.info("Safari.app is already at TikTok (opened via AppleScript)")
            # Record initial navigation
            current_url = await self.safari_controller.get_current_url()
            self._record_action("navigation", {
                "url": current_url,
                "description": f"Navigated to {current_url}",
                "browser": "safari_app"
            })
            
            # Get initial page state
            try:
                initial_state = await self.safari_controller.get_page_state()
                self._record_action("page_loaded", {
                    "title": initial_state.get('title', ''),
                    "input_fields": len(initial_state.get('inputFields', [])),
                    "buttons": len(initial_state.get('buttons', [])),
                    "has_login_form": initial_state.get('hasLoginForm', False),
                    "description": f"Page loaded: {initial_state.get('title', '')[:50]}"
                })
            except:
                pass
            
            logger.info(f"📝 Recording started - initial URL: {current_url}")
        else:
            logger.info("Navigating to TikTok...")
            await self.page.goto("https://www.tiktok.com/en/")
            await asyncio.sleep(2)
            self._record_action("navigation", {
                "url": self.page.url,
                "description": f"Navigated to {self.page.url}",
                "browser": "playwright"
            })
        
        # Monitor loop
        login_complete = False
        if self.using_actual_safari and self.safari_controller:
            last_url = await self.safari_controller.get_current_url()
        else:
            last_url = self.page.url if self.page else ""
        
        try:
            check_count = 0
            last_page_state = None
            last_screenshot_check = datetime.now()
            
            while not login_complete:
                check_count += 1
                
                # Get events from global input recorder (OS-level events)
                if self.global_input_recorder:
                    try:
                        global_events = self.global_input_recorder.get_events_since_last()
                        for event in global_events:
                            # Events are already in the right format from GlobalInputRecorder
                            self.recorded_actions.append(event)
                            desc = event.get('details', {}).get('description', '')
                            if 'click' in event.get('type', ''):
                                logger.info(f"🖱️  Click recorded: {desc}")
                            elif 'keypress' in event.get('type', ''):
                                logger.info(f"⌨️  Key recorded: {desc}")
                    except Exception as e:
                        logger.debug(f"Error getting global input events: {e}")
                
                # Get captured JavaScript events (every check)
                if self.using_actual_safari and self.safari_controller:
                    try:
                        events = await self.safari_controller.get_captured_events()
                        for event in events:
                            # Record each captured event
                            event_type = event.get('type', 'unknown')
                            if event_type == 'click':
                                self._record_action("js_click", {
                                    "target": event.get('target', {}),
                                    "position": event.get('position', {}),
                                    "url": event.get('url', ''),
                                    "description": f"Click on {event.get('target', {}).get('tag', 'element')}: {event.get('target', {}).get('text', '')[:50]}"
                                })
                            elif event_type == 'input':
                                self._record_action("js_input", {
                                    "target": event.get('target', {}),
                                    "value_length": event.get('valueLength', 0),
                                    "has_value": event.get('hasValue', False),
                                    "url": event.get('url', ''),
                                    "description": f"Input in {event.get('target', {}).get('type', 'field')}: {event.get('valueLength', 0)} chars"
                                })
                            elif event_type == 'form_submit':
                                self._record_action("js_form_submit", {
                                    "form_id": event.get('formId', ''),
                                    "url": event.get('url', ''),
                                    "description": f"Form submitted: {event.get('formId', 'unknown')}"
                                })
                            elif event_type == 'keypress':
                                self._record_action("js_keypress", {
                                    "key": event.get('key', ''),
                                    "target": event.get('target', {}),
                                    "url": event.get('url', ''),
                                    "description": f"Pressed {event.get('key', 'key')}"
                                })
                            elif event_type == 'url_change':
                                self._record_action("js_url_change", {
                                    "from": event.get('from', ''),
                                    "to": event.get('to', ''),
                                    "description": f"URL changed (JS detected): {event.get('to', '')[:60]}"
                                })
                    except Exception as e:
                        logger.debug(f"Error getting captured events: {e}")
                
                # Get comprehensive page state (every check)
                if self.using_actual_safari and self.safari_controller:
                    try:
                        page_state = await self.safari_controller.get_page_state()
                        
                        # Record state changes
                        if last_page_state:
                            # Check for new input fields
                            current_inputs = {f.get('id') or f.get('name') or f.get('placeholder', ''): f for f in page_state.get('inputFields', [])}
                            last_inputs = {f.get('id') or f.get('name') or f.get('placeholder', ''): f for f in last_page_state.get('inputFields', [])}
                            
                            for field_id, field in current_inputs.items():
                                if field_id not in last_inputs:
                                    self._record_action("input_field_appeared", {
                                        "type": field.get('type'),
                                        "name": field.get('name'),
                                        "id": field.get('id'),
                                        "placeholder": field.get('placeholder'),
                                        "description": f"Input field appeared: {field.get('type')} ({field.get('placeholder') or field.get('name') or field.get('id')})"
                                    })
                                elif field.get('hasValue') and not last_inputs[field_id].get('hasValue'):
                                    # Field was filled
                                    self._record_action("input_field_filled", {
                                        "type": field.get('type'),
                                        "name": field.get('name'),
                                        "id": field.get('id'),
                                        "value_length": field.get('valueLength'),
                                        "description": f"Input field filled: {field.get('type')} ({field.get('name') or field.get('id')}) - {field.get('valueLength')} chars"
                                    })
                            
                            # Check for new buttons
                            current_buttons = [b.get('text', '') for b in page_state.get('buttons', [])]
                            last_buttons = [b.get('text', '') for b in last_page_state.get('buttons', [])]
                            new_buttons = set(current_buttons) - set(last_buttons)
                            for btn_text in new_buttons:
                                if btn_text:
                                    self._record_action("button_appeared", {
                                        "text": btn_text[:50],
                                        "description": f"Button appeared: {btn_text[:50]}"
                                    })
                            
                            # Check for form changes
                            if page_state.get('forms', 0) != last_page_state.get('forms', 0):
                                self._record_action("form_change", {
                                    "form_count": page_state.get('forms', 0),
                                    "description": f"Form count changed to {page_state.get('forms', 0)}"
                                })
                        
                        last_page_state = page_state
                        
                        # Record page state periodically (every 5 checks)
                        if check_count % 5 == 0:
                            self._record_action("page_state_snapshot", {
                                "url": page_state.get('url', ''),
                                "title": page_state.get('title', ''),
                                "has_login_form": page_state.get('hasLoginForm', False),
                                "has_code_input": page_state.get('hasCodeInput', False),
                                "has_captcha": page_state.get('hasCaptcha', False),
                                "input_count": len(page_state.get('inputFields', [])),
                                "button_count": len(page_state.get('buttons', [])),
                                "description": f"Page state: {page_state.get('title', '')[:30]} - {len(page_state.get('inputFields', []))} inputs, {len(page_state.get('buttons', []))} buttons"
                            })
                    except Exception as e:
                        logger.debug(f"Error getting page state: {e}")
                
                # Check for captcha periodically and solve automatically
                try:
                    captcha_info = await self.detect_captcha()
                    if captcha_info:
                        logger.warning("⚠️  CAPTCHA DETECTED! Attempting to solve automatically...")
                        
                        # Take screenshot of captcha
                        screenshot_path = await self.screenshot("captcha_detected")
                        if screenshot_path:
                            self._record_action("screenshot", {
                                "path": str(screenshot_path),
                                "description": f"Captcha screenshot: {captcha_info.get('type', 'unknown')}"
                            })
                        
                        if self.using_actual_safari:
                            # Solve captcha in Safari
                            solved = await self.solve_captcha_in_safari(captcha_info)
                            if not solved:
                                logger.warning("Automatic solving failed - you may need to solve manually")
                        else:
                            logger.warning("Captcha detected but auto-solving not yet implemented for Playwright")
                            logger.info("   You may need to solve it manually")
                except Exception as e:
                    logger.debug(f"Error checking captcha: {e}")
                
                # Check if login completed (URL change or profile icon)
                try:
                    if self.using_actual_safari and self.safari_controller:
                        current_url = await self.safari_controller.get_current_url()
                        if current_url and current_url != last_url:
                            self._record_action("url_change", {
                                "from": last_url,
                                "to": current_url,
                                "description": f"URL changed to {current_url}",
                                "browser": "safari_app"
                            })
                            logger.info(f"📝 Recorded URL change: {last_url[:50]}... → {current_url[:50]}...")
                            last_url = current_url
                    elif self.page:
                        current_url = self.page.url
                        if current_url != last_url:
                            self._record_action("url_change", {
                                "from": last_url,
                                "to": current_url,
                                "description": f"URL changed to {current_url}"
                            })
                            last_url = current_url
                except Exception as e:
                    logger.debug(f"Error checking URL: {e}")
                
                # Take periodic screenshots (every 10 seconds)
                if (datetime.now() - last_screenshot_check).total_seconds() >= 10:
                    try:
                        screenshot_path = await self.screenshot("periodic_check")
                        if screenshot_path:
                            self._record_action("screenshot", {
                                "path": str(screenshot_path),
                                "description": f"Periodic screenshot: {screenshot_path.name}"
                            })
                        last_screenshot_check = datetime.now()
                    except Exception as e:
                        logger.debug(f"Error taking periodic screenshot: {e}")
                
                # Take screenshot on URL change
                if self.using_actual_safari and self.safari_controller:
                    try:
                        current_url = await self.safari_controller.get_current_url()
                        if current_url and current_url != last_url:
                            screenshot_path = await self.screenshot("url_change")
                            if screenshot_path:
                                self._record_action("screenshot", {
                                    "path": str(screenshot_path),
                                    "description": f"Screenshot on URL change: {current_url[:50]}"
                                })
                    except:
                        pass
                
                # Periodic status logging (every 10 checks = ~10 seconds)
                if check_count % 10 == 0:
                    if self.using_actual_safari and self.safari_controller:
                        try:
                            current_url = await self.safari_controller.get_current_url()
                            logger.info(f"📊 Status: URL = {current_url[:60]}... | Actions = {len(self.recorded_actions)} | Screenshots = {self.screenshot_counter}")
                        except:
                            pass
                
                # Check for login indicators
                if self.using_actual_safari and self.safari_controller:
                    # Check Safari.app for login success
                    if await self.safari_controller.check_for_login_success():
                        logger.success("✅ Login detected in Safari.app!")
                        self._record_action("login_success", {
                            "description": "Login completed in Safari.app"
                        })
                        login_complete = True
                        break
                else:
                    # Check Playwright page for login success
                    try:
                        profile_icon = await self.page.query_selector('[data-e2e="profile-icon"], [data-e2e="upload-icon"]')
                        if profile_icon:
                            logger.success("✅ Login detected! Profile icon found.")
                            self._record_action("login_success", {
                                "description": "Login completed - profile icon detected"
                            })
                            login_complete = True
                            break
                    except:
                        pass
                
                # Check for verification code field and auto-fill if code received
                if self.using_actual_safari and self.sms_reader:
                    try:
                        # Check page state for code input
                        page_state = await self.safari_controller.get_page_state()
                        if page_state.get('hasCodeInput'):
                            logger.info("📱 Verification code field detected - checking for SMS code...")
                            code = await self.sms_reader.get_latest_code(keywords=["tiktok", "verification", "code"])
                            if code:
                                logger.success(f"✅ Found verification code: {code}")
                                entered = await self.safari_controller.enter_verification_code(code)
                                if entered:
                                    logger.success("✅ Verification code entered automatically!")
                                    self._record_action("verification_code_entered", {
                                        "code": code,
                                        "description": "Verification code entered from SMS"
                                    })
                                    # Wait a moment for form to process
                                    await asyncio.sleep(2)
                    except Exception as e:
                        logger.debug(f"Error checking for verification code: {e}")
                
                # Wait a bit before next check
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("\n⏹️  Recording stopped by user")
            # Check one more time if login succeeded
            if self.using_actual_safari and self.safari_controller:
                if await self.safari_controller.check_for_login_success():
                    logger.success("✅ Login appears to be complete in Safari.app!")
                    self._record_action("login_success", {
                        "description": "Login completed (detected on stop)"
                    })
                    login_complete = True
            else:
                try:
                    profile_icon = await self.page.query_selector('[data-e2e="profile-icon"], [data-e2e="upload-icon"]')
                    if profile_icon:
                        logger.success("✅ Login appears to be complete!")
                        self._record_action("login_success", {
                            "description": "Login completed (detected on stop)"
                        })
                        login_complete = True
                except:
                    pass
    
    async def save_recording(self):
        """Save the recorded actions to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        recording_file = self.recordings_dir / f"login_recording_{timestamp}.json"
        
        # Get final URL
        final_url = None
        if self.using_actual_safari and self.safari_controller:
            try:
                final_url = await self.safari_controller.get_current_url()
            except:
                pass
        elif self.page:
            final_url = self.page.url
        
        recording_data = {
            "recorded_at": datetime.now().isoformat(),
            "total_actions": len(self.recorded_actions),
            "duration_seconds": (
                (datetime.now() - self.start_time).total_seconds() 
                if self.start_time else None
            ),
            "browser_type": self.browser_type,
            "using_actual_safari": self.using_actual_safari,
            "actions": self.recorded_actions,
            "final_url": final_url,
            "summary": {
                "navigations": len([a for a in self.recorded_actions if a.get("type") == "navigation"]),
                "url_changes": len([a for a in self.recorded_actions if a.get("type") in ["url_change", "js_url_change"]]),
                "page_states": len([a for a in self.recorded_actions if a.get("type") == "page_state_snapshot"]),
                "clicks": len([a for a in self.recorded_actions if a.get("type") in ["click", "js_click", "global_click"]]),
                "inputs": len([a for a in self.recorded_actions if a.get("type") in ["input", "js_input", "input_field_appeared", "input_field_filled"]]),
                "keypresses": len([a for a in self.recorded_actions if a.get("type") in ["keypress", "js_keypress", "global_keypress"]]),
                "form_submits": len([a for a in self.recorded_actions if a.get("type") in ["form_submit", "js_form_submit"]]),
                "input_fields": len([a for a in self.recorded_actions if a.get("type") in ["input_field_appeared", "input_field_filled"]]),
                "buttons": len([a for a in self.recorded_actions if a.get("type") == "button_appeared"]),
                "form_changes": len([a for a in self.recorded_actions if a.get("type") == "form_change"]),
                "screenshots": len([a for a in self.recorded_actions if a.get("type") == "screenshot"]),
                "captchas_detected": len([a for a in self.recorded_actions if a.get("type") == "captcha_detected"]),
                "captchas_solved": len([a for a in self.recorded_actions if a.get("type") == "captcha_solved"]),
                "verification_codes": len([a for a in self.recorded_actions if a.get("type") == "verification_code_entered"]),
                "login_success": any(a.get("type") == "login_success" for a in self.recorded_actions)
            }
        }
        
        with open(recording_file, 'w') as f:
            json.dump(recording_data, f, indent=2)
        
        logger.success(f"✅ Recording saved to: {recording_file}")
        logger.info(f"   Total actions: {len(self.recorded_actions)}")
        logger.info(f"   Duration: {recording_data.get('duration_seconds', 0):.1f} seconds")
        logger.info(f"   Summary: {recording_data['summary']}")
        return recording_file
    
    async def save_session(self):
        """Save browser session (cookies) if login was successful."""
        try:
            if self.using_actual_safari:
                # Extract cookies from actual Safari
                logger.info("Extracting cookies from Safari.app...")
                try:
                    cookies_jar = browser_cookie3.safari(domain_name="tiktok.com")
                    cookies = []
                    for cookie in cookies_jar:
                        cookie_dict = {
                            'name': cookie.name,
                            'value': cookie.value,
                            'domain': cookie.domain,
                            'path': cookie.path,
                            'secure': bool(cookie.secure),
                        }
                        if hasattr(cookie, 'expires') and cookie.expires:
                            cookie_dict['expires'] = cookie.expires
                        cookies.append(cookie_dict)
                    
                    current_url = await self.safari_controller.get_current_url() if self.safari_controller else "unknown"
                    
                    session_data = {
                        "cookies": cookies,
                        "timestamp": datetime.now().isoformat(),
                        "url": current_url,
                        "browser": "safari_app"
                    }
                except Exception as e:
                    logger.warning(f"Could not extract Safari cookies: {e}")
                    logger.info("Session will be saved from Playwright context instead")
                    cookies = await self.context.cookies() if self.context else []
                    session_data = {
                        "cookies": cookies,
                        "timestamp": datetime.now().isoformat(),
                        "url": self.page.url if self.page else "unknown",
                        "browser": "safari_app_fallback"
                    }
            else:
                cookies = await self.context.cookies()
                session_data = {
                    "cookies": cookies,
                    "timestamp": datetime.now().isoformat(),
                    "url": self.page.url if self.page else "unknown"
                }
            
            session_file = self.session_dir / "tiktok_session.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logger.success(f"✅ Session saved to: {session_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")
        
        if self.page:
            try:
                await self.page.close()
            except:
                pass
        
        if self.context:
            try:
                await self.context.close()
            except:
                pass
        
        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass
        
        if hasattr(self, 'temp_user_data_dir') and self.temp_user_data_dir and Path(self.temp_user_data_dir).exists():
            import shutil
            try:
                shutil.rmtree(self.temp_user_data_dir)
            except Exception as e:
                logger.warning(f"Failed to remove temp dir: {e}")
        
        # Stop enhanced recorders
        if self.global_input_recorder:
            try:
                events = self.global_input_recorder.stop()
                logger.info(f"Global input recorder: captured {len(events)} events")
            except Exception as e:
                logger.debug(f"Error stopping global input recorder: {e}")
            self.global_input_recorder = None
        
        if self.screenshot_recorder:
            try:
                screenshots = await self.screenshot_recorder.stop()
                logger.info(f"Screenshot recorder: captured {len(screenshots)} screenshots")
            except Exception as e:
                logger.debug(f"Error stopping screenshot recorder: {e}")
            self.screenshot_recorder = None


async def main():
    """Main execution function."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    recorder = TikTokLoginRecorder()
    
    try:
        # Start browser
        await recorder.start_browser()
        
        # Monitor and record
        await recorder.monitor_login()
        
        # Save recording
        recording_file = await recorder.save_recording()
        
        # Save session if login succeeded
        await recorder.save_session()
        
        logger.info("\n" + "=" * 60)
        logger.info("Recording Complete")
        logger.info("=" * 60)
        logger.info(f"Total actions recorded: {len(recorder.recorded_actions)}")
        logger.info(f"Recording file: {recording_file}")
        logger.info("\nYou can review the recording to see what actions were taken.")
        
        # Keep browser open for a moment
        logger.info("\nKeeping browser open for 10 seconds for review...")
        await asyncio.sleep(10)
        
    except KeyboardInterrupt:
        logger.warning("\nRecording interrupted")
        await recorder.save_recording()
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.debug(traceback.format_exc())
    finally:
        await recorder.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

