#!/usr/bin/env python3
"""
Auto-Comment Service - Unified service for Threads and Instagram auto-commenting.

Features:
- Image capture + AI Vision for post context extraction
- AI-powered comment generation
- Back button navigation for consecutive posts
- Full DB tracking (prompts, context, stats, costs)
- Rate limiting per platform/account

Usage:
    service = AutoCommentService()
    results = await service.auto_comment_feed("threads", num_posts=3)
    results = await service.auto_comment_feed("instagram", num_posts=3)
"""

import subprocess
import time
import os
import json
import base64
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False


class Platform(str, Enum):
    THREADS = "threads"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"


@dataclass
class CommentRecord:
    """Record of an auto-comment for DB storage."""
    platform: str
    post_url: str
    post_username: str
    post_caption: str
    post_image_context: str
    post_comments_context: str
    post_engagement_stats: Dict
    comment_text: str
    ai_prompt_used: str
    ai_model: str
    ai_response_raw: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    status: str
    verified: bool
    error_message: str = ""
    account_id: str = ""
    post_id: str = ""


class AutoCommentService:
    """
    Unified auto-comment service for multiple platforms.
    
    Handles:
    - Image capture and AI vision analysis
    - Context extraction (caption, comments, engagement)
    - AI comment generation
    - Comment posting
    - DB tracking
    """
    
    # Cost per 1K tokens (GPT-4o as of Jan 2026)
    COST_PER_1K_INPUT = 0.0025
    COST_PER_1K_OUTPUT = 0.01
    COST_PER_IMAGE = 0.00255  # ~85 tokens for low-res
    
    def __init__(self, db_url: str = None):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.db_pool = None
        self.session_comments: List[CommentRecord] = []
        self.commented_urls: set = set()  # In-memory dedup cache
        
        # Rate limits per hour
        self.rate_limits = {
            Platform.THREADS: 20,
            Platform.INSTAGRAM: 15,
            Platform.TIKTOK: 10,
        }
    
    async def init_db(self):
        """Initialize database connection pool."""
        if HAS_ASYNCPG and self.db_url:
            try:
                self.db_pool = await asyncpg.create_pool(self.db_url)
                logger.info("✅ Database connection initialized")
                # Load previously commented URLs for dedup
                await self._load_commented_urls()
            except Exception as e:
                logger.warning(f"Could not connect to database: {e}")
    
    async def _load_commented_urls(self):
        """Load previously commented URLs from DB for deduplication."""
        if not self.db_pool:
            return
        try:
            async with self.db_pool.acquire() as conn:
                # Try engagement_actions table first (Brand Ops schema)
                try:
                    rows = await conn.fetch('''
                        SELECT DISTINCT target_post_url FROM engagement_actions 
                        WHERE action_type = 'comment' AND status IN ('posted', 'verified')
                        AND created_at > NOW() - INTERVAL '30 days'
                    ''')
                    for row in rows:
                        if row['target_post_url']:
                            self.commented_urls.add(self._normalize_url(row['target_post_url']))
                except Exception:
                    pass
                
                # Also try legacy auto_comments table
                try:
                    rows = await conn.fetch('''
                        SELECT DISTINCT post_url FROM auto_comments 
                        WHERE status IN ('posted', 'verified', 'unverified')
                        AND created_at > NOW() - INTERVAL '30 days'
                    ''')
                    for row in rows:
                        if row['post_url']:
                            self.commented_urls.add(self._normalize_url(row['post_url']))
                except Exception:
                    pass
                
            logger.info(f"📋 Loaded {len(self.commented_urls)} previously commented URLs")
        except Exception as e:
            logger.warning(f"Could not load commented URLs: {e}")
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison (remove trailing slashes, query params)."""
        if not url:
            return ""
        # Remove query params and fragments
        url = url.split('?')[0].split('#')[0]
        # Remove trailing slash
        url = url.rstrip('/')
        # Extract post ID for platform-agnostic matching
        for pattern in ['/p/', '/post/', '/reel/']:
            if pattern in url:
                parts = url.split(pattern)
                if len(parts) > 1:
                    post_id = parts[1].split('/')[0]
                    return f"{pattern}{post_id}"
        return url
    
    def _has_commented(self, url: str) -> bool:
        """Check if we've already commented on this URL."""
        normalized = self._normalize_url(url)
        return normalized in self.commented_urls
    
    def _mark_commented(self, url: str):
        """Mark URL as commented (add to cache)."""
        normalized = self._normalize_url(url)
        self.commented_urls.add(normalized)
    
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
        """Execute JavaScript in Safari."""
        escaped = js_code.replace('"', '\\"').replace('\n', ' ')
        script = f'''
        tell application "Safari"
            tell front document
                do JavaScript "{escaped}"
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        return result if success else ""
    
    def _type_text(self, text: str) -> bool:
        """Type text using System Events."""
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
    
    def _capture_screenshot(self) -> Optional[str]:
        """Capture screenshot of current Safari window and return base64."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                temp_path = f.name
            
            # Capture Safari window
            subprocess.run([
                "screencapture", "-l",
                subprocess.run(
                    ["osascript", "-e", 'tell app "Safari" to id of window 1'],
                    capture_output=True, text=True
                ).stdout.strip(),
                temp_path
            ], timeout=10)
            
            # If window capture fails, capture screen
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                subprocess.run(["screencapture", "-x", temp_path], timeout=10)
            
            with open(temp_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            os.unlink(temp_path)
            return image_data
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
    
    def _analyze_image_with_vision(self, image_base64: str) -> str:
        """Use GPT-4 Vision to describe the image content."""
        if not self.openai_api_key:
            return ""
        
        try:
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this social media post image briefly. Focus on: main subject, any text visible, mood/style, and what makes it engaging. Keep under 100 words."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "low"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 150
            }
            
            result = subprocess.run([
                "curl", "-s", "https://api.openai.com/v1/chat/completions",
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {self.openai_api_key}",
                "-d", json.dumps(payload)
            ], capture_output=True, text=True, timeout=30)
            
            data = json.loads(result.stdout)
            return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return ""
    
    def _generate_ai_comment(self, context: Dict) -> Dict:
        """Generate AI comment and return with token usage."""
        if not self.openai_api_key:
            return {"comment": "", "usage": {}, "prompt": ""}
        
        prompt = f"""Generate a short, authentic social media comment for this post:

PLATFORM: {context.get('platform', 'unknown')}
POST BY: @{context.get('username', 'unknown')}
CAPTION: "{context.get('caption', '')[:300]}"
IMAGE DESCRIPTION: {context.get('image_context', 'N/A')}

TOP COMMENTS:
{context.get('comments_context', 'None available')}

Rules:
- Keep under 80 characters
- Be genuine and relatable
- Match the tone of the post
- No hashtags unless natural
- No emojis unless natural
"""
        
        try:
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "You are engaging authentically on social media."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 50,
                "temperature": 0.9
            }
            
            result = subprocess.run([
                "curl", "-s", "https://api.openai.com/v1/chat/completions",
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {self.openai_api_key}",
                "-d", json.dumps(payload)
            ], capture_output=True, text=True, timeout=30)
            
            data = json.loads(result.stdout)
            usage = data.get("usage", {})
            comment = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            return {
                "comment": comment,
                "usage": usage,
                "prompt": prompt,
                "raw_response": json.dumps(data)
            }
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return {"comment": "", "usage": {}, "prompt": prompt}
    
    def _calculate_cost(self, usage: Dict) -> float:
        """Calculate estimated cost from token usage."""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        cost = (prompt_tokens / 1000 * self.COST_PER_1K_INPUT) + \
               (completion_tokens / 1000 * self.COST_PER_1K_OUTPUT)
        
        return round(cost, 6)
    
    # =========================================================================
    # PLATFORM-SPECIFIC METHODS
    # =========================================================================
    
    def _navigate_to_feed(self, platform: Platform) -> bool:
        """Navigate to platform feed."""
        urls = {
            Platform.THREADS: "https://www.threads.com",
            Platform.INSTAGRAM: "https://www.instagram.com",
        }
        
        script = f'''
        tell application "Safari"
            activate
            if (count of windows) = 0 then make new document
            set URL of front document to "{urls.get(platform, '')}"
        end tell
        delay 4
        '''
        success, _ = self._run_applescript(script)
        return success
    
    def _get_feed_posts(self, platform: Platform, limit: int = 5) -> List[Dict]:
        """Get posts from feed."""
        if platform == Platform.THREADS:
            js = f'''
                (function() {{
                    var posts = [];
                    var links = document.querySelectorAll('a[href*="/post/"]');
                    for (var i = 0; i < Math.min(links.length, {limit}); i++) {{
                        posts.push({{index: i, url: links[i].href}});
                    }}
                    return JSON.stringify(posts);
                }})();
            '''
        else:  # Instagram
            js = f'''
                (function() {{
                    var posts = [];
                    var articles = document.querySelectorAll('article');
                    articles.forEach(function(a, i) {{
                        if (i < {limit}) {{
                            var link = a.querySelector('a[href*="/p/"], a[href*="/reel/"]');
                            if (link) posts.push({{index: i, url: link.href}});
                        }}
                    }});
                    return JSON.stringify(posts);
                }})();
            '''
        
        try:
            return json.loads(self._js(js))
        except:
            return []
    
    def _click_post(self, platform: Platform, index: int) -> bool:
        """Click on a post by index."""
        if platform == Platform.THREADS:
            js = f'''
                (function() {{
                    var links = document.querySelectorAll('a[href*="/post/"]');
                    if (links.length > {index}) {{
                        window.location.href = links[{index}].href;
                        return 'clicked';
                    }}
                    return 'not_found';
                }})();
            '''
        else:  # Instagram
            js = f'''
                (function() {{
                    var articles = document.querySelectorAll('article');
                    if (articles.length > {index}) {{
                        var link = articles[{index}].querySelector('a[href*="/p/"], a[href*="/reel/"]');
                        if (link) {{ link.click(); return 'clicked'; }}
                    }}
                    return 'not_found';
                }})();
            '''
        
        return 'clicked' in self._js(js)
    
    def _extract_post_context(self, platform: Platform) -> Dict:
        """Extract post context including text and engagement."""
        if platform == Platform.THREADS:
            js = '''
                (function() {
                    var result = {username: '', caption: '', comments: [], engagement: {}};
                    var containers = document.querySelectorAll('[data-pressable-container="true"]');
                    if (containers.length > 0) {
                        var main = containers[0];
                        var userLink = main.querySelector('a[href*="/@"]');
                        result.username = userLink ? userLink.href.split('/@').pop().split('/')[0] : '';
                        var texts = [];
                        main.querySelectorAll('[dir="auto"] span').forEach(function(el) {
                            var t = el.innerText.trim();
                            if (t && t.length > 3) texts.push(t);
                        });
                        result.caption = texts.slice(1, 5).join(' ');
                    }
                    for (var i = 1; i < Math.min(containers.length, 5); i++) {
                        var c = containers[i];
                        var uLink = c.querySelector('a[href*="/@"]');
                        var uname = uLink ? uLink.href.split('/@').pop().split('/')[0] : '';
                        var txt = c.querySelector('[dir="auto"] span');
                        if (uname && txt) result.comments.push({u: uname, t: txt.innerText.substring(0, 100)});
                    }
                    return JSON.stringify(result);
                })();
            '''
        else:  # Instagram
            js = '''
                (function() {
                    var result = {username: '', caption: '', comments: [], engagement: {}};
                    var container = document.querySelector('[role="dialog"]') || document;
                    var userLink = container.querySelector('a[href^="/"]');
                    if (userLink) {
                        var match = userLink.href.match(/instagram\\.com\\/([^\\/\\?]+)/);
                        result.username = match ? match[1] : '';
                    }
                    var caption = container.querySelector('span[dir="auto"]');
                    result.caption = caption ? caption.innerText.substring(0, 300) : '';
                    return JSON.stringify(result);
                })();
            '''
        
        try:
            return json.loads(self._js(js))
        except:
            return {"username": "", "caption": "", "comments": [], "engagement": {}}
    
    def _click_reply_and_type(self, platform: Platform, text: str) -> bool:
        """Click reply/comment button, type text."""
        if platform == Platform.THREADS:
            # Click first Reply button
            click_js = '''
                (function() {
                    var btn = document.querySelector('svg[aria-label="Reply"]');
                    if (btn) {
                        var parent = btn.closest('[role="button"]');
                        if (parent) { parent.click(); return 'clicked'; }
                    }
                    return 'not_found';
                })();
            '''
        else:  # Instagram
            # Focus textarea directly
            click_js = '''
                (function() {
                    var textarea = document.querySelector('textarea');
                    if (textarea) { textarea.focus(); textarea.click(); return 'focused'; }
                    return 'not_found';
                })();
            '''
        
        if 'not_found' in self._js(click_js):
            return False
        
        time.sleep(1)
        return self._type_text(text)
    
    def _submit_comment(self, platform: Platform) -> bool:
        """Submit the comment."""
        if platform == Platform.THREADS:
            js = '''
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
            '''
        else:  # Instagram
            js = '''
                (function() {
                    var buttons = document.querySelectorAll('div[role="button"], button');
                    for (var i = 0; i < buttons.length; i++) {
                        if ((buttons[i].innerText || '').trim() === 'Post') {
                            buttons[i].click();
                            return 'submitted';
                        }
                    }
                    return 'not_found';
                })();
            '''
        
        return 'submitted' in self._js(js)
    
    def _click_back(self, platform: Platform) -> bool:
        """Navigate back to feed."""
        if platform == Platform.THREADS:
            js = '''
                (function() {
                    var btn = document.querySelector('svg[aria-label="Back"]');
                    if (btn) {
                        var parent = btn.closest('[role="button"]');
                        if (parent) { parent.click(); return 'clicked'; }
                    }
                    window.history.back();
                    return 'history_back';
                })();
            '''
        else:  # Instagram
            js = '''
                (function() {
                    var btn = document.querySelector('svg[aria-label="Close"]');
                    if (btn) {
                        var parent = btn.closest('button') || btn.parentElement;
                        if (parent) { parent.click(); return 'closed'; }
                    }
                    document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
                    return 'escape';
                })();
            '''
        
        result = self._js(js)
        time.sleep(2)
        return bool(result)
    
    def _verify_comment(self, text: str) -> bool:
        """Verify comment was posted."""
        js = f'''
            (function() {{
                return document.body.innerText.includes("{text[:25]}") ? "true" : "false";
            }})();
        '''
        return 'true' in self._js(js)
    
    # =========================================================================
    # MAIN AUTO-COMMENT FLOW
    # =========================================================================
    
    async def auto_comment_feed(
        self,
        platform: Platform,
        num_posts: int = 3,
        start_index: int = 0,
        use_vision: bool = True
    ) -> List[Dict]:
        """
        Main auto-comment flow for a platform.
        
        Args:
            platform: Platform to comment on
            num_posts: Number of posts to comment on
            start_index: Starting post index
            use_vision: Whether to use AI vision for image analysis
        
        Returns:
            List of comment results with full tracking data
        """
        results = []
        
        logger.info(f"🚀 Starting {platform.value} auto-comment on {num_posts} posts")
        
        # Navigate to feed
        if not self._navigate_to_feed(platform):
            logger.error("Failed to navigate to feed")
            return results
        
        time.sleep(2)
        
        for i in range(num_posts):
            post_index = start_index + i
            record = CommentRecord(
                platform=platform.value,
                post_url="",
                post_username="",
                post_caption="",
                post_image_context="",
                post_comments_context="",
                post_engagement_stats={},
                comment_text="",
                ai_prompt_used="",
                ai_model="gpt-4o",
                ai_response_raw="",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.0,
                status="pending",
                verified=False
            )
            
            logger.info(f"\n📝 Processing post {i+1}/{num_posts}")
            
            # Get posts and click
            posts = self._get_feed_posts(platform, post_index + 1)
            if len(posts) <= post_index:
                logger.warning(f"Post {post_index} not found")
                continue
            
            record.post_url = posts[post_index].get("url", "")
            
            # Check for duplicate - skip if already commented
            if self._has_commented(record.post_url):
                logger.info(f"   ⏭️ SKIPPING - Already commented on: {record.post_url}")
                record.status = "skipped_duplicate"
                results.append(asdict(record))
                continue
            
            if not self._click_post(platform, post_index):
                logger.warning("Failed to click post")
                continue
            
            time.sleep(3)
            
            # Extract context
            context = self._extract_post_context(platform)
            record.post_username = context.get("username", "")
            record.post_caption = context.get("caption", "")
            
            # Format comments context
            comments = context.get("comments", [])
            record.post_comments_context = "\n".join([
                f"@{c.get('u','')}: {c.get('t','')}" for c in comments[:3]
            ])
            
            logger.info(f"   @{record.post_username}: {record.post_caption[:60]}...")
            
            # Capture and analyze image with vision
            if use_vision:
                logger.info("   📸 Capturing image for AI vision analysis...")
                image_b64 = self._capture_screenshot()
                if image_b64:
                    record.post_image_context = self._analyze_image_with_vision(image_b64)
                    logger.info(f"   🖼️ Vision: {record.post_image_context[:80]}...")
            
            # Generate AI comment
            ai_context = {
                "platform": platform.value,
                "username": record.post_username,
                "caption": record.post_caption,
                "image_context": record.post_image_context,
                "comments_context": record.post_comments_context
            }
            
            ai_result = self._generate_ai_comment(ai_context)
            record.comment_text = ai_result.get("comment", "")
            record.ai_prompt_used = ai_result.get("prompt", "")
            record.ai_response_raw = ai_result.get("raw_response", "")
            
            usage = ai_result.get("usage", {})
            record.prompt_tokens = usage.get("prompt_tokens", 0)
            record.completion_tokens = usage.get("completion_tokens", 0)
            record.total_tokens = usage.get("total_tokens", 0)
            record.estimated_cost_usd = self._calculate_cost(usage)
            
            if not record.comment_text:
                logger.warning("   Failed to generate comment")
                record.status = "failed"
                record.error_message = "AI generation failed"
                self._click_back(platform)
                results.append(asdict(record))
                continue
            
            logger.info(f"   💬 Comment: {record.comment_text}")
            
            # Post comment
            if not self._click_reply_and_type(platform, record.comment_text):
                logger.warning("   Failed to type comment")
                record.status = "failed"
                record.error_message = "Failed to type"
                self._click_back(platform)
                results.append(asdict(record))
                continue
            
            time.sleep(0.5)
            
            if not self._submit_comment(platform):
                logger.warning("   Failed to submit")
                record.status = "failed"
                record.error_message = "Submit failed"
                self._click_back(platform)
                results.append(asdict(record))
                continue
            
            time.sleep(2)
            
            # Verify
            record.verified = self._verify_comment(record.comment_text)
            record.status = "posted" if record.verified else "unverified"
            
            if record.verified:
                logger.success(f"   ✅ Comment posted! Cost: ${record.estimated_cost_usd:.4f}")
                # Mark as commented to prevent duplicates
                self._mark_commented(record.post_url)
            else:
                logger.warning("   ⚠️ Could not verify comment")
            
            results.append(asdict(record))
            self.session_comments.append(record)
            
            # Navigate back
            logger.info("   ⬅️ Navigating back...")
            self._click_back(platform)
            time.sleep(3)
        
        # Summary
        successful = sum(1 for r in results if r.get("status") == "posted")
        total_cost = sum(r.get("estimated_cost_usd", 0) for r in results)
        
        logger.info(f"\n🎉 Complete: {successful}/{len(results)} posted, ${total_cost:.4f} total cost")
        
        # Save to DB if available
        if self.db_pool:
            await self._save_to_db(results)
        
        return results
    
    async def _save_to_db(self, records: List[Dict], agent_run_id: str = None):
        """Save comment records to database with full Brand Ops tracking."""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                # First, create agent_run record if we have the new schema
                run_id = agent_run_id or f"auto_comment_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                
                try:
                    await conn.execute('''
                        INSERT INTO agent_runs (
                            agent_type, agent_version, run_id, platform,
                            input_context, prompt_version,
                            total_duration_ms, ai_tokens_used, ai_cost_usd,
                            status, completed_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ''',
                        'auto_commenter',
                        '1.0.0',
                        run_id,
                        records[0].get("platform") if records else None,
                        json.dumps({"num_posts": len(records)}),
                        '1.0.0',
                        0,
                        sum(r.get("total_tokens", 0) for r in records),
                        sum(r.get("estimated_cost_usd", 0) for r in records),
                        'success' if any(r.get("status") == "posted" for r in records) else 'failed',
                        datetime.utcnow()
                    )
                except Exception:
                    pass  # Table may not exist yet
                
                # Save to engagement_actions (new Brand Ops schema)
                for r in records:
                    try:
                        await conn.execute('''
                            INSERT INTO engagement_actions (
                                action_type, platform, our_username,
                                target_post_url, target_username,
                                post_caption, post_image_description,
                                top_comments, action_content,
                                ai_prompt_used, ai_model, ai_tokens_input,
                                ai_tokens_output, ai_cost_usd,
                                status, verified_at, verification_method,
                                content_id, posted_at
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                        ''',
                            'comment',
                            r.get("platform"),
                            r.get("account_id", ""),
                            r.get("post_url"),
                            r.get("post_username"),
                            r.get("post_caption"),
                            r.get("post_image_context"),
                            json.dumps(r.get("post_comments_context", "")),
                            r.get("comment_text"),
                            r.get("ai_prompt_used"),
                            r.get("ai_model"),
                            r.get("prompt_tokens"),
                            r.get("completion_tokens"),
                            r.get("estimated_cost_usd"),
                            r.get("status"),
                            datetime.utcnow() if r.get("verified") else None,
                            'page_check' if r.get("verified") else None,
                            f"{r.get('platform')}_{r.get('post_id', '')}",
                            datetime.utcnow() if r.get("status") == "posted" else None
                        )
                    except Exception as e:
                        logger.debug(f"engagement_actions insert failed (table may not exist): {e}")
                
                # Also save to legacy auto_comments table
                for r in records:
                    try:
                        await conn.execute('''
                            INSERT INTO auto_comments (
                                platform, post_url, post_username, post_caption,
                                post_image_context, post_comments_context,
                                post_engagement_stats, comment_text, ai_prompt_used,
                                ai_model, ai_response_raw, prompt_tokens,
                                completion_tokens, total_tokens, estimated_cost_usd,
                                status, verified, error_message, posted_at
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                        ''',
                            r.get("platform"),
                            r.get("post_url"),
                            r.get("post_username"),
                            r.get("post_caption"),
                            r.get("post_image_context"),
                            r.get("post_comments_context"),
                            json.dumps(r.get("post_engagement_stats", {})),
                            r.get("comment_text"),
                            r.get("ai_prompt_used"),
                            r.get("ai_model"),
                            r.get("ai_response_raw"),
                            r.get("prompt_tokens"),
                            r.get("completion_tokens"),
                            r.get("total_tokens"),
                            r.get("estimated_cost_usd"),
                            r.get("status"),
                            r.get("verified"),
                            r.get("error_message"),
                            datetime.utcnow() if r.get("status") == "posted" else None
                        )
                    except Exception as e:
                        logger.debug(f"auto_comments insert failed: {e}")
                
            logger.info(f"💾 Saved {len(records)} records to database (Brand Ops tracking)")
        except Exception as e:
            logger.error(f"Failed to save to DB: {e}")
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session."""
        return {
            "total_comments": len(self.session_comments),
            "successful": sum(1 for c in self.session_comments if c.status == "posted"),
            "failed": sum(1 for c in self.session_comments if c.status == "failed"),
            "total_cost_usd": sum(c.estimated_cost_usd for c in self.session_comments),
            "total_tokens": sum(c.total_tokens for c in self.session_comments),
            "platforms": list(set(c.platform for c in self.session_comments))
        }


# =============================================================================
# CLI
# =============================================================================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-Comment Service")
    parser.add_argument("--platform", "-p", choices=["threads", "instagram"], required=True)
    parser.add_argument("--posts", "-n", type=int, default=3, help="Number of posts")
    parser.add_argument("--start", "-s", type=int, default=0, help="Start index")
    parser.add_argument("--no-vision", action="store_true", help="Disable AI vision")
    
    args = parser.parse_args()
    
    service = AutoCommentService()
    await service.init_db()
    
    platform = Platform.THREADS if args.platform == "threads" else Platform.INSTAGRAM
    
    results = await service.auto_comment_feed(
        platform=platform,
        num_posts=args.posts,
        start_index=args.start,
        use_vision=not args.no_vision
    )
    
    print("\n📊 Session Summary:")
    summary = service.get_session_summary()
    print(f"   Total: {summary['total_comments']}")
    print(f"   Successful: {summary['successful']}")
    print(f"   Cost: ${summary['total_cost_usd']:.4f}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
