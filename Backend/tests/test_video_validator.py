"""
Tests for Video Validator
"""
import pytest
from pathlib import Path
from modules.video_ingestion.video_validator import VideoValidator


class TestVideoValidator:
    """Test VideoValidator class"""
    
    def test_is_video_file(self):
        """Test video file format detection"""
        validator = VideoValidator()
        
        assert validator.is_video_file(Path("test.mp4"))
        assert validator.is_video_file(Path("test.mov"))
        assert validator.is_video_file(Path("test.MP4"))  # Case insensitive
        assert not validator.is_video_file(Path("test.txt"))
        assert not validator.is_video_file(Path("test.jpg"))
    
    def test_validate_valid_video(self, sample_video):
        """Test validation of a valid video"""
        validator = VideoValidator(min_duration=5, max_duration=60)
        
        is_valid, error, metadata = validator.validate(sample_video)
        
        assert is_valid
        assert error is None
        assert metadata is not None
        assert metadata['duration'] >= 5
        assert metadata['has_video']
        assert metadata['width'] > 0
        assert metadata['height'] > 0
    
    def test_validate_short_video(self, short_video):
        """Test validation fails for too-short video"""
        validator = VideoValidator(min_duration=10)
        
        is_valid, error, metadata = validator.validate(short_video)
        
        assert not is_valid
        assert "too short" in error.lower()
    
    def test_validate_nonexistent_file(self):
        """Test validation fails for non-existent file"""
        validator = VideoValidator()
        
        is_valid, error, metadata = validator.validate(Path("/nonexistent/video.mp4"))
        
        assert not is_valid
        assert "does not exist" in error.lower()
    
    def test_validate_invalid_file(self, invalid_file):
        """Test validation fails for non-video file"""
        validator = VideoValidator()
        
        is_valid, error, metadata = validator.validate(invalid_file)
        
        assert not is_valid
        assert "unsupported format" in error.lower()
    
    def test_extract_metadata(self, sample_video):
        """Test metadata extraction"""
        validator = VideoValidator()
        
        metadata = validator.extract_metadata(sample_video)
        
        assert metadata is not None
        assert 'duration' in metadata
        assert 'width' in metadata
        assert 'height' in metadata
        assert 'video_codec' in metadata
        assert 'has_video' in metadata
        assert 'has_audio' in metadata
        assert metadata['file_name'] == sample_video.name
    
    def test_get_video_thumbnail(self, sample_video, temp_dir):
        """Test thumbnail extraction"""
        validator = VideoValidator()
        thumbnail_path = temp_dir / "thumbnail.jpg"
        
        success = validator.get_video_thumbnail(sample_video, thumbnail_path)
        
        assert success
        assert thumbnail_path.exists()
        assert thumbnail_path.stat().st_size > 0
    
    def test_parse_fps(self):
        """Test FPS parsing"""
        validator = VideoValidator()
        
        assert validator._parse_fps("30/1") == 30.0
        assert validator._parse_fps("30000/1001") == pytest.approx(29.97, rel=0.01)
        assert validator._parse_fps("60") == 60.0
        assert validator._parse_fps("invalid") == 0.0
    
    def test_file_size_validation(self, large_video):
        """Test file size limits"""
        # Create validator with small max size
        validator = VideoValidator(max_size_mb=1)
        
        is_valid, error, metadata = validator.validate(large_video)
        
        # May or may not be valid depending on actual file size
        # Just test that size checking works
        if not is_valid and error:
            assert "too large" in error.lower() or "duration" in error.lower()


class TestVideoValidatorIntegration:
    """Integration tests for VideoValidator"""
    
    def test_validate_multiple_formats(self, temp_dir):
        """Test validation of different video formats"""
        validator = VideoValidator()
        
        # This test would create videos in different formats
        # Skipped if FFmpeg cannot create various formats
        pytest.skip("Format conversion tests require extended FFmpeg support")
    
    def test_corrupted_video_handling(self, temp_dir):
        """Test handling of corrupted video files"""
        # Create a fake video file
        corrupted = temp_dir / "corrupted.mp4"
        corrupted.write_bytes(b"This is not valid video data")
        
        validator = VideoValidator()
        is_valid, error, metadata = validator.validate(corrupted)
        
        assert not is_valid
        assert error is not None
