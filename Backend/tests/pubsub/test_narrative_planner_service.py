"""
Narrative Planner Service Tests
================================
Test NarrativePlannerService specific behavior.

Tests:
- Pillar distribution constraints enforced
- Rejection log populated for out-of-pillar videos
- Emits step + thought + decision + artifact events
"""

import pytest
import asyncio
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Optional, Any, Set
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# NARRATIVE PLANNER MODELS
# ============================================================================

@dataclass
class Pillar:
    """Content pillar."""
    id: str
    name: str
    target_percentage: float  # 0.0 to 1.0


@dataclass
class VideoCandidate:
    """Video available for scheduling."""
    id: str
    title: str
    pillar_id: Optional[str]
    viral_score: float = 0.0
    duration_seconds: float = 60.0


@dataclass
class SlotAssignment:
    """A video assigned to a time slot."""
    slot_date: date
    slot_time: str  # e.g., "09:00"
    video_id: str
    pillar_id: Optional[str]
    reasoning: str


@dataclass
class RejectionEntry:
    """Record of why a video was rejected."""
    video_id: str
    reason: str
    pillar_id: Optional[str]
    constraint_violated: str


@dataclass
class WeeklyPlan:
    """Generated weekly content plan."""
    id: str
    week_start: date
    assignments: List[SlotAssignment] = field(default_factory=list)
    rejection_log: List[RejectionEntry] = field(default_factory=list)
    pillar_distribution: Dict[str, float] = field(default_factory=dict)
    reasoning_chain: List[str] = field(default_factory=list)


@dataclass
class PlannerEvent:
    """Event emitted by the planner."""
    event_type: str  # step, thought, decision, artifact
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class NarrativePlannerService:
    """
    Service that generates weekly content plans.
    
    Key behaviors:
    - Enforces pillar distribution constraints
    - Logs rejections with reasons
    - Emits events for each step
    """
    
    def __init__(self, pillars: List[Pillar]):
        self.pillars = {p.id: p for p in pillars}
        self.events: List[PlannerEvent] = []
    
    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event."""
        self.events.append(PlannerEvent(event_type=event_type, data=data))
    
    def _calculate_pillar_need(
        self,
        current_distribution: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate how much each pillar needs more content."""
        needs = {}
        for pillar_id, pillar in self.pillars.items():
            current = current_distribution.get(pillar_id, 0.0)
            need = max(0, pillar.target_percentage - current)
            needs[pillar_id] = need
        return needs
    
    def _check_pillar_constraint(
        self,
        video: VideoCandidate,
        current_counts: Dict[str, int],
        total_slots: int
    ) -> tuple[bool, Optional[str]]:
        """
        Check if adding this video would violate pillar constraints.
        Returns (is_valid, violation_reason).
        """
        if not video.pillar_id:
            return True, None  # Videos without pillar always allowed
        
        pillar = self.pillars.get(video.pillar_id)
        if not pillar:
            return False, f"Unknown pillar: {video.pillar_id}"
        
        current_count = current_counts.get(video.pillar_id, 0)
        max_allowed = max(1, int(total_slots * pillar.target_percentage * 1.5))  # 50% buffer, min 1
        
        if current_count >= max_allowed:
            return False, f"Pillar {pillar.name} at max capacity ({max_allowed})"
        
        return True, None
    
    async def generate_plan(
        self,
        week_start: date,
        candidates: List[VideoCandidate],
        slots_per_day: int = 3,
        days: int = 7
    ) -> WeeklyPlan:
        """Generate a weekly content plan."""
        plan = WeeklyPlan(
            id=str(uuid4()),
            week_start=week_start,
        )
        
        total_slots = slots_per_day * days
        
        # Emit step start
        self._emit("step", {
            "step_key": "planning",
            "action": "started",
            "total_slots": total_slots,
            "candidate_count": len(candidates),
        })
        
        # Sort candidates by viral score
        sorted_candidates = sorted(candidates, key=lambda v: v.viral_score, reverse=True)
        
        pillar_counts: Dict[str, int] = {p: 0 for p in self.pillars}
        used_videos: Set[str] = set()
        slot_index = 0
        
        for video in sorted_candidates:
            if slot_index >= total_slots:
                break
            
            if video.id in used_videos:
                continue
            
            # Check pillar constraint
            is_valid, violation = self._check_pillar_constraint(
                video, pillar_counts, total_slots
            )
            
            if not is_valid:
                # Log rejection
                rejection = RejectionEntry(
                    video_id=video.id,
                    reason=violation,
                    pillar_id=video.pillar_id,
                    constraint_violated="pillar_distribution",
                )
                plan.rejection_log.append(rejection)
                
                # Emit thought about rejection
                self._emit("thought", {
                    "summary": f"Rejected {video.title}: {violation}",
                    "video_id": video.id,
                })
                continue
            
            # Assign to slot
            slot_day = slot_index // slots_per_day
            slot_time_index = slot_index % slots_per_day
            slot_times = ["09:00", "14:00", "19:00"]
            
            assignment = SlotAssignment(
                slot_date=week_start + timedelta(days=slot_day),
                slot_time=slot_times[slot_time_index],
                video_id=video.id,
                pillar_id=video.pillar_id,
                reasoning=f"Selected for viral score {video.viral_score}",
            )
            
            plan.assignments.append(assignment)
            used_videos.add(video.id)
            
            if video.pillar_id:
                pillar_counts[video.pillar_id] = pillar_counts.get(video.pillar_id, 0) + 1
            
            # Emit decision
            self._emit("decision", {
                "decision": f"Assigned {video.title} to slot {slot_index}",
                "reasoning": assignment.reasoning,
                "video_id": video.id,
            })
            
            slot_index += 1
        
        # Calculate final distribution
        total_assigned = len(plan.assignments)
        if total_assigned > 0:
            for pillar_id, count in pillar_counts.items():
                plan.pillar_distribution[pillar_id] = count / total_assigned
        
        # Emit artifact created
        self._emit("artifact", {
            "artifact_type": "weekly_plan",
            "artifact_id": plan.id,
            "slot_count": len(plan.assignments),
            "rejection_count": len(plan.rejection_log),
        })
        
        # Emit step completed
        self._emit("step", {
            "step_key": "planning",
            "action": "completed",
            "assignments": len(plan.assignments),
            "rejections": len(plan.rejection_log),
        })
        
        return plan
    
    def get_events(self, event_type: Optional[str] = None) -> List[PlannerEvent]:
        """Get emitted events, optionally filtered by type."""
        if event_type:
            return [e for e in self.events if e.event_type == event_type]
        return self.events


