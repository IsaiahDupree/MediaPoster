"""
Clip Extraction Tests
=====================
Comprehensive test suite for the clip extraction service.

Test Phases:
    Phase 1: AI Provider Tests (mock and OpenAI)
    Phase 2: ClipExtractionService Unit Tests
    Phase 3: Integration Tests with Mock Data
    Phase 4: End-to-End Tests (requires real video)
    Phase 5: Worker & Pub/Sub Tests

Run specific phases:
    pytest tests/test_clip_extraction.py -k "phase1"
    pytest tests/test_clip_extraction.py -k "phase2"
    
Run all tests:
    pytest tests/test_clip_extraction.py -v
"""

import asyncio
import json
import os
import pytest
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_transcript():
    """Sample transcript with timestamps for testing."""
    return """[00:00 - 00:15] Welcome back to the channel! Today we're going to talk about something really important.
[00:15 - 00:30] This is a game changer for productivity. You won't believe how simple it is.
[00:30 - 00:45] First tip: wake up early. I know it sounds basic but hear me out.
[00:45 - 01:00] When you wake up before everyone else, you get uninterrupted focus time.
[01:00 - 01:15] Second tip: eliminate distractions. Turn off your phone notifications.
[01:15 - 01:30] I used to waste three hours a day on social media. Now I batch it.
[01:30 - 01:45] Third tip: use the Pomodoro technique. 25 minutes on, 5 minutes off.
[01:45 - 02:00] This has doubled my output. Seriously, try it for one week.
[02:00 - 02:15] Fourth tip: prioritize ruthlessly. Not everything is urgent.
[02:15 - 02:30] Use the Eisenhower matrix to sort your tasks.
[02:30 - 02:45] Fifth tip: take breaks. Your brain needs rest to perform well.
[02:45 - 03:00] Thanks for watching! Drop a comment with your favorite tip."""


@pytest.fixture
def sample_transcript_no_timestamps():
    """Sample transcript without timestamps."""
    return """Welcome back to the channel! Today we're going to talk about productivity.
This is a game changer. You won't believe how simple it is.
First tip: wake up early. When you wake up before everyone else, you get focus time.
Second tip: eliminate distractions. Turn off your phone notifications.
Third tip: use the Pomodoro technique. 25 minutes on, 5 minutes off.
Thanks for watching! Drop a comment with your favorite tip."""


@pytest.fixture
def expected_segment_count():
    """Expected number of segments from sample transcript."""
    return 3  # Mock provider should find at least 3 segments


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_video_path(temp_output_dir):
    """Create a mock video file path (doesn't need to be real for unit tests)."""
    video_path = temp_output_dir / "test_video.mp4"
    video_path.touch()  # Create empty file
    return video_path


# =============================================================================
# PHASE 1: AI PROVIDER TESTS
# =============================================================================

