"""
Engagement Autopilot API
=========================
Endpoints for managing AI-powered engagement automation.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/engagement", tags=["engagement-autopilot"])


class CommentBatch(BaseModel):
    account_id: str
    platform: str
    comments: List[Dict[str, Any]]  # [{text, post_caption, username, post_id}]


class EngagementCommentRequest(BaseModel):
    target_caption: str
    platform: str


class SettingsUpdate(BaseModel):
    mode: Optional[str] = None  # full_auto, reply_only, assist, monitor, off


class SessionRequest(BaseModel):
    account_id: str
    platform: str


@router.get("/dashboard")
async def engagement_dashboard():
    """Engagement overview: stats, pending actions, mode."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    return await svc.get_dashboard()


@router.get("/actions")
async def list_actions(
    status: str = Query("pending"),
    platform: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """List engagement actions by status."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    if status == "pending":
        actions = await svc.get_pending_actions(platform=platform, limit=limit)
    else:
        # Generic query for other statuses
        from sqlalchemy import create_engine, text
        import os
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(db_url)
        query = """SELECT id, account_id, platform, action_type, target_user,
                          target_post_id, content, status, created_at
                   FROM engagement_actions WHERE status = :status"""
        params: Dict[str, Any] = {"status": status, "limit": limit}
        if platform:
            query += " AND platform = :platform"
            params["platform"] = platform
        query += " ORDER BY created_at DESC LIMIT :limit"
        with engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()
        actions = [
            {
                "id": str(r[0]), "account_id": r[1], "platform": r[2],
                "action_type": r[3], "target_user": r[4], "content": r[6],
                "status": r[7], "created_at": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ]
    return {"actions": actions, "total": len(actions)}


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: str):
    """Approve a pending engagement action."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    return await svc.approve_action(action_id)


@router.post("/actions/{action_id}/reject")
async def reject_action(action_id: str):
    """Reject a pending engagement action."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    return await svc.reject_action(action_id)


@router.post("/replies/generate")
async def generate_replies(req: CommentBatch):
    """Generate AI replies for a batch of comments."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    return await svc.generate_comment_replies(
        account_id=req.account_id,
        platform=req.platform,
        comments=req.comments,
    )


@router.post("/comment/generate")
async def generate_engagement_comment(req: EngagementCommentRequest):
    """Generate a proactive engagement comment for niche content."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    return await svc.generate_engagement_comment(
        target_caption=req.target_caption,
        platform=req.platform,
    )


@router.post("/session/start")
async def start_session(req: SessionRequest):
    """Start an engagement session for an account."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    return await svc.start_session(account_id=req.account_id, platform=req.platform)


@router.post("/session/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop an active engagement session."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    return await svc.end_session(session_id)


@router.get("/settings")
async def get_settings():
    """Get current engagement settings."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    return await svc.get_settings()


@router.put("/settings")
async def update_settings(req: SettingsUpdate):
    """Update engagement settings (mode, etc.)."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    return await svc.update_settings(req.dict(exclude_none=True))


@router.get("/stats")
async def get_stats(period: str = Query("7d")):
    """Engagement statistics."""
    from services.engagement_autopilot import EngagementAutopilot
    days = int(period.rstrip("d")) if period.endswith("d") else 7
    svc = EngagementAutopilot()
    return await svc.get_stats(period_days=days)


@router.get("/rate-check")
async def check_rate_limit(
    account_id: str,
    platform: str,
    action_type: str,
):
    """Check if an action is within daily rate limits."""
    from services.engagement_autopilot import EngagementAutopilot
    svc = EngagementAutopilot()
    allowed, reason = await svc.can_perform_action(account_id, platform, action_type)
    return {"allowed": allowed, "reason": reason}
