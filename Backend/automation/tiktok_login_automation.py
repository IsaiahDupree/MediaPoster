"""
TikTok Login Automation with Captcha Solving

This script automates TikTok login using Playwright browser automation
and integrates with the TikTok Captcha Solver service to handle captchas.
"""

import os
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from loguru import logger
import json
from dotenv import load_dotenv
import browser_cookie3

# Load environment variables
load_dotenv()

# Add parent directory to path to import services
sys.path.append(str(Path(__file__).parent.parent))
from services.tiktok_captcha_solver import TikTokCaptchaSolver
from automation.chrome_profile_manager import ChromeProfileManager


class TikTokLoginAutomation:
    """Automates TikTok login with integrated captcha solving."""
    
    def __init__(self, headless: bool = False, save_session: bool = True, profile_name: Optional[str] = None):
        """
        Initialize the TikTok automation.
        
        Args:
            headless: Run browser in headless mode
            save_session: Save authenticated session cookies
            profile_name: Chrome profile name to use (e.g., "Default", "Profile 1")
        """
        self.headless = headless
        self.save_session = save_session
        self.captcha_solver = TikTokCaptchaSolver()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Chrome Profile Manager
        self.profile_manager = ChromeProfileManager()
        self.profile_name = profile_name
        
        # Get credentials from environment
        self.username = os.getenv("TIKTOK_USERNAME")
        self.password = os.getenv("TIKTOK_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("TIKTOK_USERNAME and TIKTOK_PASSWORD must be set in environment")
        
        # Session storage
        self.session_dir = Path(__file__).parent / "sessions"
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "tiktok_session.json"
        
        # Screenshots directory
        self.screenshots_dir = Path(__file__).parent / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)
        
        logger.info(f"TikTok automation initialized for user: {self.username}")
    
    async def screenshot(self, name: str) -> Optional[Path]:
        """Take a screenshot and save it with timestamp."""
        if not self.page:
            logger.warning("Cannot take screenshot: page not initialized")
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        await self.page.screenshot(path=str(filepath), full_page=True)
        logger.info(f"Screenshot saved: {filepath}")
        return filepath
    
    async def start_browser(self):
        """
        Start the Playwright browser with a SNAPSHOT of the local Chrome profile.
        This allows running the automation while the user's Chrome is open.
        Uses Chrome Profile Manager to find and use the configured profile.
        """
        logger.info("Creating profile snapshot...")
        self.playwright = await async_playwright().start()
        
        # Get Chrome profile using Profile Manager
        profile = None
        if self.profile_name:
            profile = self.profile_manager.select_profile(self.profile_name)
        else:
            # Try to load saved profile
            profile = self.profile_manager.get_saved_profile()
            if not profile:
                # Fallback to Default
                profile = self.profile_manager.select_profile("Default")
        
        if not profile:
            logger.error("Could not find Chrome profile")
            raise RuntimeError("No Chrome profile available")
        
        # Save profile config for future use
        self.profile_manager.save_profile_config(profile)
        logger.info(f"Using Chrome profile: {profile['name']}")
        
        # Get Chrome User Data Directory
        source_user_data_dir = Path(profile['full_path'])
        source_profile_dir = Path(profile['path'])
        
        # Create a temporary directory for the profile snapshot
        import tempfile
        import shutil
        self.temp_user_data_dir = Path(tempfile.mkdtemp())
        logger.info(f"Created temporary profile directory: {self.temp_user_data_dir}")
        
        try:
            # 1. Copy 'Local State' (Critical for encryption keys)
            if (source_user_data_dir / "Local State").exists():
                shutil.copy2(source_user_data_dir / "Local State", self.temp_user_data_dir / "Local State")
            
            # 2. Create profile directory in temp (use same name as source)
            profile_dir_name = source_profile_dir.name  # "Default", "Profile 1", etc.
            target_profile_dir = self.temp_user_data_dir / profile_dir_name
            target_profile_dir.mkdir(exist_ok=True)
            
            # 3. Copy essential files for session/cookies
            # We explicitly exclude Caches to save time and space
            files_to_copy = [
                "Cookies", 
                "Login Data", 
                "Web Data", 
                "Network Persistent State", 
                "Preferences", 
                "Secure Preferences",
                "Extension Cookies"
            ]
            
            logger.info(f"Copying essential profile files from {profile_dir_name}...")
            for filename in files_to_copy:
                src = source_profile_dir / filename
                dst = target_profile_dir / filename
                
                if src.exists():
                    try:
                        shutil.copy2(src, dst)
                    except Exception as e:
                        logger.warning(f"Could not copy {filename}: {e}")
            
            logger.info("Profile snapshot created successfully")
            
            # Launch with the temporary profile
            self.context = await self.playwright.chromium.launch_persistent_context(
                str(self.temp_user_data_dir),
                channel="chrome", # Use actual Chrome installation
                headless=False, # Must be visible
                viewport={'width': 1920, 'height': 1080},
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            # Hide webdriver property
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            self.page = self.context.pages[0]
            logger.success("Browser started successfully with profile snapshot")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    async def detect_captcha(self) -> Optional[Dict]:
        """
        Detect if a captcha is present on the page.
        
        Returns:
            Dictionary with captcha info if detected, None otherwise
        """
        logger.info("Checking for captcha...")
        
        # Wait a moment for captcha to potentially appear
        await asyncio.sleep(2)
        
        # Check for common TikTok captcha indicators
        captcha_selectors = [
            'iframe[id*="captcha"]',
            'div[class*="captcha"]',
            'div[id*="captcha"]',
            '.secsdk-captcha-wrapper',
            '#secsdk-captcha-drag-wrapper',
            'canvas[class*="captcha"]'
        ]
        
        for selector in captcha_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    logger.warning(f"Captcha detected with selector: {selector}")
                    
                    # Try to determine captcha type from element
                    captcha_type = await self._determine_captcha_type(element)
                    
                    return {
                        "detected": True,
                        "selector": selector,
                        "type": captcha_type,
                        "element": element
                    }
            except Exception as e:
                logger.debug(f"Error checking selector {selector}: {e}")
                continue
        
        logger.info("No captcha detected")
        return None
    
    async def _determine_captcha_type(self, element) -> str:
        """Determine the type of captcha from the element."""
        # Get element attributes and text content
        try:
            class_name = await element.get_attribute("class") or ""
            id_attr = await element.get_attribute("id") or ""
            
            # Pattern matching for captcha types
            if "rotate" in class_name.lower() or "rotate" in id_attr.lower():
                return "whirl"
            elif "slide" in class_name.lower() or "puzzle" in class_name.lower():
                return "slide"
            elif "3d" in class_name.lower():
                return "3d"
            elif "icon" in class_name.lower() or "select" in class_name.lower():
                return "icon"
            
            # Default to 3D if can't determine
            logger.warning("Could not determine captcha type, defaulting to 3d")
            return "3d"
            
        except Exception as e:
            logger.error(f"Error determining captcha type: {e}")
            return "3d"
    
    async def _extract_captcha_images(self, element, captcha_type: str) -> Dict[str, str]:
        """Extract image URLs from the captcha element."""
        images = {}
        
        try:
            # Query all images in the captcha container
            img_elements = await element.query_selector_all('img')
            srcs = []
            for img in img_elements:
                src = await img.get_attribute('src')
                if src:
                    srcs.append(src)
            
            logger.info(f"Found {len(srcs)} images in captcha container")
            
            if captcha_type == "slide":
                # Try to find specific classes first
                bg = await element.query_selector('img[src*="captcha-sg"], img[class*="bg"]')
                piece = await element.query_selector('img[src*="captcha-sg"][class*="slide"], img[class*="slide"]')
                
                if bg and piece:
                    images["puzzle_url"] = await bg.get_attribute("src")
                    images["piece_url"] = await piece.get_attribute("src")
                elif len(srcs) >= 2:
                    # Fallback to order: usually bg is first or second depending on DOM
                    # We'll assume standard order or try to guess
                    images["puzzle_url"] = srcs[0]
                    images["piece_url"] = srcs[1]
            
            elif captcha_type == "whirl":
                if len(srcs) >= 2:
                    images["url1"] = srcs[0] # Inner
                    images["url2"] = srcs[1] # Outer
            
            elif captcha_type == "3d":
                if len(srcs) >= 1:
                    images["image_source"] = srcs[0]
                    
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            
        return images

    async def solve_detected_captcha(self, captcha_info: Dict) -> bool:
        """
        Solve a detected captcha.
        
        Args:
            captcha_info: Information about the detected captcha
            
        Returns:
            True if solved successfully, False otherwise
        """
        try:
            logger.info(f"Attempting to solve {captcha_info['type']} captcha...")
            
            # Screenshot the captcha for debugging
            await self.screenshot(f"captcha_{captcha_info['type']}")
            
            element = captcha_info['element']
            bounding_box = await element.bounding_box()
            
            if not bounding_box:
                logger.error("Could not get captcha bounding box")
                return False
            
            # Extract images
            extracted_images = await self._extract_captcha_images(element, captcha_info['type'])
            logger.info(f"Extracted images: {extracted_images}")
            
            # Prepare arguments for solver
            solver_kwargs = {}
            image_source = None
            
            # Determine main image source and kwargs based on type
            if captcha_info['type'] == "slide":
                if "puzzle_url" in extracted_images:
                    image_source = extracted_images["puzzle_url"]
                    solver_kwargs["piece_url"] = extracted_images.get("piece_url")
                else:
                    # Fallback to screenshot
                    logger.warning("Could not extract slide images, using screenshot")
                    captcha_screenshot = self.screenshots_dir / "captcha_current.png"
                    await element.screenshot(path=str(captcha_screenshot))
                    image_source = captcha_screenshot
            
            elif captcha_info['type'] == "whirl":
                if "url1" in extracted_images:
                    image_source = extracted_images["url1"]
                    solver_kwargs["url2"] = extracted_images.get("url2")
                else:
                    logger.warning("Could not extract whirl images, using screenshot")
                    captcha_screenshot = self.screenshots_dir / "captcha_current.png"
                    await element.screenshot(path=str(captcha_screenshot))
                    image_source = captcha_screenshot
                    
            elif captcha_info['type'] == "3d":
                if "image_source" in extracted_images:
                    image_source = extracted_images["image_source"]
                else:
                    logger.warning("Could not extract 3d image, using screenshot")
                    captcha_screenshot = self.screenshots_dir / "captcha_current.png"
                    await element.screenshot(path=str(captcha_screenshot))
                    image_source = captcha_screenshot
            
            # Solve the captcha
            width = int(bounding_box['width'])
            height = int(bounding_box['height'])
            
            logger.info(f"Solving with width={width}, height={height}")
            
            solution = await self.captcha_solver.solve_captcha(
                captcha_type=captcha_info['type'],
                image_source=image_source,
                width=width,
                height=height,
                **solver_kwargs
            )
            
            logger.success(f"Captcha solution received: {solution}")
            
            # Apply the solution
            await self._apply_captcha_solution(captcha_info, solution)
            
            # Wait for verification
            await asyncio.sleep(5)
            
            # Check if captcha is still present
            still_present = await self.detect_captcha()
            
            if still_present:
                logger.error("Captcha still present after solution attempt")
                return False
            
            logger.success("Captcha solved successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error solving captcha: {e}")
            return False
    
    async def _apply_captcha_solution(self, captcha_info: Dict, solution: Dict):
        """Apply the captcha solution based on the type and response."""
        logger.info("Applying captcha solution...")
        
        element = captcha_info['element']
        captcha_type = captcha_info['type']
        
        try:
            if captcha_type in ["slide", "whirl"]:
                # Logic for sliding/rotating
                # Usually involves dragging a slider handle
                slider_handle = await element.query_selector('.secsdk-captcha-drag-icon, .captcha_verify_slide--slidebar')
                
                if not slider_handle:
                    logger.warning("Could not find slider handle, trying generic selector")
                    slider_handle = await element.query_selector('[class*="drag-icon"], [class*="slidebar"]')
                
                if slider_handle:
                    # Get handle position
                    box = await slider_handle.bounding_box()
                    if box:
                        start_x = box['x'] + box['width'] / 2
                        start_y = box['y'] + box['height'] / 2
                        
                        # Calculate target X
                        # API usually returns 'x' for slide, 'angle' for whirl
                        # For whirl, we need to map angle to slide distance
                        
                        distance = 0
                        if captcha_type == "slide":
                            # Check if solution has 'x' or 'slide_x'
                            # The API response format needs to be checked. 
                            # Assuming {'data': {'x': 123, 'y': 45}} or similar
                            # Based on previous logs: {'success': ..., 'data': ...}
                            
                            # If solution is directly the dict
                            if 'x' in solution:
                                distance = solution['x']
                            elif 'data' in solution and 'x' in solution['data']:
                                distance = solution['data']['x']
                            elif 'slide_x' in solution:
                                distance = solution['slide_x']
                                
                        elif captcha_type == "whirl":
                            # Map angle to distance
                            # Total width of slider usually corresponds to 360 degrees?
                            # This is tricky without knowing the exact mapping.
                            # Usually: distance = (angle / 360) * slider_width
                            angle = 0
                            if 'angle' in solution:
                                angle = solution['angle']
                            elif 'data' in solution and 'angle' in solution['data']:
                                angle = solution['data']['angle']
                                
                            # Estimate slider width (track width)
                            # We need the track element
                            track = await element.query_selector('.captcha_verify_slide--track, [class*="track"]')
                            track_width = 300 # Default guess
                            if track:
                                track_box = await track.bounding_box()
                                if track_box:
                                    track_width = track_box['width']
                            
                            distance = (angle / 360) * track_width
                        
                        logger.info(f"Dragging slider by {distance} pixels")
                        
                        # Perform drag
                        await self.page.mouse.move(start_x, start_y)
                        await self.page.mouse.down()
                        # Move in steps for realism
                        steps = 10
                        for i in range(steps):
                            await self.page.mouse.move(start_x + (distance * (i+1)/steps), start_y)
                            await asyncio.sleep(0.05)
                        await self.page.mouse.up()
                        
            elif captcha_type == "3d":
                # Click on objects
                # Solution usually contains a list of coordinates or objects
                # e.g. {'objects': [{'x': 10, 'y': 20}, ...]}
                
                objects = []
                if 'objects' in solution:
                    objects = solution['objects']
                elif 'data' in solution and 'objects' in solution['data']:
                    objects = solution['data']['objects']
                
                # Get image position
                img = await element.query_selector('img')
                if img:
                    img_box = await img.bounding_box()
                    if img_box:
                        img_x = img_box['x']
                        img_y = img_box['y']
                        
                        for obj in objects:
                            x = obj.get('x', 0)
                            y = obj.get('y', 0)
                            
                            target_x = img_x + x
                            target_y = img_y + y
                            
                            logger.info(f"Clicking object at {target_x}, {target_y}")
                            await self.page.mouse.click(target_x, target_y)
                            await asyncio.sleep(0.5)
                            
                # Click confirm button if exists
                confirm_btn = await element.query_selector('.verify-captcha-submit-button, button:has-text("Confirm")')
                if confirm_btn:
                    await confirm_btn.click()
                    
        except Exception as e:
            logger.error(f"Error applying solution: {e}")
            await self.screenshot("error_applying_solution")
    
    async def import_google_cookies(self) -> bool:
        """
        Import cookies from local Chrome browser for Google and TikTok.
        This helps avoid bot detection by using an existing trusted session.
        """
        logger.info("Importing cookies from local Chrome browser...")
        try:
            # Extract cookies for Google and TikTok
            # We use a broad domain filter to catch all related cookies
            cookies_jar = browser_cookie3.chrome(domain_name="") 
            
            playwright_cookies = []
            domains_to_import = [".google.com", "google.com", ".tiktok.com", "tiktok.com", ".youtube.com", "youtube.com"]
            
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
                        'expires': cookie.expires
                    }
                    # Remove None values
                    cookie_dict = {k: v for k, v in cookie_dict.items() if v is not None}
                    playwright_cookies.append(cookie_dict)
                    count += 1
            
            if playwright_cookies:
                logger.info(f"Found {count} relevant cookies. Injecting into browser context...")
                await self.context.add_cookies(playwright_cookies)
                logger.success("Cookies imported successfully")
                return True
            else:
                logger.warning("No relevant cookies found in local Chrome")
                return False
                
        except Exception as e:
            logger.error(f"Failed to import cookies: {e}")
            logger.warning("Make sure Chrome is closed or you have granted permission to access Safe Storage.")
            return False

    async def login(self) -> bool:
        """
        Execute the full login flow.
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            await self.start_browser()
            
            # Import cookies before navigating
            # await self.import_google_cookies()
            
            logger.info("Navigating to TikTok...")
            await self.page.goto("https://www.tiktok.com/en/")
            await self.screenshot("01_homepage")
            
            # Check if we're already logged in
            current_url = self.page.url
            if "login" not in current_url.lower():
                # Try to find and click the Log in button
                try:
                    logger.info("Clicking sidebar login button (User provided selector)...")
                    # User provided XPath: //*[@id="header-login-button"]/div
                    # We use force=True to ensure click even if Playwright thinks it's hidden
                    await self.page.click('xpath=//*[@id="header-login-button"]/div', force=True)
                    
                    # Wait for modal to appear
                    logger.info("Waiting for login modal...")
                    await self.page.wait_for_selector('text="Log in to TikTok"', timeout=10000)
                    await self.screenshot("02_login_modal")
                    
                    # Click Continue with Google
                    logger.info("Clicking 'Continue with Google'...")
                    
                    async with self.page.expect_popup() as popup_info:
                        await self.page.click('text="Continue with Google"')
                    
                    popup = await popup_info.value
                    logger.info("Google login popup opened")
                    await popup.wait_for_load_state()
                    
                    logger.info("Waiting for Google login to complete...")
                    await popup.wait_for_event("close", timeout=60000)
                    logger.success("Google popup closed")
                    
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.warning(f"Login flow error: {e}")
            
            await self.screenshot("03_after_login_attempt")
            
            # Check for captcha and solve if present
            captcha_info = await self.detect_captcha()
            if captcha_info:
                logger.warning("Captcha detected during login flow")
                await self.screenshot("captcha_detected")
                
                solved = await self.solve_detected_captcha(captcha_info)
                if solved:
                    logger.success("Captcha solved successfully!")
                    await self.screenshot("04_after_captcha_solved")
                else:
                    logger.error("Failed to solve captcha")
                    await self.screenshot("04_captcha_failed")
                    # Continue anyway - sometimes captcha clears on its own
            
            # Verify login
            logger.info("Verifying login status...")
            try:
                # Check for profile icon or Upload button
                await self.page.wait_for_selector('[data-e2e="profile-icon"], [data-e2e="upload-icon"]', timeout=10000)
                logger.success("Login successful! (Profile detected)")
                
                # Save session
                if self.save_session:
                    await self._save_session()
                
                return True
            except:
                logger.error("Login verification failed - Profile icon not found")
                await self.screenshot("04_login_failed_verification")
                
                # Check for captcha again (might have appeared after failed login)
                captcha_info = await self.detect_captcha()
                if captcha_info:
                    logger.warning("Captcha detected after login failure - attempting to solve...")
                    solved = await self.solve_detected_captcha(captcha_info)
                    if solved:
                        # Try verification again
                        try:
                            await self.page.wait_for_selector('[data-e2e="profile-icon"], [data-e2e="upload-icon"]', timeout=10000)
                            logger.success("Login successful after captcha solve!")
                            if self.save_session:
                                await self._save_session()
                            return True
                        except:
                            pass
                
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            await self.screenshot("error")
            return False
    
    async def _save_session(self):
        """Save browser cookies and session data."""
        try:
            cookies = await self.context.cookies()
            session_data = {
                "cookies": cookies,
                "timestamp": datetime.now().isoformat(),
                "username": self.username
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logger.success(f"Session saved to: {self.session_file}")
            
        except Exception as e:
            logger.error(f"Error saving session: {e}")
    
    async def load_session(self) -> bool:
        """Load a saved session."""
        try:
            if not self.session_file.exists():
                logger.warning("No saved session found")
                return False
            
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            await self.context.add_cookies(session_data['cookies'])
            logger.success("Session loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return False
    
    async def cleanup(self):
        """Close browser and cleanup resources."""
        logger.info("Cleaning up...")
        
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
            
        # Cleanup temp directory
        if hasattr(self, 'temp_user_data_dir') and self.temp_user_data_dir.exists():
            import shutil
            logger.info(f"Removing temporary profile: {self.temp_user_data_dir}")
            try:
                shutil.rmtree(self.temp_user_data_dir)
            except Exception as e:
                logger.warning(f"Failed to remove temp dir: {e}")
        
        logger.info("Cleanup complete")


async def main():
    """Main execution function."""
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    automation = TikTokLoginAutomation(headless=False, save_session=True)
    
    try:
        success = await automation.login()
        
        if success:
            logger.success("✅ TikTok login automation completed successfully!")
            logger.info("Check the screenshots directory for visual confirmation")
        else:
            logger.error("❌ TikTok login automation failed")
            logger.info("Check the screenshots directory for debugging")
        
        # Keep browser open for a moment to review
        if not automation.headless:
            logger.info("Keeping browser open for 30 seconds for review...")
            await asyncio.sleep(30)
        
    except KeyboardInterrupt:
        logger.warning("Automation interrupted by user")
    except Exception as e:
        logger.error(f"Automation error: {e}")
        raise
    finally:
        await automation.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
