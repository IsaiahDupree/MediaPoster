"""
Analytics API Endpoints
Performance metrics and insights
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict
from pydantic import BaseModel

from database.connection import get_db

router = APIRouter()


class AnalyticsResponse(BaseModel):
    total_videos: int
    total_clips: int
    total_posts: int
    processing_queue: int
    failed_jobs: int


@router.get("/summary", response_model=AnalyticsResponse)
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    """Get overall analytics summary"""
    from sqlalchemy import select, func
    from database.models import OriginalVideo, Clip, PlatformPost, ProcessingJob
    
    # Count videos
    result = await db.execute(select(func.count(OriginalVideo.video_id)))
    total_videos = result.scalar() or 0
    
    # Count clips
    result = await db.execute(select(func.count(Clip.clip_id)))
    total_clips = result.scalar() or 0
    
    # Count posts
    result = await db.execute(select(func.count(PlatformPost.id)))
    total_posts = result.scalar() or 0
    
    # Count queued jobs
    result = await db.execute(
        select(func.count(ProcessingJob.job_id))
        .filter(ProcessingJob.status.in_(['queued', 'running']))
    )
    processing_queue = result.scalar() or 0
    
    # Count failed jobs
    result = await db.execute(
        select(func.count(ProcessingJob.job_id))
        .filter(ProcessingJob.status == 'failed')
    )
    failed_jobs = result.scalar() or 0
    
    return AnalyticsResponse(
        total_videos=total_videos,
        total_clips=total_clips,
        total_posts=total_posts,
        processing_queue=processing_queue,
        failed_jobs=failed_jobs
    )


@router.get("/performance")
async def get_performance_metrics(
    platform: str | None = None,
    hook_type: str | None = None,
    db: AsyncSession = Depends(get_db)
):
    """Get performance metrics"""
    from sqlalchemy import select, func
    from database.models import Clip, PlatformPost, PerformanceMetric
    
    # This would use the clip_performance_summary view
    # For now, return sample structure
    return {
        "metrics": [],
        "filters": {
            "platform": platform,
            "hook_type": hook_type
        }
    }


@router.get("/trends")
async def get_analytics_trends(
    period: str = "7d",
    db: AsyncSession = Depends(get_db)
):
    """Get analytics trends over time"""
    return {
        "trends": [],
        "period": period,
        "metrics": {
            "views": [],
            "engagement": [],
            "posts": []
        }
    }
