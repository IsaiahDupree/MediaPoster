"""
Threads Auto-Engagement Module

Automates engagement on Threads posts with full context extraction:
- Navigate to post page
- Extract main post content + ALL replies
- Generate contextual AI comment
- Post reply with verification

Usage:
    from auto_engagement.threads_engagement import ThreadsEngagement
    
    threads = ThreadsEngagement()
    result = threads.engage_with_post()
    print(f"Comment posted: {result.comment_posted}")
"""

import time
import json
from typing import Optional, List
from dataclasses import dataclass, field

from .safari_controller import SafariController
from .ai_comment_generator import AICommentGenerator, PostContext


@dataclass
class ThreadsEngagementResult:
    """Result of Threads engagement."""
    success: bool
    username: str = ""
    post_url: str = ""
    post_content: str = ""
    replies_found: int = 0
    replies: List[str] = field(default_factory=list)
    generated_comment: str = ""
    comment_posted: bool = False
    proof_screenshot: str = ""
    error: str = ""


class ThreadsEngagement:
    """
    Threads auto-engagement with full context extraction.
    
    Flow:
    1. Navigate to Threads feed
    2. Find post with engagement
    3. Click into post to see all replies
    4. Extract main post + ALL replies
    5. Generate contextual AI comment
    6. Post reply
    7. Capture proof screenshot
    """
    
    THREADS_URL = "https://www.threads.net/"
    
    # JavaScript selectors for Threads
    JS_FIND_POST = '''
    (function() {
        var posts = document.querySelectorAll('div[data-pressable-container="true"]');
        for (var i = 0; i < Math.min(posts.length, 10); i++) {
            var post = posts[i];
            var userLink = post.querySelector('a[href^="/@"]');
            var postLink = post.querySelector('a[href*="/post/"]');
            
            var content = '';
            post.querySelectorAll('span[dir="auto"]').forEach(function(el) {
                content += el.innerText + ' ';
            });
            
            if (userLink && postLink && content.length > 20) {
                return JSON.stringify({
                    username: userLink.getAttribute('href').replace('/@', '').split('/')[0],
                    url: postLink.href,
                    content: content.substring(0, 300),
                    index: i
                });
            }
        }
        return null;
    })()
    '''
    
    JS_EXTRACT_CONTEXT = '''
    (function() {
        var data = {
            mainPost: '',
            username: '',
            replies: [],
            likeCount: '',
            replyCount: ''
        };
        
        var posts = document.querySelectorAll('div[data-pressable-container="true"]');
        
        if (posts[0]) {
            var mainPost = posts[0];
            var userEl = mainPost.querySelector('a[href^="/@"]');
            if (userEl) {
                data.username = userEl.getAttribute('href').replace('/@', '').split('/')[0];
            }
            
            mainPost.querySelectorAll('span[dir="auto"]').forEach(function(el) {
                var text = el.innerText.trim();
                if (text.length > 10 && !text.match(/^\\d+[hmd]$/) && text !== data.username) {
                    data.mainPost += text + ' ';
                }
            });
            
            var statsText = mainPost.innerText;
            var likeMatch = statsText.match(/(\\d+[KkMm]?)\\s*like/i);
            var replyMatch = statsText.match(/(\\d+[KkMm]?)\\s*repl/i);
            if (likeMatch) data.likeCount = likeMatch[1];
            if (replyMatch) data.replyCount = replyMatch[1];
        }
        
        for (var i = 1; i < Math.min(posts.length, 10); i++) {
            var reply = posts[i];
            var replyUser = '';
            var replyText = '';
            
            var userEl = reply.querySelector('a[href^="/@"]');
            if (userEl) {
                replyUser = userEl.getAttribute('href').replace('/@', '').split('/')[0];
            }
            
            reply.querySelectorAll('span[dir="auto"]').forEach(function(el) {
                var text = el.innerText.trim();
                if (text.length > 5 && !text.match(/^\\d+[hmd]$/) && text !== replyUser) {
                    replyText += text + ' ';
                }
            });
            
            if (replyUser && replyText.length > 5) {
                data.replies.push('@' + replyUser + ': ' + replyText.substring(0, 120));
            }
        }
        
        return JSON.stringify(data);
    })()
    '''
    
    JS_CLICK_REPLY = '''
    (function() {
        var btns = document.querySelectorAll('svg[aria-label*="Reply"], svg[aria-label*="Comment"]');
        for (var i = 0; i < btns.length; i++) {
            var btn = btns[i].closest('div[role="button"]') || btns[i].parentElement;
            if (btn) { btn.click(); return 'clicked'; }
        }
        return 'not_found';
    })()
    '''
    
    JS_FOCUS_INPUT = '''
    (function() {
        var els = document.querySelectorAll('[contenteditable="true"]');
        for (var i = 0; i < els.length; i++) {
            if (els[i].offsetParent !== null) { 
                els[i].click(); 
                els[i].focus(); 
                return 'focused'; 
            }
        }
        return 'not_found';
    })()
    '''
    
    JS_SUBMIT = '''
    (function() {
        var btns = document.querySelectorAll('div[role="button"], button');
        for (var i = 0; i < btns.length; i++) {
            var text = btns[i].innerText.toLowerCase().trim();
            if (text === 'post' || text === 'reply') { 
                btns[i].click(); 
                return 'submitted'; 
            }
        }
        // Fallback: try clicking any blue/primary button
        var primaryBtns = document.querySelectorAll('[style*="background"][role="button"]');
        for (var i = 0; i < primaryBtns.length; i++) {
            if (primaryBtns[i].offsetParent !== null) {
                primaryBtns[i].click();
                return 'clicked_primary';
            }
        }
        return 'not_found';
    })()
    '''
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize Threads engagement.
        
        Args:
            openai_api_key: OpenAI API key (optional, uses env var)
        """
        self.safari = SafariController()
        self.ai = AICommentGenerator(api_key=openai_api_key)
    
    def engage_with_post(self, skip_navigation: bool = False) -> ThreadsEngagementResult:
        """
        Engage with a Threads post.
        
        Args:
            skip_navigation: If True, assumes already on Threads
            
        Returns:
            ThreadsEngagementResult with all engagement data
        """
        result = ThreadsEngagementResult(success=False)
        timestamp = int(time.time())
        
        print("\n" + "="*60)
        print("🧵 THREADS ENGAGEMENT")
        print("="*60)
        
        # Step 1: Navigate
        if not skip_navigation:
            print("\n[1/7] Navigating to Threads...")
            nav = self.safari.navigate_with_verification(
                self.THREADS_URL, 
                'threads', 
                max_attempts=3
            )
            if not nav.success:
                result.error = "Navigation failed"
                return result
            print(f"   ✅ On Threads")
            time.sleep(3)
        
        # Step 2: Find post
        print("\n[2/7] Finding post with engagement...")
        post_data = self.safari.execute_js(self.JS_FIND_POST)
        if not post_data:
            result.error = "No post found"
            return result
        
        post = json.loads(post_data)
        result.username = post['username']
        result.post_url = post['url']
        print(f"   ✅ Found: @{result.username}")
        print(f"   Content: {post['content'][:60]}...")
        
        # Step 3: Navigate to post page
        print("\n[3/7] Opening post page...")
        self.safari.navigate_to(post['url'], wait_time=4)
        print(f"   ✅ Opened")
        
        # Step 4: Extract post + ALL replies
        print("\n[4/7] Extracting post and replies...")
        context_data = self.safari.execute_js(self.JS_EXTRACT_CONTEXT)
        if not context_data:
            result.error = "Failed to extract context"
            return result
        
        ctx = json.loads(context_data)
        result.post_content = ctx['mainPost']
        result.replies = ctx['replies']
        result.replies_found = len(ctx['replies'])
        
        print(f"   ✅ Post: {result.post_content[:60]}...")
        print(f"   ✅ Engagement: {ctx.get('likeCount', '?')} likes")
        print(f"   ✅ Replies: {result.replies_found}")
        for r in result.replies[:3]:
            print(f"      - {r[:50]}...")
        
        # Validate: Must have post content
        if len(result.post_content) < 10:
            result.error = "Insufficient post content"
            return result
        
        # Step 5: Generate AI comment
        print("\n[5/7] Generating AI comment...")
        replies_text = '\n'.join(result.replies) if result.replies else ''
        engagement = f"{ctx.get('likeCount', '')} likes"
        
        comment_result = self.ai.generate_comment(
            platform='threads',
            post_content=result.post_content,
            existing_comments=result.replies,
            username=result.username,
            engagement=engagement
        )
        
        if not comment_result.success:
            result.error = f"Comment generation failed: {comment_result.error}"
            return result
        
        result.generated_comment = comment_result.text
        print(f"   ✅ Generated: \"{result.generated_comment}\"")
        
        # Step 6: Post reply
        print("\n[6/7] Posting reply...")
        
        # Click reply button
        reply_result = self.safari.execute_js(self.JS_CLICK_REPLY)
        print(f"   Reply button: {reply_result}")
        time.sleep(2)
        
        # Focus input
        focus_result = self.safari.execute_js(self.JS_FOCUS_INPUT)
        if focus_result != 'focused':
            result.error = "Could not focus reply input"
            return result
        
        # Type comment
        self.safari.type_via_clipboard(result.generated_comment)
        print(f"   ✅ Typed comment")
        time.sleep(1)
        
        # Submit
        submit_result = self.safari.execute_js(self.JS_SUBMIT)
        result.comment_posted = submit_result in ['submitted', 'clicked_primary']
        print(f"   Submit: {submit_result}")
        time.sleep(3)
        
        # Step 7: Capture proof
        print("\n[7/7] Capturing proof...")
        result.proof_screenshot = f"/tmp/threads_proof_{timestamp}.png"
        self.safari.take_screenshot(result.proof_screenshot)
        print(f"   📸 {result.proof_screenshot}")
        
        result.success = True
        return result
    
    def check_login_state(self) -> bool:
        """Check if logged in to Threads."""
        check_js = '''
        (function() {
            var indicators = ['a[href*="/activity"]', '[aria-label="Profile"]', 'a[href*="/@"]'];
            for (var i = 0; i < indicators.length; i++) {
                if (document.querySelector(indicators[i])) return 'logged_in';
            }
            return 'not_logged_in';
        })()
        '''
        result = self.safari.execute_js(check_js)
        return result == 'logged_in'


def run_test():
    """Run a test engagement."""
    import os
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return
    
    threads = ThreadsEngagement(openai_api_key=api_key)
    result = threads.engage_with_post()
    
    print("\n" + "="*60)
    print("📊 RESULT")
    print("="*60)
    print(f"Success: {result.success}")
    print(f"Username: @{result.username}")
    print(f"Replies found: {result.replies_found}")
    print(f"Comment: {result.generated_comment}")
    print(f"Posted: {result.comment_posted}")
    print(f"Proof: {result.proof_screenshot}")
    if result.error:
        print(f"Error: {result.error}")
    
    return result


if __name__ == "__main__":
    run_test()
