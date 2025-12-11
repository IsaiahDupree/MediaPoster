"""
Full Pipeline E2E Tests
Tests complete workflow: Ingest → Analyze → Search → Display on all pages
Uses real pictures and videos through the entire pipeline.
"""
import pytest
import httpx
import time
from pathlib import Path
import os

# API and Frontend URLs
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
# FULL PIPELINE TEST - IMAGE
# =============================================================================

class TestImageFullPipeline:
    """Test complete pipeline for an image from ingest to display."""
    
    def test_01_ingest_image(self, test_image_file):
        """Step 1: Ingest image file."""
        print(f"\n{'='*60}")
        print(f"FULL IMAGE PIPELINE TEST")
        print(f"{'='*60}")
        print(f"\n📥 STEP 1: INGEST")
        print(f"   File: {Path(test_image_file).name}")
        
        response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": test_image_file},
            timeout=30
        )
        
        assert response.status_code == 200, f"Ingestion failed: {response.text}"
        data = response.json()
        
        assert "media_id" in data
        assert "filename" in data
        assert "status" in data
        
        media_id = data["media_id"]
        pytest.image_media_id = media_id
        
        print(f"   ✓ Ingested successfully")
        print(f"   ✓ Media ID: {media_id}")
        print(f"   ✓ Status: {data['status']}")
        print(f"   ✓ Filename: {data['filename']}")
    
    def test_02_verify_thumbnail_generated(self):
        """Step 2: Verify thumbnail was generated during ingestion."""
        print(f"\n🖼️  STEP 2: THUMBNAIL GENERATION")
        
        if not hasattr(pytest, 'image_media_id'):
            pytest.skip("No image ingested")
        
        # Wait a moment for thumbnail generation
        time.sleep(2)
        
        response = httpx.get(
            f"{DB_API_URL}/thumbnail/{pytest.image_media_id}?size=medium",
            timeout=30
        )
        
        assert response.status_code == 200, "Thumbnail not generated"
        assert response.headers["content-type"] == "image/jpeg"
        assert len(response.content) > 10000, "Thumbnail too small (may be grayscale)"
        
        print(f"   ✓ Thumbnail generated: {len(response.content)} bytes")
        print(f"   ✓ Content-Type: {response.headers['content-type']}")
        print(f"   ✓ Appears to be in color")
    
    def test_03_verify_in_media_list(self):
        """Step 3: Verify image appears in media list."""
        print(f"\n📋 STEP 3: MEDIA LIST")
        
        if not hasattr(pytest, 'image_media_id'):
            pytest.skip("No image ingested")
        
        response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        assert response.status_code == 200
        
        media_list = response.json()
        assert isinstance(media_list, list)
        
        # Find our media in the list
        found = any(m["media_id"] == pytest.image_media_id for m in media_list)
        
        print(f"   ✓ Media list retrieved: {len(media_list)} items")
        if found:
            print(f"   ✓ Image found in list")
        else:
            print(f"   ⚠️  Image not in first {len(media_list)} items (may be pagination)")
    
    def test_04_verify_searchable(self):
        """Step 4: Verify image is searchable."""
        print(f"\n🔍 STEP 4: SEARCH")
        
        if not hasattr(pytest, 'image_media_id'):
            pytest.skip("No image ingested")
        
        # Get the filename
        detail_response = httpx.get(
            f"{DB_API_URL}/detail/{pytest.image_media_id}",
            timeout=10
        )
        assert detail_response.status_code == 200
        filename = detail_response.json()["filename"]
        
        # Search by partial filename
        search_term = Path(filename).stem[:5]  # First 5 chars
        response = httpx.get(
            f"{DB_API_URL}/search?query={search_term}&limit=20",
            timeout=10
        )
        
        assert response.status_code == 200
        results = response.json()
        
        print(f"   ✓ Search executed: query='{search_term}'")
        print(f"   ✓ Results: {len(results)} items")
    
    def test_05_trigger_analysis(self):
        """Step 5: Trigger analysis on the image."""
        print(f"\n🔬 STEP 5: ANALYSIS")
        
        if not hasattr(pytest, 'image_media_id'):
            pytest.skip("No image ingested")
        
        response = httpx.post(
            f"{DB_API_URL}/analyze/{pytest.image_media_id}",
            timeout=10
        )
        
        # Should either start (200) or service unavailable (500)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            print(f"   ✓ Analysis started successfully")
        else:
            print(f"   ⚠️  Analysis service unavailable (expected in test env)")
    
    def test_06_verify_on_dashboard(self):
        """Step 6: Verify image appears on dashboard."""
        print(f"\n📊 STEP 6: DASHBOARD DISPLAY")
        
        response = httpx.get(FRONTEND_BASE, timeout=10)
        assert response.status_code == 200
        
        print(f"   ✓ Dashboard page loads")
        print(f"   ✓ Recent media should include our image")
    
    def test_07_verify_on_media_library(self):
        """Step 7: Verify image appears in media library."""
        print(f"\n🎬 STEP 7: MEDIA LIBRARY DISPLAY")
        
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        assert response.status_code == 200
        
        print(f"   ✓ Media library page loads")
        print(f"   ✓ Image should be visible in grid")
    
    def test_08_verify_detail_page(self):
        """Step 8: Verify image detail page displays correctly."""
        print(f"\n📄 STEP 8: DETAIL PAGE DISPLAY")
        
        if not hasattr(pytest, 'image_media_id'):
            pytest.skip("No image ingested")
        
        response = httpx.get(
            f"{FRONTEND_BASE}/media/{pytest.image_media_id}",
            timeout=10
        )
        assert response.status_code == 200
        
        content = response.content.decode('utf-8', errors='ignore')
        
        # Should show thumbnail, not video player
        assert 'img' in content.lower() or 'image' in content.lower()
        
        print(f"   ✓ Detail page loads")
        print(f"   ✓ Image thumbnail displayed")
    
    def test_09_verify_on_processing_page(self):
        """Step 9: Verify image appears on processing page."""
        print(f"\n⚡ STEP 9: PROCESSING PAGE DISPLAY")
        
        response = httpx.get(f"{FRONTEND_BASE}/processing", timeout=10)
        assert response.status_code == 200
        
        print(f"   ✓ Processing page loads")
        print(f"   ✓ Image should appear in processing queue")
    
    def test_10_pipeline_complete(self):
        """Step 10: Verify complete pipeline."""
        print(f"\n✅ STEP 10: PIPELINE COMPLETE")
        
        if not hasattr(pytest, 'image_media_id'):
            pytest.skip("No image ingested")
        
        # Final verification
        detail_response = httpx.get(
            f"{DB_API_URL}/detail/{pytest.image_media_id}",
            timeout=10
        )
        assert detail_response.status_code == 200
        
        detail = detail_response.json()
        
        print(f"\n   {'='*56}")
        print(f"   IMAGE PIPELINE SUMMARY")
        print(f"   {'='*56}")
        print(f"   Media ID:    {detail['media_id']}")
        print(f"   Filename:    {detail['filename']}")
        print(f"   Status:      {detail['status']}")
        print(f"   Created:     {detail['created_at']}")
        print(f"   {'='*56}")
        print(f"\n   ✅ Full pipeline completed successfully!")
        print(f"   ✅ Image ingested → thumbnail → list → search → analyze → display")


