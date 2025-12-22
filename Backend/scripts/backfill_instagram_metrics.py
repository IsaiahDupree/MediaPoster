#!/usr/bin/env python3
"""
Backfill Instagram metrics from RapidAPI Instagram Scraper

Uses: instagram-scraper-api2.p.rapidapi.com
Endpoints:
- /v1/info - Get user info by username
- /v1/posts - Get user posts  
- /v1/post_info - Get single post metrics by shortcode

This script fetches metrics for all Instagram posts in the database
that have platform_url set but 0 views/likes.
"""

import asyncio
import os
import re
import sys
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
# Using Instagram Looter2 API (working endpoint)
RAPIDAPI_HOST = "instagram-looter2.p.rapidapi.com"
API_BASE = f"https://{RAPIDAPI_HOST}"

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")


def extract_shortcode_from_url(url: str) -> Optional[str]:
    """
    Extract Instagram shortcode from various URL formats:
    - https://www.instagram.com/reel/DSfkWA2lOyA/
    - https://www.instagram.com/p/ABC123/
    - https://instagram.com/reel/XYZ789
    """
    if not url:
        return None
    
    patterns = [
        r'instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)',
        r'instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)/',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


async def fetch_user_profile_with_posts(username: str) -> Optional[Dict[str, Any]]:
    """
    Fetch user profile which includes recent posts with metrics
    
    Endpoint: GET /profile?username={username}
    """
    if not RAPIDAPI_KEY:
        print("❌ RAPIDAPI_KEY not set in .env")
        return None
    
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{API_BASE}/profile",
                headers=headers,
                params={"username": username}
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get("edge_owner_to_timeline_media", {}).get("edges", [])
                print(f"  ✓ Profile fetched: {len(posts)} posts found")
                return data
            else:
                print(f"  ✗ API Error {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"  ✗ Request error: {e}")
            return None


def build_post_lookup(profile_data: Dict[str, Any]) -> Dict[str, Dict]:
    """Build lookup dict from shortcode to post metrics"""
    lookup = {}
    
    if not profile_data:
        return lookup
    
    edges = profile_data.get("edge_owner_to_timeline_media", {}).get("edges", [])
    for edge in edges:
        node = edge.get("node", {})
        shortcode = node.get("shortcode")
        if shortcode:
            lookup[shortcode] = {
                "likes": (node.get("edge_liked_by") or {}).get("count", 0),
                "comments": (node.get("edge_media_to_comment") or {}).get("count", 0),
                "views": node.get("video_view_count") or node.get("video_play_count") or 0,
            }
    
    return lookup


def parse_metrics_from_response(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Parse metrics from RapidAPI response
    
    Expected structure varies by endpoint, common fields:
    - like_count / likes_count / edge_liked_by.count
    - comment_count / comments_count / edge_media_to_comment.count  
    - play_count / video_view_count (for reels/videos)
    - share_count (if available)
    """
    metrics = {
        "views": 0,
        "likes": 0,
        "comments": 0,
        "shares": 0,
    }
    
    if not data:
        return metrics
    
    # Handle nested data structures
    post_data = data.get("data", data)
    if isinstance(post_data, list) and len(post_data) > 0:
        post_data = post_data[0]
    
    # Views (play_count for reels/videos)
    metrics["views"] = (
        post_data.get("play_count") or
        post_data.get("video_view_count") or
        post_data.get("view_count") or
        post_data.get("video_play_count") or
        0
    )
    
    # Likes
    metrics["likes"] = (
        post_data.get("like_count") or
        post_data.get("likes_count") or
        post_data.get("likes") or
        (post_data.get("edge_liked_by", {}) or {}).get("count") or
        (post_data.get("edge_media_preview_like", {}) or {}).get("count") or
        0
    )
    
    # Comments
    metrics["comments"] = (
        post_data.get("comment_count") or
        post_data.get("comments_count") or
        post_data.get("comments") or
        (post_data.get("edge_media_to_comment", {}) or {}).get("count") or
        (post_data.get("edge_media_preview_comment", {}) or {}).get("count") or
        0
    )
    
    # Shares (often not available)
    metrics["shares"] = (
        post_data.get("share_count") or
        post_data.get("reshare_count") or
        0
    )
    
    return metrics


async def update_post_in_db(post_id: str, metrics: Dict[str, int]):
    """Update post metrics in database via API"""
    api_url = os.getenv("API_URL", "http://localhost:5555")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(
                f"{api_url}/api/posted-content/{post_id}",
                json={
                    "views": metrics["views"],
                    "likes": metrics["likes"],
                    "comments": metrics["comments"],
                    "shares": metrics["shares"],
                }
            )
            
            if response.status_code == 200:
                print(f"  ✓ Updated DB: views={metrics['views']}, likes={metrics['likes']}, comments={metrics['comments']}")
                return True
            else:
                print(f"  ✗ DB Update failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ DB Update error: {e}")
            return False


async def get_instagram_posts() -> list:
    """Fetch all Instagram posts from the API"""
    api_url = os.getenv("API_URL", "http://localhost:5555")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/api/posted-content?limit=100")
        if response.status_code == 200:
            data = response.json()
            return [
                p for p in data.get("items", [])
                if p.get("platform") == "instagram" and p.get("platform_url")
            ]
        return []


async def backfill_instagram_metrics(dry_run: bool = False):
    """
    Main backfill function - fetches user profile with posts and matches by shortcode
    """
    print("=" * 60)
    print("📸 Instagram Metrics Backfill")
    print("=" * 60)
    print(f"API: {RAPIDAPI_HOST}")
    print(f"Key: {'✓ Set' if RAPIDAPI_KEY else '✗ Not set'}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 60)
    
    if not RAPIDAPI_KEY:
        print("\n❌ RAPIDAPI_KEY not set")
        return
    
    posts = await get_instagram_posts()
    print(f"\n📋 Found {len(posts)} Instagram posts with URLs")
    
    if not posts:
        return
    
    # Map Blotato account IDs to actual Instagram usernames
    # Add your mappings here: blotato_id -> instagram_username
    ACCOUNT_MAPPINGS = {
        "670": "the_isaiah_dupree",
        # Add more mappings as needed
    }
    
    # Group posts by actual Instagram username
    by_user: Dict[str, list] = {}
    for post in posts:
        account_id = post.get("account_username", "").replace("@", "")
        # Use mapping if available, otherwise use as-is
        username = ACCOUNT_MAPPINGS.get(account_id, account_id)
        if username:
            if username not in by_user:
                by_user[username] = []
            by_user[username].append(post)
    
    print(f"📊 Found {len(by_user)} unique Instagram accounts")
    
    updated = 0
    failed = 0
    
    for username, user_posts in by_user.items():
        print(f"\n🔍 Fetching profile for @{username}...")
        
        profile_data = await fetch_user_profile_with_posts(username)
        if not profile_data:
            print(f"  ✗ Could not fetch profile")
            failed += len(user_posts)
            continue
        
        post_lookup = build_post_lookup(profile_data)
        print(f"  Found {len(post_lookup)} posts in profile")
        
        for post in user_posts:
            shortcode = extract_shortcode_from_url(post.get("platform_url"))
            print(f"\n  [{post['id'][:8]}] Shortcode: {shortcode}")
            
            if shortcode and shortcode in post_lookup:
                metrics = post_lookup[shortcode]
                print(f"    ✓ Found: views={metrics['views']}, likes={metrics['likes']}, comments={metrics['comments']}")
                
                if not dry_run:
                    if await update_post_in_db(post["id"], {"views": metrics["views"], "likes": metrics["likes"], "comments": metrics["comments"], "shares": 0}):
                        updated += 1
                    else:
                        failed += 1
                else:
                    print(f"    [DRY RUN] Would update")
                    updated += 1
            else:
                print(f"    ✗ Post not found in profile (may be older than 12 posts)")
                failed += 1
        
        await asyncio.sleep(1.5)
    
    print("\n" + "=" * 60)
    print(f"✅ Done: {updated} updated, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill Instagram metrics from RapidAPI")
    parser.add_argument("--dry-run", action="store_true", help="Fetch metrics but don't update DB")
    parser.add_argument("--post-id", type=str, help="Process single post by ID")
    parser.add_argument("--shortcode", type=str, help="Test fetch for single shortcode")
    
    args = parser.parse_args()
    
    if args.shortcode:
        # Test single shortcode
        async def test_shortcode():
            print(f"Testing shortcode: {args.shortcode}")
            data = await fetch_post_metrics(args.shortcode)
            if data:
                import json
                print(json.dumps(data, indent=2, default=str)[:2000])
                metrics = parse_metrics_from_response(data)
                print(f"\nParsed metrics: {metrics}")
        
        asyncio.run(test_shortcode())
    else:
        asyncio.run(backfill_instagram_metrics(dry_run=args.dry_run))
