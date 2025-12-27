"""
Remotion Service Tests
======================
Tests for Remotion service functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from services.remotion.models import RemotionRequest, RemotionResponse, Layer, AudioTrack, SourceType
from services.remotion.composer import RemotionComposer
from services.remotion.source_loader import SourceLoader
from services.remotion.worker import RemotionWorker


class TestRemotionModels:
    """Test Remotion data models."""
    
    def test_remotion_request_creation(self):
        """Test RemotionRequest model creation."""
        request = RemotionRequest(
            composition="MainComposition"
        )
        assert request.composition == "MainComposition"
        assert request.job_id is not None
        assert request.correlation_id is not None
    
    def test_layer_creation(self):
        """Test Layer model."""
        layer = Layer(
            id="layer_001",
            type="video",
            source="/path/to/video.mp4",
            source_type=SourceType.LOCAL
        )
        assert layer.id == "layer_001"
        assert layer.type == "video"
        assert layer.source_type == SourceType.LOCAL


class TestSourceLoader:
    """Test source loader."""
    
    @pytest.fixture
    def loader(self):
        """Create source loader."""
        return SourceLoader()
    
    @pytest.mark.asyncio
    async def test_load_local_source(self, loader):
        """Test loading local source."""
        # Create test file
        test_file = Path("/tmp/test_source.txt")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test content")
        
        result = await loader.load_source(
            source=str(test_file),
            source_type=SourceType.LOCAL
        )
        
        assert result == str(test_file.absolute())
        test_file.unlink()
    
    @pytest.mark.asyncio
    async def test_load_url_source(self, loader):
        """Test loading URL source."""
        # Mock requests
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"test audio content"
            mock_response.raise_for_status = Mock()
            mock_response.iter_content = lambda chunk_size: [b"test audio content"]
            mock_get.return_value = mock_response
            
            result = await loader.load_source(
                source="https://example.com/audio.mp3",
                source_type=SourceType.URL
            )
            
            # Should cache the file
            assert result is not None
            assert Path(result).exists()


class TestRemotionComposer:
    """Test Remotion composer."""
    
    @pytest.fixture
    def composer(self):
        """Create Remotion composer."""
        return RemotionComposer()
    
    @pytest.mark.asyncio
    async def test_build_composition(self, composer):
        """Test composition building."""
        request = RemotionRequest(
            composition="MainComposition",
            layers=[
                Layer(
                    id="layer_001",
                    type="video",
                    source="/tmp/test.mp4",
                    source_type=SourceType.LOCAL
                )
            ]
        )
        
        # Mock source loader
        with patch.object(composer.source_loader, 'load_source') as mock_load:
            mock_load.return_value = "/tmp/test.mp4"
            
            result = await composer.build_composition(request)
            
            assert "timeline_path" in result
            assert "props_path" in result
            assert "output_dir" in result


class TestRemotionWorker:
    """Test Remotion worker."""
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        bus = Mock()
        bus.publish = AsyncMock()
        bus.subscribe = AsyncMock()
        return bus
    
    @pytest.fixture
    def worker(self, event_bus):
        """Create Remotion worker."""
        return RemotionWorker(event_bus)
    
    def test_get_subscriptions(self, worker):
        """Test worker subscriptions."""
        from services.event_bus import Topics
        subscriptions = worker.get_subscriptions()
        assert Topics.REMOTION_REQUESTED in subscriptions
        assert Topics.TTS_COMPLETED in subscriptions
        assert Topics.MATTING_COMPLETED in subscriptions

