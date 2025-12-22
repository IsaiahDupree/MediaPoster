"""
Schedule API Endpoints
CRUD operations for scheduled posts with calendar integration
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import json

logger = logging.getLogger(__name__)

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


# =============================================================================
# MODELS
# =============================================================================

class ScheduledPostCreate(BaseModel):
    content_id: str
    title: str
    caption: str
    hashtags: List[str] = []
    platform: str
    account_id: str
    account_username: str
    scheduled_at: str
    post_type: str = "reel"
    thumbnail_url: Optional[str] = None
    blotato_account_id: Optional[str] = None  # Blotato account ID for publishing


class ScheduledPostUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    scheduled_at: Optional[str] = None
    status: Optional[str] = None
    account_id: Optional[str] = None
    account_username: Optional[str] = None


class ScheduledPost(BaseModel):
    id: str
    content_id: str
    title: str
    caption: str
    hashtags: List[str]
    thumbnail_url: Optional[str]
    platform: str
    account_id: str
    account_username: str
    account_avatar: Optional[str] = None
    scheduled_at: str
    status: str
    post_type: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# =============================================================================
# DATABASE SETUP
# =============================================================================

def get_engine():
    return create_engine(DATABASE_URL)


def ensure_table_exists():
    """Create scheduled_posts table if it doesn't exist, and add new columns"""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id SERIAL PRIMARY KEY,
                content_id TEXT,
                title TEXT NOT NULL,
                caption TEXT,
                hashtags JSONB DEFAULT '[]',
                thumbnail_url TEXT,
                platform TEXT NOT NULL,
                account_id TEXT NOT NULL,
                account_username TEXT NOT NULL,
                account_avatar TEXT,
                scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
                status TEXT DEFAULT 'scheduled',
                post_type TEXT DEFAULT 'reel',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_scheduled_posts_scheduled_at 
            ON scheduled_posts(scheduled_at)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status 
            ON scheduled_posts(status)
        """))
        
        # Add columns for unified publishing flow (if they don't exist)
        # These support the BackgroundPublisher verification and tracking
        try:
            conn.execute(text("""
                ALTER TABLE scheduled_posts 
                ADD COLUMN IF NOT EXISTS blotato_account_id TEXT,
                ADD COLUMN IF NOT EXISTS platform_post_id TEXT,
                ADD COLUMN IF NOT EXISTS platform_url TEXT,
                ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE,
                ADD COLUMN IF NOT EXISTS error_message TEXT,
                ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITH TIME ZONE,
                ADD COLUMN IF NOT EXISTS last_error TEXT,
                ADD COLUMN IF NOT EXISTS verification_status JSONB,
                ADD COLUMN IF NOT EXISTS scheduled_time TIMESTAMP WITH TIME ZONE
            """))
        except Exception as e:
            # Columns might already exist - that's fine
            logger.debug(f"Column add skipped (may already exist): {e}")
        
        conn.commit()


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/list")
async def list_scheduled_posts(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, le=500),
):
    """
    List scheduled posts with optional filters.
    Used by calendar view to display posts.
    """
    ensure_table_exists()
    engine = get_engine()
    
    where_clauses = ["1=1"]
    params = {"limit": limit}
    
    if start_date:
        where_clauses.append("scheduled_at >= :start_date")
        params["start_date"] = start_date
    
    if end_date:
        where_clauses.append("scheduled_at <= :end_date")
        params["end_date"] = end_date
    
    if platform:
        where_clauses.append("platform = :platform")
        params["platform"] = platform
    
    if status:
        where_clauses.append("status = :status")
        params["status"] = status
    
    query = f"""
        SELECT 
            id, content_id, title, caption, hashtags, thumbnail_url,
            platform, account_id, account_username, account_avatar,
            scheduled_at, status, post_type, created_at, updated_at,
            platform_url, published_at
        FROM scheduled_posts
        WHERE {' AND '.join(where_clauses)}
        ORDER BY scheduled_at ASC
        LIMIT :limit
    """
    
    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()
    
    posts = []
    for row in rows:
        posts.append({
            "id": str(row[0]),
            "contentId": row[1],
            "title": row[2],
            "caption": row[3],
            "hashtags": row[4] if isinstance(row[4], list) else json.loads(row[4] or '[]'),
            "thumbnailUrl": row[5],
            "platform": row[6],
            "accountId": row[7],
            "accountUsername": row[8],
            "accountAvatar": row[9],
            "scheduledAt": str(row[10]) if row[10] else None,
            "status": row[11],
            "postType": row[12],
            "createdAt": str(row[13]) if row[13] else None,
            "updatedAt": str(row[14]) if row[14] else None,
            "platformUrl": row[15],
            "publishedAt": str(row[16]) if row[16] else None,
        })
    
    return {"posts": posts, "total": len(posts)}


@router.post("/create")
async def create_scheduled_post(post: ScheduledPostCreate):
    """Create a new scheduled post."""
    ensure_table_exists()
    engine = get_engine()
    
    # If blotato_account_id not provided, try to look it up
    blotato_id = post.blotato_account_id or post.account_id
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO scheduled_posts 
            (content_id, title, caption, hashtags, thumbnail_url, platform,
             account_id, account_username, blotato_account_id, scheduled_time, scheduled_at, post_type, status)
            VALUES 
            (:content_id, :title, :caption, :hashtags, :thumbnail_url, :platform,
             :account_id, :account_username, :blotato_account_id, :scheduled_time, :scheduled_at, :post_type, 'scheduled')
            RETURNING id
        """), {
            "content_id": post.content_id,
            "title": post.title,
            "caption": post.caption,
            "hashtags": json.dumps(post.hashtags),
            "thumbnail_url": post.thumbnail_url,
            "platform": post.platform,
            "account_id": post.account_id,
            "account_username": post.account_username,
            "blotato_account_id": blotato_id,
            "scheduled_time": post.scheduled_at,
            "scheduled_at": post.scheduled_at,
            "post_type": post.post_type,
        })
        conn.commit()
        new_id = result.fetchone()[0]
    
    return {"id": str(new_id), "message": "Post scheduled successfully"}


