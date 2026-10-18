"""
Smart Posting Times API
========================
Endpoints for ML-driven optimal scheduling.
"""

import os
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/smart-times", tags=["smart-posting-times"])


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/optimal/{platform}")
async def get_optimal_times(
    platform: str,
    account_id: Optional[str] = None,
    lookback_days: int = 60,
    top_n: int = 10,
):
    """Get ranked optimal posting times for a platform."""
    from services.smart_posting_times import SmartPostingTimesService

    service = SmartPostingTimesService()
    windows = await service.get_optimal_times(
        platform=platform,
        account_id=account_id,
        lookback_days=lookback_days,
        top_n=top_n,
    )
    return {
        "platform": platform,
        "windows": [
            {
                "rank": w.rank,
                "day": w.day_name,
                "hour_est": w.hour_est,
                "hour_utc": w.hour_utc,
                "score": w.score,
                "confidence": w.confidence,
                "avg_engagement_rate": w.avg_engagement_rate,
                "sample_size": w.sample_size,
            }
            for w in windows
        ],
        "lookback_days": lookback_days,
    }


@router.get("/optimal")
async def get_all_platform_times(lookback_days: int = 60, top_n: int = 5):
    """Get optimal times for all platforms."""
    from services.smart_posting_times import SmartPostingTimesService

    service = SmartPostingTimesService()
    all_times = await service.get_all_platform_times(lookback_days=lookback_days, top_n=top_n)
    return {
        "platforms": {
            platform: [
                {
                    "rank": w.rank,
                    "day": w.day_name,
                    "hour_est": w.hour_est,
                    "score": w.score,
                    "confidence": w.confidence,
                    "sample_size": w.sample_size,
                }
                for w in windows
            ]
            for platform, windows in all_times.items()
        },
    }


@router.get("/weekly-schedule")
async def get_weekly_schedule(
    posts_per_day: int = 3,
    lookback_days: int = 60,
    platforms: Optional[str] = None,
):
    """Generate an optimal weekly posting schedule."""
    from services.smart_posting_times import SmartPostingTimesService

    service = SmartPostingTimesService()
    platform_list = platforms.split(",") if platforms else None
    schedule = await service.generate_weekly_schedule(
        platforms=platform_list,
        posts_per_day=posts_per_day,
        lookback_days=lookback_days,
    )
    return {
        "schedule": [
            {
                "day": s.day_name,
                "hour_est": s.hour_est,
                "platform": s.platform,
                "score": s.score,
                "confidence": s.confidence,
                "reason": s.reason,
            }
            for s in schedule
        ],
        "total_slots": len(schedule),
    }


@router.get("/heatmap/{platform}")
async def get_heatmap(platform: str, lookback_days: int = 60):
    """Get heatmap data for a platform (7 days × 24 hours)."""
    from services.smart_posting_times import SmartPostingTimesService

    service = SmartPostingTimesService()
    return await service.get_heatmap_data(platform=platform, lookback_days=lookback_days)


@router.get("/suggest")
async def suggest_time(
    platform: str,
    preferred_day: Optional[int] = None,
    account_id: Optional[str] = None,
):
    """Suggest the single best posting time for a specific post."""
    from services.smart_posting_times import SmartPostingTimesService

    service = SmartPostingTimesService()
    window = await service.suggest_time_for_post(
        platform=platform,
        preferred_day=preferred_day,
        account_id=account_id,
    )
    if not window:
        return {"suggestion": None}

    return {
        "suggestion": {
            "day": window.day_name,
            "hour_est": window.hour_est,
            "hour_utc": window.hour_utc,
            "score": window.score,
            "confidence": window.confidence,
            "sample_size": window.sample_size,
        }
    }
