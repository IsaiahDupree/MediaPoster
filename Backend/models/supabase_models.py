"""
Supabase Data Models for MediaPoster PRD2
Mirrors the schema defined in prd2.txt
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# Enums
# ============================================

class SourceType(str, Enum):
    LOCAL_UPLOAD = "local_upload"
    KALODATA_CLIP = "kalodata_clip"
    REPURPOSED = "repurposed"
    PROMPT_ONLY = "prompt_only"
    OWN_TOP_POST = "own_top_post"


class MediaType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"


class MediaStatus(str, Enum):
    INGESTED = "ingested"
    ANALYZED = "analyzed"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    ARCHIVED = "archived"


class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM_REELS = "instagram_reels"
    YOUTUBE_SHORTS = "yt_shorts"
    MULTI = "multi"


class ScheduleStatus(str, Enum):
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"
    CANCELED = "canceled"


class SentimentLabel(str, Enum):
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


class DerivativeFormat(str, Enum):
    BROLL_TEXT = "broll_text"
    FACE_CAM = "face_cam"
    FACES_VIDEO = "faces_video"
    EXPLAINER = "explainer"
    CAROUSEL = "carousel"


class PlanStatus(str, Enum):
    PLANNED = "planned"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"


# ============================================
# Core Models
# ============================================

class MediaAsset(BaseModel):
    """
    Central registry of media files
    Table: media_assets
    """
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    source_type: SourceType
    storage_path: str
    media_type: MediaType
    duration_sec: Optional[float] = None
    resolution: Optional[str] = None  # e.g., "1080x1920"
    status: MediaStatus = MediaStatus.INGESTED
    platform_hint: Platform = Platform.MULTI
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class MediaAnalysis(BaseModel):
    """
    AI insights and scoring
    Table: media_analysis
    """
    id: UUID = Field(default_factory=uuid4)
    media_id: UUID
    transcript: Optional[str] = None
    transcript_language: str = "en"
    topics: List[str] = Field(default_factory=list)  # stored as jsonb
    sentiment_overall: Optional[float] = None
    frames_sampled: int = 0
    best_frame_index: Optional[int] = None
    best_frame_url: Optional[str] = None
    
    # JSONB fields
    virality_features: Dict[str, Any] = Field(default_factory=dict)
    ai_caption_suggestions: List[str] = Field(default_factory=list)
    ai_hashtag_suggestions: List[str] = Field(default_factory=list)
    
    pre_social_score: Optional[float] = Field(None, ge=0, le=100)
    pre_social_explanation: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class PostingSchedule(BaseModel):
    """
    Planning table for future posts
    Table: posting_schedule
    """
    id: UUID = Field(default_factory=uuid4)
    media_id: UUID
    platform: Platform
    scheduled_at: datetime
    status: ScheduleStatus = ScheduleStatus.PENDING
    external_post_id: Optional[str] = None
    external_post_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class PostingMetrics(BaseModel):
    """
    Performance tracking at checkpoints
    Table: posting_metrics
    """
    id: UUID = Field(default_factory=uuid4)
    schedule_id: UUID
    check_time: datetime = Field(default_factory=datetime.utcnow)
    
    # Metrics
    views: int = 0
    likes: int = 0
    comments_count: int = 0
    shares: int = 0
    watch_time_sec: Optional[float] = None
    ctr: Optional[float] = None
    profile_visits: Optional[int] = None
    follower_delta: Optional[int] = None
    
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    post_social_score: Optional[float] = Field(None, ge=0, le=100)

    model_config = ConfigDict(from_attributes=True)


class Comment(BaseModel):
    """
    User comments tracking
    Table: comments
    """
    id: UUID = Field(default_factory=uuid4)
    schedule_id: UUID
    platform_comment_id: str
    author_handle: str
    text: str
    like_count: int = 0
    sentiment_score: Optional[float] = None
    sentiment_label: SentimentLabel = SentimentLabel.NEUTRAL
    topic_tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class AICoachInsight(BaseModel):
    """
    Strategic advice from AI Coach
    Table: ai_coach_insights
    """
    id: UUID = Field(default_factory=uuid4)
    media_id: UUID
    schedule_id: Optional[UUID] = None
    checkpoint: str  # e.g., "24h", "7d"
    input_snapshot: Dict[str, Any] = Field(default_factory=dict)
    
    summary: str
    what_worked: List[str] = Field(default_factory=list)
    what_to_change: List[str] = Field(default_factory=list)
    next_actions: List[Dict[str, Any]] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class CreativeBriefV2(BaseModel):
    """
    Brief for creating new content
    Table: creative_briefs
    """
    id: UUID = Field(default_factory=uuid4)
    source_type: SourceType
    source_reference: Dict[str, Any] = Field(default_factory=dict)
    
    angle_name: str
    target_audience: str
    core_promise: str
    hook_ideas: List[str] = Field(default_factory=list)
    
    # Structured fields
    script_outline: Dict[str, List[str]] = Field(default_factory=dict)
    visual_directions: Dict[str, List[str]] = Field(default_factory=dict)
    posting_guidance: Dict[str, Any] = Field(default_factory=dict)
    
    ready_for_use: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class DerivativeMediaPlan(BaseModel):
    """
    Plan for remixing content
    Table: derivative_media_plans
    """
    id: UUID = Field(default_factory=uuid4)
    brief_id: Optional[UUID] = None
    source_media_id: Optional[UUID] = None
    format_type: DerivativeFormat
    instructions: str
    target_platform: Platform
    estimated_length_sec: int
    status: PlanStatus = PlanStatus.PLANNED
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)
