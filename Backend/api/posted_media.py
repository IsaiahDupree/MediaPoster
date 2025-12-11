"""
Posted Media API
Fetch all videos that have been posted to creators' connected accounts
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid

from database.connection import get_db
from database.models import ScheduledPost, VideoClip, MediaCreationProject

router = APIRouter(prefix="/api/posted-media", tags=["Posted Media"])


class PostedMediaItem(BaseModel):
    """A single posted media item"""
    id: str
    title: str
    platform: str
    platform_post_id: Optional[str] = None
    platform_url: Optional[str] = None
    published_at: Optional[datetime] = None
    scheduled_time: datetime
    status: str
    thumbnail_url: Optional[str] = None
    media_type: str  # 'clip' or 'media_project'
    
    # Performance metrics (if available)
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    engagement_rate: Optional[float] = None
    
    # Source info
    clip_id: Optional[str] = None
    media_project_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class PostedMediaStats(BaseModel):
    """Stats summary for posted media"""
    total_posts: int
    posts_by_platform: dict
    posts_this_week: int
    posts_this_month: int
    most_active_platform: Optional[str] = None


class PostedMediaResponse(BaseModel):
    """Response for posted media list"""
    items: List[PostedMediaItem]
    stats: PostedMediaStats
    total: int
    page: int
    limit: int


@router.get("/list", response_model=PostedMediaResponse)
async def list_posted_media(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    status: str = Query("published", description="Filter by status (published, failed, all)"),
    days: int = Query(30, description="Number of days to look back"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all media that has been posted to connected accounts.
    Pulls from scheduled_posts table where status = 'published'
    """
    try:
        # Build base query
        query = select(ScheduledPost)
        
        # Filter by status
        if status == "published":
            query = query.filter(ScheduledPost.status == "published")
        elif status == "failed":
            query = query.filter(ScheduledPost.status == "failed")
        # else: all statuses
        
        # Filter by platform
        if platform:
            query = query.filter(ScheduledPost.platform == platform)
        
        # Filter by date range
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(ScheduledPost.scheduled_time >= cutoff_date)
        
        # Order by most recent
        query = query.order_by(desc(ScheduledPost.published_at), desc(ScheduledPost.scheduled_time))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        posts = result.scalars().all()
        
        # Transform to response items
        items = []
        for post in posts:
            # Get source content info
            title = "Untitled Post"
            thumbnail_url = None
            media_type = "unknown"
            
            if post.clip_id:
                clip_result = await db.execute(
                    select(VideoClip).filter(VideoClip.id == post.clip_id)
                )
                clip = clip_result.scalar_one_or_none()
                if clip:
                    title = clip.title or clip.filename or "Video Clip"
                    thumbnail_url = getattr(clip, 'thumbnail_path', None)
                    media_type = "clip"
            
            if post.media_project_id:
                project_result = await db.execute(
                    select(MediaCreationProject).filter(MediaCreationProject.id == post.media_project_id)
                )
                project = project_result.scalar_one_or_none()
                if project:
                    title = project.title or "Media Project"
                    thumbnail_url = project.thumbnail_url
                    media_type = "media_project"
            
            items.append(PostedMediaItem(
                id=str(post.id),
                title=title,
                platform=post.platform,
                platform_post_id=post.platform_post_id,
                platform_url=post.platform_url,
                published_at=post.published_at,
                scheduled_time=post.scheduled_time,
                status=post.status,
                thumbnail_url=thumbnail_url,
                media_type=media_type,
                clip_id=str(post.clip_id) if post.clip_id else None,
                media_project_id=str(post.media_project_id) if post.media_project_id else None,
                # Performance metrics would come from platform API sync
                views=None,
                likes=None,
                comments=None,
                shares=None,
                engagement_rate=None,
            ))
        
        # Calculate stats
        all_posts_query = select(ScheduledPost).filter(ScheduledPost.status == "published")
        all_posts_result = await db.execute(all_posts_query)
        all_posts = all_posts_result.scalars().all()
        
        # Count by platform
        platform_counts = {}
        for p in all_posts:
            platform_counts[p.platform] = platform_counts.get(p.platform, 0) + 1
        
        # Most active platform
        most_active = max(platform_counts, key=platform_counts.get) if platform_counts else None
        
        # Posts this week/month
        week_ago = datetime.utcnow() - timedelta(days=7)
        month_ago = datetime.utcnow() - timedelta(days=30)
        posts_this_week = sum(1 for p in all_posts if p.published_at and p.published_at >= week_ago)
        posts_this_month = sum(1 for p in all_posts if p.published_at and p.published_at >= month_ago)
        
        stats = PostedMediaStats(
            total_posts=len(all_posts),
            posts_by_platform=platform_counts,
            posts_this_week=posts_this_week,
            posts_this_month=posts_this_month,
            most_active_platform=most_active,
        )
        
        return PostedMediaResponse(
            items=items,
            stats=stats,
            total=total,
            page=page,
            limit=limit,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch posted media: {str(e)}")


@router.get("/platforms")
async def get_platform_breakdown(
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    """Get breakdown of posts by platform"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(ScheduledPost).filter(
            ScheduledPost.status == "published",
            ScheduledPost.scheduled_time >= cutoff_date
        )
        
        result = await db.execute(query)
        posts = result.scalars().all()
        
        platforms = {}
        for post in posts:
            if post.platform not in platforms:
                platforms[post.platform] = {
                    "count": 0,
                    "posts": [],
                }
            platforms[post.platform]["count"] += 1
            if len(platforms[post.platform]["posts"]) < 5:
                platforms[post.platform]["posts"].append({
                    "id": str(post.id),
                    "platform_url": post.platform_url,
                    "published_at": post.published_at.isoformat() if post.published_at else None,
                })
        
        return {
            "platforms": platforms,
            "total": len(posts),
            "period": f"Last {days} days",
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{post_id}")
async def get_posted_media_detail(
    post_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed info about a specific posted media"""
    try:
        post_uuid = uuid.UUID(post_id)
        
        result = await db.execute(
            select(ScheduledPost).filter(ScheduledPost.id == post_uuid)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(status_code=404, detail="Posted media not found")
        
        # Get source content
        source_info = {}
        if post.clip_id:
            clip_result = await db.execute(
                select(VideoClip).filter(VideoClip.id == post.clip_id)
            )
            clip = clip_result.scalar_one_or_none()
            if clip:
                source_info = {
                    "type": "clip",
                    "id": str(clip.id),
                    "title": clip.title,
                    "file_path": getattr(clip, 'file_path', None),
                    "thumbnail_path": getattr(clip, 'thumbnail_path', None),
                }
        
        if post.media_project_id:
            project_result = await db.execute(
                select(MediaCreationProject).filter(MediaCreationProject.id == post.media_project_id)
            )
            project = project_result.scalar_one_or_none()
            if project:
                source_info = {
                    "type": "media_project",
                    "id": str(project.id),
                    "title": project.title,
                    "thumbnail_url": project.thumbnail_url,
                    "generated_media_url": project.generated_media_url,
                }
        
        return {
            "id": str(post.id),
            "platform": post.platform,
            "platform_post_id": post.platform_post_id,
            "platform_url": post.platform_url,
            "status": post.status,
            "scheduled_time": post.scheduled_time.isoformat() if post.scheduled_time else None,
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "publish_response": post.publish_response,
            "error_message": post.last_error or post.error_message,
            "retry_count": post.retry_count,
            "source": source_info,
            "is_ai_recommended": post.is_ai_recommended,
            "recommendation_score": post.recommendation_score,
            "recommendation_reasoning": post.recommendation_reasoning,
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
