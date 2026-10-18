"""
Unit Tests for Agent Scheduler (AC-002, AC-003, AC-004)
=======================================================
Tests for agent scheduling, run tracking, and step timeline.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from services.agent_scheduler import AgentScheduler, get_agent_scheduler


class TestAgentScheduler:
    """Test suite for Agent Scheduler Service (AC-002)"""

    @pytest.fixture
    async def scheduler(self):
        """Get scheduler instance"""
        scheduler = get_agent_scheduler()
        yield scheduler
        # Cleanup is handled by singleton

    @pytest.mark.asyncio
    async def test_create_schedule_with_interval(self, scheduler):
        """Test creating a schedule with interval_seconds"""
        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Hourly Schedule",
            description="Test schedule running every hour",
            interval_seconds=3600,
            enabled=True,
            config={"test": "value"}
        )

        assert schedule_id is not None
        assert isinstance(schedule_id, str)

        # Verify next_run_at was calculated
        next_run = await scheduler.get_next_run_time(schedule_id)
        assert next_run is not None

        # Should be approximately 1 hour from now
        expected = datetime.now(timezone.utc) + timedelta(hours=1)
        time_diff = abs((next_run - expected).total_seconds())
        assert time_diff < 5  # Within 5 seconds

    @pytest.mark.asyncio
    async def test_create_schedule_with_cron(self, scheduler):
        """Test creating a schedule with cron expression"""
        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Daily Schedule",
            description="Test schedule running daily at 9am",
            cron_expression="0 9 * * *",
            enabled=True
        )

        assert schedule_id is not None

        # Verify next_run_at was calculated
        next_run = await scheduler.get_next_run_time(schedule_id)
        assert next_run is not None
        assert next_run > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_create_schedule_requires_interval_or_cron(self, scheduler):
        """Test that schedule creation fails without interval or cron"""
        with pytest.raises(ValueError, match="Either interval_seconds or cron_expression is required"):
            await scheduler.create_schedule(
                agent_type="test_agent",
                schedule_name="Invalid Schedule"
            )

    @pytest.mark.asyncio
    async def test_update_schedule_enable_disable(self, scheduler):
        """Test enabling/disabling a schedule"""
        # Create enabled schedule
        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Enable/Disable",
            interval_seconds=3600,
            enabled=True
        )

        # Disable it
        success = await scheduler.update_schedule(schedule_id, enabled=False)
        assert success is True

        # Enable it again
        success = await scheduler.update_schedule(schedule_id, enabled=True)
        assert success is True

    @pytest.mark.asyncio
    async def test_update_schedule_interval(self, scheduler):
        """Test updating schedule interval"""
        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Update Interval",
            interval_seconds=3600
        )

        # Update to run every 2 hours
        success = await scheduler.update_schedule(
            schedule_id,
            interval_seconds=7200
        )
        assert success is True

        # Verify next_run_at was recalculated
        next_run = await scheduler.get_next_run_time(schedule_id)
        assert next_run is not None

        expected = datetime.now(timezone.utc) + timedelta(hours=2)
        time_diff = abs((next_run - expected).total_seconds())
        assert time_diff < 5

    @pytest.mark.asyncio
    async def test_update_schedule_config(self, scheduler):
        """Test updating schedule configuration"""
        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Update Config",
            interval_seconds=3600,
            config={"initial": "value"}
        )

        # Update config
        success = await scheduler.update_schedule(
            schedule_id,
            config={"updated": "value", "new_key": 123}
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_delete_schedule(self, scheduler):
        """Test deleting a schedule"""
        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Delete",
            interval_seconds=3600
        )

        # Delete it
        success = await scheduler.delete_schedule(schedule_id)
        assert success is True

        # Verify it's gone
        next_run = await scheduler.get_next_run_time(schedule_id)
        assert next_run is None

    @pytest.mark.asyncio
    async def test_get_due_schedules_empty(self, scheduler):
        """Test getting due schedules when none are due"""
        # Create schedule far in future
        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Future Schedule",
            interval_seconds=86400  # 24 hours
        )

        due_schedules = await scheduler.get_due_schedules()

        # Should not include our future schedule
        future_schedule_ids = [s['id'] for s in due_schedules if s['id'] == schedule_id]
        assert len(future_schedule_ids) == 0

    @pytest.mark.asyncio
    async def test_scheduler_lifecycle(self, scheduler):
        """Test starting and stopping the scheduler"""
        # Start scheduler
        await scheduler.start()

        # Wait a bit
        await asyncio.sleep(0.1)

        # Stop scheduler
        await scheduler.stop()


class TestAgentRuns:
    """Test suite for Agent Runs Tracking (AC-003)"""

    @pytest.mark.asyncio
    async def test_create_run(self):
        """Test creating an agent run"""
        from services.agent_framework import get_run_manager

        run_manager = get_run_manager()

        # Create a schedule first
        scheduler = get_agent_scheduler()
        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Schedule for Runs",
            interval_seconds=3600
        )

        # Create a run
        run_id = await run_manager.create_run(
            schedule_id=schedule_id,
            agent_type="test_agent",
            config={"test": "config"},
            triggered_by="manual"
        )

        assert run_id is not None
        assert isinstance(run_id, str)

    @pytest.mark.asyncio
    async def test_run_status_progression(self):
        """Test updating run status through lifecycle"""
        from services.agent_framework import get_run_manager

        run_manager = get_run_manager()
        scheduler = get_agent_scheduler()

        # Create schedule and run
        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Status Progression",
            interval_seconds=3600
        )

        run_id = await run_manager.create_run(
            schedule_id=schedule_id,
            agent_type="test_agent"
        )

        # Start the run
        await run_manager.start_run(run_id)

        # Update progress
        await run_manager.update_progress(run_id, 50, "Halfway done")

        # Complete the run
        await run_manager.complete_run(
            run_id,
            status="success",
            result_summary="Test completed successfully"
        )

    @pytest.mark.asyncio
    async def test_run_heartbeat(self):
        """Test run heartbeat tracking"""
        from services.agent_framework import get_run_manager

        run_manager = get_run_manager()
        scheduler = get_agent_scheduler()

        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Heartbeat",
            interval_seconds=3600
        )

        run_id = await run_manager.create_run(
            schedule_id=schedule_id,
            agent_type="test_agent"
        )

        # Start run
        await run_manager.start_run(run_id)

        # Send heartbeat
        await run_manager.send_heartbeat(run_id)

        # Wait a bit and send another
        await asyncio.sleep(0.1)
        await run_manager.send_heartbeat(run_id)


class TestAgentSteps:
    """Test suite for Agent Steps Timeline (AC-004)"""

    @pytest.mark.asyncio
    async def test_create_step(self):
        """Test creating an agent step"""
        from services.agent_framework import get_run_manager

        run_manager = get_run_manager()
        scheduler = get_agent_scheduler()

        # Create schedule and run
        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Steps",
            interval_seconds=3600
        )

        run_id = await run_manager.create_run(
            schedule_id=schedule_id,
            agent_type="test_agent"
        )

        # Create a step
        step_id = await run_manager.create_step(
            run_id=run_id,
            step_number=1,
            step_name="Initialize",
            step_type="initialization",
            description="Initialize the agent"
        )

        assert step_id is not None

    @pytest.mark.asyncio
    async def test_step_progression(self):
        """Test step status progression"""
        from services.agent_framework import get_run_manager

        run_manager = get_run_manager()
        scheduler = get_agent_scheduler()

        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Step Progression",
            interval_seconds=3600
        )

        run_id = await run_manager.create_run(
            schedule_id=schedule_id,
            agent_type="test_agent"
        )

        # Create and start step
        step_id = await run_manager.create_step(
            run_id=run_id,
            step_number=1,
            step_name="Test Step",
            step_type="test"
        )

        # Start step
        await run_manager.start_step(step_id)

        # Complete step
        await run_manager.complete_step(
            step_id,
            status="success",
            summary="Step completed successfully",
            output_data={"result": "success"}
        )

    @pytest.mark.asyncio
    async def test_multiple_steps_timeline(self):
        """Test creating multiple steps in sequence"""
        from services.agent_framework import get_run_manager

        run_manager = get_run_manager()
        scheduler = get_agent_scheduler()

        schedule_id = await scheduler.create_schedule(
            agent_type="test_agent",
            schedule_name="Test Timeline",
            interval_seconds=3600
        )

        run_id = await run_manager.create_run(
            schedule_id=schedule_id,
            agent_type="test_agent"
        )

        # Create 3 steps in sequence
        steps = []
        for i in range(1, 4):
            step_id = await run_manager.create_step(
                run_id=run_id,
                step_number=i,
                step_name=f"Step {i}",
                step_type="test"
            )
            steps.append(step_id)

        assert len(steps) == 3


# Cleanup fixture to delete test schedules after tests
@pytest.fixture(scope="session", autouse=True)
async def cleanup_test_schedules():
    """Clean up test schedules after all tests"""
    yield

    # Delete all schedules created by tests
    from sqlalchemy import create_engine, text
    import os

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Delete test agent schedules and their runs
            conn.execute(text("""
                DELETE FROM agent_steps WHERE run_id IN (
                    SELECT id FROM agent_runs WHERE agent_type = 'test_agent'
                )
            """))
            conn.execute(text("DELETE FROM agent_runs WHERE agent_type = 'test_agent'"))
            conn.execute(text("DELETE FROM agent_schedules WHERE agent_type = 'test_agent'"))
            trans.commit()
        except:
            trans.rollback()
