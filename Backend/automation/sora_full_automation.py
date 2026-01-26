#!/usr/bin/env python3
"""
Sora Full Automation - Complete control of Sora video generation via Safari

Features:
- All button controls (characters, styles, duration, aspect ratio)
- Queue management (max 3 concurrent videos)
- Polling for video completion
- Automatic video downloading
"""

import asyncio
import subprocess
import time
import os
import json
import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AspectRatio(Enum):
    PORTRAIT = "Portrait"   # 9:16
    LANDSCAPE = "Landscape"  # 16:9


class Duration(Enum):
    SHORT = 10
    MEDIUM = 15
    LONG = 25


@dataclass
class VideoJob:
    """Represents a video generation job"""
    prompt: str
    character: Optional[str] = None
    style: Optional[str] = None
    duration: int = 15
    aspect_ratio: str = "Portrait"
    status: str = "pending"  # pending, generating, completed, failed
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    local_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class SoraFullAutomation:
    """Complete Sora automation with queue management and downloading"""
    
    MAX_QUEUE_SIZE = 3
    DOWNLOAD_DIR = Path("/Users/isaiahdupree/Documents/CompetitorResearch/sora_downloads")
    POLL_INTERVAL = 30  # seconds
    
    def __init__(self):
        self.queue: List[VideoJob] = []
        self.completed: List[VideoJob] = []
        self.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
    def _run_applescript(self, script: str) -> Tuple[bool, str]:
        """Execute AppleScript and return (success, output)"""
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout.strip() or result.stderr.strip()
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "timeout"
        except Exception as e:
            return False, str(e)
    
    def _js(self, js_code: str) -> Tuple[bool, str]:
        """Execute JavaScript in Safari and return result"""
        script = f'''
        tell application "Safari"
            do JavaScript "{js_code.replace('"', '\\"').replace('\n', '\\n')}" in front document
        end tell
        '''
        return self._run_applescript(script)
    
    # =========================================================================
    # NAVIGATION
    # =========================================================================
    
    def navigate_to_explore(self) -> bool:
        """Navigate to Sora explore page"""
        script = '''
        tell application "Safari"
            activate
            set URL of front document to "https://sora.chatgpt.com/explore"
        end tell
        '''
        success, _ = self._run_applescript(script)
        time.sleep(3)
        return success
    
    def navigate_to_library(self) -> bool:
        """Navigate to Sora library (my videos)"""
        script = '''
        tell application "Safari"
            activate
            set URL of front document to "https://sora.chatgpt.com/library"
        end tell
        '''
        success, _ = self._run_applescript(script)
        time.sleep(3)
        return success
    
    def check_login(self) -> bool:
        """Check if logged into Sora"""
        js = """
            (function() {
                var profileBtn = document.querySelector('[aria-label=Profile], [data-testid=profile]');
                var loginBtn = Array.from(document.querySelectorAll('button')).find(b => 
                    b.textContent.toLowerCase().includes('log in') || 
                    b.textContent.toLowerCase().includes('sign in')
                );
                return profileBtn ? 'logged_in' : (loginBtn ? 'not_logged_in' : 'unknown');
            })()
        """
        success, output = self._js(js)
        return "logged_in" in output
    
    def get_usage(self) -> Dict:
        """
        Get Sora usage by clicking Settings > Settings menu > Usage tab.
        Returns dict with video_gens_left, free_count, paid_count, reset_date.
        
        Flow: Settings button (sidebar) -> Settings menuitem -> Usage tab
        """
        logger.info("Checking Sora usage...")
        
        # Step 1: Navigate to sora.chatgpt.com first
        script = '''
        tell application "Safari"
            activate
            set URL of front document to "https://sora.chatgpt.com"
        end tell
        '''
        self._run_applescript(script)
        time.sleep(2)
        
        # Step 2: Click Settings button in sidebar (has aria-haspopup="menu")
        # Must dispatch full mouse events for Radix UI to recognize click
        js_click_settings_btn = """
            (function() {
                var settingsBtn = document.querySelector('button[aria-label="Settings"]');
                if (settingsBtn) {
                    ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(function(type) {
                        settingsBtn.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
                    });
                    return 'clicked_settings_btn';
                }
                return 'settings_btn_not_found';
            })()
        """
        success, output = self._js(js_click_settings_btn)
        time.sleep(0.5)
        
        # Step 3: Click "Settings" menuitem in dropdown
        js_click_settings_menu = """
            (function() {
                var menuItems = document.querySelectorAll('[role=menuitem]');
                for (var i = 0; i < menuItems.length; i++) {
                    if (menuItems[i].textContent.trim() === 'Settings') {
                        menuItems[i].click();
                        return 'clicked_settings_menuitem';
                    }
                }
                return 'settings_menuitem_not_found';
            })()
        """
        success, output = self._js(js_click_settings_menu)
        time.sleep(1)
        
        # Step 4: Click "Usage" tab in User Settings dialog
        js_click_usage = """
            (function() {
                var dialog = document.querySelector('[role=dialog]');
                if (!dialog) return 'no_dialog';
                
                var btns = dialog.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].textContent.trim() === 'Usage') {
                        btns[i].focus();
                        btns[i].click();
                        return 'clicked_usage';
                    }
                }
                return 'usage_not_found';
            })()
        """
        success, output = self._js(js_click_usage)
        time.sleep(0.5)
        
        # Step 5: Extract usage information from dialog
        js_get_usage = """
            (function() {
                var result = {
                    video_gens_left: 0,
                    free_count: 0,
                    paid_count: 0,
                    reset_date: ''
                };
                
                var dialog = document.querySelector('[role=dialog]');
                var text = dialog ? dialog.innerText : document.body.innerText;
                
                // Parse "27 video gens left"
                var gensMatch = text.match(/(\\d+)\\s*video\\s*gens?\\s*left/i);
                if (gensMatch) result.video_gens_left = parseInt(gensMatch[1]);
                
                // Parse "27 free"
                var freeMatch = text.match(/(\\d+)\\s*free/i);
                if (freeMatch) result.free_count = parseInt(freeMatch[1]);
                
                // Parse "0 paid"
                var paidMatch = text.match(/(\\d+)\\s*paid/i);
                if (paidMatch) result.paid_count = parseInt(paidMatch[1]);
                
                // Parse "More available on Jan 26"
                var dateMatch = text.match(/available\\s+on\\s+([A-Za-z]+\\s*\\d+)/i);
                if (dateMatch) result.reset_date = dateMatch[1];
                
                return JSON.stringify(result);
            })()
        """
        success, output = self._js(js_get_usage)
        
        # Close dialog
        js_close = """
            (function() {
                var doneBtn = Array.from(document.querySelectorAll('button')).find(b => 
                    b.textContent.trim().toLowerCase() === 'done'
                );
                if (doneBtn) { doneBtn.click(); return 'closed'; }
                return 'no_done_btn';
            })()
        """
        self._js(js_close)
        
        try:
            result = json.loads(output) if output.startswith('{') else {}
            logger.info(f"Usage: {result.get('video_gens_left', '?')} video gens left, resets {result.get('reset_date', 'unknown')}")
            return result
        except:
            return {'error': 'Failed to parse usage', 'raw': output}
    
    # =========================================================================
    # CHARACTER CONTROLS
    # =========================================================================
    
    def get_available_characters(self) -> List[str]:
        """Get list of available character names"""
        # First click Characters tab
        self._js("document.querySelector('button').textContent.includes('Characters') && document.querySelector('button[textContent*=Characters]').click()")
        
        js = """
            (function() {
                var chars = [];
                // Click Characters tab first
                var tabs = document.querySelectorAll('button');
                tabs.forEach(function(t) {
                    if (t.textContent.trim() === 'Characters') t.click();
                });
                
                // Wait and collect character buttons
                setTimeout(function() {
                    document.querySelectorAll('button').forEach(function(b) {
                        var txt = b.textContent.trim();
                        // Character buttons are usually single words, lowercase
                        if (txt.length > 2 && txt.length < 30 && !txt.includes(' ') && 
                            txt !== 'Characters' && txt !== 'Styles' && txt !== 'Create') {
                            chars.push(txt);
                        }
                    });
                }, 500);
                return JSON.stringify(chars);
            })()
        """
        success, output = self._js(js)
        try:
            return json.loads(output) if output.startswith('[') else []
        except:
            return []
    
    def click_characters_tab(self) -> bool:
        """Click the Characters tab to show character options"""
        js = """
            (function() {
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].textContent.trim() === 'Characters') {
                        btns[i].click();
                        return 'clicked';
                    }
                }
                return 'not_found';
            })()
        """
        success, output = self._js(js)
        time.sleep(0.5)
        return "clicked" in output
    
    def select_character(self, character: str) -> bool:
        """Select a character by name (adds @character to prompt)"""
        logger.info(f"Selecting character: @{character}")
        
        # First ensure Characters tab is open
        self.click_characters_tab()
        time.sleep(0.5)
        
        js = f"""
            (function() {{
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {{
                    if (btns[i].textContent.trim() === '{character}') {{
                        btns[i].click();
                        return 'selected';
                    }}
                }}
                return 'not_found';
            }})()
        """
        success, output = self._js(js)
        time.sleep(0.5)
        return "selected" in output
    
    # =========================================================================
    # STYLE CONTROLS
    # =========================================================================
    
    def click_styles_tab(self) -> bool:
        """Click the Styles tab to show style options"""
        js = """
            (function() {
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    var txt = btns[i].textContent.trim();
                    if (txt === 'Styles' || txt === 'StylesNEW') {
                        btns[i].click();
                        return 'clicked';
                    }
                }
                return 'not_found';
            })()
        """
        success, output = self._js(js)
        time.sleep(0.5)
        return "clicked" in output
    
    def select_style(self, style: str) -> bool:
        """Select a style by name"""
        logger.info(f"Selecting style: {style}")
        
        self.click_styles_tab()
        time.sleep(0.5)
        
        js = f"""
            (function() {{
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {{
                    if (btns[i].textContent.trim().toLowerCase() === '{style.lower()}') {{
                        btns[i].click();
                        return 'selected';
                    }}
                }}
                return 'not_found';
            }})()
        """
        success, output = self._js(js)
        return "selected" in output
    
    # =========================================================================
    # DURATION CONTROLS
    # =========================================================================
    
    def set_duration(self, seconds: int) -> bool:
        """Set video duration (10, 15, or 25 seconds)"""
        if seconds not in [10, 15, 25]:
            logger.warning(f"Invalid duration {seconds}, must be 10, 15, or 25")
            return False
            
        logger.info(f"Setting duration to {seconds} seconds")
        
        # Click duration button to open menu
        js_open = """
            (function() {
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    var txt = btns[i].textContent.trim();
                    if (txt.match(/^\\d+s$/)) {
                        btns[i].click();
                        return 'opened';
                    }
                }
                return 'not_found';
            })()
        """
        self._js(js_open)
        time.sleep(0.5)
        
        # Select duration option
        js_select = f"""
            (function() {{
                var options = document.querySelectorAll('[role=menuitem], [role=option], [role=menuitemradio], [data-radix-collection-item]');
                for (var i = 0; i < options.length; i++) {{
                    var txt = options[i].textContent.trim();
                    if (txt.includes('{seconds} seconds')) {{
                        options[i].click();
                        return 'selected';
                    }}
                }}
                return 'not_found';
            }})()
        """
        success, output = self._js(js_select)
        return "selected" in output
    
    # =========================================================================
    # ASPECT RATIO CONTROLS
    # =========================================================================
    
    def set_aspect_ratio(self, ratio: str) -> bool:
        """Set aspect ratio (Portrait or Landscape)"""
        if ratio not in ["Portrait", "Landscape"]:
            logger.warning(f"Invalid aspect ratio {ratio}, must be Portrait or Landscape")
            return False
            
        logger.info(f"Setting aspect ratio to {ratio}")
        
        # Click aspect button to open menu
        js_open = """
            (function() {
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    var txt = btns[i].textContent.trim();
                    if (txt === 'Portrait' || txt === 'Landscape') {
                        btns[i].click();
                        return 'opened';
                    }
                }
                return 'not_found';
            })()
        """
        self._js(js_open)
        time.sleep(0.5)
        
        # Select aspect option
        js_select = f"""
            (function() {{
                var options = document.querySelectorAll('[role=menuitem], [role=option], [role=menuitemradio], [data-radix-collection-item]');
                for (var i = 0; i < options.length; i++) {{
                    if (options[i].textContent.trim() === '{ratio}') {{
                        options[i].click();
                        return 'selected';
                    }}
                }}
                return 'not_found';
            }})()
        """
        success, output = self._js(js_select)
        return "selected" in output
    
    # =========================================================================
    # PROMPT INPUT
    # =========================================================================
    
    def set_prompt(self, prompt: str) -> bool:
        """Set the prompt text in textarea"""
        logger.info(f"Setting prompt: {prompt[:50]}...")
        
        js = f"""
            (function() {{
                var ta = document.querySelector('textarea');
                if (ta) {{
                    ta.focus();
                    var currentVal = ta.value || '';
                    var newVal = currentVal + (currentVal ? ' ' : '') + '{prompt.replace("'", "\\'")}';
                    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSetter.call(ta, newVal);
                    ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    return 'set';
                }}
                return 'not_found';
            }})()
        """
        success, output = self._js(js)
        return "set" in output
    
    def clear_prompt(self) -> bool:
        """Clear the prompt textarea"""
        js = """
            (function() {
                var ta = document.querySelector('textarea');
                if (ta) {
                    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSetter.call(ta, '');
                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                    return 'cleared';
                }
                return 'not_found';
            })()
        """
        success, output = self._js(js)
        return "cleared" in output
    
    # =========================================================================
    # VIDEO GENERATION
    # =========================================================================
    
    def click_create_video(self) -> bool:
        """Click the Create video button"""
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
        success, output = self._js(js)
        logger.info(f"Create video button: {output}")
        return "clicked" in output
    
    # =========================================================================
    # QUEUE MANAGEMENT
    # =========================================================================
    
    def get_queue_count(self) -> int:
        """Get current number of videos generating"""
        js = """
            (function() {
                // Look for generating indicators
                var generating = document.querySelectorAll('[data-status=generating], .generating, [aria-label*=generating]');
                if (generating.length > 0) return generating.length.toString();
                
                // Check Activity page count
                var activityBadge = document.querySelector('[aria-label=Activity] span, button[aria-label=Activity] span');
                if (activityBadge && activityBadge.textContent.match(/\\d+/)) {
                    return activityBadge.textContent.match(/\\d+/)[0];
                }
                
                return '0';
            })()
        """
        success, output = self._js(js)
        try:
            return int(output)
        except:
            return 0
    
    def can_generate(self) -> bool:
        """Check if we can generate another video (queue not full)"""
        count = self.get_queue_count()
        can = count < self.MAX_QUEUE_SIZE
        logger.info(f"Queue: {count}/{self.MAX_QUEUE_SIZE} - Can generate: {can}")
        return can
    
    # =========================================================================
    # POLLING & STATUS
    # =========================================================================
    
    def get_generating_videos(self) -> List[Dict]:
        """Get list of currently generating videos from Activity"""
        # Navigate to activity if needed
        js = """
            (function() {
                var videos = [];
                
                // Look for video cards with generating status
                var cards = document.querySelectorAll('[data-video-id], .video-card, [class*=video]');
                cards.forEach(function(card) {
                    var status = card.querySelector('[class*=progress], [class*=generating], .status');
                    if (status) {
                        var id = card.getAttribute('data-video-id') || card.id || '';
                        var progress = status.textContent || '';
                        videos.push({id: id, progress: progress, status: 'generating'});
                    }
                });
                
                return JSON.stringify(videos);
            })()
        """
        success, output = self._js(js)
        try:
            return json.loads(output) if output.startswith('[') else []
        except:
            return []
    
    def get_completed_videos(self, scroll_count: int = 5) -> List[Dict]:
        """
        Get list of all videos from /drafts page (contains ALL videos).
        Note: /drafts only loads ~13 videos at a time, scroll to load more.
        """
        # Navigate to drafts
        script = '''
        tell application "Safari"
            set URL of front document to "https://sora.chatgpt.com/drafts"
        end tell
        '''
        self._run_applescript(script)
        time.sleep(3)
        
        # Scroll to load more videos (pagination)
        if scroll_count > 0:
            scroll_js = f"""
                (async function() {{
                    for (var i = 0; i < {scroll_count}; i++) {{
                        window.scrollTo(0, document.body.scrollHeight);
                        await new Promise(r => setTimeout(r, 500));
                    }}
                    window.scrollTo(0, 0);
                }})();
            """
            self._js(scroll_js)
            time.sleep(scroll_count * 0.6 + 1)
        
        # Get all video elements with their source URLs
        js = """
            (function() {
                var videos = document.querySelectorAll('video');
                var result = [];
                videos.forEach(function(v, i) {
                    var src = v.src || (v.querySelector('source') ? v.querySelector('source').src : '');
                    if (src) {
                        result.push({
                            index: i,
                            video_src: src,
                            id: 'draft_' + i
                        });
                    }
                });
                return JSON.stringify(result);
            })()
        """
        success, output = self._js(js)
        try:
            return json.loads(output) if output.startswith('[') else []
        except:
            return []
    
    def get_drafts_videos(self) -> List[Dict]:
        """Get all video URLs directly from /drafts page"""
        return self.get_completed_videos()  # Now uses drafts
    
    def get_video_by_index(self, index: int) -> Optional[Dict]:
        """Click on a video card by index and get its details"""
        js = f"""
            (function() {{
                var cards = document.querySelectorAll('div[class*=card], div[class*=video], [class*=thumbnail]');
                if (cards.length > {index}) {{
                    cards[{index}].click();
                    return 'clicked';
                }}
                return 'not_found';
            }})()
        """
        success, output = self._js(js)
        if "clicked" not in output:
            return None
        
        time.sleep(2)
        
        # Get video details from opened page
        js_details = """
            (function() {
                var url = window.location.href;
                var video = document.querySelector('video');
                var videoSrc = video ? (video.src || (video.querySelector('source') ? video.querySelector('source').src : '')) : '';
                return JSON.stringify({
                    page_url: url,
                    video_src: videoSrc,
                    id: url.match(/\\/p\\/([a-zA-Z0-9_-]+)/) ? url.match(/\\/p\\/([a-zA-Z0-9_-]+)/)[1] : ''
                });
            })()
        """
        success, output = self._js(js_details)
        try:
            return json.loads(output)
        except:
            return None
    
    async def poll_for_completion(self, timeout: int = 600) -> List[Dict]:
        """Poll until videos complete or timeout (default 10 min)"""
        logger.info(f"Polling for video completion (timeout: {timeout}s)...")
        
        start_time = time.time()
        initial_completed = set(v.get('id', '') for v in self.get_completed_videos())
        
        while time.time() - start_time < timeout:
            # Check if queue is empty (all done)
            queue_count = self.get_queue_count()
            
            if queue_count == 0:
                # Get newly completed videos
                current_completed = self.get_completed_videos()
                new_videos = [v for v in current_completed if v.get('id') not in initial_completed]
                
                if new_videos:
                    logger.info(f"✅ {len(new_videos)} video(s) completed!")
                    return new_videos
            
            elapsed = int(time.time() - start_time)
            logger.info(f"Polling... {queue_count} generating, {elapsed}s elapsed")
            await asyncio.sleep(self.POLL_INTERVAL)
        
        logger.warning("Polling timeout reached")
        return []
    
    # =========================================================================
    # DOWNLOADING
    # =========================================================================
    
    def download_video(self, video_id: str = None, video_index: int = None) -> Optional[str]:
        """
        Download a video and return local path.
        
        Can download by:
        - video_id: Direct page ID (e.g., 's_6971ff89b12c8191b74ed9fff82da687')
        - video_index: Index of video card on Profile page (0 = first/newest)
        """
        logger.info(f"Downloading video: id={video_id}, index={video_index}")
        
        video_src = None
        actual_id = video_id or f"idx_{video_index}"
        
        if video_index is not None:
            # Click on video card by index
            video_info = self.get_video_by_index(video_index)
            if video_info and video_info.get('video_src'):
                video_src = video_info['video_src']
                actual_id = video_info.get('id', actual_id)
        elif video_id:
            # Navigate to video page directly
            script = f'''
            tell application "Safari"
                set URL of front document to "https://sora.chatgpt.com/p/{video_id}"
            end tell
            '''
            self._run_applescript(script)
            time.sleep(3)
            
            # Get video source
            js = """
                (function() {
                    var video = document.querySelector('video');
                    if (video) {
                        return video.src || (video.querySelector('source') ? video.querySelector('source').src : '');
                    }
                    return '';
                })()
            """
            success, output = self._js(js)
            if output.startswith('http'):
                video_src = output
        
        if not video_src:
            # Try to get from current page
            js = """
                (function() {
                    var video = document.querySelector('video');
                    return video ? video.src : '';
                })()
            """
            success, output = self._js(js)
            if output.startswith('http'):
                video_src = output
        
        if video_src and video_src.startswith('http'):
            # Download using curl
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Sanitize ID for filename
            safe_id = actual_id.replace('/', '_')[:30]
            filename = f"sora_{safe_id}_{timestamp}.mp4"
            local_path = self.DOWNLOAD_DIR / filename
            
            logger.info(f"Downloading from: {video_src[:80]}...")
            
            try:
                result = subprocess.run(
                    ['curl', '-L', '-o', str(local_path), video_src],
                    capture_output=True,
                    timeout=180
                )
                if local_path.exists() and local_path.stat().st_size > 10000:
                    logger.info(f"✅ Downloaded: {local_path} ({local_path.stat().st_size / 1024 / 1024:.1f} MB)")
                    return str(local_path)
                else:
                    logger.error(f"Download failed or file too small")
            except Exception as e:
                logger.error(f"Download failed: {e}")
        
        logger.warning(f"Could not download video")
        return None
    
    def download_recent_videos(self, count: int = 3) -> List[str]:
        """Download the N most recent videos from /drafts page"""
        logger.info(f"Downloading {count} most recent videos from drafts...")
        
        # Get all videos from drafts (has direct URLs)
        videos = self.get_completed_videos()
        downloaded = []
        
        for i, video in enumerate(videos[:count]):
            video_src = video.get('video_src')
            if not video_src:
                continue
                
            logger.info(f"Downloading video {i+1}/{count}...")
            
            # Download directly using the source URL
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"sora_draft_{i}_{timestamp}.mp4"
            local_path = self.DOWNLOAD_DIR / filename
            
            try:
                result = subprocess.run(
                    ['curl', '-L', '-o', str(local_path), video_src],
                    capture_output=True,
                    timeout=180
                )
                if local_path.exists() and local_path.stat().st_size > 10000:
                    size_mb = local_path.stat().st_size / 1024 / 1024
                    logger.info(f"✅ Downloaded: {local_path} ({size_mb:.1f} MB)")
                    downloaded.append(str(local_path))
                else:
                    logger.error(f"Download failed or file too small")
            except Exception as e:
                logger.error(f"Download error: {e}")
        
        return downloaded
    
    def download_from_drafts(self, count: int = 3) -> List[str]:
        """Alias for download_recent_videos - downloads from /drafts"""
        return self.download_recent_videos(count)
    
    def download_all_recent(self, count: int = 3) -> List[str]:
        """Download most recent N completed videos"""
        videos = self.get_completed_videos()[:count]
        downloaded = []
        
        for video in videos:
            video_id = video.get('id')
            if video_id:
                path = self.download_video(video_id)
                if path:
                    downloaded.append(path)
        
        return downloaded
    
    # =========================================================================
    # HIGH-LEVEL WORKFLOW
    # =========================================================================
    
    async def generate_video(
        self,
        prompt: str,
        character: Optional[str] = None,
        style: Optional[str] = None,
        duration: int = 15,
        aspect_ratio: str = "Portrait",
        wait_for_slot: bool = True
    ) -> bool:
        """
        Generate a single video with all options.
        
        Args:
            prompt: Video description
            character: Character name (e.g., 'isaiahdupree')
            style: Style name (optional)
            duration: 10, 15, or 25 seconds
            aspect_ratio: 'Portrait' or 'Landscape'
            wait_for_slot: Wait if queue is full
        """
        logger.info(f"Generating video: {prompt[:40]}...")
        
        # Wait for queue slot if needed
        if wait_for_slot:
            while not self.can_generate():
                logger.info("Queue full, waiting for slot...")
                await asyncio.sleep(30)
        
        # Navigate to explore
        self.navigate_to_explore()
        time.sleep(2)
        
        # Clear any existing prompt
        self.clear_prompt()
        
        # Select character if specified
        if character:
            self.select_character(character)
            time.sleep(0.5)
        
        # Select style if specified
        if style:
            self.select_style(style)
            time.sleep(0.5)
        
        # Set duration (on Storyboard page)
        # Note: Duration/aspect may need Storyboard - skip for now as they have defaults
        
        # Set prompt
        self.set_prompt(prompt)
        time.sleep(0.5)
        
        # Click create
        if self.click_create_video():
            logger.info("✅ Video generation started!")
            return True
        else:
            logger.error("Failed to start generation")
            return False
    
    async def batch_generate(
        self,
        jobs: List[VideoJob],
        auto_download: bool = True
    ) -> List[str]:
        """
        Generate multiple videos respecting queue limit.
        
        Args:
            jobs: List of VideoJob objects
            auto_download: Download videos when complete
            
        Returns:
            List of local file paths for downloaded videos
        """
        logger.info(f"Starting batch generation of {len(jobs)} videos")
        downloaded = []
        
        for i, job in enumerate(jobs):
            logger.info(f"Processing job {i+1}/{len(jobs)}: {job.prompt[:30]}...")
            
            success = await self.generate_video(
                prompt=job.prompt,
                character=job.character,
                style=job.style,
                duration=job.duration,
                aspect_ratio=job.aspect_ratio,
                wait_for_slot=True
            )
            
            if success:
                job.status = "generating"
            else:
                job.status = "failed"
            
            # Small delay between submissions
            await asyncio.sleep(2)
        
        # Poll for completion
        if auto_download:
            logger.info("Waiting for videos to complete...")
            completed = await self.poll_for_completion(timeout=900)  # 15 min max
            
            # Download completed videos
            for video in completed:
                path = self.download_video(video.get('id'))
                if path:
                    downloaded.append(path)
        
        return downloaded


