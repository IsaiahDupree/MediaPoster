#!/usr/bin/env python3
"""
Backfill TikTok metrics from RapidAPI TikTok Scraper7

Uses: tiktok-scraper7.p.rapidapi.com
Endpoints:
- /video/info - Get video metrics by URL or ID
"""

import asyncio
import os
import re
import sys
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "tiktok-scraper7.p.rapidapi.com"
API_BASE = f"https://{RAPIDAPI_HOST}"


def extract_video_id_from_url(url: str) -> Optional[str]:
    """Extract TikTok video ID from URL"""
    if not url:
        return None
    
    patterns = [
        r'tiktok\.com/.*/video/(\d+)',
        r'tiktok\.com/.*[?&]video_id=(\d+)',
        r'/video/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


async def fetch_user_videos(username: str) -> Optional[Dict[str, Any]]:
    """Fetch all videos for a TikTok user"""
    if not RAPIDAPI_KEY:
        print("❌ RAPIDAPI_KEY not set")
        return None
    
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{API_BASE}/user/posts",
                headers=headers,
                params={"unique_id": username}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ API Response: {data.get('code', 'no code')} - {data.get('msg', '')}")
                return data
            else:
                print(f"  ✗ API Error {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"  ✗ Request error: {e}")
            return None


def parse_video_metrics(video: Dict[str, Any]) -> Dict[str, int]:
    """Parse metrics from a single video object"""
    metrics = {"views": 0, "likes": 0, "comments": 0, "shares": 0}
    
    # Stats can be nested or at top level
    stats = video.get("stats", video)
    
    metrics["views"] = (
        stats.get("playCount") or stats.get("play_count") or 
        video.get("play_count") or 0
    )
    metrics["likes"] = (
        stats.get("diggCount") or stats.get("digg_count") or
        video.get("digg_count") or 0
    )
    metrics["comments"] = (
        stats.get("commentCount") or stats.get("comment_count") or
        video.get("comment_count") or 0
    )
    metrics["shares"] = (
        stats.get("shareCount") or stats.get("share_count") or
        video.get("share_count") or 0
    )
    
    return metrics


def build_video_lookup(data: Dict[str, Any]) -> Dict[str, Dict]:
    """Build a lookup dict from video_id to video data"""
    lookup = {}
    
    if not data or data.get("code") != 0:
        return lookup
    
    videos = data.get("data", {}).get("videos", [])
    for video in videos:
        video_id = video.get("video_id") or video.get("aweme_id")
        if video_id:
            lookup[str(video_id)] = video
    
    return lookup


async def update_post_in_db(post_id: str, metrics: Dict[str, int]):
    """Update post metrics via API"""
    api_url = os.getenv("API_URL", "http://localhost:5555")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(
                f"{api_url}/api/posted-content/{post_id}",
                params={
                    "views": metrics["views"],
                    "likes": metrics["likes"],
                    "comments": metrics["comments"],
                    "shares": metrics["shares"],
                }
            )
            
            if response.status_code == 200:
                print(f"  ✓ DB Updated: views={metrics['views']}, likes={metrics['likes']}")
                return True
            else:
                print(f"  ✗ DB Error {response.status_code}: {response.text[:100]}")
                return False
        except Exception as e:
            print(f"  ✗ DB Error: {e}")
            return False


async def get_tiktok_posts() -> list:
    """Fetch TikTok posts from API"""
    api_url = os.getenv("API_URL", "http://localhost:5555")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/api/posted-content?limit=100")
        if response.status_code == 200:
            data = response.json()
            return [
                p for p in data.get("items", [])
                if p.get("platform") == "tiktok" and p.get("platform_url")
                and "tiktok.com" in p.get("platform_url", "")
            ]
        return []


async def backfill_tiktok_metrics(dry_run: bool = False):
    """Main backfill function - fetches user videos and matches with DB"""
    print("=" * 60)
    print("🎵 TikTok Metrics Backfill")
    print("=" * 60)
    print(f"API: {RAPIDAPI_HOST}")
    print(f"Key: {'✓ Set' if RAPIDAPI_KEY else '✗ Not set'}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 60)
    
    if not RAPIDAPI_KEY:
        print("\n❌ RAPIDAPI_KEY not set")
        return
    
    posts = await get_tiktok_posts()
    print(f"\n📋 Found {len(posts)} TikTok posts with URLs")
    
    if not posts:
        return
    
    # Group posts by username
    by_user: Dict[str, list] = {}
    for post in posts:
        url = post.get("platform_url", "")
        # Extract username from URL like @isaiah_dupree
        match = re.search(r'tiktok\.com/@([^/]+)/', url)
        if match:
            username = match.group(1)
            if username not in by_user:
                by_user[username] = []
            by_user[username].append(post)
    
    print(f"📊 Found {len(by_user)} unique TikTok accounts")
    
    updated = 0
    failed = 0
    
    for username, user_posts in by_user.items():
        print(f"\n🔍 Fetching videos for @{username}...")
        
        data = await fetch_user_videos(username)
        if not data:
            print(f"  ✗ Could not fetch videos for @{username}")
            failed += len(user_posts)
            continue
        
        video_lookup = build_video_lookup(data)
        print(f"  Found {len(video_lookup)} videos from API")
        
        for post in user_posts:
            url = post.get("platform_url", "")
            video_id = extract_video_id_from_url(url)
            
            print(f"\n  [{post['id'][:8]}] Video ID: {video_id}")
            
            if video_id and video_id in video_lookup:
                video = video_lookup[video_id]
                metrics = parse_video_metrics(video)
                print(f"    ✓ Found: views={metrics['views']}, likes={metrics['likes']}, comments={metrics['comments']}")
                
                if not dry_run:
                    if await update_post_in_db(post["id"], metrics):
                        updated += 1
                    else:
                        failed += 1
                else:
                    print(f"    [DRY RUN] Would update")
                    updated += 1
            else:
                print(f"    ✗ Video not found in API response")
                failed += 1
        
        await asyncio.sleep(1.5)  # Rate limit between users
    
    print("\n" + "=" * 60)
    print(f"✅ Done: {updated} updated, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--url", type=str, help="Test single URL")
    args = parser.parse_args()
    
    if args.url:
        async def test():
            data = await fetch_video_metrics(args.url)
            if data:
                import json
                print(json.dumps(data, indent=2, default=str)[:2000])
                print(f"\nParsed: {parse_metrics(data)}")
        asyncio.run(test())
    else:
        asyncio.run(backfill_tiktok_metrics(dry_run=args.dry_run))
