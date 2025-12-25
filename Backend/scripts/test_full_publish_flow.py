#!/usr/bin/env python3
"""
Full Publish Flow Test Script
=============================
This script tests the complete publish flow:
1. Pick a random video from the media library
2. Generate title & description via AI (real OpenAI calls)
3. Save platform_content to database
4. Post to TikTok via Blotato

Run: python3 scripts/test_full_publish_flow.py
"""

import os
import sys
import json
import random
import requests
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

API_URL = "http://localhost:5555"

# ANSI colors for terminal output
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

def log(message: str, level: str = "INFO", color: str = Colors.WHITE):
    """Log a message with timestamp and level."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    level_colors = {
        "INFO": Colors.CYAN,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
        "DEBUG": Colors.MAGENTA,
        "STEP": Colors.BOLD + Colors.BLUE,
    }
    level_color = level_colors.get(level, Colors.WHITE)
    print(f"{Colors.CYAN}[{timestamp}]{Colors.END} {level_color}[{level}]{Colors.END} {color}{message}{Colors.END}")

def log_separator(title: str = ""):
    """Print a separator line."""
    print(f"\n{'='*70}")
    if title:
        print(f"{Colors.BOLD}{Colors.CYAN}{title}{Colors.END}")
        print('='*70)

def step(number: int, title: str):
    """Print a step header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}━━━ STEP {number}: {title} ━━━{Colors.END}\n")


# ==============================================================================
# STEP 1: GET RANDOM VIDEO FROM MEDIA LIBRARY
# ==============================================================================

def get_random_video():
    """Fetch a random video from the media library that has analysis data."""
    log("Fetching videos from media library...", "INFO")
    
    try:
        # Get videos with analysis data
        res = requests.get(f"{API_URL}/api/media-db/list?limit=100", timeout=30)
        
        if res.status_code != 200:
            log(f"Failed to fetch videos: HTTP {res.status_code}", "ERROR")
            return None
        
        data = res.json()
        # Handle different response formats
        if isinstance(data, list):
            videos = data
        elif isinstance(data, dict):
            videos = data.get("items", []) or data.get("videos", [])
        else:
            videos = []
        
        log(f"Found {len(videos)} videos in media library", "INFO")
        
        if not videos:
            log("No videos found in media library!", "ERROR")
            return None
        
        # Filter for videos with file_path (required for publishing)
        valid_videos = [v for v in videos if v.get("file_path")]
        log(f"Found {len(valid_videos)} videos with valid file paths", "INFO")
        
        if not valid_videos:
            log("No videos with valid file paths!", "ERROR")
            return None
        
        # Prefer videos that have been analyzed (have transcript/topics)
        analyzed_videos = [v for v in valid_videos if v.get("transcript") or v.get("topics") or v.get("pre_social_score")]
        
        if analyzed_videos:
            log(f"Found {len(analyzed_videos)} videos WITH analysis data (preferred)", "SUCCESS")
            video = random.choice(analyzed_videos)
        else:
            log("No analyzed videos found, picking random video...", "WARNING")
            video = random.choice(valid_videos)
        
        log(f"Selected video: {video.get('filename', 'Unknown')}", "SUCCESS")
        log(f"  Media ID: {video.get('media_id') or video.get('id')}", "DEBUG")
        log(f"  File path: {video.get('file_path', 'N/A')[:60]}...", "DEBUG")
        log(f"  Duration: {video.get('duration_sec', 'N/A')}s", "DEBUG")
        
        return video
        
    except Exception as e:
        log(f"Exception fetching videos: {e}", "ERROR")
        return None


# ==============================================================================
# STEP 2: GENERATE TITLE AND DESCRIPTION VIA AI
# ==============================================================================

