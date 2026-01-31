"""
External Scheduling API
=======================
API endpoints for external servers to submit videos for scheduled posting.

This allows external services (e.g., video generation pipelines, content tools)
to send videos directly to MediaPoster for scheduled publishing.

Flow:
1. External server POSTs video URL + schedule details
2. MediaPoster downloads/ingests the video
3. **Smart Queue Manager analyzes schedule & allocates optimal slots**
4. Video is scheduled for posting at optimal time(s)
5. Post Scheduler handles automatic publishing via Blotato

Smart Scheduling Features:
- Automatic rate limiting per account/platform
- Consistent posting cadence maintenance
- Conflict resolution with existing posts
- Platform-specific spacing rules
"""

import os
import uuid
import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from loguru import logger
from sqlalchemy import create_engine, text
import json

from services.external_queue_manager import get_queue_manager, ExternalQueueManager

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
    # Accept EITHER video_url OR video_path (flexible for remote URLs or local files)
    video_url: Optional[str] = Field(None, description="Public URL to download the video from")
    video_path: Optional[str] = Field(None, description="Local file path (will be uploaded to storage)")
    
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


class SmartScheduleRequest(BaseModel):
    """
    Request for SMART scheduling - let MediaPoster decide optimal times.
    
    Instead of specifying exact times, you just say which platforms/accounts
    to target, and MediaPoster will:
    - Analyze current schedule
    - Find optimal posting times
    - Respect rate limits
    - Maintain consistent cadence
    
    Accepts EITHER:
    - video_url: Remote URL to download from
    - video_path: Local file path (will be uploaded to storage automatically)
    """
    # Flexible video input - accept URL or local path
    video_url: Optional[str] = Field(None, description="Public URL to download the video from")
    video_path: Optional[str] = Field(None, description="Local file path (will be uploaded to storage)")
    
    title: str = Field(..., description="Video title")
    caption: str = Field(..., description="Default caption for all platforms")
    hashtags: List[str] = Field(default=[])
    
    # Target platforms (MediaPoster decides when)
    platforms: List[str] = Field(..., description="Platforms to post to: tiktok, instagram, youtube, etc.")
    account_ids: Optional[dict] = Field(None, description="Optional account IDs per platform, e.g. {'tiktok': '710'}")
    
    # Smart scheduling preferences
    spread_across_days: bool = Field(default=True, description="Spread posts across multiple days if needed")
    max_days_ahead: int = Field(default=7, description="Maximum days ahead to schedule")
    priority: str = Field(default="normal", description="Priority: low, normal, high (affects slot selection)")
    
    source_id: Optional[str] = Field(None)
    source_system: Optional[str] = Field(None)


class SmartBulkRequest(BaseModel):
    """
    Smart bulk scheduling - submit many videos, MediaPoster allocates all optimally.
    """
    videos: List[dict] = Field(..., description="List of {video_url, title, caption}")
    platforms: List[str] = Field(..., description="Target platforms")
    account_ids: Optional[dict] = Field(None, description="Account IDs per platform")
    hashtags: List[str] = Field(default=[])
    
    # MediaPoster will optimally distribute these across time
    spread_evenly: bool = Field(default=True, description="Distribute evenly across days")
    max_per_day: Optional[int] = Field(None, description="Override max posts per day (uses platform defaults if None)")
    start_after: Optional[str] = Field(None, description="Don't schedule before this time (ISO8601)")
    
    source_system: Optional[str] = Field(None)


class ScheduleResponse(BaseModel):
    """Response after scheduling"""
    success: bool
    scheduled_posts: List[dict]
    video_id: Optional[str] = None
    message: str
    queue_analysis: Optional[dict] = None  # Info about current queue state


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


