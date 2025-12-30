"""
ReelTrends API Endpoints
========================
Instagram Creator Tools for content generation:
- Script Generator
- Captions Generator
- Carousel Generator
- Hashtag Recommender
- Best Time To Post (Phase 2)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from loguru import logger

from services.trend_intelligence.reeltrends_service import (
    ReelTrendsService,
    ScriptLength,
    ScriptTone,
    ScriptFormat,
    HookStyle,
    CarouselStyle,
)

router = APIRouter(prefix="/api/v1/reeltrends", tags=["ReelTrends"])


# =========================================================================
# Request/Response Models
# =========================================================================

class ScriptRequest(BaseModel):
    topic: str = Field(..., description="What the video is about")
    tone: Literal["casual", "professional", "funny", "urgent"] = "casual"
    length: Literal["short", "medium", "long"] = "medium"
    format: Literal["reel", "short", "talking_head", "voiceover"] = "reel"
    niche: Optional[str] = None
    hook_style: Literal["question", "bold_claim", "controversy", "story"] = "question"


class ScriptBeatResponse(BaseModel):
    name: str
    duration_seconds: int
    script: str
    visual_notes: str
    word_count: int


class ScriptResponse(BaseModel):
    beats: List[ScriptBeatResponse]
    total_duration: int
    estimated_word_count: int
    hooks: List[str]
    hashtag_suggestions: List[str]
    topic: str
    tone: str
    format: str
    generated_at: str


class CaptionsRequest(BaseModel):
    topic: str = Field(..., description="What the content is about")
    tone: Optional[str] = None
    niche: Optional[str] = None
    include_hashtags: bool = True
    emoji_level: Literal["minimal", "moderate", "heavy"] = "moderate"


class CaptionResponse(BaseModel):
    style: str
    caption: str
    character_count: int
    emoji_usage: str


class CaptionsResponse(BaseModel):
    captions: List[CaptionResponse]
    hashtags: dict
    total_hashtag_count: int
    cta_suggestions: List[str]
    topic: str
    generated_at: str


class CarouselRequest(BaseModel):
    topic: str = Field(..., description="What the carousel is about")
    slide_count: int = Field(5, ge=3, le=10, description="Number of slides")
    style: Literal["minimal", "bold", "gradient", "photo_overlay"] = "minimal"
    niche: Optional[str] = None


class CarouselSlideResponse(BaseModel):
    slide_number: int
    purpose: str
    headline: str
    body_text: str
    image_inspo: str
    color_suggestion: str
    layout: str


class CarouselResponse(BaseModel):
    title: str
    slides: List[CarouselSlideResponse]
    cover_text: str
    design_style: str
    topic: str
    generated_at: str


class HashtagRequest(BaseModel):
    topic: str = Field(..., description="Topic for hashtag recommendations")
    niche: Optional[str] = None
    count: int = Field(10, ge=5, le=30)


class HashtagResponse(BaseModel):
    niche: List[str]
    format: List[str]
    discovery: List[str]
    total_count: int
    topic: str
    niche_category: str
    generated_at: str


class ContentPackRequest(BaseModel):
    topic: str = Field(..., description="Topic for all content")
    niche: Optional[str] = None
    tone: Literal["casual", "professional", "funny", "urgent"] = "casual"


class ContentPackResponse(BaseModel):
    topic: str
    niche: Optional[str]
    script: dict
    captions: dict
    carousel: dict
    hashtags: dict
    generated_at: str


# =========================================================================
# Endpoints
# =========================================================================

@router.post("/script", response_model=ScriptResponse)
async def generate_script(request: ScriptRequest):
    """
    Generate a 3-beat video script with time budgets.
    
    Returns:
    - Build-up, Punchline, CTA beats with scripts and visual notes
    - Alternative hook options
    - Hashtag suggestions
    
    Timing budgets:
    - Short: 22s (8/8/6)
    - Medium: 45s (15/15/15)
    - Long: 65s (25/25/15)
    """
    service = ReelTrendsService()
    
    try:
        result = await service.generate_script(
            topic=request.topic,
            tone=ScriptTone(request.tone),
            length=ScriptLength(request.length),
            format=ScriptFormat(request.format),
            niche=request.niche,
            hook_style=HookStyle(request.hook_style)
        )
        
        return ScriptResponse(
            beats=[
                ScriptBeatResponse(
                    name=b.name,
                    duration_seconds=b.duration_seconds,
                    script=b.script,
                    visual_notes=b.visual_notes,
                    word_count=b.word_count
                )
                for b in result.beats
            ],
            total_duration=result.total_duration,
            estimated_word_count=result.estimated_word_count,
            hooks=result.hooks,
            hashtag_suggestions=result.hashtag_suggestions,
            topic=result.topic,
            tone=result.tone,
            format=result.format,
            generated_at=result.generated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Script generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/captions", response_model=CaptionsResponse)
async def generate_captions(request: CaptionsRequest):
    """
    Generate 3 caption variants + bucketed hashtags.
    
    Caption styles:
    - Clean: Professional, no hype
    - Punchy: Bold, viral energy
    - Teach-Mode: Educational micro-thread
    
    Hashtag buckets:
    - Niche: 5 tags
    - Format: 3 tags
    - Discovery: 2 tags
    """
    service = ReelTrendsService()
    
    try:
        result = await service.generate_captions(
            topic=request.topic,
            tone=request.tone,
            niche=request.niche,
            include_hashtags=request.include_hashtags,
            emoji_level=request.emoji_level
        )
        
        return CaptionsResponse(
            captions=[
                CaptionResponse(
                    style=c.style,
                    caption=c.caption,
                    character_count=c.character_count,
                    emoji_usage=c.emoji_usage
                )
                for c in result.captions
            ],
            hashtags=result.hashtags,
            total_hashtag_count=result.total_hashtag_count,
            cta_suggestions=result.cta_suggestions,
            topic=result.topic,
            generated_at=result.generated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Captions generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/carousel", response_model=CarouselResponse)
async def generate_carousel(request: CarouselRequest):
    """
    Generate carousel slide content with copy + image inspiration.
    
    Structure:
    - Slide 1: Hook (question or bold claim)
    - Slides 2-N-1: Value (steps, framework, examples)
    - Slide N: CTA (takeaway + action)
    """
    service = ReelTrendsService()
    
    try:
        result = await service.generate_carousel(
            topic=request.topic,
            slide_count=request.slide_count,
            style=CarouselStyle(request.style),
            niche=request.niche
        )
        
        return CarouselResponse(
            title=result.title,
            slides=[
                CarouselSlideResponse(
                    slide_number=s.slide_number,
                    purpose=s.purpose,
                    headline=s.headline,
                    body_text=s.body_text,
                    image_inspo=s.image_inspo,
                    color_suggestion=s.color_suggestion,
                    layout=s.layout
                )
                for s in result.slides
            ],
            cover_text=result.cover_text,
            design_style=result.design_style,
            topic=result.topic,
            generated_at=result.generated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Carousel generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hashtags", response_model=HashtagResponse)
async def recommend_hashtags(request: HashtagRequest):
    """
    Recommend hashtags in three buckets:
    - Niche: 5 tags targeting specific audience
    - Format: 3 tags for content type
    - Discovery: 2 broad reach tags
    """
    service = ReelTrendsService()
    
    try:
        result = await service.recommend_hashtags(
            topic=request.topic,
            niche=request.niche,
            count=request.count
        )
        
        return HashtagResponse(
            niche=result.niche,
            format=result.format,
            discovery=result.discovery,
            total_count=result.total_count,
            topic=result.topic,
            niche_category=result.niche_category,
            generated_at=result.generated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Hashtag recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/content-pack", response_model=ContentPackResponse)
async def generate_content_pack(request: ContentPackRequest):
    """
    Generate a complete content pack with script, captions, carousel, and hashtags.
    All generated in parallel for the same topic.
    """
    service = ReelTrendsService()
    
    try:
        result = await service.generate_content_pack(
            topic=request.topic,
            niche=request.niche,
            tone=request.tone
        )
        
        return ContentPackResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Content pack generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# GET endpoints for quick access
# =========================================================================

@router.get("/script")
async def generate_script_get(
    topic: str = Query(..., description="What the video is about"),
    tone: str = Query("casual", description="casual, professional, funny, urgent"),
    length: str = Query("medium", description="short, medium, long"),
    format: str = Query("reel", description="reel, short, talking_head, voiceover"),
    niche: Optional[str] = Query(None),
    hook_style: str = Query("question", description="question, bold_claim, controversy, story")
):
    """GET endpoint for script generation"""
    request = ScriptRequest(
        topic=topic,
        tone=tone,
        length=length,
        format=format,
        niche=niche,
        hook_style=hook_style
    )
    return await generate_script(request)


@router.get("/captions")
async def generate_captions_get(
    topic: str = Query(..., description="What the content is about"),
    niche: Optional[str] = Query(None),
    emoji_level: str = Query("moderate", description="minimal, moderate, heavy")
):
    """GET endpoint for captions generation"""
    request = CaptionsRequest(
        topic=topic,
        niche=niche,
        emoji_level=emoji_level
    )
    return await generate_captions(request)


@router.get("/carousel")
async def generate_carousel_get(
    topic: str = Query(..., description="What the carousel is about"),
    slide_count: int = Query(5, ge=3, le=10),
    style: str = Query("minimal", description="minimal, bold, gradient, photo_overlay"),
    niche: Optional[str] = Query(None)
):
    """GET endpoint for carousel generation"""
    request = CarouselRequest(
        topic=topic,
        slide_count=slide_count,
        style=style,
        niche=niche
    )
    return await generate_carousel(request)


@router.get("/hashtags")
async def recommend_hashtags_get(
    topic: str = Query(..., description="Topic for hashtag recommendations"),
    niche: Optional[str] = Query(None)
):
    """GET endpoint for hashtag recommendations"""
    request = HashtagRequest(topic=topic, niche=niche)
    return await recommend_hashtags(request)


# =========================================================================
# Info endpoint
# =========================================================================

@router.get("/info")
async def get_reeltrends_info():
    """Get information about available ReelTrends tools"""
    return {
        "tools": [
            {
                "name": "Script Generator",
                "endpoint": "/api/v1/reeltrends/script",
                "description": "Generate 3-beat video scripts with time budgets",
                "options": {
                    "lengths": ["short (22s)", "medium (45s)", "long (65s)"],
                    "tones": ["casual", "professional", "funny", "urgent"],
                    "formats": ["reel", "short", "talking_head", "voiceover"],
                    "hook_styles": ["question", "bold_claim", "controversy", "story"]
                }
            },
            {
                "name": "Captions Generator",
                "endpoint": "/api/v1/reeltrends/captions",
                "description": "Generate 3 caption variants + bucketed hashtags",
                "options": {
                    "styles": ["clean", "punchy", "teach_mode"],
                    "emoji_levels": ["minimal", "moderate", "heavy"]
                }
            },
            {
                "name": "Carousel Generator",
                "endpoint": "/api/v1/reeltrends/carousel",
                "description": "Generate slide content with copy + image inspiration",
                "options": {
                    "slide_count": "3-10",
                    "styles": ["minimal", "bold", "gradient", "photo_overlay"]
                }
            },
            {
                "name": "Hashtag Recommender",
                "endpoint": "/api/v1/reeltrends/hashtags",
                "description": "Recommend hashtags in niche/format/discovery buckets"
            },
            {
                "name": "Content Pack",
                "endpoint": "/api/v1/reeltrends/content-pack",
                "description": "Generate script + captions + carousel + hashtags in one call"
            }
        ],
        "coming_soon": [
            "Best Time To Post",
            "Post Analyzer",
            "Viral Forecaster",
            "Sound Analytics"
        ]
    }
