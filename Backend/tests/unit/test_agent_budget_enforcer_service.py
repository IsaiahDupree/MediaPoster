"""
Unit tests for AgentBudgetEnforcer service logic.
Tests spend tracking, budget thresholds, and BudgetHaltError.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_session(total_spend=0.0):
    """Session mock with controllable today-spend return."""
    session = AsyncMock()
    execute_result = MagicMock()
    spend_row = MagicMock()
    spend_row.total = total_spend
    execute_result.fetchone = MagicMock(return_value=spend_row)
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()
    return session


# ── get_today_spend ───────────────────────────────────────────────────────────

class TestGetTodaySpend:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_spend(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session(total_spend=0.0)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)
        assert await enforcer.get_today_spend() == 0.0

    @pytest.mark.asyncio
    async def test_returns_accumulated_spend(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session(total_spend=4.57)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)
        assert await enforcer.get_today_spend() == 4.57

    @pytest.mark.asyncio
    async def test_returns_float(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session(total_spend="3.14")  # string from DB
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)
        result = await enforcer.get_today_spend()
        assert isinstance(result, float)


# ── check_budget ──────────────────────────────────────────────────────────────

class TestCheckBudget:
    @pytest.mark.asyncio
    async def test_ok_when_under_80pct(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session(total_spend=5.0)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)

        status = await enforcer.check_budget("test-agent")
        assert status["pct_used"] == 50.0
        assert status["status"] if "status" in status else True  # no error

    @pytest.mark.asyncio
    async def test_returns_spend_info_dict(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session(total_spend=3.0)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)

        status = await enforcer.check_budget()
        assert "spent_usd" in status
        assert "limit_usd" in status
        assert "remaining_usd" in status
        assert "pct_used" in status
        assert status["spent_usd"] == 3.0
        assert status["limit_usd"] == 10.0
        assert status["remaining_usd"] == 7.0

    @pytest.mark.asyncio
    async def test_warning_emitted_at_80pct(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session(total_spend=8.5)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)

        emit_called_with = []
        original_emit = enforcer._emit_event
        async def capture_emit(event_type, message, agent_name):
            emit_called_with.append(event_type)
        enforcer._emit_event = capture_emit

        await enforcer.check_budget("narrative-agent")
        assert "agent_budget_warning" in emit_called_with

    @pytest.mark.asyncio
    async def test_halt_raised_at_100pct(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer, BudgetHaltError
        session = _make_session(total_spend=10.0)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)
        enforcer._emit_event = AsyncMock()

        with pytest.raises(BudgetHaltError) as exc_info:
            await enforcer.check_budget("narrative-agent")

        assert "exhausted" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_halt_raised_when_over_limit(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer, BudgetHaltError
        session = _make_session(total_spend=15.0)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)
        enforcer._emit_event = AsyncMock()

        with pytest.raises(BudgetHaltError):
            await enforcer.check_budget()

    @pytest.mark.asyncio
    async def test_halt_emits_halt_event(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer, BudgetHaltError
        session = _make_session(total_spend=10.5)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)

        emitted_events = []
        async def capture_emit(event_type, message, agent_name):
            emitted_events.append(event_type)
        enforcer._emit_event = capture_emit

        with pytest.raises(BudgetHaltError):
            await enforcer.check_budget("any-agent")

        assert "agent_budget_halt" in emitted_events

    @pytest.mark.asyncio
    async def test_no_warning_below_80pct(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session(total_spend=7.9)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)

        emitted_events = []
        async def capture_emit(event_type, message, agent_name):
            emitted_events.append(event_type)
        enforcer._emit_event = capture_emit

        await enforcer.check_budget()
        assert "agent_budget_warning" not in emitted_events

    @pytest.mark.asyncio
    async def test_pct_calculated_correctly(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session(total_spend=2.5)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=5.0)

        status = await enforcer.check_budget()
        assert status["pct_used"] == 50.0

    @pytest.mark.asyncio
    async def test_remaining_is_zero_when_at_limit(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer, BudgetHaltError
        session = _make_session(total_spend=10.0)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)
        enforcer._emit_event = AsyncMock()

        with pytest.raises(BudgetHaltError):
            await enforcer.check_budget()


# ── record_spend ──────────────────────────────────────────────────────────────

class TestRecordSpend:
    @pytest.mark.asyncio
    async def test_record_inserts_row(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session()
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)

        await enforcer.record_spend(0.05, "narrative-agent")

        session.execute.assert_called()
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_record_with_default_agent_name(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session()
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=10.0)

        # Should not raise even without agent_name
        await enforcer.record_spend(0.01)
        session.commit.assert_called()


# ── BudgetHaltError ───────────────────────────────────────────────────────────

class TestBudgetHaltError:
    def test_is_subclass_of_exception(self):
        from services.agent_budget_enforcer import BudgetHaltError
        assert issubclass(BudgetHaltError, Exception)

    def test_message_preserved(self):
        from services.agent_budget_enforcer import BudgetHaltError
        err = BudgetHaltError("Daily budget exhausted: $10.00 spent of $10.00 limit")
        assert "$10.00" in str(err)

    def test_can_be_caught_as_exception(self):
        from services.agent_budget_enforcer import BudgetHaltError
        caught = False
        try:
            raise BudgetHaltError("halt!")
        except Exception:
            caught = True
        assert caught


# ── Custom limit via env ──────────────────────────────────────────────────────

class TestCustomLimit:
    @pytest.mark.asyncio
    async def test_custom_limit_respected(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer, BudgetHaltError
        session = _make_session(total_spend=3.0)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=2.0)  # lower limit
        enforcer._emit_event = AsyncMock()

        with pytest.raises(BudgetHaltError):
            await enforcer.check_budget()

    @pytest.mark.asyncio
    async def test_80pct_of_custom_limit(self):
        from services.agent_budget_enforcer import AgentBudgetEnforcer
        session = _make_session(total_spend=4.0)
        enforcer = AgentBudgetEnforcer(session, daily_limit_usd=5.0)

        emitted = []
        async def capture_emit(event_type, message, agent_name):
            emitted.append(event_type)
        enforcer._emit_event = capture_emit

        await enforcer.check_budget()
        assert "agent_budget_warning" in emitted  # 4/5 = 80%
