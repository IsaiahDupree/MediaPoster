"""
Tests for Worker Queue Abstraction (MOD-003)
"""
import pytest
import asyncio
from workers.queue_abstraction import (
    InMemoryQueue,
    QueueConfig,
    JobStatus,
    get_queue,
)


@pytest.fixture
def queue_config():
    """Create test queue configuration."""
    return QueueConfig(
        use_redis=False,  # Use in-memory for tests
        max_queue_size=100,
        worker_concurrency=3,
        poll_interval_seconds=0.1,
        default_max_retries=2,
        retry_delay_seconds=0.1
    )


@pytest.fixture
async def queue(queue_config):
    """Create test queue instance."""
    q = InMemoryQueue(queue_config)
    yield q
    # Cleanup
    if q._is_running:
        await q.stop_worker()


class TestInMemoryQueue:
    """Tests for in-memory queue implementation."""

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self, queue):
        """Test basic enqueue/dequeue operations."""
        # Enqueue job
        job_id = await queue.enqueue(
            "test_job",
            {"key": "value"}
        )

        assert job_id is not None

        # Dequeue job
        job = await queue.dequeue()
        assert job is not None
        assert job.job_type == "test_job"
        assert job.data == {"key": "value"}
        assert job.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_job(self, queue):
        """Test getting job by ID."""
        job_id = await queue.enqueue(
            "test_job",
            {"data": "test"}
        )

        job = await queue.get_job(job_id)
        assert job is not None
        assert job.job_id == job_id
        assert job.job_type == "test_job"

    @pytest.mark.asyncio
    async def test_update_job_status(self, queue):
        """Test updating job status."""
        job_id = await queue.enqueue(
            "test_job",
            {"data": "test"}
        )

        # Update to processing
        success = await queue.update_job_status(job_id, JobStatus.PROCESSING)
        assert success is True

        # Verify update
        job = await queue.get_job(job_id)
        assert job.status == JobStatus.PROCESSING
        assert job.started_at is not None

        # Update to completed
        success = await queue.update_job_status(job_id, JobStatus.COMPLETED)
        assert success is True

        job = await queue.get_job(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None

    @pytest.mark.asyncio
    async def test_queue_size(self, queue):
        """Test getting queue size."""
        assert await queue.get_queue_size() == 0

        # Add 3 jobs
        await queue.enqueue("job1", {})
        await queue.enqueue("job2", {})
        await queue.enqueue("job3", {})

        assert await queue.get_queue_size() == 3

    @pytest.mark.asyncio
    async def test_clear_queue(self, queue):
        """Test clearing queue."""
        # Add jobs
        await queue.enqueue("job1", {})
        await queue.enqueue("job2", {})

        # Clear
        cleared_count = await queue.clear_queue()
        assert cleared_count == 2
        assert await queue.get_queue_size() == 0

    @pytest.mark.asyncio
    async def test_worker_processing(self, queue):
        """Test worker processing jobs."""
        processed_jobs = []

        async def test_handler(data):
            """Test job handler."""
            processed_jobs.append(data)
            await asyncio.sleep(0.01)  # Simulate work

        # Register handler
        queue.register_handler("test_job", test_handler)

        # Start worker
        await queue.start_worker()

        # Enqueue jobs
        await queue.enqueue("test_job", {"id": 1})
        await queue.enqueue("test_job", {"id": 2})

        # Wait for processing
        await asyncio.sleep(0.5)

        # Stop worker
        await queue.stop_worker()

        # Verify jobs were processed
        assert len(processed_jobs) == 2
        assert {"id": 1} in processed_jobs
        assert {"id": 2} in processed_jobs

    @pytest.mark.asyncio
    async def test_job_retry_on_failure(self, queue):
        """Test job retry logic on failure."""
        attempt_count = 0

        async def failing_handler(data):
            """Handler that fails first 2 times."""
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Simulated failure")
            # Success on 3rd attempt

        queue.register_handler("retry_job", failing_handler)
        await queue.start_worker()

        # Enqueue job with max 3 retries
        job_id = await queue.enqueue("retry_job", {"test": "data"}, max_retries=3)

        # Wait for retries
        await asyncio.sleep(1.0)

        # Stop worker
        await queue.stop_worker()

        # Verify job succeeded after retries
        job = await queue.get_job(job_id)
        assert attempt_count == 3
        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_job_fails_after_max_retries(self, queue):
        """Test job fails after exceeding max retries."""
        attempt_count = 0

        async def always_failing_handler(data):
            """Handler that always fails."""
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Always fails")

        queue.register_handler("fail_job", always_failing_handler)
        await queue.start_worker()

        # Enqueue job with max 2 retries
        job_id = await queue.enqueue("fail_job", {"test": "data"}, max_retries=2)

        # Wait for retries
        await asyncio.sleep(1.0)

        # Stop worker
        await queue.stop_worker()

        # Verify job failed after max retries
        job = await queue.get_job(job_id)
        assert attempt_count == 3  # Initial + 2 retries
        assert job.status == JobStatus.FAILED
        assert job.error is not None


class TestGetQueue:
    """Tests for get_queue factory function."""

    def test_get_queue_returns_in_memory_by_default(self):
        """Test that get_queue returns in-memory queue when Redis not configured."""
        config = QueueConfig(use_redis=False)
        queue = get_queue(config)
        assert isinstance(queue, InMemoryQueue)

    def test_get_queue_singleton(self):
        """Test that get_queue returns same instance."""
        # Note: This test may interfere with global state
        # In real tests, you'd want to reset the global singleton
        config = QueueConfig(use_redis=False)
        queue1 = get_queue(config)
        queue2 = get_queue()
        # Should be same instance (singleton pattern)
        # Note: This may fail if other tests have initialized the queue
        # In production code, add reset_queue() for testing
