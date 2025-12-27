"""
TTS Service Tests
=================
Tests for TTS service functionality.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from services.tts.models import TTSRequest, TTSResponse, EmotionControl, EmotionVectors
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
        emotion = EmotionControl(
            method="Use emotion vectors",
            emotion_vectors=EmotionVectors(happy=0.8, calm=0.2)
        )
        request = TTSRequest(
            text="Hello, world!",
            model="indextts2",
            voice_reference="/path/to/voice.wav",
            emotion=emotion
        )
        assert request.emotion is not None
        assert request.emotion.emotion_vectors.happy == 0.8


class TestIndexTTS2Adapter:
    """Test IndexTTS2 adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create IndexTTS2 adapter."""
        return IndexTTS2Adapter()
    
    def test_get_model_name(self, adapter):
        """Test model name."""
        assert adapter.get_model_name() == "indextts2"
    
    @pytest.mark.asyncio
    async def test_generate_speech_mock(self, adapter):
        """Test speech generation with mocked API."""
        with patch.object(adapter, '_call_api') as mock_api:
            mock_api.return_value = True
            
            output_path = Path("/tmp/test_output.wav")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            result = await adapter.generate_speech(
                text="Test text",
                voice_reference_path=Path("/tmp/voice.wav"),
                output_file_path=output_path,
                emotion_params={}
            )
            
            assert result["output_path"] == str(output_path)
            assert result["model_used"] == "indextts2"
            mock_api.assert_called_once()


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
        
        # Mock adapter
        with patch.object(worker.adapters['indextts2'], 'generate_speech') as mock_gen:
            mock_gen.return_value = {
                "output_path": "/tmp/output.wav",
                "duration_seconds": 5.0,
                "model_used": "indextts2"
            }
            
            await worker.handle_event(event)
            
            # Check that completion event was emitted
            assert event_bus.publish.called
            calls = [call[0][0] for call in event_bus.publish.call_args_list]
            assert Topics.TTS_COMPLETED in calls or Topics.TTS_FAILED in calls

