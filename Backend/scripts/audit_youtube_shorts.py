#!/usr/bin/env python3
"""
YouTube Shorts Audit Script
============================
Fetches all shorts from your YouTube channel, gets transcripts,
and compares against local video transcripts to:
1. Detect duplicate/already-posted content
2. Create associations between YouTube posts and local videos
3. Update the posted_content table with matches

Usage:
    python scripts/audit_youtube_shorts.py [--channel-id CHANNEL_ID] [--dry-run]
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass
import httpx
from loguru import logger
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# YouTube transcript API
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
    HAS_TRANSCRIPT_API = True
except ImportError:
    HAS_TRANSCRIPT_API = False
    logger.warning("youtube_transcript_api not installed - transcripts will not be fetched")

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UCnDBsELI2OlaEl5yxA77HNA")

# Similarity thresholds
EXACT_MATCH_THRESHOLD = 0.95
HIGH_MATCH_THRESHOLD = 0.80
LIKELY_MATCH_THRESHOLD = 0.60


@dataclass
class YouTubeShort:
    video_id: str
    title: str
    description: str
    published_at: str
    thumbnail_url: str
    duration_seconds: int
    view_count: int
    like_count: int
    comment_count: int
    transcript: Optional[str] = None
    url: str = ""
    
    def __post_init__(self):
        self.url = f"https://www.youtube.com/shorts/{self.video_id}"


@dataclass
class LocalVideo:
    id: str
    filename: str
    title: str
    transcript: Optional[str]
    topics: List[str]
    pre_social_score: float


@dataclass
class MatchResult:
    youtube_short: YouTubeShort
    local_video: Optional[LocalVideo]
    similarity_score: float
    match_type: str  # 'exact', 'high', 'likely', 'no_match'
    matched_on: str  # 'transcript', 'title', 'none'


class YouTubeShortsAuditor:
    def __init__(self, channel_id: str = None, dry_run: bool = False):
        self.channel_id = channel_id or YOUTUBE_CHANNEL_ID
        self.api_key = YOUTUBE_API_KEY
        self.dry_run = dry_run
        self.engine = create_engine(DATABASE_URL)
        self.shorts: List[YouTubeShort] = []
        self.local_videos: List[LocalVideo] = []
        self.matches: List[MatchResult] = []
        
        if not self.api_key:
            logger.error("YOUTUBE_API_KEY not set!")
            sys.exit(1)
    
    async def fetch_channel_shorts(self, max_results: int = 100) -> List[YouTubeShort]:
        """Fetch all shorts from the YouTube channel"""
        logger.info(f"Fetching shorts from channel {self.channel_id}...")
        
        shorts = []
        next_page_token = None
        
        async with httpx.AsyncClient(timeout=30) as client:
            while len(shorts) < max_results:
                # First, search for shorts
                params = {
                    "part": "snippet",
                    "channelId": self.channel_id,
                    "type": "video",
                    "maxResults": min(50, max_results - len(shorts)),
                    "order": "date",
                    "key": self.api_key,
                }
                
                if next_page_token:
                    params["pageToken"] = next_page_token
                
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                video_ids = [item["id"]["videoId"] for item in data.get("items", []) if "videoId" in item.get("id", {})]
                
                if not video_ids:
                    break
                
                # Get video details to check duration (shorts are <= 60s)
                video_response = await client.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={
                        "part": "snippet,contentDetails,statistics",
                        "id": ",".join(video_ids),
                        "key": self.api_key,
                    }
                )
                
                if video_response.status_code == 200:
                    video_data = video_response.json()
                    for video in video_data.get("items", []):
                        duration = self._parse_duration(video.get("contentDetails", {}).get("duration", "PT0S"))
                        
                        # Only include shorts (<=60 seconds)
                        if duration <= 60:
                            snippet = video.get("snippet", {})
                            stats = video.get("statistics", {})
                            
                            shorts.append(YouTubeShort(
                                video_id=video["id"],
                                title=snippet.get("title", ""),
                                description=snippet.get("description", "")[:500],
                                published_at=snippet.get("publishedAt", ""),
                                thumbnail_url=snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                                duration_seconds=duration,
                                view_count=int(stats.get("viewCount", 0)),
                                like_count=int(stats.get("likeCount", 0)),
                                comment_count=int(stats.get("commentCount", 0)),
                            ))
                
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    break
        
        logger.info(f"Found {len(shorts)} shorts on channel")
        self.shorts = shorts
        return shorts
    
    def _parse_duration(self, duration_iso: str) -> int:
        """Parse ISO 8601 duration to seconds"""
        import re
        if not duration_iso:
            return 0
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds
    
    def fetch_transcripts(self):
        """Fetch transcripts for all shorts using youtube_transcript_api"""
        if not HAS_TRANSCRIPT_API:
            logger.warning("Skipping transcript fetch - youtube_transcript_api not available")
            return
        
        logger.info(f"Fetching transcripts for {len(self.shorts)} shorts...")
        
        fetched = 0
        failed = 0
        
        for short in self.shorts:
            try:
                # Use the fetch method (newer API)
                ytt_api = YouTubeTranscriptApi()
                transcript_list = ytt_api.fetch(short.video_id)
                # Combine all transcript segments
                short.transcript = " ".join([t.text for t in transcript_list])
                fetched += 1
                logger.debug(f"Got transcript for {short.video_id}: {len(short.transcript)} chars")
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                logger.debug(f"No transcript for {short.video_id}: {e}")
                failed += 1
            except Exception as e:
                logger.debug(f"Transcript unavailable for {short.video_id}: {type(e).__name__}")
                failed += 1
        
        logger.info(f"Fetched {fetched} transcripts, {failed} failed/unavailable")
    
    def load_local_videos(self):
        """Load local videos with transcripts from database"""
        logger.info("Loading local videos from database...")
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT v.id, v.file_name, COALESCE(v.title, v.file_name) as title,
                       va.transcript, va.topics, va.pre_social_score
                FROM videos v
                INNER JOIN video_analysis va ON v.id = va.video_id
                WHERE va.transcript IS NOT NULL 
                  AND LENGTH(va.transcript) > 20
                  AND (
                      LOWER(v.file_name) LIKE '%.mov' OR
                      LOWER(v.file_name) LIKE '%.mp4' OR
                      LOWER(v.file_name) LIKE '%.m4v'
                  )
                ORDER BY va.pre_social_score DESC
            """)).fetchall()
            
            self.local_videos = [
                LocalVideo(
                    id=str(row[0]),
                    filename=row[1],
                    title=row[2],
                    transcript=row[3],
                    topics=list(row[4]) if row[4] else [],
                    pre_social_score=float(row[5]) if row[5] else 0
                )
                for row in result
            ]
        
        logger.info(f"Loaded {len(self.local_videos)} local videos with transcripts")
    
    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        # Use SequenceMatcher for similarity
        return SequenceMatcher(None, t1, t2).ratio()
    
    def match_shorts_to_local(self):
        """Match YouTube shorts to local videos based on transcript similarity"""
        logger.info("Matching shorts to local videos...")
        
        self.matches = []
        
        for short in self.shorts:
            best_match: Optional[LocalVideo] = None
            best_score = 0.0
            matched_on = "none"
            
            # Try transcript matching first
            if short.transcript:
                for local in self.local_videos:
                    if local.transcript:
                        score = self._similarity(short.transcript, local.transcript)
                        if score > best_score:
                            best_score = score
                            best_match = local
                            matched_on = "transcript"
            
            # If no good transcript match, try title matching
            if best_score < LIKELY_MATCH_THRESHOLD:
                for local in self.local_videos:
                    # Compare title and first topic
                    title_score = self._similarity(short.title, local.title)
                    if title_score > best_score:
                        best_score = title_score
                        best_match = local
                        matched_on = "title"
            
            # Determine match type
            if best_score >= EXACT_MATCH_THRESHOLD:
                match_type = "exact"
            elif best_score >= HIGH_MATCH_THRESHOLD:
                match_type = "high"
            elif best_score >= LIKELY_MATCH_THRESHOLD:
                match_type = "likely"
            else:
                match_type = "no_match"
                best_match = None
            
            self.matches.append(MatchResult(
                youtube_short=short,
                local_video=best_match,
                similarity_score=best_score,
                match_type=match_type,
                matched_on=matched_on
            ))
        
        # Summary
        exact = sum(1 for m in self.matches if m.match_type == "exact")
        high = sum(1 for m in self.matches if m.match_type == "high")
        likely = sum(1 for m in self.matches if m.match_type == "likely")
        no_match = sum(1 for m in self.matches if m.match_type == "no_match")
        
        logger.info(f"Match results: {exact} exact, {high} high, {likely} likely, {no_match} no match")
    
    def save_associations(self):
        """Save matched associations to posted_content table"""
        if self.dry_run:
            logger.info("[DRY RUN] Would save associations...")
            return
        
        logger.info("Saving associations to database...")
        
        saved = 0
        with self.engine.connect() as conn:
            for match in self.matches:
                if match.match_type in ["exact", "high", "likely"] and match.local_video:
                    try:
                        # Check if already exists
                        existing = conn.execute(text("""
                            SELECT id FROM posted_content 
                            WHERE platform_post_id = :post_id AND platform = 'youtube'
                        """), {"post_id": match.youtube_short.video_id}).fetchone()
                        
                        if existing:
                            # Update with local association (media_id column)
                            conn.execute(text("""
                                UPDATE posted_content 
                                SET media_id = :media_id,
                                    views = :views,
                                    likes = :likes,
                                    comments = :comments,
                                    updated_at = NOW()
                                WHERE platform_post_id = :post_id AND platform = 'youtube'
                            """), {
                                "media_id": match.local_video.id,
                                "views": match.youtube_short.view_count,
                                "likes": match.youtube_short.like_count,
                                "comments": match.youtube_short.comment_count,
                                "post_id": match.youtube_short.video_id
                            })
                            saved += 1
                        else:
                            # Insert new record using correct schema
                            conn.execute(text("""
                                INSERT INTO posted_content (
                                    platform, platform_post_id, platform_url,
                                    caption, media_id,
                                    views, likes, comments,
                                    posted_at, status, created_at, updated_at
                                ) VALUES (
                                    'youtube', :post_id, :url,
                                    :caption, :media_id,
                                    :views, :likes, :comments,
                                    :posted_at, 'matched', NOW(), NOW()
                                )
                            """), {
                                "post_id": match.youtube_short.video_id,
                                "url": match.youtube_short.url,
                                "caption": match.youtube_short.title[:500],
                                "media_id": match.local_video.id,
                                "views": match.youtube_short.view_count,
                                "likes": match.youtube_short.like_count,
                                "comments": match.youtube_short.comment_count,
                                "posted_at": match.youtube_short.published_at
                            })
                            saved += 1
                    except Exception as e:
                        logger.error(f"Error saving match for {match.youtube_short.video_id}: {e}")
            
            conn.commit()
        
        logger.info(f"Saved {saved} associations")
    
    def print_report(self):
        """Print detailed audit report"""
        print("\n" + "=" * 80)
        print("YOUTUBE SHORTS AUDIT REPORT")
        print("=" * 80)
        print(f"Channel: {self.channel_id}")
        print(f"Total Shorts Found: {len(self.shorts)}")
        print(f"Local Videos with Transcripts: {len(self.local_videos)}")
        print("-" * 80)
        
        # Stats
        total_views = sum(s.view_count for s in self.shorts)
        total_likes = sum(s.like_count for s in self.shorts)
        
        print(f"Total Views: {total_views:,}")
        print(f"Total Likes: {total_likes:,}")
        print("-" * 80)
        
        # Match summary
        exact = [m for m in self.matches if m.match_type == "exact"]
        high = [m for m in self.matches if m.match_type == "high"]
        likely = [m for m in self.matches if m.match_type == "likely"]
        no_match = [m for m in self.matches if m.match_type == "no_match"]
        
        print(f"\nMATCH RESULTS:")
        print(f"  ✅ Exact matches: {len(exact)}")
        print(f"  🟡 High matches: {len(high)}")
        print(f"  🟠 Likely matches: {len(likely)}")
        print(f"  ❌ No match: {len(no_match)}")
        
        # Show exact matches
        if exact:
            print(f"\n✅ EXACT MATCHES ({len(exact)}):")
            for m in exact[:10]:
                print(f"  📺 '{m.youtube_short.title[:40]}...'")
                print(f"     → Local: '{m.local_video.filename[:40]}' ({m.similarity_score:.1%})")
        
        # Show high matches
        if high:
            print(f"\n🟡 HIGH MATCHES ({len(high)}):")
            for m in high[:10]:
                print(f"  📺 '{m.youtube_short.title[:40]}...'")
                print(f"     → Local: '{m.local_video.filename[:40]}' ({m.similarity_score:.1%})")
        
        # Show no matches (potential new content)
        if no_match:
            print(f"\n❌ NO MATCH - Potential duplicates to check ({len(no_match)}):")
            for m in no_match[:10]:
                print(f"  📺 '{m.youtube_short.title[:50]}...'")
                print(f"     Views: {m.youtube_short.view_count:,} | URL: {m.youtube_short.url}")
        
        print("\n" + "=" * 80)


