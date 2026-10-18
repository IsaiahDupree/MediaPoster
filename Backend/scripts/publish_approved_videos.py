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
    """Ingest video to media-db and return media_id."""
    try:
        res = requests.post(
            f"{API_URL}/api/media-db/ingest/file",
            params={"file_path": video_path},
            timeout=60
        )
        if res.status_code == 200:
            data = res.json()
            return data.get('id') or data.get('media_id') or data.get('media', {}).get('id')
        else:
            log(f"Ingest failed: {res.text[:100]}", C.R)
    except Exception as e:
        log(f"Ingest error: {e}", C.R)
    return None


# =============================================================================
# STEP 3: ANALYZE VIDEO
# =============================================================================

def analyze_video(media_id):
    """Run analysis on video to get hooks, topics, transcript."""
    try:
        log(f"   Analyzing video (this may take 30-60 seconds)...", C.Y)
        res = requests.post(
            f"{API_URL}/api/media-db/analyze/{media_id}",
            timeout=120
        )
        if res.status_code == 200:
            return True
        else:
            log(f"   Analysis failed: {res.text[:100]}", C.R)
    except Exception as e:
        log(f"   Analysis error: {e}", C.R)
    return False

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
    """
    Generate AI title and caption using analysis context.
    Uses hooks, topics, and transcript from the analysis.
    """
    try:
        # Build request with analysis context
        payload = {
            "platform": "tiktok",
            "tone": analysis_data.get('tone', 'engaging'),
            "include_hashtags": True,
            "include_hook": True
        }
        
        # Add hooks from analysis
        hooks = analysis_data.get('hooks', [])
        if hooks:
            payload['hooks'] = hooks[:3]
        
        res = requests.post(
            f"{API_URL}/api/analysis/generate-captions/{media_id}",
            json=payload,
            timeout=60
        )
        
        if res.status_code == 200:
            data = res.json()
            title = data.get("title", "")
            caption = data.get("captions", {}).get("tiktok", "")
            
            # Clean title - remove filename patterns
            title = clean_title(title)
            
            # If title is empty or too short, generate from topics/hooks
            if len(title) < 10:
                topics = analysis_data.get('topics', [])
                hooks = analysis_data.get('hooks', [])
                
                if hooks and len(hooks) > 0:
                    # Use first hook as title
                    title = hooks[0][:TIKTOK_TITLE_LIMIT]
                elif topics and len(topics) > 0:
                    title = f"Discover: {', '.join(topics[:2])}"
                else:
                    title = "Must Watch Content!"
            
            # Enforce TikTok limits
            if len(title) > TIKTOK_TITLE_LIMIT:
                title = title[:TIKTOK_TITLE_LIMIT-3] + "..."
            
            if len(caption) > TIKTOK_CAPTION_LIMIT:
                caption = caption[:TIKTOK_CAPTION_LIMIT-3] + "..."
            
            # Ensure caption has hashtags
            if '#' not in caption:
                caption += "\n\n#fyp #viral #trending"
            
            return {"title": title, "caption": caption}
            
    except Exception as e:
        log(f"   Caption generation error: {e}", C.R)
    
    # Fallback using analysis data directly
    topics = analysis_data.get('topics', [])
    hooks = analysis_data.get('hooks', [])
    
    if hooks:
        title = hooks[0][:TIKTOK_TITLE_LIMIT]
    elif topics:
        title = f"Discover: {', '.join(topics[:2])}"[:TIKTOK_TITLE_LIMIT]
    else:
        title = "Must Watch Content!"
    
    caption = f"Check this out! #fyp #viral"
    if topics:
        hashtags = ' '.join([f"#{t.replace(' ', '').lower()}" for t in topics[:3]])
        caption = f"Amazing content about {', '.join(topics[:2])}! {hashtags} #fyp #viral"
    
    return {"title": title, "caption": caption}


# =============================================================================
# STEP 5: PUBLISH VIA GOOGLE DRIVE + BLOTATO (WITH URL TRACKING)
# =============================================================================

