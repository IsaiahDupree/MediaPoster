"""
Media Factory Database Models
=============================
Persistent storage for jobs, stages, artifacts, and events.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database.base import Base


class MediaFactoryJob(Base):
    """
    Media Factory Pipeline Job
    
    Persistent storage for pipeline execution state.
    """
    __tablename__ = "media_factory_jobs"
    
    # Identity
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    correlation_id = Column(String(255), nullable=False, index=True)
    pipeline_id = Column(String(255), nullable=True, index=True)
    
    # Status
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed, cancelled
    progress = Column(Float, default=0.0, nullable=False)  # 0.0-1.0
    
    # Source
    brief_id = Column(String(255), nullable=True, index=True)
    brief_data = Column(JSON, nullable=True)  # Brief data snapshot
    
    # Configuration
    stages = Column(JSON, nullable=True)  # List of stages to execute
    skip_stages = Column(JSON, nullable=True)  # List of stages to skip
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error
    error = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Output
    final_output = Column(JSON, nullable=True)  # Final video paths, URLs, etc.
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default="now()", onupdate="now()", nullable=False)
    
    # Relationships
    stages_rel = relationship("MediaFactoryJobStage", back_populates="job", cascade="all, delete-orphan")
    artifacts_rel = relationship("MediaFactoryArtifact", back_populates="job", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_media_factory_jobs_status', 'status'),
        Index('ix_media_factory_jobs_correlation_id', 'correlation_id'),
        Index('ix_media_factory_jobs_created_at', 'created_at'),
    )


class MediaFactoryJobStage(Base):
    """
    Pipeline Stage State
    
    Tracks individual stage execution within a job.
    """
    __tablename__ = "media_factory_job_stages"
    
    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("media_factory_jobs.job_id"), nullable=False, index=True)
    
    # Stage Info
    stage_name = Column(String(50), nullable=False)  # brief, script, tts, music, visuals, remotion, publish
    stage_order = Column(Integer, nullable=False)  # Execution order
    
    # Status
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed, skipped
    progress = Column(Float, default=0.0, nullable=False)  # 0.0-1.0
    
    # Input/Output
    input_data = Column(JSON, nullable=True)  # Stage input snapshot
    output_data = Column(JSON, nullable=True)  # Stage output (paths, IDs, etc.)
    
    # Idempotency
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)
    
    # Retry
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error
    error = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default="now()", onupdate="now()", nullable=False)
    
    # Relationships
    job = relationship("MediaFactoryJob", back_populates="stages_rel")
    
    __table_args__ = (
        Index('ix_media_factory_job_stages_job_id_stage_name', 'job_id', 'stage_name'),
        Index('ix_media_factory_job_stages_status', 'status'),
        Index('ix_media_factory_job_stages_idempotency_key', 'idempotency_key'),
    )


class MediaFactoryArtifact(Base):
    """
    Pipeline Artifacts
    
    Tracks files generated during pipeline execution (audio, video, images, etc.).
    """
    __tablename__ = "media_factory_artifacts"
    
    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("media_factory_jobs.job_id"), nullable=False, index=True)
    stage_name = Column(String(50), nullable=False, index=True)  # Which stage generated this
    
    # Artifact Info
    artifact_type = Column(String(50), nullable=False)  # audio, video, image, json, other
    artifact_name = Column(String(255), nullable=False)
    file_path = Column(String(1000), nullable=False)  # Full path to file
    file_size_bytes = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True)  # SHA256 hash for deduplication
    
    # Metadata
    metadata = Column(JSON, nullable=True)  # Duration, resolution, format, etc.
    
    # Lifecycle
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # For cleanup
    
    # Relationships
    job = relationship("MediaFactoryJob", back_populates="artifacts_rel")
    
    __table_args__ = (
        Index('ix_media_factory_artifacts_job_id_stage_name', 'job_id', 'stage_name'),
        Index('ix_media_factory_artifacts_file_hash', 'file_hash'),
        Index('ix_media_factory_artifacts_expires_at', 'expires_at'),
    )


class MediaFactoryEvent(Base):
    """
    Pipeline Events (Audit Log)
    
    Optional: Tracks all events for audit and debugging.
    """
    __tablename__ = "media_factory_events"
    
    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("media_factory_jobs.job_id"), nullable=True, index=True)
    correlation_id = Column(String(255), nullable=False, index=True)
    
    # Event Info
    event_type = Column(String(100), nullable=False)  # tts.completed, remotion.started, etc.
    event_topic = Column(String(100), nullable=False, index=True)
    event_payload = Column(JSON, nullable=True)
    
    # Source
    source = Column(String(100), nullable=True)  # api, worker, pipeline, etc.
    
    # Timing
    occurred_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)
    
    __table_args__ = (
        Index('ix_media_factory_events_correlation_id', 'correlation_id'),
        Index('ix_media_factory_events_topic', 'event_topic'),
        Index('ix_media_factory_events_occurred_at', 'occurred_at'),
    )


class MediaFactoryDLQ(Base):
    """
    Dead Letter Queue
    
    Stores failed operations with reasons and payload snapshots.
    """
    __tablename__ = "media_factory_dlq"
    
    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String(255), nullable=False, index=True)
    stage_name = Column(String(50), nullable=False, index=True)
    correlation_id = Column(String(255), nullable=True, index=True)
    
    # Failure Info
    error = Column(Text, nullable=False)
    error_type = Column(String(100), nullable=True)  # Exception class name
    payload = Column(JSON, nullable=True)  # Operation payload snapshot
    
    # Retry Info
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Idempotency
    idempotency_key = Column(String(255), nullable=True, index=True)
    
    # Status
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Timing
    failed_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)
    
    __table_args__ = (
        Index('ix_media_factory_dlq_job_id_stage_name', 'job_id', 'stage_name'),
        Index('ix_media_factory_dlq_resolved', 'resolved'),
        Index('ix_media_factory_dlq_failed_at', 'failed_at'),
    )

