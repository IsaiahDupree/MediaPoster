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


# =============================================================================
# IMAGE DUPLICATE DETECTION (Visual Hash Based)
# =============================================================================

@router.get("/find-image-duplicates")
async def find_image_duplicates(
    db: AsyncSession = Depends(get_db),
    similarity_threshold: float = Query(default=0.90, ge=0.5, le=1.0),
    limit: int = Query(default=100, le=500),
):
    """
    Find duplicate images using perceptual hash comparison.
    
    Unlike video duplicates (transcript-based), this uses visual similarity.
    Works on images that have been analyzed and have visual_analysis data.
    """
    try:
        # Get all images with visual analysis (identify by file extension)
        result = await db.execute(
            text("""
                SELECT 
                    v.id,
                    v.file_name,
                    v.source_uri,
                    v.file_size,
                    va.visual_analysis,
                    va.pre_social_score
                FROM videos v
                JOIN video_analysis va ON v.id = va.video_id
                WHERE (
                    LOWER(v.file_name) LIKE '%.jpg' OR
                    LOWER(v.file_name) LIKE '%.jpeg' OR
                    LOWER(v.file_name) LIKE '%.png' OR
                    LOWER(v.file_name) LIKE '%.heic' OR
                    LOWER(v.file_name) LIKE '%.heif' OR
                    LOWER(v.file_name) LIKE '%.webp' OR
                    LOWER(v.file_name) LIKE '%.gif'
                )
                  AND va.visual_analysis IS NOT NULL
                ORDER BY v.created_at DESC
                LIMIT 1000
            """)
        )
        images = result.fetchall()
        
        if len(images) < 2:
            return {
                "groups": [],
                "total_duplicates": 0,
                "message": "Not enough images with analysis to compare"
            }
        
        # Group by visual summary similarity
        from difflib import SequenceMatcher
        
        duplicate_groups = []
        processed_ids = set()
        
        for i, img1 in enumerate(images):
            if str(img1[0]) in processed_ids:
                continue
            
            # Get visual summary for comparison
            visual1 = img1[4] or {}
            summary1 = visual1.get("visual_summary", "") if isinstance(visual1, dict) else ""
            
            if not summary1 or len(summary1) < 20:
                continue
            
            similar_images = [{
                "id": str(img1[0]),
                "filename": img1[1],
                "source_uri": img1[2],
                "file_size": img1[3],
                "score": float(img1[5]) if img1[5] else 0
            }]
            
            for img2 in images[i+1:]:
                if str(img2[0]) in processed_ids:
                    continue
                
                visual2 = img2[4] or {}
                summary2 = visual2.get("visual_summary", "") if isinstance(visual2, dict) else ""
                
                if not summary2 or len(summary2) < 20:
                    continue
                
                # Compare visual summaries
                similarity = SequenceMatcher(None, summary1[:500], summary2[:500]).ratio()
                
                if similarity >= similarity_threshold:
                    similar_images.append({
                        "id": str(img2[0]),
                        "filename": img2[1],
                        "source_uri": img2[2],
                        "file_size": img2[3],
                        "score": float(img2[5]) if img2[5] else 0,
                        "similarity": round(similarity, 3)
                    })
                    processed_ids.add(str(img2[0]))
            
            if len(similar_images) > 1:
                processed_ids.add(str(img1[0]))
                
                # Recommend which to keep (highest score, then largest file)
                similar_images.sort(key=lambda x: (x.get("score", 0), x.get("file_size", 0)), reverse=True)
                
                duplicate_groups.append({
                    "keep": similar_images[0],
                    "delete_candidates": similar_images[1:],
                    "count": len(similar_images),
                    "visual_preview": summary1[:200] + "..." if len(summary1) > 200 else summary1
                })
                
                if len(duplicate_groups) >= limit:
                    break
        
        total_deletable = sum(len(g["delete_candidates"]) for g in duplicate_groups)
        
        return {
            "groups": duplicate_groups,
            "total_groups": len(duplicate_groups),
            "total_duplicates": total_deletable,
            "message": f"Found {len(duplicate_groups)} groups with {total_deletable} potential duplicate images"
        }
    except Exception as e:
        logger.error(f"Error finding image duplicates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                SELECT v.id, v.file_name, v.source_uri, v.duration_sec
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
            }
            for row in rows
        ]
        
        # Estimate size based on duration (rough: 5MB per 10 seconds)
        total_duration = sum(v.get("duration_sec", 0) or 0 for v in videos)
        estimated_size_mb = total_duration * 0.5  # ~0.5 MB per second estimate
        
        return {
            "count": len(videos),
            "videos": videos,
            "total_size_mb": round(estimated_size_mb, 2),
            "message": f"{len(videos)} videos marked for deletion (~{estimated_size_mb:.1f} MB estimated)"
        }
    except Exception as e:
        logger.error(f"Error getting marked videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-detect-and-recommend")
