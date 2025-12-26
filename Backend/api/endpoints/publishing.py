"""
Publishing API Endpoints
Manage post scheduling and distribution
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import uuid

from database.connection import get_db
from database.models import VideoClip, ScheduledPost, VideoAnalysis, Video
from sqlalchemy import select, update
from loguru import logger
from services.event_bus import EventBus, Topics
from services.background_publisher import get_background_publisher
from config.platform_limits import get_platform_limits, PLATFORM_LIMITS
from typing import Dict

router = APIRouter()


# =============================================================================
# QUEUE ENDPOINTS
# =============================================================================

@router.get("/queue/pending")
async def get_pending_queue():
    """Get pending posts in the publishing queue."""
    try:
        from sqlalchemy import create_engine, text
        import os
        
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            try:
                result = conn.execute(text("""
                    SELECT id, platform, scheduled_time, status, caption
                    FROM scheduled_posts
                    WHERE status IN ('scheduled', 'pending', 'queued')
                    AND scheduled_time > NOW()
                    ORDER BY scheduled_time ASC
                    LIMIT 50
                """)).fetchall()
                
                posts = [
                    {
                        'id': str(row[0]),
                        'platform': row[1],
                        'scheduled_time': row[2].isoformat() if row[2] else None,
                        'status': row[3],
                        'caption': row[4]
                    }
                    for row in result
                ]
                return {'pending': posts, 'count': len(posts)}
            except Exception as e:
                # Table might not exist
                return {'pending': [], 'count': 0}
    except Exception as e:
        return {'pending': [], 'count': 0, 'error': str(e)}


class ScheduleRequest(BaseModel):
    clip_id: Optional[uuid.UUID] = None
    media_project_id: Optional[uuid.UUID] = None
    platforms: List[str]
    scheduled_time: datetime
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    title: Optional[str] = None  # Proper title, not filename
    idempotency_key: Optional[str] = None  # Prevent duplicate scheduling
    platform_account_ids: Optional[Dict[str, str]] = None  # Platform -> Blotato account ID mapping

class PostResponse(BaseModel):
    post_id: str
    clip_id: uuid.UUID
    status: str
    scheduled_time: Optional[datetime]
    platforms: List[str]

@router.post("/schedule", response_model=PostResponse)
async def schedule_post(
    request: ScheduleRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Schedule a clip or media project for publishing"""
    from database.models import MediaCreationProject
    
    # Check if scheduling a media project or a clip
    if request.media_project_id:
        # Schedule media creation project
        result = await db.execute(
            select(MediaCreationProject).filter(MediaCreationProject.id == request.media_project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Media project not found")
        
        if project.status != 'ready':
            raise HTTPException(status_code=400, detail=f"Project status is {project.status}, must be 'ready' to schedule")
        
        # Use generated media URL or thumbnail from project
        media_url = project.generated_media_url or project.thumbnail_url
        if not media_url:
            raise HTTPException(status_code=400, detail="Project has no media URL to publish")
        
        clip_id = None
        content_source = "media_project"
    elif request.clip_id:
        # Schedule clip (existing logic)
        result = await db.execute(
            select(VideoClip).filter(VideoClip.id == request.clip_id)
        )
        clip = result.scalar_one_or_none()
        
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        media_url = getattr(clip, 'file_path', None)
        clip_id = request.clip_id
        content_source = "clip"
    else:
        raise HTTPException(status_code=400, detail="Either clip_id or media_project_id must be provided")
    
    # BUG FIX: Validate scheduled time is in the future (with clock drift buffer)
    from datetime import timezone
    now = datetime.now(timezone.utc)
    if request.scheduled_time.tzinfo is None:
        request.scheduled_time = request.scheduled_time.replace(tzinfo=timezone.utc)
    
    # Allow 1 second buffer for clock drift between systems
    time_diff = (request.scheduled_time - now).total_seconds()
    if time_diff < -1.0:
        raise HTTPException(
            status_code=400,
            detail="Cannot schedule post in the past. Please use a future time."
        )
    elif time_diff < 1.0:
        # Schedule within 1 second of now - warn but allow (might be clock drift)
        logger.warning(
            f"Scheduling post very close to current time (diff: {time_diff:.2f}s). "
            f"This might be due to clock drift."
        )
    
    # Validate platforms list
    if not request.platforms or len(request.platforms) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one platform must be specified"
        )
    
    try:
        # Fetch proper title and caption if not provided
        proper_title = request.title
        proper_caption = request.caption
        
        # BUG FIX: Verify media file exists and analysis before scheduling
        analysis = None
        if clip_id:
            clip_result = await db.execute(
                select(VideoClip).filter(VideoClip.id == clip_id)
            )
            clip = clip_result.scalar_one_or_none()
            
            if not clip:
                raise HTTPException(status_code=404, detail="Clip not found")
            
            # Verify media file exists
            if clip.file_path:
                from pathlib import Path
                file_path = Path(clip.file_path)
                if not file_path.exists():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Media file not found: {clip.file_path}. Please ensure the file exists before scheduling."
                    )
            
            if clip.video_id:
                # Get video title
                video_result = await db.execute(
                    select(Video).filter(Video.id == clip.video_id)
                )
                video = video_result.scalar_one_or_none()
                if video and video.title and not proper_title:
                    proper_title = video.title
                
                # Get caption from analysis (platform_content preferred)
                analysis_result = await db.execute(
                    select(VideoAnalysis).filter(VideoAnalysis.video_id == clip.video_id)
                )
                analysis = analysis_result.scalar_one_or_none()
                
                # BUG FIX: Check analysis completeness
                if not analysis:
                    logger.warning(
                        f"⚠️ Scheduling post for clip {clip_id} without analysis. "
                        f"Post will use generic caption. Consider running analysis first."
                    )
                else:
                    # Check analysis completeness
                    analysis_warnings = []
                    if not analysis.transcript:
                        analysis_warnings.append("missing transcript")
                    if not analysis.topics or len(analysis.topics) == 0:
                        analysis_warnings.append("missing topics")
                    if not analysis.platform_content:
                        analysis_warnings.append("missing platform_content")
                    
                    if analysis_warnings:
                        logger.warning(
                            f"⚠️ Analysis for clip {clip_id} is incomplete: {', '.join(analysis_warnings)}. "
                            f"Post may use fallback captions."
                        )
                
                if analysis and not proper_caption:
                    # Try platform_content first, then hooks, then topics
                    if analysis.platform_content:
                        import json
                        try:
                            pc_list = analysis.platform_content if isinstance(analysis.platform_content, list) else json.loads(analysis.platform_content) if isinstance(analysis.platform_content, str) else []
                            for pc in pc_list:
                                if pc.get('platform') == request.platforms[0] if request.platforms else 'tiktok':
                                    proper_caption = pc.get('description') or pc.get('caption')
                                    break
                        except (json.JSONDecodeError, Exception):
                            pass
                        
                        # Fallback to hooks or topics, NOT transcript
                        if not proper_caption:
                            if analysis.hooks and len(analysis.hooks) > 0:
                                proper_caption = analysis.hooks[0]
                            elif analysis.topics and len(analysis.topics) > 0:
                                proper_caption = f"Discover: {', '.join(analysis.topics[:2])}"
            except Exception as e:
                logger.warning(f"Could not fetch title/caption from analysis: {e}")
        
        # Fallback to generic values if still missing
        if not proper_title or proper_title.startswith(('IMG_', 'VID_', 'MOV_')) or len(proper_title) < 5:
            proper_title = "Check this out"
            if not request.title:  # Only warn if user didn't provide title
                logger.warning(
                    f"⚠️ Using generic title for clip {clip_id}. "
                    f"Consider running analysis or providing a custom title."
                )
        if not proper_caption:
            proper_caption = "Check out this content!"
            if not request.caption:  # Only warn if user didn't provide caption
                logger.warning(
                    f"⚠️ Using generic caption for clip {clip_id}. "
                    f"Consider running analysis or providing a custom caption."
                )
        
        # BUG FIX: Validate platform-specific requirements before scheduling
        validation_errors = []
        for platform in request.platforms:
            platform_lower = platform.lower()
            limits = get_platform_limits(platform_lower)
            
            # Validate caption length
            if proper_caption and len(proper_caption) > limits.description_max:
                validation_errors.append(
                    f"{platform}: Caption too long ({len(proper_caption)}/{limits.description_max} chars)"
                )
            
            # Validate hashtag count
            if request.hashtags:
                hashtag_count = len(request.hashtags)
                if hashtag_count > limits.hashtags_max:
                    validation_errors.append(
                        f"{platform}: Too many hashtags ({hashtag_count}/{limits.hashtags_max})"
                    )
            
            # Validate title length
            if proper_title and len(proper_title) > limits.title_max:
                validation_errors.append(
                    f"{platform}: Title too long ({len(proper_title)}/{limits.title_max} chars)"
                )
        
        if validation_errors:
            raise HTTPException(
                status_code=400,
                detail=f"Platform validation failed: {'; '.join(validation_errors)}"
            )
        
        # BUG FIX: Check idempotency key to prevent duplicate scheduling
        if request.idempotency_key:
            # Check if post with this idempotency key already exists
            existing = await db.execute(
                select(ScheduledPost).filter(
                    ScheduledPost.id == request.idempotency_key  # Using idempotency_key as a unique constraint
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail="Post with this idempotency key already scheduled"
                )
        
        # BUG FIX: Verify platform accounts before scheduling (if account IDs provided)
        if request.platform_account_ids:
            publisher = get_background_publisher()
            for platform, account_id in request.platform_account_ids.items():
                # Try to get username from request or use placeholder
                username = "unknown"  # Would need to fetch from account
                account_check = await publisher.verify_account(
                    str(account_id),
                    platform,
                    username
                )
                if not account_check.get("valid"):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid Blotato account for {platform}: {account_check.get('error', 'Account not found')}"
                    )
        
        # Create scheduled post records for each platform
        scheduled_posts = []
        for platform in request.platforms:
            scheduled_post = ScheduledPost(
                clip_id=clip_id,
                media_project_id=request.media_project_id,
                platform=platform,
                scheduled_time=request.scheduled_time,
                status='scheduled',
                title=proper_title,  # Store proper title, not filename
                caption=proper_caption,  # Store proper caption, not transcript
                hashtags=request.hashtags or []  # Store hashtags
            )
            db.add(scheduled_post)
            scheduled_posts.append(scheduled_post)
        
        await db.commit()
        
        # Refresh to get IDs
        for post in scheduled_posts:
            await db.refresh(post)
        
        # Emit SCHEDULE_CREATED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.SCHEDULE_CREATED, {
                "post_id": str(scheduled_posts[0].id),
                "platforms": request.platforms,
                "scheduled_time": request.scheduled_time.isoformat(),
                "content_source": content_source,
            })
            logger.info(f"[PubSub] Emitted SCHEDULE_CREATED for {scheduled_posts[0].id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit schedule event: {e}")
        
        # Schedule via Blotato in background if media URL available
        # IMPORTANT: Create a background task for EACH platform, not just the first one
        if media_url:
            from pathlib import Path
            content_id = str(request.media_project_id) if request.media_project_id else str(clip_id)
            # Create background task for each scheduled post (one per platform)
            for scheduled_post in scheduled_posts:
                background_tasks.add_task(
                    _publish_via_blotato,
                    str(scheduled_post.id),
                    content_id,
                    str(media_url),
                    [scheduled_post.platform],  # Single platform per post
                    request.scheduled_time,
                    proper_caption,  # Use the proper caption we fetched
                    request.hashtags,
                    proper_title,  # Use the proper title we fetched
                    content_source
                )
        
        return PostResponse(
            post_id=str(scheduled_posts[0].id),
            clip_id=clip_id or uuid.uuid4(),  # Use placeholder if media project
            status="scheduled",
            scheduled_time=request.scheduled_time,
            platforms=request.platforms
        )
        
    except Exception as e:
        logger.error(f"Error scheduling post: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def _publish_via_blotato(
    post_id: str,
    content_id: str,
    media_path: str,
    platforms: List[str],
    scheduled_time: datetime,
    caption: Optional[str],
    hashtags: Optional[List[str]],
    title: Optional[str] = None,
    content_source: str = "clip"
):
    """Background task to schedule/publish via Blotato
    
    IMPORTANT: This function should only be called for FUTURE scheduled posts.
    For posts that are due now, let the scheduler worker handle them to avoid
    double publishing.
    """
    from pathlib import Path
    from modules.publishing.publisher import ContentPublisher
    from database.connection import async_session_maker
    from database.models import ScheduledPost, VideoClip, VideoAnalysis
    from sqlalchemy import update, select
    from loguru import logger
    from datetime import timezone
    
    try:
        # SAFEGUARD 1: Check if post is already being processed or published
        async with async_session_maker() as db:
            result = await db.execute(
                select(ScheduledPost).filter(ScheduledPost.id == uuid.UUID(post_id))
            )
            post = result.scalar_one_or_none()
            
            if not post:
                logger.error(f"Post {post_id} not found")
                return
            
            # If already published or publishing, skip
            if post.status in ('published', 'publishing'):
                logger.warning(f"Post {post_id} already {post.status}, skipping")
                return
            
            # SAFEGUARD 2: Atomically update status to 'publishing' to prevent concurrent processing
            # Only update if status is still 'scheduled'
            update_result = await db.execute(
                update(ScheduledPost)
                .where(
                    ScheduledPost.id == uuid.UUID(post_id),
                    ScheduledPost.status == 'scheduled'  # Only update if still scheduled
                )
                .values(status='publishing')
            )
            await db.commit()
            
            # If no rows were updated, another process is already handling this post
            if update_result.rowcount == 0:
                logger.warning(f"Post {post_id} status changed by another process, skipping")
                return
        
        # SAFEGUARD 3: Only handle future posts here, let scheduler handle due posts
        now = datetime.now(timezone.utc)
        if scheduled_time.tzinfo is None:
            scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
        
        # If post is due now or in the past, let the scheduler handle it
        if scheduled_time <= now:
            logger.info(f"Post {post_id} is due now, letting scheduler handle it")
            # Only reset status if we set it to 'publishing' (atomic check-and-reset)
            # This prevents resetting a post that's already being processed by another worker
            async with async_session_maker() as db:
                reset_result = await db.execute(
                    update(ScheduledPost)
                    .where(
                        ScheduledPost.id == uuid.UUID(post_id),
                        ScheduledPost.status == 'publishing'  # Only reset if we set it
                    )
                    .values(status='scheduled')
                )
                await db.commit()
                
                if reset_result.rowcount == 0:
                    logger.warning(
                        f"Post {post_id} status changed by another process "
                        f"(not 'publishing'), skipping reset"
                    )
                else:
                    logger.info(f"Reset post {post_id} status from 'publishing' to 'scheduled' for scheduler")
            return
        
        publisher = ContentPublisher(use_blotato=True, use_cloud_staging=True)
        
        # Calculate delay in minutes for future posts
        delta = scheduled_time - now
        delay_minutes = int(delta.total_seconds() / 60)
        
        # Fetch proper title from database if not provided
        proper_title = title
        if not proper_title or proper_title.startswith(('IMG_', 'VID_', 'MOV_')) or len(proper_title) < 5:
            try:
                async with async_session_maker() as db:
                    from database.models import Video
                    # Try to get title from clip's video
                    if content_source == "clip":
                        result = await db.execute(
                            select(VideoClip).filter(VideoClip.id == uuid.UUID(content_id))
                        )
                        clip = result.scalar_one_or_none()
                        if clip and clip.video_id:
                            # Get video title first
                            video_result = await db.execute(
                                select(Video).filter(Video.id == clip.video_id)
                            )
                            video = video_result.scalar_one_or_none()
                            if video and video.title:
                                proper_title = video.title
                            else:
                                # Fallback to analysis topics if no video title
                                analysis_result = await db.execute(
                                    select(VideoAnalysis).filter(VideoAnalysis.video_id == clip.video_id)
                                )
                                analysis = analysis_result.scalar_one_or_none()
                                if analysis and analysis.topics and len(analysis.topics) > 0:
                                    proper_title = analysis.topics[0]
            except Exception as e:
                logger.warning(f"Could not fetch title from database: {e}")
        
        # Fallback to generic title if still no good title
        if not proper_title or proper_title.startswith(('IMG_', 'VID_', 'MOV_')) or len(proper_title) < 5:
            proper_title = "Check this out"  # Generic fallback, not filename
        
        # Publish (works for both clips and media projects)
        result = publisher.publish_clip(
            clip_path=Path(media_path),
            platforms=platforms,
            metadata={
                'caption': caption or '',
                'hashtags': hashtags or [],
                'title': proper_title  # Use proper title, not filename or content_id
            },
            schedule_delay_minutes=delay_minutes
        )
        
        # Update scheduled post status
        # Note: For scheduled posts, status should be 'scheduled' (Blotato will publish later)
        # Only mark as 'published' if it was published immediately (shouldn't happen for future posts)
        async with async_session_maker() as db:
            if result.get('success'):
                # If Blotato scheduled it successfully, keep status as 'scheduled'
                # The scheduler will update to 'published' when Blotato actually publishes it
                await db.execute(
                    update(ScheduledPost)
                    .where(ScheduledPost.id == uuid.UUID(post_id))
                    .values(
                        status='scheduled',  # Keep as scheduled, Blotato will publish later
                        platform_post_id=str(result.get('posts', {}).get('post_id', '')),
                        platform_url=result.get('posts', {}).get('url', '')
                        # Don't set published_at yet - that happens when actually published
                    )
                )
                logger.success(f"Post {post_id} scheduled with Blotato successfully")
            else:
                # Mark as failed if scheduling failed
                await db.execute(
                    update(ScheduledPost)
                    .where(ScheduledPost.id == uuid.UUID(post_id))
                    .values(
                        status='failed',
                        error_message=str(result.get('error', 'Unknown error'))
                    )
                )
            await db.commit()
        
    except Exception as e:
        logger.error(f"Error publishing post {post_id}: {e}")
        # Update status to failed
        async with async_session_maker() as db:
            await db.execute(
                update(ScheduledPost)
                .where(ScheduledPost.id == uuid.UUID(post_id))
                .values(
                    status='failed',
                    error_message=str(e)
                )
            )
            await db.commit()

