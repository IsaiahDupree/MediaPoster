"""
Creator Intelligence API
========================
"What is @creator doing right now, and how do I adapt it?" Deep-dives a
specific TikTok creator's real recent posts (or auto-selects the
top-scoring creator for a niche via trend_detection.py) into an honest
style breakdown -- see services/creator_intelligence.py for exactly what
"style breakdown" does and doesn't claim.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.creator_intelligence import (
    CreatorIntelligenceUnavailable,
    analyze_creator_style,
    find_top_creator_for_niche,
)

router = APIRouter(prefix="/api/creators", tags=["Creator Intelligence"])


@router.get("/trend-breakdown")
async def trend_breakdown(
    niche: Optional[str] = Query(None, description="e.g. \"cooking\", \"fitness\" — auto-selects the top-scoring real creator for this niche"),
    creator: Optional[str] = Query(None, description="explicit TikTok @handle — overrides niche auto-selection"),
):
    """
    Give me an honest breakdown of what a top creator in this niche is
    doing right now, and how to adapt it. Provide `creator` for a specific
    handle, or `niche` to auto-select the top-scoring real creator whose
    video already passed niche-relevance filtering. At least one is
    required.
    """
    handle = creator
    if not handle:
        if not niche:
            raise HTTPException(status_code=400, detail="provide creator (a handle) or niche")
        top = await find_top_creator_for_niche(niche)
        if not top:
            raise HTTPException(
                status_code=404,
                detail=f"no attributable creator found for niche={niche!r} right now",
            )
        handle = top["handle"]

    try:
        return await analyze_creator_style(handle, niche=niche)
    except CreatorIntelligenceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
