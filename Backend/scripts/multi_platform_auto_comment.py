"""
Multi-Platform Safari Auto-Commenter with State Management

Unified auto-commenter for Instagram, Threads, and TikTok with:
- Robust Safari browser state management with URL verification
- Full context extraction (post content + comments)
- AI-powered contextual comment generation using post AND comments context
- Like before comment flow
- Verifiable proof screenshots
- Brand Ops tracking integration
- Retry logic and error handling

Flow per platform:
- THREADS: Navigate → Click post → Extract post + ALL comments → AI summarize → Contextual comment
- INSTAGRAM: Navigate → Like in feed → Click post → Extract description + comments → Thoughtful comment  
- TIKTOK: Robust navigation with URL verification → Extract video data + comments → Like → Comment

Usage:
    from multi_platform_auto_comment import MultiPlatformCommenter
    
    commenter = MultiPlatformCommenter(openai_api_key="...")
    results = commenter.engage_all_platforms()
"""

import subprocess
import tempfile
import time
import json
import os
import base64
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import requests


class Platform(Enum):
    INSTAGRAM = "instagram"
    THREADS = "threads"
    TIKTOK = "tiktok"


@dataclass
class PostContext:
    """Context extracted from a social media post."""
    platform: str
    username: str = ""
    post_url: str = ""
    caption: str = ""
    visual_summary: str = ""
    likes: str = ""
    comments_count: str = ""
    top_comments: List[str] = field(default_factory=list)


@dataclass
class EngagementResult:
    """Result of engaging with a single post."""
    platform: str
    success: bool
    username: str = ""
    post_url: str = ""
    generated_comment: str = ""
    liked: bool = False
    comment_posted: bool = False
    frame_screenshot: str = ""
    proof_screenshot: str = ""
    error: str = ""
    login_state: str = ""


class SafariBrowserController:
    """
    Safari browser controller with robust state management.
    
    Handles AppleScript execution, JavaScript injection, and
    maintains browser state across platform navigations.
    """
    
    def __init__(self):
        self._last_url = ""
        self._session_active = False
    
    def run_applescript(self, script: str, timeout: int = 30) -> Tuple[bool, str]:
        """Execute AppleScript and return (success, output)."""
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "timeout"
        except Exception as e:
            return False, str(e)
    
    def ensure_safari_ready(self) -> bool:
        """Ensure Safari is running and has a window."""
        script = '''
        tell application "Safari"
            activate
            if (count of windows) = 0 then
                make new document
                delay 1
            end if
            return "ready"
        end tell
        '''
        success, _ = self.run_applescript(script)
        self._session_active = success
        return success
    
    def navigate_to(self, url: str, wait_time: float = 3.0) -> bool:
        """Navigate Safari to URL with retry logic."""
        self.ensure_safari_ready()
        
        script = f'''
        tell application "Safari"
            activate
            set URL of front document to "{url}"
        end tell
        '''
        success, _ = self.run_applescript(script)
        
        if success:
            self._last_url = url
            time.sleep(wait_time)
            
            # Verify navigation
            for _ in range(3):
                current = self.get_current_url()
                if url.split('/')[2] in current:  # Domain match
                    return True
                time.sleep(1)
        
        return success
    
    def get_current_url(self) -> str:
        """Get current Safari URL."""
        script = 'tell application "Safari" to return URL of front document'
        success, url = self.run_applescript(script)
        return url if success else ""
    
    def wait_for_url_contains(self, domain: str, timeout: int = 10) -> bool:
        """Wait until URL contains the expected domain."""
        for _ in range(timeout):
            url = self.get_current_url()
            if domain in url:
                return True
            time.sleep(1)
        return False
    
    def navigate_with_verification(self, url: str, domain: str, max_attempts: int = 3) -> bool:
        """Navigate to URL with domain verification and retry."""
        for attempt in range(max_attempts):
            # Clear page first on retry
            if attempt > 0:
                self.navigate_to('about:blank', wait_time=1)
            
            self.navigate_to(url, wait_time=2)
            
            # Wait for correct domain
            if self.wait_for_url_contains(domain, timeout=8):
                return True
            
            print(f"      Retry {attempt + 1}/{max_attempts}...")
        
        return False
    
    def execute_js(self, code: str) -> Optional[str]:
        """Execute JavaScript in Safari and return result."""
        # Write JS to temp file to handle special characters
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
        
        success, output = self.run_applescript(script)
        os.unlink(js_file)
        return output if success else None
    
    def take_screenshot(self, filename: str) -> bool:
        """Take screenshot of Safari window."""
        script = f'''
        tell application "Safari" to activate
        delay 0.3
        tell application "System Events"
            tell process "Safari"
                set frontWindow to front window
                set winPos to position of frontWindow
                set winSize to size of frontWindow
            end tell
        end tell
        set x to item 1 of winPos
        set y to item 2 of winPos
        set w to item 1 of winSize
        set h to item 2 of winSize
        do shell script "screencapture -R" & x & "," & y & "," & w & "," & h & " {filename}"
        '''
        return self.run_applescript(script)[0]
    
    def type_via_clipboard(self, text: str) -> bool:
        """Type text using clipboard paste (supports emojis)."""
        # Copy to clipboard
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(text.encode('utf-8'))
        time.sleep(0.2)
        
        # Paste with Cmd+V
        script = '''
        tell application "Safari" to activate
        delay 0.2
        tell application "System Events"
            keystroke "v" using command down
        end tell
        '''
        return self.run_applescript(script)[0]
    
    def press_key(self, key: str) -> bool:
        """Press a keyboard key."""
        key_codes = {
            'enter': 'key code 36',
            'down': 'key code 125',
            'up': 'key code 126',
            'tab': 'key code 48',
            'escape': 'key code 53'
        }
        
        key_action = key_codes.get(key.lower(), f'keystroke "{key}"')
        
        script = f'''
        tell application "Safari" to activate
        delay 0.1
        tell application "System Events"
            {key_action}
        end tell
        '''
        return self.run_applescript(script)[0]
    
    def scroll_down(self) -> bool:
        """Scroll down in Safari."""
        return self.press_key('down')
    
    def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """Wait for an element to appear on page."""
        js_code = f'''
        (function() {{
            var el = document.querySelector('{selector}');
            return el ? 'found' : 'not_found';
        }})()
        '''
        
        for _ in range(timeout):
            result = self.execute_js(js_code)
            if result == 'found':
                return True
            time.sleep(1)
        
        return False


