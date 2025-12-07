"""
Content Metrics API endpoints
Poll metrics, view rollups, and analyze cross-platform performance
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import ContentVariant, ContentMetric, ContentRollup
from services.content_metrics import ContentMetricsService

router = APIRouter()


@router.get("/")
async def list_content_metrics(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List content metrics with pagination"""
    try:
        result = await db.execute(
            select(ContentRollup)
            .limit(limit)
            .offset(offset)
            .order_by(ContentRollup.last_updated_at.desc())
        )
        rollups = list(result.scalars().all())  # Convert to list immediately
        
        return [
            ContentRollupResponse(
                content_id=rollup.content_id,
                total_views=rollup.total_views or 0,
                total_likes=rollup.total_likes or 0,
                total_comments=rollup.total_comments or 0,
                best_platform=rollup.best_platform,
                last_updated_at=rollup.last_updated_at.isoformat() if rollup.last_updated_at else ""
            )
            for rollup in rollups
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ContentMetricResponse(BaseModel):
    id: int
    variant_id: UUID
    snapshot_at: str
    views: Optional[int]
    likes: Optional[int]
    comments: Optional[int]
    shares: Optional[int]
    traffic_type: str
    
    class Config:
        from_attributes = True


class ContentRollupResponse(BaseModel):
    content_id: UUID
    total_views: int
    total_likes: int
    total_comments: int
    best_platform: Optional[str]
    last_updated_at: str
    
    class Config:
        from_attributes = True


@router.post("/poll/{content_id}")
async def poll_content_metrics(
    content_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Poll metrics for all variants of a content item"""
    service = ContentMetricsService(db)
    metrics = await service.poll_metrics_for_content(content_id)
    
    return {
        "status": "success",
        "content_id": str(content_id),
        "metrics_collected": len(metrics)
    }


@router.get("/{content_id}/rollup", response_model=ContentRollupResponse)
async def get_content_rollup(
    content_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get aggregated rollup for a content item"""
    result = await db.execute(
        select(ContentRollup).where(ContentRollup.content_id == content_id)
    )
    rollup = result.scalar_one_or_none()
    
    if not rollup:
        raise HTTPException(status_code=404, detail="Rollup not found")
    
    return rollup


@router.get("/{content_id}/metrics", response_model=List[ContentMetricResponse])
async def get_content_metrics(
    content_id: UUID,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all metric snapshots for a content item"""
    result = await db.execute(
        select(ContentMetric)
        .join(ContentVariant, ContentMetric.variant_id == ContentVariant.id)
        .where(ContentVariant.content_id == content_id)
        .order_by(ContentMetric.snapshot_at.desc())
        .limit(limit)
    )
    metrics = list(result.scalars().all())  # Convert to list immediately
    
    return metrics


@router.post("/poll-recent")
async def poll_recent_content(
    hours: int = 48,
    db: AsyncSession = Depends(get_db)
):
    """Poll metrics for all recently published content"""
    service = ContentMetricsService(db)
    stats = await service.poll_all_recent_content(hours=hours)
    
    return {
        "status": "success",
        **stats
    }


@router.post("/{content_id}/recompute-rollup")
async def recompute_rollup(
    content_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger rollup recomputation"""
    service = ContentMetricsService(db)
    rollup = await service.recompute_rollup(content_id)
    
    if not rollup:
        raise HTTPException(status_code=404, detail="No metrics to aggregate")
    
    return {
        "status": "success",
        "content_id": str(content_id),
        "total_views": rollup.total_views
    }
