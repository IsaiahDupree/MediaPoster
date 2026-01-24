#!/usr/bin/env python3
"""
Threads Auto-Commenter - Safari Automation for automatic comment responses.

Features:
- Monitor threads for new comments
- AI-powered response generation
- Rule-based auto-replies (keywords, sentiment)
- Rate limiting to avoid spam detection
- Comment tracking to avoid duplicate replies

Uses AppleScript to control Safari browser for threads.net automation.
"""

import subprocess
import time
import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import asyncio

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    openai = None
    HAS_OPENAI = False

# Import session manager
try:
    from automation.safari_session_manager import SafariSessionManager, Platform
    HAS_SESSION_MANAGER = True
except ImportError:
    try:
        from safari_session_manager import SafariSessionManager, Platform
        HAS_SESSION_MANAGER = True
    except ImportError:
        HAS_SESSION_MANAGER = False

# Import verified selectors
try:
    from automation.threads_selectors import SELECTORS, JS, URLS, ThreadsSelectors, ThreadsJS
    HAS_SELECTORS = True
except ImportError:
    try:
        from threads_selectors import SELECTORS, JS, URLS, ThreadsSelectors, ThreadsJS
        HAS_SELECTORS = True
    except ImportError:
        HAS_SELECTORS = False
        logger.warning("Threads selectors not available, using fallback selectors")


class ReplyStrategy(str, Enum):
    """How to generate reply content."""
    AI = "ai"  # Use OpenAI to generate contextual reply
    TEMPLATE = "template"  # Use predefined templates
    KEYWORD = "keyword"  # Match keywords to responses
    CUSTOM = "custom"  # Custom callback function


@dataclass
class Comment:
    """Represents a comment on a thread."""
    comment_id: str
    username: str
    text: str
    timestamp: Optional[str] = None
    likes: int = 0
    is_reply: bool = False
    replied_to: bool = False


@dataclass
class AutoReplyRule:
    """Rule for automatic comment replies."""
    name: str
    strategy: ReplyStrategy
    enabled: bool = True
    keywords: List[str] = field(default_factory=list)  # For KEYWORD strategy
    template: str = ""  # For TEMPLATE strategy
    ai_prompt: str = ""  # For AI strategy - system prompt
    min_delay_seconds: int = 30  # Minimum delay before replying
    max_delay_seconds: int = 120  # Maximum delay (randomized)
    max_replies_per_hour: int = 10  # Rate limit
    exclude_usernames: List[str] = field(default_factory=list)  # Don't reply to these
    only_usernames: List[str] = field(default_factory=list)  # Only reply to these (if set)


@dataclass 
class AutoReplyConfig:
    """Configuration for auto-commenter."""
    rules: List[AutoReplyRule] = field(default_factory=list)
    global_rate_limit: int = 20  # Max replies per hour across all rules
    reply_to_own_posts_only: bool = True  # Only auto-reply on your own posts
    excluded_words: List[str] = field(default_factory=list)  # Don't reply if comment contains these
    track_replied_comments: bool = True  # Keep track of replied comments


