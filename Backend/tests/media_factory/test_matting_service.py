"""
Matting Service Tests
=====================
Tests for video matting service functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from services.matting.models import MattingRequest, MattingResponse
from services.matting.adapters.rvm import RVMAdapter
from services.matting.adapters.mediapipe import MediaPipeAdapter
from services.matting.worker import MattingWorker


class TestMattingModels:
    """Test matting data models."""
    
    def test_matting_request_creation(self):
        """Test MattingRequest model creation."""
        request = MattingRequest(
            video_path="/path/to/video.mp4",
            model="rvm"
        )
        assert request.video_path == "/path/to/video.mp4"
        assert request.model == "rvm"
        assert request.object_of_interest == "person"
        assert request.job_id is not None
        assert request.correlation_id is not None


class TestRVMAdapter:
    """Test RVM adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create RVM adapter."""
        return RVMAdapter()
    
    def test_get_model_name(self, adapter):
        """Test model name."""
        assert adapter.get_model_name() == "rvm"
    
    @pytest.mark.asyncio
    async def test_apply_matting_mock(self, adapter):
        """Test matting with mocked ffmpeg."""
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            
            # Mock ffprobe for duration
            with patch('subprocess.check_output') as mock_check:
                mock_check.return_value = b"10.5"
                
                output_path = Path("/tmp/test_output.mov")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Create dummy input file
                input_path = Path("/tmp/test_input.mp4")
                input_path.parent.mkdir(parents=True, exist_ok=True)
                input_path.touch()
                
                result = await adapter.apply_matting(
                    video_path=input_path,
                    output_file_path=output_path,
                    object_of_interest="person"
                )
                
                assert result["output_path"] == str(output_path)
                assert result["model_used"] == "rvm"


class TestMediaPipeAdapter:
    """Test MediaPipe adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create MediaPipe adapter."""
        return MediaPipeAdapter()
    
    def test_get_model_name(self, adapter):
        """Test model name."""
        assert adapter.get_model_name() == "mediapipe"
    
    @pytest.mark.skip(reason="Requires MediaPipe and OpenCV - integration test")
    @pytest.mark.asyncio
    async def test_apply_matting(self, adapter):
        """Test MediaPipe matting (integration test)."""
        # This would require actual video file and MediaPipe installation
        pass


class TestMattingWorker:
    """Test matting worker."""
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        bus = Mock()
        bus.publish = AsyncMock()
        bus.subscribe = AsyncMock()
        return bus
    
    @pytest.fixture
    def worker(self, event_bus):
        """Create matting worker."""
        return MattingWorker(event_bus)
    
    def test_get_subscriptions(self, worker):
        """Test worker subscriptions."""
        from services.event_bus import Topics
        subscriptions = worker.get_subscriptions()
        assert Topics.MATTING_REQUESTED in subscriptions

