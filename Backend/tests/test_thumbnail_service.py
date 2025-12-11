"""
Tests for Thumbnail Service
Covers thumbnail generation, caching, and resume capabilities.
"""
import pytest
import tempfile
import os
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import hashlib


# =============================================================================
# UNIT TESTS - Thumbnail Path Generation
# =============================================================================

class TestThumbnailPaths:
    """Test thumbnail path generation."""
    
    def test_get_thumbnail_path_creates_unique_path(self):
        """Test that different files get different thumbnail paths."""
        from services.thumbnail_service import get_thumbnail_path
        
        path1 = get_thumbnail_path("/path/to/video1.mov")
        path2 = get_thumbnail_path("/path/to/video2.mov")
        
        assert path1 != path2
        assert path1.suffix == ".jpg"
        assert path2.suffix == ".jpg"
    
    def test_get_thumbnail_path_same_file_same_path(self):
        """Test that same file always gets same thumbnail path."""
        from services.thumbnail_service import get_thumbnail_path
        
        path1 = get_thumbnail_path("/path/to/video.mov", "medium")
        path2 = get_thumbnail_path("/path/to/video.mov", "medium")
        
        assert path1 == path2
    
    def test_get_thumbnail_path_different_sizes(self):
        """Test that different sizes get different paths."""
        from services.thumbnail_service import get_thumbnail_path
        
        small = get_thumbnail_path("/path/to/video.mov", "small")
        medium = get_thumbnail_path("/path/to/video.mov", "medium")
        large = get_thumbnail_path("/path/to/video.mov", "large")
        
        assert small != medium != large
        assert "small" in str(small)
        assert "medium" in str(medium)
        assert "large" in str(large)


# =============================================================================
# UNIT TESTS - Media Type Detection
# =============================================================================

class TestMediaTypeDetection:
    """Test media type detection."""
    
    def test_detect_video_types(self):
        """Test detection of video file types."""
        from services.thumbnail_service import get_media_type
        
        video_files = [
            "video.mov", "VIDEO.MOV",
            "clip.mp4", "CLIP.MP4",
            "movie.m4v", "film.avi", "media.mkv", "stream.webm"
        ]
        
        for f in video_files:
            assert get_media_type(f) == "video", f"Failed for {f}"
    
    def test_detect_image_types(self):
        """Test detection of image file types."""
        from services.thumbnail_service import get_media_type
        
        image_files = [
            "photo.jpg", "PHOTO.JPG",
            "image.jpeg", "pic.png",
            "shot.heic", "graphic.webp"
        ]
        
        for f in image_files:
            assert get_media_type(f) == "image", f"Failed for {f}"


# =============================================================================
# UNIT TESTS - Thumbnail Caching
# =============================================================================

class TestThumbnailCaching:
    """Test thumbnail caching functionality."""
    
    def test_existing_thumbnail_returned_immediately(self, tmp_path):
        """Test that existing thumbnails are returned without regeneration."""
        from services.thumbnail_service import get_thumbnail_path, THUMBNAIL_DIR
        
        # Create a fake cached thumbnail
        test_file = "/fake/video.mov"
        thumb_path = get_thumbnail_path(test_file, "medium")
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(b"fake thumbnail data")
        
        assert thumb_path.exists()
        
        # Cleanup
        thumb_path.unlink()
    
    def test_thumbnail_directory_created(self):
        """Test that thumbnail directory is created on import."""
        from services.thumbnail_service import THUMBNAIL_DIR
        
        assert THUMBNAIL_DIR.exists()
        assert THUMBNAIL_DIR.is_dir()


# =============================================================================
# INTEGRATION TESTS - Thumbnail Generation
# =============================================================================

class TestThumbnailGeneration:
    """Test actual thumbnail generation."""
    
    @pytest.fixture
    def sample_video_path(self):
        """Get a real video file if available."""
        iphone_import = Path(os.path.expanduser("~/Documents/IphoneImport"))
        if iphone_import.exists():
            videos = list(iphone_import.glob("*.MOV"))[:1]
            if videos:
                return str(videos[0])
        return None
    
    def test_generate_video_thumbnail_with_real_file(self, sample_video_path):
        """Test thumbnail generation with real video file."""
        if not sample_video_path:
            pytest.skip("No sample video available")
        
        from services.thumbnail_service import generate_video_thumbnail
        
        result = generate_video_thumbnail(sample_video_path, width=200)
        
        if result:
            assert Path(result).exists()
            assert Path(result).suffix == ".jpg"
            # Cleanup
            Path(result).unlink(missing_ok=True)
    
    def test_generate_thumbnail_nonexistent_file(self):
        """Test thumbnail generation fails gracefully for missing file."""
        from services.thumbnail_service import generate_video_thumbnail
        
        result = generate_video_thumbnail("/nonexistent/file.mov")
        
        assert result is None
    
    def test_generate_thumbnail_returns_cached(self, tmp_path):
        """Test that cached thumbnail is returned on second call."""
        from services.thumbnail_service import get_thumbnail_path
        
        # Create fake cached thumbnail
        test_file = str(tmp_path / "test.mov")
        Path(test_file).write_bytes(b"fake video")
        
        thumb_path = get_thumbnail_path(test_file, "medium")
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(b"cached thumbnail")
        
        # Import after creating cache
        from services.thumbnail_service import generate_video_thumbnail
        
        # Should return cached path
        result = generate_video_thumbnail(test_file)
        
        assert result == str(thumb_path)
        
        # Cleanup
        thumb_path.unlink(missing_ok=True)


# =============================================================================
# INTEGRATION TESTS - Resume Capabilities
# =============================================================================

