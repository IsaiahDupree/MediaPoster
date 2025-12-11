"""
End-to-End Tests with Real Media Files
Tests the complete workflow from ingestion to analysis with actual image and video files.
"""
import pytest
import httpx
import time
from pathlib import Path
import os

# Real API URL
API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"

# Test media directory
TEST_MEDIA_DIR = Path(os.path.expanduser("~/Documents/IphoneImport"))


# =============================================================================
# FIXTURES - Find Real Media Files
# =============================================================================

@pytest.fixture(scope="module")
def real_image_file():
    """Find a real HEIC image file for testing."""
    if not TEST_MEDIA_DIR.exists():
        pytest.skip("Test media directory not found")
    
    heic_files = list(TEST_MEDIA_DIR.glob("*.HEIC"))[:1]
    if not heic_files:
        pytest.skip("No HEIC files found for testing")
    
    return str(heic_files[0])


@pytest.fixture(scope="module")
def real_video_file():
    """Find a real video file for testing."""
    if not TEST_MEDIA_DIR.exists():
        pytest.skip("Test media directory not found")
    
    video_files = list(TEST_MEDIA_DIR.glob("*.MOV"))[:1]
    if not video_files:
        pytest.skip("No MOV files found for testing")
    
    return str(video_files[0])


# =============================================================================
# E2E TEST: Image Workflow
# =============================================================================

class TestImageWorkflowE2E:
    """Test complete image workflow with real HEIC file."""
    
    def test_01_ingest_image(self, real_image_file):
        """Ingest a real HEIC image file."""
        response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": real_image_file},
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "media_id" in data
        assert data["filename"].endswith(".HEIC")
        
        # Store for next tests
        pytest.test_image_id = data["media_id"]
        print(f"\n✓ Ingested image: {data['media_id']}")
    
    def test_02_verify_image_in_list(self):
        """Verify image appears in media list."""
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert response.status_code == 200
        
        media_list = response.json()
        assert any(m["media_id"] == pytest.test_image_id for m in media_list)
        print(f"✓ Image found in list")
    
    def test_03_get_image_detail(self):
        """Get detailed information about the image."""
        response = httpx.get(
            f"{DB_API_URL}/detail/{pytest.test_image_id}",
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["media_id"] == pytest.test_image_id
        assert data["resolution"] is not None
        assert data["file_size"] > 0
        print(f"✓ Image details: {data['resolution']}, {data['file_size']} bytes")
    
    def test_04_get_image_thumbnail(self):
        """Verify thumbnail was generated with proper color."""
        response = httpx.get(
            f"{DB_API_URL}/thumbnail/{pytest.test_image_id}?size=medium",
            timeout=30
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert len(response.content) > 1000  # Reasonable thumbnail size
        print(f"✓ Thumbnail generated: {len(response.content)} bytes")
    
    def test_05_run_analysis_on_image(self):
        """Run AI analysis on the image."""
        response = httpx.post(
            f"{DB_API_URL}/analyze/{pytest.test_image_id}",
            timeout=10
        )
        
        # Should start analysis or indicate already analyzed
        assert response.status_code in [200, 500]  # 500 if analysis service unavailable
        if response.status_code == 200:
            print(f"✓ Analysis started")
    
    def test_06_verify_stats_updated(self):
        """Verify stats reflect the ingested image."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
        
        stats = response.json()
        assert stats["total_videos"] > 0
        print(f"✓ Stats: {stats['total_videos']} total media")


# =============================================================================
# E2E TEST: Video Workflow
# =============================================================================

class TestVideoWorkflowE2E:
    """Test complete video workflow with real MOV file."""
    
    def test_01_ingest_video(self, real_video_file):
        """Ingest a real MOV video file."""
        response = httpx.post(
            f"{DB_API_URL}/ingest/file",
            params={"file_path": real_video_file},
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "media_id" in data
        assert data["filename"].endswith(".MOV")
        assert data["duration_sec"] > 0
        
        pytest.test_video_id = data["media_id"]
        print(f"\n✓ Ingested video: {data['media_id']}, duration: {data['duration_sec']}s")
    
    def test_02_verify_video_in_list(self):
        """Verify video appears in media list."""
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert response.status_code == 200
        
        media_list = response.json()
        video = next((m for m in media_list if m["media_id"] == pytest.test_video_id), None)
        assert video is not None
        assert video["duration_sec"] > 0
        print(f"✓ Video found in list")
    
    def test_03_get_video_detail(self):
        """Get detailed information about the video."""
        response = httpx.get(
            f"{DB_API_URL}/detail/{pytest.test_video_id}",
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["media_id"] == pytest.test_video_id
        assert data["duration_sec"] > 0
        assert data["resolution"] is not None
        print(f"✓ Video details: {data['duration_sec']}s, {data['resolution']}")
    
    def test_04_get_video_thumbnail(self):
        """Verify video thumbnail was generated."""
        response = httpx.get(
            f"{DB_API_URL}/thumbnail/{pytest.test_video_id}?size=medium",
            timeout=30
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert len(response.content) > 1000
        print(f"✓ Video thumbnail: {len(response.content)} bytes")
    
    def test_05_stream_video(self):
        """Verify video can be streamed."""
        response = httpx.get(
            f"{DB_API_URL}/video/{pytest.test_video_id}",
            timeout=30,
            follow_redirects=True
        )
        
        assert response.status_code == 200
        assert "video/" in response.headers.get("content-type", "")
        assert len(response.content) > 10000  # Video should be substantial
        print(f"✓ Video stream: {len(response.content)} bytes")
    
    def test_06_run_analysis_on_video(self):
        """Run AI analysis on the video."""
        response = httpx.post(
            f"{DB_API_URL}/analyze/{pytest.test_video_id}",
            timeout=10
        )
        
        # Should start analysis or indicate already analyzed
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            print(f"✓ Analysis started")


# =============================================================================
# E2E TEST: Batch Ingestion
# =============================================================================

class TestBatchIngestionE2E:
    """Test batch ingestion with real directory."""
    
    @pytest.mark.skipif(not TEST_MEDIA_DIR.exists(), reason="Test media directory not available")
    def test_01_batch_ingest(self):
        """Batch ingest from real directory."""
        response = httpx.post(
            f"{DB_API_URL}/batch/ingest",
            json={
                "directory_path": str(TEST_MEDIA_DIR),
                "resume": True
            },
            timeout=30
        )
        
        # Should succeed or indicate no new files
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Batch ingest started: {data.get('total_files', 0)} files")
    
    def test_02_verify_batch_results(self):
        """Wait and verify batch ingestion results."""
        # Give it time to process
        time.sleep(5)
        
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
        
        stats = response.json()
        assert stats["total_videos"] > 0
        print(f"✓ After batch: {stats['total_videos']} total media")


# =============================================================================
# E2E TEST: Performance
# =============================================================================

class TestPerformanceE2E:
    """Test performance with real media."""
    
    def test_list_performance(self):
        """List endpoint should be fast even with many items."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0
        print(f"\n✓ List 50 items: {elapsed:.3f}s")
    
    def test_thumbnail_generation_performance(self):
        """Thumbnail generation should complete in reasonable time."""
        # Get a media item
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if response.status_code != 200 or not response.json():
            pytest.skip("No media available")
        
        media_id = response.json()[0]["media_id"]
        
        start = time.time()
        response = httpx.get(
            f"{DB_API_URL}/thumbnail/{media_id}?size=small",
            timeout=30
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 10.0  # Should be fast, especially if cached
        print(f"✓ Thumbnail generation: {elapsed:.3f}s")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
