#!/usr/bin/env python3
"""
Test video analysis system with a short video
"""
import asyncio
import sys
sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')

from services.video_analyzer import VideoAnalyzer
from database.connection import init_db, async_session_maker
from database.models import Video, VideoAnalysis
from sqlalchemy import select
import uuid


async def test_analysis():
    """Test video analysis on a real video"""
    
    # Initialize database
    await init_db()
    
    # Import after init_db
    from database.connection import async_session_maker as session_maker
    
    if session_maker is None:
        print("❌ Failed to initialize database session maker")
        return
    
    # Get a short video from database
    async with session_maker() as session:
        result = await session.execute(
            select(Video)
            .where(Video.duration_sec != None)
            .where(Video.duration_sec < 120)  # Under 2 minutes
            .limit(1)
        )
        video = result.scalar_one_or_none()
        
        if not video:
            print("❌ No suitable test video found")
            print("Need a video with duration_sec < 120")
            return
        
        print(f"🎬 Testing with: {video.file_name}")
        print(f"   Duration: {video.duration_sec}s")
        print(f"   Path: {video.source_uri}")
        print(f"   ID: {video.id}")
        print()
        
        # Initialize analyzer
        print("🔧 Initializing VideoAnalyzer...")
        try:
            analyzer = VideoAnalyzer()
        except ValueError as e:
            print(f"❌ {e}")
            print("Set OPENAI_API_KEY environment variable")
            return
        
        # Run analysis
        print("🚀 Starting analysis...")
        print("   1. Extracting audio")
        print("   2. Transcribing with Whisper")
        print("   3. Analyzing with GPT-4")
        print("   4. Saving to database")
        print()
        
        try:
            result = await analyzer.analyze_video(
                video_id=video.id,
                video_path=video.source_uri,
                db_session=session,
                metadata={
                    "file_name": video.file_name,
                    "duration": video.duration_sec
                }
            )
            
            print("✅ Analysis Complete!")
            print()
            print(f"📊 Results:")
            print(f"   Topics: {result['topics']}")
            print(f"   Hooks: {result['hooks']}")
            print(f"   Tone: {result['tone']}")
            print(f"   Pacing: {result['pacing']}")
            print(f"   Viral Score: {result['pre_social_score']}/10")
            print()
            print(f"📝 Transcript ({len(result['transcript'])} chars):")
            print(f"   {result['transcript'][:200]}...")
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_analysis())
