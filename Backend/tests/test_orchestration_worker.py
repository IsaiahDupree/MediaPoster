"""
Orchestration Worker Tests
==========================
Unit tests for orchestration worker and queue.

Run tests:
    pytest tests/test_orchestration_worker.py -v
"""

import asyncio
import pytest
from uuid import uuid4
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# WORKER CONFIG TESTS
# =============================================================================

class TestWorkerConfig:
    """Test WorkerConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration."""
        from services.video_orchestrator.orchestration_worker import WorkerConfig
        
        config = WorkerConfig()
        
        assert config.max_concurrent_clips == 3
        assert config.poll_interval_seconds == 2.0
        assert config.max_retries_per_clip == 3
        assert config.assessment_enabled is True
        assert config.auto_retry_enabled is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        from services.video_orchestrator.orchestration_worker import WorkerConfig
        
        config = WorkerConfig(
            max_concurrent_clips=5,
            max_retries_per_clip=5,
            assessment_enabled=False
        )
        
        assert config.max_concurrent_clips == 5
        assert config.max_retries_per_clip == 5
        assert config.assessment_enabled is False


# =============================================================================
# WORKER PROGRESS TESTS
# =============================================================================

class TestWorkerProgress:
    """Test WorkerProgress dataclass."""
    
    def test_progress_creation(self):
        """Test progress creation."""
        from services.video_orchestrator.orchestration_worker import WorkerProgress
        
        progress = WorkerProgress(
            plan_id="plan_123",
            status="running",
            total_clips=10,
            completed_clips=3,
            failed_clips=1
        )
        
        assert progress.plan_id == "plan_123"
        assert progress.total_clips == 10
        assert progress.completed_clips == 3
    
    def test_to_dict(self):
        """Test progress serialization."""
        from services.video_orchestrator.orchestration_worker import WorkerProgress
        from datetime import datetime
        
        progress = WorkerProgress(
            plan_id="plan_123",
            status="running",
            total_clips=10,
            completed_clips=5,
            failed_clips=1,
            started_at=datetime.utcnow()
        )
        
        data = progress.to_dict()
        
        assert data["plan_id"] == "plan_123"
        assert data["pending_clips"] == 4  # 10 - 5 - 1
        assert "started_at" in data


# =============================================================================
# WORKER EVENT TESTS
# =============================================================================

class TestWorkerEvents:
    """Test worker event system."""
    
    def test_event_enum_values(self):
        """Test WorkerEvent enum values."""
        from services.video_orchestrator.orchestration_worker import WorkerEvent
        
        assert WorkerEvent.PLAN_STARTED.value == "plan_started"
        assert WorkerEvent.CLIP_COMPLETED.value == "clip_completed"
        assert WorkerEvent.PROGRESS_UPDATE.value == "progress_update"
    
    def test_event_callback_registration(self):
        """Test event callback registration."""
        from services.video_orchestrator.orchestration_worker import OrchestrationWorker
        
        worker = OrchestrationWorker()
        events_received = []
        
        def callback(event, data):
            events_received.append((event, data))
        
        worker.on_event(callback)
        
        # Emit a test event
        from services.video_orchestrator.orchestration_worker import WorkerEvent
        worker._emit_event(WorkerEvent.PLAN_STARTED, {"plan_id": "test"})
        
        assert len(events_received) == 1
        assert events_received[0][0] == WorkerEvent.PLAN_STARTED


# =============================================================================
# ORCHESTRATION WORKER TESTS
# =============================================================================