async def resolve_video_path(
    video_url: Optional[str] = None,
    video_path: Optional[str] = None,
    dest_dir: Path = None
) -> Path:
    """
    Resolve video input to a local path.
    
    Accepts EITHER:
    - video_url: Downloads from URL
    - video_path: Uses local file directly (copies to staging if needed)
    
    Returns: Path to local video file
    """
    if dest_dir is None:
        dest_dir = Path("/tmp/mediaposter_external")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    if video_path:
        # Local file - verify it exists
        local_path = Path(video_path)
        if not local_path.exists():
            raise ValueError(f"Local video file not found: {video_path}")
        
        logger.info(f"📁 Using local video: {local_path}")
        return local_path
    
    elif video_url:
        # Remote URL - download it
        logger.info(f"🌐 Downloading video from URL: {video_url[:50]}...")
        return await download_video(video_url, dest_dir)
    
    else:
        raise ValueError("Either video_url or video_path must be provided")


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
    
    # Convert hashtags list to PostgreSQL array format
    hashtags_array = hashtags if hashtags else []
    
    # Format hashtags as PostgreSQL array literal
    hashtags_pg = "{" + ",".join(f'"{h}"' for h in hashtags_array) + "}" if hashtags_array else "{}"
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO scheduled_posts 
            (content_id, clip_id, title, caption, hashtags, thumbnail_url, platform,
             account_id, account_username, platform_account_id, blotato_account_id,
             scheduled_time, scheduled_at, status, source)
            VALUES 
            (:content_id, :clip_id, :title, :caption, CAST(:hashtags AS text[]), :thumbnail_url, :platform,
             :account_id, :account_username, :platform_account_id, :blotato_account_id,
             :scheduled_time, :scheduled_at, 'scheduled', :source)
            RETURNING id
        """), {
            "content_id": content_id,
            "clip_id": content_id if is_valid_uuid(content_id) else None,
            "title": title,
            "caption": caption,
            "hashtags": hashtags_pg,
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
    1. Downloads the video from URL OR uses local file path
    2. Ingests it into MediaPoster's media database
    3. Creates scheduled posts for each target platform/time
    
    Example with URL:
    ```json
    {
        "video_url": "https://example.com/my-video.mp4",
        "title": "My Awesome Video",
        "caption": "Check this out! #trending",
        "targets": [...]
    }
    ```
    
    Example with local path (for Safari Automation):
    ```json
    {
        "video_path": "/Users/user/sora-videos/cleaned/video.mp4",
        "title": "My Awesome Video",
        "caption": "Check this out! #trending",
        "targets": [...]
    }
    ```
    """
    try:
        # Step 1: Resolve video (download from URL or use local path)
        video_path = await resolve_video_path(
            video_url=submission.video_url,
            video_path=submission.video_path
        )
        
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
        "api_version": "2.0.0",
        "endpoints": [
            "POST /api/external/submit - Submit single video with explicit times",
            "POST /api/external/bulk-schedule - Schedule multiple videos with interval",
            "POST /api/external/smart-schedule - Let MediaPoster decide optimal times",
            "POST /api/external/smart-bulk - Smart bulk scheduling",
            "GET /api/external/queue-analysis - Analyze queue for platform/account",
            "GET /api/external/capacity - Get posting capacity summary",
            "GET /api/external/status/{source_id} - Check submission status",
            "GET /api/external/accounts - List available accounts"
        ]
    }


# =============================================================================
# SMART SCHEDULING ENDPOINTS
# =============================================================================

# Default account IDs per platform (first account is default)
DEFAULT_ACCOUNTS = {
    "tiktok": "710",
    "instagram": "807",
    "youtube": "228",
    "twitter": "4151",
    "threads": "173",
    "pinterest": "173",
    "linkedin": "571",
    "facebook": "786",
    "bluesky": "201"
}


@router.post("/smart-schedule", response_model=ScheduleResponse)
async def smart_schedule_video(request: SmartScheduleRequest):
    """
    SMART scheduling - let MediaPoster decide optimal posting times.
    
    Instead of specifying exact times, you just say which platforms to target.
    MediaPoster will:
    - Analyze current schedule for each platform/account
    - Find optimal posting times that maintain consistent cadence
    - Respect platform rate limits
    - Avoid overwhelming any single account
    
    Example with URL:
    ```json
    {
        "video_url": "https://example.com/video.mp4",
        "title": "My Video",
        "caption": "Check this out!",
        "platforms": ["tiktok", "youtube", "instagram"]
    }
    ```
    
    Example with local path (Safari Automation):
    ```json
    {
        "video_path": "/path/to/local/video.mp4",
        "title": "My Video",
        "caption": "Check this out!",
        "platforms": ["tiktok", "youtube"]
    }
    ```
    
    MediaPoster responds with the optimally allocated times.
    """
    try:
        queue_manager = get_queue_manager()
        
        # Step 1: Resolve video (URL or local path)
        video_path = await resolve_video_path(
            video_url=request.video_url,
            video_path=request.video_path
        )
        
        # Step 2: Ingest to database
        video_id = await ingest_video_to_db(
            video_path, 
            request.title,
            request.source_system
        )
        
        if not video_id:
            video_id = f"ext_{uuid.uuid4().hex[:12]}"
        
        # Step 3: For each platform, find optimal slot
        scheduled_posts = []
        queue_analyses = {}
        
        for platform in request.platforms:
            # Get account ID (from request or default)
            account_id = (request.account_ids or {}).get(platform, DEFAULT_ACCOUNTS.get(platform))
            
            if not account_id:
                logger.warning(f"No account ID for platform {platform}, skipping")
                continue
            
            # Analyze queue and find optimal slot
            analysis = queue_manager.analyze_queue(platform, account_id)
            queue_analyses[platform] = {
                "posts_today": analysis.posts_today,
                "daily_capacity_remaining": analysis.daily_capacity_remaining,
                "next_available_slot": analysis.next_available_slot.isoformat()
            }
            
            # Use the next available slot from analysis
            optimal_time = analysis.next_available_slot
            
            # Create scheduled post
            post = create_scheduled_post(
                content_id=video_id,
                platform=platform,
                account_id=account_id,
                scheduled_at=optimal_time.isoformat(),
                title=request.title,
                caption=request.caption,
                hashtags=request.hashtags,
                source=request.source_system or "smart_schedule",
                thumbnail_url=None
            )
            post["allocated_time"] = optimal_time.isoformat()
            scheduled_posts.append(post)
            
            logger.info(f"🧠 Smart scheduled {platform} post for {optimal_time}")
        
        return ScheduleResponse(
            success=True,
            video_id=video_id,
            scheduled_posts=scheduled_posts,
            message=f"Smart scheduled to {len(scheduled_posts)} platform(s) at optimal times",
            queue_analysis=queue_analyses
        )
        
    except Exception as e:
        logger.error(f"Error in smart schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-bulk", response_model=ScheduleResponse)