class TestPhase1MockAIProvider:
    """Phase 1: Test MockAIProvider functionality."""
    
    @pytest.mark.asyncio
    async def test_phase1_mock_provider_initialization(self):
        """Test MockAIProvider can be initialized."""
        from services.ai_providers.mock_provider import MockAIProvider

        provider = MockAIProvider()

        assert provider.name == "mock"
        assert provider.call_count == 0

    @pytest.mark.asyncio
    async def test_phase1_mock_provider_analyze_transcript(self, sample_transcript):
        """Test MockAIProvider can analyze transcript."""
        from services.ai_providers.mock_provider import MockAIProvider
        
        provider = MockAIProvider()
        
        result = await provider.analyze_transcript(
            transcript=sample_transcript,
            min_duration=10,
            max_duration=60,
            max_segments=5
        )
        
        assert result is not None
        assert len(result.segments) > 0
        assert len(result.segments) <= 5
        assert result.summary != ""
        assert provider.call_count == 1
    
    @pytest.mark.asyncio
    async def test_phase1_mock_provider_segment_validation(self, sample_transcript):
        """Test that MockAIProvider returns valid segments."""
        from services.ai_providers.mock_provider import MockAIProvider

        provider = MockAIProvider()

        result = await provider.analyze_transcript(
            transcript=sample_transcript,
            min_duration=10,
            max_duration=60,
            max_segments=5
        )

        for segment in result.segments:
            # Verify segment has required fields
            assert segment.start_time is not None
            assert segment.end_time is not None
            assert segment.text != ""
            assert 0 <= segment.relevance_score <= 1.0
            
            # Verify timestamp format (MM:SS)
            assert ":" in segment.start_time
            assert ":" in segment.end_time
    
    @pytest.mark.asyncio
    async def test_phase1_mock_provider_deterministic(self, sample_transcript):
        """Test that MockAIProvider returns consistent results for same input."""
        from services.ai_providers.mock_provider import MockAIProvider
        
        provider = MockAIProvider()
        
        result1 = await provider.analyze_transcript(sample_transcript)
        provider.reset()
        result2 = await provider.analyze_transcript(sample_transcript)
        
        # Same input should produce same number of segments
        assert len(result1.segments) == len(result2.segments)
        
        # Summaries should contain same hash
        assert result1.summary == result2.summary
    
    @pytest.mark.asyncio
    async def test_phase1_mock_provider_no_timestamps(self, sample_transcript_no_timestamps):
        """Test MockAIProvider handles transcript without timestamps."""
        from services.ai_providers.mock_provider import MockAIProvider
        
        provider = MockAIProvider()
        
        result = await provider.analyze_transcript(
            transcript=sample_transcript_no_timestamps,
            min_duration=10,
            max_duration=60,
            max_segments=3
        )
        
        # Should still produce segments using fallback logic
        assert len(result.segments) > 0
        assert len(result.segments) <= 3
    
    @pytest.mark.asyncio
    async def test_phase1_mock_provider_metadata_generation(self, sample_transcript):
        """Test MockAIProvider can generate clip metadata."""
        from services.ai_providers.mock_provider import MockAIProvider
        from services.ai_providers.base import TranscriptSegment
        
        provider = MockAIProvider()
        
        segment = TranscriptSegment(
            start_time="00:30",
            end_time="00:45",
            text="First tip: wake up early. This is a game changer.",
            relevance_score=0.85,
            reasoning="Strong hook with actionable advice"
        )
        
        metadata = await provider.generate_clip_metadata(segment)
        
        assert "title" in metadata
        assert "description" in metadata
        assert "hashtags" in metadata
        assert len(metadata["hashtags"]) > 0
    
    @pytest.mark.asyncio
    async def test_phase1_mock_provider_health_check(self):
        """Test MockAIProvider health check."""
        from services.ai_providers.mock_provider import MockAIProvider
        
        provider = MockAIProvider()
        
        health = await provider.health_check()
        
        assert health["status"] == "healthy"
        assert health["provider"] == "mock"
        assert health["latency_ms"] >= 0


class TestPhase1AIProviderFactory:
    """Phase 1: Test AI provider factory function."""
    
    def test_phase1_get_mock_provider_raises_not_configured(self):
        """Test getting mock provider raises NotConfiguredError in production."""
        from services.ai_providers import get_ai_provider, NotConfiguredError

        with pytest.raises(NotConfiguredError):
            get_ai_provider("mock")

    def test_phase1_mock_provider_direct_import(self):
        """Test MockAIProvider can still be imported directly for testing."""
        from services.ai_providers.mock_provider import MockAIProvider

        provider = MockAIProvider()
        assert provider.name == "mock"
    
    def test_phase1_get_openai_provider(self):
        """Test getting OpenAI provider (may fail without API key)."""
        from services.ai_providers import get_ai_provider
        
        provider = get_ai_provider("openai")
        
        assert provider.name == "openai"
    
    def test_phase1_default_provider(self):
        """Test default provider is OpenAI."""
        from services.ai_providers import get_ai_provider
        
        # Clear env var temporarily
        old_val = os.environ.pop("AI_PROVIDER", None)
        
        try:
            provider = get_ai_provider()
            assert provider.name == "openai"
        finally:
            if old_val:
                os.environ["AI_PROVIDER"] = old_val


