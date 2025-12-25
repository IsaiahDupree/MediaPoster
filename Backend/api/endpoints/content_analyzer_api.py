"""
Content Analyzer API Endpoints
AI-powered video analysis with trend matching and recommendations
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from loguru import logger
import tempfile
import os

from services.instagram.content_analyzer import get_content_analyzer

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class AnalyzeRequest(BaseModel):
    video_id: str
    transcript: str
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    duration_sec: Optional[float] = None


class AnalysisJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class RecommendationResponse(BaseModel):
    title: str
    description: str
    priority: str
    category: str


class AnalysisResultResponse(BaseModel):
    job_id: str
    video_id: str
    status: str
    hook_type: Optional[str]
    pacing: Optional[str]
    text_density: Optional[float]
    matched_trend_cards: List[str]
    recommendations: List[Dict]
    error_message: Optional[str]
    created_at: Optional[str]
    completed_at: Optional[str]


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================

@router.post("/analyze")
async def analyze_content(
    background_tasks: BackgroundTasks,
    request: AnalyzeRequest
):
    """
    Analyze video content and generate recommendations.
    
    Performs:
    - Hook type detection
    - Pacing analysis
    - Text density calculation
    - Sentiment analysis
    - Trend matching
    - AI recommendations
    
    Runs in background and returns job ID for status tracking.
    """
    try:
        analyzer = get_content_analyzer()
        
        # Create job ID immediately
        job_id = analyzer._create_analysis_job(request.video_id)
        
        # Run analysis in background
        async def analyze_task():
            try:
                await analyzer.analyze_video(
                    request.video_id,
                    request.transcript,
                    request.caption,
                    request.hashtags,
                    request.duration_sec
                )
            except Exception as e:
                logger.error(f"Background analysis failed: {e}")
        
        background_tasks.add_task(analyze_task)
        
        return AnalysisJobResponse(
            job_id=job_id,
            status="started",
            message="Analysis started in background"
        )
        
    except Exception as e:
        logger.error(f"Failed to start analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/{job_id}")
async def get_analysis_status(job_id: str):
    """
    Get analysis job status and results.
    
    Returns current status and results if completed.
    """
    try:
        analyzer = get_content_analyzer()
        results = analyzer.get_analysis_results(job_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="Analysis job not found")
        
        return AnalysisResultResponse(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/{job_id}/recommendations")
async def get_recommendations(job_id: str):
    """
    Get recommendations for a completed analysis.
    
    Returns list of actionable recommendations.
    """
    try:
        analyzer = get_content_analyzer()
        results = analyzer.get_analysis_results(job_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="Analysis job not found")
        
        if results["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Analysis not completed yet. Status: {results['status']}"
            )
        
        return {
            "job_id": job_id,
            "video_id": results["video_id"],
            "recommendations": results["recommendations"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/quick")
async def quick_analyze(
    transcript: str = Form(...),
    caption: Optional[str] = Form(None),
    hashtags: Optional[str] = Form(None),
    duration_sec: Optional[float] = Form(None)
):
    """
    Quick synchronous analysis without video upload.
    
    Useful for analyzing existing content or testing.
    Returns results immediately (may take 10-30 seconds).
    """
    try:
        import uuid
        video_id = str(uuid.uuid4())
        
        # Parse hashtags
        hashtag_list = []
        if hashtags:
            hashtag_list = [h.strip() for h in hashtags.split(",") if h.strip()]
        
        analyzer = get_content_analyzer()
        results = await analyzer.analyze_video(
            video_id,
            transcript,
            caption,
            hashtag_list,
            duration_sec
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Quick analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/from-media/{media_id}")
async def analyze_from_media(
    background_tasks: BackgroundTasks,
    media_id: str
):
    """
    Analyze content from existing media library.
    
    Fetches transcript and metadata from media_library table.
    """
    try:
        from sqlalchemy import create_engine, text
        
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(DATABASE_URL)
        
        # Fetch media data
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    id, transcript, title, duration_sec
                FROM media_library
                WHERE id = :media_id
            """), {"media_id": media_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="Media not found")
            
            video_id, transcript, caption, duration = result
            
            if not transcript:
                raise HTTPException(
                    status_code=400,
                    detail="Media has no transcript. Run analysis first."
                )
        
        # Start analysis
        analyzer = get_content_analyzer()
        job_id = analyzer._create_analysis_job(str(video_id))
        
        async def analyze_task():
            try:
                await analyzer.analyze_video(
                    str(video_id),
                    transcript,
                    caption,
                    [],
                    duration
                )
            except Exception as e:
                logger.error(f"Analysis from media failed: {e}")
        
        background_tasks.add_task(analyze_task)
        
        return AnalysisJobResponse(
            job_id=job_id,
            status="started",
            message=f"Analyzing media {media_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze from media: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/batch")
async def batch_analyze(
    background_tasks: BackgroundTasks,
    media_ids: List[str]
):
    """
    Analyze multiple videos from media library in batch.
    
    Returns list of job IDs for tracking.
    """
    try:
        analyzer = get_content_analyzer()
        job_ids = []
        
        from sqlalchemy import create_engine, text
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(DATABASE_URL)
        
        async def batch_task():
            for media_id in media_ids:
                try:
                    # Fetch media data
                    with engine.connect() as conn:
                        result = conn.execute(text("""
                            SELECT id, transcript, title, duration_sec
                            FROM media_library
                            WHERE id = :media_id
                        """), {"media_id": media_id}).fetchone()
                        
                        if not result or not result[1]:
                            logger.warning(f"Skipping {media_id}: no transcript")
                            continue
                        
                        video_id, transcript, caption, duration = result
                    
                    # Analyze
                    await analyzer.analyze_video(
                        str(video_id),
                        transcript,
                        caption,
                        [],
                        duration
                    )
                    
                except Exception as e:
                    logger.error(f"Batch analysis failed for {media_id}: {e}")
        
        # Create job IDs
        for media_id in media_ids:
            job_id = analyzer._create_analysis_job(media_id)
            job_ids.append(job_id)
        
        background_tasks.add_task(batch_task)
        
        return {
            "job_ids": job_ids,
            "count": len(job_ids),
            "status": "started",
            "message": f"Analyzing {len(job_ids)} videos in batch"
        }
        
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_analyzer_stats():
    """
    Get content analyzer statistics.
    
    Returns counts of analysis jobs by status.
    """
    try:
        from sqlalchemy import create_engine, text
        import os
        
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Count by status
            result = conn.execute(text("""
                SELECT status, COUNT(*) as count
                FROM ig_analysis_jobs
                GROUP BY status
            """))
            
            status_counts = {row[0]: row[1] for row in result.fetchall()}
            
            # Total count
            total = conn.execute(text("""
                SELECT COUNT(*) FROM ig_analysis_jobs
            """)).scalar()
            
            # Average completion time
            avg_time = conn.execute(text("""
                SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at)))
                FROM ig_analysis_jobs
                WHERE status = 'completed'
                  AND completed_at IS NOT NULL
            """)).scalar()
        
        return {
            "total_jobs": total,
            "pending": status_counts.get("pending", 0),
            "processing": status_counts.get("processing", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
            "avg_completion_time_sec": round(avg_time, 1) if avg_time else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to get analyzer stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
