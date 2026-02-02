"""
Tests for Sora Generation Workflow (BM-010)
=============================================
Tests the end-to-end Sora video generation workflow.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from automation.sora_generator import (
    SoraGenerator,
    GenerationJob,
    GenerationStatus,
    AspectRatio,
    Duration,
    get_sora_generator,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton between tests."""
    SoraGenerator.reset_instance()
    yield
    SoraGenerator.reset_instance()


@pytest.fixture
def event_bus():
    """Create mock event bus."""
    bus = MagicMock()
    bus.publish = AsyncMock()
    bus.subscribe = MagicMock()
    bus.unsubscribe = MagicMock()
    return bus


@pytest.fixture
def generator(event_bus):
    """Create SoraGenerator instance."""
    gen = SoraGenerator(event_bus=event_bus, output_dir="/tmp/test_sora")
    return gen


class TestSoraGeneratorInit:
    """Test BM-010: SoraGenerator initialization."""

    def test_initialization(self, generator):
        """BM-010: Generator should initialize with default settings."""
        assert generator is not None
        assert generator._max_concurrent == 2
        assert generator.POLL_INTERVAL == 30
        assert generator.MAX_POLL_DURATION == 900
        assert generator.MAX_RETRIES == 2
        assert not generator.is_running

    def test_singleton_pattern(self, event_bus):
        """BM-010: Should use singleton pattern."""
        gen1 = SoraGenerator.get_instance(event_bus=event_bus)
        gen2 = SoraGenerator.get_instance()
        assert gen1 is gen2

    def test_get_sora_generator_helper(self, event_bus):
        """BM-010: get_sora_generator should return singleton."""
        gen = get_sora_generator(event_bus=event_bus)
        assert isinstance(gen, SoraGenerator)

    def test_base_url(self):
        """BM-010: Should use correct Sora URL."""
        assert SoraGenerator.BASE_URL == "https://sora.chatgpt.com"


class TestGenerationJob:
    """Test BM-010: GenerationJob dataclass."""

    def test_job_creation(self):
        """BM-010: Job should create with defaults."""
        job = GenerationJob(prompt="A cat playing piano")
        assert job.prompt == "A cat playing piano"
        assert job.status == GenerationStatus.QUEUED
        assert job.duration == 15
        assert job.aspect_ratio == "Portrait"
        assert job.character is None
        assert job.video_path is None
        assert job.id.startswith("sora-gen-")

    def test_job_to_dict(self):
        """BM-010: Job should serialize to dict."""
        job = GenerationJob(prompt="Test prompt", duration=25)
        d = job.to_dict()
        assert d["prompt"] == "Test prompt"
        assert d["duration"] == 25
        assert d["status"] == "queued"
        assert "id" in d
        assert "created_at" in d

    def test_duration_seconds(self):
        """BM-010: Job should calculate duration when completed."""
        job = GenerationJob(prompt="Test")
        assert job.duration_seconds is None

        job.started_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        job.completed_at = datetime(2026, 1, 1, 0, 5, 0, tzinfo=timezone.utc)
        assert job.duration_seconds == 300.0


class TestGenerationEnums:
    """Test BM-010: Enums."""

    def test_aspect_ratios(self):
        """BM-010: Should define all aspect ratios."""
        assert AspectRatio.PORTRAIT.value == "Portrait"
        assert AspectRatio.LANDSCAPE.value == "Landscape"
        assert AspectRatio.SQUARE.value == "Square"

    def test_durations(self):
        """BM-010: Should define all durations."""
        assert Duration.SHORT.value == 10
        assert Duration.MEDIUM.value == 15
        assert Duration.LONG.value == 25

    def test_generation_statuses(self):
        """BM-010: Should define all generation statuses."""
        statuses = [s.value for s in GenerationStatus]
        assert "queued" in statuses
        assert "generating" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "downloading" in statuses
        assert "processing" in statuses


