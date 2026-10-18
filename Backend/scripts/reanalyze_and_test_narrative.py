#!/usr/bin/env python3
"""
Re-analyze videos that have analysis but missing platform_content,
then run the narrative builder E2E test.
"""
import asyncio
import httpx
import sys
from pathlib import Path
from typing import List, Optional
from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

API_URL = "http://localhost:5555"

async def get_videos_needing_reanalysis() -> List[dict]:
    """Get videos that have analysis but missing platform_content"""
    from database.connection import init_db
    from sqlalchemy import create_engine, text
    from config import settings
    
    # Initialize database if needed
    await init_db()
    
    # Create synchronous engine for this script
    db_url = settings.database_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif db_url.startswith("postgresql://") and "+" in db_url:
        db_url = db_url.split("+")[0] + "://" + db_url.split("@")[-1] if "@" in db_url else db_url
    
    try:
        sync_engine = create_engine(db_url, pool_pre_ping=True)
        with sync_engine.connect() as conn:
            query = text("""
                SELECT v.id, v.file_name, v.title
                FROM videos v
                JOIN video_analysis va ON va.video_id = v.id
                WHERE va.transcript IS NOT NULL
                  AND va.platform_content IS NULL
                LIMIT 50
            """)
            result = conn.execute(query)
            rows = result.fetchall()
            
            videos = [
                {
                    "id": str(row[0]),
                    "file_name": row[1] or "Unknown",
                    "title": row[2] or "N/A"
                }
                for row in rows
            ]
            
            logger.info(f"Found {len(videos)} videos needing re-analysis")
            return videos
            
    except Exception as e:
        logger.error(f"Error fetching videos: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

async def reanalyze_video(media_id: str, current: int = 0, total: int = 0) -> bool:
    """Re-analyze a video with force=true"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            logger.info(f"[{current}/{total}] 🔄 Re-analyzing {media_id}...")
            
            # Trigger re-analysis with force=true
            response = await client.post(
                f"{API_URL}/api/media-db/analyze/{media_id}",
                params={"force": "true"}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[{current}/{total}] ✅ Analysis started: {result.get('status', 'unknown')}")
                return True
            else:
                logger.error(f"[{current}/{total}] ❌ Failed to start analysis: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"[{current}/{total}] ❌ Error re-analyzing {media_id}: {e}")
            return False

async def wait_for_analysis(media_id: str, max_wait: int = 600) -> bool:
    """Wait for analysis to complete"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                logger.warning(f"⏱️  Timeout waiting for analysis: {media_id}")
                return False
            
            try:
                response = await client.get(f"{API_URL}/api/media-db/analysis/{media_id}")
                if response.status_code == 200:
                    data = response.json()
                    platform_content = data.get("platform_content")
                    
                    if platform_content:
                        logger.info(f"✅ Analysis complete with platform_content: {media_id}")
                        return True
                    else:
                        logger.debug(f"⏳ Still analyzing... ({int(elapsed)}s)")
                        await asyncio.sleep(5)
                else:
                    logger.warning(f"⚠️  Analysis check failed: {response.status_code}")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error checking analysis status: {e}")
                await asyncio.sleep(5)

async def reanalyze_all_videos(videos: List[dict], wait_for_completion: bool = False) -> int:
    """Re-analyze all videos (optionally wait for completion)"""
    total = len(videos)
    successful = 0
    
    logger.info(f"🔄 Triggering re-analysis for {total} videos...")
    logger.info("   (Analysis runs in background - 5-10 min per video)")
    
    # Trigger all analyses in parallel
    tasks = []
    for i, video in enumerate(videos, 1):
        media_id = video["id"]
        file_name = video["file_name"]
        tasks.append(reanalyze_video(media_id, i, total))
    
    # Wait for all triggers to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successful = sum(1 for r in results if r is True)
    
    logger.info(f"✅ Triggered {successful}/{total} re-analyses")
    
    if wait_for_completion:
        logger.info("⏳ Waiting for analyses to complete (this may take a while)...")
        for i, video in enumerate(videos, 1):
            if results[i-1] is True:
                media_id = video["id"]
                file_name = video["file_name"]
                if await wait_for_analysis(media_id, max_wait=600):
                    logger.info(f"✅ Completed: {file_name}")
                else:
                    logger.warning(f"⚠️  Timeout: {file_name}")
    
    return successful

async def run_narrative_builder_test():
    """Run the narrative builder E2E test"""
    import subprocess
    
    logger.info("\n" + "="*60)
    logger.info("🧪 Running Narrative Builder E2E Test")
    logger.info("="*60 + "\n")
    
    test_file = Path(__file__).parent.parent / "tests" / "test_narrative_builder_e2e.py"
    
    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return False
    
    try:
        result = subprocess.run(
            [
                "python", "-m", "pytest",
                str(test_file),
                "-v", "-s",
                "--asyncio-mode=auto"
            ],
            cwd=Path(__file__).parent.parent,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("\n✅ Narrative Builder E2E test passed!")
            return True
        else:
            logger.error(f"\n❌ Narrative Builder E2E test failed (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        logger.error(f"Error running test: {e}")
        return False

async def main():
    """Main function"""
    logger.info("🚀 Starting Re-Analysis and Narrative Builder Test")
    logger.info("="*60)
    
    # Step 1: Get videos needing re-analysis
    logger.info("\n📋 Step 1: Finding videos needing re-analysis...")
    videos = await get_videos_needing_reanalysis()
    
    if not videos:
        logger.info("✅ No videos need re-analysis (all have platform_content)")
    else:
        logger.info(f"📊 Found {len(videos)} videos needing re-analysis:")
        for video in videos[:10]:  # Show first 10
            logger.info(f"   - {video['file_name']} ({video['id'][:8]}...)")
        if len(videos) > 10:
            logger.info(f"   ... and {len(videos) - 10} more")
        
        # Step 2: Re-analyze videos
        logger.info(f"\n🔄 Step 2: Re-analyzing {len(videos)} videos...")
        successful = await reanalyze_all_videos(videos)
        
        logger.info(f"\n📊 Re-analysis Summary:")
        logger.info(f"   Total: {len(videos)}")
        logger.info(f"   Successful: {successful}")
        logger.info(f"   Failed: {len(videos) - successful}")
    
    # Step 3: Run narrative builder test
    logger.info("\n🧪 Step 3: Running Narrative Builder E2E test...")
    test_passed = await run_narrative_builder_test()
    
    logger.info("\n" + "="*60)
    if test_passed:
        logger.info("✅ All tasks completed successfully!")
    else:
        logger.warning("⚠️  Some tasks may have failed - check logs above")
    logger.info("="*60)

if __name__ == "__main__":
    asyncio.run(main())

