#!/usr/bin/env python3
"""
Analyze 10 videos with 100% analysis
Delete placeholder videos with zero data
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db, init_db
from database.models import Video, VideoAnalysis
import httpx
from loguru import logger

BASE_URL = "http://localhost:5555"


async def get_videos_with_data(db: AsyncSession):
    """Get videos that have actual data (duration_sec > 0, file exists)"""
    query = select(Video).where(
        Video.duration_sec.isnot(None),
        Video.duration_sec > 0
    ).order_by(Video.created_at.desc()).limit(20)
    
    result = await db.execute(query)
    videos = result.scalars().all()
    
    # Filter to only videos with valid file paths
    valid_videos = []
    for video in videos:
        file_path = video.source_uri
        if file_path and Path(file_path).exists():
            valid_videos.append(video)
    
    return valid_videos


async def delete_placeholder_videos(db: AsyncSession):
    """Delete videos that are placeholders with zero data"""
    logger.info("🗑️  Checking for placeholder videos to delete...")
    
    # Delete videos with no duration_sec or zero duration_sec
    delete_query = delete(Video).where(
        (Video.duration_sec.is_(None)) | (Video.duration_sec == 0)
    )
    
    result = await db.execute(delete_query)
    await db.commit()
    
    deleted_count = result.rowcount
    if deleted_count > 0:
        logger.info(f"✅ Deleted {deleted_count} placeholder videos")
    else:
        logger.info("✅ No placeholder videos found")
    return deleted_count


async def analyze_video(video_id: str, force: bool = True, current: int = 0, total: int = 0):
    """Trigger full analysis for a video"""
    progress = f"[{current}/{total}]" if total > 0 else ""
    logger.info(f"  {progress} 🔬 Starting analysis for {video_id}...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            start_time = time.time()
            response = await client.post(
                f"{BASE_URL}/api/media-db/analyze/{video_id}",
                params={"force": force}
            )
            elapsed = time.time() - start_time
            response.raise_for_status()
            result = response.json()
            status = result.get('status', 'started')
            logger.info(f"    ✅ Analysis started: {status} ({elapsed:.1f}s)")
            logger.info(f"    ⏳ Estimated time: 5-10 minutes per video")
            return result
        except Exception as e:
            logger.error(f"    ❌ Failed: {str(e)[:100]}")
            return None


async def wait_for_analysis_complete(video_id: str, max_wait: int = 600):
    """Wait for analysis to complete"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(max_wait // 5):
            try:
                # Check if analysis exists and is complete
                response = await client.get(
                    f"{BASE_URL}/api/analysis/results/{video_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("transcript") or data.get("topics"):
                        logger.info(f"✅ Analysis complete for {video_id}")
                        return True
            except:
                pass
            
            await asyncio.sleep(5)
            if i % 10 == 0:
                logger.info(f"⏳ Waiting for analysis {video_id}... ({i*5}s)")
        
        return False


async def main():
    """Main function"""
    start_time = time.time()
    
    logger.info("="*80)
    logger.info("🚀 Video Analysis and Cleanup")
    logger.info("="*80)
    logger.info(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Initialize database
    logger.info("🔌 Connecting to database...")
    await init_db()
    logger.info("✅ Database connected")
    logger.info("")
    
    # Get database session
    async for db in get_db():
        # Step 1: Delete placeholder videos
        logger.info("="*80)
        logger.info("🗑️  STEP 1: Delete Placeholder Videos")
        logger.info("="*80)
        deleted = await delete_placeholder_videos(db)
        logger.info("")
        
        # Step 2: Get 10 videos with actual data
        logger.info("="*80)
        logger.info("📹 STEP 2: Find Videos to Analyze")
        logger.info("="*80)
        logger.info("🔍 Searching for videos with actual data...")
        videos = await get_videos_with_data(db)
        
        if len(videos) < 10:
            logger.warning(f"⚠️  Only found {len(videos)} videos with data. Need 10.")
            logger.info("📂 Expanding search to all videos...")
            # Get all videos regardless
            query = select(Video).order_by(Video.created_at.desc()).limit(20)
            result = await db.execute(query)
            videos = result.scalars().all()
            logger.info(f"✅ Found {len(videos)} total videos")
        
        videos_to_analyze = videos[:10]
        logger.info("")
        logger.info(f"📋 Selected {len(videos_to_analyze)} videos to analyze:")
        for idx, video in enumerate(videos_to_analyze, 1):
            duration = f"{video.duration_sec:.1f}s" if video.duration_sec else "unknown"
            logger.info(f"  {idx}. {video.file_name} (ID: {video.id}, Duration: {duration})")
        logger.info("")
        
        # Step 3: Analyze each video
        logger.info("="*80)
        logger.info("🔬 STEP 3: Start Video Analysis")
        logger.info("="*80)
        logger.info("⚠️  Note: Each analysis takes 5-10 minutes")
        logger.info("")
        
        analysis_tasks = []
        start_analysis_time = time.time()
        
        for idx, video in enumerate(videos_to_analyze, 1):
            task = analyze_video(str(video.id), force=True, current=idx, total=len(videos_to_analyze))
            analysis_tasks.append((str(video.id), video.file_name, task))
            await asyncio.sleep(2)  # Rate limiting
        
        # Start all analyses
        logger.info("")
        logger.info("🚀 Starting all analyses in parallel...")
        results = await asyncio.gather(*[task for _, _, task in analysis_tasks], return_exceptions=True)
        
        analysis_start_elapsed = time.time() - start_analysis_time
        successful = sum(1 for r in results if r is not None and not isinstance(r, Exception))
        logger.info("")
        logger.info(f"✅ Started {successful}/{len(analysis_tasks)} analyses in {analysis_start_elapsed:.1f}s")
        logger.info(f"⏱️  Estimated total time: {len(analysis_tasks) * 7:.0f} minutes")
        logger.info("")
        
        # Step 4: Wait for analyses to complete (with timeout)
        logger.info("="*80)
        logger.info("⏳ STEP 4: Wait for Analyses to Complete")
        logger.info("="*80)
        logger.info("📊 Monitoring analysis progress...")
        logger.info("")
        
        completed = 0
        for idx, (video_id, file_name, _) in enumerate(analysis_tasks, 1):
            logger.info(f"[{idx}/{len(analysis_tasks)}] Waiting for {file_name}...")
            if await wait_for_analysis_complete(video_id, max_wait=300):
                completed += 1
                logger.info(f"  ✅ {file_name} complete ({completed}/{len(analysis_tasks)})")
            else:
                logger.warning(f"  ⏱️  {file_name} timeout (still running in background)")
            logger.info("")
        
        total_elapsed = time.time() - start_time
        logger.info("="*80)
        logger.info("📊 FINAL STATUS")
        logger.info("="*80)
        logger.info(f"✅ Completed: {completed}/{len(analysis_tasks)} analyses")
        logger.info(f"⏱️  Total time: {total_elapsed/60:.1f} minutes ({total_elapsed:.0f} seconds)")
        
        if completed == len(analysis_tasks):
            logger.info("🎉 All analyses complete!")
        else:
            logger.info(f"💡 {len(analysis_tasks) - completed} analyses still running in background")
        
        break


if __name__ == "__main__":
    asyncio.run(main())