class TestSoraGeneratorStartStop:
    """Test BM-010: Start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start(self, generator, event_bus):
        """BM-010: Start should set running and subscribe to events."""
        await generator.start()
        assert generator.is_running
        event_bus.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, generator, event_bus):
        """BM-010: Stop should unset running."""
        await generator.start()
        await generator.stop()
        assert not generator.is_running


class TestSoraGeneratorGenerate:
    """Test BM-010: Video generation workflow."""

    @pytest.mark.asyncio
    async def test_generate_creates_job(self, generator):
        """BM-010: generate() should create and track a job."""
        # Mock internal methods to avoid actual Safari calls
        generator._navigate_to_sora = AsyncMock()
        generator._submit_prompt = AsyncMock()
        generator._poll_for_completion = AsyncMock()
        generator._download_video = AsyncMock()
        generator._remove_watermark = AsyncMock()

        job = await generator.generate(
            prompt="A sunset over the ocean",
            duration=15,
            aspect_ratio="Landscape",
        )

        assert job.id in generator._jobs
        assert job.prompt == "A sunset over the ocean"
        assert job.status == GenerationStatus.COMPLETED
        assert job.duration == 15
        assert job.aspect_ratio == "Landscape"

    @pytest.mark.asyncio
    async def test_generate_emits_events(self, generator, event_bus):
        """BM-010: generate() should emit start and complete events."""
        generator._navigate_to_sora = AsyncMock()
        generator._submit_prompt = AsyncMock()
        generator._poll_for_completion = AsyncMock()
        generator._download_video = AsyncMock()
        generator._remove_watermark = AsyncMock()

        await generator.generate(prompt="Test video")

        # Should emit started and completed events (kwargs-based publish)
        calls = [c.kwargs.get("topic", c.args[0] if c.args else "") for c in event_bus.publish.call_args_list]
        assert "sora.generate.started" in calls
        assert "sora.generate.completed" in calls

    @pytest.mark.asyncio
    async def test_generate_failure_emits_failed(self, generator, event_bus):
        """BM-010: Failed generation should emit failed event."""
        generator._navigate_to_sora = AsyncMock(side_effect=Exception("Safari error"))

        job = await generator.generate(prompt="Fail test")

        assert job.status == GenerationStatus.FAILED
        assert job.error == "Safari error"

        calls = [c.kwargs.get("topic", c.args[0] if c.args else "") for c in event_bus.publish.call_args_list]
        assert "sora.generate.failed" in calls

    @pytest.mark.asyncio
    async def test_generate_with_character(self, generator):
        """BM-010: generate() should accept character parameter."""
        generator._navigate_to_sora = AsyncMock()
        generator._submit_prompt = AsyncMock()
        generator._poll_for_completion = AsyncMock()
        generator._download_video = AsyncMock()
        generator._remove_watermark = AsyncMock()

        job = await generator.generate(
            prompt="Character story",
            character="@isaiahdupree",
        )

        assert job.character == "@isaiahdupree"
        assert job.status == GenerationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_generate_with_pipeline_id(self, generator, event_bus):
        """BM-010: generate() should pass pipeline_id to events."""
        generator._navigate_to_sora = AsyncMock()
        generator._submit_prompt = AsyncMock()
        generator._poll_for_completion = AsyncMock()
        generator._download_video = AsyncMock()
        generator._remove_watermark = AsyncMock()

        job = await generator.generate(
            prompt="Pipeline test",
            pipeline_id="pipeline-abc123",
        )

        assert job.metadata.get("pipeline_id") == "pipeline-abc123"

        # Check that events include pipeline_id
        for call in event_bus.publish.call_args_list:
            payload = call.kwargs.get("payload", {})
            if "pipeline_id" in payload:
                assert payload["pipeline_id"] == "pipeline-abc123"


class TestSoraGeneratorBatch:
    """Test BM-010: Batch generation."""

    @pytest.mark.asyncio
    async def test_generate_batch(self, generator, event_bus):
        """BM-010: generate_batch should delegate to SoraPipeline."""
        mock_result = {
            "status": "success",
            "stitched_video": "/tmp/stitched.mp4",
            "parts": [{"part": 1}, {"part": 2}],
        }

        with patch("automation.sora.pipeline.SoraPipeline") as MockPipeline:
            instance = MockPipeline.return_value
            instance.generate_multi_part = AsyncMock(return_value=mock_result)

            result = await generator.generate_batch(
                prompts=[
                    {"prompt": "Scene 1", "character": "@test"},
                    {"prompt": "Scene 2"},
                ],
                auto_stitch=True,
                pipeline_id="pipeline-batch",
            )

        assert "batch_id" in result
        assert result["status"] == "success"
        assert result["stitched_video"] == "/tmp/stitched.mp4"

        # Should emit batch events (kwargs-based publish)
        calls = [c.kwargs.get("topic", c.args[0] if c.args else "") for c in event_bus.publish.call_args_list]
        assert "sora.batch.started" in calls
        assert "sora.batch.completed" in calls

    @pytest.mark.asyncio
    async def test_generate_batch_failure(self, generator, event_bus):
        """BM-010: Batch failure should emit failed event."""
        with patch("automation.sora.pipeline.SoraPipeline") as MockPipeline:
            instance = MockPipeline.return_value
            instance.generate_multi_part = AsyncMock(
                side_effect=Exception("Batch error")
            )

            result = await generator.generate_batch(
                prompts=[{"prompt": "Fail"}],
            )

        assert result["status"] == "failed"
        assert result["error"] == "Batch error"


class TestSoraGeneratorQueries:
    """Test BM-010: Query methods."""

    @pytest.mark.asyncio
    async def test_get_job(self, generator):
        """BM-010: get_job should return tracked job."""
        generator._navigate_to_sora = AsyncMock()
        generator._submit_prompt = AsyncMock()
        generator._poll_for_completion = AsyncMock()
        generator._download_video = AsyncMock()
        generator._remove_watermark = AsyncMock()

        job = await generator.generate(prompt="Track me")
        found = generator.get_job(job.id)
        assert found is not None
        assert found.id == job.id

    def test_get_job_not_found(self, generator):
        """BM-010: get_job should return None for unknown ID."""
        assert generator.get_job("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_completed_jobs(self, generator):
        """BM-010: get_completed_jobs should return only completed."""
        generator._navigate_to_sora = AsyncMock()
        generator._submit_prompt = AsyncMock()
        generator._poll_for_completion = AsyncMock()
        generator._download_video = AsyncMock()
        generator._remove_watermark = AsyncMock()

        await generator.generate(prompt="Job 1")
        await generator.generate(prompt="Job 2")

        completed = generator.get_completed_jobs()
        assert len(completed) == 2
        assert all(j.status == GenerationStatus.COMPLETED for j in completed)

    def test_get_stats(self, generator):
        """BM-010: get_stats should return generation statistics."""
        stats = generator.get_stats()
        assert stats["total_jobs"] == 0
        assert stats["active_jobs"] == 0
        assert stats["completed_jobs"] == 0
        assert stats["failed_jobs"] == 0
        assert stats["is_running"] is False
        assert stats["max_concurrent"] == 2


class TestSoraGeneratorEventHandling:
    """Test BM-010: Event bus handling."""

    @pytest.mark.asyncio
    async def test_handle_generate_request(self, generator, event_bus):
        """BM-010: Should handle generate request events."""
        generator._navigate_to_sora = AsyncMock()
        generator._submit_prompt = AsyncMock()
        generator._poll_for_completion = AsyncMock()
        generator._download_video = AsyncMock()
        generator._remove_watermark = AsyncMock()

        mock_event = MagicMock()
        mock_event.payload = {
            "prompt": "Event-driven generation",
            "character": "@test",
            "duration": 25,
            "aspect_ratio": "Landscape",
            "pipeline_id": "pipeline-event",
        }

        await generator._handle_generate_request(mock_event)

        # Should have created a job
        assert len(generator._jobs) == 1
        job = list(generator._jobs.values())[0]
        assert job.prompt == "Event-driven generation"
        assert job.character == "@test"
        assert job.duration == 25