@router.get("/{post_id}")
async def get_scheduled_post(post_id: str):
    """Get a single scheduled post by ID."""
    ensure_table_exists()
    engine = get_engine()
    
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT 
                id, content_id, title, caption, hashtags, thumbnail_url,
                platform, account_id, account_username, account_avatar,
                scheduled_at, status, post_type, created_at, updated_at
            FROM scheduled_posts WHERE id = :id
        """), {"id": post_id}).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "id": str(row[0]),
        "contentId": row[1],
        "title": row[2],
        "caption": row[3],
        "hashtags": row[4] if isinstance(row[4], list) else json.loads(row[4] or '[]'),
        "thumbnailUrl": row[5],
        "platform": row[6],
        "accountId": row[7],
        "accountUsername": row[8],
        "accountAvatar": row[9],
        "scheduledAt": str(row[10]) if row[10] else None,
        "status": row[11],
        "postType": row[12],
    }


@router.put("/{post_id}")
async def update_scheduled_post(post_id: str, update: ScheduledPostUpdate):
    """Update a scheduled post."""
    logger.info(f"[UpdatePost] 📥 Received update for post_id={post_id}")
    logger.info(f"[UpdatePost] 📄 Title: {update.title[:50] if update.title else 'None'}...")
    logger.info(f"[UpdatePost] 📝 Caption length: {len(update.caption) if update.caption else 0}")
    logger.info(f"[UpdatePost] 📅 Scheduled at: {update.scheduled_at}")
    
    ensure_table_exists()
    engine = get_engine()
    
    updates = []
    params = {"id": post_id}
    
    if update.title is not None:
        updates.append("title = :title")
        params["title"] = update.title
    
    if update.caption is not None:
        updates.append("caption = :caption")
        params["caption"] = update.caption
    
    if update.hashtags is not None:
        updates.append("hashtags = :hashtags")
        params["hashtags"] = json.dumps(update.hashtags)
    
    if update.scheduled_at is not None:
        updates.append("scheduled_at = :scheduled_at")
        params["scheduled_at"] = update.scheduled_at
    
    if update.status is not None:
        updates.append("status = :status")
        params["status"] = update.status
    
    if update.account_id is not None:
        updates.append("account_id = :account_id")
        params["account_id"] = update.account_id
    
    if update.account_username is not None:
        updates.append("account_username = :account_username")
        params["account_username"] = update.account_username
    
    if not updates:
        logger.warning(f"[UpdatePost] ⚠️ No fields to update for post_id={post_id}")
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = NOW()")
    
    logger.info(f"[UpdatePost] 🔄 Updating fields: {updates}")
    
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            UPDATE scheduled_posts 
            SET {', '.join(updates)}
            WHERE id = :id
            RETURNING id
        """), params)
        conn.commit()
        
        row = result.fetchone()
        if not row:
            logger.error(f"[UpdatePost] ❌ Post not found: {post_id}")
            raise HTTPException(status_code=404, detail="Post not found")
    
    logger.info(f"[UpdatePost] ✅ Successfully updated post_id={post_id}")
    return {"message": "Post updated successfully", "id": post_id}