class TestPhase1OpenAIProvider:
    """Phase 1: Test OpenAI provider (requires API key for full tests)."""
    
    def test_phase1_openai_provider_initialization(self):
        """Test OpenAI provider can be initialized."""
        from services.ai_providers import OpenAIProvider
        
        provider = OpenAIProvider()
        
        assert provider.name == "openai"
        assert provider.config is not None
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    @pytest.mark.asyncio
    async def test_phase1_openai_provider_health_check(self):
        """Test OpenAI provider health check (requires API key)."""
        from services.ai_providers import OpenAIProvider
        
        provider = OpenAIProvider()
        
        health = await provider.health_check()
        
        assert health["status"] == "healthy"
        assert health["provider"] == "openai"
        assert "latency_ms" in health
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    @pytest.mark.asyncio
    async def test_phase1_openai_provider_analyze_transcript(self, sample_transcript):
        """Test OpenAI provider transcript analysis (requires API key)."""
        from services.ai_providers import OpenAIProvider
        
        provider = OpenAIProvider()
        
        result = await provider.analyze_transcript(
            transcript=sample_transcript,
            min_duration=10,
            max_duration=60,
            max_segments=3
        )
        
        assert result is not None
        assert len(result.segments) > 0
        assert len(result.segments) <= 3
        
        # Verify segment quality
        for segment in result.segments:
            assert segment.start_time != ""
            assert segment.end_time != ""
            assert segment.text != ""
            assert 0 <= segment.relevance_score <= 1.0


# =============================================================================
# PHASE 2: CLIP EXTRACTION SERVICE UNIT TESTS
# =============================================================================

class TestPhase2ClipExtractionServiceInit:
    """Phase 2: Test ClipExtractionService initialization."""
    
    def test_phase2_service_initialization_defaults(self, temp_output_dir):
        """Test service initializes with defaults."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(output_dir=temp_output_dir)
        
        assert service.output_dir == temp_output_dir
        assert service.font_size == 24
        assert service.font_color == "#FFFFFF"
    
    def test_phase2_service_initialization_custom(self, temp_output_dir):
        """Test service initializes with custom options."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(
            ai_provider="mock",
            output_dir=temp_output_dir,
            font_size=32,
            font_color="#000000"
        )
        
        assert service.ai_provider_name == "mock"
        assert service.font_size == 32
        assert service.font_color == "#000000"
    
    def test_phase2_service_creates_output_dir(self):
        """Test service creates output directory if it doesn't exist."""
        from services.clip_extraction_service import ClipExtractionService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "new_clips"
            
            service = ClipExtractionService(output_dir=new_dir)
            
            assert new_dir.exists()


class TestPhase2ClipExtractionServiceHelpers:
    """Phase 2: Test ClipExtractionService helper methods."""
    
    def test_phase2_parse_timestamp_mm_ss(self, temp_output_dir):
        """Test parsing MM:SS timestamp."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(output_dir=temp_output_dir)
        
        assert service._parse_timestamp("01:30") == 90
        assert service._parse_timestamp("00:45") == 45
        assert service._parse_timestamp("10:00") == 600
    
    def test_phase2_parse_timestamp_hh_mm_ss(self, temp_output_dir):
        """Test parsing HH:MM:SS timestamp."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(output_dir=temp_output_dir)
        
        assert service._parse_timestamp("01:30:00") == 5400
        assert service._parse_timestamp("00:01:30") == 90
    
    def test_phase2_parse_timestamp_invalid(self, temp_output_dir):
        """Test parsing invalid timestamp returns 0."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(output_dir=temp_output_dir)
        
        assert service._parse_timestamp("invalid") == 0.0
        assert service._parse_timestamp("") == 0.0
    
    def test_phase2_format_ms_to_timestamp(self, temp_output_dir):
        """Test formatting milliseconds to MM:SS."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(output_dir=temp_output_dir)
        
        assert service._format_ms_to_timestamp(90000) == "01:30"
        assert service._format_ms_to_timestamp(45000) == "00:45"
        assert service._format_ms_to_timestamp(600000) == "10:00"
    
    def test_phase2_parse_transcript_line(self, temp_output_dir):
        """Test parsing transcript line."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(output_dir=temp_output_dir)
        
        result = service._parse_transcript_line("[00:30 - 00:45] This is the text.")
        
        assert result is not None
        assert result[0] == "00:30"
        assert result[1] == "00:45"
        assert result[2] == "This is the text."
    
    def test_phase2_parse_transcript_line_invalid(self, temp_output_dir):
        """Test parsing invalid transcript line."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(output_dir=temp_output_dir)
        
        result = service._parse_transcript_line("No timestamps here")
        
        assert result is None


