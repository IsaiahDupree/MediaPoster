"""
Trend Discovery Database Models
================================
Models for storing trend data, media ingestion, scoring, and content briefs.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, 
    ForeignKey, JSON, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database.connection import Base


# =============================================================================
# TREND ENTITIES (sounds, hashtags, keywords, users)
# =============================================================================

class TrendEntity(Base):
    """
    A trackable entity: sound, hashtag, keyword, or user/creator.
    """
    __tablename__ = "trend_entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False)  # 'sound' | 'hashtag' | 'keyword' | 'user'
    external_id = Column(String(255))  # Platform-specific ID
    name = Column(String(500), nullable=False)
    platform = Column(String(50), default='instagram')  # 'instagram' | 'tiktok'
    
    # Classification
    country = Column(String(10))  # ISO country code
    niche = Column(String(100))
    
    # Metadata
    first_seen_at = Column(DateTime(timezone=True))
    last_seen_at = Column(DateTime(timezone=True))
    
    # For sounds
    artist = Column(String(255))
    preview_url = Column(Text)
    duration_sec = Column(Float)
    
    # For users
    username = Column(String(255))
    follower_count = Column(Integer)
    
    # Raw API response
    raw_data = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    metrics = relationship("TrendMetricsDaily", back_populates="entity", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('platform', 'type', 'external_id', name='uq_trend_entity_platform_type_external'),
        Index('ix_trend_entity_type', 'type'),
        Index('ix_trend_entity_niche', 'niche'),
        Index('ix_trend_entity_country', 'country'),
    )


# =============================================================================
# TREND MEDIA (raw posts/reels ingested)
# =============================================================================

class TrendMedia(Base):
    """
    Raw media item from Instagram/TikTok for trend analysis.
    """
    __tablename__ = "trend_media"
    
    media_id = Column(String(100), primary_key=True)
    platform = Column(String(50), nullable=False)  # 'instagram' | 'tiktok'
    
    # Author
    author_id = Column(String(100))
    author_username = Column(String(255))
    
    # Content
    caption = Column(Text)
    hashtags = Column(ARRAY(String))
    keywords = Column(ARRAY(String))  # Extracted from caption
    
    # Media type
    media_type = Column(String(50))  # 'reel' | 'post' | 'carousel' | 'story'
    
    # Audio/Music
    music_id = Column(String(100))
    music_title = Column(String(500))
    music_artist = Column(String(255))
    
    # Metrics (snapshot at ingestion)
    play_count = Column(Integer)
    like_count = Column(Integer)
    comment_count = Column(Integer)
    share_count = Column(Integer)
    save_count = Column(Integer)
    
    # Computed
    engagement_rate = Column(Float)
    velocity_score = Column(Float)
    
    # Metadata
    posted_at = Column(DateTime(timezone=True))
    location_id = Column(String(100))
    location_name = Column(String(255))
    language = Column(String(10))
    
    # Thumbnail/Preview
    thumbnail_url = Column(Text)
    media_url = Column(Text)
    
    # Raw API response
    raw_data = Column(JSONB)
    
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_trend_media_music_id', 'music_id'),
        Index('ix_trend_media_author_id', 'author_id'),
        Index('ix_trend_media_posted_at', 'posted_at'),
        Index('ix_trend_media_platform', 'platform'),
    )


# =============================================================================
# TREND METRICS (daily snapshots)
# =============================================================================

class TrendMetricsDaily(Base):
    """
    Daily metrics snapshot for trend entities.
    Used to calculate velocity, saturation, etc.
    """
    __tablename__ = "trend_metrics_daily"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey('trend_entities.id', ondelete='CASCADE'))
    date = Column(DateTime(timezone=True), nullable=False)
    
    # Adoption metrics
    unique_creators = Column(Integer, default=0)  # Unique creators using this entity
    total_posts = Column(Integer, default=0)
    new_posts_24h = Column(Integer, default=0)
    
    # Performance metrics
    median_plays = Column(Integer)
    median_likes = Column(Integer)
    median_comments = Column(Integer)
    avg_engagement_rate = Column(Float)
    
    # Computed scores
    velocity_score = Column(Float)  # How fast it's growing (0-100)
    saturation_score = Column(Float)  # How crowded it is (0-100)
    efficiency_score = Column(Float)  # Engagement quality (0-100)
    trend_score = Column(Float)  # Composite score (0-100)
    
    # Delta from previous period
    velocity_delta_24h = Column(Float)
    velocity_delta_7d = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    entity = relationship("TrendEntity", back_populates="metrics")
    
    __table_args__ = (
        UniqueConstraint('entity_id', 'date', name='uq_trend_metrics_entity_date'),
        Index('ix_trend_metrics_date', 'date'),
        Index('ix_trend_metrics_trend_score', 'trend_score'),
    )


# =============================================================================
# TREND CLUSTERS (grouped content = a "trend")
# =============================================================================

class TrendCluster(Base):
    """
    A cluster of related content that forms a "trend".
    Includes AI-generated summary and content ideas.
    """
    __tablename__ = "trend_clusters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identity
    name = Column(String(500))
    slug = Column(String(255), unique=True)
    
    # AI-generated content
    summary = Column(Text)  # "What this trend is about"
    format_bullets = Column(JSONB)  # ["Hook: ...", "Build: ...", "Payoff: ..."]
    content_ideas = Column(JSONB)  # ["Idea 1", "Idea 2", ...]
    
    # Associated entities
    primary_sound_id = Column(UUID(as_uuid=True), ForeignKey('trend_entities.id'))
    primary_hashtag = Column(String(255))
    
    # Classification
    country = Column(String(10))
    niche = Column(String(100))
    
    # Scores
    velocity_score = Column(Float)
    saturation_score = Column(Float)
    trend_score = Column(Float)
    decay_estimate_days = Column(Integer)
    
    # Geo distribution
    geo_distribution = Column(JSONB)  # {"US": 45, "UK": 20, ...}
    
    # Status
    status = Column(String(50), default='active')  # 'active' | 'declining' | 'saturated'
    
    # Media count
    media_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    media = relationship("TrendClusterMedia", back_populates="cluster", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_trend_cluster_niche', 'niche'),
        Index('ix_trend_cluster_country', 'country'),
        Index('ix_trend_cluster_trend_score', 'trend_score'),
    )


class TrendClusterMedia(Base):
    """
    Junction table linking clusters to their example media.
    """
    __tablename__ = "trend_cluster_media"
    
    cluster_id = Column(UUID(as_uuid=True), ForeignKey('trend_clusters.id', ondelete='CASCADE'), primary_key=True)
    media_id = Column(String(100), ForeignKey('trend_media.media_id', ondelete='CASCADE'), primary_key=True)
    
    # Ranking within cluster
    rank = Column(Integer)
    is_top_example = Column(Boolean, default=False)
    
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    cluster = relationship("TrendCluster", back_populates="media")


# =============================================================================
# CONTENT BRIEFS (generated from trends)
# =============================================================================

class ContentBrief(Base):
    """
    AI-generated content brief based on a trend.
    """
    __tablename__ = "content_briefs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Source
    trend_type = Column(String(50))  # 'sound' | 'hashtag' | 'cluster' | 'topic'
    trend_id = Column(String(255))  # External ID or cluster UUID
    trend_name = Column(String(500))
    
    # Generated content
    hook_options = Column(JSONB)  # ["Hook 1", "Hook 2", "Hook 3"]
    script_outline = Column(JSONB)  # {"hook": "...", "problem": "...", ...}
    
    recommended_format = Column(String(50))  # 'reel' | 'carousel' | 'post'
    optimal_length_sec = Column(JSONB)  # {"min": 25, "max": 45}
    
    must_include_phrases = Column(JSONB)  # ["phrase 1", "phrase 2"]
    differentiation_twist = Column(Text)
    
    # Example posts
    top_examples = Column(JSONB)  # [{"media_id": "...", "caption_preview": "...", "plays": 123}]
    
    # Metadata
    niche = Column(String(100))
    country = Column(String(10))
    
    # Validity
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('ix_content_brief_trend_type', 'trend_type'),
        Index('ix_content_brief_niche', 'niche'),
    )


# =============================================================================
# NICHES (user-defined categories)
# =============================================================================

class Niche(Base):
    """
    User-defined niche for trend tracking.
    """
    __tablename__ = "niches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(255))
    
    # Seed data for discovery
    seed_hashtags = Column(ARRAY(String))
    seed_keywords = Column(ARRAY(String))
    seed_accounts = Column(ARRAY(String))  # Usernames to monitor
    
    # Settings
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# =============================================================================
# QUERY CACHE (for expensive queries)
# =============================================================================

class QueryCache(Base):
    """
    Cache for expensive trend queries.
    """
    __tablename__ = "query_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    query_type = Column(String(100), nullable=False)  # 'hashtag_top50', 'content_brief', etc.
    input_hash = Column(String(64), nullable=False)  # SHA256 of input params
    
    result = Column(JSONB, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        UniqueConstraint('query_type', 'input_hash', name='uq_query_cache_type_hash'),
        Index('ix_query_cache_expires', 'expires_at'),
    )


# =============================================================================
# USER SAVED ITEMS
# =============================================================================

class UserSavedItem(Base):
    """
    User's saved trends, sounds, hashtags, etc.
    """
    __tablename__ = "user_saved_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(UUID(as_uuid=True), nullable=False)  # References user system
    
    # What's saved
    entity_type = Column(String(50), nullable=False)  # 'sound' | 'hashtag' | 'trend' | 'cluster' | 'brief'
    entity_id = Column(String(255), nullable=False)
    
    # Organization
    collection_name = Column(String(255), default='default')
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'entity_type', 'entity_id', name='uq_user_saved_unique'),
        Index('ix_user_saved_user_id', 'user_id'),
        Index('ix_user_saved_collection', 'collection_name'),
    )


# =============================================================================
# EXPERIMENTS (A/B testing for creators)
# =============================================================================

class Experiment(Base):
    """
    Creator experiment for A/B testing content strategies.
    """
    __tablename__ = "experiments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Experiment definition
    name = Column(String(255))
    variable = Column(String(100))  # 'hook_style' | 'length' | 'format' | 'cta'
    control_desc = Column(Text)
    variant_desc = Column(Text)
    
    # Success criteria
    success_metric = Column(String(100))  # 'save_rate' | 'completion_rate' | 'engagement'
    target_sample_size = Column(Integer, default=4)
    
    # Status
    status = Column(String(50), default='planned')  # 'planned' | 'running' | 'completed' | 'cancelled'
    
    # Results
    control_posts = Column(JSONB)  # [{"media_id": "...", "metric_value": 123}]
    variant_posts = Column(JSONB)
    results = Column(JSONB)  # {"winner": "variant", "lift": 0.25, ...}
    
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_experiment_user_id', 'user_id'),
        Index('ix_experiment_status', 'status'),
    )
