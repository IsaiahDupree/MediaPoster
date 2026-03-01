"""
Publishing Controls API
========================
Queue management, rate limiting, and runtime config for Blotato video publishing.

All endpoints designed to be callable from external servers
(Safari Automation, dashboard, mobile app, etc.)
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from services.video_publishing_controller import (
    get_publishing_controller,
    PublishingConfig,
    QueueItem,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/publish-controls", tags=["Publishing Controls"])


# =============================================================================
# Request / Response Models
# =============================================================================

class UpdateConfigRequest(BaseModel):
    """Update runtime publishing configuration."""
    global_enabled: Optional[bool] = None
    global_videos_per_day: Optional[int] = Field(None, ge=1, le=100)
    global_posts_per_day: Optional[int] = Field(None, ge=1, le=200)
    platform_limits: Optional[Dict[str, int]] = None
    posting_windows: Optional[Dict[str, str]] = None
    min_interval_minutes: Optional[int] = Field(None, ge=0, le=1440)
    priority_order: Optional[List[str]] = None
    updated_by: str = "api"


class EnqueueVideoRequest(BaseModel):
    """Add a video to the publish queue."""
    video_url: str = Field(..., description="Media URL (Google Drive, local path, etc.)")
    caption: str = Field(..., description="Post caption")
    platform: str = Field(..., description="Target platform (tiktok, instagram, etc.)")
    account_id: str = Field(..., description="Blotato account ID")
    title: str = Field(default="", description="Display title")
    account_username: str = Field(default="", description="Account username for display")
    hashtags: Optional[List[str]] = None
    priority: int = Field(default=5, ge=1, le=10, description="1=highest, 10=lowest")
    scheduled_for: Optional[datetime] = Field(None, description="When to publish (null=next slot)")
    video_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BulkEnqueueRequest(BaseModel):
    """Add multiple videos to the queue."""
    items: List[EnqueueVideoRequest]


class RescheduleRequest(BaseModel):
    """Reschedule a queue item."""
    scheduled_for: datetime


class PriorityRequest(BaseModel):
    """Change item priority."""
    priority: int = Field(..., ge=1, le=10)


class UpdateQueueItemRequest(BaseModel):
    """Update fields on a queue item."""
    caption: Optional[str] = None
    title: Optional[str] = None
    hashtags: Optional[List[str]] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    scheduled_for: Optional[datetime] = None


# =============================================================================
# Config Endpoints
# =============================================================================

@router.get("/config")
async def get_config():
    """
    Get current publishing configuration.

    Returns global limits, per-platform limits, posting windows, and interval settings.
    """
    controller = get_publishing_controller()
    return controller.get_config().to_dict()


@router.patch("/config")
async def update_config(request: UpdateConfigRequest):
    """
    Update publishing configuration at runtime.

    Only provided fields are updated; omitted fields remain unchanged.

    Example:
    ```json
    {
        "global_videos_per_day": 6,
        "platform_limits": {"tiktok": 3, "instagram": 2, "youtube": 1}
    }
    ```
    """
    controller = get_publishing_controller()
    kwargs = {k: v for k, v in request.model_dump().items() if v is not None}
    config = controller.update_config(**kwargs)
    return {"updated": True, "config": config.to_dict()}


@router.post("/config/pause")
async def pause_publishing():
    """
    Pause ALL publishing globally.

    No posts will be published until resumed. Queue items remain intact.
    """
    controller = get_publishing_controller()
    config = controller.pause_all()
    return {
        "status": "paused",
        "global_enabled": config.global_enabled,
        "message": "All publishing paused. Queue items preserved. POST /config/resume to re-enable.",
    }


@router.post("/config/resume")
async def resume_publishing():
    """
    Resume publishing after a global pause.
    """
    controller = get_publishing_controller()
    config = controller.resume_all()
    return {
        "status": "resumed",
        "global_enabled": config.global_enabled,
        "message": "Publishing resumed.",
    }


# =============================================================================
# Queue Endpoints
# =============================================================================

@router.get("/queue")
async def get_queue(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List items in the video publish queue.

    Filters:
    - **platform**: tiktok, instagram, youtube, twitter, threads, etc.
    - **status**: queued, scheduled, publishing, published, failed, paused, cancelled
    """
    controller = get_publishing_controller()
    items = controller.get_queue(
        platform=platform, status=status, limit=limit, offset=offset
    )
    return {
        "items": [i.to_dict() for i in items],
        "count": len(items),
        "filters": {"platform": platform, "status": status},
    }


@router.get("/queue/stats")
async def get_queue_stats():
    """
    Queue statistics: counts by status, by platform, upcoming 24h, next item.
    """
    controller = get_publishing_controller()
    return controller.get_queue_stats()


@router.post("/queue")
async def enqueue_video(request: EnqueueVideoRequest):
    """
    Add a video to the publish queue.

    The video will be published according to its priority, scheduled time,
    and the current rate limits.
    """
    controller = get_publishing_controller()
    item = controller.enqueue_video(
        video_url=request.video_url,
        caption=request.caption,
        platform=request.platform,
        account_id=request.account_id,
        title=request.title,
        account_username=request.account_username,
        hashtags=request.hashtags,
        priority=request.priority,
        scheduled_for=request.scheduled_for,
        video_id=request.video_id,
        thumbnail_url=request.thumbnail_url,
        metadata=request.metadata,
    )
    return {"queued": True, "item": item.to_dict()}


