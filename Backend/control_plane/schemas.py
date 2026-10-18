"""
Command & Control API Schemas

Pydantic models for command envelopes, event envelopes, and job states.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from uuid import uuid4


def generate_id(prefix: str = "") -> str:
    """Generate a prefixed unique ID."""
    return f"{prefix}{uuid4().hex[:16]}"


class CommandTarget(BaseModel):
    """Target for a command."""
    service: str = "mediaposter"
    instance_id: Optional[str] = None


class CommandEnvelope(BaseModel):
    """
    Command envelope for submitting commands to MediaPoster.
    
    Example:
        {
            "version": "1.0",
            "command_id": "cmd_abc123",
            "command": "clip.generate",
            "args": {"video_id": "vid_123", "start_ms": 0, "end_ms": 60000}
        }
    """
    version: str = "1.0"
    command_id: str = Field(default_factory=lambda: generate_id("cmd_"))
    correlation_id: Optional[str] = None
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    issued_by: Optional[str] = None
    command: str
    target: Optional[CommandTarget] = None
    args: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    priority: Literal["low", "normal", "high"] = "normal"
    timeout_s: int = 3600


class CommandAck(BaseModel):
    """Acknowledgment response when command is accepted."""
    accepted: bool = True
    job_id: str
    command_id: str
    queued_at: datetime = Field(default_factory=datetime.utcnow)


class EventEnvelope(BaseModel):
    """
    Event envelope emitted during job execution.
    
    Example:
        {
            "version": "1.0",
            "event_id": "evt_abc123",
            "job_id": "job_xyz789",
            "type": "job.progress",
            "stage": "ai_analysis",
            "percent": 42,
            "message": "transcription complete"
        }
    """
    version: str = "1.0"
    event_id: str = Field(default_factory=lambda: generate_id("evt_"))
    correlation_id: Optional[str] = None
    job_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: Literal[
        "job.queued",
        "job.started", 
        "job.progress",
        "job.stage_complete",
        "job.completed",
        "job.failed",
        "job.cancelled"
    ]
    stage: Optional[str] = None
    percent: Optional[int] = None
    message: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    cursor: Optional[str] = None


class JobState(BaseModel):
    """Current state of a job."""
    job_id: str
    command_id: str
    correlation_id: Optional[str] = None
    command: str
    args: Dict[str, Any] = Field(default_factory=dict)
    state: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"] = "QUEUED"
    stage: Optional[str] = None
    percent: int = 0
    result: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    priority: str = "normal"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class JobListResponse(BaseModel):
    """Response for listing jobs."""
    jobs: List[JobState]
    total: int
    offset: int = 0
    limit: int = 50


class JobEventsResponse(BaseModel):
    """Response for listing job events."""
    events: List[EventEnvelope]
    total: int
    cursor: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "unhealthy"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReadyResponse(BaseModel):
    """Readiness check response."""
    ready: bool
    checks: Dict[str, bool] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class CancelResponse(BaseModel):
    """Response for cancel request."""
    cancelled: bool
    job_id: str
    message: Optional[str] = None


class RetryResponse(BaseModel):
    """Response for retry request."""
    retried: bool
    job_id: str
    new_job_id: Optional[str] = None
    message: Optional[str] = None
