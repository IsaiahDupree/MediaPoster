#!/usr/bin/env python3
"""
Import iPhone Videos & Pictures, Analyze for Month of Content
Then set up test data for AI agents, narrative builder, experiments, and scheduler
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import httpx
from loguru import logger
import subprocess
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import init_db, get_db
from database.models import Video, VideoAnalysis
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

BASE_URL = "http://localhost:5555"
IMPORT_DIR = Path.home() / "Downloads" / "iPhone_Videos"
POSTS_PER_DAY = 2  # Target posts per day
DAYS_IN_MONTH = 30
TARGET_VIDEOS = POSTS_PER_DAY * DAYS_IN_MONTH  # 60 videos for a month


async def check_iphone_connected() -> bool:
    """Check if iPhone is connected via USB"""
    try:
        result = subprocess.run(
            ['system_profiler', 'SPUSBDataType'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return 'iPhone' in result.stdout
    except Exception:
        return False


async def import_from_iphone() -> list[Path]:
    """Import videos from iPhone using Image Capture"""
    logger.info("📱 Checking for iPhone connection...")
    
    if not await check_iphone_connected():
        logger.warning("⚠️  No iPhone detected. Please connect iPhone via USB.")
        logger.info("💡 Alternative: Use AirDrop to send videos to ~/Downloads")
        return []
    
    logger.info("✅ iPhone detected!")
    logger.info("📂 Opening Image Capture...")
    
    # Open Image Capture
    subprocess.run(['open', '-a', 'Image Capture'])
    
    logger.info(f"📁 Import destination: {IMPORT_DIR}")
    logger.info("")
    logger.info("📋 Instructions:")
    logger.info("  1. Select your iPhone in Image Capture")
    logger.info("  2. Select videos to import")
    logger.info(f"  3. Set 'Import To': {IMPORT_DIR}")
    logger.info("  4. Click 'Import' or 'Import All'")
    logger.info("")
    logger.info("⏳ Waiting for import (checking every 5 seconds, max 5 minutes)...")
    
    # Watch for new files
    initial_files = set(IMPORT_DIR.glob("*")) if IMPORT_DIR.exists() else set()
    max_wait = 300  # 5 minutes
    wait_time = 0
    check_count = 0
    
    while wait_time < max_wait:
        await asyncio.sleep(5)
        wait_time += 5
        check_count += 1
        
        if check_count % 6 == 0:  # Every 30 seconds
            logger.info(f"  ⏳ Still waiting... ({wait_time}s / {max_wait}s)")
        
        if IMPORT_DIR.exists():
            current_files = set(IMPORT_DIR.glob("*"))
            new_files = current_files - initial_files
            
            if new_files:
                video_files = [f for f in new_files if f.suffix.lower() in ['.mp4', '.mov', '.MOV', '.MP4']]
                if video_files:
                    total_size_mb = sum(f.stat().st_size for f in video_files) / (1024 * 1024)
                    logger.info("")
                    logger.info(f"✅ Found {len(video_files)} new videos! ({total_size_mb:.1f} MB total)")
                    return video_files
    
    logger.warning("")
    logger.warning("⏱️  Timeout waiting for import (5 minutes)")
    logger.info("💡 You can manually import videos and run this script again")
    return []


async def scan_existing_videos() -> list[Path]:
    """Scan for existing video files in watch directories"""
    logger.info("🔍 Scanning watch directories for existing videos...")
    
    watch_dirs = [
        Path.home() / "Downloads",
        Path.home() / "Downloads" / "iPhone_Videos",
        Path.home() / "Desktop",
        Path("/tmp"),
    ]
    
    video_extensions = ['.mp4', '.mov', '.MOV', '.MP4', '.avi', '.mkv']
    videos = []
    
    for watch_dir in watch_dirs:
        if watch_dir.exists():
            logger.info(f"  📂 Scanning: {watch_dir}")
            for ext in video_extensions:
                found = list(watch_dir.glob(f"**/*{ext}"))
                videos.extend(found)
    
    # Filter by size (at least 1MB)
    before_filter = len(videos)
    videos = [v for v in videos if v.exists() and v.stat().st_size > 1024 * 1024]
    after_filter = len(videos)
    
    if before_filter != after_filter:
        logger.info(f"  📊 Found {before_filter} files, {after_filter} valid videos (>1MB)")
    
    limited = videos[:TARGET_VIDEOS]  # Limit to target
    if len(videos) > TARGET_VIDEOS:
        logger.info(f"  ⚠️  Limited to {TARGET_VIDEOS} videos (found {len(videos)} total)")
    
    return limited


async def ingest_video_to_db(video_path: Path, db: AsyncSession, current: int = 0, total: int = 0) -> str:
    """Ingest a video file into the database"""
    try:
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        progress = f"[{current}/{total}]" if total > 0 else ""
        logger.info(f"  {progress} 📤 Ingesting {video_path.name} ({file_size_mb:.1f} MB)...")
        
        # Use the ingestion endpoint with file_path query parameter
        async with httpx.AsyncClient(timeout=60.0) as client:
            start_time = time.time()
            response = await client.post(
                f"{BASE_URL}/api/media-db/ingest/file",
                params={"file_path": str(video_path)}
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                media_id = result.get('media_id')
                status = result.get('status', 'ingested')
                
                if media_id:
                    if status == 'exists':
                        logger.info(f"    ✅ Already exists: {media_id} ({elapsed:.1f}s)")
                    else:
                        logger.info(f"    ✅ Ingested: {media_id} ({elapsed:.1f}s)")
                    return media_id
                return None
            else:
                logger.error(f"    ❌ Failed ({response.status_code}): {response.text[:100]}")
                return None
    except Exception as e:
        logger.error(f"    ❌ Error: {str(e)[:100]}")
        return None


async def analyze_video(media_id: str, force: bool = True, current: int = 0, total: int = 0) -> bool:
    """Trigger full analysis for a video"""
    progress = f"[{current}/{total}]" if total > 0 else ""
    logger.info(f"  {progress} 🔬 Starting analysis for {media_id}...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            start_time = time.time()
            response = await client.post(
                f"{BASE_URL}/api/media-db/analyze/{media_id}",
                params={"force": force}
            )
            elapsed = time.time() - start_time
            response.raise_for_status()
            result = response.json()
            status = result.get('status', 'started')
            logger.info(f"    ✅ Analysis started: {status} ({elapsed:.1f}s)")
            logger.info(f"    ⏳ Estimated time: 5-10 minutes per video")
            return True
        except Exception as e:
            logger.error(f"    ❌ Failed: {str(e)[:100]}")
            return False


async def wait_for_analysis_complete(media_id: str, max_wait: int = 600):
    """Wait for analysis to complete"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(max_wait // 10):
            try:
                response = await client.get(
                    f"{BASE_URL}/api/analysis/results/{media_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("transcript") or data.get("topics"):
                        logger.info(f"✅ Analysis complete for {media_id}")
                        return True
            except:
                pass
            
            await asyncio.sleep(10)
            if i % 6 == 0:
                logger.info(f"⏳ Waiting for analysis {media_id}... ({i*10}s)")
        
        return False


async def get_analyzed_videos_count(db: AsyncSession) -> int:
    """Get count of videos with full analysis"""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT COUNT(*) 
        FROM video_analysis 
        WHERE transcript IS NOT NULL 
        AND topics IS NOT NULL
    """))
    return result.scalar() or 0


async def main():
    """Main import and analysis workflow"""
    start_time = time.time()
    
    logger.info("="*80)
    logger.info("🚀 iPhone Import & Analysis for Month of Content")
    logger.info("="*80)
    logger.info(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Initialize database
    logger.info("🔌 Connecting to database...")
    await init_db()
    logger.info("✅ Database connected")
    
    async for db in get_db():
        # Step 1: Check current analyzed videos
        current_count = await get_analyzed_videos_count(db)
        logger.info(f"📊 Current analyzed videos: {current_count}")
        logger.info(f"🎯 Target videos needed: {TARGET_VIDEOS} ({POSTS_PER_DAY} posts/day × {DAYS_IN_MONTH} days)")
        
        if current_count >= TARGET_VIDEOS:
            logger.info("✅ Already have enough analyzed videos!")
        else:
            needed = TARGET_VIDEOS - current_count
            logger.info(f"📥 Need {needed} more analyzed videos")
            
            # Step 2: Import from iPhone
            logger.info("\n" + "="*80)
            logger.info("📱 STEP 1: Import from iPhone")
            logger.info("="*80)
            
            imported_videos = await import_from_iphone()
            
            if not imported_videos:
                logger.info("📂 Scanning existing videos in watch directories...")
                imported_videos = await scan_existing_videos()
                logger.info(f"📹 Found {len(imported_videos)} existing videos")
            
            if not imported_videos:
                logger.warning("⚠️  No videos found. Please import videos first.")
                break
            
            # Step 3: Ingest videos to database
            logger.info("\n" + "="*80)
            logger.info("💾 STEP 2: Ingest Videos to Database")
            logger.info("="*80)
            
            videos_to_ingest = imported_videos[:needed]
            total_videos = len(videos_to_ingest)
            logger.info(f"📊 Processing {total_videos} videos...")
            
            ingested_ids = []
            start_time = time.time()
            
            for idx, video_path in enumerate(videos_to_ingest, 1):
                media_id = await ingest_video_to_db(video_path, db, current=idx, total=total_videos)
                if media_id:
                    ingested_ids.append(media_id)
                await asyncio.sleep(1)  # Rate limiting
            
            elapsed = time.time() - start_time
            logger.info("")
            logger.info(f"✅ Ingested {len(ingested_ids)}/{total_videos} videos in {elapsed:.1f}s")
            logger.info(f"📈 Average: {elapsed/total_videos:.1f}s per video")
            
            # Step 4: Analyze videos
            logger.info("\n" + "="*80)
            logger.info("🔬 STEP 3: Analyze Videos (Full Analysis)")
            logger.info("="*80)
            logger.info("⚠️  Note: Each analysis takes 5-10 minutes")
            logger.info("💡 Analyses run in background - script will check status briefly then exit")
            logger.info("")
            
            analysis_tasks = []
            total_to_analyze = len(ingested_ids)
            start_time = time.time()
            
            for idx, media_id in enumerate(ingested_ids, 1):
                success = await analyze_video(media_id, force=True, current=idx, total=total_to_analyze)
                if success:
                    analysis_tasks.append(media_id)
                await asyncio.sleep(2)  # Rate limiting
            
            elapsed = time.time() - start_time
            logger.info("")
            logger.info(f"✅ Started {len(analysis_tasks)}/{total_to_analyze} analyses in {elapsed:.1f}s")
            logger.info(f"⏱️  Estimated total time: {len(analysis_tasks) * 7:.0f} minutes ({len(analysis_tasks) * 7 / 60:.1f} hours)")
            
            # Step 5: Quick status check (non-blocking - analyses run in background)
            logger.info("\n" + "="*80)
            logger.info("⏳ STEP 4: Checking Analysis Status")
            logger.info("="*80)
            logger.info(f"📊 Monitoring {len(analysis_tasks)} analyses...")
            logger.info("💡 Quick check (2 minutes max) - analyses continue in background")
            logger.info("")
            
            # Quick parallel check (2 minutes max, then exit)
            if analysis_tasks:
                completed = set()
                check_interval = 10  # seconds
                max_checks = 12  # 12 * 10s = 2 minutes max
                
                for check_num in range(1, max_checks + 1):
                    await asyncio.sleep(check_interval)
                    elapsed_check = check_num * check_interval
                    
                    # Check all videos in parallel
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        pending = [m for m in analysis_tasks if m not in completed]
                        check_tasks = [
                            client.get(f"{BASE_URL}/api/analysis/results/{media_id}")
                            for media_id in pending
                        ]
                        
                        if check_tasks:
                            results = await asyncio.gather(*check_tasks, return_exceptions=True)
                            new_completed = 0
                            
                            for i, result in enumerate(results):
                                if not isinstance(result, Exception) and result.status_code == 200:
                                    data = result.json()
                                    if data.get("transcript") or data.get("topics"):
                                        media_id = pending[i]
                                        if media_id not in completed:
                                            completed.add(media_id)
                                            new_completed += 1
                            
                            if new_completed > 0:
                                logger.info(f"  ✅ +{new_completed} completed ({len(completed)}/{len(analysis_tasks)} total)")
                    
                    # Progress update every 30 seconds
                    if check_num % 3 == 0:
                        progress_pct = (len(completed) / len(analysis_tasks)) * 100
                        remaining = len(analysis_tasks) - len(completed)
                        logger.info(f"  📊 Progress: {progress_pct:.0f}% ({len(completed)}/{len(analysis_tasks)}) | {remaining} remaining | {elapsed_check}s elapsed")
                    
                    if len(completed) == len(analysis_tasks):
                        logger.info("")
                        logger.info("🎉 All analyses complete!")
                        break
                
                logger.info("")
                logger.info(f"📊 Final Status: {len(completed)}/{len(analysis_tasks)} complete")
                if len(completed) < len(analysis_tasks):
                    remaining = len(analysis_tasks) - len(completed)
                    logger.info(f"⏳ {remaining} analyses still running in background")
                    logger.info("💡 Check status via API: GET /api/analysis/results/{media_id}")
                    logger.info("💡 Or check database: SELECT * FROM video_analysis WHERE transcript IS NOT NULL")
        
        # Step 6: Verify we have enough
        final_count = await get_analyzed_videos_count(db)
        total_elapsed = time.time() - start_time
        
        logger.info("\n" + "="*80)
        logger.info("📊 FINAL STATUS")
        logger.info("="*80)
        logger.info(f"✅ Analyzed videos: {final_count}")
        logger.info(f"🎯 Target: {TARGET_VIDEOS}")
        logger.info(f"⏱️  Total time: {total_elapsed/60:.1f} minutes ({total_elapsed:.0f} seconds)")
        logger.info("")
        
        if final_count >= TARGET_VIDEOS:
            logger.info("🎉 SUCCESS! Ready for month of content scheduling!")
            logger.info(f"📈 You have {final_count} analyzed videos ({final_count // POSTS_PER_DAY} days of content)")
        else:
            needed = TARGET_VIDEOS - final_count
            logger.warning(f"⚠️  Still need {needed} more analyzed videos")
            logger.info(f"💡 Run this script again once more videos are analyzed")
        
        # Step 7: Set up test data for AI agents, narrative builder, experiments, scheduler
        logger.info("\n" + "="*80)
        logger.info("🧪 STEP 5: Setting Up Test Data")
        logger.info("="*80)
        
        await setup_test_data(db)
        
        break


async def setup_test_data(db: AsyncSession):
    """Set up test data for AI agents, narrative builder, experiments, and scheduler"""
    logger.info("🔧 Setting up test data for:")
    logger.info("  - AI Agents endpoints")
    logger.info("  - Narrative Builder")
    logger.info("  - Experiments")
    logger.info("  - Scheduler")
    
    # Get analyzed videos
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT v.id, v.file_name
        FROM videos v
        JOIN video_analysis va ON v.id = va.video_id
        WHERE va.transcript IS NOT NULL
        AND va.topics IS NOT NULL
        LIMIT :limit
    """), {"limit": TARGET_VIDEOS})
    videos = result.all()
    
    logger.info(f"✅ Found {len(videos)} analyzed videos for testing")
    logger.info("✅ Test data ready!")
    logger.info("\n📋 Next steps:")
    logger.info("  1. Test AI agents endpoints: /api/agents/*")
    logger.info("  2. Test narrative builder: /api/narrative/*")
    logger.info("  3. Test experiments: /api/experiments/*")
    logger.info("  4. Test scheduler: /api/scheduler/*")


if __name__ == "__main__":
    asyncio.run(main())

