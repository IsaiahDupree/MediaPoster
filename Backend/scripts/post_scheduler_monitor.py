#!/usr/bin/env python3
"""
Post Scheduler Monitor
Schedules posts and monitors their status changes in real-time.
Shows timer, events, and captures URLs for successful posts.
"""

import requests
import time
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict

API_URL = "http://localhost:5555"

# ANSI colors for terminal
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(message: str, color: str = Colors.WHITE):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.CYAN}[{timestamp}]{Colors.END} {color}{message}{Colors.END}")

def log_event(event_type: str, message: str):
    icons = {
        "schedule": "📅",
        "pending": "⏳",
        "processing": "🔄",
        "posted": "✅",
        "failed": "❌",
        "url": "🔗",
        "timer": "⏱️",
        "info": "ℹ️",
    }
    icon = icons.get(event_type, "•")
    color = {
        "schedule": Colors.BLUE,
        "pending": Colors.YELLOW,
        "processing": Colors.MAGENTA,
        "posted": Colors.GREEN,
        "failed": Colors.RED,
        "url": Colors.CYAN,
        "timer": Colors.WHITE,
        "info": Colors.WHITE,
    }.get(event_type, Colors.WHITE)
    log(f"{icon} {message}", color)

def get_approved_videos(limit: int = 5) -> List[Dict]:
    """Get top approved videos from media library."""
    try:
        res = requests.get(f"{API_URL}/api/analyzed-content/list?curation_status=approved&limit={limit}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data.get("items", [])
    except Exception as e:
        log_event("failed", f"Failed to fetch videos: {e}")
    return []

def generate_caption(video_id: str) -> Dict:
    """Generate AI caption for a video."""
    try:
        res = requests.post(
            f"{API_URL}/api/analysis/generate-captions/{video_id}",
            json={"platform": "tiktok", "tone": "engaging", "include_hashtags": True},
            timeout=30
        )
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        log_event("failed", f"Caption generation failed: {e}")
    return {"title": "Amazing Content", "captions": {"tiktok": "Check this out! #fyp"}}

def schedule_post(video_id: str, title: str, caption: str, scheduled_at: datetime) -> str:
    """Schedule a post and return the post ID."""
    try:
        res = requests.post(
            f"{API_URL}/api/schedule/create",
            json={
                "content_id": video_id,
                "title": title,
                "caption": caption,
                "platform": "tiktok",
                "account_id": "710",
                "account_username": "isaiah_dupree",
                "scheduled_at": scheduled_at.isoformat()
            },
            timeout=10
        )
        if res.status_code in [200, 201]:
            data = res.json()
            return data.get("id")
    except Exception as e:
        log_event("failed", f"Schedule failed: {e}")
    return None

def get_post_status(post_id: str) -> Dict:
    """Get current post status."""
    try:
        res = requests.get(f"{API_URL}/api/schedule/{post_id}", timeout=5)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {}

def format_time_until(target: datetime) -> str:
    """Format time remaining until target."""
    now = datetime.now(timezone.utc)
    diff = target - now
    if diff.total_seconds() < 0:
        return "NOW"
    minutes, seconds = divmod(int(diff.total_seconds()), 60)
    return f"{minutes}m {seconds}s"

def main():
    print("\n" + "="*60)
    print(f"{Colors.BOLD}{Colors.CYAN}🚀 POST SCHEDULER MONITOR{Colors.END}")
    print("="*60 + "\n")
    
    # Step 1: Get approved videos
    log_event("info", "Fetching top 5 approved videos...")
    videos = get_approved_videos(5)
    
    if len(videos) < 5:
        log_event("failed", f"Only found {len(videos)} approved videos, need 5")
        return
    
    log_event("info", f"Found {len(videos)} approved videos")
    
    # Step 2: Schedule posts 12 seconds apart (5 posts within 1 minute)
    scheduled_posts = []
    start_time = datetime.now(timezone.utc) + timedelta(seconds=30)  # Start in 30 seconds
    
    print("\n" + "-"*60)
    print(f"{Colors.BOLD}SCHEDULING POSTS{Colors.END}")
    print("-"*60)
    
    for i, video in enumerate(videos[:5]):
        video_id = video.get("id")
        scheduled_at = start_time + timedelta(seconds=i * 12)  # 12 seconds apart
        
        # Generate caption
        log_event("info", f"Generating caption for video {i+1}...")
        caption_data = generate_caption(video_id)
        title = caption_data.get("title", f"Video {i+1}")
        caption = caption_data.get("captions", {}).get("tiktok", "Amazing content! #fyp")
        
        # Schedule post
        post_id = schedule_post(video_id, title, caption, scheduled_at)
        
        if post_id:
            scheduled_posts.append({
                "id": post_id,
                "title": title[:40],
                "scheduled_at": scheduled_at,
                "video_id": video_id,
                "status": "scheduled",
                "url": None
            })
            log_event("schedule", f"Post {i+1}: {title[:30]}... @ {scheduled_at.strftime('%H:%M:%S')} UTC")
        else:
            log_event("failed", f"Failed to schedule post {i+1}")
    
    if not scheduled_posts:
        log_event("failed", "No posts were scheduled")
        return
    
    print("\n" + "-"*60)
    print(f"{Colors.BOLD}MONITORING STATUS CHANGES{Colors.END}")
    print("-"*60)
    print("Watching for: scheduled → processing → posted/failed\n")
    
    # Step 3: Monitor posts for status changes
    status_history = {p["id"]: ["scheduled"] for p in scheduled_posts}
    all_done = False
    monitor_start = datetime.now()
    max_monitor_time = 300  # 5 minutes max
    
    while not all_done and (datetime.now() - monitor_start).seconds < max_monitor_time:
        all_done = True
        
        for post in scheduled_posts:
            post_id = post["id"]
            current_status = post["status"]
            
            # Skip if already in terminal state
            if current_status in ["posted", "failed"]:
                continue
            
            all_done = False
            
            # Check status
            post_data = get_post_status(post_id)
            new_status = post_data.get("status", current_status)
            
            # Detect status change
            if new_status != current_status:
                post["status"] = new_status
                status_history[post_id].append(new_status)
                
                # Log the change
                if new_status == "posted":
                    post_url = post_data.get("post_url") or post_data.get("url")
                    post["url"] = post_url
                    log_event("posted", f"✅ {post['title']}...")
                    if post_url:
                        log_event("url", f"   URL: {post_url}")
                elif new_status == "failed":
                    error = post_data.get("error") or "Unknown error"
                    log_event("failed", f"❌ {post['title']}... - {error}")
                elif new_status == "processing":
                    log_event("processing", f"🔄 {post['title']}...")
                else:
                    log_event("info", f"Status changed to {new_status}: {post['title']}...")
            
            # Show timer for pending posts
            time_until = format_time_until(post["scheduled_at"])
            if time_until != "NOW" and current_status == "scheduled":
                pass  # Don't spam with timer updates
        
        # Status summary every 5 seconds
        time.sleep(2)
        
        # Print current status
        posted = sum(1 for p in scheduled_posts if p["status"] == "posted")
        failed = sum(1 for p in scheduled_posts if p["status"] == "failed")
        pending = sum(1 for p in scheduled_posts if p["status"] in ["scheduled", "pending", "processing"])
        
        elapsed = (datetime.now() - monitor_start).seconds
        if elapsed % 10 == 0 and pending > 0:
            log_event("timer", f"Status: {posted} posted, {failed} failed, {pending} pending | Elapsed: {elapsed}s")
    
    # Final summary
    print("\n" + "="*60)
    print(f"{Colors.BOLD}FINAL RESULTS{Colors.END}")
    print("="*60)
    
    posted_count = sum(1 for p in scheduled_posts if p["status"] == "posted")
    failed_count = sum(1 for p in scheduled_posts if p["status"] == "failed")
    pending_count = sum(1 for p in scheduled_posts if p["status"] not in ["posted", "failed"])
    
    print(f"\n{Colors.GREEN}✅ Posted: {posted_count}{Colors.END}")
    print(f"{Colors.RED}❌ Failed: {failed_count}{Colors.END}")
    print(f"{Colors.YELLOW}⏳ Pending: {pending_count}{Colors.END}")
    
    print("\n" + "-"*60)
    print("POST DETAILS:")
    print("-"*60)
    
    for i, post in enumerate(scheduled_posts):
        status_icon = "✅" if post["status"] == "posted" else "❌" if post["status"] == "failed" else "⏳"
        print(f"\n{i+1}. {status_icon} {post['title']}...")
        print(f"   ID: {post['id']}")
        print(f"   Status: {post['status']}")
        print(f"   History: {' → '.join(status_history[post['id']])}")
        if post["url"]:
            print(f"   URL: {Colors.CYAN}{post['url']}{Colors.END}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
