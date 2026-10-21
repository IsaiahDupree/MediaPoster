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
    return None

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
    return {"success": False, "error": "airtime_required"}

def update_post_status(post_id, status, url=None):
    raise RuntimeError("airtime_required: schedule state is owned by Airtime")

def main():
    log("airtime_required: direct publishing test is disabled; use Airtime")
    return 2

if __name__ == "__main__":
    raise SystemExit(main() or 0)
