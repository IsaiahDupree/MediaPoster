"""
ACTP Data Models
================
Pydantic models for the Ad Creative Testing Pipeline.
Maps to Supabase tables.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────

class CampaignStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    ORGANIC_TESTING = "organic_testing"
    AD_TESTING = "ad_testing"
    ITERATING = "iterating"
    SCALING = "scaling"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class RoundType(str, Enum):
    ORGANIC = "organic"
    AD = "ad"
    SCALE = "scale"


class RoundStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    PUBLISHING = "publishing"
    WAITING = "waiting"
    COLLECTING = "collecting"
    SELECTING = "selecting"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationSource(str, Enum):
    SORA = "sora"
    VEO3 = "veo3"
    NANO_BANANA = "nano_banana"
    REMOTION = "remotion"
    REMIX = "remix"


class Platform(str, Enum):
    YOUTUBE_SHORTS = "youtube_shorts"
    TIKTOK = "tiktok"
    INSTAGRAM_REELS = "instagram_reels"
    META_ADS = "meta"
    TIKTOK_ADS = "tiktok_ads"
    YOUTUBE_ADS = "youtube_ads"


class AdDeploymentStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Core Models ──────────────────────────────────────────

class TestCampaign(BaseModel):
    """A test campaign managing the full creative testing lifecycle."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    offer_id: Optional[str] = None
    offer_name: Optional[str] = None
    offer_url: Optional[str] = None
    status: CampaignStatus = CampaignStatus.DRAFT
    config: Dict[str, Any] = Field(default_factory=dict)
    angles: List[str] = Field(default_factory=list)
    target_audience: Optional[Dict[str, Any]] = None
    mode: str = "offer"  # "offer" or "growth"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_spend_cents: int = 0
    total_creatives: int = 0
    total_rounds: int = 0


class TestRound(BaseModel):
    """A single testing round within a campaign."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    round_number: int
    round_type: RoundType
    status: RoundStatus = RoundStatus.PENDING
    budget_per_creative_cents: int = 0
    total_budget_cents: int = 0
    total_spend_cents: int = 0
    config: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    wait_until: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Creative(BaseModel):
    """A video creative generated for testing."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    round_id: str
    parent_creative_id: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    hook: Optional[str] = None
    cta: Optional[str] = None
    angle: Optional[str] = None
    script: Optional[str] = None
    target_audience: Optional[str] = None
    generation_source: GenerationSource = GenerationSource.SORA
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)
    organic_score: Optional[float] = None
    ad_score: Optional[float] = None
    is_winner: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrganicPost(BaseModel):
    """An organic post of a creative on a social platform."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    creative_id: str
    platform: Platform
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    organic_score: Optional[float] = None
    status: str = "pending"  # pending, published, failed
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AdDeployment(BaseModel):
    """An ad deployment of a winning creative."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    creative_id: str
    round_id: str
    platform: Platform
    external_campaign_id: Optional[str] = None
    external_ad_set_id: Optional[str] = None
    external_ad_id: Optional[str] = None
    budget_cents: int = 0
    spend_cents: int = 0
    metrics: Dict[str, Any] = Field(default_factory=dict)
    ad_score: Optional[float] = None
    status: AdDeploymentStatus = AdDeploymentStatus.PENDING
    landing_page_url: Optional[str] = None
    audience_config: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PerformanceLog(BaseModel):
    """Time-series performance metric entry."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    creative_id: str
    round_id: str
    metric_type: str  # views, likes, comments, ctr, cpc, etc.
    value: float
    platform: Platform
    measured_at: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Optional[Dict[str, Any]] = None


class WinnerSelection(BaseModel):
    """Record of a winner selection decision."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    round_id: str
    creative_id: str
    rank: int
    score: float
    selection_reason: str
    promoted_to_round_id: Optional[str] = None
    selected_at: datetime = Field(default_factory=datetime.utcnow)


# ─── API Request/Response Models ─────────────────────────

class CreateCampaignRequest(BaseModel):
    """Request to create a new test campaign."""
    name: str
    offer_id: Optional[str] = None
    offer_name: Optional[str] = None
    offer_url: Optional[str] = None
    angles: List[str] = Field(default_factory=list)
    target_audience: Optional[Dict[str, Any]] = None
    mode: str = "offer"
    config: Optional[Dict[str, Any]] = None


class CampaignSummary(BaseModel):
    """Summary view of a campaign for list endpoints."""
    id: str
    name: str
    status: CampaignStatus
    mode: str
    total_rounds: int
    total_creatives: int
    total_spend_cents: int
    current_round: Optional[int] = None
    best_organic_score: Optional[float] = None
    best_ad_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class RoundDetail(BaseModel):
    """Detailed view of a round with creatives."""
    round: TestRound
    creatives: List[Creative] = Field(default_factory=list)
    winners: List[WinnerSelection] = Field(default_factory=list)
    organic_posts: List[OrganicPost] = Field(default_factory=list)
    ad_deployments: List[AdDeployment] = Field(default_factory=list)


class CampaignDetail(BaseModel):
    """Full campaign detail with rounds."""
    campaign: TestCampaign
    rounds: List[RoundDetail] = Field(default_factory=list)


class CreativeLineage(BaseModel):
    """Creative genealogy tree node."""
    creative: Creative
    children: List["CreativeLineage"] = Field(default_factory=list)
    depth: int = 0


class PipelineDashboard(BaseModel):
    """Overall pipeline analytics dashboard."""
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_rounds: int = 0
    total_creatives: int = 0
    total_spend_cents: int = 0
    total_winners: int = 0
    avg_rounds_to_winner: Optional[float] = None
    top_performing_angles: List[Dict[str, Any]] = Field(default_factory=list)
    recent_winners: List[Creative] = Field(default_factory=list)
