"""
Tests for Generated Video Multi-Channel Pipeline (BM-011)
==========================================================
Tests the video publish pipeline with analysis, approval, and routing.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from services.video_publish_pipeline import (
    VideoPublishPipeline,
    VideoPipelineJob,
    PublishResult,
    PipelineStage,
    get_video_publish_pipeline,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton between tests."""
    VideoPublishPipeline.reset_instance()
    yield
    VideoPublishPipeline.reset_instance()


@pytest.fixture
def event_bus():
    """Create mock event bus."""
    bus = MagicMock()
    bus.publish = AsyncMock()
    bus.subscribe = MagicMock()
    bus.unsubscribe = MagicMock()
    return bus


@pytest.fixture
def pipeline(event_bus):
    """Create VideoPublishPipeline instance."""
    return VideoPublishPipeline(event_bus=event_bus)


class TestVideoPublishPipelineInit:
    """Test BM-011: Pipeline initialization."""

    def test_initialization(self, pipeline):
        """BM-011: Pipeline should initialize correctly."""
        assert pipeline is not None
        assert not pipeline._is_running
        assert len(pipeline._jobs) == 0

    def test_singleton_pattern(self, event_bus):
        """BM-011: Should use singleton pattern."""
        p1 = VideoPublishPipeline.get_instance(event_bus=event_bus)
        p2 = VideoPublishPipeline.get_instance()
        assert p1 is p2

    def test_helper_function(self, event_bus):
        """BM-011: get_video_publish_pipeline should return singleton."""
        p = get_video_publish_pipeline(event_bus=event_bus)
        assert isinstance(p, VideoPublishPipeline)


class TestVideoPipelineJob:
    """Test BM-011: Job dataclass."""

    def test_job_creation(self):
        """BM-011: Job should create with defaults."""
        job = VideoPipelineJob(
            video_path="/tmp/test.mp4",
            target_platforms=["tiktok", "instagram"],
        )
        assert job.id.startswith("vpipe-")
        assert job.stage == PipelineStage.INITIALIZED
        assert job.video_path == "/tmp/test.mp4"
        assert len(job.target_platforms) == 2
        assert not job.approval_required

    def test_job_to_dict(self):
        """BM-011: Job should serialize to dict."""
        job = VideoPipelineJob(
            video_path="/tmp/test.mp4",
            target_platforms=["tiktok"],
            video_source="sora",
        )
        d = job.to_dict()
        assert d["video_source"] == "sora"
        assert d["target_platforms"] == ["tiktok"]
        assert d["stage"] == "initialized"

    def test_publish_result_counts(self):
        """BM-011: Should track successful and failed publishes."""
        job = VideoPipelineJob()
        job.publish_results = [
            PublishResult(platform="tiktok", success=True, post_url="https://tiktok.com/1"),
            PublishResult(platform="instagram", success=True, post_url="https://instagram.com/1"),
            PublishResult(platform="youtube", success=False, error="Upload failed"),
        ]
        assert job.successful_publishes == 2
        assert job.failed_publishes == 1


