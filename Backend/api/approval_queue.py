"""
Human in the Loop - Approval Queue API
Gives users control over what gets posted, where, and when.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from database.connection import get_db

router = APIRouter(prefix="/api/approval-queue", tags=["Approval Queue"])


# ============================================================================
# ENUMS & MODELS
# ============================================================================

class ApprovalStatus(str, Enum):
    PENDING = "pending"           # Waiting for review
    APPROVED = "approved"         # Ready to post
    REJECTED = "rejected"         # Will not be posted
    NEEDS_CHANGES = "needs_changes"  # Requires modifications
    SCHEDULED = "scheduled"       # Approved and scheduled
    POSTED = "posted"             # Already published


class ContentType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    CAROUSEL = "carousel"
    TEXT = "text"
    STORY = "story"
    REEL = "reel"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class QueueItem(BaseModel):
    """An item in the approval queue"""
    id: str
    content_id: str
    content_type: ContentType
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    media_url: Optional[str] = None
    
    # Target platforms
    platforms: List[str]
    platform_settings: Dict[str, Dict[str, Any]] = {}
    
    # Status & workflow
    status: ApprovalStatus
    priority: Priority = Priority.NORMAL
    
    # AI recommendations
    ai_score: Optional[float] = None
    ai_recommendations: List[str] = []
    ai_best_time: Optional[str] = None
    ai_hashtags: List[str] = []
    ai_caption_suggestions: List[str] = []
    
    # Review info
    reviewer_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    requested_changes: List[str] = []
    
    # Scheduling
    scheduled_time: Optional[datetime] = None
    auto_schedule: bool = False
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class QueueStats(BaseModel):
    """Statistics about the approval queue"""
    total: int
    pending: int
    approved: int
    rejected: int
    needs_changes: int
    scheduled: int
    posted: int
    by_platform: Dict[str, int]
    by_priority: Dict[str, int]
    avg_review_time_hours: float
    oldest_pending_hours: Optional[float]


class ApprovalAction(BaseModel):
    """Action to take on a queue item"""
    action: str  # approve, reject, request_changes, schedule
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    requested_changes: List[str] = []
    scheduled_time: Optional[datetime] = None
    platforms: Optional[List[str]] = None  # Override platforms
    platform_settings: Optional[Dict[str, Dict]] = None


class BulkAction(BaseModel):
    """Bulk action on multiple items"""
    item_ids: List[str]
    action: str
    notes: Optional[str] = None
    scheduled_time: Optional[datetime] = None


class ControlSettings(BaseModel):
    """User control settings for automation"""
    require_approval: bool = True
    auto_approve_high_score: bool = False
    auto_approve_threshold: float = 85.0
    notify_on_new_content: bool = True
    notify_on_schedule: bool = True
    default_review_priority: Priority = Priority.NORMAL
    max_posts_per_day: int = 10
    blackout_hours: List[int] = []  # Hours when posting is disabled
    require_caption_review: bool = True
    require_hashtag_review: bool = True
    platforms_requiring_approval: List[str] = []  # Empty = all platforms


# ============================================================================
# IN-MEMORY STORAGE (Replace with DB in production)
# ============================================================================

# Queue storage
approval_queue: Dict[str, QueueItem] = {}
control_settings: ControlSettings = ControlSettings()

# Generate some sample data
def _init_sample_data():
    import random
    
    platforms = ["instagram", "tiktok", "youtube", "facebook", "linkedin"]
    titles = [
        "5 Tips for Better Content",
        "Behind the Scenes Look",
        "Weekly Update",
        "Product Showcase",
        "Tutorial: Getting Started",
        "Q&A Session Highlights",
        "Monthly Recap",
        "Special Announcement",
    ]
    
    for i in range(8):
        item_id = str(uuid.uuid4())
        target_platforms = random.sample(platforms, random.randint(1, 3))
        
        status = random.choice([
            ApprovalStatus.PENDING,
            ApprovalStatus.PENDING,
            ApprovalStatus.PENDING,
            ApprovalStatus.APPROVED,
            ApprovalStatus.NEEDS_CHANGES,
        ])
        
        approval_queue[item_id] = QueueItem(
            id=item_id,
            content_id=f"content-{i+1}",
            content_type=random.choice(list(ContentType)),
            title=titles[i],
            description=f"Sample content #{i+1} waiting for review",
            platforms=target_platforms,
            status=status,
            priority=random.choice(list(Priority)),
            ai_score=random.uniform(60, 95),
            ai_recommendations=[
                "Add more engaging hook in first 3 seconds",
                "Consider adding captions for accessibility",
                "Trending audio would increase reach",
            ][:random.randint(1, 3)],
            ai_best_time=f"{random.randint(9, 21)}:00",
            ai_hashtags=["#content", "#creator", "#viral", "#trending"][:random.randint(2, 4)],
            ai_caption_suggestions=[
                "Check out our latest update! 🚀",
                "You won't believe what happened next...",
                "This changes everything 👀",
            ],
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
            updated_at=datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
            requested_changes=["Update thumbnail", "Shorten intro"] if status == ApprovalStatus.NEEDS_CHANGES else [],
        )

_init_sample_data()


# ============================================================================
# QUEUE ENDPOINTS
# ============================================================================

@router.get("/items", response_model=List[QueueItem])
async def get_queue_items(
    status: Optional[ApprovalStatus] = None,
    platform: Optional[str] = None,
    priority: Optional[Priority] = None,
    sort_by: str = Query("created_at", description="created_at, priority, ai_score"),
    order: str = Query("desc", description="asc or desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get items in the approval queue with filtering"""
    items = list(approval_queue.values())
    
    # Filter
    if status:
        items = [i for i in items if i.status == status]
    if platform:
        items = [i for i in items if platform in i.platforms]
    if priority:
        items = [i for i in items if i.priority == priority]
    
    # Sort
    priority_order = {Priority.URGENT: 0, Priority.HIGH: 1, Priority.NORMAL: 2, Priority.LOW: 3}
    
    if sort_by == "priority":
        items.sort(key=lambda x: priority_order.get(x.priority, 2), reverse=(order == "desc"))
    elif sort_by == "ai_score":
        items.sort(key=lambda x: x.ai_score or 0, reverse=(order == "desc"))
    else:
        items.sort(key=lambda x: x.created_at, reverse=(order == "desc"))
    
    return items[offset:offset + limit]


