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
    raise RuntimeError("script_hub_required: generate through ScriptHub")


# ==============================================================================
# STEP 3: SAVE PLATFORM CONTENT TO DATABASE
# ==============================================================================

def save_platform_content(media_id: str, title: str, description: str, hashtags: list, account_id: int = 710):
    raise RuntimeError("script_hub_required: content storage is owned by ScriptHub")


# ==============================================================================
# STEP 4: PUBLISH TO TIKTOK
# ==============================================================================

def publish_to_tiktok(media_id: str, title: str, description: str, hashtags: list, account_id: int = 710):
    return {"success": False, "error": "airtime_required"}


# ==============================================================================
# MAIN FLOW
# ==============================================================================

def main():
    log("airtime_required: legacy publish flow is disabled; use ScriptHub and Airtime", "ERROR")
    return 2


if __name__ == "__main__":
    raise SystemExit(main() or 0)
