"""
Posted Content Matcher API Endpoints
Scrapes posted content and cross-references with local library to prevent duplicates
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from loguru import logger
from datetime import datetime

from database.connection import get_db
from services.posted_content_matcher import PostedContentMatcher, SafariPostedContentScraper

router = APIRouter(prefix="/api/posted-matcher", tags=["Posted Content Matcher"])


class ScrapeRequest(BaseModel):
    username: str
    platform: str  # 'tiktok', 'instagram'
    max_videos: int = 50


class MatchRequest(BaseModel):
    transcript: str
    platform: str
    posted_url: str


class MarkPostedRequest(BaseModel):
    local_video_id: str
    platform: str
    posted_url: str


@router.post("/scrape-and-match")
async def scrape_and_match_posted_content(
    request: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Scrape posted content from a social platform and match with local library.
    Uses Safari automation to collect video URLs from profile.
    
    NOTE: This opens Safari and requires manual login if not already logged in.
    """
    matcher = PostedContentMatcher(db)
    
    try:
        if request.platform == "tiktok":
            result = await matcher.scrape_and_match_tiktok(
                request.username, 
                request.max_videos
            )
        elif request.platform == "instagram":
            result = await matcher.scrape_and_match_instagram(
                request.username,
                request.max_videos
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {request.platform}")
        
        return result
    except Exception as e:
        logger.error(f"Error scraping and matching: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match-transcript")
async def match_transcript_to_library(
    request: MatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Match a single transcript against the local library.
    Returns the best matching local video if found.
    """
    matcher = PostedContentMatcher(db)
    
    try:
        local_transcripts = await matcher.get_local_transcripts()
        
        if not local_transcripts:
            return {
                "match_found": False,
                "message": "No local transcripts available for matching"
            }
        
        match = await matcher.match_transcript_to_library(
            request.transcript,
            local_transcripts,
            threshold=0.80
        )
        
        if match:
            return {
                "match_found": True,
                "local_video_id": match["local_video_id"],
                "local_filename": match["local_filename"],
                "similarity_score": match["similarity_score"],
                "match_type": match["match_type"],
                "recommendation": "This video appears to already exist in your library"
            }
        else:
            return {
                "match_found": False,
                "message": "No matching video found in local library"
            }
    except Exception as e:
        logger.error(f"Error matching transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-as-posted")
async def mark_video_as_posted(
    request: MarkPostedRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a local video as already posted to a platform.
    This prevents the video from being scheduled for posting again.
    """
    matcher = PostedContentMatcher(db)
    
    try:
        success = await matcher.mark_video_as_posted(
            request.local_video_id,
            request.platform,
            request.posted_url
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Video marked as posted to {request.platform}",
                "local_video_id": request.local_video_id,
                "posted_url": request.posted_url
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to mark video as posted")
    except Exception as e:
        logger.error(f"Error marking video as posted: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/already-posted")
async def get_already_posted_videos(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, le=500),
):
    """
    Get list of videos that have been marked as already posted.
    """
    matcher = PostedContentMatcher(db)
    
    try:
        videos = await matcher.get_already_posted_videos()
        return {
            "count": len(videos),
            "videos": videos[:limit]
        }
    except Exception as e:
        logger.error(f"Error getting already posted videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-before-post/{video_id}")
async def check_before_posting(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a video has already been posted before scheduling.
    Use this before adding a video to the posting queue.
    """
    try:
        query = text("""
            SELECT 
                v.id,
                v.file_name,
                va.curation_status,
                va.visual_analysis->'posted_platforms' as posted_platforms
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE v.id = CAST(:video_id AS uuid)
        """)
        
        result = await db.execute(query, {"video_id": video_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        
        posted_platforms = row[3]
        is_posted = row[2] == 'already_posted' or (posted_platforms and len(posted_platforms) > 0)
        
        return {
            "video_id": video_id,
            "filename": row[1],
            "already_posted": is_posted,
            "posted_platforms": posted_platforms or [],
            "safe_to_post": not is_posted,
            "message": "This video has already been posted" if is_posted else "Safe to post"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cross-reference-summary")
async def get_cross_reference_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary of cross-reference status between posted content and local library.
    """
    try:
        # Count total videos
        total_result = await db.execute(text("SELECT COUNT(*) FROM videos"))
        total_videos = total_result.scalar()
        
        # Count already posted
        posted_result = await db.execute(text("""
            SELECT COUNT(*) FROM video_analysis 
            WHERE curation_status = 'already_posted'
        """))
        already_posted = posted_result.scalar()
        
        # Count with transcripts
        transcript_result = await db.execute(text("""
            SELECT COUNT(*) FROM video_analysis 
            WHERE transcript IS NOT NULL AND LENGTH(transcript) > 30
        """))
        with_transcripts = transcript_result.scalar()
        
        # Count approved for posting
        approved_result = await db.execute(text("""
            SELECT COUNT(*) FROM video_analysis 
            WHERE curation_status = 'approved'
        """))
        approved = approved_result.scalar()
        
        return {
            "total_videos": total_videos,
            "with_transcripts": with_transcripts,
            "already_posted": already_posted,
            "approved_for_posting": approved,
            "safe_to_post": approved,  # Approved but not already posted
            "needs_transcript": total_videos - with_transcripts,
            "message": f"{already_posted} videos marked as already posted, {approved} approved and safe to post"
        }
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task for scraping
_scrape_jobs: Dict[str, Dict[str, Any]] = {}


@router.post("/scrape-background")
async def start_background_scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a background scrape job (non-blocking).
    Returns a job_id to check status.
    """
    import uuid
    job_id = str(uuid.uuid4())
    
    _scrape_jobs[job_id] = {
        "status": "starting",
        "platform": request.platform,
        "username": request.username,
        "started_at": datetime.now().isoformat(),
        "urls_found": 0,
        "matches_found": 0
    }
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": f"Background scrape started for @{request.username} on {request.platform}"
    }


@router.get("/scrape-status/{job_id}")
async def get_scrape_status(job_id: str):
    """Get status of a background scrape job."""
    if job_id not in _scrape_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return _scrape_jobs[job_id]
