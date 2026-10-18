"""
Post Tracking API Endpoints (PTK-001, PTK-003, PTK-006)
========================================================
API for capturing post URLs, tracking engagement, and computing performance scores.

Endpoints:
- POST /api/post-tracking/capture - Capture post URL after publishing
- GET /api/post-tracking/{post_id}/status - Get tracking status
- GET /api/post-tracking/{post_id}/score - Get performance score
- POST /api/post-tracking/{post_id}/checkback - Trigger manual checkback
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from database.connection import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from services.post_tracker import get_post_tracker

router = APIRouter(prefix="/api/post-tracking", tags=["Post Tracking"])


# =====================================================
# Request/Response Models
# =====================================================

class CapturePostURLRequest(BaseModel):
    """Request to capture post URL after publishing"""
    scheduled_post_id: Optional[UUID] = Field(None, description="ID of scheduled post")
    posted_content_id: Optional[UUID] = Field(None, description="ID of posted content")
    platform_url: Optional[str] = Field(None, description="Public URL to published post")
    platform_post_id: Optional[str] = Field(None, description="Platform's internal post ID")
    platform: Optional[str] = Field(None, description="Platform name")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class PostTrackingStatusResponse(BaseModel):
    """Response with post tracking status"""
    success: bool
    post_id: Optional[str] = None
    platform: Optional[str] = None
    platform_url: Optional[str] = None
    platform_post_id: Optional[str] = None
    status: Optional[str] = None
    published_at: Optional[str] = None
    performance_score: Optional[float] = None
    latest_metrics: Optional[Dict[str, Any]] = None
    checkback_schedule: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class PerformanceScoreResponse(BaseModel):
    """Response with performance score"""
    success: bool
    post_id: str
    performance_score: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =====================================================
# Endpoints
# =====================================================

@router.post("/capture", response_model=Dict[str, Any])
async def capture_post_url(
    request: CapturePostURLRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Capture post URL after publishing (PTK-001)

    This endpoint should be called by publishing services (Safari automation, Blotato API)
    after successfully publishing a post to capture the platform URL.

    Features:
    - Stores platform URL in database
    - Links to scheduled post or posted content
    - Emits POST_PUBLISHED event
    - Schedules engagement checkbacks

    Example:
        POST /api/post-tracking/capture
        {
            "scheduled_post_id": "uuid",
            "platform_url": "https://twitter.com/user/status/123",
            "platform_post_id": "123",
            "platform": "twitter"
        }
    """
    tracker = get_post_tracker()

    result = await tracker.capture_post_url(
        db=db,
        scheduled_post_id=request.scheduled_post_id,
        posted_content_id=request.posted_content_id,
        platform_url=request.platform_url,
        platform_post_id=request.platform_post_id,
        platform=request.platform,
        metadata=request.metadata
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to capture post URL")
        )

    return result


@router.get("/{post_id}/status", response_model=PostTrackingStatusResponse)
async def get_post_tracking_status(
    post_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get tracking status for a post

    Returns:
    - Platform URL and post ID
    - Publishing status
    - Latest engagement metrics
    - Performance score
    - Checkback schedule with completion status

    Example:
        GET /api/post-tracking/abc-123/status
    """
    tracker = get_post_tracker()

    result = await tracker.get_post_tracking_status(
        db=db,
        scheduled_post_id=post_id
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Post not found")
        )

    return PostTrackingStatusResponse(**result)


@router.get("/{post_id}/score", response_model=PerformanceScoreResponse)
async def get_performance_score(
    post_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance score for a post (PTK-006)

    Performance score is calculated based on:
    - Engagement rate (40 points)
    - View velocity (30 points)
    - Save rate (20 points)
    - Virality/share rate (10 points)

    Score range: 0.0 to 100.0

    Example:
        GET /api/post-tracking/abc-123/score
    """
    tracker = get_post_tracker()

    score = await tracker.compute_performance_score(
        db=db,
        scheduled_post_id=post_id
    )

    if score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or insufficient metrics data"
        )

    # Get latest metrics
    status_result = await tracker.get_post_tracking_status(db, post_id)

    return PerformanceScoreResponse(
        success=True,
        post_id=str(post_id),
        performance_score=score,
        metrics=status_result.get("latest_metrics")
    )


@router.post("/{post_id}/checkback", response_model=Dict[str, Any])
async def trigger_manual_checkback(
    post_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger manual engagement checkback (PTK-003)

    Forces an immediate metrics collection for a post.
    Useful for testing or when you want to manually refresh metrics.

    Example:
        POST /api/post-tracking/abc-123/checkback
    """
    tracker = get_post_tracker()

    # Get post status to verify it exists
    status_result = await tracker.get_post_tracking_status(db, post_id)

    if not status_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Emit checkback event (will be picked up by metrics workers)
    event_bus = tracker.event_bus
    from services.event_bus import Topics

    await event_bus.publish(
        Topics.CHECKBACK_TRIGGERED,
        {
            "scheduled_post_id": str(post_id),
            "platform": status_result.get("platform"),
            "platform_url": status_result.get("platform_url"),
            "manual": True,
            "triggered_at": datetime.utcnow().isoformat()
        }
    )

    return {
        "success": True,
        "message": "Manual checkback triggered",
        "post_id": str(post_id),
        "platform": status_result.get("platform")
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "post-tracking",
        "features": [
            "PTK-001: Post URL Capture",
            "PTK-002: Post Reference Database",
            "PTK-003: Engagement Checkback Scheduler",
            "PTK-006: Post Performance Scoring"
        ]
    }
