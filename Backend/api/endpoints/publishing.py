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
from database.models import VideoClip, ScheduledPost
from sqlalchemy import select, update
from loguru import logger

router = APIRouter()

class ScheduleRequest(BaseModel):
    clip_id: uuid.UUID
    platforms: List[str]
    scheduled_time: datetime
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None

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
    
    try:
        # Create scheduled post records for each platform
        scheduled_posts = []
        for platform in request.platforms:
            scheduled_post = ScheduledPost(
                clip_id=clip_id,
                media_project_id=request.media_project_id,
                platform=platform,
                scheduled_time=request.scheduled_time,
                status='scheduled'
            )
            db.add(scheduled_post)
            scheduled_posts.append(scheduled_post)
        
        await db.commit()
        
        # Refresh to get IDs
        for post in scheduled_posts:
            await db.refresh(post)
        
        # Schedule via Blotato in background if media URL available
        if media_url:
            from pathlib import Path
            content_id = str(request.media_project_id) if request.media_project_id else str(clip_id)
            background_tasks.add_task(
                _publish_via_blotato,
                str(scheduled_posts[0].id),
                content_id,
                str(media_url),
                request.platforms,
                request.scheduled_time,
                request.caption,
                request.hashtags,
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
    content_source: str = "clip"
):
    """Background task to publish via Blotato"""
    from pathlib import Path
    from modules.publishing.publisher import ContentPublisher
    from database.connection import async_session_maker
    from database.models import ScheduledPost
    from sqlalchemy import update
    from loguru import logger
    
    try:
        publisher = ContentPublisher(use_blotato=True, use_cloud_staging=True)
        
        # Calculate delay in minutes
        delay_minutes = None
        if scheduled_time > datetime.now(scheduled_time.tzinfo):
            delta = scheduled_time - datetime.now(scheduled_time.tzinfo)
            delay_minutes = int(delta.total_seconds() / 60)
        
        # Publish (works for both clips and media projects)
        result = publisher.publish_clip(
            clip_path=Path(media_path),
            platforms=platforms,
            metadata={
                'caption': caption or '',
                'hashtags': hashtags or [],
                'title': f'{content_source.title()} {content_id}'
            },
            schedule_delay_minutes=delay_minutes
        )
        
        # Update scheduled post status
        async with async_session_maker() as db:
            await db.execute(
                update(ScheduledPost)
                .where(ScheduledPost.id == uuid.UUID(post_id))
                .values(
                    status='published' if result.get('success') else 'failed',
                    platform_post_id=str(result.get('posts', {}).get('post_id', '')),
                    platform_url=result.get('posts', {}).get('url', ''),
                    published_at=datetime.now() if result.get('success') else None
                )
            )
            await db.commit()
        
        logger.success(f"Post {post_id} published successfully")
        
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
