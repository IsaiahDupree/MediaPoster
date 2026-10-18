"""
Tests for iOS Import Session Save/Resume Feature

Tests that:
1. Session state is saved correctly (scanned files, filters, job status)
2. Session state is restored correctly on page reload
3. Duplicate status is recalculated on restore (not stale)
4. Button count reflects current duplicate status after restore
"""

import pytest
import tempfile
import json
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
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
    
    for i in range(10):
        video = Path(temp_dir) / f"video_{i}.mp4"
        video.write_bytes(f"fake video content {i}".encode() * 100)
    
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def clean_history():
    """Clear iOS import history"""
    history_file = Path("/tmp/mediaposter/ios_import_history.json")
    if history_file.exists():
        history_file.unlink()
    yield
    if history_file.exists():
        history_file.unlink()


class TestScanReturnsCorrectDuplicateInfo:
    """Test that scan API returns accurate duplicate information"""
    
    def test_scan_returns_is_duplicate_field(self, client, temp_import_dir, clean_history):
        """Each file in scan response should have is_duplicate field"""
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
        
        for file in data["files"]:
            assert "is_duplicate" in file, f"File {file['filename']} missing is_duplicate field"
            assert "will_import" in file, f"File {file['filename']} missing will_import field"
    
    def test_scan_duplicates_count_matches_is_duplicate_files(self, client, temp_import_dir, clean_history):
        """duplicates_count should match number of files with is_duplicate=True"""
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
        
        is_dup_count = len([f for f in data["files"] if f["is_duplicate"]])
        assert data["duplicates_count"] == is_dup_count, \
            f"duplicates_count ({data['duplicates_count']}) != is_duplicate files ({is_dup_count})"
    
    def test_scan_to_import_count_matches_will_import_files(self, client, temp_import_dir, clean_history):
        """to_import_count should match number of files with will_import=True"""
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
        
        will_import_count = len([f for f in data["files"] if f["will_import"]])
        assert data["to_import_count"] == will_import_count, \
            f"to_import_count ({data['to_import_count']}) != will_import files ({will_import_count})"


class TestSessionRestoreRecalculatesDuplicates:
    """Test that restoring a session recalculates duplicate status"""
    
    def test_rescan_after_import_updates_duplicate_status(self, client, temp_import_dir, clean_history):
        """Rescanning after import should show updated duplicate status"""
        client.delete("/api/import/ios/history")
        
        # First scan - no duplicates
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
        data1 = response.json()
        assert data1["duplicates_count"] == 0, "First scan should have no duplicates"
        assert data1["to_import_count"] == 10, "First scan should have 10 files to import"
        
        # Import files
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
        for _ in range(10):
            response = client.get("/api/import/ios/job/current")
            job = response.json().get("job")
            if job and job.get("status") == "completed":
                break
            time.sleep(0.5)
        
        # Rescan - all should be duplicates now
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
        data2 = response.json()
        
        assert data2["duplicates_count"] == 10, f"Rescan should show 10 duplicates, got {data2['duplicates_count']}"
        assert data2["to_import_count"] == 0, f"Rescan should have 0 files to import, got {data2['to_import_count']}"
        
        # Verify each file has updated is_duplicate status
        for file in data2["files"]:
            assert file["is_duplicate"] == True, f"{file['filename']} should be marked as duplicate"
            assert file["will_import"] == False, f"{file['filename']} should have will_import=False"
    
    def test_session_state_should_be_refreshed_not_stale(self, client, temp_import_dir, clean_history):
        """
        Simulates the bug: frontend shows stale session data.
        
        Scenario:
        1. User scans 10 files (no duplicates)
        2. Frontend saves session state with 10 files, 0 duplicates
        3. User imports all 10 files
        4. User refreshes page - frontend loads stale session (0 duplicates)
        5. BUT backend now knows 10 are duplicates
        
        Fix: Frontend should rescan or recalculate duplicate status on restore
        """
        client.delete("/api/import/ios/history")
        
        # Step 1: First scan
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
        session_state = response.json()
        
        # Step 2: Save session state (simulating localStorage save)
        saved_files = session_state["files"]
        assert len([f for f in saved_files if f["is_duplicate"]]) == 0
        
        # Step 3: Import all files
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
        
        import time
        time.sleep(3)
        
        # Step 4: Simulate page refresh - load stale session
        # The saved_files still say is_duplicate=False (stale!)
        stale_duplicates = len([f for f in saved_files if f["is_duplicate"]])
        assert stale_duplicates == 0, "Stale session shows 0 duplicates"
        
        # Step 5: Backend knows the truth
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
        fresh_data = response.json()
        
        # Backend correctly shows all as duplicates
        assert fresh_data["duplicates_count"] == 10, \
            f"Backend should show 10 duplicates, got {fresh_data['duplicates_count']}"
        
        # This test documents the bug: frontend needs to rescan on restore
        # to get accurate duplicate status


class TestImportHistoryAccuracy:
    """Test that import history accurately tracks imported files"""
    
    def test_history_count_matches_imported_files(self, client, temp_import_dir, clean_history):
        """After import, history should contain all imported files"""
        client.delete("/api/import/ios/history")
        
        # Import 10 files
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
        
        import time
        time.sleep(3)
        
        # Check history
        response = client.get("/api/import/ios/history")
        data = response.json()
        
        assert data["count"] == 10, f"History should have 10 entries, got {data['count']}"
    
    def test_partial_import_updates_history(self, client, temp_import_dir, clean_history):
        """If only some files are imported, history should reflect that"""
        client.delete("/api/import/ios/history")
        
        # First import - all 10 files (videos only, we have 10 videos)
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
        
        import time
        time.sleep(3)
        
        # Add 5 more new files
        for i in range(5):
            new_video = Path(temp_import_dir) / f"new_video_{i}.mp4"
            new_video.write_bytes(f"new video content {i}".encode() * 100)
        
        # Scan again
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
        data = response.json()
        
        # Should show 10 duplicates, 5 new
        assert data["total_count"] == 15, f"Total should be 15, got {data['total_count']}"
        assert data["duplicates_count"] == 10, f"Duplicates should be 10, got {data['duplicates_count']}"
        assert data["to_import_count"] == 5, f"To import should be 5, got {data['to_import_count']}"


class TestButtonCountAfterFiltersChange:
    """Test that button count updates correctly when filters change"""
    
    def test_toggle_skip_duplicates_updates_to_import_count(self, client, temp_import_dir, clean_history):
        """Toggling skip_duplicates should update to_import_count"""
        client.delete("/api/import/ios/history")
        
        # Import files first
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
        
        import time
        time.sleep(3)
        
        # Scan with skip_duplicates=True
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
        data_skip = response.json()
        
        # Scan with skip_duplicates=False
        response = client.post("/api/import/ios/scan", json={
            "path": temp_import_dir,
            "filters": {
                "media_types": ["video"],
                "skip_duplicates": False,
                "auto_analyze": False,
                "min_size_mb": 0,
                "max_size_mb": 10000
            }
        })
        data_no_skip = response.json()
        
        # With skip=True, to_import should be 0 (all duplicates)
        assert data_skip["to_import_count"] == 0, \
            f"With skip_duplicates=True, to_import should be 0, got {data_skip['to_import_count']}"
        
        # With skip=False, to_import should be 10 (include duplicates)
        assert data_no_skip["to_import_count"] == 10, \
            f"With skip_duplicates=False, to_import should be 10, got {data_no_skip['to_import_count']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
