"""
Enhanced TikTok Login Automation v2
Based on screenshot analysis and recording patterns.
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, Optional, List
from loguru import logger
from playwright.async_api import async_playwright, Page, BrowserContext
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from automation.browser_profile_manager import BrowserProfileManager, BrowserType
from services.tiktok_captcha_solver import TikTokCaptchaSolver
from automation.safari_app_controller import SafariAppController


class TikTokLoginAutomationV2:
    """
    Enhanced login automation based on recorded patterns.
    Uses multiple detection methods for robust login verification.
    """
    
    def __init__(self, browser_type: BrowserType = "safari", use_profile: bool = True):
        self.browser_manager = BrowserProfileManager()
        self.captcha_solver = TikTokCaptchaSolver()
        self.browser_type = browser_type
        self.use_profile = use_profile
        
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.safari_controller: Optional[SafariAppController] = None
        self.using_actual_safari = False
        
        # Login detection methods (from analysis)
        self.detection_methods = [
            self._detect_login_by_url,
            self._detect_login_by_dom_elements,
            self._detect_login_by_cookies,
            self._detect_login_by_page_content
        ]
    
    async def start_browser(self):
        """Start browser with profile."""
        logger.info(f"Starting {self.browser_type} browser...")
        self.playwright = await async_playwright().start()
        
        if self.browser_type == "safari":
            # Use actual Safari.app
            self.safari_controller = SafariAppController()
            self.using_actual_safari = True
            await self.safari_controller.launch_safari("https://www.tiktok.com/en/")
            logger.success("✅ Safari.app opened")
        else:
            # Use Playwright Chrome
            if self.use_profile:
                profile = self.browser_manager.get_saved_profile()
                if not profile or profile.get("browser") != "chrome":
                    profile = self.browser_manager.select_profile("chrome", "Default")
                
                if profile:
                    user_data_dir = self.browser_manager.get_chrome_user_data_dir()
                    context = await self.playwright.chromium.launch_persistent_context(
                        user_data_dir=str(user_data_dir / profile['name']),
                        headless=False,
                        args=['--disable-blink-features=AutomationControlled']
                    )
                    self.context = context
                    pages = context.pages
                    if pages:
                        self.page = pages[0]
                    else:
                        self.page = await context.new_page()
                    logger.success(f"✅ Chrome opened with profile: {profile['name']}")
                else:
                    browser = await self.playwright.chromium.launch(headless=False)
                    self.context = await browser.new_context()
                    self.page = await self.context.new_page()
            else:
                browser = await self.playwright.chromium.launch(headless=False)
                self.context = await browser.new_context()
                self.page = await self.context.new_page()
            
            await self.page.goto("https://www.tiktok.com/en/")
    
    async def _detect_login_by_url(self) -> bool:
        """Method 1: URL-based detection (medium confidence)."""
        try:
            if self.using_actual_safari and self.safari_controller:
                current_url = await self.safari_controller.get_current_url()
            elif self.page:
                current_url = self.page.url
            else:
                return False
            
            # Check if URL contains tiktok.com but not login/passport
            if 'tiktok.com' in current_url.lower():
                if 'login' not in current_url.lower() and 'passport' not in current_url.lower():
                    logger.debug("✅ Login detected by URL pattern")
                    return True
            return False
        except Exception as e:
            logger.debug(f"URL detection error: {e}")
            return False
    
    async def _detect_login_by_dom_elements(self) -> bool:
        """Method 2: DOM element detection (high confidence)."""
        try:
            if self.using_actual_safari and self.safari_controller:
                # Use JavaScript injection to check for elements
                script = '''
                tell application "Safari"
                    tell front window
                        tell current tab
                            do JavaScript "
                                (function() {
                                    var profileIcon = document.querySelector('[data-e2e=\"profile-icon\"], [data-e2e=\"upload-icon\"], [data-e2e=\"user-avatar\"]');
                                    var uploadButton = document.querySelector('[data-e2e=\"upload-button\"]');
                                    var userMenu = document.querySelector('[data-e2e=\"user-menu\"]');
                                    return (profileIcon || uploadButton || userMenu) ? 'found' : 'not_found';
                                })();
                            "
                        end tell
                    end tell
                end tell
                '''
                result = self.safari_controller._run_applescript(script)
                if 'found' in result.lower():
                    logger.debug("✅ Login detected by DOM elements (Safari)")
                    return True
            elif self.page:
                # Use Playwright selectors
                selectors = [
                    '[data-e2e="profile-icon"]',
                    '[data-e2e="upload-icon"]',
                    '[data-e2e="upload-button"]',
                    '[data-e2e="user-avatar"]',
                    '[data-e2e="user-menu"]',
                    'button[aria-label*="Profile"]',
                    'a[href*="/@"]'  # User profile link
                ]
                
                for selector in selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            logger.debug(f"✅ Login detected by DOM element: {selector}")
                            return True
                    except:
                        continue
            return False
        except Exception as e:
            logger.debug(f"DOM detection error: {e}")
            return False
    
    async def _detect_login_by_cookies(self) -> bool:
        """Method 3: Cookie-based detection (high confidence)."""
        try:
            if self.using_actual_safari:
                # Safari cookies require special handling
                # For now, skip cookie detection for Safari
                return False
            elif self.page:
                cookies = await self.context.cookies()
                auth_indicators = ['session', 'token', 'auth', 'login', 'sid', 'tt_chain_token']
                
                for cookie in cookies:
                    name_lower = cookie.get('name', '').lower()
                    if any(indicator in name_lower for indicator in auth_indicators):
                        logger.debug(f"✅ Login detected by cookie: {cookie.get('name')}")
                        return True
            return False
        except Exception as e:
            logger.debug(f"Cookie detection error: {e}")
            return False
    
    async def _detect_login_by_page_content(self) -> bool:
        """Method 4: Page content detection (medium confidence)."""
        try:
            if self.using_actual_safari and self.safari_controller:
                script = '''
                tell application "Safari"
                    tell front window
                        tell current tab
                            do JavaScript "
                                (function() {
                                    var bodyText = document.body.innerText || '';
                                    var hasLoginButton = /log\\s*in|sign\\s*in/i.test(bodyText);
                                    var hasProfileElements = document.querySelector('[href*=\"/@\"]') !== null;
                                    return (!hasLoginButton && hasProfileElements) ? 'logged_in' : 'not_logged_in';
                                })();
                            "
                        end tell
                    end tell
                end tell
                '''
                result = self.safari_controller._run_applescript(script)
                if 'logged_in' in result.lower():
                    logger.debug("✅ Login detected by page content (Safari)")
                    return True
            elif self.page:
                # Check for absence of login button and presence of user elements
                try:
                    login_button = await self.page.query_selector('button:has-text("Log in"), a:has-text("Log in")')
                    profile_link = await self.page.query_selector('a[href*="/@"]')
                    
                    if not login_button and profile_link:
                        logger.debug("✅ Login detected by page content")
                        return True
                except:
                    pass
            return False
        except Exception as e:
            logger.debug(f"Content detection error: {e}")
            return False
    
    async def check_login_status(self, use_all_methods: bool = True) -> Dict:
        """
        Check login status using multiple detection methods.
        
        Returns:
            Dict with 'logged_in' (bool) and 'confidence' (str: 'high', 'medium', 'low')
        """
        results = []
        
        for method in self.detection_methods:
            try:
                result = await method()
                results.append(result)
                if result and not use_all_methods:
                    # Early exit if we get a high-confidence match
                    break
            except Exception as e:
                logger.debug(f"Detection method error: {e}")
                results.append(False)
        
        # Calculate confidence based on number of positive results
        positive_count = sum(results)
        total_methods = len(self.detection_methods)
        
        if positive_count >= 2:
            confidence = 'high'
        elif positive_count == 1:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        logged_in = positive_count > 0
        
        return {
            'logged_in': logged_in,
            'confidence': confidence,
            'method_results': {
                'url_check': results[0] if len(results) > 0 else False,
                'dom_elements': results[1] if len(results) > 1 else False,
                'cookies': results[2] if len(results) > 2 else False,
                'page_content': results[3] if len(results) > 3 else False
            },
            'positive_count': positive_count,
            'total_methods': total_methods
        }
    
    async def wait_for_login(self, timeout: int = 300, check_interval: float = 2.0) -> bool:
        """
        Wait for login to complete, checking periodically.
        
        Args:
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
        
        Returns:
            True if login detected, False if timeout
        """
        logger.info(f"⏳ Waiting for login (timeout: {timeout}s)...")
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            status = await self.check_login_status()
            
            if status['logged_in']:
                logger.success(f"✅ Login detected! (confidence: {status['confidence']})")
                logger.info(f"   Methods: URL={status['method_results']['url_check']}, "
                          f"DOM={status['method_results']['dom_elements']}, "
                          f"Cookies={status['method_results']['cookies']}, "
                          f"Content={status['method_results']['page_content']}")
                return True
            
            await asyncio.sleep(check_interval)
        
        logger.warning("⏱️  Login timeout - login not detected")
        return False
    
    async def detect_captcha(self) -> Optional[Dict]:
        """Detect if captcha is present."""
        try:
            if self.using_actual_safari and self.safari_controller:
                return await self.safari_controller.detect_captcha()
            elif self.page:
                # Check for captcha elements
                captcha_selectors = [
                    '.secsdk-captcha-wrapper',
                    '[class*="captcha"]',
                    'iframe[src*="captcha"]'
                ]
                
                for selector in captcha_selectors:
                    element = await self.page.query_selector(selector)
                    if element:
                        return {'type': 'unknown', 'element': selector}
            return None
        except Exception as e:
            logger.debug(f"Captcha detection error: {e}")
            return None
    
    async def solve_captcha_if_present(self) -> bool:
        """Detect and solve captcha if present."""
        captcha_info = await self.detect_captcha()
        if captcha_info:
            logger.warning("⚠️  Captcha detected! Attempting to solve...")
            
            if self.using_actual_safari and self.safari_controller:
                # Get captcha images
                image_urls = await self.safari_controller.get_captcha_image_urls()
                if image_urls:
                    # Solve using captcha solver
                    solution = await self.captcha_solver.solve_captcha(
                        captcha_type=captcha_info.get('type', 'unknown'),
                        image_urls=image_urls
                    )
                    if solution:
                        # Apply solution
                        return await self.safari_controller.apply_captcha_solution(solution)
            else:
                # Playwright captcha solving
                logger.warning("Captcha solving for Playwright not yet implemented")
            
            return False
        return True  # No captcha to solve
    
    async def save_session(self, output_path: Optional[Path] = None):
        """Save browser session (cookies, etc.) for reuse."""
        if output_path is None:
            output_path = Path(__file__).parent / "sessions" / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path.parent.mkdir(exist_ok=True)
        
        session_data = {
            'saved_at': datetime.now().isoformat(),
            'browser_type': self.browser_type,
            'using_actual_safari': self.using_actual_safari
        }
        
        if self.using_actual_safari:
            current_url = await self.safari_controller.get_current_url()
            session_data['url'] = current_url
            logger.info("Safari session saved (cookies are in Safari's storage)")
        elif self.page:
            cookies = await self.context.cookies()
            session_data['cookies'] = cookies
            session_data['url'] = self.page.url
        
        with open(output_path, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        logger.success(f"✅ Session saved to: {output_path}")
        return output_path
    
    async def cleanup(self):
        """Clean up browser resources."""
        if self.playwright:
            if self.context and not self.using_actual_safari:
                await self.context.close()
            await self.playwright.stop()


async def main():
    """Example usage."""
    automation = TikTokLoginAutomationV2(browser_type="safari", use_profile=True)
    
    try:
        await automation.start_browser()
        
        logger.info("Browser opened. Please log in manually...")
        logger.info("The system will detect when login is complete.")
        
        # Wait for login
        logged_in = await automation.wait_for_login(timeout=300)
        
        if logged_in:
            # Save session
            await automation.save_session()
            logger.success("✅ Login complete and session saved!")
        else:
            logger.warning("Login not detected within timeout")
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await automation.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

