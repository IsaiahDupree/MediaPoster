"""
Content Pipeline Database Models
Defines tables for automated content sourcing, analysis, scheduling, and publishing.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, 
    ForeignKey, JSON, ARRAY, Index, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from database.connection import Base


class ContentStatus(enum.Enum):
    """Status of content in the pipeline"""
    PENDING_ANALYSIS = "pending_analysis"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    REJECTED = "rejected"
    SAVED_FOR_LATER = "saved_for_later"


class PostStatus(enum.Enum):
    """Status of a scheduled post"""
    PENDING = "pending"
    POSTING = "posting"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class AssignmentStatus(enum.Enum):
    """Status of platform assignment"""
    SUGGESTED = "suggested"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContentItem(Base):
    """Main content item in the pipeline"""
    __tablename__ = "content_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Reference to media table
    
    # Source info
    source_type = Column(String(50), default="media_library")  # media_library, upload, import
    source_path = Column(Text)
    
    # Status
    status = Column(String(30), default=ContentStatus.PENDING_ANALYSIS.value, index=True)
    
    # AI Analysis Results
    quality_score = Column(Integer, default=0)  # 0-100
    niche = Column(String(100))  # lifestyle, fitness, comedy, etc.
    ai_analysis = Column(JSONB, default={})
    """
    ai_analysis structure:
    {
        "title": "AI generated title",
        "short_description": "Brief description",
        "detailed_description": "Full description",
        "scene_type": "outdoor",
        "people_count": 1,
        "mood": "happy",
        "topics": ["travel", "lifestyle"],
        "hashtags": ["#travel", "#lifestyle"],
        "suggested_platforms": ["instagram", "tiktok"],
        "content_type": "image|video|clip",
        "engagement_prediction": "high|medium|low"
    }
    """
    
    # Content metadata
    content_type = Column(String(20))  # image, video, clip
    duration_sec = Column(Float)
    resolution = Column(String(20))
    aspect_ratio = Column(String(10))
    file_size = Column(Integer)
    
    # Priority & Scheduling
    priority = Column(Integer, default=0)  # Higher = more priority
    earliest_post_date = Column(DateTime)
    latest_post_date = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    analyzed_at = Column(DateTime)
    approved_at = Column(DateTime)
    approved_by = Column(String(100))
    
    # Relationships
    variations = relationship("ContentVariation", back_populates="content_item", cascade="all, delete-orphan")
    platform_assignments = relationship("ContentPlatformAssignment", back_populates="content_item", cascade="all, delete-orphan")
    scheduled_posts = relationship("ScheduledPost", back_populates="content_item")

    __table_args__ = (
        Index('idx_content_status_priority', 'status', 'priority'),
        Index('idx_content_niche', 'niche'),
        Index('idx_content_quality', 'quality_score'),
    )


class ContentVariation(Base):
    """Multiple title/description variations per content"""
    __tablename__ = "content_variations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)
    
    # Variation content
    title = Column(String(500))
    description = Column(Text)
    hashtags = Column(ARRAY(String), default=[])
    call_to_action = Column(String(200))
    
    # Metadata
    variation_index = Column(Integer, default=0)
    is_primary = Column(Boolean, default=False)
    platform_hint = Column(String(50))  # Optimized for which platform
    
    # Usage tracking
    times_used = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    last_used_platform = Column(String(50))
    
    # Performance (if tracked)
    avg_engagement = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    content_item = relationship("ContentItem", back_populates="variations")

    __table_args__ = (
        Index('idx_variation_content', 'content_id'),
        Index('idx_variation_primary', 'content_id', 'is_primary'),
    )


class ContentPlatformAssignment(Base):
    """Assigns content to specific platforms and accounts"""
    __tablename__ = "content_platform_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)
    
    # Platform & Account
    platform = Column(String(50), nullable=False)  # instagram, tiktok, youtube, etc.
    account_id = Column(Integer, nullable=True)  # FK to social_accounts
    account_username = Column(String(100))
    
    # Matching
    match_score = Column(Float, default=0)  # 0-100
    match_reasons = Column(ARRAY(String), default=[])
    """
    match_reasons examples:
    ["niche_match", "format_compatible", "quality_threshold_met", "account_focus_aligned"]
    """
    
    # Status
    status = Column(String(20), default=AssignmentStatus.SUGGESTED.value)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    approved_at = Column(DateTime)
    
    # Relationships
    content_item = relationship("ContentItem", back_populates="platform_assignments")

    __table_args__ = (
        Index('idx_assignment_content_platform', 'content_id', 'platform'),
        Index('idx_assignment_status', 'status'),
    )


class ScheduledPost(Base):
    """Posts scheduled for publishing"""
    __tablename__ = "scheduled_posts_v2"  # v2 to avoid conflict with existing table

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id"), nullable=False)
    variation_id = Column(UUID(as_uuid=True), ForeignKey("content_variations.id"), nullable=True)
    
    # Platform & Account
    platform = Column(String(50), nullable=False)
    account_id = Column(Integer)
    account_username = Column(String(100))
    
    # Scheduling
    scheduled_time = Column(DateTime, nullable=False, index=True)
    time_slot = Column(String(20))  # morning, midday, afternoon, evening, night
    priority = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default=PostStatus.PENDING.value, index=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Posting results
    posted_at = Column(DateTime)
    platform_post_id = Column(String(255))
    platform_url = Column(Text)
    error_message = Column(Text)
    
    # Performance tracking
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    content_item = relationship("ContentItem", back_populates="scheduled_posts")

    __table_args__ = (
        Index('idx_scheduled_time_status', 'scheduled_time', 'status'),
        Index('idx_scheduled_platform', 'platform', 'status'),
    )


class PostingScheduleConfig(Base):
    """Configuration for posting schedule"""
    __tablename__ = "posting_schedule_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Schedule name
    name = Column(String(100), default="default")
    is_active = Column(Boolean, default=True)
    
    # Time settings
    timezone = Column(String(50), default="America/New_York")
    daylight_start_hour = Column(Integer, default=6)  # 6 AM
    daylight_end_hour = Column(Integer, default=22)  # 10 PM
    posting_interval_hours = Column(Integer, default=4)
    
    # Limits
    min_posts_per_day = Column(Integer, default=1)
    max_posts_per_day = Column(Integer, default=4)
    min_gap_between_same_content_days = Column(Integer, default=30)
    
    # Platform-specific settings
    platform_configs = Column(JSONB, default={})
    """
    platform_configs structure:
    {
        "instagram": {
            "enabled": true,
            "max_posts_per_day": 3,
            "preferred_times": ["10:00", "14:00", "18:00"],
            "min_quality_score": 70
        },
        "tiktok": {
            "enabled": true,
            "max_posts_per_day": 4,
            "preferred_times": ["09:00", "12:00", "17:00", "21:00"],
            "min_quality_score": 60
        }
    }
    """
    
    # Content settings
    content_runway_warning_days = Column(Integer, default=14)
    content_runway_critical_days = Column(Integer, default=7)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class ContentSourceConfig(Base):
    """Configuration for content sourcing"""
    __tablename__ = "content_source_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Source identification
    name = Column(String(100))
    source_type = Column(String(50))  # folder, api, rss, etc.
    is_active = Column(Boolean, default=True)
    
    # Source settings
    source_path = Column(Text)  # Folder path or API endpoint
    source_config = Column(JSONB, default={})
    
    # Filtering
    min_quality_score = Column(Integer, default=50)
    allowed_content_types = Column(ARRAY(String), default=["image", "video"])
    niche_filter = Column(ARRAY(String), default=[])
    
    # Scheduling
    scan_interval_minutes = Column(Integer, default=60)
    last_scanned_at = Column(DateTime)
    
    # Stats
    total_items_found = Column(Integer, default=0)
    total_items_imported = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