@router.get("/stats", response_model=QueueStats)
async def get_queue_stats():
    """Get statistics about the approval queue"""
    items = list(approval_queue.values())
    
    # Count by status
    pending = sum(1 for i in items if i.status == ApprovalStatus.PENDING)
    approved = sum(1 for i in items if i.status == ApprovalStatus.APPROVED)
    rejected = sum(1 for i in items if i.status == ApprovalStatus.REJECTED)
    needs_changes = sum(1 for i in items if i.status == ApprovalStatus.NEEDS_CHANGES)
    scheduled = sum(1 for i in items if i.status == ApprovalStatus.SCHEDULED)
    posted = sum(1 for i in items if i.status == ApprovalStatus.POSTED)
    
    # Count by platform
    by_platform: Dict[str, int] = {}
    for item in items:
        for platform in item.platforms:
            by_platform[platform] = by_platform.get(platform, 0) + 1
    
    # Count by priority
    by_priority = {p.value: sum(1 for i in items if i.priority == p) for p in Priority}
    
    # Calculate review time
    reviewed_items = [i for i in items if i.reviewed_at]
    if reviewed_items:
        avg_review_time = sum(
            (i.reviewed_at - i.created_at).total_seconds() / 3600
            for i in reviewed_items
        ) / len(reviewed_items)
    else:
        avg_review_time = 0
    
    # Oldest pending
    pending_items = [i for i in items if i.status == ApprovalStatus.PENDING]
    if pending_items:
        oldest = min(pending_items, key=lambda x: x.created_at)
        oldest_hours = (datetime.utcnow() - oldest.created_at).total_seconds() / 3600
    else:
        oldest_hours = None
    
    return QueueStats(
        total=len(items),
        pending=pending,
        approved=approved,
        rejected=rejected,
        needs_changes=needs_changes,
        scheduled=scheduled,
        posted=posted,
        by_platform=by_platform,
        by_priority=by_priority,
        avg_review_time_hours=round(avg_review_time, 1),
        oldest_pending_hours=round(oldest_hours, 1) if oldest_hours else None,
    )


@router.get("/item/{item_id}", response_model=QueueItem)
async def get_queue_item(item_id: str):
    """Get a specific queue item"""
    item = approval_queue.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/item/{item_id}/action")
