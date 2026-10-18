"""
AI Title & Description Generation API (PIPE-003)
================================================
Generate AI-powered titles, descriptions, and metadata for videos
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.ai_title_generator import AITitleGenerator, Platform, TitleStyle
from loguru import logger

router = APIRouter(prefix="/api/ai-titles", tags=["AI Title Generator"])


# Request/Response Models

class GenerateSuggestionsRequest(BaseModel):
    """Request to generate content suggestions"""
    video_id: str = Field(..., description="Video ID (UUID)")
    platforms: List[Platform] = Field(
        default=[Platform.TIKTOK, Platform.INSTAGRAM],
        description="Target platforms"
    )
    content_analysis: Optional[Dict[str, Any]] = Field(
        None,
        description="Pre-computed content analysis (optional)"
    )
    transcript: Optional[str] = Field(None, description="Video transcript (optional)")
    target_audience: Optional[str] = Field(
        None,
        description="Target audience description (optional)"
    )
    brand_voice: Optional[str] = Field(
        None,
        description="Brand voice guidelines (optional)"
    )
    include_hashtags: bool = Field(True, description="Generate hashtags")
    title_variations: int = Field(3, description="Number of title variations per style", ge=1, le=10)


class TitleVariationResponse(BaseModel):
    """Title variation response"""
    text: str
    style: str
    platform: str
    character_count: int
    hook_score: float
    seo_score: float
    engagement_prediction: float
    metadata: Dict[str, Any] = {}


class ContentSuggestionsResponse(BaseModel):
    """Content suggestions response"""
    titles: List[TitleVariationResponse]
    descriptions: Dict[str, str]
    hashtags: List[str]
    call_to_action: str
    key_moments: List[Dict[str, Any]]
    target_keywords: List[str]
    generated_at: str


class BatchGenerateRequest(BaseModel):
    """Batch generate request"""
    video_ids: List[str] = Field(..., description="List of video IDs")
    platforms: List[Platform] = Field(
        default=[Platform.TIKTOK, Platform.INSTAGRAM],
        description="Target platforms"
    )
    max_concurrent: int = Field(3, description="Max concurrent generations", ge=1, le=10)


# API Endpoints

@router.post("/generate", response_model=ContentSuggestionsResponse)
async def generate_suggestions(
    request: GenerateSuggestionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI-powered title and description suggestions for a video

    This endpoint uses GPT-4 to generate:
    - Multiple title variations optimized for each platform
    - Platform-specific descriptions
    - Relevant hashtags
    - Call-to-action suggestions
    - Key moments and timestamps

    The generator uses the FATE framework (Focus, Authority, Tribe, Emotion)
    to create engaging, high-converting content.

    **Example Request:**
    ```json
    {
        "video_id": "abc-123",
        "platforms": ["tiktok", "instagram", "youtube"],
        "target_audience": "fitness enthusiasts aged 25-35",
        "brand_voice": "energetic, motivational, authentic",
        "include_hashtags": true,
        "title_variations": 3
    }
    ```

    **Example Response:**
    ```json
    {
        "titles": [
            {
                "text": "This workout changed my life in 30 days",
                "style": "story",
                "platform": "tiktok",
                "character_count": 41,
                "hook_score": 0.85,
                "seo_score": 0.70,
                "engagement_prediction": 0.82
            }
        ],
        "descriptions": {
            "tiktok": "30-day transformation you won't believe! 💪 #fitness",
            "instagram": "Full story of my fitness journey..."
        },
        "hashtags": ["#fitness", "#transformation", "#motivation"],
        "call_to_action": "Follow for more workout tips!",
        "key_moments": [
            {"timestamp": 5, "description": "Before transformation", "emotion": "vulnerable"}
        ],
        "target_keywords": ["workout", "transformation", "fitness"]
    }
    ```
    """
    try:
        # Create generator
        generator = AITitleGenerator(db)

        # Generate suggestions
        suggestions = await generator.generate_suggestions(
            video_id=request.video_id,
            platforms=request.platforms,
            content_analysis=request.content_analysis,
            transcript=request.transcript,
            target_audience=request.target_audience,
            brand_voice=request.brand_voice,
            include_hashtags=request.include_hashtags,
            title_variations=request.title_variations
        )

        # Convert to response model
        return ContentSuggestionsResponse(
            titles=[
                TitleVariationResponse(
                    text=t.text,
                    style=t.style.value,
                    platform=t.platform.value,
                    character_count=t.character_count,
                    hook_score=t.hook_score,
                    seo_score=t.seo_score,
                    engagement_prediction=t.engagement_prediction,
                    metadata=t.metadata
                )
                for t in suggestions.titles
            ],
            descriptions={p.value: desc for p, desc in suggestions.descriptions.items()},
            hashtags=suggestions.hashtags,
            call_to_action=suggestions.call_to_action,
            key_moments=suggestions.key_moments,
            target_keywords=suggestions.target_keywords,
            generated_at=suggestions.generated_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=Dict[str, ContentSuggestionsResponse])
async def batch_generate(
    request: BatchGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Batch generate suggestions for multiple videos

    Efficiently generate content suggestions for multiple videos in parallel.

    **Example Request:**
    ```json
    {
        "video_ids": ["abc-123", "def-456", "ghi-789"],
        "platforms": ["tiktok", "instagram"],
        "max_concurrent": 3
    }
    ```
    """
    try:
        # Create generator
        generator = AITitleGenerator(db)

        # Batch generate
        results = await generator.batch_generate(
            video_ids=request.video_ids,
            platforms=request.platforms,
            max_concurrent=request.max_concurrent
        )

        # Convert to response
        response = {}
        for video_id, suggestions in results.items():
            response[video_id] = ContentSuggestionsResponse(
                titles=[
                    TitleVariationResponse(
                        text=t.text,
                        style=t.style.value,
                        platform=t.platform.value,
                        character_count=t.character_count,
                        hook_score=t.hook_score,
                        seo_score=t.seo_score,
                        engagement_prediction=t.engagement_prediction,
                        metadata=t.metadata
                    )
                    for t in suggestions.titles
                ],
                descriptions={p.value: desc for p, desc in suggestions.descriptions.items()},
                hashtags=suggestions.hashtags,
                call_to_action=suggestions.call_to_action,
                key_moments=suggestions.key_moments,
                target_keywords=suggestions.target_keywords,
                generated_at=suggestions.generated_at.isoformat()
            )

        return response

    except Exception as e:
        logger.error(f"Error in batch generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/styles", response_model=List[str])
async def get_title_styles():
    """
    Get available title generation styles

    Returns list of title styles that can be used for generation:
    - curiosity: "You won't believe..."
    - question: "How does this work?"
    - listicle: "5 ways to..."
    - story: "I tried... and this happened"
    - direct: "How to..."
    - urgency: "Stop doing this now"
    - controversial: "Nobody talks about..."
    """
    return [style.value for style in TitleStyle]


@router.get("/platforms", response_model=List[str])
async def get_supported_platforms():
    """
    Get supported social media platforms

    Returns list of platforms that have optimized title/description generation
    """
    return [platform.value for platform in Platform]


@router.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns the status of the AI Title Generator service
    """
    from services.ai_title_generator import openai
    from config import settings

    return {
        "status": "healthy",
        "service": "ai-title-generator",
        "ai_enabled": openai is not None and bool(settings.openai_api_key),
        "fallback_mode": not (openai and settings.openai_api_key)
    }
