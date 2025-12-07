"""
FastAPI Endpoints for Content Intelligence Platform Publishing
Multi-platform publishing, metrics collection, and comment analysis
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import uuid

from database.connection import get_db
from database.models import PlatformPost, PlatformCheckback, PostComment
from services.multi_platform_publisher import MultiPlatformPublisher
from services.platform_adapters.base import (
    PlatformType, PublishRequest, MockPlatformAdapter
)

router = APIRouter()


# ==================== Request/Response Models ====================

class PublishVideoRequest(BaseModel):
    """Request to publish video"""
    video_path: str
    title: str
    caption: str
    hashtags: List[str] = []
    platforms: List[str]  # List of platform names
    content_variant_id: Optional[str] = None
    clip_id: Optional[str] = None
    thumbnail_path: Optional[str] = None


class PublishResponse(BaseModel):
    """Publishing result"""
    success: bool
    total_platforms: int
    successful: int
    failed: int
    results: dict


class CollectMetricsRequest(BaseModel):
    """Request to collect metrics"""
    post_id: str
    checkback_hours: int  # 1, 6, 24, 72, or 168


class MetricsResponse(BaseModel):
    """Metrics collection result"""
    success: bool
    checkback_hours: Optional[int] = None
    metrics: Optional[dict] = None
    error: Optional[str] = None


class CollectCommentsRequest(BaseModel):
    """Request to collect comments"""
    post_id: str
    limit: int = 100
    analyze_sentiment: bool = True


class CommentsResponse(BaseModel):
    """Comments collection result"""
    success: bool
    comments_collected: int
    comments_stored: int
    sentiment_analyzed: int
    sample_sentiments: List[dict] = []


class PostDetailResponse(BaseModel):
    """Post details with latest metrics"""
    id: str
    platform: str
    platform_post_id: str
    post_url: Optional[str]
    title: str
    caption: str
    published_at: datetime
    status: str
    latest_metrics: Optional[dict] = None
    total_checkbacks: int


# ==================== Helper Functions ====================

def get_publisher(db: Session) -> MultiPlatformPublisher:
    """
    Get configured multi-platform publisher
    
    TODO: In production, load real adapters based on configuration
    For now, using mock adapters for all platforms
    """
    publisher = MultiPlatformPublisher(db=db)
    
    # Register mock adapters for all supported platforms
    # TODO: Replace with real adapters when APIs are integrated
    for platform_type in PlatformType:
        adapter = MockPlatformAdapter(platform_type)
        publisher.register_adapter(adapter)
    
    return publisher


# ==================== Endpoints ====================

@router.post("/publish", response_model=PublishResponse)
def publish_video(
    request: PublishVideoRequest,
    db: Session = Depends(get_db)
):
    """
    Publish video to multiple platforms
    
    This endpoint:
    1. Publishes video to specified platforms
    2. Stores post records in database
    3. Returns post URLs and IDs
    
    Example:
        ```
        POST /api/platform/publish
        {
            "video_path": "/path/to/video.mp4",
            "title": "My Awesome Video",
            "caption": "Check this out!",
            "hashtags": ["viral", "content"],
            "platforms": ["tiktok", "instagram", "youtube"]
        }
        ```
    """
    publisher = get_publisher(db)
    
    # Convert string UUIDs if provided
    content_variant_id = uuid.UUID(request.content_variant_id) if request.content_variant_id else None
    clip_id = uuid.UUID(request.clip_id) if request.clip_id else None
    
    # Create publish request
    pub_request = PublishRequest(
        video_path=request.video_path,
        title=request.title,
        caption=request.caption,
        hashtags=request.hashtags,
        thumbnail_path=request.thumbnail_path
    )
    
    # Publish to all platforms
    result = publisher.publish_to_multiple_platforms(
        platforms=request.platforms,
        request=pub_request,
        content_variant_id=content_variant_id,
        clip_id=clip_id
    )
    
    return PublishResponse(**result)


@router.get("/platforms")
def get_available_platforms(db: Session = Depends(get_db)):
    """
    Get list of available platforms
    
    Returns platforms that have been configured with adapters
    """
    publisher = get_publisher(db)
    platforms = publisher.get_available_platforms()
    
    return {
        "platforms": platforms,
        "total": len(platforms)
    }


@router.post("/metrics/collect", response_model=MetricsResponse)
def collect_post_metrics(
    request: CollectMetricsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Collect performance metrics for a post
    
    Checkback hours typically: 1, 6, 24, 72, 168 (7 days)
    
    Example:
        ```
        POST /api/platform/metrics/collect
        {
            "post_id": "uuid-here",
            "checkback_hours": 24
        }
        ```
    """
    publisher = get_publisher(db)
    
    post_id = uuid.UUID(request.post_id)
    
    # Collect metrics (could be done in background task for production)
    result = publisher.collect_metrics(
        post_id=post_id,
        checkback_hours=request.checkback_hours
    )
    
    if "error" in result:
        return MetricsResponse(success=False, error=result["error"])
    
    return MetricsResponse(**result)


