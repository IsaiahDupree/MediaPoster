"""
Posted Content Matcher Service
Scrapes posted content from social platforms and cross-references with local library
to prevent posting duplicate content.
"""
import asyncio
import subprocess
import json
import re
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from difflib import SequenceMatcher
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Import the existing Safari controller from TikTok automation
from automation.safari_app_controller import SafariAppController

# RapidAPI configuration
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")


@dataclass
class PostedVideo:
    """Represents a video posted on a social platform"""
    platform: str  # 'tiktok', 'instagram', 'youtube'
    url: str
    video_id: str
    username: str
    transcript: Optional[str] = None
    caption: Optional[str] = None
    posted_at: Optional[datetime] = None


@dataclass
class MatchResult:
    """Result of matching a posted video to local library"""
    posted_video: PostedVideo
    local_video_id: Optional[str]
    local_filename: Optional[str]
    similarity_score: float
    match_type: str  # 'exact', 'high', 'likely', 'no_match'
    transcript_preview: str


class SafariPostedContentScraper:
    """
    Scrapes posted content URLs from social platforms using Safari.
    Uses the existing SafariAppController from TikTok automation for consistency.
    """
    
    def __init__(self):
        self.collected_urls: Dict[str, List[str]] = {
            'tiktok': [],
            'instagram': [],
            'youtube': []
        }
        # Use existing Safari controller from TikTok automation
        self.safari = SafariAppController()
    
    def _run_applescript(self, script: str, timeout: int = 30) -> str:
        """Execute AppleScript using the shared Safari controller."""
        return self.safari._run_applescript(script, timeout)
    
    def open_safari(self) -> bool:
        """Open Safari browser."""
        script = '''
        tell application "Safari"
            activate
        end tell
        '''
        self._run_applescript(script)
        time.sleep(1)
        return True
    
    def navigate_to_url(self, url: str) -> bool:
        """Navigate Safari to a URL."""
        script = f'''
        tell application "Safari"
            activate
            if (count of windows) = 0 then
                make new document
            end if
            set URL of front document to "{url}"
        end tell
        '''
        self._run_applescript(script)
        time.sleep(3)
        return True
    
    def execute_javascript(self, js_code: str) -> str:
        """Execute JavaScript in Safari."""
        js_escaped = js_code.replace('\\', '\\\\').replace('"', '\\"')
        script = f'''
tell application "Safari"
    if (count of windows) > 0 then
        return do JavaScript "{js_escaped}" in front document
    end if
    return ""
end tell
'''
        return self._run_applescript(script)
    
    def scroll_page(self) -> None:
        """Scroll the page down."""
        self.execute_javascript("window.scrollBy(0, window.innerHeight);")
        time.sleep(1.5)
    
    async def scrape_tiktok_profile(self, username: str, max_videos: int = 100) -> List[str]:
        """Scrape video URLs from a TikTok profile."""
        logger.info(f"Scraping TikTok profile: @{username}")
        
        self.open_safari()
        self.navigate_to_url(f"https://www.tiktok.com/@{username}")
        time.sleep(4)
        
        # Check if logged in / profile loads
        urls = []
        last_count = 0
        no_change_count = 0
        
        while len(urls) < max_videos and no_change_count < 5:
            # Collect video URLs
            js_code = '''
            (function() {
                var links = document.querySelectorAll('a[href*="/video/"]');
                var urls = [];
                links.forEach(function(link) {
                    var href = link.getAttribute('href');
                    if (href && href.includes('/video/') && !urls.includes(href)) {
                        if (!href.startsWith('http')) {
                            href = 'https://www.tiktok.com' + href;
                        }
                        urls.push(href);
                    }
                });
                return JSON.stringify(urls);
            })();
            '''
            result = self.execute_javascript(js_code)
            try:
                new_urls = json.loads(result) if result else []
                for url in new_urls:
                    if url not in urls:
                        urls.append(url)
            except:
                pass
            
            # Scroll to load more
            for _ in range(3):
                self.scroll_page()
            
            if len(urls) == last_count:
                no_change_count += 1
            else:
                no_change_count = 0
                last_count = len(urls)
            
            logger.info(f"Collected {len(urls)} TikTok URLs...")
        
        self.collected_urls['tiktok'] = urls
        return urls
    
    async def scrape_instagram_profile(self, username: str, max_videos: int = 100) -> List[str]:
        """Scrape video/reel URLs from an Instagram profile."""
        logger.info(f"Scraping Instagram profile: @{username}")
        
        self.open_safari()
        self.navigate_to_url(f"https://www.instagram.com/{username}/reels/")
        time.sleep(4)
        
        urls = []
        last_count = 0
        no_change_count = 0
        
        while len(urls) < max_videos and no_change_count < 5:
            js_code = '''
            (function() {
                var links = document.querySelectorAll('a[href*="/reel/"], a[href*="/p/"]');
                var urls = [];
                links.forEach(function(link) {
                    var href = link.getAttribute('href');
                    if (href && !urls.includes(href)) {
                        urls.push('https://www.instagram.com' + href);
                    }
                });
                return JSON.stringify(urls);
            })();
            '''
            result = self.execute_javascript(js_code)
            try:
                new_urls = json.loads(result) if result else []
                for url in new_urls:
                    if url not in urls:
                        urls.append(url)
            except:
                pass
            
            for _ in range(3):
                self.scroll_page()
            
            if len(urls) == last_count:
                no_change_count += 1
            else:
                no_change_count = 0
                last_count = len(urls)
            
            logger.info(f"Collected {len(urls)} Instagram URLs...")
        
        self.collected_urls['instagram'] = urls
        return urls


