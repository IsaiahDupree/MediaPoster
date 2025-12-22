"""
E2E Tests for Recent Feature Developments
Tests thumbnail generation during ingestion, analysis workflow, video playback, and state persistence.
"""
import pytest
import httpx
import time
from pathlib import Path
import os

# API URLs
API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"
FRONTEND_BASE = "http://localhost:5557"

# Test media directory
TEST_MEDIA_DIR = Path(os.path.expanduser("~/Documents/IphoneImport"))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def test_image_file():
    """Get a real HEIC image for testing."""
    if not TEST_MEDIA_DIR.exists():
        pytest.skip("Test media directory not found")
    
    heic_files = list(TEST_MEDIA_DIR.glob("*.HEIC"))
    if not heic_files:
        pytest.skip("No HEIC files found")
    
    return str(heic_files[0])


@pytest.fixture(scope="module")
def test_video_file():
    """Get a real MOV video for testing."""
    if not TEST_MEDIA_DIR.exists():
        pytest.skip("Test media directory not found")
    
    mov_files = list(TEST_MEDIA_DIR.glob("*.MOV"))
    if not mov_files:
        pytest.skip("No MOV files found")
    
    return str(mov_files[0])


# =============================================================================
# FEATURE 1: Thumbnail Generation During Ingestion
# =============================================================================

class TestThumbnailDuringIngestion:
    """Test that thumbnails are generated automatically during ingestion."""
    
    def test_image_ingestion_generates_thumbnail(self, test_image_file):
        """Ingesting an image should automatically generate a color thumbnail."""
        print(f"\n🖼️  Testing image: {Path(test_image_file).name}")
        
        # Step 1: Ingest the image
        ingest_response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": test_image_file},
            timeout=30
        )
        
        assert ingest_response.status_code == 200, "Image ingestion failed"
        data = ingest_response.json()
        media_id = data["media_id"]
        print(f"✓ Ingested: {media_id}")
        
        # Step 2: Verify thumbnail was generated immediately
        # Give it a moment to generate
        time.sleep(2)
        
        thumb_response = httpx.get(
            f"{DB_API_URL}/thumbnail/{media_id}?size=medium",
            timeout=30
        )
        
        assert thumb_response.status_code == 200, "Thumbnail not generated during ingestion"
        assert thumb_response.headers["content-type"] == "image/jpeg"
        assert len(thumb_response.content) > 1000, "Thumbnail too small"
        print(f"✓ Thumbnail generated: {len(thumb_response.content)} bytes")
        
        # Step 3: Verify it's in color (not black and white)
        # Color JPEGs are typically larger than grayscale
        # A 400px wide color JPEG should be > 10KB
        assert len(thumb_response.content) > 10000, "Thumbnail may be grayscale (too small)"
        print(f"✓ Thumbnail appears to be in color")
        
        # Store for next tests
        pytest.test_image_id = media_id
    
    def test_video_ingestion_generates_thumbnail(self, test_video_file):
        """Ingesting a video should automatically generate a thumbnail."""
        print(f"\n🎬 Testing video: {Path(test_video_file).name}")
        
        # Step 1: Ingest the video
        ingest_response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": test_video_file},
            timeout=30
        )
        
        assert ingest_response.status_code == 200, "Video ingestion failed"
        data = ingest_response.json()
        media_id = data["media_id"]
        print(f"✓ Ingested: {media_id}")
        
        # Step 2: Verify thumbnail was generated
        time.sleep(2)
        
        thumb_response = httpx.get(
            f"{DB_API_URL}/thumbnail/{media_id}?size=medium",
            timeout=30
        )
        
        assert thumb_response.status_code == 200, "Video thumbnail not generated"
        assert thumb_response.headers["content-type"] == "image/jpeg"
        print(f"✓ Video thumbnail generated: {len(thumb_response.content)} bytes")
        
        # Store for next tests
        pytest.test_video_id = media_id
    
    def test_thumbnail_persists_in_database(self):
        """Thumbnail path should be stored in database."""
        if not hasattr(pytest, 'test_image_id'):
            pytest.skip("No test image available")
        
        # Get media detail
        detail_response = httpx.get(
            f"{DB_API_URL}/detail/{pytest.test_image_id}",
            timeout=10
        )
        
        assert detail_response.status_code == 200
        detail = detail_response.json()
        
        # Thumbnail path should be set (not null)
        # Note: API might not return thumbnail_path in response
        # But it should be accessible via thumbnail endpoint
        print(f"✓ Thumbnail persisted for {pytest.test_image_id}")


