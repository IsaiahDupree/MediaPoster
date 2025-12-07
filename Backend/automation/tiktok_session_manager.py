"""
TikTok Session Manager
Handles cookie persistence, session state, and action history tracking.
"""
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger

try:
    import browser_cookie3
    BROWSER_COOKIES_AVAILABLE = True
except ImportError:
    BROWSER_COOKIES_AVAILABLE = False


class TikTokSessionManager:
    """
    Manages TikTok session cookies and application state.
    
    Features:
    - Save/restore cookies to persist login
    - Track current page state
    - Record action history for debugging
    - Rate limit tracking
    """
    
    def __init__(self, 
                 session_dir: Optional[Path] = None,
                 max_action_history: int = 100):
        """
        Initialize the session manager.
        
        Args:
            session_dir: Directory to store session files
            max_action_history: Maximum number of actions to keep in history
        """
        if session_dir is None:
            session_dir = Path(__file__).parent / "sessions"
        
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True, parents=True)
        
        self.max_action_history = max_action_history
        
        # Session state
        self.cookies: List[Dict] = []
        self.session_saved_at: Optional[datetime] = None
        self.logged_in_user: Optional[str] = None
        
        # Current state
        self.current_state: Dict = {
            "page_type": "unknown",  # fyp, profile, video, search, inbox, other
            "current_url": "",
            "last_action": None,
            "last_action_time": None
        }
        
        # Action history
        self.action_history: List[Dict] = []
        
        # Rate limit tracking
        self.rate_limits: Dict[str, Dict] = {
            "like": {"count": 0, "window_start": None, "max_per_hour": 100},
            "comment": {"count": 0, "window_start": None, "max_per_hour": 30},
            "follow": {"count": 0, "window_start": None, "max_per_hour": 50},
            "message": {"count": 0, "window_start": None, "max_per_hour": 20},
            "navigation": {"count": 0, "window_start": None, "max_per_hour": 200}
        }
    
    # ==================== Cookie Management ====================
    
    async def save_cookies_from_safari(self) -> bool:
        """
        Extract and save cookies from Safari.
        
        Returns:
            True if cookies were saved successfully.
        """
        if not BROWSER_COOKIES_AVAILABLE:
            logger.warning("browser_cookie3 not available. Cannot extract Safari cookies.")
            return False
        
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
            
            self.cookies = cookies
            self.session_saved_at = datetime.now()
            
            # Save to file
            session_file = self.session_dir / "tiktok_cookies.json"
            session_data = {
                "cookies": cookies,
                "saved_at": self.session_saved_at.isoformat(),
                "cookie_count": len(cookies)
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logger.success(f"✅ Saved {len(cookies)} TikTok cookies to {session_file}")
            return True
            
        except PermissionError:
            logger.error("❌ Permission denied. Grant Full Disk Access to Terminal.")
            return False
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False
    
    async def save_cookies_from_context(self, context) -> bool:
        """
        Save cookies from a Playwright browser context.
        
        Args:
            context: Playwright BrowserContext
            
        Returns:
            True if cookies were saved successfully.
        """
        try:
            cookies = await context.cookies()
            
            # Filter to TikTok cookies
            tiktok_cookies = [
                c for c in cookies 
                if 'tiktok' in c.get('domain', '').lower()
            ]
            
            self.cookies = tiktok_cookies
            self.session_saved_at = datetime.now()
            
            # Save to file
            session_file = self.session_dir / "tiktok_cookies.json"
            session_data = {
                "cookies": tiktok_cookies,
                "saved_at": self.session_saved_at.isoformat(),
                "cookie_count": len(tiktok_cookies),
                "source": "playwright"
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logger.success(f"✅ Saved {len(tiktok_cookies)} cookies from Playwright context")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save cookies from context: {e}")
            return False
    
    async def load_cookies(self, path: Optional[Path] = None) -> List[Dict]:
        """
        Load cookies from a saved session file.
        
        Args:
            path: Path to cookie file (default: session_dir/tiktok_cookies.json)
            
        Returns:
            List of cookie dictionaries.
        """
        if path is None:
            path = self.session_dir / "tiktok_cookies.json"
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            self.cookies = data.get('cookies', [])
            
            if 'saved_at' in data:
                self.session_saved_at = datetime.fromisoformat(data['saved_at'])
            
            logger.info(f"✅ Loaded {len(self.cookies)} cookies from {path}")
            return self.cookies
            
        except FileNotFoundError:
            logger.warning(f"Cookie file not found: {path}")
            return []
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return []
    
    async def inject_cookies_into_context(self, context) -> bool:
        """
        Inject stored cookies into a Playwright context.
        
        Args:
            context: Playwright BrowserContext
            
        Returns:
            True if cookies were injected.
        """
        if not self.cookies:
            await self.load_cookies()
        
        if not self.cookies:
            logger.warning("No cookies to inject")
            return False
        
        try:
            await context.add_cookies(self.cookies)
            logger.success(f"✅ Injected {len(self.cookies)} cookies into browser")
            return True
        except Exception as e:
            logger.error(f"Failed to inject cookies: {e}")
            return False
    
    def get_session_age(self) -> Optional[timedelta]:
        """
        Get how old the saved session is.
        
        Returns:
            timedelta since session was saved, or None if no session.
        """
        if self.session_saved_at:
            return datetime.now() - self.session_saved_at
        return None
    
    def is_session_fresh(self, max_age_hours: int = 24) -> bool:
        """
        Check if the session is fresh (not too old).
        
        Args:
            max_age_hours: Maximum age in hours to consider fresh.
            
        Returns:
            True if session is fresh.
        """
        age = self.get_session_age()
        if age is None:
            return False
        return age < timedelta(hours=max_age_hours)
    
    # ==================== State Management ====================
    
    def update_state(self, **kwargs) -> None:
        """
        Update current state with new values.
        
        Args:
            **kwargs: State fields to update (page_type, current_url, etc.)
        """
        self.current_state.update(kwargs)
        self.current_state['last_updated'] = datetime.now().isoformat()
    
    def get_current_state(self) -> Dict:
        """
        Get the current session state.
        
        Returns:
            Dict with current state.
        """
        return {
            **self.current_state,
            "logged_in_user": self.logged_in_user,
            "session_age": str(self.get_session_age()) if self.get_session_age() else None,
            "action_count": len(self.action_history),
            "rate_limits": self._get_rate_limit_status()
        }
    
    def detect_page_type(self, url: str) -> str:
        """
        Detect the page type from a URL.
        
        Args:
            url: TikTok URL
            
        Returns:
            Page type string: fyp, profile, video, search, inbox, other
        """
        url_lower = url.lower()
        
        if '/foryou' in url_lower or url_lower.endswith('/en/') or url_lower.endswith('.com/'):
            return 'fyp'
        elif '/@' in url_lower:
            if '/video/' in url_lower:
                return 'video'
            return 'profile'
        elif '/video/' in url_lower:
            return 'video'
        elif '/search' in url_lower:
            return 'search'
        elif '/messages' in url_lower or '/inbox' in url_lower:
            return 'inbox'
        elif '/login' in url_lower or '/passport' in url_lower:
            return 'login'
        else:
            return 'other'
    
    def save_state_to_file(self) -> Path:
        """
        Save current state to a file.
        
        Returns:
            Path to the state file.
        """
        state_file = self.session_dir / "session_state.json"
        
        state_data = {
            "current_state": self.current_state,
            "logged_in_user": self.logged_in_user,
            "session_saved_at": self.session_saved_at.isoformat() if self.session_saved_at else None,
            "action_history": self.action_history[-20:],  # Save last 20 actions
            "rate_limits": self.rate_limits,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2)
        
        logger.debug(f"State saved to {state_file}")
        return state_file
    
    def load_state_from_file(self) -> bool:
        """
        Load state from a file.
        
        Returns:
            True if state was loaded.
        """
        state_file = self.session_dir / "session_state.json"
        
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
            
            self.current_state = data.get('current_state', self.current_state)
            self.logged_in_user = data.get('logged_in_user')
            self.action_history = data.get('action_history', [])
            
            if data.get('session_saved_at'):
                self.session_saved_at = datetime.fromisoformat(data['session_saved_at'])
            
            # Restore rate limits but reset counts if window has expired
            saved_limits = data.get('rate_limits', {})
            for action_type, limits in saved_limits.items():
                if action_type in self.rate_limits:
                    if limits.get('window_start'):
                        window_start = datetime.fromisoformat(limits['window_start'])
                        if datetime.now() - window_start < timedelta(hours=1):
                            self.rate_limits[action_type] = limits
            
            logger.info("✅ State loaded from file")
            return True
            
        except FileNotFoundError:
            logger.debug("No saved state file found")
            return False
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False
    
    # ==================== Action History ====================
    
    def add_action(self, action_type: str, details: Dict = None) -> None:
        """
        Record an action in the history.
        
        Args:
            action_type: Type of action (like, comment, follow, navigate, etc.)
            details: Action details
        """
        action = {
            "type": action_type,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        self.action_history.append(action)
        
        # Trim history if too long
        if len(self.action_history) > self.max_action_history:
            self.action_history = self.action_history[-self.max_action_history:]
        
        # Update last action in state
        self.current_state['last_action'] = action_type
        self.current_state['last_action_time'] = action['timestamp']
        
        # Update rate limit counters
        self._update_rate_limit(action_type)
    
    def get_action_history(self, 
                           action_type: Optional[str] = None,
                           limit: int = 50) -> List[Dict]:
        """
        Get action history, optionally filtered by type.
        
        Args:
            action_type: Filter by action type (optional)
            limit: Maximum number of actions to return
            
        Returns:
            List of action records.
        """
        history = self.action_history
        
        if action_type:
            history = [a for a in history if a['type'] == action_type]
        
        return history[-limit:]
    
    # ==================== Rate Limiting ====================
    
    def _update_rate_limit(self, action_type: str) -> None:
        """Update rate limit counter for an action type."""
        if action_type not in self.rate_limits:
            return
        
        limits = self.rate_limits[action_type]
        now = datetime.now()
        
        # Check if we're in a new window
        if limits['window_start'] is None:
            limits['window_start'] = now.isoformat()
            limits['count'] = 1
        else:
            window_start = datetime.fromisoformat(limits['window_start'])
            if now - window_start >= timedelta(hours=1):
                # New window
                limits['window_start'] = now.isoformat()
                limits['count'] = 1
            else:
                limits['count'] += 1
    
    def _get_rate_limit_status(self) -> Dict[str, Dict]:
        """Get current rate limit status for all action types."""
        status = {}
        now = datetime.now()
        
        for action_type, limits in self.rate_limits.items():
            remaining = limits['max_per_hour'] - limits['count']
            
            time_until_reset = None
            if limits['window_start']:
                window_start = datetime.fromisoformat(limits['window_start'])
                reset_time = window_start + timedelta(hours=1)
                if reset_time > now:
                    time_until_reset = str(reset_time - now)
            
            status[action_type] = {
                "count": limits['count'],
                "max": limits['max_per_hour'],
                "remaining": max(0, remaining),
                "time_until_reset": time_until_reset
            }
        
        return status
    
    def can_perform_action(self, action_type: str) -> bool:
        """
        Check if an action can be performed (rate limit check).
        
        Args:
            action_type: Type of action to check
            
        Returns:
            True if action is allowed.
        """
        if action_type not in self.rate_limits:
            return True
        
        limits = self.rate_limits[action_type]
        now = datetime.now()
        
        # Check if window has reset
        if limits['window_start']:
            window_start = datetime.fromisoformat(limits['window_start'])
            if now - window_start >= timedelta(hours=1):
                return True  # Window reset
        
        return limits['count'] < limits['max_per_hour']
    
    def get_wait_time_for_action(self, action_type: str) -> float:
        """
        Get recommended wait time before performing an action.
        
        Args:
            action_type: Type of action
            
        Returns:
            Seconds to wait (0 if no wait needed).
        """
        import random
        
        # Default delays (min, max) in seconds
        delays = {
            "like": (2.0, 5.0),
            "comment": (5.0, 15.0),
            "follow": (3.0, 8.0),
            "message": (10.0, 30.0),
            "navigation": (1.0, 3.0)
        }
        
        if action_type not in delays:
            return random.uniform(1.0, 2.0)
        
        min_delay, max_delay = delays[action_type]
        return random.uniform(min_delay, max_delay)


# Convenience function
def create_session_manager(session_dir: Optional[Path] = None) -> TikTokSessionManager:
    """Create a new session manager instance."""
    return TikTokSessionManager(session_dir=session_dir)


# Test function
async def test_session_manager():
    """Test the session manager."""
    print("Testing TikTok Session Manager...")
    
    manager = TikTokSessionManager()
    
    # Test state management
    manager.update_state(page_type="fyp", current_url="https://www.tiktok.com/en/")
    print(f"Current state: {manager.get_current_state()}")
    
    # Test page type detection
    test_urls = [
        "https://www.tiktok.com/en/",
        "https://www.tiktok.com/@username",
        "https://www.tiktok.com/@username/video/123456",
        "https://www.tiktok.com/search?q=test",
        "https://www.tiktok.com/messages"
    ]
    
    for url in test_urls:
        page_type = manager.detect_page_type(url)
        print(f"  {url[:50]}... -> {page_type}")
    
    # Test action history
    manager.add_action("like", {"video_id": "123"})
    manager.add_action("comment", {"text": "Great video!"})
    manager.add_action("navigation", {"url": "https://tiktok.com/@user"})
    
    print(f"\nAction history: {len(manager.action_history)} actions")
    
    # Test rate limits
    print(f"\nRate limits: {manager._get_rate_limit_status()}")
    
    # Test save/load
    manager.save_state_to_file()
    print("\n✅ State saved to file")
    
    # Load cookies if available
    cookies = await manager.load_cookies()
    print(f"Loaded {len(cookies)} cookies")
    
    print("\n✅ Session manager test complete!")


if __name__ == "__main__":
    asyncio.run(test_session_manager())
