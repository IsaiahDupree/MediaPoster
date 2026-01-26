"""
Engagement Scraper (PTK-004)
=============================
Safari automation to navigate to post URLs and scrape engagement metrics.

Supports:
- TikTok: views, likes, comments, shares, saves, favorites
- Instagram: likes, comments, views (for reels)
- X/Twitter: likes, retweets, replies, views
- Threads: likes, comments, reposts

Features:
- Navigate to post URL
- Extract metrics per platform
- Handle deleted/private posts
- Return structured data

Usage:
    scraper = EngagementScraper()
    metrics = await scraper.scrape_post_metrics(
        platform="tiktok",
        post_url="https://www.tiktok.com/@user/video/123"
    )
"""

import asyncio
import subprocess
import json
import re
from typing import Dict, Optional, Any
from loguru import logger
from datetime import datetime
from enum import Enum


class Platform(Enum):
    """Supported platforms"""
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    THREADS = "threads"


class PostStatus(Enum):
    """Post status"""
    ACTIVE = "active"
    DELETED = "deleted"
    PRIVATE = "private"
    NOT_FOUND = "not_found"
    ERROR = "error"


class EngagementScraper:
    """
    Scrapes engagement metrics from social media posts using Safari automation
    """

    def __init__(self):
        """Initialize engagement scraper"""
        self.safari_path = "/Applications/Safari.app"

        # Platform selectors (XPath/CSS patterns)
        self.selectors = {
            "tiktok": {
                "views": '[data-e2e="video-views"]',
                "likes": '[data-e2e="like-count"]',
                "comments": '[data-e2e="comment-count"]',
                "shares": '[data-e2e="share-count"]',
                "saves": '[data-e2e="undefined-count"]',  # TikTok uses "undefined" for favorites
            },
            "instagram": {
                "likes": 'section._ae2s._ae3v._ae3w button span',
                "comments": 'a[href*="/comments/"]',
                "views": 'span._ac2a',  # For reels
            },
            "twitter": {
                "likes": '[data-testid="like"]',
                "retweets": '[data-testid="retweet"]',
                "replies": '[data-testid="reply"]',
                "views": 'a[href*="/analytics"]',
            },
            "threads": {
                "likes": '[aria-label*="Like"]',
                "comments": '[aria-label*="Reply"]',
                "reposts": '[aria-label*="Repost"]',
            }
        }

    def _run_applescript(self, script: str, timeout: int = 30) -> str:
        """Execute AppleScript and return output"""
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
            if "not allowed assistive access" in e.stderr.lower() or "not allowed automation" in e.stderr.lower():
                logger.error("⚠️  Safari automation requires permissions!")
                logger.info("Go to: System Settings > Privacy & Security > Automation")
                logger.info("Enable Terminal/iTerm to control Safari")
            raise
        except subprocess.TimeoutExpired:
            logger.warning(f"AppleScript timeout after {timeout}s")
            raise

    async def _open_url_in_safari(self, url: str) -> bool:
        """
        Open URL in Safari

        Returns:
            True if successful, False otherwise
        """
        try:
            script = f'''
            tell application "Safari"
                activate
                open location "{url}"
                delay 3
                return "success"
            end tell
            '''

            result = self._run_applescript(script, timeout=10)
            return "success" in result.lower()
        except Exception as e:
            logger.error(f"Error opening URL in Safari: {e}")
            return False

    async def _extract_tiktok_metrics(self) -> Dict[str, Any]:
        """
        Extract TikTok metrics using JavaScript injection

        Returns:
            Dictionary with views, likes, comments, shares, saves
        """
        js_code = """
        (function() {
            // Check if post exists
            var videoPlayer = document.querySelector('[data-e2e="video-player"]');
            if (!videoPlayer) {
                return {status: 'not_found', error: 'Video player not found'};
            }

            // Check if deleted/private
            var errorMsg = document.querySelector('[data-e2e="video-error"]');
            if (errorMsg) {
                return {status: 'deleted', error: 'Video unavailable'};
            }

            // Extract metrics
            function extractNumber(selector) {
                var elem = document.querySelector(selector);
                if (!elem) return 0;
                var text = elem.textContent.trim();

                // Handle K, M, B suffixes
                if (text.includes('K')) {
                    return parseFloat(text.replace('K', '')) * 1000;
                } else if (text.includes('M')) {
                    return parseFloat(text.replace('M', '')) * 1000000;
                } else if (text.includes('B')) {
                    return parseFloat(text.replace('B', '')) * 1000000000;
                }

                return parseInt(text.replace(/,/g, '')) || 0;
            }

            return {
                status: 'active',
                views: extractNumber('[data-e2e="video-views"]'),
                likes: extractNumber('[data-e2e="like-count"]'),
                comments: extractNumber('[data-e2e="comment-count"]'),
                shares: extractNumber('[data-e2e="share-count"]'),
                saves: extractNumber('[data-e2e="undefined-count"]'),
                timestamp: new Date().toISOString()
            };
        })();
        """

        # Inject JavaScript into Safari
        script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{js_code.replace('"', '\\"').replace(chr(10), ' ')}"
            end tell
        end tell
        '''

        try:
            result = self._run_applescript(script, timeout=15)

            # Parse JSON result
            metrics = json.loads(result) if result else {"status": "error"}
            return metrics
        except Exception as e:
            logger.error(f"Error extracting TikTok metrics: {e}")
            return {"status": "error", "error": str(e)}

    async def _extract_instagram_metrics(self) -> Dict[str, Any]:
        """
        Extract Instagram metrics using JavaScript injection

        Returns:
            Dictionary with likes, comments, views (for reels)
        """
        js_code = """
        (function() {
            // Check if post exists
            var article = document.querySelector('article[role="presentation"]');
            if (!article) {
                return {status: 'not_found', error: 'Post not found'};
            }

            // Check if private/deleted
            var errorMsg = document.querySelector('[data-testid="error"]');
            if (errorMsg || document.body.textContent.includes('Page Not Found')) {
                return {status: 'deleted', error: 'Post unavailable'};
            }

            // Extract metrics
            function extractNumber(selector) {
                var elem = document.querySelector(selector);
                if (!elem) return 0;
                var text = elem.textContent.trim();

                // Remove commas and parse
                return parseInt(text.replace(/[^0-9]/g, '')) || 0;
            }

            // Get likes
            var likesButton = document.querySelector('section._ae2s._ae3v._ae3w button span');
            var likes = likesButton ? extractNumber('section._ae2s._ae3v._ae3w button span') : 0;

            // Get comments
            var commentsLink = document.querySelector('a[href*="/comments/"]');
            var comments = commentsLink ? extractNumber('a[href*="/comments/"]') : 0;

            // Get views (for Reels)
            var viewsSpan = document.querySelector('span._ac2a');
            var views = viewsSpan ? extractNumber('span._ac2a') : 0;

            return {
                status: 'active',
                likes: likes,
                comments: comments,
                views: views,
                timestamp: new Date().toISOString()
            };
        })();
        """

        script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{js_code.replace('"', '\\"').replace(chr(10), ' ')}"
            end tell
        end tell
        '''

        try:
            result = self._run_applescript(script, timeout=15)
            metrics = json.loads(result) if result else {"status": "error"}
            return metrics
        except Exception as e:
            logger.error(f"Error extracting Instagram metrics: {e}")
            return {"status": "error", "error": str(e)}

    async def _extract_twitter_metrics(self) -> Dict[str, Any]:
        """
        Extract X/Twitter metrics using JavaScript injection

        Returns:
            Dictionary with likes, retweets, replies, views
        """
        js_code = """
        (function() {
            // Check if tweet exists
            var article = document.querySelector('article[data-testid="tweet"]');
            if (!article) {
                return {status: 'not_found', error: 'Tweet not found'};
            }

            // Check if deleted/suspended
            if (document.body.textContent.includes('This Post is from a suspended account')) {
                return {status: 'deleted', error: 'Account suspended'};
            }

            function extractMetric(testId) {
                var button = document.querySelector(`[data-testid="${testId}"]`);
                if (!button) return 0;
                var span = button.querySelector('span[data-testid="app-text-transition-container"]');
                if (!span) return 0;
                var text = span.textContent.trim();

                // Handle K, M, B
                if (text.includes('K')) return parseFloat(text.replace('K', '')) * 1000;
                if (text.includes('M')) return parseFloat(text.replace('M', '')) * 1000000;
                if (text.includes('B')) return parseFloat(text.replace('B', '')) * 1000000000;

                return parseInt(text.replace(/,/g, '')) || 0;
            }

            return {
                status: 'active',
                likes: extractMetric('like'),
                retweets: extractMetric('retweet'),
                replies: extractMetric('reply'),
                views: 0,  // Views not always visible
                timestamp: new Date().toISOString()
            };
        })();
        """

        script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{js_code.replace('"', '\\"').replace(chr(10), ' ')}"
            end tell
        end tell
        '''

        try:
            result = self._run_applescript(script, timeout=15)
            metrics = json.loads(result) if result else {"status": "error"}
            return metrics
        except Exception as e:
            logger.error(f"Error extracting Twitter metrics: {e}")
            return {"status": "error", "error": str(e)}

    async def _extract_threads_metrics(self) -> Dict[str, Any]:
        """
        Extract Threads metrics using JavaScript injection

        Returns:
            Dictionary with likes, comments, reposts
        """
        js_code = """
        (function() {
            // Check if post exists
            var main = document.querySelector('main[role="main"]');
            if (!main) {
                return {status: 'not_found', error: 'Post not found'};
            }

            // Extract metrics from aria-labels
            function extractFromAriaLabel(pattern) {
                var buttons = document.querySelectorAll('button[aria-label], div[aria-label]');
                for (var btn of buttons) {
                    var label = btn.getAttribute('aria-label');
                    if (label && label.includes(pattern)) {
                        var match = label.match(/\\d+/);
                        return match ? parseInt(match[0]) : 0;
                    }
                }
                return 0;
            }

            return {
                status: 'active',
                likes: extractFromAriaLabel('Like'),
                comments: extractFromAriaLabel('Reply'),
                reposts: extractFromAriaLabel('Repost'),
                timestamp: new Date().toISOString()
            };
        })();
        """

        script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{js_code.replace('"', '\\"').replace(chr(10), ' ')}"
            end tell
        end tell
        '''

        try:
            result = self._run_applescript(script, timeout=15)
            metrics = json.loads(result) if result else {"status": "error"}
            return metrics
        except Exception as e:
            logger.error(f"Error extracting Threads metrics: {e}")
            return {"status": "error", "error": str(e)}

    async def scrape_post_metrics(
        self,
        platform: str,
        post_url: str,
        retry_count: int = 2
    ) -> Dict[str, Any]:
        """
        Scrape engagement metrics from a post URL

        Args:
            platform: Platform name (tiktok, instagram, twitter, threads)
            post_url: URL of the post
            retry_count: Number of retries on failure

        Returns:
            Dictionary with metrics and status:
            {
                "success": bool,
                "status": str,  # active, deleted, private, not_found, error
                "platform": str,
                "post_url": str,
                "metrics": {...},
                "scraped_at": str,
                "error": str (optional)
            }
        """
        try:
            platform = platform.lower()

            # Validate platform
            if platform not in [p.value for p in Platform]:
                return {
                    "success": False,
                    "status": "error",
                    "platform": platform,
                    "post_url": post_url,
                    "error": f"Unsupported platform: {platform}",
                    "scraped_at": datetime.now().isoformat()
                }

            logger.info(f"🔍 Scraping {platform} metrics from: {post_url}")

            # Open URL in Safari
            opened = await self._open_url_in_safari(post_url)
            if not opened:
                return {
                    "success": False,
                    "status": "error",
                    "platform": platform,
                    "post_url": post_url,
                    "error": "Failed to open URL in Safari",
                    "scraped_at": datetime.now().isoformat()
                }

            # Wait for page to load
            await asyncio.sleep(3)

            # Extract metrics based on platform
            metrics = {}
            if platform == Platform.TIKTOK.value:
                metrics = await self._extract_tiktok_metrics()
            elif platform == Platform.INSTAGRAM.value:
                metrics = await self._extract_instagram_metrics()
            elif platform == Platform.TWITTER.value:
                metrics = await self._extract_twitter_metrics()
            elif platform == Platform.THREADS.value:
                metrics = await self._extract_threads_metrics()

            # Handle status
            status = metrics.get("status", "error")
            success = status == "active"

            result = {
                "success": success,
                "status": status,
                "platform": platform,
                "post_url": post_url,
                "metrics": {k: v for k, v in metrics.items() if k not in ["status", "error", "timestamp"]},
                "scraped_at": datetime.now().isoformat()
            }

            if "error" in metrics:
                result["error"] = metrics["error"]

            if success:
                logger.success(f"✅ Scraped {platform} metrics: {result['metrics']}")
            else:
                logger.warning(f"⚠️  Post status: {status}")

            return result

        except Exception as e:
            logger.error(f"Error scraping metrics: {e}")

            # Retry on error
            if retry_count > 0:
                logger.info(f"Retrying... ({retry_count} attempts left)")
                await asyncio.sleep(2)
                return await self.scrape_post_metrics(platform, post_url, retry_count - 1)

            return {
                "success": False,
                "status": "error",
                "platform": platform,
                "post_url": post_url,
                "error": str(e),
                "scraped_at": datetime.now().isoformat()
            }


# Singleton accessor
_scraper_instance: Optional[EngagementScraper] = None

def get_engagement_scraper() -> EngagementScraper:
    """Get the singleton engagement scraper instance"""
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = EngagementScraper()
    return _scraper_instance


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python engagement_scraper.py <platform> <post_url>")
        print("Example: python engagement_scraper.py tiktok https://www.tiktok.com/@user/video/123")
        sys.exit(1)

    platform = sys.argv[1]
    post_url = sys.argv[2]

    scraper = EngagementScraper()
    result = asyncio.run(scraper.scrape_post_metrics(platform, post_url))

    print("\n" + "="*60)
    print(f"Platform: {result['platform']}")
    print(f"Status: {result['status']}")
    print(f"Success: {result['success']}")
    print(f"URL: {result['post_url']}")
    print("\nMetrics:")
    for key, value in result.get('metrics', {}).items():
        print(f"  {key}: {value:,}")
    if 'error' in result:
        print(f"\nError: {result['error']}")
    print("="*60)