class ThreadsAutoCommenter:
    """
    Safari-based Threads auto-comment system.
    Monitors threads and automatically replies based on configured rules.
    """
    
    THREADS_URL = "https://www.threads.net"
    
    def __init__(self, config: Optional[AutoReplyConfig] = None):
        self.session_manager = SafariSessionManager() if HAS_SESSION_MANAGER else None
        self.config = config or AutoReplyConfig()
        self.replied_comments: set = set()  # Track replied comment IDs
        self.reply_count_this_hour: int = 0
        self.hour_started: datetime = datetime.now()
        self.openai_client = None
        
        # Initialize OpenAI if available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and HAS_OPENAI:
            self.openai_client = openai.OpenAI(api_key=api_key)
    
    def _run_applescript(self, script: str) -> Tuple[bool, str]:
        """Execute AppleScript and return (success, output)."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Script timed out"
        except Exception as e:
            return False, str(e)
    
    def _escape_for_js(self, text: str) -> str:
        """Escape text for JavaScript injection."""
        return (text
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("'", "\\'")
                .replace("\n", "\\n")
                .replace("\r", ""))
    
    def require_login(self) -> bool:
        """Check if logged into Threads."""
        if self.session_manager:
            return self.session_manager.require_login(Platform.THREADS)
        return True
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()
        
        # Reset counter if hour has passed
        if now - self.hour_started > timedelta(hours=1):
            self.reply_count_this_hour = 0
            self.hour_started = now
        
        return self.reply_count_this_hour < self.config.global_rate_limit
    
    def navigate_to_thread(self, thread_url: str) -> bool:
        """Navigate Safari to a specific thread."""
        script = f'''
        tell application "Safari"
            activate
            if (count of windows) = 0 then
                make new document
            end if
            set URL of front document to "{thread_url}"
        end tell
        delay 3
        return "navigated"
        '''
        success, _ = self._run_applescript(script)
        return success
    
    def get_comments_on_thread(self, thread_url: str, limit: int = 50) -> List[Comment]:
        """
        Get comments from a thread page using verified selectors.
        
        Args:
            thread_url: URL of the thread
            limit: Maximum comments to fetch
            
        Returns:
            List of Comment objects
        """
        if not self.navigate_to_thread(thread_url):
            logger.error("Failed to navigate to thread")
            return []
        
        time.sleep(2)
        
        # Scroll to load more comments using verified JS
        if HAS_SELECTORS:
            scroll_js = JS.scroll_and_load(3)
        else:
            scroll_js = '''
                (async function() {
                    for (var i = 0; i < 3; i++) {
                        window.scrollTo(0, document.body.scrollHeight);
                        await new Promise(r => setTimeout(r, 800));
                    }
                    window.scrollTo(0, 0);
                })();
            '''
        
        scroll_script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{scroll_js.replace('"', '\\"')}"
            end tell
        end tell
        '''
        self._run_applescript(scroll_script)
        time.sleep(2)
        
        # Extract comments using verified JS
        if HAS_SELECTORS:
            extract_js = JS.extract_comments(limit)
        else:
            extract_js = f'''
                (function() {{
                    var comments = [];
                    var commentEls = document.querySelectorAll('[data-pressable-container="true"]');
                    for (var i = 1; i < Math.min(commentEls.length, {limit + 1}); i++) {{
                        var el = commentEls[i];
                        var userLink = el.querySelector('a[href*="/@"]');
                        var username = userLink ? userLink.href.split('/@').pop().split('/')[0].split('?')[0] : '';
                        var textEl = el.querySelector('[dir="auto"] span');
                        var text = textEl ? textEl.innerText : '';
                        var timeEl = el.querySelector('time');
                        var timestamp = timeEl ? timeEl.getAttribute('datetime') : '';
                        var postLink = el.querySelector('a[href*="/post/"]');
                        var commentId = '';
                        if (postLink) {{
                            var match = postLink.href.match(/\\/post\\/([A-Za-z0-9_-]+)/);
                            commentId = match ? match[1] : 'comment_' + i;
                        }} else {{
                            commentId = 'comment_' + i;
                        }}
                        if (username && text) {{
                            comments.push({{
                                comment_id: commentId,
                                username: username,
                                text: text.substring(0, 500),
                                timestamp: timestamp
                            }});
                        }}
                    }}
                    return JSON.stringify(comments);
                }})();
            '''
        
        extract_script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{extract_js.replace('"', '\\"').replace(chr(10), ' ')}"
            end tell
        end tell
        '''
        
        success, result = self._run_applescript(extract_script)
        
        if success:
            try:
                comments_data = json.loads(result)
                comments = [
                    Comment(
                        comment_id=c['comment_id'],
                        username=c['username'],
                        text=c['text'],
                        timestamp=c.get('timestamp'),
                        likes=c.get('likes', 0),
                        replied_to=c['comment_id'] in self.replied_comments
                    )
                    for c in comments_data
                ]
                logger.info(f"Found {len(comments)} comments on thread")
                return comments
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse comments: {e}")
                return []
        
        return []
    
    def _generate_ai_reply(self, comment: Comment, rule: AutoReplyRule) -> str:
        """Generate AI-powered reply using OpenAI."""
        if not self.openai_client:
            logger.error("OpenAI client not initialized")
            return ""
        
        system_prompt = rule.ai_prompt or """You are a friendly social media manager responding to comments on Threads.
