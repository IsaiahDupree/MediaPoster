#!/usr/bin/env python3
"""
Instagram Context Extractor - Captures full post context for AI comment generation.

Extracts:
- Post image (screenshot + AI vision analysis)
- Caption text
- Username
- Top comments (text + usernames)
- Engagement stats (likes, comments count)

Usage:
    python scripts/instagram_context_extractor.py --url "https://www.instagram.com/p/ABC123/"
    python scripts/instagram_context_extractor.py --test
"""

import subprocess
import time
import os
import json
import base64
import tempfile
import argparse
import urllib.request
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional


@dataclass
class Comment:
    """A comment on a post."""
    username: str
    text: str
    likes: int = 0


@dataclass
class PostContext:
    """Full context extracted from a post."""
    url: str
    post_id: str
    username: str
    caption: str
    image_description: str  # AI vision analysis
    image_alt_text: str     # Native alt text if available
    comments: List[Dict]
    likes_count: str
    comments_count: str
    timestamp: str
    extraction_time: str


class SafariController:
    """Controls Safari for automation."""
    
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
        except Exception as e:
            return False, str(e)
    
    def js(self, code: str) -> str:
        """Execute JavaScript in Safari."""
        # Use temp file to avoid escaping issues
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
        
        try:
            os.unlink(js_file)
        except:
            pass
        
        return result if success else ""
    
    def navigate(self, url: str, wait: int = 4) -> bool:
        """Navigate to URL."""
        script = f'''
        tell application "Safari"
            activate
            set URL of front document to "{url}"
        end tell
        '''
        success, _ = self.run_applescript(script)
        if success:
            time.sleep(wait)
        return success
    
    def get_url(self) -> str:
        """Get current URL."""
        script = '''
        tell application "Safari"
            tell front document
                return URL
            end tell
        end tell
        '''
        success, url = self.run_applescript(script)
        return url if success else ""
    
    def capture_screenshot(self) -> Optional[str]:
        """Capture Safari window screenshot, return base64."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            temp_path = f.name
        
        # Capture Safari window
        script = f'''
        tell application "Safari" to activate
        delay 0.5
        do shell script "screencapture -w -o {temp_path}"
        '''
        success, _ = self.run_applescript(script, timeout=10)
        
        if not success or not os.path.exists(temp_path):
            # Fallback: capture entire screen
            subprocess.run(['screencapture', '-x', temp_path], timeout=5)
        
        if os.path.exists(temp_path):
            with open(temp_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')
            os.unlink(temp_path)
            return data
        return None


class InstagramContextExtractor:
    """Extracts full context from Instagram posts."""
    
    def __init__(self):
        self.safari = SafariController()
        self.api_key = self._load_api_key()
    
    def _load_api_key(self) -> str:
        """Load OpenAI API key."""
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            env_file = Path("Backend/.env")
            if not env_file.exists():
                env_file = Path(".env")
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("OPENAI_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
        return key or ""
    
    def extract_caption_and_user(self) -> Dict:
        """Extract caption and username from current post."""
        js_code = '''
        (function() {
            var result = {username: '', caption: '', verified: false};
            
            // Get username from header or link
            var userLinks = document.querySelectorAll('a[href^="/"]');
            for (var i = 0; i < userLinks.length; i++) {
                var href = userLinks[i].getAttribute('href');
                if (href && href.match(/^\\/[a-zA-Z0-9_.]+\\/$/) && !href.includes('/p/')) {
                    result.username = href.replace(/\\//g, '');
                    break;
                }
            }
            
            // Also try header
            var header = document.querySelector('header a[href^="/"]');
            if (header && !result.username) {
                var href = header.getAttribute('href');
                result.username = href.replace(/\\//g, '');
            }
            
            // Get caption - look for h1 or specific span patterns
            var h1 = document.querySelector('h1');
            if (h1) {
                result.caption = h1.innerText;
            }
            
            // Also look in article spans
            if (!result.caption || result.caption.length < 10) {
                var article = document.querySelector('article');
                if (article) {
                    var spans = article.querySelectorAll('span');
                    for (var i = 0; i < spans.length; i++) {
                        var text = spans[i].innerText;
                        if (text && text.length > 20 && text.length < 2000 && !text.includes('like')) {
                            result.caption = text;
                            break;
                        }
                    }
                }
            }
            
            // Check for verified badge
            var verified = document.querySelector('svg[aria-label="Verified"]');
            result.verified = !!verified;
            
            return JSON.stringify(result);
        })();
        '''
        
        result = self.safari.js(js_code)
        try:
            return json.loads(result) if result else {}
        except:
            return {}
    
    def extract_comments(self, max_comments: int = 5) -> List[Dict]:
        """Extract top comments from current post."""
        js_code = f'''
        (function() {{
            var comments = [];
            
            // Find comment elements - they're usually in a specific structure
            var commentContainers = document.querySelectorAll('ul ul li, div[role="button"] + ul li');
            
            // Also try finding by structure
            if (commentContainers.length === 0) {{
                // Look for spans that look like comments (username followed by text)
                var allSpans = document.querySelectorAll('span');
                var currentComment = null;
                
                for (var i = 0; i < allSpans.length && comments.length < {max_comments}; i++) {{
                    var span = allSpans[i];
                    var text = span.innerText;
                    
                    // Skip if too short or contains certain keywords
                    if (!text || text.length < 2 || text.includes('like') || text.includes('Reply')) continue;
                    
                    // Check if this looks like a username (link nearby)
                    var parent = span.parentElement;
                    var link = parent ? parent.querySelector('a[href^="/"]') : null;
                    
                    if (link && text.length < 30) {{
                        // This might be a username
                        currentComment = {{username: text, text: '', likes: 0}};
                    }} else if (currentComment && text.length > 10 && text.length < 500) {{
                        // This might be comment text
                        currentComment.text = text;
                        comments.push(currentComment);
                        currentComment = null;
                    }}
                }}
            }}
            
            // Try alternative: look for comment section
            var commentSection = document.querySelector('ul[class*="Comment"], div[class*="comment"]');
            if (commentSection && comments.length === 0) {{
                var items = commentSection.querySelectorAll('li, div[role="button"]');
                for (var i = 0; i < items.length && comments.length < {max_comments}; i++) {{
                    var item = items[i];
                    var userEl = item.querySelector('a[href^="/"]');
                    var textEl = item.querySelector('span');
                    
                    if (userEl && textEl) {{
                        var username = userEl.getAttribute('href').replace(/\\//g, '');
                        var text = textEl.innerText;
                        if (username && text && text.length > 5) {{
                            comments.push({{username: username, text: text, likes: 0}});
                        }}
                    }}
                }}
            }}
            
            // Final fallback: scan all text nodes
            if (comments.length === 0) {{
                var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                var textNodes = [];
                while (walker.nextNode()) {{
                    var text = walker.currentNode.textContent.trim();
                    if (text.length > 15 && text.length < 300) {{
                        textNodes.push(text);
                    }}
                }}
                
                // Take some reasonable looking ones
                for (var i = 0; i < textNodes.length && comments.length < {max_comments}; i++) {{
                    var t = textNodes[i];
                    if (!t.includes('Follow') && !t.includes('like') && !t.includes('comment')) {{
                        comments.push({{username: 'user', text: t, likes: 0}});
                    }}
                }}
            }}
            
            return JSON.stringify(comments.slice(0, {max_comments}));
        }})();
        '''
        
        result = self.safari.js(js_code)
        try:
            return json.loads(result) if result else []
        except:
            return []
    
    def extract_engagement_stats(self) -> Dict:
        """Extract likes and comments count."""
        js_code = '''
        (function() {
            var result = {likes: '', comments: ''};
            
            // Look for like count
            var likeElements = document.querySelectorAll('span, button');
            for (var i = 0; i < likeElements.length; i++) {
                var text = likeElements[i].innerText || '';
                if (text.match(/^[\\d,.]+ likes?$/i) || text.match(/^[\\d,.]+ others?$/i)) {
                    result.likes = text;
                    break;
                }
            }
            
            // Look for section with "View all X comments"
            var viewAll = document.body.innerText.match(/View all (\\d+) comments/i);
            if (viewAll) {
                result.comments = viewAll[1];
            }
            
            return JSON.stringify(result);
        })();
        '''
        
        result = self.safari.js(js_code)
        try:
            return json.loads(result) if result else {}
        except:
            return {}
    
    def extract_image_alt_text(self) -> str:
        """Extract alt text from post image if available."""
        js_code = '''
        (function() {
            // Look for main post image
            var images = document.querySelectorAll('article img, div[role="button"] img');
            for (var i = 0; i < images.length; i++) {
                var alt = images[i].getAttribute('alt');
                if (alt && alt.length > 10 && !alt.includes('profile')) {
                    return alt;
                }
            }
            
            // Fallback to any image with substantial alt text
            var allImages = document.querySelectorAll('img[alt]');
            for (var i = 0; i < allImages.length; i++) {
                var alt = allImages[i].getAttribute('alt');
                if (alt && alt.length > 20) {
                    return alt;
                }
            }
            
            return '';
        })();
        '''
        
        return self.safari.js(js_code)
    
    def analyze_image_with_vision(self, image_base64: str) -> str:
        """Use GPT-4 Vision to describe the image."""
        if not self.api_key:
            return "API key not available"
        
        try:
            data = json.dumps({
                'model': 'gpt-4o',
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': 'Describe this Instagram post image in 2-3 sentences. Focus on: main subject, setting/background, mood/style, any text visible. Be concise.'
                            },
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/png;base64,{image_base64}',
                                    'detail': 'low'
                                }
                            }
                        ]
                    }
                ],
                'max_tokens': 150
            }).encode('utf-8')
            
            req = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions',
                data=data,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as resp:
                response = json.loads(resp.read().decode('utf-8'))
                return response['choices'][0]['message']['content'].strip()
                
        except Exception as e:
            return f"Vision analysis failed: {str(e)[:50]}"
    
    def extract_full_context(self, url: str = None, use_vision: bool = True) -> PostContext:
        """Extract full context from an Instagram post."""
        print(f"\n{'='*60}")
        print("📸 INSTAGRAM CONTEXT EXTRACTION")
        print(f"{'='*60}")
        
        # Navigate if URL provided
        if url:
            print(f"\n🌐 Navigating to: {url[:60]}...")
            self.safari.navigate(url, wait=4)
        
        current_url = self.safari.get_url()
        post_id = ""
        if "/p/" in current_url:
            post_id = current_url.split("/p/")[1].split("/")[0]
        elif "/reel/" in current_url:
            post_id = current_url.split("/reel/")[1].split("/")[0]
        
        print(f"   URL: {current_url[:50]}...")
        print(f"   Post ID: {post_id}")
        
        # Extract username and caption
        print("\n📝 Extracting caption and user...")
        user_data = self.extract_caption_and_user()
        username = user_data.get('username', '')
        caption = user_data.get('caption', '')
        print(f"   Username: @{username}")
        print(f"   Caption: {caption[:80]}..." if len(caption) > 80 else f"   Caption: {caption}")
        
        # Extract comments
        print("\n💬 Extracting top comments...")
        comments = self.extract_comments(max_comments=5)
        print(f"   Found {len(comments)} comments")
        for i, c in enumerate(comments[:3]):
            print(f"   {i+1}. @{c.get('username','')}: {c.get('text','')[:40]}...")
        
        # Extract engagement stats
        print("\n📊 Extracting engagement stats...")
        stats = self.extract_engagement_stats()
        print(f"   Likes: {stats.get('likes', 'N/A')}")
        print(f"   Comments: {stats.get('comments', 'N/A')}")
        
        # Extract image alt text
        print("\n🏷️ Extracting image alt text...")
        alt_text = self.extract_image_alt_text()
        print(f"   Alt text: {alt_text[:80]}..." if len(alt_text) > 80 else f"   Alt text: {alt_text or 'None'}")
        
        # Capture and analyze image with vision
        image_description = ""
        if use_vision:
            print("\n📸 Capturing screenshot for AI vision...")
            screenshot = self.safari.capture_screenshot()
            if screenshot:
                print(f"   Screenshot captured ({len(screenshot)} bytes)")
                print("   🤖 Analyzing with GPT-4 Vision...")
                image_description = self.analyze_image_with_vision(screenshot)
                print(f"   Vision: {image_description[:100]}...")
            else:
                print("   ❌ Screenshot capture failed")
        
        # Build context object
        context = PostContext(
            url=current_url,
            post_id=post_id,
            username=username,
            caption=caption,
            image_description=image_description,
            image_alt_text=alt_text,
            comments=[asdict(Comment(**c)) if isinstance(c, dict) else c for c in comments],
            likes_count=stats.get('likes', ''),
            comments_count=stats.get('comments', ''),
            timestamp="",
            extraction_time=datetime.now().isoformat()
        )
        
        # Print summary
        print(f"\n{'='*60}")
        print("✅ CONTEXT EXTRACTION COMPLETE")
        print(f"{'='*60}")
        print(f"   Username:     @{context.username}")
        print(f"   Caption:      {len(context.caption)} chars")
        print(f"   Comments:     {len(context.comments)}")
        print(f"   Image desc:   {len(context.image_description)} chars")
        print(f"   Alt text:     {len(context.image_alt_text)} chars")
        
        return context
    
    def generate_contextual_comment(self, context: PostContext) -> str:
        """Generate an AI comment using the full context."""
        if not self.api_key:
            return "Great post!"
        
        # Build rich prompt
        prompt_parts = []
        prompt_parts.append(f"Instagram post by @{context.username}")
        
        if context.caption:
            prompt_parts.append(f"Caption: {context.caption[:200]}")
        
        if context.image_description:
            prompt_parts.append(f"Image shows: {context.image_description}")
        elif context.image_alt_text:
            prompt_parts.append(f"Image: {context.image_alt_text}")
        
        if context.comments:
            top_comments = [f"@{c['username']}: {c['text'][:50]}" for c in context.comments[:3]]
            prompt_parts.append(f"Top comments: {'; '.join(top_comments)}")
        
        full_context = "\n".join(prompt_parts)
        
        print(f"\n🤖 Generating AI comment with full context...")
        print(f"   Context length: {len(full_context)} chars")
        
        try:
            data = json.dumps({
                'model': 'gpt-4o',
                'messages': [
                    {
                        'role': 'system',
                        'content': '''Generate a short, authentic Instagram comment (under 60 characters).
Rules:
- Be genuine and conversational
- Reference something specific from the post (image, caption, or vibe)
- No hashtags, no emojis
- Match the tone of existing comments
- Don't be generic - make it feel personal'''
                    },
                    {'role': 'user', 'content': full_context}
                ],
                'max_tokens': 40,
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
                comment = response['choices'][0]['message']['content'].strip().strip('"')
                print(f"   💬 Generated: {comment}")
                return comment
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return "Love this!"


def main():
    parser = argparse.ArgumentParser(description="Instagram Context Extractor")
    parser.add_argument("--url", "-u", type=str, help="Instagram post URL")
    parser.add_argument("--test", "-t", action="store_true", help="Test on current Safari page")
    parser.add_argument("--no-vision", action="store_true", help="Skip AI vision analysis")
    parser.add_argument("--generate", "-g", action="store_true", help="Generate a comment")
    parser.add_argument("--output", "-o", type=str, help="Save context to JSON file")
    
    args = parser.parse_args()
    
    extractor = InstagramContextExtractor()
    
    # Extract context
    context = extractor.extract_full_context(
        url=args.url if not args.test else None,
        use_vision=not args.no_vision
    )
    
    # Generate comment if requested
    if args.generate:
        comment = extractor.generate_contextual_comment(context)
        print(f"\n🎯 FINAL COMMENT: {comment}")
    
    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(asdict(context), indent=2))
        print(f"\n💾 Saved to: {output_path}")
    
    return context


if __name__ == "__main__":
    main()
