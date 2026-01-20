"""
Whisper Transcription Service Tests (TRANS-001)
================================================
Tests for WhisperTranscriber service

Test Coverage:
- TRANS-001: Transcription with word timestamps
- Audio extraction from video
- Error handling for missing files
- Image file detection (no audio)
"""

import pytest
import pytest_asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from services.whisper_transcriber import WhisperTranscriber


@pytest.fixture
def mock_ai_client():
    """Mock AIClient for testing"""
    with patch('services.whisper_transcriber.AIClient') as mock_client_class:
        mock_instance = Mock()
        mock_instance.transcribe = Mock(return_value={
            "text": "This is a test transcription",
            "language": "en",
            "duration": 5.0,
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.5,
                    "text": "This is a test",
                    "words": [
                        {"word": "This", "start": 0.0, "end": 0.3},
                        {"word": "is", "start": 0.3, "end": 0.5},
                        {"word": "a", "start": 0.5, "end": 0.6},
                        {"word": "test", "start": 0.6, "end": 1.0}
                    ]
                },
                {
                    "start": 2.5,
                    "end": 5.0,
                    "text": "transcription",
                    "words": [
                        {"word": "transcription", "start": 2.5, "end": 3.5}
                    ]
                }
            ]
        })
        mock_client_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_model_registry():
    """Mock ModelRegistry for testing"""
    with patch('services.whisper_transcriber.ModelRegistry') as mock_registry:
        mock_config = Mock()
        mock_config.provider = "groq"
        mock_config.model = "whisper-large-v3"
        mock_config.cost_input = 0.0
        mock_registry.get_model_config.return_value = mock_config
        yield mock_registry


@pytest.fixture
def transcriber(mock_ai_client, mock_model_registry):
    """Create transcriber instance with mocked dependencies"""
    return WhisperTranscriber()


class TestWhisperTranscriberInit:
    """Test transcriber initialization"""

    def test_initialization(self, transcriber):
        """Test transcriber initializes correctly"""
        assert transcriber is not None
        assert transcriber.provider == "groq"
        assert transcriber.config is not None

    def test_initialization_failure(self, mock_model_registry):
        """Test initialization handles errors gracefully"""
        with patch('services.whisper_transcriber.AIClient') as mock_client:
            mock_client.side_effect = Exception("API key missing")

            with pytest.raises(ValueError, match="Transcription initialization failed"):
                WhisperTranscriber()


class TestAudioStreamDetection:
    """Test audio stream detection (TRANS-001 prerequisite)"""

    def test_image_file_has_no_audio(self, transcriber):
        """Test image files are correctly identified as having no audio"""
        # Image extensions should be skipped without FFprobe check
        for ext in ['.jpg', '.png', '.gif', '.webp', '.heic']:
            fake_path = f"/tmp/test_image{ext}"
            assert transcriber.has_audio_stream(fake_path) is False

    @patch('subprocess.run')
    def test_video_with_audio_detected(self, mock_run, transcriber):
        """Test video with audio stream is detected"""
        mock_run.return_value = Mock(
            stdout="audio",
            stderr="",
            returncode=0
        )

        result = transcriber.has_audio_stream("/tmp/video_with_audio.mp4")
        assert result is True

        # Verify FFprobe was called correctly
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "ffprobe" in cmd
        assert "-select_streams" in cmd
        assert "a" in cmd

    @patch('subprocess.run')
    def test_video_without_audio_detected(self, mock_run, transcriber):
        """Test video without audio stream is detected"""
        mock_run.return_value = Mock(
            stdout="",
            stderr="",
            returncode=0
        )

        result = transcriber.has_audio_stream("/tmp/video_no_audio.mp4")
        assert result is False

    @patch('subprocess.run')
    def test_ffprobe_error_returns_false(self, mock_run, transcriber):
        """Test FFprobe errors are handled gracefully"""
        mock_run.side_effect = Exception("FFprobe not found")

        result = transcriber.has_audio_stream("/tmp/test.mp4")
        assert result is False  # Should assume no audio on error


