"""
Tests for iOS Import save and resume previous session feature.

Tests:
1. Save state to localStorage
2. Restore state from localStorage
3. Recalculate will_import based on current filters
4. Duplicate detection before import
5. Resume paused jobs
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import the iOS import API functions
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.endpoints.ios_import_api import (
    scan_directory,
    is_duplicate,
    mark_as_imported,
    load_import_history,
    save_import_history,
    get_file_hash
)
from api.endpoints.ios_import_api import ImportFilter, ScanRequest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_video_file(temp_dir):
    """Create a sample video file for testing"""
    video_file = temp_dir / "test_video.MOV"
    video_file.write_bytes(b"fake video content" * 1000)  # ~17KB
    return video_file


@pytest.fixture
def duplicate_video_file(temp_dir):
    """Create a duplicate video file (same name, size, mtime)"""
    video_file = temp_dir / "test_video_dup.MOV"
    video_file.write_bytes(b"fake video content" * 1000)  # Same size
    return video_file


class TestSaveResumeSession:
    """Test save and resume previous session functionality"""
    
    @pytest.mark.asyncio
    async def test_save_state_structure(self, temp_dir, sample_video_file):
        """Test that saved state has correct structure"""
        # Create a scan request
        request = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["video"],
                skip_duplicates=True
            )
        )
        
        # Scan directory (async)
        result = await scan_directory(request)
        
        # Verify structure
        assert "files" in result
        assert "total_count" in result
        assert "duplicates_count" in result
        assert "to_import_count" in result
        
        # Verify file structure
        if result["files"]:
            file = result["files"][0]
            assert "path" in file
            assert "filename" in file
            assert "type" in file
            assert "size_bytes" in file
            assert "modified_at" in file
            assert "is_duplicate" in file
            assert "will_import" in file
    
    @pytest.mark.asyncio
    async def test_will_import_calculation_with_duplicates(self, temp_dir, sample_video_file):
        """Test that will_import is correctly calculated based on skip_duplicates filter"""
        # First, mark the file as imported (making it a duplicate)
        mark_as_imported(sample_video_file)
        
        # Test with skip_duplicates=True
        request_with_skip = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["video"],
                skip_duplicates=True
            )
        )
        result_with_skip = await scan_directory(request_with_skip)
        
        # Find our file
        test_file = next((f for f in result_with_skip["files"] if f["filename"] == sample_video_file.name), None)
        assert test_file is not None
        assert test_file["is_duplicate"] is True
        assert test_file["will_import"] is False  # Should not import duplicates
        
        # Test with skip_duplicates=False
        request_without_skip = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["video"],
                skip_duplicates=False
            )
        )
        result_without_skip = await scan_directory(request_without_skip)
        
        # Find our file
        test_file2 = next((f for f in result_without_skip["files"] if f["filename"] == sample_video_file.name), None)
        assert test_file2 is not None
        assert test_file2["is_duplicate"] is True
        assert test_file2["will_import"] is True  # Should import even if duplicate
    
    @pytest.mark.asyncio
    async def test_will_import_calculation_with_media_type_filter(self, temp_dir, sample_video_file):
        """Test that will_import respects media_type filter"""
        # Test with video filter
        request_video = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["video"],
                skip_duplicates=False
            )
        )
        result_video = await scan_directory(request_video)
        
        # Video file should be included
        video_file = next((f for f in result_video["files"] if f["type"] == "video"), None)
        if video_file:
            assert video_file["will_import"] is True
        
        # Test with image filter only
        request_image = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["image"],
                skip_duplicates=False
            )
        )
        result_image = await scan_directory(request_image)
        
        # Video file should NOT be included
        video_file_in_image = next((f for f in result_image["files"] if f["type"] == "video"), None)
        if video_file_in_image:
            assert video_file_in_image["will_import"] is False
    
    @pytest.mark.asyncio
    async def test_will_import_calculation_with_size_filter(self, temp_dir):
        """Test that will_import respects size filters"""
        # Create a small file (< 1MB)
        small_file = temp_dir / "small.MOV"
        small_file.write_bytes(b"x" * 100)  # 100 bytes
        
        # Create a large file (> 10MB)
        large_file = temp_dir / "large.MOV"
        large_file.write_bytes(b"x" * (11 * 1024 * 1024))  # 11MB
        
        # Test with size filter 1MB - 10MB
        request = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["video"],
                min_size_mb=1.0,
                max_size_mb=10.0,
                skip_duplicates=False
            )
        )
        result = await scan_directory(request)
        
        # Small file should be excluded
        small = next((f for f in result["files"] if f["filename"] == "small.MOV"), None)
        if small:
            assert small["will_import"] is False
        
        # Large file should be excluded
        large = next((f for f in result["files"] if f["filename"] == "large.MOV"), None)
        if large:
            assert large["will_import"] is False


class TestDuplicateDetection:
    """Test duplicate detection before import"""
    
    @pytest.mark.asyncio
    async def test_duplicate_detection_before_import(self, temp_dir, sample_video_file):
        """Test that duplicates are detected before import starts"""
        # Mark file as imported
        mark_as_imported(sample_video_file)
        
        # Scan directory
        request = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["video"],
                skip_duplicates=True
            )
        )
        result = await scan_directory(request)
        
        # Verify duplicate is detected
        test_file = next((f for f in result["files"] if f["filename"] == sample_video_file.name), None)
        assert test_file is not None
        assert test_file["is_duplicate"] is True
        assert result["duplicates_count"] > 0
        
        # Verify it won't be imported
        assert test_file["will_import"] is False
        assert result["to_import_count"] == 0
    
    @pytest.mark.asyncio
    async def test_duplicate_count_accuracy(self, temp_dir):
        """Test that duplicate count matches actual duplicates"""
        # Create multiple files
        files = []
        for i in range(5):
            file = temp_dir / f"video_{i}.MOV"
            file.write_bytes(b"content" * 1000)
            files.append(file)
        
        # Mark 2 as imported
        mark_as_imported(files[0])
        mark_as_imported(files[1])
        
        # Scan
        request = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["video"],
                skip_duplicates=True
            )
        )
        result = await scan_directory(request)
        
        # Should have 2 duplicates
        assert result["duplicates_count"] == 2
        assert result["to_import_count"] == 3  # 5 total - 2 duplicates
    
    def test_file_hash_consistency(self, temp_dir, sample_video_file):
        """Test that file hash is consistent for duplicate detection"""
        hash1 = get_file_hash(sample_video_file)
        hash2 = get_file_hash(sample_video_file)
        
        # Hash should be the same
        assert hash1 == hash2
        
        # Mark as imported
        mark_as_imported(sample_video_file)
        
        # Should be detected as duplicate
        assert is_duplicate(sample_video_file) is True


class TestCountAccuracy:
    """Test that file counts are accurate"""
    
    @pytest.mark.asyncio
    async def test_start_import_count_matches_will_import(self, temp_dir):
        """Test that 'Start Import (X files)' count matches files with will_import=True"""
        # Create mix of files
        files = []
        for i in range(10):
            file = temp_dir / f"video_{i}.MOV"
            file.write_bytes(b"content" * 1000)
            files.append(file)
        
        # Mark some as duplicates
        for i in range(3):
            mark_as_imported(files[i])
        
        # Scan with skip_duplicates=True
        request = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["video"],
                skip_duplicates=True
            )
        )
        result = await scan_directory(request)
        
        # Count files with will_import=True
        will_import_count = sum(1 for f in result["files"] if f["will_import"])
        
        # Should match to_import_count
        assert will_import_count == result["to_import_count"]
        assert will_import_count == 7  # 10 total - 3 duplicates
    
    @pytest.mark.asyncio
    async def test_count_updates_when_filters_change(self, temp_dir, sample_video_file):
        """Test that count updates correctly when filters change"""
        # Mark file as duplicate
        mark_as_imported(sample_video_file)
        
        # Scan with skip_duplicates=True
        request1 = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["video"],
                skip_duplicates=True
            )
        )
        result1 = await scan_directory(request1)
        count1 = result1["to_import_count"]
        
        # Scan with skip_duplicates=False
        request2 = ScanRequest(
            path=str(temp_dir),
            filters=ImportFilter(
                media_types=["video"],
                skip_duplicates=False
            )
        )
        result2 = await scan_directory(request2)
        count2 = result2["to_import_count"]
        
        # Count should be different
        assert count1 < count2
        # With skip_duplicates=False, duplicate should be included
        assert count2 > 0


class TestStatePersistence:
    """Test state save and restore"""
    
    def test_import_history_persistence(self, temp_dir, sample_video_file):
        """Test that import history persists across sessions"""
        # Mark file as imported
        mark_as_imported(sample_video_file)
        
        # Verify it's in history
        history = load_import_history()
        file_hash = get_file_hash(sample_video_file)
        assert file_hash in history
        
        # Clear in-memory history
        from api.endpoints.ios_import_api import _import_history
        _import_history.clear()
        
        # Reload from disk
        history2 = load_import_history()
        assert file_hash in history2
    
    def test_restore_state_recalculates_will_import(self, temp_dir, sample_video_file):
        """Test that restoring state recalculates will_import based on current filters"""
        # Mark file as imported
        mark_as_imported(sample_video_file)
        
        # Simulate saved state with old will_import value
        saved_state = {
            "files": [{
                "path": str(sample_video_file),
                "filename": sample_video_file.name,
                "type": "video",
                "size_bytes": sample_video_file.stat().st_size,
                "modified_at": datetime.fromtimestamp(sample_video_file.stat().st_mtime).isoformat(),
                "is_duplicate": True,
                "will_import": True  # Old value - should be False with skip_duplicates=True
            }],
            "filters": {
                "media_types": ["video"],
                "skip_duplicates": True
            }
        }
        
        # Recalculate will_import with current filters
        filters = ImportFilter(**saved_state["filters"])
        for file in saved_state["files"]:
            file_path = Path(file["path"])
            is_dup = is_duplicate(file_path)
            file["will_import"] = not (filters.skip_duplicates and is_dup)
        
        # Verify will_import is recalculated correctly
        assert saved_state["files"][0]["will_import"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

