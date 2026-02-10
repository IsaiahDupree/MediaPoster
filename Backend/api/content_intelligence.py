"""
Content Intelligence API
=========================
Endpoints for the closed-loop content intelligence system.
"""

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/intelligence", tags=["content-intelligence"])


class BriefGenerateRequest(BaseModel):
    count: int = 7


class BriefStatusUpdate(BaseModel):
    status: str  # draft, approved, produced, published


@router.get("/insights")
async def get_insights(lookback_days: int = Query(90)):
    """Analyze content patterns and return winning/losing insights."""
    from services.content_intelligence import ContentIntelligenceEngine
    engine = ContentIntelligenceEngine()
    return await engine.analyze_patterns(lookback_days=lookback_days)


@router.get("/briefs")
async def list_briefs(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """List generated content briefs."""
    from services.content_intelligence import ContentIntelligenceEngine
    engine = ContentIntelligenceEngine()
    briefs = await engine.get_briefs(status=status, limit=limit)
    return {"briefs": briefs, "total": len(briefs)}


@router.post("/briefs/generate")
async def generate_briefs(req: BriefGenerateRequest):
    """Generate data-backed content briefs using GPT + performance data."""
    from services.content_intelligence import ContentIntelligenceEngine
    engine = ContentIntelligenceEngine()
    briefs = await engine.generate_briefs(count=req.count)
    return {"briefs": briefs, "count": len(briefs)}


@router.put("/briefs/{brief_id}")
async def update_brief(brief_id: str, req: BriefStatusUpdate):
    """Update a brief's status (draft → approved → produced → published)."""
    from services.content_intelligence import ContentIntelligenceEngine
    engine = ContentIntelligenceEngine()
    return await engine.update_brief_status(brief_id, req.status)


@router.get("/report")
async def weekly_report():
    """Generate AI-summarized weekly intelligence report."""
    from services.content_intelligence import ContentIntelligenceEngine
    engine = ContentIntelligenceEngine()
    return await engine.weekly_report()


@router.post("/tag-posts")
async def tag_untagged_posts(limit: int = Query(20)):
    """AI-tag attributes on untagged posts."""
    from services.content_intelligence import ContentIntelligenceEngine
    engine = ContentIntelligenceEngine()
    return await engine.tag_untagged_posts(limit=limit)


@router.get("/attributes/{post_id}")
async def get_post_attributes(post_id: str):
    """View AI-tagged attributes for a specific post."""
    from sqlalchemy import create_engine, text
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, topic_category, hook_type, emotional_tone,
                   visual_style, caption_structure, ai_confidence, created_at
            FROM content_attributes WHERE post_id = :post_id
        """), {"post_id": post_id}).fetchall()
    return {
        "post_id": post_id,
        "attributes": [
            {
                "id": str(r[0]),
                "topic_category": r[1],
                "hook_type": r[2],
                "emotional_tone": r[3],
                "visual_style": r[4],
                "caption_structure": r[5],
                "ai_confidence": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ],
    }
