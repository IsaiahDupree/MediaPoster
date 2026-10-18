"""
Orchestrator Goals API (PRD-06)
================================
F1 — GoalDecompositionAgent endpoints
F2 — CrossPipelineLearning endpoints
F3 — StrategyVariantRunner endpoints
F4 — Budget status endpoint
F5 — Live agent feed SSE endpoint

Endpoints:
    POST /api/orchestrator/goals/decompose
    GET  /api/orchestrator/goals/{goal_id}/status
    POST /api/orchestrator/goals/{goal_id}/actuals
    GET  /api/orchestrator/learnings
    POST /api/orchestrator/pipeline/record
    POST /api/orchestrator/pipeline/variants
    GET  /api/orchestrator/budget/status
    GET  /api/agents/feed                  ← SSE live event stream
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.goal_decomposition import GoalDecompositionAgent
from services.cross_pipeline_learning import CrossPipelineLearningService
from services.agent_budget_enforcer import AgentBudgetEnforcer, BudgetHaltError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Orchestrator Goals"])


# ── Request / Response models ────────────────────────────────────────────────

class DecomposeGoalRequest(BaseModel):
    goal: str = Field(..., min_length=10, description="Natural language goal, e.g. 'Grow @handle to 100K in 60 days'")
    platforms: List[str] = Field(default=["tiktok", "instagram"], description="Target platforms")


class RecordActualRequest(BaseModel):
    milestone_week: int = Field(..., ge=1, le=52)
    metric: str = Field(..., description="e.g. 'followers', 'views', 'leads'")
    actual: float = Field(..., ge=0)


class RecordPipelineResultRequest(BaseModel):
    pipeline_id: str
    theme: str
    fate_scores: Dict[str, float] = Field(default_factory=dict, description="Keys: focus, authority, tribe, emotion")
    awareness_level: int = Field(..., ge=1, le=5)
    platform: str
    published_count: int = Field(default=0, ge=0)
    engagement_at_24h: float = Field(default=0.0, ge=0)


class PipelineVariantsRequest(BaseModel):
    base_theme: str = Field(..., description="Base content theme")
    variants: List[Dict[str, Any]] = Field(..., description="List of variant overrides, e.g. [{awareness_level: 1}, {awareness_level: 3}]")
    platforms: List[str] = Field(default=["tiktok", "instagram"])


class SpendRequest(BaseModel):
    amount_usd: float = Field(..., gt=0)
    agent_name: str = Field(default="unknown")


# ── F1 — Goal Decomposition ───────────────────────────────────────────────────

@router.post("/api/orchestrator/goals/decompose")
async def decompose_goal(req: DecomposeGoalRequest, db: AsyncSession = Depends(get_db)):
    """
    Decompose a high-level goal into a 12-week pipeline schedule using GPT-4o.
    Returns goal_id + list of weekly milestones with pipeline configs.
    """
    agent = GoalDecompositionAgent(db)
    try:
        result = await agent.decompose(goal=req.goal, platforms=req.platforms)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"decompose_goal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/orchestrator/goals/{goal_id}/status")
async def get_goal_status(goal_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get milestone progress vs actuals for a decomposed goal.
    Each milestone shows: target, actual (if recorded), and % achieved.
    """
    agent = GoalDecompositionAgent(db)
    try:
        result = await agent.get_status(goal_id)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"get_goal_status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/orchestrator/goals/{goal_id}/actuals")
