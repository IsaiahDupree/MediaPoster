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
    """Extract caption from analysis data"""
    # Try platform_content first
    platform_content = analysis.get("platform_content") or []
    for pc in platform_content:
        if pc.get("platform", "").lower() == platform.lower():
            caption = pc.get("description") or pc.get("caption") or pc.get("text")
            if caption:
                return caption
    
    # Fall back to suggested caption
    deep = analysis.get("deep_analysis", {})
    if deep.get("suggested_caption"):
        return deep["suggested_caption"]
    
    # Fall back to transcript
    transcript = analysis.get("transcript", "")
    if transcript:
        return transcript[:200] + "..." if len(transcript) > 200 else transcript
    
    return "Check out this video! 🎬 #content #video"


async def schedule_video(client: httpx.AsyncClient, video: dict, scheduled_time: datetime) -> bool:
    """Schedule a single video"""
    media_id = video["media_id"]
    filename = video["filename"]
    
    print(f"\n📹 Scheduling: {filename}")
    print(f"   Media ID: {media_id}")
    
    # Get media details and analysis
    details = await get_media_details(client, media_id)
    if not details:
        print(f"   ❌ Failed to get media details")
        return False
    
    media = details["media"]
    analysis = details["analysis"]
    
    # Get caption
    caption = get_caption_from_analysis(analysis, "instagram")
    
    # Add hashtags if not present
    if "#" not in caption:
        hashtags = analysis.get("deep_analysis", {}).get("suggested_hashtags", [])
        if not hashtags:
            topics = analysis.get("topics", [])
            hashtags = [f"#{t.replace(' ', '')}" for t in topics[:5]]
        if hashtags:
            caption = f"{caption}\n\n{' '.join(hashtags)}"
    
    # Generate proper title from analysis, not filename
    title = None
    if analysis:
        # Try to get title from analysis
        title = (
            analysis.get("title") or
            (analysis.get("topics", [])[0] if analysis.get("topics") else None) or
            (analysis.get("hooks", [])[0] if analysis.get("hooks") else None)
        )
    
    # Fallback to generic title if still no good title
    if not title or title.startswith(('IMG_', 'VID_', 'MOV_')) or len(title) < 5:
        title = "Check this out"
    
    # Build schedule request
    payload = {
        "content_id": media_id,
        "title": title,  # Use proper title, not filename
        "caption": caption,
        "hashtags": [],
        "platform": INSTAGRAM_ACCOUNT["platform"],
        "account_id": INSTAGRAM_ACCOUNT["blotato_id"],
        "account_username": INSTAGRAM_ACCOUNT["username"],
        "blotato_account_id": INSTAGRAM_ACCOUNT["blotato_id"],
        "scheduled_at": scheduled_time.isoformat(),
        "post_type": "reel",
        "thumbnail_url": media.get("thumbnail_url")
    }
    
    print(f"   📅 Scheduled for: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   📝 Caption: {caption[:60]}...")
    
    # Create scheduled post
    try:
        res = await client.post(f"{API_URL}/api/schedule/create", json=payload)
        if res.status_code == 200:
            data = res.json()
            print(f"   ✅ Scheduled! ID: {data.get('id')}")
            return True
        else:
            print(f"   ❌ Failed: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def main():
    print("=" * 60)
    print("📅 SCHEDULE TEST VIDEOS")
    print("=" * 60)
    print(f"\n🎯 Target: Instagram @{INSTAGRAM_ACCOUNT['username']} (ID: {INSTAGRAM_ACCOUNT['blotato_id']})")
    print(f"📹 Videos: {len(VIDEOS)}")
    
    # Schedule times: 2 min apart starting from now
    base_time = datetime.now(timezone.utc) + timedelta(minutes=1)
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Verify API is up
        try:
            health = await client.get(f"{API_URL}/api/blotato/health")
            if health.status_code != 200:
                print("\n❌ Backend API not available")
                return
            print("\n✅ Backend API connected")
        except Exception as e:
            print(f"\n❌ Cannot connect to backend: {e}")
            return
        
        # Schedule each video
        success_count = 0
        for i, video in enumerate(VIDEOS):
            scheduled_time = base_time + timedelta(minutes=i * 2)  # 2 min apart
            if await schedule_video(client, video, scheduled_time):
                success_count += 1
        
        print("\n" + "=" * 60)
        print(f"📊 RESULTS: {success_count}/{len(VIDEOS)} videos scheduled")
        print("=" * 60)
        
        if success_count > 0:
            print(f"\n🌐 View scheduled posts at: http://localhost:5557/schedule")
            print(f"   You can click 'Publish' on each post to test immediately")
            print(f"   Or wait for the scheduled time to auto-publish")


if __name__ == "__main__":
    asyncio.run(main())