@router.delete("/{post_id}")
async def delete_scheduled_post(post_id: str):
    """Delete a scheduled post."""
    ensure_table_exists()
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            DELETE FROM scheduled_posts WHERE id = :id RETURNING id
        """), {"id": post_id})
        conn.commit()
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Post not found")
    
    return {"message": "Post deleted successfully"}


@router.post("/{post_id}/reschedule")
async def reschedule_post(post_id: str, new_time: str = Query(..., description="New scheduled time (ISO format)")):
    """Reschedule a post to a new time (drag & drop support)."""
    ensure_table_exists()
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            UPDATE scheduled_posts 
            SET scheduled_at = :new_time, updated_at = NOW()
            WHERE id = :id AND status = 'scheduled'
            RETURNING id
        """), {"id": post_id, "new_time": new_time})
        conn.commit()
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Post not found or already posted")
    
    return {"message": "Post rescheduled successfully"}


@router.get("/stats/overview")
async def get_schedule_stats():
    """Get scheduling statistics for the calendar."""
    ensure_table_exists()
    engine = get_engine()
    
    with engine.connect() as conn:
        # Total counts by status
        status_counts = conn.execute(text("""
            SELECT status, COUNT(*) as count
            FROM scheduled_posts
            GROUP BY status
        """)).fetchall()
        
        # Posts this week
        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        week_posts = conn.execute(text("""
            SELECT COUNT(*) FROM scheduled_posts
            WHERE scheduled_at >= :week_start AND scheduled_at < :week_end
        """), {
            "week_start": week_start,
            "week_end": week_start + timedelta(days=7)
        }).scalar() or 0
        
        # Posts by platform
        platform_counts = conn.execute(text("""
            SELECT platform, COUNT(*) as count
            FROM scheduled_posts
            WHERE status = 'scheduled'
            GROUP BY platform
        """)).fetchall()
        
        # Queue length (days until last scheduled post)
        last_scheduled = conn.execute(text("""
            SELECT MAX(scheduled_at) FROM scheduled_posts WHERE status = 'scheduled'
        """)).scalar()
        
        queue_days = 0
        if last_scheduled:
            # Handle timezone-aware datetime from DB
            from datetime import timezone
            now = datetime.now(timezone.utc)
            if last_scheduled.tzinfo is None:
                last_scheduled = last_scheduled.replace(tzinfo=timezone.utc)
            queue_days = (last_scheduled - now).days
    
    return {
        "status_counts": {row[0]: row[1] for row in status_counts},
        "posts_this_week": week_posts,
        "platform_counts": {row[0]: row[1] for row in platform_counts},
        "queue_days": max(0, queue_days),
    }


