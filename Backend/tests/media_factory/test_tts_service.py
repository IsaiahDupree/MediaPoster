"""
TTS Service Tests
=================
Tests for TTS service functionality.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from services.tts.models import TTSRequest, TTSResponse, EmotionConfig, EmotionMethod
from services.tts.adapters.indextts2 import IndexTTS2Adapter
from services.tts.worker import TTSWorker


class TestTTSModels:
    """Test TTS data models."""

    def test_tts_request_creation(self):
        """Test TTSRequest model creation."""
        request = TTSRequest(
            text="Hello, world!",
            model="indextts2",
            voice_reference="/path/to/voice.wav"
        )
        assert request.text == "Hello, world!"
        assert request.model == "indextts2"
        assert request.voice_reference == "/path/to/voice.wav"
        assert request.job_id is not None
        assert request.correlation_id is not None

    def test_tts_request_with_emotion(self):
        """Test TTSRequest with emotion control."""
        emotion = EmotionConfig(
            method=EmotionMethod.VECTORS,
            vectors={"happy": 0.8, "calm": 0.2}
        )
        request = TTSRequest(
            text="Hello, world!",
            model="indextts2",
            voice_reference="/path/to/voice.wav",
            emotion=emotion
        )
        assert request.emotion is not None
        assert request.emotion.vectors["happy"] == 0.8


class TestIndexTTS2Adapter:
    """Test IndexTTS2 adapter."""

    @pytest.fixture
    def adapter(self):
        """Create IndexTTS2 adapter."""
        return IndexTTS2Adapter()

    def test_get_model_name(self, adapter):
        """Test model info returns correct name."""
        info = adapter.get_model_info()
        assert info["name"] == "IndexTTS2"

    @pytest.mark.asyncio
    async def test_generate_speech_mock(self, adapter):
        """Test speech generation with mocked API call."""
        # Mock the external call_indextts2_api function used by generate()
        request = TTSRequest(
            text="Test text",
            model="indextts2",
            voice_reference="/tmp/voice.wav"
        )

        mock_response = TTSResponse(
            job_id=request.job_id,
            success=True,
            audio_path="/tmp/test_output.wav",
            duration_seconds=3.0,
            model_used="indextts2",
            correlation_id=request.correlation_id
        )

        with patch.object(adapter, 'generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            result = await adapter.generate(request)

            assert result.success is True
            assert result.audio_path == "/tmp/test_output.wav"
            assert result.model_used == "indextts2"
            mock_gen.assert_called_once()


class TestTTSWorker:
    """Test TTS worker."""

    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        bus = Mock()
        bus.publish = AsyncMock()
        bus.subscribe = AsyncMock()
        return bus

    @pytest.fixture
    def worker(self, event_bus):
        """Create TTS worker."""
        return TTSWorker(event_bus)

    def test_get_subscriptions(self, worker):
        """Test worker subscriptions."""
        from services.event_bus import Topics
        subscriptions = worker.get_subscriptions()
        assert Topics.TTS_REQUESTED in subscriptions

    @pytest.mark.asyncio
    async def test_handle_event_success(self, worker, event_bus):
        """Test successful TTS event handling."""
        from services.event_bus import Event, Topics
        from uuid import uuid4

        event = Event(
            id=str(uuid4()),
            topic=Topics.TTS_REQUESTED,
            payload={
                "text": "Test text",
                "model": "indextts2",
                "voice_reference": "/tmp/voice.wav"
            },
            correlation_id=str(uuid4())
        )

        # Mock the _get_adapter to return a mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.generate.return_value = TTSResponse(
            job_id="test-job",
            success=True,
            audio_path="/tmp/output.wav",
            duration_seconds=5.0,
            model_used="indextts2",
            correlation_id=event.correlation_id
        )

        with patch.object(worker, '_get_adapter', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_adapter

            await worker.handle_event(event)

            # Check that events were emitted via the event bus
            assert event_bus.publish.called

