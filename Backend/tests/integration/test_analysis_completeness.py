"""
Integration tests for analysis completeness verification
Tests that analysis jobs produce complete results with transcript and score
"""
import requests
import time
import sys

API_BASE = "http://localhost:5555"


def test_analysis_completeness():
    """Test that forced analysis produces complete results"""
    
    # Get a video with incomplete analysis
    response = requests.get(f"{API_BASE}/api/media-db/list?limit=1")
    assert response.status_code == 200
    data = response.json()
    
    # Handle both list and dict response formats
    media_list = data if isinstance(data, list) else data.get("media", [])
    
    if not media_list:
        print("⚠️ No videos found to test")
        return
    
    video = media_list[0]
    video_id = video["media_id"]
    print(f"✅ Testing analysis for: {video['filename']} ({video_id})")
    
    # Force re-analysis
    print("🔄 Starting forced analysis...")
    response = requests.post(f"{API_BASE}/api/media-db/analyze/{video_id}?force=true")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "analyzing"
    
    # Wait for analysis to complete (max 60 seconds)
    print("⏳ Waiting for analysis to complete...")
    max_wait = 60
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # Check if analysis is complete by querying the video
        response = requests.get(f"{API_BASE}/api/media-db/{video_id}")
        if response.status_code == 200:
            video_data = response.json()
            
            has_transcript = video_data.get("transcript") is not None and len(video_data.get("transcript", "")) > 0
            has_score = video_data.get("pre_social_score") is not None
            
            if has_transcript and has_score:
                print(f"✅ Analysis complete!")
                print(f"   Transcript length: {len(video_data.get('transcript', ''))}")
                print(f"   Score: {video_data.get('pre_social_score')}")
                print(f"   Topics: {len(video_data.get('topics', []))}")
                print(f"   Time taken: {time.time() - start_time:.1f}s")
                
                # Verify completeness
                assert has_transcript, "Analysis missing transcript"
                assert has_score, "Analysis missing pre_social_score"
                assert video_data.get("pre_social_score") > 0, "Score should be > 0"
                
                return True
        
        time.sleep(2)
    
    print(f"❌ Analysis did not complete within {max_wait}s")
    return False


def test_scheduler_query_filters_incomplete():
    """Test that the scheduler query correctly identifies incomplete analyses"""
    import psycopg2
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=54322,
            database="postgres",
            user="postgres",
            password="postgres"
        )
        cursor = conn.cursor()
        
        # Count videos needing analysis (same query as scheduler)
        cursor.execute("""
            SELECT COUNT(*)
            FROM videos v
            LEFT JOIN video_analysis va ON v.id = va.video_id
            WHERE (LOWER(v.file_name) LIKE '%.mp4'
                   OR LOWER(v.file_name) LIKE '%.mov'
                   OR LOWER(v.file_name) LIKE '%.m4v'
                   OR LOWER(v.file_name) LIKE '%.avi'
                   OR LOWER(v.file_name) LIKE '%.mkv'
                   OR LOWER(v.file_name) LIKE '%.webm')
              AND (va.video_id IS NULL 
                   OR va.transcript IS NULL 
                   OR TRIM(va.transcript) = ''
                   OR va.pre_social_score IS NULL)
        """)
        
        incomplete_count = cursor.fetchone()[0]
        
        # Count total video files
        cursor.execute("""
            SELECT COUNT(*)
            FROM videos v
            WHERE (LOWER(v.file_name) LIKE '%.mp4'
                   OR LOWER(v.file_name) LIKE '%.mov'
                   OR LOWER(v.file_name) LIKE '%.m4v'
                   OR LOWER(v.file_name) LIKE '%.avi'
                   OR LOWER(v.file_name) LIKE '%.mkv'
                   OR LOWER(v.file_name) LIKE '%.webm')
        """)
        
        total_videos = cursor.fetchone()[0]
        
        # Count complete analyses
        cursor.execute("""
            SELECT COUNT(*)
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE (LOWER(v.file_name) LIKE '%.mp4'
                   OR LOWER(v.file_name) LIKE '%.mov')
              AND va.transcript IS NOT NULL
              AND TRIM(va.transcript) != ''
              AND va.pre_social_score IS NOT NULL
        """)
        
        complete_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print(f"✅ Scheduler query test:")
        print(f"   Total videos: {total_videos}")
        print(f"   Complete analyses: {complete_count}")
        print(f"   Incomplete/missing: {incomplete_count}")
        print(f"   Progress: {complete_count / total_videos * 100:.1f}%")
        
        assert incomplete_count + complete_count <= total_videos, "Count mismatch"
        
        return True
        
    except Exception as e:
        print(f"❌ Database query test failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Running Analysis Completeness Tests\n")
    
    try:
        # Test 1: Scheduler query
        print("=" * 60)
        print("Test 1: Scheduler Query Filters")
        print("=" * 60)
        if not test_scheduler_query_filters_incomplete():
            sys.exit(1)
        
        print("\n" + "=" * 60)
        print("Test 2: Analysis Completeness")
        print("=" * 60)
        if not test_analysis_completeness():
            sys.exit(1)
        
        print("\n✅ All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to {API_BASE}")
        print("   Make sure the backend is running")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