@router.post("/comments/collect", response_model=CommentsResponse)
def collect_post_comments(
    request: CollectCommentsRequest,
    db: Session = Depends(get_db)
):
    """
    Collect and analyze comments on a post
    
    Automatically performs sentiment analysis on comments
    
    Example:
        ```
        POST /api/platform/comments/collect
        {
            "post_id": "uuid-here",
            "limit": 100,
            "analyze_sentiment": true
        }
        ```
    """
    publisher = get_publisher(db)
    
    post_id = uuid.UUID(request.post_id)
    
    result = publisher.collect_comments(
        post_id=post_id,
        limit=request.limit,
        analyze_sentiment=request.analyze_sentiment
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return CommentsResponse(**result)


@router.get("/posts", response_model=List[PostDetailResponse])
def list_posts(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List published posts with optional filters
    
    Query params:
        - platform: Filter by platform (tiktok, instagram, etc.)
        - status: Filter by status (published, scheduled, failed)
        - limit: Max results (default: 50)
    """
    query = db.query(PlatformPost)
    
    if platform:
        query = query.filter(PlatformPost.platform == platform)
    
    if status:
        query = query.filter(PlatformPost.status == status)
    
    posts = query.order_by(PlatformPost.published_at.desc()).limit(limit).all()
    
    results = []
    for post in posts:
        # Get latest metrics
        latest_checkback = db.query(PlatformCheckback)\
            .filter_by(platform_post_id=post.id)\
            .order_by(PlatformCheckback.checkback_h.desc())\
            .first()
        
        latest_metrics = None
        if latest_checkback:
            latest_metrics = {
                "checkback_hours": latest_checkback.checkback_h,
                "views": latest_checkback.views,
                "likes": latest_checkback.likes,
                "comments": latest_checkback.comments,
                "shares": latest_checkback.shares,
                "saves": latest_checkback.saves,
                "engagement_rate": (
                    latest_checkback.like_rate +
                    latest_checkback.comment_rate +
                    latest_checkback.share_rate
                ) if latest_checkback.like_rate else 0
            }
        
        total_checkbacks = db.query(PlatformCheckback)\
            .filter_by(platform_post_id=post.id)\
            .count()
        
        results.append(PostDetailResponse(
            id=str(post.id),
            platform=post.platform,
            platform_post_id=post.platform_post_id,
            post_url=post.platform_url,
            title=post.title,
            caption=post.caption,
            published_at=post.published_at,
            status=post.status,
            latest_metrics=latest_metrics,
            total_checkbacks=total_checkbacks
        ))
    
    return results


@router.get("/posts/{post_id}")
def get_post_details(
    post_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific post
    
    Includes:
    - Post metadata
    - All checkback metrics
    - Comment summary
    """
    post_uuid = uuid.UUID(post_id)
    post = db.query(PlatformPost).filter_by(id=post_uuid).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Get all checkbacks
    checkbacks = db.query(PlatformCheckback)\
        .filter_by(platform_post_id=post.id)\
        .order_by(PlatformCheckback.checkback_h)\
        .all()
    
    checkback_data = [
        {
            "checkback_hours": cb.checkback_h,
            "checked_at": cb.checked_at,
            "views": cb.views,
            "likes": cb.likes,
            "comments": cb.comments,
            "shares": cb.shares,
            "saves": cb.saves,
            "engagement_rate": (cb.like_rate or 0) + (cb.comment_rate or 0) + (cb.share_rate or 0)
        }
        for cb in checkbacks
    ]
    
    # Get comment summary
    total_comments = db.query(PostComment).filter_by(platform_post_id=post.id).count()
    
    avg_sentiment = db.query(PostComment.sentiment_score)\
        .filter_by(platform_post_id=post.id)\
        .filter(PostComment.sentiment_score.isnot(None))\
        .all()
    
    avg_sentiment_score = None
    if avg_sentiment:
        scores = [s[0] for s in avg_sentiment if s[0] is not None]
        avg_sentiment_score = sum(scores) / len(scores) if scores else None
    
    return {
        "post": {
            "id": str(post.id),
            "platform": post.platform,
            "platform_post_id": post.platform_post_id,
            "post_url": post.platform_url,
            "title": post.title,
            "caption": post.caption,
            "hashtags": post.hashtags,
            "published_at": post.published_at,
            "status": post.status
        },
        "metrics_timeline": checkback_data,
        "comments_summary": {
            "total_comments": total_comments,
            "avg_sentiment": avg_sentiment_score
        }
    }


@router.post("/schedule-checkbacks/{post_id}")
def schedule_post_checkbacks(
    post_id: str,
    checkback_hours: List[int] = [1, 6, 24, 72, 168],
    db: Session = Depends(get_db)
):
    """
    Schedule automated metric checkbacks for a post
    
    Default checkbacks: 1h, 6h, 24h, 72h, 168h (7 days)
    
    TODO: In production, this will create background jobs
    """
    post_uuid = uuid.UUID(post_id)
    post = db.query(PlatformPost).filter_by(id=post_uuid).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    publisher = get_publisher(db)
    publisher.schedule_checkbacks(post_uuid, checkback_hours)
    
    return {
        "success": True,
        "post_id": post_id,
        "checkbacks_scheduled": checkback_hours,
        "message": "Checkbacks scheduled successfully"
    }
