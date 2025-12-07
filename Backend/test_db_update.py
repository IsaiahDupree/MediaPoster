"""
Test database update directly without background task
"""
import asyncio
import sys
sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')

async def test_db_update():
    from database.connection import init_db, async_session_maker
    from database.models import Video
    from sqlalchemy import select, update
    from datetime import datetime
    import uuid
    
    # Initialize database
    await init_db()
    
    # Test video ID
    video_id = uuid.UUID("a989e0f2-0d97-48af-85a3-8e6ad06c041b")
    
    print(f"Testing database update for video {video_id}")
    
    # Get current value
    async with async_session_maker() as session:
        result = await session.execute(
            select(Video).where(Video.id == video_id)
        )
        video = result.scalar_one_or_none()
        
        if not video:
            print("❌ Video not found!")
            return
            
        print(f"Current thumbnail_path: {video.thumbnail_path}")
        
    # Try to update
    test_path = "/tmp/mediaposter_thumbnails/test.jpg"
    
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                update(Video)
                .where(Video.id == video_id)
                .values(
                    thumbnail_path=test_path,
                    thumbnail_generated_at=datetime.utcnow()
                )
            )
            await session.commit()
            print(f"✅ Update executed! Rows affected: {result.rowcount}")
    except Exception as e:
        print(f"❌ Update failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Verify
    async with async_session_maker() as session:
        result = await session.execute(
            select(Video).where(Video.id == video_id)
        )
        video = result.scalar_one_or_none()
        print(f"New thumbnail_path: {video.thumbnail_path}")

if __name__ == "__main__":
    asyncio.run(test_db_update())