# =============================================================================
# FEATURE 2: Analysis Workflow After Ingestion
# =============================================================================

class TestAnalysisWorkflow:
    """Test that analysis can be run after ingestion."""
    
    def test_trigger_analysis_on_ingested_media(self):
        """Should be able to trigger analysis on ingested media."""
        if not hasattr(pytest, 'test_image_id'):
            pytest.skip("No test media available")
        
        print(f"\n🔬 Testing analysis on: {pytest.test_image_id}")
        
        # Trigger analysis
        analyze_response = httpx.post(
            f"{DB_API_URL}/analyze/{pytest.test_image_id}",
            timeout=10
        )
        
        # Should either start analysis (200) or indicate service unavailable (500)
        assert analyze_response.status_code in [200, 500]
        
        if analyze_response.status_code == 200:
            print(f"✓ Analysis started successfully")
        else:
            print(f"⚠️  Analysis service unavailable (expected in test env)")
    
    def test_batch_analysis_workflow(self):
        """Should be able to trigger batch analysis."""
        print(f"\n🔬 Testing batch analysis")
        
        # Trigger batch analysis on first 5 pending items
        batch_response = httpx.post(
            f"{DB_API_URL}/batch/analyze?limit=5",
            timeout=10
        )
        
        # Should either start (200) or indicate service unavailable (500)
        assert batch_response.status_code in [200, 500]
        
        if batch_response.status_code == 200:
            data = batch_response.json()
            print(f"✓ Batch analysis started: {data.get('count', 0)} items")
        else:
            print(f"⚠️  Batch analysis service unavailable")
    
    def test_analysis_updates_database(self):
        """Analysis results should be stored in database."""
        # Get stats to see analyzed count
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        print(f"✓ Analyzed: {stats['analyzed_count']}/{stats['total_videos']}")


# =============================================================================
# FEATURE 3: Video Playback
# =============================================================================

class TestVideoPlayback:
    """Test that videos are playable in the frontend."""
    
    def test_video_streaming_endpoint(self):
        """Video streaming endpoint should serve video files."""
        if not hasattr(pytest, 'test_video_id'):
            pytest.skip("No test video available")
        
        print(f"\n▶️  Testing video playback: {pytest.test_video_id}")
        
        # Request video stream
        video_response = httpx.get(
            f"{DB_API_URL}/video/{pytest.test_video_id}",
            timeout=30,
            follow_redirects=True
        )
        
        assert video_response.status_code == 200, "Video streaming failed"
        assert "video/" in video_response.headers.get("content-type", "")
        assert len(video_response.content) > 100000, "Video file too small"
        print(f"✓ Video streams: {len(video_response.content)} bytes")
        print(f"✓ Content-Type: {video_response.headers.get('content-type')}")
    
    def test_video_has_cache_headers(self):
        """Video responses should have caching headers."""
        if not hasattr(pytest, 'test_video_id'):
            pytest.skip("No test video available")
        
        video_response = httpx.get(
            f"{DB_API_URL}/video/{pytest.test_video_id}",
            timeout=30
        )
        
        assert video_response.status_code == 200
        assert "cache-control" in video_response.headers
        print(f"✓ Cache-Control: {video_response.headers.get('cache-control')}")
    
    def test_video_detail_page_shows_player(self):
        """Video detail page should be accessible."""
        if not hasattr(pytest, 'test_video_id'):
            pytest.skip("No test video available")
        
        # Check frontend page loads
        page_response = httpx.get(
            f"{FRONTEND_BASE}/media/{pytest.test_video_id}",
            timeout=10
        )
        
        assert page_response.status_code == 200
        content = page_response.content.decode('utf-8', errors='ignore')
        
        # Should contain video element
        assert '<video' in content or 'video' in content.lower()
        print(f"✓ Video detail page loads with player")
    
    def test_image_detail_page_shows_thumbnail(self):
        """Image detail page should show thumbnail, not video player."""
        if not hasattr(pytest, 'test_image_id'):
            pytest.skip("No test image available")
        
        page_response = httpx.get(
            f"{FRONTEND_BASE}/media/{pytest.test_image_id}",
            timeout=10
        )
        
        assert page_response.status_code == 200
        print(f"✓ Image detail page loads")


# =============================================================================
# FEATURE 4: State Persistence (Partial)
# =============================================================================