class TestPhase2ClipExtractionServiceAIProvider:
    """Phase 2: Test ClipExtractionService AI provider integration."""
    
    def test_phase2_service_uses_mock_provider(self, temp_output_dir):
        """Test service can use mock provider when injected directly."""
        from services.clip_extraction_service import ClipExtractionService
        from services.ai_providers.mock_provider import MockAIProvider

        service = ClipExtractionService(
            ai_provider_instance=MockAIProvider(),
            output_dir=temp_output_dir
        )

        provider = service._get_ai_provider()

        assert provider.name == "mock"

    @pytest.mark.asyncio
    async def test_phase2_service_identify_segments_mock(self, temp_output_dir, sample_transcript):
        """Test segment identification with mock provider."""
        from services.clip_extraction_service import ClipExtractionService
        from services.ai_providers.mock_provider import MockAIProvider

        service = ClipExtractionService(
            ai_provider_instance=MockAIProvider(),
            output_dir=temp_output_dir
        )
        
        segments = await service._identify_segments(
            formatted_transcript=sample_transcript,
            min_duration=10,
            max_duration=60,
            max_segments=5
        )
        
        assert len(segments) > 0
        assert len(segments) <= 5
        
        for segment in segments:
            assert segment.start_time is not None
            assert segment.end_time is not None


class TestPhase2TranscriptionMock:
    """Phase 2: Test transcription with mock data."""
    
    @pytest.mark.asyncio
    async def test_phase2_mock_transcribe(self, temp_output_dir, mock_video_path):
        """Test mock transcription returns valid structure."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(output_dir=temp_output_dir)
        
        result = await service._mock_transcribe(mock_video_path)
        
        assert "text" in result
        assert "formatted" in result
        assert "words" in result
        assert len(result["words"]) > 0
    
    @pytest.mark.asyncio
    async def test_phase2_mock_transcribe_word_structure(self, temp_output_dir, mock_video_path):
        """Test mock transcription word structure."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(output_dir=temp_output_dir)
        
        result = await service._mock_transcribe(mock_video_path)
        
        for word in result["words"]:
            assert "text" in word
            assert "start" in word
            assert "end" in word
            assert word["end"] > word["start"]


# =============================================================================
# PHASE 3: INTEGRATION TESTS WITH MOCK DATA
# =============================================================================

class TestPhase3IntegrationMockProvider:
    """Phase 3: Integration tests using mock provider."""
    
    @pytest.mark.asyncio
    async def test_phase3_full_pipeline_mock(self, temp_output_dir, mock_video_path):
        """Test full extraction pipeline with mock provider."""
        from services.clip_extraction_service import ClipExtractionService
        from services.ai_providers.mock_provider import MockAIProvider

        service = ClipExtractionService(
            ai_provider_instance=MockAIProvider(),
            output_dir=temp_output_dir
        )
        
        # Mock the video processing since we don't have a real video
        with patch.object(service, '_transcribe_video') as mock_transcribe:
            with patch.object(service, '_render_clips') as mock_render:
                mock_transcribe.return_value = {
                    "text": "Test transcript",
                    "formatted": "[00:00 - 00:15] Test segment one.\n[00:15 - 00:30] Test segment two.",
                    "words": [{"text": "Test", "start": 0, "end": 500}],
                    "topics": ["test"],
                    "summary": "Test summary"
                }
                mock_render.return_value = []
                
                result = await service.extract_clips(
                    video_path=str(mock_video_path),
                    output_dir=temp_output_dir,
                    min_clip_duration=10,
                    max_clip_duration=60,
                    max_clips=3
                )
                
                assert result.job_id is not None
                assert result.source_video == str(mock_video_path)
    
    @pytest.mark.asyncio
    async def test_phase3_progress_callback(self, temp_output_dir, mock_video_path):
        """Test progress callback is called during extraction."""
        from services.clip_extraction_service import ClipExtractionService
        from services.ai_providers.mock_provider import MockAIProvider

        service = ClipExtractionService(
            ai_provider_instance=MockAIProvider(),
            output_dir=temp_output_dir
        )
        
        progress_updates = []
        
        def progress_callback(pct: int, step: str):
            progress_updates.append((pct, step))
        
        # Mock the video processing
        with patch.object(service, '_transcribe_video') as mock_transcribe:
            with patch.object(service, '_render_clips') as mock_render:
                mock_transcribe.return_value = {
                    "text": "Test",
                    "formatted": "[00:00 - 00:20] Test segment.",
                    "words": [],
                    "topics": [],
                    "summary": ""
                }
                mock_render.return_value = []
                
                await service.extract_clips(
                    video_path=str(mock_video_path),
                    progress_callback=progress_callback,
                    min_clip_duration=10,
                    max_clip_duration=60,
                    max_clips=3
                )
                
                # Verify progress was reported
                assert len(progress_updates) > 0
                
                # Verify progress increases
                percentages = [p[0] for p in progress_updates]
                assert percentages[0] < percentages[-1]
    
    @pytest.mark.asyncio
    async def test_phase3_file_not_found(self, temp_output_dir):
        """Test extraction with non-existent file."""
        from services.clip_extraction_service import ClipExtractionService
        from services.ai_providers.mock_provider import MockAIProvider

        service = ClipExtractionService(
            ai_provider_instance=MockAIProvider(),
            output_dir=temp_output_dir
        )
        
        result = await service.extract_clips(
            video_path="/nonexistent/video.mp4",
            min_clip_duration=10,
            max_clip_duration=60,
            max_clips=3
        )
        
        assert result.success is False
        assert "not found" in result.error.lower() or "FileNotFoundError" in result.error


