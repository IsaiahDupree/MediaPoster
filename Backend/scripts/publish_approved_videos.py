#!/usr/bin/env python3
"""
Publish Approved+Analyzed Videos to TikTok
==========================================
Uses ONLY analyzed+approved videos from media library with valid file paths.

Flow:
1. Query API for analyzed+approved videos with valid file paths
2. Generate AI title/caption using analysis context (hooks, topics, transcript)
3. Upload to Google Drive → Blotato → TikTok
4. Capture polling URL and post result

TikTok Limits:
- Title: 150 characters max
- Caption: 2200 characters max

Usage:
    python3 scripts/publish_approved_videos.py
"""

import requests
import time
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_URL = "http://localhost:5555"

# TikTok character limits
TIKTOK_TITLE_LIMIT = 150
TIKTOK_CAPTION_LIMIT = 2200

# Account: 710 = @isaiah_dupree
TIKTOK_ACCOUNT_ID = "710"
TIKTOK_USERNAME = "isaiah_dupree"

# Colors
class C:
    R, G, Y, B, M, C, W = '\033[91m', '\033[92m', '\033[93m', '\033[94m', '\033[95m', '\033[96m', '\033[97m'
    BOLD, END = '\033[1m', '\033[0m'

def log(msg, color=C.W):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C.C}[{ts}]{C.END} {color}{msg}{C.END}")

def log_step(step, msg):
    print(f"\n{C.BOLD}{C.B}═══ Step {step}: {msg} ═══{C.END}")


# =============================================================================
# STEP 1: GET APPROVED+ANALYZED VIDEOS FROM API
# =============================================================================

def get_approved_analyzed_videos(limit=10):
    """
    Get approved+analyzed videos from the API that have valid file paths.
    Uses filters: media_type=video, analysis_status=analyzed, curation_status=approved
    """
    valid_videos = []
    
    try:
        # Query for analyzed+approved videos
        res = requests.get(
            f"{API_URL}/api/analyzed-content/list",
            params={
                "media_type": "video",
                "analysis_status": "analyzed",
                "curation_status": "approved",
                "limit": limit * 2  # Get extra in case some don't have valid paths
            },
            timeout=30
        )
        
        if res.status_code != 200:
            log(f"API error: {res.status_code}", C.R)
            return []
        
        items = res.json().get('items', [])
        log(f"Found {len(items)} approved+analyzed videos in API", C.W)
        
        # Check each video has a valid file path
        for item in items:
            media_id = item.get('id')
            
            # Get full details including file_path
            detail_res = requests.get(f"{API_URL}/api/media-db/detail/{media_id}", timeout=10)
            if detail_res.status_code != 200:
                continue
            
            detail = detail_res.json()
            file_path = detail.get('file_path', '')
            
            # Skip test videos and invalid paths
            if not file_path or not os.path.exists(file_path):
                continue
            if 'test' in file_path.lower():
                continue
            if not any(file_path.lower().endswith(ext) for ext in ['.mov', '.mp4', '.m4v']):
                continue
            
            valid_videos.append({
                "id": media_id,
                "title": item.get('title', 'Unknown'),
                "file_path": file_path,
                "score": item.get('score', 0),
                "hooks": detail.get('hooks', []),
                "topics": detail.get('topics', []),
                "transcript": detail.get('transcript', ''),
                "tone": detail.get('tone', ''),
            })
            
            if len(valid_videos) >= limit:
                break
        
        return valid_videos
        
    except Exception as e:
        log(f"Error fetching videos: {e}", C.R)
        return []


# =============================================================================
# STEP 2: INGEST VIDEO TO MEDIA-DB
# =============================================================================

def ingest_video(video_path):
    return None


# =============================================================================
# STEP 3: ANALYZE VIDEO
# =============================================================================

def analyze_video(media_id):
    return None

def get_analysis_data(media_id):
    """Get analysis data for a video."""
    try:
        res = requests.get(f"{API_URL}/api/analysis/results/{media_id}", timeout=10)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {}


# =============================================================================
# STEP 4: GENERATE PROPER TITLE & CAPTION
# =============================================================================

def clean_title(title):
    """Clean title by removing filename patterns and enforcing limits."""
    if not title:
        return ""
    
    # Remove file extensions
    for ext in ['.mov', '.mp4', '.MOV', '.MP4', '.png', '.PNG', '.jpg', '.JPG', '.HEIC', '.heic']:
        title = title.replace(ext, '')
    
    # Remove common filename patterns
    title = re.sub(r'IMG_\d+', '', title)
    title = re.sub(r'[A-Z]{4}\d{4}', '', title)
    title = re.sub(r'^[\s._-]+|[\s._-]+$', '', title)
    
    # Remove leading emoji if followed by filename remnant
    title = re.sub(r'^[🔥✨💡🚀🎬📱]+\s*$', '', title)
    
    return title.strip()


def generate_title_caption(media_id, analysis_data):
    return None


# =============================================================================
# STEP 5: PUBLISH VIA GOOGLE DRIVE + BLOTATO (WITH URL TRACKING)
# =============================================================================

def publish_video(media_id, title, caption):
    return {"success": False, "error": "airtime_required"}


def poll_for_post_url(post_submission_id, max_attempts=12, delay=10):
    """
    Poll Blotato API to get the public URL for a post.
    TikTok posts can take 30-120 seconds to process.
    
    Note: Blotato may return profile URL initially. Specific video URLs 
    may take additional time as TikTok processes the upload.
    """
    if not post_submission_id:
        log(f"   ⚠️ No submission ID to poll", C.Y)
        return None
    
    log(f"   📊 Polling for TikTok URL (ID: {post_submission_id[:20]}...)", C.Y)
    
    for attempt in range(max_attempts):
        try:
            # Use correct endpoint: /posts/status/{submission_id}
            res = requests.get(
                f"{API_URL}/api/blotato/posts/status/{post_submission_id}",
                timeout=30
            )
            
            if res.status_code == 200:
                data = res.json()
                url = data.get("publicUrl") or data.get("public_url") or data.get("url")
                status = data.get("status", "unknown")
                
                log(f"   Poll {attempt + 1}/{max_attempts}: status={status}", C.W)
                
                if status in ["failed", "error", "FAILED"]:
                    error_msg = data.get('errorMessage') or data.get('error') or 'Unknown error'
                    log(f"   ❌ Post failed: {error_msg}", C.R)
                    return None
                
                if status in ["published", "PUBLISHED"]:
                    if url:
                        # Check if it's a specific video URL (contains /video/)
                        if '/video/' in url:
                            log(f"   ✅ Got TikTok video URL!", C.G)
                            return url
                        else:
                            # Profile URL - video URL may not be available yet from TikTok
                            log(f"   ✅ Published! Profile: {url}", C.G)
                            log(f"   ℹ️ Specific video URL pending from TikTok", C.W)
                            return url
                    else:
                        log(f"   ⚠️ Published but no URL yet", C.Y)
            else:
                log(f"   Poll returned {res.status_code}", C.Y)
            
            time.sleep(delay)
            
        except Exception as e:
            log(f"   Poll error: {e}", C.R)
            time.sleep(delay)
    
    log(f"   ⚠️ URL not available after {max_attempts * delay}s", C.Y)
    return None


def get_post_polling_status(post_id):
    """Poll Blotato for post status and URL."""
    try:
        res = requests.get(f"{API_URL}/api/blotato/posts/{post_id}/status", timeout=30)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {}


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("script_hub_required: legacy MediaPoster publishing is disabled; use ScriptHub and Airtime")
    return 2


if __name__ == "__main__":
    raise SystemExit(main() or 0)
