"""
External Scheduling API
=======================
API endpoints for external servers to submit videos for scheduled posting.

This allows external services (e.g., video generation pipelines, content tools)
to send videos directly to MediaPoster for scheduled publishing.

Flow:
1. External server POSTs video URL + schedule details
2. MediaPoster downloads/ingests the video
3. Video is scheduled for posting at specified time(s)
4. Post Scheduler handles automatic publishing via Blotato
"""

import os
import uuid
import httpx
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from loguru import logger
from sqlalchemy import create_engine, text
import json

router = APIRouter(prefix="/api/external", tags=["External Scheduling"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

# =============================================================================
# MODELS
# =============================================================================

class ScheduleTarget(BaseModel):
    """Single platform scheduling target"""
    platform: str = Field(..., description="Platform: tiktok, instagram, youtube, twitter, threads, etc.")
    account_id: str = Field(..., description="Blotato account ID for the platform")
    scheduled_at: str = Field(..., description="ISO8601 datetime for posting")
    title: Optional[str] = Field(None, description="Platform-specific title (required for YouTube)")
    caption: Optional[str] = Field(None, description="Platform-specific caption override")


class ExternalVideoSubmission(BaseModel):
    """Request to submit a video from external source for scheduled posting"""
    video_url: str = Field(..., description="Public URL to download the video from")
    title: str = Field(..., description="Video title")
    caption: str = Field(..., description="Default caption for all platforms")
    hashtags: List[str] = Field(default=[], description="Hashtags to append")
    
    # Scheduling targets
    targets: List[ScheduleTarget] = Field(..., description="List of platform targets with schedules")
    
    # Optional metadata
    source_id: Optional[str] = Field(None, description="External reference ID from source system")
    source_system: Optional[str] = Field(None, description="Name of the source system (e.g., 'sora-pipeline')")
    thumbnail_url: Optional[str] = Field(None, description="Optional thumbnail URL")
    
    # Processing options
    skip_analysis: bool = Field(default=False, description="Skip AI analysis (faster)")
    priority: str = Field(default="normal", description="Priority: low, normal, high")


class BulkScheduleRequest(BaseModel):
    """Request to schedule multiple videos with frequency"""
    video_urls: List[str] = Field(..., description="List of video URLs to schedule")
    title_template: str = Field(default="Video {n}", description="Title template ({n} = index)")
    caption_template: str = Field(..., description="Caption template")
    hashtags: List[str] = Field(default=[])
    
    # Frequency settings
    platform: str = Field(..., description="Target platform")
    account_id: str = Field(..., description="Blotato account ID")
    start_time: str = Field(..., description="First post time (ISO8601)")
    interval_minutes: int = Field(default=60, description="Minutes between posts")
    
    source_system: Optional[str] = Field(None)


class ScheduleResponse(BaseModel):
    """Response after scheduling"""
    success: bool
    scheduled_posts: List[dict]
    video_id: Optional[str] = None
    message: str


# =============================================================================
# HELPERS
# =============================================================================

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


async def download_video(url: str, dest_dir: Path) -> Path:
    """Download video from URL to local storage"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    ext = Path(url).suffix or '.mp4'
    if '?' in ext:
        ext = ext.split('?')[0]
    if not ext.startswith('.'):
        ext = '.mp4'
    
    filename = f"external_{uuid.uuid4().hex[:8]}{ext}"
    dest_path = dest_dir / filename
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        
        with open(dest_path, 'wb') as f:
            f.write(response.content)
    
    logger.info(f"Downloaded video to {dest_path}")
    return dest_path


async def ingest_video_to_db(video_path: Path, title: str, source_system: str = None) -> str:
    """Ingest video into MediaPoster database, return video ID"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:5555/api/media-db/ingest/file",
                json={
                    "file_path": str(video_path),
                    "title": title,
                    "source": source_system or "external_api"
                }
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("video_id") or data.get("id")
    except Exception as e:
        logger.error(f"Failed to ingest video: {e}")
    
    return None


def create_scheduled_post(
    content_id: str,
    platform: str,
    account_id: str,
    scheduled_at: str,
    title: str,
    caption: str,
    hashtags: List[str],
    source: str = "external_api",
    thumbnail_url: str = None
) -> dict:
    """Create a scheduled post in the database"""
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO scheduled_posts 
            (content_id, clip_id, title, caption, hashtags, thumbnail_url, platform,
             account_id, account_username, platform_account_id, blotato_account_id,
             scheduled_time, scheduled_at, status, source)
            VALUES 
            (:content_id, :clip_id, :title, :caption, :hashtags, :thumbnail_url, :platform,
             :account_id, :account_username, :platform_account_id, :blotato_account_id,
             :scheduled_time, :scheduled_at, 'scheduled', :source)
            RETURNING id
        """), {
            "content_id": content_id,
            "clip_id": content_id if is_valid_uuid(content_id) else None,
            "title": title,
            "caption": caption,
            "hashtags": json.dumps(hashtags) if hashtags else '[]',
            "thumbnail_url": thumbnail_url,
            "platform": platform,
            "account_id": account_id,
            "account_username": f"{platform}_{account_id}",
            "platform_account_id": account_id,
            "blotato_account_id": account_id,
            "scheduled_time": scheduled_at,
            "scheduled_at": scheduled_at,
            "source": source,
        })
        conn.commit()
        post_id = result.fetchone()[0]
    
    return {
        "id": str(post_id),
        "platform": platform,
        "account_id": account_id,
        "scheduled_at": scheduled_at,
        "status": "scheduled"
    }


def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except (ValueError, AttributeError):
        return False


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/submit", response_model=ScheduleResponse)
async def submit_video(
    submission: ExternalVideoSubmission,
    background_tasks: BackgroundTasks
):
    """
    Submit a video from external source for scheduled posting.
    
    This endpoint:
    1. Downloads the video from the provided URL
    2. Ingests it into MediaPoster's media database
    3. Creates scheduled posts for each target platform/time
    
    Example:
    ```json
    {
        "video_url": "https://example.com/my-video.mp4",
        "title": "My Awesome Video",
        "caption": "Check this out! #trending",
        "hashtags": ["#ai", "#automation"],
        "targets": [
            {"platform": "tiktok", "account_id": "710", "scheduled_at": "2026-01-31T15:00:00Z"},
            {"platform": "youtube", "account_id": "228", "scheduled_at": "2026-01-31T16:00:00Z", "title": "YouTube Title"}
        ]
    }
    ```
    """
    try:
        # Step 1: Download video
        download_dir = Path("/tmp/mediaposter_external")
        video_path = await download_video(submission.video_url, download_dir)
        
        # Step 2: Ingest to database
        video_id = await ingest_video_to_db(
            video_path, 
            submission.title,
            submission.source_system
        )
        
        if not video_id:
            # Use a placeholder content_id if ingestion fails
            video_id = f"ext_{uuid.uuid4().hex[:12]}"
            logger.warning(f"Using placeholder ID: {video_id}")
        
        # Step 3: Create scheduled posts for each target
        scheduled_posts = []
        for target in submission.targets:
            post = create_scheduled_post(
                content_id=video_id,
                platform=target.platform,
                account_id=target.account_id,
                scheduled_at=target.scheduled_at,
                title=target.title or submission.title,
                caption=target.caption or submission.caption,
                hashtags=submission.hashtags,
                source=submission.source_system or "external_api",
                thumbnail_url=submission.thumbnail_url
            )
            scheduled_posts.append(post)
            logger.info(f"Scheduled {target.platform} post for {target.scheduled_at}")
        
        return ScheduleResponse(
            success=True,
            video_id=video_id,
            scheduled_posts=scheduled_posts,
            message=f"Video scheduled for {len(scheduled_posts)} platform(s)"
        )
        
    except httpx.HTTPError as e:
        logger.error(f"Failed to download video: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")
    except Exception as e:
        logger.error(f"Error submitting video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-schedule", response_model=ScheduleResponse)
async def bulk_schedule_videos(request: BulkScheduleRequest):
    """
    Schedule multiple videos with a set frequency.
    
    Example: Post 10 videos to TikTok, one every hour starting at 3pm:
    ```json
    {
        "video_urls": ["url1", "url2", "url3", ...],
        "caption_template": "Daily content #{n} 🔥",
        "platform": "tiktok",
        "account_id": "710",
        "start_time": "2026-01-31T15:00:00Z",
        "interval_minutes": 60
    }
    ```
    """
    try:
        download_dir = Path("/tmp/mediaposter_external")
        scheduled_posts = []
        
        start_dt = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
        
        for i, url in enumerate(request.video_urls):
            # Calculate scheduled time
            post_time = start_dt + timedelta(minutes=i * request.interval_minutes)
            
            # Download video
            video_path = await download_video(url, download_dir)
            
            # Ingest
            title = request.title_template.replace("{n}", str(i + 1))
            video_id = await ingest_video_to_db(video_path, title, request.source_system)
            
            if not video_id:
                video_id = f"ext_{uuid.uuid4().hex[:12]}"
            
            # Create scheduled post
            caption = request.caption_template.replace("{n}", str(i + 1))
            post = create_scheduled_post(
                content_id=video_id,
                platform=request.platform,
                account_id=request.account_id,
                scheduled_at=post_time.isoformat(),
                title=title,
                caption=caption,
                hashtags=request.hashtags,
                source=request.source_system or "external_bulk"
            )
            scheduled_posts.append(post)
            logger.info(f"Scheduled video {i+1}/{len(request.video_urls)} for {post_time}")
        
        return ScheduleResponse(
            success=True,
            scheduled_posts=scheduled_posts,
            message=f"Scheduled {len(scheduled_posts)} videos from {start_dt} with {request.interval_minutes}min intervals"
        )
        
    except Exception as e:
        logger.error(f"Error in bulk schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{source_id}")
async def get_submission_status(source_id: str):
    """
    Get status of posts submitted with a specific source_id.
    
    Useful for external systems to track their submissions.
    """
    engine = get_engine()
    
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, platform, status, scheduled_time, platform_url, error_message
            FROM scheduled_posts 
            WHERE content_id LIKE :source_pattern OR source = :source_id
            ORDER BY scheduled_time
        """), {"source_pattern": f"%{source_id}%", "source_id": source_id}).fetchall()
    
    posts = [{
        "id": str(row[0]),
        "platform": row[1],
        "status": row[2],
        "scheduled_at": row[3].isoformat() if row[3] else None,
        "platform_url": row[4],
        "error": row[5]
    } for row in rows]
    
    return {
        "source_id": source_id,
        "total": len(posts),
        "posts": posts
    }


