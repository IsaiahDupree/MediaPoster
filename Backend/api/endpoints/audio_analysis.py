"""
Audio Analysis API Endpoints
Detect background music and audio characteristics in video content.
Part of Background Music Detection feature (Phase 1)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database.connection import get_db
from services.audio_analyzer import get_audio_analyzer, AudioAnalysisResult

router = APIRouter(prefix="/api/analysis/audio", tags=["Audio Analysis"])


class AudioAnalysisResponse(BaseModel):
    """Response model for audio analysis"""
    success: bool
    media_id: str
    has_background_music: Optional[bool] = None
    audio_type: Optional[str] = None
    confidence: Optional[float] = None
    music_confidence: Optional[float] = None
    speech_ratio: Optional[float] = None
    music_characteristics: Optional[Dict[str, Any]] = None
    copyright_risk: Optional[str] = None
    duration_sec: Optional[float] = None
    error: Optional[str] = None


@router.get("/health")
async def health_check():
    """Health check for audio analysis service"""
    analyzer = get_audio_analyzer()
    return {
        "status": "healthy",
        "service": "audio_analysis",
        "librosa_available": analyzer is not None
    }


class BatchAnalysisRequest(BaseModel):
    """Request for batch audio analysis"""
    media_ids: List[str] = []


# NOTE: /batch MUST be defined BEFORE /{media_id} for route matching to work correctly
@router.post("/batch")
async def analyze_audio_batch(
    request: BatchAnalysisRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Analyze audio for multiple videos.
    Returns summary of results.
    """
    media_ids = request.media_ids
    
    if not media_ids:
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "results": {},
            "message": "No media IDs provided"
        }
    
    results = {
        "total": len(media_ids),
        "success": 0,
        "failed": 0,
        "results": {}
    }
    
    for media_id in media_ids:
        try:
            response = await analyze_audio_single(media_id, db)
            results["results"][media_id] = {
                "success": response.success,
                "has_music": response.has_background_music,
                "audio_type": response.audio_type
            }
            if response.success:
                results["success"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            results["results"][media_id] = {
                "success": False,
                "error": str(e)
            }
            results["failed"] += 1
    
    return results


@router.post("/analyze/{media_id}")
async def analyze_audio_single(
    media_id: str,
    db: AsyncSession = Depends(get_db)
) -> AudioAnalysisResponse:
    """
    Analyze audio content of a video for background music detection.
    
    This endpoint:
    1. Fetches the video file path from database
    2. Extracts and analyzes the audio track
    3. Stores results in video_analysis table
    4. Returns music detection results
    """
    logger.info(f"[AudioAnalysis] Starting audio analysis for media_id: {media_id}")
    
    # Fetch video path from database
    try:
        result = await db.execute(text("""
            SELECT id, source_uri, file_name 
            FROM videos 
            WHERE id = CAST(:media_id AS uuid)
        """), {"media_id": media_id})
        video = result.fetchone()
        
        if not video:
            raise HTTPException(status_code=404, detail=f"Video not found: {media_id}")
        
        video_path = video[1]  # source_uri
        if not video_path:
            raise HTTPException(status_code=400, detail="Video has no source_uri")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AudioAnalysis] Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Run audio analysis
    analyzer = get_audio_analyzer()
    analysis_result = await analyzer.analyze_video_audio(video_path)
    
    if analysis_result.error:
        logger.error(f"[AudioAnalysis] Analysis failed: {analysis_result.error}")
        return AudioAnalysisResponse(
            success=False,
            media_id=media_id,
            error=analysis_result.error
        )
    
    # Store results in database
    try:
        await db.execute(text("""
            UPDATE video_analysis SET
                audio_analysis = :audio_analysis,
                has_background_music = :has_music,
                audio_type = :audio_type,
                music_confidence = :music_confidence,
                speech_ratio = :speech_ratio,
                music_characteristics = :music_chars,
                copyright_risk = :copyright_risk,
                audio_analyzed_at = NOW()
            WHERE video_id = CAST(:media_id AS uuid)
        """), {
            "media_id": media_id,
            "audio_analysis": analysis_result.to_dict(),
            "has_music": analysis_result.has_music,
            "audio_type": analysis_result.audio_type,
            "music_confidence": analysis_result.music_confidence,
            "speech_ratio": analysis_result.speech_ratio,
            "music_chars": analysis_result.music_characteristics,
            "copyright_risk": analysis_result.copyright_risk
        })
        await db.commit()
        logger.info(f"[AudioAnalysis] Results stored for {media_id}")
        
    except Exception as e:
        logger.warning(f"[AudioAnalysis] Failed to store results: {e}")
        # Don't fail the request, just log warning
    
    return AudioAnalysisResponse(
        success=True,
        media_id=media_id,
        has_background_music=analysis_result.has_music,
        audio_type=analysis_result.audio_type,
        confidence=analysis_result.confidence,
        music_confidence=analysis_result.music_confidence,
        speech_ratio=analysis_result.speech_ratio,
        music_characteristics=analysis_result.music_characteristics,
        copyright_risk=analysis_result.copyright_risk,
        duration_sec=analysis_result.duration_sec
    )