class TestAudioExtraction:
    """Test audio extraction from video"""

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_extract_audio_success(self, mock_exists, mock_run, transcriber):
        """Test successful audio extraction"""
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0)

        with tempfile.NamedTemporaryFile(suffix='.mp4') as video_file:
            audio_path = transcriber.extract_audio(video_file.name)

            assert audio_path is not None
            assert audio_path.endswith('_audio.mp3')

            # Verify FFmpeg was called with correct parameters
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "ffmpeg" in cmd
            assert "-vn" in cmd  # No video
            assert "-acodec" in cmd
            assert "libmp3lame" in cmd
            assert "-ar" in cmd and "16000" in cmd  # 16kHz
            assert "-ac" in cmd and "1" in cmd  # Mono

    def test_extract_audio_file_not_found(self, transcriber):
        """Test audio extraction fails for non-existent file"""
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            transcriber.extract_audio("/tmp/nonexistent_video.mp4")

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_extract_audio_ffmpeg_error(self, mock_exists, mock_run, transcriber):
        """Test audio extraction handles FFmpeg errors"""
        mock_exists.return_value = True
        # Mock subprocess.CalledProcessError instead of generic Exception
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, 'ffmpeg', stderr=b"FFmpeg error")

        with tempfile.NamedTemporaryFile(suffix='.mp4') as video_file:
            with pytest.raises(RuntimeError, match="Failed to extract audio"):
                transcriber.extract_audio(video_file.name)


class TestTranscription:
    """Test TRANS-001: Transcription with word timestamps"""

    def test_transcribe_audio(self, transcriber, mock_ai_client):
        """Test audio transcription returns text and timestamps"""
        # Create temp audio file for testing
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as audio_file:
            audio_path = audio_file.name

        try:
            result = transcriber.transcribe(audio_path)

            # TRANS-001 Acceptance: Transcripts generated
            assert "text" in result
            assert len(result["text"]) > 0

            # TRANS-001 Acceptance: Word timestamps
            assert "segments" in result
            segments = result["segments"]
            assert len(segments) > 0

            # Verify each segment has words with timestamps
            for segment in segments:
                assert "words" in segment
                for word in segment["words"]:
                    assert "word" in word
                    assert "start" in word
                    assert "end" in word

            # Verify mock was called correctly
            mock_ai_client.transcribe.assert_called_once_with(audio_path, language="en")

        finally:
            # Cleanup
            if os.path.exists(audio_path):
                os.remove(audio_path)

    def test_transcribe_audio_file_not_found(self, transcriber):
        """Test transcription fails for non-existent audio file"""
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            transcriber.transcribe("/tmp/nonexistent_audio.mp3")

    def test_transcribe_api_error(self, transcriber, mock_ai_client):
        """Test transcription handles API errors"""
        mock_ai_client.transcribe.side_effect = Exception("API error")

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as audio_file:
            audio_path = audio_file.name

        try:
            with pytest.raises(RuntimeError, match="Transcription failed"):
                transcriber.transcribe(audio_path)
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)


class TestVideoTranscription:
    """Test complete video transcription pipeline"""

    @patch('services.whisper_transcriber.WhisperTranscriber.has_audio_stream')
    @patch('services.whisper_transcriber.WhisperTranscriber.extract_audio')
    @patch('services.whisper_transcriber.WhisperTranscriber.transcribe')
    def test_transcribe_video_success(
        self,
        mock_transcribe,
        mock_extract,
        mock_has_audio,
        transcriber
    ):
        """Test complete video transcription pipeline"""
        # Setup mocks
        mock_has_audio.return_value = True
        mock_extract.return_value = "/tmp/test_audio.mp3"
        mock_transcribe.return_value = {
            "text": "Test transcription",
            "language": "en",
            "segments": []
        }

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_file:
            video_path = video_file.name

        try:
            result = transcriber.transcribe_video(video_path)

            # Verify pipeline executed correctly
            mock_has_audio.assert_called_once_with(video_path)
            mock_extract.assert_called_once_with(video_path)
            mock_transcribe.assert_called_once_with("/tmp/test_audio.mp3")

            # Verify result
            assert "text" in result
            assert result["text"] == "Test transcription"

        finally:
            if os.path.exists(video_path):
                os.remove(video_path)

    @patch('services.whisper_transcriber.WhisperTranscriber.has_audio_stream')
    def test_transcribe_video_no_audio(self, mock_has_audio, transcriber):
        """Test video with no audio returns empty transcript"""
        mock_has_audio.return_value = False

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_file:
            video_path = video_file.name

        try:
            result = transcriber.transcribe_video(video_path)

            # Should return empty transcript
            assert result["text"] == ""
            assert result["no_audio"] is True
            assert result["language"] is None

        finally:
            if os.path.exists(video_path):
                os.remove(video_path)

    @patch('services.whisper_transcriber.WhisperTranscriber.has_audio_stream')
    @patch('services.whisper_transcriber.WhisperTranscriber.extract_audio')
    @patch('services.whisper_transcriber.WhisperTranscriber.transcribe')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_transcribe_video_cleanup(
        self,
        mock_remove,
        mock_path_exists,
        mock_transcribe,
        mock_extract,
        mock_has_audio,
        transcriber
    ):
        """Test temp audio file is cleaned up after transcription"""
        mock_has_audio.return_value = True
        mock_extract.return_value = "/tmp/test_audio.mp3"
        mock_transcribe.return_value = {"text": "Test"}
        mock_path_exists.return_value = True  # Temp file exists for cleanup

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_file:
            video_path = video_file.name

        try:
            transcriber.transcribe_video(video_path, cleanup=True)

            # Verify cleanup was called
            mock_remove.assert_called_once_with("/tmp/test_audio.mp3")

        finally:
            if os.path.exists(video_path):
                os.remove(video_path)


