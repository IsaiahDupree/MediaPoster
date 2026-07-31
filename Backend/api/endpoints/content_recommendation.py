"""
Content Recommendation API
===========================
"What should I post next?" — fuses live niche trends with this account's
own historical top-performers, optionally scoped to a Brand's niche/voice/
audience.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Brand
from services.content_recommendation import get_content_recommendation_service

router = APIRouter(prefix="/api/recommend", tags=["Content Recommendation"])


@router.get("/next-content")
async def recommend_next_content(
    brand_id: Optional[UUID] = Query(None, description="Brand to scope niche/voice/audience to"),
    niche: Optional[str] = Query(None, description="Override niche directly (skips Brand lookup if brand_id omitted)"),
    available_minutes: Optional[int] = Query(None, ge=1, description="How long you have to produce this today"),
    db: AsyncSession = Depends(get_db),
):
    """
    What should I post next, given what's trending in my niche right now and
    what has historically worked for my account? Provide either brand_id
    (looks up niche/voice/audience) or a raw niche string directly — at
    least one of brand_id/niche should be set for a trend-aware answer, but
    neither is required (a history-only recommendation still comes back).
    """
    brand_voice = None
    target_audience = None
    primary_goal = None
    resolved_niche = niche
    resolved_available_minutes = available_minutes

    if brand_id is not None:
        result = await db.execute(select(Brand).where(Brand.id == brand_id))
        brand = result.scalar_one_or_none()
        if not brand:
            raise HTTPException(status_code=404, detail=f"Brand {brand_id} not found")
        resolved_niche = resolved_niche or brand.niche
        brand_voice = brand.brand_voice
        target_audience = brand.target_audience
        primary_goal = brand.primary_goal
        # per-call override wins; otherwise fall back to the creator's stated capacity
        resolved_available_minutes = available_minutes if available_minutes is not None \
            else brand.available_minutes_per_day

    service = get_content_recommendation_service()
    return await service.recommend_next_content(
        niche=resolved_niche,
        brand_voice=brand_voice,
        target_audience=target_audience,
        available_minutes=resolved_available_minutes,
        primary_goal=primary_goal,
    )
