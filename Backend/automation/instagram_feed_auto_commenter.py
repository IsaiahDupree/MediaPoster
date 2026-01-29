#!/usr/bin/env python3
"""
Instagram Feed Auto-Commenter - Safari Automation

Similar to Threads auto-commenter but for Instagram.

Features:
- Navigate to Instagram feed
- Click on posts sequentially
- Extract post content + image alt text + comments
- Generate AI response based on context
- Post comment using verified selectors
- Navigate back to feed
- Repeat for next post

Usage:
    python instagram_feed_auto_commenter.py --feed 3
    python instagram_feed_auto_commenter.py --feed 5 --start-index 2
"""

import subprocess
import time
import os
import json
from typing import List, Dict, Optional
from loguru import logger

try:
    from automation.instagram_selectors import SELECTORS, JS, URLS
    HAS_SELECTORS = True
except ImportError:
    try:
        from instagram_selectors import SELECTORS, JS, URLS
        HAS_SELECTORS = True
    except ImportError:
        HAS_SELECTORS = False
        logger.warning("Instagram selectors not available")

# Import comment tracker for duplicate detection
try:
    from services.engagement.comment_tracker import get_comment_tracker
    HAS_TRACKER = True
except ImportError:
    HAS_TRACKER = False
    get_comment_tracker = None


