#!/usr/bin/env python3
"""
Download videos from collected manifest using RapidAPI.
Uses the shortcodes collected by Safari scraper and fetches video URLs via API.
"""
import os
import json
import time
import re
import requests
from pathlib import Path
from datetime import datetime

STORAGE_BASE = "/Users/isaiahdupree/Documents/CompetitorResearch/accounts"


def load_api_key() -> str:
    """Load RapidAPI key from .env file"""
    env_path = Path(__file__).parent.parent / ".env"
    with open(env_path) as f:
        for line in f:
            if line.startswith('RAPIDAPI_KEY='):
                return line.strip().split('=', 1)[1]
    raise ValueError("RAPIDAPI_KEY not found")


def fetch_video_url(shortcode: str, api_key: str) -> dict:
    """Fetch video URL from RapidAPI"""
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "instagram-looter2.p.rapidapi.com"
    }
    
    # Try reel URL first, then post URL
    urls_to_try = [
        f"https://instagram-looter2.p.rapidapi.com/post?url=https://www.instagram.com/reel/{shortcode}/",
        f"https://instagram-looter2.p.rapidapi.com/post?url=https://www.instagram.com/p/{shortcode}/",
    ]
    
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                video_url = data.get('video_url')
                if video_url:
                    return {
                        'video_url': video_url,
                        'caption': data.get('caption', '')[:200] if data.get('caption') else '',
                        'views': data.get('video_view_count', 0),
                        'likes': data.get('like_count', 0)
                    }
        except Exception as e:
            print(f"    API error: {e}")
        time.sleep(0.5)
    
    return {}


def download_video(video_url: str, filepath: Path) -> bool:
    """Download video from URL"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        resp = requests.get(video_url, headers=headers, timeout=120, stream=True)
        if resp.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"    Download error: {e}")
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="Target username")
    parser.add_argument("--limit", type=int, default=0, help="Limit downloads (0=all)")
    args = parser.parse_args()
    
    username = args.username
    storage_path = Path(STORAGE_BASE) / username / "posts"
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Load manifest
    manifest_path = Path(STORAGE_BASE) / username / "safari_manifest.json"
    if not manifest_path.exists():
        print(f"No manifest found at {manifest_path}")
        return
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    post_urls = manifest.get('post_urls', [])
    downloaded = set(manifest.get('downloaded', []))
    failed = set(manifest.get('failed', []))
    
    print(f"="*60)
    print(f"DOWNLOADING VIDEOS FOR @{username}")
    print(f"="*60)
    print(f"URLs in manifest: {len(post_urls)}")
    print(f"Already downloaded: {len(downloaded)}")
    print()
    
    api_key = load_api_key()
    
    # Process each URL
    new_downloads = 0
    new_failed = 0
    limit = args.limit if args.limit > 0 else len(post_urls)
    
    skipped = 0
    for i, post_url in enumerate(post_urls):
        if new_downloads >= limit:
            break
            
        # Extract shortcode
        match = re.search(r'/(?:reel|p)/([A-Za-z0-9_-]+)', post_url)
        if not match:
            continue
        shortcode = match.group(1)
        
        # Skip if already downloaded
        filepath = storage_path / f"{shortcode}.mp4"
        if filepath.exists():
            if shortcode not in downloaded:
                downloaded.add(shortcode)
            skipped += 1
            continue
        
        # Skip if in downloaded set
        if shortcode in downloaded:
            skipped += 1
            continue
        
        print(f"[{i+1}/{len(post_urls)}] {shortcode}...", end=" ")
        
        # Fetch video URL via API
        video_info = fetch_video_url(shortcode, api_key)
        if not video_info.get('video_url'):
            print("❌ No video URL")
            failed.add(shortcode)
            new_failed += 1
            continue
        
        # Download
        if download_video(video_info['video_url'], filepath):
            size_mb = filepath.stat().st_size / (1024*1024)
            print(f"✓ ({size_mb:.1f}MB)")
            downloaded.add(shortcode)
            new_downloads += 1
        else:
            print("❌ Download failed")
            failed.add(shortcode)
            new_failed += 1
        
        # Save progress
        manifest['downloaded'] = list(downloaded)
        manifest['failed'] = list(failed)
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        time.sleep(1)  # Rate limiting
    
    # Summary
    total_videos = len(list(storage_path.glob("*.mp4")))
    total_size = sum(f.stat().st_size for f in storage_path.glob("*.mp4"))
    
    print(f"\n{'='*60}")
    print(f"COMPLETE")
    print(f"{'='*60}")
    print(f"  Skipped (already have): {skipped}")
    print(f"  New downloads: {new_downloads}")
    print(f"  Failed: {new_failed}")
    print(f"  Total videos: {total_videos}")
    print(f"  Total size: {total_size/(1024*1024):.1f} MB")
    print(f"\n  Storage: {storage_path}")


if __name__ == "__main__":
    main()
