"""
Remotion Models Unit Tests
===========================
Tests for Remotion service data models
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID

from services.remotion.models import (
    SourceType,
    Layer,
    AudioTrack,
    CaptionConfig,
    RemotionRequest,
    RemotionResponse,
    RemotionJobStatus,
)


class TestSourceType:
    """Tests for SourceType enum"""

    def test_source_type_values(self):
        assert SourceType.LOCAL == "local"
        assert SourceType.URL == "url"
        assert SourceType.TTS == "tts"
        assert SourceType.MEDIAPOSTER == "mediaposter"
        assert SourceType.MATTING == "matting"

    def test_all_source_types(self):
        types = list(SourceType)
        assert len(types) == 5


class TestLayer:
    """Tests for Layer dataclass"""

    def test_basic_layer(self):
        layer = Layer(id="layer-1", type="video")
        
        assert layer.id == "layer-1"
        assert layer.type == "video"
        assert layer.source is None
        assert layer.start == 0.0
        assert layer.opacity == 1.0

    def test_video_layer_with_source(self):
        layer = Layer(
            id="video-1",
            type="video",
            source="/path/to/video.mp4",
            source_type=SourceType.LOCAL,
            start=0.0,
            end=10.0,
        )
        
        assert layer.source == "/path/to/video.mp4"
        assert layer.source_type == SourceType.LOCAL
        assert layer.end == 10.0

    def test_image_layer(self):
        layer = Layer(
            id="image-1",
            type="image",
            source="https://example.com/image.png",
            source_type=SourceType.URL,
            position={"x": 100, "y": 200, "width": 800, "height": 600},
        )
        
        assert layer.type == "image"
        assert layer.position["x"] == 100
        assert layer.position["width"] == 800

    def test_text_layer(self):
        layer = Layer(
            id="text-1",
            type="text",
            content="Hello World",
            style={"fontSize": 48, "color": "#ffffff"},
            animation="fadeIn",
        )
        
        assert layer.type == "text"
        assert layer.content == "Hello World"
        assert layer.style["fontSize"] == 48
        assert layer.animation == "fadeIn"

    def test_layer_opacity(self):
        layer = Layer(id="layer-1", type="video", opacity=0.5)
        
        assert layer.opacity == 0.5

    def test_tts_source_layer(self):
        layer = Layer(
            id="audio-1",
            type="audio",
            source="tts-job-123",
            source_type=SourceType.TTS,
        )
        
        assert layer.source_type == SourceType.TTS


class TestAudioTrack:
    """Tests for AudioTrack dataclass"""

    def test_basic_audio(self):
        audio = AudioTrack(
            id="audio-1",
            source="/path/to/audio.mp3",
            source_type=SourceType.LOCAL,
        )
        
        assert audio.id == "audio-1"
        assert audio.source == "/path/to/audio.mp3"
        assert audio.start == 0.0
        assert audio.volume == 1.0

    def test_audio_with_ducking(self):
        audio = AudioTrack(
            id="music-1",
            source="https://example.com/music.mp3",
            source_type=SourceType.URL,
            volume=0.8,
            ducking={"duck_under": "voiceover-1", "duck_db": -6},
        )
        
        assert audio.volume == 0.8
        assert audio.ducking["duck_under"] == "voiceover-1"
        assert audio.ducking["duck_db"] == -6

    def test_audio_start_offset(self):
        audio = AudioTrack(
            id="audio-1",
            source="/path/to/audio.mp3",
            source_type=SourceType.LOCAL,
            start=5.0,
        )
        
        assert audio.start == 5.0


class TestCaptionConfig:
    """Tests for CaptionConfig dataclass"""

    def test_default_config(self):
        config = CaptionConfig()
        
        assert config.enabled is True
        assert config.style == "burned_in"
        assert config.emphasis_words is True
        assert config.position == "bottom"

    def test_custom_config(self):
        config = CaptionConfig(
            enabled=True,
            style="overlay",
            source="/path/to/timestamps.json",
            emphasis_words=False,
            position="top",
        )
        
        assert config.style == "overlay"
        assert config.source == "/path/to/timestamps.json"
        assert config.emphasis_words is False
        assert config.position == "top"

    def test_disabled_captions(self):
        config = CaptionConfig(enabled=False)
        
        assert config.enabled is False


class TestRemotionRequest:
    """Tests for RemotionRequest dataclass"""

    def test_default_request(self):
        request = RemotionRequest()
        
        assert request.composition == "MainComposition"
        assert request.job_id is not None
        assert request.correlation_id is not None
        assert request.output is not None
        assert request.captions is not None

    def test_auto_generated_job_id(self):
        request = RemotionRequest()
        
        # Should be a valid UUID
        UUID(request.job_id)

    def test_custom_job_id(self):
        request = RemotionRequest(job_id="custom-job-123")
        
        assert request.job_id == "custom-job-123"

    def test_request_with_layers(self):
        layers = [
            Layer(id="video-1", type="video", source="/path/video.mp4", source_type=SourceType.LOCAL),
            Layer(id="text-1", type="text", content="Title"),
        ]
        
        request = RemotionRequest(
            composition="DevVlogMeme",
            layers=layers,
        )
        
        assert request.composition == "DevVlogMeme"
        assert len(request.layers) == 2

    def test_request_with_audio(self):
        audio = [
            AudioTrack(id="music-1", source="/path/music.mp3", source_type=SourceType.LOCAL),
        ]
        
        request = RemotionRequest(audio=audio)
        
        assert len(request.audio) == 1

    def test_request_with_timeline(self):
        timeline = {
            "fps": 30,
            "resolution": "1080x1920",
            "duration": 30.0,
            "layers": [],
        }
        
        request = RemotionRequest(timeline=timeline)
        
        assert request.timeline["duration"] == 30.0

    def test_default_output_config(self):
        request = RemotionRequest()
        
        assert request.output["format"] == "mp4"
        assert request.output["resolution"] == "1080x1920"
        assert request.output["fps"] == 30

    def test_custom_output_config(self):
        request = RemotionRequest(
            output={
                "format": "webm",
                "resolution": "1920x1080",
                "fps": 60,
            }
        )
        
        assert request.output["format"] == "webm"
        assert request.output["fps"] == 60

    def test_request_with_props(self):
        request = RemotionRequest(
            props={
                "title": "My Video",
                "duration": 30,
                "theme": "dark",
            }
        )
        
        assert request.props["title"] == "My Video"

    def test_request_output_path(self):
        request = RemotionRequest(output_path="/output/video.mp4")
        
        assert request.output_path == "/output/video.mp4"


class TestRemotionResponse:
    """Tests for RemotionResponse dataclass"""

    def test_successful_response(self):
        response = RemotionResponse(
            job_id="job-123",
            success=True,
            video_path="/output/video.mp4",
            video_url="https://cdn.example.com/video.mp4",
            duration_seconds=30.5,
            file_size_mb=25.4,
            render_time=45.2,
        )
        
        assert response.success is True
        assert response.video_path == "/output/video.mp4"
        assert response.duration_seconds == 30.5
        assert response.file_size_mb == 25.4

    def test_failed_response(self):
        response = RemotionResponse(
            job_id="job-123",
            success=False,
            error="Render failed: out of memory",
        )
        
        assert response.success is False
        assert "out of memory" in response.error

    def test_response_with_variants(self):
        response = RemotionResponse(
            job_id="job-123",
            success=True,
            video_path="/output/video.mp4",
            variants=[
                {"platform": "tiktok", "path": "/output/video_tiktok.mp4"},
                {"platform": "youtube", "path": "/output/video_youtube.mp4"},
            ],
        )
        
        assert len(response.variants) == 2

    def test_response_with_thumbnails(self):
        response = RemotionResponse(
            job_id="job-123",
            success=True,
            video_path="/output/video.mp4",
            thumbnails=[
                {"time": 0, "path": "/output/thumb_0.jpg"},
                {"time": 10, "path": "/output/thumb_10.jpg"},
            ],
        )
        
        assert len(response.thumbnails) == 2

    def test_response_timestamp(self):
        response = RemotionResponse(job_id="job-123", success=True)
        
        assert response.timestamp is not None
        assert isinstance(response.timestamp, datetime)


class TestRemotionJobStatus:
    """Tests for RemotionJobStatus dataclass"""

    def test_pending_status(self):
        status = RemotionJobStatus(
            job_id="job-123",
            status="pending",
        )
        
        assert status.job_id == "job-123"
        assert status.status == "pending"
        assert status.progress == 0.0

    def test_processing_status(self):
        status = RemotionJobStatus(
            job_id="job-123",
            status="processing",
            progress=0.5,
            started_at=datetime.now(timezone.utc),
        )
        
        assert status.status == "processing"
        assert status.progress == 0.5
        assert status.started_at is not None

    def test_completed_status(self):
        response = RemotionResponse(job_id="job-123", success=True, video_path="/output/video.mp4")
        
        status = RemotionJobStatus(
            job_id="job-123",
            status="completed",
            progress=1.0,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            response=response,
        )
        
        assert status.status == "completed"
        assert status.progress == 1.0
        assert status.response is not None
        assert status.response.success is True

    def test_failed_status(self):
        status = RemotionJobStatus(
            job_id="job-123",
            status="failed",
            error="Render timeout",
        )
        
        assert status.status == "failed"
        assert status.error == "Render timeout"

    def test_status_stages(self):
        """Test all possible status stages"""
        stages = ["pending", "processing", "composing", "rendering", "completed", "failed"]
        
        for stage in stages:
            status = RemotionJobStatus(job_id="job-123", status=stage)
            assert status.status == stage
