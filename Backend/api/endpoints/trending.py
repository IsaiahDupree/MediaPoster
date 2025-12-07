"""
API Endpoints for Trending Content Discovery
TikTok trending analysis and content recommendations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from database.connection import get_db
from services.trending_content import TrendingContentService

router = APIRouter()


# ==================== Response Models ====================

class TrendingTopicResponse(BaseModel):
    """Trending topic data"""
    hashtag: str
    video_count: int
    total_views: int
    total_likes: int
    avg_engagement_rate: float


class CompetitorAnalysisResponse(BaseModel):
    """Competitor content analysis"""
    username: str
    total_videos_analyzed: int
    avg_views_per_video: int
    engagement_rate: float
    top_hashtags: List[dict]
    best_performing_videos: List[dict]


class HashtagInsightsResponse(BaseModel):
    """Hashtag performance insights"""
    hashtag: str
    total_videos: int
    avg_views: int
    engagement_rate: float
    best_posting_hour: Optional[int]
    recommendation: str


class ContentIdeaResponse(BaseModel):
    """Content idea suggestion"""
    title: str
    inspiration: dict
    suggested_hashtags: List[str]
    why_trending: str
    action: str


# ==================== Endpoints ====================

@router.get("/trending/topics", response_model=List[TrendingTopicResponse])
async def get_trending_topics(
    region: str = Query("US", description="Region code (US, GB, etc.)"),
    limit: int = Query(50, description="Number of videos to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Discover what's trending on TikTok right now
    
    Analyzes trending videos to identify popular hashtags and topics
    
    Example:
        ```
        GET /api/trending/topics?region=US&limit=50
        ```
    """
    try:
        # Note: TrendingContentService needs async conversion
        # For now, return empty list until service is converted
        from loguru import logger
        logger.warning("TrendingContentService needs async conversion - returning empty list")
        return []
        
        # TODO: Convert TrendingContentService to async
        # service = TrendingContentService(db)
        # topics = await service.discover_trending_topics(
        #     region=region,
        #     limit=limit
        # )
        # return topics
        
    except Exception as e:
        from loguru import logger
        logger.error(f"Error getting trending topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending/competitor/{username}", response_model=CompetitorAnalysisResponse)
async def analyze_competitor(
    username: str,
    count: int = Query(20, description="Number of posts to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a competitor's TikTok content strategy
    
    Returns insights about:
    - Average views and engagement
    - Most used hashtags
    - Best performing content
    
    Example:
        ```
        GET /api/trending/competitor/username?count=20
        ```
    """
    service = TrendingContentService(db)
    
    try:
        analysis = await service.analyze_competitor_content(
            username=username,
            count=count
        )
        
        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending/hashtag/{hashtag}", response_model=HashtagInsightsResponse)
async def get_hashtag_insights(
    hashtag: str,
    count: int = Query(30, description="Number of videos to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed insights about a specific hashtag
    
    Analyzes recent videos using the hashtag to provide:
    - Average performance metrics
    - Best posting times
    - Usage recommendations
    
    Example:
        ```
        GET /api/trending/hashtag/viral?count=30
        ```
    """
    service = TrendingContentService(db)
    
    try:
        insights = await service.get_hashtag_insights(
            hashtag=hashtag,
            count=count
        )
        
        if "error" in insights:
            raise HTTPException(status_code=404, detail=insights["error"])
        
        return insights
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending/ideas", response_model=List[ContentIdeaResponse])
async def generate_content_ideas(
    region: str = Query("US", description="Region code"),
    niche: Optional[str] = Query(None, description="Optional niche filter"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate content ideas based on trending content
    
    Analyzes what's performing well to suggest content ideas
    
    Example:
        ```
        GET /api/trending/ideas?region=US
        ```
    """
    service = TrendingContentService(db)
    
    try:
        ideas = await service.generate_content_ideas(
            region=region,
            niche=niche
        )
        
        return ideas
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending/video/{video_id}")
async def get_video_details(
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific TikTok video
    
    Example:
        ```
        GET /api/trending/video/1234567890
        ```
    """
    service = TrendingContentService(db)
    
    try:
        video_info = await service.tiktok_api.get_video_info(video_id)
        
        if not video_info:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return video_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
