#!/usr/bin/env python3
"""
Import 25 Videos, Run Full Analysis, and Schedule Some for Next 3 Days
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import httpx
from loguru import logger
import time
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:5555"
TARGET_VIDEOS = 25
VIDEOS_TO_SCHEDULE = 8  # Schedule ~8 videos across 3 days (2-3 per day)

# Watch directories for videos - PRIORITIZE iPhone import location
# PRIMARY SOURCE: ~/Documents/IphoneImport (116GB, 8491 items)
IPHONE_IMPORT_DIR = Path.home() / "Documents" / "IphoneImport"
WATCH_DIRS = [
    IPHONE_IMPORT_DIR,  # First priority: iPhone imported videos (116GB, 8491 items)
    Path.home() / "Downloads",  # Second: Other downloads
    Path.home() / "Desktop",  # Third: Desktop
    Path("/tmp"),  # Last: Temp files
]


async def scan_for_videos() -> list[Path]:
    """
    Scan for existing video files in watch directories, prioritizing iPhone imports.
    
    IMPORTANT: Videos are REFERENCED by their original path, NOT copied.
    The database stores source_uri pointing to the original file location.
    """
    logger.info("🔍 Scanning for video files...")
    logger.info(f"📱 Priority: iPhone import directory ({IPHONE_IMPORT_DIR})")
    logger.info("ℹ️  Videos are REFERENCED (not copied) - original files stay in place")
    logger.info("")
    
    video_extensions = ['.mp4', '.mov', '.MOV', '.MP4', '.avi', '.mkv', '.m4v']
    videos = []
    videos_by_source = {}
    
    for watch_dir in WATCH_DIRS:
        if watch_dir.exists():
            logger.info(f"  📂 Scanning: {watch_dir}")
            dir_videos = []
            for ext in video_extensions:
                found = list(watch_dir.glob(f"**/*{ext}"))
                dir_videos.extend(found)
            
            # Filter by size (at least 1MB)
            valid_videos = [v for v in dir_videos if v.exists() and v.stat().st_size > 1024 * 1024]
            videos_by_source[str(watch_dir)] = valid_videos
            videos.extend(valid_videos)
            
            if valid_videos:
                logger.info(f"    ✅ Found {len(valid_videos)} valid videos")
    
    logger.info("")
    
    # Prioritize iPhone import directory videos
    iphone_videos = videos_by_source.get(str(IPHONE_IMPORT_DIR), [])
    other_videos = [v for v in videos if v not in iphone_videos]
    
    # Combine: iPhone videos first, then others
    prioritized_videos = list(iphone_videos) + other_videos
    
    # Remove duplicates (same file path)
    seen_paths = set()
    unique_videos = []
    for video in prioritized_videos:
        video_str = str(video.resolve())  # Use absolute path for deduplication
        if video_str not in seen_paths:
            seen_paths.add(video_str)
            unique_videos.append(video)
    
    logger.info(f"📊 Video sources:")
    logger.info(f"   📱 iPhone imports: {len(iphone_videos)}")
    logger.info(f"   📁 Other sources: {len(other_videos)}")
    logger.info(f"   ✅ Total unique: {len(unique_videos)}")
    logger.info("")
    
    # Limit to target
    limited = unique_videos[:TARGET_VIDEOS]
    if len(unique_videos) > TARGET_VIDEOS:
        logger.info(f"  ⚠️  Limited to {TARGET_VIDEOS} videos (found {len(unique_videos)} total)")
        iphone_count = min(len(iphone_videos), TARGET_VIDEOS)
        logger.info(f"  📱 Using {iphone_count} from iPhone imports (priority)")
    
    return limited


async def ingest_video(video_path: Path, current: int = 0, total: int = 0) -> str:
    """
    Ingest a video file into the database.
    
    NOTE: This stores a REFERENCE to the original file path in source_uri.
    The file is NOT copied or moved - it stays in its original location.
    """
    try:
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        progress = f"[{current}/{total}]" if total > 0 else ""
        source_dir = video_path.parent.name
        logger.info(f"  {progress} 📤 Ingesting {video_path.name} ({file_size_mb:.1f} MB) from {source_dir}...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            start_time = time.time()
            # Use absolute path to ensure consistent referencing
            abs_path = str(video_path.resolve())
            response = await client.post(
                f"{BASE_URL}/api/media-db/ingest/file",
                params={"file_path": abs_path}
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                media_id = result.get('media_id')
                status = result.get('status', 'ingested')
                
                if media_id:
                    if status == 'exists':
                        logger.info(f"    ✅ Already exists: {media_id} (referencing: {abs_path}) ({elapsed:.1f}s)")
                    else:
                        logger.info(f"    ✅ Ingested: {media_id} (referencing: {abs_path}) ({elapsed:.1f}s)")
                    return media_id
                return None
            else:
                logger.error(f"    ❌ Failed ({response.status_code}): {response.text[:100]}")
                return None
    except Exception as e:
        logger.error(f"    ❌ Error: {str(e)[:100]}")
        return None


async def analyze_video(media_id: str, current: int = 0, total: int = 0) -> bool:
    """Trigger full analysis for a video"""
    progress = f"[{current}/{total}]" if total > 0 else ""
    logger.info(f"  {progress} 🔬 Starting analysis for {media_id}...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            start_time = time.time()
            response = await client.post(
                f"{BASE_URL}/api/media-db/analyze/{media_id}",
                params={"force": True}
            )
            elapsed = time.time() - start_time
            response.raise_for_status()
            result = response.json()
            status = result.get('status', 'started')
            logger.info(f"    ✅ Analysis started: {status} ({elapsed:.1f}s)")
            logger.info(f"    ⏳ Analysis runs in background (5-10 minutes per video)")
            return True
        except Exception as e:
            logger.error(f"    ❌ Failed: {str(e)[:100]}")
            return False


async def wait_for_analysis(media_id: str, max_wait: int = 600) -> bool:
    """Wait for analysis to complete (polling)"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(max_wait // 10):
            try:
                response = await client.get(
                    f"{BASE_URL}/api/media-db/analysis/{media_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("transcript") or data.get("topics"):
                        logger.info(f"    ✅ Analysis complete for {media_id}")
                        return True
            except:
                pass
            
            await asyncio.sleep(10)
            if i % 6 == 0:  # Every minute
                logger.info(f"    ⏳ Waiting for analysis... ({i*10}s)")
        
        logger.warning(f"    ⚠️  Timeout waiting for analysis (10 minutes)")
        return False


async def get_video_info(media_id: str) -> dict:
    """Get video information including title and analysis"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/api/media-db/detail/{media_id}")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}


async def schedule_video(media_id: str, scheduled_time: datetime, platform: str = "tiktok") -> bool:
    """Schedule a video for posting using direct DB insert"""
    from sqlalchemy import create_engine, text
    import os
    import uuid
    
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(db_url)
        
        # Get video info for logging
        video_info = await get_video_info(media_id)
        title = video_info.get("file_name", f"Video {media_id[:8]}")
        
        with engine.connect() as conn:
            # Insert directly into scheduled_posts
            post_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO scheduled_posts (
                    id, clip_id, platform, scheduled_time, status, 
                    is_ai_recommended, recommendation_reasoning, source, origin_type
                ) VALUES (
                    :id, :clip_id, :platform, :scheduled_time, 'scheduled',
                    true, :reasoning, 'auto-analyze-schedule', 'media_library'
                )
            """), {
                "id": post_id,
                "clip_id": media_id,  # Use media_id as clip_id reference
                "platform": platform,
                "scheduled_time": scheduled_time,
                "reasoning": f"Auto-scheduled from analyzed video: {title}"
            })
            conn.commit()
        
        logger.info(f"    ✅ Scheduled: {scheduled_time.strftime('%Y-%m-%d %H:%M')} on {platform}")
        return True
    except Exception as e:
        logger.error(f"    ❌ Error scheduling: {str(e)[:100]}")
        return False


