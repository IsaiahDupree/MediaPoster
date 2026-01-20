"""
Platform Matching API (PIPE-004)
=================================
API endpoints for intelligent platform matching
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from services.platform_matcher import PlatformMatcher, Platform, ContentType
from loguru import logger

router = APIRouter(prefix="/api/platform-matching", tags=["Platform Matching"])


# Request/Response Models

class MatchVideoRequest(BaseModel):
    """Request to match a video to platforms"""
    duration: int = Field(..., description="Video duration in seconds", ge=1)
    aspect_ratio: str = Field(..., description="Aspect ratio (e.g., '9:16', '16:9', '1:1')")
    content_type: str = Field(..., description="Content type (e.g., 'tutorial', 'vlog', 'comedy')")
    niche: Optional[str] = Field(None, description="Content niche (e.g., 'fitness', 'tech')")
    target_audience: Optional[str] = Field(None, description="Target audience (e.g., 'young', 'professional', 'general')")
    has_text_overlay: bool = Field(False, description="Whether video has text overlays")
    quality_score: float = Field(7.0, description="Video quality score (1-10)", ge=1.0, le=10.0)
    top_n: int = Field(5, description="Number of top matches to return", ge=1, le=15)


class PlatformMatchResponse(BaseModel):
    """Platform match response"""
    platform: str
    confidence_score: float
    format_score: float
    duration_score: float
    content_score: float
    audience_score: float
    recommendations: List[str]
    required_adaptations: List[str]
    metadata: Dict[str, Any]


class VideoInfo(BaseModel):
    """Video information for batch matching"""
    id: str
    duration: int
    aspect_ratio: str
    content_type: str
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    has_text_overlay: bool = False
    quality_score: float = 7.0


class BatchMatchRequest(BaseModel):
    """Batch match request"""
    videos: List[VideoInfo] = Field(..., description="List of videos to match")
    top_n: int = Field(5, description="Number of top matches per video", ge=1, le=15)


# API Endpoints

@router.post("/match", response_model=List[PlatformMatchResponse])
async def match_video(request: MatchVideoRequest):
    """
    Match a video to optimal social media platforms

    This endpoint analyzes video characteristics and recommends the best
    platforms to publish on, along with specific recommendations and
    required adaptations for each platform.

    **Scoring Methodology:**
    - **Format Score**: How well the aspect ratio fits the platform (30% weight)
    - **Duration Score**: How well the duration fits platform limits (25% weight)
    - **Content Score**: How well the content type fits platform preferences (25% weight)
    - **Audience Score**: How well the audience aligns with platform demographics (20% weight)
    - **Confidence Score**: Weighted combination of all scores (0-1)

    **Example Request:**
    ```json
    {
        "duration": 45,
        "aspect_ratio": "9:16",
        "content_type": "tutorial",
        "niche": "fitness",
        "target_audience": "young",
        "has_text_overlay": true,
        "quality_score": 8.5,
        "top_n": 3
    }
    ```

    **Example Response:**
    ```json
    [
        {
            "platform": "tiktok",
            "confidence_score": 0.925,
            "format_score": 1.0,
            "duration_score": 0.85,
            "content_score": 1.0,
            "audience_score": 0.9,
            "recommendations": [
                "Use trending sounds and effects",
                "Hook viewers in first 3 seconds",
                "Use up to 30 relevant hashtags"
            ],
            "required_adaptations": [],
            "metadata": {
                "quality_score": 8.5,
                "has_text_overlay": true
            }
        }
    ]
    ```

    **Content Types:**
    - `talking_head`: Direct-to-camera speaking
    - `broll`: B-roll footage, scenic shots
    - `tutorial`: How-to, educational
    - `vlog`: Personal vlog style
    - `product_demo`: Product demonstrations
    - `comedy`: Comedy/entertainment
    - `educational`: Educational content
    - `entertainment`: General entertainment
    - `news`: News content
    - `review`: Product/service reviews

    **Aspect Ratios:**
    - `9:16`: Vertical (TikTok, Reels, Stories)
    - `1:1`: Square (Instagram Feed)
    - `16:9`: Horizontal (YouTube, Facebook)
    """
    try:
        # Create matcher
        matcher = PlatformMatcher()

        # Match video
        matches = matcher.match_video(
            duration=request.duration,
            aspect_ratio=request.aspect_ratio,
            content_type=request.content_type,
            niche=request.niche,
            target_audience=request.target_audience,
            has_text_overlay=request.has_text_overlay,
            quality_score=request.quality_score,
            top_n=request.top_n
        )

        # Convert to response
        return [
            PlatformMatchResponse(**match.to_dict())
            for match in matches
        ]

    except Exception as e:
        logger.error(f"Error matching video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=Dict[str, List[PlatformMatchResponse]])
async def batch_match(request: BatchMatchRequest):
    """
    Batch match multiple videos to platforms

    Process multiple videos at once and get platform recommendations for each.

    **Example Request:**
    ```json
    {
        "videos": [
            {
                "id": "video-1",
                "duration": 30,
                "aspect_ratio": "9:16",
                "content_type": "tutorial",
                "niche": "fitness"
            },
            {
                "id": "video-2",
                "duration": 180,
                "aspect_ratio": "16:9",
                "content_type": "vlog",
                "niche": "travel"
            }
        ],
        "top_n": 3
    }
    ```
    """
    try:
        # Create matcher
        matcher = PlatformMatcher()

        # Convert videos to dicts
        videos = [video.model_dump() for video in request.videos]

        # Batch match
        results = matcher.batch_match(
            videos=videos,
            top_n=request.top_n
        )

        # Convert to response
        response = {}
        for video_id, matches in results.items():
            response[video_id] = [
                PlatformMatchResponse(**match.to_dict())
                for match in matches
            ]

        return response

    except Exception as e:
        logger.error(f"Error in batch matching: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platforms", response_model=List[str])
async def get_supported_platforms():
    """
    Get list of supported platforms

    Returns all platforms that the matcher can recommend.
    """
    return [platform.value for platform in Platform]


@router.get("/content-types", response_model=List[str])
async def get_content_types():
    """
    Get list of supported content types

    Returns all content types that can be matched.
    """
    return [content_type.value for content_type in ContentType]


@router.get("/requirements/{platform}")
async def get_platform_requirements(platform: str):
    """
    Get requirements for a specific platform

    Returns detailed requirements and preferences for the specified platform.

    **Example Response:**
    ```json
    {
        "platform": "tiktok",
        "min_duration": 5,
        "max_duration": 180,
        "preferred_aspect_ratios": ["9:16"],
        "preferred_content_types": ["comedy", "educational", "entertainment", "tutorial"],
        "requires_vertical": true,
        "audience_skew": "young",
        "best_for_niches": ["fitness", "food", "comedy", "tech", "education", "diy"],
        "supports_text_overlay": true,
        "supports_captions": true,
        "supports_hashtags": true,
        "max_hashtags": 30
    }
    ```
    """
    try:
        # Create matcher
        matcher = PlatformMatcher()

        # Get platform enum
        try:
            platform_enum = Platform(platform.lower())
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Platform '{platform}' not found")

        # Get requirements
        if platform_enum not in matcher.platform_requirements:
            raise HTTPException(status_code=404, detail=f"Requirements for '{platform}' not found")

        requirements = matcher.platform_requirements[platform_enum]

        return {
            "platform": requirements.platform.value,
            "min_duration": requirements.min_duration,
            "max_duration": requirements.max_duration,
            "preferred_aspect_ratios": [ar.value for ar in requirements.preferred_aspect_ratios],
            "preferred_content_types": [ct.value for ct in requirements.preferred_content_types],
            "requires_vertical": requirements.requires_vertical,
            "audience_skew": requirements.audience_skew,
            "best_for_niches": requirements.best_for_niches,
            "supports_text_overlay": requirements.supports_text_overlay,
            "supports_captions": requirements.supports_captions,
            "supports_hashtags": requirements.supports_hashtags,
            "max_hashtags": requirements.max_hashtags
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting platform requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns the status of the Platform Matching service
    """
    matcher = PlatformMatcher()

    return {
        "status": "healthy",
        "service": "platform-matcher",
        "platforms_supported": len(matcher.platform_requirements),
        "platform_list": [p.value for p in Platform]
    }
