"""
Idempotency & De-duplication Tests
===================================
Ensure duplicate message delivery is harmless.

These tests verify:
- No duplicate scheduled posts
- No duplicate artifacts
- No duplicate "winner promoted" actions
- Exactly one "final state" for the run
- Unique constraints work correctly
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Any
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# IDEMPOTENCY INFRASTRUCTURE
# ============================================================================

class IdempotencyStore:
    """Track processed idempotency keys to prevent duplicate operations."""
    
    def __init__(self):
        self._processed: Set[str] = set()
        self._lock = asyncio.Lock()
    
    async def check_and_mark(self, key: str) -> bool:
        """
        Check if key was already processed. If not, mark it.
        Returns True if this is the first time (should process).
        Returns False if already processed (skip).
        """
        async with self._lock:
            if key in self._processed:
                return False
            self._processed.add(key)
            return True
    
    async def is_processed(self, key: str) -> bool:
        """Check if key was processed."""
        return key in self._processed
    
    def clear(self):
        """Clear all keys (for testing)."""
        self._processed.clear()


def generate_idempotency_key(run_id: str, step_key: str, operation: str) -> str:
    """Generate idempotency key for an operation."""
    return f"{run_id}:{step_key}:{operation}"


# ============================================================================
# SIMULATED SERVICES WITH IDEMPOTENCY
# ============================================================================

@dataclass
class ScheduledPost:
    """A scheduled post."""
    id: str
    run_id: str
    video_id: str
    platform: str
    scheduled_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Artifact:
    """A generated artifact."""
    id: str
    run_id: str
    step_key: str
    artifact_type: str
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SchedulerService:
    """Service that schedules posts with idempotency."""
    
    def __init__(self, idempotency_store: IdempotencyStore):
        self.store = idempotency_store
        self.scheduled_posts: List[ScheduledPost] = []
        self._lock = asyncio.Lock()
    
    async def schedule_post(
        self,
        run_id: str,
        video_id: str,
        platform: str,
        scheduled_at: datetime,
        idempotency_key: Optional[str] = None
    ) -> Optional[ScheduledPost]:
        """
        Schedule a post. Returns None if already scheduled (idempotent).
        """
        key = idempotency_key or f"{run_id}:{video_id}:{platform}"
        
        # Check idempotency
        should_process = await self.store.check_and_mark(key)
        if not should_process:
            return None  # Already processed
        
        async with self._lock:
            post = ScheduledPost(
                id=str(uuid4()),
                run_id=run_id,
                video_id=video_id,
                platform=platform,
                scheduled_at=scheduled_at,
            )
            self.scheduled_posts.append(post)
            return post
    
    def get_posts_for_run(self, run_id: str) -> List[ScheduledPost]:
        """Get all posts for a run."""
        return [p for p in self.scheduled_posts if p.run_id == run_id]


class ArtifactService:
    """Service that creates artifacts with idempotency."""
    
    def __init__(self, idempotency_store: IdempotencyStore):
        self.store = idempotency_store
        self.artifacts: List[Artifact] = []
        self._lock = asyncio.Lock()
    
    async def create_artifact(
        self,
        run_id: str,
        step_key: str,
        artifact_type: str,
        data: Dict[str, Any]
    ) -> Optional[Artifact]:
        """
        Create an artifact. Returns None if already created (idempotent).
        """
        key = f"{run_id}:{step_key}:{artifact_type}"
        
        should_process = await self.store.check_and_mark(key)
        if not should_process:
            return None
        
        async with self._lock:
            artifact = Artifact(
                id=str(uuid4()),
                run_id=run_id,
                step_key=step_key,
                artifact_type=artifact_type,
                data=data,
            )
            self.artifacts.append(artifact)
            return artifact
    
    def get_artifacts_for_run(self, run_id: str) -> List[Artifact]:
        """Get all artifacts for a run."""
        return [a for a in self.artifacts if a.run_id == run_id]


class RunStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class Run:
    """A workflow run with final state."""
    id: str
    status: RunStatus = RunStatus.RUNNING
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


class RunManager:
    """Manages runs with idempotent completion."""
    
    def __init__(self):
        self.runs: Dict[str, Run] = {}
        self._lock = asyncio.Lock()
    
    async def create_run(self, run_id: str) -> Run:
        """Create a new run."""
        async with self._lock:
            run = Run(id=run_id)
            self.runs[run_id] = run
            return run
    
    async def complete_run(
        self,
        run_id: str,
        status: RunStatus,
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Complete a run. Returns True if status changed, False if already terminal.
        This is idempotent - calling twice returns False the second time.
        """
        async with self._lock:
            run = self.runs.get(run_id)
            if not run:
                return False
            
            # Already in terminal state
            if run.status in (RunStatus.SUCCEEDED, RunStatus.FAILED):
                return False
            
            run.status = status
            run.completed_at = datetime.now(timezone.utc)
            run.result = result
            return True
    
    def get_run(self, run_id: str) -> Optional[Run]:
        """Get run by ID."""
        return self.runs.get(run_id)