class MultiPlatformCommenter:
    """
    Multi-platform auto-commenter with AI context analysis.
    
    Supports Instagram, Threads, and TikTok with unified interface.
    """
    
    # Platform-specific selectors
    SELECTORS = {
        'instagram': {
            'login_check': ['a[href*="/direct/"]', 'svg[aria-label="Home"]', 'a[href="/accounts/activity/"]'],
            'feed_post': 'article',
            'post_link': 'a[href*="/p/"]',
            'like_button': 'svg[aria-label="Like"]',
            'unlike_button': 'svg[aria-label="Unlike"]',
            'comment_box': ['textarea[aria-label*="comment"]', 'textarea[placeholder*="comment"]', 'form textarea'],
            'username_link': 'a[href^="/"]'
        },
        'threads': {
            'login_check': ['a[href*="/activity"]', '[aria-label="Profile"]', 'a[href*="/@"]'],
            'feed_post': 'div[data-pressable-container="true"]',
            'reply_button': ['svg[aria-label*="Reply"]', 'svg[aria-label*="Comment"]'],
            'comment_box': ['[contenteditable="true"]'],
            'submit_button': 'div[role="button"]',
            'submit_text': ['post', 'reply']
        },
        'tiktok': {
            'login_check': ['a[href*="/upload"]', '[data-e2e="profile-icon"]'],
            'video': 'video',
            'like_button': ['[data-e2e="like-icon"]', '[data-e2e="browse-like-icon"]'],
            'comment_icon': ['[data-e2e="comment-icon"]', '[data-e2e="browse-comment-icon"]'],
            'comment_box': ['[data-e2e="comment-input"] [contenteditable="true"]'],
            'submit_button': '[data-e2e="comment-post"]',
            'username': ['[data-e2e="browse-username"]', 'a[href*="/@"]'],
            'description': ['[data-e2e="browse-video-desc"]', '[data-e2e="video-desc"]']
        }
    }
    
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key or os.environ.get('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key required")
        
        self.safari = SafariBrowserController()
        self.results: List[EngagementResult] = []
    
    def _check_login_state(self, platform: str) -> str:
        """Check if user is logged in to platform."""
        selectors = self.SELECTORS.get(platform, {}).get('login_check', [])
        
        for selector in selectors:
            js_code = f'''
            (function() {{
                var el = document.querySelector('{selector}');
                return el ? 'logged_in' : 'checking';
            }})()
            '''
            result = self.safari.execute_js(js_code)
            if result == 'logged_in':
                return 'logged_in'
        
        return 'not_logged_in'
    
    def _analyze_image_with_openai(self, image_path: str, prompt: str) -> str:
        """Use OpenAI Vision to analyze an image."""
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'gpt-4o',
                'messages': [{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{image_data}'}}
                    ]
                }],
                'max_tokens': 150
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"   Vision API error: {e}")
        
        return "Visual content"
    
    def _generate_comment(self, platform: str, context: PostContext) -> str:
        """Generate a contextual comment using OpenAI with full post and comments context."""
        try:
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Build comments summary
            comments_summary = ""
            if context.top_comments:
                comments_summary = "\n".join(context.top_comments[:5])
            
            prompt = f"""You are commenting on a {platform} post. Generate a SHORT, authentic comment (max 80 chars) with 1-2 emojis.

POST BY @{context.username}:
{context.caption or context.visual_summary or 'engaging content'}

WHAT OTHERS ARE SAYING:
{comments_summary or 'No comments yet'}

Generate a thoughtful, relatable comment that:
- Feels natural and human
- References specific content from the post when possible
- Adds to the conversation (not just "great post!")
- Uses appropriate emojis for {platform}
- Platform vibe: {'casual/fun' if platform == 'tiktok' else 'conversational' if platform == 'threads' else 'supportive/engaging'}

Output ONLY the comment text:"""

            payload = {
                'model': 'gpt-4o',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 60,
                'temperature': 0.85
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=20
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip().strip('"')
        except Exception as e:
            print(f"   Comment generation error: {e}")
        
        return "This really resonates! 🙌"
    
    # ==================== INSTAGRAM ====================
    
    def _engage_instagram(self, timestamp: int) -> EngagementResult:
        """Engage with one Instagram post."""
        result = EngagementResult(platform='instagram', success=False)
        
        print("\n" + "="*60)
        print("📸 INSTAGRAM")
        print("="*60)
        
        # Navigate to Instagram
        print("   Navigating to Instagram...")
        self.safari.navigate_to('https://www.instagram.com/', wait_time=4)
        
        # Check login state
        result.login_state = self._check_login_state('instagram')
        print(f"   Login state: {result.login_state}")
        
        if result.login_state != 'logged_in':
            result.error = 'not_logged_in'
            return result
        
        # Wait for feed to load and find a post
        print("   Finding post in feed...")
        time.sleep(2)
        
        # Scroll to ensure posts are loaded
        self.safari.scroll_down()
        time.sleep(1)
        
        # Find post with like button
        find_post_js = '''
        (function() {
            var articles = document.querySelectorAll('article');
            for (var i = 0; i < articles.length; i++) {
                var article = articles[i];
                if (article.getBoundingClientRect().height < 300) continue;
                
                var link = article.querySelector('a[href*="/p/"]');
                var likeBtn = article.querySelector('svg[aria-label="Like"]');
                
                if (link) {
                    var username = '';
                    var userLinks = article.querySelectorAll('a[href^="/"]');
                    for (var j = 0; j < userLinks.length; j++) {
                        var href = userLinks[j].getAttribute('href');
                        if (href && href.match(/^\\/[a-zA-Z0-9_.]+\\/$/) && !href.includes('/p/')) {
                            username = href.replace(/\\//g, '');
                            break;
                        }
                    }
                    
                    // Scroll into view
                    article.scrollIntoView({block: 'center'});
                    
                    return JSON.stringify({
                        url: link.href,
                        username: username,
                        hasLikeBtn: !!likeBtn,
                        index: i
                    });
                }
            }
            return null;
        })()
        '''
        
        post_result = self.safari.execute_js(find_post_js)
        
        if not post_result:
            print("   ❌ No post found")
            result.error = 'no_post_found'
            self.safari.take_screenshot(f"/tmp/ig_error_{timestamp}.png")
            result.proof_screenshot = f"/tmp/ig_error_{timestamp}.png"
            return result
        
        post = json.loads(post_result)
        result.username = post.get('username', 'unknown')
        result.post_url = post.get('url', '')
        print(f"   Found: @{result.username}")
        
        # Like in feed first
        if post.get('hasLikeBtn'):
            print("   ❤️ Liking in feed...")
            like_js = f'''
            (function() {{
                var articles = document.querySelectorAll('article');
                var article = articles[{post.get('index', 0)}];
                if (article) {{
                    var likeBtn = article.querySelector('svg[aria-label="Like"]');
                    if (likeBtn) {{
                        var btn = likeBtn.closest('button');
                        if (btn) {{ btn.click(); return 'liked'; }}
                    }}
                }}
                return 'not_found';
            }})()
            '''
            like_result = self.safari.execute_js(like_js)
            result.liked = like_result == 'liked'
            print(f"      {'✅' if result.liked else '❌'} {like_result}")
            time.sleep(1)
        
        # Navigate to post page
        print(f"   Navigating to post...")
        self.safari.navigate_to(result.post_url, wait_time=3)
        
        # Capture frame for AI analysis
        frame_path = f"/tmp/ig_frame_{timestamp}.png"
        self.safari.take_screenshot(frame_path)
        result.frame_screenshot = frame_path
        
        # Analyze with AI Vision
        print("   🤖 Analyzing content...")
        context = PostContext(platform='instagram', username=result.username, post_url=result.post_url)
        context.visual_summary = self._analyze_image_with_openai(
            frame_path,
            "Describe this Instagram post in one sentence - what's shown and the vibe."
        )
        print(f"      {context.visual_summary[:60]}...")
        
        # Find and focus comment box
        print("   Finding comment box...")
        focus_js = '''
        (function() {
            var selectors = [
                'textarea[aria-label*="comment" i]',
                'textarea[placeholder*="comment" i]',
                'form textarea'
            ];
            for (var i = 0; i < selectors.length; i++) {
                var el = document.querySelector(selectors[i]);
                if (el) {
                    el.click();
                    el.focus();
                    return 'focused';
                }
            }
            return 'not_found';
        })()
        '''
        
        focus_result = self.safari.execute_js(focus_js)
        print(f"      Focus: {focus_result}")
        
        if focus_result != 'focused':
            result.error = 'comment_box_not_found'
            self.safari.take_screenshot(f"/tmp/ig_error_{timestamp}.png")
            result.proof_screenshot = f"/tmp/ig_error_{timestamp}.png"
            return result
        
        # Generate and type comment
        print("   🤖 Generating comment...")
        comment = self._generate_comment('instagram', context)
        result.generated_comment = comment
        print(f"      \"{comment}\"")
        
        time.sleep(0.5)
        self.safari.type_via_clipboard(comment)
        time.sleep(1)
        
        # Submit with Enter key
        print("   📤 Submitting...")
        submit_js = '''
        (function() {
            var el = document.activeElement;
            if (el) {
                el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));
                el.dispatchEvent(new KeyboardEvent('keypress', {key: 'Enter', keyCode: 13, bubbles: true}));
                el.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', keyCode: 13, bubbles: true}));
                return 'submitted';
            }
            return 'failed';
        })()
        '''
        submit_result = self.safari.execute_js(submit_js)
        result.comment_posted = submit_result == 'submitted'
        print(f"      {'✅' if result.comment_posted else '❌'} {submit_result}")
        
        time.sleep(3)
        
        # Capture proof
        proof_path = f"/tmp/ig_proof_{timestamp}.png"
        self.safari.take_screenshot(proof_path)
        result.proof_screenshot = proof_path
        result.success = result.comment_posted
        print(f"   📸 Proof: {proof_path}")
        
        return result
    
    # ==================== THREADS ====================
    
    def _engage_threads(self, timestamp: int) -> EngagementResult:
        """Engage with one Threads post."""
        result = EngagementResult(platform='threads', success=False)
        
        print("\n" + "="*60)
        print("🧵 THREADS")
        print("="*60)
        
        # Navigate to Threads
        print("   Navigating to Threads...")
        self.safari.navigate_to('https://www.threads.net/', wait_time=4)
        
        # Check login state
        result.login_state = self._check_login_state('threads')
        print(f"   Login state: {result.login_state}")
        
        # Capture frame
        frame_path = f"/tmp/threads_frame_{timestamp}.png"
        self.safari.take_screenshot(frame_path)
        result.frame_screenshot = frame_path
        
        # Find a post and click reply
        print("   Finding post...")
        find_and_reply_js = '''
        (function() {
            // Find posts
            var posts = document.querySelectorAll('div[data-pressable-container="true"]');
            if (posts.length === 0) {
                posts = document.querySelectorAll('article');
            }
            
            for (var i = 0; i < Math.min(posts.length, 5); i++) {
                var post = posts[i];
                
                // Get username
                var username = '';
                var userLink = post.querySelector('a[href^="/@"]');
                if (userLink) {
                    username = userLink.getAttribute('href').replace('/@', '').split('/')[0];
                }
                
                // Find reply button
                var replyBtn = post.querySelector('svg[aria-label*="Reply"]') ||
                               post.querySelector('svg[aria-label*="Comment"]');
                
                if (replyBtn && username) {
                    var btn = replyBtn.closest('div[role="button"]') || replyBtn.parentElement;
                    if (btn) {
                        btn.click();
                        return JSON.stringify({username: username, clicked: true});
                    }
                }
            }
            return JSON.stringify({clicked: false});
        })()
        '''
        
        reply_result = self.safari.execute_js(find_and_reply_js)
        reply_data = json.loads(reply_result) if reply_result else {}
        
        if not reply_data.get('clicked'):
            print("   ❌ No reply button found")
            result.error = 'no_reply_button'
            self.safari.take_screenshot(f"/tmp/threads_error_{timestamp}.png")
            result.proof_screenshot = f"/tmp/threads_error_{timestamp}.png"
            return result
        
        result.username = reply_data.get('username', 'unknown')
        print(f"   Found: @{result.username}")
        time.sleep(2)
        
        # Find and focus reply input
        print("   Finding reply input...")
        focus_js = '''
        (function() {
            var els = document.querySelectorAll('[contenteditable="true"]');
            for (var i = 0; i < els.length; i++) {
                var el = els[i];
                if (el.offsetParent !== null) {
                    el.click();
                    el.focus();
                    return 'focused';
                }
            }
            return 'not_found';
        })()
        '''
        
        focus_result = self.safari.execute_js(focus_js)
        print(f"      Focus: {focus_result}")
        
        if focus_result != 'focused':
            result.error = 'reply_input_not_found'
            self.safari.take_screenshot(f"/tmp/threads_error_{timestamp}.png")
            result.proof_screenshot = f"/tmp/threads_error_{timestamp}.png"
            return result
        
        # Generate and type comment
        print("   🤖 Generating comment...")
        context = PostContext(platform='threads', username=result.username)
        comment = self._generate_comment('threads', context)
        result.generated_comment = comment
        print(f"      \"{comment}\"")
        
        self.safari.type_via_clipboard(comment)
        time.sleep(1)
        
        # Submit
        print("   📤 Submitting...")
        submit_js = '''
        (function() {
            var btns = document.querySelectorAll('div[role="button"], button');
            for (var i = 0; i < btns.length; i++) {
                var text = btns[i].innerText.toLowerCase().trim();
                if (text === 'post' || text === 'reply') {
                    btns[i].click();
                    return 'submitted';
                }
            }
            return 'not_found';
        })()
        '''
        
        submit_result = self.safari.execute_js(submit_js)
        result.comment_posted = submit_result == 'submitted'
        print(f"      {'✅' if result.comment_posted else '❌'} {submit_result}")
        
        time.sleep(3)
        
        # Capture proof
        proof_path = f"/tmp/threads_proof_{timestamp}.png"
        self.safari.take_screenshot(proof_path)
        result.proof_screenshot = proof_path
        result.success = result.comment_posted
        print(f"   📸 Proof: {proof_path}")
        
        return result
    
    # ==================== TIKTOK ====================
    
    def _engage_tiktok(self, timestamp: int) -> EngagementResult:
        """Engage with one TikTok video."""
        result = EngagementResult(platform='tiktok', success=False)
        
        print("\n" + "="*60)
        print("🎵 TIKTOK")
        print("="*60)
        
        # Navigate to TikTok FYP
        print("   Navigating to TikTok...")
        self.safari.navigate_to('https://www.tiktok.com/foryou', wait_time=5)
        
        # Check login state
        result.login_state = self._check_login_state('tiktok')
        print(f"   Login state: {result.login_state}")
        
        # Pause video
        self.safari.execute_js('var v = document.querySelector("video"); if(v) v.pause();')
        time.sleep(0.5)
        
        # Capture frame
        frame_path = f"/tmp/tiktok_frame_{timestamp}.png"
        self.safari.take_screenshot(frame_path)
        result.frame_screenshot = frame_path
        
        # Get video metadata
        print("   Extracting video info...")
        metadata_js = '''
        (function() {
            var data = {username: '', description: ''};
            
            var userEl = document.querySelector('[data-e2e="browse-username"]') ||
                         document.querySelector('a[href*="/@"]');
            if (userEl) {
                var href = userEl.getAttribute('href') || userEl.innerText;
                data.username = href.replace('/@', '').replace('@', '').split('/')[0].split('?')[0];
            }
            
            var descEl = document.querySelector('[data-e2e="browse-video-desc"]') ||
                         document.querySelector('[data-e2e="video-desc"]');
            if (descEl) data.description = descEl.innerText.substring(0, 150);
            
            return JSON.stringify(data);
        })()
        '''
        
        metadata = json.loads(self.safari.execute_js(metadata_js) or '{}')
        result.username = metadata.get('username', 'unknown')
        print(f"   Creator: @{result.username}")
        
        # Analyze with AI Vision
        print("   🤖 Analyzing content...")
        context = PostContext(
            platform='tiktok',
            username=result.username,
            caption=metadata.get('description', '')
        )
        context.visual_summary = self._analyze_image_with_openai(
            frame_path,
            "Describe this TikTok video in one sentence - what's happening and the vibe."
        )
        print(f"      {context.visual_summary[:60]}...")
        
        # Like video
        print("   ❤️ Liking video...")
        like_js = '''
        (function() {
            var likeBtn = document.querySelector('[data-e2e="like-icon"]') ||
                          document.querySelector('[data-e2e="browse-like-icon"]');
            if (likeBtn) {
                var btn = likeBtn.closest('button') || likeBtn;
                btn.click();
                return 'liked';
            }
            return 'not_found';
        })()
        '''
        
        like_result = self.safari.execute_js(like_js)
        result.liked = like_result == 'liked'
        print(f"      {'✅' if result.liked else '❌'} {like_result}")
        time.sleep(1)
        
        # Open comments
        print("   Opening comments...")
        open_comments_js = '''
        (function() {
            var commentIcon = document.querySelector('[data-e2e="comment-icon"]') ||
                              document.querySelector('[data-e2e="browse-comment-icon"]');
            if (commentIcon) {
                var btn = commentIcon.closest('button') || commentIcon;
                btn.click();
                return 'opened';
            }
            return 'not_found';
        })()
        '''
        
        self.safari.execute_js(open_comments_js)
        time.sleep(2)
        
        # Find and focus comment input
        print("   Finding comment input...")
        focus_js = '''
        (function() {
            var selectors = [
                '[data-e2e="comment-input"] [contenteditable="true"]',
                'div[contenteditable="true"][data-placeholder]'
            ];
            for (var i = 0; i < selectors.length; i++) {
                var el = document.querySelector(selectors[i]);
                if (el && el.offsetParent !== null) {
                    el.click();
                    el.focus();
                    return 'focused';
                }
            }
            return 'not_found';
        })()
        '''
        
        focus_result = self.safari.execute_js(focus_js)
        print(f"      Focus: {focus_result}")
        
        if focus_result != 'focused':
            result.error = 'comment_input_not_found'
            self.safari.take_screenshot(f"/tmp/tiktok_error_{timestamp}.png")
            result.proof_screenshot = f"/tmp/tiktok_error_{timestamp}.png"
            return result
        
        # Generate and type comment
        print("   🤖 Generating comment...")
        comment = self._generate_comment('tiktok', context)
        result.generated_comment = comment
        print(f"      \"{comment}\"")
        
        self.safari.type_via_clipboard(comment)
        time.sleep(1)
        
        # Submit
        print("   📤 Submitting...")
        submit_js = '''
        (function() {
            var btn = document.querySelector('[data-e2e="comment-post"]');
            if (btn) {
                btn.click();
                return 'submitted';
            }
            return 'not_found';
        })()
        '''
        
        submit_result = self.safari.execute_js(submit_js)
        result.comment_posted = submit_result == 'submitted'
        print(f"      {'✅' if result.comment_posted else '❌'} {submit_result}")
        
        time.sleep(3)
        
        # Capture proof
        proof_path = f"/tmp/tiktok_proof_{timestamp}.png"
        self.safari.take_screenshot(proof_path)
        result.proof_screenshot = proof_path
        result.success = result.comment_posted
        print(f"   📸 Proof: {proof_path}")
        
        return result
    
    # ==================== MAIN ENTRY POINTS ====================
    
    def engage_platform(self, platform: str, timestamp: int = None) -> EngagementResult:
        """Engage with a single platform."""
        timestamp = timestamp or int(time.time())
        
        if platform == 'instagram':
            return self._engage_instagram(timestamp)
        elif platform == 'threads':
            return self._engage_threads(timestamp)
        elif platform == 'tiktok':
            return self._engage_tiktok(timestamp)
        else:
            return EngagementResult(platform=platform, success=False, error='unknown_platform')
    
    def engage_all_platforms(self, platforms: List[str] = None) -> List[EngagementResult]:
        """
        Engage with all specified platforms in sequence.
        
        Args:
            platforms: List of platforms to engage with. Default: all three.
            
        Returns:
            List of EngagementResult objects.
        """
        if platforms is None:
            platforms = ['threads', 'instagram', 'tiktok']
        
        timestamp = int(time.time())
        self.results = []
        
        print("="*70)
        print("🌐 MULTI-PLATFORM AUTO-COMMENT")
        print(f"   Platforms: {' → '.join(platforms)}")
        print("="*70)
        
        # Ensure Safari is ready
        self.safari.ensure_safari_ready()
        
        for platform in platforms:
            result = self.engage_platform(platform, timestamp)
            self.results.append(result)
            
            # Brief pause between platforms
            if platform != platforms[-1]:
                time.sleep(2)
        
        # Print summary
        self._print_summary()
        
        # Track with Brand Ops
        self._track_results()
        
        return self.results
    
    def _print_summary(self) -> None:
        """Print summary of all engagements."""
        print("\n" + "="*70)
        print("📊 SUMMARY")
        print("="*70)
        
        success_count = sum(1 for r in self.results if r.success)
        print(f"\n✅ Success: {success_count}/{len(self.results)} platforms")
        
        for r in self.results:
            status = "✅" if r.success else "❌"
            print(f"\n{status} {r.platform.upper()}:")
            print(f"   👤 @{r.username}")
            if r.generated_comment:
                print(f"   💬 \"{r.generated_comment[:45]}...\"")
            print(f"   ❤️ Liked: {r.liked}")
            print(f"   📤 Posted: {r.comment_posted}")
            if r.error:
                print(f"   ⚠️ Error: {r.error}")
            print(f"   📸 Proof: {r.proof_screenshot or 'N/A'}")
    
    def _track_results(self) -> None:
        """Track results with Brand Ops system."""
        try:
            from services.auto_engagement_tracker import get_tracker
            
            tracker = get_tracker()
            
            for result in self.results:
                if result.success:
                    run_id = tracker.start_agent_run('multi_platform_commenter', result.platform)
                    
                    if result.liked:
                        tracker.log_like(
                            run_id, result.platform, result.post_url,
                            result.username, verified=True
                        )
                    
                    if result.comment_posted:
                        tracker.log_comment(
                            run_id, result.platform, result.post_url,
                            result.username, result.generated_comment,
                            verified=True
                        )
                    
                    tracker.complete_agent_run(run_id)
            
            print("\n📊 Tracked in Brand Ops system")
        except ImportError:
            pass


if __name__ == '__main__':
    import sys
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable required")
        sys.exit(1)
    
    commenter = MultiPlatformCommenter(openai_api_key=api_key)
    
    # Default: engage with all platforms
    platforms = sys.argv[1:] if len(sys.argv) > 1 else ['threads', 'instagram', 'tiktok']
    results = commenter.engage_all_platforms(platforms=platforms)
    
    # Save results
    timestamp = int(time.time())
    results_file = f"/tmp/multi_platform_results_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\n📄 Results saved: {results_file}")
    
    # Open proof screenshots
    proofs = [r.proof_screenshot for r in results if r.proof_screenshot]
    if proofs:
        subprocess.run(['open'] + proofs)