class TestTranscriptionAcceptanceCriteria:
    """Test TRANS-001 acceptance criteria are met"""

    @patch('services.whisper_transcriber.WhisperTranscriber.has_audio_stream')
    @patch('services.whisper_transcriber.WhisperTranscriber.extract_audio')
    @patch('services.whisper_transcriber.WhisperTranscriber.transcribe')
    @patch('os.path.exists')
    def test_transcripts_generated(
        self,
        mock_path_exists,
        mock_transcribe,
        mock_extract,
        mock_has_audio,
        transcriber
    ):
        """TRANS-001 Acceptance: Transcripts generated"""
        mock_has_audio.return_value = True
        mock_extract.return_value = "/tmp/test_audio.mp3"
        mock_transcribe.return_value = {
            "text": "This is a test transcription",
            "segments": []
        }
        mock_path_exists.return_value = True

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_file:
            video_path = video_file.name

        try:
            result = transcriber.transcribe_video(video_path)

            # Must have text
            assert "text" in result
            assert isinstance(result["text"], str)
            assert len(result["text"]) > 0

        finally:
            if os.path.exists(video_path):
                os.remove(video_path)

    @patch('services.whisper_transcriber.WhisperTranscriber.has_audio_stream')
    @patch('services.whisper_transcriber.WhisperTranscriber.extract_audio')
    @patch('services.whisper_transcriber.WhisperTranscriber.transcribe')
    @patch('os.path.exists')
    def test_word_timestamps(
        self,
        mock_path_exists,
        mock_transcribe,
        mock_extract,
        mock_has_audio,
        transcriber
    ):
        """TRANS-001 Acceptance: Word timestamps"""
        mock_has_audio.return_value = True
        mock_extract.return_value = "/tmp/test_audio.mp3"
        mock_transcribe.return_value = {
            "text": "This is a test",
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.5,
                    "text": "This is a test",
                    "words": [
                        {"word": "This", "start": 0.0, "end": 0.3},
                        {"word": "is", "start": 0.3, "end": 0.5},
                        {"word": "a", "start": 0.5, "end": 0.6},
                        {"word": "test", "start": 0.6, "end": 1.0}
                    ]
                }
            ]
        }
        mock_path_exists.return_value = True

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_file:
            video_path = video_file.name

        try:
            result = transcriber.transcribe_video(video_path)

            # Must have segments with word-level timestamps
            assert "segments" in result
            segments = result["segments"]

            if len(segments) > 0:  # If transcription returned segments
                for segment in segments:
                    assert "words" in segment

                    for word in segment["words"]:
                        # Each word must have text and timestamps
                        assert "word" in word
                        assert "start" in word
                        assert "end" in word

                        # Timestamps must be numeric
                        assert isinstance(word["start"], (int, float))
                        assert isinstance(word["end"], (int, float))

                        # End must be after start
                        assert word["end"] >= word["start"]

        finally:
            if os.path.exists(video_path):
                os.remove(video_path)
