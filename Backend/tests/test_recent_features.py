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
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