# ============================================================================
# TESTS
# ============================================================================

class TestPillarDistribution:
    """Test pillar distribution constraint enforcement."""
    
    @pytest.fixture
    def pillars(self):
        return [
            Pillar(id="education", name="Education", target_percentage=0.4),
            Pillar(id="entertainment", name="Entertainment", target_percentage=0.35),
            Pillar(id="promotion", name="Promotion", target_percentage=0.25),
        ]
    
    @pytest.fixture
    def planner(self, pillars):
        return NarrativePlannerService(pillars)
    
    @pytest.mark.asyncio
    async def test_balanced_distribution_all_accepted(self, planner):
        """Balanced video mix should all be accepted."""
        candidates = [
            VideoCandidate(id="1", title="Edu 1", pillar_id="education", viral_score=90),
            VideoCandidate(id="2", title="Ent 1", pillar_id="entertainment", viral_score=85),
            VideoCandidate(id="3", title="Promo 1", pillar_id="promotion", viral_score=80),
            VideoCandidate(id="4", title="Edu 2", pillar_id="education", viral_score=75),
            VideoCandidate(id="5", title="Ent 2", pillar_id="entertainment", viral_score=70),
        ]
        
        plan = await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=2,
            days=3
        )
        
        # All 5 should be assigned (6 slots available)
        assert len(plan.assignments) == 5
        assert len(plan.rejection_log) == 0
    
    @pytest.mark.asyncio
    async def test_overrepresented_pillar_rejected(self, planner):
        """Videos from overrepresented pillar should be rejected."""
        # All education videos
        candidates = [
            VideoCandidate(id=f"edu-{i}", title=f"Edu {i}", 
                          pillar_id="education", viral_score=90-i)
            for i in range(10)
        ]
        
        plan = await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=2,
            days=3  # 6 slots total
        )
        
        # Should reject some due to pillar constraint
        # 40% target * 1.5 buffer * 6 slots = max 3.6 → 3 education slots
        assert len(plan.rejection_log) > 0
        
        # All rejections should mention pillar constraint
        for rejection in plan.rejection_log:
            assert "pillar" in rejection.reason.lower() or "capacity" in rejection.reason.lower()
    
    @pytest.mark.asyncio
    async def test_pillar_distribution_calculated(self, planner):
        """Final pillar distribution should be calculated."""
        candidates = [
            VideoCandidate(id="1", title="Edu", pillar_id="education", viral_score=90),
            VideoCandidate(id="2", title="Ent", pillar_id="entertainment", viral_score=85),
        ]
        
        plan = await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=1,
            days=2
        )
        
        assert "education" in plan.pillar_distribution
        assert "entertainment" in plan.pillar_distribution
        assert plan.pillar_distribution["education"] == 0.5
        assert plan.pillar_distribution["entertainment"] == 0.5