async def smart_bulk_schedule(request: SmartBulkRequest):
    """
    SMART bulk scheduling - submit many videos, MediaPoster allocates all optimally.
    
    MediaPoster will distribute the videos across optimal time slots,
    respecting rate limits and maintaining consistent posting cadence.
    
    Example:
    ```json
    {
        "videos": [
            {"video_url": "url1", "title": "Video 1", "caption": "Caption 1"},
            {"video_url": "url2", "title": "Video 2", "caption": "Caption 2"}
        ],
        "platforms": ["tiktok", "instagram"],
        "spread_evenly": true
    }
    ```
    """
    try:
        queue_manager = get_queue_manager()
        download_dir = Path("/tmp/mediaposter_external")
        scheduled_posts = []
        
        start_after = None
        if request.start_after:
            start_after = datetime.fromisoformat(request.start_after.replace('Z', '+00:00'))
        
        for platform in request.platforms:
            account_id = (request.account_ids or {}).get(platform, DEFAULT_ACCOUNTS.get(platform))
            
            if not account_id:
                continue
            
            # Prepare video list for allocation
            video_dicts = []
            for v in request.videos:
                video_dicts.append({
                    "video_url": v.get("video_url"),
                    "title": v.get("title", "Untitled"),
                    "caption": v.get("caption", "")
                })
            
            # Let queue manager allocate optimal slots
            allocations = queue_manager.allocate_slots(
                videos=video_dicts,
                platform=platform,
                account_id=account_id,
                start_after=start_after,
                respect_requested_times=False  # Let MediaPoster decide
            )
            
            # Process each allocation
            for video, allocated_time in allocations:
                # Download and ingest
                video_path = await download_video(video["video_url"], download_dir)
                video_id = await ingest_video_to_db(video_path, video["title"], request.source_system)
                
                if not video_id:
                    video_id = f"ext_{uuid.uuid4().hex[:12]}"
                
                # Create scheduled post
                post = create_scheduled_post(
                    content_id=video_id,
                    platform=platform,
                    account_id=account_id,
                    scheduled_at=allocated_time.isoformat(),
                    title=video["title"],
                    caption=video.get("caption", "") + " " + " ".join(request.hashtags),
                    hashtags=request.hashtags,
                    source=request.source_system or "smart_bulk"
                )
                post["allocated_time"] = allocated_time.isoformat()
                scheduled_posts.append(post)
                
                logger.info(f"🧠 Smart bulk: {platform} post scheduled for {allocated_time}")
        
        return ScheduleResponse(
            success=True,
            scheduled_posts=scheduled_posts,
            message=f"Smart scheduled {len(scheduled_posts)} posts across {len(request.platforms)} platform(s)"
        )
        
    except Exception as e:
        logger.error(f"Error in smart bulk schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue-analysis")
async def get_queue_analysis(
    platform: str = Query(..., description="Platform to analyze"),
    account_id: str = Query(..., description="Account ID to analyze"),
    days_ahead: int = Query(7, description="Days to look ahead")
):
    """
    Analyze the current queue state for a specific platform/account.
    
    Returns:
    - Current posting activity (today, this week)
    - Remaining daily capacity
    - Next available posting slot
    - Recommended posting times
    """
    queue_manager = get_queue_manager()
    analysis = queue_manager.analyze_queue(platform, account_id, days_ahead)
    
    return {
        "platform": analysis.platform,
        "account_id": analysis.account_id,
        "posts_today": analysis.posts_today,
        "posts_this_week": analysis.posts_this_week,
        "daily_capacity_remaining": analysis.daily_capacity_remaining,
        "next_available_slot": analysis.next_available_slot.isoformat(),
        "existing_slots": [s.isoformat() for s in analysis.existing_slots],
        "recommended_slots": [s.isoformat() for s in analysis.recommended_slots[:10]]  # Top 10
    }


@router.get("/capacity")
async def get_posting_capacity(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    account_id: Optional[str] = Query(None, description="Filter by account")
):
    """
    Get a summary of posting capacity across all accounts.
    
    Useful for external systems to know how much capacity is available
    before submitting videos.
    """
    queue_manager = get_queue_manager()
    return queue_manager.get_posting_summary(platform, account_id)