class ExperimentService:
    """Service for experiment winner promotion with idempotency."""
    
    def __init__(self, idempotency_store: IdempotencyStore):
        self.store = idempotency_store
        self.promotions: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
    
    async def promote_winner(
        self,
        experiment_id: str,
        winner_variant_id: str,
        metrics: Dict[str, float]
    ) -> bool:
        """
        Promote experiment winner. Idempotent - only promotes once.
        Returns True if promoted, False if already promoted.
        """
        key = f"experiment:{experiment_id}:promote"
        
        should_process = await self.store.check_and_mark(key)
        if not should_process:
            return False
        
        async with self._lock:
            self.promotions.append({
                "experiment_id": experiment_id,
                "winner_variant_id": winner_variant_id,
                "metrics": metrics,
                "promoted_at": datetime.now(timezone.utc).isoformat(),
            })
            return True
    
    def get_promotion(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get promotion for experiment."""
        for p in self.promotions:
            if p["experiment_id"] == experiment_id:
                return p
        return None


# ============================================================================
# TESTS
# ============================================================================

class TestSchedulerIdempotency:
    """Test scheduler creates no duplicate posts."""
    
    @pytest.fixture
    def store(self):
        return IdempotencyStore()
    
    @pytest.fixture
    def scheduler(self, store):
        return SchedulerService(store)
    
    @pytest.mark.asyncio
    async def test_same_post_not_scheduled_twice(self, scheduler):
        """Same post request twice should only create one post."""
        run_id = str(uuid4())
        video_id = "vid-123"
        platform = "tiktok"
        scheduled_at = datetime.now(timezone.utc)
        
        # First call creates post
        post1 = await scheduler.schedule_post(run_id, video_id, platform, scheduled_at)
        assert post1 is not None
        
        # Second call returns None (already scheduled)
        post2 = await scheduler.schedule_post(run_id, video_id, platform, scheduled_at)
        assert post2 is None
        
        # Only one post exists
        posts = scheduler.get_posts_for_run(run_id)
        assert len(posts) == 1
    
    @pytest.mark.asyncio
    async def test_different_posts_both_scheduled(self, scheduler):
        """Different posts should both be scheduled."""
        run_id = str(uuid4())
        scheduled_at = datetime.now(timezone.utc)
        
        post1 = await scheduler.schedule_post(run_id, "vid-1", "tiktok", scheduled_at)
        post2 = await scheduler.schedule_post(run_id, "vid-2", "tiktok", scheduled_at)
        
        assert post1 is not None
        assert post2 is not None
        
        posts = scheduler.get_posts_for_run(run_id)
        assert len(posts) == 2
    
    @pytest.mark.asyncio
    async def test_same_video_different_platform_both_scheduled(self, scheduler):
        """Same video on different platforms should both be scheduled."""
        run_id = str(uuid4())
        video_id = "vid-123"
        scheduled_at = datetime.now(timezone.utc)
        
        post1 = await scheduler.schedule_post(run_id, video_id, "tiktok", scheduled_at)
        post2 = await scheduler.schedule_post(run_id, video_id, "instagram", scheduled_at)
        
        assert post1 is not None
        assert post2 is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_duplicate_requests(self, scheduler):
        """Concurrent duplicate requests should only create one post."""
        run_id = str(uuid4())
        video_id = "vid-123"
        platform = "tiktok"
        scheduled_at = datetime.now(timezone.utc)
        
        # Simulate 10 concurrent duplicate requests
        results = await asyncio.gather(*[
            scheduler.schedule_post(run_id, video_id, platform, scheduled_at)
            for _ in range(10)
        ])
        
        # Only one should have succeeded
        created = [r for r in results if r is not None]
        assert len(created) == 1
        
        # Only one post in storage
        posts = scheduler.get_posts_for_run(run_id)
        assert len(posts) == 1


class TestArtifactIdempotency:
    """Test artifact creation is idempotent."""
    
    @pytest.fixture
    def store(self):
        return IdempotencyStore()
    
    @pytest.fixture
    def artifact_service(self, store):
        return ArtifactService(store)
    
    @pytest.mark.asyncio
    async def test_same_artifact_not_created_twice(self, artifact_service):
        """Same artifact request twice should only create one."""
        run_id = str(uuid4())
        
        artifact1 = await artifact_service.create_artifact(
            run_id, "planning", "weekly_plan", {"slots": 7}
        )
        artifact2 = await artifact_service.create_artifact(
            run_id, "planning", "weekly_plan", {"slots": 7}
        )
        
        assert artifact1 is not None
        assert artifact2 is None
        
        artifacts = artifact_service.get_artifacts_for_run(run_id)
        assert len(artifacts) == 1
    
    @pytest.mark.asyncio
    async def test_different_artifact_types_both_created(self, artifact_service):
        """Different artifact types should both be created."""
        run_id = str(uuid4())
        
        artifact1 = await artifact_service.create_artifact(
            run_id, "planning", "weekly_plan", {"slots": 7}
        )
        artifact2 = await artifact_service.create_artifact(
            run_id, "planning", "rejection_log", {"rejected": 3}
        )
        
        assert artifact1 is not None
        assert artifact2 is not None


class TestRunFinalState:
    """Test run has exactly one final state."""
    
    @pytest.fixture
    def run_manager(self):
        return RunManager()
    
    @pytest.mark.asyncio
    async def test_run_can_only_complete_once(self, run_manager):
        """Run can only transition to terminal state once."""
        run_id = str(uuid4())
        await run_manager.create_run(run_id)
        
        # First completion succeeds
        result1 = await run_manager.complete_run(run_id, RunStatus.SUCCEEDED)
        assert result1 is True
        
        # Second completion fails (already terminal)
        result2 = await run_manager.complete_run(run_id, RunStatus.FAILED)
        assert result2 is False
        
        # Status is still succeeded (first completion)
        run = run_manager.get_run(run_id)
        assert run.status == RunStatus.SUCCEEDED
    
    @pytest.mark.asyncio
    async def test_concurrent_completions_only_one_wins(self, run_manager):
        """Concurrent completion attempts should only succeed once."""
        run_id = str(uuid4())
        await run_manager.create_run(run_id)
        
        # Simulate concurrent completion attempts
        results = await asyncio.gather(*[
            run_manager.complete_run(run_id, RunStatus.SUCCEEDED)
            for _ in range(10)
        ])
        
        # Only one should have succeeded
        successes = [r for r in results if r is True]
        assert len(successes) == 1
        
        # Run has valid terminal state
        run = run_manager.get_run(run_id)
        assert run.status == RunStatus.SUCCEEDED
        assert run.completed_at is not None


class TestExperimentPromotionIdempotency:
    """Test experiment winner promotion is idempotent."""
    
    @pytest.fixture
    def store(self):
        return IdempotencyStore()
    
    @pytest.fixture
    def experiment_service(self, store):
        return ExperimentService(store)
    
    @pytest.mark.asyncio
    async def test_winner_promoted_only_once(self, experiment_service):
        """Winner should only be promoted once."""
        experiment_id = str(uuid4())
        
        result1 = await experiment_service.promote_winner(
            experiment_id, "variant-a", {"conversion_rate": 0.15}
        )
        result2 = await experiment_service.promote_winner(
            experiment_id, "variant-a", {"conversion_rate": 0.15}
        )
        
        assert result1 is True
        assert result2 is False
        
        # Only one promotion exists
        promotion = experiment_service.get_promotion(experiment_id)
        assert promotion is not None
        assert len(experiment_service.promotions) == 1
    
    @pytest.mark.asyncio
    async def test_different_winners_not_allowed(self, experiment_service):
        """Cannot promote different winner for same experiment."""
        experiment_id = str(uuid4())
        
        # First promotion
        result1 = await experiment_service.promote_winner(
            experiment_id, "variant-a", {"conversion_rate": 0.15}
        )
        
        # Try to promote different variant
        result2 = await experiment_service.promote_winner(
            experiment_id, "variant-b", {"conversion_rate": 0.12}
        )
        
        assert result1 is True
        assert result2 is False  # Blocked by idempotency
        
        # Original winner preserved
        promotion = experiment_service.get_promotion(experiment_id)
        assert promotion["winner_variant_id"] == "variant-a"


class TestIdempotencyKeyGeneration:
    """Test idempotency key generation patterns."""
    
    def test_key_includes_run_step_operation(self):
        """Key should include run, step, and operation."""
        key = generate_idempotency_key("run-123", "planning", "create_plan")
        assert "run-123" in key
        assert "planning" in key
        assert "create_plan" in key
    
    def test_same_inputs_same_key(self):
        """Same inputs should produce same key."""
        key1 = generate_idempotency_key("run-123", "step-a", "op-x")
        key2 = generate_idempotency_key("run-123", "step-a", "op-x")
        assert key1 == key2
    
    def test_different_inputs_different_keys(self):
        """Different inputs should produce different keys."""
        key1 = generate_idempotency_key("run-123", "step-a", "op-x")
        key2 = generate_idempotency_key("run-456", "step-a", "op-x")
        assert key1 != key2


class TestIdempotencyStore:
    """Test IdempotencyStore behavior."""
    
    @pytest.fixture
    def store(self):
        return IdempotencyStore()
    
    @pytest.mark.asyncio
    async def test_first_check_returns_true(self, store):
        """First check should return True (process it)."""
        result = await store.check_and_mark("key-1")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_second_check_returns_false(self, store):
        """Second check should return False (skip it)."""
        await store.check_and_mark("key-1")
        result = await store.check_and_mark("key-1")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_different_keys_both_process(self, store):
        """Different keys should both be processed."""
        result1 = await store.check_and_mark("key-1")
        result2 = await store.check_and_mark("key-2")
        assert result1 is True
        assert result2 is True
    
    @pytest.mark.asyncio
    async def test_concurrent_same_key_only_one_processes(self, store):
        """Concurrent checks for same key should only allow one."""
        results = await asyncio.gather(*[
            store.check_and_mark("key-1") for _ in range(100)
        ])
        
        processed = [r for r in results if r is True]
        assert len(processed) == 1
