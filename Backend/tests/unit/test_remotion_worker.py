"""
Remotion Worker Unit Tests
===========================
Tests for Remotion rendering worker and event handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from services.remotion.worker import RemotionWorker
from services.remotion.models import (
    SourceType,
    Layer,
    AudioTrack,
    RemotionRequest,
    RemotionResponse,
    RemotionJobStatus,
)
from services.event_bus import Event, Topics


class TestRemotionWorkerInit:
    """Tests for RemotionWorker initialization"""

    def test_init_with_defaults(self):
        with patch('services.remotion.worker.EventBus'):
            worker = RemotionWorker()
        
        assert worker._jobs == {}
        assert worker._pending_sources == {}
        assert worker.composer is not None
        assert worker.source_loader is not None

    def test_init_with_custom_id(self):
        with patch('services.remotion.worker.EventBus'):
            worker = RemotionWorker(worker_id="remotion-worker-1")
        
        assert worker.worker_id == "remotion-worker-1"


class TestRemotionWorkerSubscriptions:
    """Tests for event subscriptions"""

    def test_get_subscriptions(self):
        with patch('services.remotion.worker.EventBus'):
            worker = RemotionWorker()
        
        subs = worker.get_subscriptions()
        
        assert Topics.REMOTION_REQUESTED in subs
        assert Topics.TTS_COMPLETED in subs
        assert Topics.MATTING_COMPLETED in subs


class TestRemotionWorkerEventHandling:
    """Tests for event handling"""

    @pytest.fixture
    def worker(self):
        with patch('services.remotion.worker.EventBus'):
            worker = RemotionWorker()
            worker.emit = AsyncMock()
            return worker

    @pytest.mark.asyncio
    async def test_handle_remotion_requested(self, worker):
        event = Event(
            topic=Topics.REMOTION_REQUESTED,
            payload={
                "composition": "MainComposition",
                "layers": [
                    {"id": "video-1", "type": "video", "source": "/path/video.mp4"}
                ],
            },
            correlation_id="corr-123",
        )
        
        with patch.object(worker, '_handle_render_request', new_callable=AsyncMock) as mock_handle:
            await worker.handle_event(event)
            mock_handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_tts_completed(self, worker):
        event = Event(
            topic=Topics.TTS_COMPLETED,
            payload={"job_id": "tts-123", "audio_path": "/path/audio.mp3"},
            correlation_id="corr-123",
        )
        
        with patch.object(worker, '_handle_tts_completed', new_callable=AsyncMock) as mock_handle:
            await worker.handle_event(event)
            mock_handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_matting_completed(self, worker):
        event = Event(
            topic=Topics.MATTING_COMPLETED,
            payload={"job_id": "mat-123", "output_path": "/path/matted.mp4"},
            correlation_id="corr-123",
        )
        
        with patch.object(worker, '_handle_matting_completed', new_callable=AsyncMock) as mock_handle:
            await worker.handle_event(event)
            mock_handle.assert_called_once_with(event)


class TestRemotionWorkerRenderRequest:
    """Tests for render request handling"""

    @pytest.fixture
    def worker(self):
        with patch('services.remotion.worker.EventBus'):
            worker = RemotionWorker()
            worker.emit = AsyncMock()
            return worker

    @pytest.mark.asyncio
    async def test_handle_invalid_request(self, worker):
        event = Event(
            topic=Topics.REMOTION_REQUESTED,
            payload={},  # Invalid - missing required fields
            correlation_id="corr-123",
        )
        
        with patch.object(worker, '_parse_request', return_value=None):
            await worker._handle_render_request(event)
        
        # Should emit failed event
        worker.emit.assert_called()

    @pytest.mark.asyncio
    async def test_creates_job_status(self, worker):
        event = Event(
            topic=Topics.REMOTION_REQUESTED,
            payload={
                "composition": "MainComposition",
                "job_id": "job-123",
            },
            correlation_id="corr-123",
        )
        
        request = RemotionRequest(
            composition="MainComposition",
            job_id="job-123",
        )
        
        with patch.object(worker, '_parse_request', return_value=request):
            with patch.object(worker, '_process_render', new_callable=AsyncMock):
                await worker._handle_render_request(event)
        
        assert "job-123" in worker._jobs


class TestRemotionWorkerJobTracking:
    """Tests for job status tracking"""

    @pytest.fixture
    def worker(self):
        with patch('services.remotion.worker.EventBus'):
            worker = RemotionWorker()
            return worker

    def test_add_job(self, worker):
        status = RemotionJobStatus(
            job_id="job-123",
            status="pending",
            correlation_id="corr-123",
        )
        
        worker._jobs["job-123"] = status
        
        assert "job-123" in worker._jobs
        assert worker._jobs["job-123"].status == "pending"

    def test_update_job_progress(self, worker):
        status = RemotionJobStatus(
            job_id="job-123",
            status="processing",
            progress=0.0,
        )
        worker._jobs["job-123"] = status
        
        worker._jobs["job-123"].progress = 0.5
        worker._jobs["job-123"].status = "rendering"
        
        assert worker._jobs["job-123"].progress == 0.5
        assert worker._jobs["job-123"].status == "rendering"

    def test_complete_job(self, worker):
        status = RemotionJobStatus(
            job_id="job-123",
            status="processing",
            started_at=datetime.now(timezone.utc),
        )
        worker._jobs["job-123"] = status
        
        response = RemotionResponse(
            job_id="job-123",
            success=True,
            video_path="/output/video.mp4",
        )
        
        worker._jobs["job-123"].status = "completed"
        worker._jobs["job-123"].progress = 1.0
        worker._jobs["job-123"].completed_at = datetime.now(timezone.utc)
        worker._jobs["job-123"].response = response
        
        assert worker._jobs["job-123"].status == "completed"
        assert worker._jobs["job-123"].response.success is True


class TestRemotionWorkerParseRequest:
    """Tests for request parsing"""

    @pytest.fixture
    def worker(self):
        with patch('services.remotion.worker.EventBus'):
            return RemotionWorker()

    def test_parse_basic_request(self, worker):
        payload = {
            "composition": "DevVlogMeme",
            "job_id": "job-123",
        }
        
        result = worker._parse_request(payload)
        
        if result:
            assert result.composition == "DevVlogMeme"

    def test_parse_request_with_layers(self, worker):
        payload = {
            "composition": "MainComposition",
            "layers": [
                {
                    "id": "video-1",
                    "type": "video",
                    "source": "/path/video.mp4",
                    "source_type": "local",
                    "start": 0.0,
                    "end": 10.0,
                },
            ],
        }
        
        result = worker._parse_request(payload)
        
        if result and result.layers:
            assert len(result.layers) == 1

    def test_parse_request_with_audio(self, worker):
        payload = {
            "composition": "MainComposition",
            "audio": [
                {
                    "id": "music-1",
                    "source": "/path/music.mp3",
                    "source_type": "local",
                    "volume": 0.8,
                },
            ],
        }
        
        result = worker._parse_request(payload)
        
        if result and result.audio:
            assert len(result.audio) == 1


class TestRemotionWorkerPendingSources:
    """Tests for pending source tracking"""

    @pytest.fixture
    def worker(self):
        with patch('services.remotion.worker.EventBus'):
            return RemotionWorker()

    def test_track_pending_tts(self, worker):
        worker._pending_sources["job-123"] = {
            "tts-456": {"type": "tts", "status": "pending"},
        }
        
        assert "job-123" in worker._pending_sources
        assert "tts-456" in worker._pending_sources["job-123"]

    def test_track_pending_matting(self, worker):
        worker._pending_sources["job-123"] = {
            "mat-789": {"type": "matting", "status": "pending"},
        }
        
        assert "mat-789" in worker._pending_sources["job-123"]

    def test_resolve_pending_source(self, worker):
        worker._pending_sources["job-123"] = {
            "tts-456": {"type": "tts", "status": "pending"},
        }
        
        # Mark as resolved
        worker._pending_sources["job-123"]["tts-456"]["status"] = "resolved"
        worker._pending_sources["job-123"]["tts-456"]["path"] = "/path/audio.mp3"
        
        assert worker._pending_sources["job-123"]["tts-456"]["status"] == "resolved"
        assert worker._pending_sources["job-123"]["tts-456"]["path"] == "/path/audio.mp3"


class TestRemotionWorkerEventEmission:
    """Tests for event emission"""

    @pytest.fixture
    def worker(self):
        with patch('services.remotion.worker.EventBus'):
            worker = RemotionWorker()
            worker.emit = AsyncMock()
            return worker

    @pytest.mark.asyncio
    async def test_emit_started_event(self, worker):
        await worker.emit(
            Topics.REMOTION_STARTED,
            {"job_id": "job-123", "composition": "MainComposition"},
            "corr-123",
        )
        
        worker.emit.assert_called_with(
            Topics.REMOTION_STARTED,
            {"job_id": "job-123", "composition": "MainComposition"},
            "corr-123",
        )

    @pytest.mark.asyncio
    async def test_emit_progress_event(self, worker):
        await worker.emit(
            Topics.REMOTION_PROGRESS,
            {"job_id": "job-123", "progress": 0.5},
            "corr-123",
        )
        
        worker.emit.assert_called()

    @pytest.mark.asyncio
    async def test_emit_completed_event(self, worker):
        await worker.emit(
            Topics.REMOTION_COMPLETED,
            {
                "job_id": "job-123",
                "success": True,
                "video_path": "/output/video.mp4",
            },
            "corr-123",
        )
        
        worker.emit.assert_called()

    @pytest.mark.asyncio
    async def test_emit_failed_event(self, worker):
        await worker.emit(
            Topics.REMOTION_FAILED,
            {
                "job_id": "job-123",
                "error": "Render failed",
            },
            "corr-123",
        )
        
        worker.emit.assert_called()