# =============================================================================
# CLI INTERFACE
# =============================================================================

async def main():
    """Test the full automation workflow"""
    automation = SoraFullAutomation()
    
    print("\n" + "="*60)
    print("SORA FULL AUTOMATION TEST")
    print("="*60)
    
    # Check login
    if not automation.check_login():
        print("❌ Not logged in - please log into Sora first")
        return
    
    print("✅ Logged in")
    
    # Check queue
    queue_count = automation.get_queue_count()
    print(f"Current queue: {queue_count}/{automation.MAX_QUEUE_SIZE}")
    
    # Test single video generation
    test_prompt = "doing a backflip through crashing ocean waves, slow motion, cinematic"
    
    print(f"\nGenerating test video with @isaiahdupree:")
    print(f"Prompt: {test_prompt}")
    
    success = await automation.generate_video(
        prompt=test_prompt,
        character="isaiahdupree",
        duration=15,
        aspect_ratio="Portrait"
    )
    
    if success:
        print("\n✅ Video generation started!")
        print("Polling for completion...")
        
        # Poll and download
        completed = await automation.poll_for_completion(timeout=300)
        
        if completed:
            print(f"\n✅ {len(completed)} video(s) completed!")
            for video in completed:
                path = automation.download_video(video.get('id'))
                if path:
                    print(f"Downloaded: {path}")
        else:
            print("No videos completed within timeout")
    else:
        print("❌ Failed to start generation")


if __name__ == "__main__":
    asyncio.run(main())