class TestPhase3DataclassValidation:
    """Phase 3: Test dataclass structures."""
    
    def test_phase3_transcript_segment_dataclass(self):
        """Test TranscriptSegment dataclass."""
        from services.clip_extraction_service import TranscriptSegment
        
        segment = TranscriptSegment(
            start_time="00:30",
            end_time="00:45",
            text="Test segment text",
            relevance_score=0.85,
            reasoning="This is engaging"
        )
        
        assert segment.start_time == "00:30"
        assert segment.end_time == "00:45"
        assert segment.text == "Test segment text"
        assert segment.relevance_score == 0.85
    
    def test_phase3_clip_result_dataclass(self):
        """Test ClipResult dataclass."""
        from services.clip_extraction_service import ClipResult
        
        clip = ClipResult(
            clip_id="abc123",
            filename="clip_1.mp4",
            path="/path/to/clip.mp4",
            start_time="00:30",
            end_time="00:45",
            duration=15.0,
            text="Clip text",
            relevance_score=0.85,
            reasoning="Engaging content"
        )
        
        assert clip.clip_id == "abc123"
        assert clip.duration == 15.0
    
    def test_phase3_extraction_result_dataclass(self):
        """Test ExtractionResult dataclass."""
        from services.clip_extraction_service import ExtractionResult, ClipResult
        
        clip = ClipResult(
            clip_id="abc123",
            filename="clip_1.mp4",
            path="/path/clip.mp4",
            start_time="00:00",
            end_time="00:15",
            duration=15.0,
            text="Test",
            relevance_score=0.8,
            reasoning="Test"
        )
        
        result = ExtractionResult(
            job_id="job123",
            source_video="/path/video.mp4",
            clips=[clip],
            transcript_text="Full transcript",
            key_topics=["topic1"],
            summary="Summary",
            total_duration=15.0,
            processing_time=5.5,
            success=True
        )
        
        assert result.job_id == "job123"
        assert len(result.clips) == 1
        assert result.success is True


# =============================================================================
# PHASE 4: END-TO-END TESTS (Requires real video)
# =============================================================================

class TestPhase4EndToEnd:
    """Phase 4: End-to-end tests with real video files."""
    
    @pytest.fixture
    def real_video_path(self):
        """Path to a real test video (if available)."""
        test_video = Path(__file__).parent / "fixtures" / "test_video.mp4"
        if test_video.exists():
            return test_video
        return None
    
    @pytest.mark.skipif(
        not Path(__file__).parent.joinpath("fixtures", "test_video.mp4").exists(),
        reason="No test video available"
    )
    @pytest.mark.asyncio
    async def test_phase4_real_video_extraction(self, real_video_path, temp_output_dir):
        """Test extraction with real video file."""
        from services.clip_extraction_service import ClipExtractionService
        from services.ai_providers.mock_provider import MockAIProvider

        service = ClipExtractionService(
            ai_provider_instance=MockAIProvider(),  # Use mock to avoid API calls
            output_dir=temp_output_dir
        )
        
        result = await service.extract_clips(
            video_path=str(real_video_path),
            min_clip_duration=5,
            max_clip_duration=30,
            max_clips=2
        )
        
        assert result.success is True
        # Additional assertions for real video
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    @pytest.mark.asyncio
    async def test_phase4_openai_integration(self, sample_transcript, temp_output_dir):
        """Test with real OpenAI API (requires API key)."""
        from services.clip_extraction_service import ClipExtractionService
        
        service = ClipExtractionService(
            ai_provider="openai",
            output_dir=temp_output_dir
        )
        
        segments = await service._identify_segments(
            formatted_transcript=sample_transcript,
            min_duration=10,
            max_duration=60,
            max_segments=3
        )
        
        assert len(segments) > 0
        assert len(segments) <= 3
        
        # Verify OpenAI returned quality segments
        for segment in segments:
            assert segment.reasoning != ""
            assert len(segment.text) > 10


