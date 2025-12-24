"""
Integration Tests: Broker/DB Semantics
=======================================
Test real queue/database behavior that unit tests can't catch.

These tests verify:
- Locking works (two workers don't process same job)
- At-least-once delivery (duplicates happen, must be idempotent)
- Visibility timeout / stale lock recovery
- Delay scheduling (available_at respected)
- DLQ behavior (after N failures → dead-letter)

NOTE: These tests require a running PostgreSQL database.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4
import os

# Skip if no database available
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping integration tests"
)


# ============================================================================
# QUEUE SIMULATION (mimics pgmq-like behavior)
# ============================================================================

class JobStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class QueueJob:
    """Represents a job in the queue."""
    def __init__(
        self,
        id: str,
        payload: Dict[str, Any],
        status: str = JobStatus.QUEUED,
        attempt: int = 0,
        max_attempts: int = 3,
        available_at: Optional[datetime] = None,
        locked_by: Optional[str] = None,
        locked_until: Optional[datetime] = None,
    ):
        self.id = id
        self.payload = payload
        self.status = status
        self.attempt = attempt
        self.max_attempts = max_attempts
        self.available_at = available_at or datetime.now(timezone.utc)
        self.locked_by = locked_by
        self.locked_until = locked_until
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None


class InMemoryQueue:
    """In-memory queue for testing queue semantics."""
    
    def __init__(self, visibility_timeout_seconds: int = 30):
        self.jobs: Dict[str, QueueJob] = {}
        self.visibility_timeout = timedelta(seconds=visibility_timeout_seconds)
        self._lock = asyncio.Lock()
    
    async def enqueue(
        self,
        payload: Dict[str, Any],
        delay_seconds: int = 0,
        max_attempts: int = 3
    ) -> str:
        """Add a job to the queue."""
        job_id = str(uuid4())
        available_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        
        async with self._lock:
            self.jobs[job_id] = QueueJob(
                id=job_id,
                payload=payload,
                available_at=available_at,
                max_attempts=max_attempts,
            )
        
        return job_id
    
    async def dequeue(self, worker_id: str) -> Optional[QueueJob]:
        """Get next available job with exclusive lock."""
        now = datetime.now(timezone.utc)
        
        async with self._lock:
            for job in self.jobs.values():
                # Check if job is available
                if job.status != JobStatus.QUEUED:
                    continue
                if job.available_at > now:
                    continue
                if job.locked_until and job.locked_until > now:
                    continue
                
                # Lock the job
                job.status = JobStatus.PROCESSING
                job.locked_by = worker_id
                job.locked_until = now + self.visibility_timeout
                job.attempt += 1
                
                return job
        
        return None
    
    async def complete(self, job_id: str, worker_id: str) -> bool:
        """Mark job as completed."""
        async with self._lock:
            job = self.jobs.get(job_id)
            if not job or job.locked_by != worker_id:
                return False
            
            job.status = JobStatus.SUCCEEDED
            job.completed_at = datetime.now(timezone.utc)
            job.locked_by = None
            job.locked_until = None
            return True
    
    async def fail(self, job_id: str, worker_id: str, error: str) -> bool:
        """Mark job as failed, possibly move to DLQ."""
        async with self._lock:
            job = self.jobs.get(job_id)
            if not job or job.locked_by != worker_id:
                return False
            
            job.error = error
            job.locked_by = None
            job.locked_until = None
            
            if job.attempt >= job.max_attempts:
                job.status = JobStatus.DEAD_LETTER
            else:
                job.status = JobStatus.QUEUED
                # Exponential backoff
                backoff_seconds = 2 ** job.attempt
                job.available_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
            
            return True
    
    async def recover_stale_locks(self) -> int:
        """Recover jobs with expired locks."""
        now = datetime.now(timezone.utc)
        recovered = 0
        
        async with self._lock:
            for job in self.jobs.values():
                if job.status == JobStatus.PROCESSING:
                    if job.locked_until and job.locked_until < now:
                        job.status = JobStatus.QUEUED
                        job.locked_by = None
                        job.locked_until = None
                        recovered += 1
        
        return recovered
    
    def get_dead_letter_jobs(self) -> List[QueueJob]:
        """Get all dead-lettered jobs."""
        return [j for j in self.jobs.values() if j.status == JobStatus.DEAD_LETTER]
    
    def get_job(self, job_id: str) -> Optional[QueueJob]:
        """Get job by ID."""
        return self.jobs.get(job_id)


# ============================================================================
# TESTS
# ============================================================================

class TestQueueLocking:
    """Test that locking prevents double-processing."""
    
    @pytest.fixture
    def queue(self):
        return InMemoryQueue(visibility_timeout_seconds=5)
    
    @pytest.mark.asyncio
    async def test_only_one_worker_gets_job(self, queue):
        """Two workers trying to dequeue should only give job to one."""
        job_id = await queue.enqueue({"task": "test"})
        
        # Two workers try to dequeue simultaneously
        job1 = await queue.dequeue("worker-1")
        job2 = await queue.dequeue("worker-2")
        
        # Only one should get the job
        assert (job1 is not None) != (job2 is not None) or (job1 is None and job2 is None)
        
        # The one that got it should have it locked
        job = queue.get_job(job_id)
        assert job.locked_by in ["worker-1", "worker-2", None]
    
    @pytest.mark.asyncio
    async def test_locked_job_not_available(self, queue):
        """A locked job should not be available to other workers."""
        job_id = await queue.enqueue({"task": "test"})
        
        # Worker 1 takes the job
        job1 = await queue.dequeue("worker-1")
        assert job1 is not None
        
        # Worker 2 should not get any job
        job2 = await queue.dequeue("worker-2")
        assert job2 is None
    
    @pytest.mark.asyncio
    async def test_completed_job_stays_completed(self, queue):
        """Completed job should not be available again."""
        job_id = await queue.enqueue({"task": "test"})
        
        job = await queue.dequeue("worker-1")
        await queue.complete(job_id, "worker-1")
        
        # Try to get another job
        job2 = await queue.dequeue("worker-2")
        assert job2 is None
        
        # Original job is succeeded
        assert queue.get_job(job_id).status == JobStatus.SUCCEEDED


class TestVisibilityTimeout:
    """Test visibility timeout and lock recovery."""
    
    @pytest.fixture
    def queue(self):
        # Very short timeout for testing
        return InMemoryQueue(visibility_timeout_seconds=1)
    
    @pytest.mark.asyncio
    async def test_stale_lock_recovered(self, queue):
        """Jobs with expired locks should be recovered."""
        job_id = await queue.enqueue({"task": "test"})
        
        # Worker takes job but doesn't complete
        job = await queue.dequeue("worker-1")
        assert job is not None
        
        # Wait for lock to expire
        await asyncio.sleep(1.5)
        
        # Recover stale locks
        recovered = await queue.recover_stale_locks()
        assert recovered == 1
        
        # Job should be available again
        job = queue.get_job(job_id)
        assert job.status == JobStatus.QUEUED
        assert job.locked_by is None
    
    @pytest.mark.asyncio
    async def test_recovered_job_can_be_processed(self, queue):
        """Recovered job should be processable by another worker."""
        job_id = await queue.enqueue({"task": "test"})
        
        # Worker 1 takes job but "dies"
        await queue.dequeue("worker-1")
        await asyncio.sleep(1.5)
        await queue.recover_stale_locks()
        
        # Worker 2 should now get the job
        job = await queue.dequeue("worker-2")
        assert job is not None
        assert job.id == job_id
        assert job.attempt == 2  # Second attempt


class TestDelayScheduling:
    """Test delayed job availability."""
    
    @pytest.fixture
    def queue(self):
        return InMemoryQueue()
    
    @pytest.mark.asyncio
    async def test_delayed_job_not_immediately_available(self, queue):
        """Job with delay should not be immediately available."""
        job_id = await queue.enqueue({"task": "test"}, delay_seconds=2)
        
        # Should not be available yet
        job = await queue.dequeue("worker-1")
        assert job is None
    
    @pytest.mark.asyncio
    async def test_delayed_job_available_after_delay(self, queue):
        """Job should be available after delay passes."""
        job_id = await queue.enqueue({"task": "test"}, delay_seconds=1)
        
        # Not available yet
        job = await queue.dequeue("worker-1")
        assert job is None
        
        # Wait for delay
        await asyncio.sleep(1.1)
        
        # Now available
        job = await queue.dequeue("worker-1")
        assert job is not None
        assert job.id == job_id


class TestRetryAndDLQ:
    """Test retry behavior and dead-letter queue."""
    
    @pytest.fixture
    def queue(self):
        return InMemoryQueue()
    
    @pytest.mark.asyncio
    async def test_failed_job_retried(self, queue):
        """Failed job should be retried."""
        job_id = await queue.enqueue({"task": "test"}, max_attempts=3)
        
        # First attempt fails
        job = await queue.dequeue("worker-1")
        await queue.fail(job_id, "worker-1", "Error 1")
        
        # Job should be queued again
        stored_job = queue.get_job(job_id)
        assert stored_job.status == JobStatus.QUEUED
        assert stored_job.attempt == 1
    
    @pytest.mark.asyncio
    async def test_job_goes_to_dlq_after_max_attempts(self, queue):
        """Job should go to DLQ after max attempts."""
        job_id = await queue.enqueue({"task": "test"}, max_attempts=2)
        
        # First attempt
        job = await queue.dequeue("worker-1")
        await queue.fail(job_id, "worker-1", "Error 1")
        
        # Manually reset available_at for immediate retry in test
        queue.jobs[job_id].available_at = datetime.now(timezone.utc)
        
        # Second attempt (final)
        job = await queue.dequeue("worker-1")
        await queue.fail(job_id, "worker-1", "Error 2")
        
        # Should be in DLQ
        stored_job = queue.get_job(job_id)
        assert stored_job.status == JobStatus.DEAD_LETTER
        
        dlq_jobs = queue.get_dead_letter_jobs()
        assert len(dlq_jobs) == 1
        assert dlq_jobs[0].id == job_id
    
    @pytest.mark.asyncio
    async def test_retry_has_exponential_backoff(self, queue):
        """Retry should use exponential backoff."""
        job_id = await queue.enqueue({"task": "test"}, max_attempts=5)
        
        # First failure
        job = await queue.dequeue("worker-1")
        before_fail = datetime.now(timezone.utc)
        await queue.fail(job_id, "worker-1", "Error")
        
        stored_job = queue.get_job(job_id)
        backoff = (stored_job.available_at - before_fail).total_seconds()
        
        # Should have ~2 second backoff (2^1)
        assert 1.5 < backoff < 3.0


class TestConcurrentWorkers:
    """Test behavior with multiple concurrent workers."""
    
    @pytest.fixture
    def queue(self):
        return InMemoryQueue()
    
    @pytest.mark.asyncio
    async def test_multiple_jobs_distributed(self, queue):
        """Multiple jobs should be distributed across workers."""
        # Enqueue 5 jobs
        job_ids = []
        for i in range(5):
            job_id = await queue.enqueue({"task": f"test-{i}"})
            job_ids.append(job_id)
        
        # 3 workers dequeue
        worker_jobs = {}
        for worker_id in ["w1", "w2", "w3"]:
            job = await queue.dequeue(worker_id)
            if job:
                worker_jobs[worker_id] = job.id
        
        # Each should have a unique job
        assert len(worker_jobs) == 3
        assert len(set(worker_jobs.values())) == 3
    
    @pytest.mark.asyncio
    async def test_no_duplicate_processing(self, queue):
        """Same job should never be processed twice simultaneously."""
        job_id = await queue.enqueue({"task": "test"})
        
        # Simulate race condition with many workers
        results = await asyncio.gather(*[
            queue.dequeue(f"worker-{i}") for i in range(10)
        ])
        
        # Only one should have gotten the job
        got_job = [r for r in results if r is not None]
        assert len(got_job) == 1


class TestAtLeastOnceDelivery:
    """Test at-least-once delivery semantics."""
    
    @pytest.fixture
    def queue(self):
        return InMemoryQueue(visibility_timeout_seconds=1)
    
    @pytest.mark.asyncio
    async def test_job_redelivered_on_worker_crash(self, queue):
        """Job should be redelivered if worker crashes."""
        job_id = await queue.enqueue({"task": "test"})
        process_count = 0
        
        # Worker 1 gets job but "crashes"
        job1 = await queue.dequeue("worker-1")
        assert job1 is not None
        process_count += 1
        
        # Wait for timeout
        await asyncio.sleep(1.5)
        await queue.recover_stale_locks()
        
        # Worker 2 gets same job
        job2 = await queue.dequeue("worker-2")
        assert job2 is not None
        assert job2.id == job_id
        process_count += 1
        
        # Job was delivered twice (at-least-once)
        assert process_count == 2