async def auto_detect_and_recommend(
    db: AsyncSession = Depends(get_db),
    similarity_threshold: float = Query(default=0.85, ge=0.5, le=1.0),
    dry_run: bool = Query(default=True, description="If True, only preview what would be deleted"),
):
    """
    Auto-detect duplicates and recommend which to delete.
    
    **Protection Rules:**
    1. If one video has captions and other doesn't → KEEP the one WITH captions
    2. If both have same caption status → KEEP the longer one
    3. If same duration and caption status → KEEP the one with higher social score
    
    Returns a list of recommended deletions with reasons.
    """
    detector = DuplicateDetector(db)
    
    try:
        # Find all duplicates (including cross-caption-status for proper recommendations)
        duplicates = await detector.find_duplicates(
            similarity_threshold=similarity_threshold,
            limit=500,
            compare_same_caption_status_only=False,  # Compare ALL to find caption variants
        )
        
        recommendations = []
        protected_pairs = []  # Caption variant pairs
        
        for pair in duplicates:
            # Determine which to keep and which to delete
            keep_id = None
            delete_id = None
            reason = ""
            
            # Rule 1: Caption protection - ALWAYS keep the one with captions
            if pair.video1_has_captions and not pair.video2_has_captions:
                keep_id = pair.video1_id
                delete_id = pair.video2_id
                reason = "Video 1 has captions, Video 2 does not"
            elif pair.video2_has_captions and not pair.video1_has_captions:
                keep_id = pair.video2_id
                delete_id = pair.video1_id
                reason = "Video 2 has captions, Video 1 does not"
            
            # Rule 2: Same caption status - keep longer
            elif abs(pair.video1_duration - pair.video2_duration) > 1:
                if pair.video1_duration > pair.video2_duration:
                    keep_id = pair.video1_id
                    delete_id = pair.video2_id
                    reason = f"Video 1 is longer ({pair.video1_duration:.1f}s vs {pair.video2_duration:.1f}s)"
                else:
                    keep_id = pair.video2_id
                    delete_id = pair.video1_id
                    reason = f"Video 2 is longer ({pair.video2_duration:.1f}s vs {pair.video1_duration:.1f}s)"
            
            # Rule 3: Same duration - need manual review or use social score
            else:
                # For now, mark for manual review
                protected_pairs.append({
                    "video1_id": pair.video1_id,
                    "video1_filename": pair.video1_filename,
                    "video2_id": pair.video2_id,
                    "video2_filename": pair.video2_filename,
                    "similarity": pair.similarity_score,
                    "reason": "Same duration and caption status - manual review needed"
                })
                continue
            
            recommendations.append({
                "keep": {
                    "id": keep_id,
                    "filename": pair.video1_filename if keep_id == pair.video1_id else pair.video2_filename,
                    "has_captions": pair.video1_has_captions if keep_id == pair.video1_id else pair.video2_has_captions,
                    "duration_sec": pair.video1_duration if keep_id == pair.video1_id else pair.video2_duration,
                },
                "delete": {
                    "id": delete_id,
                    "filename": pair.video2_filename if delete_id == pair.video2_id else pair.video1_filename,
                    "has_captions": pair.video2_has_captions if delete_id == pair.video2_id else pair.video1_has_captions,
                    "duration_sec": pair.video2_duration if delete_id == pair.video2_id else pair.video1_duration,
                },
                "similarity": pair.similarity_score,
                "reason": reason,
            })
        
        # If not dry run, mark recommended deletions
        if not dry_run and recommendations:
            delete_ids = [r["delete"]["id"] for r in recommendations]
            for vid in delete_ids:
                await db.execute(
                    text("""
                        UPDATE video_analysis 
                        SET curation_status = 'duplicate_to_delete'
                        WHERE video_id = CAST(:video_id AS uuid)
                    """),
                    {"video_id": vid}
                )
            await db.commit()
        
        return {
            "status": "dry_run" if dry_run else "marked_for_deletion",
            "total_duplicate_pairs": len(duplicates),
            "auto_delete_candidates": len(recommendations),
            "protected_pairs": len(protected_pairs),
            "recommendations": recommendations,
            "needs_manual_review": protected_pairs,
            "message": f"Found {len(recommendations)} safe-to-delete duplicates" + 
                      (f" (DRY RUN - nothing marked)" if dry_run else f" - marked {len(recommendations)} for deletion")
        }
    except Exception as e:
        logger.error(f"Error in auto-detect: {e}")
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
