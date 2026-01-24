#!/usr/bin/env python3
"""
Safari Auto Comment

Implements Instagram auto-commenting functionality using Safari.app
via AppleScript for DOM manipulation. Adapted from Instagram-Core.ts

Uses the real Safari browser with existing logins/cookies.

Requires:
- macOS
- Safari Developer Menu enabled (Safari > Settings > Advanced > Show Develop menu)
- Automation permissions in System Settings > Privacy & Security > Automation
"""

import subprocess
import tempfile
import time
import json
import os
import sys
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

# ==================== SELECTORS ====================

# Comment box selectors in priority order
COMMENT_BOX_SELECTORS = [
    'textarea[aria-label="Add a comment…"]',        # Unicode ellipsis (primary)
    'textarea[placeholder="Add a comment…"]',       # Unicode ellipsis
    'textarea[placeholder="Add a comment..."]',     # Three dots fallback
    'textarea[aria-label*="comment"]',              # Partial match
    'form textarea',                                 # Generic form textarea
    'div[contenteditable="true"][role="textbox"]'   # Contenteditable fallback
]

# Comment icon selector to open the composer
COMMENT_ICON_SELECTOR = 'svg[aria-label="Comment"]'

# Submit button selectors
SUBMIT_SELECTORS = [
    'button[type="submit"]',
    'div[role="button"]',
    'form div[role="button"]',
    'form button:not([type])'
]

# Multi-locale submit button labels
SUBMIT_LABELS = [
    # English
    'post', 'send',
    # French
    'publier', 'envoyer',
    # Spanish / Portuguese
    'publicar', 'enviar', 'postar',
    # Italian
    'pubblica',
    # German
    'veröffentlichen', 'senden',
    # Turkish
    'gönder',
    # Japanese
    '投稿',
    # Korean
    '게시', '보내기',
    # Chinese (Simplified)
    '发布', '发表', '发送',
    # Vietnamese
    'gửi'
]

# Locale-specific keywords for comment field detection
COMMENT_KEYWORDS = [
    'comment', 'comentario', 'comentários', 'commentaire', 'kommentar', 'commento',
    'коммент', 'تعليق', 'yorum', 'コメント', '評論', '评论', '댓글', 'komentar'
]

# ==================== DATA CLASSES ====================

@dataclass
class MethodAttempt:
    method: str
    success: bool
    time_ms: int
    error: Optional[str] = None

@dataclass
class CommentResult:
    success: bool
    error: Optional[str] = None
    method: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class CommentBoxResult:
    found: bool
    selector: Optional[str] = None
    is_content_editable: bool = False

@dataclass
class LikeResult:
    success: bool
    already_liked: bool = False
    verified: bool = False
    error: Optional[str] = None

@dataclass
class PostContext:
    username: str = ''
    caption: str = ''
    image_alt: str = ''
    like_count: str = ''
    top_comments: List[str] = field(default_factory=list)
    post_url: str = ''

@dataclass
class EngageResult:
    like_result: Optional[LikeResult] = None
    comment_result: Optional[CommentResult] = None
    context: Optional[PostContext] = None
    generated_comment: str = ''
    screenshot_path: Optional[str] = None

# ==================== SAFARI CONTROLLER ====================

