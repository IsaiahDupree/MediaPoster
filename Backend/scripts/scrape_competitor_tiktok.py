#!/usr/bin/env python3
"""
Scrape TikTok competitor profile, download videos, and transcribe for analysis.
Usage: python scrape_competitor_tiktok.py pensacola_bigfoot
"""

import asyncio
import httpx
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import logging

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OUTPUT_BASE = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts")


@dataclass
class VideoInfo:
    video_id: str
    url: str
    caption: str
    play_count: int
    like_count: int
    comment_count: int
    share_count: int
    duration: int
    created_time: int
    cover_url: str
    play_url: str
    local_path: Optional[str] = None
    transcript: Optional[str] = None


class TikTokCompetitorScraper:
    def __init__(self, username: str):
        self.username = username.lstrip('@')
        self.output_dir = OUTPUT_BASE / self.username
        self.videos_dir = self.output_dir / "videos"
        self.transcripts_dir = self.output_dir / "transcripts"
        self.videos: List[VideoInfo] = []
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(exist_ok=True)
        self.transcripts_dir.mkdir(exist_ok=True)
        
    async def fetch_profile(self) -> Optional[Dict]:
        """Fetch user profile info"""
        logger.info(f"Fetching profile for @{self.username}...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://tiktok-scraper7.p.rapidapi.com/user/info",
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
                },
                params={"unique_id": self.username}
            )
            
            if response.status_code != 200:
                logger.error(f"Profile fetch failed: {response.status_code}")
                return None
                
            data = response.json()
            if data.get("data"):
                user = data["data"].get("user", {})
                stats = data["data"].get("stats", {})
                logger.info(f"✅ Found: {user.get('nickname')} - {stats.get('followerCount', 0):,} followers, {stats.get('videoCount', 0)} videos")
                return data["data"]
            return None
    
    async def fetch_all_videos(self, max_videos: int = 100) -> List[VideoInfo]:
        """Fetch all videos from profile using pagination"""
        logger.info(f"Fetching videos for @{self.username}...")
        
        all_videos = []
        cursor = "0"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            while len(all_videos) < max_videos:
                response = await client.get(
                    "https://tiktok-scraper7.p.rapidapi.com/user/posts",
                    headers={
                        "X-RapidAPI-Key": RAPIDAPI_KEY,
                        "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
                    },
                    params={
                        "unique_id": self.username,
                        "count": 30,
                        "cursor": cursor
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Video fetch failed: {response.status_code}")
                    break
                    
                data = response.json()
                videos = data.get("data", {}).get("videos", [])
                
                if not videos:
                    logger.info("No more videos found")
                    break
                
                for v in videos:
                    video_info = VideoInfo(
                        video_id=v.get("video_id", ""),
                        url=f"https://www.tiktok.com/@{self.username}/video/{v.get('video_id', '')}",
                        caption=v.get("title", ""),
                        play_count=v.get("play_count", 0),
                        like_count=v.get("digg_count", 0),
                        comment_count=v.get("comment_count", 0),
                        share_count=v.get("share_count", 0),
                        duration=v.get("duration", 0),
                        created_time=v.get("create_time", 0),
                        cover_url=v.get("cover", ""),
                        play_url=v.get("play", "") or v.get("wmplay", "")
                    )
                    all_videos.append(video_info)
                
                logger.info(f"  Fetched {len(all_videos)} videos so far...")
                
                # Check for more
                has_more = data.get("data", {}).get("hasMore", False)
                cursor = str(data.get("data", {}).get("cursor", "0"))
                
                if not has_more:
                    break
                    
                await asyncio.sleep(0.5)  # Rate limiting
        
        self.videos = all_videos
        logger.info(f"✅ Total videos fetched: {len(all_videos)}")
        return all_videos
    
    async def download_video(self, video: VideoInfo) -> bool:
        """Download a single video"""
        if not video.play_url:
            logger.warning(f"No play URL for video {video.video_id}")
            return False
            
        filename = f"{video.video_id}.mp4"
        filepath = self.videos_dir / filename
        
        if filepath.exists():
            logger.info(f"  ⏭️  Already exists: {filename}")
            video.local_path = str(filepath)
            return True
        
        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                response = await client.get(video.play_url)
                
                if response.status_code == 200:
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    
                    size_mb = filepath.stat().st_size / (1024 * 1024)
                    logger.info(f"  ✅ Downloaded: {filename} ({size_mb:.1f} MB)")
                    video.local_path = str(filepath)
                    return True
                else:
                    logger.error(f"  ❌ Download failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"  ❌ Error downloading {video.video_id}: {e}")
            return False
    
    async def download_all_videos(self) -> int:
        """Download all videos"""
        logger.info(f"Downloading {len(self.videos)} videos...")
        
        success_count = 0
        for i, video in enumerate(self.videos):
            logger.info(f"[{i+1}/{len(self.videos)}] Downloading {video.video_id}...")
            if await self.download_video(video):
                success_count += 1
            await asyncio.sleep(0.3)  # Rate limiting
        
        logger.info(f"✅ Downloaded {success_count}/{len(self.videos)} videos")
        return success_count
    
    async def transcribe_video(self, video: VideoInfo) -> Optional[str]:
        """Transcribe a video using OpenAI Whisper API"""
        if not video.local_path or not Path(video.local_path).exists():
            return None
            
        transcript_file = self.transcripts_dir / f"{video.video_id}.txt"
        
        if transcript_file.exists():
            logger.info(f"  ⏭️  Transcript exists: {video.video_id}")
            video.transcript = transcript_file.read_text()
            return video.transcript
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(video.local_path, "rb") as f:
                    files = {"file": (f"{video.video_id}.mp4", f, "video/mp4")}
                    data = {"model": "whisper-1"}
                    
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                        files=files,
                        data=data
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        transcript = result.get("text", "")
                        
                        # Save transcript
                        transcript_file.write_text(transcript)
                        video.transcript = transcript
                        
                        logger.info(f"  ✅ Transcribed: {video.video_id} ({len(transcript)} chars)")
                        return transcript
                    else:
                        logger.error(f"  ❌ Transcription failed: {response.status_code} - {response.text}")
                        return None
                        
        except Exception as e:
            logger.error(f"  ❌ Error transcribing {video.video_id}: {e}")
            return None
    
    async def transcribe_all_videos(self) -> int:
        """Transcribe all downloaded videos"""
        videos_with_files = [v for v in self.videos if v.local_path]
        logger.info(f"Transcribing {len(videos_with_files)} videos...")
        
        success_count = 0
        for i, video in enumerate(videos_with_files):
            logger.info(f"[{i+1}/{len(videos_with_files)}] Transcribing {video.video_id}...")
            if await self.transcribe_video(video):
                success_count += 1
            await asyncio.sleep(0.5)  # Rate limiting for OpenAI
        
        logger.info(f"✅ Transcribed {success_count}/{len(videos_with_files)} videos")
        return success_count
    
    def save_manifest(self):
        """Save video manifest with all metadata"""
        manifest_path = self.output_dir / "manifest.json"
        
        manifest = {
            "username": self.username,
            "scraped_at": datetime.now().isoformat(),
            "total_videos": len(self.videos),
            "videos": [asdict(v) for v in self.videos]
        }
        
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"✅ Saved manifest to {manifest_path}")
    
    def generate_analysis_report(self) -> str:
        """Generate analysis report of all transcripts"""
        videos_with_transcripts = [v for v in self.videos if v.transcript]
        
        if not videos_with_transcripts:
            return "No transcripts available for analysis"
        
        # Sort by views
        videos_with_transcripts.sort(key=lambda x: x.play_count, reverse=True)
        
        report_lines = [
            f"# Content Analysis: @{self.username}",
            f"## Overview",
            f"- Total videos: {len(self.videos)}",
            f"- Transcribed: {len(videos_with_transcripts)}",
            f"- Total views: {sum(v.play_count for v in self.videos):,}",
            f"- Avg views: {sum(v.play_count for v in self.videos) // len(self.videos):,}",
            "",
            "## Top Performing Videos (by views)",
            ""
        ]
        
        for i, video in enumerate(videos_with_transcripts[:10]):
            report_lines.extend([
                f"### #{i+1}: {video.play_count:,} views",
                f"**Duration:** {video.duration}s | **Likes:** {video.like_count:,} | **Comments:** {video.comment_count:,}",
                f"**Caption:** {video.caption[:200]}..." if len(video.caption) > 200 else f"**Caption:** {video.caption}",
                f"**Transcript:**",
                f"```",
                video.transcript[:500] + "..." if len(video.transcript) > 500 else video.transcript,
                f"```",
                ""
            ])
        
        # Add all transcripts section
        report_lines.extend([
            "",
            "## All Transcripts (for pattern analysis)",
            ""
        ])
        
        for video in videos_with_transcripts:
            report_lines.extend([
                f"---",
                f"### Video {video.video_id} ({video.play_count:,} views, {video.duration}s)",
                f"**Caption:** {video.caption}",
                f"**Transcript:**",
                video.transcript,
                ""
            ])
        
        report = "\n".join(report_lines)
        
        # Save report
        report_path = self.output_dir / "analysis_report.md"
        report_path.write_text(report)
        logger.info(f"✅ Saved analysis report to {report_path}")
        
        return report


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scrape_competitor_tiktok.py <username>")
        print("Example: python scrape_competitor_tiktok.py pensacola_bigfoot")
        sys.exit(1)
    
    username = sys.argv[1].lstrip('@')
    
    if not RAPIDAPI_KEY:
        print("❌ RAPIDAPI_KEY not set in .env")
        sys.exit(1)
    
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not set in .env")
        sys.exit(1)
    
    scraper = TikTokCompetitorScraper(username)
    
    # Step 1: Fetch profile
    profile = await scraper.fetch_profile()
    if not profile:
        print(f"❌ Could not find profile for @{username}")
        sys.exit(1)
    
    # Step 2: Fetch all videos
    await scraper.fetch_all_videos(max_videos=200)
    
    if not scraper.videos:
        print(f"❌ No videos found for @{username}")
        sys.exit(1)
    
    # Step 3: Download videos
    await scraper.download_all_videos()
    
    # Step 4: Transcribe videos
    await scraper.transcribe_all_videos()
    
    # Step 5: Save manifest
    scraper.save_manifest()
    
    # Step 6: Generate analysis report
    report = scraper.generate_analysis_report()
    
    print("\n" + "="*60)
    print(f"✅ COMPLETE: @{username}")
    print(f"   Videos: {len(scraper.videos)}")
    print(f"   Downloaded: {len([v for v in scraper.videos if v.local_path])}")
    print(f"   Transcribed: {len([v for v in scraper.videos if v.transcript])}")
    print(f"   Output: {scraper.output_dir}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
