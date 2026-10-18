"""
Unit Tests: Step Machine Transitions
=====================================
Test workflow step state transitions without any broker/DB.

These tests verify:
- Valid state transitions (queued → running → succeeded/failed)
- Invalid transitions are rejected
- Step duration calculations
- Progress tracking
"""

import pytest
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class StepStatus(str, Enum):
    """Valid step statuses."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class RunStatus(str, Enum):
    """Valid run statuses."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Valid transitions map
VALID_STEP_TRANSITIONS = {
    StepStatus.PENDING: [StepStatus.QUEUED, StepStatus.CANCELLED],
    StepStatus.QUEUED: [StepStatus.RUNNING, StepStatus.CANCELLED],
    StepStatus.RUNNING: [StepStatus.SUCCEEDED, StepStatus.FAILED, StepStatus.RETRYING],
    StepStatus.RETRYING: [StepStatus.RUNNING, StepStatus.FAILED, StepStatus.CANCELLED],
    StepStatus.SUCCEEDED: [],  # Terminal
    StepStatus.FAILED: [StepStatus.RETRYING],  # Can retry
    StepStatus.CANCELLED: [],  # Terminal
}

VALID_RUN_TRANSITIONS = {
    RunStatus.QUEUED: [RunStatus.RUNNING, RunStatus.CANCELLED],
    RunStatus.RUNNING: [RunStatus.SUCCEEDED, RunStatus.FAILED],
    RunStatus.SUCCEEDED: [],  # Terminal
    RunStatus.FAILED: [],  # Terminal
    RunStatus.CANCELLED: [],  # Terminal
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


@dataclass
class Step:
    """Represents a workflow step."""
    key: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempt: int = 0
    max_attempts: int = 3
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    def transition_to(self, new_status: StepStatus) -> None:
        """Transition to a new status, validating the transition."""
        valid_targets = VALID_STEP_TRANSITIONS.get(self.status, [])
        if new_status not in valid_targets:
            raise InvalidTransitionError(
                f"Cannot transition from {self.status} to {new_status}. "
                f"Valid transitions: {valid_targets}"
            )
        
        old_status = self.status
        self.status = new_status
        
        # Update timestamps
        if new_status == StepStatus.RUNNING:
            self.started_at = datetime.now(timezone.utc)
            self.attempt += 1
        elif new_status in (StepStatus.SUCCEEDED, StepStatus.FAILED, StepStatus.CANCELLED):
            self.completed_at = datetime.now(timezone.utc)
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate step duration in milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None
    
    @property
    def is_terminal(self) -> bool:
        """Check if step is in a terminal state."""
        return self.status in (StepStatus.SUCCEEDED, StepStatus.FAILED, StepStatus.CANCELLED)
    
    @property
    def can_retry(self) -> bool:
        """Check if step can be retried."""
        return (
            self.status == StepStatus.FAILED and 
            self.attempt < self.max_attempts
        )


@dataclass
class Run:
    """Represents a workflow run containing multiple steps."""
    id: str
    workflow_type: str
    status: RunStatus = RunStatus.QUEUED
    steps: List[Step] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def transition_to(self, new_status: RunStatus) -> None:
        """Transition run to a new status."""
        valid_targets = VALID_RUN_TRANSITIONS.get(self.status, [])
        if new_status not in valid_targets:
            raise InvalidTransitionError(
                f"Run cannot transition from {self.status} to {new_status}"
            )
        
        self.status = new_status
        
        if new_status == RunStatus.RUNNING:
            self.started_at = datetime.now(timezone.utc)
        elif new_status in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED):
            self.completed_at = datetime.now(timezone.utc)
    
    @property
    def progress_percent(self) -> int:
        """Calculate run progress as percentage."""
        if not self.steps:
            return 0
        completed = sum(1 for s in self.steps if s.is_terminal)
        return int((completed / len(self.steps)) * 100)
    
    @property
    def current_step(self) -> Optional[Step]:
        """Get the currently running step."""
        for step in self.steps:
            if step.status == StepStatus.RUNNING:
                return step
        return None


class TestStepTransitions:
    """Test step state machine transitions."""
    
    def test_pending_to_queued(self):
        """Step can transition from pending to queued."""
        step = Step(key="analysis")
        step.transition_to(StepStatus.QUEUED)
        assert step.status == StepStatus.QUEUED
    
    def test_queued_to_running(self):
        """Step can transition from queued to running."""
        step = Step(key="analysis", status=StepStatus.QUEUED)
        step.transition_to(StepStatus.RUNNING)
        assert step.status == StepStatus.RUNNING
        assert step.started_at is not None
        assert step.attempt == 1
    
    def test_running_to_succeeded(self):
        """Step can transition from running to succeeded."""
        step = Step(key="analysis", status=StepStatus.RUNNING)
        step.started_at = datetime.now(timezone.utc)
        step.transition_to(StepStatus.SUCCEEDED)
        assert step.status == StepStatus.SUCCEEDED
        assert step.completed_at is not None
        assert step.is_terminal is True
    
    def test_running_to_failed(self):
        """Step can transition from running to failed."""
        step = Step(key="analysis", status=StepStatus.RUNNING)
        step.started_at = datetime.now(timezone.utc)
        step.transition_to(StepStatus.FAILED)
        assert step.status == StepStatus.FAILED
        assert step.is_terminal is True
    
    def test_failed_to_retrying(self):
        """Failed step can transition to retrying."""
        step = Step(key="analysis", status=StepStatus.FAILED, attempt=1)
        step.transition_to(StepStatus.RETRYING)
        assert step.status == StepStatus.RETRYING
    
    def test_retrying_to_running(self):
        """Retrying step can transition back to running."""
        step = Step(key="analysis", status=StepStatus.RETRYING, attempt=1)
        step.transition_to(StepStatus.RUNNING)
        assert step.status == StepStatus.RUNNING
        assert step.attempt == 2
    
    def test_invalid_transition_pending_to_succeeded(self):
        """Cannot skip directly to succeeded from pending."""
        step = Step(key="analysis")
        with pytest.raises(InvalidTransitionError):
            step.transition_to(StepStatus.SUCCEEDED)
    
    def test_invalid_transition_succeeded_to_running(self):
        """Cannot transition from terminal state."""
        step = Step(key="analysis", status=StepStatus.SUCCEEDED)
        with pytest.raises(InvalidTransitionError):
            step.transition_to(StepStatus.RUNNING)
    
    def test_invalid_transition_queued_to_failed(self):
        """Cannot fail without running first."""
        step = Step(key="analysis", status=StepStatus.QUEUED)
        with pytest.raises(InvalidTransitionError):
            step.transition_to(StepStatus.FAILED)


