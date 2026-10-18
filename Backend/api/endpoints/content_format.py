"""
Content Format Detection API Endpoints

Comprehensive content format classification for videos.
"""
import os
import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy import create_engine, text
from loguru import logger

from services.format_detector import FormatDetector, ContentFormat

router = APIRouter(prefix="/api/content-format", tags=["Content Format Detection"])

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
async def detect_format_single(video_id: str):
    """
    Detect content format for a single video.
    
    Returns comprehensive format classification.
    """
    engine = get_engine()
    detector = FormatDetector()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                v.id, v.file_name, v.duration_sec,
                va.transcript, va.visual_analysis, va.transcription_data,
                va.transcription_duration_sec, va.topics, va.tone,
                va.is_broll, va.broll_visual_type
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
            "transcription_data": result[5] if isinstance(result[5], dict) else {},
            "transcription_duration_sec": result[6],
            "topics": result[7] or [],
            "tone": result[8],
            "is_broll": result[9],
            "broll_visual_type": result[10]
        }
        
        # Detect format
        analysis = detector.detect_from_db_record(video_data)
        
        # Update database with format data
        conn.execute(text("""
            UPDATE video_analysis SET
                content_format = :format,
                format_confidence = :confidence,
                format_secondary = :secondary,
                format_attributes = :attributes,
                format_best_platforms = :platforms,
                format_suggested_use = :suggested_use
            WHERE video_id = :video_id
        """), {
            "video_id": video_id,
            "format": analysis.primary_format.value,
            "confidence": analysis.confidence,
            "secondary": json.dumps([f.value for f in analysis.secondary_formats]),
            "attributes": json.dumps({
                "has_speech": analysis.has_speech,
                "has_music": analysis.has_music,
                "has_voiceover": analysis.has_voiceover,
                "has_captions": analysis.has_captions,
                "has_text_overlay": analysis.has_text_overlay,
                "has_people": analysis.has_people,
                "people_speaking": analysis.people_speaking,
                "people_count": analysis.people_count_estimate,
                "duration_category": analysis.duration_category,
                "production_quality": analysis.production_quality.value,
                "reasons": analysis.reasons
            }),
            "platforms": json.dumps(analysis.best_platforms),
            "suggested_use": analysis.suggested_use
        })
        conn.commit()
        
        return {
            "video_id": video_data["video_id"],
            "file_name": video_data["file_name"],
            "primary_format": analysis.primary_format.value,
            "confidence": analysis.confidence,
            "secondary_formats": [f.value for f in analysis.secondary_formats],
            "attributes": {
                "has_speech": analysis.has_speech,
                "has_music": analysis.has_music,
                "has_voiceover": analysis.has_voiceover,
                "has_captions": analysis.has_captions,
                "has_text_overlay": analysis.has_text_overlay,
                "has_people": analysis.has_people,
                "people_speaking": analysis.people_speaking,
                "people_count": analysis.people_count_estimate,
            },
            "duration_category": analysis.duration_category,
            "production_quality": analysis.production_quality.value,
            "best_platforms": analysis.best_platforms,
            "suggested_use": analysis.suggested_use,
            "reasons": analysis.reasons
        }


