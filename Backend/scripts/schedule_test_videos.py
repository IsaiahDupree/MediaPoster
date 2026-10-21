#!/usr/bin/env python3
"""
Schedule Test Videos Script
Schedules 3 analyzed videos to Instagram @the_isaiah_dupree for testing.
Videos will appear in the frontend schedule page at http://localhost:5557/schedule
"""

import asyncio
import httpx
from datetime import datetime, timedelta, timezone

API_URL = "http://localhost:5555"

# Videos to schedule (analyzed with pre_social_score)
VIDEOS = [
    {
        "media_id": "8d978df0-429c-4df7-a521-2db44c1a34dd",
        "filename": "BDEO9881.MOV",
        "score": 75
    },
    {
        "media_id": "8dd5973d-6de4-48c2-940f-9334b0dd480a",
        "filename": "IMG_3591.MOV",
        "score": 65
    },
    {
        "media_id": "471b2bfe-d8e7-4aab-ad0d-40645e30ebb4",
        "filename": "IMG_4573.MOV",
        "score": 65
    },
]

# Instagram account
INSTAGRAM_ACCOUNT = {
    "blotato_id": "807",
    "username": "the_isaiah_dupree",
    "platform": "instagram"
}


async def get_media_details(client: httpx.AsyncClient, media_id: str) -> dict:
    """Fetch media details and analysis"""
    try:
        # Get media details
        res = await client.get(f"{API_URL}/api/media-db/detail/{media_id}")
        if res.status_code != 200:
            return None
        media = res.json()
        
        # Get analysis for caption
        analysis_res = await client.get(f"{API_URL}/api/media-db/analysis/{media_id}")
        analysis = analysis_res.json() if analysis_res.status_code == 200 else {}
        
        return {
            "media": media,
            "analysis": analysis
        }
    except Exception as e:
        print(f"  ❌ Error fetching media {media_id}: {e}")
        return None


def get_caption_from_analysis(analysis: dict, platform: str) -> str:
    return None


async def schedule_video(client: httpx.AsyncClient, video: dict, scheduled_time: datetime) -> bool:
    return False


async def main():
    print("airtime_required: legacy scheduling test is disabled; use Airtime")
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()) or 0)