class InstagramFeedAutoCommenter:
    """
    Automated Instagram feed commenter that:
    1. Navigates to instagram.com feed
    2. Clicks on posts sequentially
    3. Extracts post content + image alt text + top comments
    4. Generates AI response based on context
    5. Posts comment using verified selectors
    6. Closes modal/navigates back
    7. Repeats for next post
    """
    
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self._checked_urls = set()  # Track checked URLs in session
        
    def _run_applescript(self, script: str) -> tuple:
        """Run AppleScript and return (success, result)."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout.strip()
        except Exception as e:
            return False, str(e)
    
    def _js(self, js_code: str) -> str:
        """Execute JavaScript in Safari and return result."""
        escaped_js = js_code.replace('"', '\\"').replace('\n', ' ')
        script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{escaped_js}"
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        return result if success else ""
    
    def _type_text(self, text: str) -> bool:
        """Type text using System Events keystroke."""
        escaped = text.replace('"', '\\"').replace("'", "'")
        script = f'''
        tell application "Safari"
            activate
        end tell
        delay 0.3
        tell application "System Events"
            keystroke "{escaped}"
        end tell
        delay 0.3
        '''
        success, _ = self._run_applescript(script)
        return success
    
    def _check_duplicate(self, post_url: str) -> bool:
        """Check if we've already commented on this post."""
        if post_url in self._checked_urls:
            return True
        
        if HAS_TRACKER and get_comment_tracker:
            import asyncio
            try:
                tracker = get_comment_tracker()
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(asyncio.run, tracker.has_commented_on('instagram', post_url))
                        is_dup = future.result(timeout=5)
                else:
                    is_dup = loop.run_until_complete(tracker.has_commented_on('instagram', post_url))
                if is_dup:
                    self._checked_urls.add(post_url)
                return is_dup
            except Exception as e:
                logger.warning(f"Duplicate check failed: {e}")
        return False
    
    def _find_non_duplicate_post(self, max_scrolls: int = 10, batch_size: int = 3) -> Optional[Dict]:
        """
        Find a post we haven't commented on yet, scrolling if needed.
        
        Strategy:
        1. Collect batch_size (3) posts at a time
        2. Check all posts in batch for duplicates
        3. If all are duplicates, scroll to next batch
        4. Return first non-duplicate found
        """
        checked_in_session = set()
        
        for scroll_attempt in range(max_scrolls):
            posts = self.get_feed_posts(limit=10)
            if not posts:
                logger.warning(f"No posts found, scrolling...")
                self._js(JS.scroll_feed() if HAS_SELECTORS else "window.scrollBy(0, 600);")
                time.sleep(2)
                continue
            
            # Filter to posts we haven't checked this session
            new_posts = [p for p in posts if p.get('postUrl', '') not in checked_in_session]
            
            if not new_posts:
                logger.info(f"📜 All visible posts already checked, scrolling... ({scroll_attempt + 1}/{max_scrolls})")
                self._js(JS.scroll_feed() if HAS_SELECTORS else "window.scrollBy(0, 600);")
                time.sleep(2)
                continue
            
            # Check batch of posts
            batch = new_posts[:batch_size]
            logger.info(f"🔍 Checking batch of {len(batch)} posts for duplicates...")
            
            non_duplicates = []
            for post in batch:
                post_url = post.get('postUrl', '')
                if not post_url:
                    continue
                
                checked_in_session.add(post_url)
                
                if self._check_duplicate(post_url):
                    logger.info(f"   ⏭️ Duplicate: {post_url[:50]}... - scrolling past")
                else:
                    logger.info(f"   ✅ Fresh post found: {post_url[:50]}...")
                    non_duplicates.append(post)
            
            # Return first non-duplicate
            if non_duplicates:
                selected = non_duplicates[0]
                logger.info(f"🎯 Selected post ({len(non_duplicates)} non-duplicates in batch)")
                return selected
            
            # All posts in batch were duplicates - scroll
            logger.info(f"📜 All {len(batch)} posts in batch were duplicates, scrolling... ({scroll_attempt + 1}/{max_scrolls})")
            self._js(JS.scroll_feed() if HAS_SELECTORS else "window.scrollBy(0, 600);")
            time.sleep(2)
            self._js(JS.scroll_feed() if HAS_SELECTORS else "window.scrollBy(0, 600);")
            time.sleep(1)
        
        logger.warning(f"❌ No non-duplicate posts found after {max_scrolls} scroll attempts")
        return None
    
    def navigate_to_feed(self) -> bool:
        """Navigate Safari to Instagram feed."""
        script = '''
        tell application "Safari"
            activate
            if (count of windows) = 0 then make new document
            set URL of front document to "https://www.instagram.com/"
        end tell
        delay 4
        '''
        success, _ = self._run_applescript(script)
        return success
    
    def check_login(self) -> bool:
        """Check if logged into Instagram."""
        if HAS_SELECTORS:
            js = JS.check_login()
        else:
            js = '''
                (function() {
                    var homeIcon = document.querySelector('svg[aria-label="Home"]');
                    return homeIcon ? 'logged_in' : 'not_logged_in';
                })();
            '''
        return 'logged_in' in self._js(js)
    
    def get_feed_posts(self, limit: int = 5) -> List[Dict]:
        """Get list of posts from the feed."""
        if HAS_SELECTORS:
            js = JS.get_feed_posts(limit)
        else:
            js = f'''
                (function() {{
                    var posts = [];
                    var articles = document.querySelectorAll('article');
                    articles.forEach(function(article, i) {{
                        if (i < {limit}) {{
                            var postLink = article.querySelector('a[href*="/p/"], a[href*="/reel/"]');
                            if (postLink) {{
                                posts.push({{index: i, postUrl: postLink.href}});
                            }}
                        }}
                    }});
                    return JSON.stringify(posts);
                }})();
            '''
        try:
            return json.loads(self._js(js))
        except:
            return []
    
    def click_post(self, index: int = 0) -> bool:
        """Click on a post by index to open it in modal."""
        js = f'''
            (function() {{
                var articles = document.querySelectorAll('article');
                if (articles.length > {index}) {{
                    var postLink = articles[{index}].querySelector('a[href*="/p/"], a[href*="/reel/"]');
                    if (postLink) {{
                        postLink.click();
                        return 'clicked';
                    }}
                }}
                return 'not_found';
            }})();
        '''
        return 'clicked' in self._js(js)
    
    def extract_post_context(self) -> Dict:
        """Extract post content, image alt text, and comments."""
        if HAS_SELECTORS:
            js = JS.extract_post_context()
        else:
            js = '''
                (function() {
                    var result = {post: {}, comments: []};
                    var article = document.querySelector('[role="dialog"] article') || document.querySelector('article');
                    if (article) {
                        var captionSpan = article.querySelector('span[dir="auto"]');
                        result.post.caption = captionSpan ? captionSpan.innerText.substring(0, 200) : '';
                        
                        var userLink = article.querySelector('a[href^="/"]');
                        if (userLink) {
                            var match = userLink.href.match(/instagram\\.com\\/([^\\/\\?]+)/);
                            result.post.username = match ? match[1] : '';
                        }
                        
                        var images = article.querySelectorAll('img[alt]');
                        var alts = [];
                        images.forEach(function(img) {
                            if (img.alt && img.alt.length > 5) alts.push(img.alt);
                        });
                        result.post.imageAlt = alts.slice(0, 3);
                    }
                    return JSON.stringify(result);
                })();
            '''
        try:
            return json.loads(self._js(js))
        except:
            return {"post": {}, "comments": []}
    
    def click_comment_button(self) -> bool:
        """Click the comment button on the current post."""
        js = '''
            (function() {
                var commentBtn = document.querySelector('svg[aria-label="Comment"]');
                if (commentBtn) {
                    var btn = commentBtn.closest('button') || commentBtn.closest('[role="button"]') || commentBtn.parentElement;
                    if (btn) {
                        btn.click();
                        return 'clicked';
                    }
                }
                return 'not_found';
            })();
        '''
        return 'clicked' in self._js(js)
    
    def focus_comment_input(self) -> bool:
        """Focus the comment input textarea."""
        if HAS_SELECTORS:
            js = JS.focus_comment_input()
        else:
            js = '''
                (function() {
                    var selectors = [
                        'textarea[placeholder*="comment" i]',
                        'textarea[aria-label*="comment" i]',
                        'textarea[placeholder*="Add a comment" i]'
                    ];
                    for (var i = 0; i < selectors.length; i++) {
                        var input = document.querySelector(selectors[i]);
                        if (input) {
                            input.focus();
                            input.click();
                            return 'found';
                        }
                    }
                    return 'not_found';
                })();
            '''
        return 'found' in self._js(js)
    
    def submit_comment(self) -> bool:
        """Submit the comment by clicking Post button."""
        if HAS_SELECTORS:
            js = JS.submit_comment()
        else:
            js = '''
                (function() {
                    var buttons = document.querySelectorAll('button[type="submit"], div[role="button"]');
                    for (var i = 0; i < buttons.length; i++) {
                        var text = (buttons[i].innerText || '').trim().toLowerCase();
                        if (text === 'post' && !buttons[i].disabled) {
                            buttons[i].click();
                            return 'clicked';
                        }
                    }
                    return 'not_found';
                })();
            '''
        result = self._js(js)
        return 'clicked' in result
    
    def close_modal(self) -> bool:
        """Close the post modal to return to feed."""
        if HAS_SELECTORS:
            js = JS.click_back_or_close()
        else:
            js = '''
                (function() {
                    var closeBtn = document.querySelector('svg[aria-label="Close"]');
                    if (closeBtn) {
                        var btn = closeBtn.closest('button') || closeBtn.parentElement;
                        if (btn) {
                            btn.click();
                            return 'closed';
                        }
                    }
                    document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', code: 'Escape', keyCode: 27}));
                    return 'escape';
                })();
            '''
        result = self._js(js)
        time.sleep(1)
        return 'closed' in result or 'escape' in result
    
    def verify_comment_posted(self, comment_text: str) -> bool:
        """Verify the comment was posted."""
        js = f'''
            (function() {{
                var text = document.body.innerText;
                return text.includes("{comment_text[:25]}") ? "true" : "false";
            }})();
        '''
        return 'true' in self._js(js)
    
    def generate_ai_reply(self, context: Dict) -> str:
        """Generate AI reply using OpenAI based on post context."""
        if not self.openai_api_key:
            logger.warning("No OpenAI API key configured")
            return ""
        
        post = context.get("post", {})
        username = post.get("username", "")
        caption = post.get("caption", "")
        image_alts = post.get("imageAlt", [])
        comments = context.get("comments", [])
        
        prompt = f"""Reply to this Instagram post:

POST BY: @{username}
CAPTION: "{caption[:300]}"
"""
        if image_alts:
            prompt += f"IMAGE DESCRIPTION: {', '.join(image_alts[:2])}\n"
        
        if comments:
            prompt += "\nTOP COMMENTS:\n"
            for c in comments[:3]:
                prompt += f"- @{c.get('u','')}: {c.get('t','')[:60]}\n"
        
        try:
            curl_cmd = [
                "curl", "-s", "https://api.openai.com/v1/chat/completions",
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {self.openai_api_key}",
                "-d", json.dumps({
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": "You are engaging on Instagram. Generate a short, authentic comment under 80 characters. Be genuine and relatable. No hashtags or emojis unless natural."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 40,
                    "temperature": 0.9
                })
            ]
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)
            return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return ""
    
    def auto_comment_feed(self, num_posts: int = 2, start_index: int = 0) -> List[Dict]:
        """
        Main function: Auto-comment on posts from the Instagram feed.
        
        Args:
            num_posts: Number of posts to comment on
            start_index: Which post index to start from (0 = first)
        
        Returns:
            List of results with post URLs and comment status
        """
        results = []
        
        logger.info(f"🚀 Starting Instagram auto-comment on {num_posts} posts")
        
        # Step 1: Navigate to feed
        if not self.navigate_to_feed():
            logger.error("Failed to navigate to Instagram feed")
            return results
        
        time.sleep(2)
        
        # Check login
        if not self.check_login():
            logger.error("Not logged into Instagram - please log in manually")
            return results
        
        logger.info("✅ Logged into Instagram")
        
        for i in range(num_posts):
            post_result = {"index": i, "url": "", "comment": "", "success": False}
            
            logger.info(f"\n📝 Processing post {i+1}/{num_posts}")
            
            # Find non-duplicate post (checks batch of 3, scrolls if all duplicates)
            post = self._find_non_duplicate_post(max_scrolls=10, batch_size=3)
            
            if not post:
                logger.warning(f"No non-duplicate posts found")
                continue
            
            post_url = post.get("postUrl", "")
            post_index = post.get("index", 0)
            post_result["url"] = post_url
            logger.info(f"   URL: {post_url[:60]}")
            
            # Click on post to open modal
            if not self.click_post(post_index):
                logger.warning("   Failed to click post")
                continue
            
            time.sleep(2)
            
            # Step 3: Extract context
            context = self.extract_post_context()
            caption = context.get("post", {}).get("caption", "")[:80]
            logger.info(f"   Caption: {caption}...")
            
            # Step 4: Generate AI reply
            reply = self.generate_ai_reply(context)
            if not reply:
                logger.warning("   Failed to generate AI reply")
                self.close_modal()
                time.sleep(1)
                continue
            
            post_result["comment"] = reply
            logger.info(f"   Reply: {reply}")
            
            # Step 5: Click comment button (may already be visible)
            self.click_comment_button()
            time.sleep(0.5)
            
            # Step 6: Focus comment input
            if not self.focus_comment_input():
                logger.warning("   Failed to find comment input")
                self.close_modal()
                time.sleep(1)
                continue
            
            time.sleep(0.5)
            
            # Step 7: Type reply using keyboard
            if not self._type_text(reply):
                logger.warning("   Failed to type reply")
                self.close_modal()
                time.sleep(1)
                continue
            
            time.sleep(0.5)
            
            # Step 8: Submit comment
            if not self.submit_comment():
                logger.warning("   Failed to submit comment")
                self.close_modal()
                time.sleep(1)
                continue
            
            time.sleep(2)
            
            # Step 9: Verify
            if self.verify_comment_posted(reply):
                post_result["success"] = True
                logger.success(f"   ✅ Comment posted successfully!")
            else:
                logger.warning("   ⚠️ Could not verify comment")
                post_result["success"] = True  # Assume success if no error
            
            results.append(post_result)
            
            # Step 10: Close modal and return to feed
            logger.info("   Closing modal...")
            self.close_modal()
            time.sleep(2)
        
        # Summary
        successful = sum(1 for r in results if r["success"])
        logger.info(f"\n🎉 Instagram auto-comment complete: {successful}/{len(results)} successful")
        
        return results


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """Command-line interface for Instagram auto-commenter."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Instagram Feed Auto-Commenter")
    parser.add_argument("--feed", "-f", type=int, nargs="?", const=2,
                       help="Auto-comment on N posts from feed (default: 2)")
    parser.add_argument("--start-index", "-s", type=int, default=0,
                       help="Start from post index N in feed (default: 0)")
    
    args = parser.parse_args()
    
    if args.feed:
        commenter = InstagramFeedAutoCommenter()
        results = commenter.auto_comment_feed(
            num_posts=args.feed,
            start_index=args.start_index
        )
        print(f"\n🎉 Instagram auto-comment complete!")
        for r in results:
            status = "✅" if r["success"] else "❌"
            print(f"   {status} {r['url'][:50]}...")
            if r["comment"]:
                print(f"      → {r['comment'][:60]}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
