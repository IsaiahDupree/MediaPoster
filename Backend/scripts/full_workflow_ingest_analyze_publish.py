#!/usr/bin/env python3
"""
Full Workflow: Ingest → Analyze → Generate Content → Schedule → Publish to TikTok

This script demonstrates the complete workflow:
1. Finds/ingests a video from iPhone import directory
2. Runs full AI analysis
3. Generates platform-specific titles/descriptions using 100% analysis context
4. Schedules the post
5. Publishes to TikTok via Blotato
6. Shows the TikTok URL and schedule entry

PROBLEM EXPLANATION:
===================
The platform_content field was not saving because the save logic was commented out
in Backend/api/media_processing_db.py. Even though:
- The column exists in the database (JSONB type)
- The request model accepts platform_content
- The data was being sent correctly

The fix uncommented the saving logic so platform_content now persists properly.
"""
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
import time
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:5555"
IPHONE_IMPORT_DIR = Path.home() / "Documents" / "IphoneImport"
TIKTOK_ACCOUNT_ID = "710"  # Update with your TikTok account ID


def find_video_to_process() -> tuple[str, str]:
    """Find a video that's ingested but not yet analyzed"""
    # Get list of videos
    response = requests.get(f"{BASE_URL}/api/media-db/list?limit=50", timeout=30)
    if response.status_code != 200:
        raise Exception(f"Failed to get video list: {response.status_code}")
    
    videos = response.json()
    
    # Find an ingested (not analyzed) video
    for video in videos:
        if video.get("status") == "ingested":
            return video["media_id"], video.get("filename", "unknown")
    
    # If all are analyzed, use the first one
    if videos:
        return videos[0]["media_id"], videos[0].get("filename", "unknown")
    
    raise Exception("No videos found in database")


def ingest_video_if_needed() -> tuple[str, str]:
    raise RuntimeError("script_hub_required: legacy ingestion and generation are disabled")


def run_analysis(media_id: str) -> dict:
    raise RuntimeError("script_hub_required: legacy analysis and generation are disabled")


def generate_platform_content(media_id: str, analysis: dict) -> dict:
    raise RuntimeError("script_hub_required: generate through ScriptHub")


def save_platform_content(media_id: str, captions: dict):
    raise RuntimeError("script_hub_required: content storage is owned by ScriptHub")


def schedule_post(media_id: str, captions: dict):
    raise RuntimeError("airtime_required: schedule through Airtime")


def publish_to_tiktok(media_id: str, captions: dict) -> dict:
    return {"success": False, "error": "airtime_required"}


def check_schedule(media_id: str):
    """Check if the post appears in the schedule"""
    logger.info("📋 Checking schedule...")
    
    response = requests.get(f"{BASE_URL}/api/schedule/list", timeout=30)
    
    if response.status_code == 200:
        schedules = response.json()
        
        # Find our scheduled post
        our_schedule = next(
            (s for s in schedules if s.get("media_id") == media_id),
            None
        )
        
        if our_schedule:
            logger.success("✅ Found in schedule:")
            logger.info(f"   Scheduled at: {our_schedule.get('scheduled_at')}")
            logger.info(f"   Platform: {our_schedule.get('platform')}")
            logger.info(f"   Status: {our_schedule.get('status')}")
        else:
            logger.warning("   ⚠️  Not found in schedule list")


def main():
    logger.error("airtime_required: legacy MediaPoster workflow is disabled; use ScriptHub and Airtime")
    return 2


if __name__ == "__main__":
    raise SystemExit(main() or 0)