class TestStepDuration:
    """Test step duration calculations."""
    
    def test_duration_calculation(self):
        """Duration should be calculated correctly."""
        step = Step(key="analysis")
        step.started_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        step.completed_at = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
        
        assert step.duration_ms == 5000.0
    
    def test_duration_none_when_not_started(self):
        """Duration should be None if not started."""
        step = Step(key="analysis")
        assert step.duration_ms is None
    
    def test_duration_none_when_running(self):
        """Duration should be None while running."""
        step = Step(key="analysis", status=StepStatus.RUNNING)
        step.started_at = datetime.now(timezone.utc)
        assert step.duration_ms is None


class TestStepRetry:
    """Test step retry logic."""
    
    def test_can_retry_when_failed_under_max(self):
        """Step can retry when under max attempts."""
        step = Step(key="analysis", status=StepStatus.FAILED, attempt=1, max_attempts=3)
        assert step.can_retry is True
    
    def test_cannot_retry_when_at_max(self):
        """Step cannot retry when at max attempts."""
        step = Step(key="analysis", status=StepStatus.FAILED, attempt=3, max_attempts=3)
        assert step.can_retry is False
    
    def test_cannot_retry_when_succeeded(self):
        """Succeeded step cannot retry."""
        step = Step(key="analysis", status=StepStatus.SUCCEEDED, attempt=1)
        assert step.can_retry is False
    
    def test_attempt_increments_on_run(self):
        """Attempt count should increment each time step runs."""
        step = Step(key="analysis", status=StepStatus.QUEUED)
        
        step.transition_to(StepStatus.RUNNING)
        assert step.attempt == 1
        
        step.transition_to(StepStatus.FAILED)
        step.transition_to(StepStatus.RETRYING)
        step.transition_to(StepStatus.RUNNING)
        assert step.attempt == 2


class TestRunTransitions:
    """Test run state machine transitions."""
    
    def test_queued_to_running(self):
        """Run can transition from queued to running."""
        run = Run(id="run-1", workflow_type="analysis")
        run.transition_to(RunStatus.RUNNING)
        assert run.status == RunStatus.RUNNING
        assert run.started_at is not None
    
    def test_running_to_succeeded(self):
        """Run can transition from running to succeeded."""
        run = Run(id="run-1", workflow_type="analysis", status=RunStatus.RUNNING)
        run.transition_to(RunStatus.SUCCEEDED)
        assert run.status == RunStatus.SUCCEEDED
        assert run.completed_at is not None
    
    def test_running_to_failed(self):
        """Run can transition from running to failed."""
        run = Run(id="run-1", workflow_type="analysis", status=RunStatus.RUNNING)
        run.transition_to(RunStatus.FAILED)
        assert run.status == RunStatus.FAILED
    
    def test_queued_to_cancelled(self):
        """Run can be cancelled before starting."""
        run = Run(id="run-1", workflow_type="analysis")
        run.transition_to(RunStatus.CANCELLED)
        assert run.status == RunStatus.CANCELLED


class TestRunProgress:
    """Test run progress tracking."""
    
    def test_progress_zero_with_no_steps(self):
        """Progress is 0 with no steps."""
        run = Run(id="run-1", workflow_type="analysis")
        assert run.progress_percent == 0
    
    def test_progress_calculation(self):
        """Progress should reflect completed steps."""
        run = Run(
            id="run-1",
            workflow_type="analysis",
            steps=[
                Step(key="step1", status=StepStatus.SUCCEEDED),
                Step(key="step2", status=StepStatus.RUNNING),
                Step(key="step3", status=StepStatus.PENDING),
                Step(key="step4", status=StepStatus.PENDING),
            ]
        )
        assert run.progress_percent == 25  # 1 of 4 complete
    
    def test_progress_100_when_all_complete(self):
        """Progress is 100 when all steps complete."""
        run = Run(
            id="run-1",
            workflow_type="analysis",
            steps=[
                Step(key="step1", status=StepStatus.SUCCEEDED),
                Step(key="step2", status=StepStatus.SUCCEEDED),
            ]
        )
        assert run.progress_percent == 100
    
    def test_current_step_returns_running(self):
        """Current step should return the running step."""
        run = Run(
            id="run-1",
            workflow_type="analysis",
            steps=[
                Step(key="step1", status=StepStatus.SUCCEEDED),
                Step(key="step2", status=StepStatus.RUNNING),
                Step(key="step3", status=StepStatus.PENDING),
            ]
        )
        assert run.current_step.key == "step2"
    
    def test_current_step_none_when_no_running(self):
        """Current step is None when no step is running."""
        run = Run(
            id="run-1",
            workflow_type="analysis",
            steps=[
                Step(key="step1", status=StepStatus.SUCCEEDED),
                Step(key="step2", status=StepStatus.PENDING),
            ]
        )
        assert run.current_step is None
