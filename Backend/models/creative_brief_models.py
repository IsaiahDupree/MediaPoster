"""
Creative Brief Models
Schemas for Kalodata-style product data + AI video analysis
Supports short-form (TikTok/Reels) and long-form content
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class VideoFormat(Enum):
    """Supported video formats"""
    SHORT_FORM = "short_form"      # TikTok, Reels, Shorts (15-60s)
    LONG_FORM = "long_form"        # YouTube, tutorials (2-15min)
    AD_CREATIVE = "ad_creative"    # Paid ads (15-45s)
    UGC = "ugc"                    # User-generated content style
    BRAND = "brand"                # Polished brand content


class AspectRatio(Enum):
    """Video aspect ratios"""
    VERTICAL = "9:16"
    HORIZONTAL = "16:9"
    SQUARE = "1:1"


class SceneRole(Enum):
    """Role of a scene in video structure"""
    HOOK = "hook"
    PROBLEM = "problem"
    DEMO = "demo"
    PROOF = "proof"
    AFTER = "after"
    CTA = "cta"
    TRANSITION = "transition"
    INTRO = "intro"
    OUTRO = "outro"
    OTHER = "other"


# ============================================
# Product Performance Snapshot (Kalodata-style)
# ============================================

@dataclass
class PriceRange:
    """Price range for a product"""
    min_price: float
    max_price: Optional[float] = None


@dataclass
class Metrics30Day:
    """30-day performance metrics"""
    revenue_usd: float
    revenue_growth_rate_pct: Optional[float] = None
    items_sold: int = 0
    avg_unit_price: float = 0.0


@dataclass
class AffiliateInfo:
    """Affiliate/creator program info"""
    is_affiliate_product: bool = False
    commission_rate_pct: Optional[float] = None
    creator_count: int = 0
    creator_conversion_ratio_pct: Optional[float] = None


@dataclass
class ProductPerformanceSnapshot:
    """Product performance data from Kalodata-style source"""
    product_id: str
    product_name: str
    category: Optional[str] = None
    price_range: Optional[PriceRange] = None
    launch_date: Optional[str] = None
    
    metrics_30d: Optional[Metrics30Day] = None
    affiliate: Optional[AffiliateInfo] = None
    
    highest_revenue_video_id: Optional[str] = None
    
    # Extensible metadata for different niches
    niche_data: Dict[str, Any] = field(default_factory=dict)


# ============================================
# Video/Scene Analysis (AI-generated)
# ============================================

@dataclass
class FrameTags:
    """Visual tags extracted from frame analysis"""
    setting: str = ""                    # "bathroom sink", "car interior"
    camera_type: str = ""                # "handheld phone", "tripod"
    shot_type: str = ""                  # "close-up", "medium", "POV"
    main_objects: List[str] = field(default_factory=list)
    color_palette: List[str] = field(default_factory=list)
    on_screen_text: Optional[str] = None


@dataclass
class SceneSemantics:
    """Semantic understanding of a scene"""
    mini_summary: str = ""
    emotion: str = ""                    # "frustration", "relief", "excitement"
    hook_type: Optional[str] = None      # if role == hook: "POV", "confession"
    cta_type: Optional[str] = None       # if role == cta: "tap basket", "swipe up"


@dataclass
class SceneAnalysis:
    """Analysis of a single scene/segment"""
    start_sec: float
    end_sec: float
    role: SceneRole
    
    frame_tags: FrameTags = field(default_factory=FrameTags)
    semantics: SceneSemantics = field(default_factory=SceneSemantics)
    
    # Extension: for long-form, scenes can have chapters
    chapter_title: Optional[str] = None
    chapter_number: Optional[int] = None


@dataclass
class TranscriptData:
    """Transcript and language data"""
    full_text: str = ""
    language: str = "en"
    summary: str = ""
    key_phrases: List[str] = field(default_factory=list)
    
    # For long-form: section timestamps
    sections: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class VideoPerformance:
    """Video performance metrics"""
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    click_through_rate_pct: Optional[float] = None
    conversion_rate_pct: Optional[float] = None
    revenue_contribution_usd: Optional[float] = None
    watch_time_avg_sec: Optional[float] = None
    retention_rate_pct: Optional[float] = None


@dataclass
class ExtractedAngles:
    """AI-extracted creative angles from video"""
    core_promise: str = ""               # "Glass-glow skin in 7 days"
    angle_types: List[str] = field(default_factory=list)  # ["transformation", "tutorial"]
    primary_pain_points: List[str] = field(default_factory=list)
    emotional_drivers: List[str] = field(default_factory=list)
    hook_lines: List[str] = field(default_factory=list)
    cta_style: str = ""
    
    # Long-form extensions
    key_takeaways: List[str] = field(default_factory=list)
    chapter_hooks: List[str] = field(default_factory=list)


@dataclass
class VideoAnalysisSnapshot:
    """Complete AI analysis of a video"""
    video_id: str
    video_url: str
    duration_sec: float
    aspect_ratio: str = "9:16"
    poster_frame_url: Optional[str] = None
    
    performance: VideoPerformance = field(default_factory=VideoPerformance)
    transcript: TranscriptData = field(default_factory=TranscriptData)
    scenes: List[SceneAnalysis] = field(default_factory=list)
    extracted_angles: ExtractedAngles = field(default_factory=ExtractedAngles)
    
    # Format classification
    video_format: VideoFormat = VideoFormat.SHORT_FORM
    
    # Niche-specific extensions
    niche_tags: Dict[str, Any] = field(default_factory=dict)


# ============================================
# Combined Insight Snapshot
# ============================================

@dataclass
class SnapshotMeta:
    """Metadata about the snapshot generation"""
    snapshot_date: str
    data_sources: List[str] = field(default_factory=list)
    overall_angle_label: str = ""
    recommended_use_cases: List[str] = field(default_factory=list)
    
    # Format recommendations
    recommended_formats: List[VideoFormat] = field(default_factory=list)
    recommended_durations: Dict[str, int] = field(default_factory=dict)


@dataclass
class AngleInsightSnapshot:
    """
    Complete snapshot combining:
    - Product performance (Kalodata-style)
    - Video analysis (AI-generated)
    - Metadata and recommendations
    """
    product: ProductPerformanceSnapshot
    video: VideoAnalysisSnapshot
    meta: SnapshotMeta
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        import dataclasses
        return dataclasses.asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AngleInsightSnapshot":
        """Create from dictionary"""
        # Simplified - would need proper deserialization
        return cls(
            product=ProductPerformanceSnapshot(**data.get("product", {})),
            video=VideoAnalysisSnapshot(**data.get("video", {})),
            meta=SnapshotMeta(**data.get("meta", {}))
        )


# ============================================
# Creative Brief Output Models
# ============================================

@dataclass
class BriefSection:
    """A section of the creative brief"""
    title: str
    content: str
    bullet_points: List[str] = field(default_factory=list)


@dataclass
class ShotDescription:
    """Description of a single shot for production"""
    shot_number: int
    start_sec: float
    end_sec: float
    
    camera_direction: str = ""
    action: str = ""
    voiceover: str = ""
    on_screen_text: str = ""
    music_cue: str = ""
    
    # Visual references
    reference_notes: str = ""


@dataclass
class CreativeBrief:
    """
    Human-readable creative brief for production
    Supports both short-form and long-form content
    """
    title: str
    format: VideoFormat
    duration_target_sec: int
    aspect_ratio: AspectRatio
    
    # Brief sections
    product_summary: BriefSection
    performance_rationale: BriefSection
    target_audience: BriefSection
    core_insight: BriefSection
    key_message: BriefSection
    
    # Shot treatment
    shots: List[ShotDescription] = field(default_factory=list)
    
    # Style guide
    look_and_feel: BriefSection = field(default_factory=lambda: BriefSection("", ""))
    offer_and_cta: BriefSection = field(default_factory=lambda: BriefSection("", ""))
    
    # Extended for long-form
    chapter_outline: List[Dict[str, Any]] = field(default_factory=list)
    
    # Generation metadata
    generated_at: str = ""
    source_snapshot_id: Optional[str] = None
    
    def to_markdown(self) -> str:
        """Export brief as markdown"""
        from services.creative_brief_service import CreativeBriefService
        return CreativeBriefService.brief_to_markdown(self)


@dataclass  
class VideoPrompt:
    """
    Text-to-video prompt for AI generation
    Supports single-prompt and multi-shot formats
    """
    duration_seconds: int
    aspect_ratio: str
    style: str = "realistic_ugc"
    
    # Single prompt version
    full_prompt: str = ""
    
    # Multi-shot version
    shots: List[Dict[str, Any]] = field(default_factory=list)
    
    # Safety/moderation flags
    safety: Dict[str, bool] = field(default_factory=lambda: {
        "no_logos": True,
        "no_celebrities": True,
        "no_watermarks": True,
        "no_explicit": True
    })
    
    # Generation settings
    quality: str = "high"
    motion_amount: str = "medium"
    
    def to_single_prompt(self) -> str:
        """Get as single text prompt"""
        if self.full_prompt:
            return self.full_prompt
        
        # Build from shots
        lines = [f"Create a {self.duration_seconds}-second vertical {self.aspect_ratio} video.\n"]
        for shot in self.shots:
            lines.append(f"Scene ({shot.get('start', 0)}-{shot.get('end', 0)}s):\n{shot.get('prompt', '')}\n")
        return "\n".join(lines)
    
    def to_structured_json(self) -> Dict[str, Any]:
        """Get as structured JSON for advanced APIs"""
        return {
            "duration_seconds": self.duration_seconds,
            "aspect_ratio": self.aspect_ratio,
            "style": self.style,
            "shots": self.shots,
            "safety": self.safety,
            "quality": self.quality
        }