@router.get("/accounts")
async def list_available_accounts():
    """
    List all available Blotato accounts for scheduling.
    
    Use these account IDs in your schedule targets.
    """
    return {
        "accounts": {
            "tiktok": [
                {"id": "710", "username": "@isaiah_dupree"},
                {"id": "243", "username": "@the_isaiah_dupree"},
                {"id": "4508", "username": "@dupree_isaiah"},
                {"id": "571", "username": "@soursides_is_sour"}
            ],
            "instagram": [
                {"id": "807", "username": "@the_isaiah_dupree"},
                {"id": "670", "username": "@the_isaiah_dupree_"},
                {"id": "1369", "username": "@dupree_isaiah_"},
                {"id": "4508", "username": "@dupree_isaiah"}
            ],
            "youtube": [
                {"id": "228", "username": "Isaiah Dupree"},
                {"id": "3370", "username": "lofi_creator"}
            ],
            "twitter": [
                {"id": "4151", "username": "@IsaiahDupree7"}
            ],
            "threads": [
                {"id": "173", "username": "@the_isaiah_dupree_"},
                {"id": "201", "username": "@the_isaiah_dupree"},
                {"id": "1369", "username": "@dupree_isaiah_"},
                {"id": "4150", "username": "@isaiahdupree75"}
            ]
        }
    }


@router.get("/health")
async def external_api_health():
    """Health check for external API"""
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "endpoints": [
            "POST /api/external/submit - Submit single video",
            "POST /api/external/bulk-schedule - Schedule multiple videos",
            "GET /api/external/status/{source_id} - Check submission status",
            "GET /api/external/accounts - List available accounts"
        ]
    }
