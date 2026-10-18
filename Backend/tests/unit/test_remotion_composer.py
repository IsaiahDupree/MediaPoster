"""
Remotion Composer Unit Tests
=============================
Tests for Remotion composition building and timeline generation
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from services.remotion.composer import RemotionComposer
from services.remotion.models import (
    SourceType,
    Layer,
    AudioTrack,
    CaptionConfig,
    RemotionRequest,
)


class TestRemotionComposerInit:
    """Tests for RemotionComposer initialization"""

    def test_default_init(self):
        composer = RemotionComposer()
        
        assert composer.remotion_dir is not None
        assert isinstance(composer.remotion_dir, Path)

    def test_custom_dir(self):
        composer = RemotionComposer(remotion_dir="/custom/remotion")
        
        assert str(composer.remotion_dir) == "/custom/remotion"

    def test_source_loader_initialized(self):
        composer = RemotionComposer()
        
        assert composer.source_loader is not None


class TestRemotionComposerBuildComposition:
    """Tests for build_composition method"""

    @pytest.fixture
    def composer(self):
        return RemotionComposer(remotion_dir="/tmp/remotion-test")

    @pytest.fixture
    def basic_request(self):
        return RemotionRequest(
            composition="MainComposition",
            layers=[
                Layer(
                    id="video-1",
                    type="video",
                    source="/path/to/video.mp4",
                    source_type=SourceType.LOCAL,
                    start=0.0,
                    end=10.0,
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_build_composition_creates_output_dir(self, composer, basic_request):
        with patch.object(composer, '_load_sources', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = {"video-1": "/path/to/video.mp4"}
            
            with patch.object(composer, '_generate_timeline', new_callable=AsyncMock) as mock_timeline:
                mock_timeline.return_value = {"fps": 30, "layers": []}
                
                with patch.object(composer, '_generate_composition', new_callable=AsyncMock) as mock_comp:
                    mock_comp.return_value = None
                    
                    with patch('builtins.open', MagicMock()):
                        with patch.object(Path, 'mkdir'):
                            result = await composer.build_composition(basic_request, "/tmp/test-output")
        
        assert "output_dir" in result

    @pytest.mark.asyncio
    async def test_build_composition_returns_paths(self, composer, basic_request):
        with patch.object(composer, '_load_sources', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = {"video-1": "/path/to/video.mp4"}
            
            with patch.object(composer, '_generate_timeline', new_callable=AsyncMock) as mock_timeline:
                mock_timeline.return_value = {"fps": 30, "layers": []}
                
                with patch.object(composer, '_generate_composition', new_callable=AsyncMock) as mock_comp:
                    mock_comp.return_value = Path("/tmp/composition.tsx")
                    
                    with patch('builtins.open', MagicMock()):
                        with patch.object(Path, 'mkdir'):
                            result = await composer.build_composition(basic_request, "/tmp/test-output")
        
        assert "timeline_path" in result
        assert "props_path" in result
        assert "sources_loaded" in result


class TestRemotionComposerLoadSources:
    """Tests for _load_sources method"""

    @pytest.fixture
    def composer(self):
        return RemotionComposer(remotion_dir="/tmp/remotion-test")

    @pytest.mark.asyncio
    async def test_load_layer_sources(self, composer):
        request = RemotionRequest(
            layers=[
                Layer(
                    id="video-1",
                    type="video",
                    source="/path/to/video.mp4",
                    source_type=SourceType.LOCAL,
                ),
            ],
        )
        
        with patch.object(composer.source_loader, 'load_source', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = "/loaded/video.mp4"
            
            result = await composer._load_sources(request)
        
        assert "video-1" in result
        assert result["video-1"] == "/loaded/video.mp4"

    @pytest.mark.asyncio
    async def test_load_audio_sources(self, composer):
        request = RemotionRequest(
            audio=[
                AudioTrack(
                    id="music-1",
                    source="/path/to/music.mp3",
                    source_type=SourceType.LOCAL,
                ),
            ],
        )
        
        with patch.object(composer.source_loader, 'load_source', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = "/loaded/music.mp3"
            
            result = await composer._load_sources(request)
        
        assert "music-1" in result

    @pytest.mark.asyncio
    async def test_load_multiple_sources(self, composer):
        request = RemotionRequest(
            layers=[
                Layer(id="video-1", type="video", source="/video.mp4", source_type=SourceType.LOCAL),
                Layer(id="image-1", type="image", source="/image.png", source_type=SourceType.LOCAL),
            ],
            audio=[
                AudioTrack(id="music-1", source="/music.mp3", source_type=SourceType.LOCAL),
            ],
        )
        
        with patch.object(composer.source_loader, 'load_source', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = "/loaded/file"
            
            result = await composer._load_sources(request)
        
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_handle_failed_source_load(self, composer):
        request = RemotionRequest(
            layers=[
                Layer(id="video-1", type="video", source="/missing.mp4", source_type=SourceType.LOCAL),
            ],
        )
        
        with patch.object(composer.source_loader, 'load_source', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = None  # Failed to load
            
            result = await composer._load_sources(request)
        
        assert "video-1" not in result


class TestRemotionComposerGenerateTimeline:
    """Tests for _generate_timeline method"""

    @pytest.fixture
    def composer(self):
        return RemotionComposer(remotion_dir="/tmp/remotion-test")

    @pytest.mark.asyncio
    async def test_use_existing_timeline(self, composer):
        timeline = {"fps": 60, "resolution": "1920x1080", "layers": []}
        request = RemotionRequest(timeline=timeline)
        
        result = await composer._generate_timeline(request, {})
        
        assert result == timeline

    @pytest.mark.asyncio
    async def test_generate_from_layers(self, composer):
        request = RemotionRequest(
            layers=[
                Layer(id="video-1", type="video", source="/video.mp4", start=0.0, end=10.0),
            ],
        )
        
        result = await composer._generate_timeline(request, {"video-1": "/loaded/video.mp4"})
        
        assert "fps" in result
        assert "layers" in result
        assert len(result["layers"]) == 1

    @pytest.mark.asyncio
    async def test_timeline_duration_calculation(self, composer):
        request = RemotionRequest(
            layers=[
                Layer(id="layer-1", type="video", start=0.0, end=10.0),
                Layer(id="layer-2", type="video", start=5.0, end=20.0),
            ],
        )
        
        result = await composer._generate_timeline(request, {})
        
        assert result["duration"] == 20.0

    @pytest.mark.asyncio
    async def test_timeline_includes_audio(self, composer):
        request = RemotionRequest(
            audio=[
                AudioTrack(id="music-1", source="/music.mp3", source_type=SourceType.LOCAL, volume=0.8),
            ],
        )
        
        result = await composer._generate_timeline(request, {"music-1": "/loaded/music.mp3"})
        
        assert "audio" in result
        assert len(result["audio"]) == 1

    @pytest.mark.asyncio
    async def test_timeline_includes_captions(self, composer):
        request = RemotionRequest(
            captions=CaptionConfig(
                enabled=True,
                style="overlay",
                position="bottom",
            ),
        )
        
        result = await composer._generate_timeline(request, {})
        
        assert "captions" in result
        assert result["captions"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_timeline_layer_data(self, composer):
        request = RemotionRequest(
            layers=[
                Layer(
                    id="text-1",
                    type="text",
                    content="Hello World",
                    position={"x": 100, "y": 200},
                    style={"fontSize": 48},
                    animation="fadeIn",
                    start=0.0,
                    end=5.0,
                ),
            ],
        )
        
        result = await composer._generate_timeline(request, {})
        
        layer = result["layers"][0]
        assert layer["id"] == "text-1"
        assert layer["content"] == "Hello World"
        assert layer["style"]["fontSize"] == 48
        assert layer["animation"] == "fadeIn"


class TestRemotionComposerGenerateComposition:
    """Tests for _generate_composition method"""

    @pytest.fixture
    def composer(self):
        return RemotionComposer(remotion_dir="/tmp/remotion-test")

    @pytest.mark.asyncio
    async def test_use_existing_composition(self, composer):
        request = RemotionRequest(composition="DevVlogMeme")
        
        with patch.object(Path, 'exists', return_value=True):
            result = await composer._generate_composition(request, Path("/output"))
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_fallback_to_main_composition(self, composer):
        request = RemotionRequest(composition="NonExistent")
        
        # First call returns False (requested comp), second returns True (default)
        with patch.object(Path, 'exists', side_effect=[False, True]):
            result = await composer._generate_composition(request, Path("/output"))
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_fallback_to_root(self, composer):
        request = RemotionRequest(composition="NonExistent")
        
        # First two calls return False, third returns True (Root.tsx)
        with patch.object(Path, 'exists', side_effect=[False, False, True]):
            result = await composer._generate_composition(request, Path("/output"))
        
        assert result is not None


class TestRemotionComposerIntegration:
    """Integration tests for RemotionComposer"""

    @pytest.fixture
    def composer(self):
        return RemotionComposer(remotion_dir="/tmp/remotion-test")

    @pytest.mark.asyncio
    async def test_full_workflow(self, composer):
        """Test complete composition building workflow"""
        request = RemotionRequest(
            composition="MainComposition",
            layers=[
                Layer(
                    id="background",
                    type="video",
                    source="/path/to/bg.mp4",
                    source_type=SourceType.LOCAL,
                    start=0.0,
                    end=30.0,
                ),
                Layer(
                    id="title",
                    type="text",
                    content="My Video",
                    style={"fontSize": 72, "color": "#ffffff"},
                    start=0.0,
                    end=5.0,
                ),
            ],
            audio=[
                AudioTrack(
                    id="music",
                    source="/path/to/music.mp3",
                    source_type=SourceType.LOCAL,
                    volume=0.6,
                ),
            ],
            captions=CaptionConfig(enabled=True, style="burned_in"),
            output={"format": "mp4", "fps": 30, "resolution": "1080x1920"},
        )
        
        with patch.object(composer.source_loader, 'load_source', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = "/loaded/file"
            
            with patch('builtins.open', MagicMock()):
                with patch.object(Path, 'mkdir'):
                    with patch.object(Path, 'exists', return_value=True):
                        result = await composer.build_composition(request, "/tmp/output")
        
        assert result["sources_loaded"] is not None
        assert len(result["sources_loaded"]) == 3
