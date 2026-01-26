"""
Agent Event Model (AC-005)
===========================
Append-only event timeline for debugging and observability of autonomous agents.

This model provides:
- Immutable event logging for all agent actions
- Filterable by step, topic, agent, and status
- Complete audit trail for autonomous operations
- Debugging and troubleshooting support
"""

from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from enum import Enum
from database.models import Base


class AgentEventType(str, Enum):
    """Types of agent events"""
    STARTED = "started"
    STEP = "step"
    ACTION = "action"
    DECISION = "decision"
    ERROR = "error"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    RESUMED = "resumed"


class AgentEventStatus(str, Enum):
    """Status of agent event"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentEvent(Base):
    """
    Append-only event log for agent operations (AC-005)

    Each event represents a single step or action taken by an autonomous agent.
    Events are immutable once created and provide a complete audit trail.

    Fields:
        id: Unique event identifier
        agent_id: ID of the agent that generated this event
        agent_name: Name/type of the agent (e.g., "slot_executor", "learner")
        run_id: ID of the agent run/session this event belongs to
        event_type: Type of event (started, step, action, decision, error, completed, failed)
        status: Current status (pending, running, success, failed, skipped)
        step: Step number within the run (for ordering)
        topic: Category/topic of the event (e.g., "content_generation", "publishing")
        message: Human-readable description of the event
        details: Additional structured data (JSON)
        error: Error message if status is failed
        duration_ms: Duration of this step in milliseconds
        created_at: When this event was created (immutable)

    Indexes:
        - agent_id, run_id (for filtering by agent/run)
        - topic (for filtering by category)
        - step (for ordering events within a run)
        - created_at (for time-based queries)
    """
    __tablename__ = "agent_events"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Agent identification
    agent_id = Column(String(255), nullable=False, index=True)
    agent_name = Column(String(255), nullable=False)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Event classification
    event_type = Column(SQLEnum(AgentEventType), nullable=False)
    status = Column(SQLEnum(AgentEventStatus), nullable=False, default=AgentEventStatus.SUCCESS)
    step = Column(Integer, nullable=False, default=0)
    topic = Column(String(255), nullable=True, index=True)

    # Event content
    message = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)

    # Performance
    duration_ms = Column(Integer, nullable=True)

    # Timestamps (immutable - append-only)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_agent_events_agent_run', 'agent_id', 'run_id'),
        Index('idx_agent_events_topic', 'topic'),
        Index('idx_agent_events_step', 'step'),
        Index('idx_agent_events_created_at', 'created_at'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": str(self.run_id),
            "event_type": self.event_type.value if isinstance(self.event_type, Enum) else self.event_type,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "step": self.step,
            "topic": self.topic,
            "message": self.message,
            "details": self.details,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
