"""
Content Growth API
Track and analyze content performance over time
Backfill and sync metrics from social platforms
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio

from database.connection import get_db

router = APIRouter(prefix="/api/content-growth", tags=["Content Growth"])


# ============================================================================
# MODELS
# ============================================================================

class MetricType(str, Enum):
    VIEWS = "views"
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    SAVES = "saves"
    REACH = "reach"
    IMPRESSIONS = "impressions"
    ENGAGEMENT_RATE = "engagement_rate"
    WATCH_TIME = "watch_time"
    AVERAGE_VIEW_DURATION = "avg_view_duration"


class MetricSnapshot(BaseModel):
    """Single point in time metrics"""
    timestamp: datetime
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    reach: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0
    watch_time_seconds: int = 0
    avg_view_duration: float = 0.0


class ContentMetricsHistory(BaseModel):
    """Full metrics history for a piece of content"""
    post_id: str
    platform: str
    platform_post_id: Optional[str]
    platform_url: Optional[str]
    title: str
    published_at: Optional[datetime]
    
    # Current metrics
    current: MetricSnapshot
    
    # Historical data
    history: List[MetricSnapshot]
    
    # Growth metrics
    growth_24h: Dict[str, float]
    growth_7d: Dict[str, float]
    growth_30d: Dict[str, float]
    
    # Velocity (rate of change)
    velocity: Dict[str, float]


class GrowthSummary(BaseModel):
    """Summary of growth across all content"""
    total_views: int
    total_engagement: int
    total_posts: int
    avg_views_per_post: float
    avg_engagement_rate: float
    top_performing: List[Dict[str, Any]]
    fastest_growing: List[Dict[str, Any]]
    platform_breakdown: Dict[str, Dict[str, int]]


class BackfillStatus(BaseModel):
    """Status of a backfill job"""
    job_id: str
    status: str  # pending, running, completed, failed
    total_posts: int
    processed: int
    failed: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    errors: List[str]


# ============================================================================
# IN-MEMORY STORAGE (Replace with DB in production)
# ============================================================================

# Simulated metrics history storage
# In production, this would be a database table
metrics_history: Dict[str, List[MetricSnapshot]] = {}
backfill_jobs: Dict[str, BackfillStatus] = {}


# ============================================================================
# MOCK DATA GENERATORS
# ============================================================================

def generate_mock_history(post_id: str, days: int = 30) -> List[MetricSnapshot]:
    """Generate mock historical metrics for demo"""
    import random
    
    history = []
    base_views = random.randint(100, 5000)
    base_likes = int(base_views * random.uniform(0.03, 0.15))
    base_comments = int(base_likes * random.uniform(0.05, 0.2))
    base_shares = int(base_likes * random.uniform(0.02, 0.1))
    
    for day in range(days, 0, -1):
        timestamp = datetime.utcnow() - timedelta(days=day)
        
        # Simulate growth curve (fast initial, then slowing)
        growth_factor = 1 - (0.95 ** (days - day))
        
        # Add some randomness
        noise = random.uniform(0.9, 1.1)
        
        views = int(base_views * growth_factor * noise)
        likes = int(base_likes * growth_factor * noise)
        comments = int(base_comments * growth_factor * noise)
        shares = int(base_shares * growth_factor * noise)
        
        engagement_rate = ((likes + comments + shares) / max(views, 1)) * 100
        
        history.append(MetricSnapshot(
            timestamp=timestamp,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            saves=int(likes * 0.3),
            reach=int(views * 1.2),
            impressions=int(views * 1.5),
            engagement_rate=round(engagement_rate, 2),
            watch_time_seconds=views * random.randint(15, 60),
            avg_view_duration=random.uniform(10, 45),
        ))
    
    return history


def calculate_growth(history: List[MetricSnapshot], metric: str, days: int) -> float:
    """Calculate growth percentage over specified days"""
    if len(history) < 2:
        return 0.0
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = [h for h in history if h.timestamp >= cutoff]
    
    if len(recent) < 2:
        return 0.0
    
    start_value = getattr(recent[0], metric, 0)
    end_value = getattr(recent[-1], metric, 0)
    
    if start_value == 0:
        return 100.0 if end_value > 0 else 0.0
    
    return round(((end_value - start_value) / start_value) * 100, 2)


def calculate_velocity(history: List[MetricSnapshot], metric: str) -> float:
    """Calculate rate of change per day"""
    if len(history) < 2:
        return 0.0
    
    # Use last 7 days
    recent = history[-7:] if len(history) >= 7 else history
    
    start_value = getattr(recent[0], metric, 0)
    end_value = getattr(recent[-1], metric, 0)
    days = max((recent[-1].timestamp - recent[0].timestamp).days, 1)
    
    return round((end_value - start_value) / days, 2)


# ============================================================================
# PLATFORM API INTEGRATIONS (Simulated)
# ============================================================================

async def fetch_instagram_metrics(platform_post_id: str) -> MetricSnapshot:
    """Fetch metrics from Instagram Graph API"""
    # In production: Call Instagram Graph API
    # GET /{media-id}/insights
    import random
    await asyncio.sleep(0.1)  # Simulate API call
    
    views = random.randint(1000, 50000)
    likes = int(views * random.uniform(0.05, 0.15))
    return MetricSnapshot(
        timestamp=datetime.utcnow(),
        views=views,
        likes=likes,
        comments=int(likes * 0.1),
        shares=int(likes * 0.05),
        saves=int(likes * 0.2),
        reach=int(views * 0.9),
        impressions=int(views * 1.3),
        engagement_rate=round((likes / views) * 100, 2),
    )


async def fetch_tiktok_metrics(platform_post_id: str) -> MetricSnapshot:
    """Fetch metrics from TikTok API"""
    import random
    await asyncio.sleep(0.1)
    
    views = random.randint(5000, 200000)
    likes = int(views * random.uniform(0.08, 0.2))
    return MetricSnapshot(
        timestamp=datetime.utcnow(),
        views=views,
        likes=likes,
        comments=int(likes * 0.05),
        shares=int(likes * 0.1),
        saves=int(likes * 0.15),
        engagement_rate=round((likes / views) * 100, 2),
    )


async def fetch_youtube_metrics(platform_post_id: str) -> MetricSnapshot:
    """Fetch metrics from YouTube Data API"""
    import random
    await asyncio.sleep(0.1)
    
    views = random.randint(500, 30000)
    likes = int(views * random.uniform(0.03, 0.1))
    watch_time = views * random.randint(30, 180)
    return MetricSnapshot(
        timestamp=datetime.utcnow(),
        views=views,
        likes=likes,
        comments=int(likes * 0.08),
        shares=int(likes * 0.03),
        watch_time_seconds=watch_time,
        avg_view_duration=round(watch_time / max(views, 1), 1),
        engagement_rate=round((likes / views) * 100, 2),
    )


async def fetch_platform_metrics(platform: str, platform_post_id: str) -> MetricSnapshot:
    """Route to correct platform API"""
    fetchers = {
        "instagram": fetch_instagram_metrics,
        "tiktok": fetch_tiktok_metrics,
        "youtube": fetch_youtube_metrics,
    }
    
    fetcher = fetchers.get(platform)
    if fetcher:
        return await fetcher(platform_post_id)
    
    # Default mock for other platforms
    import random
    views = random.randint(100, 10000)
    return MetricSnapshot(
        timestamp=datetime.utcnow(),
        views=views,
        likes=int(views * 0.05),
        comments=int(views * 0.01),
        shares=int(views * 0.005),
        engagement_rate=5.0,
    )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/content/{post_id}", response_model=ContentMetricsHistory)
async def get_content_growth(
    post_id: str,
    days: int = Query(30, description="Number of days of history"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get metrics history and growth data for a specific post
    """
    from database.models import ScheduledPost, VideoClip, MediaCreationProject
    
    try:
        post_uuid = uuid.UUID(post_id)
        
        # Get post details
        result = await db.execute(
            select(ScheduledPost).filter(ScheduledPost.id == post_uuid)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Get title from source content
        title = "Untitled"
        if post.clip_id:
            clip_result = await db.execute(
                select(VideoClip).filter(VideoClip.id == post.clip_id)
            )
            clip = clip_result.scalar_one_or_none()
            if clip:
                title = clip.title or clip.filename or "Video Clip"
        elif post.media_project_id:
            project_result = await db.execute(
                select(MediaCreationProject).filter(MediaCreationProject.id == post.media_project_id)
            )
            project = project_result.scalar_one_or_none()
            if project:
                title = project.title or "Media Project"
        
        # Get or generate history
        if post_id not in metrics_history:
            metrics_history[post_id] = generate_mock_history(post_id, days)
        
        history = metrics_history[post_id]
        current = history[-1] if history else MetricSnapshot(timestamp=datetime.utcnow())
        
        # Calculate growth metrics
        growth_24h = {
            "views": calculate_growth(history, "views", 1),
            "likes": calculate_growth(history, "likes", 1),
            "comments": calculate_growth(history, "comments", 1),
            "shares": calculate_growth(history, "shares", 1),
        }
        
        growth_7d = {
            "views": calculate_growth(history, "views", 7),
            "likes": calculate_growth(history, "likes", 7),
            "comments": calculate_growth(history, "comments", 7),
            "shares": calculate_growth(history, "shares", 7),
        }
        
        growth_30d = {
            "views": calculate_growth(history, "views", 30),
            "likes": calculate_growth(history, "likes", 30),
            "comments": calculate_growth(history, "comments", 30),
            "shares": calculate_growth(history, "shares", 30),
        }
        
        velocity = {
            "views_per_day": calculate_velocity(history, "views"),
            "likes_per_day": calculate_velocity(history, "likes"),
            "comments_per_day": calculate_velocity(history, "comments"),
        }
        
        return ContentMetricsHistory(
            post_id=post_id,
            platform=post.platform,
            platform_post_id=post.platform_post_id,
            platform_url=post.platform_url,
            title=title,
            published_at=post.published_at,
            current=current,
            history=history[-days:],
            growth_24h=growth_24h,
            growth_7d=growth_7d,
            growth_30d=growth_30d,
            velocity=velocity,
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=GrowthSummary)
async def get_growth_summary(
    days: int = Query(30, description="Period to analyze"),
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall growth summary across all published content
    """
    from database.models import ScheduledPost
    
    try:
        query = select(ScheduledPost).filter(ScheduledPost.status == "published")
        
        if platform:
            query = query.filter(ScheduledPost.platform == platform)
        
        result = await db.execute(query)
        posts = result.scalars().all()
        
        total_views = 0
        total_engagement = 0
        platform_breakdown: Dict[str, Dict[str, int]] = {}
        post_metrics = []
        
        for post in posts:
            post_id = str(post.id)
            
            # Get or generate metrics
            if post_id not in metrics_history:
                metrics_history[post_id] = generate_mock_history(post_id, days)
            
            history = metrics_history[post_id]
            if history:
                current = history[-1]
                total_views += current.views
                total_engagement += current.likes + current.comments + current.shares
                
                # Platform breakdown
                if post.platform not in platform_breakdown:
                    platform_breakdown[post.platform] = {"views": 0, "likes": 0, "posts": 0}
                platform_breakdown[post.platform]["views"] += current.views
                platform_breakdown[post.platform]["likes"] += current.likes
                platform_breakdown[post.platform]["posts"] += 1
                
                # Track for top performers
                velocity = calculate_velocity(history, "views")
                post_metrics.append({
                    "post_id": post_id,
                    "platform": post.platform,
                    "views": current.views,
                    "engagement": current.likes + current.comments + current.shares,
                    "engagement_rate": current.engagement_rate,
                    "velocity": velocity,
                })
        
        # Sort for top performers
        top_performing = sorted(post_metrics, key=lambda x: x["views"], reverse=True)[:5]
        fastest_growing = sorted(post_metrics, key=lambda x: x["velocity"], reverse=True)[:5]
        
        num_posts = len(posts)
        avg_views = total_views / num_posts if num_posts > 0 else 0
        avg_engagement = (total_engagement / total_views * 100) if total_views > 0 else 0
        
        return GrowthSummary(
            total_views=total_views,
            total_engagement=total_engagement,
            total_posts=num_posts,
            avg_views_per_post=round(avg_views, 1),
            avg_engagement_rate=round(avg_engagement, 2),
            top_performing=top_performing,
            fastest_growing=fastest_growing,
            platform_breakdown=platform_breakdown,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backfill")
async def start_backfill(
    background_tasks: BackgroundTasks,
    platform: Optional[str] = None,
    days: int = Query(30, description="Days of history to fetch"),
    db: AsyncSession = Depends(get_db)
):
    """
    Start a background job to backfill metrics from social platforms
    """
    from database.models import ScheduledPost
    
    job_id = str(uuid.uuid4())
    
    # Get posts to backfill
    query = select(ScheduledPost).filter(ScheduledPost.status == "published")
    if platform:
        query = query.filter(ScheduledPost.platform == platform)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    # Create job status
    backfill_jobs[job_id] = BackfillStatus(
        job_id=job_id,
        status="pending",
        total_posts=len(posts),
        processed=0,
        failed=0,
        started_at=None,
        completed_at=None,
        errors=[],
    )
    
    # Start background task
    background_tasks.add_task(
        run_backfill_job,
        job_id,
        [str(p.id) for p in posts],
        [(p.platform, p.platform_post_id) for p in posts],
        days,
    )
    
    return {
        "job_id": job_id,
        "message": f"Backfill started for {len(posts)} posts",
        "status_url": f"/api/content-growth/backfill/{job_id}",
    }


async def run_backfill_job(
    job_id: str,
    post_ids: List[str],
    platform_info: List[tuple],
    days: int
):
    """Background task to fetch and store metrics"""
    job = backfill_jobs.get(job_id)
    if not job:
        return
    
    job.status = "running"
    job.started_at = datetime.utcnow()
    
    for i, (post_id, (platform, platform_post_id)) in enumerate(zip(post_ids, platform_info)):
        try:
            # Generate history (in production, fetch from API)
            history = []
            for day in range(days, 0, -1):
                try:
                    # Simulate fetching historical data point
                    metrics = await fetch_platform_metrics(platform, platform_post_id or "")
                    metrics.timestamp = datetime.utcnow() - timedelta(days=day)
                    history.append(metrics)
                except Exception:
                    pass
            
            # Get current metrics
            current = await fetch_platform_metrics(platform, platform_post_id or "")
            history.append(current)
            
            # Store in memory (in production, save to database)
            metrics_history[post_id] = history
            
            job.processed += 1
            
        except Exception as e:
            job.failed += 1
            job.errors.append(f"Post {post_id}: {str(e)}")
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.05)
    
    job.status = "completed"
    job.completed_at = datetime.utcnow()


@router.get("/backfill/{job_id}", response_model=BackfillStatus)
async def get_backfill_status(job_id: str):
    """Get status of a backfill job"""
    job = backfill_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/sync/{post_id}")
async def sync_post_metrics(
    post_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync current metrics for a specific post from its platform
    """
    from database.models import ScheduledPost
    
    try:
        post_uuid = uuid.UUID(post_id)
        
        result = await db.execute(
            select(ScheduledPost).filter(ScheduledPost.id == post_uuid)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if not post.platform_post_id:
            raise HTTPException(status_code=400, detail="Post has no platform ID")
        
        # Fetch current metrics
        current = await fetch_platform_metrics(post.platform, post.platform_post_id)
        
        # Append to history
        if post_id not in metrics_history:
            metrics_history[post_id] = []
        
        metrics_history[post_id].append(current)
        
        return {
            "post_id": post_id,
            "platform": post.platform,
            "synced_at": current.timestamp.isoformat(),
            "metrics": current.dict(),
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chart-data/{post_id}")
async def get_chart_data(
    post_id: str,
    metric: MetricType = MetricType.VIEWS,
    days: int = Query(30, description="Number of days"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get formatted chart data for a specific metric over time
    """
    # Generate or get history
    if post_id not in metrics_history:
        metrics_history[post_id] = generate_mock_history(post_id, days)
    
    history = metrics_history[post_id][-days:]
    
    # Format for chart
    labels = [h.timestamp.strftime("%m/%d") for h in history]
    values = [getattr(h, metric.value, 0) for h in history]
    
    # Calculate trend line (simple linear regression)
    if len(values) >= 2:
        n = len(values)
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(i * v for i, v in enumerate(values))
        sum_x2 = sum(i ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0
        intercept = (sum_y - slope * sum_x) / n
        
        trend = [round(slope * i + intercept, 1) for i in range(n)]
    else:
        trend = values
    
    return {
        "metric": metric.value,
        "labels": labels,
        "values": values,
        "trend": trend,
        "total_growth": round(((values[-1] - values[0]) / max(values[0], 1)) * 100, 1) if values else 0,
        "avg_daily_growth": round((values[-1] - values[0]) / max(len(values), 1), 1) if values else 0,
    }


@router.get("/compare")
async def compare_content_performance(
    post_ids: List[str] = Query(..., description="Post IDs to compare"),
    metric: MetricType = MetricType.VIEWS,
    days: int = Query(30),
):
    """
    Compare metrics across multiple posts
    """
    comparison = []
    
    for post_id in post_ids[:5]:  # Max 5 posts
        if post_id not in metrics_history:
            metrics_history[post_id] = generate_mock_history(post_id, days)
        
        history = metrics_history[post_id][-days:]
        
        if history:
            current = history[-1]
            comparison.append({
                "post_id": post_id,
                "current_value": getattr(current, metric.value, 0),
                "growth_7d": calculate_growth(history, metric.value, 7),
                "growth_30d": calculate_growth(history, metric.value, 30),
                "velocity": calculate_velocity(history, metric.value),
                "history": [
                    {"date": h.timestamp.strftime("%m/%d"), "value": getattr(h, metric.value, 0)}
                    for h in history
                ],
            })
    
    return {
        "metric": metric.value,
        "posts": comparison,
    }