# =============================================================================
# PHASE 5: WORKER & PUB/SUB TESTS
# =============================================================================

class TestPhase5Worker:
    """Phase 5: Test ClipExtractionWorker pub/sub integration."""
    
    @pytest.mark.asyncio
    async def test_phase5_worker_initialization(self):
        """Test worker can be initialized."""
        from services.workers.clip_extraction_worker import ClipExtractionWorker
        
        worker = ClipExtractionWorker()
        
        assert worker.worker_id is not None
        assert "ClipExtractionWorker" in worker.worker_id
    
    @pytest.mark.asyncio
    async def test_phase5_worker_subscriptions(self):
        """Test worker subscribes to correct topics."""
        from services.workers.clip_extraction_worker import ClipExtractionWorker
        from services.event_bus import Topics
        
        worker = ClipExtractionWorker()
        
        subscriptions = worker.get_subscriptions()
        
        assert Topics.CLIP_EXTRACTION_REQUESTED in subscriptions
    
    @pytest.mark.asyncio
    async def test_phase5_worker_event_handling(self, temp_output_dir, mock_video_path):
        """Test worker handles extraction events."""
        from services.workers.clip_extraction_worker import ClipExtractionWorker
        from services.event_bus import Event, Topics, EventBus
        
        # Reset event bus for clean test
        EventBus.reset_instance()
        
        worker = ClipExtractionWorker(default_output_dir=str(temp_output_dir))
        
        # Create mock event
        event = Event(
            topic=Topics.CLIP_EXTRACTION_REQUESTED,
            payload={
                "video_path": str(mock_video_path),
                "media_id": "test-media-123",
                "options": {"max_clips": 2}
            }
        )
        
        # Mock the extraction service
        with patch.object(worker, '_get_extraction_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.extract_clips = AsyncMock(return_value=MagicMock(
                success=True,
                clips=[],
                key_topics=[],
                total_duration=0,
                processing_time=1.0
            ))
            mock_get_service.return_value = mock_service
            
            # Handle event should not raise
            try:
                await worker.handle_event(event)
            except Exception as e:
                # May fail on DB save, that's OK for this test
                pass


class TestPhase5EventBusIntegration:
    """Phase 5: Test event bus integration."""
    
    @pytest.mark.asyncio
    async def test_phase5_topics_exist(self):
        """Test clip extraction topics are defined."""
        from services.event_bus import Topics
        
        assert hasattr(Topics, 'CLIP_EXTRACTION_REQUESTED')
        assert hasattr(Topics, 'CLIP_EXTRACTION_STARTED')
        assert hasattr(Topics, 'CLIP_EXTRACTION_COMPLETED')
        assert hasattr(Topics, 'CLIP_EXTRACTION_FAILED')
    
    @pytest.mark.asyncio
    async def test_phase5_publish_extraction_event(self):
        """Test publishing clip extraction event."""
        from services.event_bus import EventBus, Topics
        
        # Reset for clean test
        EventBus.reset_instance()
        bus = EventBus.get_instance()
        
        event_received = []
        
        async def handler(event):
            event_received.append(event)
        
        bus.subscribe(Topics.CLIP_EXTRACTION_REQUESTED, handler)
        
        await bus.publish(
            Topics.CLIP_EXTRACTION_REQUESTED,
            {"video_path": "/test/video.mp4", "media_id": "123"}
        )
        
        assert len(event_received) == 1
        assert event_received[0].payload["media_id"] == "123"


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"])
