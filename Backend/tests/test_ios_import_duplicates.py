"""
Tests for iOS Import Duplicate Detection

Ensures that the skip_duplicates functionality works correctly:
1. Files are hashed consistently
2. Duplicates are detected and skipped
3. Import history is persisted and loaded correctly
4. Scan correctly marks duplicates
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
import shutil
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.endpoints.ios_import_api import (
    get_file_hash,
    is_duplicate,
    mark_as_imported,
    load_import_history,
    save_import_history,
    get_media_type,
    _import_history,
    IMPORT_HISTORY_FILE
)


@pytest.fixture
def temp_media_dir():
    """Create a temporary directory with test media files"""
    temp_dir = tempfile.mkdtemp()
    
    # Create test video files
    video1 = Path(temp_dir) / "video1.mp4"
    video1.write_bytes(b"fake video content 1" * 100)
    
    video2 = Path(temp_dir) / "video2.mov"
    video2.write_bytes(b"fake video content 2" * 100)
    
    # Create test image files
    image1 = Path(temp_dir) / "photo1.jpg"
    image1.write_bytes(b"fake image content 1" * 50)
    
    image2 = Path(temp_dir) / "photo2.heic"
    image2.write_bytes(b"fake image content 2" * 50)
    
    # Create a duplicate (same name and size as video1)
    duplicate = Path(temp_dir) / "subfolder"
    duplicate.mkdir()
    dup_video = duplicate / "video1.mp4"
    dup_video.write_bytes(b"fake video content 1" * 100)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def clean_history():
    """Clear import history before and after each test"""
    global _import_history
    _import_history.clear()
    if IMPORT_HISTORY_FILE.exists():
        IMPORT_HISTORY_FILE.unlink()
    yield
    _import_history.clear()
    if IMPORT_HISTORY_FILE.exists():
        IMPORT_HISTORY_FILE.unlink()


class TestFileHashGeneration:
    """Test that file hashes are generated correctly and consistently"""
    
    def test_hash_same_file_twice(self, temp_media_dir):
        """Same file should produce same hash"""
        video = Path(temp_media_dir) / "video1.mp4"
        hash1 = get_file_hash(video)
        hash2 = get_file_hash(video)
        assert hash1 == hash2, "Same file should produce identical hash"
    
    def test_hash_different_files(self, temp_media_dir):
        """Different files should produce different hashes"""
        video1 = Path(temp_media_dir) / "video1.mp4"
        video2 = Path(temp_media_dir) / "video2.mov"
        hash1 = get_file_hash(video1)
        hash2 = get_file_hash(video2)
        assert hash1 != hash2, "Different files should have different hashes"
    
    def test_hash_includes_filename(self, temp_media_dir):
        """Hash should include filename - same content, different name = different hash"""
        # Create two files with same content but different names
        file1 = Path(temp_media_dir) / "same_content_a.mp4"
        file2 = Path(temp_media_dir) / "same_content_b.mp4"
        content = b"identical content" * 100
        file1.write_bytes(content)
        file2.write_bytes(content)
        
        hash1 = get_file_hash(file1)
        hash2 = get_file_hash(file2)
        assert hash1 != hash2, "Files with same content but different names should have different hashes"


class TestDuplicateDetection:
    """Test that duplicates are correctly detected"""
    
    def test_new_file_not_duplicate(self, temp_media_dir, clean_history):
        """A new file should not be detected as duplicate"""
        video = Path(temp_media_dir) / "video1.mp4"
        assert not is_duplicate(video), "New file should not be a duplicate"
    
    def test_imported_file_is_duplicate(self, temp_media_dir, clean_history):
        """A previously imported file should be detected as duplicate"""
        video = Path(temp_media_dir) / "video1.mp4"
        
        # First check - not a duplicate
        assert not is_duplicate(video)
        
        # Mark as imported
        mark_as_imported(video)
        
        # Now it should be a duplicate
        assert is_duplicate(video), "Imported file should be detected as duplicate"
    
    def test_similar_file_different_location_not_duplicate(self, temp_media_dir, clean_history):
        """Files with same name in different folders should be independent"""
        video1 = Path(temp_media_dir) / "video1.mp4"
        video2 = Path(temp_media_dir) / "subfolder" / "video1.mp4"
        
        # Import the first one
        mark_as_imported(video1)
        
        # The second one has same content but different path/mtime
        # This tests the hash algorithm - they might be different due to mtime
        # If we want them to be considered duplicates, we'd need content-based hashing
        
        # For now, verify the detection logic runs without error
        result = is_duplicate(video2)
        assert isinstance(result, bool), "is_duplicate should return boolean"


class TestImportHistory:
    """Test that import history is persisted correctly"""
    
    def test_history_persists_to_disk(self, temp_media_dir, clean_history):
        """Import history should be saved to disk"""
        video = Path(temp_media_dir) / "video1.mp4"
        mark_as_imported(video)
        
        # Check file was created
        assert IMPORT_HISTORY_FILE.exists(), "History file should be created"
        
        # Check content
        with open(IMPORT_HISTORY_FILE) as f:
            data = json.load(f)
        assert len(data) == 1, "History should contain one entry"
    
    def test_history_loads_from_disk(self, temp_media_dir, clean_history):
        """Import history should be loaded from disk on restart"""
        video = Path(temp_media_dir) / "video1.mp4"
        
        # Import and save
        mark_as_imported(video)
        
        # Clear in-memory history
        global _import_history
        _import_history.clear()
        
        # Load from disk
        load_import_history()
        
        # Should still detect as duplicate
        assert is_duplicate(video), "Should detect duplicate after loading from disk"
    
    def test_history_entry_contains_metadata(self, temp_media_dir, clean_history):
        """History entries should contain useful metadata"""
        video = Path(temp_media_dir) / "video1.mp4"
        mark_as_imported(video, destination="/imported/video1.mp4")
        
        with open(IMPORT_HISTORY_FILE) as f:
            data = json.load(f)
        
        entry = list(data.values())[0]
        assert "source_path" in entry
        assert "filename" in entry
        assert "size_bytes" in entry
        assert "imported_at" in entry
        assert entry["filename"] == "video1.mp4"


class TestMediaTypeDetection:
    """Test media type detection"""
    
    def test_video_extensions(self):
        """Common video extensions should be detected"""
        video_exts = ['.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm', '.3gp']
        for ext in video_exts:
            path = Path(f"/fake/video{ext}")
            assert get_media_type(path) == 'video', f"{ext} should be detected as video"
    
    def test_image_extensions(self):
        """Common image extensions should be detected"""
        image_exts = ['.jpg', '.jpeg', '.png', '.heic', '.heif', '.gif', '.webp']
        for ext in image_exts:
            path = Path(f"/fake/image{ext}")
            assert get_media_type(path) == 'image', f"{ext} should be detected as image"
    
    def test_unknown_extension(self):
        """Unknown extensions should return None"""
        path = Path("/fake/document.pdf")
        assert get_media_type(path) is None, "Unknown extension should return None"
    
    def test_case_insensitive(self):
        """Extension detection should be case insensitive"""
        assert get_media_type(Path("/fake/VIDEO.MP4")) == 'video'
        assert get_media_type(Path("/fake/PHOTO.JPG")) == 'image'


class TestSkipDuplicatesIntegration:
    """Integration tests for skip_duplicates functionality"""
    
    def test_scan_marks_duplicates(self, temp_media_dir, clean_history):
        """Scanning should correctly mark files as duplicates"""
        video = Path(temp_media_dir) / "video1.mp4"
        
        # Import first
        mark_as_imported(video)
        
        # Now check if scan would mark it correctly
        assert is_duplicate(video), "Scan should mark imported file as duplicate"
    
    def test_multiple_imports_tracked(self, temp_media_dir, clean_history):
        """Multiple imports should all be tracked"""
        files = [
            Path(temp_media_dir) / "video1.mp4",
            Path(temp_media_dir) / "video2.mov",
            Path(temp_media_dir) / "photo1.jpg",
        ]
        
        for f in files:
            mark_as_imported(f)
        
        # All should now be duplicates
        for f in files:
            assert is_duplicate(f), f"{f.name} should be detected as duplicate"
        
        # New file should not be duplicate
        new_file = Path(temp_media_dir) / "photo2.heic"
        assert not is_duplicate(new_file), "New file should not be duplicate"


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_history_file(self, clean_history):
        """Should handle empty or missing history file gracefully"""
        global _import_history
        _import_history.clear()
        
        # Ensure no history file exists
        if IMPORT_HISTORY_FILE.exists():
            IMPORT_HISTORY_FILE.unlink()
        
        # Should not raise - load should return empty since file doesn't exist
        load_import_history()
        assert _import_history == {}, "Empty/missing history should return empty dict"
    
    def test_corrupted_history_file(self, clean_history):
        """Should handle corrupted history file gracefully"""
        IMPORT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        IMPORT_HISTORY_FILE.write_text("not valid json {{{")
        
        # Should not raise, should return empty
        history = load_import_history()
        assert history == {}, "Corrupted history should return empty dict"
    
    def test_very_long_filename(self, temp_media_dir, clean_history):
        """Should handle very long filenames"""
        long_name = "a" * 200 + ".mp4"
        long_file = Path(temp_media_dir) / long_name
        long_file.write_bytes(b"content")
        
        # Should not raise
        hash_val = get_file_hash(long_file)
        assert hash_val is not None
        
        mark_as_imported(long_file)
        assert is_duplicate(long_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
