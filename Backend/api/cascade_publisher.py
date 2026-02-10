"""
Multi-Account Cascade API
==========================
Endpoints for managing cascade publishing rules and monitoring cascade posts.
"""

from typing import Optional, List
from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/cascade", tags=["cascade-publisher"])


class CascadeRuleRequest(BaseModel):
    platform: str
    primary_account_id: str
    secondary_account_ids: List[str]
    mode: str = "always"
    delay_min: int = 120
    delay_max: int = 360
    performance_gate_threshold: int = 1000
    refresh_caption: bool = True


class TriggerCascadeRequest(BaseModel):
    original_post_id: str
    platform: str
    account_id: str


@router.get("/rules")
async def get_rules():
    """List all cascade rules."""
    from services.cascade_publisher import CascadePublisher
    svc = CascadePublisher()
    rules = await svc.get_rules()
    return {"rules": rules, "total": len(rules)}


@router.post("/rules")
async def upsert_rule(req: CascadeRuleRequest):
    """Create or update a cascade rule."""
    from services.cascade_publisher import CascadePublisher
    svc = CascadePublisher()
    return await svc.upsert_rule(
        platform=req.platform,
        primary_account_id=req.primary_account_id,
        secondary_account_ids=req.secondary_account_ids,
        mode=req.mode,
        delay_min=req.delay_min,
        delay_max=req.delay_max,
        performance_gate_threshold=req.performance_gate_threshold,
        refresh_caption=req.refresh_caption,
    )


@router.post("/rules/seed-defaults")
async def seed_defaults():
    """Create default cascade rules from account hierarchy."""
    from services.cascade_publisher import CascadePublisher
    svc = CascadePublisher()
    return await svc.seed_default_rules()


@router.get("/posts")
async def list_cascade_posts(status: Optional[str] = None):
    """List cascade posts with optional status filter."""
    from sqlalchemy import create_engine, text
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(db_url)
    query = """SELECT id, original_post_id, target_account_id, delay_minutes,
                      refreshed_caption, status, scheduled_post_id, gate_result, created_at
               FROM cascade_posts WHERE 1=1"""
    params = {}
    if status:
        query += " AND status = :status"
        params["status"] = status
    query += " ORDER BY created_at DESC LIMIT 50"
    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()
    return {
        "posts": [
            {
                "id": str(r[0]),
                "original_post_id": str(r[1]) if r[1] else None,
                "target_account_id": r[2],
                "delay_minutes": r[3],
                "refreshed_caption_preview": (r[4] or "")[:80],
                "status": r[5],
                "scheduled_post_id": str(r[6]) if r[6] else None,
                "gate_result": r[7],
                "created_at": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ],
    }


@router.post("/posts/{cascade_id}/approve")
async def approve_cascade(cascade_id: str):
    """Manually approve a gated/manual cascade post."""
    from sqlalchemy import create_engine, text
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text("UPDATE cascade_posts SET status = 'pending' WHERE id = :id"), {"id": cascade_id})
        conn.commit()
    return {"cascade_id": cascade_id, "status": "pending"}


@router.post("/posts/{cascade_id}/skip")
async def skip_cascade(cascade_id: str):
    """Skip a cascade post."""
    from sqlalchemy import create_engine, text
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text("UPDATE cascade_posts SET status = 'skipped' WHERE id = :id"), {"id": cascade_id})
        conn.commit()
    return {"cascade_id": cascade_id, "status": "skipped"}


@router.post("/trigger")
async def trigger_cascade(req: TriggerCascadeRequest):
    """Manually trigger a cascade for a published post."""
    from services.cascade_publisher import CascadePublisher
    svc = CascadePublisher()
    return await svc.on_post_published(
        original_post_id=req.original_post_id,
        platform=req.platform,
        account_id=req.account_id,
    )


@router.post("/cycle")
async def run_cycle():
    """Process all pending cascade posts whose delay has elapsed."""
    from services.cascade_publisher import CascadePublisher
    svc = CascadePublisher()
    return await svc.run_cascade_cycle()


@router.post("/check-gates")
async def check_gates():
    """Check performance gates on gated cascade posts."""
    from services.cascade_publisher import CascadePublisher
    svc = CascadePublisher()
    return await svc.check_performance_gates()


@router.get("/stats")
async def get_stats():
    """Cascade performance statistics."""
    from services.cascade_publisher import CascadePublisher
    svc = CascadePublisher()
    return await svc.get_stats()
