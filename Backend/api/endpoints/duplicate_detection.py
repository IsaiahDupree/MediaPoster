"""
Duplicate Detection API Endpoints
Find and manage duplicate videos based on transcript similarity
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from loguru import logger

from database.connection import get_db
from services.duplicate_detector import DuplicateDetector, DuplicatePair

router = APIRouter(prefix="/api/duplicates", tags=["Duplicate Detection"])


class DuplicatePairResponse(BaseModel):
    video1: Dict[str, Any]
    video2: Dict[str, Any]
    similarity_score: float
    transcript_preview: str
    recommendation: str


class DuplicateListResponse(BaseModel):
    total_pairs: int
    duplicates: List[DuplicatePairResponse]
    message: str


class DeleteRequest(BaseModel):
    video_ids: List[str]
    soft_delete: bool = True  # Soft delete by default (marks as deleted, doesn't remove)


@router.get("/find", response_model=DuplicateListResponse)
async def find_duplicate_videos(
    db: AsyncSession = Depends(get_db),
    similarity_threshold: float = Query(default=0.85, ge=0.5, le=1.0, description="Minimum similarity (0.5-1.0)"),
    limit: int = Query(default=50, le=200, description="Max pairs to return"),
    min_transcript_length: int = Query(default=50, description="Min transcript chars"),
    compare_same_caption_status: bool = Query(default=True, description="Only compare videos with same caption status"),
):
    """
    Find videos with similar transcripts that may be duplicates.
    
    Returns pairs of videos with:
    - Similarity score (0-1)
    - Recommendation on which to keep
    - Preview of the transcript
    
    **Protection**: By default, only compares videos with the same caption status
    (both have captions, or both don't) to avoid false positives.
    """
    detector = DuplicateDetector(db)
    
    try:
        duplicates = await detector.find_duplicates(
            similarity_threshold=similarity_threshold,
            min_transcript_length=min_transcript_length,
            limit=limit,
            compare_same_caption_status_only=compare_same_caption_status,
        )
        
        return DuplicateListResponse(
            total_pairs=len(duplicates),
            duplicates=[d.to_dict() for d in duplicates],
            message=f"Found {len(duplicates)} potential duplicate pairs with {similarity_threshold:.0%}+ similarity"
        )
    except Exception as e:
        logger.error(f"Error finding duplicates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exact", response_model=DuplicateListResponse)
async def find_exact_duplicates(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=200),
):
    """
    Find videos with exactly matching transcripts (99%+ similarity).
    These are almost certainly duplicates.
    """
    detector = DuplicateDetector(db)
    
    try:
        duplicates = await detector.find_exact_duplicates(limit=limit)
        
        return DuplicateListResponse(
            total_pairs=len(duplicates),
            duplicates=[d.to_dict() for d in duplicates],
            message=f"Found {len(duplicates)} exact duplicate pairs (99%+ match)"
        )
    except Exception as e:
        logger.error(f"Error finding exact duplicates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_duplicate_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get a summary of potential duplicates in the library.
    """
    detector = DuplicateDetector(db)
    
    try:
        # Find at different thresholds
        exact = await detector.find_duplicates(similarity_threshold=0.99, limit=100)
        high = await detector.find_duplicates(similarity_threshold=0.90, limit=100)
        medium = await detector.find_duplicates(similarity_threshold=0.80, limit=100)
        
        # Calculate potential storage savings (rough estimate)
        # Assume average video is ~50MB
        exact_savings_mb = len(exact) * 50
        
        return {
            "summary": {
                "exact_matches": len(exact),
                "high_similarity": len(high),
                "medium_similarity": len(medium),
            },
            "estimated_savings_mb": exact_savings_mb,
            "recommendations": {
                "safe_to_delete": len(exact),
                "review_recommended": len(high) - len(exact),
            },
            "message": f"Found {len(exact)} exact duplicates that are safe to delete"
        }
    except Exception as e:
        logger.error(f"Error getting duplicate summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-for-deletion")
async def mark_videos_for_deletion(
    request: DeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark videos for deletion (soft delete).
    Does NOT actually delete files - just marks them in the database.
    """
    try:
        marked = []
        for video_id in request.video_ids:
            # Update curation_status to 'duplicate_to_delete'
            await db.execute(
                text("""
                    UPDATE video_analysis 
                    SET curation_status = 'duplicate_to_delete'
                    WHERE video_id = CAST(:video_id AS uuid)
                """),
                {"video_id": video_id}
            )
            marked.append(video_id)
        
        await db.commit()
        
        return {
            "status": "success",
            "marked_count": len(marked),
            "video_ids": marked,
            "message": f"Marked {len(marked)} videos for deletion. Use /api/duplicates/execute-deletion to permanently delete."
        }
    except Exception as e:
        logger.error(f"Error marking videos for deletion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marked-for-deletion")
async def get_marked_for_deletion(
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of videos currently marked for deletion.
    """
    try:
        result = await db.execute(
            text("""
                SELECT v.id, v.file_name, v.source_uri, v.duration_sec, v.file_size_bytes
                FROM videos v
                JOIN video_analysis va ON v.id = va.video_id
                WHERE va.curation_status = 'duplicate_to_delete'
            """)
        )
        rows = result.fetchall()
        
        videos = [
            {
                "id": str(row[0]),
                "filename": row[1],
                "source_uri": row[2],
                "duration_sec": row[3],
                "file_size_bytes": row[4],
            }
            for row in rows
        ]
        
        total_size_mb = sum(v.get("file_size_bytes", 0) or 0 for v in videos) / (1024 * 1024)
        
        return {
            "count": len(videos),
            "videos": videos,
            "total_size_mb": round(total_size_mb, 2),
            "message": f"{len(videos)} videos marked for deletion ({total_size_mb:.1f} MB)"
        }
    except Exception as e:
        logger.error(f"Error getting marked videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/execute-deletion")
async def execute_deletion(
    db: AsyncSession = Depends(get_db),
    delete_files: bool = Query(default=False, description="Actually delete files from disk"),
):
    """
    Execute deletion of videos marked as 'duplicate_to_delete'.
    
    WARNING: If delete_files=True, this will permanently delete files from disk!
    """
    import os
    
    try:
        # Get videos marked for deletion
        result = await db.execute(
            text("""
                SELECT v.id, v.source_uri
                FROM videos v
                JOIN video_analysis va ON v.id = va.video_id
                WHERE va.curation_status = 'duplicate_to_delete'
            """)
        )
        rows = result.fetchall()
        
        deleted_ids = []
        deleted_files = []
        errors = []
        
        for row in rows:
            video_id = str(row[0])
            source_uri = row[1]
            
            try:
                # Delete from database
                await db.execute(
                    text("DELETE FROM video_analysis WHERE video_id = CAST(:vid AS uuid)"),
                    {"vid": video_id}
                )
                await db.execute(
                    text("DELETE FROM videos WHERE id = CAST(:vid AS uuid)"),
                    {"vid": video_id}
                )
                deleted_ids.append(video_id)
                
                # Optionally delete file from disk
                if delete_files and source_uri and os.path.exists(source_uri):
                    os.remove(source_uri)
                    deleted_files.append(source_uri)
                    
            except Exception as e:
                errors.append({"video_id": video_id, "error": str(e)})
        
        await db.commit()
        
        return {
            "status": "success",
            "deleted_from_db": len(deleted_ids),
            "deleted_files": len(deleted_files) if delete_files else 0,
            "errors": errors,
            "message": f"Deleted {len(deleted_ids)} videos from database" + 
                      (f" and {len(deleted_files)} files from disk" if delete_files else "")
        }
    except Exception as e:
        logger.error(f"Error executing deletion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