@router.post("/queue/bulk")
async def enqueue_bulk(request: BulkEnqueueRequest):
    """
    Add multiple videos to the queue at once.
    """
    controller = get_publishing_controller()
    items = []
    for req in request.items:
        item = controller.enqueue_video(
            video_url=req.video_url,
            caption=req.caption,
            platform=req.platform,
            account_id=req.account_id,
            title=req.title,
            account_username=req.account_username,
            hashtags=req.hashtags,
            priority=req.priority,
            scheduled_for=req.scheduled_for,
            video_id=req.video_id,
            thumbnail_url=req.thumbnail_url,
            metadata=req.metadata,
        )
        items.append(item)
    return {"queued": len(items), "items": [i.to_dict() for i in items]}


@router.get("/queue/{item_id}")
async def get_queue_item(item_id: str):
    """Get a single queue item by ID."""
    controller = get_publishing_controller()
    item = controller.get_queue_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")
    return item.to_dict()


@router.patch("/queue/{item_id}")
async def update_queue_item(item_id: str, request: UpdateQueueItemRequest):
    """
    Update a queue item's caption, title, hashtags, priority, or scheduled time.
    """
    controller = get_publishing_controller()
    kwargs = {k: v for k, v in request.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")

    ok = controller.update_queue_item(item_id, **kwargs)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")

    item = controller.get_queue_item(item_id)
    return {"updated": True, "item": item.to_dict() if item else None}


@router.patch("/queue/{item_id}/priority")
async def set_priority(item_id: str, request: PriorityRequest):
    """Change an item's priority (1=highest, 10=lowest)."""
    controller = get_publishing_controller()
    ok = controller.set_priority(item_id, request.priority)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")
    return {"item_id": item_id, "priority": request.priority}


@router.post("/queue/{item_id}/reschedule")
async def reschedule_item(item_id: str, request: RescheduleRequest):
    """Reschedule a queue item to a new time."""
    controller = get_publishing_controller()
    ok = controller.reschedule_item(item_id, request.scheduled_for)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")
    return {"item_id": item_id, "scheduled_for": request.scheduled_for.isoformat()}


@router.post("/queue/{item_id}/pause")
async def pause_item(item_id: str):
    """Pause a single queue item (keeps it in queue but won't publish)."""
    controller = get_publishing_controller()
    ok = controller.pause_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")
    return {"item_id": item_id, "status": "paused"}


@router.post("/queue/{item_id}/resume")
async def resume_item(item_id: str):
    """Resume a paused queue item."""
    controller = get_publishing_controller()
    ok = controller.resume_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")
    return {"item_id": item_id, "status": "queued"}


@router.post("/queue/{item_id}/cancel")
async def cancel_item(item_id: str):
    """Cancel a queue item."""
    controller = get_publishing_controller()
    ok = controller.cancel_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")
    return {"item_id": item_id, "status": "cancelled"}


@router.post("/queue/{item_id}/retry")
async def retry_item(item_id: str):
    """Retry a failed queue item."""
    controller = get_publishing_controller()
    ok = controller.retry_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")
    return {"item_id": item_id, "status": "queued", "retry_count": 0}


@router.delete("/queue/{item_id}")
async def delete_item(item_id: str):
    """Permanently delete a queue item."""
    controller = get_publishing_controller()
    ok = controller.delete_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Queue item '{item_id}' not found")
    return {"deleted": True, "item_id": item_id}


# =============================================================================
# Dashboard / Status Endpoints
# =============================================================================

@router.get("/status")
async def get_publishing_status():
    """
    Full publishing status for dashboard.

    Returns config, daily summary (global + per-platform usage), and queue stats.
    Designed for external server polling.
    """
    controller = get_publishing_controller()
    return controller.get_status()


@router.get("/daily-summary")
async def get_daily_summary():
    """
    Today's publishing summary.

    Shows: global published count, per-platform counts, remaining budget.
    """
    controller = get_publishing_controller()
    return controller.get_daily_summary()


@router.get("/history")
async def get_publishing_history(
    days: int = 7,
    platform: Optional[str] = None,
    limit: int = 100,
):
    """
    Published video history.

    Filter by date range and platform.
    """
    controller = get_publishing_controller()
    items = controller.get_history(days=days, platform=platform, limit=limit)
    return {"items": [i.to_dict() for i in items], "count": len(items)}


# =============================================================================
# Queue Processing — dequeue + publish via Blotato
# =============================================================================

@router.post("/process")
async def process_next(background_tasks: BackgroundTasks):
    """
    Process the next queued item: dequeue → upload to cloud → Blotato → platform.

    Atomically claims the next ready item and publishes it via PublishService.
    Respects rate limits and posting windows.
    """
    controller = get_publishing_controller()
    result = await controller.process_next_item()
    return result


@router.post("/process/batch")
async def process_batch(max_items: int = 5):
    """
    Process up to `max_items` from the queue in sequence.

    Stops early if the queue is empty or rate limits are hit.
    """
    controller = get_publishing_controller()
    result = await controller.process_batch(max_items=min(max_items, 20))
    return result


# =============================================================================
# Rate Check (for external servers to query before publishing)
# =============================================================================

@router.get("/can-publish/{platform}")
async def can_publish(platform: str):
    """
    Check if publishing is allowed for a platform right now.

    Returns whether rate limits, global pause, and interval checks pass.
    Useful for external servers to check before attempting to publish.
    """
    controller = get_publishing_controller()
    allowed = controller.can_publish(platform)
    config = controller.get_config()
    daily = controller.get_daily_summary()
    platform_info = daily.get("platforms", {}).get(platform, {})

    return {
        "platform": platform,
        "can_publish": allowed,
        "global_enabled": config.global_enabled,
        "platform_published_today": platform_info.get("published_today", 0),
        "platform_daily_limit": platform_info.get("daily_limit", "unlimited"),
        "platform_remaining": platform_info.get("remaining", "unlimited"),
        "global_remaining": daily.get("global_remaining", 0),
    }
