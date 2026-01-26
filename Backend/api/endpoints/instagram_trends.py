"""
Instagram Trends Feed API (IG-TREND-001)
========================================
Regional trending content, sounds, hashtags with velocity metrics.

Endpoints:
- GET /api/instagram-trends/feed - Complete trends feed
- GET /api/instagram-trends/hashtags - Trending hashtags
- GET /api/instagram-trends/sounds - Trending sounds
- GET /api/instagram-trends/formats - Trending content formats
- GET /api/instagram-trends/search - Search trending hashtags
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from loguru import logger

from services.trend_intelligence import (
    get_instagram_trends_service,
    Region,
    TrendingHashtag,
    TrendingSound,
    TrendingFormat,
    InstagramTrendsFeed
)

router = APIRouter(prefix="/api/instagram-trends", tags=["Instagram Trends"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class HashtagResponse(BaseModel):
    """Trending hashtag response"""
    tag: str
    media_count: int
    velocity_1d: float
    velocity_7d: float
    acceleration: float
    trending_score: float
    region: str
    discovered_at: datetime


class SoundResponse(BaseModel):
    """Trending sound response"""
    audio_id: str
    title: str
    artist: Optional[str]
    usage_count: int
    velocity_1d: float
    velocity_7d: float
    acceleration: float
    trending_score: float
    region: str
    discovered_at: datetime


class FormatResponse(BaseModel):
    """Trending format response"""
    format_id: str
    format_name: str
    description: str
    example_count: int
    velocity_7d: float
    trending_score: float
    region: str
    discovered_at: datetime


class TrendsFeedResponse(BaseModel):
    """Complete trends feed response"""
    hashtags: List[HashtagResponse]
    sounds: List[SoundResponse]
    formats: List[FormatResponse]
    region: str
    generated_at: datetime
    next_refresh: datetime


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/feed", response_model=TrendsFeedResponse)
async def get_trends_feed(
    region: str = Query("US", description="Region code (US, UK, EU, GLOBAL)"),
    hashtag_limit: int = Query(20, ge=1, le=100, description="Number of trending hashtags"),
    sound_limit: int = Query(15, ge=1, le=50, description="Number of trending sounds"),
    format_limit: int = Query(10, ge=1, le=20, description="Number of trending formats"),
    force_refresh: bool = Query(False, description="Force cache refresh")
):
    """
    Get complete Instagram trends feed (IG-TREND-001)

    Returns trending hashtags, sounds, and formats with velocity metrics.

    **Velocity Metrics:**
    - `velocity_1d`: 1-day growth rate (%)
    - `velocity_7d`: 7-day growth rate (%)
    - `acceleration`: Rate of velocity change (positive = speeding up)
    - `trending_score`: Weighted score combining count, velocity, and acceleration

    **Regions:**
    - US: United States
    - UK: United Kingdom
    - EU: European Union
    - GLOBAL: Worldwide trends
    """
    try:
        # Parse region
        try:
            region_enum = Region[region.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid region: {region}. Valid: US, UK, EU, GLOBAL"
            )

        service = get_instagram_trends_service()

        feed = await service.get_trends_feed(
            region=region_enum,
            hashtag_limit=hashtag_limit,
            sound_limit=sound_limit,
            format_limit=format_limit,
            force_refresh=force_refresh
        )

        # Convert to response model
        return TrendsFeedResponse(
            hashtags=[HashtagResponse(**h.__dict__) for h in feed.hashtags],
            sounds=[SoundResponse(**s.__dict__) for s in feed.sounds],
            formats=[FormatResponse(**f.__dict__) for f in feed.formats],
            region=feed.region,
            generated_at=feed.generated_at,
            next_refresh=feed.next_refresh
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trends feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hashtags", response_model=List[HashtagResponse])
async def get_trending_hashtags(
    region: str = Query("US", description="Region code"),
    limit: int = Query(20, ge=1, le=100, description="Number of results")
):
    """
    Get trending hashtags with velocity metrics

    Returns hashtags sorted by trending_score (combination of count, velocity, and acceleration).
    """
    try:
        region_enum = Region[region.upper()]
        service = get_instagram_trends_service()

        hashtags = await service.get_trending_hashtags(
            region=region_enum,
            limit=limit
        )

        return [HashtagResponse(**h.__dict__) for h in hashtags]

    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid region: {region}. Valid: US, UK, EU, GLOBAL"
        )
    except Exception as e:
        logger.error(f"Error fetching trending hashtags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sounds", response_model=List[SoundResponse])
async def get_trending_sounds(
    region: str = Query("US", description="Region code"),
    limit: int = Query(15, ge=1, le=50, description="Number of results")
):
    """
    Get trending sounds/music with velocity metrics

    Returns sounds sorted by trending_score.
    """
    try:
        region_enum = Region[region.upper()]
        service = get_instagram_trends_service()

        sounds = await service.get_trending_sounds(
            region=region_enum,
            limit=limit
        )

        return [SoundResponse(**s.__dict__) for s in sounds]

    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid region: {region}. Valid: US, UK, EU, GLOBAL"
        )
    except Exception as e:
        logger.error(f"Error fetching trending sounds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats", response_model=List[FormatResponse])
async def get_trending_formats(
    region: str = Query("US", description="Region code"),
    limit: int = Query(10, ge=1, le=20, description="Number of results")
):
    """
    Get trending content formats

    Returns popular content format patterns (e.g., "Text-on-Screen Hook", "Overhead Grab POV").
    """
    try:
        region_enum = Region[region.upper()]
        service = get_instagram_trends_service()

        formats = await service.get_trending_formats(
            region=region_enum,
            limit=limit
        )

        return [FormatResponse(**f.__dict__) for f in formats]

    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid region: {region}. Valid: US, UK, EU, GLOBAL"
        )
    except Exception as e:
        logger.error(f"Error fetching trending formats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[HashtagResponse])
async def search_trending_hashtags(
    query: str = Query(..., description="Search query (hashtag partial match)"),
    region: str = Query("US", description="Region code"),
    limit: int = Query(10, ge=1, le=50, description="Number of results")
):
    """
    Search for specific trending hashtags

    Searches within currently trending hashtags for matches.
    """
    try:
        region_enum = Region[region.upper()]
        service = get_instagram_trends_service()

        hashtags = await service.search_trending_hashtags(
            query=query,
            region=region_enum,
            limit=limit
        )

        return [HashtagResponse(**h.__dict__) for h in hashtags]

    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid region: {region}. Valid: US, UK, EU, GLOBAL"
        )
    except Exception as e:
        logger.error(f"Error searching trending hashtags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-cache")
async def clear_trends_cache():
    """
    Clear the trends cache (force refresh on next request)

    Useful for debugging or when you need immediate fresh data.
    """
    try:
        service = get_instagram_trends_service()
        service.clear_cache()

        return {
            "success": True,
            "message": "Trends cache cleared"
        }

    except Exception as e:
        logger.error(f"Error clearing trends cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def instagram_trends_health():
    """Health check for Instagram trends service"""
    try:
        service = get_instagram_trends_service()

        return {
            "success": True,
            "service": "instagram_trends",
            "status": "operational",
            "cache_size": len(service._cache)
        }

    except Exception as e:
        logger.error(f"Instagram trends health check failed: {e}")
        return {
            "success": False,
            "service": "instagram_trends",
            "status": "error",
            "error": str(e)
        }
