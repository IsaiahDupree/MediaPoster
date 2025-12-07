"""
API endpoints for content calendar management
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.calendar_service import CalendarService
from services.exceptions import ServiceError


router = APIRouter(prefix="/calendar", tags=["calendar"])


# Request/Response Models
class SchedulePostRequest(BaseModel):
    """Request model for scheduling a post"""
    clip_id: Optional[UUID] = None
    content_variant_id: Optional[UUID] = None
    platform: str = Field(..., description="Target platform (e.g., tiktok, instagram, youtube)")
    scheduled_time: datetime = Field(..., description="When to publish (ISO 8601 format)")
    platform_account_id: Optional[UUID] = None
    is_ai_recommended: bool = False
    recommendation_score: Optional[float] = Field(None, ge=0, le=1)
    recommendation_reasoning: Optional[str] = None


class SchedulePostUpdate(BaseModel):
    """Request model for updating a scheduled post"""
    scheduled_time: datetime = Field(..., description="New scheduled time")


class BulkScheduleItem(BaseModel):
    """Single item in bulk schedule request"""
    clip_id: Optional[UUID] = None
    content_variant_id: Optional[UUID] = None
    platform: str
    scheduled_time: datetime
    platform_account_id: Optional[UUID] = None
    is_ai_recommended: bool = False
    recommendation_score: Optional[float] = None
    recommendation_reasoning: Optional[str] = None


class BulkScheduleRequest(BaseModel):
    """Request model for bulk scheduling"""
    posts: List[BulkScheduleItem]


class ScheduledPostResponse(BaseModel):
    """Response model for scheduled post"""
    id: str
    platform: str
    scheduled_time: str
    status: str
    is_ai_recommended: bool
    recommendation_score: Optional[float] = None
    recommendation_reasoning: Optional[str] = None
    published_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    content: Optional[dict] = None
    clip: Optional[dict] = None


# API Endpoints
@router.get("/posts", response_model=List[ScheduledPostResponse])
async def get_calendar_posts(
    start_date: Optional[datetime] = Query(None, description="Start date for calendar range"),
    end_date: Optional[datetime] = Query(None, description="End date for calendar range"),
    platforms: Optional[str] = Query(None, description="Comma-separated list of platforms to filter"),
    status: Optional[str] = Query(None, description="Filter by status (scheduled, published, failed)"),
    user_id: UUID = Query(UUID("00000000-0000-0000-0000-000000000000"), description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get scheduled posts for calendar view
    
    Returns posts within the specified date range, optionally filtered by platform and status.
    """
    try:
        calendar_service = CalendarService(db)
        
        # Parse platforms if provided
        platform_list = platforms.split(',') if platforms else None
        
        posts = await calendar_service.get_calendar_posts(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            platforms=platform_list,
            status=status
        )
        
        return posts
        
    except ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/schedule", response_model=dict)
async def schedule_post(
    request: SchedulePostRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Schedule a new post
    
    Creates a scheduled post for the specified platform and time.
    """
    try:
        calendar_service = CalendarService(db)
        
        scheduled_post = await calendar_service.schedule_post(
            clip_id=request.clip_id,
            content_variant_id=request.content_variant_id,
            platform=request.platform,
            scheduled_time=request.scheduled_time,
            platform_account_id=request.platform_account_id,
            is_ai_recommended=request.is_ai_recommended,
            recommendation_score=request.recommendation_score,
            recommendation_reasoning=request.recommendation_reasoning
        )
        
        return {
            "success": True,
            "post_id": str(scheduled_post.id),
            "scheduled_time": scheduled_post.scheduled_time.isoformat(),
            "platform": scheduled_post.platform
        }
        
    except ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.patch("/posts/{post_id}", response_model=dict)
async def update_scheduled_post(
    post_id: UUID,
    update: SchedulePostUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update (reschedule) an existing post
    
    Move a scheduled post to a different time.
    """
    try:
        calendar_service = CalendarService(db)
        
        updated_post = await calendar_service.reschedule_post(
            post_id=post_id,
            new_time=update.scheduled_time
        )
        
        return {
            "success": True,
            "post_id": str(updated_post.id),
            "new_scheduled_time": updated_post.scheduled_time.isoformat(),
            "status": updated_post.status
        }
        
    except ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/posts/{post_id}", response_model=dict)
async def cancel_scheduled_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a scheduled post
    
    Marks a post as cancelled so it won't be published.
    """
    try:
        calendar_service = CalendarService(db)
        
        success = await calendar_service.cancel_scheduled_post(post_id)
        
        return {
            "success": success,
            "post_id": str(post_id),
            "message": "Post cancelled successfully"
        }
        
    except ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/bulk-schedule", response_model=dict)
async def bulk_schedule_posts(
    request: BulkScheduleRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk schedule multiple posts
    
    Schedule multiple posts at once with a single request.
    """
    try:
        calendar_service = CalendarService(db)
        
        # Convert Pydantic models to dicts
        posts_data = [post.dict() for post in request.posts]
        
        scheduled_posts = await calendar_service.bulk_schedule(posts_data)
        
        return {
            "success": True,
            "scheduled_count": len(scheduled_posts),
            "post_ids": [str(post.id) for post in scheduled_posts]
        }
        
    except ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/gaps", response_model=List[dict])
async def get_posting_gaps(
    start_date: datetime = Query(..., description="Start date for gap analysis"),
    end_date: datetime = Query(..., description="End date for gap analysis"),
    platforms: Optional[str] = Query(None, description="Comma-separated platforms to analyze"),
    user_id: UUID = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Identify gaps in posting schedule
    
    Returns dates within the range that have no scheduled posts.
    Useful for AI recommendations to fill gaps.
    """
    try:
        calendar_service = CalendarService(db)
        
        # Parse platforms if provided
        platform_list = platforms.split(',') if platforms else None
        
        gaps = await calendar_service.get_posting_gaps(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            platforms=platform_list
        )
        
        return gaps
        
    except ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/posts/{post_id}/publish", response_model=dict)
async def publish_now(
    post_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Publish a scheduled post immediately
    
    Triggers immediate publishing instead of waiting for scheduled time.
    Note: This will be implemented in Phase 2 with publishing logic.
    """
    # TODO: Implement in Phase 2 with publisher_service
    raise HTTPException(status_code=501, detail="Immediate publishing not yet implemented")