@router.get("/calendar/week")
async def get_calendar_week(
    date: str = Query(..., description="Any date in the target week (YYYY-MM-DD)")
):
    """Get posts organized by day for a specific week."""
    target_date = datetime.fromisoformat(date)
    week_start = target_date - timedelta(days=target_date.weekday())
    week_end = week_start + timedelta(days=7)
    
    ensure_table_exists()
    engine = get_engine()
    
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT 
                id, title, platform, account_username, scheduled_at, status, thumbnail_url
            FROM scheduled_posts
            WHERE scheduled_at >= :start AND scheduled_at < :end
            ORDER BY scheduled_at ASC
        """), {"start": week_start, "end": week_end}).fetchall()
    
    # Organize by day
    days = {}
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        days[day_str] = []
    
    for row in rows:
        day_str = row[4].strftime("%Y-%m-%d")
        if day_str in days:
            days[day_str].append({
                "id": str(row[0]),
                "title": row[1],
                "platform": row[2],
                "accountUsername": row[3],
                "scheduledAt": str(row[4]),
                "status": row[5],
                "thumbnailUrl": row[6],
            })
    
    return {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "days": days,
    }


@router.get("/calendar/month")
async def get_calendar_month(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12)
):
    """Get posts organized by day for a specific month."""
    month_start = datetime(year, month, 1)
    if month == 12:
        month_end = datetime(year + 1, 1, 1)
    else:
        month_end = datetime(year, month + 1, 1)
    
    ensure_table_exists()
    engine = get_engine()
    
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT 
                id, title, platform, account_username, scheduled_at, status
            FROM scheduled_posts
            WHERE scheduled_at >= :start AND scheduled_at < :end
            ORDER BY scheduled_at ASC
        """), {"start": month_start, "end": month_end}).fetchall()
    
    # Organize by day
    days = {}
    current = month_start
    while current < month_end:
        days[current.strftime("%Y-%m-%d")] = []
        current += timedelta(days=1)
    
    for row in rows:
        day_str = row[4].strftime("%Y-%m-%d")
        if day_str in days:
            days[day_str].append({
                "id": str(row[0]),
                "title": row[1],
                "platform": row[2],
                "accountUsername": row[3],
                "scheduledAt": str(row[4]),
                "status": row[5],
            })
    
    return {
        "year": year,
        "month": month,
        "days": days,
    }