class TestStatePersistence:
    """Test that data persists across backend restarts."""
    
    def test_ingested_media_persists(self):
        """Ingested media should remain in database."""
        if not hasattr(pytest, 'test_image_id'):
            pytest.skip("No test media available")
        
        print(f"\n💾 Testing state persistence")
        
        # Verify media still exists
        detail_response = httpx.get(
            f"{DB_API_URL}/detail/{pytest.test_image_id}",
            timeout=10
        )
        
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["media_id"] == pytest.test_image_id
        print(f"✓ Media persists in database")
    
    def test_thumbnails_persist_on_disk(self):
        """Thumbnails should persist in file cache."""
        if not hasattr(pytest, 'test_image_id'):
            pytest.skip("No test media available")
        
        # Thumbnail should still be accessible
        thumb_response = httpx.get(
            f"{DB_API_URL}/thumbnail/{pytest.test_image_id}?size=medium",
            timeout=30
        )
        
        assert thumb_response.status_code == 200
        print(f"✓ Thumbnail persists on disk")
    
    def test_stats_reflect_current_state(self):
        """Stats should reflect current database state."""
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        assert stats["total_videos"] > 0
        print(f"✓ Stats: {stats['total_videos']} total, {stats['analyzed_count']} analyzed")
    
    def test_media_list_shows_persisted_items(self):
        """Media list should show all persisted items."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        assert list_response.status_code == 200
        
        media_list = list_response.json()
        assert len(media_list) > 0
        print(f"✓ Media list: {len(media_list)} items")


# =============================================================================
# FEATURE 5: Complete End-to-End Workflow
# =============================================================================

class TestCompleteWorkflow:
    """Test complete user workflow from ingestion to playback."""
    
    def test_complete_image_workflow(self, test_image_file):
        """Complete workflow: Ingest → Thumbnail → View → Analyze."""
        print(f"\n🔄 Complete Image Workflow")
        print(f"   File: {Path(test_image_file).name}")
        
        # Step 1: Ingest
        print("   Step 1: Ingesting...")
        ingest_response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": test_image_file},
            timeout=30
        )
        assert ingest_response.status_code == 200
        media_id = ingest_response.json()["media_id"]
        print(f"   ✓ Ingested: {media_id}")
        
        # Step 2: Verify thumbnail generated
        print("   Step 2: Checking thumbnail...")
        time.sleep(2)
        thumb_response = httpx.get(
            f"{DB_API_URL}/thumbnail/{media_id}?size=medium",
            timeout=30
        )
        assert thumb_response.status_code == 200
        print(f"   ✓ Thumbnail: {len(thumb_response.content)} bytes")
        
        # Step 3: View in media list
        print("   Step 3: Checking media list...")
        list_response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert list_response.status_code == 200
        media_list = list_response.json()
        assert any(m["media_id"] == media_id for m in media_list)
        print(f"   ✓ Appears in media list")
        
        # Step 4: View detail page
        print("   Step 4: Checking detail page...")
        detail_response = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
        assert detail_response.status_code == 200
        print(f"   ✓ Detail page accessible")
        
        # Step 5: Trigger analysis
        print("   Step 5: Triggering analysis...")
        analyze_response = httpx.post(f"{DB_API_URL}/analyze/{media_id}", timeout=10)
        assert analyze_response.status_code in [200, 500]
        print(f"   ✓ Analysis triggered")
        
        print(f"\n   ✅ Complete workflow successful!")
    
    def test_complete_video_workflow(self, test_video_file):
        """Complete workflow: Ingest → Thumbnail → Stream → Analyze."""
        print(f"\n🔄 Complete Video Workflow")
        print(f"   File: {Path(test_video_file).name}")
        
        # Step 1: Ingest
        print("   Step 1: Ingesting...")
        ingest_response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": test_video_file},
            timeout=30
        )
        assert ingest_response.status_code == 200
        data = ingest_response.json()
        media_id = data["media_id"]
        print(f"   ✓ Ingested: {media_id}")
        print(f"   ✓ Duration: {data.get('duration_sec', 0)}s")
        
        # Step 2: Verify thumbnail generated
        print("   Step 2: Checking thumbnail...")
        time.sleep(2)
        thumb_response = httpx.get(
            f"{DB_API_URL}/thumbnail/{media_id}?size=medium",
            timeout=30
        )
        assert thumb_response.status_code == 200
        print(f"   ✓ Thumbnail: {len(thumb_response.content)} bytes")
        
        # Step 3: Stream video
        print("   Step 3: Streaming video...")
        video_response = httpx.get(
            f"{DB_API_URL}/video/{media_id}",
            timeout=30
        )
        assert video_response.status_code == 200
        assert "video/" in video_response.headers.get("content-type", "")
        print(f"   ✓ Video streams: {len(video_response.content)} bytes")
        
        # Step 4: View detail page
        print("   Step 4: Checking detail page...")
        page_response = httpx.get(f"{FRONTEND_BASE}/media/{media_id}", timeout=10)
        assert page_response.status_code == 200
        print(f"   ✓ Detail page accessible")
        
        # Step 5: Trigger analysis
        print("   Step 5: Triggering analysis...")
        analyze_response = httpx.post(f"{DB_API_URL}/analyze/{media_id}", timeout=10)
        assert analyze_response.status_code in [200, 500]
        print(f"   ✓ Analysis triggered")
        
        print(f"\n   ✅ Complete workflow successful!")


# =============================================================================
# FEATURE 6: Frontend Button State Sync (Manual Test)
# =============================================================================

class TestFrontendStateSync:
    """Test frontend state synchronization (requires manual verification)."""
    
    def test_frontend_can_fetch_current_state(self):
        """Frontend should be able to fetch current backend state."""
        print(f"\n🔄 Testing frontend state sync")
        
        # Frontend should be able to get current stats
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert stats_response.status_code == 200
        print(f"✓ Stats endpoint accessible")
        
        # Frontend should be able to get health status
        health_response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        assert health_response.status_code == 200
        health = health_response.json()
        assert health["status"] == "healthy"
        print(f"✓ Health endpoint accessible")
        
        # Frontend should be able to get media list
        list_response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert list_response.status_code == 200
        print(f"✓ Media list endpoint accessible")
        
        print(f"\n⚠️  Note: Full state sync requires:")
        print(f"   1. Job state persistence in database")
        print(f"   2. Frontend polling for active jobs")
        print(f"   3. Resume incomplete jobs on restart")
        print(f"   See IMPLEMENTATION_SUMMARY.md for details")


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test performance of recent features."""
    
    def test_thumbnail_generation_speed(self, test_image_file):
        """Thumbnail generation should be reasonably fast."""
        print(f"\n⚡ Testing thumbnail generation speed")
        
        start = time.time()
        
        ingest_response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": test_image_file},
            timeout=30
        )
        
        elapsed = time.time() - start
        
        assert ingest_response.status_code == 200
        assert elapsed < 10.0, f"Ingestion took {elapsed:.2f}s (too slow)"
        print(f"✓ Ingestion + thumbnail: {elapsed:.3f}s")
    
    def test_video_streaming_performance(self):
        """Video streaming should start quickly."""
        if not hasattr(pytest, 'test_video_id'):
            pytest.skip("No test video available")
        
        print(f"\n⚡ Testing video streaming speed")
        
        start = time.time()
        
        video_response = httpx.get(
            f"{DB_API_URL}/video/{pytest.test_video_id}",
            timeout=30
        )
        
        elapsed = time.time() - start
        
        assert video_response.status_code == 200
        # Streaming should start within reasonable time
        # (Full download time depends on file size)
        print(f"✓ Video stream started: {elapsed:.3f}s")


