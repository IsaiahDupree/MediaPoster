"""
Tests for Content Intelligence Phase 2: Visual Analysis
Tests frame sampling, vision analysis, and video analysis orchestration
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, AnalyzedVideo, VideoFrame
from services.frame_sampler import FrameSamplerService
from services.vision_analyzer import VisionAnalyzer
from services.video_analysis import VideoAnalysisService


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestFrameSamplerService:
    """Test frame sampling service"""
    
    def test_initialization(self, temp_dir):
        """Test service initialization"""
        sampler = FrameSamplerService(output_dir=temp_dir)
        
        assert sampler.output_dir == Path(temp_dir)
        assert sampler.output_dir.exists()
    
    @patch('subprocess.run')
    def test_check_ffmpeg_installed(self, mock_run):
        """Test FFmpeg detection"""
        mock_run.return_value = Mock(returncode=0)
        sampler = FrameSamplerService()
        
        assert sampler.check_ffmpeg_installed() is True
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_get_video_duration(self, mock_run, temp_dir):
        """Test video duration extraction"""
        mock_run.return_value = Mock(returncode=0, stdout="120.5\n")
        sampler = FrameSamplerService(output_dir=temp_dir)
        
        duration = sampler.get_video_duration("/fake/video.mp4")
        
        assert duration == 120.5
    
    @patch('subprocess.run')
    def test_extract_frame_at_time(self, mock_run, temp_dir):
        """Test single frame extraction"""
        mock_run.return_value = Mock(returncode=0)
        sampler = FrameSamplerService(output_dir=temp_dir)
        
        # Create fake output file to simulate FFmpeg success
        output_path = Path(temp_dir) / "test_frame.jpg"
        output_path.touch()
        
        with patch.object(Path, 'exists', return_value=True):
            result = sampler.extract_frame_at_time(
                "/fake/video.mp4",
                time_s=1.5,
                output_filename="test_frame"
            )
        
        assert result is not None
        assert "test_frame.jpg" in result
    
    @patch.object(FrameSamplerService, 'get_video_duration')
    @patch.object(FrameSamplerService, 'extract_frame_at_time')
    def test_sample_frames_uniform(self, mock_extract, mock_duration, temp_dir):
        """Test uniform frame sampling"""
        mock_duration.return_value = 10.0  # 10 second video
        mock_extract.return_value = "/fake/frame.jpg"
        
        sampler = FrameSamplerService(output_dir=temp_dir)
        frames = sampler.sample_frames_uniform(
            video_path="/fake/video.mp4",
            interval_s=2.0,
            video_id="test123"
        )
        
        # Should sample at 0, 2, 4, 6, 8, 10 seconds
        assert len(frames) == 6
        assert frames[0]["time_s"] == 0.0
        assert frames[-1]["time_s"] == 10.0
    
    @patch.object(FrameSamplerService, 'extract_frame_at_time')
    def test_sample_frames_at_times(self, mock_extract, temp_dir):
        """Test sampling at specific timestamps"""
        mock_extract.return_value = "/fake/frame.jpg"
        
        sampler = FrameSamplerService(output_dir=temp_dir)
        timestamps = [0.5, 2.3, 5.7, 8.1]
        
        frames = sampler.sample_frames_at_times(
            video_path="/fake/video.mp4",
            timestamps=timestamps,
            video_id="test456"
        )
        
        assert len(frames) == 4
        assert frames[0]["time_s"] == 0.5
        assert frames[2]["time_s"] == 5.7
    
    def test_cleanup_frames(self, temp_dir):
        """Test frame cleanup"""
        sampler = FrameSamplerService(output_dir=temp_dir)
        
        # Create fake frames
        for i in range(3):
            frame_file = Path(temp_dir) / f"video123_frame_{i:04d}.jpg"
            frame_file.touch()
        
        # Cleanup specific video
        sampler.cleanup_frames(video_id="video123")
        
        # Verify cleanup
        remaining_files = list(Path(temp_dir).glob("*.jpg"))
        assert len(remaining_files) == 0


class TestVisionAnalyzer:
    """Test vision analysis service"""
    
    def test_initialization_without_api_key(self):
        """Test initialization without API key"""
        analyzer = VisionAnalyzer(api_key=None)
        
        assert analyzer.is_enabled() is False
    
    def test_initialization_with_api_key(self):
        """Test initialization with API key"""
        analyzer = VisionAnalyzer(api_key="fake-key-123")
        
        assert analyzer.client is not None
    
    def test_encode_image(self, temp_dir):
        """Test image encoding to base64"""
        # Create a small test image
        test_image = Path(temp_dir) / "test.jpg"
        test_image.write_bytes(b"fake image data")
        
        analyzer = VisionAnalyzer(api_key="fake-key")
        encoded = analyzer.encode_image(str(test_image))
        
        assert isinstance(encoded, str)
        assert len(encoded) > 0
    
    @patch('openai.OpenAI')
    def test_analyze_frame_comprehensive(self, mock_openai_class, temp_dir):
        """Test comprehensive frame analysis"""
        # Create test image
        test_image = Path(temp_dir) / "frame.jpg"
        test_image.write_bytes(b"fake image")
        
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"shot_type": "close_up", "has_face": true}'))]
        mock_response.model = "gpt-4-vision"
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        analyzer = VisionAnalyzer(api_key="fake-key")
        analyzer.client = mock_client
        
        result = analyzer.analyze_frame(str(test_image), analysis_type="comprehensive")
        
        assert "shot_type" in result
        assert result["shot_type"] == "close_up"
    
    @patch('openai.OpenAI')
    def test_detect_pattern_interrupt(self, mock_openai_class, temp_dir):
        """Test pattern interrupt detection"""
        # Create test images
        frame1 = Path(temp_dir) / "frame1.jpg"
        frame2 = Path(temp_dir) / "frame2.jpg"
        frame1.write_bytes(b"image1")
        frame2.write_bytes(b"image2")
        
        # Mock response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(
            content='{"has_pattern_interrupt": true, "interrupt_type": "zoom", "interrupt_strength": 0.8}'
        ))]
        mock_client.chat.completions.create.return_value = mock_response
        
        analyzer = VisionAnalyzer(api_key="fake-key")
        analyzer.client = mock_client
        
        result = analyzer.detect_pattern_interrupt(str(frame1), str(frame2))
        
        assert result["has_pattern_interrupt"] is True
        assert result["interrupt_type"] == "zoom"


class TestVideoAnalysisService:
    """Test video analysis orchestrator"""
    
    def test_initialization(self, db_session, temp_dir):
        """Test service initialization"""
        service = VideoAnalysisService(
            db=db_session,
            frame_output_dir=temp_dir,
            openai_api_key="fake-key"
        )
        
        assert service.frame_sampler is not None
        assert service.vision_analyzer is not None
    
    def test_is_ready(self, db_session, temp_dir):
        """Test readiness check"""
        with patch.object(FrameSamplerService, 'check_ffmpeg_installed', return_value=True):
            service = VideoAnalysisService(db=db_session, frame_output_dir=temp_dir, openai_api_key="key")
            
            readiness = service.is_ready()
            
            assert "ffmpeg_installed" in readiness
            assert "vision_api_enabled" in readiness
    
    @patch.object(FrameSamplerService, 'check_ffmpeg_installed', return_value=True)
    @patch.object(FrameSamplerService, 'sample_frames_uniform')
    @patch.object(VisionAnalyzer, 'analyze_frame')
    def test_analyze_video_frames(self, mock_analyze, mock_sample, mock_ffmpeg, db_session, temp_dir):
        """Test full video frame analysis workflow"""
        # Setup mocks
        mock_sample.return_value = [
            {"time_s": 0.0, "frame_path": "/tmp/frame_0.jpg", "frame_index": 0},
            {"time_s": 1.0, "frame_path": "/tmp/frame_1.jpg", "frame_index": 1}
        ]
        
        mock_analyze.return_value = {
            "shot_type": "close_up",
            "presence": ["face"],
            "is_hook_frame": True,
            "visual_clutter_score": 0.2
        }
        
        # Create test video record
        video = AnalyzedVideo(duration_seconds=10.0)
        db_session.add(video)
        db_session.commit()
        
        # Run analysis
        service = VideoAnalysisService(db=db_session, frame_output_dir=temp_dir, openai_api_key="key")
        result = service.analyze_video_frames(
            video_path="/fake/video.mp4",
            video_id=video.id,
            sampling_interval_s=1.0,
            store_in_db=True
        )
        
        assert result["success"] is True
        assert result["frames_extracted"] == 2
        assert result["frames_analyzed"] == 2
        
        # Verify database storage
        stored_frames = db_session.query(VideoFrame).filter_by(video_id=video.id).all()
        assert len(stored_frames) == 2
    
    @patch.object(FrameSamplerService, 'sample_frames_at_times')
    @patch.object(VisionAnalyzer, 'analyze_frame')
    def test_analyze_hook_frames(self, mock_analyze, mock_sample, db_session, temp_dir):
        """Test specialized hook frame analysis"""
        mock_sample.return_value = [
            {"time_s": 0.0, "frame_path": "/tmp/hook_0.jpg"},
            {"time_s": 0.5, "frame_path": "/tmp/hook_1.jpg"}
        ]
        
        mock_analyze.return_value = {
            "is_hook_frame": True,
            "hook_score": 0.85,
            "reasons": ["direct eye contact", "bold text"],
            "suggestions": ["Add more color contrast"]
        }
        
        video = AnalyzedVideo(duration_seconds=10.0)
        db_session.add(video)
        db_session.commit()
        
        service = VideoAnalysisService(db=db_session, frame_output_dir=temp_dir, openai_api_key="key")
        result = service.analyze_hook_frames(
            video_path="/fake/video.mp4",
            video_id=video.id,
            hook_segment_end_s=5.0
        )
        
        assert result["success"] is True
        assert result["best_hook_score"] == 0.85
        assert "direct eye contact" in result["all_hook_data"][0]["reasons"]
    
    def test_store_frame_analyses(self, db_session, temp_dir):
        """Test storing frame analyses in database"""
        video = AnalyzedVideo(duration_seconds=10.0)
        db_session.add(video)
        db_session.commit()
        
        frame_analyses = [
            {
                "time_s": 1.0,
                "frame_path": "/tmp/frame1.jpg",
                "analysis": {
                    "shot_type": "medium",
                    "presence": ["face", "laptop"],
                    "text_on_screen": "Hello World",
                    "visual_clutter_score": 0.5,
                    "is_hook_frame": False
                }
            },
            {
                "time_s": 2.0,
                "frame_path": "/tmp/frame2.jpg",
                "analysis": {
                    "shot_type": "close_up",
                    "presence": ["face"],
                    "is_hook_frame": True,
                    "visual_clutter_score": 0.2
                }
            }
        ]
        
        service = VideoAnalysisService(db=db_session, frame_output_dir=temp_dir)
        count = service._store_frame_analyses(video.id, frame_analyses)
        
        assert count == 2
        
        # Verify stored frames
        frames = db_session.query(VideoFrame).filter_by(video_id=video.id).all()
        assert len(frames) == 2
        assert frames[0].shot_type == "medium"
        assert frames[1].is_hook_frame is True
