"""
Hashtag Generator API Endpoints
AI-powered hashtag recommendations based on content and trends
"""
from fastapi import APIRouter, HTTPException, Query, Form
from pydantic import BaseModel
from typing import Optional, List, Dict
from loguru import logger

from services.instagram.hashtag_generator import get_hashtag_generator

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class HashtagResponse(BaseModel):
    tag: str
    media_count: int
    velocity: float
    trending_score: float
    competition: str
    type: str


class GenerateHashtagsRequest(BaseModel):
    content: str
    niche: Optional[str] = None
    existing_hashtags: Optional[List[str]] = None


class GenerateHashtagsResponse(BaseModel):
    trending: List[Dict]
    niche: List[Dict]
    long_tail: List[Dict]
    detected_niche: str
    total_count: int


class HashtagAnalysisResponse(BaseModel):
    tag: str
    found: bool
    media_count: Optional[int] = None
    velocity: Optional[float] = None
    trending_score: Optional[float] = None
    competition: str
    category: Optional[str] = None
    recommendation: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/generate")
async def generate_hashtags(request: GenerateHashtagsRequest):
    """
    Generate optimized hashtag set for content.
    
    Returns:
    - 10 trending hashtags (high velocity, high competition)
    - 10 niche hashtags (medium competition, targeted)
    - 10 long-tail hashtags (low competition, specific)
    
    Total: 30 hashtags
    """
    try:
        generator = get_hashtag_generator()
        result = await generator.generate_hashtags(
            request.content,
            request.niche,
            request.existing_hashtags
        )
        
        return GenerateHashtagsResponse(**result)
    except Exception as e:
        logger.error(f"Failed to generate hashtags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/quick")
async def generate_hashtags_quick(
    content: str = Form(..., description="Video transcript or caption"),
    niche: Optional[str] = Form(None, description="Content niche"),
    existing_hashtags: Optional[str] = Form(None, description="Comma-separated existing hashtags")
):
    """
    Quick hashtag generation via form data.
    
    Useful for testing or simple integrations.
    """
    try:
        # Parse existing hashtags
        existing_list = []
        if existing_hashtags:
            existing_list = [h.strip() for h in existing_hashtags.split(",") if h.strip()]
        
        generator = get_hashtag_generator()
        result = await generator.generate_hashtags(content, niche, existing_list)
        
        return result
    except Exception as e:
        logger.error(f"Quick hashtag generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/{hashtag}")
async def analyze_hashtag(hashtag: str):
    """
    Analyze performance metrics for a specific hashtag.
    
    Returns competition score and recommendations.
    """
    try:
        generator = get_hashtag_generator()
        analysis = generator.analyze_hashtag_performance(hashtag)
        
        return HashtagAnalysisResponse(**analysis)
    except Exception as e:
        logger.error(f"Failed to analyze hashtag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/{category}")
async def get_hashtag_suggestions(
    category: str,
    limit: int = Query(30, ge=1, le=50, description="Number of suggestions")
):
    """
    Get hashtag suggestions for a specific category.
    
    Returns mix of trending, medium, and low competition tags.
    """
    try:
        generator = get_hashtag_generator()
        suggestions = generator.get_hashtag_suggestions_by_category(category, limit)
        
        return {
            "category": category,
            "count": len(suggestions),
            "hashtags": suggestions
        }
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-analyze")
async def batch_analyze_hashtags(hashtags: List[str]):
    """
    Analyze multiple hashtags at once.
    
    Returns analysis for each hashtag.
    """
    try:
        generator = get_hashtag_generator()
        results = []
        
        for hashtag in hashtags:
            analysis = generator.analyze_hashtag_performance(hashtag)
            results.append(analysis)
        
        return {
            "count": len(results),
            "analyses": results
        }
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
