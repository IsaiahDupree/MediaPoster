"""
AI-Assisted Curation API
========================
Endpoints for sentiment analysis, duplicate detection, auto-curation, and bulk operations.
Based on PRD_AI_ASSISTED_CURATION.md
"""
import os
import uuid
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from database.connection import get_db
from database.models import Video, VideoAnalysis
from loguru import logger

router = APIRouter(prefix="/api/curation", tags=["AI Curation"])

# OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# iPhone Import folder path
IPHONE_IMPORT_DIR = "/Users/isaiahdupree/Documents/IphoneImport"

# =============================================================================
# MODELS
# =============================================================================

class SentimentResult(BaseModel):
    score: float  # -1.0 to 1.0
    label: str  # very_negative, negative, neutral, positive, very_positive

class DuplicateGroup(BaseModel):
    group_id: str
    videos: List[Dict[str, Any]]
    similarity_score: float
    transcript_preview: str
    is_caption_variant: bool = False  # True if videos might be caption vs no-caption versions
    caption_variant_reason: Optional[str] = None  # Explanation of why flagged as caption variant

class AutoCurationSettings(BaseModel):
    auto_deny_threshold: float = -0.5
    auto_approve_threshold: float = 0.7
    min_score_for_approval: int = 60
    enabled: bool = True

class BulkFilter(BaseModel):
    sentiment_min: Optional[float] = None
    sentiment_max: Optional[float] = None
    score_min: Optional[float] = None
    score_max: Optional[float] = None
    duration_min: Optional[int] = None
    duration_max: Optional[int] = None
    has_transcript: Optional[bool] = None

class CoverageStats(BaseModel):
    total_media: int
    analyzed: int
    unanalyzed: int
    with_transcript: int
    with_sentiment: int
    approved: int
    rejected: int
    pending: int

# =============================================================================
# SENTIMENT ANALYSIS
# =============================================================================

