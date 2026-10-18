"""
Database models for Phase 2: Video Analysis & Categorization System
Supports 8-lens analytical framework with word-level timestamps and frame analysis
"""
from sqlalchemy import Column, String, DateTime, Integer, Float, JSON, ForeignKey, Text, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database.base import Base


class Video(Base):
    """Core video entity for analysis"""
    __tablename__ = "videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    
    # Processing status
    status = Column(String, default='uploaded', nullable=False)  # uploaded, processing, analyzed, published, failed
    
    # Metadata
    original_filename = Column(String)
    file_size_bytes = Column(Integer)
    resolution = Column(String)  # e.g., "1920x1080"
    fps = Column(Float)
    codec = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    analyzed_at = Column(DateTime, nullable=True)
    
    # Relationships
    segments = relationship("VideoSegment", back_populates="video", cascade="all, delete-orphan")
    words = relationship("VideoWord", back_populates="video", cascade="all, delete-orphan")
    frames = relationship("VideoFrame", back_populates="video", cascade="all, delete-orphan")
    tags = relationship("VideoTag", back_populates="video", cascade="all, delete-orphan", uselist=False)
    performance = relationship("VideoPerformanceCheckback", back_populates="video", cascade="all, delete-orphan")


class VideoSegment(Base):
    """Timeline segments with multi-lens tagging"""
    __tablename__ = "video_segments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey('videos.id'), nullable=False, index=True)
    
    # Timeline structure
    segment_type = Column(String, nullable=False)  # hook, context, payload, payoff, cta
    start_s = Column(Float, nullable=False)
    end_s = Column(Float, nullable=False)
    
    # Lens 1: Timeline/Structure
    hook_type = Column(String, nullable=True)  # pain, contrarian, aspirational, gap, absurd
    pattern_interrupt = Column(String, nullable=True)  # question, statement, story, promise
    
    # Lens 2: Psychology (FATE)
    focus_tags = Column(ARRAY(String), default=[])  # specific problem, narrow audience
    authority_tags = Column(ARRAY(String), default=[])  # credentials, proof, demo
    tribe_tags = Column(ARRAY(String), default=[])  # identity, shared enemy, in-jokes
    emotion_tags = Column(ARRAY(String), default=[])  # relief, excitement, curiosity, fomo
    
    # Lens 5: Copy Layer
    cta_type = Column(String, nullable=True)  # conversion, engagement, open_loop, conversation
    cta_mechanic = Column(String, nullable=True)  # comment_keyword, link, dm, save_share
    cta_keyword = Column(String, nullable=True)  # The actual keyword (e.g., "Tech", "PROMPT")
    
    # Derived metrics
    word_count = Column(Integer, default=0)
    avg_wpm = Column(Float, nullable=True)  # Words per minute
    sentiment_avg = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="segments")
    words = relationship("VideoWord", back_populates="segment")
    frames = relationship("VideoFrame", back_populates="segment")


class VideoWord(Base):
    """Word-level transcript with timestamps"""
    __tablename__ = "video_words"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey('videos.id'), nullable=False, index=True)
    segment_id = Column(UUID(as_uuid=True), ForeignKey('video_segments.id'), nullable=True, index=True)
    
    # Word timing
    word = Column(String, nullable=False)
    start_s = Column(Float, nullable=False)
    end_s = Column(Float, nullable=False)
    
    # Structure
    word_index = Column(Integer, nullable=False)  # Position in full transcript
    sentence_id = Column(Integer, nullable=True)  # Sentence grouping
    speaker = Column(String, default='main')  # For multi-speaker if needed
    
    # Linguistic features
    pos = Column(String, nullable=True)  # Part of speech (optional NLP)
    is_emphasis = Column(Boolean, default=False)  # Caps, pitch change, etc.
    is_question = Column(Boolean, default=False)
    is_list_marker = Column(Boolean, default=False)  # "first", "second", etc.
    
    # Semantic tagging
    speech_function = Column(String, nullable=True)  # hook, proof, step, metaphor, cta
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    emotion = Column(String, nullable=True)  # curiosity, frustration, hope
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="words")
    segment = relationship("VideoSegment", back_populates="words")


class VideoFrame(Base):
    """Sampled frames with visual analysis"""
    __tablename__ = "video_frames"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey('videos.id'), nullable=False, index=True)
    segment_id = Column(UUID(as_uuid=True), ForeignKey('video_segments.id'), nullable=True, index=True)
    
    # Frame timing
    frame_time_s = Column(Float, nullable=False, index=True)
    frame_number = Column(Integer, nullable=False)
    frame_path = Column(String, nullable=False)  # Saved frame image path
    
    # Lens 3: Visual Layer
    shot_type = Column(String, nullable=True)  # close_up, medium, wide, screen_record
    camera_motion = Column(String, nullable=True)  # static, slight, aggressive
    presence = Column(String, nullable=True)  # face, full_body, hands, no_human
    objects = Column(ARRAY(String), default=[])  # Detected objects
    text_on_screen = Column(Text, nullable=True)  # OCR results
    
    # Pattern interrupts
    is_pattern_interrupt = Column(Boolean, default=False)
    is_hook_frame = Column(Boolean, default=False)
    has_meme_element = Column(Boolean, default=False)
    
    # Visual metrics
    brightness_level = Column(String, nullable=True)  # dark, normal, bright
    color_temperature = Column(String, nullable=True)  # warm, neutral, cool
    visual_clutter_score = Column(Float, nullable=True)  # 0-1
    
    # Face & expression (if detected)
    face_detected = Column(Boolean, default=False)
    face_expression = Column(String, nullable=True)  # neutral, smiling, surprised
    eye_contact = Column(Boolean, default=False)
    
    # Raw analysis data
    vision_analysis = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="frames")
    segment = relationship("VideoSegment", back_populates="frames")


