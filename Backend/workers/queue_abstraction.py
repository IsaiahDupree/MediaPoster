"""
Worker Queue Abstraction (MOD-003)
===================================
Unified interface for job queues supporting both Redis and in-memory implementations.

This abstraction allows:
- Production: Use Redis/BullMQ for distributed job processing
- Development/Testing: Use in-memory queue without Redis dependency
- Easy provider swapping without changing application code

Usage:
    >>> from workers.queue_abstraction import get_queue, QueueConfig
    >>>
    >>> # Initialize queue (auto-detects Redis or falls back to in-memory)
    >>> queue = get_queue()
    >>>
    >>> # Add job
    >>> job_id = await queue.enqueue(
    ...     "render_video",
    ...     {"video_id": "123", "format": "shorts"}
    ... )
    >>>
    >>> # Process jobs
    >>> async def render_handler(job_data):
    ...     print(f"Rendering: {job_data}")
    ...
    >>> queue.register_handler("render_video", render_handler)
    >>> await queue.start_worker()
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, Callable, List, Awaitable
from loguru import logger
import os


class JobStatus(Enum):
    """Job execution statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Job:
    """Represents a job in the queue."""
    job_id: str
    job_type: str
    data: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "data": self.data,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }


@dataclass
class QueueConfig:
    """Configuration for queue implementation."""
    # Redis configuration
    use_redis: bool = field(default_factory=lambda: bool(os.getenv("REDIS_URL")))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))

    # In-memory configuration
    max_queue_size: int = 1000

    # Worker configuration
    worker_concurrency: int = 5
    poll_interval_seconds: float = 1.0

    # Retry configuration
    default_max_retries: int = 3
    retry_delay_seconds: float = 5.0