async def analyze_sentiment(transcript: str) -> SentimentResult:
    """Analyze sentiment of a transcript using OpenAI."""
    if not transcript or len(transcript.strip()) < 10:
        return SentimentResult(score=0.0, label="neutral")
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Analyze the sentiment of this video transcript. 
                    Return ONLY a JSON object with:
                    - score: float from -1.0 (very negative) to 1.0 (very positive)
                    - label: one of "very_negative", "negative", "neutral", "positive", "very_positive"
                    
                    Consider:
                    - Emotional tone and energy
                    - Positive/negative language
                    - Overall message vibe
                    - Would viewers feel good watching this?"""
                },
                {"role": "user", "content": transcript[:2000]}  # Limit to 2000 chars
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        score = float(result.get("score", 0))
        label = result.get("label", "neutral")
        
        # Validate score range
        score = max(-1.0, min(1.0, score))
        
        return SentimentResult(score=score, label=label)
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        return SentimentResult(score=0.0, label="neutral")

def get_transcript_hash(transcript: str) -> str:
    """Generate MD5 hash of normalized transcript for duplicate detection."""
    if not transcript:
        return ""
    # Normalize: lowercase, remove extra whitespace
    normalized = " ".join(transcript.lower().split())
    return hashlib.md5(normalized.encode()).hexdigest()

# =============================================================================
# COVERAGE STATS ENDPOINT
# =============================================================================

@router.get("/coverage-stats", response_model=CoverageStats)
async def get_coverage_stats(db: AsyncSession = Depends(get_db)):
    """Get analysis coverage statistics."""
    
    # Total videos
    total_result = await db.execute(select(func.count(Video.id)))
    total_media = total_result.scalar() or 0
    
    # With analysis
    analyzed_result = await db.execute(
        select(func.count(VideoAnalysis.video_id))
    )
    analyzed = analyzed_result.scalar() or 0
    
    # With transcript
    with_transcript_result = await db.execute(
        select(func.count(VideoAnalysis.video_id))
        .where(VideoAnalysis.transcript.isnot(None))
    )
    with_transcript = with_transcript_result.scalar() or 0
    
    # With sentiment
    with_sentiment_result = await db.execute(
        select(func.count(VideoAnalysis.video_id))
        .where(VideoAnalysis.sentiment_score.isnot(None))
    )
    with_sentiment = with_sentiment_result.scalar() or 0
    
    # Curation status counts
    approved_result = await db.execute(
        select(func.count(Video.id)).where(Video.curation_status == 'approved')
    )
    approved = approved_result.scalar() or 0
    
    rejected_result = await db.execute(
        select(func.count(Video.id)).where(Video.curation_status == 'rejected')
    )
    rejected = rejected_result.scalar() or 0
    
    pending_result = await db.execute(
        select(func.count(Video.id)).where(
            (Video.curation_status == 'pending') | (Video.curation_status.is_(None))
        )
    )
    pending = pending_result.scalar() or 0
    
    return CoverageStats(
        total_media=total_media,
        analyzed=analyzed,
        unanalyzed=total_media - analyzed,
        with_transcript=with_transcript,
        with_sentiment=with_sentiment,
        approved=approved,
        rejected=rejected,
        pending=pending
    )

# =============================================================================
# BATCH SENTIMENT ANALYSIS
# =============================================================================

_sentiment_jobs = {}

@router.post("/analyze-sentiment/batch")
async def batch_analyze_sentiment(
    background_tasks: BackgroundTasks,
    limit: int = Query(100, description="Max videos to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Queue sentiment analysis for all videos with transcripts but no sentiment score."""
    
    job_id = str(uuid.uuid4())
    
    # Find videos needing sentiment analysis
    result = await db.execute(
        select(VideoAnalysis.video_id, VideoAnalysis.transcript)
        .where(VideoAnalysis.transcript.isnot(None))
        .where(VideoAnalysis.sentiment_score.is_(None))
        .limit(limit)
    )
    videos = result.fetchall()
    
    if not videos:
        return {"message": "No videos need sentiment analysis", "count": 0}
    
    _sentiment_jobs[job_id] = {
        "status": "running",
        "total": len(videos),
        "completed": 0,
        "failed": 0,
        "started_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_batch_sentiment, job_id, videos)
    
    return {
        "job_id": job_id,
        "message": f"Started sentiment analysis for {len(videos)} videos",
        "total": len(videos)
    }

async def run_batch_sentiment(job_id: str, videos: List):
    """Background task to analyze sentiment for multiple videos."""
    from database.connection import async_session_maker
    
    for video_id, transcript in videos:
        try:
            # Analyze sentiment
            sentiment = await analyze_sentiment(transcript)
            transcript_hash = get_transcript_hash(transcript)
            
            # Update database
            async with async_session_maker() as db:
                await db.execute(
                    update(VideoAnalysis)
                    .where(VideoAnalysis.video_id == video_id)
                    .values(
                        sentiment_score=sentiment.score,
                        sentiment_label=sentiment.label,
                        transcript_hash=transcript_hash
                    )
                )
                await db.commit()
            
            _sentiment_jobs[job_id]["completed"] += 1
            logger.info(f"✅ Sentiment analyzed: {video_id} -> {sentiment.label} ({sentiment.score})")
            
        except Exception as e:
            _sentiment_jobs[job_id]["failed"] += 1
            logger.error(f"❌ Sentiment analysis failed for {video_id}: {e}")
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    _sentiment_jobs[job_id]["status"] = "completed"
    _sentiment_jobs[job_id]["completed_at"] = datetime.now().isoformat()

@router.get("/analyze-sentiment/status/{job_id}")
async def get_sentiment_job_status(job_id: str):
    """Get status of a sentiment analysis job."""
    if job_id not in _sentiment_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _sentiment_jobs[job_id]

# =============================================================================
# DUPLICATE DETECTION
# =============================================================================

def detect_caption_variant(videos: List) -> tuple[bool, str]:
    """
    Detect if a group of videos with same transcript might be caption variants.
    Returns (is_caption_variant, reason)
    
    Indicators:
    - Significant file size difference (>20%) with same duration suggests captions added
    - Different resolutions with same content
    - Filename contains 'caption', 'sub', 'text' keywords
    """
    if len(videos) < 2:
        return False, ""
    
    file_sizes = [v.file_size or 0 for v in videos]
    filenames = [v.file_name.lower() if v.file_name else "" for v in videos]
    resolutions = [v.resolution for v in videos]
    
    reasons = []
    
    # Check for caption-related keywords in filenames
    caption_keywords = ['caption', 'captions', 'captioned', 'sub', 'subs', 'subtitle', 'text', 'titled']
    has_caption_keyword = any(
        any(kw in fn for kw in caption_keywords) 
        for fn in filenames
    )
    if has_caption_keyword:
        reasons.append("Filename contains caption-related keyword")
    
    # Check for significant file size difference (>20%)
    if min(file_sizes) > 0:
        size_ratio = max(file_sizes) / min(file_sizes)
        if size_ratio > 1.2:  # 20% difference
            reasons.append(f"File size varies by {((size_ratio-1)*100):.0f}% (caption encoding)")
    
    # Check for different resolutions (re-encoded with captions might change)
    unique_resolutions = set(r for r in resolutions if r)
    if len(unique_resolutions) > 1:
        reasons.append(f"Different resolutions: {', '.join(unique_resolutions)}")
    
    is_variant = len(reasons) > 0
    return is_variant, "; ".join(reasons) if reasons else ""

@router.get("/duplicates")
async def find_duplicates(
    threshold: float = Query(0.9, description="Similarity threshold (0.0-1.0)"),
    include_caption_variants: bool = Query(False, description="Include potential caption variants"),
    db: AsyncSession = Depends(get_db)
):
    """Find videos with duplicate/similar transcripts.
    
    Caption variants (same transcript, one with captions burned in) are flagged
    and excluded by default to prevent accidental deletion of valuable content.
    """
    from rapidfuzz import fuzz
    
    # Get all videos with transcripts and hashes
    result = await db.execute(
        select(
            VideoAnalysis.video_id,
            VideoAnalysis.transcript,
            VideoAnalysis.transcript_hash,
            VideoAnalysis.pre_social_score,
            VideoAnalysis.visual_analysis,
            Video.file_name,
            Video.source_uri,
            Video.file_size,
            Video.resolution,
            Video.duration_sec
        )
        .join(Video, Video.id == VideoAnalysis.video_id)
        .where(VideoAnalysis.transcript.isnot(None))
        .where(VideoAnalysis.transcript != '')
    )
    videos = result.fetchall()
    
    if len(videos) < 2:
        return {"groups": [], "total_duplicates": 0, "caption_variants_excluded": 0}
    
    # First pass: group by exact hash match
    hash_groups = {}
    for v in videos:
        h = v.transcript_hash or get_transcript_hash(v.transcript)
        if h not in hash_groups:
            hash_groups[h] = []
        hash_groups[h].append(v)
    
    # Find groups with duplicates
    duplicate_groups = []
    caption_variant_groups = []
    processed_ids = set()
    
    for h, group in hash_groups.items():
        if len(group) > 1:
            # Check if this might be a caption variant
            is_caption_variant, caption_reason = detect_caption_variant(group)
            
            group_id = str(uuid.uuid4())
            dup_group = DuplicateGroup(
                group_id=group_id,
                videos=[{
                    "video_id": str(v.video_id),
                    "filename": v.file_name,
                    "file_path": v.source_uri,
                    "file_size": v.file_size,
                    "resolution": v.resolution,
                    "duration_sec": v.duration_sec,
                    "score": float(v.pre_social_score) if v.pre_social_score else 0
                } for v in group],
                similarity_score=1.0,
                transcript_preview=group[0].transcript[:200] if group[0].transcript else "",
                is_caption_variant=is_caption_variant,
                caption_variant_reason=caption_reason if is_caption_variant else None
            )
            
            if is_caption_variant:
                caption_variant_groups.append(dup_group)
            else:
                duplicate_groups.append(dup_group)
            
            for v in group:
                processed_ids.add(str(v.video_id))
    
    # Second pass: fuzzy matching for remaining videos (expensive, limit comparisons)
    remaining = [v for v in videos if str(v.video_id) not in processed_ids]
    
    if len(remaining) > 1 and len(remaining) < 500:  # Only fuzzy match if reasonable count
        for i, v1 in enumerate(remaining):
            if str(v1.video_id) in processed_ids:
                continue
            
            similar = [v1]
            for v2 in remaining[i+1:]:
                if str(v2.video_id) in processed_ids:
                    continue
                
                # Compare transcripts
                if v1.transcript and v2.transcript:
                    ratio = fuzz.ratio(v1.transcript[:1000], v2.transcript[:1000]) / 100.0
                    if ratio >= threshold:
                        similar.append(v2)
                        processed_ids.add(str(v2.video_id))
            
            if len(similar) > 1:
                processed_ids.add(str(v1.video_id))
                
                # Check for caption variants in fuzzy matches too
                is_caption_variant, caption_reason = detect_caption_variant(similar)
                
                group_id = str(uuid.uuid4())
                dup_group = DuplicateGroup(
                    group_id=group_id,
                    videos=[{
                        "video_id": str(v.video_id),
                        "filename": v.file_name,
                        "file_path": v.source_uri,
                        "file_size": v.file_size,
                        "resolution": v.resolution,
                        "duration_sec": v.duration_sec,
                        "score": float(v.pre_social_score) if v.pre_social_score else 0
                    } for v in similar],
                    similarity_score=threshold,
                    transcript_preview=v1.transcript[:200] if v1.transcript else "",
                    is_caption_variant=is_caption_variant,
                    caption_variant_reason=caption_reason if is_caption_variant else None
                )
                
                if is_caption_variant:
                    caption_variant_groups.append(dup_group)
                else:
                    duplicate_groups.append(dup_group)
    
    # Calculate total duplicates (videos that could be deleted)
    total_duplicates = sum(len(g.videos) - 1 for g in duplicate_groups)
    caption_variants_excluded = sum(len(g.videos) - 1 for g in caption_variant_groups)
    
    # Optionally include caption variants if requested
    result_groups = duplicate_groups
    if include_caption_variants:
        result_groups = duplicate_groups + caption_variant_groups
    
    return {
        "groups": [g.model_dump() for g in result_groups],
        "total_groups": len(result_groups),
        "total_duplicates": total_duplicates,
        "caption_variants_excluded": caption_variants_excluded,
        "caption_variant_groups": len(caption_variant_groups),
        "message": f"Found {len(duplicate_groups)} true duplicate groups. Excluded {len(caption_variant_groups)} potential caption variant groups (use include_caption_variants=true to see them)."
    }

@router.post("/duplicates/delete")
async def delete_duplicates(
    group_id: str,
    keep_video_id: str,
    delete_video_ids: List[str],
    db: AsyncSession = Depends(get_db)
):
    """Delete duplicate videos, keeping the specified one. PERMANENTLY DELETES FILES."""
    
    deleted_count = 0
    freed_bytes = 0
    errors = []
    
    for video_id in delete_video_ids:
        if video_id == keep_video_id:
            continue
        
        try:
            # Get video info
            result = await db.execute(
                select(Video).where(Video.id == uuid.UUID(video_id))
            )
            video = result.scalar_one_or_none()
            
            if not video:
                errors.append(f"Video {video_id} not found")
                continue
            
            file_path = video.source_uri
            file_size = video.file_size or 0
            
            # Log deletion for audit
            await db.execute(
                text("""
                    INSERT INTO deletion_audit (media_id, filename, file_path, file_size, reason, duplicate_group_id)
                    VALUES (:media_id, :filename, :file_path, :file_size, :reason, :group_id)
                """),
                {
                    "media_id": video_id,
                    "filename": video.file_name,
                    "file_path": file_path,
                    "file_size": file_size,
                    "reason": "Duplicate transcript",
                    "group_id": group_id
                }
            )
            
            # Delete from database first
            await db.execute(delete(VideoAnalysis).where(VideoAnalysis.video_id == uuid.UUID(video_id)))
            await db.execute(delete(Video).where(Video.id == uuid.UUID(video_id)))
            
            # Delete actual file
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ Deleted file: {file_path}")
            
            deleted_count += 1
            freed_bytes += file_size
            
        except Exception as e:
            errors.append(f"Failed to delete {video_id}: {str(e)}")
            logger.error(f"❌ Delete failed for {video_id}: {e}")
    
    await db.commit()
    
    return {
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
        "errors": errors if errors else None
    }

# =============================================================================
# AUTO-CURATION
# =============================================================================

# Default settings
_auto_curation_settings = AutoCurationSettings()

@router.get("/auto-curate/settings")
async def get_auto_curation_settings():
    """Get current auto-curation settings."""
    return _auto_curation_settings

@router.put("/auto-curate/settings")
async def update_auto_curation_settings(settings: AutoCurationSettings):
    """Update auto-curation settings."""
    global _auto_curation_settings
    _auto_curation_settings = settings
    return settings

@router.get("/auto-curate/preview")
async def preview_auto_curation(db: AsyncSession = Depends(get_db)):
    """Preview what would be auto-curated without making changes."""
    
    settings = _auto_curation_settings
    
    # Find videos that would be auto-denied
    deny_result = await db.execute(
        select(func.count(Video.id))
        .join(VideoAnalysis, Video.id == VideoAnalysis.video_id)
        .where(Video.curation_status == 'pending')
        .where(VideoAnalysis.sentiment_score < settings.auto_deny_threshold)
    )
    would_deny = deny_result.scalar() or 0
    
    # Find videos that would be auto-approved
    approve_result = await db.execute(
        select(func.count(Video.id))
        .join(VideoAnalysis, Video.id == VideoAnalysis.video_id)
        .where(Video.curation_status == 'pending')
        .where(VideoAnalysis.sentiment_score > settings.auto_approve_threshold)
        .where(VideoAnalysis.pre_social_score >= settings.min_score_for_approval)
    )
    would_approve = approve_result.scalar() or 0
    
    # Find videos that would need review
    review_result = await db.execute(
        select(func.count(Video.id))
        .join(VideoAnalysis, Video.id == VideoAnalysis.video_id)
        .where(Video.curation_status == 'pending')
        .where(
            (VideoAnalysis.sentiment_score >= settings.auto_deny_threshold) &
            (VideoAnalysis.sentiment_score <= settings.auto_approve_threshold)
        )
    )
    need_review = review_result.scalar() or 0
    
    return {
        "would_deny": would_deny,
        "would_approve": would_approve,
        "need_review": need_review,
        "settings": settings.model_dump()
    }

@router.post("/auto-curate/run")
async def run_auto_curation(db: AsyncSession = Depends(get_db)):
    """Run auto-curation on all pending content based on sentiment."""
    
    settings = _auto_curation_settings
    
    if not settings.enabled:
        return {"message": "Auto-curation is disabled", "auto_approved": 0, "auto_denied": 0}
    
    # Auto-deny negative sentiment
    deny_result = await db.execute(
        update(Video)
        .where(Video.id.in_(
            select(Video.id)
            .join(VideoAnalysis, Video.id == VideoAnalysis.video_id)
            .where(Video.curation_status == 'pending')
            .where(VideoAnalysis.sentiment_score < settings.auto_deny_threshold)
        ))
        .values(
            curation_status='rejected',
            auto_curated=True,
            auto_curation_reason=f'Negative sentiment (threshold: {settings.auto_deny_threshold})'
        )
    )
    auto_denied = deny_result.rowcount
    
    # Auto-approve positive sentiment + good score
    approve_result = await db.execute(
        update(Video)
        .where(Video.id.in_(
            select(Video.id)
            .join(VideoAnalysis, Video.id == VideoAnalysis.video_id)
            .where(Video.curation_status == 'pending')
            .where(VideoAnalysis.sentiment_score > settings.auto_approve_threshold)
            .where(VideoAnalysis.pre_social_score >= settings.min_score_for_approval)
        ))
        .values(
            curation_status='approved',
            auto_curated=True,
            auto_curation_reason=f'Positive sentiment (threshold: {settings.auto_approve_threshold})'
        )
    )
    auto_approved = approve_result.rowcount
    
    await db.commit()
    
    logger.info(f"🤖 Auto-curation complete: {auto_approved} approved, {auto_denied} denied")
    
    return {
        "auto_approved": auto_approved,
        "auto_denied": auto_denied,
        "message": f"Auto-curated {auto_approved + auto_denied} videos"
    }

# =============================================================================
# BULK CURATION
# =============================================================================

@router.post("/bulk-approve")
async def bulk_approve(
    media_ids: Optional[List[str]] = None,
    filter: Optional[BulkFilter] = None,
    db: AsyncSession = Depends(get_db)
):
    """Bulk approve videos by ID list or filter."""
    
    if media_ids:
        # Approve by IDs
        result = await db.execute(
            update(Video)
            .where(Video.id.in_([uuid.UUID(mid) for mid in media_ids]))
            .values(curation_status='approved')
        )
        count = result.rowcount
    elif filter:
        # Build filter query
        query = select(Video.id).join(VideoAnalysis, Video.id == VideoAnalysis.video_id, isouter=True)
        
        if filter.sentiment_min is not None:
            query = query.where(VideoAnalysis.sentiment_score >= filter.sentiment_min)
        if filter.sentiment_max is not None:
            query = query.where(VideoAnalysis.sentiment_score <= filter.sentiment_max)
        if filter.score_min is not None:
            query = query.where(VideoAnalysis.pre_social_score >= filter.score_min)
        if filter.score_max is not None:
            query = query.where(VideoAnalysis.pre_social_score <= filter.score_max)
        if filter.duration_min is not None:
            query = query.where(Video.duration_sec >= filter.duration_min)
        if filter.duration_max is not None:
            query = query.where(Video.duration_sec <= filter.duration_max)
        if filter.has_transcript is not None:
            if filter.has_transcript:
                query = query.where(VideoAnalysis.transcript.isnot(None))
            else:
                query = query.where(VideoAnalysis.transcript.is_(None))
        
        result = await db.execute(
            update(Video)
            .where(Video.id.in_(query))
            .values(curation_status='approved')
        )
        count = result.rowcount
    else:
        raise HTTPException(status_code=400, detail="Must provide media_ids or filter")
    
    await db.commit()
    
    return {"approved_count": count}

@router.post("/bulk-deny")
async def bulk_deny(
    media_ids: Optional[List[str]] = None,
    filter: Optional[BulkFilter] = None,
    db: AsyncSession = Depends(get_db)
):
    """Bulk deny videos by ID list or filter."""
    
    if media_ids:
        result = await db.execute(
            update(Video)
            .where(Video.id.in_([uuid.UUID(mid) for mid in media_ids]))
            .values(curation_status='rejected')
        )
        count = result.rowcount
    elif filter:
        query = select(Video.id).join(VideoAnalysis, Video.id == VideoAnalysis.video_id, isouter=True)
        
        if filter.sentiment_min is not None:
            query = query.where(VideoAnalysis.sentiment_score >= filter.sentiment_min)
        if filter.sentiment_max is not None:
            query = query.where(VideoAnalysis.sentiment_score <= filter.sentiment_max)
        if filter.score_min is not None:
            query = query.where(VideoAnalysis.pre_social_score >= filter.score_min)
        if filter.score_max is not None:
            query = query.where(VideoAnalysis.pre_social_score <= filter.score_max)
        if filter.duration_min is not None:
            query = query.where(Video.duration_sec >= filter.duration_min)
        if filter.duration_max is not None:
            query = query.where(Video.duration_sec <= filter.duration_max)
        if filter.has_transcript is not None:
            if filter.has_transcript:
                query = query.where(VideoAnalysis.transcript.isnot(None))
            else:
                query = query.where(VideoAnalysis.transcript.is_(None))
        
        result = await db.execute(
            update(Video)
            .where(Video.id.in_(query))
            .values(curation_status='rejected')
        )
        count = result.rowcount
    else:
        raise HTTPException(status_code=400, detail="Must provide media_ids or filter")
    
    await db.commit()
    
    return {"denied_count": count}

@router.get("/filter-preview")
async def filter_preview(
    sentiment_min: Optional[float] = None,
    sentiment_max: Optional[float] = None,
    score_min: Optional[float] = None,
    score_max: Optional[float] = None,
    duration_min: Optional[int] = None,
    duration_max: Optional[int] = None,
    has_transcript: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Preview how many videos match a filter without making changes."""
    
    query = select(func.count(Video.id)).join(
        VideoAnalysis, Video.id == VideoAnalysis.video_id, isouter=True
    )
    
    if sentiment_min is not None:
        query = query.where(VideoAnalysis.sentiment_score >= sentiment_min)
    if sentiment_max is not None:
        query = query.where(VideoAnalysis.sentiment_score <= sentiment_max)
    if score_min is not None:
        query = query.where(VideoAnalysis.pre_social_score >= score_min)
    if score_max is not None:
        query = query.where(VideoAnalysis.pre_social_score <= score_max)
    if duration_min is not None:
        query = query.where(Video.duration_sec >= duration_min)
    if duration_max is not None:
        query = query.where(Video.duration_sec <= duration_max)
    if has_transcript is not None:
        if has_transcript:
            query = query.where(VideoAnalysis.transcript.isnot(None))
        else:
            query = query.where(VideoAnalysis.transcript.is_(None))
    
    result = await db.execute(query)
    count = result.scalar() or 0
    
    return {"count": count}