class VideoTag(Base):
    """Comprehensive tags across all lenses"""
    __tablename__ = "video_tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey('videos.id'), nullable=False, unique=True, index=True)
    
    # Lens 4: Audio & Voice
    voice_tone = Column(String, nullable=True)  # teacher, coach, rant, confessional, storyteller
    pacing = Column(String, nullable=True)  # punchy, medium, slow
    language_style = Column(String, nullable=True)  # plain, gen_z, technical
    music_energy = Column(String, nullable=True)  # none, chill, high
    beat_synced = Column(Boolean, default=False)
    
    # Lens 7: Offer & Monetization
    offer_layer = Column(String, nullable=True)  # none, seed, soft_pitch, hard_pitch
    offer_type = Column(String, nullable=True)  # course, saas, service, download
    proof_mode = Column(String, nullable=True)  # story, dashboard, testimonial, screen_record
    
    # Lens 8: Isaiah-Specific
    angle = Column(String, nullable=True)  # engineer_brain, automation_diary, content_nerd
    demo_depth = Column(String, nullable=True)  # glimpse, walkthrough, build
    
    # Lens 6: Algorithm Intent
    intended_metric = Column(String, nullable=True)  # saves, shares, comments, clicks, profile_taps
    funnels_into = Column(String, nullable=True)  # newsletter, course, app, community
    
    # Custom tags
    custom_tags = Column(ARRAY(String), default=[])
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="tags")


class VideoPerformanceCheckback(Base):
    """Performance metrics at scheduled intervals"""
    __tablename__ = "video_performance_checkbacks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey('videos.id'), nullable=False, index=True)
    
    # Platform info
    platform = Column(String, nullable=False)  # tiktok, instagram, youtube, twitter
    platform_post_id = Column(String, nullable=False, index=True)
    checkback_hours = Column(Integer, nullable=False)  # 1, 6, 24, 72, 168
    
    # View metrics
    views = Column(Integer, default=0)
    unique_viewers = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    
    # Watch behavior
    avg_watch_time_s = Column(Float, nullable=True)
    avg_watch_pct = Column(Float, nullable=True)
    completion_rate = Column(Float, nullable=True)
    
    # Engagement
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    profile_taps = Column(Integer, default=0)
    link_clicks = Column(Integer, default=0)
    
    # Derived rates
    like_rate = Column(Float, nullable=True)  # likes / views
    comment_rate = Column(Float, nullable=True)
    share_rate = Column(Float, nullable=True)
    save_rate = Column(Float, nullable=True)
    ctr = Column(Float, nullable=True)  # clicks / impressions
    
    # Retention curve (array of {t_pct: float, retention: float})
    retention_curve = Column(JSON, nullable=True)
    
    # Comment analysis summary
    comment_sentiment_avg = Column(Float, nullable=True)
    comment_themes = Column(ARRAY(String), default=[])
    keyword_response_count = Column(Integer, default=0)
    
    # Timestamps
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    video = relationship("Video", back_populates="performance")
    comments = relationship("VideoCommentAnalysis", back_populates="checkback", cascade="all, delete-orphan")


class VideoCommentAnalysis(Base):
    """Individual comment sentiment & theme analysis"""
    __tablename__ = "video_comments_analysis"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checkback_id = Column(UUID(as_uuid=True), ForeignKey('video_performance_checkbacks.id'), nullable=False, index=True)
    
    # Comment info
    comment_id = Column(String, nullable=False, unique=True, index=True)
    comment_text = Column(Text, nullable=False)
    author = Column(String, nullable=True)
    
    # Sentiment
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    emotion_tags = Column(ARRAY(String), default=[])
    
    # Classification
    intent = Column(String, nullable=True)  # question, praise, critique, spam
    theme_tags = Column(ARRAY(String), default=[])
    
    # CTA response
    is_keyword_response = Column(Boolean, default=False)
    keyword = Column(String, nullable=True)
    
    # Timestamps
    comment_created_at = Column(DateTime, nullable=True)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    checkback = relationship("VideoPerformanceCheckback", back_populates="comments")


# Migration helper
def create_analysis_tables(engine):
    """Create all video analysis tables"""
    Base.metadata.create_all(bind=engine, tables=[
        Video.__table__,
        VideoSegment.__table__,
        VideoWord.__table__,
        VideoFrame.__table__,
        VideoTag.__table__,
        VideoPerformanceCheckback.__table__,
        VideoCommentAnalysis.__table__
    ])


def drop_analysis_tables(engine):
    """Drop all video analysis tables"""
    Base.metadata.drop_all(bind=engine, tables=[
        VideoCommentAnalysis.__table__,
        VideoPerformanceCheckback.__table__,
        VideoTag.__table__,
        VideoFrame.__table__,
        VideoWord.__table__,
        VideoSegment.__table__,
        Video.__table__
    ])