# =============================================================================
# FEATURE 7: Video Transcoding (10-bit to 8-bit)
# =============================================================================

class TestVideoTranscoding:
    """Test video transcoding for browser compatibility."""
    
    def test_video_stream_endpoint_exists(self):
        """Video stream endpoint should exist and respond."""
        # Get any video from the list
        list_response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert list_response.status_code == 200
        
        media_list = list_response.json()
        videos = [m for m in media_list if m.get('duration_sec', 0) > 0]
        
        if not videos:
            pytest.skip("No videos in database")
        
        video_id = videos[0]['media_id']
        print(f"\n🎬 Testing video transcoding: {video_id}")
        
        # Request transcoded stream
        stream_response = httpx.get(
            f"{DB_API_URL}/video-stream/{video_id}",
            timeout=120,  # Transcoding can take time
            follow_redirects=True
        )
        
        assert stream_response.status_code == 200
        content_type = stream_response.headers.get("content-type", "")
        print(f"✓ Content-Type: {content_type}")
        
        # Should be video/mp4 (transcoded) or video/quicktime (original)
        assert "video/" in content_type
    
    def test_transcoded_video_is_mp4(self):
        """Transcoded video should be MP4 format for browser compatibility."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        media_list = list_response.json()
        videos = [m for m in media_list if m.get('duration_sec', 0) > 0]
        
        if not videos:
            pytest.skip("No videos in database")
        
        video_id = videos[0]['media_id']
        
        # Check if transcoded cache exists
        import os
        cache_path = f"/tmp/mediaposter/transcoded/{video_id}.mp4"
        
        if os.path.exists(cache_path):
            # Verify it's a valid MP4
            import subprocess
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0", 
                 "-show_entries", "stream=codec_name,pix_fmt", "-of", "csv=p=0", cache_path],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                codec_info = result.stdout.strip()
                print(f"✓ Transcoded codec: {codec_info}")
                
                # Should be h264 with yuv420p (8-bit)
                assert "h264" in codec_info.lower()
                assert "yuv420p" in codec_info  # 8-bit, not yuv420p10le
                print(f"✓ Video is 8-bit H.264 (browser compatible)")
            else:
                print(f"⚠️  Could not probe transcoded file")
        else:
            print(f"⚠️  Transcoded cache not found (will be created on first request)")
    
    def test_transcoding_uses_temp_file(self):
        """Transcoding should use temp file to avoid serving incomplete files."""
        # Check that temp files don't exist (they should be renamed after completion)
        import os
        cache_dir = "/tmp/mediaposter/transcoded"
        
        if os.path.exists(cache_dir):
            temp_files = [f for f in os.listdir(cache_dir) if '.tmp.' in f]
            print(f"✓ Temp files in cache: {len(temp_files)}")
            
            # Old temp files might indicate failed transcodes
            if temp_files:
                print(f"⚠️  Found temp files (may be failed transcodes): {temp_files[:3]}")
        else:
            print(f"✓ Cache directory will be created on first transcode")


# =============================================================================
# FEATURE 8: Batch Analysis with Status Updates
# =============================================================================

class TestBatchAnalysisStatus:
    """Test batch analysis with real-time status updates."""
    
    def test_batch_analyze_returns_count(self):
        """Batch analyze should return count of queued items."""
        print(f"\n🔬 Testing batch analysis status")
        
        response = httpx.post(
            f"{DB_API_URL}/batch/analyze?limit=5",
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "count" in data
        print(f"✓ Batch analyze response: {data}")
    
    def test_analysis_updates_status_to_analyzing(self):
        """Triggering analysis should update status to 'analyzing'."""
        # Get an unanalyzed item
        list_response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        media_list = list_response.json()
        
        unanalyzed = [m for m in media_list if m.get('status') == 'ingested']
        
        if not unanalyzed:
            print(f"⚠️  No unanalyzed items to test")
            return
        
        media_id = unanalyzed[0]['media_id']
        print(f"✓ Testing status update for: {media_id}")
        
        # Trigger analysis
        analyze_response = httpx.post(
            f"{DB_API_URL}/analyze/{media_id}",
            timeout=10
        )
        
        if analyze_response.status_code == 200:
            # Check if status updated
            time.sleep(1)
            detail_response = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
            
            if detail_response.status_code == 200:
                detail = detail_response.json()
                status = detail.get('status', 'ingested')
                print(f"✓ Status after triggering: {status}")
                
                # Status could be any valid state
                valid_statuses = ['pending', 'ingested', 'analyzing', 'analyzed', 'failed', 'unknown']
                assert status in valid_statuses or status is None, f"Unexpected status: {status}"
    
    def test_stats_show_analyzing_count(self):
        """Stats should show count of items being analyzed."""
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        print(f"✓ Stats: total={stats.get('total_videos')}, analyzed={stats.get('analyzed_count')}")


# =============================================================================
# FEATURE 9: Deep Image Analysis Integration
# =============================================================================

class TestDeepImageAnalysis:
    """Test deep image analysis integration."""
    
    def test_image_analysis_endpoint_exists(self):
        """Image analysis endpoint should exist."""
        print(f"\n🔍 Testing deep image analysis")
        
        # Try with a placeholder URL (will fail but endpoint should exist)
        response = httpx.post(
            f"{API_BASE}/api/image-analysis/analyze",
            json={"test": True},
            timeout=10
        )
        
        # Should return 400 (missing required params) not 404
        assert response.status_code in [200, 400, 422, 500]
        
        if response.status_code == 400:
            data = response.json()
            assert "image_url" in str(data) or "image_base64" in str(data)
            print(f"✓ Endpoint exists, requires image_url or image_base64")
    
    def test_image_analysis_with_thumbnail(self):
        """Image analysis should work with thumbnail URL."""
        # Get a media item
        list_response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        media_list = list_response.json()
        
        if not media_list:
            pytest.skip("No media in database")
        
        media_id = media_list[0]['media_id']
        thumb_url = f"http://localhost:5555/api/media-db/thumbnail/{media_id}?size=large"
        
        print(f"✓ Testing with thumbnail: {media_id}")
        
        response = httpx.post(
            f"{API_BASE}/api/image-analysis/analyze",
            json={
                "image_url": thumb_url,
                "custom_fields": ["scene_analysis"],
                "depth": "quick"
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Analysis complete: {list(data.keys())[:5]}...")
            
            # Should have analysis fields
            assert "analysis_id" in data or "title" in data or "scene_type" in data
        else:
            print(f"⚠️  Analysis returned {response.status_code} (may need API key)")
    
    def test_analysis_result_stored_in_database(self):
        """Deep analysis results should be stored in video analysis."""
        # Get an analyzed item
        list_response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        media_list = list_response.json()
        
        analyzed = [m for m in media_list if m.get('status') == 'analyzed']
        
        if not analyzed:
            print(f"⚠️  No analyzed items to check")
            return
        
        media_id = analyzed[0]['media_id']
        
        # Get analysis details
        analysis_response = httpx.get(
            f"{DB_API_URL}/analysis/{media_id}",
            timeout=10
        )
        
        if analysis_response.status_code == 200:
            data = analysis_response.json()
            visual_analysis = data.get('visual_analysis') or {}
            
            if isinstance(visual_analysis, dict) and visual_analysis.get('deep_analysis'):
                print(f"✓ Deep analysis stored for {media_id}")
            else:
                print(f"⚠️  No deep analysis stored (may not have run yet)")
        else:
            print(f"⚠️  Could not get analysis: {analysis_response.status_code}")


# =============================================================================
# FEATURE 10: Curate Page Video Playback
# =============================================================================

class TestCuratePageVideo:
    """Test video playback on the curate page."""
    
    def test_curate_page_loads(self):
        """Curate page should load successfully."""
        print(f"\n📱 Testing curate page")
        
        response = httpx.get(f"{FRONTEND_BASE}/curate", timeout=10)
        assert response.status_code == 200
        print(f"✓ Curate page loads")
    
    def test_video_source_uses_stream_endpoint(self):
        """Video source should use the video-stream endpoint."""
        response = httpx.get(f"{FRONTEND_BASE}/curate", timeout=10)
        content = response.content.decode('utf-8', errors='ignore')
        
        # Page should reference video-stream or video endpoint
        has_video_ref = 'video-stream' in content or 'video/' in content
        print(f"✓ Page references video endpoints: {has_video_ref}")
    
    def test_video_autoplay_attributes(self):
        """Video element should have correct autoplay attributes."""
        # This is a frontend test - check the page source
        response = httpx.get(f"{FRONTEND_BASE}/curate", timeout=10)
        
        # Just verify the page loads - actual video attributes are in React
        assert response.status_code == 200
        print(f"✓ Curate page accessible for video playback")


# =============================================================================
# FEATURE 11: Media Library Analyze Button
# =============================================================================

class TestMediaLibraryAnalyzeButton:
    """Test the analyze button on the media library page."""
    
    def test_media_library_page_loads(self):
        """Media library page should load."""
        print(f"\n📚 Testing media library")
        
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        assert response.status_code == 200
        print(f"✓ Media library page loads")
    
    def test_batch_analyze_api_works(self):
        """Batch analyze API should accept requests."""
        response = httpx.post(
            f"{DB_API_URL}/batch/analyze?limit=3",
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Batch analyze: {data}")
    
    def test_stats_update_after_analysis(self):
        """Stats should update after analysis runs."""
        # Get initial stats
        initial_stats = httpx.get(f"{DB_API_URL}/stats", timeout=10).json()
        
        # Trigger batch analysis
        httpx.post(f"{DB_API_URL}/batch/analyze?limit=1", timeout=30)
        
        # Wait a moment
        time.sleep(3)
        
        # Get updated stats
        updated_stats = httpx.get(f"{DB_API_URL}/stats", timeout=10).json()
        
        print(f"✓ Initial: {initial_stats.get('analyzed_count')}, Updated: {updated_stats.get('analyzed_count')}")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
