#!/usr/bin/env python3
"""
Direct backend test: Trigger analysis and show database results
Tests the full flow: API -> VideoAnalyzer -> Database -> Query results
"""
import asyncio
import requests
import time
import json

API_BASE = "http://localhost:5555/api"

async def test_analysis_flow():
    """Test video analysis and show database results"""
    
    # Step 1: Generate and Upload a Test Video
    print("🎥 Step 1: Generating and uploading test video...")
    
    # Generate synthetic video with audio using ffmpeg
    import subprocess
    test_file = "test_video_analysis.mp4"
    
    # Generate 15s video with sine wave audio (min duration is 10s)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=15:size=640x480:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=15",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        test_file
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Generated {test_file}")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg generation failed: {e.stderr.decode()}")
        return

    # Upload video
    with open(test_file, 'rb') as f:
        files = {'file': (test_file, f, 'video/mp4')}
        response = requests.post(f"{API_BASE}/videos/upload", files=files)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code}")
        print(response.text)
        return
        
    upload_data = response.json()
    video_id = upload_data['video_id']
    print(f"✅ Uploaded video: {upload_data['file_name']}")
    print(f"   ID: {video_id}")
    
    test_video = {
        'id': video_id,
        'file_name': upload_data['file_name'],
        'duration_sec': upload_data.get('duration', 5.0),
        'source_uri': f"uploaded/{test_file}" # Placeholder
    }
    
    print(f"✅ Selected: {test_video['file_name']}")
    print(f"   ID: {test_video['id']}")
    print(f"   Duration: {test_video.get('duration_sec', 'Unknown')}s")
    print(f"   Path: {test_video['source_uri']}")
    print()
    
    # Step 2: Trigger analysis
    print("🚀 Step 2: Triggering analysis...")
    response = requests.post(f"{API_BASE}/videos/{test_video['id']}/analyze")
    
    if response.status_code != 200:
        print(f"❌ Failed to start analysis: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    print(f"✅ {result['message']}")
    print(f"   Status: {result['status']}")
    print()
    
    # Step 3: Wait and monitor (analysis runs in background)
    print("⏳ Step 3: Waiting for analysis to complete...")
    print("   (This may take 30-60 seconds for transcription + GPT-4)")
    print()
    
    max_wait = 120  # 2 minutes max
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        time.sleep(5)
        elapsed = int(time.time() - start_time)
        print(f"   ⏱️  {elapsed}s elapsed...")
        
        # Check if analysis is complete by looking for video_analysis record
        # We'll use a simple check - see if we can get video with analysis
        try:
            # Import to check database directly
            sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')
            from database.connection import init_db, async_session_maker
            from database.models import VideoAnalysis
            from sqlalchemy import select
            
            if not hasattr(test_analysis_flow, '_db_initialized'):
                await init_db()
                test_analysis_flow._db_initialized = True
            
            from database.connection import async_session_maker as session_maker
            
            async with session_maker() as session:
                result = await session.execute(
                    select(VideoAnalysis).where(
                        VideoAnalysis.video_id == test_video['id']
                    )
                )
                analysis = result.scalar_one_or_none()
                
                if analysis:
                    # Analysis complete!
                    print(f"\n✅ Analysis complete after {elapsed}s!")
                    print()
                    print("=" * 70)
                    print("📊 ANALYSIS RESULTS FROM DATABASE")
                    print("=" * 70)
                    print()
                    print(f"🎬 Video: {test_video['file_name']}")
                    print(f"🆔 Video ID: {test_video['id']}")
                    print()
                    print("📝 TRANSCRIPT:")
                    print("-" * 70)
                    print(f"{analysis.transcript[:500]}...")
                    print(f"(Total length: {len(analysis.transcript)} characters)")
                    print()
                    print("🎯 TOPICS:")
                    for topic in (analysis.topics or []):
                        print(f"   • {topic}")
                    print()
                    print("🪝 HOOKS:")
                    for hook in (analysis.hooks or []):
                        print(f"   • {hook}")
                    print()
                    print("🎭 TONE:")
                    print(f"   {analysis.tone}")
                    print()
                    print("⚡ PACING:")
                    print(f"   {analysis.pacing}")
                    print()
                    print("🔑 KEY MOMENTS:")
                    if analysis.key_moments:
                        for timestamp, moment in analysis.key_moments.items():
                            print(f"   {timestamp}: {moment}")
                    print()
                    print(f"🚀 VIRAL SCORE: {analysis.pre_social_score}/10")
                    print()
                    print(f"📅 Analyzed: {analysis.created_at}")
                    print(f"🔢 Version: {analysis.analysis_version}")
                    print()
                    print("=" * 70)
                    print()
                    print("💡 This data is now stored in the database and can be")
                    print("   accessed via the API or displayed in the frontend!")
                    
                    return
                    
        except Exception as e:
            print(f"   ⚠️  Database check error: {e}")
            # Continue waiting
    
    print()
    print(f"⏱️  Timeout after {max_wait}s - analysis may still be running")
    print("   Check backend logs for progress")


if __name__ == "__main__":
    import sys
    asyncio.run(test_analysis_flow())
