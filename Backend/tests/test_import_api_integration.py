"""
Integration Tests for iOS and Android Import APIs

Tests the actual API endpoints for:
1. Device detection
2. Import statistics
3. Scan functionality with skip_duplicates
4. Job management (start, pause, resume, cancel)
5. Import history management
"""

import pytest
import tempfile
import json
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def temp_import_dir():
    """Create a temporary directory with test media files"""
    temp_dir = tempfile.mkdtemp()
    
    # Create test video files
    for i in range(5):
        video = Path(temp_dir) / f"video_{i}.mp4"
        video.write_bytes(f"fake video content {i}".encode() * 100)
    
    # Create test image files
    for i in range(3):
        image = Path(temp_dir) / f"photo_{i}.jpg"
        image.write_bytes(f"fake image content {i}".encode() * 50)
    
    yield temp_dir
    
    shutil.rmtree(temp_dir)


@pytest.fixture
def clean_ios_history():
    """Clear iOS import history"""
    history_file = Path("/tmp/mediaposter/ios_import_history.json")
    if history_file.exists():
        history_file.unlink()
    yield
    if history_file.exists():
        history_file.unlink()


@pytest.fixture
def clean_android_history():
    """Clear Android import history"""
    history_file = Path("/tmp/mediaposter/android_import_history.json")
    if history_file.exists():
        history_file.unlink()
    yield
    if history_file.exists():
        history_file.unlink()


