"""
AgentBudgetEnforcer (PRD-06 F4)
=================================
Track OpenAI spend per day. Pause non-critical agents at 80% of daily limit.
Halt all agents at 100%. Emit agent_events for warnings and halts.

Usage:
    enforcer = AgentBudgetEnforcer(db_session)
    await enforcer.check_budget()          # raises BudgetHaltError if over limit
    await enforcer.record_spend(0.015)     # log a spend amount
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DAILY_BUDGET_USD = float(os.environ.get("AGENT_DAILY_BUDGET_USD", "10.0"))


class BudgetHaltError(Exception):
    """Raised when the daily budget is exhausted."""
    pass


async def _ensure_tables(session: AsyncSession) -> None:
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS agent_spend_log (
            id          TEXT PRIMARY KEY,
            amount_usd  FLOAT NOT NULL,
            agent_name  TEXT,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """))
    await session.commit()


class AgentBudgetEnforcer:
    def __init__(self, session: AsyncSession, daily_limit_usd: float = DAILY_BUDGET_USD):
        self.session = session
        self.daily_limit = daily_limit_usd

    async def record_spend(self, amount_usd: float, agent_name: str = "unknown") -> None:
        """Log an OpenAI spend event."""
        await _ensure_tables(self.session)
        await self.session.execute(text("""
            INSERT INTO agent_spend_log (id, amount_usd, agent_name)
            VALUES (:id, :amt, :agent)
        """), {"id": str(uuid4()), "amt": amount_usd, "agent": agent_name})
        await self.session.commit()

    async def get_today_spend(self) -> float:
        """Return total USD spent today (UTC)."""
        await _ensure_tables(self.session)
        row = (await self.session.execute(text("""
            SELECT COALESCE(SUM(amount_usd), 0) AS total
            FROM agent_spend_log
            WHERE recorded_at >= DATE_TRUNC('day', NOW() AT TIME ZONE 'UTC')
        """))).fetchone()
        return float(row.total) if row else 0.0

    async def check_budget(self, agent_name: str = "unknown") -> Dict[str, Any]:
        """
        Check if agent is allowed to run.
        Emits budget_warning event at 80%, raises BudgetHaltError at 100%.
        Returns dict with spend info.
        """
        spent = await self.get_today_spend()
        pct = (spent / self.daily_limit * 100) if self.daily_limit > 0 else 0
        remaining = max(0.0, self.daily_limit - spent)

        status = {
            "spent_usd": round(spent, 4),
            "limit_usd": self.daily_limit,
            "remaining_usd": round(remaining, 4),
            "pct_used": round(pct, 1),
            "agent_name": agent_name,
        }

        if pct >= 100:
            await self._emit_event("agent_budget_halt", f"Daily budget exhausted (${spent:.2f}/${self.daily_limit:.2f}). All agents halted.", agent_name)
            raise BudgetHaltError(
                f"Daily budget exhausted: ${spent:.2f} spent of ${self.daily_limit:.2f} limit. "
                "Agents will resume tomorrow UTC midnight."
            )

        if pct >= 80:
            await self._emit_event("agent_budget_warning", f"Budget at {pct:.0f}% (${spent:.2f}/${self.daily_limit:.2f}). Non-critical agents paused.", agent_name)
            logger.warning(f"AgentBudgetEnforcer: {pct:.0f}% of daily budget used by {agent_name}")

        return status

    async def _emit_event(self, event_type: str, message: str, agent_name: str) -> None:
        """Write a budget event to agent_events table if it exists."""
        try:
            await self.session.execute(text("""
                INSERT INTO agent_events (id, agent_id, agent_name, event_type, topic, message, created_at)
                VALUES (:id, :agent_id, :agent_name, :event_type, 'budget', :message, NOW())
                ON CONFLICT DO NOTHING
            """), {
                "id": str(uuid4()),
                "agent_id": f"budget_enforcer_{agent_name}",
                "agent_name": agent_name,
                "event_type": event_type,
                "message": message,
            })
            await self.session.commit()
        except Exception as e:
            # Don't fail the budget check if event logging fails
            logger.warning(f"AgentBudgetEnforcer: could not write event: {e}")
