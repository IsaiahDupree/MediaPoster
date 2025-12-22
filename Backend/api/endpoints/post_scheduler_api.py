"""
Post Scheduler API Endpoints
Control and monitor the background post scheduler
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from services.post_scheduler import get_scheduler, start_scheduler, stop_scheduler

router = APIRouter()


class SchedulerStatusResponse(BaseModel):
    is_running: bool
    check_interval_seconds: int
    max_retries: int
    blotato_configured: bool
    status_counts: dict
    upcoming_posts: int
    due_now: int
    recent_failures_24h: int


class QueueItem(BaseModel):
    id: int
    title: Optional[str]
    platform: str
    account_username: Optional[str]
    scheduled_at: Optional[str]
    status: str
    retry_count: int
    last_error: Optional[str]


class ProcessResult(BaseModel):
    processed: int
    success: int
    failed: int


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """Get the current scheduler status and statistics"""
    scheduler = get_scheduler()
    return scheduler.get_status()


@router.post("/start")
async def start_post_scheduler(background_tasks: BackgroundTasks):
    """Start the background post scheduler"""
    scheduler = get_scheduler()
    
    if scheduler.is_running:
        return {"message": "Scheduler is already running", "status": "running"}
    
    # Start in background
    background_tasks.add_task(scheduler.start)
    
    return {"message": "Scheduler started", "status": "starting"}


@router.post("/stop")
async def stop_post_scheduler():
    """Stop the background post scheduler"""
    scheduler = get_scheduler()
    
    if not scheduler.is_running:
        return {"message": "Scheduler is not running", "status": "stopped"}
    
    scheduler.stop()
    
    return {"message": "Scheduler stopped", "status": "stopped"}


@router.post("/process-now", response_model=ProcessResult)
async def process_due_posts_now():
    """
    Manually trigger processing of all due posts.
    Useful for testing or catching up on missed posts.
    """
    scheduler = get_scheduler()
    result = await scheduler.process_due_posts()
    return result


@router.get("/queue", response_model=List[QueueItem])
async def get_post_queue(limit: int = 20):
    """Get the upcoming post queue"""
    scheduler = get_scheduler()
    return scheduler.get_queue(limit=limit)


@router.post("/retry/{post_id}")
async def retry_failed_post(post_id: int):
    """Manually retry a failed post"""
    from sqlalchemy import create_engine, text
    import os
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if post exists and is failed
        result = conn.execute(text("""
            SELECT status FROM scheduled_posts WHERE id = :id
        """), {"id": post_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if result[0] not in ('failed', 'scheduled'):
            raise HTTPException(status_code=400, detail=f"Cannot retry post with status: {result[0]}")
        
        # Reset for retry
        conn.execute(text("""
            UPDATE scheduled_posts
            SET 
                status = 'scheduled',
                retry_count = 0,
                scheduled_at = NOW(),
                last_error = NULL,
                error_message = NULL,
                updated_at = NOW()
            WHERE id = :id
        """), {"id": post_id})
        conn.commit()
    
    return {"message": f"Post {post_id} queued for retry", "post_id": post_id}


@router.delete("/cancel/{post_id}")
async def cancel_scheduled_post(post_id: int):
    """Cancel a scheduled post"""
    from sqlalchemy import create_engine, text
    import os
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT status FROM scheduled_posts WHERE id = :id
        """), {"id": post_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if result[0] == 'posted':
            raise HTTPException(status_code=400, detail="Cannot cancel already posted content")
        
        conn.execute(text("""
            UPDATE scheduled_posts
            SET status = 'cancelled', updated_at = NOW()
            WHERE id = :id
        """), {"id": post_id})
        conn.commit()
    
    return {"message": f"Post {post_id} cancelled", "post_id": post_id}


@router.get("/history")
async def get_publish_history(
    limit: int = 50,
    status: Optional[str] = None
):
    """Get recent publish history"""
    from sqlalchemy import create_engine, text
    import os
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        query = """
            SELECT 
                id, title, platform, account_username,
                scheduled_at, published_at, status,
                platform_post_id, platform_url, error_message
            FROM scheduled_posts
            WHERE 1=1
        """
        params = {"limit": limit}
        
        if status:
            query += " AND status = :status"
            params["status"] = status
        
        query += " ORDER BY COALESCE(published_at, scheduled_at) DESC LIMIT :limit"
        
        result = conn.execute(text(query), params)
        
        history = []
        for row in result.fetchall():
            history.append({
                "id": row[0],
                "title": row[1],
                "platform": row[2],
                "account_username": row[3],
                "scheduled_at": str(row[4]) if row[4] else None,
                "published_at": str(row[5]) if row[5] else None,
                "status": row[6],
                "platform_post_id": row[7],
                "platform_url": row[8],
                "error_message": row[9]
            })
        
        return {"history": history, "total": len(history)}


@router.put("/settings")
async def update_scheduler_settings(
    check_interval: Optional[int] = None,
    max_retries: Optional[int] = None
):
    """Update scheduler settings"""
    scheduler = get_scheduler()
    
    if check_interval is not None:
        if check_interval < 10:
            raise HTTPException(status_code=400, detail="Check interval must be at least 10 seconds")
        scheduler.check_interval = check_interval
    
    if max_retries is not None:
        if max_retries < 0 or max_retries > 10:
            raise HTTPException(status_code=400, detail="Max retries must be between 0 and 10")
        scheduler.max_retries = max_retries
    
    return {
        "message": "Settings updated",
        "check_interval": scheduler.check_interval,
        "max_retries": scheduler.max_retries
    }
