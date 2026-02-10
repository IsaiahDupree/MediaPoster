"""
Content Recycling API
======================
Endpoints for the evergreen content re-queue system.
"""

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/recycling", tags=["content-recycling"])


# ─── Models ──────────────────────────────────────────────────────────────────

class RecycleRequest(BaseModel):
    content_id: str
    platforms: Optional[List[str]] = None
    use_ai_captions: bool = True
    use_smart_times: bool = True


class BatchRecycleRequest(BaseModel):
    max_posts: int = 5
    platforms: Optional[List[str]] = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/candidates")
async def find_recyclable_content(
    platform: Optional[str] = None,
    limit: int = 10,
    min_age_days: int = 7,
    lookback_days: int = 180,
):
    """Find content eligible for recycling based on engagement data."""
    from services.content_recycling_engine import ContentRecyclingEngine

    engine = ContentRecyclingEngine()
    candidates = await engine.find_recyclable_content(
        platform=platform,
        limit=limit,
        min_age_days=min_age_days,
        lookback_days=lookback_days,
    )
    return {
        "candidates": [
            {
                "content_id": c.content_id,
                "platform": c.original_platform,
                "caption_preview": c.original_caption[:100] + "..." if len(c.original_caption) > 100 else c.original_caption,
                "views": c.views,
                "likes": c.likes,
                "engagement_rate": c.engagement_rate,
                "evergreen_score": c.evergreen_score,
                "recycle_count": c.recycle_count,
                "eligible_platforms": c.eligible_platforms,
                "published_at": c.published_at.isoformat() if c.published_at else None,
            }
            for c in candidates
        ],
        "total": len(candidates),
    }


@router.post("/recycle")
async def recycle_content(req: RecycleRequest):
    """Recycle a specific piece of content with fresh AI captions."""
    from services.content_recycling_engine import ContentRecyclingEngine

    engine = ContentRecyclingEngine()
    result = await engine.recycle_content(
        content_id=req.content_id,
        platforms=req.platforms,
        use_ai_captions=req.use_ai_captions,
        use_smart_times=req.use_smart_times,
    )
    return {
        "success": result.success,
        "content_id": result.content_id,
        "platforms": result.platforms,
        "scheduled_post_ids": result.scheduled_post_ids,
        "new_captions": result.new_captions,
        "scheduled_times": result.scheduled_times,
        "error": result.error,
    }


@router.post("/auto-recycle")
async def auto_recycle_batch(req: BatchRecycleRequest):
    """Automatically find and recycle the best evergreen content."""
    from services.content_recycling_engine import ContentRecyclingEngine

    engine = ContentRecyclingEngine()
    summary = await engine.auto_recycle_batch(
        max_posts=req.max_posts,
        platforms=req.platforms,
    )
    return summary


@router.get("/stats")
async def get_recycling_stats():
    """Get overall content recycling statistics."""
    from services.content_recycling_engine import ContentRecyclingEngine

    engine = ContentRecyclingEngine()
    return await engine.get_recycling_stats()
