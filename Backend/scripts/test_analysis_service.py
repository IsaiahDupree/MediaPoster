"""
Test Analysis Service
=====================
Tests the analysis service to ensure it's actually analyzing videos
and not marking them as analyzed prematurely.
"""
import asyncio
import httpx
import json
from datetime import datetime
from pathlib import Path


API_URL = "http://localhost:5555"


async def test_analysis_service():
    """Test the analysis service end-to-end"""
    print("\n" + "="*80)
    print("🧪 TESTING ANALYSIS SERVICE")
    print("="*80 + "\n")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Get a video that needs analysis
        print("📋 Step 1: Finding unanalyzed video...")
        list_res = await client.get(f"{API_URL}/api/media-db/list?limit=10")
        if not list_res.ok:
            print(f"❌ Failed to list videos: {list_res.status_code}")
            return
        
        videos = list_res.json().get("media", [])
        if not videos:
            print("❌ No videos found")
            return
        
        # Find a video without analysis
        unanalyzed = None
        for video in videos:
            if video.get("status") != "analyzed":
                unanalyzed = video
                break
        
        if not unanalyzed:
            print("⚠️  All videos appear analyzed. Testing with first video anyway...")
            unanalyzed = videos[0]
        
        video_id = unanalyzed.get("media_id") or unanalyzed.get("id")
        filename = unanalyzed.get("filename", "unknown")
        
        print(f"✅ Found video: {video_id}")
        print(f"   Filename: {filename}")
        print(f"   Current Status: {unanalyzed.get('status', 'unknown')}")
        print(f"   Has Analysis: {bool(unanalyzed.get('analysis'))}")
        
        # Step 2: Check current analysis status
        print(f"\n📊 Step 2: Checking current analysis status...")
        analysis_res = await client.get(f"{API_URL}/api/media-db/analysis/{video_id}")
        if analysis_res.ok:
            analysis_data = analysis_res.json()
            print(f"   Transcript: {'✅' if analysis_data.get('transcript') else '❌'}")
            print(f"   Topics: {'✅' if analysis_data.get('topics') else '❌'}")
            print(f"   Hooks: {'✅' if analysis_data.get('hooks') else '❌'}")
            print(f"   Pre-Social Score: {analysis_data.get('pre_social_score', 'N/A')}")
            print(f"   Visual Analysis: {'✅' if analysis_data.get('visual_analysis') else '❌'}")
            print(f"   Deep Analysis: {'✅' if analysis_data.get('deep_analysis') else '❌'}")
        else:
            print(f"   No analysis found (status: {analysis_res.status_code})")
        
        # Step 3: Start analysis
        print(f"\n🚀 Step 3: Starting analysis...")
        start_time = datetime.now()
        
        analyze_res = await client.post(f"{API_URL}/api/media-db/analyze/{video_id}?force=true")
        if not analyze_res.ok:
            print(f"❌ Failed to start analysis: {analyze_res.status_code}")
            print(f"   Response: {analyze_res.text}")
            return
        
        analyze_data = analyze_res.json()
        print(f"✅ Analysis started: {analyze_data.get('status', 'unknown')}")
        
        # Step 4: Poll for completion (with timeout)
        print(f"\n⏳ Step 4: Waiting for analysis to complete...")
        max_wait = 300  # 5 minutes
        poll_interval = 2  # 2 seconds
        elapsed = 0
        
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
            # Check analysis status
            status_res = await client.get(f"{API_URL}/api/media-db/analysis/{video_id}")
            if status_res.ok:
                current_analysis = status_res.json()
                has_transcript = bool(current_analysis.get('transcript'))
                has_topics = bool(current_analysis.get('topics'))
                has_score = current_analysis.get('pre_social_score') is not None
                
                if has_transcript and has_topics and has_score:
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    print(f"\n✅ Analysis completed in {duration:.1f} seconds!")
                    print(f"   Transcript: ✅ ({len(current_analysis.get('transcript', ''))} chars)")
                    print(f"   Topics: ✅ ({len(current_analysis.get('topics', []))} topics)")
                    print(f"   Score: ✅ ({current_analysis.get('pre_social_score')})")
                    break
                else:
                    print(f"   [{elapsed}s] Still analyzing... transcript={has_transcript}, topics={has_topics}, score={has_score}")
            else:
                print(f"   [{elapsed}s] Waiting... (status check failed: {status_res.status_code})")
        
        if elapsed >= max_wait:
            print(f"\n⏱️  Timeout after {max_wait} seconds")
            print("   Analysis may still be running or may have failed")
        
        # Step 5: Verify final analysis
        print(f"\n🔍 Step 5: Verifying final analysis...")
        final_res = await client.get(f"{API_URL}/api/media-db/analysis/{video_id}")
        if final_res.ok:
            final_analysis = final_res.json()
            print(f"   Transcript: {'✅' if final_analysis.get('transcript') else '❌'} ({len(final_analysis.get('transcript', ''))} chars)")
            print(f"   Topics: {'✅' if final_analysis.get('topics') else '❌'} ({len(final_analysis.get('topics', []))} items)")
            print(f"   Hooks: {'✅' if final_analysis.get('hooks') else '❌'} ({len(final_analysis.get('hooks', []))} items)")
            print(f"   Pre-Social Score: {final_analysis.get('pre_social_score', 'N/A')}")
            print(f"   Visual Analysis: {'✅' if final_analysis.get('visual_analysis') else '❌'}")
            print(f"   Deep Analysis: {'✅' if final_analysis.get('deep_analysis') else '❌'}")
            
            # Check if analysis is actually complete
            is_complete = (
                final_analysis.get('transcript') and
                len(final_analysis.get('transcript', '')) > 10 and
                final_analysis.get('topics') and
                len(final_analysis.get('topics', [])) > 0 and
                final_analysis.get('pre_social_score') is not None
            )
            
            if is_complete:
                print(f"\n✅ ANALYSIS VERIFIED: Video has complete analysis")
            else:
                print(f"\n❌ ANALYSIS INCOMPLETE: Missing required fields")
                print(f"   This indicates analysis may have failed or completed prematurely")
        else:
            print(f"❌ Failed to get final analysis: {final_res.status_code}")
        
        # Step 6: Check video status in list
        print(f"\n📋 Step 6: Checking video status in list...")
        list_res2 = await client.get(f"{API_URL}/api/media-db/list?limit=100")
        if list_res2.ok:
            videos2 = list_res2.json().get("media", [])
            video_in_list = next((v for v in videos2 if (v.get("media_id") or v.get("id")) == video_id), None)
            if video_in_list:
                print(f"   Status: {video_in_list.get('status', 'unknown')}")
                print(f"   Has Analysis: {bool(video_in_list.get('analysis'))}")
                
                if video_in_list.get('status') == 'analyzed' and not is_complete:
                    print(f"\n⚠️  WARNING: Video marked as 'analyzed' but analysis is incomplete!")
                    print(f"   This is a FALSE POSITIVE - the status doesn't match the actual analysis")
            else:
                print(f"   Video not found in list")
        
        print("\n" + "="*80)
        print("🧪 TEST COMPLETE")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_analysis_service())

