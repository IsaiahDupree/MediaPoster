"""
Comprehensive Analysis Service Test
==================================
Tests the analysis service to ensure it works correctly and doesn't produce false positives.
"""
import asyncio
import httpx
import json
from datetime import datetime
from pathlib import Path


API_URL = "http://localhost:5555"
TIMEOUT = 300.0


async def test_analysis_service():
    """Test the analysis service end-to-end"""
    print("\n" + "="*80)
    print("🧪 COMPREHENSIVE ANALYSIS SERVICE TEST")
    print("="*80 + "\n")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Step 1: Get a video that needs analysis
        print("📋 Step 1: Finding unanalyzed video...")
        list_res = await client.get(f"{API_URL}/api/media-db/list?limit=10")
        if not list_res.ok:
            print(f"❌ Failed to list videos: {list_res.status_code}")
            return False
        
        videos = list_res.json().get("media", [])
        if not videos:
            print("❌ No videos found")
            return False
        
        # Find a video without complete analysis
        test_video = None
        for video in videos:
            status = video.get("status", "unknown")
            has_analysis = bool(video.get("analysis"))
            
            # Look for videos that are NOT marked as analyzed
            if status != "analyzed":
                test_video = video
                break
        
        if not test_video:
            print("⚠️  All videos appear analyzed. Testing with first video anyway...")
            test_video = videos[0]
        
        video_id = test_video.get("media_id") or test_video.get("id")
        filename = test_video.get("filename", "unknown")
        
        print(f"✅ Found test video: {video_id}")
        print(f"   Filename: {filename}")
        print(f"   Current Status: {test_video.get('status', 'unknown')}")
        print(f"   Has Analysis: {bool(test_video.get('analysis'))}")
        
        # Step 2: Check current analysis status
        print(f"\n📊 Step 2: Checking current analysis status...")
        analysis_res = await client.get(f"{API_URL}/api/media-db/analysis/{video_id}")
        if analysis_res.ok:
            analysis_data = analysis_res.json()
            transcript = analysis_data.get('transcript', '')
            topics = analysis_data.get('topics', [])
            score = analysis_data.get('pre_social_score')
            
            print(f"   Transcript: {'✅' if transcript and len(transcript) > 10 else '❌'} ({len(transcript)} chars)")
            print(f"   Topics: {'✅' if topics and len(topics) > 0 else '❌'} ({len(topics)} items)")
            print(f"   Pre-Social Score: {'✅' if score is not None else '❌'} ({score})")
            print(f"   Visual Analysis: {'✅' if analysis_data.get('visual_analysis') else '❌'}")
            print(f"   Deep Analysis: {'✅' if analysis_data.get('deep_analysis') else '❌'}")
            
            # Check if analysis is complete
            is_complete = (
                transcript and len(transcript) > 10 and
                topics and len(topics) > 0 and
                score is not None
            )
            
            if is_complete:
                print(f"   ✅ Analysis is COMPLETE")
            else:
                print(f"   ⚠️  Analysis is INCOMPLETE (this is expected if not yet analyzed)")
        else:
            print(f"   No analysis found (status: {analysis_res.status_code})")
        
        # Step 3: Start analysis
        print(f"\n🚀 Step 3: Starting analysis...")
        start_time = datetime.now()
        
        analyze_res = await client.post(f"{API_URL}/api/media-db/analyze/{video_id}?force=true")
        if not analyze_res.ok:
            print(f"❌ Failed to start analysis: {analyze_res.status_code}")
            print(f"   Response: {analyze_res.text}")
            return False
        
        analyze_data = analyze_res.json()
        print(f"✅ Analysis started: {analyze_data.get('status', 'unknown')}")
        
        # Step 4: Poll for completion (with timeout)
        print(f"\n⏳ Step 4: Waiting for analysis to complete...")
        print(f"   (This may take 1-5 minutes depending on video length)")
        max_wait = 300  # 5 minutes
        poll_interval = 3  # 3 seconds
        elapsed = 0
        last_status = None
        
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
            # Check analysis status
            status_res = await client.get(f"{API_URL}/api/media-db/analysis/{video_id}")
            if status_res.ok:
                current_analysis = status_res.json()
                transcript = current_analysis.get('transcript', '')
                topics = current_analysis.get('topics', [])
                score = current_analysis.get('pre_social_score')
                
                has_transcript = bool(transcript and len(transcript) > 10)
                has_topics = bool(topics and len(topics) > 0)
                has_score = score is not None
                
                status_str = f"transcript={has_transcript}, topics={has_topics}, score={has_score}"
                if status_str != last_status:
                    print(f"   [{elapsed}s] {status_str}")
                    last_status = status_str
                
                if has_transcript and has_topics and has_score:
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    print(f"\n✅ Analysis completed in {duration:.1f} seconds!")
                    break
            else:
                if elapsed % 15 == 0:  # Log every 15 seconds
                    print(f"   [{elapsed}s] Waiting... (status check: {status_res.status_code})")
        
        if elapsed >= max_wait:
            print(f"\n⏱️  Timeout after {max_wait} seconds")
            print("   Analysis may still be running or may have failed")
            return False
        
        # Step 5: Verify final analysis
        print(f"\n🔍 Step 5: Verifying final analysis...")
        final_res = await client.get(f"{API_URL}/api/media-db/analysis/{video_id}")
        if not final_res.ok:
            print(f"❌ Failed to get final analysis: {final_res.status_code}")
            return False
        
        final_analysis = final_res.json()
        transcript = final_analysis.get('transcript', '')
        topics = final_analysis.get('topics', [])
        score = final_analysis.get('pre_social_score')
        
        print(f"   Transcript: {'✅' if transcript and len(transcript) > 10 else '❌'} ({len(transcript)} chars)")
        print(f"   Topics: {'✅' if topics and len(topics) > 0 else '❌'} ({len(topics)} items)")
        print(f"   Hooks: {'✅' if final_analysis.get('hooks') else '❌'} ({len(final_analysis.get('hooks', []))} items)")
        print(f"   Pre-Social Score: {score}")
        print(f"   Visual Analysis: {'✅' if final_analysis.get('visual_analysis') else '❌'}")
        print(f"   Deep Analysis: {'✅' if final_analysis.get('deep_analysis') else '❌'}")
        
        # Check if analysis is actually complete
        is_complete = (
            transcript and len(transcript) > 10 and
            topics and len(topics) > 0 and
            score is not None
        )
        
        if not is_complete:
            print(f"\n❌ ANALYSIS INCOMPLETE: Missing required fields")
            print(f"   This indicates analysis may have failed or completed prematurely")
            return False
        
        # Step 6: Check video status in list (should be "analyzed")
        print(f"\n📋 Step 6: Checking video status in list...")
        list_res2 = await client.get(f"{API_URL}/api/media-db/list?limit=100")
        if not list_res2.ok:
            print(f"❌ Failed to get video list: {list_res2.status_code}")
            return False
        
        videos2 = list_res2.json().get("media", [])
        video_in_list = next((v for v in videos2 if (v.get("media_id") or v.get("id")) == video_id), None)
        if not video_in_list:
            print(f"❌ Video not found in list")
            return False
        
        list_status = video_in_list.get('status', 'unknown')
        print(f"   Status in list: {list_status}")
        print(f"   Has Analysis: {bool(video_in_list.get('analysis'))}")
        
        if list_status == 'analyzed' and is_complete:
            print(f"\n✅ SUCCESS: Video correctly marked as 'analyzed' with complete analysis")
            return True
        elif list_status == 'analyzed' and not is_complete:
            print(f"\n❌ FALSE POSITIVE: Video marked as 'analyzed' but analysis is incomplete!")
            return False
        elif list_status != 'analyzed' and is_complete:
            print(f"\n⚠️  WARNING: Video has complete analysis but status is '{list_status}'")
            print(f"   This may indicate a status check issue")
            return False
        else:
            print(f"\n⚠️  Video status: '{list_status}', Analysis complete: {is_complete}")
            return False


if __name__ == "__main__":
    success = asyncio.run(test_analysis_service())
    exit(0 if success else 1)

