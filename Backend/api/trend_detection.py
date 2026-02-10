"""
Trend Detection API
====================
Endpoints for monitoring, filtering, and acting on detected trends.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/trends", tags=["trend-detection"])


class NicheConfigUpdate(BaseModel):
    primary_topics: Optional[List[str]] = None
    secondary_topics: Optional[List[str]] = None
    brand_keywords: Optional[List[str]] = None
    exclude_topics: Optional[List[str]] = None


@router.get("")
async def list_trends(
    status: Optional[str] = None,
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
):
    """List detected trends with optional filters."""
    from services.trend_detection import TrendDetectionService
    svc = TrendDetectionService()
    trends = await svc.get_trends(status=status, min_score=min_score, limit=limit)
    return {"trends": trends, "total": len(trends)}


@router.get("/dashboard")
async def trend_dashboard():
    """Trend radar data: counts by status, top trends, recent alerts."""
    from services.trend_detection import TrendDetectionService
    svc = TrendDetectionService()
    emerging = await svc.get_trends(status="emerging", limit=5)
    hot = await svc.get_trends(status="hot", limit=5)
    peaked = await svc.get_trends(status="peaked", limit=5)
    return {
        "emerging": emerging,
        "hot": hot,
        "peaked": peaked,
        "summary": {
            "emerging_count": len(emerging),
            "hot_count": len(hot),
            "peaked_count": len(peaked),
        },
    }


@router.get("/alerts")
async def recent_alerts(limit: int = Query(10)):
    """Recent high-score trend alerts."""
    from services.trend_detection import TrendDetectionService
    svc = TrendDetectionService()
    return await svc.get_trends(min_score=0.6, limit=limit)


@router.get("/{trend_id}")
async def get_trend(trend_id: str):
    """Get trend details + generated brief if available."""
    from sqlalchemy import create_engine, text
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        trend = conn.execute(text("""
            SELECT id, source_platform, trend_type, trend_identifier, trend_description,
                   velocity_score, volume_score, niche_relevance, composite_score,
                   status, first_detected_at, last_seen_at, brief_generated
            FROM detected_trends WHERE id = :id
        """), {"id": trend_id}).fetchone()
        if not trend:
            return {"error": "Trend not found"}

        briefs = conn.execute(text("""
            SELECT id, sora_prompt, suggested_caption, urgency, window_hours, created_at
            FROM trend_briefs WHERE trend_id = :id ORDER BY created_at DESC
        """), {"id": trend_id}).fetchall()

    return {
        "id": str(trend[0]),
        "source_platform": trend[1],
        "trend_type": trend[2],
        "trend_identifier": trend[3],
        "trend_description": trend[4],
        "composite_score": trend[8],
        "status": trend[9],
        "first_detected_at": trend[10].isoformat() if trend[10] else None,
        "briefs": [
            {
                "id": str(b[0]),
                "sora_prompt": b[1],
                "suggested_caption": b[2],
                "urgency": b[3],
                "window_hours": b[4],
                "created_at": b[5].isoformat() if b[5] else None,
            }
            for b in briefs
        ],
    }


@router.post("/{trend_id}/generate-brief")
async def generate_brief(trend_id: str):
    """Generate a content brief for a specific trend."""
    from services.trend_detection import TrendDetectionService
    svc = TrendDetectionService()
    return await svc.generate_trend_brief(trend_id)


@router.post("/scan")
async def run_scan():
    """Manually trigger a full trend scan cycle."""
    from services.trend_detection import TrendDetectionService
    svc = TrendDetectionService()
    return await svc.run_scan_cycle()


@router.put("/niche-config")
async def update_niche_config(req: NicheConfigUpdate):
    """Update niche relevance keywords."""
    from services.trend_detection import TrendDetectionService
    svc = TrendDetectionService()
    return await svc.update_niche_config(req.dict(exclude_none=True))