def generate_content_for_video(media_id: str):
    """Generate title and description using AI (real OpenAI calls)."""
    log(f"Generating AI content for media_id: {media_id}", "INFO")
    
    try:
        # Call the generate-captions endpoint
        res = requests.post(
            f"{API_URL}/api/analysis/generate-captions/{media_id}",
            json={
                "platform": "tiktok",
                "tone": "engaging",
                "style": "viral",
                "include_hashtags": True,
                "include_hook": True,
                "custom_prompt": "Generate an engaging, viral-worthy title (max 80 chars) and a compelling description with hashtags. Make it catchy and attention-grabbing."
            },
            timeout=60
        )
        
        if res.status_code == 200:
            data = res.json()
            title = data.get("title", "")
            description = data.get("captions", {}).get("tiktok", "") or data.get("description", "")
            hashtags = data.get("hashtags", [])
            
            log(f"AI Generated Title: {title}", "SUCCESS")
            log(f"AI Generated Description ({len(description)} chars): {description[:100]}...", "SUCCESS")
            log(f"AI Generated Hashtags: {hashtags}", "SUCCESS")
            
            return {
                "title": title,
                "description": description,
                "hashtags": hashtags,
                "raw_response": data
            }
        else:
            log(f"Caption generation failed: HTTP {res.status_code}", "WARNING")
            log(f"Response: {res.text[:200]}", "DEBUG")
            return None
            
    except Exception as e:
        log(f"Exception generating captions: {e}", "ERROR")
        return None


# ==============================================================================
# STEP 3: SAVE PLATFORM CONTENT TO DATABASE
# ==============================================================================

def save_platform_content(media_id: str, title: str, description: str, hashtags: list, account_id: int = 710):
    """Save the generated content as platform_content in the database."""
    log(f"Saving platform_content to database for media_id: {media_id}", "INFO")
    
    # Build platform_content array for TikTok
    platform_content = [{
        "platform": "tiktok",
        "account_id": account_id,
        "username": "isaiah_dupree",
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "vertical_thumbnail_index": 0,
        "horizontal_thumbnail_index": 0,
    }]
    
    try:
        # Update analysis with platform_content
        res = requests.put(
            f"{API_URL}/api/media-db/analysis/{media_id}",
            json={"platform_content": platform_content},
            timeout=30
        )
        
        if res.status_code == 200:
            log("Successfully saved platform_content to database!", "SUCCESS")
            
            # Verify it was saved
            verify_res = requests.get(f"{API_URL}/api/media-db/analysis/{media_id}", timeout=10)
            if verify_res.status_code == 200:
                saved_data = verify_res.json()
                saved_pc = saved_data.get("platform_content", [])
                if saved_pc:
                    log(f"Verified: platform_content has {len(saved_pc)} entries", "SUCCESS")
                    log(f"  Title: {saved_pc[0].get('title', 'N/A')[:50]}...", "DEBUG")
                    log(f"  Description: {saved_pc[0].get('description', 'N/A')[:50]}...", "DEBUG")
                    return True
                else:
                    log("Warning: platform_content not found in saved data!", "WARNING")
            return True
        else:
            log(f"Failed to save platform_content: HTTP {res.status_code}", "ERROR")
            log(f"Response: {res.text[:200]}", "DEBUG")
            return False
            
    except Exception as e:
        log(f"Exception saving platform_content: {e}", "ERROR")
        return False


# ==============================================================================
# STEP 4: PUBLISH TO TIKTOK
# ==============================================================================

def publish_to_tiktok(media_id: str, title: str, description: str, hashtags: list, account_id: int = 710):
    """Publish the video to TikTok via the full-publish endpoint."""
    log(f"Publishing to TikTok (account {account_id})...", "INFO")
    
    # Combine description with hashtags
    full_caption = description
    if hashtags:
        hashtag_str = " ".join([f"#{h.strip('#')}" for h in hashtags[:5]])
        if hashtag_str not in full_caption:
            full_caption = f"{full_caption}\n\n{hashtag_str}"
    
    log(f"Title: {title}", "DEBUG")
    log(f"Caption ({len(full_caption)} chars): {full_caption[:100]}...", "DEBUG")
    
    payload = {
        "media_id": media_id,
        "blotato_account_id": str(account_id),
        "platform": "tiktok",
        "username": "isaiah_dupree",
        "text": full_caption,
        "title": title,
        "hashtags": hashtags,
        "cleanup_gdrive": True,
    }
    
    try:
        log("Calling /api/blotato/posts/full-publish endpoint...", "INFO")
        res = requests.post(
            f"{API_URL}/api/blotato/posts/full-publish",
            json=payload,
            timeout=300  # 5 minute timeout for upload + publish
        )
        
        if res.status_code == 200:
            data = res.json()
            success = data.get("success", False)
            post_id = data.get("post_submission_id")
            error = data.get("error")
            steps = data.get("steps", {})
            
            if success:
                log(f"🎉 PUBLISHED SUCCESSFULLY!", "SUCCESS", Colors.GREEN)
                log(f"  Post Submission ID: {post_id}", "SUCCESS")
                
                # Log step details
                for step_name, step_data in steps.items():
                    step_success = step_data.get("success", False) if isinstance(step_data, dict) else step_data
                    icon = "✓" if step_success else "✗"
                    log(f"  {icon} {step_name}: {step_data}", "DEBUG")
                
                return {
                    "success": True,
                    "post_submission_id": post_id,
                    "steps": steps
                }
            else:
                log(f"Publish failed: {error}", "ERROR")
                return {
                    "success": False,
                    "error": error,
                    "steps": steps
                }
        else:
            log(f"Publish request failed: HTTP {res.status_code}", "ERROR")
            log(f"Response: {res.text[:500]}", "DEBUG")
            return {
                "success": False,
                "error": f"HTTP {res.status_code}: {res.text[:200]}"
            }
            
    except requests.exceptions.Timeout:
        log("Request timed out after 5 minutes", "ERROR")
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        log(f"Exception during publish: {e}", "ERROR")
        return {"success": False, "error": str(e)}


