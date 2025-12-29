"""
B-Roll Detection API Endpoints

Endpoints for detecting and managing B-roll footage in the media library.
"""
import os
import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy import create_engine, text
from loguru import logger

from services.broll_detector import BRollDetector, BRollConfidence

router = APIRouter(prefix="/api/broll", tags=["B-Roll Detection"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
    return _engine


@router.get("/detect/{video_id}")
async def detect_broll_single(video_id: str):
    """
    Detect if a single video is B-roll.
    
    Returns B-roll classification and confidence.
    """
    engine = get_engine()
    detector = BRollDetector()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                v.id, v.file_name, v.duration_sec,
                va.transcript, va.visual_analysis, va.transcription_data,
                va.transcription_duration_sec, va.silence_ratio, va.words_per_minute
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE v.id = :video_id
        """), {"video_id": video_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Build analysis dict
        video_data = {
            "video_id": str(result[0]),
            "file_name": result[1],
            "duration_sec": result[2],
            "transcript": result[3],
            "visual_analysis": result[4] if isinstance(result[4], dict) else {},
            "transcription_data": result[5] if isinstance(result[5], dict) else {
                "silence_ratio": result[7],
                "words_per_minute": result[8]
            },
            "transcription_duration_sec": result[6]
        }
        
        # Detect B-roll
        analysis = detector.detect_from_db_record(video_data)
        
        # Update database with B-roll status
        conn.execute(text("""
            UPDATE video_analysis SET
                is_broll = :is_broll,
                broll_confidence = :confidence,
                broll_confidence_score = :score,
                broll_reasons = :reasons,
                broll_visual_type = :visual_type,
                broll_suggested_use = :suggested_use
            WHERE video_id = :video_id
        """), {
            "video_id": video_id,
            "is_broll": analysis.is_broll,
            "confidence": analysis.confidence.value,
            "score": analysis.confidence_score,
            "reasons": json.dumps(analysis.reasons),
            "visual_type": analysis.visual_type,
            "suggested_use": analysis.suggested_use
        })
        conn.commit()
        
        return {
            "video_id": video_data["video_id"],
            "file_name": video_data["file_name"],
            "is_broll": analysis.is_broll,
            "confidence": analysis.confidence.value,
            "confidence_score": analysis.confidence_score,
            "reasons": analysis.reasons,
            "has_speech": analysis.has_speech,
            "has_people": analysis.has_people,
            "people_speaking": analysis.people_speaking,
            "speech_percentage": analysis.speech_percentage,
            "visual_type": analysis.visual_type,
            "suggested_use": analysis.suggested_use
        }


@router.post("/detect-all")
async def detect_broll_all(
    limit: int = Query(100, le=500),
    only_unprocessed: bool = Query(True, description="Only process videos without B-roll status")
):
    """
    Detect B-roll for all videos in the library.
    
    Updates video_analysis records with B-roll classification.
    """
    engine = get_engine()
    detector = BRollDetector()
    
    with engine.connect() as conn:
        # Get videos to process
        where_clause = "AND va.is_broll IS NULL" if only_unprocessed else ""
        
        result = conn.execute(text(f"""
            SELECT 
                v.id, v.file_name, v.duration_sec,
                va.transcript, va.visual_analysis, va.transcription_data,
                va.transcription_duration_sec, va.silence_ratio, va.words_per_minute
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE 1=1
            {where_clause}
            ORDER BY va.analyzed_at DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        processed = 0
        broll_count = 0
        results = []
        
        for row in result:
            video_data = {
                "video_id": str(row[0]),
                "file_name": row[1],
                "duration_sec": row[2],
                "transcript": row[3],
                "visual_analysis": row[4] if isinstance(row[4], dict) else {},
                "transcription_data": row[5] if isinstance(row[5], dict) else {
                    "silence_ratio": row[7],
                    "words_per_minute": row[8]
                },
                "transcription_duration_sec": row[6]
            }
            
            analysis = detector.detect_from_db_record(video_data)
            
            # Update database
            conn.execute(text("""
                UPDATE video_analysis SET
                    is_broll = :is_broll,
                    broll_confidence = :confidence,
                    broll_confidence_score = :score,
                    broll_reasons = :reasons,
                    broll_visual_type = :visual_type,
                    broll_suggested_use = :suggested_use
                WHERE video_id = :video_id
            """), {
                "video_id": video_data["video_id"],
                "is_broll": analysis.is_broll,
                "confidence": analysis.confidence.value,
                "score": analysis.confidence_score,
                "reasons": json.dumps(analysis.reasons),
                "visual_type": analysis.visual_type,
                "suggested_use": analysis.suggested_use
            })
            
            processed += 1
            if analysis.is_broll:
                broll_count += 1
                results.append({
                    "video_id": video_data["video_id"],
                    "file_name": video_data["file_name"],
                    "confidence": analysis.confidence.value,
                    "visual_type": analysis.visual_type
                })
        
        conn.commit()
        
        logger.info(f"[BRoll API] Processed {processed} videos, found {broll_count} B-roll")
        
        return {
            "processed": processed,
            "broll_found": broll_count,
            "broll_percentage": (broll_count / processed * 100) if processed > 0 else 0,
            "broll_videos": results[:20]  # First 20 for preview
        }


@router.get("/list")
async def list_broll_videos(
    limit: int = Query(50, le=200),
    confidence: Optional[str] = Query(None, description="Filter by confidence: definite, high, medium"),
    visual_type: Optional[str] = Query(None, description="Filter by visual type: scenic, action, people"),
    suggested_use: Optional[str] = Query(None, description="Filter by use: overlay, cutaway, supplemental")
):
    """
    List all detected B-roll videos.
    """
    engine = get_engine()
    
    filters = ["va.is_broll = TRUE"]
    params = {"limit": limit}
    
    if confidence:
        filters.append("va.broll_confidence = :confidence")
        params["confidence"] = confidence
    
    if visual_type:
        filters.append("va.broll_visual_type = :visual_type")
        params["visual_type"] = visual_type
    
    if suggested_use:
        filters.append("va.broll_suggested_use = :suggested_use")
        params["suggested_use"] = suggested_use
    
    where_clause = " AND ".join(filters)
    
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT 
                v.id, v.file_name, v.duration_sec, v.thumbnail_path,
                va.is_broll, va.broll_confidence, va.broll_confidence_score,
                va.broll_reasons, va.broll_visual_type, va.broll_suggested_use,
                va.topics, va.pre_social_score
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE {where_clause}
            ORDER BY va.broll_confidence_score DESC
            LIMIT :limit
        """), params).fetchall()
        
        videos = []
        for row in result:
            videos.append({
                "id": str(row[0]),
                "file_name": row[1],
                "duration_sec": row[2],
                "thumbnail_url": f"/api/media-db/thumbnail/{row[0]}" if row[3] else None,
                "is_broll": row[4],
                "confidence": row[5],
                "confidence_score": row[6],
                "reasons": row[7] if isinstance(row[7], list) else [],
                "visual_type": row[8],
                "suggested_use": row[9],
                "topics": row[10] or [],
                "score": row[11]
            })
        
        return {
            "total": len(videos),
            "videos": videos
        }


@router.get("/stats")
async def broll_stats():
    """
    Get B-roll detection statistics.
    """
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_analyzed,
                SUM(CASE WHEN is_broll = TRUE THEN 1 ELSE 0 END) as broll_count,
                SUM(CASE WHEN is_broll = FALSE THEN 1 ELSE 0 END) as non_broll_count,
                SUM(CASE WHEN is_broll IS NULL THEN 1 ELSE 0 END) as unprocessed
            FROM video_analysis
        """)).fetchone()
        
        # Get breakdown by confidence
        confidence_result = conn.execute(text("""
            SELECT broll_confidence, COUNT(*) as count
            FROM video_analysis
            WHERE is_broll = TRUE
            GROUP BY broll_confidence
        """)).fetchall()
        
        # Get breakdown by visual type
        visual_result = conn.execute(text("""
            SELECT broll_visual_type, COUNT(*) as count
            FROM video_analysis
            WHERE is_broll = TRUE
            GROUP BY broll_visual_type
        """)).fetchall()
        
        return {
            "total_analyzed": result[0] or 0,
            "broll_count": result[1] or 0,
            "non_broll_count": result[2] or 0,
            "unprocessed": result[3] or 0,
            "broll_percentage": (result[1] / result[0] * 100) if result[0] else 0,
            "by_confidence": {row[0]: row[1] for row in confidence_result if row[0]},
            "by_visual_type": {row[0]: row[1] for row in visual_result if row[0]}
        }