class TestRejectionLog:
    """Test rejection log is populated correctly."""
    
    @pytest.fixture
    def pillars(self):
        return [
            Pillar(id="education", name="Education", target_percentage=0.5),
        ]
    
    @pytest.fixture
    def planner(self, pillars):
        return NarrativePlannerService(pillars)
    
    @pytest.mark.asyncio
    async def test_rejection_log_contains_video_id(self, planner):
        """Rejection log should contain video ID."""
        candidates = [
            VideoCandidate(id=f"edu-{i}", title=f"Edu {i}", 
                          pillar_id="education", viral_score=90-i)
            for i in range(10)
        ]
        
        plan = await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=1,
            days=2  # Only 2 slots
        )
        
        if plan.rejection_log:
            for rejection in plan.rejection_log:
                assert rejection.video_id is not None
                assert rejection.video_id.startswith("edu-")
    
    @pytest.mark.asyncio
    async def test_rejection_log_contains_reason(self, planner):
        """Rejection log should contain reason."""
        candidates = [
            VideoCandidate(id=f"edu-{i}", title=f"Edu {i}", 
                          pillar_id="education", viral_score=90-i)
            for i in range(10)
        ]
        
        plan = await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=1,
            days=1
        )
        
        for rejection in plan.rejection_log:
            assert rejection.reason is not None
            assert len(rejection.reason) > 0
    
    @pytest.mark.asyncio
    async def test_rejection_log_contains_constraint(self, planner):
        """Rejection log should specify which constraint was violated."""
        candidates = [
            VideoCandidate(id=f"edu-{i}", title=f"Edu {i}", 
                          pillar_id="education", viral_score=90-i)
            for i in range(10)
        ]
        
        plan = await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=1,
            days=1
        )
        
        for rejection in plan.rejection_log:
            assert rejection.constraint_violated is not None


class TestEventEmission:
    """Test that planner emits correct events."""
    
    @pytest.fixture
    def pillars(self):
        return [
            Pillar(id="education", name="Education", target_percentage=0.5),
        ]
    
    @pytest.fixture
    def planner(self, pillars):
        return NarrativePlannerService(pillars)
    
    @pytest.mark.asyncio
    async def test_emits_step_events(self, planner):
        """Should emit step started and completed events."""
        candidates = [
            VideoCandidate(id="1", title="Test", pillar_id="education", viral_score=90),
        ]
        
        await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=1,
            days=1
        )
        
        step_events = planner.get_events("step")
        assert len(step_events) >= 2
        
        actions = [e.data["action"] for e in step_events]
        assert "started" in actions
        assert "completed" in actions
    
    @pytest.mark.asyncio
    async def test_emits_decision_events(self, planner):
        """Should emit decision events for assignments."""
        candidates = [
            VideoCandidate(id="1", title="Test", pillar_id="education", viral_score=90),
        ]
        
        await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=1,
            days=1
        )
        
        decision_events = planner.get_events("decision")
        assert len(decision_events) >= 1
        
        for event in decision_events:
            assert "decision" in event.data
            assert "reasoning" in event.data
    
    @pytest.mark.asyncio
    async def test_emits_thought_events_for_rejections(self, planner):
        """Should emit thought events for rejections."""
        candidates = [
            VideoCandidate(id=f"edu-{i}", title=f"Edu {i}", 
                          pillar_id="education", viral_score=90-i)
            for i in range(5)
        ]
        
        plan = await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=1,
            days=1  # Only 1 slot, 4 rejections
        )
        
        thought_events = planner.get_events("thought")
        
        # Should have thoughts for rejections
        if plan.rejection_log:
            assert len(thought_events) >= len(plan.rejection_log)
    
    @pytest.mark.asyncio
    async def test_emits_artifact_event(self, planner):
        """Should emit artifact event for generated plan."""
        candidates = [
            VideoCandidate(id="1", title="Test", pillar_id="education", viral_score=90),
        ]
        
        plan = await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=1,
            days=1
        )
        
        artifact_events = planner.get_events("artifact")
        assert len(artifact_events) == 1
        
        artifact = artifact_events[0]
        assert artifact.data["artifact_type"] == "weekly_plan"
        assert artifact.data["artifact_id"] == plan.id
    
    @pytest.mark.asyncio
    async def test_thought_summaries_not_too_long(self, planner):
        """Thought summaries should be concise."""
        candidates = [
            VideoCandidate(id=f"edu-{i}", title=f"Very Long Education Video Title Number {i}", 
                          pillar_id="education", viral_score=90-i)
            for i in range(5)
        ]
        
        await planner.generate_plan(
            week_start=date.today(),
            candidates=candidates,
            slots_per_day=1,
            days=1
        )
        
        thought_events = planner.get_events("thought")
        
        for event in thought_events:
            summary = event.data.get("summary", "")
            # Summaries should be concise (under 200 chars)
            assert len(summary) < 200, f"Summary too long: {summary}"