class TestOrchestrationWorker:
    """Test OrchestrationWorker."""
    
    @pytest.fixture
    def worker(self):
        """Create worker instance."""
        from services.video_orchestrator.orchestration_worker import (
            OrchestrationWorker, WorkerConfig
        )
        from services.video_orchestrator.models import ProviderName
        
        config = WorkerConfig(
            max_concurrent_clips=2,
            poll_interval_seconds=0.1,
            max_retries_per_clip=2,
            assessment_enabled=False  # Disable for faster tests
        )
        
        from services.video_providers.mock_provider import MockVideoProvider

        return OrchestrationWorker(
            config=config,
            provider_instance=MockVideoProvider(simulate_delay=0, processing_steps=2)
        )
    
    @pytest.fixture
    def sample_plan_data(self):
        """Create sample plan, scene, and clips."""
        from services.video_orchestrator.models import (
            ClipPlan, Scene, ClipPlanClip, VideoProject,
            NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName,
            PlanStatus, ClipState
        )
        
        project_id = uuid4()
        plan_id = uuid4()
        scene_id = uuid4()
        
        plan = ClipPlan(
            id=plan_id,
            project_id=project_id,
            status=PlanStatus.READY
        )
        
        scene = Scene(
            id=scene_id,
            clip_plan_id=plan_id,
            name="Test Scene",
            scene_order=0
        )
        
        clips = [
            ClipPlanClip(
                id=uuid4(),
                scene_id=scene_id,
                clip_order=i,
                target_seconds=4,
                narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
                visual_intent=VisualIntent(prompt=f"Test clip {i}"),
                provider_hints=ProviderHints(primary_provider=ProviderName.MOCK),
                acceptance=AcceptanceCriteria(),
                state=ClipState.PENDING
            )
            for i in range(3)
        ]
        
        return {"plan": plan, "scene": scene, "clips": clips}
    
    def test_worker_creation(self, worker):
        """Test worker creation."""
        assert worker.config.max_concurrent_clips == 2
        assert worker.config.assessment_enabled is False
    
    def test_get_progress_none(self, worker):
        """Test getting progress for non-existent plan."""
        progress = worker.get_progress("nonexistent")
        assert progress is None
    
    def test_is_running_false(self, worker):
        """Test is_running returns False for non-running plan."""
        assert worker.is_running("nonexistent") is False
    
    @pytest.mark.asyncio
    async def test_run_clip_plan(self, worker, sample_plan_data):
        """Test running a clip plan."""
        events_received = []
        
        def callback(event, data):
            events_received.append((event, data))
        
        worker.on_event(callback)
        
        result = await worker.run_clip_plan(
            sample_plan_data["plan"],
            [sample_plan_data["scene"]],
            sample_plan_data["clips"]
        )
        
        # Should complete (using mock provider)
        assert result is True
        
        # Check events
        event_types = [e[0].value for e in events_received]
        assert "plan_started" in event_types
        assert "clip_started" in event_types
        assert "plan_completed" in event_types or "plan_failed" in event_types
    
    @pytest.mark.asyncio
    async def test_run_clip_plan_progress(self, worker, sample_plan_data):
        """Test progress tracking during plan execution."""
        plan_id = str(sample_plan_data["plan"].id)
        
        # Start plan in background
        task = asyncio.create_task(worker.run_clip_plan(
            sample_plan_data["plan"],
            [sample_plan_data["scene"]],
            sample_plan_data["clips"]
        ))
        
        # Wait briefly then check progress
        await asyncio.sleep(0.1)
        
        progress = worker.get_progress(plan_id)
        assert progress is not None
        assert progress.total_clips == 3
        
        # Wait for completion
        await task
    
    @pytest.mark.asyncio
    async def test_prevent_duplicate_run(self, worker, sample_plan_data):
        """Test that same plan can't run twice simultaneously."""
        # Start first run
        task1 = asyncio.create_task(worker.run_clip_plan(
            sample_plan_data["plan"],
            [sample_plan_data["scene"]],
            sample_plan_data["clips"]
        ))
        
        await asyncio.sleep(0.05)
        
        # Try to start second run
        result2 = await worker.run_clip_plan(
            sample_plan_data["plan"],
            [sample_plan_data["scene"]],
            sample_plan_data["clips"]
        )
        
        # Second run should be rejected
        assert result2 is False
        
        # Wait for first to complete
        await task1


# =============================================================================
# ORCHESTRATION QUEUE TESTS
# =============================================================================

