#!/usr/bin/env python3
"""
Local Testing Script
Real integration tests without mocks
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.video_ingestion import VideoValidator, VideoFileWatcher
from database.connection import init_db, close_db, async_session_maker
from database.models import OriginalVideo


async def test_database_connection():
    """Test real database connection"""
    logger.info("Testing database connection...")
    
    try:
        await init_db()
        
        if async_session_maker:
            async with async_session_maker() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1
                logger.success("✓ Database connection successful")
                return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        logger.info("Make sure PostgreSQL/Supabase is configured in .env")
        return False
    finally:
        await close_db()
    
    return False


async def test_video_validator():
    """Test video validation with real video"""
    logger.info("\nTesting video validator...")
    
    # Ask user for a video file
    video_path_str = input("Enter path to a video file (or press Enter to skip): ").strip()
    
    if not video_path_str:
        logger.warning("Skipping video validator test")
        return False
    
    video_path = Path(video_path_str).expanduser()
    
    if not video_path.exists():
        logger.error(f"File not found: {video_path}")
        return False
    
    validator = VideoValidator()
    is_valid, error, metadata = validator.validate(video_path)
    
    if is_valid:
        logger.success(f"✓ Video is valid!")
        logger.info(f"  File: {metadata['file_name']}")
        logger.info(f"  Duration: {metadata['duration']:.1f}s")
        logger.info(f"  Resolution: {metadata['width']}x{metadata['height']}")
        logger.info(f"  FPS: {metadata['fps']:.2f}")
        logger.info(f"  Size: {metadata['file_size_bytes'] / (1024*1024):.2f}MB")
        logger.info(f"  Codec: {metadata['video_codec']}")
        
        # Test thumbnail generation
        thumbnail_path = video_path.parent / f"{video_path.stem}_thumb.jpg"
        if validator.get_video_thumbnail(video_path, thumbnail_path):
            logger.success(f"✓ Thumbnail created: {thumbnail_path}")
        
        return True
    else:
        logger.error(f"✗ Video validation failed: {error}")
        return False


async def test_database_operations():
    """Test real database CRUD operations"""
    logger.info("\nTesting database operations...")
    
    try:
        await init_db()
        
        if not async_session_maker:
            logger.error("Database not initialized")
            return False
        
        async with async_session_maker() as session:
            # Create a test video record
            test_video = OriginalVideo(
                file_path="/tmp/test_video.mp4",
                file_name="test_video.mp4",
                file_size_bytes=1024000,
                duration_seconds=30.5,
                source="test",
                processing_status="pending",
                analysis_data={"test": True}
            )
            
            session.add(test_video)
            await session.commit()
            await session.refresh(test_video)
            
            logger.success(f"✓ Created test video record: {test_video.video_id}")
            
            # Read it back
            from sqlalchemy import select
            result = await session.execute(
                select(OriginalVideo).filter(OriginalVideo.video_id == test_video.video_id)
            )
            retrieved = result.scalar_one()
            
            assert retrieved.file_name == "test_video.mp4"
            logger.success("✓ Read test video record")
            
            # Update it
            retrieved.processing_status = "completed"
            await session.commit()
            logger.success("✓ Updated test video record")
            
            # Delete it
            await session.delete(retrieved)
            await session.commit()
            logger.success("✓ Deleted test video record")
            
            return True
            
    except Exception as e:
        logger.error(f"✗ Database operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await close_db()


def test_file_watcher():
    """Test file watcher with real directory"""
    logger.info("\nTesting file watcher...")
    
    watch_dir_str = input("Enter directory to watch (or press Enter for ~/Desktop): ").strip()
    
    if not watch_dir_str:
        watch_dir = Path.home() / "Desktop"
    else:
        watch_dir = Path(watch_dir_str).expanduser()
    
    if not watch_dir.exists():
        logger.error(f"Directory not found: {watch_dir}")
        return False
    
    logger.info(f"Watching: {watch_dir}")
    logger.info("Copy a video file to this directory to test detection")
    logger.info("Press Ctrl+C to stop...\n")
    
    detected_files = []
    
    def on_video(path: Path):
        logger.success(f"✓ Detected: {path.name}")
        detected_files.append(path)
        
        # Validate the detected video
        validator = VideoValidator()
        is_valid, error, metadata = validator.validate(path)
        
        if is_valid:
            logger.info(f"  Duration: {metadata['duration']:.1f}s")
            logger.info(f"  Size: {metadata['file_size_bytes'] / (1024*1024):.2f}MB")
        else:
            logger.warning(f"  Invalid: {error}")
    
    watcher = VideoFileWatcher([str(watch_dir)])
    
    try:
        watcher.start(on_video)
        
        # Keep running until Ctrl+C
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nStopping watcher...")
        watcher.stop()
        logger.success(f"✓ File watcher stopped. Detected {len(detected_files)} file(s)")
        return True


async def test_api_server():
    """Test running the FastAPI server"""
    logger.info("\nTesting API server...")
    logger.info("Starting FastAPI server on http://localhost:8000")
    logger.info("Visit http://localhost:8000/docs for API documentation")
    logger.info("Press Ctrl+C to stop...")
    
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("\nServer stopped")


async def run_all_tests():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("MediaPoster - Local Integration Tests")
    logger.info("=" * 60)
    
    results = {}
    
    # Test 1: Database connection
    results['database'] = await test_database_connection()
    
    # Test 2: Video validator
    results['validator'] = await test_video_validator()
    
    # Test 3: Database operations
    if results['database']:
        results['db_operations'] = await test_database_operations()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Results:")
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {test_name}: {status}")
    logger.info("=" * 60)


async def main():
    """Main menu"""
    print("\n" + "=" * 60)
    print("   MediaPoster - Local Testing")
    print("=" * 60)
    print("\nChoose a test:")
    print("  1. Test database connection")
    print("  2. Test video validator")
    print("  3. Test database operations (CRUD)")
    print("  4. Test file watcher (real-time)")
    print("  5. Start API server")
    print("  6. Run all tests")
    print("  0. Exit")
    print()
    
    choice = input("Enter choice (0-6): ").strip()
    print()
    
    if choice == '0':
        logger.info("Goodbye!")
        return
    elif choice == '1':
        await test_database_connection()
    elif choice == '2':
        await test_video_validator()
    elif choice == '3':
        await test_database_operations()
    elif choice == '4':
        test_file_watcher()
    elif choice == '5':
        await test_api_server()
    elif choice == '6':
        await run_all_tests()
    else:
        logger.error("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
