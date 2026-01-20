"""
Tests for HuggingFace TTS Adapter (MF-003)
===========================================
Tests the HuggingFace TTS adapter implementation.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp

from services.tts.adapters.huggingface import HuggingFaceTTSAdapter, create_huggingface_adapter
from services.tts.models import TTSRequest, TTSResponse, TTSModel


@pytest.fixture
def hf_adapter():
    """Create HuggingFace TTS adapter for testing."""
    return HuggingFaceTTSAdapter(
        model_type=TTSModel.HF_MMS,
        api_token="test_token_12345"
    )


@pytest.fixture
def tts_request():
    """Create a sample TTS request."""
    return TTSRequest(
        text="Hello world, this is a test.",
        voice_reference="/path/to/voice.wav",
        model=TTSModel.HF_MMS
    )


def test_adapter_initialization():
    """Test adapter initialization."""
    adapter = HuggingFaceTTSAdapter(
        model_type=TTSModel.HF_MMS,
        api_token="test_token"
    )

    assert adapter.model_name == "huggingface"
    assert adapter.model_type == TTSModel.HF_MMS
    assert adapter.api_token == "test_token"
    assert not adapter.is_loaded()


def test_get_model_info(hf_adapter):
    """Test getting model information."""
    info = hf_adapter.get_model_info()

    assert info["adapter"] == "huggingface"
    assert info["model_type"] == str(TTSModel.HF_MMS)
    assert "model_id" in info
    assert "model_name" in info
    assert "supports_voice_cloning" in info
    assert "max_length" in info
    assert "sample_rate" in info
    assert info["has_api_token"]


def test_adapter_with_different_models():
    """Test adapter initialization with different models."""
    # Test MMS model
    adapter_mms = HuggingFaceTTSAdapter(
        model_type=TTSModel.HF_MMS,
        api_token="test_token"
    )
    assert adapter_mms.model_config["model_id"] == "facebook/mms-tts-eng"
    assert not adapter_mms.model_config["supports_voice_cloning"]

    # Test MetaVoice model
    adapter_metavoice = HuggingFaceTTSAdapter(
        model_type=TTSModel.HF_METAVOICE,
        api_token="test_token"
    )
    assert adapter_metavoice.model_config["supports_voice_cloning"]


@pytest.mark.asyncio
async def test_load_model(hf_adapter):
    """Test model loading."""
    result = await hf_adapter.load_model()

    assert result is True
    assert hf_adapter.is_loaded()


@pytest.mark.asyncio
async def test_unload_model(hf_adapter):
    """Test model unloading."""
    await hf_adapter.load_model()
    result = await hf_adapter.unload_model()

    assert result is True
    assert not hf_adapter.is_loaded()


@pytest.mark.asyncio
async def test_generate_empty_text(hf_adapter, tts_request):
    """Test generation with empty text."""
    tts_request.text = ""

    response = await hf_adapter.generate(tts_request)

    assert not response.success
    assert response.error
    assert "empty" in response.error.lower()


@pytest.mark.asyncio
async def test_generate_success(hf_adapter, tts_request, tmp_path):
    """Test successful TTS generation."""
    # Mock the API response
    mock_audio_data = b"fake_audio_data_12345"

    # Create a mock response with context manager support
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read = AsyncMock(return_value=mock_audio_data)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session_class.return_value = mock_session

        # Set output path
        output_path = str(tmp_path / "test_output.wav")

        response = await hf_adapter.generate(tts_request, output_path=output_path)

        assert response.success
        assert response.audio_path == output_path
        assert response.model_used
        assert response.generation_time is not None
        assert Path(output_path).exists()


@pytest.mark.asyncio
async def test_generate_api_error(hf_adapter, tts_request):
    """Test handling of API errors."""

    async def mock_post_error(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        return mock_response

    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = mock_post_error
        mock_session_class.return_value = mock_session

        # Set max retries to 1 for faster test
        hf_adapter.max_retries = 1

        response = await hf_adapter.generate(tts_request)

        assert not response.success
        assert response.error
        assert "500" in response.error or "failed" in response.error.lower()


@pytest.mark.asyncio
async def test_generate_model_loading(hf_adapter, tts_request, tmp_path):
    """Test handling of model loading state (503 error)."""
    call_count = 0
    mock_audio_data = b"fake_audio_data_12345"

    def create_mock_response():
        nonlocal call_count
        call_count += 1

        mock_response = AsyncMock()
        if call_count == 1:
            # First call: model loading
            mock_response.status = 503
            mock_response.text = AsyncMock(return_value='{"error": "Model is loading"}')
        else:
            # Second call: success
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=mock_audio_data)

        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        return mock_response

    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(side_effect=lambda *args, **kwargs: create_mock_response())
        mock_session_class.return_value = mock_session

        # Speed up the test by patching sleep
        with patch('asyncio.sleep', new_callable=AsyncMock):
            output_path = str(tmp_path / "test_output.wav")
            response = await hf_adapter.generate(tts_request, output_path=output_path)

            assert response.success
            assert call_count == 2  # Should have retried


@pytest.mark.asyncio
async def test_generate_timeout(hf_adapter, tts_request):
    """Test handling of timeouts."""

    async def mock_post_timeout(*args, **kwargs):
        await asyncio.sleep(100)  # Simulate long request

    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = mock_post_timeout
        mock_session_class.return_value = mock_session

        # Set low timeout and max retries for faster test
        hf_adapter.timeout_seconds = 1
        hf_adapter.max_retries = 1

        with patch('asyncio.sleep', new_callable=AsyncMock):
            response = await hf_adapter.generate(tts_request)

            assert not response.success
            assert response.error
            assert "timeout" in response.error.lower() or "failed" in response.error.lower()


def test_create_huggingface_adapter():
    """Test factory function."""
    adapter = create_huggingface_adapter(
        model_type=TTSModel.HF_MMS,
        api_token="test_token"
    )

    assert isinstance(adapter, HuggingFaceTTSAdapter)
    assert adapter.model_type == TTSModel.HF_MMS
    assert adapter.api_token == "test_token"


def test_text_truncation():
    """Test that long text is truncated."""
    adapter = HuggingFaceTTSAdapter(
        model_type=TTSModel.HF_MMS,
        api_token="test_token"
    )

    long_text = "a" * 1000
    request = TTSRequest(
        text=long_text,
        voice_reference="/path/to/voice.wav"
    )

    max_length = adapter.model_config["max_length"]
    assert len(request.text) > max_length


def test_adapter_without_api_token():
    """Test adapter initialization without API token."""
    adapter = HuggingFaceTTSAdapter(
        model_type=TTSModel.HF_MMS,
        api_token=None
    )

    info = adapter.get_model_info()
    assert not info["has_api_token"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