class TestOrchestrationQueue:
    """Test OrchestrationQueue."""
    
    @pytest.fixture
    def queue(self):
        """Create queue instance."""
        from services.video_orchestrator.orchestration_worker import (
            OrchestrationQueue, OrchestrationWorker, WorkerConfig
        )
        from services.video_orchestrator.models import ProviderName
        
        config = WorkerConfig(
            max_concurrent_clips=1,
            poll_interval_seconds=0.1,
            assessment_enabled=False
        )
        
        from services.video_providers.mock_provider import MockVideoProvider

        worker = OrchestrationWorker(
            config=config,
            provider_instance=MockVideoProvider(simulate_delay=0, processing_steps=2)
        )
        return OrchestrationQueue(worker=worker, max_workers=1)
    
    def test_queue_creation(self, queue):
        """Test queue creation."""
        assert queue.max_workers == 1
        assert queue._running is False
    
    def test_get_queue_status(self, queue):
        """Test queue status."""
        status = queue.get_queue_status()
        
        assert "running" in status
        assert "queued" in status
        assert "active" in status
        assert "completed" in status
    
    @pytest.mark.asyncio
    async def test_queue_start_stop(self, queue):
        """Test starting and stopping queue."""
        await queue.start()
        assert queue._running is True
        
        await queue.stop()
        assert queue._running is False
    
    @pytest.mark.asyncio
    async def test_enqueue_job(self, queue):
        """Test enqueueing a job."""
        from services.video_orchestrator.models import (
            ClipPlan, Scene, ClipPlanClip, NarrationConfig,
            VisualIntent, ProviderHints, AcceptanceCriteria,
            NarrationMode, ProviderName, PlanStatus, ClipState
        )
        
        plan_id = uuid4()
        scene_id = uuid4()
        
        plan = ClipPlan(id=plan_id, project_id=uuid4(), status=PlanStatus.READY)
        scene = Scene(id=scene_id, clip_plan_id=plan_id, name="Test", scene_order=0)
        clips = [
            ClipPlanClip(
                id=uuid4(),
                scene_id=scene_id,
                clip_order=0,
                target_seconds=4,
                narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
                visual_intent=VisualIntent(prompt="Test"),
                provider_hints=ProviderHints(primary_provider=ProviderName.MOCK),
                acceptance=AcceptanceCriteria(),
                state=ClipState.PENDING
            )
        ]
        
        await queue.start()
        
        job_id = await queue.enqueue(plan, [scene], clips)
        
        assert job_id == str(plan_id)
        
        # Wait for processing
        await asyncio.sleep(1)
        
        await queue.stop()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestWorkerIntegration:
    """Integration tests for worker system."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test full worker workflow with multiple clips."""
        from services.video_orchestrator.orchestration_worker import (
            OrchestrationWorker, WorkerConfig, WorkerEvent
        )
        from services.video_orchestrator.models import (
            ClipPlan, Scene, ClipPlanClip, NarrationConfig,
            VisualIntent, ProviderHints, AcceptanceCriteria,
            NarrationMode, ProviderName, PlanStatus, ClipState
        )
        
        # Create worker
        config = WorkerConfig(
            max_concurrent_clips=2,
            poll_interval_seconds=0.1,
            assessment_enabled=False
        )
        from services.video_providers.mock_provider import MockVideoProvider

        worker = OrchestrationWorker(
            config=config,
            provider_instance=MockVideoProvider(simulate_delay=0, processing_steps=2)
        )

        # Track events
        events = []
        worker.on_event(lambda e, d: events.append(e))
        
        # Create plan
        plan_id = uuid4()
        scene_id = uuid4()
        
        plan = ClipPlan(id=plan_id, project_id=uuid4(), status=PlanStatus.READY)
        scene = Scene(id=scene_id, clip_plan_id=plan_id, name="Main", scene_order=0)
        clips = [
            ClipPlanClip(
                id=uuid4(),
                scene_id=scene_id,
                clip_order=i,
                target_seconds=4,
                narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
                visual_intent=VisualIntent(prompt=f"Scene {i}"),
                provider_hints=ProviderHints(primary_provider=ProviderName.MOCK),
                acceptance=AcceptanceCriteria(),
                state=ClipState.PENDING
            )
            for i in range(4)
        ]
        
        # Run
        result = await worker.run_clip_plan(plan, [scene], clips)
        
        # Verify
        assert result is True
        assert WorkerEvent.PLAN_STARTED in events
        assert WorkerEvent.PLAN_COMPLETED in events
        
        # All clips should be processed
        progress = worker.get_progress(str(plan_id))
        assert progress.completed_clips == 4


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
