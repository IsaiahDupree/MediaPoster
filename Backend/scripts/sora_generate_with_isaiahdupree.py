#!/usr/bin/env python3
"""
Sora Generate with @isaiahdupree Character
==========================================

Generates a Sora video using the @isaiahdupree character by typing it
directly into the prompt field (most reliable method).

Usage:
    python scripts/sora_generate_with_isaiahdupree.py "your prompt here"
    python scripts/sora_generate_with_isaiahdupree.py  # Uses default prompt

Features:
    ✅ Types @isaiahdupree directly in prompt (works reliably)
    ✅ Navigates to sora.chatgpt.com/explore
    ✅ Checks login status
    ✅ Clicks Create Video button
    ✅ Polls /drafts for completion
    ✅ Downloads when ready

Requirements:
    - Safari with Remote Automation enabled
    - Logged into sora.chatgpt.com
"""

import asyncio
import subprocess
import sys
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


# Constants
CHARACTER = "isaiahdupree"
DEFAULT_PROMPT = "ever feel like managing all your social media is like juggling cats? what if there was a way to simplify the chaos with just one click? curious? there's more to this than meets the eye..."
DOWNLOAD_DIR = Path("/Users/isaiahdupree/Documents/CompetitorResearch/sora_downloads")
POLL_INTERVAL = 30  # seconds
MAX_TIMEOUT = 600  # 10 minutes


