#!/usr/bin/env python3
"""
Auto-Comment Runner - Reproducible script for automated commenting on Threads/Instagram.

Features:
- Safari state management (login check, page load verification)
- Duplicate prevention with persistent cache
- Real AI comment generation via OpenAI
- Verifiable results with JSON output
- Structured logging

Usage:
    python scripts/auto_comment_runner.py --platform threads --posts 5
    python scripts/auto_comment_runner.py --platform instagram --posts 5
    python scripts/auto_comment_runner.py --platform both --posts 5
"""

import subprocess
import time
import os
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from enum import Enum


class Platform(str, Enum):
    THREADS = "threads"
    INSTAGRAM = "instagram"


@dataclass
class CommentResult:
    """Result of a single comment attempt."""
    platform: str
    post_index: int
    post_url: str
    post_id: str
    username: str
    context: str
    ai_comment: str
    status: str  # pending, posted, failed, skipped
    error: str = ""
    timestamp: str = ""
    verified: bool = False


@dataclass 
class RunResult:
    """Result of an auto-comment run."""
    run_id: str
    platform: str
    started_at: str
    completed_at: str
    total_posts: int
    posted: int
    failed: int
    skipped: int
    comments: List[Dict]
    safari_state: Dict


class SafariController:
    """Manages Safari browser state and automation."""
    
    def __init__(self):
        self.current_url = ""
        self.is_ready = False
    
    def run_applescript(self, script: str, timeout: int = 30) -> tuple:
        """Run AppleScript and return (success, result)."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "timeout"
        except Exception as e:
            return False, str(e)
    
    def js(self, code: str) -> str:
        """Execute JavaScript in Safari and return result."""
        # Write JS to temp file to avoid escaping issues
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            js_file = f.name
        
        script = f'''
        tell application "Safari"
            tell front document
                set jsCode to read POSIX file "{js_file}"
                do JavaScript jsCode
            end tell
        end tell
        '''
        success, result = self.run_applescript(script)
        
        # Clean up
        try:
            os.unlink(js_file)
        except:
            pass
        
        return result if success else ""
    
    def get_current_url(self) -> str:
        """Get current Safari URL."""
        script = '''
        tell application "Safari"
            tell front document
                return URL
            end tell
        end tell
        '''
        success, url = self.run_applescript(script)
        self.current_url = url if success else ""
        return self.current_url
    
    def navigate(self, url: str, wait_seconds: int = 4) -> bool:
        """Navigate Safari to URL and wait for load."""
        script = f'''
        tell application "Safari"
            activate
            set URL of front document to "{url}"
        end tell
        '''
        success, _ = self.run_applescript(script)
        if success:
            time.sleep(wait_seconds)
            self.current_url = url
        return success
    
    def check_safari_ready(self) -> Dict:
        """Check Safari state and readiness."""
        state = {
            "safari_running": False,
            "has_window": False,
            "current_url": "",
            "page_loaded": False,
            "error": ""
        }
        
        # Check if Safari is running
        script = '''
        tell application "System Events"
            return (name of processes) contains "Safari"
        end tell
        '''
        success, result = self.run_applescript(script)
        state["safari_running"] = success and result == "true"
        
        if not state["safari_running"]:
            state["error"] = "Safari not running"
            return state
        
        # Check for window
        script = '''
        tell application "Safari"
            return count of windows
        end tell
        '''
        success, result = self.run_applescript(script)
        try:
            state["has_window"] = success and int(result) > 0
        except:
            state["has_window"] = False
        
        if not state["has_window"]:
            state["error"] = "No Safari window"
            return state
        
        # Get current URL
        state["current_url"] = self.get_current_url()
        
        # Check if page is loaded (has body)
        body_check = self.js("document.body ? 'loaded' : 'loading'")
        state["page_loaded"] = body_check == "loaded"
        
        self.is_ready = state["page_loaded"]
        return state
    
    def check_login(self, platform: Platform) -> Dict:
        """Check if user is logged in to platform."""
        result = {"logged_in": False, "username": "", "error": ""}
        
        if platform == Platform.THREADS:
            # Check for profile link or login button
            check = self.js('''
                (function() {
                    var profile = document.querySelector('a[href*="/@"]');
                    var login = document.querySelector('div[role="button"]');
                    if (profile) {
                        var href = profile.getAttribute('href');
                        var match = href.match(/@([^/]+)/);
                        return JSON.stringify({logged_in: true, username: match ? match[1] : ''});
                    }
                    return JSON.stringify({logged_in: false, username: ''});
                })();
            ''')
            try:
                data = json.loads(check) if check else {}
                result["logged_in"] = data.get("logged_in", False)
                result["username"] = data.get("username", "")
            except:
                result["error"] = "Could not parse login check"
                
        elif platform == Platform.INSTAGRAM:
            # Check for profile picture or login form
            check = self.js('''
                (function() {
                    var avatar = document.querySelector('img[alt*="profile"]') || 
                                 document.querySelector('span[role="link"] img');
                    var loginForm = document.querySelector('input[name="username"]');
                    if (avatar && !loginForm) {
                        return JSON.stringify({logged_in: true});
                    }
                    return JSON.stringify({logged_in: false});
                })();
            ''')
            try:
                data = json.loads(check) if check else {}
                result["logged_in"] = data.get("logged_in", False)
            except:
                result["error"] = "Could not parse login check"
        
        return result
    
    def wait_for_feed(self, platform: Platform, max_wait: int = 15) -> bool:
        """Wait for feed to load with posts."""
        if platform == Platform.THREADS:
            selector = 'a[href*="/post/"]'
        else:
            selector = 'a[href*="/p/"], a[href*="/reel/"]'
        
        for attempt in range(max_wait):
            # Scroll to trigger lazy load
            if attempt > 2:
                self.js("window.scrollTo(0, 500);")
            
            count = self.js(f"document.querySelectorAll('{selector}').length")
            try:
                if int(count) > 0:
                    return True
            except:
                pass
            
            # Also check for any links as fallback
            if attempt > 5:
                any_links = self.js("document.querySelectorAll('a[href]').length")
                try:
                    if int(any_links) > 20:  # Page has loaded something
                        # Try scrolling more
                        self.js("window.scrollTo(0, 800);")
                        time.sleep(1)
                        count = self.js(f"document.querySelectorAll('{selector}').length")
                        if int(count) > 0:
                            return True
                except:
                    pass
            
            time.sleep(1)
        return False
    
    def type_text(self, text: str) -> bool:
        """Type text using System Events."""
        safe = text.replace('"', '').replace("'", "").replace('\\', '')[:80]
        script = f'''
        tell application "Safari" to activate
        delay 0.3
        tell application "System Events"
            keystroke "{safe}"
        end tell
        '''
        success, _ = self.run_applescript(script)
        return success


class AICommentGenerator:
    """Generates comments using OpenAI API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gpt-4o"
    
    def generate(self, context: str, platform: str) -> Dict:
        """Generate a comment for the given context."""
        result = {"comment": "", "error": "", "tokens": 0}
        
        try:
            data = json.dumps({
                'model': self.model,
                'messages': [
                    {
                        'role': 'system', 
                        'content': f'Generate a short, authentic {platform} comment (under 50 chars). Be genuine and conversational. No hashtags, no emojis, no quotes.'
                    },
                    {'role': 'user', 'content': f'Comment on this post: {context}'}
                ],
                'max_tokens': 30,
                'temperature': 0.9
            }).encode('utf-8')
            
            req = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions',
                data=data,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
            )
            
            with urllib.request.urlopen(req, timeout=15) as resp:
                response = json.loads(resp.read().decode('utf-8'))
                comment = response['choices'][0]['message']['content'].strip()
                # Clean up the comment
                comment = comment.strip('"').strip("'")
                result["comment"] = comment[:80]
                result["tokens"] = response.get('usage', {}).get('total_tokens', 0)
                
        except Exception as e:
            result["error"] = str(e)
        
        return result