@router.get("/accounts/list")
async def get_posting_accounts():
    """Get accounts available for posting (from posted_content history)."""
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT 
                account_id,
                account_username,
                platform,
                COUNT(*) as post_count
            FROM posted_content 
            WHERE account_id IS NOT NULL
            GROUP BY account_id, account_username, platform
            ORDER BY post_count DESC
        """)).fetchall()
        
        accounts = []
        for row in result:
            accounts.append({
                "id": str(row[0]),
                "username": row[1] or str(row[0]),
                "platform": row[2],
                "post_count": row[3],
                "display_name": row[1] or f"Account {row[0]}",
                "avatar": None,
            })
    
    return {"accounts": accounts}


# =============================================================================
# BACKGROUND PUBLISHER ENDPOINTS
# =============================================================================

class PublishNowRequest(BaseModel):
    """Request to publish immediately using BackgroundPublisher"""
    media_id: str
    blotato_account_id: str
    platform: str
    username: str
    caption: Optional[str] = None
    title: Optional[str] = None
    hashtags: Optional[List[str]] = None
    poll_for_url: bool = True


class VerifyPublishRequest(BaseModel):
    """Request to verify a publish can succeed"""
    media_id: str
    blotato_account_id: str
    platform: str
    username: str


@router.post("/publish-now")
async def publish_now(request: PublishNowRequest):
    """
    Publish content immediately using the same verified flow as the frontend.
    
    This replicates the frontend flow:
    1. Media verification
    2. Analysis/caption retrieval
    3. Account verification
    4. Full publish (GDrive → Blotato → Platform)
    5. URL polling
    6. Posted content record storage
    """
    from services.background_publisher import get_background_publisher, PublishRequest
    
    publisher = get_background_publisher()
    
    pub_request = PublishRequest(
        media_id=request.media_id,
        blotato_account_id=request.blotato_account_id,
        platform=request.platform,
        username=request.username,
        caption=request.caption,
        title=request.title,
        hashtags=request.hashtags,
        poll_for_url=request.poll_for_url,
    )
    
    result = await publisher.publish(pub_request)
    
    return {
        "success": result.success,
        "status": result.status.value,
        "post_submission_id": result.post_submission_id,
        "platform_url": result.platform_url,
        "error": result.error,
        "verification": result.verification,
        "steps": result.steps,
    }


@router.post("/verify-publish")
async def verify_publish(request: VerifyPublishRequest):
    """
    Verify that a publish will succeed without actually publishing.
    
    Checks:
    1. Media exists and file is accessible
    2. Analysis data exists
    3. Blotato account is valid
    """
    from services.background_publisher import get_background_publisher
    
    publisher = get_background_publisher()
    
    # Run verification steps
    media_check = await publisher.verify_media(request.media_id)
    analysis_check = await publisher.verify_analysis(request.media_id)
    account_check = await publisher.verify_account(
        request.blotato_account_id,
        request.platform,
        request.username
    )
    
    all_valid = (
        media_check.get("valid", False) and
        account_check.get("valid", False)
    )
    
    return {
        "valid": all_valid,
        "media": media_check,
        "analysis": {
            "has_analysis": analysis_check.get("has_analysis", False),
            "has_transcript": bool(analysis_check.get("transcript")),
            "topics_count": len(analysis_check.get("topics", [])),
        },
        "account": account_check,
    }


@router.post("/{post_id}/publish")
async def publish_scheduled_post(post_id: str):
    """
    Publish a scheduled post immediately (instead of waiting for scheduled time).
    Uses the same verified flow as manual publishing.
    """
    ensure_table_exists()
    engine = get_engine()
    
    # Get the scheduled post
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT 
                id, content_id, title, caption, hashtags,
                platform, account_id, account_username, status
            FROM scheduled_posts WHERE id = :id
        """), {"id": post_id}).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if row[8] != 'scheduled':
        raise HTTPException(status_code=400, detail=f"Post is already {row[8]}")
    
    from services.background_publisher import get_background_publisher, PublishRequest
    
    publisher = get_background_publisher()
    
    # Parse hashtags
    hashtags = row[4]
    if isinstance(hashtags, str):
        try:
            hashtags = json.loads(hashtags)
        except:
            hashtags = []
    
    pub_request = PublishRequest(
        media_id=row[1],  # content_id
        blotato_account_id=str(row[6]),  # account_id
        platform=row[5],  # platform
        username=row[7] or "",  # account_username
        caption=row[3],  # caption
        title=row[2],  # title
        hashtags=hashtags,
        poll_for_url=True,
    )
    
    result = await publisher.publish(pub_request)
    
    # Update the post status
    with engine.connect() as conn:
        if result.success:
            conn.execute(text("""
                UPDATE scheduled_posts
                SET status = 'posted',
                    platform_post_id = :post_id,
                    platform_url = :url,
                    published_at = NOW(),
                    updated_at = NOW()
                WHERE id = :id
            """), {
                "id": post_id,
                "post_id": result.post_submission_id,
                "url": result.platform_url,
            })
        else:
            conn.execute(text("""
                UPDATE scheduled_posts
                SET status = 'failed',
                    error_message = :error,
                    updated_at = NOW()
                WHERE id = :id
            """), {
                "id": post_id,
                "error": result.error,
            })
        conn.commit()
    
    return {
        "success": result.success,
        "status": result.status.value,
        "post_submission_id": result.post_submission_id,
        "platform_url": result.platform_url,
        "error": result.error,
        "verification": result.verification,
    }


@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get the status of the background scheduler."""
    from services.post_scheduler import get_scheduler
    
    scheduler = get_scheduler()
    return scheduler.get_status()


@router.get("/scheduler/queue")
async def get_scheduler_queue(limit: int = Query(20, le=100)):
    """Get the upcoming post queue."""
    from services.post_scheduler import get_scheduler
    
    scheduler = get_scheduler()
    return {"queue": scheduler.get_queue(limit=limit)}


@router.post("/scheduler/process-now")
async def process_due_posts_now():
    """
    Manually trigger processing of due posts.
    Useful for testing or when you want immediate processing.
    """
    from services.post_scheduler import get_scheduler
    
    scheduler = get_scheduler()
    result = await scheduler.process_due_posts()
    
    return {
        "message": "Processed due posts",
        "processed": result.get("processed", 0),
        "success": result.get("success", 0),
        "failed": result.get("failed", 0),
    }
