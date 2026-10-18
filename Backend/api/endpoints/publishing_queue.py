"""
Publishing Queue API Endpoints
Manages scheduled publishing queue
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid
import logging

from database.connection import get_db
from services.publishing_queue import PublishingQueueService, QueueItem
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Request Models ====================

class QueueItemCreate(BaseModel):
    platform: str
    scheduled_for: datetime
    content_item_id: Optional[str] = None
    clip_id: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    priority: int = 0
    platform_metadata: Optional[Dict[str, Any]] = None


class QueueItemUpdate(BaseModel):
    scheduled_for: Optional[datetime] = None
    priority: Optional[int] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None


class BulkScheduleRequest(BaseModel):
    items: List[QueueItemCreate]


# ==================== Endpoints ====================

@router.get("/queue")
def get_publishing_queue(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get publishing queue (simple endpoint for /api/publishing/queue)"""
    return {"items": [], "count": 0}


@router.get("/analytics")
def get_publishing_analytics(
    db: Session = Depends(get_db)
):
    """Get publishing analytics summary"""
    return {
        "total_published": 0,
        "total_scheduled": 0,
        "success_rate": 100,
        "platforms": {}
    }


@router.post("/add")
def add_to_queue(
    request: QueueItemCreate,
    db: Session = Depends(get_db),
    http_request: Request = None  # For correlation ID
):
    """Add item to publishing queue"""
    # BUG FIX: Use standardized validation utilities
    from utils.input_validation import (
        validate_platform,
        validate_scheduled_time,
        validate_url,
        validate_priority,
        validate_uuid
    )
    from utils.error_handling import ValidationError
    
    # Get correlation ID from request state (set by middleware)
    correlation_id = getattr(http_request.state, "correlation_id", None) if http_request else None
    
    try:
        # Validate scheduled_for is in the future
        if request.scheduled_for:
            request.scheduled_for = validate_scheduled_time(request.scheduled_for, "scheduled_for")
        
        # Validate platform
        request.platform = validate_platform(request.platform)
        
        # Validate at least one content reference
        if not request.content_item_id and not request.clip_id:
            raise ValidationError(
                "Either content_item_id or clip_id must be provided",
                correlation_id=correlation_id
            )
        
        # Validate UUIDs if provided
        if request.content_item_id:
            request.content_item_id = validate_uuid(request.content_item_id, "content_item_id")
        if request.clip_id:
            request.clip_id = validate_uuid(request.clip_id, "clip_id")
        
        # Validate video_url if provided
        if request.video_url:
            request.video_url = validate_url(request.video_url, "video_url")
        
        # Validate priority range
        request.priority = validate_priority(request.priority)
        
        service = PublishingQueueService(db)
        
        item = service.add_to_queue(
            platform=request.platform,
            scheduled_for=request.scheduled_for,
            content_item_id=request.content_item_id,
            clip_id=request.clip_id,
            caption=request.caption,
            hashtags=request.hashtags,
            video_url=request.video_url,
            thumbnail_url=request.thumbnail_url,
            priority=request.priority,
            platform_metadata=request.platform_metadata,
            user_id=None  # Would come from auth
        )
        
        return  {
            "id": str(item.id),
            "status": "queued",
            "scheduled_for": item.scheduled_for.isoformat(),
            "message": "Item added to queue successfully",
            "correlation_id": correlation_id
        }
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except ValidationError as e:
        # Re-raise with correlation ID
        if correlation_id and not e.correlation_id:
            e.correlation_id = correlation_id
        raise e.to_http_exception()
    except Exception as e:
        from utils.error_handling import handle_exception
        http_exc = handle_exception(e, correlation_id, {"endpoint": "/api/publishing/add"})
        raise http_exc


@router.post("/bulk")
def bulk_schedule(
    request: BulkScheduleRequest,
    db: Session = Depends(get_db)
):
    """Add multiple items to queue"""
    service = PublishingQueueService(db)
    
    items_data = [item.dict() for item in request.items]
    created_items = service.bulk_schedule(items_data)
    
    return {
        "scheduled": len(created_items),
        "items": [{"id": str(item.id), "scheduled_for": item.scheduled_for.isoformat()} for item in created_items]
    }


@router.get("/items")
def get_queue_items(
    status: Optional[str] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get queue items with filtering and pagination"""
    service = PublishingQueueService(db)
    
    if status:
        items = service.get_items_by_status(status, limit=limit, offset=offset)
    else:
        items = service.get_next_items(limit=limit, platform=platform)
    
    return {
        "items": [
            {
                "id": str(item.id),
                "platform": item.platform,
                "status": item.status,
                "scheduled_for": item.scheduled_for.isoformat() if item.scheduled_for else None,
                "priority": item.priority,
                "caption": item.caption,
                "retry_count": item.retry_count,
                "platform_url": item.platform_url
            }
            for item in items
        ],
        "count": len(items)
    }


@router.get("/status")
def get_queue_status(db: Session = Depends(get_db)):
    """Get queue statistics"""
    service = PublishingQueueService(db)
    stats = service.get_queue_statistics()
    
    return {
        "statistics": stats,
        "timestamp": datetime.now().isoformat()
    }


@router.put("/{item_id}/retry")
def retry_item(
    item_id: str,
    db: Session = Depends(get_db)
):
    """Retry a failed queue item"""
    service = PublishingQueueService(db)
    
    success = service.retry_failed_item(item_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot retry item - max retries reached or item not found"
        )
    
    return {"message": "Item scheduled for retry", "id": item_id}


@router.put("/{item_id}/reschedule")
def reschedule_item(
    item_id: str,
    new_time: datetime,
    db: Session = Depends(get_db)
):
    """Reschedule a queued item"""
    service = PublishingQueueService(db)
    
    success = service.reschedule_item(item_id, new_time)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Item not found or not in queued status"
        )
    
    return {
        "message": "Item rescheduled",
        "id": item_id,
        "new_scheduled_time": new_time.isoformat()
    }


@router.delete("/{item_id}/cancel")
def cancel_item(
    item_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a queued item"""
    service = PublishingQueueService(db)
    
    success = service.cancel_item(item_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {"message": "Item cancelled", "id": item_id}


@router.post("/process")
def process_queue(
    platform: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Process next items in queue
    This endpoint would typically be called by a scheduler/cron job
    """
    service = PublishingQueueService(db)
    
    items = service.get_next_items(limit=limit, platform=platform)
    
    processed = []
    for item in items:
        # Mark as processing
        service.update_status(str(item.id), 'processing')
        
        # TODO: Actually publish to platform
        # For now, just simulate
        processed.append(str(item.id))
    
    return {
        "processed": len(processed),
        "items": processed,
        "message": f"Processing {len(processed)} items"
    }
