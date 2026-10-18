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
    """Ingest a video from iPhone import directory if needed"""
    logger.info("🔍 Checking for videos to ingest...")
    
    if not IPHONE_IMPORT_DIR.exists():
        logger.warning(f"iPhone import directory not found: {IPHONE_IMPORT_DIR}")
        return find_video_to_process()
    
    # Find a video file
    video_extensions = ['.mp4', '.mov', '.MOV', '.MP4', '.avi', '.mkv', '.m4v']
    video_files = []
    
    for file_path in IPHONE_IMPORT_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            try:
                if file_path.stat().st_size > 0:
                    video_files.append(file_path)
            except:
                continue
    
    if not video_files:
        logger.info("No video files found in iPhone import, using existing videos")
        return find_video_to_process()
    
    # Try to ingest the first video
    video_path = video_files[0]
    logger.info(f"📥 Ingesting video: {video_path.name}")
    
    response = requests.post(
        f"{BASE_URL}/api/media-db/ingest/file",
        params={"file_path": str(video_path)},
        timeout=60
    )
    
    if response.status_code == 200:
        data = response.json()
        media_id = data.get("media_id")
        if media_id:
            logger.success(f"✅ Ingested: {media_id}")
            return media_id, video_path.name
        
    # If ingestion failed or video already exists, find it
    logger.info("Video already ingested or ingestion failed, finding existing video...")
    return find_video_to_process()


def run_analysis(media_id: str) -> dict:
    """Run full AI analysis on the video"""
    logger.info(f"🔬 Starting analysis for {media_id}...")
    
    # Start analysis
    response = requests.post(
        f"{BASE_URL}/api/media-db/analyze/{media_id}",
        json={"force_reanalyze": False},
        timeout=300
    )
    
    if response.status_code != 200:
        raise Exception(f"Analysis failed: {response.status_code} - {response.text}")
    
    job_data = response.json()
    job_id = job_data.get("job_id")
    
    if not job_id:
        logger.info("Analysis already complete or in progress")
        # Check if analysis exists
        detail_response = requests.get(f"{BASE_URL}/api/media-db/detail/{media_id}", timeout=30)
        if detail_response.status_code == 200:
            detail = detail_response.json()
            if detail.get("pre_social_score") is not None:
                logger.success("✅ Analysis already exists")
                return detail
    
    logger.info(f"⏳ Analysis job started: {job_id}")
    logger.info("   Waiting for analysis to complete (this may take a few minutes)...")
    
    # Poll for completion
    max_wait = 600  # 10 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        time.sleep(5)
        
        # Check job status
        status_response = requests.get(f"{BASE_URL}/api/media-db/analysis/status/{job_id}", timeout=30)
        if status_response.status_code == 200:
            status = status_response.json()
            completed = status.get("completed", 0)
            total = status.get("total", 1)
            
            if completed >= total:
                logger.success("✅ Analysis complete!")
                break
            
            logger.info(f"   Progress: {completed}/{total} videos analyzed...")
        
        # Also check if analysis is done by checking detail
        detail_response = requests.get(f"{BASE_URL}/api/media-db/detail/{media_id}", timeout=30)
        if detail_response.status_code == 200:
            detail = detail_response.json()
            if detail.get("pre_social_score") is not None:
                logger.success("✅ Analysis complete!")
                return detail
    
    # Get final analysis
    detail_response = requests.get(f"{BASE_URL}/api/media-db/detail/{media_id}", timeout=30)
    if detail_response.status_code == 200:
        return detail_response.json()
    
    raise Exception("Analysis did not complete in time")


def generate_platform_content(media_id: str, analysis: dict) -> dict:
    """Generate platform-specific titles and descriptions using 100% analysis context"""
    logger.info("🤖 Generating AI-powered titles and descriptions...")
    logger.info("   Using 100% analysis context (transcript, topics, hooks, full analysis)")
    
    # Use the generate-captions endpoint which uses full analysis context
    response = requests.post(
        f"{BASE_URL}/api/analysis/generate-captions/{media_id}",
        json={
            "platform": "tiktok",
            "tone": "engaging",
            "style": "viral",
            "include_hashtags": True,
            "include_hook": True
        },
        timeout=60
    )
    
    if response.status_code != 200:
        raise Exception(f"Caption generation failed: {response.status_code} - {response.text}")
    
    captions = response.json()
    logger.success("✅ Generated captions:")
    logger.info(f"   Title: {captions.get('title', 'N/A')}")
    logger.info(f"   Description: {captions.get('description', 'N/A')[:100]}...")
    
    return captions