class TestiOSImportAPI:
    """Test iOS Import API endpoints"""
    
    def test_device_endpoint_exists(self, client):
        """Device endpoint should return valid response"""
        response = client.get("/api/import/ios/device")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
    
    def test_stats_endpoint(self, client, clean_ios_history):
        """Stats endpoint should return valid statistics"""
        response = client.get("/api/import/ios/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected fields
        assert "total_imports" in data
        assert "total_size_gb" in data
        assert "duplicates_skipped" in data
        assert "videos_imported" in data
        assert "images_imported" in data
    
    def test_current_job_endpoint(self, client):
        """Current job endpoint should return job or null"""
        response = client.get("/api/import/ios/job/current")
        assert response.status_code == 200
        data = response.json()
        assert "job" in data
    
    def test_scan_nonexistent_directory(self, client):
        """Scanning non-existent directory should return 404"""
        response = client.post("/api/import/ios/scan", json={
            "path": "/nonexistent/path/that/does/not/exist",
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        assert response.status_code == 404
    
    def test_scan_valid_directory(self, client, temp_import_dir, clean_ios_history):
        """Scanning valid directory should return file list"""
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "files" in data
        assert "total_count" in data
        assert "duplicates_count" in data
        assert "to_import_count" in data
        
        # We created 5 videos + 3 images = 8 files
        assert data["total_count"] == 8
        assert data["duplicates_count"] == 0  # Fresh scan
        assert data["to_import_count"] == 8
    
    def test_scan_with_video_filter(self, client, temp_import_dir, clean_ios_history):
        """Scanning with video-only filter should return only videos"""
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Only 5 videos should be returned
        assert data["total_count"] == 5
        for file in data["files"]:
            assert file["type"] == "video"
    
    def test_scan_with_image_filter(self, client, temp_import_dir, clean_ios_history):
        """Scanning with image-only filter should return only images"""
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Only 3 images should be returned
        assert data["total_count"] == 3
        for file in data["files"]:
            assert file["type"] == "image"
    
    def test_history_endpoint(self, client, clean_ios_history):
        """History endpoint should return import history"""
        # Clear history first via API
        client.delete("/api/import/ios/history")
        
        response = client.get("/api/import/ios/history")
        assert response.status_code == 200
        data = response.json()
        
        assert "count" in data
        assert "history" in data
        assert data["count"] == 0  # Clean history
    
    def test_clear_history_endpoint(self, client, clean_ios_history):
        """Clear history endpoint should work"""
        response = client.delete("/api/import/ios/history")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
    
    def test_open_image_capture_endpoint(self, client):
        """Open Image Capture endpoint should exist"""
        response = client.post("/api/import/ios/open-image-capture")
        # This might fail on CI without GUI, but endpoint should exist
        assert response.status_code in [200, 500]


class TestAndroidImportAPI:
    """Test Android Import API endpoints"""
    
    def test_device_endpoint_exists(self, client):
        """Device endpoint should return valid response"""
        response = client.get("/api/import/android/device")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
    
    def test_stats_endpoint(self, client, clean_android_history):
        """Stats endpoint should return valid statistics"""
        response = client.get("/api/import/android/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_imports" in data
        assert "total_size_gb" in data
        assert "videos_imported" in data
        assert "images_imported" in data
    
    def test_current_job_endpoint(self, client):
        """Current job endpoint should return job or null"""
        response = client.get("/api/import/android/job/current")
        assert response.status_code == 200
        data = response.json()
        assert "job" in data
    
    def test_scan_valid_directory(self, client, temp_import_dir, clean_android_history):
        """Scanning valid directory should return file list"""
        response = client.post("/api/import/android/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] == 8
        assert data["to_import_count"] == 8
    
    def test_history_endpoint(self, client, clean_android_history):
        """History endpoint should return import history"""
        response = client.get("/api/import/android/history")
        assert response.status_code == 200
        data = response.json()
        
        assert "count" in data
        assert "history" in data


class TestSkipDuplicatesIntegration:
    """Test skip_duplicates functionality across API"""
    
    def test_scan_detects_duplicates_after_import(self, client, temp_import_dir, clean_ios_history):
        """After starting import, subsequent scans should detect duplicates"""
        # First scan - no duplicates
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data["duplicates_count"] == 0
        assert data["to_import_count"] == 8
        
        # Start import
        response = client.post("/api/import/ios/start", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        assert response.status_code == 200
        
        # Wait for job to complete (poll)
        import time
        for _ in range(10):
            response = client.get("/api/import/ios/job/current")
            job = response.json().get("job")
            if job and job.get("status") == "completed":
                break
            time.sleep(0.5)
        
        # Now scan again - should detect duplicates
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # All files should now be duplicates
        assert data["duplicates_count"] == 8
        assert data["to_import_count"] == 0, "No files should be marked for import after previous import"
    
    def test_skip_duplicates_false_imports_all(self, client, temp_import_dir, clean_ios_history):
        """With skip_duplicates=False, duplicates should still be marked for import"""
        # First import
        client.post("/api/import/ios/start", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        
        # Wait for completion
        import time
        time.sleep(2)
        
        # Scan with skip_duplicates=False
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video"],
                "skip_duplicates": False,  # Allow duplicates
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Files are duplicates but will_import should be True
        for file in data["files"]:
            assert file["will_import"] == True, "With skip_duplicates=False, all files should be marked for import"


class TestJobManagement:
    """Test import job management endpoints"""
    
    def test_pause_nonexistent_job(self, client):
        """Pausing non-existent job should return 404"""
        response = client.post("/api/import/ios/job/fake-job-id/pause")
        assert response.status_code == 404
    
    def test_resume_nonexistent_job(self, client):
        """Resuming non-existent job should return 404"""
        response = client.post("/api/import/ios/job/fake-job-id/resume")
        assert response.status_code == 404
    
    def test_cancel_nonexistent_job(self, client):
        """Cancelling non-existent job should return 404"""
        response = client.post("/api/import/ios/job/fake-job-id/cancel")
        assert response.status_code == 404


class TestStartImportButtonCount:
    """Test that Start Import button shows correct count (non-duplicates only when skip_duplicates=True)"""
    
    def test_to_import_count_equals_total_when_no_duplicates(self, client, temp_import_dir, clean_ios_history):
        """When no duplicates exist, to_import_count should equal total_count"""
        # Clear any existing history
        client.delete("/api/import/ios/history")
        
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        data = response.json()
        
        assert data["to_import_count"] == data["total_count"], \
            "With no duplicates, to_import_count should equal total_count"
        assert data["duplicates_count"] == 0
    
    def test_to_import_count_excludes_duplicates(self, client, temp_import_dir, clean_ios_history):
        """When duplicates exist and skip_duplicates=True, to_import_count should exclude them"""
        # Clear and do first import
        client.delete("/api/import/ios/history")
        
        # First import
        response = client.post("/api/import/ios/start", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        
        # Wait for completion
        import time
        for _ in range(10):
            response = client.get("/api/import/ios/job/current")
            job = response.json().get("job")
            if job and job.get("status") == "completed":
                break
            time.sleep(0.5)
        
        # Now scan again - duplicates should be excluded from to_import_count
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        data = response.json()
        
        # All 8 files should be duplicates now
        assert data["total_count"] == 8
        assert data["duplicates_count"] == 8
        assert data["to_import_count"] == 0, \
            "With skip_duplicates=True, to_import_count should be 0 when all are duplicates"
        
        # Verify each file has will_import=False
        for file in data["files"]:
            assert file["is_duplicate"] == True, f"{file['filename']} should be marked as duplicate"
            assert file["will_import"] == False, f"{file['filename']} should have will_import=False"
    
    def test_to_import_count_includes_duplicates_when_disabled(self, client, temp_import_dir, clean_ios_history):
        """When skip_duplicates=False, to_import_count should include duplicates"""
        # Clear and do first import
        client.delete("/api/import/ios/history")
        
        # First import (with skip duplicates ON)
        response = client.post("/api/import/ios/start", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        
        import time
        time.sleep(2)
        
        # Now scan with skip_duplicates=False
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video"],
                "skip_duplicates": False,  # Disabled
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        data = response.json()
        
        # All files should be marked for import even if duplicates
        assert data["to_import_count"] == data["total_count"], \
            "With skip_duplicates=False, to_import_count should equal total_count"
        
        # Verify each file has will_import=True
        for file in data["files"]:
            assert file["will_import"] == True, \
                f"{file['filename']} should have will_import=True when skip_duplicates=False"
    
    def test_button_count_matches_will_import_files(self, client, temp_import_dir, clean_ios_history):
        """The count shown on Start Import button should match files with will_import=True"""
        client.delete("/api/import/ios/history")
        
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        data = response.json()
        
        # Count files where will_import=True
        will_import_count = len([f for f in data["files"] if f["will_import"]])
        
        # This should match to_import_count
        assert data["to_import_count"] == will_import_count, \
            f"to_import_count ({data['to_import_count']}) should match will_import file count ({will_import_count})"


class TestAPIResponseFormats:
    """Test that API responses have correct format"""
    
    def test_ios_device_response_format(self, client):
        """iOS device response should have expected structure"""
        response = client.get("/api/import/ios/device")
        data = response.json()
        
        assert isinstance(data.get("connected"), bool)
        if data["connected"]:
            assert "name" in data
    
    def test_android_device_response_format(self, client):
        """Android device response should have expected structure"""
        response = client.get("/api/import/android/device")
        data = response.json()
        
        assert isinstance(data.get("connected"), bool)
        if data["connected"]:
            assert "name" in data
    
    def test_scan_file_format(self, client, temp_import_dir, clean_ios_history):
        """Scanned file entries should have all required fields"""
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video", "image"],
                "skip_duplicates": True,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        data = response.json()
        
        for file in data["files"]:
            assert "path" in file
            assert "filename" in file
            assert "type" in file
            assert "size_bytes" in file
            assert "modified_at" in file
            assert "is_duplicate" in file
            assert "will_import" in file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
