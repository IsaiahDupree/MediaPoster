"""
SQLAlchemy models for MediaPoster database
Maps to Supabase Postgres schema including EverReach/Blend tables
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, BigInteger, ForeignKey, TIMESTAMP, Interval, Numeric, Index, Date
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
    
    # Post content (stored to avoid falling back to filename/transcript)
    title = Column(Text)  # Proper title, not filename
    caption = Column(Text)  # Proper caption, not transcript
    hashtags = Column(ARRAY(Text))  # Hashtags array
    
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
# CONTENT METRICS HISTORY (Growth Tracking)
# =====================================================

class ContentMetricsSnapshot(Base):
    """Historical metrics snapshot for tracking content growth over time"""
    __tablename__ = "content_metrics_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to the published post
    scheduled_post_id = Column(UUID(as_uuid=True), ForeignKey("scheduled_posts.id", ondelete="CASCADE"))
    
    # Platform info (denormalized for query efficiency)
    platform = Column(String(50), nullable=False)
    platform_post_id = Column(String(255))
    
    # Metrics at this point in time
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    
    # Engagement metrics
    engagement_rate = Column(Float, default=0.0)
    
    # Video-specific metrics
    watch_time_seconds = Column(Integer, default=0)
    avg_view_duration = Column(Float, default=0.0)
    
    # Timestamp when this snapshot was taken
    snapshot_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Source of the data
    data_source = Column(String(50), default='api')  # api, manual, backfill
    
    # Relationships
    scheduled_post = relationship("ScheduledPost", foreign_keys=[scheduled_post_id])
    
    __table_args__ = (
        # Index for efficient time-series queries
        Index('idx_metrics_post_time', scheduled_post_id, snapshot_at.desc()),
        Index('idx_metrics_platform_time', platform, snapshot_at.desc()),
    )


class ContentGrowthSummary(Base):
    """Aggregated growth metrics per content (updated periodically)"""
    __tablename__ = "content_growth_summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    scheduled_post_id = Column(UUID(as_uuid=True), ForeignKey("scheduled_posts.id", ondelete="CASCADE"), unique=True)
    platform = Column(String(50), nullable=False)
    
    # Current totals
    current_views = Column(Integer, default=0)
    current_likes = Column(Integer, default=0)
    current_comments = Column(Integer, default=0)
    current_shares = Column(Integer, default=0)
    current_engagement_rate = Column(Float, default=0.0)
    
    # Growth metrics (percentage change)
    growth_24h_views = Column(Float, default=0.0)
    growth_7d_views = Column(Float, default=0.0)
    growth_30d_views = Column(Float, default=0.0)
    
    growth_24h_engagement = Column(Float, default=0.0)
    growth_7d_engagement = Column(Float, default=0.0)
    growth_30d_engagement = Column(Float, default=0.0)
    
    # Velocity (rate per day)
    views_per_day = Column(Float, default=0.0)
    engagement_per_day = Column(Float, default=0.0)
    
    # Peak metrics
    peak_views_day = Column(Date)
    peak_views_count = Column(Integer, default=0)
    
    # Timestamps
    first_snapshot_at = Column(TIMESTAMP(timezone=True))
    last_snapshot_at = Column(TIMESTAMP(timezone=True))
    last_calculated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    scheduled_post = relationship("ScheduledPost", foreign_keys=[scheduled_post_id])


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
    title = Column(String(150))  # AI-generated title (~20% of platform char limit)
    file_size = Column(BigInteger)  # File size in bytes (supports up to ~9.2 exabytes)
    duration_sec = Column(Integer)
    resolution = Column(Text)
    aspect_ratio = Column(Text)
    
    # Thumbnail fields
    thumbnail_path = Column(Text)
    thumbnail_generated_at = Column(TIMESTAMP(timezone=True))
    best_frame_score = Column(Numeric(5, 3))
    
    # Curation fields
    curation_status = Column(Text, default='pending')  # 'pending', 'approved', 'rejected'
    auto_curated = Column(Boolean, default=False)
    auto_curation_reason = Column(Text)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    analysis = relationship("VideoAnalysis", back_populates="video", uselist=False, cascade="all, delete-orphan")


class VideoAnalysis(Base):
    """AI Analysis for Video Library - Matches actual database schema"""
    __tablename__ = "video_analysis"
    
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True)
    transcript = Column(Text)
    topics = Column(ARRAY(Text))
    hooks = Column(ARRAY(Text))
    tone = Column(Text)
    pacing = Column(Text)
    key_moments = Column(JSONB)
    pre_social_score = Column(Numeric)  # Score before posting (predicted)
    analysis_version = Column(Text)
    analyzed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Deep analysis columns (added via migration)
    visual_analysis = Column(JSONB)  # Frame-by-frame visual analysis
    deep_analysis = Column(JSONB)  # Comprehensive deep analysis from GPT-4 Vision
    frame_analyses = Column(JSONB)  # Individual frame analysis data
    platform_content = Column(JSONB)  # Platform-specific content recommendations
    detected_hook = Column(Text)  # Best detected hook phrase
    music_suggestion = Column(JSONB)  # AI-suggested music recommendations
    pillar_tags = Column(ARRAY(Text))  # Content pillar categorization
    format_tags = Column(ARRAY(Text))  # Format tags
    
    # Audio analysis fields (Background Music Detection)
    audio_analysis = Column(JSONB)  # Full audio analysis result
    has_background_music = Column(Boolean)  # Quick boolean for filtering
    audio_type = Column(Text)  # 'speech_only', 'music_only', 'mixed', 'silence', 'ambient'
    music_confidence = Column(Numeric(4, 3))  # 0.0-1.0 confidence
    speech_ratio = Column(Numeric(4, 3))  # Speech ratio 0.0-1.0
    music_characteristics = Column(JSONB)  # {tempo_bpm, energy, genre_hints, mood}
    copyright_risk = Column(Text, default='unknown')  # 'low', 'medium', 'high', 'unknown'
    audio_analyzed_at = Column(TIMESTAMP(timezone=True))  # When audio was analyzed
    
    # Music matching fields (Auto Background Music Suggestion)
    suggested_music_id = Column(UUID(as_uuid=True))  # ID of auto-suggested music track
    music_match_score = Column(Numeric(4, 3))  # Compatibility score 0.0-1.0
    music_match_reasoning = Column(Text)  # Explanation of why music was matched
    music_alternatives = Column(JSONB)  # Array of alternative music options
    music_matched_at = Column(TIMESTAMP(timezone=True))  # When music matching was performed
    
    # Comprehensive transcription metadata (OpenAI Whisper)
    transcription_data = Column(JSONB)  # Full transcription response (words, segments, etc.)
    transcription_language = Column(Text)  # Detected language (e.g., 'en', 'es')
    transcription_duration_sec = Column(Numeric(10, 3))  # Duration in seconds from Whisper
    transcription_word_count = Column(Integer)  # Total word count
    transcription_segment_count = Column(Integer)  # Total segment count
    words_per_minute = Column(Numeric(6, 2))  # Speaking pace
    significant_pauses = Column(JSONB)  # Array of pauses > 1s
    avg_confidence = Column(Numeric(6, 4))  # Average logprob across segments
    silence_ratio = Column(Numeric(4, 3))  # Ratio of silence/no-speech
    transcribed_at = Column(TIMESTAMP(timezone=True))  # When transcription was performed
    
    # Sentiment analysis fields
    sentiment_score = Column(Numeric(4, 3))  # -1.0 to 1.0
    sentiment_label = Column(Text)  # 'very_negative', 'negative', 'neutral', 'positive', 'very_positive'
    transcript_hash = Column(Text)  # For duplicate detection
    
    # Curation fields
    curation_status = Column(Text)  # 'pending', 'approved', 'rejected'
    curated_at = Column(TIMESTAMP(timezone=True))
    
    # Creative Brief Generation Fields (Enhanced Analysis v3.2)
    pain_points = Column(ARRAY(Text))  # Problems/frustrations the content addresses
    emotional_drivers = Column(ARRAY(Text))  # Motivations (FOMO, transformation, belonging)
    emotional_journey = Column(JSONB)  # {opening_emotion, peak_emotion, closing_emotion}
    call_to_action = Column(JSONB)  # {type, text, strength, timestamp_hint}
    scene_structure = Column(JSONB)  # [{start_sec, end_sec, role, summary, emotion}]
    content_type = Column(Text)  # tutorial/storytime/review/transformation/etc.
    target_audience = Column(JSONB)  # {demographic, interests[], awareness_level}
    
    # Relationships
    video = relationship("Video", back_populates="analysis")


# =====================================================
# API USAGE TRACKING (Phase 52)
# =====================================================

class APIProvider(Base):
    """External API provider configuration"""
    __tablename__ = "api_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)  # e.g., 'rapidapi_tiktok'
    display_name = Column(Text)  # e.g., 'RapidAPI TikTok'
    host = Column(Text)  # e.g., 'tiktok-api6.p.rapidapi.com'
    base_url = Column(Text)  # Full base URL
    
    # Current tier configuration
    current_tier = Column(Text, default='basic')  # e.g., 'basic', 'pro', 'ultra', 'mega'
    monthly_limit = Column(Integer, default=50)
    monthly_cost_usd = Column(Numeric(10, 2), default=0)
    overage_cost_per_call = Column(Numeric(10, 6), default=0)
    rate_limit_per_second = Column(Integer, default=0)
    
    # Budget thresholds
    warning_threshold_pct = Column(Float, default=80.0)
    hard_limit_pct = Column(Float, default=95.0)
    
    # Available endpoints (JSON array)
    endpoints = Column(JSONB)  # [{name, path, method, description}]
    
    # Tier options (JSON object)
    tier_options = Column(JSONB)  # {tier_name: {limit, cost, overage, rate_limit}}
    
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    usage_logs = relationship("APIUsageLog", back_populates="provider", cascade="all, delete-orphan")
    monthly_summaries = relationship("APIMonthlyUsage", back_populates="provider", cascade="all, delete-orphan")


class APIUsageLog(Base):
    """Individual API call log"""
    __tablename__ = "api_usage_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("api_providers.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(Text)  # e.g., '/video/details'
    
    # Call details
    success = Column(Boolean, default=True)
    cached = Column(Boolean, default=False)  # If served from cache (doesn't count against quota)
    response_time_ms = Column(Integer)
    response_size_bytes = Column(Integer)
    status_code = Column(Integer)
    
    # Context
    resource_id = Column(Text)  # e.g., video_id, user_id
    resource_type = Column(Text)  # e.g., 'video', 'user', 'search'
    call_metadata = Column(JSONB)  # Additional context
    
    # Timing
    called_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    provider = relationship("APIProvider", back_populates="usage_logs")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_api_usage_provider_date', 'provider_id', 'called_at'),
        Index('idx_api_usage_endpoint', 'endpoint'),
    )


class APIMonthlyUsage(Base):
    """Monthly aggregated API usage for budget tracking"""
    __tablename__ = "api_monthly_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("api_providers.id", ondelete="CASCADE"), nullable=False)
    
    # Period
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    
    # Usage counts
    total_calls = Column(Integer, default=0)
    successful_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)
    cached_calls = Column(Integer, default=0)  # Calls served from cache
    
    # Budget tracking
    monthly_limit = Column(Integer)  # Limit at time of tracking
    tier_name = Column(Text)  # Tier at time of tracking
    base_cost_usd = Column(Numeric(10, 2), default=0)
    overage_calls = Column(Integer, default=0)
    overage_cost_usd = Column(Numeric(10, 2), default=0)
    total_cost_usd = Column(Numeric(10, 2), default=0)
    
    # Endpoint breakdown (JSON)
    endpoint_usage = Column(JSONB)  # {endpoint: {calls, success, failed}}
    
    # Timestamps
    period_start = Column(Date)
    period_end = Column(Date)
    last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    provider = relationship("APIProvider", back_populates="monthly_summaries")
    
    # Unique constraint on provider + year + month
    __table_args__ = (
        Index('idx_api_monthly_provider_period', 'provider_id', 'year', 'month', unique=True),
    )


class APIResponseCache(Base):
    """Cache for API responses to reduce duplicate calls"""
    __tablename__ = "api_response_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key = Column(Text, nullable=False, unique=True)  # e.g., 'tiktok:video:123456789'
    provider_name = Column(Text, nullable=False)
    endpoint = Column(Text)
    
    # Cached response
    response_data = Column(JSONB)
    
    # Cache management
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True))
    hit_count = Column(Integer, default=0)
    last_hit_at = Column(TIMESTAMP(timezone=True))
    
    # Index for cache lookups
    __table_args__ = (
        Index('idx_cache_key', 'cache_key'),
        Index('idx_cache_expires', 'expires_at'),
    )


# =====================================================
# POSTED CONTENT TRACKING
# =====================================================

class PostedContent(Base):
    """Track content that has been published to social media platforms"""
    __tablename__ = "posted_content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Platform info
    platform = Column(Text, nullable=False)  # tiktok, instagram, youtube, twitter
    platform_post_id = Column(Text)  # Blotato submission ID
    platform_url = Column(Text)  # Public URL on the platform
    
    # Account info
    account_id = Column(Text)  # Blotato account ID
    account_username = Column(Text)
    
    # Local content reference
    media_id = Column(UUID(as_uuid=True))  # Reference to local media library
    
    # Content details
    caption = Column(Text)
    hashtags = Column(ARRAY(Text))
    
    # Analytics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    
    # Status
    status = Column(Text, default='published')  # published, failed, deleted
    error_message = Column(Text)
    
    # Timestamps
    posted_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    analytics_updated_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_posted_content_platform', 'platform'),
        Index('idx_posted_content_media_id', 'media_id'),
        Index('idx_posted_content_platform_post_id', 'platform_post_id'),
        Index('idx_posted_content_posted_at', 'posted_at'),
    )


# =====================================================
# CONTENT OPS ENTITIES (Phase 2)
# =====================================================

class Brand(Base):
    """Brand entity - represents a company/product brand"""
    __tablename__ = "brands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text)
    logo_url = Column(Text)
    website_url = Column(Text)

    # Brand voice and values
    brand_voice = Column(JSONB)  # {tone: str, keywords: List[str], avoid: List[str]}
    core_values = Column(ARRAY(Text))
    target_audience = Column(Text)

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    offers = relationship("Offer", back_populates="brand", cascade="all, delete-orphan")
    templates = relationship("ContentTemplate", back_populates="brand", cascade="all, delete-orphan")


class Offer(Base):
    """Offer entity - products/services/CTAs linked to a brand"""
    __tablename__ = "offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)

    title = Column(Text, nullable=False)
    description = Column(Text)
    offer_type = Column(String(50))  # product, service, lead_magnet, content, event

    # Offer details
    landing_page_url = Column(Text)
    cta_text = Column(Text)  # Default CTA for this offer
    terms = Column(Text)  # Terms and conditions

    # Pricing (optional)
    price = Column(Numeric(10, 2))
    currency = Column(String(3), default='USD')

    # Metadata
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher = more priority
    valid_from = Column(TIMESTAMP(timezone=True))
    valid_until = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    brand = relationship("Brand", back_populates="offers")
    touchpoints = relationship("Touchpoint", back_populates="offer", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_offers_brand_id', 'brand_id'),
        Index('idx_offers_is_active', 'is_active'),
    )


class ICP(Base):
    """Ideal Customer Profile - target audience personas"""
    __tablename__ = "icps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(Text, nullable=False)  # e.g., "Solo Founder", "Enterprise CMO"
    description = Column(Text)

    # Demographics
    age_range = Column(String(50))  # e.g., "25-34", "35-44"
    location = Column(ARRAY(Text))  # Countries/regions
    job_titles = Column(ARRAY(Text))
    company_size = Column(String(50))  # e.g., "1-10", "11-50", "51-200"

    # Psychographics
    pain_points = Column(ARRAY(Text))
    goals = Column(ARRAY(Text))
    interests = Column(ARRAY(Text))
    objections = Column(ARRAY(Text))

    # Awareness level (default for this ICP)
    default_awareness_level = Column(String(50))  # unaware, problem_aware, solution_aware, product_aware, most_aware

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    touchpoints = relationship("Touchpoint", back_populates="icp", cascade="all, delete-orphan")


class ContentTemplate(Base):
    """Content template - AI prompts with FATE weights and awareness levels"""
    __tablename__ = "content_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"))

    # Template identity
    name = Column(Text, nullable=False)
    description = Column(Text)
    template_type = Column(String(50))  # post, email, dm, ad, story

    # Template content
    prompt_text = Column(Text, nullable=False)  # AI prompt with {variable} placeholders
    required_variables = Column(ARRAY(Text))  # Extracted variable names

    # FATE weights (must sum to ~1.0)
    fate_focus = Column(Float, nullable=False)
    fate_authority = Column(Float, nullable=False)
    fate_tribe = Column(Float, nullable=False)
    fate_emotion = Column(Float, nullable=False)

    # Awareness level
    awareness_level = Column(String(50), nullable=False)  # unaware, problem_aware, solution_aware, product_aware, most_aware

    # CTA configuration
    cta_strength = Column(String(20))  # none, soft, direct
    cta_template = Column(Text)  # Optional CTA template

    # Performance tracking
    usage_count = Column(Integer, default=0)
    avg_reward_score = Column(Float, default=0.0)
    performance_label = Column(String(20))  # winner, promising, average, loser

    # Metadata
    is_active = Column(Boolean, default=True)
    created_by = Column(Text)  # User ID or "system"
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    brand = relationship("Brand", back_populates="templates")
    touchpoints = relationship("Touchpoint", back_populates="template", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_templates_brand_id', 'brand_id'),
        Index('idx_templates_awareness_level', 'awareness_level'),
        Index('idx_templates_performance', 'performance_label'),
    )


class Touchpoint(Base):
    """Touchpoint - links Brand → Offer → ICP → Template with attribution"""
    __tablename__ = "touchpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Traceback chain
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"))
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False)
    icp_id = Column(UUID(as_uuid=True), ForeignKey("icps.id", ondelete="CASCADE"))
    template_id = Column(UUID(as_uuid=True), ForeignKey("content_templates.id", ondelete="CASCADE"))

    # Touchpoint details
    channel = Column(String(50), nullable=False)  # twitter, instagram, email, dm, ad
    message_type = Column(String(50))  # post, story, comment, dm, email

    # Content reference
    posted_content_id = Column(UUID(as_uuid=True), ForeignKey("posted_content.id", ondelete="SET NULL"))
    shortlink = Column(Text)  # Attribution shortlink

    # Performance metrics (copied from posted_content on checkback)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    reposts = Column(Integer, default=0)

    # Calculated scores
    engagement_rate = Column(Float, default=0.0)
    click_rate = Column(Float, default=0.0)
    reward_score = Column(Float, default=0.0)

    # Metadata
    published_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    offer = relationship("Offer", back_populates="touchpoints")
    icp = relationship("ICP", back_populates="touchpoints")
    template = relationship("ContentTemplate", back_populates="touchpoints")

    # Indexes
    __table_args__ = (
        Index('idx_touchpoints_offer_id', 'offer_id'),
        Index('idx_touchpoints_icp_id', 'icp_id'),
        Index('idx_touchpoints_template_id', 'template_id'),
        Index('idx_touchpoints_channel', 'channel'),
        Index('idx_touchpoints_published_at', 'published_at'),
    )


class Shortlink(Base):
    """Shortlink tracking for attribution"""
    __tablename__ = "shortlinks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Shortlink details
    short_code = Column(String(20), unique=True, nullable=False)
    destination_url = Column(Text, nullable=False)

    # Attribution chain
    touchpoint_id = Column(UUID(as_uuid=True), ForeignKey("touchpoints.id", ondelete="CASCADE"))
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"))
    template_id = Column(UUID(as_uuid=True), ForeignKey("content_templates.id", ondelete="SET NULL"))
    icp_id = Column(UUID(as_uuid=True), ForeignKey("icps.id", ondelete="SET NULL"))

    # UTM parameters
    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(200))
    utm_content = Column(String(200))
    utm_term = Column(String(200))

    # Click tracking
    click_count = Column(Integer, default=0)
    last_clicked_at = Column(TIMESTAMP(timezone=True))

    # Metadata
    is_active = Column(Boolean, default=True)
    expires_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_shortlinks_short_code', 'short_code'),
        Index('idx_shortlinks_touchpoint_id', 'touchpoint_id'),
        Index('idx_shortlinks_offer_id', 'offer_id'),
    )


# =====================================================
# CONTENT OPS ENTITIES (Phase 2)
# =====================================================

class CreatorProfile(Base):
    """Creator Profile - Voice rules, banned phrases, tone descriptors (ENTITY-004)"""
    __tablename__ = "creator_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)

    # Profile details
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Voice rules
    voice_tone = Column(ARRAY(String))  # ["casual", "educational", "witty"]
    voice_style = Column(ARRAY(String))  # ["first_person", "storytelling", "data_driven"]

    # Banned phrases
    banned_phrases = Column(ARRAY(String))  # ["click here", "limited time only"]
    banned_patterns = Column(ARRAY(String))  # ["ALL CAPS", "excessive emojis"]

    # Tone descriptors
    tone_descriptors = Column(JSONB)  # {"formality": "casual", "humor": "high", "technical": "medium"}

    # Content preferences
    preferred_length_min = Column(Integer)  # Min word count
    preferred_length_max = Column(Integer)  # Max word count
    preferred_formats = Column(ARRAY(String))  # ["thread", "single_post", "carousel"]

    # Language and style
    language = Column(String(10), default="en")
    emoji_policy = Column(String(50))  # "none", "minimal", "moderate", "heavy"
    hashtag_policy = Column(String(50))  # "none", "end_only", "inline", "both"

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    content_plans = relationship("ContentPlan", back_populates="creator_profile", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_creator_profiles_workspace_id', 'workspace_id'),
        Index('idx_creator_profiles_is_active', 'is_active'),
    )


class ContentPlan(Base):
    """Content Plan - Weekly plan with slots tagged by Awareness × FATE (ENTITY-005)"""
    __tablename__ = "content_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    creator_profile_id = Column(UUID(as_uuid=True), ForeignKey("creator_profiles.id", ondelete="CASCADE"))

    # Plan details
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Time range
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)

    # Plan strategy
    target_posts_per_day = Column(Integer, default=3)
    awareness_distribution = Column(JSONB)  # {"unaware": 0.1, "problem_aware": 0.4, "solution_aware": 0.3, "product_aware": 0.15, "most_aware": 0.05}
    fate_emphasis = Column(JSONB)  # {"focus": 0.3, "authority": 0.25, "tribe": 0.25, "emotion": 0.2}

    # Status
    status = Column(String(50), default="draft")  # draft, active, executing, completed, archived
    execution_progress = Column(Float, default=0.0)  # 0.0 to 1.0

    # Learnings from execution
    learnings = Column(JSONB)  # {"winning_templates": [], "losing_templates": [], "best_time": ""}
    avg_performance_score = Column(Float)

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator_profile = relationship("CreatorProfile", back_populates="content_plans")
    slots = relationship("ContentSlot", back_populates="content_plan", cascade="all, delete-orphan")
    prompt_runs = relationship("PromptRun", back_populates="content_plan", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_content_plans_workspace_id', 'workspace_id'),
        Index('idx_content_plans_creator_profile_id', 'creator_profile_id'),
        Index('idx_content_plans_week_start_date', 'week_start_date'),
        Index('idx_content_plans_status', 'status'),
    )


class ContentSlot(Base):
    """Content Slot - Individual time slot in a content plan"""
    __tablename__ = "content_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_plan_id = Column(UUID(as_uuid=True), ForeignKey("content_plans.id", ondelete="CASCADE"), nullable=False)

    # Slot details
    scheduled_time = Column(TIMESTAMP(timezone=True), nullable=False)

    # Awareness × FATE targeting
    awareness_level = Column(String(50))  # unaware, problem_aware, solution_aware, product_aware, most_aware
    fate_primary = Column(String(50))  # focus, authority, tribe, emotion

    # Routing
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="SET NULL"))
    icp_id = Column(UUID(as_uuid=True), ForeignKey("icps.id", ondelete="SET NULL"))
    template_id = Column(UUID(as_uuid=True), ForeignKey("content_templates.id", ondelete="SET NULL"))

    # Platform targeting
    platforms = Column(ARRAY(String))  # ["twitter", "instagram", "tiktok"]
    content_format = Column(String(50))  # "post", "thread", "video", "carousel"

    # Execution status
    status = Column(String(50), default="pending")  # pending, generating, qa_review, approved, published, failed
    executed_at = Column(TIMESTAMP(timezone=True))
    touchpoint_id = Column(UUID(as_uuid=True), ForeignKey("touchpoints.id", ondelete="SET NULL"))

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    content_plan = relationship("ContentPlan", back_populates="slots")
    offer = relationship("Offer")
    icp = relationship("ICP")
    template = relationship("ContentTemplate")
    prompt_runs = relationship("PromptRun", back_populates="content_slot")
    touchpoint = relationship("Touchpoint")

    # Indexes
    __table_args__ = (
        Index('idx_content_slots_content_plan_id', 'content_plan_id'),
        Index('idx_content_slots_scheduled_time', 'scheduled_time'),
        Index('idx_content_slots_status', 'status'),
        Index('idx_content_slots_awareness_level', 'awareness_level'),
    )


class PromptRun(Base):
    """Prompt Run - Traceback of every post to template → prompt → offer → ICP → slot (ENTITY-006)"""
    __tablename__ = "prompt_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Full traceback chain
    content_plan_id = Column(UUID(as_uuid=True), ForeignKey("content_plans.id", ondelete="CASCADE"))
    content_slot_id = Column(UUID(as_uuid=True), ForeignKey("content_slots.id", ondelete="SET NULL"))
    template_id = Column(UUID(as_uuid=True), ForeignKey("content_templates.id", ondelete="CASCADE"), nullable=False)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False)
    icp_id = Column(UUID(as_uuid=True), ForeignKey("icps.id", ondelete="CASCADE"))
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"))

    # Template snapshot (in case template changes)
    template_snapshot = Column(JSONB)  # Full template at time of generation

    # Input variables
    input_variables = Column(JSONB, nullable=False)  # {"pain": "...", "outcome": "...", "mechanism": "..."}

    # Prompt details
    prompt_text = Column(Text, nullable=False)  # Final rendered prompt sent to AI
    system_prompt = Column(Text)  # System instructions

    # AI model details
    model_name = Column(String(100))  # "gpt-4o", "claude-3-opus", etc.
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer)

    # Generated output
    generated_text = Column(Text, nullable=False)
    generated_variants = Column(JSONB)  # Multiple variants if requested
    selected_variant_index = Column(Integer, default=0)

    # QA Gate results
    qa_status = Column(String(50))  # "pending", "passed", "failed", "needs_review"
    qa_flags = Column(JSONB)  # {"banned_phrase": false, "spam_pattern": false, ...}
    qa_reviewed_by = Column(String(100))  # User who reviewed
    qa_reviewed_at = Column(TIMESTAMP(timezone=True))

    # Publication details
    published_touchpoint_id = Column(UUID(as_uuid=True), ForeignKey("touchpoints.id", ondelete="SET NULL"))
    published_at = Column(TIMESTAMP(timezone=True))

    # Performance (copied from touchpoint after metrics collection)
    engagement_rate = Column(Float)
    click_rate = Column(Float)
    reward_score = Column(Float)
    performance_label = Column(String(50))  # "winner", "loser", "neutral", "insufficient_data"

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    content_plan = relationship("ContentPlan", back_populates="prompt_runs")
    content_slot = relationship("ContentSlot", foreign_keys=[content_slot_id], back_populates="prompt_runs")
    template = relationship("ContentTemplate")
    offer = relationship("Offer")
    icp = relationship("ICP")
    brand = relationship("Brand")
    touchpoint = relationship("Touchpoint")

    # Indexes
    __table_args__ = (
        Index('idx_prompt_runs_content_plan_id', 'content_plan_id'),
        Index('idx_prompt_runs_template_id', 'template_id'),
        Index('idx_prompt_runs_offer_id', 'offer_id'),
        Index('idx_prompt_runs_published_at', 'published_at'),
        Index('idx_prompt_runs_performance_label', 'performance_label'),
        Index('idx_prompt_runs_qa_status', 'qa_status'),
    )


# =====================================================
# VOICE CLONING (VC-001 to VC-012)
# =====================================================

class VoiceProfile(Base):
    """Voice profile for voice cloning and TTS generation (VC-002)"""
    __tablename__ = "voice_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Profile metadata
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Reference audio URLs (JSON array of S3/storage URLs)
    reference_urls = Column(JSONB, default=[])

    # Voice embedding (from Modal/external service)
    embedding_id = Column(String(255))  # External service's voice ID
    embedding_created_at = Column(TIMESTAMP(timezone=True))

    # Quality metrics
    quality_score = Column(Float)  # 0.0 to 1.0
    quality_notes = Column(Text)

    # Default settings
    default_speed = Column(Float, default=1.0)  # 0.5 to 2.0
    default_emotion = Column(String(20), default='neutral')
    default_stability = Column(Float, default=0.5)  # 0.0 to 1.0

    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    generations = relationship("VoiceGeneration", back_populates="voice_profile")

    # Indexes
    __table_args__ = (
        Index('idx_voice_profiles_user', 'user_id'),
        Index('idx_voice_profiles_default', 'user_id', postgresql_where=Column('is_default') == True),
        Index('idx_voice_profiles_active', 'user_id', postgresql_where=Column('is_active') == True),
    )


class VoiceGeneration(Base):
    """Voice generation jobs and history (VC-006)"""
    __tablename__ = "voice_generations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    voice_profile_id = Column(UUID(as_uuid=True), ForeignKey("voice_profiles.id", ondelete="SET NULL"))

    # Input
    input_text = Column(Text, nullable=False)
    options = Column(JSONB, default={})  # speed, pitch, emotion, stability

    # Output
    output_url = Column(Text)
    duration_seconds = Column(Float)
    file_size_bytes = Column(BigInteger)

    # Processing status
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    modal_job_id = Column(String(255))  # External service job ID
    processing_time_ms = Column(Integer)
    error_message = Column(Text)

    # Cost tracking
    cost_credits = Column(Float, default=0.0)

    # Usage tracking (where was this audio used?)
    used_in_clip_id = Column(UUID(as_uuid=True))
    used_in_post_id = Column(UUID(as_uuid=True))
    used_in_creative_brief_id = Column(UUID(as_uuid=True))

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    voice_profile = relationship("VoiceProfile", back_populates="generations")

    # Indexes
    __table_args__ = (
        Index('idx_voice_generations_user', 'user_id', 'created_at'),
        Index('idx_voice_generations_profile', 'voice_profile_id', 'created_at'),
        Index('idx_voice_generations_status', 'status', 'created_at'),
        Index('idx_voice_generations_clip', 'used_in_clip_id'),
        Index('idx_voice_generations_post', 'used_in_post_id'),
    )


# =====================================================
# MUSIC LIBRARY (MUSIC-001: Music Library with Metadata)
# =====================================================

class MusicTrack(Base):
    """
    Music track with metadata for background music selection.
    Supports Suno, SoundCloud, and social platform music sources.

    Features:
    - Rich metadata (tempo, mood, energy, genre)
    - Platform trending data
    - Auto-matching attributes
    - Licensing information
    - Usage tracking
    """
    __tablename__ = "music_tracks"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)

    # Track identification
    title = Column(String(500), nullable=False)
    artist = Column(String(500))
    source = Column(String(50), nullable=False)  # 'suno', 'soundcloud', 'social_platform', 'local'
    source_id = Column(Text)  # External ID from source platform
    source_url = Column(Text)  # URL to original track

    # File information
    file_path = Column(Text, nullable=False)  # Local path to audio file
    file_size_bytes = Column(BigInteger)
    file_format = Column(String(20))  # 'mp3', 'wav', 'ogg', etc.
    checksum = Column(String(64))  # SHA-256 for deduplication

    # Audio properties
    duration_seconds = Column(Float, nullable=False)
    sample_rate = Column(Integer)  # Hz
    bitrate = Column(Integer)  # kbps
    channels = Column(Integer, default=2)  # 1=mono, 2=stereo

    # Musical metadata
    tempo_bpm = Column(Float)  # Beats per minute
    key = Column(String(10))  # 'C', 'Am', 'F#m', etc.
    time_signature = Column(String(10))  # '4/4', '3/4', etc.
    genre = Column(String(100))
    subgenre = Column(String(100))

    # Mood & Energy (for auto-matching)
    mood = Column(String(100))  # 'energetic', 'calm', 'upbeat', 'melancholic', etc.
    energy_level = Column(Float)  # 0.0-1.0 scale
    valence = Column(Float)  # 0.0-1.0 (negative to positive emotional tone)
    danceability = Column(Float)  # 0.0-1.0
    instrumentalness = Column(Float)  # 0.0-1.0 (0=vocals, 1=instrumental)

    # Tagging & categorization
    tags = Column(ARRAY(String))  # ['viral', 'trending', 'uplifting', 'cinematic']
    moods = Column(ARRAY(String))  # Multiple moods
    use_cases = Column(ARRAY(String))  # ['intro', 'background', 'outro', 'transition']

    # Content matching attributes
    suitable_for_content_types = Column(ARRAY(String))  # ['educational', 'comedy', 'motivational']
    recommended_video_pacing = Column(String(50))  # 'slow', 'medium', 'fast', 'dynamic'

    # Licensing & usage
    license_type = Column(String(100))  # 'public_domain', 'royalty_free', 'licensed', 'copyright'
    attribution_required = Column(Boolean, default=False)
    commercial_use_allowed = Column(Boolean, default=True)
    license_url = Column(Text)

    # Platform-specific metadata
    platform = Column(String(50))  # 'tiktok', 'instagram', 'youtube', etc. (if trending on platform)
    platform_popularity = Column(Integer)  # View count, usage count, etc.
    is_trending = Column(Boolean, default=False)
    trending_rank = Column(Integer)  # Rank in trending charts
    trending_date = Column(Date)

    # Audio analysis (advanced)
    audio_features = Column(JSONB)  # Detailed audio analysis from librosa/essentia
    waveform_peaks = Column(JSONB)  # Peak timestamps for sync
    beat_timestamps = Column(JSONB)  # Beat detection for video sync

    # Usage tracking
    times_used = Column(Integer, default=0)
    last_used_at = Column(TIMESTAMP(timezone=True))
    avg_match_score = Column(Float)  # Average compatibility score when matched

    # Quality & status
    quality_rating = Column(Float)  # 1.0-5.0 user/system rating
    is_active = Column(Boolean, default=True)
    is_curated = Column(Boolean, default=False)  # Hand-picked by team
    curation_notes = Column(Text)

    # Import metadata
    imported_from = Column(String(100))  # 'suno_crawler', 'manual_upload', 'api_import'
    import_batch_id = Column(UUID(as_uuid=True))
    imported_at = Column(TIMESTAMP(timezone=True))

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes for fast querying
    __table_args__ = (
        Index('idx_music_tracks_source', 'source'),
        Index('idx_music_tracks_genre', 'genre'),
        Index('idx_music_tracks_mood', 'mood'),
        Index('idx_music_tracks_tempo', 'tempo_bpm'),
        Index('idx_music_tracks_energy', 'energy_level'),
        Index('idx_music_tracks_is_trending', 'is_trending'),
        Index('idx_music_tracks_workspace_id', 'workspace_id'),
        Index('idx_music_tracks_checksum', 'checksum'),  # Deduplication
    )


# =====================================================
# AI CHARACTER GENERATION (CHAR-001 to CHAR-004)
# =====================================================

class CharacterAsset(Base):
    """
    AI-generated character assets (CHAR-001)

    Stores base character images generated via DALL-E or other image models.
    Characters can have multiple expression variants.
    """
    __tablename__ = "character_assets"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)

    # Character identity
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)  # Character appearance, traits
    style = Column(String(50), nullable=False)  # 'cartoon', 'realistic', 'mascot', etc.
    base_expression = Column(String(50), default='neutral')  # Default expression

    # File information
    file_path = Column(Text, nullable=False)  # Local storage path
    file_size_bytes = Column(BigInteger)
    checksum = Column(String(64))  # SHA-256 for deduplication
    image_url = Column(Text)  # Original generation URL (temporary)

    # Generation metadata
    original_prompt = Column(Text)  # User's prompt
    revised_prompt = Column(Text)  # DALL-E's revised prompt
    generation_params = Column(JSONB)  # Model, size, quality, etc.

    # Character properties (CHAR-003: JSON index)
    has_transparent_background = Column(Boolean, default=False)  # CHAR-002
    has_body_layer = Column(Boolean, default=False)  # CHAR-004
    has_mouth_layer = Column(Boolean, default=False)  # CHAR-004
    body_layer_path = Column(Text)  # Separate body layer for lip-sync
    mouth_layer_path = Column(Text)  # Separate mouth layer for lip-sync

    # Additional metadata
    character_metadata = Column('metadata', JSONB, default={})  # Flexible JSON storage

    # Usage tracking
    times_used = Column(Integer, default=0)
    last_used_at = Column(TIMESTAMP(timezone=True))

    # Status
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    variants = relationship("CharacterVariant", back_populates="character", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_character_assets_workspace_id', 'workspace_id'),
        Index('idx_character_assets_style', 'style'),
        Index('idx_character_assets_checksum', 'checksum'),
    )


class CharacterVariant(Base):
    """
    Character expression variants (CHAR-001)

    Different expressions/poses of the same character (happy, sad, surprised, etc.)
    Maintains consistency with base character while changing expression.
    """
    __tablename__ = "character_variants"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(UUID(as_uuid=True), ForeignKey("character_assets.id", ondelete="CASCADE"), nullable=False)

    # Variant details
    expression = Column(String(50), nullable=False)  # 'happy', 'sad', 'surprised', etc.

    # File information
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger)
    image_url = Column(Text)  # Original generation URL (temporary)

    # Generation metadata
    prompt = Column(Text)
    revised_prompt = Column(Text)
    generation_params = Column(JSONB)

    # Variant properties (CHAR-004: Separate layers)
    has_transparent_background = Column(Boolean, default=False)
    has_body_layer = Column(Boolean, default=False)
    has_mouth_layer = Column(Boolean, default=False)
    body_layer_path = Column(Text)
    mouth_layer_path = Column(Text)

    # Usage tracking
    times_used = Column(Integer, default=0)
    last_used_at = Column(TIMESTAMP(timezone=True))

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    character = relationship("CharacterAsset", back_populates="variants")

    # Indexes
    __table_args__ = (
        Index('idx_character_variants_character_id', 'character_id'),
        Index('idx_character_variants_expression', 'expression'),
    )