# NOTE: /list MUST be defined BEFORE /{media_id} for route matching to work correctly
@router.get("/list")
async def list_analyzed_media(
    limit: int = 50,
    offset: int = 0,
    has_music: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List media that have been analyzed for audio.
    Optionally filter by has_background_music status.
    """
    try:
        # Build query
        query = """
            SELECT 
                va.video_id,
                v.file_name,
                va.has_background_music,
                va.audio_type,
                va.music_confidence,
                va.copyright_risk,
                va.audio_analyzed_at
            FROM video_analysis va
            JOIN videos v ON v.id = va.video_id
            WHERE va.audio_analyzed_at IS NOT NULL
        """
        params = {"limit": limit, "offset": offset}
        
        if has_music is not None:
            query += " AND va.has_background_music = :has_music"
            params["has_music"] = has_music
        
        query += " ORDER BY va.audio_analyzed_at DESC LIMIT :limit OFFSET :offset"
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "media_id": str(row[0]),
                "file_name": row[1],
                "has_background_music": row[2],
                "audio_type": row[3],
                "music_confidence": float(row[4]) if row[4] else None,
                "copyright_risk": row[5],
                "analyzed_at": row[6].isoformat() if row[6] else None
            })
        
        return {
            "items": items,
            "total": len(items),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"[AudioAnalysis] Failed to list analyzed media: {e}")
        return {
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "error": str(e)
        }


@router.get("/{media_id}")
async def get_audio_analysis(
    media_id: str,
    db: AsyncSession = Depends(get_db)
) -> AudioAnalysisResponse:
    """
    Get existing audio analysis results for a video.
    Returns cached results if available, otherwise returns empty response.
    """
    try:
        result = await db.execute(text("""
            SELECT 
                audio_analysis,
                has_background_music,
                audio_type,
                music_confidence,
                speech_ratio,
                music_characteristics,
                copyright_risk,
                audio_analyzed_at
            FROM video_analysis 
            WHERE video_id = CAST(:media_id AS uuid)
        """), {"media_id": media_id})
        row = result.fetchone()
        
        if not row or row[0] is None:
            return AudioAnalysisResponse(
                success=True,
                media_id=media_id,
                error="No audio analysis available. Run POST to analyze."
            )
        
        audio_analysis = row[0] or {}
        
        return AudioAnalysisResponse(
            success=True,
            media_id=media_id,
            has_background_music=row[1],
            audio_type=row[2],
            confidence=audio_analysis.get("confidence"),
            music_confidence=float(row[3]) if row[3] else None,
            speech_ratio=float(row[4]) if row[4] else None,
            music_characteristics=row[5],
            copyright_risk=row[6],
            duration_sec=audio_analysis.get("duration_sec")
        )
        
    except Exception as e:
        logger.error(f"[AudioAnalysis] Failed to get analysis: {e}")
        return AudioAnalysisResponse(
            success=False,
            media_id=media_id,
            error=f"Failed to retrieve analysis: {str(e)}"
        )


