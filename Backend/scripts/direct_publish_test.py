#!/usr/bin/env python3
"""
Direct Publishing Test
Schedules 5 posts and publishes them directly via Blotato API.
Monitors status and captures URLs.
"""

import requests
import time
import json
from datetime import datetime, timedelta, timezone

API_URL = "http://localhost:5555"

# ANSI colors
class C:
    R = '\033[91m'  # Red
    G = '\033[92m'  # Green
    Y = '\033[93m'  # Yellow
    B = '\033[94m'  # Blue
    M = '\033[95m'  # Magenta
    C = '\033[96m'  # Cyan
    W = '\033[97m'  # White
    BOLD = '\033[1m'
    END = '\033[0m'

def log(msg, color=C.W):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C.C}[{ts}]{C.END} {color}{msg}{C.END}")

def get_approved_videos(limit=5):
    """Get top approved videos."""
    try:
        res = requests.get(f"{API_URL}/api/analyzed-content/list?curation_status=approved&limit={limit}", timeout=10)
        if res.status_code == 200:
            return res.json().get("items", [])
    except Exception as e:
        log(f"❌ Failed to fetch videos: {e}", C.R)
    return []

def generate_caption(video_id):
    """Generate AI caption."""
    try:
        res = requests.post(
            f"{API_URL}/api/analysis/generate-captions/{video_id}",
            json={"platform": "tiktok", "tone": "engaging", "include_hashtags": True},
            timeout=30
        )
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {"title": "Amazing Content", "captions": {"tiktok": "Check this out! #fyp"}}

def get_video_file_path(video_id):
    """Get the local file path for a video."""
    try:
        # Try to get the media info
        res = requests.get(f"{API_URL}/api/analyzed-content/list?limit=100", timeout=10)
        if res.status_code == 200:
            items = res.json().get("items", [])
            for item in items:
                if item.get("id") == video_id:
                    return item.get("file_path") or item.get("source_path")
    except:
        pass
    return None

def publish_to_tiktok(account_id, title, caption, video_id):
    """Publish directly to TikTok via Blotato API."""
    try:
        # First, we need to upload media to Google Drive or get a URL
        # For now, let's try the full-publish endpoint
        
        # Get video info
        video_res = requests.get(f"{API_URL}/api/analyzed-content/{video_id}", timeout=10)
        
        # Try publishing via Blotato
        publish_payload = {
            "account_id": account_id,
            "text": f"{title}\n\n{caption}",
            "platform": "tiktok",
            "media_urls": [],  # Would need actual media URL
            "tiktok_title": title,
            "tiktok_privacy": "PUBLIC_TO_EVERYONE",
            "tiktok_is_ai_generated": True
        }
        
        log(f"📤 Publishing to TikTok account {account_id}...", C.M)
        log(f"   Title: {title[:50]}...", C.W)
        
        res = requests.post(
            f"{API_URL}/api/blotato/posts",
            json=publish_payload,
            timeout=60
        )
        
        if res.status_code == 200:
            data = res.json()
            return {
                "success": True,
                "post_id": data.get("post_id"),
                "url": data.get("url"),
                "response": data
            }
        else:
            return {
                "success": False,
                "error": f"Status {res.status_code}: {res.text[:200]}"
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_post_status(post_id, status, url=None):
    """Update post status in our database."""
    try:
        update_data = {"status": status}
        if url:
            update_data["post_url"] = url
        requests.put(f"{API_URL}/api/schedule/{post_id}", json=update_data, timeout=5)
    except:
        pass

def main():
    print("\n" + "="*60)
    print(f"{C.BOLD}{C.C}🚀 DIRECT PUBLISHING TEST{C.END}")
    print("="*60)
    print(f"Target: TikTok Account 710 (@isaiah_dupree)")
    print(f"Posts: 5 videos, 12 seconds apart")
    print("="*60 + "\n")
    
    # Step 1: Get approved videos
    log("📥 Fetching top 5 approved videos...", C.B)
    videos = get_approved_videos(5)
    
    if len(videos) < 5:
        log(f"❌ Only found {len(videos)} approved videos", C.R)
        return
    
    log(f"✅ Found {len(videos)} approved videos", C.G)
    
    # Step 2: Generate captions and schedule
    posts = []
    start_time = datetime.now(timezone.utc) + timedelta(seconds=10)
    
    print("\n" + "-"*60)
    print(f"{C.BOLD}PREPARING POSTS{C.END}")
    print("-"*60)
    
    for i, video in enumerate(videos[:5]):
        video_id = video.get("id")
        video_title = video.get("title", "Unknown")
        scheduled_at = start_time + timedelta(seconds=i * 12)
        
        log(f"🎬 Video {i+1}: {video_title[:40]}...", C.W)
        
        # Generate caption
        log(f"   Generating caption...", C.Y)
        cap_data = generate_caption(video_id)
        title = cap_data.get("title", f"Video {i+1}")
        caption = cap_data.get("captions", {}).get("tiktok", "#fyp")
        
        posts.append({
            "index": i + 1,
            "video_id": video_id,
            "title": title,
            "caption": caption,
            "scheduled_at": scheduled_at,
            "status": "pending",
            "url": None
        })
        
        log(f"   ✅ Ready: {title[:40]}...", C.G)
    
    # Step 3: Publish posts with timer
    print("\n" + "-"*60)
    print(f"{C.BOLD}PUBLISHING (12 seconds apart){C.END}")
    print("-"*60 + "\n")
    
    results = []
    
    for i, post in enumerate(posts):
        # Wait until scheduled time
        now = datetime.now(timezone.utc)
        wait_time = (post["scheduled_at"] - now).total_seconds()
        
        if wait_time > 0:
            log(f"⏳ Waiting {wait_time:.0f}s for post {post['index']}...", C.Y)
            
            # Countdown
            while wait_time > 0:
                print(f"\r{C.Y}   ⏱️  T-{int(wait_time)}s {C.END}", end="", flush=True)
                time.sleep(1)
                wait_time -= 1
            print()
        
        # Publish
        log(f"🚀 Publishing post {post['index']}: {post['title'][:40]}...", C.M)
        
        result = publish_to_tiktok(
            account_id="710",
            title=post["title"],
            caption=post["caption"],
            video_id=post["video_id"]
        )
        
        post["status"] = "posted" if result["success"] else "failed"
        post["url"] = result.get("url")
        post["result"] = result
        
        if result["success"]:
            log(f"   ✅ SUCCESS!", C.G)
            if result.get("url"):
                log(f"   🔗 URL: {result['url']}", C.C)
        else:
            log(f"   ❌ FAILED: {result.get('error', 'Unknown')[:100]}", C.R)
        
        results.append(post)
    
    # Final summary
    print("\n" + "="*60)
    print(f"{C.BOLD}FINAL RESULTS{C.END}")
    print("="*60)
    
    success = sum(1 for p in results if p["status"] == "posted")
    failed = sum(1 for p in results if p["status"] == "failed")
    
    print(f"\n{C.G}✅ Success: {success}{C.END}")
    print(f"{C.R}❌ Failed: {failed}{C.END}")
    
    print("\n" + "-"*60)
    print("DETAILS:")
    print("-"*60)
    
    for post in results:
        icon = "✅" if post["status"] == "posted" else "❌"
        print(f"\n{icon} Post {post['index']}: {post['title'][:40]}...")
        print(f"   Status: {post['status']}")
        if post.get("url"):
            print(f"   {C.C}URL: {post['url']}{C.END}")
        elif post.get("result", {}).get("error"):
            print(f"   {C.R}Error: {post['result']['error'][:100]}{C.END}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
