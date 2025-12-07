"""
SQLAlchemy models for MediaPoster database
Maps to Supabase Postgres schema including EverReach/Blend tables
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, BigInteger, ForeignKey, TIMESTAMP, Interval, Numeric
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy import JSON

# SQLite compatibility removed for Postgres
# JSONB = JSON
# def ARRAY(*args, **kwargs):
#     return JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

# =====================================================
# PEOPLE GRAPH (EverReach)
# =====================================================

class Person(Base):
    """Core person entity"""
    __tablename__ = "people"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(Text)
    primary_email = Column(Text)
    company = Column(Text)
    role = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    identities = relationship("Identity", back_populates="person", cascade="all, delete-orphan")
    events = relationship("PersonEvent", back_populates="person", cascade="all, delete-orphan")
    insights = relationship("PersonInsight", back_populates="person", uselist=False, cascade="all, delete-orphan")
    outbound_messages = relationship("OutboundMessage", back_populates="person", cascade="all, delete-orphan")


class Identity(Base):
    """Cross-platform identity mapping"""
    __tablename__ = "identities"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"))
    channel = Column(String(50), nullable=False)
    handle = Column(Text, nullable=False)
    extra = Column(JSONB)
    is_verified = Column(Boolean, default=False)
    first_seen_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_seen_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    person = relationship("Person", back_populates="identities")


class PersonEvent(Base):
    """Unified event stream"""
    __tablename__ = "person_events"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"))
    channel = Column(Text, nullable=False)
    event_type = Column(Text, nullable=False)
    platform_id = Column(Text)
    content_excerpt = Column(Text)
    sentiment = Column(Float)
    traffic_type = Column(String(20), default='organic')
    event_metadata = Column(JSONB)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    occurred_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    person = relationship("Person", back_populates="events")


class PersonInsight(Base):
    """Computed person lens"""
    __tablename__ = "person_insights"
    
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), primary_key=True)
    interests = Column(JSONB)
    tone_preferences = Column(JSONB)
    channel_preferences = Column(JSONB)
    avg_reply_time = Column(Interval)
    activity_state = Column(String(20))
    last_active_at = Column(TIMESTAMP(timezone=True))
    seasonality = Column(JSONB)
    warmth_score = Column(Float)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    person = relationship("Person", back_populates="insights")


class Segment(Base):
    """Dynamic people grouping"""
    __tablename__ = "segments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text)
    definition = Column(JSONB)
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    members = relationship("SegmentMember", back_populates="segment", cascade="all, delete-orphan")
    insights = relationship("SegmentInsight", back_populates="segment", cascade="all, delete-orphan")


class SegmentMember(Base):
    """Segment membership junction table"""
    __tablename__ = "segment_members"
    
    segment_id = Column(UUID(as_uuid=True), ForeignKey("segments.id", ondelete="CASCADE"), primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), primary_key=True)
    added_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    segment = relationship("Segment", back_populates="members")


class SegmentInsight(Base):
    """Per-segment analytics"""
    __tablename__ = "segment_insights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id = Column(UUID(as_uuid=True), ForeignKey("segments.id", ondelete="CASCADE"))
    traffic_type = Column(String(20))
    top_topics = Column(JSONB)
    top_platforms = Column(JSONB)
    top_formats = Column(JSONB)
    engagement_style = Column(JSONB)
    best_times = Column(JSONB)
    expected_reach_range = Column(Text)  # INT4RANGE stored as text
    expected_engagement_rate_range = Column(Text)  # NUMRANGE stored as text
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    segment = relationship("Segment", back_populates="insights")


class OutboundMessage(Base):
    """Email/DM tracking"""
    __tablename__ = "outbound_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"))
    segment_id = Column(UUID(as_uuid=True), ForeignKey("segments.id", ondelete="SET NULL"))
    channel = Column(Text, nullable=False)
    goal_type = Column(Text)
    variant = Column(Text)
    subject = Column(Text)
    body = Column(Text)
    sent_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    opened_at = Column(TIMESTAMP(timezone=True))
    clicked_at = Column(TIMESTAMP(timezone=True))
    replied_at = Column(TIMESTAMP(timezone=True))
    message_metadata = Column(JSONB)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    
    # Relationships
    person = relationship("Person", back_populates="outbound_messages")


# =====================================================
# CONTENT GRAPH (Blend) - Extensions to existing tables
# =====================================================



class ContentItem(Base):
    """Canonical content pieces - single source of truth"""
    __tablename__ = "content_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(Text, unique=True)
    type = Column(Text)  # video, article, audio, image, carousel
    source_url = Column(Text)
    title = Column(Text)
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    variants = relationship("ContentVariant", back_populates="content_item", cascade="all, delete-orphan")
    rollup = relationship("ContentRollup", back_populates="content_item", uselist=False, cascade="all, delete-orphan")
    experiments = relationship("ContentExperiment", back_populates="content_item", cascade="all, delete-orphan")


class ContentVariant(Base):
    """Platform-specific variations of content"""
    __tablename__ = "content_variants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"))
    platform = Column(Text, nullable=False)
    variant_type = Column(Text)  # video, image, carousel, text
    status = Column(Text, default="draft")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    content_item = relationship("ContentItem", back_populates="variants")
    posts = relationship("PlatformPost", back_populates="variant", cascade="all, delete-orphan")
    metrics = relationship("ContentMetric", back_populates="variant", cascade="all, delete-orphan")


class ContentMetric(Base):
    """Time-series metrics for content variants"""
    __tablename__ = "content_metrics"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("content_variants.id", ondelete="CASCADE"), nullable=False)
    snapshot_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    # Metrics
    views = Column(BigInteger, default=0)
    impressions = Column(BigInteger, default=0)
    reach = Column(BigInteger, default=0)
    likes = Column(BigInteger, default=0)
    comments = Column(BigInteger, default=0)
    shares = Column(BigInteger, default=0)
    saves = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    watch_time_seconds = Column(Float)
    sentiment_score = Column(Float)
    
    traffic_type = Column(String(20), default='organic')  # organic or paid
    raw_metadata = Column(JSONB)  # Raw payload from platform
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    variant = relationship("ContentVariant", back_populates="metrics")


class ContentRollup(Base):

    """Aggregated cross-platform metrics"""
    __tablename__ = "content_rollups"
    
    content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True)
    total_views = Column(BigInteger, default=0)
    total_impressions = Column(BigInteger, default=0)
    total_likes = Column(BigInteger, default=0)
    total_comments = Column(BigInteger, default=0)
    total_shares = Column(BigInteger, default=0)
    total_saves = Column(BigInteger, default=0)
    total_clicks = Column(BigInteger, default=0)
    avg_watch_time_seconds = Column(Float)
    global_sentiment = Column(Float)
    best_platform = Column(Text)
    last_updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    content_item = relationship("ContentItem", back_populates="rollup")


class ContentExperiment(Base):
    """A/B testing framework"""
    __tablename__ = "content_experiments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"))
    name = Column(Text, nullable=False)
    hypothesis = Column(Text)
    primary_metric = Column(Text)
    status = Column(String(20), default='draft')
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    
    # Relationships
    content_item = relationship("ContentItem", back_populates="experiments")



# =====================================================
# PLATFORM CONNECTORS
# =====================================================

class IGConnection(Base):
    """Instagram/Meta OAuth tokens"""
    __tablename__ = "ig_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    everreach_user_id = Column(UUID(as_uuid=True), nullable=False)
    fb_page_id = Column(Text, nullable=False)
    ig_business_id = Column(Text, nullable=False)
    access_token = Column(Text, nullable=False)
    token_expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_synced_at = Column(TIMESTAMP(timezone=True))


class ConnectorConfig(Base):
    """Generic connector configuration"""
    __tablename__ = "connector_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)  # Required by database schema
    connector_type = Column(Text, nullable=False)
    config = Column(JSONB, nullable=False)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


# =====================================================
# EXISTING MODELS (from original MediaPoster)
# Kept for backward compatibility
# =====================================================

class OriginalVideo(Base):
    """Original videos uploaded from iPhone"""
    __tablename__ = "original_videos"
    
    video_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_name = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    
    date_recorded = Column(TIMESTAMP(timezone=True))
    date_uploaded = Column(TIMESTAMP(timezone=True), server_default=func.now())
    date_processed = Column(TIMESTAMP(timezone=True))
    
    transcript = Column(Text)
    topics = Column(ARRAY(Text))
    keywords = Column(ARRAY(Text))
    
    analysis_data = Column(JSONB)
    video_metadata = Column(JSONB)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    
    processing_status = Column(String(50), default="pending")
    error_message = Column(Text)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    clips = relationship("Clip", back_populates="parent_video", cascade="all, delete-orphan")
    highlights = relationship("Highlight", back_populates="video", cascade="all, delete-orphan")


class Clip(Base):
    """Generated short clips from highlights"""
    __tablename__ = "clips"
    
    clip_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_video_id = Column(UUID(as_uuid=True), ForeignKey("original_videos.video_id", ondelete="CASCADE"), nullable=False)
    
    segment_start_seconds = Column(Float, nullable=False)
    segment_end_seconds = Column(Float, nullable=False)
    clip_duration_seconds = Column(Float, nullable=False)
    
    file_path = Column(Text)
    file_size_bytes = Column(BigInteger)
    
    hook_text = Column(Text)
    caption_text = Column(Text)
    generated_hashtags = Column(ARRAY(Text))
    
    tags = Column(ARRAY(Text))
    content_category = Column(String(100))
    hook_type = Column(String(100))
    has_cta = Column(Boolean, default=False)
    visual_elements = Column(JSONB)
    target_keyword = Column(String(255))
    predicted_audience_reaction = Column(String(100))
    
    clip_status = Column(String(50), default="generated")
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    parent_video = relationship("OriginalVideo", back_populates="clips")
    # platform_posts = relationship("PlatformPost", back_populates="clip", cascade="all, delete-orphan") # Obsolete: PlatformPost now references VideoClip
    clip_tags = relationship("ClipTag", back_populates="clip", cascade="all, delete-orphan")


class PerformanceMetric(Base):
    """Performance metrics for posted clips"""
    __tablename__ = "performance_metrics"
    
    metric_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("platform_posts.id", ondelete="CASCADE"), nullable=False)
    
    measured_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    
    engagement_rate = Column(Float)
    watch_time_seconds = Column(Float)
    completion_rate = Column(Float)
    
    is_initial_check = Column(Boolean, default=False)
    minutes_after_post = Column(Integer)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    post = relationship("PlatformPost", back_populates="performance_metrics")


class Highlight(Base):
    """AI-detected highlights from videos"""
    __tablename__ = "highlights"
    
    highlight_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("original_videos.video_id", ondelete="CASCADE"), nullable=False)
    
    start_time_seconds = Column(Float, nullable=False)
    end_time_seconds = Column(Float, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    
    highlight_score = Column(Float, nullable=False)
    detection_signals = Column(JSONB)
    
    reasoning = Column(Text)
    suggested_hook = Column(Text)
    
    status = Column(String(50), default="detected")
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    video = relationship("OriginalVideo", back_populates="highlights")


class ProcessingJob(Base):
    """Async processing jobs queue"""
    __tablename__ = "processing_jobs"
    
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(100), nullable=False)
    
    entity_id = Column(UUID(as_uuid=True))
    entity_type = Column(String(50))
    
    status = Column(String(50), default="queued")
    progress_percent = Column(Integer, default=0)
    
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    
    result = Column(JSONB)
    error_message = Column(Text)
    
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class ContentTag(Base):
    """Content tags for flexible categorization"""
    __tablename__ = "content_tags"
    
    tag_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag_name = Column(String(100), unique=True, nullable=False)
    tag_category = Column(String(50))
    description = Column(Text)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    clip_tags = relationship("ClipTag", back_populates="tag", cascade="all, delete-orphan")


class ClipTag(Base):
    """Junction table for clips and tags"""
    __tablename__ = "clip_tags"
    
    clip_id = Column(UUID(as_uuid=True), ForeignKey("clips.clip_id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("content_tags.tag_id", ondelete="CASCADE"), primary_key=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    clip = relationship("Clip", back_populates="clip_tags")
    tag = relationship("ContentTag", back_populates="clip_tags")


class AIServiceLog(Base):
    """Logs for AI service usage and cost tracking"""
    __tablename__ = "ai_service_logs"
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    service_name = Column(String(100), nullable=False)
    operation = Column(String(100), nullable=False)
    
    entity_id = Column(UUID(as_uuid=True))
    entity_type = Column(String(50))
    
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    
    tokens_used = Column(Integer)
    cost_usd = Column(Float)
    processing_time_ms = Column(Integer)
    
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class SystemSetting(Base):
    """System-wide settings"""
    __tablename__ = "system_settings"
    
    setting_key = Column(String(100), primary_key=True)
    setting_value = Column(JSONB, nullable=False)
    description = Column(Text)
    
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

# =====================================================
# CONTENT INTELLIGENCE SYSTEM
# =====================================================

class AnalyzedVideo(Base):
    """Core video analysis metadata"""
    __tablename__ = "analyzed_videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_video_id = Column(UUID(as_uuid=True), ForeignKey("original_videos.video_id", ondelete="CASCADE"))
    content_item_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"))
    duration_seconds = Column(Float)
    transcript_full = Column(Text)
    analyzed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    content_item = relationship("ContentItem", foreign_keys=[content_item_id])
    segments = relationship("VideoSegment", back_populates="video", cascade="all, delete-orphan")
    words = relationship("VideoWord", back_populates="video", cascade="all, delete-orphan")
    frames = relationship("VideoFrame", back_populates="video", cascade="all, delete-orphan")


class VideoSegment(Base):
    """Timeline segments with psychology tags"""
    __tablename__ = "video_segments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("analyzed_videos.id", ondelete="CASCADE"))
    segment_type = Column(Text, nullable=False)
    start_s = Column(Float, nullable=False)
    end_s = Column(Float, nullable=False)
    hook_type = Column(Text)
    focus = Column(Text)
    authority_signal = Column(Text)
    tribe_marker = Column(Text)
    emotion = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    video = relationship("AnalyzedVideo", back_populates="segments")


class VideoWord(Base):
    """Word-level timestamps with NLP"""
    __tablename__ = "video_words"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("analyzed_videos.id", ondelete="CASCADE"))
    segment_id = Column(BigInteger, ForeignKey("video_segments.id", ondelete="CASCADE"))
    word_index = Column(Integer, nullable=False)
    word = Column(Text, nullable=False)
    start_s = Column(Float, nullable=False)
    end_s = Column(Float, nullable=False)
    is_emphasis = Column(Boolean, default=False)
    is_question = Column(Boolean, default=False)
    is_cta_keyword = Column(Boolean, default=False)
    speech_function = Column(Text)
    sentiment_score = Column(Float)
    emotion = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    video = relationship("AnalyzedVideo", back_populates="words")


class VideoFrame(Base):
    """Frame-by-frame visual analysis"""
    __tablename__ = "video_frames"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("analyzed_videos.id", ondelete="CASCADE"))
    segment_id = Column(BigInteger, ForeignKey("video_segments.id", ondelete="SET NULL"))
    frame_time_s = Column(Float, nullable=False)
    frame_url = Column(Text)
    shot_type = Column(Text)
    camera_motion = Column(Text)
    presence = Column(ARRAY(Text))
    objects = Column(ARRAY(Text))
    text_on_screen = Column(Text)
    logo_detected = Column(ARRAY(Text))
    brightness_level = Column(Text)
    color_temperature = Column(Text)
    visual_clutter_score = Column(Float)
    is_pattern_interrupt = Column(Boolean, default=False)
    is_hook_frame = Column(Boolean, default=False)
    has_meme_element = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    video = relationship("AnalyzedVideo", back_populates="frames")


class VideoCaption(Base):
    """Caption styling and positioning"""
    __tablename__ = "video_captions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("analyzed_videos.id", ondelete="CASCADE"))
    clip_id = Column(UUID(as_uuid=True), ForeignKey("clips.clip_id", ondelete="CASCADE"))
    start_s = Column(Float, nullable=False)
    end_s = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    font_family = Column(Text)
    font_weight = Column(Text)
    font_size = Column(Integer)
    text_color = Column(Text)
    background_style = Column(Text)
    position = Column(Text)
    animation = Column(Text)
    emphasized_words = Column(ARRAY(Text))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class VideoHeadline(Base):
    """Persistent headline overlay"""
    __tablename__ = "video_headlines"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("analyzed_videos.id", ondelete="CASCADE"))
    clip_id = Column(UUID(as_uuid=True), ForeignKey("video_clips.id", ondelete="CASCADE"))
    main_text = Column(Text, nullable=False)
    sub_text = Column(Text)
    start_s = Column(Float, default=0)
    end_s = Column(Float)
    position = Column(Text)
    font_family = Column(Text)
    font_size = Column(Integer)
    text_color = Column(Text)
    background_style = Column(Text)
    corner_radius = Column(Integer)
    padding = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class PlatformPost(Base):
    """Platform-specific post tracking"""
    __tablename__ = "platform_posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_variant_id = Column(UUID(as_uuid=True), ForeignKey("content_variants.id", ondelete="CASCADE"))
    clip_id = Column(UUID(as_uuid=True), ForeignKey("video_clips.id", ondelete="SET NULL"))
    platform = Column(Text, nullable=False)
    platform_post_id = Column(Text, nullable=False)
    platform_url = Column(Text)
    published_at = Column(TIMESTAMP(timezone=True))
    scheduled_for = Column(TIMESTAMP(timezone=True))
    status = Column(Text, default="scheduled")
    title = Column(Text)
    caption = Column(Text)
    hashtags = Column(ARRAY(Text))
    thumbnail_url = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    
    # Relationships
    checkbacks = relationship("PlatformCheckback", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("PostComment", back_populates="post", cascade="all, delete-orphan")

    clip_posts = relationship("ClipPost", back_populates="post", cascade="all, delete-orphan")
    performance_metrics = relationship("PerformanceMetric", back_populates="post", cascade="all, delete-orphan")
    performance_analytics = relationship("ContentPerformanceAnalytics", back_populates="post", cascade="all, delete-orphan")
    variant = relationship("ContentVariant", back_populates="posts")
    # clip = relationship("Clip", back_populates="platform_posts") # Obsolete: clip_id now references video_clips.id



class PlatformCheckback(Base):
    """Checkback metrics at intervals"""
    __tablename__ = "platform_checkbacks"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    platform_post_id = Column(UUID(as_uuid=True), ForeignKey("platform_posts.id", ondelete="CASCADE"))
    checkback_h = Column(Integer, nullable=False)
    checked_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    views = Column(Integer, default=0)
    unique_viewers = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    avg_watch_time_s = Column(Float)
    avg_watch_pct = Column(Float)
    retention_curve = Column(JSONB)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    profile_taps = Column(Integer, default=0)
    link_clicks = Column(Integer, default=0)
    like_rate = Column(Float)
    comment_rate = Column(Float)
    share_rate = Column(Float)
    save_rate = Column(Float)
    cta_response_count = Column(Integer, default=0)
    engaged_users = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    post = relationship("PlatformPost", back_populates="checkbacks")


class PostComment(Base):
    """Comment-level sentiment analysis"""
    __tablename__ = "post_comments"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    platform_post_id = Column(UUID(as_uuid=True), ForeignKey("platform_posts.id", ondelete="CASCADE"))
    platform_comment_id = Column(Text, nullable=False)
    author_handle = Column(Text)
    author_name = Column(Text)
    text = Column(Text, nullable=False)
    created_at_platform = Column(TIMESTAMP(timezone=True))
    sentiment_score = Column(Float)
    emotion_tags = Column(ARRAY(Text))
    intent = Column(Text)
    theme_tags = Column(ARRAY(Text))
    is_cta_response = Column(Boolean, default=False)
    cta_keyword = Column(Text)
    is_spam = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    post = relationship("PlatformPost", back_populates="comments")


class WeeklyMetric(Base):
    """Weekly North Star Metrics"""
    __tablename__ = "weekly_metrics"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    week_start_date = Column(JSON, nullable=False)  # DATE type
    user_id = Column(UUID(as_uuid=True))
    engaged_reach = Column(Integer, default=0)
    engaged_reach_delta_pct = Column(Float)
    content_leverage_score = Column(Float, default=0)
    cls_delta_pct = Column(Float)
    warm_lead_flow = Column(Integer, default=0)
    warm_lead_flow_delta_pct = Column(Float)
    total_posts = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    total_watch_time_s = Column(BigInteger, default=0)
    avg_retention_pct = Column(Float)
    platform_reach = Column(JSONB)
    platform_posts = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class ContentInsight(Base):
    """AI-generated insights"""
    __tablename__ = "content_insights"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    insight_type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    metric_impact = Column(Text)
    based_on_post_ids = Column(ARRAY(UUID(as_uuid=True)))
    based_on_segment_ids = Column(ARRAY(UUID(as_uuid=True)))
    sample_size = Column(Integer)
    confidence_score = Column(Float)
    pattern_data = Column(JSONB)
    recommended_action = Column(JSONB)
    status = Column(Text, default="active")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True))
    dismissed_at = Column(TIMESTAMP(timezone=True))
    times_applied = Column(Integer, default=0)
    avg_result_improvement = Column(Float)


# =====================================================
# VIDEO CLIPS (Clip Generation System)
# =====================================================

class VideoClip(Base):
    """Video clip configurations with AI suggestions"""
    __tablename__ = "video_clips"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), nullable=False)  # FK to videos table
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Clip timing (in seconds)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    # duration is computed in DB as GENERATED column
    
    # Clip metadata
    title = Column(String(500))
    description = Column(Text)
    clip_type = Column(String(50), default="custom")  # highlight, full, custom, ai_generated
    
    # Configuration (JSONB for flexibility)
    overlay_config = Column(JSONB, default={})  # text overlays, positioning
    caption_config = Column(JSONB, default={})  # caption styling, animations
    thumbnail_config = Column(JSONB, default={})  # thumbnail frame selection
    
    # AI-generated insights
    ai_suggested = Column(Boolean, default=False)
    ai_score = Column(Float)  # 0-1 quality score
    ai_reasoning = Column(Text)  # why AI selected this clip
    
    # Segment associations
    segment_ids = Column(ARRAY(UUID(as_uuid=True)))  # video_segments
    hook_segment_id = Column(UUID(as_uuid=True))  # primary hook
    
    # Platform optimization
    platform_variants = Column(JSONB, default={})  # platform-specific configs
    target_platforms = Column(ARRAY(String(50)))  # intended platforms
    
    # Status tracking
    status = Column(String(50), default="draft")  # draft, ready, published, archived
    render_status = Column(String(50))  # pending, processing, completed, failed
    rendered_url = Column(String(500))  # URL to rendered video
    render_error = Column(Text)  # error message if rendering failed
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    clip_posts = relationship("ClipPost", back_populates="clip", cascade="all, delete-orphan")


class ClipPost(Base):
    """Junction table linking clips to platform posts"""
    __tablename__ = "clip_posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clip_id = Column(UUID(as_uuid=True), ForeignKey("video_clips.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("platform_posts.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(50), nullable=False)
    
    # Platform-specific overrides
    platform_config = Column(JSONB, default={})  # platform metadata overrides
    thumbnail_url = Column(String(500))  # platform-specific thumbnail
    
    # Timestamp
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    clip = relationship("VideoClip", back_populates="clip_posts")
    post = relationship("PlatformPost", back_populates="clip_posts")


# =====================================================
# SEGMENT PERFORMANCE & EDITING (Analysis Enhancement)
# =====================================================

class SegmentPerformance(Base):
    """Tracks performance metrics for video segments"""
    __tablename__ = "segment_performance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id = Column(UUID(as_uuid=True), nullable=False)  # FK to video_segments
    post_id = Column(UUID(as_uuid=True), ForeignKey("platform_posts.id", ondelete="CASCADE"), nullable=False)
    
    # Metrics at segment timestamps  
    views_at_start = Column(Integer, default=0)
    views_at_end = Column(Integer, default=0)
    retention_rate = Column(Float)  # % who watched full segment
    
    # Engagement during segment
    likes_during = Column(Integer, default=0)
    comments_during = Column(Integer, default=0)
    shares_during = Column(Integer, default=0)
    replays_during = Column(Integer, default=0)
    
    # Calculated scores (auto-computed by DB trigger)
    engagement_score = Column(Float)
    effectiveness_score = Column(Float)
    
    # Timestamps
    measured_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class SegmentEditHistory(Base):
    """Audit log of manual segment edits"""
    __tablename__ = "segment_edit_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id = Column(UUID(as_uuid=True), nullable=False)  # FK to video_segments
    edited_by = Column(UUID(as_uuid=True), nullable=False)
    
    # What changed
    edit_type = Column(String(50), nullable=False)  # created, updated, split, merged, deleted
    field_changes = Column(JSONB)  # Before/after values
    
    # Why
    edit_reason = Column(Text)
    
    # When
    edited_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


# =====================================================
# CONTENT CALENDAR & AI RECOMMENDATIONS
# =====================================================


class PostingGoal(Base):
    """User-defined goals for content performance and campaigns"""
    __tablename__ = "posting_goals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Goal configuration
    goal_type = Column(String(50), nullable=False)  # campaign, performance, fulfillment, sentiment
    goal_name = Column(String(200), nullable=False)
    target_metrics = Column(JSONB, nullable=False)  # {metric: target_value}
    priority = Column(Integer, default=1)  # 1-5, 5 being highest
    
    # Timeline
    start_date = Column(TIMESTAMP(timezone=True))
    end_date = Column(TIMESTAMP(timezone=True))
    
    # Status
    status = Column(String(50), default='active')  # active, paused, completed
    
    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class ScheduledPost(Base):
    """Posts scheduled for future publishing"""
    __tablename__ = "scheduled_posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Content reference
    clip_id = Column(UUID(as_uuid=True), ForeignKey("video_clips.id", ondelete="CASCADE"))
    content_variant_id = Column(UUID(as_uuid=True), ForeignKey("content_variants.id", ondelete="CASCADE"))
    media_project_id = Column(UUID(as_uuid=True), ForeignKey("media_creation_projects.id", ondelete="SET NULL"))  # Link to media creation projects
    
    # Platform details
    platform = Column(String(50), nullable=False)
    platform_account_id = Column(UUID(as_uuid=True))  # References connector_configs
    
    # Scheduling
    scheduled_time = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Publishing status
    status = Column(String(50), default='scheduled')  # scheduled, publishing, published, failed, cancelled, max_retries_reached
    publish_response = Column(JSONB)  # Response from platform API
    error_message = Column(Text)  # Deprecated - use last_error
    
    # Platform post tracking
    platform_post_id = Column(Text)  # ID from platform after publishing
    platform_url = Column(Text)  # URL to published post
    
    # Retry tracking (added via migration)
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(TIMESTAMP(timezone=True))
    last_error = Column(Text)
    
    # AI recommendation tracking
    is_ai_recommended = Column(Boolean, default=False)
    recommendation_score = Column(Float)
    recommendation_reasoning = Column(Text)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    published_at = Column(TIMESTAMP(timezone=True))
    
    # Relationships
    clip = relationship("VideoClip", foreign_keys=[clip_id])
    content_variant = relationship("ContentVariant", foreign_keys=[content_variant_id])


# =====================================================
# MEDIA CREATION SYSTEM (Phase 5)
# =====================================================

class MediaCreationTemplate(Base):
    """Templates for media creation"""
    __tablename__ = "media_creation_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    template_name = Column(String(200), nullable=False)
    content_type = Column(String(50), nullable=False)
    description = Column(Text)
    
    template_config = Column(JSONB, nullable=False, default={})
    ai_provider = Column(String(50))
    ai_model = Column(String(100))
    
    theme = Column(String(100))
    color_scheme = Column(JSONB)
    font_family = Column(String(100))
    
    default_duration = Column(Integer)
    aspect_ratio = Column(String(20))
    resolution = Column(String(20))
    
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class MediaCreationProject(Base):
    """Media creation projects"""
    __tablename__ = "media_creation_projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    project_name = Column(String(200), nullable=False)
    content_type = Column(String(50), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("media_creation_templates.id"))
    
    content_data = Column(JSONB, nullable=False, default={})
    source_video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"))
    source_images = Column(JSONB)
    generated_media_url = Column(Text)
    thumbnail_url = Column(Text)
    
    editing_state = Column(JSONB)
    is_draft = Column(Boolean, default=True)
    
    status = Column(String(50), default='draft')
    error_message = Column(Text)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(TIMESTAMP(timezone=True))


class MediaCreationAsset(Base):
    """Assets for media creation projects"""
    __tablename__ = "media_creation_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("media_creation_projects.id", ondelete="CASCADE"), nullable=False)
    
    asset_type = Column(String(50), nullable=False)
    asset_url = Column(Text, nullable=False)
    asset_path = Column(Text)
    
    asset_metadata = Column(JSONB, default={})  # Renamed from 'metadata' (reserved in SQLAlchemy)
    order_index = Column(Integer)
    
    ai_provider = Column(String(50))
    ai_model = Column(String(100))
    generation_prompt = Column(Text)
    generation_params = Column(JSONB)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class AIRecommendation(Base):
    """AI-generated content recommendations"""
    __tablename__ = "ai_recommendations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Recommendation details
    recommendation_type = Column(String(50), nullable=False)  # content, timing, platform, optimization
    content_id = Column(UUID(as_uuid=True))  # Reference to clip or content item
    recommendation_data = Column(JSONB, nullable=False)  # Full recommendation details
    
    # AI analysis
    confidence_score = Column(Float)  # 0-1
    reasoning = Column(Text)  # AI explanation
    based_on_goals = Column(ARRAY(UUID(as_uuid=True)))  # Array of goal IDs
    
    # User interaction
    status = Column(String(50), default='pending')  # pending, accepted, rejected, expired
    user_feedback = Column(JSONB)  # User's response/rating
    
    # Expiry
    expires_at = Column(TIMESTAMP(timezone=True))
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class ContentPerformanceAnalytics(Base):
    """Advanced analytics for content performance"""
    __tablename__ = "content_performance_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("platform_posts.id", ondelete="CASCADE"))
    analysis_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Performance scores (normalized 0-100)
    engagement_score = Column(Float)
    reach_score = Column(Float)
    sentiment_score = Column(Float)
    virality_score = Column(Float)
    
    # Calculated metrics
    engagement_rate = Column(Float)
    completion_rate = Column(Float)
    share_rate = Column(Float)
    save_rate = Column(Float)
    
    # Time-based analysis
    peak_engagement_time = Column(TIMESTAMP(timezone=True))
    engagement_velocity = Column(JSONB)  # Hour-by-hour breakdown
    
    # Audience insights
    audience_demographics = Column(JSONB)
    top_performing_segments = Column(JSONB)
    
    # Content insights
    hook_effectiveness = Column(Float)
    cta_effectiveness = Column(Float)
    optimal_length_seconds = Column(Float)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    post = relationship("PlatformPost", back_populates="performance_analytics")


# =====================================================
# VIDEO LIBRARY (Phase 2)
# =====================================================

class Video(Base):
    """Video Library - Reference to video files"""
    __tablename__ = "videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    source_type = Column(Text, nullable=False)  # 'local', 'gdrive', 'supabase', 's3', 'other'
    source_uri = Column(Text, nullable=False)
    file_name = Column(Text)
    file_size = Column(BigInteger)  # File size in bytes (supports up to ~9.2 exabytes)
    duration_sec = Column(Integer)
    resolution = Column(Text)
    aspect_ratio = Column(Text)
    
    # Thumbnail fields
    thumbnail_path = Column(Text)
    thumbnail_generated_at = Column(TIMESTAMP(timezone=True))
    best_frame_score = Column(Numeric(5, 3))
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    analysis = relationship("VideoAnalysis", back_populates="video", uselist=False, cascade="all, delete-orphan")


class VideoAnalysis(Base):
    """AI Analysis for Video Library"""
    __tablename__ = "video_analysis"
    
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True)
    transcript = Column(Text)
    topics = Column(ARRAY(Text))
    hooks = Column(ARRAY(Text))
    tone = Column(Text)
    pacing = Column(Text)
    key_moments = Column(JSONB)
    visual_analysis = Column(JSONB)  # New: Visual context from frames
    music_suggestion = Column(JSONB) # New: Background music recommendation
    pre_social_score = Column(Float)
    analysis_version = Column(Text)
    analyzed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="analysis")