class PostedContentMatcher:
    """Matches posted content with local library to detect duplicates"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scraper = SafariPostedContentScraper()
    
    def _normalize_transcript(self, transcript: str) -> str:
        """Normalize transcript for comparison."""
        if not transcript:
            return ""
        normalized = " ".join(transcript.lower().split())
        for char in ".,!?;:'\"()-":
            normalized = normalized.replace(char, "")
        return normalized
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two texts."""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()
    
    async def get_local_transcripts(self, min_length: int = 30) -> List[Dict[str, Any]]:
        """Fetch all transcripts from local library."""
        query = text("""
            SELECT 
                v.id,
                v.file_name,
                va.transcript,
                va.curation_status
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.transcript IS NOT NULL 
              AND LENGTH(va.transcript) > :min_length
        """)
        
        result = await self.db.execute(query, {"min_length": min_length})
        rows = result.fetchall()
        
        return [
            {
                "id": str(row[0]),
                "filename": row[1],
                "transcript": row[2],
                "normalized": self._normalize_transcript(row[2]),
                "curation_status": row[3]
            }
            for row in rows
        ]
    
    async def match_transcript_to_library(
        self, 
        transcript: str, 
        local_transcripts: List[Dict[str, Any]],
        threshold: float = 0.80
    ) -> Optional[Dict[str, Any]]:
        """Find best matching local video for a transcript."""
        if not transcript or len(transcript) < 20:
            return None
        
        normalized = self._normalize_transcript(transcript)
        best_match = None
        best_score = 0.0
        
        for local in local_transcripts:
            if not local["normalized"]:
                continue
            
            # Quick length check to skip obviously different transcripts
            len_ratio = min(len(normalized), len(local["normalized"])) / max(len(normalized), len(local["normalized"]), 1)
            if len_ratio < 0.3:
                continue
            
            score = self._calculate_similarity(normalized, local["normalized"])
            if score > best_score:
                best_score = score
                best_match = local
        
        if best_score >= threshold:
            return {
                "local_video_id": best_match["id"],
                "local_filename": best_match["filename"],
                "similarity_score": best_score,
                "match_type": "exact" if best_score >= 0.95 else "high" if best_score >= 0.85 else "likely"
            }
        
        return None
    
    async def mark_video_as_posted(
        self, 
        local_video_id: str, 
        platform: str, 
        posted_url: str
    ) -> bool:
        """Mark a local video as already posted to a platform."""
        try:
            # Update curation_status to include posting info
            await self.db.execute(
                text("""
                    UPDATE video_analysis 
                    SET curation_status = 'already_posted',
                        visual_analysis = COALESCE(visual_analysis, '{}'::jsonb) || 
                            jsonb_build_object('posted_platforms', 
                                COALESCE(visual_analysis->'posted_platforms', '[]'::jsonb) || 
                                jsonb_build_array(jsonb_build_object('platform', :platform, 'url', :url, 'matched_at', :matched_at))
                            )
                    WHERE video_id = CAST(:video_id AS uuid)
                """),
                {
                    "video_id": local_video_id,
                    "platform": platform,
                    "url": posted_url,
                    "matched_at": datetime.now().isoformat()
                }
            )
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking video as posted: {e}")
            return False
    
    async def get_already_posted_videos(self) -> List[Dict[str, Any]]:
        """Get list of videos already marked as posted."""
        query = text("""
            SELECT 
                v.id,
                v.file_name,
                va.visual_analysis->'posted_platforms' as posted_platforms,
                va.curation_status
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.curation_status = 'already_posted'
               OR va.visual_analysis->'posted_platforms' IS NOT NULL
        """)
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        return [
            {
                "id": str(row[0]),
                "filename": row[1],
                "posted_platforms": row[2],
                "curation_status": row[3]
            }
            for row in rows
        ]
    
    async def scrape_and_match_tiktok(
        self, 
        username: str, 
        max_videos: int = 50
    ) -> Dict[str, Any]:
        """Scrape TikTok profile and match with local library."""
        # Scrape URLs
        urls = await self.scraper.scrape_tiktok_profile(username, max_videos)
        
        # Get local transcripts
        local_transcripts = await self.get_local_transcripts()
        
        matches = []
        unmatched = []
        
        # For now, just return the URLs - transcript fetching would require RapidAPI
        for url in urls:
            video_id = re.search(r'/video/(\d+)', url)
            if video_id:
                unmatched.append({
                    "url": url,
                    "video_id": video_id.group(1),
                    "platform": "tiktok"
                })
        
        return {
            "platform": "tiktok",
            "username": username,
            "total_scraped": len(urls),
            "urls": urls,
            "matches": matches,
            "unmatched": unmatched,
            "local_transcripts_available": len(local_transcripts)
        }
    
    async def scrape_and_match_instagram(
        self, 
        username: str, 
        max_videos: int = 50
    ) -> Dict[str, Any]:
        """Scrape Instagram profile and match with local library."""
        urls = await self.scraper.scrape_instagram_profile(username, max_videos)
        local_transcripts = await self.get_local_transcripts()
        
        matches = []
        unmatched = []
        
        for url in urls:
            shortcode = re.search(r'/(?:reel|p)/([A-Za-z0-9_-]+)', url)
            if shortcode:
                unmatched.append({
                    "url": url,
                    "shortcode": shortcode.group(1),
                    "platform": "instagram"
                })
        
        return {
            "platform": "instagram",
            "username": username,
            "total_scraped": len(urls),
            "urls": urls,
            "matches": matches,
            "unmatched": unmatched,
            "local_transcripts_available": len(local_transcripts)
        }


async def fetch_tiktok_transcript_via_api(video_id: str) -> Optional[str]:
    """Fetch transcript for a TikTok video via RapidAPI."""
    import httpx
    
    if not RAPIDAPI_KEY:
        logger.warning("RAPIDAPI_KEY not set")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://tiktok-scraper7.p.rapidapi.com/video/info",
                params={"video_id": video_id},
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Try to get description/caption as proxy for transcript
                return data.get("data", {}).get("desc", "")
    except Exception as e:
        logger.error(f"Error fetching TikTok transcript: {e}")
    
    return None