@router.get("/candidates")
async def get_broll_candidates(
    limit: int = Query(20, le=100),
    for_video_id: Optional[str] = Query(None, description="Get B-roll candidates for a specific video")
):
    """
    Get B-roll candidates for video editing.
    
    If for_video_id is provided, returns B-roll that would complement that video.
    """
    engine = get_engine()
    
    with engine.connect() as conn:
        if for_video_id:
            # Get the main video's topics
            main_video = conn.execute(text("""
                SELECT va.topics FROM video_analysis va WHERE va.video_id = :video_id
            """), {"video_id": for_video_id}).fetchone()
            
            if not main_video or not main_video[0]:
                raise HTTPException(status_code=404, detail="Video not found or has no topics")
            
            topics = main_video[0]
            
            # Find B-roll with matching topics
            result = conn.execute(text("""
                SELECT 
                    v.id, v.file_name, v.duration_sec, v.thumbnail_path,
                    va.broll_confidence, va.broll_visual_type, va.broll_suggested_use,
                    va.topics, va.pre_social_score,
                    (SELECT COUNT(*) FROM unnest(va.topics) t WHERE t = ANY(:topics)) as topic_matches
                FROM videos v
                JOIN video_analysis va ON v.id = va.video_id
                WHERE va.is_broll = TRUE
                AND v.id != :video_id
                ORDER BY topic_matches DESC, va.broll_confidence_score DESC
                LIMIT :limit
            """), {"video_id": for_video_id, "topics": topics, "limit": limit}).fetchall()
        else:
            # Get general B-roll candidates
            result = conn.execute(text("""
                SELECT 
                    v.id, v.file_name, v.duration_sec, v.thumbnail_path,
                    va.broll_confidence, va.broll_visual_type, va.broll_suggested_use,
                    va.topics, va.pre_social_score, 0 as topic_matches
                FROM videos v
                JOIN video_analysis va ON v.id = va.video_id
                WHERE va.is_broll = TRUE
                ORDER BY va.broll_confidence_score DESC, va.pre_social_score DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
        
        candidates = []
        for row in result:
            candidates.append({
                "id": str(row[0]),
                "file_name": row[1],
                "duration_sec": row[2],
                "thumbnail_url": f"/api/media-db/thumbnail/{row[0]}" if row[3] else None,
                "confidence": row[4],
                "visual_type": row[5],
                "suggested_use": row[6],
                "topics": row[7] or [],
                "score": row[8],
                "topic_matches": row[9] if len(row) > 9 else 0
            })
        
        return {
            "for_video_id": for_video_id,
            "candidates": candidates,
            "total": len(candidates)
        }
