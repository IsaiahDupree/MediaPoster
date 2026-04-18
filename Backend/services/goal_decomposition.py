"""
GoalDecompositionAgent (PRD-06 F1)
====================================
Accept a natural language goal, use GPT-4o to decompose it into a schedule of
PipelineConfig objects, persist them, and track milestone progress vs actuals.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _ensure_goal_tables(session: AsyncSession) -> None:
    """Create goal decomposition tables if they don't exist (idempotent)."""
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS decomposed_goals (
            id          TEXT PRIMARY KEY,
            goal_text   TEXT NOT NULL,
            platforms   TEXT NOT NULL,       -- JSON array
            milestones  TEXT NOT NULL,       -- JSON array of milestone objects
            status      TEXT NOT NULL DEFAULT 'active',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS goal_milestone_actuals (
            id          TEXT PRIMARY KEY,
            goal_id     TEXT NOT NULL REFERENCES decomposed_goals(id) ON DELETE CASCADE,
            milestone_week INT NOT NULL,
            metric      TEXT NOT NULL,
            target      FLOAT,
            actual      FLOAT,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """))
    await session.commit()


# ── OpenAI call ───────────────────────────────────────────────────────────────

async def _decompose_with_gpt4o(goal: str, platforms: List[str]) -> Dict[str, Any]:
    """Call GPT-4o to break a high-level goal into 30/60/90-day milestones."""
    import httpx

    platform_str = ", ".join(platforms)
    prompt = f"""You are a content strategy AI. Decompose this growth goal into an actionable 90-day content schedule.

GOAL: {goal}
PLATFORMS: {platform_str}

Return ONLY valid JSON with this exact schema:
{{
  "summary": "One sentence restatement of the goal",
  "milestones": [
    {{
      "week": 1,
      "theme": "content theme for this week",
      "awareness_level": 1,
      "platforms": ["tiktok"],
      "target_metric": "followers",
      "target_value": 500,
      "pipeline_config": {{
        "theme": "short descriptive theme",
        "num_parts": 3,
        "publish_platforms": ["tiktok", "instagram"],
        "schedule_tweets": true,
        "tweets_per_day": 8
      }}
    }}
  ],
  "total_weeks": 12,
  "primary_kpi": "followers | views | leads | revenue"
}}

Include 12 milestone entries (one per week). Vary awareness levels (1-5) across the schedule.
awareness_level 1=pure story/cold audience, 5=direct offer/warm audience."""

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set — cannot call GPT-4o for goal decomposition")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()

    raw = data["choices"][0]["message"]["content"]
    parsed = json.loads(raw)

    # Validate required keys
    for key in ("summary", "milestones", "total_weeks", "primary_kpi"):
        if key not in parsed:
            raise ValueError(f"GPT-4o response missing required key: {key}")
    if not parsed["milestones"]:
        raise ValueError("GPT-4o returned empty milestones list")

    return parsed


# ── GoalDecompositionAgent ────────────────────────────────────────────────────

class GoalDecompositionAgent:
    """
    Decomposes a natural language goal into a 12-week pipeline schedule.

    Usage:
        agent = GoalDecompositionAgent(db_session)
        result = await agent.decompose(
            goal="Grow @the_isaiah_dupree to 100K followers in 60 days",
            platforms=["tiktok", "instagram"]
        )
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def decompose(self, goal: str, platforms: List[str]) -> Dict[str, Any]:
        """Decompose goal and persist the schedule. Returns goal_id + milestones."""
        await _ensure_goal_tables(self.session)

        logger.info(f"GoalDecompositionAgent: decomposing goal='{goal[:60]}...' platforms={platforms}")
        decomposed = await _decompose_with_gpt4o(goal, platforms)

        goal_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await self.session.execute(text("""
            INSERT INTO decomposed_goals (id, goal_text, platforms, milestones, status, created_at, updated_at)
            VALUES (:id, :goal_text, :platforms, :milestones, 'active', :now, :now)
        """), {
            "id": goal_id,
            "goal_text": goal,
            "platforms": json.dumps(platforms),
            "milestones": json.dumps(decomposed["milestones"]),
            "now": now,
        })
        await self.session.commit()

        logger.info(f"GoalDecompositionAgent: created goal_id={goal_id} with {len(decomposed['milestones'])} milestones")

        return {
            "goal_id": goal_id,
            "summary": decomposed["summary"],
            "total_weeks": decomposed["total_weeks"],
            "primary_kpi": decomposed["primary_kpi"],
            "milestones": decomposed["milestones"],
            "status": "active",
            "created_at": now,
        }

    async def get_status(self, goal_id: str) -> Dict[str, Any]:
        """Return milestone progress with actuals vs targets."""
        await _ensure_goal_tables(self.session)

        row = (await self.session.execute(
            text("SELECT id, goal_text, platforms, milestones, status, created_at FROM decomposed_goals WHERE id = :id"),
            {"id": goal_id},
        )).fetchone()

        if not row:
            raise ValueError(f"Goal not found: {goal_id}")

        milestones = json.loads(row.milestones)

        actuals_rows = (await self.session.execute(
            text("SELECT milestone_week, metric, target, actual FROM goal_milestone_actuals WHERE goal_id = :id ORDER BY milestone_week"),
            {"id": goal_id},
        )).fetchall()

        actuals_by_week: Dict[int, Dict] = {}
        for r in actuals_rows:
            actuals_by_week.setdefault(r.milestone_week, {})[r.metric] = {
                "target": r.target, "actual": r.actual,
                "pct": round((r.actual / r.target * 100), 1) if r.target else None,
            }

        # Annotate milestones with actuals
        current_week = _current_week_number(row.created_at)
        for m in milestones:
            week = m["week"]
            m["actuals"] = actuals_by_week.get(week, {})
            m["state"] = "future" if week > current_week else ("active" if week == current_week else "past")

        return {
            "goal_id": goal_id,
            "goal_text": row.goal_text,
            "platforms": json.loads(row.platforms),
            "status": row.status,
            "current_week": current_week,
            "milestones": milestones,
        }

    async def record_actual(self, goal_id: str, milestone_week: int, metric: str, actual: float) -> None:
        """Record an actual result for a milestone week."""
        await _ensure_goal_tables(self.session)

        # Get target from milestone
        row = (await self.session.execute(
            text("SELECT milestones FROM decomposed_goals WHERE id = :id"), {"id": goal_id}
        )).fetchone()
        if not row:
            raise ValueError(f"Goal not found: {goal_id}")

        milestones = json.loads(row.milestones)
        target = None
        for m in milestones:
            if m["week"] == milestone_week and m.get("target_metric") == metric:
                target = m.get("target_value")
                break

        await self.session.execute(text("""
            INSERT INTO goal_milestone_actuals (id, goal_id, milestone_week, metric, target, actual, recorded_at)
            VALUES (:id, :goal_id, :week, :metric, :target, :actual, NOW())
            ON CONFLICT DO NOTHING
        """), {
            "id": str(uuid4()), "goal_id": goal_id, "week": milestone_week,
            "metric": metric, "target": target, "actual": actual,
        })
        await self.session.commit()


def _current_week_number(created_at) -> int:
    """Return how many weeks have elapsed since the goal was created."""
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    elapsed = (now - created_at.astimezone(timezone.utc)).days
    return max(1, (elapsed // 7) + 1)