class QueueAbstraction(ABC):
    """
    Abstract base class for job queue implementations.

    Provides unified interface for Redis-backed and in-memory queues.
    """

    @abstractmethod
    async def enqueue(
        self,
        job_type: str,
        data: Dict[str, Any],
        job_id: Optional[str] = None,
        max_retries: Optional[int] = None
    ) -> str:
        """
        Add job to queue.

        Args:
            job_type: Type of job (e.g., "render_video", "process_audio")
            data: Job data dictionary
            job_id: Optional custom job ID
            max_retries: Optional max retry count (overrides default)

        Returns:
            Job ID
        """
        pass

    @abstractmethod
    async def dequeue(self) -> Optional[Job]:
        """
        Get next job from queue.

        Returns:
            Job or None if queue is empty
        """
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job or None if not found
        """
        pass

    @abstractmethod
    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None
    ) -> bool:
        """
        Update job status.

        Args:
            job_id: Job identifier
            status: New status
            error: Optional error message

        Returns:
            True if updated, False if job not found
        """
        pass

    @abstractmethod
    async def get_queue_size(self) -> int:
        """Get number of pending jobs."""
        pass

    @abstractmethod
    async def clear_queue(self) -> int:
        """Clear all pending jobs. Returns number of jobs cleared."""
        pass

    @abstractmethod
    def register_handler(
        self,
        job_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    ) -> None:
        """
        Register job handler function.

        Args:
            job_type: Type of job
            handler: Async function to handle job
        """
        pass

    @abstractmethod
    async def start_worker(self) -> None:
        """Start worker to process jobs."""
        pass

    @abstractmethod
    async def stop_worker(self) -> None:
        """Stop worker."""
        pass


class InMemoryQueue(QueueAbstraction):
    """
    In-memory queue implementation for development and testing.

    Stores jobs in memory using asyncio.Queue.
    """

    def __init__(self, config: QueueConfig):
        """Initialize in-memory queue."""
        self.config = config
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=config.max_queue_size)
        self._jobs: Dict[str, Job] = {}
        self._handlers: Dict[str, Callable] = {}
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running = False

        logger.info("📦 In-memory queue initialized")

    async def enqueue(
        self,
        job_type: str,
        data: Dict[str, Any],
        job_id: Optional[str] = None,
        max_retries: Optional[int] = None
    ) -> str:
        """Add job to queue."""
        if not job_id:
            job_id = str(uuid.uuid4())

        job = Job(
            job_id=job_id,
            job_type=job_type,
            data=data,
            max_retries=max_retries or self.config.default_max_retries
        )

        self._jobs[job_id] = job
        await self._queue.put(job)

        logger.debug(f"✓ Job enqueued: {job_type} ({job_id[:8]})")
        return job_id

    async def dequeue(self) -> Optional[Job]:
        """Get next job from queue."""
        try:
            job = await asyncio.wait_for(
                self._queue.get(),
                timeout=self.config.poll_interval_seconds
            )
            return job
        except asyncio.TimeoutError:
            return None

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None
    ) -> bool:
        """Update job status."""
        job = self._jobs.get(job_id)
        if not job:
            return False

        job.status = status
        if error:
            job.error = error

        if status == JobStatus.PROCESSING:
            job.started_at = datetime.now(timezone.utc)
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
            job.completed_at = datetime.now(timezone.utc)

        return True

    async def get_queue_size(self) -> int:
        """Get number of pending jobs."""
        return self._queue.qsize()

    async def clear_queue(self) -> int:
        """Clear all pending jobs."""
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break

        # Clear job records
        self._jobs.clear()
        return count

    def register_handler(
        self,
        job_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    ) -> None:
        """Register job handler."""
        self._handlers[job_type] = handler
        logger.info(f"✓ Registered handler for: {job_type}")

    async def start_worker(self) -> None:
        """Start worker to process jobs."""
        if self._is_running:
            logger.warning("Worker already running")
            return

        self._is_running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("✓ In-memory queue worker started")

    async def stop_worker(self) -> None:
        """Stop worker."""
        self._is_running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("✓ In-memory queue worker stopped")

    async def _worker_loop(self) -> None:
        """Worker loop to process jobs."""
        while self._is_running:
            try:
                job = await self.dequeue()
                if not job:
                    continue

                # Process job
                await self._process_job(job)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(1)

    async def _process_job(self, job: Job) -> None:
        """Process a single job."""
        try:
            # Update status to processing
            await self.update_job_status(job.job_id, JobStatus.PROCESSING)

            # Get handler
            handler = self._handlers.get(job.job_type)
            if not handler:
                raise ValueError(f"No handler registered for job type: {job.job_type}")

            # Execute handler
            logger.info(f"▶️  Processing job: {job.job_type} ({job.job_id[:8]})")
            await handler(job.data)

            # Mark as completed
            await self.update_job_status(job.job_id, JobStatus.COMPLETED)
            logger.success(f"✓ Job completed: {job.job_type} ({job.job_id[:8]})")

        except Exception as e:
            logger.error(f"Job failed: {job.job_type} ({job.job_id[:8]}) - {e}")

            # Retry logic
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                await self.update_job_status(job.job_id, JobStatus.RETRYING)

                # Re-enqueue after delay
                await asyncio.sleep(self.config.retry_delay_seconds)
                await self._queue.put(job)

                logger.info(
                    f"🔄 Retrying job: {job.job_type} ({job.job_id[:8]}) "
                    f"- Attempt {job.retry_count}/{job.max_retries}"
                )
            else:
                # Max retries exceeded
                await self.update_job_status(
                    job.job_id,
                    JobStatus.FAILED,
                    error=str(e)
                )


class RedisQueue(QueueAbstraction):
    """
    Redis-backed queue implementation for production.

    Uses Redis lists and hashes for distributed job processing.
    """

    def __init__(self, config: QueueConfig):
        """Initialize Redis queue."""
        self.config = config
        self._handlers: Dict[str, Callable] = {}
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running = False

        # Redis client (lazy initialization)
        self._redis = None

        logger.info(f"📦 Redis queue initialized: {config.redis_url}")

    async def _get_redis(self):
        """Get or create Redis client."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.config.redis_url, decode_responses=True)
                await self._redis.ping()
                logger.success("✓ Connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

        return self._redis

    async def enqueue(
        self,
        job_type: str,
        data: Dict[str, Any],
        job_id: Optional[str] = None,
        max_retries: Optional[int] = None
    ) -> str:
        """Add job to Redis queue."""
        if not job_id:
            job_id = str(uuid.uuid4())

        job = Job(
            job_id=job_id,
            job_type=job_type,
            data=data,
            max_retries=max_retries or self.config.default_max_retries
        )

        redis = await self._get_redis()

        # Store job data in hash
        import json
        await redis.hset(f"job:{job_id}", mapping={
            "data": json.dumps(job.to_dict())
        })

        # Add to pending queue
        await redis.lpush("queue:pending", job_id)

        logger.debug(f"✓ Job enqueued to Redis: {job_type} ({job_id[:8]})")
        return job_id

    async def dequeue(self) -> Optional[Job]:
        """Get next job from Redis queue."""
        redis = await self._get_redis()

        # Blocking pop from pending queue
        result = await redis.brpop("queue:pending", timeout=self.config.poll_interval_seconds)

        if not result:
            return None

        _, job_id = result

        # Get job data
        import json
        job_data = await redis.hget(f"job:{job_id}", "data")
        if not job_data:
            return None

        job_dict = json.loads(job_data)
        job = Job(
            job_id=job_dict["job_id"],
            job_type=job_dict["job_type"],
            data=job_dict["data"],
            status=JobStatus(job_dict["status"]),
            max_retries=job_dict["max_retries"]
        )

        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID from Redis."""
        redis = await self._get_redis()

        import json
        job_data = await redis.hget(f"job:{job_id}", "data")
        if not job_data:
            return None

        job_dict = json.loads(job_data)
        return Job(
            job_id=job_dict["job_id"],
            job_type=job_dict["job_type"],
            data=job_dict["data"],
            status=JobStatus(job_dict["status"]),
            max_retries=job_dict["max_retries"]
        )

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None
    ) -> bool:
        """Update job status in Redis."""
        job = await self.get_job(job_id)
        if not job:
            return False

        job.status = status
        if error:
            job.error = error

        if status == JobStatus.PROCESSING:
            job.started_at = datetime.now(timezone.utc)
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
            job.completed_at = datetime.now(timezone.utc)

        redis = await self._get_redis()

        import json
        await redis.hset(f"job:{job_id}", mapping={
            "data": json.dumps(job.to_dict())
        })

        return True

    async def get_queue_size(self) -> int:
        """Get number of pending jobs in Redis."""
        redis = await self._get_redis()
        return await redis.llen("queue:pending")

    async def clear_queue(self) -> int:
        """Clear all pending jobs from Redis."""
        redis = await self._get_redis()
        size = await redis.llen("queue:pending")
        await redis.delete("queue:pending")
        return size

    def register_handler(
        self,
        job_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    ) -> None:
        """Register job handler."""
        self._handlers[job_type] = handler
        logger.info(f"✓ Registered handler for: {job_type}")

    async def start_worker(self) -> None:
        """Start Redis queue worker."""
        if self._is_running:
            logger.warning("Worker already running")
            return

        self._is_running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("✓ Redis queue worker started")

    async def stop_worker(self) -> None:
        """Stop Redis queue worker."""
        self._is_running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        if self._redis:
            await self._redis.close()

        logger.info("✓ Redis queue worker stopped")

    async def _worker_loop(self) -> None:
        """Worker loop to process jobs from Redis."""
        # Same logic as InMemoryQueue
        while self._is_running:
            try:
                job = await self.dequeue()
                if not job:
                    continue

                await self._process_job(job)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Redis worker loop: {e}")
                await asyncio.sleep(1)

    async def _process_job(self, job: Job) -> None:
        """Process a single job (same as InMemoryQueue)."""
        try:
            await self.update_job_status(job.job_id, JobStatus.PROCESSING)

            handler = self._handlers.get(job.job_type)
            if not handler:
                raise ValueError(f"No handler registered for job type: {job.job_type}")

            logger.info(f"▶️  Processing job: {job.job_type} ({job.job_id[:8]})")
            await handler(job.data)

            await self.update_job_status(job.job_id, JobStatus.COMPLETED)
            logger.success(f"✓ Job completed: {job.job_type} ({job.job_id[:8]})")

        except Exception as e:
            logger.error(f"Job failed: {job.job_type} ({job.job_id[:8]}) - {e}")

            if job.retry_count < job.max_retries:
                job.retry_count += 1
                await self.update_job_status(job.job_id, JobStatus.RETRYING)

                redis = await self._get_redis()
                await asyncio.sleep(self.config.retry_delay_seconds)
                await redis.lpush("queue:pending", job.job_id)

                logger.info(
                    f"🔄 Retrying job: {job.job_type} ({job.job_id[:8]}) "
                    f"- Attempt {job.retry_count}/{job.max_retries}"
                )
            else:
                await self.update_job_status(
                    job.job_id,
                    JobStatus.FAILED,
                    error=str(e)
                )


# Global queue instance
_queue: Optional[QueueAbstraction] = None


def get_queue(config: Optional[QueueConfig] = None) -> QueueAbstraction:
    """
    Get or create the global queue instance.

    Auto-detects Redis availability and falls back to in-memory.

    Args:
        config: Optional queue configuration

    Returns:
        Queue instance (Redis or in-memory)
    """
    global _queue

    if _queue is None:
        if config is None:
            config = QueueConfig()

        if config.use_redis:
            try:
                _queue = RedisQueue(config)
                logger.info("Using Redis queue")
            except Exception as e:
                logger.warning(f"Redis not available, falling back to in-memory queue: {e}")
                _queue = InMemoryQueue(config)
        else:
            _queue = InMemoryQueue(config)
            logger.info("Using in-memory queue")

    return _queue


__all__ = [
    "QueueAbstraction",
    "InMemoryQueue",
    "RedisQueue",
    "QueueConfig",
    "JobStatus",
    "Job",
    "get_queue",
]
