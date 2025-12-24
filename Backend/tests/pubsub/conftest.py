"""
PubSub Test Configuration
=========================
Shared fixtures and utilities for pub/sub tests.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
import os

# Set test database URL
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


# ============================================================================
# EVENT BUS FIXTURES
# ============================================================================

@pytest.fixture
def event_bus():
    """Fresh EventBus instance for each test."""
    from services.event_bus import EventBus
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()


@pytest.fixture
def mock_event_bus():
    """Mock EventBus for isolated unit tests."""
    bus = MagicMock()
    bus.publish = AsyncMock(return_value=str(uuid4()))
    bus.subscribe = MagicMock()
    bus.get_recent_events = MagicMock(return_value=[])
    bus.get_dead_letter_queue = MagicMock(return_value=[])
    return bus


# ============================================================================
# EVENT FIXTURES
# ============================================================================

@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    from services.event_bus import Event
    return Event(
        id=str(uuid4()),
        topic="test.event",
        timestamp=datetime.now(timezone.utc),
        source="test-suite",
        correlation_id=str(uuid4()),
        payload={"key": "value", "count": 42},
        metadata={"version": "1.0"}
    )


@pytest.fixture
def sample_event_dict():
    """Sample event as dictionary."""
    return {
        "id": str(uuid4()),
        "topic": "test.event",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "test-suite",
        "correlation_id": str(uuid4()),
        "payload": {"key": "value"},
        "metadata": {}
    }


# ============================================================================
# WORKFLOW FIXTURES
# ============================================================================

@pytest.fixture
def sample_run_id():
    """Generate a unique run ID."""
    return str(uuid4())


@pytest.fixture
def sample_correlation_id():
    """Generate a unique correlation ID."""
    return str(uuid4())


@pytest.fixture
def workflow_events(sample_correlation_id):
    """Generate a sequence of workflow events."""
    from services.event_bus import Event, Topics
    
    base_time = datetime.now(timezone.utc)
    
    return [
        Event(
            topic=Topics.ANALYSIS_REQUESTED,
            payload={"video_id": "vid-123"},
            correlation_id=sample_correlation_id,
            source="test",
            metadata={"step": "start"}
        ),
        Event(
            topic=Topics.ANALYSIS_STARTED,
            payload={"video_id": "vid-123"},
            correlation_id=sample_correlation_id,
            source="test",
            metadata={"step": "processing"}
        ),
        Event(
            topic=Topics.ANALYSIS_COMPLETED,
            payload={"video_id": "vid-123", "score": 85},
            correlation_id=sample_correlation_id,
            source="test",
            metadata={"step": "complete"}
        ),
    ]


# ============================================================================
# MESSAGE SCHEMA FIXTURES
# ============================================================================

@pytest.fixture
def valid_message_envelope():
    """Valid message envelope for contract tests."""
    return {
        "id": str(uuid4()),
        "topic": "media.analysis.completed",
        "run_id": str(uuid4()),
        "step_key": "analysis",
        "event_type": "step.completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "v": 1,
            "video_id": "vid-123",
            "score": 85,
            "duration_ms": 1234
        },
        "metadata": {
            "attempt": 1,
            "source": "analysis-worker"
        }
    }


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
async def db_session():
    """Async database session for integration tests."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    engine = create_async_engine(async_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sync_db_session():
    """Sync database session for simpler tests."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    
    session = Session()
    yield session
    session.rollback()
    session.close()


# ============================================================================
# TIMING UTILITIES
# ============================================================================

@pytest.fixture
def timer():
    """Simple timer utility."""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = datetime.now(timezone.utc)
        
        def stop(self):
            self.end_time = datetime.now(timezone.utc)
        
        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds() * 1000
            return None
    
    return Timer()


# ============================================================================
# ASYNC EVENT COLLECTOR
# ============================================================================

@pytest.fixture
def event_collector():
    """Collects events for assertions."""
    class EventCollector:
        def __init__(self):
            self.events: List[Any] = []
            self.by_topic: Dict[str, List[Any]] = {}
        
        async def collect(self, event):
            self.events.append(event)
            topic = event.topic
            if topic not in self.by_topic:
                self.by_topic[topic] = []
            self.by_topic[topic].append(event)
        
        def count(self, topic: Optional[str] = None) -> int:
            if topic:
                return len(self.by_topic.get(topic, []))
            return len(self.events)
        
        def get_last(self, topic: Optional[str] = None):
            events = self.by_topic.get(topic, []) if topic else self.events
            return events[-1] if events else None
        
        def clear(self):
            self.events.clear()
            self.by_topic.clear()
    
    return EventCollector()


# ============================================================================
# IDEMPOTENCY KEY GENERATOR
# ============================================================================

@pytest.fixture
def idempotency_key_generator():
    """Generate idempotency keys for testing."""
    def generate(run_id: str, step_key: str, attempt: int = 1) -> str:
        return f"{run_id}:{step_key}:{attempt}"
    return generate