Keep responses:
- Short (1-2 sentences max)
- Engaging and authentic
- No emojis unless the original comment uses them
- Professional but warm
- Never promotional or salesy
- Match the tone of the comment"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Reply to this comment from @{comment.username}: \"{comment.text}\""}
                ],
                max_tokens=100,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI reply generation failed: {e}")
            return ""
    
    def _generate_template_reply(self, comment: Comment, rule: AutoReplyRule) -> str:
        """Generate reply from template with variable substitution."""
        template = rule.template
        
        # Replace variables
        reply = template.replace("{username}", f"@{comment.username}")
        reply = reply.replace("{text}", comment.text[:50])
        
        return reply
    
    def _generate_keyword_reply(self, comment: Comment, rule: AutoReplyRule) -> Optional[str]:
        """Check if comment matches keywords and return appropriate response."""
        text_lower = comment.text.lower()
        
        for keyword in rule.keywords:
            if keyword.lower() in text_lower:
                # If template is set, use it; otherwise use AI
                if rule.template:
                    return self._generate_template_reply(comment, rule)
                elif self.openai_client:
                    return self._generate_ai_reply(comment, rule)
        
        return None
    
    def generate_reply(self, comment: Comment, rule: AutoReplyRule) -> Optional[str]:
        """Generate a reply based on the rule strategy."""
        if rule.strategy == ReplyStrategy.AI:
            return self._generate_ai_reply(comment, rule)
        elif rule.strategy == ReplyStrategy.TEMPLATE:
            return self._generate_template_reply(comment, rule)
        elif rule.strategy == ReplyStrategy.KEYWORD:
            return self._generate_keyword_reply(comment, rule)
        
        return None
    
    def post_reply_to_comment(self, thread_url: str, reply_text: str) -> Dict[str, Any]:
        """
        Post a reply to a thread/comment using verified selectors.
        
        Verified selectors (Jan 2026):
        - Reply button: svg[aria-label="Reply"]
        - Text input: [role="textbox"][contenteditable="true"]
        - Submit: Second svg[aria-label="Reply"] or svg[aria-label="Create"]
        """
        # Step 1: Click the reply button to open composer
        if HAS_SELECTORS:
            click_js = JS.click_reply_button()
        else:
            click_js = '''
                (function() {
                    var replyBtns = document.querySelectorAll('svg[aria-label="Reply"]');
                    if (replyBtns.length > 0) {
                        var btn = replyBtns[0].closest('[role="button"]') || replyBtns[0].parentElement;
                        if (btn) { btn.click(); return 'clicked'; }
                    }
                    return 'not_found';
                })();
            '''
        
        click_reply_script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{click_js.replace('"', '\\"').replace(chr(10), ' ')}"
            end tell
        end tell
        '''
        success, result = self._run_applescript(click_reply_script)
        
        if not success or result == 'not_found':
            return {'success': False, 'error': 'Reply button not found'}
        
        time.sleep(1)
        
        # Step 2: Type the reply using verified selector
        if HAS_SELECTORS:
            type_js = JS.type_in_composer(reply_text)
        else:
            escaped_text = self._escape_for_js(reply_text)
            type_js = f'''
                (function() {{
                    var input = document.querySelector('[role="textbox"][contenteditable="true"]');
                    if (!input) input = document.querySelector('[contenteditable="true"]');
                    if (input) {{
                        input.focus();
                        input.innerText = '{escaped_text}';
                        input.dispatchEvent(new InputEvent('input', {{ bubbles: true }}));
                        return 'typed';
                    }}
                    return 'input_not_found';
                }})();
            '''
        
        type_script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{type_js.replace('"', '\\"').replace(chr(10), ' ')}"
            end tell
        end tell
        '''
        success, result = self._run_applescript(type_script)
        
        if not success or 'typed' not in result:
            return {'success': False, 'error': 'Failed to type reply'}
        
        time.sleep(0.5)
        
        # Step 3: Submit the reply using verified selector
        if HAS_SELECTORS:
            submit_js = JS.submit_reply()
        else:
            submit_js = '''
                (function() {
                    var replyBtns = document.querySelectorAll('svg[aria-label="Reply"]');
                    if (replyBtns.length >= 2) {
                        var btn = replyBtns[1].closest('[role="button"]');
                        if (btn && !btn.getAttribute('aria-disabled')) {
                            btn.click();
                            return 'clicked_reply';
                        }
                    }
                    var createBtn = document.querySelector('svg[aria-label="Create"]');
                    if (createBtn) {
                        var btn = createBtn.closest('[role="button"]');
                        if (btn) { btn.click(); return 'clicked_create'; }
                    }
                    return 'submit_not_found';
                })();
            '''
        
        post_script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{submit_js.replace('"', '\\"').replace(chr(10), ' ')}"
            end tell
        end tell
        '''
        success, result = self._run_applescript(post_script)
        
        if success and 'clicked' in result:
            self.reply_count_this_hour += 1
            logger.success(f"✅ Reply posted: {reply_text[:50]}...")
            return {'success': True, 'reply_text': reply_text}
        
        return {'success': False, 'error': f'Failed to submit reply: {result}'}
    
    def should_reply_to_comment(self, comment: Comment, rule: AutoReplyRule) -> bool:
        """Check if we should reply to this comment based on rule criteria."""
        # Already replied?
        if comment.comment_id in self.replied_comments:
            return False
        
        # Excluded username?
        if comment.username in rule.exclude_usernames:
            return False
        
        # Only specific usernames?
        if rule.only_usernames and comment.username not in rule.only_usernames:
            return False
        
        # Contains excluded words?
        text_lower = comment.text.lower()
        for word in self.config.excluded_words:
            if word.lower() in text_lower:
                return False
        
        # For keyword strategy, check if any keyword matches
        if rule.strategy == ReplyStrategy.KEYWORD:
            has_keyword = any(kw.lower() in text_lower for kw in rule.keywords)
            if not has_keyword:
                return False
        
        return True
    
    async def process_thread(
        self,
        thread_url: str,
        rules: Optional[List[AutoReplyRule]] = None
    ) -> Dict[str, Any]:
        """
        Process a single thread - get comments and auto-reply based on rules.
        
        Args:
            thread_url: URL of the thread to process
            rules: Override rules (uses config rules if not provided)
            
        Returns:
            Dict with processing results
        """
        if not self.require_login():
            return {'success': False, 'error': 'Not logged in to Threads'}
        
        rules = rules or self.config.rules
        if not rules:
            return {'success': False, 'error': 'No auto-reply rules configured'}
        
        results = {
            'thread_url': thread_url,
            'comments_found': 0,
            'replies_sent': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Get comments
        comments = self.get_comments_on_thread(thread_url)
        results['comments_found'] = len(comments)
        
        for comment in comments:
            # Check rate limit
            if not self._check_rate_limit():
                logger.warning("Rate limit reached, stopping auto-replies")
                break
            
            # Try each rule
            for rule in rules:
                if not rule.enabled:
                    continue
                
                if self.should_reply_to_comment(comment, rule):
                    # Generate reply
                    reply_text = self.generate_reply(comment, rule)
                    
                    if reply_text:
                        # Random delay to seem human
                        import random
                        delay = random.randint(rule.min_delay_seconds, rule.max_delay_seconds)
                        logger.info(f"Waiting {delay}s before replying to @{comment.username}...")
                        await asyncio.sleep(delay)
                        
                        # Post reply
                        result = self.post_reply_to_comment(thread_url, reply_text)
                        
                        if result.get('success'):
                            self.replied_comments.add(comment.comment_id)
                            results['replies_sent'] += 1
                            logger.success(f"Replied to @{comment.username}: {reply_text[:50]}")
                        else:
                            results['errors'].append({
                                'comment_id': comment.comment_id,
                                'error': result.get('error')
                            })
                        
                        # Only apply first matching rule
                        break
                else:
                    results['skipped'] += 1
        
        return results
    
    async def monitor_threads(
        self,
        thread_urls: List[str],
        check_interval_minutes: int = 15,
        duration_hours: Optional[int] = None
    ):
        """
        Continuously monitor threads for new comments and auto-reply.
        
        Args:
            thread_urls: List of thread URLs to monitor
            check_interval_minutes: How often to check each thread
            duration_hours: How long to run (None = indefinitely)
        """
        logger.info(f"Starting auto-comment monitor for {len(thread_urls)} threads")
        logger.info(f"Check interval: {check_interval_minutes} minutes")
        
        start_time = datetime.now()
        
        while True:
            # Check if we should stop
            if duration_hours:
                elapsed = datetime.now() - start_time
                if elapsed.total_seconds() > duration_hours * 3600:
                    logger.info("Monitor duration reached, stopping")
                    break
            
            for url in thread_urls:
                try:
                    logger.info(f"Checking thread: {url}")
                    results = await self.process_thread(url)
                    logger.info(f"Processed: {results['replies_sent']} replies sent, {results['skipped']} skipped")
                except Exception as e:
                    logger.error(f"Error processing thread {url}: {e}")
            
            # Wait before next check
            logger.info(f"Waiting {check_interval_minutes} minutes before next check...")
            await asyncio.sleep(check_interval_minutes * 60)


# =============================================================================
# PRESET RULES
# =============================================================================

def get_engagement_rules() -> List[AutoReplyRule]:
    """Get preset engagement-focused auto-reply rules."""
    return [
        AutoReplyRule(
            name="thank_compliments",
            strategy=ReplyStrategy.KEYWORD,
            keywords=["love this", "amazing", "great", "awesome", "thank you", "helpful", "valuable"],
            template="Thank you so much {username}! Really appreciate the kind words 🙏",
            min_delay_seconds=30,
            max_delay_seconds=90
        ),
        AutoReplyRule(
            name="answer_questions",
            strategy=ReplyStrategy.AI,
            keywords=["?", "how", "what", "why", "when", "where"],
            ai_prompt="""You are responding to questions on your social media post.
Be helpful and direct. If you don't know the answer, say so honestly.
Keep responses under 280 characters. Be conversational.""",
            min_delay_seconds=60,
            max_delay_seconds=180
        ),
        AutoReplyRule(
            name="acknowledge_feedback",
            strategy=ReplyStrategy.TEMPLATE,
            keywords=["suggestion", "idea", "thought", "consider", "maybe"],
            template="Great point {username}! I'll definitely keep that in mind. Thanks for sharing!",
            min_delay_seconds=45,
            max_delay_seconds=120
        )
    ]


def get_lead_gen_rules() -> List[AutoReplyRule]:
    """Get preset lead generation focused rules."""
    return [
        AutoReplyRule(
            name="dm_interest",
            strategy=ReplyStrategy.KEYWORD,
            keywords=["interested", "tell me more", "how can i", "sign up", "where can i", "link"],
            template="Hey {username}! Check out the link in my bio, or DM me and I'll send you all the details 📩",
            min_delay_seconds=30,
            max_delay_seconds=60
        ),
        AutoReplyRule(
            name="price_questions",
            strategy=ReplyStrategy.KEYWORD,
            keywords=["price", "cost", "how much", "pricing", "rate"],
            template="Great question {username}! Shoot me a DM and I'll share all the pricing info with you 💬",
            min_delay_seconds=20,
            max_delay_seconds=45
        )
    ]


# =============================================================================
# FEED AUTO-COMMENTER - Full automated workflow
# =============================================================================

class ThreadsFeedAutoCommenter:
    """
    Automated feed commenter that:
    1. Navigates to threads.com main feed
    2. Clicks on posts sequentially
    3. Extracts post content + image alt text (OCR substitute) + top comments
    4. Generates AI response based on context
    5. Posts comment using verified selectors
    6. Navigates back using Back button
    7. Repeats for next post
    """
    
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
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
        script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{js_code.replace('"', '\\"').replace(chr(10), ' ')}"
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
    
    def navigate_to_feed(self) -> bool:
        """Navigate Safari to threads.com main feed."""
        script = '''
        tell application "Safari"
            activate
            if (count of windows) = 0 then make new document
            set URL of front document to "https://www.threads.com"
        end tell
        delay 4
        '''
        success, _ = self._run_applescript(script)
        return success
    
    def click_post(self, index: int = 0) -> str:
        """Click on a post by index from the feed. Returns post URL."""
        js = f'''
            (function() {{
                var postLinks = document.querySelectorAll('a[href*="/post/"]');
                if (postLinks.length > {index}) {{
                    var href = postLinks[{index}].href;
                    window.location.href = href;
                    return href;
                }}
                return 'not_found';
            }})();
        '''
        return self._js(js)
    
    def extract_post_context(self) -> dict:
        """Extract post content, image alt text, and top comments."""
        js = '''
            (function() {
                var result = {post: {}, images: [], comments: []};
                var containers = document.querySelectorAll('[data-pressable-container="true"]');
                
                if (containers.length > 0) {
                    var main = containers[0];
                    var userLink = main.querySelector('a[href*="/@"]');
                    result.post.username = userLink ? userLink.href.split('/@').pop().split('/')[0] : '';
                    
                    var texts = [];
                    main.querySelectorAll('[dir="auto"] span').forEach(function(el) {
                        var t = el.innerText.trim();
                        if (t && t.length > 3 && texts.indexOf(t) === -1 && !t.includes('View activity')) {
                            texts.push(t);
                        }
                    });
                    result.post.text = texts.slice(1, 5).join(' ');
                    
                    main.querySelectorAll('img').forEach(function(img) {
                        var w = img.naturalWidth || img.width;
                        if (w > 100 && img.alt && !img.alt.includes('profile')) {
                            result.images.push(img.alt);
                        }
                    });
                }
                
                for (var i = 1; i < Math.min(containers.length, 5); i++) {
                    var c = containers[i];
                    var uLink = c.querySelector('a[href*="/@"]');
                    var uname = uLink ? uLink.href.split('/@').pop().split('/')[0] : '';
                    var allText = [];
                    c.querySelectorAll('[dir="auto"] span').forEach(function(el) {
                        var t = el.innerText.trim();
                        if (t && t.length > 2 && allText.indexOf(t) === -1) allText.push(t);
                    });
                    if (uname) result.comments.push({u: uname, t: allText.join(' ').substring(0, 150)});
                }
                
                return JSON.stringify(result);
            })();
        '''
        result = self._js(js)
        try:
            return json.loads(result)
        except:
            return {"post": {}, "images": [], "comments": []}
    
    def generate_ai_reply(self, context: dict) -> str:
        """Generate AI reply using OpenAI based on post context."""
        if not self.openai_api_key:
            return ""
        
        post_text = context.get("post", {}).get("text", "")
        username = context.get("post", {}).get("username", "")
        images = context.get("images", [])
        comments = context.get("comments", [])
        
        prompt = f"""Reply to this Threads post:

POST BY: @{username}
POST TEXT: "{post_text}"
"""
        if images:
            prompt += f"IMAGE CONTEXT: {', '.join(images[:3])}\n"
        
        if comments:
            prompt += "\nTOP COMMENTS:\n"
            for c in comments[:4]:
                prompt += f"- @{c.get('u','')}: {c.get('t','')[:80]}\n"
        
        try:
            import subprocess
            curl_cmd = [
                "curl", "-s", "https://api.openai.com/v1/chat/completions",
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {self.openai_api_key}",
                "-d", json.dumps({
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": "You are engaging on social media. Generate a short, authentic reply under 80 characters. Be relatable, no hashtags."},
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
    
    def click_reply_button(self) -> bool:
        """Click the Reply button to open composer."""
        js = '''
            (function() {
                var replyBtns = document.querySelectorAll('svg[aria-label="Reply"]');
                if (replyBtns.length > 0) {
                    var btn = replyBtns[0].closest('[role="button"]');
                    if (btn) { btn.click(); return 'clicked'; }
                }
                return 'not_found';
            })();
        '''
        return 'clicked' in self._js(js)
    
    def submit_reply(self) -> bool:
        """Click the second Reply button to submit the comment."""
        js = '''
            (function() {
                var replyBtns = document.querySelectorAll('svg[aria-label="Reply"]');
                if (replyBtns.length >= 2) {
                    var btn = replyBtns[1].closest('[role="button"]');
                    if (btn && !btn.getAttribute('aria-disabled')) {
                        btn.click();
                        return 'submitted';
                    }
                }
                return 'not_found';
            })();
        '''
        return 'submitted' in self._js(js)
    
    def click_back(self) -> bool:
        """Click Back button to return to feed."""
        js = '''
            (function() {
                var backBtn = document.querySelector('svg[aria-label="Back"]');
                if (backBtn) {
                    var btn = backBtn.closest('[role="button"]') || backBtn.parentElement;
                    if (btn) { btn.click(); return 'clicked'; }
                }
                window.history.back();
                return 'history_back';
            })();
        '''
        result = self._js(js)
        time.sleep(2)
        return 'clicked' in result or 'history_back' in result
    
    def verify_comment_posted(self, comment_text: str) -> bool:
        """Verify the comment was posted by checking page content."""
        js = f'''
            (function() {{
                return document.body.innerText.includes("{comment_text[:30]}") ? "true" : "false";
            }})();
        '''
        return 'true' in self._js(js)
    
    def auto_comment_feed(self, num_posts: int = 2, start_index: int = 0) -> list:
        """
        Main function: Auto-comment on posts from the feed.
        
        Args:
            num_posts: Number of posts to comment on
            start_index: Which post index to start from (0 = first)
        
        Returns:
            List of results with post URLs and comment status
        """
        results = []
        
        logger.info(f"🚀 Starting auto-comment on {num_posts} posts from feed")
        
        # Step 1: Navigate to feed
        if not self.navigate_to_feed():
            logger.error("Failed to navigate to feed")
            return results
        
        time.sleep(2)
        
        for i in range(num_posts):
            post_index = start_index + i
            post_result = {"index": post_index, "url": "", "comment": "", "success": False}
            
            logger.info(f"\n📝 Processing post {i+1}/{num_posts} (index {post_index})")
            
            # Step 2: Click on post
            post_url = self.click_post(post_index)
            if 'not_found' in post_url:
                logger.warning(f"Post at index {post_index} not found")
                continue
            
            post_result["url"] = post_url
            logger.info(f"   URL: {post_url}")
            time.sleep(3)
            
            # Step 3: Extract context
            context = self.extract_post_context()
            post_text = context.get("post", {}).get("text", "")[:100]
            logger.info(f"   Post: {post_text}...")
            
            # Step 4: Generate AI reply
            reply = self.generate_ai_reply(context)
            if not reply:
                logger.warning("   Failed to generate AI reply")
                self.click_back()
                time.sleep(2)
                continue
            
            post_result["comment"] = reply
            logger.info(f"   Reply: {reply}")
            
            # Step 5: Click reply button
            if not self.click_reply_button():
                logger.warning("   Failed to click reply button")
                self.click_back()
                time.sleep(2)
                continue
            
            time.sleep(1)
            
            # Step 6: Type reply
            if not self._type_text(reply):
                logger.warning("   Failed to type reply")
                self.click_back()
                time.sleep(2)
                continue
            
            time.sleep(0.5)
            
            # Step 7: Submit
            if not self.submit_reply():
                logger.warning("   Failed to submit reply")
                self.click_back()
                time.sleep(2)
                continue
            
            time.sleep(2)
            
            # Step 8: Verify
            if self.verify_comment_posted(reply):
                post_result["success"] = True
                logger.success(f"   ✅ Comment posted successfully!")
            else:
                logger.warning("   ⚠️ Could not verify comment")
            
            results.append(post_result)
            
            # Step 9: Navigate back using Back button
            logger.info("   Navigating back to feed...")
            self.click_back()
            time.sleep(3)
        
        # Summary
        successful = sum(1 for r in results if r["success"])
        logger.info(f"\n🎉 Auto-comment complete: {successful}/{len(results)} successful")
        
        return results


# =============================================================================
# CLI INTERFACE
# =============================================================================

async def main():
    """Command-line interface for Threads auto-commenter."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Threads Auto-Commenter")
    parser.add_argument("--thread", "-t", help="Thread URL to process")
    parser.add_argument("--monitor", "-m", nargs="+", help="Thread URLs to monitor")
    parser.add_argument("--interval", "-i", type=int, default=15, help="Check interval in minutes")
    parser.add_argument("--duration", "-d", type=int, help="Monitor duration in hours")
    parser.add_argument("--rules", "-r", choices=["engagement", "lead_gen"], default="engagement",
                       help="Preset rules to use")
    parser.add_argument("--list-comments", "-l", help="Just list comments on a thread (no replies)")
    parser.add_argument("--feed", "-f", type=int, nargs="?", const=2, 
                       help="Auto-comment on N posts from feed (default: 2)")
    parser.add_argument("--start-index", "-s", type=int, default=0,
                       help="Start from post index N in feed (default: 0)")
    
    args = parser.parse_args()
    
    # Feed auto-commenter mode
    if args.feed:
        feed_commenter = ThreadsFeedAutoCommenter()
        results = feed_commenter.auto_comment_feed(
            num_posts=args.feed,
            start_index=args.start_index
        )
        print(f"\n🎉 Feed auto-comment complete!")
        for r in results:
            status = "✅" if r["success"] else "❌"
            print(f"   {status} {r['url'][:50]}...")
            if r["comment"]:
                print(f"      → {r['comment'][:60]}")
        return
    
    # Select rules
    if args.rules == "engagement":
        rules = get_engagement_rules()
    else:
        rules = get_lead_gen_rules()
    
    config = AutoReplyConfig(rules=rules)
    commenter = ThreadsAutoCommenter(config=config)
    
    if args.list_comments:
        comments = commenter.get_comments_on_thread(args.list_comments)
        print(f"\n📝 Found {len(comments)} comments:\n")
        for c in comments:
            print(f"  @{c.username}: {c.text[:100]}...")
        return
    
    if args.thread:
        results = await commenter.process_thread(args.thread)
        print(f"\n✅ Processing complete:")
        print(f"   Comments found: {results['comments_found']}")
        print(f"   Replies sent: {results['replies_sent']}")
        print(f"   Skipped: {results['skipped']}")
        return
    
    if args.monitor:
        await commenter.monitor_threads(
            args.monitor,
            check_interval_minutes=args.interval,
            duration_hours=args.duration
        )
        return
    
    parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
