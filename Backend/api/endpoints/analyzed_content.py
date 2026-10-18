"""
Analyzed Content API
Fetch analyzed/curated videos for scheduling
"""
from fastapi import APIRouter, Query
from sqlalchemy import create_engine, text
from typing import Optional, List
import os

from services.event_bus import EventBus, Topics

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


@router.get("/list")
async def list_analyzed_content(
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    min_score: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="Filter by curation_status: approved, pending, rejected"),
    media_type: Optional[str] = Query(None, description="Filter by media type: video, image"),
    sort_by: str = Query("score", description="score, date, duration")
):
    """
    List analyzed videos with scores for scheduling.
    Returns videos that have been analyzed with their pre_social_score.
    """
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Build query
        where_clauses = ["va.video_id IS NOT NULL"]
        params = {"limit": limit, "offset": offset}
        
        if min_score is not None:
            where_clauses.append("va.pre_social_score >= :min_score")
            params["min_score"] = min_score
        
        if status:
            where_clauses.append("v.curation_status = :status")
            params["status"] = status
        
        # Filter by media type based on file extension
        if media_type == "video":
            where_clauses.append("LOWER(v.file_name) ~ '\\.(mov|mp4|avi|mkv|webm|m4v)$'")
        elif media_type == "image":
            where_clauses.append("LOWER(v.file_name) ~ '\\.(jpg|jpeg|png|gif|heic|webp|bmp)$'")
        
        where_sql = " AND ".join(where_clauses)
        
        # Sort order
        order_sql = "va.pre_social_score DESC NULLS LAST"
        if sort_by == "date":
            order_sql = "va.analyzed_at DESC NULLS LAST"
        elif sort_by == "duration":
            order_sql = "v.duration_sec DESC NULLS LAST"
        
        # Main query - include all analysis fields
        result = conn.execute(text(f"""
            SELECT 
                v.id,
                v.file_name,
                v.duration_sec,
                v.thumbnail_path,
                va.pre_social_score,
                va.analyzed_at,
                va.hooks,
                va.topics,
                va.transcript,
                va.tone,
                va.pacing,
                va.key_moments
            FROM videos v
            INNER JOIN video_analysis va ON v.id = va.video_id
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT :limit OFFSET :offset
        """), params).fetchall()
        
        # Get total count
        count_result = conn.execute(text(f"""
            SELECT COUNT(*)
            FROM videos v
            INNER JOIN video_analysis va ON v.id = va.video_id
            WHERE {where_sql}
        """), params).scalar()
        
        # Get stats
        stats = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE v.curation_status = 'approved') as approved,
                COUNT(*) FILTER (WHERE v.curation_status = 'pending' OR v.curation_status IS NULL) as pending,
                AVG(va.pre_social_score) as avg_score
            FROM videos v
            INNER JOIN video_analysis va ON v.id = va.video_id
        """)).fetchone()
        
        items = []
        for i, row in enumerate(result, offset + 1):
            # Convert thumbnail path to static URL
            thumb_path = row[3]
            if thumb_path and thumb_path.startswith("/tmp/mediaposter/thumbnails/"):
                thumb_filename = thumb_path.split("/")[-1]
                thumb_path = f"/thumbnails/{thumb_filename}"
            
            items.append({
                "id": str(row[0]),
                "index": i,
                "title": row[1] or "Untitled",
                "duration_sec": row[2],
                "thumbnail_path": thumb_path,
                "score": int(row[4]) if row[4] else None,
                "analyzed_at": str(row[5]) if row[5] else None,
                "hooks": row[6] if row[6] else [],
                "topics": row[7] if row[7] else [],
                "transcript": row[8] if row[8] else None,
                "tone": row[9] if row[9] else None,
                "pacing": row[10] if row[10] else None,
                "key_moments": row[11] if row[11] else [],
                "scheduled_count": 0,  # TODO: join with scheduled_posts
            })
        
        return {
            "items": items,
            "total": count_result,
            "stats": {
                "total_analyzed": stats[0] if stats else 0,
                "approved": stats[1] if stats else 0,
                "pending": stats[2] if stats else 0,
                "avg_score": round(stats[3], 1) if stats and stats[3] else 0,
            },
            "limit": limit,
            "offset": offset
        }


@router.get("/top")
async def get_top_content(limit: int = Query(20, le=50)):
    """Get top scoring analyzed content for quick scheduling"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                v.id,
                v.file_name,
                v.duration_sec,
                v.thumbnail_path,
                va.pre_social_score,
                va.hooks
            FROM videos v
            INNER JOIN video_analysis va ON v.id = va.video_id
            WHERE va.pre_social_score >= 80
            ORDER BY va.pre_social_score DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        items = []
        for i, row in enumerate(result, 1):
            items.append({
                "id": str(row[0]),
                "index": i,
                "title": row[1] or "Untitled",
                "duration_sec": row[2],
                "thumbnail_path": row[3],
                "score": int(row[4]) if row[4] else None,
                "hooks": row[5] if row[5] else [],
            })
        
        return {"items": items, "total": len(items)}
