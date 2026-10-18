"""
Scheduler Service Tests
========================
Test SchedulerService specific behavior.

Tests:
- Due schedule selection correctness
- No duplicate runs for same schedule window
- next_run_at update correctness
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# SCHEDULER MODELS
# ============================================================================

class ScheduleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class Schedule:
    """A recurring schedule definition."""
    id: str
    workflow_type: str
    cron_expression: str  # e.g., "0 9 * * 1" (9am every Monday)
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_run_id: Optional[str] = None
    timezone: str = "UTC"
    
    def is_due(self, current_time: datetime) -> bool:
        """Check if schedule is due for execution."""
        if self.status != ScheduleStatus.ACTIVE:
            return False
        if self.next_run_at is None:
            return False
        return current_time >= self.next_run_at


@dataclass
class ScheduleRun:
    """A single execution of a schedule."""
    id: str
    schedule_id: str
    workflow_type: str
    status: RunStatus = RunStatus.QUEUED
    scheduled_for: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class SchedulerService:
    """
    Service that processes due schedules and creates runs.
    
    Key invariants:
    - No duplicate runs for the same schedule window
    - next_run_at always updated after run creation
    - Only active schedules processed
    """
    
    def __init__(self):
        self.schedules: Dict[str, Schedule] = {}
        self.runs: Dict[str, ScheduleRun] = {}
        self._lock = asyncio.Lock()
        self._processed_windows: set = set()  # Tracks (schedule_id, window_key)
    
    def add_schedule(self, schedule: Schedule) -> None:
        """Add a schedule to the service."""
        self.schedules[schedule.id] = schedule
    
    def _get_window_key(self, schedule_id: str, run_time: datetime) -> str:
        """Generate unique key for a schedule window to prevent duplicates."""
        # Round to minute for window key
        window = run_time.replace(second=0, microsecond=0)
        return f"{schedule_id}:{window.isoformat()}"
    
    async def tick(self, current_time: Optional[datetime] = None) -> List[ScheduleRun]:
        """
        Process due schedules and create runs.
        Called by cron every minute.
        
        Returns list of newly created runs.
        """
        current_time = current_time or datetime.now(timezone.utc)
        created_runs = []
        
        async with self._lock:
            for schedule in self.schedules.values():
                if not schedule.is_due(current_time):
                    continue
                
                # Check for duplicate window
                window_key = self._get_window_key(schedule.id, schedule.next_run_at)
                if window_key in self._processed_windows:
                    continue
                
                # Create run
                run = ScheduleRun(
                    id=str(uuid4()),
                    schedule_id=schedule.id,
                    workflow_type=schedule.workflow_type,
                    scheduled_for=schedule.next_run_at,
                )
                
                self.runs[run.id] = run
                created_runs.append(run)
                
                # Mark window as processed
                self._processed_windows.add(window_key)
                
                # Update schedule
                schedule.last_run_at = current_time
                schedule.last_run_id = run.id
                schedule.next_run_at = self._calculate_next_run(schedule, current_time)
        
        return created_runs
    
    def _calculate_next_run(self, schedule: Schedule, after: datetime) -> datetime:
        """Calculate next run time based on cron expression."""
        # Simplified: just add 1 week for weekly schedules
        # In production, use croniter or similar
        return after + timedelta(weeks=1)
    
    def get_due_schedules(self, current_time: Optional[datetime] = None) -> List[Schedule]:
        """Get all schedules that are due."""
        current_time = current_time or datetime.now(timezone.utc)
        return [s for s in self.schedules.values() if s.is_due(current_time)]
    
    def get_runs_for_schedule(self, schedule_id: str) -> List[ScheduleRun]:
        """Get all runs for a schedule."""
        return [r for r in self.runs.values() if r.schedule_id == schedule_id]


# ============================================================================
# TESTS
# ============================================================================

class TestScheduleDueSelection:
    """Test due schedule selection correctness."""
    
    @pytest.fixture
    def scheduler(self):
        return SchedulerService()
    
    @pytest.fixture
    def now(self):
        return datetime.now(timezone.utc)
    
    def test_active_schedule_with_past_next_run_is_due(self, scheduler, now):
        """Active schedule with next_run_at in past is due."""
        schedule = Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=now - timedelta(hours=1),
        )
        scheduler.add_schedule(schedule)
        
        due = scheduler.get_due_schedules(now)
        assert len(due) == 1
        assert due[0].id == "sched-1"
    
    def test_active_schedule_with_future_next_run_not_due(self, scheduler, now):
        """Active schedule with next_run_at in future is not due."""
        schedule = Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=now + timedelta(hours=1),
        )
        scheduler.add_schedule(schedule)
        
        due = scheduler.get_due_schedules(now)
        assert len(due) == 0
    
    def test_paused_schedule_not_due(self, scheduler, now):
        """Paused schedule is never due."""
        schedule = Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.PAUSED,
            next_run_at=now - timedelta(hours=1),
        )
        scheduler.add_schedule(schedule)
        
        due = scheduler.get_due_schedules(now)
        assert len(due) == 0
    
    def test_schedule_without_next_run_not_due(self, scheduler, now):
        """Schedule without next_run_at is not due."""
        schedule = Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=None,
        )
        scheduler.add_schedule(schedule)
        
        due = scheduler.get_due_schedules(now)
        assert len(due) == 0
    
    def test_multiple_due_schedules(self, scheduler, now):
        """Multiple schedules can be due at once."""
        for i in range(3):
            scheduler.add_schedule(Schedule(
                id=f"sched-{i}",
                workflow_type="narrative_weekly",
                cron_expression="0 9 * * 1",
                status=ScheduleStatus.ACTIVE,
                next_run_at=now - timedelta(minutes=i),
            ))
        
        due = scheduler.get_due_schedules(now)
        assert len(due) == 3


class TestNoDuplicateRuns:
    """Test that no duplicate runs are created for same schedule window."""
    
    @pytest.fixture
    def scheduler(self):
        return SchedulerService()
    
    @pytest.fixture
    def now(self):
        return datetime.now(timezone.utc)
    
    @pytest.mark.asyncio
    async def test_single_tick_creates_one_run(self, scheduler, now):
        """Single tick should create exactly one run."""
        scheduler.add_schedule(Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=now - timedelta(minutes=5),
        ))
        
        runs = await scheduler.tick(now)
        assert len(runs) == 1
    
    @pytest.mark.asyncio
    async def test_multiple_ticks_same_window_creates_one_run(self, scheduler, now):
        """Multiple ticks in same window should only create one run."""
        scheduler.add_schedule(Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=now - timedelta(minutes=5),
        ))
        
        # First tick creates run
        runs1 = await scheduler.tick(now)
        assert len(runs1) == 1
        
        # Second tick in same minute creates nothing
        runs2 = await scheduler.tick(now + timedelta(seconds=30))
        assert len(runs2) == 0
        
        # Total runs for schedule is 1
        all_runs = scheduler.get_runs_for_schedule("sched-1")
        assert len(all_runs) == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_ticks_create_one_run(self, scheduler, now):
        """Concurrent ticks should only create one run (race condition safe)."""
        scheduler.add_schedule(Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=now - timedelta(minutes=5),
        ))
        
        # Simulate concurrent ticks
        results = await asyncio.gather(*[
            scheduler.tick(now) for _ in range(10)
        ])
        
        # Only one should have created a run
        created = [r for runs in results for r in runs]
        assert len(created) == 1
        
        # Verify only one run exists
        all_runs = scheduler.get_runs_for_schedule("sched-1")
        assert len(all_runs) == 1
    
    @pytest.mark.asyncio
    async def test_different_windows_create_separate_runs(self, scheduler, now):
        """Different schedule windows should create separate runs."""
        schedule = Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=now - timedelta(minutes=5),
        )
        scheduler.add_schedule(schedule)
        
        # First tick
        runs1 = await scheduler.tick(now)
        assert len(runs1) == 1
        
        # Manually set next_run for next week
        schedule.next_run_at = now + timedelta(weeks=1) - timedelta(minutes=1)
        
        # Second tick (next week's window)
        runs2 = await scheduler.tick(now + timedelta(weeks=1))
        assert len(runs2) == 1
        
        # Total should be 2 runs
        all_runs = scheduler.get_runs_for_schedule("sched-1")
        assert len(all_runs) == 2


class TestNextRunAtUpdate:
    """Test next_run_at is correctly updated after run creation."""
    
    @pytest.fixture
    def scheduler(self):
        return SchedulerService()
    
    @pytest.fixture
    def now(self):
        return datetime.now(timezone.utc)
    
    @pytest.mark.asyncio
    async def test_next_run_at_updated_after_tick(self, scheduler, now):
        """next_run_at should be updated after tick."""
        original_next_run = now - timedelta(minutes=5)
        
        scheduler.add_schedule(Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=original_next_run,
        ))
        
        await scheduler.tick(now)
        
        schedule = scheduler.schedules["sched-1"]
        assert schedule.next_run_at != original_next_run
        assert schedule.next_run_at > now
    
    @pytest.mark.asyncio
    async def test_last_run_at_updated(self, scheduler, now):
        """last_run_at should be updated after tick."""
        scheduler.add_schedule(Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=now - timedelta(minutes=5),
        ))
        
        assert scheduler.schedules["sched-1"].last_run_at is None
        
        await scheduler.tick(now)
        
        schedule = scheduler.schedules["sched-1"]
        assert schedule.last_run_at is not None
        assert schedule.last_run_at == now
    
    @pytest.mark.asyncio
    async def test_last_run_id_updated(self, scheduler, now):
        """last_run_id should reference the created run."""
        scheduler.add_schedule(Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=now - timedelta(minutes=5),
        ))
        
        runs = await scheduler.tick(now)
        
        schedule = scheduler.schedules["sched-1"]
        assert schedule.last_run_id == runs[0].id


class TestSchedulerEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def scheduler(self):
        return SchedulerService()
    
    @pytest.fixture
    def now(self):
        return datetime.now(timezone.utc)
    
    @pytest.mark.asyncio
    async def test_empty_schedules_returns_empty(self, scheduler, now):
        """Tick with no schedules returns empty list."""
        runs = await scheduler.tick(now)
        assert runs == []
    
    @pytest.mark.asyncio
    async def test_all_schedules_not_due_returns_empty(self, scheduler, now):
        """Tick with no due schedules returns empty list."""
        scheduler.add_schedule(Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=now + timedelta(hours=1),
        ))
        
        runs = await scheduler.tick(now)
        assert runs == []
    
    def test_schedule_is_due_exact_time(self, scheduler, now):
        """Schedule is due at exact next_run_at time."""
        schedule = Schedule(
            id="sched-1",
            workflow_type="narrative_weekly",
            cron_expression="0 9 * * 1",
            status=ScheduleStatus.ACTIVE,
            next_run_at=now,
        )
        
        assert schedule.is_due(now) is True