async def take_action(
    item_id: str,
    action: ApprovalAction,
    background_tasks: BackgroundTasks,
):
    """Take an action on a queue item (approve, reject, request changes, schedule)"""
    item = approval_queue.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    now = datetime.utcnow()
    
    if action.action == "approve":
        item.status = ApprovalStatus.APPROVED
        item.reviewer_notes = action.notes
        item.reviewed_at = now
        
        # If schedule time provided, schedule it
        if action.scheduled_time:
            item.status = ApprovalStatus.SCHEDULED
            item.scheduled_time = action.scheduled_time
        
        # Override platforms if specified
        if action.platforms:
            item.platforms = action.platforms
        if action.platform_settings:
            item.platform_settings = action.platform_settings
            
    elif action.action == "reject":
        item.status = ApprovalStatus.REJECTED
        item.rejection_reason = action.rejection_reason
        item.reviewer_notes = action.notes
        item.reviewed_at = now
        
    elif action.action == "request_changes":
        item.status = ApprovalStatus.NEEDS_CHANGES
        item.requested_changes = action.requested_changes
        item.reviewer_notes = action.notes
        item.reviewed_at = now
        
    elif action.action == "schedule":
        if not action.scheduled_time:
            raise HTTPException(status_code=400, detail="scheduled_time required for schedule action")
        item.status = ApprovalStatus.SCHEDULED
        item.scheduled_time = action.scheduled_time
        item.reviewer_notes = action.notes
        item.reviewed_at = now
        
        # Override platforms if specified
        if action.platforms:
            item.platforms = action.platforms
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action.action}")
    
    item.updated_at = now
    
    return {
        "success": True,
        "item_id": item_id,
        "new_status": item.status.value,
        "message": f"Item {action.action}d successfully",
    }


@router.post("/bulk-action")
async def bulk_action(action: BulkAction):
    """Take action on multiple items at once"""
    results = []
    
    for item_id in action.item_ids:
        item = approval_queue.get(item_id)
        if not item:
            results.append({"item_id": item_id, "success": False, "error": "Not found"})
            continue
        
        now = datetime.utcnow()
        
        if action.action == "approve":
            item.status = ApprovalStatus.APPROVED
            if action.scheduled_time:
                item.status = ApprovalStatus.SCHEDULED
                item.scheduled_time = action.scheduled_time
        elif action.action == "reject":
            item.status = ApprovalStatus.REJECTED
        elif action.action == "schedule":
            if action.scheduled_time:
                item.status = ApprovalStatus.SCHEDULED
                item.scheduled_time = action.scheduled_time
        
        item.reviewer_notes = action.notes
        item.reviewed_at = now
        item.updated_at = now
        
        results.append({"item_id": item_id, "success": True, "new_status": item.status.value})
    
    return {
        "processed": len(results),
        "successful": sum(1 for r in results if r["success"]),
        "results": results,
    }


@router.delete("/item/{item_id}")
async def delete_queue_item(item_id: str):
    """Remove an item from the queue"""
    if item_id not in approval_queue:
        raise HTTPException(status_code=404, detail="Item not found")
    
    del approval_queue[item_id]
    return {"success": True, "message": "Item deleted"}


@router.post("/item/{item_id}/resubmit")
async def resubmit_item(item_id: str):
    """Resubmit an item for review (after making changes)"""
    item = approval_queue.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.status = ApprovalStatus.PENDING
    item.requested_changes = []
    item.rejection_reason = None
    item.reviewed_at = None
    item.updated_at = datetime.utcnow()
    
    return {"success": True, "message": "Item resubmitted for review"}


# ============================================================================
# CONTROL SETTINGS ENDPOINTS
# ============================================================================

@router.get("/settings", response_model=ControlSettings)
async def get_control_settings():
    """Get current control settings"""
    return control_settings


@router.put("/settings")
async def update_control_settings(settings: ControlSettings):
    """Update control settings"""
    global control_settings
    control_settings = settings
    return {"success": True, "settings": control_settings}