async def main():
    parser = argparse.ArgumentParser(description="Audit YouTube shorts and match to local videos")
    parser.add_argument("--channel-id", default=YOUTUBE_CHANNEL_ID, help="YouTube channel ID")
    parser.add_argument("--max-results", type=int, default=100, help="Max shorts to fetch")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to database")
    parser.add_argument("--skip-transcripts", action="store_true", help="Skip transcript fetching")
    args = parser.parse_args()
    
    logger.info("Starting YouTube Shorts Audit...")
    
    auditor = YouTubeShortsAuditor(
        channel_id=args.channel_id,
        dry_run=args.dry_run
    )
    
    # Fetch shorts from YouTube
    await auditor.fetch_channel_shorts(max_results=args.max_results)
    
    if not auditor.shorts:
        logger.warning("No shorts found!")
        return
    
    # Fetch transcripts
    if not args.skip_transcripts:
        auditor.fetch_transcripts()
    
    # Load local videos
    auditor.load_local_videos()
    
    # Match shorts to local videos
    auditor.match_shorts_to_local()
    
    # Print report
    auditor.print_report()
    
    # Save associations
    if not args.dry_run:
        auditor.save_associations()
    else:
        logger.info("[DRY RUN] Skipping database save")
    
    logger.info("Audit complete!")


if __name__ == "__main__":
    asyncio.run(main())
