"""
Format Discovery API Endpoints
Automatically discovers clips that match format criteria (e.g., b-roll candidates)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from loguru import logger

from database.connection import get_db
from database.models import Video, VideoAnalysis
from services.format_classifier import FormatClassifier, VideoFormat, FormatClassification

router = APIRouter(prefix="/api/format-discovery", tags=["Format Discovery"])


class BrollCandidate(BaseModel):
    media_id: str
    filename: str
    duration_sec: Optional[float] = None
    thumbnail_url: Optional[str] = None
    format_type: str
    confidence: float
    reasons: List[str]
    has_person: bool
    has_speech: bool
    has_captions: bool


class DiscoveryResponse(BaseModel):
    total_found: int
    broll_text_candidates: List[BrollCandidate]
    pure_broll_candidates: List[BrollCandidate]
    message: str


@router.get("/broll-candidates", response_model=DiscoveryResponse)
async def discover_broll_candidates(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=200),
    include_with_person: bool = Query(default=True, description="Include clips with person (not talking)"),
    include_pure_broll: bool = Query(default=True, description="Include clips without any person"),
):
    """
    Discover videos that are candidates for B-Roll + Text overlays.
    
    Returns two categories:
    - **broll_text_candidates**: Person visible but NOT talking (no captions needed)
    - **pure_broll_candidates**: No person, no speech (perfect for text overlays)
    """
    classifier = FormatClassifier(db)
    
    # Query videos (only actual videos, not images)
    query = select(Video).where(
        Video.duration_sec > 0
    ).order_by(Video.created_at.desc()).limit(limit * 3)
    
    result = await db.execute(query)
    videos = result.scalars().all()
    
    broll_text_candidates = []
    pure_broll_candidates = []
    
    for video in videos:
        try:
            classification = await classifier.classify_video(str(video.id))
            
            # Skip if already has captions
            if classification.has_captions:
                continue
            
            candidate = BrollCandidate(
                media_id=str(video.id),
                filename=video.file_name or "",
                duration_sec=video.duration_sec,
                thumbnail_url=f"/api/media-db/thumbnail/{video.id}",
                format_type=classification.format.value,
                confidence=classification.confidence,
                reasons=classification.reasons,
                has_person=classification.has_person,
                has_speech=classification.has_speech,
                has_captions=classification.has_captions,
            )
            
            if include_with_person and classification.format == VideoFormat.BROLL_TEXT_CANDIDATE:
                broll_text_candidates.append(candidate)
            elif include_pure_broll and classification.format in [
                VideoFormat.PURE_BROLL,
                VideoFormat.MUSIC_ONLY,
                VideoFormat.SILENT
            ]:
                pure_broll_candidates.append(candidate)
            
            # Stop if we have enough
            if len(broll_text_candidates) >= limit and len(pure_broll_candidates) >= limit:
                break
                
        except Exception as e:
            logger.warning(f"Error classifying video {video.id}: {e}")
            continue
    
    total = len(broll_text_candidates) + len(pure_broll_candidates)
    
    return DiscoveryResponse(
        total_found=total,
        broll_text_candidates=broll_text_candidates[:limit],
        pure_broll_candidates=pure_broll_candidates[:limit],
        message=f"Found {len(broll_text_candidates)} clips with person (not talking) and {len(pure_broll_candidates)} pure b-roll clips"
    )


@router.get("/classify/{media_id}")
async def classify_single_video(
    media_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Classify a single video to determine its format type.
    """
    classifier = FormatClassifier(db)
    
    try:
        classification = await classifier.classify_video(media_id)
        return {
            "media_id": media_id,
            "classification": classification.to_dict()
        }
    except Exception as e:
        logger.error(f"Error classifying video {media_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-format/{format_id}")
async def run_format_on_candidates(
    format_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=10, le=50, description="Number of clips to process"),
    text_content: Optional[str] = Query(default=None, description="Text to overlay on clips"),
):
    """
    Run a format (e.g., broll_text_v1) on automatically discovered candidates.
    
    This will:
    1. Find matching b-roll clips
    2. Queue them for processing with the specified format
    3. Return the queued job IDs
    """
    # Validate format exists
    from services.formats.sample_formats import get_sample_format
    format_def = get_sample_format(format_id)
    
    if not format_def:
        raise HTTPException(status_code=404, detail=f"Format '{format_id}' not found")
    
    # Get clip filter from format defaults
    clip_filter = format_def.get("defaults", {}).get("params", {}).get("clipFilter", "broll_text")
    
    # Discover candidates
    classifier = FormatClassifier(db)
    
    query = select(Video).where(Video.duration_sec > 0).order_by(Video.created_at.desc()).limit(limit * 5)
    result = await db.execute(query)
    videos = result.scalars().all()
    
    candidates = []
    for video in videos:
        try:
            classification = await classifier.classify_video(str(video.id))
            
            if classification.has_captions:
                continue
            
            # Match based on clip filter
            if clip_filter == "broll_text" and classification.format == VideoFormat.BROLL_TEXT_CANDIDATE:
                candidates.append(video)
            elif clip_filter == "pure_broll" and classification.format in [
                VideoFormat.PURE_BROLL, VideoFormat.MUSIC_ONLY, VideoFormat.SILENT
            ]:
                candidates.append(video)
            
            if len(candidates) >= limit:
                break
        except Exception as e:
            continue
    
    if not candidates:
        return {
            "status": "no_candidates",
            "message": f"No matching clips found for format '{format_id}'",
            "format": format_def["name"],
            "candidates_found": 0
        }
    
    # Return candidates for now (actual format run would be implemented with Remotion)
    return {
        "status": "candidates_found",
        "message": f"Found {len(candidates)} clips ready for '{format_def['name']}'",
        "format": format_def["name"],
        "format_id": format_id,
        "candidates_found": len(candidates),
        "candidates": [
            {
                "media_id": str(v.id),
                "filename": v.file_name,
                "duration_sec": v.duration_sec,
                "thumbnail_url": f"/api/media-db/thumbnail/{v.id}"
            }
            for v in candidates
        ],
        "next_step": "Call /api/formats/{format_id}/run with selected candidates to process"
    }
