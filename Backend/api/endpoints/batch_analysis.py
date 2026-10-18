"""
Batch Analysis API Endpoints (CUR-001, CUR-002)
================================================
REST API for batch video analysis and sentiment analysis
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel, Field

from services.batch_video_analyzer import get_batch_analyzer
from services.sentiment_analyzer import get_sentiment_analyzer
from loguru import logger


router = APIRouter(prefix="/api/analysis/batch", tags=["Batch Analysis"])


class BatchAnalysisRequest(BaseModel):
    """Request to batch analyze videos"""
    max_videos: Optional[int] = Field(default=None, description="Maximum videos to analyze")


class SentimentBatchRequest(BaseModel):
    """Request to batch analyze sentiment"""
    max_items: Optional[int] = Field(default=None, description="Maximum items to analyze")


@router.post("/analyze-videos")
async def batch_analyze_videos(request: BatchAnalysisRequest):
    """
    Batch analyze all unanalyzed videos

    Processes videos to extract:
    - Transcripts (via Whisper)
    - Visual content analysis (via GPT-4 Vision)
    - Scene descriptions, objects, mood
    - Quality scores

    Progress is tracked via event bus.
    """
    try:
        analyzer = get_batch_analyzer()
        result = await analyzer.analyze_all_unanalyzed(max_videos=request.max_videos)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.error(f"Batch video analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze-sentiment")
async def batch_analyze_sentiment(request: SentimentBatchRequest):
    """
    Batch analyze sentiment for all transcripts

    Scores each transcript on:
    - Sentiment score (-1.0 to +1.0)
    - Sentiment label (negative/neutral/positive)
    - Emotion breakdown
    - Theme extraction

    Uses GPT-4 for accurate sentiment detection.
    """
    try:
        analyzer = get_sentiment_analyzer()
        result = await analyzer.batch_analyze_unscored(max_items=request.max_items)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.error(f"Batch sentiment analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")


@router.get("/video-stats")
async def get_video_analysis_stats():
    """
    Get statistics on video analysis progress

    Returns:
    - Total videos
    - Analyzed count
    - Unanalyzed count
    - Percent complete
    """
    try:
        analyzer = get_batch_analyzer()
        stats = await analyzer.get_analysis_stats()

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        logger.error(f"Failed to get video stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/sentiment-stats")
async def get_sentiment_stats():
    """
    Get statistics on sentiment analysis

    Returns:
    - Total transcripts
    - Scored count
    - Distribution (positive/neutral/negative)
    - Average sentiment score
    """
    try:
        analyzer = get_sentiment_analyzer()
        stats = await analyzer.get_sentiment_stats()

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        logger.error(f"Failed to get sentiment stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/unanalyzed-videos")
async def get_unanalyzed_videos(
    limit: int = Query(default=100, ge=1, le=1000, description="Max videos to return")
):
    """
    Get list of unanalyzed videos

    Returns basic info for videos that haven't been analyzed yet.
    """
    try:
        analyzer = get_batch_analyzer()
        videos = await analyzer.get_unanalyzed_videos(limit=limit)

        video_info = [
            {
                'id': str(v.id),
                'filename': v.filename,
                'media_type': v.media_type,
                'duration_seconds': v.duration_seconds,
                'created_at': v.created_at.isoformat() if v.created_at else None
            }
            for v in videos
        ]

        return {
            "success": True,
            "count": len(video_info),
            "videos": video_info
        }

    except Exception as e:
        logger.error(f"Failed to get unanalyzed videos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get videos: {str(e)}")


@router.post("/analyze-single/{media_id}")
async def analyze_single_video(media_id: str):
    """
    Analyze a single video by ID

    Useful for re-analyzing or analyzing a specific video on demand.
    """
    try:
        from database.connection import get_db_context
        from database.models import MediaLibrary

        async with get_db_context() as db:
            media = await db.get(MediaLibrary, media_id)

            if not media:
                raise HTTPException(status_code=404, detail="Media not found")

            analyzer = get_batch_analyzer()
            result = await analyzer.analyze_video(media, db)

            return {
                "success": True,
                **result
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single video analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
