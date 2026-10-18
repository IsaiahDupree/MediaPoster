"""
Video Routing API Endpoints
Handles video orientation detection and platform routing
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from loguru import logger

from services.video.video_analyzer import get_video_analyzer, Orientation
from services.video.video_router import get_video_router

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class AnalyzeVideoRequest(BaseModel):
    video_id: str
    file_path: str


class VideoMetadataResponse(BaseModel):
    video_id: str
    orientation: str
    aspect_ratio: float
    width: int
    height: int
    duration_seconds: float
    file_size_bytes: int
    codec: str
    bitrate: int
    fps: float


class RouteVideoRequest(BaseModel):
    video_id: str
    orientation: str
    duration_seconds: float
    user_preferences: Optional[Dict] = None
    manual_override: Optional[List[str]] = None


class RoutingDecisionResponse(BaseModel):
    video_id: str
    recommended_platforms: List[str]
    routing_rule: str
    reasoning: str
    youtube_channel_id: Optional[str] = None
    alternative_platforms: Optional[List[str]] = None
    can_override: bool
    auto_routed: bool


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/analyze", response_model=VideoMetadataResponse)
async def analyze_video(request: AnalyzeVideoRequest):
    """
    Analyze video file to extract orientation and metadata.
    
    Uses FFmpeg to extract:
    - Orientation (vertical, horizontal, square)
    - Dimensions and aspect ratio
    - Duration
    - Codec and bitrate information
    """
    try:
        analyzer = get_video_analyzer()
        metadata = analyzer.analyze_video(request.file_path)
        
        return VideoMetadataResponse(
            video_id=request.video_id,
            orientation=metadata.orientation.value,
            aspect_ratio=metadata.aspect_ratio,
            width=metadata.width,
            height=metadata.height,
            duration_seconds=metadata.duration_seconds,
            file_size_bytes=metadata.file_size_bytes,
            codec=metadata.codec,
            bitrate=metadata.bitrate,
            fps=metadata.fps
        )
    except FileNotFoundError as e:
        logger.error(f"Video file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route", response_model=RoutingDecisionResponse)
async def route_video(request: RouteVideoRequest):
    """
    Determine optimal platforms for video based on characteristics.
    
    Routing Rules:
    - Vertical + < 60s → TikTok, Instagram Reels, YouTube Shorts
    - Horizontal + > 60s → YouTube (main channel)
    - Horizontal + < 60s → YouTube Shorts
    - Square → Instagram Feed, Facebook
    """
    try:
        router_service = get_video_router()
        
        # Convert orientation string to enum
        orientation = Orientation(request.orientation)
        
        # Determine platforms
        decision = router_service.determine_platforms(
            video_id=request.video_id,
            orientation=orientation,
            duration=request.duration_seconds,
            user_preferences=request.user_preferences,
            manual_override=request.manual_override
        )
        
        return RoutingDecisionResponse(
            video_id=decision.video_id,
            recommended_platforms=decision.recommended_platforms,
            routing_rule=decision.routing_rule,
            reasoning=decision.reasoning,
            youtube_channel_id=decision.youtube_channel_id,
            alternative_platforms=decision.alternative_platforms,
            can_override=decision.can_override,
            auto_routed=decision.auto_routed
        )
    except ValueError as e:
        logger.error(f"Invalid orientation value: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid orientation: {request.orientation}")
    except Exception as e:
        logger.error(f"Error routing video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-and-route")
async def analyze_and_route_video(request: AnalyzeVideoRequest):
    """
    Analyze video and automatically determine routing in one call.
    
    Combines analyze + route endpoints for convenience.
    """
    try:
        # Analyze video
        analyzer = get_video_analyzer()
        metadata = analyzer.analyze_video(request.file_path)
        
        # Route based on analysis
        router_service = get_video_router()
        decision = router_service.determine_platforms(
            video_id=request.video_id,
            orientation=metadata.orientation,
            duration=metadata.duration_seconds
        )
        
        return {
            "metadata": VideoMetadataResponse(
                video_id=request.video_id,
                orientation=metadata.orientation.value,
                aspect_ratio=metadata.aspect_ratio,
                width=metadata.width,
                height=metadata.height,
                duration_seconds=metadata.duration_seconds,
                file_size_bytes=metadata.file_size_bytes,
                codec=metadata.codec,
                bitrate=metadata.bitrate,
                fps=metadata.fps
            ),
            "routing": RoutingDecisionResponse(
                video_id=decision.video_id,
                recommended_platforms=decision.recommended_platforms,
                routing_rule=decision.routing_rule,
                reasoning=decision.reasoning,
                youtube_channel_id=decision.youtube_channel_id,
                alternative_platforms=decision.alternative_platforms,
                can_override=decision.can_override,
                auto_routed=decision.auto_routed
            )
        }
    except FileNotFoundError as e:
        logger.error(f"Video file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in analyze-and-route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing-rules")
async def get_routing_rules():
    """
    Get current routing rules configuration.
    
    Returns the rules used to determine platform routing.
    """
    return {
        "rules": [
            {
                "name": "vertical_short_form",
                "condition": "Vertical (9:16) + < 60 seconds",
                "platforms": ["tiktok", "instagram_reels", "youtube_shorts"],
                "reasoning": "Short vertical content optimal for short-form platforms"
            },
            {
                "name": "vertical_medium_form",
                "condition": "Vertical (9:16) + 60-90 seconds",
                "platforms": ["instagram_reels", "youtube_shorts"],
                "reasoning": "Medium vertical content for Reels and Shorts"
            },
            {
                "name": "vertical_long_form",
                "condition": "Vertical (9:16) + > 90 seconds",
                "platforms": ["instagram_reels"],
                "reasoning": "Long vertical content for Instagram Reels only"
            },
            {
                "name": "horizontal_short_form",
                "condition": "Horizontal (16:9) + < 60 seconds",
                "platforms": ["youtube_shorts", "facebook"],
                "reasoning": "Short horizontal content for Shorts and Facebook"
            },
            {
                "name": "horizontal_long_form",
                "condition": "Horizontal (16:9) + > 60 seconds",
                "platforms": ["youtube"],
                "reasoning": "Long horizontal content optimal for YouTube main channel"
            },
            {
                "name": "square_format",
                "condition": "Square (1:1) + any duration",
                "platforms": ["instagram_feed", "facebook"],
                "reasoning": "Square format optimal for Instagram Feed and Facebook"
            }
        ],
        "thresholds": {
            "short_form_seconds": 60,
            "medium_form_seconds": 90,
            "vertical_aspect_ratio": 0.75,
            "horizontal_aspect_ratio": 1.33
        }
    }


@router.get("/health")
async def health_check():
    """Check if video routing service is healthy"""
    try:
        analyzer = get_video_analyzer()
        router_service = get_video_router()
        
        return {
            "status": "healthy",
            "services": {
                "video_analyzer": "operational",
                "video_router": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")
