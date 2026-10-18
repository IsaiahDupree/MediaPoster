"""
Instagram Profile Scraper with Safari Automation
================================================
Scrolls through an Instagram profile and extracts all post data
using Safari AppleScript automation.
"""

import os
import json
import asyncio
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from loguru import logger


@dataclass
class InstagramPost:
    """Represents an Instagram post"""
    post_id: str
    shortcode: str
    url: str
    caption: str = ""
    likes: int = 0
    comments: int = 0
    timestamp: str = ""
    media_type: str = "image"  # image, video, carousel
    thumbnail_url: str = ""
    video_url: str = ""
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)


@dataclass
class InstagramProfile:
    """Represents an Instagram profile with all scraped data"""
    username: str
    full_name: str = ""
    bio: str = ""
    followers: int = 0
    following: int = 0
    post_count: int = 0
    is_verified: bool = False
    profile_pic_url: str = ""
    posts: List[InstagramPost] = field(default_factory=list)
    scraped_at: str = ""


class SafariInstagramScraper:
    """
    Scrapes Instagram profiles using Safari automation.
    Uses AppleScript to control Safari and extract data.
    """
    
    def __init__(self, output_dir: str = "/tmp/instagram_scrapes"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _run_applescript(self, script: str) -> str:
        """Execute AppleScript and return result"""
        cmd = ["osascript", "-e", script]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        logger.error(f"AppleScript error: {result.stderr}")
        return ""
    
    def _run_javascript_in_safari(self, js_code: str) -> str:
        """Run JavaScript in Safari and return result"""
        # Escape quotes for AppleScript
        js_escaped = js_code.replace('\\', '\\\\').replace('"', '\\"')
        
        script = f'''
        tell application "Safari"
            tell front document
                set jsResult to do JavaScript "{js_escaped}"
                return jsResult
            end tell
        end tell
        '''
        
        return self._run_applescript(script)
    
    def open_profile(self, username: str) -> bool:
        """Open Instagram profile in Safari"""
        url = f"https://www.instagram.com/{username}/"
        
        script = f'''
        tell application "Safari"
            activate
            if (count of windows) = 0 then
                make new document
            end if
            set URL of front document to "{url}"
        end tell
        '''
        
        self._run_applescript(script)
        time.sleep(3)  # Wait for page to load
        
        logger.info(f"Opened Instagram profile: @{username}")
        return True
    
    def scroll_page(self, scroll_count: int = 10, delay: float = 2.0) -> None:
        """Scroll the page to load more posts"""
        
        for i in range(scroll_count):
            js_code = "window.scrollBy(0, window.innerHeight * 2); 'scrolled';"
            self._run_javascript_in_safari(js_code)
            logger.info(f"Scroll {i+1}/{scroll_count}")
            time.sleep(delay)  # Wait for content to load
    
    def extract_profile_info(self) -> Dict[str, Any]:
        """Extract profile header information"""
        
        js_code = '''
        (function() {
            try {
                var result = {};
                
                // Get username from URL
                result.username = window.location.pathname.replace(/\\//g, '');
                
                // Get profile header info
                var header = document.querySelector('header');
                if (header) {
                    // Full name
                    var nameEl = header.querySelector('span[class*="x1lliihq"]');
                    result.full_name = nameEl ? nameEl.textContent : '';
                    
                    // Bio
                    var bioEl = header.querySelector('h1');
                    result.bio = bioEl ? bioEl.textContent : '';
                    
                    // Stats (posts, followers, following)
                    var stats = header.querySelectorAll('li span span');
                    if (stats.length >= 3) {
                        result.post_count = stats[0] ? stats[0].textContent : '0';
                        result.followers = stats[1] ? stats[1].textContent : '0';
                        result.following = stats[2] ? stats[2].textContent : '0';
                    }
                    
                    // Profile pic
                    var picEl = header.querySelector('img');
                    result.profile_pic_url = picEl ? picEl.src : '';
                    
                    // Verified badge
                    result.is_verified = !!header.querySelector('svg[aria-label="Verified"]');
                }
                
                return JSON.stringify(result);
            } catch(e) {
                return JSON.stringify({error: e.message});
            }
        })();
        '''
        
        result = self._run_javascript_in_safari(js_code)
        try:
            return json.loads(result) if result else {}
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse profile info: {result}")
            return {}
    
    def extract_posts(self) -> List[Dict[str, Any]]:
        """Extract all visible posts from the page"""
        
        js_code = '''
        (function() {
            try {
                var posts = [];
                var postLinks = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
                
                postLinks.forEach(function(link) {
                    var href = link.getAttribute('href');
                    var shortcode = href.split('/')[2];
                    
                    // Get the post container
                    var container = link.closest('div[class*="_aagw"]') || link.parentElement;
                    
                    // Get thumbnail
                    var img = link.querySelector('img');
                    var thumbnail = img ? img.src : '';
                    
                    // Determine if video
                    var isVideo = href.includes('/reel/') || !!link.querySelector('svg[aria-label*="Video"]');
                    
                    // Avoid duplicates
                    if (!posts.find(p => p.shortcode === shortcode)) {
                        posts.push({
                            shortcode: shortcode,
                            url: 'https://www.instagram.com' + href,
                            thumbnail_url: thumbnail,
                            media_type: isVideo ? 'video' : 'image'
                        });
                    }
                });
                
                return JSON.stringify(posts);
            } catch(e) {
                return JSON.stringify([]);
            }
        })();
        '''
        
        result = self._run_javascript_in_safari(js_code)
        try:
            return json.loads(result) if result else []
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse posts: {result}")
            return []
    
    def get_post_details(self, shortcode: str) -> Dict[str, Any]:
        """Get detailed info for a specific post by navigating to it"""
        
        url = f"https://www.instagram.com/p/{shortcode}/"
        
        # Navigate to post
        script = f'''
        tell application "Safari"
            set URL of front document to "{url}"
        end tell
        '''
        self._run_applescript(script)
        time.sleep(2)
        
        # Extract post details
        js_code = '''
        (function() {
            try {
                var result = {};
                
                // Caption
                var captionEl = document.querySelector('h1') || 
                               document.querySelector('span[class*="_ap3a"]') ||
                               document.querySelector('div[class*="C4VMK"] span');
                result.caption = captionEl ? captionEl.textContent : '';
                
                // Likes
                var likesEl = document.querySelector('section span span') ||
                             document.querySelector('button[class*="like"] span');
                result.likes = likesEl ? likesEl.textContent : '0';
                
                // Comments count
                var commentsEl = document.querySelectorAll('ul[class*="XQXOT"] li');
                result.comments = commentsEl ? commentsEl.length : 0;
                
                // Timestamp
                var timeEl = document.querySelector('time');
                result.timestamp = timeEl ? timeEl.getAttribute('datetime') : '';
                
                // Video URL for reels
                var videoEl = document.querySelector('video');
                result.video_url = videoEl ? videoEl.src : '';
                
                // Extract hashtags
                var hashtagEls = document.querySelectorAll('a[href*="/explore/tags/"]');
                result.hashtags = Array.from(hashtagEls).map(a => a.textContent);
                
                // Extract mentions
                var mentionEls = document.querySelectorAll('a[href^="/"]:not([href*="/explore/"])');
                result.mentions = Array.from(mentionEls)
                    .filter(a => a.textContent.startsWith('@'))
                    .map(a => a.textContent);
                
                return JSON.stringify(result);
            } catch(e) {
                return JSON.stringify({error: e.message});
            }
        })();
        '''
        
        result = self._run_javascript_in_safari(js_code)
        try:
            return json.loads(result) if result else {}
        except json.JSONDecodeError:
            return {}
    
    async def scrape_profile(
        self,
        username: str,
        scroll_count: int = 10,
        get_post_details: bool = False
    ) -> InstagramProfile:
        """
        Full profile scrape workflow.
        
        Args:
            username: Instagram username to scrape
            scroll_count: Number of times to scroll for more posts
            get_post_details: Whether to visit each post for full details
        """
        
        logger.info(f"Starting scrape of @{username}")
        
        # Open profile
        self.open_profile(username)
        time.sleep(3)
        
        # Get profile info
        profile_info = self.extract_profile_info()
        logger.info(f"Profile info: {profile_info}")
        
        # Scroll to load posts
        logger.info(f"Scrolling {scroll_count} times to load posts...")
        self.scroll_page(scroll_count)
        
        # Extract posts
        posts_data = self.extract_posts()
        logger.info(f"Found {len(posts_data)} posts")
        
        # Optionally get detailed info for each post
        posts = []
        if get_post_details and posts_data:
            for i, post_data in enumerate(posts_data[:20]):  # Limit to first 20
                logger.info(f"Getting details for post {i+1}/{min(len(posts_data), 20)}")
                details = self.get_post_details(post_data['shortcode'])
                
                posts.append(InstagramPost(
                    post_id=post_data['shortcode'],
                    shortcode=post_data['shortcode'],
                    url=post_data['url'],
                    caption=details.get('caption', ''),
                    likes=self._parse_count(details.get('likes', '0')),
                    comments=details.get('comments', 0),
                    timestamp=details.get('timestamp', ''),
                    media_type=post_data.get('media_type', 'image'),
                    thumbnail_url=post_data.get('thumbnail_url', ''),
                    video_url=details.get('video_url', ''),
                    hashtags=details.get('hashtags', []),
                    mentions=details.get('mentions', [])
                ))
                
                time.sleep(1)  # Rate limiting
        else:
            # Basic post info only
            for post_data in posts_data:
                posts.append(InstagramPost(
                    post_id=post_data['shortcode'],
                    shortcode=post_data['shortcode'],
                    url=post_data['url'],
                    media_type=post_data.get('media_type', 'image'),
                    thumbnail_url=post_data.get('thumbnail_url', '')
                ))
        
        # Create profile object
        profile = InstagramProfile(
            username=username,
            full_name=profile_info.get('full_name', ''),
            bio=profile_info.get('bio', ''),
            followers=self._parse_count(profile_info.get('followers', '0')),
            following=self._parse_count(profile_info.get('following', '0')),
            post_count=self._parse_count(profile_info.get('post_count', '0')),
            is_verified=profile_info.get('is_verified', False),
            profile_pic_url=profile_info.get('profile_pic_url', ''),
            posts=posts,
            scraped_at=datetime.now().isoformat()
        )
        
        # Save to file
        output_file = self.output_dir / f"{username}_profile.json"
        with open(output_file, 'w') as f:
            json.dump(asdict(profile), f, indent=2)
        
        logger.success(f"Saved profile data to {output_file}")
        
        return profile
    
    def _parse_count(self, count_str: str) -> int:
        """Parse count strings like '1.2K', '500', '1M' to integers"""
        if not count_str:
            return 0
        
        count_str = count_str.strip().replace(',', '')
        
        try:
            if 'K' in count_str.upper():
                return int(float(count_str.upper().replace('K', '')) * 1000)
            elif 'M' in count_str.upper():
                return int(float(count_str.upper().replace('M', '')) * 1000000)
            else:
                return int(count_str)
        except ValueError:
            return 0


async def main():
    """Scrape personalbrandlaunch profile"""
    
    print("\n" + "="*60)
    print("Instagram Profile Scraper - Safari Automation")
    print("="*60 + "\n")
    
    scraper = SafariInstagramScraper()
    
    profile = await scraper.scrape_profile(
        username="personalbrandlaunch",
        scroll_count=8,  # Scroll 8 times to load posts
        get_post_details=True  # Get full details for each post
    )
    
    print(f"\n✅ Scraped @{profile.username}")
    print(f"📊 Followers: {profile.followers:,}")
    print(f"📝 Posts found: {len(profile.posts)}")
    print(f"💾 Saved to: /tmp/instagram_scrapes/{profile.username}_profile.json")
    
    return profile


if __name__ == "__main__":
    asyncio.run(main())