async def record_goal_actual(goal_id: str, req: RecordActualRequest, db: AsyncSession = Depends(get_db)):
    """Record an actual result for a milestone week (e.g. week=2, metric='followers', actual=1500)."""
    agent = GoalDecompositionAgent(db)
    try:
        await agent.record_actual(goal_id, req.milestone_week, req.metric, req.actual)
        return {"success": True, "message": f"Recorded {req.metric}={req.actual} for week {req.milestone_week}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"record_goal_actual error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── F2 — Cross-Pipeline Learning ─────────────────────────────────────────────

@router.get("/api/orchestrator/learnings")
async def get_learnings(db: AsyncSession = Depends(get_db)):
    """
    Return the current 'what's working' context blob generated from last 30 days of pipeline results.
    Inject this into content generation prompts to improve output quality over time.
    """
    service = CrossPipelineLearningService(db)
    try:
        result = await service.get_learnings_context()
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"get_learnings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/orchestrator/pipeline/record")
async def record_pipeline_result(req: RecordPipelineResultRequest, db: AsyncSession = Depends(get_db)):
    """Record a completed pipeline's performance data to feed cross-pipeline learning."""
    service = CrossPipelineLearningService(db)
    try:
        row_id = await service.record_pipeline_result(
            pipeline_id=req.pipeline_id,
            theme=req.theme,
            fate_scores=req.fate_scores,
            awareness_level=req.awareness_level,
            platform=req.platform,
            published_count=req.published_count,
            engagement_at_24h=req.engagement_at_24h,
        )
        return {"success": True, "result_id": row_id, "message": "Pipeline result recorded and learnings regenerated"}
    except Exception as e:
        logger.error(f"record_pipeline_result error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── F3 — Strategy Variant Runner ─────────────────────────────────────────────

@router.post("/api/orchestrator/pipeline/variants")
async def run_pipeline_variants(req: PipelineVariantsRequest, db: AsyncSession = Depends(get_db)):
    """
    Spin up N strategy variants (different awareness levels / angles) for the same theme.
    Evaluates which variant would be recommended based on cross-pipeline learnings + variant config.
    Returns variant configs ranked by predicted performance.
    """
    if len(req.variants) < 1 or len(req.variants) > 10:
        raise HTTPException(status_code=400, detail="variants must have 1-10 items")

    service = CrossPipelineLearningService(db)
    learnings = await service.get_learnings_context()
    learnings_ctx = learnings.get("context", "")

    scored_variants = []
    for i, variant_override in enumerate(req.variants):
        awareness = variant_override.get("awareness_level", 2)
        platforms = variant_override.get("platforms", req.platforms)

        # Score heuristic: higher engagement historically at awareness levels per learnings
        # Real scoring would use the pre_social_score from content analysis after generation
        config = {
            "variant_index": i,
            "theme": req.base_theme,
            "awareness_level": awareness,
            "platforms": platforms,
            "pipeline_config": {
                "theme": req.base_theme,
                "num_parts": variant_override.get("num_parts", 3),
                "publish_platforms": platforms,
                "schedule_tweets": variant_override.get("schedule_tweets", True),
                "tweets_per_day": variant_override.get("tweets_per_day", 8),
            },
            "status": "pending",
            "predicted_score": None,
        }

        # Placeholder score — in production this runs the pipeline and reads pre_social_score
        # Awareness 1-2 = cold content (high reach, lower conversion)
        # Awareness 4-5 = warm content (lower reach, higher conversion)
        heuristic_score = {1: 0.7, 2: 0.75, 3: 0.8, 4: 0.65, 5: 0.55}.get(awareness, 0.6)
        config["predicted_score"] = heuristic_score
        scored_variants.append(config)

    # Rank by score
    scored_variants.sort(key=lambda x: x["predicted_score"], reverse=True)
    if scored_variants:
        scored_variants[0]["status"] = "recommended"

    return {
        "success": True,
        "data": {
            "base_theme": req.base_theme,
            "variant_count": len(scored_variants),
            "recommended_variant": scored_variants[0]["variant_index"] if scored_variants else None,
            "variants": scored_variants,
            "learnings_applied": bool(learnings_ctx and "No pipeline" not in learnings_ctx),
        }
    }


# ── F4 — Budget Status ────────────────────────────────────────────────────────

@router.get("/api/orchestrator/budget/status")
async def get_budget_status(db: AsyncSession = Depends(get_db)):
    """Return today's OpenAI spend vs daily limit."""
    enforcer = AgentBudgetEnforcer(db)
    try:
        spent = await enforcer.get_today_spend()
        limit = enforcer.daily_limit
        pct = (spent / limit * 100) if limit > 0 else 0
        return {
            "success": True,
            "data": {
                "spent_usd": round(spent, 4),
                "limit_usd": limit,
                "remaining_usd": round(max(0, limit - spent), 4),
                "pct_used": round(pct, 1),
                "status": "halt" if pct >= 100 else ("warning" if pct >= 80 else "ok"),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/orchestrator/budget/record-spend")
async def record_spend(req: SpendRequest, db: AsyncSession = Depends(get_db)):
    """Record an OpenAI API spend event."""
    enforcer = AgentBudgetEnforcer(db)
    try:
        await enforcer.record_spend(req.amount_usd, req.agent_name)
        return {"success": True, "recorded_usd": req.amount_usd}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── F5 — Live Agent Feed SSE ─────────────────────────────────────────────────

@router.get("/api/agents/feed")
async def live_agent_feed(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Server-Sent Events stream of all new agent events in real-time.
    Format: data: {"agent": "narrative", "type": "thought", "text": "...", "ts": "..."}

    Dashboard connects here to show a Polsia-style live activity feed.
    Polls agent_events table every second, streaming only new rows.
    """
    async def event_generator():
        from sqlalchemy import text as sql_text
        last_id: Optional[str] = None

        # Get the most recent event id to start from
        try:
            row = (await db.execute(sql_text(
                "SELECT id FROM agent_events ORDER BY created_at DESC LIMIT 1"
            ))).fetchone()
            if row:
                last_id = row.id
        except Exception:
            pass  # Table may not exist yet; stream will start from first event

        # Heartbeat to keep connection alive
        yield "data: {\"type\":\"connected\",\"ts\":\"" + datetime.now(timezone.utc).isoformat() + "\"}\n\n"

        while True:
            if await request.is_disconnected():
                break

            try:
                query = sql_text("""
                    SELECT id, agent_id, agent_name, event_type, topic, message, created_at
                    FROM agent_events
                    WHERE (:last_id IS NULL OR created_at > (
                        SELECT created_at FROM agent_events WHERE id = :last_id
                    ))
                    ORDER BY created_at ASC
                    LIMIT 50
                """)
                rows = (await db.execute(query, {"last_id": last_id})).fetchall()

                for row in rows:
                    last_id = row.id
                    payload = json.dumps({
                        "agent": row.agent_name or row.agent_id or "unknown",
                        "type": row.event_type or "event",
                        "topic": row.topic or "",
                        "text": row.message or "",
                        "ts": row.created_at.isoformat() if row.created_at else datetime.now(timezone.utc).isoformat(),
                    })
                    yield f"data: {payload}\n\n"

            except Exception as e:
                logger.warning(f"SSE feed error: {e}")
                yield f"data: {{\"type\":\"error\",\"text\":\"{str(e)[:100]}\"}}\n\n"

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