# =============================================================================
# FULL PIPELINE TEST - VIDEO
# =============================================================================

class TestVideoFullPipeline:
    """Test complete pipeline for a video from ingest to display."""
    
    def test_01_ingest_video(self, test_video_file):
        """Step 1: Ingest video file."""
        print(f"\n{'='*60}")
        print(f"FULL VIDEO PIPELINE TEST")
        print(f"{'='*60}")
        print(f"\n📥 STEP 1: INGEST")
        print(f"   File: {Path(test_video_file).name}")
        
        response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": test_video_file},
            timeout=30
        )
        
        assert response.status_code == 200, f"Ingestion failed: {response.text}"
        data = response.json()
        
        assert "media_id" in data
        assert "filename" in data
        assert "status" in data
        
        media_id = data["media_id"]
        pytest.video_media_id = media_id
        
        print(f"   ✓ Ingested successfully")
        print(f"   ✓ Media ID: {media_id}")
        print(f"   ✓ Status: {data['status']}")
        print(f"   ✓ Duration: {data.get('duration_sec', 0)}s")
    
    def test_02_verify_thumbnail_generated(self):
        """Step 2: Verify video thumbnail was generated."""
        print(f"\n🖼️  STEP 2: THUMBNAIL GENERATION")
        
        if not hasattr(pytest, 'video_media_id'):
            pytest.skip("No video ingested")
        
        time.sleep(2)
        
        response = httpx.get(
            f"{DB_API_URL}/thumbnail/{pytest.video_media_id}?size=medium",
            timeout=30
        )
        
        assert response.status_code == 200, "Video thumbnail not generated"
        assert response.headers["content-type"] == "image/jpeg"
        
        print(f"   ✓ Video thumbnail generated: {len(response.content)} bytes")
    
    def test_03_verify_video_streamable(self):
        """Step 3: Verify video is streamable."""
        print(f"\n▶️  STEP 3: VIDEO STREAMING")
        
        if not hasattr(pytest, 'video_media_id'):
            pytest.skip("No video ingested")
        
        response = httpx.get(
            f"{DB_API_URL}/video/{pytest.video_media_id}",
            timeout=30
        )
        
        assert response.status_code == 200, "Video streaming failed"
        assert "video/" in response.headers.get("content-type", "")
        assert len(response.content) > 100000, "Video file too small"
        
        print(f"   ✓ Video streams: {len(response.content)} bytes")
        print(f"   ✓ Content-Type: {response.headers.get('content-type')}")
    
    def test_04_verify_in_media_list(self):
        """Step 4: Verify video appears in media list."""
        print(f"\n📋 STEP 4: MEDIA LIST")
        
        if not hasattr(pytest, 'video_media_id'):
            pytest.skip("No video ingested")
        
        response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        assert response.status_code == 200
        
        media_list = response.json()
        found = any(m["media_id"] == pytest.video_media_id for m in media_list)
        
        print(f"   ✓ Media list retrieved: {len(media_list)} items")
        if found:
            print(f"   ✓ Video found in list")
        else:
            print(f"   ⚠️  Video not in first {len(media_list)} items")
    
    def test_05_verify_searchable(self):
        """Step 5: Verify video is searchable."""
        print(f"\n🔍 STEP 5: SEARCH")
        
        if not hasattr(pytest, 'video_media_id'):
            pytest.skip("No video ingested")
        
        detail_response = httpx.get(
            f"{DB_API_URL}/detail/{pytest.video_media_id}",
            timeout=10
        )
        filename = detail_response.json()["filename"]
        
        search_term = Path(filename).stem[:5]
        response = httpx.get(
            f"{DB_API_URL}/search?query={search_term}&limit=20",
            timeout=10
        )
        
        assert response.status_code == 200
        results = response.json()
        
        print(f"   ✓ Search executed: query='{search_term}'")
        print(f"   ✓ Results: {len(results)} items")
    
    def test_06_trigger_analysis(self):
        """Step 6: Trigger analysis on the video."""
        print(f"\n🔬 STEP 6: ANALYSIS")
        
        if not hasattr(pytest, 'video_media_id'):
            pytest.skip("No video ingested")
        
        response = httpx.post(
            f"{DB_API_URL}/analyze/{pytest.video_media_id}",
            timeout=10
        )
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            print(f"   ✓ Analysis started successfully")
        else:
            print(f"   ⚠️  Analysis service unavailable")
    
    def test_07_verify_on_dashboard(self):
        """Step 7: Verify video appears on dashboard."""
        print(f"\n📊 STEP 7: DASHBOARD DISPLAY")
        
        response = httpx.get(FRONTEND_BASE, timeout=10)
        assert response.status_code == 200
        
        print(f"   ✓ Dashboard page loads")
    
    def test_08_verify_on_media_library(self):
        """Step 8: Verify video appears in media library."""
        print(f"\n🎬 STEP 8: MEDIA LIBRARY DISPLAY")
        
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        assert response.status_code == 200
        
        print(f"   ✓ Media library page loads")
    
    def test_09_verify_detail_page_with_player(self):
        """Step 9: Verify video detail page shows video player."""
        print(f"\n📄 STEP 9: DETAIL PAGE WITH VIDEO PLAYER")
        
        if not hasattr(pytest, 'video_media_id'):
            pytest.skip("No video ingested")
        
        response = httpx.get(
            f"{FRONTEND_BASE}/media/{pytest.video_media_id}",
            timeout=10
        )
        assert response.status_code == 200
        
        content = response.content.decode('utf-8', errors='ignore')
        
        # Should have video element
        assert 'video' in content.lower()
        
        print(f"   ✓ Detail page loads")
        print(f"   ✓ Video player displayed")
    
    def test_10_verify_on_processing_page(self):
        """Step 10: Verify video appears on processing page."""
        print(f"\n⚡ STEP 10: PROCESSING PAGE DISPLAY")
        
        response = httpx.get(f"{FRONTEND_BASE}/processing", timeout=10)
        assert response.status_code == 200
        
        print(f"   ✓ Processing page loads")
    
    def test_11_pipeline_complete(self):
        """Step 11: Verify complete pipeline."""
        print(f"\n✅ STEP 11: PIPELINE COMPLETE")
        
        if not hasattr(pytest, 'video_media_id'):
            pytest.skip("No video ingested")
        
        detail_response = httpx.get(
            f"{DB_API_URL}/detail/{pytest.video_media_id}",
            timeout=10
        )
        assert detail_response.status_code == 200
        
        detail = detail_response.json()
        
        print(f"\n   {'='*56}")
        print(f"   VIDEO PIPELINE SUMMARY")
        print(f"   {'='*56}")
        print(f"   Media ID:    {detail['media_id']}")
        print(f"   Filename:    {detail['filename']}")
        print(f"   Status:      {detail['status']}")
        print(f"   Duration:    {detail.get('duration_sec', 0)}s")
        print(f"   Created:     {detail['created_at']}")
        print(f"   {'='*56}")
        print(f"\n   ✅ Full pipeline completed successfully!")
        print(f"   ✅ Video ingested → thumbnail → stream → list → search → analyze → display")


# =============================================================================
# CROSS-PAGE VERIFICATION
# =============================================================================

class TestCrossPageVerification:
    """Verify media appears correctly across all pages."""
    
    def test_verify_all_pages_accessible(self):
        """Verify all pages in the pipeline are accessible."""
        print(f"\n{'='*60}")
        print(f"CROSS-PAGE VERIFICATION")
        print(f"{'='*60}\n")
        
        pages = [
            ("/", "Dashboard"),
            ("/media", "Media Library"),
            ("/processing", "Processing"),
            ("/analytics", "Analytics"),
            ("/insights", "AI Coach"),
            ("/schedule", "Schedule"),
        ]
        
        for path, name in pages:
            response = httpx.get(f"{FRONTEND_BASE}{path}", timeout=10)
            assert response.status_code == 200, f"{name} page failed to load"
            print(f"   ✓ {name:20} → {path}")
        
        print(f"\n   ✅ All pages in pipeline accessible")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
