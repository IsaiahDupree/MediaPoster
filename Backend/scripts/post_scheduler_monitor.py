#!/usr/bin/env python3
"""Legacy post scheduler; command-line scheduling is blocked pending Airtime migration."""

import requests
import time
import sys
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

def generate_caption(video_id: str) -> Dict | None:
    """Block unreceipted legacy generation; drafts must come from ScriptHub."""
    log_event("failed", f"script_hub_required: legacy caption generation blocked for {video_id}")
    return None

def schedule_post(video_id: str, title: str, caption: str, scheduled_at: datetime) -> str | None:
    """Reject legacy queue writes; Airtime owns all social scheduling."""
    log_event("failed", "airtime_required: legacy schedule write blocked")
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
    log_event("failed", "airtime_required: this legacy scheduling command is disabled; submit approved content through Airtime")
    return 2

if __name__ == "__main__":
    sys.exit(main())