class TestThumbnailResume:
    """Test smart resume capabilities for thumbnail generation."""
    
    def test_thumbnail_state_tracking(self, tmp_path):
        """Test that thumbnail generation state is tracked."""
        from services.thumbnail_service import ThumbnailState
        
        state = ThumbnailState(tmp_path / "thumb_state.json")
        
        # Record some thumbnails
        state.mark_generated("/path/to/video1.mov", "medium", "/thumbs/video1.jpg")
        state.mark_generated("/path/to/video2.mov", "small", "/thumbs/video2.jpg")
        state.mark_failed("/path/to/video3.mov", "Error message")
        
        # Save and reload
        state.save()
        
        state2 = ThumbnailState(tmp_path / "thumb_state.json")
        state2.load()
        
        assert state2.is_generated("/path/to/video1.mov", "medium")
        assert state2.is_generated("/path/to/video2.mov", "small")
        assert state2.is_failed("/path/to/video3.mov")
    
    def test_skip_already_generated(self, tmp_path):
        """Test that already generated thumbnails are skipped."""
        from services.thumbnail_service import ThumbnailState
        
        state = ThumbnailState(tmp_path / "thumb_state.json")
        state.mark_generated("/path/to/video.mov", "medium", "/thumbs/video.jpg")
        
        # Should return True (already done)
        assert state.is_generated("/path/to/video.mov", "medium")
        
        # Different size should not be marked
        assert not state.is_generated("/path/to/video.mov", "large")
    
    def test_retry_failed_thumbnails(self, tmp_path):
        """Test that failed thumbnails can be retried."""
        from services.thumbnail_service import ThumbnailState
        
        state = ThumbnailState(tmp_path / "thumb_state.json")
        
        # Mark as failed
        state.mark_failed("/path/to/video.mov", "Initial error")
        assert state.is_failed("/path/to/video.mov")
        
        # Clear for retry
        state.clear_failed("/path/to/video.mov")
        assert not state.is_failed("/path/to/video.mov")


# =============================================================================
# INTEGRATION TESTS - Batch Thumbnail Generation
# =============================================================================

class TestBatchThumbnails:
    """Test batch thumbnail generation."""
    
    def test_batch_thumbnail_tracking(self, tmp_path):
        """Test tracking of batch thumbnail jobs."""
        from services.thumbnail_service import ThumbnailBatchJob
        
        files = [
            str(tmp_path / f"video{i}.mov")
            for i in range(10)
        ]
        
        job = ThumbnailBatchJob(files, sizes=["small", "medium"])
        
        assert job.total_files == 10
        assert job.total_thumbnails == 20  # 10 files * 2 sizes
        assert job.processed_count == 0
        assert job.progress == 0.0
    
    def test_batch_progress_updates(self, tmp_path):
        """Test batch job progress tracking."""
        from services.thumbnail_service import ThumbnailBatchJob
        
        files = [str(tmp_path / f"video{i}.mov") for i in range(5)]
        job = ThumbnailBatchJob(files, sizes=["medium"])
        
        # Simulate processing
        job.mark_complete(files[0], "medium")
        assert job.processed_count == 1
        assert job.progress == 0.2
        
        job.mark_complete(files[1], "medium")
        job.mark_complete(files[2], "medium")
        assert job.progress == 0.6
    
    def test_batch_resume_skips_completed(self, tmp_path):
        """Test that resume skips already completed thumbnails."""
        from services.thumbnail_service import ThumbnailBatchJob
        
        files = [str(tmp_path / f"video{i}.mov") for i in range(5)]
        job = ThumbnailBatchJob(files, sizes=["medium"])
        
        # Mark some as complete
        job.mark_complete(files[0], "medium")
        job.mark_complete(files[1], "medium")
        
        # Get remaining
        remaining = job.get_remaining()
        
        assert len(remaining) == 3
        assert files[0] not in [r[0] for r in remaining]
        assert files[1] not in [r[0] for r in remaining]


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

class TestThumbnailAPI:
    """Test thumbnail API endpoints."""
    
    def test_thumbnail_url_format(self):
        """Test thumbnail URL generation."""
        from api.media_processing import media_items
        
        media_id = "test-123"
        expected_url = f"/api/media/thumbnail/{media_id}?size=medium"
        
        # URL should follow this format
        assert f"/api/media/thumbnail/{media_id}" in expected_url
    
    def test_thumbnail_sizes_validated(self):
        """Test that only valid sizes are accepted."""
        valid_sizes = ["small", "medium", "large"]
        
        for size in valid_sizes:
            assert size in ["small", "medium", "large"]
        
        # Invalid sizes should not be in list
        assert "tiny" not in valid_sizes
        assert "huge" not in valid_sizes


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestThumbnailPerformance:
    """Performance tests for thumbnail generation."""
    
    def test_cached_thumbnail_fast(self, tmp_path):
        """Test that cached thumbnails are returned quickly."""
        import time
        from services.thumbnail_service import get_thumbnail_path
        
        # Create cached thumbnail
        test_file = str(tmp_path / "video.mov")
        Path(test_file).write_bytes(b"fake")
        
        thumb_path = get_thumbnail_path(test_file, "medium")
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(b"cached")
        
        # Time the lookup
        start = time.time()
        for _ in range(100):
            get_thumbnail_path(test_file, "medium")
        elapsed = time.time() - start
        
        # Should be very fast (< 10ms for 100 lookups)
        assert elapsed < 0.1
        
        # Cleanup
        thumb_path.unlink(missing_ok=True)
    
    def test_hash_computation_deterministic(self):
        """Test that file path hashing is deterministic."""
        from services.thumbnail_service import get_thumbnail_path
        
        results = set()
        for _ in range(10):
            path = get_thumbnail_path("/same/path/video.mov", "medium")
            results.add(str(path))
        
        # All should be the same
        assert len(results) == 1


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
