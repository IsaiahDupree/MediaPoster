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
from services.event_bus import EventBus, Topics


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


# =============================================================================
# PHASE 4: MAINLINE / EXPERIMENTS TOGGLE
# =============================================================================

from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

def get_sync_engine():
    return create_engine(DATABASE_URL)


@router.get("/posts/by-origin")
async def get_posts_by_origin(
    origin: Optional[str] = Query(None, description="Filter by origin: NARRATIVE, EXPERIMENT, MANUAL, or ALL"),
    account_role: Optional[str] = Query(None, description="Filter by account role: MAINLINE or EXPERIMENT_ARM"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(100, description="Max results")
):
    """
    Get scheduled posts filtered by origin (Narrative Builder vs Experiments).
    
    This enables the calendar toggle between:
    - MAINLINE: Posts from Narrative Builder to primary accounts
    - EXPERIMENT_ARM: Posts from Experiments to test accounts
    - ALL: All scheduled posts
    """
    engine = get_sync_engine()
    
    with engine.connect() as conn:
        query = """
            SELECT 
                sp.id, sp.account_id, sp.platform, sp.content_id, sp.caption,
                sp.scheduled_at, sp.status, sp.origin, sp.experiment_id, sp.goal_id,
                sa.handle, sa.account_role,
                v.file_name as content_title
            FROM scheduled_posts sp
            LEFT JOIN social_accounts sa ON sp.account_id = sa.id
            LEFT JOIN videos v ON sp.content_id::uuid = v.id
            WHERE 1=1
        """
        params = {'limit': limit}
        
        # Filter by origin
        if origin and origin != 'ALL':
            query += " AND sp.origin = :origin"
            params['origin'] = origin
        
        # Filter by account role
        if account_role:
            query += " AND sa.account_role = :account_role"
            params['account_role'] = account_role
        
        # Filter by date range
        if start_date:
            query += " AND sp.scheduled_at >= :start_date"
            params['start_date'] = start_date
        
        if end_date:
            query += " AND sp.scheduled_at <= :end_date"
            params['end_date'] = end_date
        
        # Filter by platform
        if platform:
            query += " AND sp.platform = :platform"
            params['platform'] = platform
        
        query += " ORDER BY sp.scheduled_at ASC LIMIT :limit"
        
        try:
            result = conn.execute(text(query), params).fetchall()
            
            posts = []
            for row in result:
                posts.append({
                    'id': str(row[0]),
                    'account_id': str(row[1]) if row[1] else None,
                    'platform': row[2],
                    'content_id': str(row[3]) if row[3] else None,
                    'caption': row[4],
                    'scheduled_at': row[5].isoformat() if row[5] else None,
                    'status': row[6],
                    'origin': row[7] or 'MANUAL',
                    'experiment_id': str(row[8]) if row[8] else None,
                    'goal_id': str(row[9]) if row[9] else None,
                    'account_handle': row[10],
                    'account_role': row[11] or 'MAINLINE',
                    'content_title': row[12]
                })
            
            # Calculate counts by origin
            origin_counts = {}
            for p in posts:
                o = p['origin']
                origin_counts[o] = origin_counts.get(o, 0) + 1
            
            return {
                'posts': posts,
                'count': len(posts),
                'origin_counts': origin_counts,
                'filters': {
                    'origin': origin,
                    'account_role': account_role,
                    'start_date': start_date,
                    'end_date': end_date
                }
            }
            
        except Exception as e:
            return {'posts': [], 'count': 0, 'error': str(e)}


@router.get("/stats/by-origin")
async def get_calendar_stats_by_origin():
    """
    Get calendar statistics grouped by origin.
    
    Returns counts for:
    - NARRATIVE: Posts scheduled by Narrative Builder (mainline)
    - EXPERIMENT: Posts scheduled by Experiments (test accounts)
    - MANUAL: Manually scheduled posts
    """
    engine = get_sync_engine()
    
    with engine.connect() as conn:
        try:
            # Overall stats by origin
            result = conn.execute(text("""
                SELECT 
                    COALESCE(origin, 'MANUAL') as origin,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'scheduled') as pending,
                    COUNT(*) FILTER (WHERE status = 'posted') as posted,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed
                FROM scheduled_posts
                WHERE scheduled_at > NOW() - INTERVAL '30 days'
                GROUP BY COALESCE(origin, 'MANUAL')
            """)).fetchall()
            
            by_origin = {}
            for row in result:
                by_origin[row[0]] = {
                    'total': row[1],
                    'pending': row[2],
                    'posted': row[3],
                    'failed': row[4]
                }
            
            # Stats by account role
            role_result = conn.execute(text("""
                SELECT 
                    COALESCE(sa.account_role, 'MAINLINE') as account_role,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE sp.status = 'scheduled') as pending
                FROM scheduled_posts sp
                LEFT JOIN social_accounts sa ON sp.account_id = sa.id
                WHERE sp.scheduled_at > NOW() - INTERVAL '30 days'
                GROUP BY COALESCE(sa.account_role, 'MAINLINE')
            """)).fetchall()
            
            by_role = {}
            for row in role_result:
                by_role[row[0]] = {
                    'total': row[1],
                    'pending': row[2]
                }
            
            # Upcoming posts by day
            upcoming = conn.execute(text("""
                SELECT 
                    DATE(scheduled_at) as day,
                    COALESCE(origin, 'MANUAL') as origin,
                    COUNT(*) as count
                FROM scheduled_posts
                WHERE scheduled_at > NOW() AND scheduled_at < NOW() + INTERVAL '7 days'
                AND status = 'scheduled'
                GROUP BY DATE(scheduled_at), COALESCE(origin, 'MANUAL')
                ORDER BY day
            """)).fetchall()
            
            upcoming_by_day = {}
            for row in upcoming:
                day = str(row[0])
                if day not in upcoming_by_day:
                    upcoming_by_day[day] = {}
                upcoming_by_day[day][row[1]] = row[2]
            
            return {
                'by_origin': by_origin,
                'by_account_role': by_role,
                'upcoming_7_days': upcoming_by_day,
                'summary': {
                    'narrative_posts': by_origin.get('NARRATIVE', {}).get('total', 0),
                    'experiment_posts': by_origin.get('EXPERIMENT', {}).get('total', 0),
                    'manual_posts': by_origin.get('MANUAL', {}).get('total', 0),
                    'mainline_pending': by_role.get('MAINLINE', {}).get('pending', 0),
                    'experiment_arm_pending': by_role.get('EXPERIMENT_ARM', {}).get('pending', 0)
                }
            }
            
        except Exception as e:
            return {'error': str(e), 'by_origin': {}, 'by_account_role': {}}


@router.get("/view-modes")
async def get_calendar_view_modes():
    """
    Get available calendar view modes and their configurations.
    
    Returns the toggle options for the calendar UI:
    - Mainline (Narrative Builder posts to MAINLINE accounts)
    - Experiments (Experiment posts to EXPERIMENT_ARM accounts)
    - All (Combined view)
    """
    return {
        'view_modes': [
            {
                'id': 'mainline',
                'label': 'Mainline',
                'description': 'Posts from Narrative Builder to primary accounts',
                'filter': {'origin': 'NARRATIVE', 'account_role': 'MAINLINE'},
                'color': '#10B981',  # Green
                'icon': '🎯'
            },
            {
                'id': 'experiments',
                'label': 'Experiments',
                'description': 'A/B test posts to experiment accounts',
                'filter': {'origin': 'EXPERIMENT', 'account_role': 'EXPERIMENT_ARM'},
                'color': '#8B5CF6',  # Purple
                'icon': '🧪'
            },
            {
                'id': 'manual',
                'label': 'Manual',
                'description': 'Manually scheduled posts',
                'filter': {'origin': 'MANUAL'},
                'color': '#6B7280',  # Gray
                'icon': '✋'
            },
            {
                'id': 'all',
                'label': 'All Posts',
                'description': 'Combined view of all scheduled posts',
                'filter': {},
                'color': '#3B82F6',  # Blue
                'icon': '📅'
            }
        ],
        'default_mode': 'mainline',
        'guardrails': {
            'narrative_only_to_mainline': True,
            'experiments_only_to_experiment_arm': True,
            'cross_posting_blocked': True
        }
    }
