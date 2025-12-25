"""
Unit Tests for Video Analyzer Service
Tests video orientation detection and metadata extraction
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.video.video_analyzer import VideoAnalyzer, Orientation, VideoMetadata


class TestVideoAnalyzer:
    """Test suite for video analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        with patch('services.video.video_analyzer.subprocess.run'):
            return VideoAnalyzer()
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initializes correctly"""
        assert analyzer is not None
    
    def test_detect_vertical_orientation(self, analyzer):
        """Test vertical video detection (9:16)"""
        # 1080x1920 = 0.5625 aspect ratio
        orientation = analyzer.detect_orientation(1080, 1920)
        assert orientation == Orientation.VERTICAL
    
    def test_detect_horizontal_orientation(self, analyzer):
        """Test horizontal video detection (16:9)"""
        # 1920x1080 = 1.7778 aspect ratio
        orientation = analyzer.detect_orientation(1920, 1080)
        assert orientation == Orientation.HORIZONTAL
    
    def test_detect_square_orientation(self, analyzer):
        """Test square video detection (1:1)"""
        # 1080x1080 = 1.0 aspect ratio
        orientation = analyzer.detect_orientation(1080, 1080)
        assert orientation == Orientation.SQUARE
    
    def test_detect_vertical_edge_case(self, analyzer):
        """Test vertical detection at boundary (aspect < 0.75)"""
        # 720x1000 = 0.72 aspect ratio (just below 0.75)
        orientation = analyzer.detect_orientation(720, 1000)
        assert orientation == Orientation.VERTICAL
    
    def test_detect_horizontal_edge_case(self, analyzer):
        """Test horizontal detection at boundary (aspect > 1.33)"""
        # 1400x1000 = 1.4 aspect ratio (just above 1.33)
        orientation = analyzer.detect_orientation(1400, 1000)
        assert orientation == Orientation.HORIZONTAL
    
    def test_detect_square_lower_boundary(self, analyzer):
        """Test square detection at lower boundary"""
        # 800x1000 = 0.8 aspect ratio (between 0.75 and 1.33)
        orientation = analyzer.detect_orientation(800, 1000)
        assert orientation == Orientation.SQUARE
    
    def test_detect_square_upper_boundary(self, analyzer):
        """Test square detection at upper boundary"""
        # 1300x1000 = 1.3 aspect ratio (between 0.75 and 1.33)
        orientation = analyzer.detect_orientation(1300, 1000)
        assert orientation == Orientation.SQUARE
    
    def test_detect_orientation_zero_height(self, analyzer):
        """Test orientation with zero height"""
        orientation = analyzer.detect_orientation(1920, 0)
        assert orientation == Orientation.SQUARE  # Fallback
    
    def test_parse_fps_fraction(self, analyzer):
        """Test FPS parsing from fraction format"""
        fps = analyzer._parse_fps("30/1")
        assert fps == 30.0
    
    def test_parse_fps_ntsc(self, analyzer):
        """Test FPS parsing for NTSC format"""
        fps = analyzer._parse_fps("30000/1001")
        assert 29.97 <= fps <= 29.98
    
    def test_parse_fps_direct(self, analyzer):
        """Test FPS parsing from direct number"""
        fps = analyzer._parse_fps("60")
        assert fps == 60.0
    
    def test_parse_fps_invalid(self, analyzer):
        """Test FPS parsing with invalid input"""
        fps = analyzer._parse_fps("invalid")
        assert fps == 0.0
    
    @patch('services.video.video_analyzer.subprocess.run')
    def test_extract_metadata_success(self, mock_run, analyzer):
        """Test successful metadata extraction"""
        mock_metadata = {
            "format": {
                "duration": "125.5",
                "size": "45678901"
            },
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "codec_name": "h264",
                    "bit_rate": "2500000",
                    "r_frame_rate": "30/1"
                }
            ]
        }
        
        mock_run.return_value = Mock(
            stdout=json.dumps(mock_metadata),
            returncode=0
        )
        
        metadata = analyzer._extract_metadata("test.mp4")
        assert metadata["format"]["duration"] == "125.5"
        assert metadata["streams"][0]["width"] == 1920
    
    @patch('services.video.video_analyzer.subprocess.run')
    def test_extract_metadata_failure(self, mock_run, analyzer):
        """Test metadata extraction failure"""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'ffprobe', stderr="Error")
        
        with pytest.raises(RuntimeError):
            analyzer._extract_metadata("test.mp4")
    
    def test_get_video_stream_success(self, analyzer):
        """Test extracting video stream from metadata"""
        metadata = {
            "streams": [
                {"codec_type": "audio"},
                {"codec_type": "video", "width": 1920, "height": 1080}
            ]
        }
        
        stream = analyzer._get_video_stream(metadata)
        assert stream["codec_type"] == "video"
        assert stream["width"] == 1920
    
    def test_get_video_stream_not_found(self, analyzer):
        """Test error when no video stream found"""
        metadata = {
            "streams": [
                {"codec_type": "audio"}
            ]
        }
        
        with pytest.raises(RuntimeError, match="No video stream found"):
            analyzer._get_video_stream(metadata)
    
    @patch('services.video.video_analyzer.subprocess.run')
    @patch('os.path.exists')
    def test_analyze_video_complete(self, mock_exists, mock_run, analyzer):
        """Test complete video analysis workflow"""
        mock_exists.return_value = True
        
        mock_metadata = {
            "format": {
                "duration": "125.5",
                "size": "45678901"
            },
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "codec_name": "h264",
                    "bit_rate": "2500000",
                    "r_frame_rate": "30/1"
                }
            ]
        }
        
        mock_run.return_value = Mock(
            stdout=json.dumps(mock_metadata),
            returncode=0
        )
        
        result = analyzer.analyze_video("test.mp4")
        
        assert result.orientation == Orientation.HORIZONTAL
        assert result.width == 1920
        assert result.height == 1080
        assert result.duration_seconds == 125.5
        assert result.codec == "h264"
        assert result.fps == 30.0
    
    @patch('os.path.exists')
    def test_analyze_video_file_not_found(self, mock_exists, analyzer):
        """Test analysis with non-existent file"""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_video("nonexistent.mp4")
    
    @patch('services.video.video_analyzer.subprocess.run')
    def test_get_duration(self, mock_run, analyzer):
        """Test duration extraction"""
        mock_run.return_value = Mock(
            stdout="125.5\n",
            returncode=0
        )
        
        duration = analyzer.get_duration("test.mp4")
        assert duration == 125.5
    
    @patch('services.video.video_analyzer.subprocess.run')
    def test_get_duration_failure(self, mock_run, analyzer):
        """Test duration extraction failure"""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'ffprobe', stderr="Error")
        
        duration = analyzer.get_duration("test.mp4")
        assert duration == 0.0
    
    @patch('services.video.video_analyzer.subprocess.run')
    def test_get_dimensions(self, mock_run, analyzer):
        """Test dimension extraction"""
        mock_run.return_value = Mock(
            stdout="1920x1080\n",
            returncode=0
        )
        
        width, height = analyzer.get_dimensions("test.mp4")
        assert width == 1920
        assert height == 1080
    
    @patch('services.video.video_analyzer.subprocess.run')
    def test_get_dimensions_failure(self, mock_run, analyzer):
        """Test dimension extraction failure"""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'ffprobe', stderr="Error")
        
        width, height = analyzer.get_dimensions("test.mp4")
        assert width == 0
        assert height == 0
    
    def test_common_resolutions_vertical(self, analyzer):
        """Test common vertical resolutions"""
        # iPhone vertical
        assert analyzer.detect_orientation(1080, 1920) == Orientation.VERTICAL
        # 4K vertical
        assert analyzer.detect_orientation(2160, 3840) == Orientation.VERTICAL
        # 720p vertical
        assert analyzer.detect_orientation(720, 1280) == Orientation.VERTICAL
    
    def test_common_resolutions_horizontal(self, analyzer):
        """Test common horizontal resolutions"""
        # 1080p
        assert analyzer.detect_orientation(1920, 1080) == Orientation.HORIZONTAL
        # 4K
        assert analyzer.detect_orientation(3840, 2160) == Orientation.HORIZONTAL
        # 720p
        assert analyzer.detect_orientation(1280, 720) == Orientation.HORIZONTAL
    
    def test_common_resolutions_square(self, analyzer):
        """Test common square resolutions"""
        # Instagram square
        assert analyzer.detect_orientation(1080, 1080) == Orientation.SQUARE
        # 720p square
        assert analyzer.detect_orientation(720, 720) == Orientation.SQUARE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
