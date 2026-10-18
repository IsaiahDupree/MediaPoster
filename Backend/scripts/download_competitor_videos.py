#!/usr/bin/env python3
"""
Batch Download Script for Instagram Competitor Videos
Downloads all available videos from a competitor's Instagram account.

Usage:
    python download_competitor_videos.py personalbrandlaunch
    python download_competitor_videos.py personalbrandlaunch --max-pages 10
"""
import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Configuration
STORAGE_BASE = "/Users/isaiahdupree/Documents/CompetitorResearch/accounts"
ENV_FILE = Path(__file__).parent.parent / ".env"


def load_api_key() -> str:
    """Load RapidAPI key from .env file"""
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith('RAPIDAPI_KEY='):
                return line.strip().split('=', 1)[1]
    raise ValueError("RAPIDAPI_KEY not found in .env")


def get_user_info(username: str, api_key: str) -> Dict:
    """Get user profile info including user_id"""
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "instagram-looter2.p.rapidapi.com"
    }
    
    resp = requests.get(
        f"https://instagram-looter2.p.rapidapi.com/profile?username={username}",
        headers=headers
    )
    
    if resp.status_code != 200:
        raise Exception(f"Failed to get profile: {resp.status_code}")
    
    return resp.json()


def fetch_posts_batch(username: str, api_key: str, end_cursor: str = None) -> Dict:
    """Fetch a batch of posts from Instagram"""
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "instagram-looter2.p.rapidapi.com"
    }
    
    url = f"https://instagram-looter2.p.rapidapi.com/profile?username={username}"
    if end_cursor:
        url += f"&end_cursor={end_cursor}"
    
    resp = requests.get(url, headers=headers)
    
    if resp.status_code != 200:
        return {"edges": [], "has_next": False, "cursor": None}
    
    data = resp.json()
    timeline = data.get('edge_owner_to_timeline_media', {})
    
    return {
        "edges": timeline.get('edges', []),
        "has_next": timeline.get('page_info', {}).get('has_next_page', False),
        "cursor": timeline.get('page_info', {}).get('end_cursor'),
        "total": timeline.get('count', 0)
    }


def fetch_single_post(shortcode: str, api_key: str) -> Optional[Dict]:
    """Fetch a single post by shortcode to get video URL"""
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "instagram-looter2.p.rapidapi.com"
    }
    
    # Try different endpoints
    endpoints = [
        f"https://instagram-looter2.p.rapidapi.com/post?url=https://www.instagram.com/p/{shortcode}/",
        f"https://instagram-looter2.p.rapidapi.com/post?shortcode={shortcode}",
    ]
    
    for url in endpoints:
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('video_url') or data.get('is_video'):
                    return data
        except:
            pass
    
    return None


def download_video(video_url: str, filepath: str) -> bool:
    """Download a video from URL"""
    try:
        resp = requests.get(video_url, timeout=120, stream=True)
        if resp.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"    Error downloading: {e}")
    return False


def load_manifest(username: str) -> Dict:
    """Load or create download manifest"""
    manifest_path = Path(STORAGE_BASE) / username / "download_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return {
        "username": username,
        "created_at": datetime.now().isoformat(),
        "videos": {},
        "downloaded": [],
        "failed": [],
        "total_discovered": 0
    }


def save_manifest(username: str, manifest: Dict):
    """Save download manifest"""
    manifest_path = Path(STORAGE_BASE) / username / "download_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Download Instagram competitor videos")
    parser.add_argument("username", help="Instagram username to download from")
    parser.add_argument("--max-pages", type=int, default=50, help="Max pages to fetch")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests")
    parser.add_argument("--resume", action="store_true", help="Resume from manifest")
    args = parser.parse_args()
    
    username = args.username
    api_key = load_api_key()
    storage_path = Path(STORAGE_BASE) / username / "posts"
    storage_path.mkdir(parents=True, exist_ok=True)
    
    print(f"=" * 60)
    print(f"DOWNLOADING VIDEOS FROM @{username}")
    print(f"=" * 60)
    
    # Load or create manifest
    manifest = load_manifest(username)
    
    # Get profile info
    print("\n📊 Fetching profile info...")
    profile = get_user_info(username, api_key)
    user_id = profile.get('id')
    total_posts = profile.get('edge_owner_to_timeline_media', {}).get('count', 0)
    print(f"   User ID: {user_id}")
    print(f"   Total posts: {total_posts}")
    
    # Fetch initial batch from profile
    print("\n📥 Fetching posts from profile...")
    timeline = profile.get('edge_owner_to_timeline_media', {})
    edges = timeline.get('edges', [])
    
    # Process initial batch
    videos_found = 0
    for edge in edges:
        node = edge.get('node', {})
        if node.get('is_video'):
            shortcode = node.get('shortcode')
            video_url = node.get('video_url')
            if shortcode and video_url:
                manifest["videos"][shortcode] = {
                    "shortcode": shortcode,
                    "video_url": video_url,
                    "views": node.get('video_view_count', 0),
                    "caption": (node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''))[:200]
                }
                videos_found += 1
    
    print(f"   Videos found in profile: {videos_found}")
    
    # Try to get more posts via individual post lookups
    # (Instagram limits profile to 12 posts, but individual posts can be fetched)
    print("\n🔍 Attempting to discover more videos...")
    print("   Note: API is limited to ~12 posts per profile request")
    print("   Downloading available videos...\n")
    
    # Download all discovered videos
    downloaded = 0
    skipped = 0
    failed = 0
    
    for shortcode, video_info in manifest["videos"].items():
        filepath = storage_path / f"{shortcode}.mp4"
        
        if filepath.exists():
            skipped += 1
            continue
        
        if shortcode in manifest["downloaded"]:
            continue
            
        video_url = video_info.get("video_url")
        if not video_url:
            print(f"   ⚠️  {shortcode}: No video URL, trying to fetch...")
            post_data = fetch_single_post(shortcode, api_key)
            if post_data and post_data.get('video_url'):
                video_url = post_data['video_url']
                manifest["videos"][shortcode]["video_url"] = video_url
            else:
                print(f"   ❌ {shortcode}: Could not get video URL")
                manifest["failed"].append(shortcode)
                failed += 1
                continue
        
        print(f"   📹 Downloading {shortcode}...", end=" ")
        if download_video(video_url, str(filepath)):
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"✓ ({size_mb:.1f}MB)")
            manifest["downloaded"].append(shortcode)
            downloaded += 1
        else:
            print("❌")
            manifest["failed"].append(shortcode)
            failed += 1
        
        time.sleep(args.delay)
    
    # Save manifest
    manifest["total_discovered"] = len(manifest["videos"])
    manifest["last_updated"] = datetime.now().isoformat()
    save_manifest(username, manifest)
    
    # Summary
    print(f"\n" + "=" * 60)
    print(f"DOWNLOAD COMPLETE")
    print(f"=" * 60)
    print(f"   Videos discovered: {len(manifest['videos'])}")
    print(f"   Downloaded: {downloaded}")
    print(f"   Already had: {skipped}")
    print(f"   Failed: {failed}")
    print(f"\n   Storage: {storage_path}")
    print(f"   Manifest: {STORAGE_BASE}/{username}/download_manifest.json")
    
    # List all videos in storage
    all_videos = list(storage_path.glob("*.mp4"))
    print(f"\n   Total videos in storage: {len(all_videos)}")
    
    # Calculate total size
    total_size = sum(v.stat().st_size for v in all_videos)
    print(f"   Total size: {total_size / (1024*1024):.1f} MB")


if __name__ == "__main__":
    main()