class AutoCommentRunner:
    """Main runner for auto-commenting."""
    
    def __init__(self, output_dir: str = None):
        self.safari = SafariController()
        self.output_dir = Path(output_dir or "Backend/logs/auto_comments")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            env_file = Path("Backend/.env")
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("OPENAI_API_KEY="):
                        self.api_key = line.split("=", 1)[1].strip()
                        break
        
        self.ai = AICommentGenerator(self.api_key) if self.api_key else None
        
        # Dedup cache
        self.commented_ids: set = set()
        self._load_commented_cache()
    
    def _load_commented_cache(self):
        """Load previously commented post IDs from cache file."""
        cache_file = self.output_dir / "commented_cache.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                self.commented_ids = set(data.get("post_ids", []))
                print(f"📋 Loaded {len(self.commented_ids)} previously commented posts")
            except:
                pass
    
    def _save_commented_cache(self):
        """Save commented post IDs to cache file."""
        cache_file = self.output_dir / "commented_cache.json"
        cache_file.write_text(json.dumps({
            "post_ids": list(self.commented_ids),
            "updated_at": datetime.now().isoformat()
        }, indent=2))
    
    def _get_feed_posts(self, platform: Platform) -> List[Dict]:
        """Get posts from current feed."""
        if platform == Platform.THREADS:
            js_code = '''
                (function() {
                    var links = document.querySelectorAll('a[href*="/post/"]');
                    var posts = [];
                    var seen = {};
                    for (var i = 0; i < links.length && posts.length < 10; i++) {
                        var href = links[i].href;
                        if (!seen[href]) {
                            seen[href] = true;
                            var id = href.split('/post/')[1];
                            if (id) id = id.split('/')[0].split('?')[0];
                            posts.push({url: href, id: id || ''});
                        }
                    }
                    return JSON.stringify(posts);
                })();
            '''
        else:
            js_code = '''
                (function() {
                    var links = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
                    var posts = [];
                    var seen = {};
                    for (var i = 0; i < links.length && posts.length < 10; i++) {
                        var href = links[i].href;
                        if (!seen[href]) {
                            seen[href] = true;
                            var id = href.includes('/p/') ? href.split('/p/')[1] : href.split('/reel/')[1];
                            if (id) id = id.split('/')[0].split('?')[0];
                            posts.push({url: href, id: id || ''});
                        }
                    }
                    return JSON.stringify(posts);
                })();
            '''
        
        result = self.safari.js(js_code)
        try:
            return json.loads(result) if result else []
        except:
            return []
    
    def _extract_context(self, platform: Platform) -> Dict:
        """Extract post context (username, caption)."""
        if platform == Platform.THREADS:
            js_code = '''
                (function() {
                    var container = document.querySelector('[data-pressable-container="true"]');
                    if (!container) return JSON.stringify({});
                    
                    var userLink = container.querySelector('a[href*="/@"]');
                    var username = '';
                    if (userLink) {
                        var match = userLink.href.match(/@([^/]+)/);
                        username = match ? match[1] : '';
                    }
                    
                    var textEl = container.querySelector('[dir="auto"] span');
                    var caption = textEl ? textEl.innerText.substring(0, 150) : '';
                    
                    return JSON.stringify({username: username, caption: caption});
                })();
            '''
        else:
            js_code = '''
                (function() {
                    var username = '';
                    var caption = '';
                    
                    var userLink = document.querySelector('a[href*="/@"], header a[href^="/"]');
                    if (userLink) {
                        var href = userLink.getAttribute('href');
                        username = href.replace(/^\\/@?/, '').split('/')[0];
                    }
                    
                    var h1 = document.querySelector('h1');
                    if (h1) caption = h1.innerText;
                    
                    var spans = document.querySelectorAll('span');
                    for (var i = 0; i < spans.length && caption.length < 100; i++) {
                        var t = spans[i].innerText;
                        if (t.length > 20 && t.length < 200) {
                            caption += ' ' + t;
                        }
                    }
                    
                    return JSON.stringify({username: username, caption: caption.substring(0, 150)});
                })();
            '''
        
        result = self.safari.js(js_code)
        try:
            return json.loads(result) if result else {}
        except:
            return {}
    
    def _click_post(self, platform: Platform, url: str) -> bool:
        """Navigate to post."""
        self.safari.js(f"window.location.href = '{url}';")
        time.sleep(3)
        return True
    
    def _click_reply(self, platform: Platform) -> bool:
        """Click reply/comment button."""
        if platform == Platform.THREADS:
            result = self.safari.js('''
                (function() {
                    var btn = document.querySelector('svg[aria-label="Reply"]');
                    if (btn) {
                        btn.closest('[role="button"]').click();
                        return 'clicked';
                    }
                    return 'not_found';
                })();
            ''')
        else:
            result = self.safari.js('''
                (function() {
                    var textarea = document.querySelector('textarea');
                    if (textarea) {
                        textarea.focus();
                        textarea.click();
                        return 'focused';
                    }
                    return 'not_found';
                })();
            ''')
        return result in ['clicked', 'focused']
    
    def _submit_comment(self, platform: Platform) -> bool:
        """Submit the comment."""
        if platform == Platform.THREADS:
            result = self.safari.js('''
                (function() {
                    var btns = document.querySelectorAll('svg[aria-label="Reply"]');
                    if (btns.length >= 2) {
                        var btn = btns[1].closest('[role="button"]');
                        if (btn && !btn.getAttribute('aria-disabled')) {
                            btn.click();
                            return 'submitted';
                        }
                    }
                    return 'not_found';
                })();
            ''')
        else:
            result = self.safari.js('''
                (function() {
                    var btns = document.querySelectorAll('div[role="button"], button');
                    for (var i = 0; i < btns.length; i++) {
                        var txt = (btns[i].innerText || '').trim();
                        if (txt === 'Post') {
                            btns[i].click();
                            return 'submitted';
                        }
                    }
                    return 'not_found';
                })();
            ''')
        return result == 'submitted'
    
    def _verify_comment(self, comment: str) -> bool:
        """Verify comment was posted."""
        time.sleep(1)
        page_text = self.safari.js("document.body.innerText.substring(0, 5000)")
        return comment[:20] in page_text if comment else False
    
    def _go_back(self, platform: Platform):
        """Navigate back to feed."""
        if platform == Platform.THREADS:
            self.safari.js('''
                var btn = document.querySelector('svg[aria-label="Back"]');
                if (btn) btn.closest('[role="button"]').click();
                else history.back();
            ''')
        else:
            self.safari.js("history.back();")
        time.sleep(3)
    
    def run(self, platform: Platform, num_posts: int = 5) -> RunResult:
        """Run auto-comment for specified platform."""
        run_id = f"{platform.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now().isoformat()
        comments: List[CommentResult] = []
        
        print(f"\n{'='*60}")
        print(f"🚀 AUTO-COMMENT: {platform.value.upper()}")
        print(f"   Run ID: {run_id}")
        print(f"   Posts:  {num_posts}")
        print(f"{'='*60}")
        
        # Check Safari state
        safari_state = self.safari.check_safari_ready()
        print(f"\n📱 Safari State:")
        print(f"   Running: {safari_state['safari_running']}")
        print(f"   Window:  {safari_state['has_window']}")
        print(f"   URL:     {safari_state['current_url'][:50]}...")
        
        if not safari_state['safari_running'] or not safari_state['has_window']:
            print(f"   ❌ Error: {safari_state['error']}")
            return self._create_result(run_id, platform, started_at, safari_state, comments)
        
        # Navigate to platform
        base_url = "https://www.threads.com" if platform == Platform.THREADS else "https://www.instagram.com/"
        print(f"\n🌐 Navigating to {base_url}...")
        self.safari.navigate(base_url, wait_seconds=5)
        
        # Check login
        login_state = self.safari.check_login(platform)
        print(f"   Logged in: {login_state['logged_in']}")
        if login_state.get('username'):
            print(f"   Username:  @{login_state['username']}")
        
        if not login_state['logged_in']:
            print("   ⚠️ Warning: May not be logged in")
        
        # Wait for feed
        print("\n⏳ Waiting for feed to load...")
        if not self.safari.wait_for_feed(platform, max_wait=10):
            print("   ❌ Feed did not load")
            safari_state['error'] = "Feed did not load"
            return self._create_result(run_id, platform, started_at, safari_state, comments)
        
        # Get initial posts
        posts = self._get_feed_posts(platform)
        print(f"   Found {len(posts)} posts")
        
        # Process posts
        for i in range(num_posts):
            print(f"\n📝 Post {i+1}/{num_posts}")
            
            # Refresh post list (feed may have changed)
            posts = self._get_feed_posts(platform)
            if len(posts) <= i:
                print(f"   ❌ Not enough posts (found {len(posts)})")
                # Scroll to load more
                self.safari.js("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                posts = self._get_feed_posts(platform)
                if len(posts) <= i:
                    continue
            
            post = posts[i]
            post_url = post.get('url', '')
            post_id = post.get('id', '')
            
            result = CommentResult(
                platform=platform.value,
                post_index=i + 1,
                post_url=post_url,
                post_id=post_id,
                username="",
                context="",
                ai_comment="",
                status="pending",
                timestamp=datetime.now().isoformat()
            )
            
            print(f"   URL: {post_url[:60]}...")
            print(f"   ID:  {post_id}")
            
            # Check dedup
            if post_id in self.commented_ids:
                print(f"   ⏭️ SKIP: Already commented")
                result.status = "skipped"
                result.error = "duplicate"
                comments.append(result)
                continue
            
            # Click post
            self._click_post(platform, post_url)
            
            # Extract context
            context = self._extract_context(platform)
            result.username = context.get('username', '')
            result.context = context.get('caption', '')[:100]
            print(f"   @{result.username}: {result.context[:40]}...")
            
            # Generate AI comment
            if self.ai:
                ai_result = self.ai.generate(
                    f"@{result.username}: {result.context}",
                    platform.value
                )
                result.ai_comment = ai_result.get('comment', '')
                if ai_result.get('error'):
                    print(f"   ⚠️ AI Error: {ai_result['error']}")
            
            if not result.ai_comment:
                result.ai_comment = "Great content!"
            
            print(f"   💬 Comment: {result.ai_comment}")
            
            # Click reply
            if not self._click_reply(platform):
                print("   ❌ Could not click reply")
                result.status = "failed"
                result.error = "reply_button_not_found"
                comments.append(result)
                self._go_back(platform)
                continue
            
            time.sleep(0.5)
            
            # Type comment
            self.safari.type_text(result.ai_comment)
            time.sleep(0.5)
            
            # Submit
            if self._submit_comment(platform):
                print("   ✅ Submitted")
                result.status = "posted"
                
                # Verify
                time.sleep(2)
                result.verified = self._verify_comment(result.ai_comment)
                if result.verified:
                    print("   ✅ Verified")
                    self.commented_ids.add(post_id)
                else:
                    print("   ⚠️ Not verified (may still be posted)")
            else:
                print("   ❌ Submit failed")
                result.status = "failed"
                result.error = "submit_failed"
            
            comments.append(result)
            
            # Go back
            self._go_back(platform)
        
        # Save cache
        self._save_commented_cache()
        
        return self._create_result(run_id, platform, started_at, safari_state, comments)
    
    def _create_result(self, run_id: str, platform: Platform, started_at: str, 
                       safari_state: Dict, comments: List[CommentResult]) -> RunResult:
        """Create and save run result."""
        posted = sum(1 for c in comments if c.status == "posted")
        failed = sum(1 for c in comments if c.status == "failed")
        skipped = sum(1 for c in comments if c.status == "skipped")
        
        result = RunResult(
            run_id=run_id,
            platform=platform.value,
            started_at=started_at,
            completed_at=datetime.now().isoformat(),
            total_posts=len(comments),
            posted=posted,
            failed=failed,
            skipped=skipped,
            comments=[asdict(c) for c in comments],
            safari_state=safari_state
        )
        
        # Save to file
        output_file = self.output_dir / f"{run_id}.json"
        output_file.write_text(json.dumps(asdict(result), indent=2))
        print(f"\n💾 Results saved: {output_file}")
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 RESULTS: {platform.value.upper()}")
        print(f"{'='*60}")
        print(f"   Posted:  {posted}")
        print(f"   Failed:  {failed}")
        print(f"   Skipped: {skipped}")
        print(f"   Total:   {len(comments)}")
        
        for c in comments:
            status_icon = "✅" if c.status == "posted" else "⏭️" if c.status == "skipped" else "❌"
            print(f"   {status_icon} Post {c.post_index}: {c.ai_comment[:35]}...")
        
        return result


def main():
    parser = argparse.ArgumentParser(description="Auto-Comment Runner")
    parser.add_argument("--platform", "-p", choices=["threads", "instagram", "both"], 
                        required=True, help="Platform to comment on")
    parser.add_argument("--posts", "-n", type=int, default=5, 
                        help="Number of posts to comment on (default: 5)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output directory for results")
    
    args = parser.parse_args()
    
    runner = AutoCommentRunner(output_dir=args.output)
    
    if args.platform == "both":
        print("\n" + "="*60)
        print("🚀 RUNNING AUTO-COMMENT ON BOTH PLATFORMS")
        print("="*60)
        
        threads_result = runner.run(Platform.THREADS, args.posts)
        insta_result = runner.run(Platform.INSTAGRAM, args.posts)
        
        total_posted = threads_result.posted + insta_result.posted
        total = threads_result.total_posts + insta_result.total_posts
        
        print(f"\n{'='*60}")
        print(f"🎉 FINAL SUMMARY")
        print(f"{'='*60}")
        print(f"   Threads:   {threads_result.posted}/{threads_result.total_posts}")
        print(f"   Instagram: {insta_result.posted}/{insta_result.total_posts}")
        print(f"   Total:     {total_posted}/{total}")
    else:
        platform = Platform.THREADS if args.platform == "threads" else Platform.INSTAGRAM
        runner.run(platform, args.posts)


if __name__ == "__main__":
    main()
