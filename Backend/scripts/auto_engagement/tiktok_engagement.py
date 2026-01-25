"""
TikTok Auto-Engagement Module

Automates engagement on TikTok videos with full context extraction:
- Robust navigation with URL verification
- Extract video data (creator, description, engagement stats)
- Extract top comments from comment panel
- Like video
- Generate contextual AI comment
- Post comment with verification

Usage:
    from auto_engagement.tiktok_engagement import TikTokEngagement
    
    tiktok = TikTokEngagement()
    result = tiktok.engage_with_video()
    print(f"Comment posted: {result.comment_posted}")
"""

import time
import json
from typing import Optional, List
from dataclasses import dataclass, field

from .safari_controller import SafariController
from .ai_comment_generator import AICommentGenerator


@dataclass
class TikTokEngagementResult:
    """Result of TikTok engagement."""
    success: bool
    username: str = ""
    description: str = ""
    likes: str = ""
    comments_count: str = ""
    shares: str = ""
    comments_found: int = 0
    comments: List[str] = field(default_factory=list)
    liked: bool = False
    generated_comment: str = ""
    comment_posted: bool = False
    proof_screenshot: str = ""
    error: str = ""


class TikTokEngagement:
    """
    TikTok auto-engagement with full context extraction.
    
    Flow:
    1. Navigate to TikTok For You page with verification
    2. Pause video
    3. Extract video data (creator, description, engagement)
    4. Like video
    5. Open comments panel
    6. Extract top comments
    7. Generate contextual AI comment
    8. Post comment
    9. Capture proof screenshot
    """
    
    TIKTOK_URL = "https://www.tiktok.com/foryou"
    
    # Updated selectors based on current TikTok layout (Jan 2026)
    JS_PAUSE_VIDEO = '''
    (function() {
        var video = document.querySelector('video');
        if (video) {
            video.pause();
            return 'paused';
        }
        return 'no_video';
    })()
    '''
    
    JS_EXTRACT_VIDEO_DATA = '''
    (function() {
        var data = {username: '', description: '', likes: '', comments: '', shares: '', saves: ''};
        
        // Get username from user profile links (most reliable method)
        var userLinks = document.querySelectorAll('a[href*="/@"]');
        for (var i = 0; i < userLinks.length; i++) {
            var link = userLinks[i];
            var href = link.getAttribute('href') || '';
            var text = (link.innerText || '').trim();
            
            // Extract username from href
            var match = href.match(/@([^/\\?]+)/);
            if (match && match[1] && !match[1].includes('video')) {
                // Prefer link with visible text (creator name)
                if (text && text.length > 0 && text.length < 50) {
                    data.username = match[1];
                    data.displayName = text;
                    break;
                } else if (!data.username) {
                    data.username = match[1];
                }
            }
        }
        
        // Fallback selectors
        if (!data.username) {
            var userSelectors = [
                '[data-e2e="browse-username"]',
                '[data-e2e="video-author-uniqueid"]',
                'h3[data-e2e="video-author-uniqueid"]'
            ];
            for (var i = 0; i < userSelectors.length; i++) {
                var el = document.querySelector(userSelectors[i]);
                if (el) {
                    var text = (el.innerText || el.textContent || '').replace('@', '').trim();
                    if (text && text.length > 0 && text.length < 50) {
                        data.username = text;
                        break;
                    }
                }
            }
        }
        
        // Get description from various elements
        var descSelectors = [
            '[data-e2e="browse-video-desc"]',
            '[data-e2e="video-desc"]',
            'span[data-e2e="new-desc"]',
            '.video-meta-title',
            'h1'
        ];
        for (var i = 0; i < descSelectors.length; i++) {
            var el = document.querySelector(descSelectors[i]);
            if (el && el.innerText.length > 5) {
                data.description = el.innerText.substring(0, 300);
                break;
            }
        }
        
        // Get engagement stats from sidebar
        var sidebar = document.querySelector('[class*="DivActionItemContainer"]') || document.body;
        var sidebarText = sidebar.innerText;
        
        // Look for numbers near engagement icons
        var strongEls = document.querySelectorAll('strong, span[data-e2e*="count"]');
        var counts = [];
        strongEls.forEach(function(el) {
            var text = el.innerText.trim();
            if (text.match(/^[\\d.]+[KMB]?$/i)) {
                counts.push(text);
            }
        });
        
        // Assign counts based on position (typically: likes, comments, saves/bookmarks, shares)
        if (counts.length >= 1) data.likes = counts[0];
        if (counts.length >= 2) data.comments = counts[1];
        if (counts.length >= 3) data.saves = counts[2];
        if (counts.length >= 4) data.shares = counts[3];
        
        return JSON.stringify(data);
    })()
    '''
    
    JS_LIKE_VIDEO = '''
    (function() {
        // Multiple selectors for like button
        var selectors = [
            '[data-e2e="like-icon"]',
            '[data-e2e="browse-like-icon"]',
            'span[data-e2e="like-icon"]',
            '[class*="ButtonLike"]',
            'button[aria-label*="like" i]'
        ];
        
        for (var i = 0; i < selectors.length; i++) {
            var el = document.querySelector(selectors[i]);
            if (el) {
                var btn = el.closest('button') || el;
                btn.click();
                return 'liked';
            }
        }
        return 'not_found';
    })()
    '''
    
    JS_OPEN_COMMENTS = '''
    (function() {
        var selectors = [
            '[data-e2e="comment-icon"]',
            '[data-e2e="browse-comment-icon"]',
            'span[data-e2e="comment-icon"]',
            '[class*="ButtonComment"]',
            'button[aria-label*="comment" i]'
        ];
        
        for (var i = 0; i < selectors.length; i++) {
            var el = document.querySelector(selectors[i]);
            if (el) {
                var btn = el.closest('button') || el;
                btn.click();
                return 'opened';
            }
        }
        return 'not_found';
    })()
    '''
    
    JS_EXTRACT_COMMENTS = '''
    (function() {
        var comments = [];
        
        // Multiple selectors for comment items
        var itemSelectors = [
            '[data-e2e="comment-item"]',
            '[class*="CommentItem"]',
            '[class*="comment-item"]',
            'div[class*="DivCommentItemContainer"]'
        ];
        
        var items = [];
        for (var s = 0; s < itemSelectors.length; s++) {
            items = document.querySelectorAll(itemSelectors[s]);
            if (items.length > 0) break;
        }
        
        for (var i = 0; i < Math.min(items.length, 8); i++) {
            var item = items[i];
            var username = '';
            var text = '';
            
            // Get username
            var userEl = item.querySelector('a[href*="/@"]') || 
                         item.querySelector('[data-e2e="comment-username"]') ||
                         item.querySelector('span[class*="UserName"]');
            if (userEl) {
                var href = userEl.getAttribute('href') || '';
                var match = href.match(/@([^/\\?]+)/);
                if (match) {
                    username = match[1];
                } else {
                    username = userEl.innerText.replace('@', '').trim();
                }
            }
            
            // Get comment text
            var textEl = item.querySelector('[data-e2e="comment-text"]') ||
                         item.querySelector('p[class*="PCommentText"]') ||
                         item.querySelector('span[class*="SpanCommentText"]');
            if (textEl) {
                text = textEl.innerText.trim();
            }
            
            // Fallback: get all text and clean it
            if (!text) {
                text = item.innerText.replace(/\\n/g, ' ').trim();
                // Remove common UI elements
                text = text.replace(/Reply|\\d+[dwmh]|like|\\d+[KMB]?\\s*$/gi, '').trim();
            }
            
            if (text.length > 5 && text.length < 200) {
                var entry = username ? '@' + username + ': ' + text.substring(0, 100) : text.substring(0, 100);
                comments.push(entry);
            }
        }
        
        return JSON.stringify(comments);
    })()
    '''
    
    JS_FOCUS_COMMENT_INPUT = '''
    (function() {
        var selectors = [
            '[data-e2e="comment-input"] [contenteditable="true"]',
            '[class*="CommentInput"] [contenteditable="true"]',
            'div[contenteditable="true"][data-placeholder*="comment" i]',
            '[contenteditable="true"]'
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
    
    JS_SUBMIT_COMMENT = '''
    (function() {
        var selectors = [
            '[data-e2e="comment-post"]',
            'button[class*="PostButton"]',
            'div[class*="DivPostButton"]'
        ];
        
        for (var i = 0; i < selectors.length; i++) {
            var btn = document.querySelector(selectors[i]);
            if (btn) {
                btn.click();
                return 'submitted';
            }
        }
        return 'not_found';
    })()
    '''
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize TikTok engagement.
        
        Args:
            openai_api_key: OpenAI API key (optional, uses env var)
        """
        self.safari = SafariController()
        self.ai = AICommentGenerator(api_key=openai_api_key)
    
    def engage_with_video(self, skip_navigation: bool = False) -> TikTokEngagementResult:
        """
        Engage with a TikTok video.
        
        Args:
            skip_navigation: If True, assumes already on TikTok
            
        Returns:
            TikTokEngagementResult with all engagement data
        """
        result = TikTokEngagementResult(success=False)
        timestamp = int(time.time())
        
        print("\n" + "="*60)
        print("🎵 TIKTOK ENGAGEMENT")
        print("="*60)
        
        # Step 1: Navigate with verification
        if not skip_navigation:
            print("\n[1/9] Navigating to TikTok...")
            
            # Clear and navigate
            self.safari.navigate_to('about:blank', wait_time=1)
            nav = self.safari.navigate_with_verification(
                self.TIKTOK_URL,
                'tiktok.com',
                max_attempts=3
            )
            
            if not nav.success:
                result.error = "Navigation failed"
                return result
            
            print(f"   ✅ On TikTok")
            time.sleep(3)
        
        # Step 2: Pause video
        print("\n[2/9] Pausing video...")
        pause_result = self.safari.execute_js(self.JS_PAUSE_VIDEO)
        print(f"   {pause_result}")
        
        # Step 3: Extract video data
        print("\n[3/9] Extracting video data...")
        video_data = self.safari.execute_js(self.JS_EXTRACT_VIDEO_DATA)
        
        if not video_data:
            result.error = "Failed to extract video data"
            return result
        
        vd = json.loads(video_data)
        result.username = vd.get('username', '')
        result.description = vd.get('description', '')
        result.likes = vd.get('likes', '')
        result.comments_count = vd.get('comments', '')
        result.shares = vd.get('shares', '')
        
        print(f"   ✅ Creator: @{result.username}")
        print(f"   ✅ Description: {result.description[:60]}..." if result.description else "   ⚠️ No description")
        print(f"   ✅ Engagement: {result.likes} likes, {result.comments_count} comments")
        
        # Validate
        if not result.username and not result.description:
            result.error = "No video data extracted"
            return result
        
        # Step 4: Like video
        print("\n[4/9] Liking video...")
        like_result = self.safari.execute_js(self.JS_LIKE_VIDEO)
        result.liked = like_result == 'liked'
        print(f"   {like_result}")
        time.sleep(1)
        
        # Step 5: Open comments panel
        print("\n[5/9] Opening comments...")
        comment_result = self.safari.execute_js(self.JS_OPEN_COMMENTS)
        print(f"   {comment_result}")
        time.sleep(2)
        
        # Step 6: Extract top comments
        print("\n[6/9] Extracting top comments...")
        comments_data = self.safari.execute_js(self.JS_EXTRACT_COMMENTS)
        
        if comments_data:
            result.comments = json.loads(comments_data)
            result.comments_found = len(result.comments)
            print(f"   ✅ Found {result.comments_found} comments")
            for c in result.comments[:3]:
                print(f"      - {c[:50]}...")
        else:
            print(f"   ⚠️ No comments extracted")
        
        # Step 7: Generate AI comment
        print("\n[7/9] Generating AI comment...")
        engagement = f"{result.likes} likes, {result.comments_count} comments"
        
        comment_result_ai = self.ai.generate_comment(
            platform='tiktok',
            post_content=result.description,
            existing_comments=result.comments,
            username=result.username,
            engagement=engagement
        )
        
        if not comment_result_ai.success:
            result.error = f"Comment generation failed: {comment_result_ai.error}"
            return result
        
        result.generated_comment = comment_result_ai.text
        print(f"   ✅ Generated: \"{result.generated_comment}\"")
        
        # Step 8: Post comment
        print("\n[8/9] Posting comment...")
        
        # Focus input
        focus_result = self.safari.execute_js(self.JS_FOCUS_COMMENT_INPUT)
        if focus_result != 'focused':
            result.error = "Could not focus comment input"
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
        
        # Step 9: Capture proof
        print("\n[9/9] Capturing proof...")
        result.proof_screenshot = f"/tmp/tiktok_proof_{timestamp}.png"
        self.safari.take_screenshot(result.proof_screenshot)
        print(f"   📸 {result.proof_screenshot}")
        
        result.success = True
        return result
    
    def check_login_state(self) -> bool:
        """Check if logged in to TikTok."""
        check_js = '''
        (function() {
            var indicators = ['a[href*="/upload"]', '[data-e2e="profile-icon"]', 'button[aria-label*="inbox" i]'];
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
    
    tiktok = TikTokEngagement(openai_api_key=api_key)
    result = tiktok.engage_with_video()
    
    print("\n" + "="*60)
    print("📊 RESULT")
    print("="*60)
    print(f"Success: {result.success}")
    print(f"Username: @{result.username}")
    print(f"Description: {result.description[:50]}..." if result.description else "No description")
    print(f"Engagement: {result.likes} likes, {result.comments_count} comments")
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