@router.get("/scheduled")
async def get_scheduled_posts(
    limit: int = 50,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get scheduled posts - alias for common endpoint pattern"""
    from sqlalchemy import select
    from database.models import ScheduledPost
    from datetime import datetime, timedelta, timezone
    
    try:
        query = select(ScheduledPost).order_by(ScheduledPost.scheduled_time.desc()).limit(limit)
        
        if status:
            query = query.where(ScheduledPost.status == status)
        
        result = await db.execute(query)
        posts = list(result.scalars().all())
        
        return [
            {
                "id": str(post.id),
                "clip_id": str(post.clip_id) if post.clip_id else None,
                "platform": post.platform,
                "scheduled_time": post.scheduled_time.isoformat() if post.scheduled_time else None,
                "status": post.status,
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "platform_post_id": post.platform_post_id,
                "platform_url": post.platform_url,
            }
            for post in posts
        ]
    except Exception as e:
        from loguru import logger
        logger.error(f"Error fetching scheduled posts: {e}")
        return []

@router.get("/calendar")
async def get_calendar_posts(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get scheduled posts for calendar view"""
    from sqlalchemy import select
    from database.models import ScheduledPost
    from datetime import datetime, timedelta, timezone
    
    try:
        # Default to last 30 days and next 30 days if not provided
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc) + timedelta(days=30)
        
        query = select(ScheduledPost).where(
            ScheduledPost.scheduled_time >= start_date
        ).where(
            ScheduledPost.scheduled_time <= end_date
        ).order_by(ScheduledPost.scheduled_time)
        
        result = await db.execute(query)
        posts = list(result.scalars().all())  # Convert to list immediately
        
        return [
            {
                "id": str(post.id),
                "clip_id": str(post.clip_id) if post.clip_id else None,
                "content_variant_id": str(post.content_variant_id) if post.content_variant_id else None,
                "platform": post.platform,
                "scheduled_time": post.scheduled_time.isoformat(),
                "status": post.status,
                "caption": None,  # Would come from clip or variant
                "thumbnail_url": None,  # Would come from clip
                "error_message": post.error_message,
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "platform_post_id": post.platform_post_id,
                "platform_url": post.platform_url,
                "retry_count": post.retry_count,
            }
            for post in posts
        ]
    except Exception as e:
        from loguru import logger
        logger.error(f"Error fetching calendar posts: {e}")
        return []
