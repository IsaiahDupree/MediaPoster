"""
Schedule API Endpoints
CRUD operations for scheduled posts with calendar integration
"""
import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import json

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


class ScheduledPostUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    scheduled_at: Optional[str] = None
    status: Optional[str] = None


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
    """Create scheduled_posts table if it doesn't exist"""
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
            scheduled_at, status, post_type, created_at, updated_at
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
        })
    
    return {"posts": posts, "total": len(posts)}


@router.post("/create")
async def create_scheduled_post(post: ScheduledPostCreate):
    """Create a new scheduled post."""
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO scheduled_posts 
            (content_id, title, caption, hashtags, thumbnail_url, platform,
             account_id, account_username, scheduled_time, scheduled_at, post_type, status)
            VALUES 
            (:content_id, :title, :caption, :hashtags, :thumbnail_url, :platform,
             :account_id, :account_username, :scheduled_time, :scheduled_at, :post_type, 'scheduled')
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
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = NOW()")
    
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            UPDATE scheduled_posts 
            SET {', '.join(updates)}
            WHERE id = :id
            RETURNING id
        """), params)
        conn.commit()
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Post not found")
    
    return {"message": "Post updated successfully"}


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