@router.post("/detect-all")
async def detect_format_all(
    limit: int = Query(200, le=1000),
    only_unprocessed: bool = Query(True)
):
    """
    Detect content format for all videos.
    
    Updates video_analysis records with format classification.
    """
    engine = get_engine()
    detector = FormatDetector()
    
    with engine.connect() as conn:
        where_clause = "AND va.content_format IS NULL" if only_unprocessed else ""
        
        result = conn.execute(text(f"""
            SELECT 
                v.id, v.file_name, v.duration_sec,
                va.transcript, va.visual_analysis, va.transcription_data,
                va.transcription_duration_sec, va.topics, va.tone,
                va.is_broll, va.broll_visual_type
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE 1=1
            {where_clause}
            ORDER BY va.analyzed_at DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        processed = 0
        format_counts: Dict[str, int] = {}
        
        for row in result:
            video_data = {
                "video_id": str(row[0]),
                "file_name": row[1],
                "duration_sec": row[2],
                "transcript": row[3],
                "visual_analysis": row[4] if isinstance(row[4], dict) else {},
                "transcription_data": row[5] if isinstance(row[5], dict) else {},
                "transcription_duration_sec": row[6],
                "topics": row[7] or [],
                "tone": row[8],
                "is_broll": row[9],
                "broll_visual_type": row[10]
            }
            
            analysis = detector.detect_from_db_record(video_data)
            
            # Update database
            conn.execute(text("""
                UPDATE video_analysis SET
                    content_format = :format,
                    format_confidence = :confidence,
                    format_secondary = :secondary,
                    format_attributes = :attributes,
                    format_best_platforms = :platforms,
                    format_suggested_use = :suggested_use
                WHERE video_id = :video_id
            """), {
                "video_id": video_data["video_id"],
                "format": analysis.primary_format.value,
                "confidence": analysis.confidence,
                "secondary": json.dumps([f.value for f in analysis.secondary_formats]),
                "attributes": json.dumps({
                    "has_speech": analysis.has_speech,
                    "has_music": analysis.has_music,
                    "has_people": analysis.has_people,
                    "people_speaking": analysis.people_speaking,
                    "duration_category": analysis.duration_category,
                    "reasons": analysis.reasons
                }),
                "platforms": json.dumps(analysis.best_platforms),
                "suggested_use": analysis.suggested_use
            })
            
            processed += 1
            fmt = analysis.primary_format.value
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        
        conn.commit()
        
        logger.info(f"[FormatAPI] Processed {processed} videos")
        
        return {
            "processed": processed,
            "format_distribution": format_counts
        }


@router.get("/list")
async def list_by_format(
    format_type: Optional[str] = Query(None, description="Filter by format type"),
    limit: int = Query(50, le=200)
):
    """
    List videos by content format.
    """
    engine = get_engine()
    
    filters = ["va.content_format IS NOT NULL"]
    params = {"limit": limit}
    
    if format_type:
        filters.append("va.content_format = :format_type")
        params["format_type"] = format_type
    
    where_clause = " AND ".join(filters)
    
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT 
                v.id, v.file_name, v.duration_sec, v.thumbnail_path,
                va.content_format, va.format_confidence, va.format_secondary,
                va.format_attributes, va.format_best_platforms, va.format_suggested_use,
                va.pre_social_score, va.topics
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE {where_clause}
            ORDER BY va.format_confidence DESC, va.pre_social_score DESC
            LIMIT :limit
        """), params).fetchall()
        
        videos = []
        for row in result:
            attrs = row[7] if isinstance(row[7], dict) else {}
            videos.append({
                "id": str(row[0]),
                "file_name": row[1],
                "duration_sec": row[2],
                "thumbnail_url": f"/api/media-db/thumbnail/{row[0]}" if row[3] else None,
                "format": row[4],
                "confidence": row[5],
                "secondary_formats": row[6] if isinstance(row[6], list) else [],
                "has_speech": attrs.get("has_speech", False),
                "has_people": attrs.get("has_people", False),
                "best_platforms": row[8] if isinstance(row[8], list) else [],
                "suggested_use": row[9],
                "score": row[10],
                "topics": row[11] or []
            })
        
        return {
            "total": len(videos),
            "format_type": format_type,
            "videos": videos
        }


@router.get("/stats")
async def format_stats():
    """
    Get content format statistics.
    """
    engine = get_engine()
    
    with engine.connect() as conn:
        # Overall stats
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN content_format IS NOT NULL THEN 1 ELSE 0 END) as processed,
                SUM(CASE WHEN content_format IS NULL THEN 1 ELSE 0 END) as unprocessed
            FROM video_analysis
        """)).fetchone()
        
        # By format
        format_result = conn.execute(text("""
            SELECT content_format, COUNT(*) as count, AVG(format_confidence) as avg_confidence
            FROM video_analysis
            WHERE content_format IS NOT NULL
            GROUP BY content_format
            ORDER BY count DESC
        """)).fetchall()
        
        # By suggested use
        use_result = conn.execute(text("""
            SELECT format_suggested_use, COUNT(*) as count
            FROM video_analysis
            WHERE format_suggested_use IS NOT NULL
            GROUP BY format_suggested_use
        """)).fetchall()
        
        return {
            "total_videos": result[0] or 0,
            "processed": result[1] or 0,
            "unprocessed": result[2] or 0,
            "by_format": {
                row[0]: {"count": row[1], "avg_confidence": float(row[2]) if row[2] else 0}
                for row in format_result if row[0]
            },
            "by_suggested_use": {row[0]: row[1] for row in use_result if row[0]}
        }


@router.get("/formats")
async def list_format_types():
    """
    List all available content format types.
    """
    formats = [
        {"value": "talking_head", "label": "Talking Head", "description": "Person speaking directly to camera"},
        {"value": "interview", "label": "Interview", "description": "Two or more people in conversation"},
        {"value": "broll_scenic", "label": "B-Roll (Scenic)", "description": "Environmental/landscape footage"},
        {"value": "broll_action", "label": "B-Roll (Action)", "description": "Movement/action footage"},
        {"value": "broll_people", "label": "B-Roll (People)", "description": "People present but not speaking"},
        {"value": "animated", "label": "Animated", "description": "Animation or motion graphics"},
        {"value": "screen_recording", "label": "Screen Recording", "description": "Software demo or gameplay"},
        {"value": "music_video", "label": "Music Video", "description": "Music-focused content"},
        {"value": "montage", "label": "Montage", "description": "Quick cuts with music"},
        {"value": "documentary", "label": "Documentary", "description": "Narrated/voiceover content"},
        {"value": "tutorial_hands", "label": "Tutorial (Hands-on)", "description": "Hands-on demonstration"},
        {"value": "live_event", "label": "Live Event", "description": "Concert, sports, performance"},
        {"value": "meme_content", "label": "Meme Content", "description": "Viral/meme style"},
        {"value": "reaction", "label": "Reaction", "description": "Reacting to other content"},
    ]
    return {"formats": formats}