def save_platform_content(media_id: str, captions: dict):
    """Save the generated platform content to the database"""
    logger.info("💾 Saving platform_content to database...")
    
    platform_content = [
        {
            "platform": "tiktok",
            "account_id": int(TIKTOK_ACCOUNT_ID),
            "title": captions.get("title", ""),
            "description": captions.get("description", ""),
            "hashtags": captions.get("hashtags", []),
            "optimal_length": "15-60s"
        }
    ]
    
    response = requests.put(
        f"{BASE_URL}/api/media-db/analysis/{media_id}",
        json={"platform_content": platform_content},
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to save platform_content: {response.status_code} - {response.text}")
    
    logger.success("✅ platform_content saved successfully")
    
    # Verify it was saved
    detail_response = requests.get(f"{BASE_URL}/api/media-db/detail/{media_id}", timeout=30)
    if detail_response.status_code == 200:
        detail = detail_response.json()
        saved_pc = detail.get("platform_content")
        if saved_pc:
            logger.info(f"   Verified: {len(saved_pc)} platform entries saved")
        else:
            logger.warning("   ⚠️  platform_content not found after save (this was the bug!)")


def schedule_post(media_id: str, captions: dict):
    """Schedule the post for the next hour"""
    logger.info("📅 Scheduling post...")
    
    # Schedule for 1 hour from now
    scheduled_time = datetime.now() + timedelta(hours=1)
    
    response = requests.post(
        f"{BASE_URL}/api/schedule/create",
        json={
            "media_id": media_id,
            "platform": "tiktok",
            "scheduled_at": scheduled_time.isoformat(),
            "title": captions.get("title", ""),
            "description": captions.get("description", ""),
            "hashtags": captions.get("hashtags", [])
        },
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"Scheduling failed: {response.status_code} - {response.text}")
    
    schedule_data = response.json()
    schedule_id = schedule_data.get("schedule_id") or schedule_data.get("id")
    
    logger.success(f"✅ Post scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   Schedule ID: {schedule_id}")
    
    return schedule_id, scheduled_time


def publish_to_tiktok(media_id: str, captions: dict) -> dict:
    """Publish video to TikTok via Blotato"""
    logger.info("📤 Publishing to TikTok via Blotato...")
    
    title = captions.get("title", "")
    description = captions.get("description", "")
    hashtags = captions.get("hashtags", [])
    
    text = f"{title}\n\n{description}\n\n{' '.join(hashtags)}"
    
    response = requests.post(
        f"{BASE_URL}/api/blotato/posts/full-publish",
        json={
            "media_id": media_id,
            "blotato_account_id": TIKTOK_ACCOUNT_ID,
            "platform": "tiktok",
            "username": "",  # Will be looked up from account_id
            "text": text,
            "cleanup_gdrive": True
        },
        timeout=120
    )
    
    if response.status_code != 200:
        raise Exception(f"Publish failed: {response.status_code} - {response.text}")
    
    publish_data = response.json()
    
    if publish_data.get("success"):
        post_id = publish_data.get("blotato_post_id") or publish_data.get("post_submission_id")
        url = publish_data.get("url")
        
        logger.success("✅ Published to TikTok!")
        logger.info(f"   Post ID: {post_id}")
        if url:
            logger.info(f"   URL: {url}")
        else:
            logger.info("   URL: Will be available after processing (check status endpoint)")
        
        return publish_data
    else:
        error = publish_data.get("error", "Unknown error")
        raise Exception(f"Publish failed: {error}")


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
    """Run the full workflow"""
    logger.info("="*70)
    logger.info("FULL WORKFLOW: Ingest → Analyze → Generate → Schedule → Publish")
    logger.info("="*70)
    logger.info("")
    
    try:
        # Step 1: Ingest video
        logger.info("STEP 1: Ingest Video")
        logger.info("-" * 70)
        media_id, filename = ingest_video_if_needed()
        logger.info(f"   Media ID: {media_id}")
        logger.info(f"   Filename: {filename}")
        logger.info("")
        
        # Step 2: Run analysis
        logger.info("STEP 2: Run Full AI Analysis")
        logger.info("-" * 70)
        analysis = run_analysis(media_id)
        logger.info(f"   Score: {analysis.get('pre_social_score', 'N/A')}")
        logger.info(f"   Topics: {', '.join(analysis.get('topics', [])[:3])}")
        logger.info("")
        
        # Step 3: Generate platform content
        logger.info("STEP 3: Generate AI Titles/Descriptions (100% Analysis Context)")
        logger.info("-" * 70)
        captions = generate_platform_content(media_id, analysis)
        logger.info("")
        
        # Step 4: Save platform content
        logger.info("STEP 4: Save platform_content to Database")
        logger.info("-" * 70)
        save_platform_content(media_id, captions)
        logger.info("")
        
        # Step 5: Schedule post
        logger.info("STEP 5: Schedule Post")
        logger.info("-" * 70)
        schedule_id, scheduled_time = schedule_post(media_id, captions)
        logger.info("")
        
        # Step 6: Publish to TikTok
        logger.info("STEP 6: Publish to TikTok")
        logger.info("-" * 70)
        publish_result = publish_to_tiktok(media_id, captions)
        logger.info("")
        
        # Step 7: Check schedule
        logger.info("STEP 7: Verify Schedule Entry")
        logger.info("-" * 70)
        check_schedule(media_id)
        logger.info("")
        
        # Summary
        logger.info("="*70)
        logger.success("✅ FULL WORKFLOW COMPLETE!")
        logger.info("="*70)
        logger.info(f"Media ID: {media_id}")
        logger.info(f"TikTok Post ID: {publish_result.get('blotato_post_id') or publish_result.get('post_submission_id')}")
        if publish_result.get("url"):
            logger.info(f"TikTok URL: {publish_result['url']}")
        logger.info(f"Scheduled for: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        logger.info("Check the schedule page to see your post!")
        
    except Exception as e:
        logger.error(f"❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

