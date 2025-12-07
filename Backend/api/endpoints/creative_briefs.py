"""
Creative Brief API Endpoints
REST API for generating creative briefs and T2V prompts
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from loguru import logger

from models.creative_brief_models import (
    AngleInsightSnapshot,
    ProductPerformanceSnapshot,
    VideoAnalysisSnapshot,
    VideoFormat,
    AspectRatio,
    PriceRange,
    Metrics30Day,
    AffiliateInfo,
    VideoPerformance,
    TranscriptData,
    ExtractedAngles,
    SceneAnalysis,
    SceneRole,
    FrameTags,
    SceneSemantics,
    SnapshotMeta
)
from services.creative_brief_service import CreativeBriefService

router = APIRouter(prefix="/api/creative-briefs", tags=["creative-briefs"])


# ============================================
# Request/Response Models
# ============================================

class VideoFormatEnum(str, Enum):
    short_form = "short_form"
    long_form = "long_form"
    ad_creative = "ad_creative"
    ugc = "ugc"


class ProductDataRequest(BaseModel):
    """Product data from Kalodata-style source"""
    product_id: str
    product_name: str
    category: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    launch_date: Optional[str] = None
    
    # 30-day metrics
    revenue_usd: Optional[float] = None
    revenue_growth_pct: Optional[float] = None
    items_sold: Optional[int] = None
    avg_unit_price: Optional[float] = None
    
    # Affiliate data
    is_affiliate: bool = False
    commission_rate_pct: Optional[float] = None
    creator_count: Optional[int] = None
    conversion_ratio_pct: Optional[float] = None


class SceneDataRequest(BaseModel):
    """Scene data from video analysis"""
    start_sec: float
    end_sec: float
    role: str = "other"  # hook, problem, demo, proof, after, cta
    
    setting: Optional[str] = None
    camera_type: Optional[str] = None
    shot_type: Optional[str] = None
    main_objects: List[str] = Field(default_factory=list)
    on_screen_text: Optional[str] = None
    
    summary: Optional[str] = None
    emotion: Optional[str] = None
    hook_type: Optional[str] = None


class VideoDataRequest(BaseModel):
    """Video analysis data"""
    video_id: str
    video_url: str
    duration_sec: float
    aspect_ratio: str = "9:16"
    
    # Performance
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    revenue_contribution_usd: Optional[float] = None
    
    # Transcript
    transcript_text: Optional[str] = None
    transcript_summary: Optional[str] = None
    key_phrases: List[str] = Field(default_factory=list)
    
    # Scenes
    scenes: List[SceneDataRequest] = Field(default_factory=list)
    
    # Extracted angles
    core_promise: Optional[str] = None
    angle_types: List[str] = Field(default_factory=list)
    pain_points: List[str] = Field(default_factory=list)
    emotional_drivers: List[str] = Field(default_factory=list)
    hook_lines: List[str] = Field(default_factory=list)
    cta_style: Optional[str] = None


class GenerateBriefRequest(BaseModel):
    """Request to generate a creative brief"""
    product: ProductDataRequest
    video: VideoDataRequest
    
    format_type: VideoFormatEnum = VideoFormatEnum.short_form
    target_duration: Optional[int] = None
    niche: str = "default"
    
    # Output options
    include_shots: bool = True
    output_format: str = "markdown"  # markdown, json


class GeneratePromptRequest(BaseModel):
    """Request to generate a T2V prompt"""
    product: ProductDataRequest
    video: VideoDataRequest
    
    style: str = "realistic_ugc"
    output_format: str = "text"  # text, json
    include_safety: bool = True


class BriefResponse(BaseModel):
    """Creative brief response"""
    brief_id: str
    title: str
    format: str
    duration_target_sec: int
    
    # Markdown version
    markdown: Optional[str] = None
    
    # JSON version
    brief_json: Optional[Dict[str, Any]] = None
    
    generated_at: str


class PromptResponse(BaseModel):
    """T2V prompt response"""
    prompt_id: str
    duration_seconds: int
    aspect_ratio: str
    style: str
    
    # Text prompt
    full_prompt: Optional[str] = None
    
    # Structured prompt
    shots: Optional[List[Dict[str, Any]]] = None
    
    safety: Dict[str, bool]


# ============================================
# Helper Functions
# ============================================

def convert_to_snapshot(product: ProductDataRequest, video: VideoDataRequest) -> AngleInsightSnapshot:
    """Convert request data to AngleInsightSnapshot"""
    
    # Build product snapshot
    price_range = None
    if product.price_min is not None:
        price_range = PriceRange(
            min_price=product.price_min,
            max_price=product.price_max
        )
    
    metrics = None
    if product.revenue_usd is not None:
        metrics = Metrics30Day(
            revenue_usd=product.revenue_usd,
            revenue_growth_rate_pct=product.revenue_growth_pct,
            items_sold=product.items_sold or 0,
            avg_unit_price=product.avg_unit_price or 0.0
        )
    
    affiliate = AffiliateInfo(
        is_affiliate_product=product.is_affiliate,
        commission_rate_pct=product.commission_rate_pct,
        creator_count=product.creator_count or 0,
        creator_conversion_ratio_pct=product.conversion_ratio_pct
    )
    
    product_snapshot = ProductPerformanceSnapshot(
        product_id=product.product_id,
        product_name=product.product_name,
        category=product.category,
        price_range=price_range,
        launch_date=product.launch_date,
        metrics_30d=metrics,
        affiliate=affiliate,
        highest_revenue_video_id=video.video_id
    )
    
    # Build video snapshot
    performance = VideoPerformance(
        views=video.views,
        likes=video.likes,
        comments=video.comments,
        shares=video.shares,
        revenue_contribution_usd=video.revenue_contribution_usd
    )
    
    transcript = TranscriptData(
        full_text=video.transcript_text or "",
        summary=video.transcript_summary or "",
        key_phrases=video.key_phrases
    )
    
    scenes = []
    for s in video.scenes:
        role = SceneRole.OTHER
        try:
            role = SceneRole(s.role.lower())
        except ValueError:
            pass
        
        scene = SceneAnalysis(
            start_sec=s.start_sec,
            end_sec=s.end_sec,
            role=role,
            frame_tags=FrameTags(
                setting=s.setting or "",
                camera_type=s.camera_type or "",
                shot_type=s.shot_type or "",
                main_objects=s.main_objects,
                on_screen_text=s.on_screen_text
            ),
            semantics=SceneSemantics(
                mini_summary=s.summary or "",
                emotion=s.emotion or "",
                hook_type=s.hook_type
            )
        )
        scenes.append(scene)
    
    extracted = ExtractedAngles(
        core_promise=video.core_promise or "",
        angle_types=video.angle_types,
        primary_pain_points=video.pain_points,
        emotional_drivers=video.emotional_drivers,
        hook_lines=video.hook_lines,
        cta_style=video.cta_style or ""
    )
    
    video_snapshot = VideoAnalysisSnapshot(
        video_id=video.video_id,
        video_url=video.video_url,
        duration_sec=video.duration_sec,
        aspect_ratio=video.aspect_ratio,
        performance=performance,
        transcript=transcript,
        scenes=scenes,
        extracted_angles=extracted
    )
    
    meta = SnapshotMeta(
        snapshot_date="",
        data_sources=["api_request"],
        overall_angle_label=video.core_promise or "",
        recommended_use_cases=["creative_brief", "t2v_prompt"]
    )
    
    return AngleInsightSnapshot(
        product=product_snapshot,
        video=video_snapshot,
        meta=meta
    )


# ============================================
# Endpoints
# ============================================

@router.post("/generate-brief", response_model=BriefResponse)
async def generate_creative_brief(request: GenerateBriefRequest):
    """
    Generate a human-readable creative brief from product + video data
    
    Supports:
    - short_form: TikTok, Reels, Shorts (15-60s)
    - long_form: YouTube tutorials (2-15min)
    - ad_creative: Paid ads (15-45s)
    - ugc: User-generated content style
    """
    try:
        snapshot = convert_to_snapshot(request.product, request.video)
        
        format_map = {
            VideoFormatEnum.short_form: VideoFormat.SHORT_FORM,
            VideoFormatEnum.long_form: VideoFormat.LONG_FORM,
            VideoFormatEnum.ad_creative: VideoFormat.AD_CREATIVE,
            VideoFormatEnum.ugc: VideoFormat.UGC
        }
        
        brief = CreativeBriefService.build_creative_brief(
            snapshot=snapshot,
            format_type=format_map.get(request.format_type, VideoFormat.SHORT_FORM),
            target_duration=request.target_duration,
            niche=request.niche
        )
        
        import uuid
        from datetime import datetime
        
        response = BriefResponse(
            brief_id=str(uuid.uuid4()),
            title=brief.title,
            format=brief.format.value,
            duration_target_sec=brief.duration_target_sec,
            generated_at=datetime.now().isoformat()
        )
        
        if request.output_format == "markdown":
            response.markdown = brief.to_markdown()
        else:
            import dataclasses
            # Convert to dict, handling enums
            brief_dict = {}
            for field in dataclasses.fields(brief):
                value = getattr(brief, field.name)
                if hasattr(value, 'value'):
                    brief_dict[field.name] = value.value
                else:
                    brief_dict[field.name] = value
            response.brief_json = brief_dict
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating brief: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-prompt", response_model=PromptResponse)
async def generate_video_prompt(request: GeneratePromptRequest):
    """
    Generate a text-to-video prompt for AI video generation
    
    Supports output formats:
    - text: Single comprehensive prompt
    - json: Structured multi-shot prompt for advanced APIs
    """
    try:
        snapshot = convert_to_snapshot(request.product, request.video)
        
        prompt = CreativeBriefService.build_video_prompt(
            snapshot=snapshot,
            output_format=request.output_format,
            style=request.style,
            include_safety=request.include_safety
        )
        
        import uuid
        
        response = PromptResponse(
            prompt_id=str(uuid.uuid4()),
            duration_seconds=prompt.duration_seconds,
            aspect_ratio=prompt.aspect_ratio,
            style=prompt.style,
            safety=prompt.safety
        )
        
        if request.output_format == "text":
            response.full_prompt = prompt.to_single_prompt()
        else:
            response.shots = prompt.shots
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported video formats with configurations"""
    formats = []
    for format_type, config in CreativeBriefService.FORMAT_CONFIGS.items():
        formats.append({
            "format": format_type.value,
            "duration_range": config["duration_range"],
            "default_duration": config["default_duration"],
            "aspect_ratio": config["aspect_ratio"].value,
            "platforms": config["platforms"]
        })
    return {"formats": formats}


@router.get("/niches")
async def get_supported_niches():
    """Get list of supported content niches with style guides"""
    niches = []
    for niche, style in CreativeBriefService.NICHE_STYLES.items():
        niches.append({
            "niche": niche,
            **style
        })
    return {"niches": niches}


@router.get("/scene-roles")
async def get_scene_roles():
    """Get list of valid scene roles"""
    return {
        "roles": [
            {"role": "hook", "description": "Opening/attention grabber"},
            {"role": "problem", "description": "Problem identification"},
            {"role": "demo", "description": "Product demonstration"},
            {"role": "proof", "description": "Social proof/testimonials"},
            {"role": "after", "description": "Results/transformation"},
            {"role": "cta", "description": "Call to action"},
            {"role": "intro", "description": "Introduction (long-form)"},
            {"role": "outro", "description": "Outro (long-form)"},
            {"role": "transition", "description": "Transition between sections"},
            {"role": "other", "description": "Other/miscellaneous"}
        ]
    }