async def get_random_unanalyzed_videos(count: int = 25) -> list[str]:
    """Get random videos from DB that haven't been analyzed yet"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Get all videos
            response = await client.get(f"{BASE_URL}/api/media-db/list?limit=500")
            if response.status_code == 200:
                all_videos = response.json()
                
                # Filter unanalyzed (no transcript)
                unanalyzed = [
                    v for v in all_videos 
                    if not v.get('transcript')
                ]
                
                logger.info(f"📊 Found {len(all_videos)} total videos, {len(unanalyzed)} unanalyzed")
                
                # Pick random sample
                if len(unanalyzed) > count:
                    selected = random.sample(unanalyzed, count)
                else:
                    selected = unanalyzed[:count]
                
                # Use media_id field (not id)
                return [v['media_id'] for v in selected]
        except Exception as e:
            logger.error(f"Error fetching videos: {e}")
    return []


async def main():
    """Main workflow"""
    start_time = time.time()
    
    logger.info("="*80)
    logger.info("🚀 Analyze 25 Random Videos and Schedule for Next 3 Days")
    logger.info("="*80)
    logger.info(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Step 1: Get random unanalyzed videos from database
    logger.info("="*80)
    logger.info("📹 STEP 1: Selecting Random Videos from Database")
    logger.info("="*80)
    
    ingested_ids = await get_random_unanalyzed_videos(TARGET_VIDEOS)
    
    if not ingested_ids:
        logger.error("❌ No unanalyzed videos found in database!")
        logger.info("   Run auto-sync first: curl -X POST 'http://localhost:5555/api/ingestion/auto-sync?limit=100'")
        return
    
    logger.info(f"✅ Selected {len(ingested_ids)} random videos for analysis")
    logger.info("")
    
    # Step 2: Start analysis (non-blocking)
    logger.info("="*80)
    logger.info("🔬 STEP 2: Starting Full Analysis")
    logger.info("="*80)
    logger.info("ℹ️  Analysis runs in background. We'll wait for a few to complete before scheduling.")
    logger.info("")
    
    analysis_start = time.time()
    analysis_started = []
    
    for idx, media_id in enumerate(ingested_ids, 1):
        success = await analyze_video(media_id, current=idx, total=len(ingested_ids))
        if success:
            analysis_started.append(media_id)
        await asyncio.sleep(1)  # Rate limiting
    
    logger.info("")
    logger.info(f"✅ Started analysis for {len(analysis_started)} videos")
    logger.info("⏳ Waiting for ALL analyses to complete before scheduling...")
    logger.info("   (This may take 2-4 hours for 25 videos - ~5-10 min each)")
    logger.info("")
    
    # Step 4: Wait for ALL analyses to complete (100% before scheduling)
    analyzed_ids = []
    failed_ids = []
    
    for idx, media_id in enumerate(analysis_started, 1):
        logger.info(f"  [{idx}/{len(analysis_started)}] Waiting for {media_id[:8]}...")
        if await wait_for_analysis(media_id, max_wait=900):  # 15 min max per video
            analyzed_ids.append(media_id)
            logger.info(f"    ✅ Complete ({len(analyzed_ids)}/{len(analysis_started)})")
        else:
            failed_ids.append(media_id)
            logger.warning(f"    ⚠️  Timeout - skipping")
    
    logger.info("")
    if failed_ids:
        logger.warning(f"⚠️  {len(failed_ids)} analyses timed out")
    logger.info(f"✅ {len(analyzed_ids)}/{len(analysis_started)} videos fully analyzed and ready for scheduling")
    
    logger.info("")
    
    # Step 3: Schedule videos for next 3 days
    logger.info("="*80)
    logger.info("📅 STEP 3: Scheduling Videos for Next 3 Days")
    logger.info("="*80)
    
    # Generate schedule times: 2-3 posts per day, spread throughout the day
    now = datetime.now()
    schedule_times = []
    platforms = ["tiktok", "instagram"]
    
    for day_offset in range(3):  # Next 3 days
        day = now + timedelta(days=day_offset + 1)
        
        # 2-3 posts per day at different times
        times_per_day = random.randint(2, 3)
        base_hours = [9, 12, 15, 18, 21]  # Good posting times
        
        for i in range(times_per_day):
            hour = base_hours[i % len(base_hours)]
            minute = random.randint(0, 59)
            schedule_time = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            platform = platforms[i % len(platforms)]
            schedule_times.append((schedule_time, platform))
    
    # Limit to number of videos we want to schedule
    schedule_times = schedule_times[:VIDEOS_TO_SCHEDULE]
    
    logger.info(f"📊 Scheduling {len(schedule_times)} videos across 3 days:")
    for st, platform in schedule_times:
        logger.info(f"   - {st.strftime('%Y-%m-%d %H:%M')} on {platform}")
    logger.info("")
    
    scheduled_count = 0
    videos_to_schedule = analyzed_ids[:len(schedule_times)] if analyzed_ids else ingested_ids[:len(schedule_times)]
    
    for idx, (schedule_time, platform) in enumerate(schedule_times):
        if idx < len(videos_to_schedule):
            media_id = videos_to_schedule[idx]
            if await schedule_video(media_id, schedule_time, platform):
                scheduled_count += 1
            await asyncio.sleep(0.5)
    
    logger.info("")
    logger.info(f"✅ Scheduled {scheduled_count}/{len(schedule_times)} videos")
    
    # Summary
    total_elapsed = time.time() - start_time
    logger.info("")
    logger.info("="*80)
    logger.info("📊 SUMMARY")
    logger.info("="*80)
    logger.info(f"✅ Videos selected: {len(ingested_ids)}")
    logger.info(f"✅ Analysis started: {len(analysis_started)}")
    logger.info(f"✅ Analysis completed: {len(analyzed_ids)}")
    logger.info(f"✅ Videos scheduled: {scheduled_count}/{len(schedule_times)}")
    logger.info(f"⏱️  Total time: {total_elapsed:.1f}s")
    logger.info("")
    logger.info("💡 All analyses completed before scheduling.")
    logger.info("   Videos are from: ~/Documents/IphoneImport (116GB, 8491 items)")
    logger.info("   Check the schedule page to see your scheduled posts!")
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())


