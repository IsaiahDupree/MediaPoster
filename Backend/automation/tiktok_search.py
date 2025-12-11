"""
TikTok Search - Browser automation for searching users, hashtags, and videos.

Usage:
    from automation.tiktok_search import TikTokSearch
    
    search = TikTokSearch(safari_controller)
    users = search.search_users("arduino")
    videos = search.search_videos("#coding")
"""

import time
import pyautogui
from typing import Optional, List, Dict
from dataclasses import dataclass
from urllib.parse import quote


@dataclass
class SearchResult:
    """Base search result."""
    title: str = ""
    subtitle: str = ""
    url: Optional[str] = None


@dataclass
class UserResult(SearchResult):
    """User search result."""
    username: str = ""
    followers: str = ""
    verified: bool = False


@dataclass
class VideoResult(SearchResult):
    """Video search result."""
    author: str = ""
    views: str = ""
    likes: str = ""


@dataclass
class HashtagResult(SearchResult):
    """Hashtag search result."""
    name: str = ""
    views: str = ""
    posts: str = ""


class TikTokSearch:
    """
    Browser automation for TikTok search functionality.
    
    Supports:
    - User search
    - Video/content search
    - Hashtag search
    - Sound/music search
    """
    
    SELECTORS = {
        # Search bar
        "search_input": 'input[data-e2e="search-user-input"]',
        "search_input_alt": 'input[type="search"]',
        "search_button": '[data-e2e="search-icon"]',
        "search_clear": '[data-e2e="search-clear-icon"]',
        
        # Search results page tabs
        "tab_top": '[data-e2e="search-top-tab"]',
        "tab_users": '[data-e2e="search-user-tab"]',
        "tab_videos": '[data-e2e="search-video-tab"]',
        "tab_sounds": '[data-e2e="search-sound-tab"]',
        "tab_live": '[data-e2e="search-live-tab"]',
        
        # User results
        "user_card": '[data-e2e="search-user-card"]',
        "user_avatar": '[data-e2e="search-avatar"]',
        "user_username": '[data-e2e="search-username"]',
        "user_nickname": '[data-e2e="search-nickname"]',
        "user_follower_count": '[data-e2e="search-follow-count"]',
        
        # Video results
        "video_card": '[data-e2e="search-video-card"]',
        "video_item": '[class*="DivItemContainer"]',
        
        # Hashtag results
        "hashtag_card": '[data-e2e="search-challenge-card"]',
        "hashtag_name": '[class*="ChallengeTitle"]',
        "hashtag_views": '[class*="ChallengeViews"]',
    }
    
    # URL patterns for direct navigation
    SEARCH_URLS = {
        "top": "https://www.tiktok.com/search?q={query}",
        "users": "https://www.tiktok.com/search/user?q={query}",
        "videos": "https://www.tiktok.com/search/video?q={query}",
        "sounds": "https://www.tiktok.com/search/sound?q={query}",
        "live": "https://www.tiktok.com/search/live?q={query}",
    }
    
    def __init__(self, safari_controller):
        """
        Initialize search with Safari controller.
        
        Args:
            safari_controller: SafariController instance
        """
        self.safari = safari_controller
        self.last_query: Optional[str] = None
    
    def search(self, query: str, search_type: str = "top") -> bool:
        """
        Perform a search and navigate to results page.
        
        Args:
            query: Search query
            search_type: One of 'top', 'users', 'videos', 'sounds', 'live'
            
        Returns:
            True if search successful
        """
        if search_type not in self.SEARCH_URLS:
            search_type = "top"
        
        # Navigate directly to search URL (more reliable than typing)
        url = self.SEARCH_URLS[search_type].format(query=quote(query))
        self.safari.navigate(url)
        
        time.sleep(3)  # Wait for results to load
        
        self.last_query = query
        
        # Verify results loaded
        check = self.safari.run_js("""
            var results = document.querySelectorAll('[data-e2e*="search"]');
            var cards = document.querySelectorAll('[class*="DivItemContainer"], [class*="DivUserCard"]');
            return (results.length > 0 || cards.length > 0) ? 'LOADED' : 'EMPTY';
        """)
        
        return 'LOADED' in check
    
    def search_via_input(self, query: str) -> bool:
        """
        Search by typing into search bar (alternative method).
        
        Args:
            query: Search query
            
        Returns:
            True if search submitted
        """
        # Click search input
        result = self.safari.run_js(f"""
            var input = document.querySelector('{self.SELECTORS["search_input"]}');
            if (!input) input = document.querySelector('{self.SELECTORS["search_input_alt"]}');
            
            if (input) {{
                input.focus();
                input.click();
                return 'FOCUSED';
            }}
            return 'NOT_FOUND';
        """)
        
        if 'FOCUSED' not in result:
            return False
        
        time.sleep(0.3)
        
        # Clear existing text and type query
        pyautogui.hotkey('command', 'a')
        pyautogui.typewrite(query, interval=0.03)
        time.sleep(0.5)
        
        # Submit search
        pyautogui.press('return')
        time.sleep(3)
        
        self.last_query = query
        return True
    
    def switch_tab(self, tab: str) -> bool:
        """
        Switch to a different search results tab.
        
        Args:
            tab: One of 'top', 'users', 'videos', 'sounds', 'live'
            
        Returns:
            True if tab switched
        """
        tab_selector = {
            "top": self.SELECTORS["tab_top"],
            "users": self.SELECTORS["tab_users"],
            "videos": self.SELECTORS["tab_videos"],
            "sounds": self.SELECTORS["tab_sounds"],
            "live": self.SELECTORS["tab_live"],
        }.get(tab)
        
        if not tab_selector:
            return False
        
        result = self.safari.run_js(f"""
            var tab = document.querySelector('{tab_selector}');
            if (tab) {{
                tab.click();
                return 'CLICKED';
            }}
            return 'NOT_FOUND';
        """)
        
        if 'CLICKED' in result:
            time.sleep(2)
            return True
        
        return False
    
    def search_users(self, query: str, limit: int = 20) -> List[UserResult]:
        """
        Search for users and return results.
        
        Args:
            query: Search query
            limit: Max results to return
            
        Returns:
            List of UserResult objects
        """
        if not self.search(query, "users"):
            return []
        
        time.sleep(2)
        
        result = self.safari.run_js(f"""
            var users = [];
            var cards = document.querySelectorAll('[data-e2e="search-user-card"], [class*="DivUserCardContainer"]');
            
            var count = Math.min(cards.length, {limit});
            for (var i = 0; i < count; i++) {{
                var card = cards[i];
                var username = card.querySelector('[data-e2e="search-username"], [class*="Username"]');
                var nickname = card.querySelector('[data-e2e="search-nickname"], [class*="Nickname"]');
                var followers = card.querySelector('[data-e2e="search-follow-count"], [class*="FollowerCount"]');
                var verified = card.querySelector('[class*="Verified"], svg[class*="verified"]');
                var link = card.querySelector('a[href*="/@"]');
                
                users.push({{
                    username: username ? username.innerText.trim().replace('@', '') : '',
                    title: nickname ? nickname.innerText.trim() : '',
                    subtitle: followers ? followers.innerText.trim() : '',
                    followers: followers ? followers.innerText.trim() : '',
                    verified: !!verified,
                    url: link ? link.href : ''
                }});
            }}
            
            return JSON.stringify(users);
        """)
        
        try:
            import json
            data = json.loads(result)
            return [UserResult(**u) for u in data]
        except:
            return []
    
    def search_videos(self, query: str, limit: int = 20) -> List[VideoResult]:
        """
        Search for videos and return results.
        
        Args:
            query: Search query (can include hashtags)
            limit: Max results to return
            
        Returns:
            List of VideoResult objects
        """
        if not self.search(query, "videos"):
            return []
        
        time.sleep(2)
        
        result = self.safari.run_js(f"""
            var videos = [];
            var items = document.querySelectorAll('[data-e2e="search-video-card"], [class*="DivItemContainer"]');
            
            var count = Math.min(items.length, {limit});
            for (var i = 0; i < count; i++) {{
                var item = items[i];
                var title = item.querySelector('[class*="Title"], [class*="Caption"]');
                var author = item.querySelector('[class*="Author"], [class*="Username"]');
                var views = item.querySelector('[class*="Views"], [class*="PlayCount"]');
                var likes = item.querySelector('[class*="Likes"], [data-e2e="like-count"]');
                var link = item.querySelector('a[href*="/video/"]');
                
                videos.push({{
                    title: title ? title.innerText.trim().substring(0, 100) : '',
                    subtitle: author ? author.innerText.trim() : '',
                    author: author ? author.innerText.trim() : '',
                    views: views ? views.innerText.trim() : '',
                    likes: likes ? likes.innerText.trim() : '',
                    url: link ? link.href : ''
                }});
            }}
            
            return JSON.stringify(videos);
        """)
        
        try:
            import json
            data = json.loads(result)
            return [VideoResult(**v) for v in data]
        except:
            return []
    
    def search_hashtags(self, query: str, limit: int = 10) -> List[HashtagResult]:
        """
        Search for hashtags/challenges.
        
        Args:
            query: Hashtag to search (with or without #)
            limit: Max results
            
        Returns:
            List of HashtagResult objects
        """
        # Clean hashtag
        query = query.lstrip('#')
        
        if not self.search(query, "top"):
            return []
        
        time.sleep(2)
        
        result = self.safari.run_js(f"""
            var hashtags = [];
            var cards = document.querySelectorAll('[data-e2e="search-challenge-card"], [class*="ChallengeCard"]');
            
            var count = Math.min(cards.length, {limit});
            for (var i = 0; i < count; i++) {{
                var card = cards[i];
                var name = card.querySelector('[class*="ChallengeTitle"], [class*="HashtagTitle"]');
                var views = card.querySelector('[class*="ChallengeViews"], [class*="ViewCount"]');
                var link = card.querySelector('a[href*="/tag/"]');
                
                hashtags.push({{
                    name: name ? name.innerText.trim().replace('#', '') : '',
                    title: name ? name.innerText.trim() : '',
                    subtitle: views ? views.innerText.trim() : '',
                    views: views ? views.innerText.trim() : '',
                    posts: '',
                    url: link ? link.href : ''
                }});
            }}
            
            return JSON.stringify(hashtags);
        """)
        
        try:
            import json
            data = json.loads(result)
            return [HashtagResult(**h) for h in data]
        except:
            return []
    
    def click_first_result(self) -> bool:
        """
        Click on the first search result.
        
        Returns:
            True if clicked
        """
        result = self.safari.run_js("""
            var first = document.querySelector(
                '[data-e2e="search-user-card"] a, ' +
                '[data-e2e="search-video-card"] a, ' +
                '[class*="DivItemContainer"] a, ' +
                '[class*="DivUserCardContainer"] a'
            );
            
            if (first) {
                first.click();
                return 'CLICKED';
            }
            return 'NOT_FOUND';
        """)
        
        if 'CLICKED' in result:
            time.sleep(2)
            return True
        
        return False
    
    def scroll_load_more(self, scrolls: int = 3) -> int:
        """
        Scroll to load more search results.
        
        Args:
            scrolls: Number of scroll actions
            
        Returns:
            Number of results after scrolling
        """
        initial_count = int(self.safari.run_js("""
            return document.querySelectorAll(
                '[data-e2e*="search-"] [class*="Container"], ' +
                '[class*="DivItemContainer"]'
            ).length;
        """) or 0)
        
        for _ in range(scrolls):
            self.safari.run_js("window.scrollBy(0, window.innerHeight);")
            time.sleep(1.5)
        
        final_count = int(self.safari.run_js("""
            return document.querySelectorAll(
                '[data-e2e*="search-"] [class*="Container"], ' +
                '[class*="DivItemContainer"]'
            ).length;
        """) or 0)
        
        return final_count
    
    def navigate_to_user(self, username: str) -> bool:
        """
        Navigate directly to a user's profile.
        
        Args:
            username: TikTok username (without @)
            
        Returns:
            True if navigation successful
        """
        username = username.lstrip('@')
        url = f"https://www.tiktok.com/@{username}"
        self.safari.navigate(url)
        time.sleep(3)
        
        # Verify profile loaded
        check = self.safari.run_js("""
            var username = document.querySelector('[data-e2e="user-title"], [class*="UserTitle"]');
            return username ? 'LOADED' : 'NOT_FOUND';
        """)
        
        return 'LOADED' in check
    
    def navigate_to_hashtag(self, hashtag: str) -> bool:
        """
        Navigate directly to a hashtag page.
        
        Args:
            hashtag: Hashtag name (with or without #)
            
        Returns:
            True if navigation successful
        """
        hashtag = hashtag.lstrip('#')
        url = f"https://www.tiktok.com/tag/{hashtag}"
        self.safari.navigate(url)
        time.sleep(3)
        
        # Verify hashtag page loaded
        check = self.safari.run_js("""
            var title = document.querySelector('[data-e2e="challenge-title"], [class*="ChallengeTitle"]');
            var videos = document.querySelectorAll('[class*="DivItemContainer"]');
            return (title || videos.length > 0) ? 'LOADED' : 'NOT_FOUND';
        """)
        
        return 'LOADED' in check


def discover_search_selectors(safari_controller) -> Dict[str, str]:
    """
    Discover search interface selectors.
    Run with Safari on a search results page.
    """
    result = safari_controller.run_js("""
        var selectors = {};
        
        // Find elements with search-related data-e2e attributes
        var e2eElements = document.querySelectorAll('[data-e2e*="search"]');
        e2eElements.forEach(function(el) {
            var key = el.getAttribute('data-e2e');
            selectors[key] = {
                tag: el.tagName,
                text: el.innerText ? el.innerText.substring(0, 30) : ''
            };
        });
        
        return JSON.stringify(selectors, null, 2);
    """)
    
    print("Discovered Search Selectors:")
    print(result)
    return result
