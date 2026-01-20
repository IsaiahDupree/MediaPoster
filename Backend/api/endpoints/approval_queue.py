"""
Approval Queue API (AUTO-005)
==============================
API endpoints for human approval workflow
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from services.approval_queue import (
    get_approval_queue,
    ApprovalStatus,
    ApprovalPriority
)
from loguru import logger

router = APIRouter(prefix="/api/approval-queue", tags=["Approval Queue"])


# Request/Response Models

class AddItemRequest(BaseModel):
    """Request to add item to approval queue"""
    content_id: str = Field(..., description="Content ID")
    content_type: str = Field(..., description="Content type (post, video, comment, dm)")
    content_data: Dict[str, Any] = Field(..., description="Content data")
    priority: ApprovalPriority = Field(ApprovalPriority.MEDIUM, description="Priority level")
    quality_score: float = Field(0.0, description="AI quality score (0-1)", ge=0.0, le=1.0)
    engagement_prediction: float = Field(0.0, description="Predicted engagement (0-1)", ge=0.0, le=1.0)
    brand_safety_score: float = Field(0.0, description="Brand safety score (0-1)", ge=0.0, le=1.0)
    expires_in_hours: Optional[int] = Field(24, description="Hours until expiry (null = no expiry)", ge=1)
    assigned_to: Optional[str] = Field(None, description="User to assign to")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ReviewRequest(BaseModel):
    """Request to review (approve/reject) an item"""
    reviewed_by: str = Field(..., description="Reviewer identifier (user ID or email)")
    feedback: str = Field("", description="Feedback or reason")


class RejectRequest(ReviewRequest):
    """Request to reject an item"""
    allow_retry: bool = Field(True, description="Allow retry after rejection")


class AssignRequest(BaseModel):
    """Request to assign an item"""
    assigned_to: str = Field(..., description="User to assign to")


class ApprovalItemResponse(BaseModel):
    """Approval item response"""
    id: str
    content_id: str
    content_type: str
    content_data: Dict[str, Any]
    status: str
    priority: str
    created_at: str
    expires_at: Optional[str]
    assigned_to: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[str]
    feedback: str
    quality_score: float
    engagement_prediction: float
    brand_safety_score: float
    metadata: Dict[str, Any]


# API Endpoints

@router.post("/items", response_model=Dict[str, str])
async def add_item(request: AddItemRequest):
    """
    Add an item to the approval queue

    Content requiring human review can be added to the queue with priority,
    AI scores, and expiration settings.

    **Example Request:**
    ```json
    {
        "content_id": "post-123",
        "content_type": "post",
        "content_data": {
            "text": "Check out this amazing product!",
            "platform": "tiktok",
            "media_url": "https://..."
        },
        "priority": "high",
        "quality_score": 0.85,
        "engagement_prediction": 0.78,
        "brand_safety_score": 0.95,
        "expires_in_hours": 24,
        "assigned_to": "reviewer@example.com"
    }
    ```

    **Response:**
    ```json
    {
        "item_id": "abc-123-def-456",
        "message": "Item added to approval queue"
    }
    ```
    """
    try:
        queue = get_approval_queue()

        item_id = await queue.add_item(
            content_id=request.content_id,
            content_type=request.content_type,
            content_data=request.content_data,
            priority=request.priority,
            quality_score=request.quality_score,
            engagement_prediction=request.engagement_prediction,
            brand_safety_score=request.brand_safety_score,
            expires_in_hours=request.expires_in_hours,
            assigned_to=request.assigned_to,
            metadata=request.metadata
        )

        return {
            "item_id": item_id,
            "message": "Item added to approval queue"
        }

    except Exception as e:
        logger.error(f"Error adding item to queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items/pending", response_model=List[ApprovalItemResponse])
async def get_pending_items(
    priority: Optional[ApprovalPriority] = Query(None, description="Filter by priority"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
    limit: int = Query(50, description="Maximum items to return", ge=1, le=200)
):
    """
    Get pending items from the approval queue

    Returns items sorted by priority (urgent > high > medium > low)
    and creation time (oldest first).

    **Example Response:**
    ```json
    [
        {
            "id": "abc-123",
            "content_id": "post-123",
            "content_type": "post",
            "content_data": {...},
            "status": "pending",
            "priority": "high",
            "created_at": "2026-01-20T12:00:00Z",
            "expires_at": "2026-01-21T12:00:00Z",
            "assigned_to": "reviewer@example.com",
            "quality_score": 0.85,
            "engagement_prediction": 0.78,
            "brand_safety_score": 0.95,
            "metadata": {}
        }
    ]
    ```
    """
    try:
        queue = get_approval_queue()

        items = await queue.get_pending_items(
            priority=priority,
            content_type=content_type,
            assigned_to=assigned_to,
            limit=limit
        )

        return [ApprovalItemResponse(**item.to_dict()) for item in items]

    except Exception as e:
        logger.error(f"Error getting pending items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items/{item_id}", response_model=ApprovalItemResponse)
async def get_item(item_id: str):
    """
    Get a specific approval item by ID
    """
    try:
        queue = get_approval_queue()

        item = await queue.get_item(item_id)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        return ApprovalItemResponse(**item.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items/{item_id}/approve")
async def approve_item(item_id: str, request: ReviewRequest):
    """
    Approve an item

    Marks the item as approved and emits an event for downstream processing.

    **Example Request:**
    ```json
    {
        "reviewed_by": "reviewer@example.com",
        "feedback": "Looks great! Ready to publish."
    }
    ```
    """
    try:
        queue = get_approval_queue()

        success = await queue.approve_item(
            item_id=item_id,
            reviewed_by=request.reviewed_by,
            feedback=request.feedback
        )

        if not success:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "success": True,
            "message": "Item approved",
            "item_id": item_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items/{item_id}/reject")
async def reject_item(item_id: str, request: RejectRequest):
    """
    Reject an item

    Marks the item as rejected and emits an event. Optionally allows retry.

    **Example Request:**
    ```json
    {
        "reviewed_by": "reviewer@example.com",
        "feedback": "Hook needs improvement. Make it more engaging.",
        "allow_retry": true
    }
    ```
    """
    try:
        queue = get_approval_queue()

        success = await queue.reject_item(
            item_id=item_id,
            reviewed_by=request.reviewed_by,
            feedback=request.feedback,
            allow_retry=request.allow_retry
        )

        if not success:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "success": True,
            "message": "Item rejected",
            "item_id": item_id,
            "allow_retry": request.allow_retry
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items/{item_id}/assign")
async def assign_item(item_id: str, request: AssignRequest):
    """
    Assign an item to a reviewer

    **Example Request:**
    ```json
    {
        "assigned_to": "reviewer@example.com"
    }
    ```
    """
    try:
        queue = get_approval_queue()

        success = await queue.assign_item(
            item_id=item_id,
            assigned_to=request.assigned_to
        )

        if not success:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "success": True,
            "message": "Item assigned",
            "item_id": item_id,
            "assigned_to": request.assigned_to
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/items/{item_id}")
async def remove_item(item_id: str):
    """
    Remove an item from the queue

    This permanently deletes the item from the queue.
    """
    try:
        queue = get_approval_queue()

        success = await queue.remove_item(item_id)

        if not success:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "success": True,
            "message": "Item removed",
            "item_id": item_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_queue_stats():
    """
    Get queue statistics

    Returns counts, averages, and overall queue health.

    **Example Response:**
    ```json
    {
        "total_items": 42,
        "pending": 15,
        "approved": 20,
        "rejected": 5,
        "expired": 2,
        "pending_urgent": 3,
        "pending_high": 7,
        "average_quality_score": 0.823,
        "average_engagement_prediction": 0.756,
        "is_running": true
    }
    ```
    """
    try:
        queue = get_approval_queue()

        stats = await queue.get_stats()

        return stats

    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns the status of the Approval Queue service
    """
    queue = get_approval_queue()
    stats = await queue.get_stats()

    return {
        "status": "healthy",
        "service": "approval-queue",
        "is_running": stats["is_running"],
        "pending_items": stats["pending"],
        "urgent_items": stats["pending_urgent"]
    }
