"""
Content Runway API (PIPE-007)
==============================
Maintain 60+ approved content pieces for consistent posting.

Tracks content inventory and alerts when runway is low (<60 pieces).
Provides visibility into content readiness for the next 60 days.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import uuid
from loguru import logger

from database.connection import get_db
from database.models import (
    VideoClip,
    ContentVariant,
    ScheduledPost,
    PlatformPost
)

router = APIRouter(prefix="/api/runway", tags=["Content Runway"])


# ==================== Response Models ====================

class RunwayStatus(BaseModel):
    """Content runway status"""
    total_approved: int
    short_form_count: int
    long_form_count: int
    scheduled_count: int
    available_count: int  # Approved but not scheduled
    days_of_runway: float
    target_days: int = 60
    is_healthy: bool  # True if >= 60 approved pieces
    is_critical: bool  # True if < 30 approved pieces
    alerts: List[str]


class RunwayBreakdown(BaseModel):
    """Detailed runway breakdown by platform"""
    platform: str
    approved: int
    scheduled: int
    available: int
    days_of_runway: float
    is_healthy: bool


class RunwayAlert(BaseModel):
    """Runway alert"""
    severity: str  # "critical", "warning", "info"
    message: str
    recommended_action: str


# ==================== Endpoints ====================

@router.get("/status", response_model=RunwayStatus)
async def get_runway_status(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current content runway status

    Returns:
        - Total approved content count
        - Breakdown by form (short/long)
        - Scheduled vs available count
        - Days of runway remaining
        - Health alerts
    """
    try:
        # Get all approved video clips (not scheduled)
        approved_clips_query = select(VideoClip).where(
            and_(
                VideoClip.status == 'approved',
                VideoClip.id.notin_(
                    select(ScheduledPost.clip_id).where(
                        ScheduledPost.clip_id.isnot(None),
                        ScheduledPost.status.in_(['scheduled', 'published'])
                    )
                )
            )
        )

        approved_clips_result = await db.execute(approved_clips_query)
        approved_clips = approved_clips_result.scalars().all()

        # Get all approved content variants (not scheduled)
        approved_variants_query = select(ContentVariant).where(
            and_(
                ContentVariant.status == 'approved',
                ContentVariant.id.notin_(
                    select(ScheduledPost.content_variant_id).where(
                        ScheduledPost.content_variant_id.isnot(None),
                        ScheduledPost.status.in_(['scheduled', 'published'])
                    )
                )
            )
        )

        approved_variants_result = await db.execute(approved_variants_query)
        approved_variants = approved_variants_result.scalars().all()

        # Count short form vs long form
        short_form_count = sum(
            1 for clip in approved_clips
            if clip.duration_seconds and clip.duration_seconds <= 60
        )
        long_form_count = sum(
            1 for clip in approved_clips
            if clip.duration_seconds and clip.duration_seconds > 60
        )

        # Add content variants to short form count
        short_form_count += len(approved_variants)

        total_approved = len(approved_clips) + len(approved_variants)

        # Get scheduled posts count
        scheduled_query = select(func.count(ScheduledPost.id)).where(
            ScheduledPost.status == 'scheduled'
        )
        scheduled_result = await db.execute(scheduled_query)
        scheduled_count = scheduled_result.scalar() or 0

        # Calculate days of runway (assuming 2 posts per day average)
        posts_per_day = 2.0
        days_of_runway = total_approved / posts_per_day if posts_per_day > 0 else 0

        # Health checks
        target_days = 60
        target_pieces = int(target_days * posts_per_day)  # 120 pieces for 60 days

        is_healthy = total_approved >= target_pieces
        is_critical = total_approved < (target_pieces // 2)  # Less than 30 days

        # Generate alerts
        alerts = []
        if is_critical:
            alerts.append(f"🚨 CRITICAL: Only {days_of_runway:.0f} days of content runway. Need {target_pieces - total_approved} more pieces.")
        elif not is_healthy:
            alerts.append(f"⚠️ WARNING: Only {days_of_runway:.0f} days of content runway. Target is {target_days} days.")
        else:
            alerts.append(f"✅ Runway is healthy: {days_of_runway:.0f} days of content available.")

        if short_form_count < 40:
            alerts.append(f"📹 Need more short-form content (current: {short_form_count})")

        if long_form_count < 20:
            alerts.append(f"🎬 Need more long-form content (current: {long_form_count})")

        return RunwayStatus(
            total_approved=total_approved,
            short_form_count=short_form_count,
            long_form_count=long_form_count,
            scheduled_count=scheduled_count,
            available_count=total_approved,
            days_of_runway=days_of_runway,
            target_days=target_days,
            is_healthy=is_healthy,
            is_critical=is_critical,
            alerts=alerts
        )

    except Exception as e:
        logger.error(f"Error getting runway status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/breakdown")
async def get_runway_breakdown(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> List[RunwayBreakdown]:
    """
    Get runway breakdown by platform

    Returns breakdown of approved, scheduled, and available content per platform.
    """
    try:
        platforms = ["instagram", "tiktok", "youtube", "twitter", "linkedin"]
        breakdown = []

        for platform in platforms:
            # Count approved content targeted for this platform
            # This is simplified - in reality you'd filter by platform tags/metadata
            approved_count = 20  # Placeholder
            scheduled_count = 5  # Placeholder
            available_count = approved_count - scheduled_count

            posts_per_day = 1.5  # Platform-specific posting rate
            days_of_runway = available_count / posts_per_day if posts_per_day > 0 else 0

            breakdown.append(RunwayBreakdown(
                platform=platform,
                approved=approved_count,
                scheduled=scheduled_count,
                available=available_count,
                days_of_runway=days_of_runway,
                is_healthy=days_of_runway >= 30
            ))

        return breakdown

    except Exception as e:
        logger.error(f"Error getting runway breakdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_runway_alerts(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> List[RunwayAlert]:
    """
    Get current runway alerts and recommendations

    Returns actionable alerts for maintaining healthy runway.
    """
    try:
        # Get current status
        status = await get_runway_status(user_id, db)

        alerts = []

        # Critical alerts
        if status.is_critical:
            alerts.append(RunwayAlert(
                severity="critical",
                message=f"Only {status.days_of_runway:.0f} days of content runway remaining",
                recommended_action="Upload and approve at least 30 new content pieces immediately"
            ))

        # Warning alerts
        elif not status.is_healthy:
            alerts.append(RunwayAlert(
                severity="warning",
                message=f"Content runway below 60-day target ({status.days_of_runway:.0f} days)",
                recommended_action=f"Approve {status.target_days * 2 - status.total_approved} more content pieces"
            ))

        # Content type alerts
        if status.short_form_count < 40:
            alerts.append(RunwayAlert(
                severity="warning",
                message=f"Low short-form content ({status.short_form_count} pieces)",
                recommended_action="Upload more short-form videos (<60s)"
            ))

        if status.long_form_count < 20:
            alerts.append(RunwayAlert(
                severity="info",
                message=f"Low long-form content ({status.long_form_count} pieces)",
                recommended_action="Upload more long-form videos (>60s)"
            ))

        # Healthy status
        if not alerts:
            alerts.append(RunwayAlert(
                severity="info",
                message="Content runway is healthy",
                recommended_action="Continue approving 2-3 new pieces per day to maintain runway"
            ))

        return alerts

    except Exception as e:
        logger.error(f"Error getting runway alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def get_runway_trends(
    days: int = 30,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get runway trends over time

    Args:
        days: Number of days of history to return (default: 30)

    Returns historical runway data for trend visualization.
    """
    try:
        # This would query historical data
        # For now, return sample trend data

        trends = []
        now = datetime.now(timezone.utc)

        for i in range(days):
            date = now - timedelta(days=days - i)
            # In production, query actual historical data
            trends.append({
                "date": date.date().isoformat(),
                "approved_count": 80 + (i * 2),  # Sample data
                "days_of_runway": 40.0 + i,
                "is_healthy": (40.0 + i) >= 60
            })

        return {
            "trends": trends,
            "summary": {
                "average_approval_rate": 2.5,  # Pieces per day
                "trend_direction": "improving"  # "improving", "stable", "declining"
            }
        }

    except Exception as e:
        logger.error(f"Error getting runway trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recalculate")
async def recalculate_runway(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Force recalculation of runway metrics

    Useful after bulk content uploads or status changes.
    """
    try:
        # Get fresh status
        status = await get_runway_status(user_id, db)

        logger.info(
            f"Runway recalculated: {status.total_approved} approved pieces, "
            f"{status.days_of_runway:.0f} days of runway"
        )

        return {
            "success": True,
            "status": status,
            "recalculated_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error recalculating runway: {e}")
        raise HTTPException(status_code=500, detail=str(e))