class SoraIsaiahDupreeGenerator:
    """
    Generates Sora videos with @isaiahdupree character.
    
    Uses direct prompt typing method which is the most reliable.
    """
    
    def __init__(self):
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    def _run_applescript(self, script: str) -> str:
        """Execute AppleScript and return result."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"AppleScript error: {e}")
            return ""
    
    def _run_js(self, js_code: str) -> str:
        """Execute JavaScript in Safari and return result."""
        js_escaped = js_code.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
        script = f'''
tell application "Safari"
    do JavaScript "{js_escaped}" in front document
end tell
'''
        return self._run_applescript(script)
    
    def navigate_to_explore(self):
        """Navigate Safari to Sora explore page."""
        logger.info("📍 Navigating to sora.chatgpt.com/explore...")
        script = '''
tell application "Safari"
    activate
    if (count of windows) = 0 then
        make new document
    end if
    set URL of front document to "https://sora.chatgpt.com/explore"
end tell
'''
        self._run_applescript(script)
        time.sleep(3)
        logger.info("   ✅ Done")
    
    def check_login(self) -> bool:
        """Check if logged into Sora."""
        logger.info("🔐 Checking login status...")
        js = """
            (function() {
                // Check for login indicators
                if (document.querySelector('textarea')) return 'logged_in';
                if (document.body.innerHTML.includes('Sign in')) return 'not_logged_in';
                return 'logged_in';
            })()
        """
        result = self._run_js(js)
        logged_in = "logged_in" in result
        if logged_in:
            logger.info("   ✅ Logged in")
        else:
            logger.error("   ❌ Not logged in - please log in manually")
        return logged_in
    
    def set_prompt_with_character(self, prompt: str) -> bool:
        """
        Set prompt with @isaiahdupree character prefix.
        
        This method types @isaiahdupree directly into the prompt field,
        which is the most reliable way to use the character.
        """
        full_prompt = f"@{CHARACTER} {prompt}"
        logger.info(f"📝 Setting prompt with @{CHARACTER}...")
        logger.info(f"   Full prompt: {full_prompt[:60]}...")
        
        js = f"""
            (function() {{
                var ta = document.querySelector('textarea');
                if (ta) {{
                    ta.focus();
                    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSetter.call(ta, '{full_prompt.replace("'", "\\'")}');
                    ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    return 'set';
                }}
                return 'not_found';
            }})()
        """
        result = self._run_js(js)
        success = "set" in result
        if success:
            logger.info("   ✅ Prompt set with @isaiahdupree")
        else:
            logger.error("   ❌ Failed to set prompt")
        return success
    
    def click_create_video(self) -> bool:
        """Click the Create Video button."""
        logger.info("🎬 Clicking Create Video...")
        js = """
            (function() {
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    var txt = btns[i].textContent.trim();
                    if (txt === 'Create video' || txt === 'Create') {
                        if (btns[i].disabled) return 'disabled';
                        btns[i].click();
                        return 'clicked';
                    }
                }
                return 'not_found';
            })()
        """
        result = self._run_js(js)
        success = "clicked" in result
        if success:
            logger.info("   ✅ Video generation started!")
        else:
            logger.error(f"   ❌ Failed: {result}")
        return success
    
    def get_drafts_count(self) -> int:
        """Get current video count from /drafts page."""
        # Navigate to drafts
        script = 'tell application "Safari" to set URL of front document to "https://sora.chatgpt.com/drafts"'
        self._run_applescript(script)
        time.sleep(3)
        
        # Scroll to load videos
        self._run_js("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        self._run_js("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # Count videos
        js = """
            (function() {
                var videos = document.querySelectorAll('video');
                return videos.length.toString();
            })()
        """
        result = self._run_js(js)
        try:
            return int(result)
        except:
            return 0
    
    def get_video_urls(self) -> list:
        """Get video source URLs from /drafts page."""
        js = """
            (function() {
                var videos = document.querySelectorAll('video');
                var urls = [];
                videos.forEach(function(v) {
                    var src = v.src || (v.querySelector('source') ? v.querySelector('source').src : '');
                    if (src) urls.push(src);
                });
                return JSON.stringify(urls);
            })()
        """
        result = self._run_js(js)
        try:
            import json
            return json.loads(result) if result.startswith('[') else []
        except:
            return []
    
    def download_video(self, url: str) -> Optional[str]:
        """Download video from URL."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"sora_{CHARACTER}_{timestamp}.mp4"
        local_path = DOWNLOAD_DIR / filename
        
        logger.info(f"📥 Downloading video...")
        
        try:
            result = subprocess.run(
                ['curl', '-L', '-o', str(local_path), url],
                capture_output=True,
                timeout=180
            )
            
            if local_path.exists() and local_path.stat().st_size > 10000:
                size_mb = local_path.stat().st_size / 1024 / 1024
                logger.info(f"   ✅ Downloaded: {filename} ({size_mb:.1f} MB)")
                return str(local_path)
            else:
                logger.error("   ❌ Download failed or file too small")
        except Exception as e:
            logger.error(f"   ❌ Download error: {e}")
        
        return None
    
    async def poll_for_completion(self, initial_count: int, timeout: int = MAX_TIMEOUT) -> Optional[str]:
        """Poll /drafts until new video appears, then download."""
        logger.info(f"⏳ Polling for completion (initial count: {initial_count})...")
        
        start_time = time.time()
        poll_num = 0
        
        while time.time() - start_time < timeout:
            poll_num += 1
            elapsed = int(time.time() - start_time)
            
            current_count = self.get_drafts_count()
            logger.info(f"   Poll #{poll_num}: {current_count} videos ({elapsed}s elapsed)")
            
            if current_count > initial_count:
                logger.info("   ✅ New video detected!")
                
                # Get the newest video URL
                urls = self.get_video_urls()
                if urls:
                    return self.download_video(urls[0])
                break
            
            await asyncio.sleep(POLL_INTERVAL)
        
        logger.warning("   ⚠️ Timeout - no new video detected")
        return None
    
    async def generate(self, prompt: str, wait_for_completion: bool = True) -> dict:
        """
        Full generation flow:
        1. Navigate to explore
        2. Check login
        3. Set prompt with @isaiahdupree
        4. Click Create Video
        5. Poll for completion (optional)
        6. Download when ready
        """
        result = {
            "success": False,
            "character": CHARACTER,
            "prompt": prompt,
            "video_path": None,
            "error": None
        }
        
        print("\n" + "="*60)
        print(f"🎬 SORA GENERATION WITH @{CHARACTER}")
        print("="*60)
        print(f"Prompt: {prompt[:60]}...")
        print("="*60 + "\n")
        
        # Step 1: Navigate
        self.navigate_to_explore()
        
        # Step 2: Check login
        if not self.check_login():
            result["error"] = "Not logged in"
            return result
        
        # Step 3: Get initial drafts count (for polling)
        if wait_for_completion:
            logger.info("📊 Getting initial drafts count...")
            initial_count = self.get_drafts_count()
            logger.info(f"   Initial count: {initial_count}")
            
            # Navigate back to explore
            self.navigate_to_explore()
        
        # Step 4: Set prompt with @isaiahdupree
        if not self.set_prompt_with_character(prompt):
            result["error"] = "Failed to set prompt"
            return result
        
        time.sleep(1)
        
        # Step 5: Click Create Video
        if not self.click_create_video():
            result["error"] = "Failed to click Create Video"
            return result
        
        result["success"] = True
        
        # Step 6: Poll for completion (optional)
        if wait_for_completion:
            print("\n" + "-"*60)
            print("Video generation started! Polling for completion...")
            print("This typically takes 8-12 minutes.")
            print("-"*60 + "\n")
            
            video_path = await self.poll_for_completion(initial_count)
            if video_path:
                result["video_path"] = video_path
        
        return result


async def main():
    """Main entry point."""
    # Get prompt from command line or use default
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = DEFAULT_PROMPT
        print(f"Using default prompt (pass custom prompt as argument)")
    
    generator = SoraIsaiahDupreeGenerator()
    result = await generator.generate(prompt, wait_for_completion=True)
    
    print("\n" + "="*60)
    if result["success"]:
        print("✅ GENERATION COMPLETE")
        if result["video_path"]:
            print(f"📁 Video saved: {result['video_path']}")
        else:
            print("⏳ Video is generating - check Sora activity page")
    else:
        print(f"❌ FAILED: {result['error']}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