def publish_video(media_id, title, caption):
    """
    Publish video via full-publish flow with Google Drive.
    Then poll for the public URL using the status endpoint.
    """
    try:
        text = f"{title}\n\n{caption}"
        
        # Use regular full-publish endpoint (faster, no blocking poll)
        res = requests.post(
            f"{API_URL}/api/blotato/posts/full-publish",
            json={
                "media_id": media_id,
                "blotato_account_id": TIKTOK_ACCOUNT_ID,
                "platform": "tiktok",
                "username": TIKTOK_USERNAME,
                "text": text,
                "cleanup_gdrive": True
            },
            timeout=120
        )
        
        if res.status_code == 200:
            data = res.json()
            post_id = data.get("post_submission_id")
            
            return {
                "success": data.get("success", False),
                "post_id": post_id,
                "url": None,  # Will poll for URL after
                "error": data.get("error")
            }
        else:
            return {"success": False, "error": f"HTTP {res.status_code}: {res.text[:200]}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timeout during upload"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
    print("\n" + "="*70)
    print(f"{C.BOLD}{C.C}🎬 PUBLISH APPROVED+ANALYZED VIDEOS TO TIKTOK{C.END}")
    print("="*70)
    print(f"Account: {TIKTOK_ACCOUNT_ID} (@{TIKTOK_USERNAME})")
    print(f"Title Limit: {TIKTOK_TITLE_LIMIT} chars | Caption Limit: {TIKTOK_CAPTION_LIMIT} chars")
    print(f"Filter: Video + Analyzed + Approved (with valid file paths)")
    print("="*70)
    
    # Step 1: Get approved+analyzed videos from API
    log_step(1, "Fetching approved+analyzed videos from API")
    
    videos = get_approved_analyzed_videos(limit=5)
    
    if not videos:
        log("❌ No approved+analyzed videos found with valid file paths!", C.R)
        log("Make sure you have videos that are:", C.Y)
        log("  - Media type: Video (.mov, .mp4)", C.Y)
        log("  - Analysis status: Analyzed", C.Y)
        log("  - Curation status: Approved", C.Y)
        log("  - Have valid file_path in database", C.Y)
        return
    
    log(f"✅ Found {len(videos)} videos ready to publish", C.G)
    
    print(f"\n{C.BOLD}Videos to publish:{C.END}")
    for i, v in enumerate(videos):
        topics = v.get('topics', [])[:2]
        log(f"  {i+1}. {v['title']} (score: {v['score']})", C.W)
        log(f"     Topics: {topics}", C.W)
    
    # Process each video
    results = []
    
    for idx, video in enumerate(videos):
        print(f"\n{'─'*70}")
        print(f"{C.BOLD}Video {idx+1}/{len(videos)}: {video['title']}{C.END}")
        print(f"{'─'*70}")
        
        media_id = video['id']
        
        # Show analysis data
        log_step(2, "Using existing analysis data")
        hooks = video.get('hooks', [])
        topics = video.get('topics', [])
        log(f"   Hooks: {hooks[:2] if hooks else 'None'}", C.W)
        log(f"   Topics: {topics[:3] if topics else 'None'}", C.W)
        log(f"   Tone: {video.get('tone', 'N/A')}", C.W)
        
        # Generate title & caption using analysis
        log_step(3, "Generating AI title & caption from analysis")
        
        content = generate_title_caption(media_id, video)
        title = content['title']
        caption = content['caption']
        
        log(f"📝 Title ({len(title)} chars): {title}", C.G)
        log(f"📝 Caption preview: {caption[:100]}...", C.G)
        
        # Publish
        log_step(4, "Publishing via Google Drive + Blotato")
        
        log(f"📤 Uploading video to Google Drive...", C.M)
        log(f"   File: {video['file_path']}", C.W)
        
        result = publish_video(media_id, title, caption)
        
        result['video'] = video['title']
        result['title'] = title
        result['media_id'] = media_id
        result['topics'] = topics
        
        if result['success']:
            log(f"✅ Published successfully!", C.G)
            
            post_id = result.get('post_id')
            url = result.get('url')
            
            if post_id:
                log(f"📋 Blotato Post ID: {post_id}", C.W)
            
            # If we didn't get URL from the response, poll for it
            if not url and post_id:
                log(f"📊 Polling Blotato for TikTok URL...", C.Y)
                url = poll_for_post_url(post_id, max_attempts=6, delay=10)
                result['url'] = url
            
            if url:
                log(f"🔗 TikTok URL: {url}", C.C)
            else:
                log(f"⚠️ URL not available yet (post may still be processing)", C.Y)
            
            # Show steps if available
            steps = result.get('steps', {})
            if steps:
                log(f"   Steps completed: {list(steps.keys())}", C.W)
        else:
            log(f"❌ Publish failed: {result.get('error', 'Unknown')[:150]}", C.R)
        
        results.append(result)
        
        # Wait between posts (15 seconds)
        if idx < len(videos) - 1:
            log(f"\n⏳ Waiting 15 seconds before next video...", C.Y)
            time.sleep(15)
    
    # Final summary
    print("\n" + "="*70)
    print(f"{C.BOLD}FINAL RESULTS{C.END}")
    print("="*70)
    
    success = sum(1 for r in results if r.get('success'))
    failed = len(results) - success
    
    print(f"\n{C.G}✅ Success: {success}/{len(results)}{C.END}")
    print(f"{C.R}❌ Failed: {failed}/{len(results)}{C.END}")
    
    print(f"\n{'─'*70}")
    print("POST DETAILS:")
    print(f"{'─'*70}")
    
    for i, r in enumerate(results):
        icon = "✅" if r.get('success') else "❌"
        print(f"\n{icon} Video {i+1}: {r.get('video', 'Unknown')}")
        print(f"   Title: {r.get('title', 'N/A')}")
        print(f"   Topics: {r.get('topics', [])[:2]}")
        
        if r.get('success'):
            if r.get('url'):
                print(f"   {C.C}🔗 URL: {r['url']}{C.END}")
            if r.get('post_id'):
                print(f"   📋 Post ID: {r['post_id']}")
            if r.get('polling_url'):
                print(f"   {C.C}📊 Polling: {r['polling_url']}{C.END}")
        else:
            print(f"   {C.R}Error: {r.get('error', 'Unknown')[:100]}{C.END}")
    
    print("\n" + "="*70)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
