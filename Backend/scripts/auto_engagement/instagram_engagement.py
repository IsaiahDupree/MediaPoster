"""
Instagram Auto-Engagement Module

Automates engagement on Instagram posts with full context extraction:
- Like post in feed
- Navigate to post page
- Extract caption + ALL comments
- Generate contextual AI comment
- Post comment with verification

Usage:
    from auto_engagement.instagram_engagement import InstagramEngagement
    
    instagram = InstagramEngagement()
    result = instagram.engage_with_post()
    print(f"Comment posted: {result.comment_posted}")
"""

import time
import json
from typing import Optional, List
from dataclasses import dataclass, field

from .safari_controller import SafariController
from .ai_comment_generator import AICommentGenerator


@dataclass
class InstagramEngagementResult:
    """Result of Instagram engagement."""
    success: bool
    username: str = ""
    post_url: str = ""
    caption: str = ""
    comments_found: int = 0
    comments: List[str] = field(default_factory=list)
    liked: bool = False
    generated_comment: str = ""
    comment_posted: bool = False
    proof_screenshot: str = ""
    error: str = ""


class InstagramEngagement:
    """
    Instagram auto-engagement with full context extraction.
    
    Flow:
    1. Navigate to Instagram feed
    2. Find post in feed
    3. Like post (if not already liked)
    4. Navigate to post page
    5. Expand and extract caption + ALL comments
    6. Generate contextual AI comment
    7. Post comment
    8. Capture proof screenshot
    """
    
    INSTAGRAM_URL = "https://www.instagram.com/"
    
    JS_FIND_POST = '''
    (function() {
        var articles = document.querySelectorAll('article');
        for (var i = 0; i < articles.length; i++) {
            var art = articles[i];
            if (art.getBoundingClientRect().height < 300) continue;
            
            var username = '';
            var links = art.querySelectorAll('a[href^="/"]');
            for (var j = 0; j < links.length; j++) {
                var href = links[j].getAttribute('href');
                if (href && href.match(/^\\/[a-zA-Z0-9_.]+\\/$/) && !href.includes('/p/')) {
                    username = href.replace(/\\//g, '');
                    break;
                }
            }
            
            var postLink = art.querySelector('a[href*="/p/"]');
            var likeBtn = art.querySelector('svg[aria-label="Like"]');
            
            if (username && postLink) {
                art.scrollIntoView({block: 'center'});
                return JSON.stringify({
                    username: username, 
                    url: postLink.href, 
                    canLike: !!likeBtn, 
                    index: i
                });
            }
        }
        return null;
    })()
    '''
    
    JS_LIKE_POST = '''
    (function() {
        var art = document.querySelector('article');
        if (art) {
            var btn = art.querySelector('svg[aria-label="Like"]');
            if (btn) {
                var b = btn.closest('button');
                if (b) { b.click(); return 'liked'; }
            }
            // Check if already liked
            if (art.querySelector('svg[aria-label="Unlike"]')) {
                return 'already_liked';
            }
        }
        return 'not_found';
    })()
    '''
    
    JS_EXPAND_COMMENTS = '''
    (function() {
        var links = document.querySelectorAll('span, a, div[role="button"]');
        for (var i = 0; i < links.length; i++) {
            var text = links[i].innerText.toLowerCase();
            if (text.includes('view all') && text.includes('comment')) {
                links[i].click();
                return 'expanded: ' + links[i].innerText;
            }
        }
        return 'no_expand_needed';
    })()
    '''
    
    JS_EXTRACT_CONTEXT = '''
    (function() {
        var data = {caption: '', comments: [], commentCount: 0};
        
        // Get caption
        var article = document.querySelector('article') || document.body;
        var spans = article.querySelectorAll('span[dir="auto"], span');
        for (var i = 0; i < spans.length; i++) {
            var text = spans[i].innerText.trim();
            if (text.length > 30 && text.length < 2000 && !text.includes('View all') && !text.includes('likes')) {
                data.caption = text.substring(0, 400);
                break;
            }
        }
        
        // Get comment count
        var countMatch = document.body.innerText.match(/(\\d+)\\s*comment/i);
        if (countMatch) data.commentCount = parseInt(countMatch[1]);
        
        // Extract comments using username link pattern
        var seenComments = new Set();
        var allLinks = document.querySelectorAll('a[href^="/"]');
        
        for (var l = 0; l < allLinks.length; l++) {
            var link = allLinks[l];
            var href = link.getAttribute('href');
            
            if (href && href.match(/^\\/[a-zA-Z0-9_.]+\\/$/) && 
                !href.includes('/p/') && !href.includes('/explore/') &&
                !href.includes('/reels/') && !href.includes('/stories/')) {
                
                var username = href.replace(/\\//g, '');
                var container = link.closest('div[style]') || link.closest('li') || link.parentElement.parentElement;
                
                if (container) {
                    var textParts = [];
                    container.querySelectorAll('span').forEach(function(span) {
                        var txt = span.innerText.trim();
                        if (txt.length > 3 && txt.length < 300 && 
                            txt !== username && !txt.match(/^\\d+[wdhm]$/) &&
                            !txt.includes('Reply') && !txt.includes('View') &&
                            !txt.includes('like') && !txt.includes('Edited')) {
                            textParts.push(txt);
                        }
                    });
                    
                    if (textParts.length > 0) {
                        var commentText = textParts.join(' ').substring(0, 120);
                        var entry = '@' + username + ': ' + commentText;
                        if (!seenComments.has(entry) && data.comments.length < 10) {
                            seenComments.add(entry);
                            data.comments.push(entry);
                        }
                    }
                }
            }
        }
        
        return JSON.stringify(data);
    })()
    '''
    
    JS_FOCUS_COMMENT = '''
    (function() {
        var selectors = [
            'textarea[aria-label*="comment" i]',
            'textarea[placeholder*="comment" i]',
            'form textarea',
            'textarea'
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
    
    JS_SUBMIT_COMMENT = '''
    (function() {
        var el = document.activeElement;
        if (el && el.tagName === 'TEXTAREA') {
            el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));
            el.dispatchEvent(new KeyboardEvent('keypress', {key: 'Enter', keyCode: 13, bubbles: true}));
            return 'submitted';
        }
        return 'failed';
    })()
    '''
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize Instagram engagement.
        
        Args:
            openai_api_key: OpenAI API key (optional, uses env var)
        """
        self.safari = SafariController()
        self.ai = AICommentGenerator(api_key=openai_api_key)
    
    def engage_with_post(self, skip_navigation: bool = False) -> InstagramEngagementResult:
        """
        Engage with an Instagram post.
        
        Args:
            skip_navigation: If True, assumes already on Instagram
            
        Returns:
            InstagramEngagementResult with all engagement data
        """
        result = InstagramEngagementResult(success=False)
        timestamp = int(time.time())
        
        print("\n" + "="*60)
        print("📸 INSTAGRAM ENGAGEMENT")
        print("="*60)
        
        # Step 1: Navigate
        if not skip_navigation:
            print("\n[1/8] Navigating to Instagram...")
            nav = self.safari.navigate_with_verification(
                self.INSTAGRAM_URL,
                'instagram',
                max_attempts=3
            )
            if not nav.success:
                result.error = "Navigation failed"
                return result
            print(f"   ✅ On Instagram")
            time.sleep(4)
            
            # Scroll to load posts
            self.safari.scroll_down(400)
            time.sleep(2)
        
        # Step 2: Find post
        print("\n[2/8] Finding post in feed...")
        post_data = self.safari.execute_js(self.JS_FIND_POST)
        if not post_data:
            result.error = "No post found"
            return result
        
        post = json.loads(post_data)
        result.username = post['username']
        result.post_url = post['url']
        print(f"   ✅ Found: @{result.username}")
        
        # Step 3: Like in feed
        print("\n[3/8] Liking post...")
        if post.get('canLike'):
            like_result = self.safari.execute_js(self.JS_LIKE_POST)
            result.liked = like_result in ['liked', 'already_liked']
            print(f"   {like_result}")
            time.sleep(1)
        else:
            print(f"   ⏭️ Already liked")
            result.liked = True
        
        # Step 4: Navigate to post page
        print("\n[4/8] Opening post page...")
        self.safari.navigate_to(result.post_url, wait_time=4)
        print(f"   ✅ Opened")
        
        # Step 5: Expand comments
        print("\n[5/8] Expanding comments...")
        expand_result = self.safari.execute_js(self.JS_EXPAND_COMMENTS)
        print(f"   {expand_result}")
        time.sleep(2)
        
        # Step 6: Extract caption + comments
        print("\n[6/8] Extracting caption and comments...")
        context_data = self.safari.execute_js(self.JS_EXTRACT_CONTEXT)
        if not context_data:
            result.error = "Failed to extract context"
            return result
        
        ctx = json.loads(context_data)
        result.caption = ctx['caption']
        result.comments = ctx['comments']
        result.comments_found = len(ctx['comments'])
        
        print(f"   ✅ Caption: {result.caption[:60]}..." if result.caption else "   ⚠️ No caption found")
        print(f"   ✅ Comments: {result.comments_found}")
        for c in result.comments[:3]:
            print(f"      - {c[:50]}...")
        
        # Validate
        if not result.caption and result.comments_found == 0:
            result.error = "No content extracted"
            return result
        
        # Step 7: Generate AI comment
        print("\n[7/8] Generating AI comment...")
        comment_result = self.ai.generate_comment(
            platform='instagram',
            post_content=result.caption,
            existing_comments=result.comments,
            username=result.username
        )
        
        if not comment_result.success:
            result.error = f"Comment generation failed: {comment_result.error}"
            return result
        
        result.generated_comment = comment_result.text
        print(f"   ✅ Generated: \"{result.generated_comment}\"")
        
        # Step 8: Post comment
        print("\n[8/8] Posting comment...")
        
        # Focus comment box
        focus_result = self.safari.execute_js(self.JS_FOCUS_COMMENT)
        if focus_result != 'focused':
            result.error = "Could not focus comment box"
            return result
        print(f"   Focus: {focus_result}")
        
        # Type comment
        self.safari.type_via_clipboard(result.generated_comment)
        print(f"   ✅ Typed")
        time.sleep(1)
        
        # Submit
        submit_result = self.safari.execute_js(self.JS_SUBMIT_COMMENT)
        result.comment_posted = submit_result == 'submitted'
        print(f"   Submit: {submit_result}")
        time.sleep(3)
        
        # Capture proof
        result.proof_screenshot = f"/tmp/ig_proof_{timestamp}.png"
        self.safari.take_screenshot(result.proof_screenshot)
        print(f"   📸 {result.proof_screenshot}")
        
        result.success = True
        return result
    
    def check_login_state(self) -> bool:
        """Check if logged in to Instagram."""
        check_js = '''
        (function() {
            var indicators = ['a[href*="/direct/"]', 'svg[aria-label="Home"]', 'a[href="/accounts/activity/"]'];
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
    
    instagram = InstagramEngagement(openai_api_key=api_key)
    result = instagram.engage_with_post()
    
    print("\n" + "="*60)
    print("📊 RESULT")
    print("="*60)
    print(f"Success: {result.success}")
    print(f"Username: @{result.username}")
    print(f"Liked: {result.liked}")
    print(f"Comments found: {result.comments_found}")
    print(f"Comment: {result.generated_comment}")
    print(f"Posted: {result.comment_posted}")
    print(f"Proof: {result.proof_screenshot}")
    if result.error:
        print(f"Error: {result.error}")
    
    return result


if __name__ == "__main__":
    run_test()
