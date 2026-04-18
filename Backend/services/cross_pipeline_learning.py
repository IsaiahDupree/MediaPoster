"""
CrossPipelineLearningService (PRD-06 F2)
=========================================
After every completed pipeline, store performance data.
Query last 30 days, identify what's working, inject into the next pipeline's prompt.

Usage:
    service = CrossPipelineLearningService(db_session)
    await service.record_pipeline_result(pipeline_id, theme, fate_scores, ...)
    context = await service.get_learnings_context()
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


async def _ensure_tables(session: AsyncSession) -> None:
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS pipeline_results (
            id                TEXT PRIMARY KEY,
            pipeline_id       TEXT NOT NULL,
            theme             TEXT NOT NULL,
            fate_focus        FLOAT,
            fate_authority    FLOAT,
            fate_tribe        FLOAT,
            fate_emotion      FLOAT,
            awareness_level   INT,
            platform          TEXT,
            published_count   INT DEFAULT 0,
            engagement_at_24h FLOAT DEFAULT 0,
            completed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS pipeline_learnings (
            id           TEXT PRIMARY KEY,
            context_blob TEXT NOT NULL,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """))
    await session.commit()


class CrossPipelineLearningService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_pipeline_result(
        self,
        pipeline_id: str,
        theme: str,
        fate_scores: Dict[str, float],
        awareness_level: int,
        platform: str,
        published_count: int,
        engagement_at_24h: float,
    ) -> str:
        """Persist a completed pipeline's performance data."""
        await _ensure_tables(self.session)

        row_id = str(uuid4())
        await self.session.execute(text("""
            INSERT INTO pipeline_results
                (id, pipeline_id, theme, fate_focus, fate_authority, fate_tribe, fate_emotion,
                 awareness_level, platform, published_count, engagement_at_24h)
            VALUES
                (:id, :pipeline_id, :theme, :focus, :authority, :tribe, :emotion,
                 :awareness, :platform, :published, :engagement)
        """), {
            "id": row_id,
            "pipeline_id": pipeline_id,
            "theme": theme,
            "focus": fate_scores.get("focus", 0.0),
            "authority": fate_scores.get("authority", 0.0),
            "tribe": fate_scores.get("tribe", 0.0),
            "emotion": fate_scores.get("emotion", 0.0),
            "awareness": awareness_level,
            "platform": platform,
            "published": published_count,
            "engagement": engagement_at_24h,
        })
        await self.session.commit()
        logger.info(f"CrossPipelineLearning: recorded result for pipeline {pipeline_id}")

        # Regenerate learnings blob after each new result
        await self._regenerate_learnings()
        return row_id

    async def get_learnings_context(self) -> Dict[str, Any]:
        """Return the current 'what's working' context blob."""
        await _ensure_tables(self.session)

        row = (await self.session.execute(
            text("SELECT context_blob, generated_at FROM pipeline_learnings ORDER BY generated_at DESC LIMIT 1")
        )).fetchone()

        if not row:
            return {"context": "No pipeline results yet — run at least one pipeline to generate learnings.", "generated_at": None}

        return {"context": row.context_blob, "generated_at": row.generated_at.isoformat() if row.generated_at else None}

    async def get_prompt_injection(self) -> str:
        """Return a compact string to inject into the next pipeline's content generation prompt."""
        learnings = await self.get_learnings_context()
        ctx = learnings.get("context", "")
        if not ctx or "No pipeline" in ctx:
            return ""
        return f"\n\n[CROSS-PIPELINE LEARNINGS — USE THESE INSIGHTS]\n{ctx}\n"

    async def _regenerate_learnings(self) -> None:
        """Query last 30 days, call GPT-4o to summarize what's working."""
        rows = (await self.session.execute(text("""
            SELECT theme, fate_focus, fate_authority, fate_tribe, fate_emotion,
                   awareness_level, platform, published_count, engagement_at_24h
            FROM pipeline_results
            WHERE completed_at > NOW() - INTERVAL '30 days'
            ORDER BY engagement_at_24h DESC
            LIMIT 50
        """))).fetchall()

        if not rows:
            return

        results_json = json.dumps([
            {
                "theme": r.theme,
                "fate": {"focus": r.fate_focus, "authority": r.fate_authority,
                         "tribe": r.fate_tribe, "emotion": r.fate_emotion},
                "awareness_level": r.awareness_level,
                "platform": r.platform,
                "published": r.published_count,
                "engagement_24h": r.engagement_at_24h,
            }
            for r in rows
        ], indent=2)

        if not OPENAI_API_KEY:
            logger.warning("CrossPipelineLearning: OPENAI_API_KEY not set, skipping learnings generation")
            return

        prompt = f"""Analyze these content pipeline results from the last 30 days and write a concise 'what's working' summary for a content AI.

PIPELINE RESULTS:
{results_json}

Write 5-8 bullet points covering:
- Which themes drove the highest engagement
- Which FATE dimensions correlate with success (focus/authority/tribe/emotion)
- Which awareness levels perform best per platform
- Any patterns in publish_count vs engagement
- Hook types or angles to repeat

Format as plain bullet points. Be specific, reference actual theme names and numbers."""

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.5,
                    },
                )
                resp.raise_for_status()
                context_blob = resp.json()["choices"][0]["message"]["content"]

            await self.session.execute(text("""
                INSERT INTO pipeline_learnings (id, context_blob, generated_at)
                VALUES (:id, :blob, NOW())
            """), {"id": str(uuid4()), "blob": context_blob})
            await self.session.commit()
            logger.info("CrossPipelineLearning: regenerated learnings context")

        except Exception as e:
            logger.error(f"CrossPipelineLearning: failed to regenerate learnings: {e}")