class TestPublishResult:
    """Test BM-011: PublishResult dataclass."""

    def test_success_result(self):
        """BM-011: Success result should have post_url."""
        result = PublishResult(
            platform="tiktok",
            success=True,
            post_url="https://tiktok.com/@user/video/123",
            account_id="710",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["post_url"] == "https://tiktok.com/@user/video/123"

    def test_failure_result(self):
        """BM-011: Failure result should have error."""
        result = PublishResult(
            platform="youtube",
            success=False,
            error="Quota exceeded",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "Quota exceeded"


class TestPipelineStages:
    """Test BM-011: Pipeline stages."""

    def test_all_stages(self):
        """BM-011: Should define all pipeline stages."""
        stages = [s.value for s in PipelineStage]
        assert "initialized" in stages
        assert "generating" in stages
        assert "analyzing" in stages
        assert "awaiting_approval" in stages
        assert "routing" in stages
        assert "publishing" in stages
        assert "completed" in stages
        assert "failed" in stages
        assert "rejected" in stages


class TestPipelineStartStop:
    """Test BM-011: Start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start(self, pipeline, event_bus):
        """BM-011: Start should subscribe to events."""
        await pipeline.start()
        assert pipeline._is_running
        assert event_bus.subscribe.call_count == 3  # pipeline, approved, rejected

    @pytest.mark.asyncio
    async def test_stop(self, pipeline):
        """BM-011: Stop should set not running."""
        await pipeline.start()
        await pipeline.stop()
        assert not pipeline._is_running


class TestRunPipeline:
    """Test BM-011: Pipeline execution."""

    @pytest.mark.asyncio
    async def test_run_pipeline_no_approval(self, pipeline, event_bus):
        """BM-011: Pipeline without approval should go directly to routing."""
        # Mock channel router via the module where it's imported
        mock_route_result = MagicMock()
        mock_tiktok = MagicMock(success=True, post_url="https://tiktok.com/1", account_id=None, error=None)
        mock_ig = MagicMock(success=True, post_url="https://instagram.com/1", account_id=None, error=None)
        mock_route_result.platform_results = {"tiktok": mock_tiktok, "instagram": mock_ig}

        with patch("services.channel_router.ChannelRouter") as MockRouter:
            mock_instance = MockRouter.get_instance.return_value
            mock_instance.route_content = AsyncMock(return_value=mock_route_result)

            job = await pipeline.run_pipeline(
                video_path="/tmp/test.mp4",
                target_platforms=["tiktok", "instagram"],
                analysis_override={"detected_hook": "Test", "hashtags": ["ai"]},
            )

        assert job.stage == PipelineStage.COMPLETED
        assert job.successful_publishes == 2
        assert "tiktok" in job.published_urls
        assert "instagram" in job.published_urls

    @pytest.mark.asyncio
    async def test_run_pipeline_with_approval(self, pipeline, event_bus):
        """BM-011: Pipeline with approval should pause at approval stage."""
        with patch("services.approval_queue.ApprovalQueue") as MockQueue:
            mock_queue = MockQueue.return_value
            mock_queue.add_item = AsyncMock(return_value="approval-123")

            job = await pipeline.run_pipeline(
                video_path="/tmp/test.mp4",
                target_platforms=["tiktok"],
                approval_required=True,
                analysis_override={"detected_hook": "Test"},
            )

        # Approval submission may fail gracefully, but stage should still be AWAITING_APPROVAL
        assert job.stage == PipelineStage.AWAITING_APPROVAL
        assert job.approval_id is not None

    @pytest.mark.asyncio
    async def test_run_pipeline_emits_events(self, pipeline, event_bus):
        """BM-011: Pipeline should emit lifecycle events."""
        mock_route_result = MagicMock()
        mock_route_result.platform_results = {}

        with patch("services.channel_router.ChannelRouter") as MockRouter:
            mock_instance = MockRouter.get_instance.return_value
            mock_instance.route_content = AsyncMock(return_value=mock_route_result)

            await pipeline.run_pipeline(
                video_path="/tmp/test.mp4",
                target_platforms=["tiktok"],
                analysis_override={"detected_hook": "Test"},
            )

        calls = [c.kwargs.get("topic", c.args[0] if c.args else "") for c in event_bus.publish.call_args_list]
        assert "video.pipeline.started" in calls
        assert "video.pipeline.completed" in calls

    @pytest.mark.asyncio
    async def test_run_pipeline_failure(self, pipeline, event_bus):
        """BM-011: Pipeline failure should emit failed event."""
        job = await pipeline.run_pipeline(
            video_path="",  # Empty path triggers ValueError
            target_platforms=["tiktok"],
        )

        assert job.stage == PipelineStage.FAILED
        assert job.error is not None

    @pytest.mark.asyncio
    async def test_run_pipeline_with_offer_url(self, pipeline, event_bus):
        """BM-011: Pipeline should pass offer_url through."""
        mock_route_result = MagicMock()
        mock_route_result.platform_results = {}

        with patch("services.channel_router.ChannelRouter") as MockRouter:
            mock_instance = MockRouter.get_instance.return_value
            mock_instance.route_content = AsyncMock(return_value=mock_route_result)

            job = await pipeline.run_pipeline(
                video_path="/tmp/test.mp4",
                target_platforms=["twitter"],
                offer_url="https://example.com/offer",
                analysis_override={"detected_hook": "Test"},
            )

        assert job.offer_url == "https://example.com/offer"

    @pytest.mark.asyncio
    async def test_run_pipeline_fallback_to_eventbus(self, pipeline, event_bus):
        """BM-011: Should fall back to EventBus when ChannelRouter unavailable."""
        # Simulate ImportError by patching the import to raise
        with patch.dict("sys.modules", {"services.channel_router": None}):
            job = await pipeline.run_pipeline(
                video_path="/tmp/test.mp4",
                target_platforms=["tiktok", "instagram"],
                analysis_override={"detected_hook": "Test"},
            )

        # Should still complete (optimistic publishing via events)
        assert job.stage == PipelineStage.COMPLETED
        assert len(job.publish_results) == 2


class TestApprovalHandling:
    """Test BM-011: Approval gate integration."""

    @pytest.mark.asyncio
    async def test_handle_approval_response(self, pipeline, event_bus):
        """BM-011: Approval should continue pipeline to publishing."""
        # Create a job in awaiting_approval state
        job = VideoPipelineJob(
            video_path="/tmp/test.mp4",
            target_platforms=["tiktok"],
            stage=PipelineStage.AWAITING_APPROVAL,
            approval_id="approval-xyz",
            approval_required=True,
            analysis={"detected_hook": "Test"},
        )
        pipeline._jobs[job.id] = job

        # Mock channel router for the publish step
        mock_route_result = MagicMock()
        mock_tiktok = MagicMock(success=True, post_url="https://tiktok.com/1", account_id=None, error=None)
        mock_route_result.platform_results = {"tiktok": mock_tiktok}

        with patch("services.channel_router.ChannelRouter") as MockRouter:
            mock_instance = MockRouter.get_instance.return_value
            mock_instance.route_content = AsyncMock(return_value=mock_route_result)

            # Simulate approval event
            mock_event = MagicMock()
            mock_event.payload = {"approval_id": "approval-xyz"}
            await pipeline._handle_approval_response(mock_event)

        assert job.stage == PipelineStage.COMPLETED

    @pytest.mark.asyncio
    async def test_handle_rejection_response(self, pipeline, event_bus):
        """BM-011: Rejection should mark pipeline as rejected."""
        job = VideoPipelineJob(
            video_path="/tmp/test.mp4",
            target_platforms=["tiktok"],
            stage=PipelineStage.AWAITING_APPROVAL,
            approval_id="approval-rej",
        )
        pipeline._jobs[job.id] = job

        mock_event = MagicMock()
        mock_event.payload = {
            "approval_id": "approval-rej",
            "reason": "Low quality",
        }
        await pipeline._handle_rejection_response(mock_event)

        assert job.stage == PipelineStage.REJECTED
        assert job.error == "Low quality"

    @pytest.mark.asyncio
    async def test_approval_unknown_id(self, pipeline):
        """BM-011: Unknown approval ID should be ignored."""
        mock_event = MagicMock()
        mock_event.payload = {"approval_id": "nonexistent"}
        # Should not raise
        await pipeline._handle_approval_response(mock_event)


class TestPipelineQueries:
    """Test BM-011: Query methods."""

    def test_get_job(self, pipeline):
        """BM-011: get_job should find tracked jobs."""
        job = VideoPipelineJob(video_path="/tmp/test.mp4")
        pipeline._jobs[job.id] = job
        assert pipeline.get_job(job.id) is not None

    def test_get_pending_approvals(self, pipeline):
        """BM-011: get_pending_approvals should filter correctly."""
        job1 = VideoPipelineJob(stage=PipelineStage.AWAITING_APPROVAL)
        job2 = VideoPipelineJob(stage=PipelineStage.COMPLETED)
        pipeline._jobs[job1.id] = job1
        pipeline._jobs[job2.id] = job2

        pending = pipeline.get_pending_approvals()
        assert len(pending) == 1
        assert pending[0].id == job1.id

    def test_get_stats(self, pipeline):
        """BM-011: get_stats should return pipeline statistics."""
        stats = pipeline.get_stats()
        assert stats["total_jobs"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["awaiting_approval"] == 0