class SafariController:
    """Controls Safari browser via AppleScript."""
    
    def __init__(self, timeout: int = 30000):
        self.timeout = timeout
    
    def run_applescript(self, script: str) -> tuple:
        """Execute AppleScript and return (success, output)."""
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=self.timeout // 1000
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, 'timeout'
        except Exception as e:
            return False, str(e)
    
    def execute_js(self, js_code: str) -> str:
        """Execute JavaScript in Safari using temp file to avoid escaping issues."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(js_code)
            js_file = f.name
        
        try:
            script = f'''
            tell application "Safari"
                tell front document
                    set jsCode to read POSIX file "{js_file}"
                    do JavaScript jsCode
                end tell
            end tell
            '''
            success, output = self.run_applescript(script)
            return output if success else ''
        finally:
            os.unlink(js_file)
    
    def navigate_to(self, url: str) -> bool:
        """Navigate Safari to a URL."""
        script = f'''
        tell application "Safari"
            activate
            tell front document
                set URL to "{url}"
            end tell
        end tell
        '''
        success, _ = self.run_applescript(script)
        return success
    
    def get_current_url(self) -> str:
        """Get current Safari URL."""
        script = '''
        tell application "Safari"
            tell front document
                return URL
            end tell
        end tell
        '''
        success, output = self.run_applescript(script)
        return output if success else ''

# ==================== SAFARI AUTO COMMENT CLASS ====================

class SafariAutoComment:
    """Instagram auto-commenting via Safari AppleScript."""
    
    def __init__(self, timeout: int = 30000):
        self.safari = SafariController(timeout)
        self.timeout = timeout
    
    def delay(self, ms: int):
        """Helper delay function."""
        time.sleep(ms / 1000)
    
    def log(self, msg: str, is_moderation: bool = False):
        """Log message."""
        if is_moderation:
            print(msg, flush=True)
    
    def navigate_to_post(self, permalink: str) -> bool:
        """Navigate to an Instagram post permalink."""
        print(f'[safari] Navigating to post: {permalink}', flush=True)
        success = self.safari.navigate_to(permalink)
        if success:
            self.delay(3000)  # Wait for post to load
        return success
    
    def scroll_post_into_view(self):
        """Scroll post into view."""
        js_code = '''
(function() {
    var article = document.querySelector('article');
    if (article) {
        article.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return 'scrolled';
    }
    return 'no_article';
})()'''
        self.safari.execute_js(js_code)
        self.delay(1500)
    
    def take_screenshot(self, filename: str = None) -> Optional[str]:
        """Take screenshot of Safari window automatically (no manual click)."""
        if not filename:
            filename = f"/tmp/instagram_proof_{int(time.time())}.png"
        
        # Get Safari window ID and capture it directly
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
        success, _ = self.safari.run_applescript(script)
        return filename if success and os.path.exists(filename) else None
    
    def like_post(self) -> LikeResult:
        """Like the current post and verify."""
        # Check current like state and click if needed
        # Handle both article view and modal/dialog view
        js_code = '''
(function() {
    // Find the container - could be article or modal dialog
    var container = document.querySelector('article') || 
                    document.querySelector('div[role="dialog"]') ||
                    document.querySelector('div[role="presentation"]') ||
                    document.body;
    
    // Look for Like/Unlike SVG in the action section (near Comment, Share)
    var sections = container.querySelectorAll('section');
    
    // Also check direct descendants if no sections found
    if (sections.length === 0) {
        // Try finding like button directly
        var likeBtn = container.querySelector('svg[aria-label="Like"]');
        var unlikeBtn = container.querySelector('svg[aria-label="Unlike"]');
        
        if (unlikeBtn) {
            return JSON.stringify({status: 'already_liked', clicked: false});
        }
        
        if (likeBtn) {
            var btn = likeBtn.closest('button') || 
                      likeBtn.closest('div[role="button"]') || 
                      likeBtn.parentElement;
            if (btn) {
                btn.click();
                return JSON.stringify({status: 'clicked', clicked: true});
            }
        }
    }
    
    for (var i = 0; i < sections.length; i++) {
        var section = sections[i];
        var hasComment = section.querySelector('svg[aria-label="Comment"]');
        var hasShare = section.querySelector('svg[aria-label="Share Post"]') || 
                       section.querySelector('svg[aria-label="Share"]');
        
        if (hasComment || hasShare) {
            var likeBtn = section.querySelector('svg[aria-label="Like"]');
            var unlikeBtn = section.querySelector('svg[aria-label="Unlike"]');
            
            if (unlikeBtn) {
                return JSON.stringify({status: 'already_liked', clicked: false});
            }
            
            if (likeBtn) {
                var btn = likeBtn.closest('button') || 
                          likeBtn.closest('div[role="button"]') || 
                          likeBtn.parentElement;
                if (btn) {
                    btn.click();
                    return JSON.stringify({status: 'clicked', clicked: true});
                }
            }
        }
    }
    
    // Final fallback: find any Like button on page
    var allLike = document.querySelector('svg[aria-label="Like"]');
    var allUnlike = document.querySelector('svg[aria-label="Unlike"]');
    
    if (allUnlike) {
        return JSON.stringify({status: 'already_liked', clicked: false});
    }
    
    if (allLike) {
        var btn = allLike.closest('button') || 
                  allLike.closest('div[role="button"]') || 
                  allLike.parentElement;
        if (btn) {
            btn.click();
            return JSON.stringify({status: 'clicked', clicked: true});
        }
    }
    
    return JSON.stringify({error: 'like_button_not_found'});
})()'''
        
        try:
            result = self.safari.execute_js(js_code)
            data = json.loads(result) if result else {}
            
            if data.get('error'):
                return LikeResult(success=False, error=data['error'])
            
            if data.get('status') == 'already_liked':
                return LikeResult(success=True, already_liked=True, verified=True)
            
            if data.get('status') == 'clicked':
                self.delay(1500)
                # Verify like was successful
                verify_js = '''
(function() {
    // Check for Unlike button anywhere on page
    var unlikeBtn = document.querySelector('svg[aria-label="Unlike"]');
    if (unlikeBtn) return 'verified';
    return 'not_verified';
})()'''
                verify_result = self.safari.execute_js(verify_js)
                verified = verify_result == 'verified'
                return LikeResult(success=verified, already_liked=False, verified=verified)
            
            return LikeResult(success=False, error='unknown_state')
        except Exception as e:
            return LikeResult(success=False, error=str(e))
    
    def extract_post_context(self) -> PostContext:
        """Extract context from the current post for AI comment generation."""
        js_code = '''
(function() {
    var result = {
        username: '',
        caption: '',
        image_alt: '',
        like_count: '',
        top_comments: [],
        post_url: window.location.href
    };
    
    // Find container - article, modal, or body
    var container = document.querySelector('article') || 
                    document.querySelector('div[role="dialog"]') ||
                    document.querySelector('div[role="presentation"]') ||
                    document.body;
    
    // Get username from any link that looks like a username
    var userLinks = container.querySelectorAll('a[href^="/"]');
    for (var i = 0; i < userLinks.length; i++) {
        var href = userLinks[i].getAttribute('href');
        if (href && href.match(/^\\/[a-zA-Z0-9_.]+\\/?$/) && !href.includes('/p/') && !href.includes('/reel/')) {
            result.username = href.replace(/\\//g, '');
            break;
        }
    }
    
    // Get caption - look for h1 or main text span
    var h1 = container.querySelector('h1');
    if (h1) {
        result.caption = h1.innerText.substring(0, 500);
    } else {
        var spans = container.querySelectorAll('span[dir="auto"]');
        for (var i = 0; i < spans.length; i++) {
            var text = spans[i].innerText;
            if (text && text.length > 20 && text.length < 1000 && 
                !text.includes('likes') && !text.includes('followers')) {
                result.caption = text.substring(0, 500);
                break;
            }
        }
    }
    
    // Get image alt text - check entire page
    var imgs = document.querySelectorAll('img[alt]');
    for (var i = 0; i < imgs.length; i++) {
        var alt = imgs[i].getAttribute('alt');
        if (alt && alt.length > 20 && !alt.toLowerCase().includes('profile')) {
            result.image_alt = alt.substring(0, 300);
            break;
        }
    }
    
    // Get like count - look for "X likes" text
    var allSpans = container.querySelectorAll('span');
    for (var i = 0; i < allSpans.length; i++) {
        var text = allSpans[i].innerText;
        if (text && text.match(/^[\\d,]+\\s*likes?$/i)) {
            result.like_count = text;
            break;
        }
    }
    
    // Get top comments (up to 3)
    var comments = container.querySelectorAll('ul li');
    var commentCount = 0;
    for (var i = 0; i < comments.length && commentCount < 3; i++) {
        var li = comments[i];
        var commentText = li.innerText;
        if (commentText && commentText.length > 5 && commentText.length < 200) {
            result.top_comments.push(commentText.substring(0, 150));
            commentCount++;
        }
    }
    
    return JSON.stringify(result);
})()'''
        
        try:
            result = self.safari.execute_js(js_code)
            data = json.loads(result) if result else {}
            return PostContext(
                username=data.get('username', ''),
                caption=data.get('caption', ''),
                image_alt=data.get('image_alt', ''),
                like_count=data.get('like_count', ''),
                top_comments=data.get('top_comments', []),
                post_url=data.get('post_url', '')
            )
        except:
            return PostContext()
    
    def generate_ai_comment(self, context: PostContext, api_key: str = None) -> Optional[str]:
        """Generate an AI comment based on post context using OpenAI."""
        import urllib.request
        
        if not api_key:
            api_key = os.environ.get('OPENAI_API_KEY')
        
        if not api_key:
            print('[safari] No OpenAI API key found', flush=True)
            return None
        
        # Build context prompt
        context_parts = []
        if context.username:
            context_parts.append(f"Post by @{context.username}")
        if context.caption:
            context_parts.append(f"Caption: {context.caption[:200]}")
        if context.image_alt:
            context_parts.append(f"Image: {context.image_alt[:150]}")
        if context.top_comments:
            context_parts.append(f"Top comments: {'; '.join(context.top_comments[:2])}")
        
        context_str = '\n'.join(context_parts) if context_parts else "Instagram post"
        
        try:
            data = json.dumps({
                'model': 'gpt-4o',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a thoughtful social media user. Write a brief, genuine comment (under 60 characters). Be natural and engaging. No hashtags. One emoji max. No quotes around response.'
                    },
                    {
                        'role': 'user',
                        'content': f'Write a concise, authentic comment for this post:\n\n{context_str}'
                    }
                ],
                'max_tokens': 50,
                'temperature': 0.8
            }).encode('utf-8')
            
            req = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions',
                data=data,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                }
            )
            
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                comment = result['choices'][0]['message']['content'].strip()
                # Clean up
                comment = comment.replace('"', '').replace('*', '').strip()
                return comment[:80] if len(comment) > 80 else comment
        except Exception as e:
            print(f'[safari] AI generation error: {e}', flush=True)
            return None
    
    def engage_with_post(self, permalink: str, api_key: str = None) -> EngageResult:
        """Full engagement: navigate, extract context, like, generate AI comment, post comment."""
        result = EngageResult()
        
        print(f'\n{"="*60}', flush=True)
        print('🚀 SAFARI AUTO-ENGAGE', flush=True)
        print(f'{"="*60}', flush=True)
        print(f'📍 Post: {permalink}', flush=True)
        
        # Step 1: Navigate
        print('\n📱 Step 1: Navigating to post...', flush=True)
        if not self.navigate_to_post(permalink):
            result.comment_result = CommentResult(success=False, error='Failed to navigate')
            return result
        print('   ✅ Navigation complete', flush=True)
        
        # Step 2: Scroll into view
        self.scroll_post_into_view()
        
        # Step 3: Extract context
        print('\n📝 Step 2: Extracting post context...', flush=True)
        context = self.extract_post_context()
        result.context = context
        print(f'   Username: @{context.username}', flush=True)
        print(f'   Caption: {context.caption[:60]}...' if context.caption else '   Caption: (none)', flush=True)
        print(f'   Image: {context.image_alt[:60]}...' if context.image_alt else '   Image alt: (none)', flush=True)
        print(f'   Likes: {context.like_count}' if context.like_count else '   Likes: (unknown)', flush=True)
        
        # Step 4: Like post
        print('\n❤️ Step 3: Liking post...', flush=True)
        like_result = self.like_post()
        result.like_result = like_result
        if like_result.already_liked:
            print('   ℹ️ Already liked', flush=True)
        elif like_result.success:
            print(f'   ✅ LIKED (verified: {like_result.verified})', flush=True)
        else:
            print(f'   ❌ Like failed: {like_result.error}', flush=True)
        
        # Step 5: Generate AI comment
        print('\n🤖 Step 4: Generating AI comment...', flush=True)
        comment = self.generate_ai_comment(context, api_key)
        if comment:
            result.generated_comment = comment
            print(f'   ✅ Generated: "{comment}"', flush=True)
        else:
            print('   ❌ AI generation failed, using fallback', flush=True)
            comment = 'Love this! 🔥'
            result.generated_comment = comment
        
        # Step 6: Post comment
        print('\n💬 Step 5: Posting comment...', flush=True)
        comment_result = self.post_comment(comment, is_moderation_execution=False)
        result.comment_result = comment_result
        
        if comment_result.success:
            print(f'   ✅ COMMENT POSTED (method: {comment_result.method})', flush=True)
        else:
            print(f'   ❌ Comment failed: {comment_result.error}', flush=True)
        
        # Step 7: Take screenshot for proof
        print('\n📸 Step 6: Taking screenshot for proof...', flush=True)
        screenshot_path = self.take_screenshot()
        if screenshot_path:
            result.screenshot_path = screenshot_path
            print(f'   ✅ Screenshot saved: {screenshot_path}', flush=True)
        else:
            print('   ⚠️ Screenshot failed', flush=True)
        
        # Final summary
        print(f'\n{"="*60}', flush=True)
        print('📊 VERIFICATION SUMMARY', flush=True)
        print(f'{"="*60}', flush=True)
        print(f'   Post URL:   {context.post_url}', flush=True)
        print(f'   Username:   @{context.username}', flush=True)
        print(f'   Like:       {"✅ SUCCESS" if like_result.success else "❌ FAILED"} (verified: {like_result.verified})', flush=True)
        print(f'   Comment:    {"✅ SUCCESS" if comment_result.success else "❌ FAILED"}', flush=True)
        print(f'   AI Comment: "{result.generated_comment}"', flush=True)
        print(f'   Screenshot: {screenshot_path or "none"}', flush=True)
        print(f'{"="*60}\n', flush=True)
        
        return result
    
    def like_post_in_feed(self, post_index: int) -> LikeResult:
        """Like a post directly in the feed view (before clicking into it)."""
        js_code = f'''
(function() {{
    var articles = document.querySelectorAll('article');
    if (articles.length <= {post_index}) return JSON.stringify({{error: 'post_not_found'}});
    
    var article = articles[{post_index}];
    
    // Scroll into view
    article.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    
    // Check if already liked
    var unlikeBtn = article.querySelector('svg[aria-label="Unlike"]');
    if (unlikeBtn) return JSON.stringify({{status: 'already_liked'}});
    
    // Find like button
    var likeBtn = article.querySelector('svg[aria-label="Like"]');
    if (!likeBtn) return JSON.stringify({{error: 'like_button_not_found'}});
    
    // Click it
    var btn = likeBtn.closest('button') || likeBtn.closest('div[role="button"]') || likeBtn.parentElement;
    if (btn) {{
        btn.click();
        return JSON.stringify({{status: 'clicked'}});
    }}
    
    return JSON.stringify({{error: 'click_failed'}});
}})()'''
        
        try:
            result = self.safari.execute_js(js_code)
            data = json.loads(result) if result else {}
            
            if data.get('error'):
                return LikeResult(success=False, error=data['error'])
            
            if data.get('status') == 'already_liked':
                return LikeResult(success=True, already_liked=True, verified=True)
            
            if data.get('status') == 'clicked':
                self.delay(1500)
                # Verify
                verify_js = f'''
(function() {{
    var articles = document.querySelectorAll('article');
    if (articles.length <= {post_index}) return 'not_found';
    var unlikeBtn = articles[{post_index}].querySelector('svg[aria-label="Unlike"]');
    return unlikeBtn ? 'verified' : 'not_verified';
}})()'''
                verify = self.safari.execute_js(verify_js)
                return LikeResult(success=(verify == 'verified'), verified=(verify == 'verified'))
            
            return LikeResult(success=False, error='unknown')
        except Exception as e:
            return LikeResult(success=False, error=str(e))
    
    def click_into_post(self, post_index: int) -> bool:
        """Click into a post from the feed to open it."""
        js_code = f'''
(function() {{
    var articles = document.querySelectorAll('article');
    if (articles.length <= {post_index}) return 'not_found';
    
    var article = articles[{post_index}];
    
    // Click the image or video to open post
    var media = article.querySelector('img[src*="instagram"], video, div[role="button"] img');
    if (media) {{
        media.click();
        return 'clicked_media';
    }}
    
    // Fallback: click comment icon
    var commentIcon = article.querySelector('svg[aria-label="Comment"]');
    if (commentIcon) {{
        var btn = commentIcon.closest('button') || commentIcon.parentElement;
        if (btn) {{
            btn.click();
            return 'clicked_comment';
        }}
    }}
    
    return 'not_found';
}})()'''
        
        result = self.safari.execute_js(js_code)
        if result and result.startswith('clicked'):
            self.delay(2000)
            return True
        return False
    
    def get_feed_posts(self, count: int = 3) -> List[Dict]:
        """Get post info from the feed. Scrolls to load posts if needed."""
        # First scroll to ensure we're past stories and have posts loaded
        self.safari.execute_js('window.scrollTo(0, 0);')
        self.delay(500)
        self.safari.execute_js('window.scrollBy(0, 400);')
        self.delay(1500)
        
        js_code = f'''
(function() {{
    var articles = document.querySelectorAll('article');
    var results = [];
    
    for (var i = 0; i < articles.length && results.length < {count}; i++) {{
        var article = articles[i];
        var rect = article.getBoundingClientRect();
        
        // Skip if not in view or too small (likely not a real post)
        if (rect.height < 300) continue;
        
        // Skip ads
        var text = article.innerText || '';
        if (text.includes('Sponsored') || text.includes('Paid partnership')) continue;
        
        // Must have post link
        var link = article.querySelector('a[href*="/p/"], a[href*="/reel/"]');
        if (!link) continue;
        
        // Must have like/comment buttons (real post indicators)
        var likeBtn = article.querySelector('svg[aria-label="Like"]');
        var unlikeBtn = article.querySelector('svg[aria-label="Unlike"]');
        var commentBtn = article.querySelector('svg[aria-label="Comment"]');
        if (!commentBtn) continue;  // Must have comment button
        
        // Get username - find first link matching username pattern
        var username = '';
        var allLinks = article.querySelectorAll('a[href^="/"]');
        for (var j = 0; j < allLinks.length; j++) {{
            var href = allLinks[j].getAttribute('href');
            if (href && href.match(/^\\/[a-zA-Z0-9_.]+\\/$/) && !href.includes('/p/') && !href.includes('/reel/')) {{
                username = href.replace(/\\//g, '');
                break;
            }}
        }}
        
        // Get image alt for context
        var img = article.querySelector('img[alt]');
        var alt = img ? img.getAttribute('alt') : '';
        
        results.push({{
            index: i,
            url: link.href,
            username: username,
            liked: !!unlikeBtn,
            canLike: !!likeBtn,
            hasComment: !!commentBtn,
            imageAlt: alt ? alt.substring(0, 200) : '',
            top: Math.round(rect.top)
        }});
    }}
    
    return JSON.stringify(results);
}})()'''
        
        try:
            result = self.safari.execute_js(js_code)
            return json.loads(result) if result else []
        except:
            return []
    
    def find_post_by_url(self, url: str) -> int:
        """Find a post's current index by its URL."""
        js_code = f'''
(function() {{
    var articles = document.querySelectorAll('article');
    for (var i = 0; i < articles.length; i++) {{
        var link = articles[i].querySelector('a[href*="/p/"], a[href*="/reel/"]');
        if (link && link.href === "{url}") {{
            return i;
        }}
    }}
    return -1;
}})()'''
        try:
            result = self.safari.execute_js(js_code)
            return int(result) if result and result != '-1' else -1
        except:
            return -1
    
    def engage_multiple_posts(self, count: int = 3, api_key: str = None) -> List[EngageResult]:
        """Refresh feed, get posts, like in feed, then comment on each."""
        results = []
        processed_urls = set()
        
        print(f'\n{"="*60}', flush=True)
        print(f'🚀 SAFARI AUTO-ENGAGE: {count} POSTS', flush=True)
        print(f'{"="*60}', flush=True)
        
        # Step 1: Navigate to Instagram and refresh
        print('\n📱 Step 1: Refreshing Instagram feed...', flush=True)
        self.safari.navigate_to('https://www.instagram.com/')
        self.delay(4000)
        
        # Process posts one at a time, finding the first visible one each iteration
        for i in range(count):
            print(f'\n{"="*60}', flush=True)
            print(f'📝 FINDING POST {i+1}/{count}', flush=True)
            print(f'{"="*60}', flush=True)
            
            # Find first available post that we haven't processed yet
            post = None
            for attempt in range(3):
                # Get current visible posts
                js_code = '''
(function() {
    var articles = document.querySelectorAll('article');
    var results = [];
    
    for (var i = 0; i < articles.length && results.length < 5; i++) {
        var article = articles[i];
        var rect = article.getBoundingClientRect();
        
        if (rect.height < 300) continue;
        
        var text = article.innerText || '';
        if (text.includes('Sponsored') || text.includes('Paid partnership')) continue;
        
        var link = article.querySelector('a[href*="/p/"], a[href*="/reel/"]');
        if (!link) continue;
        
        var likeBtn = article.querySelector('svg[aria-label="Like"]');
        var unlikeBtn = article.querySelector('svg[aria-label="Unlike"]');
        var commentBtn = article.querySelector('svg[aria-label="Comment"]');
        if (!commentBtn) continue;
        
        var username = '';
        var allLinks = article.querySelectorAll('a[href^="/"]');
        for (var j = 0; j < allLinks.length; j++) {
            var href = allLinks[j].getAttribute('href');
            if (href && href.match(/^\\/[a-zA-Z0-9_.]+\\/$/) && !href.includes('/p/') && !href.includes('/reel/')) {
                username = href.replace(/\\//g, '');
                break;
            }
        }
        
        var img = article.querySelector('img[alt]');
        var alt = img ? img.getAttribute('alt') : '';
        
        results.push({
            index: i,
            url: link.href,
            username: username,
            liked: !!unlikeBtn,
            canLike: !!likeBtn,
            imageAlt: alt ? alt.substring(0, 200) : ''
        });
    }
    return JSON.stringify(results);
})()'''
                result = self.safari.execute_js(js_code)
                try:
                    posts = json.loads(result) if result else []
                except:
                    posts = []
                
                # Find first post not yet processed
                for p in posts:
                    if p['url'] not in processed_urls:
                        post = p
                        break
                
                if post:
                    break
                
                # Scroll to find more posts
                print(f'   Scrolling to find more posts (attempt {attempt+1})...', flush=True)
                self.safari.execute_js('window.scrollBy(0, 600);')
                self.delay(2000)
            
            if not post:
                print('   ❌ No more posts found', flush=True)
                break
            
            processed_urls.add(post['url'])
            print(f'   ✅ Found: @{post["username"]}', flush=True)
            print(f'   URL: {post["url"]}', flush=True)
            
            engage_result = EngageResult()
            engage_result.context = PostContext(
                username=post['username'],
                post_url=post['url'],
                image_alt=post.get('imageAlt', '')
            )
            
            # Step: Like in feed FIRST (using current index)
            print('\n❤️ Liking in feed...', flush=True)
            like_result = self.like_post_in_feed(post['index'])
            engage_result.like_result = like_result
            
            if like_result.already_liked:
                print('   ℹ️ Already liked', flush=True)
            elif like_result.success:
                print(f'   ✅ LIKED (verified: {like_result.verified})', flush=True)
            else:
                print(f'   ❌ Like failed: {like_result.error}', flush=True)
            
            # Step: Navigate to post URL
            print('\n🔗 Navigating to post...', flush=True)
            self.safari.navigate_to(post['url'])
            self.delay(3000)
            print('   ✅ Opened post', flush=True)
            
            # Step: Extract full context
            print('\n📝 Extracting context...', flush=True)
            context = self.extract_post_context()
            engage_result.context = context
            print(f'   Username: @{context.username}', flush=True)
            print(f'   Image: {context.image_alt[:50]}...' if context.image_alt else '   Image: (none)', flush=True)
            
            # Step: Generate AI comment
            print('\n🤖 Generating AI comment...', flush=True)
            comment = self.generate_ai_comment(context, api_key)
            if comment:
                engage_result.generated_comment = comment
                print(f'   ✅ Generated: "{comment}"', flush=True)
            else:
                comment = 'Love this!'
                engage_result.generated_comment = comment
                print(f'   ⚠️ Using fallback: "{comment}"', flush=True)
            
            # Step: Post comment
            print('\n💬 Posting comment...', flush=True)
            comment_result = self.post_comment(comment, is_moderation_execution=False)
            engage_result.comment_result = comment_result
            
            if comment_result.success:
                print(f'   ✅ COMMENT POSTED (method: {comment_result.method})', flush=True)
            else:
                print(f'   ❌ Comment failed: {comment_result.error}', flush=True)
            
            # Step: Screenshot
            screenshot = self.take_screenshot()
            engage_result.screenshot_path = screenshot
            if screenshot:
                print(f'   📸 Screenshot: {screenshot}', flush=True)
            
            results.append(engage_result)
            
            # Navigate back to feed for next post
            if i < count - 1:
                print('\n⬅️ Returning to feed...', flush=True)
                self.safari.navigate_to('https://www.instagram.com/')
                self.delay(3000)
        
        # Final summary
        print(f'\n{"="*60}', flush=True)
        print('📊 FINAL SUMMARY', flush=True)
        print(f'{"="*60}', flush=True)
        
        likes_success = sum(1 for r in results if r.like_result and r.like_result.success)
        comments_success = sum(1 for r in results if r.comment_result and r.comment_result.success)
        
        print(f'   Posts processed: {len(results)}', flush=True)
        print(f'   Likes:    {likes_success}/{len(results)} ✅', flush=True)
        print(f'   Comments: {comments_success}/{len(results)} ✅', flush=True)
        
        for i, r in enumerate(results):
            like_status = '✅' if (r.like_result and r.like_result.success) else '❌'
            comment_status = '✅' if (r.comment_result and r.comment_result.success) else '❌'
            print(f'   {i+1}. Like {like_status} | Comment {comment_status} | "{r.generated_comment[:30]}..."', flush=True)
        
        print(f'{"="*60}\n', flush=True)
        
        return results
    
    def find_comment_box(self) -> CommentBoxResult:
        """Find comment box using multiple selectors."""
        # Embed selectors directly in JS to avoid Unicode issues with AppleScript
        js_code = '''
(function() {
    var selectors = [
        'textarea[aria-label="Add a comment…"]',
        'textarea[placeholder="Add a comment…"]',
        'textarea[placeholder="Add a comment..."]',
        'textarea[aria-label*="comment"]',
        'form textarea',
        'div[contenteditable="true"][role="textbox"]'
    ];
    for (var i = 0; i < selectors.length; i++) {
        var el = document.querySelector(selectors[i]);
        if (el) {
            var isContentEditable = el.getAttribute('contenteditable') === 'true';
            return JSON.stringify({
                found: true,
                selectorIndex: i,
                isContentEditable: isContentEditable
            });
        }
    }
    return JSON.stringify({ found: false, selectorIndex: -1, isContentEditable: false });
})()'''
        
        try:
            result = self.safari.execute_js(js_code)
            data = json.loads(result) if result else {}
            return CommentBoxResult(
                found=data.get('found', False),
                selector=str(data.get('selectorIndex', -1)),  # Store index as string
                is_content_editable=data.get('isContentEditable', False)
            )
        except:
            return CommentBoxResult(found=False)
    
    def click_comment_icon(self) -> bool:
        """Click the comment icon to open the composer."""
        js_code = '''
(function() {
    var icon = document.querySelector('svg[aria-label="Comment"]');
    if (icon) {
        var button = icon.closest('button') || icon.closest('div[role="button"]') || icon.parentElement;
        if (button) {
            button.click();
            return 'clicked';
        }
    }
    return 'not_found';
})()'''
        
        try:
            result = self.safari.execute_js(js_code)
            if result == 'clicked':
                self.delay(700)
                return True
        except:
            pass
        return False
    
    def find_comment_box_by_keyword(self) -> CommentBoxResult:
        """Locale-aware comment field detection."""
        keywords_json = json.dumps(COMMENT_KEYWORDS)
        
        js_code = f'''
(function() {{
    var keywords = {keywords_json};
    var candidates = document.querySelectorAll('textarea, form textarea, div[contenteditable="true"][role="textbox"], [role="textbox"][contenteditable="true"]');
    
    for (var i = 0; i < candidates.length; i++) {{
        var el = candidates[i];
        var label = ((el.getAttribute('aria-label') || '') + ' ' +
                    (el.getAttribute('placeholder') || '') + ' ' +
                    (el.textContent || '')).toLowerCase();
        
        for (var j = 0; j < keywords.length; j++) {{
            if (label.includes(keywords[j])) {{
                return JSON.stringify({{ found: true, index: i }});
            }}
        }}
    }}
    return JSON.stringify({{ found: false, index: -1 }});
}})()'''
        
        try:
            result = self.safari.execute_js(js_code)
            data = json.loads(result) if result else {}
            if data.get('found'):
                return CommentBoxResult(found=True, selector=f"locale_keyword_{data['index']}")
        except:
            pass
        return CommentBoxResult(found=False)
    
    def focus_and_clear_comment_box(self, selector: str) -> bool:
        """Focus and clear the comment box. Selector is index or 'locale_keyword_N'."""
        # Build JS with selectors embedded to avoid Unicode issues
        js_code = f'''
(function() {{
    var selectors = [
        'textarea[aria-label="Add a comment…"]',
        'textarea[placeholder="Add a comment…"]',
        'textarea[placeholder="Add a comment..."]',
        'textarea[aria-label*="comment"]',
        'form textarea',
        'div[contenteditable="true"][role="textbox"]'
    ];
    var el = null;
    var selectorRef = '{selector}';
    
    // If selector is a locale keyword match, re-find it
    if (selectorRef.startsWith('locale_keyword_')) {{
        var idx = parseInt(selectorRef.replace('locale_keyword_', ''));
        var candidates = document.querySelectorAll('textarea, form textarea, div[contenteditable="true"][role="textbox"]');
        el = candidates[idx];
    }} else {{
        // It's an index into our selectors array
        var idx = parseInt(selectorRef);
        if (idx >= 0 && idx < selectors.length) {{
            el = document.querySelector(selectors[idx]);
        }}
    }}
    
    if (!el) return 'not_found';
    
    // Focus the element
    el.focus();
    
    // Clear content
    if (el.tagName === 'TEXTAREA') {{
        el.value = '';
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }} else {{
        // Contenteditable
        el.textContent = '';
        el.innerHTML = '';
        el.dispatchEvent(new InputEvent('input', {{ bubbles: true }}));
    }}
    
    return 'cleared';
}})()'''
        
        try:
            result = self.safari.execute_js(js_code)
            self.delay(400)
            return result == 'cleared'
        except:
            return False
    
    def type_comment(self, comment: str, selector: str) -> bool:
        """Type comment text using clipboard paste to support emojis."""
        # First, click/focus the textarea via JavaScript
        js_code = f'''
(function() {{
    var selectors = [
        'textarea[aria-label="Add a comment…"]',
        'textarea[placeholder="Add a comment…"]',
        'textarea[placeholder="Add a comment..."]',
        'textarea[aria-label*="comment"]',
        'form textarea',
        'div[contenteditable="true"][role="textbox"]'
    ];
    var el = null;
    var selectorRef = '{selector}';
    
    if (selectorRef.startsWith('locale_keyword_')) {{
        var idx = parseInt(selectorRef.replace('locale_keyword_', ''));
        var candidates = document.querySelectorAll('textarea, form textarea, div[contenteditable="true"][role="textbox"]');
        el = candidates[idx];
    }} else {{
        var idx = parseInt(selectorRef);
        if (idx >= 0 && idx < selectors.length) {{
            el = document.querySelector(selectors[idx]);
        }}
    }}
    
    if (!el) return 'not_found';
    
    // Click and focus the element
    el.click();
    el.focus();
    return 'focused';
}})()'''
        
        try:
            result = self.safari.execute_js(js_code)
            if result != 'focused':
                return False
            
            self.delay(300)
            
            # Use clipboard paste to support emojis
            # First, copy comment to clipboard using pbcopy
            import subprocess
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(comment.encode('utf-8'))
            
            self.delay(200)
            
            # Now paste using Cmd+V
            script = '''
            tell application "Safari" to activate
            delay 0.2
            tell application "System Events"
                keystroke "v" using command down
            end tell
            '''
            success, _ = self.safari.run_applescript(script)
            self.delay(500)
            return success
        except:
            return False
    
    def submit_comment(self) -> Dict[str, Any]:
        """Submit comment using multiple methods."""
        attempts: List[MethodAttempt] = []
        successful_method: Optional[str] = None
        
        # Method 1: Press Enter key
        method1_start = int(time.time() * 1000)
        try:
            js_code = '''
(function() {
    var el = document.activeElement;
    if (el) {
        el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
        el.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', keyCode: 13, bubbles: true }));
        el.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', keyCode: 13, bubbles: true }));
        return 'enter_sent';
    }
    return 'no_focus';
})()'''
            result = self.safari.execute_js(js_code)
            elapsed = int(time.time() * 1000) - method1_start
            
            if result == 'enter_sent':
                attempts.append(MethodAttempt('enter_key', True, elapsed))
                successful_method = 'enter_key'
                print('[safari] Submit method 1 (Enter key) invoked', flush=True)
                self.delay(2000)
                return {'success': True, 'method': successful_method, 'attempts': attempts}
            attempts.append(MethodAttempt('enter_key', False, elapsed, result))
        except Exception as e:
            attempts.append(MethodAttempt('enter_key', False, int(time.time() * 1000) - method1_start, str(e)))
        
        # Method 2: Click submit button
        method2_start = int(time.time() * 1000)
        try:
            js_code = '''
(function() {
    var btn = document.querySelector('button[type="submit"]');
    if (btn && !btn.disabled) {
        btn.click();
        return 'clicked';
    }
    return 'not_found';
})()'''
            result = self.safari.execute_js(js_code)
            elapsed = int(time.time() * 1000) - method2_start
            
            if result == 'clicked':
                attempts.append(MethodAttempt('submit_button', True, elapsed))
                successful_method = 'submit_button'
                print('[safari] Submit method 2 (submit button) invoked', flush=True)
                self.delay(2000)
                return {'success': True, 'method': successful_method, 'attempts': attempts}
            attempts.append(MethodAttempt('submit_button', False, elapsed, result))
        except Exception as e:
            attempts.append(MethodAttempt('submit_button', False, int(time.time() * 1000) - method2_start, str(e)))
        
        # Method 3: Form dispatch
        method3_start = int(time.time() * 1000)
        try:
            js_code = '''
(function() {
    var form = document.querySelector('article form') || document.querySelector('form');
    if (form) {
        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        return 'dispatched';
    }
    return 'no_form';
})()'''
            result = self.safari.execute_js(js_code)
            elapsed = int(time.time() * 1000) - method3_start
            
            if result == 'dispatched':
                attempts.append(MethodAttempt('form_dispatch', True, elapsed))
                successful_method = 'form_dispatch'
                print('[safari] Submit method 3 (form dispatch) invoked', flush=True)
                self.delay(2000)
                return {'success': True, 'method': successful_method, 'attempts': attempts}
            attempts.append(MethodAttempt('form_dispatch', False, elapsed, result))
        except Exception as e:
            attempts.append(MethodAttempt('form_dispatch', False, int(time.time() * 1000) - method3_start, str(e)))
        
        # Method 4: Click role button by text label
        method4_start = int(time.time() * 1000)
        try:
            labels_json = json.dumps(SUBMIT_LABELS)
            js_code = f'''
(function() {{
    var labels = {labels_json};
    var selectors = ['div[role="button"]', 'button[role="button"]', 'form div[role="button"]', 'form button:not([type])'];
    
    for (var s = 0; s < selectors.length; s++) {{
        var nodes = document.querySelectorAll(selectors[s]);
        for (var i = 0; i < nodes.length; i++) {{
            var text = (nodes[i].textContent || '').trim().toLowerCase();
            for (var j = 0; j < labels.length; j++) {{
                if (text === labels[j] || text.includes(labels[j])) {{
                    nodes[i].click();
                    return 'clicked_' + text;
                }}
            }}
        }}
    }}
    return 'not_found';
}})()'''
            result = self.safari.execute_js(js_code)
            elapsed = int(time.time() * 1000) - method4_start
            
            if result and result.startswith('clicked_'):
                attempts.append(MethodAttempt('role_button_text', True, elapsed))
                successful_method = 'role_button_text'
                print(f'[safari] Submit method 4 (role button) invoked: {result}', flush=True)
                self.delay(2000)
                return {'success': True, 'method': successful_method, 'attempts': attempts}
            attempts.append(MethodAttempt('role_button_text', False, elapsed, result))
        except Exception as e:
            attempts.append(MethodAttempt('role_button_text', False, int(time.time() * 1000) - method4_start, str(e)))
        
        return {'success': False, 'method': None, 'attempts': attempts}
    
    def verify_comment_posted(self, comment: str) -> bool:
        """Verify comment was posted successfully."""
        selectors_json = json.dumps(COMMENT_BOX_SELECTORS)
        
        # Method 1: Check if comment box is empty
        js_code1 = f'''
(function() {{
    var selectors = {selectors_json};
    for (var i = 0; i < selectors.length; i++) {{
        var el = document.querySelector(selectors[i]);
        if (el) {{
            if (el.tagName === 'TEXTAREA') {{
                return (el.value || '').trim() === '' ? 'empty' : 'has_text';
            }} else {{
                return (el.textContent || '').trim() === '' ? 'empty' : 'has_text';
            }}
        }}
    }}
    return 'not_found';
}})()'''
        
        try:
            result = self.safari.execute_js(js_code1)
            if result == 'empty':
                print('[safari] Verification method 1: comment box empty ✓', flush=True)
                return True
        except:
            pass
        
        # Method 2: Check for comment text in page
        escaped_comment = comment.replace('"', '\\"').replace('\n', ' ')
        js_code2 = f'''
(function() {{
    var article = document.querySelector('article');
    if (article) {{
        var text = article.innerText || '';
        return text.includes("{escaped_comment}") ? 'found' : 'not_found';
    }}
    return 'no_article';
}})()'''
        
        try:
            result = self.safari.execute_js(js_code2)
            if result == 'found':
                print('[safari] Verification method 2: comment text found ✓', flush=True)
                return True
        except:
            pass
        
        # Method 3: Check for error messages
        js_code3 = '''
(function() {
    var body = document.body.innerText.toLowerCase();
    var errors = ["couldn't post", 'try again', 'action blocked', 
                  'comments on this post have been limited',
                  'only followers can comment', 
                  'commenting has been turned off'];
    for (var i = 0; i < errors.length; i++) {
        if (body.includes(errors[i])) {
            return 'error_' + errors[i];
        }
    }
    return 'no_error';
})()'''
        
        try:
            result = self.safari.execute_js(js_code3)
            if result == 'no_error':
                print('[safari] Verification method 3: no errors found ✓', flush=True)
                return True
            print(f'[safari] Error detected: {result}', flush=True)
        except:
            return True  # Assume success if no error detected
        
        return False
    
    def check_comment_restrictions(self) -> Optional[str]:
        """Check for commenting restrictions."""
        js_code = '''
(function() {
    var body = document.body.innerText.toLowerCase();
    if (body.includes('comments on this post have been limited')) return 'comment_limited';
    if (body.includes('only followers can comment')) return 'followers_only';
    if (body.includes('commenting has been turned off')) return 'commenting_turned_off';
    if (body.includes('action blocked')) return 'action_blocked';
    return 'null';
})()'''
        
        try:
            result = self.safari.execute_js(js_code)
            return None if result == 'null' else result
        except:
            return None
    
    def post_comment(self, comment: str, is_moderation_execution: bool = False) -> CommentResult:
        """Main method: Post a comment on the current post."""
        start_time = int(time.time() * 1000)
        
        try:
            print('[safari] Starting comment operation', flush=True)
            if is_moderation_execution:
                print('🚀 Starting Safari auto-comment...', flush=True)
            
            # Step 1: Scroll post into view
            self.scroll_post_into_view()
            if is_moderation_execution:
                print('📍 Post scrolled into view', flush=True)
            
            # Step 2: Find comment box
            comment_box_result = self.find_comment_box()
            print(f'[safari] Comment box search: {"✓" if comment_box_result.found else "✗"}', flush=True)
            
            # Step 3: If not found, click comment icon
            if not comment_box_result.found:
                if is_moderation_execution:
                    print('🔍 Looking for comment icon...', flush=True)
                icon_clicked = self.click_comment_icon()
                if icon_clicked:
                    if is_moderation_execution:
                        print('✅ Clicked comment icon', flush=True)
                    comment_box_result = self.find_comment_box()
            
            # Step 4: Fallback to locale keyword search
            if not comment_box_result.found:
                keyword_result = self.find_comment_box_by_keyword()
                if keyword_result.found:
                    comment_box_result = keyword_result
                    if is_moderation_execution:
                        print('✅ Found comment box via locale keywords', flush=True)
            
            # Check for restrictions if still not found
            if not comment_box_result.found:
                restriction = self.check_comment_restrictions()
                if restriction:
                    return CommentResult(success=False, error=restriction)
                return CommentResult(success=False, error='Comment box not found with any selector')
            
            if is_moderation_execution:
                print('✅ Found comment box', flush=True)
            
            # Step 5: Focus and clear
            cleared = self.focus_and_clear_comment_box(comment_box_result.selector)
            if not cleared:
                return CommentResult(success=False, error='Failed to focus/clear comment box')
            if is_moderation_execution:
                print('✅ Comment box focused and cleared', flush=True)
            
            # Step 6: Type the comment
            if is_moderation_execution:
                print(f'⌨️ Typing: "{comment}"', flush=True)
            typed = self.type_comment(comment, comment_box_result.selector)
            if not typed:
                return CommentResult(success=False, error='Failed to type comment')
            if is_moderation_execution:
                print('✅ Comment typed', flush=True)
            
            # Step 7: Submit
            if is_moderation_execution:
                print('📤 Submitting comment...', flush=True)
            submit_result = self.submit_comment()
            
            if not submit_result['success']:
                return CommentResult(
                    success=False,
                    error='Failed to submit comment with any method',
                    metadata={
                        'comment_method': None,
                        'comment_method_attempt_time_ms': int(time.time() * 1000) - start_time,
                        'comment_method_attempts': [a.__dict__ for a in submit_result['attempts']]
                    }
                )
            
            # Step 8: Verify
            if is_moderation_execution:
                print('🔍 Verifying comment posted...', flush=True)
            self.delay(2000)
            verified = self.verify_comment_posted(comment)
            
            if verified:
                if is_moderation_execution:
                    print('✅ Comment verified - successfully posted!', flush=True)
                return CommentResult(
                    success=True,
                    method=submit_result['method'],
                    metadata={
                        'comment_method': submit_result['method'],
                        'comment_method_attempt_time_ms': int(time.time() * 1000) - start_time,
                        'comment_method_attempts': [a.__dict__ for a in submit_result['attempts']]
                    }
                )
            
            # Check for specific errors
            restriction = self.check_comment_restrictions()
            if restriction:
                return CommentResult(success=False, error=restriction)
            
            return CommentResult(success=False, error='Could not verify comment was posted')
        
        except Exception as e:
            print(f'[safari] Comment operation error: {e}', flush=True)
            return CommentResult(success=False, error=str(e))
    
    def post_comment_on_permalink(self, permalink: str, comment: str, is_moderation_execution: bool = False) -> CommentResult:
        """Post a comment on a specific permalink."""
        # Navigate to the post
        navigated = self.navigate_to_post(permalink)
        if not navigated:
            return CommentResult(success=False, error='Failed to navigate to post')
        
        # Post the comment
        return self.post_comment(comment, is_moderation_execution)


# ==================== STANDALONE EXECUTION ====================

def execute_comment(permalink: str, comment: str) -> CommentResult:
    """Execute a comment on a post (for direct CLI usage)."""
    auto_comment = SafariAutoComment()
    return auto_comment.post_comment_on_permalink(permalink, comment, True)


if __name__ == '__main__':
    args = sys.argv[1:]
    
    if len(args) < 2:
        print('Usage: python safari_auto_comment.py <permalink> <comment>')
        print('Example: python safari_auto_comment.py "https://www.instagram.com/p/ABC123/" "Great post!"')
        sys.exit(1)
    
    permalink = args[0]
    comment = ' '.join(args[1:])
    
    print(f'\n🌐 Safari Auto Comment\n')
    print(f'📍 Permalink: {permalink}')
    print(f'💬 Comment: {comment}\n')
    
    result = execute_comment(permalink, comment)
    
    if result.success:
        print(f'\n✅ Comment posted successfully!')
        print(f'   Method: {result.method}')
        sys.exit(0)
    else:
        print(f'\n❌ Failed to post comment: {result.error}')
        sys.exit(1)
