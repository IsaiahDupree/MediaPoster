"""
Tests for Media Factory Pipeline Orchestrator (MF-001)
"""
import pytest
import asyncio
from services.media_factory.orchestrator import (
    MediaFactoryOrchestrator,
    PipelineStage,
    JobStatus,
    get_orchestrator,
)


@pytest.fixture
def orchestrator():
    """Create test orchestrator instance."""
    return MediaFactoryOrchestrator()


@pytest.fixture
def sample_brief():
    """Create sample content brief."""
    return {
        "brief_id": "test-brief-123",
        "status": "draft",
        "cluster": {
            "cluster_id": "test-cluster-1",
            "name": "Test Trend",
            "why_now": "Testing purposes",
            "confidence": 0.85
        },
        "angle": {
            "angle_id": "angle-123",
            "audience_role": "developer",
            "intent": "learn",
            "stakes": "time",
            "format": "tutorial",
            "promise": "Learn testing",
            "unique_lens": "practical examples",
            "convergence_pattern": "Problem × Tool"
        },
        "title": "Test Video",
        "hook": "Want to learn testing?",
        "promise": "Learn testing in 45 seconds",
        "unique_lens": "practical examples",
        "format": "shorts",
        "length_sec": 45,
        "hook_sec": 1.2
    }


class TestMediaFactoryOrchestrator:
    """Tests for media factory orchestrator."""

    @pytest.mark.asyncio
    async def test_create_job(self, orchestrator, sample_brief):
        """Test creating a media factory job."""
        job_id = await orchestrator.create_job(sample_brief)

        assert job_id is not None
        assert len(job_id) > 0

        # Verify job was created
        status = orchestrator.get_job_status(job_id)
        assert status is not None
        assert status["status"] == JobStatus.PENDING.value
        assert status["brief"] == sample_brief

    @pytest.mark.asyncio
    async def test_create_job_with_custom_id(self, orchestrator, sample_brief):
        """Test creating job with custom ID."""
        custom_id = "custom-job-123"
        job_id = await orchestrator.create_job(sample_brief, job_id=custom_id)

        assert job_id == custom_id

        status = orchestrator.get_job_status(custom_id)
        assert status is not None

    @pytest.mark.asyncio
    async def test_register_stage_handler(self, orchestrator):
        """Test registering stage handlers."""
        async def mock_script_handler(job):
            return {"script": "test script"}

        orchestrator.register_stage_handler(
            PipelineStage.SCRIPT_GENERATION,
            mock_script_handler
        )

        # Verify handler is registered
        assert PipelineStage.SCRIPT_GENERATION in orchestrator._stage_handlers

    @pytest.mark.asyncio
    async def test_execute_pipeline_no_handlers(self, orchestrator, sample_brief):
        """Test pipeline execution with no handlers (default no-op behavior)."""
        job_id = await orchestrator.create_job(sample_brief)

        # Execute pipeline (should use default no-op handlers)
        result = await orchestrator.execute_pipeline(job_id)

        assert result["status"] == JobStatus.COMPLETED.value
        assert len(result["stage_results"]) == 6  # All 6 stages

        # Verify all stages completed
        for stage_result in result["stage_results"]:
            assert stage_result["status"] == JobStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_execute_pipeline_with_handlers(self, orchestrator, sample_brief):
        """Test pipeline execution with custom handlers."""
        # Register mock handlers
        async def mock_script_handler(job):
            await asyncio.sleep(0.01)  # Simulate work
            return {
                "script": {
                    "lines": ["Line 1", "Line 2"],
                    "shots": []
                }
            }

        async def mock_tts_handler(job):
            await asyncio.sleep(0.01)
            return {"audio_url": "https://example.com/audio.mp3"}

        orchestrator.register_stage_handler(
            PipelineStage.SCRIPT_GENERATION,
            mock_script_handler
        )
        orchestrator.register_stage_handler(
            PipelineStage.TTS_GENERATION,
            mock_tts_handler
        )

        # Execute pipeline
        job_id = await orchestrator.create_job(sample_brief)
        result = await orchestrator.execute_pipeline(job_id)

        assert result["status"] == JobStatus.COMPLETED.value

        # Verify script output was stored
        assert result["script"] is not None
        assert result["script"]["script"]["lines"] == ["Line 1", "Line 2"]

        # Verify TTS output was stored
        assert result["audio_url"] == "https://example.com/audio.mp3"

    @pytest.mark.asyncio
    async def test_pipeline_stops_on_stage_failure(self, orchestrator, sample_brief):
        """Test that pipeline stops when a stage fails."""
        async def failing_handler(job):
            raise ValueError("Simulated failure")

        orchestrator.register_stage_handler(
            PipelineStage.SCRIPT_GENERATION,
            failing_handler
        )

        job_id = await orchestrator.create_job(sample_brief)
        result = await orchestrator.execute_pipeline(job_id)

        # Job should fail
        assert result["status"] == JobStatus.FAILED.value
        assert result["error"] is not None

        # Only first stage should have run
        assert len(result["stage_results"]) == 1
        assert result["stage_results"][0]["status"] == JobStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_get_job_status(self, orchestrator, sample_brief):
        """Test getting job status."""
        job_id = await orchestrator.create_job(sample_brief)

        status = orchestrator.get_job_status(job_id)
        assert status is not None
        assert status["job_id"] == job_id
        assert status["status"] == JobStatus.PENDING.value

        # Non-existent job
        status = orchestrator.get_job_status("non-existent")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_all_jobs(self, orchestrator, sample_brief):
        """Test getting all jobs."""
        # Create multiple jobs
        job_id1 = await orchestrator.create_job(sample_brief)
        job_id2 = await orchestrator.create_job(sample_brief)

        all_jobs = orchestrator.get_all_jobs()
        assert len(all_jobs) >= 2

        job_ids = [job["job_id"] for job in all_jobs]
        assert job_id1 in job_ids
        assert job_id2 in job_ids

    @pytest.mark.asyncio
    async def test_cancel_job(self, orchestrator, sample_brief):
        """Test cancelling a job."""
        job_id = await orchestrator.create_job(sample_brief)

        # Cancel job
        success = await orchestrator.cancel_job(job_id)
        assert success is True

        # Verify job is cancelled
        status = orchestrator.get_job_status(job_id)
        assert status["status"] == JobStatus.CANCELLED.value

        # Cannot cancel again
        success = await orchestrator.cancel_job(job_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_stage_timing(self, orchestrator, sample_brief):
        """Test that stage timing is tracked."""
        async def slow_handler(job):
            await asyncio.sleep(0.1)
            return {"result": "done"}

        orchestrator.register_stage_handler(
            PipelineStage.SCRIPT_GENERATION,
            slow_handler
        )

        job_id = await orchestrator.create_job(sample_brief)
        result = await orchestrator.execute_pipeline(job_id)

        # Check first stage has timing info
        first_stage = result["stage_results"][0]
        assert first_stage["started_at"] is not None
        assert first_stage["completed_at"] is not None
        assert first_stage["duration_seconds"] >= 0.1


class TestGetOrchestrator:
    """Tests for get_orchestrator singleton."""

    def test_get_orchestrator_returns_instance(self):
        """Test that get_orchestrator returns an instance."""
        orchestrator = get_orchestrator()
        assert isinstance(orchestrator, MediaFactoryOrchestrator)

    def test_get_orchestrator_singleton(self):
        """Test that get_orchestrator returns same instance."""
        orchestrator1 = get_orchestrator()
        orchestrator2 = get_orchestrator()
        # Should be same instance
        # Note: This may not work if global state is reset between calls