# ==============================================================================
# MAIN FLOW
# ==============================================================================

def main():
    log_separator("FULL PUBLISH FLOW TEST")
    log("Testing the complete video → generate → save → publish flow", "INFO")
    log(f"Target: TikTok Account 710 (@isaiah_dupree)", "INFO")
    log(f"API URL: {API_URL}", "INFO")
    
    # Check API health
    try:
        health = requests.get(f"{API_URL}/api/health", timeout=5)
        if health.status_code == 200:
            log("API is healthy ✓", "SUCCESS")
        else:
            log(f"API health check failed: {health.status_code}", "ERROR")
            return
    except Exception as e:
        log(f"Cannot connect to API: {e}", "ERROR")
        return
    
    # STEP 1: Get random video
    step(1, "SELECT RANDOM VIDEO")
    video = get_random_video()
    if not video:
        log("Failed to get a video. Aborting.", "ERROR")
        return
    
    media_id = video.get("media_id") or video.get("id")
    filename = video.get("filename", "Unknown")
    
    # STEP 2: Generate AI content
    step(2, "GENERATE AI CONTENT")
    content = generate_content_for_video(media_id)
    
    if not content or not content.get("title"):
        log("AI generation failed or returned empty title. Using fallback...", "WARNING")
        # Fallback to transcript-based content
        content = {
            "title": f"Check this out! 🔥",
            "description": f"Amazing content from {filename}! Watch till the end 👀 #fyp #viral",
            "hashtags": ["#fyp", "#viral", "#trending", "#foryou"]
        }
        log(f"Using fallback title: {content['title']}", "WARNING")
    
    title = content["title"]
    description = content["description"]
    hashtags = content.get("hashtags", [])
    
    # STEP 3: Save to database
    step(3, "SAVE PLATFORM CONTENT TO DATABASE")
    saved = save_platform_content(media_id, title, description, hashtags, account_id=710)
    if not saved:
        log("Failed to save platform_content. Continuing anyway (backend has fallback)...", "WARNING")
    
    # STEP 4: Publish to TikTok
    step(4, "PUBLISH TO TIKTOK")
    result = publish_to_tiktok(media_id, title, description, hashtags, account_id=710)
    
    # Final Summary
    log_separator("FINAL RESULTS")
    
    print(f"\n{Colors.BOLD}Video:{Colors.END} {filename}")
    print(f"{Colors.BOLD}Media ID:{Colors.END} {media_id}")
    print(f"{Colors.BOLD}Title:{Colors.END} {title}")
    print(f"{Colors.BOLD}Description:{Colors.END} {description[:100]}...")
    print(f"{Colors.BOLD}Hashtags:{Colors.END} {hashtags}")
    
    if result.get("success"):
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ SUCCESS!{Colors.END}")
        print(f"{Colors.GREEN}Post Submission ID: {result.get('post_submission_id')}{Colors.END}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ FAILED{Colors.END}")
        print(f"{Colors.RED}Error: {result.get('error')}{Colors.END}")
    
    print("\n" + "="*70)
    
    return result


if __name__ == "__main__":
    main()
