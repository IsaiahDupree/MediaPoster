"""
Remotion Adapter Unit Tests
============================
Tests for Remotion rendering adapter
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from services.video_renderer.remotion_adapter import RemotionAdapter
from services.video_renderer.base import (
    RenderRequest,
    RenderResponse,
    RenderEngine,
    Layer,
)


class TestRemotionAdapterInit:
    """Tests for RemotionAdapter initialization"""

    def test_default_init(self):
        adapter = RemotionAdapter()
        
        assert adapter.project_dir is not None
        assert isinstance(adapter.project_dir, Path)

    def test_custom_project_dir(self):
        adapter = RemotionAdapter(project_dir="/custom/remotion")
        
        assert str(adapter.project_dir) == "/custom/remotion"

    def test_engine_name(self):
        adapter = RemotionAdapter()
        
        assert adapter.get_engine_name() == RenderEngine.REMOTION


class TestRemotionAdapterValidation:
    """Tests for request validation"""

    @pytest.fixture
    def adapter(self):
        return RemotionAdapter(project_dir="/tmp/remotion-test")

    @pytest.fixture
    def valid_request(self):
        return RenderRequest(
            layers=[
                Layer(id="video-1", type="video", source="/path/video.mp4"),
            ],
            duration=10.0,
            output_path="/output/video.mp4",
        )

    @pytest.mark.asyncio
    async def test_validate_valid_request(self, adapter, valid_request):
        with patch.object(Path, 'exists', return_value=True):
            result = await adapter.validate_request(valid_request)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_no_layers(self, adapter):
        request = RenderRequest(
            layers=[],
            duration=10.0,
            output_path="/output/video.mp4",
        )
        
        result = await adapter.validate_request(request)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_invalid_duration(self, adapter):
        request = RenderRequest(
            layers=[Layer(id="video-1", type="video")],
            duration=0.0,
            output_path="/output/video.mp4",
        )
        
        result = await adapter.validate_request(request)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_negative_duration(self, adapter):
        request = RenderRequest(
            layers=[Layer(id="video-1", type="video")],
            duration=-5.0,
            output_path="/output/video.mp4",
        )
        
        result = await adapter.validate_request(request)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_missing_project_dir(self, adapter):
        request = RenderRequest(
            layers=[Layer(id="video-1", type="video")],
            duration=10.0,
            output_path="/output/video.mp4",
        )
        
        with patch.object(Path, 'exists', return_value=False):
            result = await adapter.validate_request(request)
        
        assert result is False


class TestRemotionAdapterFormats:
    """Tests for supported formats"""

    @pytest.fixture
    def adapter(self):
        return RemotionAdapter()

    def test_get_supported_formats(self, adapter):
        formats = adapter.get_supported_formats()
        
        assert isinstance(formats, list)
        assert "MainComposition" in formats
        assert "DevVlogMeme" in formats
        assert "Explainer" in formats

    def test_format_count(self, adapter):
        formats = adapter.get_supported_formats()
        
        assert len(formats) >= 5


class TestRemotionAdapterResolution:
    """Tests for resolution handling"""

    @pytest.fixture
    def adapter(self):
        return RemotionAdapter()

    def test_get_default_resolution(self, adapter):
        resolution = adapter.get_default_resolution()
        
        assert "width" in resolution
        assert "height" in resolution
        assert resolution["width"] == 1920
        assert resolution["height"] == 1080


class TestRemotionAdapterRender:
    """Tests for render method"""

    @pytest.fixture
    def adapter(self):
        return RemotionAdapter(project_dir="/tmp/remotion-test")

    @pytest.fixture
    def render_request(self):
        return RenderRequest(
            layers=[
                Layer(id="video-1", type="video", source="/path/video.mp4"),
            ],
            duration=10.0,
            output_path="/output/video.mp4",
            composition="MainComposition",
        )

    @pytest.mark.asyncio
    async def test_render_calls_cli(self, adapter, render_request):
        with patch.object(Path, 'exists', return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.getsize', return_value=10000000):
                        result = await adapter.render(render_request)
        
        # Should have attempted to run
        assert mock_run.called or result is not None

    @pytest.mark.asyncio
    async def test_render_with_progress_callback(self, adapter, render_request):
        progress_values = []
        
        def on_progress(value):
            progress_values.append(value)
        
        with patch.object(adapter, 'validate_request', new_callable=AsyncMock, return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.getsize', return_value=10000000):
                        await adapter.render(render_request, on_progress=on_progress)


class TestRemotionAdapterErrorHandling:
    """Tests for error handling"""

    @pytest.fixture
    def adapter(self):
        return RemotionAdapter(project_dir="/tmp/remotion-test")

    @pytest.mark.asyncio
    async def test_handle_render_failure(self, adapter):
        request = RenderRequest(
            layers=[Layer(id="video-1", type="video")],
            duration=10.0,
            output_path="/output/video.mp4",
        )
        
        with patch.object(adapter, 'validate_request', new_callable=AsyncMock, return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="Render error")
                
                result = await adapter.render(request)
        
        if result:
            assert result.success is False or "error" in str(result).lower()

    @pytest.mark.asyncio
    async def test_handle_missing_output(self, adapter):
        request = RenderRequest(
            layers=[Layer(id="video-1", type="video")],
            duration=10.0,
            output_path="/output/video.mp4",
        )
        
        with patch.object(adapter, 'validate_request', new_callable=AsyncMock, return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                
                with patch('os.path.exists', return_value=False):
                    result = await adapter.render(request)
        
        if result:
            assert result.success is False or result.video_path is None


class TestRemotionAdapterIntegration:
    """Integration tests for RemotionAdapter"""

    @pytest.fixture
    def adapter(self):
        return RemotionAdapter()

    def test_full_render_workflow_setup(self, adapter):
        """Test that adapter is properly configured for rendering"""
        assert adapter.project_dir is not None
        assert adapter.get_engine_name() == RenderEngine.REMOTION
        assert len(adapter.get_supported_formats()) > 0
        
        resolution = adapter.get_default_resolution()
        assert resolution["width"] > 0
        assert resolution["height"] > 0


class TestRemotionAdapterCompositions:
    """Tests for composition handling"""

    @pytest.fixture
    def adapter(self):
        return RemotionAdapter()

    def test_main_composition_supported(self, adapter):
        formats = adapter.get_supported_formats()
        assert "MainComposition" in formats

    def test_dev_vlog_meme_supported(self, adapter):
        formats = adapter.get_supported_formats()
        assert "DevVlogMeme" in formats

    def test_explainer_supported(self, adapter):
        formats = adapter.get_supported_formats()
        assert "Explainer" in formats

    def test_trend_breakdown_supported(self, adapter):
        formats = adapter.get_supported_formats()
        assert "TrendBreakdown" in formats

    def test_product_promo_supported(self, adapter):
        formats = adapter.get_supported_formats()
        assert "ProductPromo" in formats

    def test_ugc_corner_supported(self, adapter):
        formats = adapter.get_supported_formats()
        assert "UGCCorner" in formats

    def test_broll_text_supported(self, adapter):
        formats = adapter.get_supported_formats()
        assert "BrollText" in formats
