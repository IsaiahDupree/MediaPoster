"""
Posted Media API
Fetch all videos that have been posted to creators' connected accounts
Includes Instagram sync to detect already-posted content
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import uuid
import os
import hashlib
from loguru import logger

from database.connection import get_db
from database.models import ScheduledPost, VideoClip, MediaCreationProject, PostedContent, Video

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
    
    model_config = {"from_attributes": True}


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
    Pulls from both scheduled_posts and posted_content tables.
    """
    try:
        items = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # =====================================================================
        # 1. Fetch from PostedContent table (primary source for Blotato posts)
        # =====================================================================
        pc_query = select(PostedContent)
        
        if status == "published":
            pc_query = pc_query.filter(PostedContent.status == "published")
        elif status == "failed":
            pc_query = pc_query.filter(PostedContent.status == "failed")
        
        if platform:
            pc_query = pc_query.filter(func.lower(PostedContent.platform) == platform.lower())
        
        pc_query = pc_query.filter(PostedContent.posted_at >= cutoff_date)
        pc_query = pc_query.order_by(desc(PostedContent.posted_at))
        
        pc_result = await db.execute(pc_query)
        posted_contents = pc_result.scalars().all()
        
        for pc in posted_contents:
            # Build thumbnail URL from media_id if available
            thumbnail_url = None
            if pc.media_id:
                thumbnail_url = f"/api/media-db/thumbnail/{pc.media_id}"
            
            items.append(PostedMediaItem(
                id=str(pc.id),
                title=pc.caption[:50] if pc.caption else "Posted via MediaPoster",
                platform=pc.platform,
                platform_post_id=pc.platform_post_id,
                platform_url=pc.platform_url,
                published_at=pc.posted_at,
                scheduled_time=pc.posted_at or datetime.utcnow(),
                status=pc.status or "published",
                thumbnail_url=thumbnail_url,
                media_type="posted_content",
                clip_id=str(pc.media_id) if pc.media_id else None,
                media_project_id=None,
                views=pc.views,
                likes=pc.likes,
                comments=pc.comments,
                shares=pc.shares,
                engagement_rate=None,
            ))
        
        # =====================================================================
        # 2. Also fetch from ScheduledPost table (legacy/scheduled posts)
        # =====================================================================
        sp_query = select(ScheduledPost)
        
        if status == "published":
            sp_query = sp_query.filter(ScheduledPost.status == "published")
        elif status == "failed":
            sp_query = sp_query.filter(ScheduledPost.status == "failed")
        
        if platform:
            sp_query = sp_query.filter(ScheduledPost.platform == platform)
        
        sp_query = sp_query.filter(ScheduledPost.scheduled_time >= cutoff_date)
        sp_query = sp_query.order_by(desc(ScheduledPost.published_at), desc(ScheduledPost.scheduled_time))
        
        sp_result = await db.execute(sp_query)
        scheduled_posts = sp_result.scalars().all()
        
        for post in scheduled_posts:
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
                views=None,
                likes=None,
                comments=None,
                shares=None,
                engagement_rate=None,
            ))
        
        # Sort combined items by published_at
        items.sort(key=lambda x: x.published_at or datetime.min, reverse=True)
        
        # Apply pagination
        total = len(items)
        offset = (page - 1) * limit
        items = items[offset:offset + limit]
        
        # =====================================================================
        # 3. Calculate stats from both tables
        # =====================================================================
        platform_counts = {}
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        posts_this_week = 0
        posts_this_month = 0
        
        # Count from PostedContent
        for pc in posted_contents:
            platform_counts[pc.platform] = platform_counts.get(pc.platform, 0) + 1
            if pc.posted_at and pc.posted_at >= week_ago:
                posts_this_week += 1
            if pc.posted_at and pc.posted_at >= month_ago:
                posts_this_month += 1
        
        # Count from ScheduledPost
        for p in scheduled_posts:
            platform_counts[p.platform] = platform_counts.get(p.platform, 0) + 1
            if p.published_at and p.published_at >= week_ago:
                posts_this_week += 1
            if p.published_at and p.published_at >= month_ago:
                posts_this_month += 1
        
        most_active = max(platform_counts, key=platform_counts.get) if platform_counts else None
        
        stats = PostedMediaStats(
            total_posts=len(posted_contents) + len(scheduled_posts),
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
        logger.error(f"Error fetching posted media: {e}", exc_info=True)
        # Return empty result instead of crashing - frontend can handle empty state
        return PostedMediaResponse(
            items=[],
            stats=PostedMediaStats(
                total_posts=0,
                posts_by_platform={},
                posts_this_week=0,
                posts_this_month=0,
                most_active_platform=None,
            ),
            total=0,
            page=page,
            limit=limit,
        )


@router.get("/all")
async def get_all_posted_media_ids(
    days: int = Query(90, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all media IDs that have been posted.
    Returns a simple list of media IDs for quick lookup.
    Used by frontend to mark which media items have been posted.
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        posted_media_ids = set()
        
        # Get media IDs from PostedContent table
        pc_query = select(PostedContent.media_id).filter(
            PostedContent.status == "published",
            PostedContent.posted_at >= cutoff_date,
            PostedContent.media_id.isnot(None)
        )
        pc_result = await db.execute(pc_query)
        pc_ids = pc_result.scalars().all()
        for media_id in pc_ids:
            if media_id:
                posted_media_ids.add(str(media_id))
        
        # Get media IDs from ScheduledPost table (via clip_id or content_variant_id)
        sp_query = select(ScheduledPost).filter(
            ScheduledPost.status == "published",
            ScheduledPost.scheduled_time >= cutoff_date
        )
        sp_result = await db.execute(sp_query)
        scheduled_posts = sp_result.scalars().all()
        
        for post in scheduled_posts:
            # Get video_id from clip or content_variant
            try:
                if post.clip_id:
                    # Get video_id from video_clips table
                    clip_query = select(VideoClip.video_id).filter(VideoClip.id == post.clip_id)
                    clip_result = await db.execute(clip_query)
                    video_id = clip_result.scalar_one_or_none()
                    if video_id:
                        posted_media_ids.add(str(video_id))
                elif post.content_variant_id:
                    # Content variants also reference videos
                    # For now, use content_variant_id as the media_id
                    posted_media_ids.add(str(post.content_variant_id))
            except Exception as e:
                # Log but don't fail - some posts might have invalid references
                logger.warning(f"Error getting video_id for scheduled post {post.id}: {e}")
                continue
        
        return {
            "posted_media_ids": list(posted_media_ids),
            "count": len(posted_media_ids),
            "days": days
        }
        
    except Exception as e:
        logger.error(f"Error fetching all posted media IDs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch posted media IDs: {str(e)}")


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


# =============================================================================
# INSTAGRAM SYNC - Fetch posts from Instagram to detect duplicates
# =============================================================================

class InstagramSyncRequest(BaseModel):
    """Request to sync Instagram posts"""
    username: str
    max_posts: int = 50


class InstagramPostInfo(BaseModel):
    """Instagram post information"""
    post_id: str
    shortcode: str
    url: str
    caption: Optional[str] = None
    media_type: str
    thumbnail_url: Optional[str] = None
    likes: int = 0
    comments: int = 0
    views: int = 0
    posted_at: Optional[datetime] = None
    matched_media_id: Optional[str] = None  # If matched to local media
    is_duplicate: bool = False


class InstagramSyncResponse(BaseModel):
    """Response from Instagram sync"""
    username: str
    total_posts_fetched: int
    posts_synced: int
    duplicates_found: int
    posts: List[InstagramPostInfo]


@router.post("/instagram/sync")
async def sync_instagram_posts(
    request: InstagramSyncRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync posts from Instagram account to detect which local media has already been posted.
    Uses RapidAPI Instagram service to fetch posts.
    """
    try:
        from services.instagram_analytics import InstagramAnalytics
        
        logger.info(f"[Instagram Sync] Starting sync for @{request.username}")
        
        # Initialize Instagram analytics
        ig = InstagramAnalytics()
        
        # Get user ID from username
        user_id = await ig.get_user_id_from_username(request.username)
        if not user_id:
            raise HTTPException(status_code=404, detail=f"Instagram user @{request.username} not found")
        
        # Fetch user's media
        media_data = await ig.get_user_media(user_id, max_items=request.max_posts)
        ig_posts = media_data.get("items", [])
        
        logger.info(f"[Instagram Sync] Fetched {len(ig_posts)} posts from @{request.username}")
        
        # Get all local media for comparison
        local_media_result = await db.execute(select(Video))
        local_media = local_media_result.scalars().all()
        
        # Get existing posted content for this platform
        existing_posts = await db.execute(
            select(PostedContent).where(PostedContent.platform == "instagram")
        )
        existing_platform_posts = {p.platform_post_id: p for p in existing_posts.scalars().all()}
        
        synced_posts = []
        duplicates_found = 0
        posts_synced = 0
        
        for ig_post in ig_posts:
            post_id = str(ig_post.get("media_id", ""))
            shortcode = ig_post.get("shortcode", "")
            caption = ig_post.get("caption", "") or ""
            
            # Check if already tracked
            is_already_tracked = post_id in existing_platform_posts
            
            # Try to match with local media by caption similarity or filename
            matched_media_id = None
            is_duplicate = False
            
            for media in local_media:
                # Match by caption containing filename (without extension)
                filename_base = os.path.splitext(media.filename or "")[0].lower()
                if filename_base and len(filename_base) > 3:
                    if filename_base in caption.lower():
                        matched_media_id = str(media.id)
                        is_duplicate = True
                        break
                
                # Match by existing media_id reference in PostedContent
                if post_id in existing_platform_posts:
                    existing = existing_platform_posts[post_id]
                    if existing.media_id:
                        matched_media_id = str(existing.media_id)
                        is_duplicate = True
                        break
            
            # If not already tracked, create PostedContent record
            if not is_already_tracked and shortcode:
                posted_at_ts = ig_post.get("taken_at")
                posted_at = datetime.fromtimestamp(posted_at_ts, tz=timezone.utc) if posted_at_ts else None
                
                new_posted = PostedContent(
                    platform="instagram",
                    platform_post_id=post_id,
                    platform_url=f"https://www.instagram.com/p/{shortcode}/",
                    account_username=request.username,
                    caption=caption[:500] if caption else None,
                    views=ig_post.get("play_count", 0),
                    likes=ig_post.get("like_count", 0),
                    comments=ig_post.get("comment_count", 0),
                    status="published",
                    posted_at=posted_at,
                    media_id=uuid.UUID(matched_media_id) if matched_media_id else None
                )
                db.add(new_posted)
                posts_synced += 1
            
            if is_duplicate:
                duplicates_found += 1
            
            # Build response item
            posted_at_ts = ig_post.get("taken_at")
            synced_posts.append(InstagramPostInfo(
                post_id=post_id,
                shortcode=shortcode,
                url=f"https://www.instagram.com/p/{shortcode}/" if shortcode else "",
                caption=caption[:200] if caption else None,
                media_type="video" if ig_post.get("media_type") == 2 else "image",
                thumbnail_url=ig_post.get("thumbnail_url"),
                likes=ig_post.get("like_count", 0),
                comments=ig_post.get("comment_count", 0),
                views=ig_post.get("play_count", 0),
                posted_at=datetime.fromtimestamp(posted_at_ts, tz=timezone.utc) if posted_at_ts else None,
                matched_media_id=matched_media_id,
                is_duplicate=is_duplicate
            ))
        
        await db.commit()
        
        logger.success(f"[Instagram Sync] Synced {posts_synced} new posts, found {duplicates_found} duplicates")
        
        return InstagramSyncResponse(
            username=request.username,
            total_posts_fetched=len(ig_posts),
            posts_synced=posts_synced,
            duplicates_found=duplicates_found,
            posts=synced_posts
        )
        
    except ImportError as e:
        logger.error(f"[Instagram Sync] Instagram service not available: {e}")
        raise HTTPException(status_code=503, detail="Instagram service not configured. Check RAPIDAPI_KEY.")
    except Exception as e:
        logger.error(f"[Instagram Sync] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instagram/check-duplicate/{media_id}")
async def check_if_posted_to_instagram(
    media_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a specific media item has already been posted to Instagram.
    Returns matching Instagram posts if found.
    """
    try:
        media_uuid = uuid.UUID(media_id)
        
        # Check PostedContent for this media on Instagram
        result = await db.execute(
            select(PostedContent).where(
                PostedContent.media_id == media_uuid,
                PostedContent.platform == "instagram"
            )
        )
        posts = result.scalars().all()
        
        if posts:
            return {
                "media_id": media_id,
                "is_posted": True,
                "post_count": len(posts),
                "posts": [
                    {
                        "platform_post_id": p.platform_post_id,
                        "platform_url": p.platform_url,
                        "posted_at": p.posted_at.isoformat() if p.posted_at else None,
                        "views": p.views,
                        "likes": p.likes,
                        "comments": p.comments
                    }
                    for p in posts
                ]
            }
        else:
            return {
                "media_id": media_id,
                "is_posted": False,
                "post_count": 0,
                "posts": []
            }
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")


@router.get("/instagram/posted-media")
async def get_instagram_posted_media(
    username: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all media that has been posted to Instagram.
    Returns list of local media IDs that have Instagram posts.
    """
    query = select(PostedContent).where(
        PostedContent.platform == "instagram",
        PostedContent.media_id.isnot(None)
    )
    
    if username:
        query = query.where(PostedContent.account_username == username)
    
    result = await db.execute(query.order_by(desc(PostedContent.posted_at)))
    posts = result.scalars().all()
    
    return {
        "total": len(posts),
        "posted_media_ids": list(set(str(p.media_id) for p in posts if p.media_id)),
        "posts": [
            {
                "media_id": str(p.media_id) if p.media_id else None,
                "platform_post_id": p.platform_post_id,
                "platform_url": p.platform_url,
                "caption": p.caption[:100] if p.caption else None,
                "posted_at": p.posted_at.isoformat() if p.posted_at else None,
                "views": p.views,
                "likes": p.likes,
                "comments": p.comments
            }
            for p in posts
        ]
    }