@router.get("/settings/presets")
async def get_settings_presets():
    """Get preset configurations for different control levels"""
    return {
        "presets": [
            {
                "id": "full_control",
                "name": "Full Control",
                "description": "Review and approve every piece of content before posting",
                "settings": {
                    "require_approval": True,
                    "auto_approve_high_score": False,
                    "require_caption_review": True,
                    "require_hashtag_review": True,
                    "platforms_requiring_approval": [],
                }
            },
            {
                "id": "trust_ai",
                "name": "Trust AI Recommendations",
                "description": "Auto-approve content with high AI scores",
                "settings": {
                    "require_approval": True,
                    "auto_approve_high_score": True,
                    "auto_approve_threshold": 85.0,
                    "require_caption_review": False,
                    "require_hashtag_review": False,
                }
            },
            {
                "id": "platform_specific",
                "name": "Platform-Specific Review",
                "description": "Only require approval for specific platforms",
                "settings": {
                    "require_approval": True,
                    "auto_approve_high_score": True,
                    "auto_approve_threshold": 75.0,
                    "platforms_requiring_approval": ["linkedin", "youtube"],
                }
            },
            {
                "id": "fully_automated",
                "name": "Fully Automated",
                "description": "Let AI handle everything (not recommended)",
                "settings": {
                    "require_approval": False,
                    "auto_approve_high_score": True,
                    "auto_approve_threshold": 60.0,
                    "notify_on_schedule": True,
                }
            },
        ]
    }


# ============================================================================
# PLATFORM CONTROL ENDPOINTS
# ============================================================================

@router.get("/platforms")
async def get_platform_controls():
    """Get per-platform control settings"""
    return {
        "platforms": {
            "instagram": {
                "enabled": True,
                "require_approval": True,
                "max_posts_per_day": 3,
                "allowed_content_types": ["image", "video", "carousel", "reel", "story"],
                "auto_hashtags": True,
                "auto_caption": False,
            },
            "tiktok": {
                "enabled": True,
                "require_approval": True,
                "max_posts_per_day": 5,
                "allowed_content_types": ["video"],
                "auto_hashtags": True,
                "auto_caption": True,
            },
            "youtube": {
                "enabled": True,
                "require_approval": True,
                "max_posts_per_day": 1,
                "allowed_content_types": ["video"],
                "auto_hashtags": False,
                "auto_caption": False,
            },
            "linkedin": {
                "enabled": True,
                "require_approval": True,
                "max_posts_per_day": 2,
                "allowed_content_types": ["image", "video", "text"],
                "auto_hashtags": False,
                "auto_caption": False,
            },
            "facebook": {
                "enabled": True,
                "require_approval": False,
                "max_posts_per_day": 2,
                "allowed_content_types": ["image", "video", "text"],
                "auto_hashtags": True,
                "auto_caption": True,
            },
            "twitter": {
                "enabled": True,
                "require_approval": False,
                "max_posts_per_day": 10,
                "allowed_content_types": ["image", "video", "text"],
                "auto_hashtags": True,
                "auto_caption": True,
            },
        }
    }


@router.put("/platforms/{platform}")
async def update_platform_control(platform: str, settings: Dict[str, Any]):
    """Update control settings for a specific platform"""
    # In production, save to database
    return {
        "success": True,
        "platform": platform,
        "settings": settings,
    }


# ============================================================================
# ACTIVITY LOG
# ============================================================================

@router.get("/activity")
async def get_activity_log(
    limit: int = Query(50, ge=1, le=200),
    action_type: Optional[str] = None,
):
    """Get recent activity in the approval queue"""
    # Generate sample activity
    activities = [
        {
            "id": "act-1",
            "action": "approved",
            "item_title": "Weekly Update",
            "platforms": ["instagram", "tiktok"],
            "user": "admin",
            "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        },
        {
            "id": "act-2",
            "action": "rejected",
            "item_title": "Draft Post",
            "reason": "Image quality too low",
            "user": "admin",
            "timestamp": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
        },
        {
            "id": "act-3",
            "action": "scheduled",
            "item_title": "Product Showcase",
            "platforms": ["youtube"],
            "scheduled_for": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "user": "admin",
            "timestamp": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
        },
        {
            "id": "act-4",
            "action": "request_changes",
            "item_title": "Tutorial Video",
            "changes": ["Add intro", "Fix audio levels"],
            "user": "admin",
            "timestamp": (datetime.utcnow() - timedelta(hours=8)).isoformat(),
        },
        {
            "id": "act-5",
            "action": "auto_approved",
            "item_title": "Behind the Scenes",
            "reason": "AI score 92% exceeded threshold",
            "platforms": ["instagram"],
            "timestamp": (datetime.utcnow() - timedelta(hours=12)).isoformat(),
        },
    ]
    
    if action_type:
        activities = [a for a in activities if a["action"] == action_type]
    
    return {"activities": activities[:limit]}
