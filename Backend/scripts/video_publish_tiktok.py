#!/usr/bin/env python3
"""
Video Publishing Script for TikTok
Complete flow: Find videos → Generate captions → Upload to Google Drive → Publish via Blotato

Usage:
    python3 scripts/video_publish_tiktok.py

Requirements:
    - Backend server running on localhost:5555
    - Google Drive credentials configured
    - Blotato API configured
"""

import requests
import time
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_URL = "http://localhost:5555"

# Account mapping (from memory)
TIKTOK_ACCOUNTS = {
    "710": "isaiah_dupree",
    "243": "the_isaiah_dupree",
    "4508": "dupree_isaiah"
}

# Colors for terminal output
class C:
    R = '\033[91m'
    G = '\033[92m'
    Y = '\033[93m'
    B = '\033[94m'
    M = '\033[95m'
    C = '\033[96m'
    W = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(msg, color=C.W):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C.C}[{ts}]{C.END} {color}{msg}{C.END}")

def log_step(step, msg):
    print(f"\n{C.BOLD}{C.B}[Step {step}]{C.END} {msg}")


# =============================================================================
# STEP 1: FIND VIDEOS
# =============================================================================

def find_local_videos():
    """Find video files in local storage and workspace."""
    video_dirs = [
        "/Users/isaiahdupree/Documents/Software/MediaPoster/local_storage",
        "/Users/isaiahdupree/Documents/Software/MediaPoster/Backend",
        "/Users/isaiahdupree/Documents/Software/MediaPoster/workspace",
    ]
    
    videos = []
    extensions = ['.mov', '.mp4', '.m4v', '.avi']
    
    for base_dir in video_dirs:
        if not os.path.exists(base_dir):
            continue
        for root, dirs, files in os.walk(base_dir):
            # Skip node_modules, venv, .git
            dirs[:] = [d for d in dirs if d not in ['node_modules', 'venv', '.git', '__pycache__']]
            for f in files:
                if any(f.lower().endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, f)
                    videos.append({
                        "path": full_path,
                        "name": f,
                        "size": os.path.getsize(full_path)
                    })
    
    return videos

def get_videos_from_media_db():
    """Get videos from media-db that have file paths."""
    try:
        res = requests.get(f"{API_URL}/api/media-db/all?limit=50", timeout=10)
        if res.status_code == 200:
            data = res.json()
            items = data.get('items', []) if isinstance(data, dict) else data
            videos = []
            for item in items:
                file_path = item.get('file_path')
                if file_path and os.path.exists(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.mov', '.mp4', '.m4v']:
                        videos.append({
                            "id": item.get('id'),
                            "path": file_path,
                            "name": os.path.basename(file_path),
                            "title": item.get('title'),
                            "has_analysis": bool(item.get('hooks') or item.get('topics'))
                        })
            return videos
    except Exception as e:
        log(f"Error fetching from media-db: {e}", C.R)
    return []


# =============================================================================
# STEP 2: INGEST VIDEO TO MEDIA-DB
# =============================================================================

def ingest_video_to_db(video_path):
    """Add video to media-db if not already there."""
    try:
        # file_path is a query parameter, not JSON body
        res = requests.post(
            f"{API_URL}/api/media-db/ingest/file",
            params={"file_path": video_path},
            timeout=60
        )
        if res.status_code == 200:
            data = res.json()
            media_id = data.get('id') or data.get('media_id') or data.get('media', {}).get('id')
            log(f"✅ Ingested successfully, ID: {media_id}", C.G)
            return media_id
        else:
            log(f"Ingest failed: {res.status_code} - {res.text[:200]}", C.R)
    except Exception as e:
        log(f"Ingest error: {e}", C.R)
    return None


# =============================================================================
# STEP 3: GENERATE CAPTIONS
# =============================================================================

def generate_caption(media_id, platform="tiktok"):
    """Generate AI caption for the video."""
    try:
        res = requests.post(
            f"{API_URL}/api/analysis/generate-captions/{media_id}",
            json={
                "platform": platform,
                "tone": "engaging",
                "include_hashtags": True,
                "include_hook": True
            },
            timeout=60
        )
        if res.status_code == 200:
            data = res.json()
            return {
                "title": data.get("title", "Amazing Content"),
                "caption": data.get("captions", {}).get(platform, "#fyp #viral")
            }
    except Exception as e:
        log(f"Caption generation error: {e}", C.R)
    
    return {
        "title": "Check This Out!",
        "caption": "Amazing content you don't want to miss! #fyp #viral #trending"
    }


# =============================================================================
# STEP 4: PUBLISH VIA BLOTATO (GOOGLE DRIVE FLOW)
# =============================================================================

def publish_via_full_flow(media_id, account_id, username, title, caption, platform="tiktok"):
    """
    Full publish flow:
    1. Get file from media-db
    2. Upload to Google Drive
    3. Upload to Blotato
    4. Post to platform
    """
    try:
        text = f"{title}\n\n{caption}"
        
        log(f"📤 Starting full publish flow...", C.M)
        log(f"   Media ID: {media_id}", C.W)
        log(f"   Account: {account_id} (@{username})", C.W)
        log(f"   Platform: {platform}", C.W)
        
        res = requests.post(
            f"{API_URL}/api/blotato/posts/full-publish",
            json={
                "media_id": media_id,
                "blotato_account_id": account_id,
                "platform": platform,
                "username": username,
                "text": text,
                "cleanup_gdrive": True
            },
            timeout=120  # 2 minutes for upload + publish
        )
        
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                return {
                    "success": True,
                    "post_id": data.get("blotato_post_id"),
                    "url": data.get("url"),
                    "media_url": data.get("media_url")
                }
            else:
                return {
                    "success": False,
                    "error": data.get("error", "Unknown error")
                }
        else:
            return {
                "success": False,
                "error": f"Status {res.status_code}: {res.text[:200]}"
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# MAIN SCRIPT
# =============================================================================

def main():
    print("\n" + "="*70)
    print(f"{C.BOLD}{C.C}🎬 VIDEO PUBLISHING SCRIPT - TikTok{C.END}")
    print("="*70)
    print(f"Target: TikTok Account 710 (@isaiah_dupree)")
    print(f"Flow: Video → Media-DB → Caption → Google Drive → Blotato → TikTok")
    print("="*70)
    
    account_id = "710"
    username = TIKTOK_ACCOUNTS.get(account_id, "isaiah_dupree")
    
    # Step 1: Find videos
    log_step(1, "Finding videos...")
    
    # First check media-db
    db_videos = get_videos_from_media_db()
    log(f"Found {len(db_videos)} videos in media-db with file paths", C.W)
    
    # Also find local videos
    local_videos = find_local_videos()
    log(f"Found {len(local_videos)} local video files", C.W)
    
    if not db_videos and not local_videos:
        log("❌ No videos found!", C.R)
        return
    
    # Use media-db videos first (they're already ingested)
    videos_to_publish = []
    
    if db_videos:
        videos_to_publish = db_videos[:5]
        log(f"Using {len(videos_to_publish)} videos from media-db", C.G)
    else:
        # Need to ingest local videos first
        log("Ingesting local videos to media-db...", C.Y)
        for v in local_videos[:5]:
            log_step("1b", f"Ingesting: {v['name']}")
            media_id = ingest_video_to_db(v['path'])
            if media_id:
                videos_to_publish.append({
                    "id": media_id,
                    "path": v['path'],
                    "name": v['name']
                })
                log(f"✅ Ingested: {media_id}", C.G)
            else:
                log(f"❌ Failed to ingest: {v['name']}", C.R)
    
    if not videos_to_publish:
        log("❌ No videos available for publishing!", C.R)
        return
    
    print(f"\n{C.BOLD}Videos to publish:{C.END}")
    for i, v in enumerate(videos_to_publish):
        print(f"  {i+1}. {v.get('name') or v.get('title', 'Unknown')}")
    
    # Step 2-4: Process each video
    results = []
    
    for i, video in enumerate(videos_to_publish):
        print(f"\n{'-'*70}")
        print(f"{C.BOLD}Processing Video {i+1}/{len(videos_to_publish)}{C.END}")
        print(f"{'-'*70}")
        
        media_id = video.get('id')
        video_name = video.get('name') or video.get('title', 'Unknown')
        
        log(f"🎬 Video: {video_name}", C.B)
        
        # Step 2: Generate caption
        log_step(2, "Generating AI caption...")
        caption_data = generate_caption(media_id, "tiktok")
        title = caption_data["title"]
        caption = caption_data["caption"]
        
        log(f"📝 Title: {title[:50]}...", C.G)
        log(f"📝 Caption: {caption[:80]}...", C.G)
        
        # Step 3: Publish
        log_step(3, "Publishing via Google Drive + Blotato...")
        
        result = publish_via_full_flow(
            media_id=media_id,
            account_id=account_id,
            username=username,
            title=title,
            caption=caption,
            platform="tiktok"
        )
        
        result["video_name"] = video_name
        result["title"] = title
        results.append(result)
        
        if result["success"]:
            log(f"✅ Published successfully!", C.G)
            if result.get("url"):
                log(f"🔗 URL: {result['url']}", C.C)
        else:
            log(f"❌ Failed: {result.get('error', 'Unknown')[:100]}", C.R)
        
        # Wait between posts
        if i < len(videos_to_publish) - 1:
            log(f"⏳ Waiting 15 seconds before next post...", C.Y)
            time.sleep(15)
    
    # Final summary
    print("\n" + "="*70)
    print(f"{C.BOLD}FINAL RESULTS{C.END}")
    print("="*70)
    
    success_count = sum(1 for r in results if r["success"])
    fail_count = sum(1 for r in results if not r["success"])
    
    print(f"\n{C.G}✅ Success: {success_count}{C.END}")
    print(f"{C.R}❌ Failed: {fail_count}{C.END}")
    
    print(f"\n{'-'*70}")
    print("Details:")
    print(f"{'-'*70}")
    
    for i, result in enumerate(results):
        icon = "✅" if result["success"] else "❌"
        print(f"\n{icon} Video {i+1}: {result.get('video_name', 'Unknown')}")
        print(f"   Title: {result.get('title', 'N/A')[:50]}")
        
        if result["success"]:
            if result.get("url"):
                print(f"   {C.C}URL: {result['url']}{C.END}")
            if result.get("post_id"):
                print(f"   Post ID: {result['post_id']}")
        else:
            print(f"   {C.R}Error: {result.get('error', 'Unknown')[:80]}{C.END}")
    
    print("\n" + "="*70)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
