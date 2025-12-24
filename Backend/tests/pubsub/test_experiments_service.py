"""
Experiments Service Tests
==========================
Test ExperimentsService specific behavior.

Tests:
- Control/variant tagging correct
- Sample size gating
- Winner criteria + promotion emits attribution metadata
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# EXPERIMENTS MODELS
# ============================================================================

class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VariantType(str, Enum):
    CONTROL = "control"
    TREATMENT = "treatment"


@dataclass
class Variant:
    """Experiment variant (control or treatment)."""
    id: str
    experiment_id: str
    variant_type: VariantType
    name: str
    content_id: str
    post_id: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class Hypothesis:
    """Experiment hypothesis."""
    id: str
    statement: str
    metric: str  # e.g., "engagement_rate", "view_count"
    expected_lift: float  # e.g., 0.10 for 10% lift


@dataclass 
class Experiment:
    """An A/B experiment."""
    id: str
    name: str
    hypothesis: Hypothesis
    status: ExperimentStatus = ExperimentStatus.DRAFT
    variants: List[Variant] = field(default_factory=list)
    min_sample_size: int = 100
    min_runtime_hours: int = 24
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    winner_variant_id: Optional[str] = None
    confidence_level: float = 0.0


@dataclass
class WinnerDecision:
    """Decision about experiment winner."""
    experiment_id: str
    winner_variant_id: str
    winning_metric: str
    control_value: float
    treatment_value: float
    lift: float
    confidence: float
    attribution: Dict[str, Any]


@dataclass
class ExperimentEvent:
    """Event emitted by experiments service."""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExperimentsService:
    """
    Service for managing A/B experiments.
    
    Key behaviors:
    - Correct control/variant tagging
    - Sample size gating before winner declaration
    - Winner decision with attribution metadata
    """
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        self.events: List[ExperimentEvent] = []
    
    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event."""
        self.events.append(ExperimentEvent(event_type=event_type, data=data))
    
    def create_experiment(
        self,
        name: str,
        hypothesis: Hypothesis,
        control_content_id: str,
        treatment_content_id: str,
        min_sample_size: int = 100,
        min_runtime_hours: int = 24
    ) -> Experiment:
        """Create a new experiment with control and treatment variants."""
        experiment_id = str(uuid4())
        
        # Create control variant
        control = Variant(
            id=str(uuid4()),
            experiment_id=experiment_id,
            variant_type=VariantType.CONTROL,
            name="Control",
            content_id=control_content_id,
        )
        
        # Create treatment variant
        treatment = Variant(
            id=str(uuid4()),
            experiment_id=experiment_id,
            variant_type=VariantType.TREATMENT,
            name="Treatment",
            content_id=treatment_content_id,
        )
        
        experiment = Experiment(
            id=experiment_id,
            name=name,
            hypothesis=hypothesis,
            variants=[control, treatment],
            min_sample_size=min_sample_size,
            min_runtime_hours=min_runtime_hours,
        )
        
        self.experiments[experiment_id] = experiment
        
        self._emit("experiment.created", {
            "experiment_id": experiment_id,
            "name": name,
            "hypothesis": hypothesis.statement,
            "variants": [
                {"id": control.id, "type": "control"},
                {"id": treatment.id, "type": "treatment"},
            ],
        })
        
        return experiment
    
    def get_variant(self, experiment_id: str, variant_type: VariantType) -> Optional[Variant]:
        """Get a specific variant from an experiment."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return None
        
        for variant in experiment.variants:
            if variant.variant_type == variant_type:
                return variant
        return None
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return False
        
        if experiment.status != ExperimentStatus.DRAFT:
            return False
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now(timezone.utc)
        
        self._emit("experiment.started", {
            "experiment_id": experiment_id,
            "started_at": experiment.started_at.isoformat(),
        })
        
        return True
    
    def record_metrics(
        self,
        experiment_id: str,
        variant_id: str,
        metrics: Dict[str, float]
    ) -> bool:
        """Record metrics for a variant."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return False
        
        for variant in experiment.variants:
            if variant.id == variant_id:
                variant.metrics.update(metrics)
                
                self._emit("metrics.recorded", {
                    "experiment_id": experiment_id,
                    "variant_id": variant_id,
                    "metrics": metrics,
                })
                return True
        
        return False
    
    def _check_sample_size_met(self, experiment: Experiment) -> bool:
        """Check if minimum sample size is met for all variants."""
        for variant in experiment.variants:
            sample_size = variant.metrics.get("sample_size", 0)
            if sample_size < experiment.min_sample_size:
                return False
        return True
    
    def _check_runtime_met(self, experiment: Experiment) -> bool:
        """Check if minimum runtime has passed."""
        if not experiment.started_at:
            return False
        
        runtime = datetime.now(timezone.utc) - experiment.started_at
        return runtime >= timedelta(hours=experiment.min_runtime_hours)
    
    def _calculate_winner(self, experiment: Experiment) -> Optional[WinnerDecision]:
        """Calculate experiment winner if criteria met."""
        control = self.get_variant(experiment.id, VariantType.CONTROL)
        treatment = self.get_variant(experiment.id, VariantType.TREATMENT)
        
        if not control or not treatment:
            return None
        
        metric = experiment.hypothesis.metric
        control_value = control.metrics.get(metric, 0)
        treatment_value = treatment.metrics.get(metric, 0)
        
        if control_value == 0:
            lift = 0
        else:
            lift = (treatment_value - control_value) / control_value
        
        # Simplified confidence calculation
        # In production, use proper statistical test
        control_sample = control.metrics.get("sample_size", 0)
        treatment_sample = treatment.metrics.get("sample_size", 0)
        total_sample = control_sample + treatment_sample
        
        confidence = min(0.95, total_sample / 1000)  # Simplified
        
        # Determine winner
        if lift > 0 and lift >= experiment.hypothesis.expected_lift * 0.5:
            winner_id = treatment.id
        else:
            winner_id = control.id
        
        return WinnerDecision(
            experiment_id=experiment.id,
            winner_variant_id=winner_id,
            winning_metric=metric,
            control_value=control_value,
            treatment_value=treatment_value,
            lift=lift,
            confidence=confidence,
            attribution={
                "hypothesis_id": experiment.hypothesis.id,
                "expected_lift": experiment.hypothesis.expected_lift,
                "actual_lift": lift,
                "sample_sizes": {
                    "control": control_sample,
                    "treatment": treatment_sample,
                },
                "runtime_hours": (
                    (datetime.now(timezone.utc) - experiment.started_at).total_seconds() / 3600
                    if experiment.started_at else 0
                ),
            },
        )
    
    def check_and_complete_experiment(
        self,
        experiment_id: str,
        force: bool = False
    ) -> Optional[WinnerDecision]:
        """
        Check if experiment can be completed and declare winner.
        
        Returns WinnerDecision if experiment completed, None otherwise.
        Respects sample size gating unless force=True.
        """
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return None
        
        if experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # Check gating criteria
        if not force:
            if not self._check_sample_size_met(experiment):
                self._emit("experiment.gating_failed", {
                    "experiment_id": experiment_id,
                    "reason": "sample_size",
                })
                return None
            
            if not self._check_runtime_met(experiment):
                self._emit("experiment.gating_failed", {
                    "experiment_id": experiment_id,
                    "reason": "runtime",
                })
                return None
        
        # Calculate winner
        decision = self._calculate_winner(experiment)
        if not decision:
            return None
        
        # Update experiment
        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.now(timezone.utc)
        experiment.winner_variant_id = decision.winner_variant_id
        experiment.confidence_level = decision.confidence
        
        # Emit winner event with attribution
        self._emit("experiment.winner_declared", {
            "experiment_id": experiment_id,
            "winner_variant_id": decision.winner_variant_id,
            "lift": decision.lift,
            "confidence": decision.confidence,
            "attribution": decision.attribution,
        })
        
        return decision
    
    def get_events(self, event_type: Optional[str] = None) -> List[ExperimentEvent]:
        """Get emitted events."""
        if event_type:
            return [e for e in self.events if e.event_type == event_type]
        return self.events


# ============================================================================
# TESTS
# ============================================================================

class TestVariantTagging:
    """Test control/variant tagging is correct."""
    
    @pytest.fixture
    def service(self):
        return ExperimentsService()
    
    @pytest.fixture
    def hypothesis(self):
        return Hypothesis(
            id="hyp-1",
            statement="Treatment will have higher engagement",
            metric="engagement_rate",
            expected_lift=0.10,
        )
    
    def test_control_variant_tagged_correctly(self, service, hypothesis):
        """Control variant should have CONTROL type."""
        experiment = service.create_experiment(
            name="Test Experiment",
            hypothesis=hypothesis,
            control_content_id="content-control",
            treatment_content_id="content-treatment",
        )
        
        control = service.get_variant(experiment.id, VariantType.CONTROL)
        assert control is not None
        assert control.variant_type == VariantType.CONTROL
        assert control.name == "Control"
    
    def test_treatment_variant_tagged_correctly(self, service, hypothesis):
        """Treatment variant should have TREATMENT type."""
        experiment = service.create_experiment(
            name="Test Experiment",
            hypothesis=hypothesis,
            control_content_id="content-control",
            treatment_content_id="content-treatment",
        )
        
        treatment = service.get_variant(experiment.id, VariantType.TREATMENT)
        assert treatment is not None
        assert treatment.variant_type == VariantType.TREATMENT
        assert treatment.name == "Treatment"
    
    def test_variants_have_correct_content_ids(self, service, hypothesis):
        """Variants should have correct content IDs."""
        experiment = service.create_experiment(
            name="Test Experiment",
            hypothesis=hypothesis,
            control_content_id="content-control",
            treatment_content_id="content-treatment",
        )
        
        control = service.get_variant(experiment.id, VariantType.CONTROL)
        treatment = service.get_variant(experiment.id, VariantType.TREATMENT)
        
        assert control.content_id == "content-control"
        assert treatment.content_id == "content-treatment"
    
    def test_variant_ids_are_unique(self, service, hypothesis):
        """Each variant should have unique ID."""
        experiment = service.create_experiment(
            name="Test Experiment",
            hypothesis=hypothesis,
            control_content_id="content-control",
            treatment_content_id="content-treatment",
        )
        
        variant_ids = [v.id for v in experiment.variants]
        assert len(variant_ids) == len(set(variant_ids))


class TestSampleSizeGating:
    """Test sample size gating before winner declaration."""
    
    @pytest.fixture
    def service(self):
        return ExperimentsService()
    
    @pytest.fixture
    def hypothesis(self):
        return Hypothesis(
            id="hyp-1",
            statement="Treatment better",
            metric="engagement_rate",
            expected_lift=0.10,
        )
    
    def test_cannot_complete_without_sample_size(self, service, hypothesis):
        """Cannot complete experiment without meeting sample size."""
        experiment = service.create_experiment(
            name="Test",
            hypothesis=hypothesis,
            control_content_id="c1",
            treatment_content_id="t1",
            min_sample_size=100,
            min_runtime_hours=0,  # No runtime requirement
        )
        
        service.start_experiment(experiment.id)
        
        # Record small sample
        control = service.get_variant(experiment.id, VariantType.CONTROL)
        treatment = service.get_variant(experiment.id, VariantType.TREATMENT)
        
        service.record_metrics(experiment.id, control.id, {
            "sample_size": 50,
            "engagement_rate": 0.05,
        })
        service.record_metrics(experiment.id, treatment.id, {
            "sample_size": 50,
            "engagement_rate": 0.06,
        })
        
        # Should not complete
        decision = service.check_and_complete_experiment(experiment.id)
        assert decision is None
        assert experiment.status == ExperimentStatus.RUNNING
    
    def test_can_complete_with_sample_size(self, service, hypothesis):
        """Can complete experiment when sample size met."""
        experiment = service.create_experiment(
            name="Test",
            hypothesis=hypothesis,
            control_content_id="c1",
            treatment_content_id="t1",
            min_sample_size=100,
            min_runtime_hours=0,
        )
        
        service.start_experiment(experiment.id)
        
        control = service.get_variant(experiment.id, VariantType.CONTROL)
        treatment = service.get_variant(experiment.id, VariantType.TREATMENT)
        
        service.record_metrics(experiment.id, control.id, {
            "sample_size": 150,
            "engagement_rate": 0.05,
        })
        service.record_metrics(experiment.id, treatment.id, {
            "sample_size": 150,
            "engagement_rate": 0.06,
        })
        
        decision = service.check_and_complete_experiment(experiment.id)
        assert decision is not None
        assert experiment.status == ExperimentStatus.COMPLETED
    
    def test_force_bypasses_sample_size(self, service, hypothesis):
        """Force flag should bypass sample size requirement."""
        experiment = service.create_experiment(
            name="Test",
            hypothesis=hypothesis,
            control_content_id="c1",
            treatment_content_id="t1",
            min_sample_size=1000,  # High threshold
            min_runtime_hours=0,
        )
        
        service.start_experiment(experiment.id)
        
        control = service.get_variant(experiment.id, VariantType.CONTROL)
        treatment = service.get_variant(experiment.id, VariantType.TREATMENT)
        
        service.record_metrics(experiment.id, control.id, {
            "sample_size": 10,
            "engagement_rate": 0.05,
        })
        service.record_metrics(experiment.id, treatment.id, {
            "sample_size": 10,
            "engagement_rate": 0.06,
        })
        
        # Force completion
        decision = service.check_and_complete_experiment(experiment.id, force=True)
        assert decision is not None
    
    def test_gating_failed_event_emitted(self, service, hypothesis):
        """Should emit gating_failed event when criteria not met."""
        experiment = service.create_experiment(
            name="Test",
            hypothesis=hypothesis,
            control_content_id="c1",
            treatment_content_id="t1",
            min_sample_size=100,
            min_runtime_hours=0,
        )
        
        service.start_experiment(experiment.id)
        
        # Try to complete without metrics
        service.check_and_complete_experiment(experiment.id)
        
        gating_events = service.get_events("experiment.gating_failed")
        assert len(gating_events) >= 1
        assert gating_events[0].data["reason"] == "sample_size"


class TestWinnerCriteria:
    """Test winner criteria and promotion with attribution."""
    
    @pytest.fixture
    def service(self):
        return ExperimentsService()
    
    @pytest.fixture
    def hypothesis(self):
        return Hypothesis(
            id="hyp-1",
            statement="Treatment better",
            metric="engagement_rate",
            expected_lift=0.10,
        )
    
    def test_treatment_wins_with_lift(self, service, hypothesis):
        """Treatment should win if it has positive lift."""
        experiment = service.create_experiment(
            name="Test",
            hypothesis=hypothesis,
            control_content_id="c1",
            treatment_content_id="t1",
            min_sample_size=10,
            min_runtime_hours=0,
        )
        
        service.start_experiment(experiment.id)
        
        control = service.get_variant(experiment.id, VariantType.CONTROL)
        treatment = service.get_variant(experiment.id, VariantType.TREATMENT)
        
        service.record_metrics(experiment.id, control.id, {
            "sample_size": 100,
            "engagement_rate": 0.05,
        })
        service.record_metrics(experiment.id, treatment.id, {
            "sample_size": 100,
            "engagement_rate": 0.08,  # 60% lift
        })
        
        decision = service.check_and_complete_experiment(experiment.id)
        
        assert decision.winner_variant_id == treatment.id
        assert decision.lift > 0
    
    def test_control_wins_with_no_lift(self, service, hypothesis):
        """Control should win if treatment has no improvement."""
        experiment = service.create_experiment(
            name="Test",
            hypothesis=hypothesis,
            control_content_id="c1",
            treatment_content_id="t1",
            min_sample_size=10,
            min_runtime_hours=0,
        )
        
        service.start_experiment(experiment.id)
        
        control = service.get_variant(experiment.id, VariantType.CONTROL)
        treatment = service.get_variant(experiment.id, VariantType.TREATMENT)
        
        service.record_metrics(experiment.id, control.id, {
            "sample_size": 100,
            "engagement_rate": 0.05,
        })
        service.record_metrics(experiment.id, treatment.id, {
            "sample_size": 100,
            "engagement_rate": 0.04,  # Worse than control
        })
        
        decision = service.check_and_complete_experiment(experiment.id)
        
        assert decision.winner_variant_id == control.id
    
    def test_winner_event_has_attribution(self, service, hypothesis):
        """Winner event should include attribution metadata."""
        experiment = service.create_experiment(
            name="Test",
            hypothesis=hypothesis,
            control_content_id="c1",
            treatment_content_id="t1",
            min_sample_size=10,
            min_runtime_hours=0,
        )
        
        service.start_experiment(experiment.id)
        
        control = service.get_variant(experiment.id, VariantType.CONTROL)
        treatment = service.get_variant(experiment.id, VariantType.TREATMENT)
        
        service.record_metrics(experiment.id, control.id, {
            "sample_size": 100,
            "engagement_rate": 0.05,
        })
        service.record_metrics(experiment.id, treatment.id, {
            "sample_size": 100,
            "engagement_rate": 0.06,
        })
        
        service.check_and_complete_experiment(experiment.id)
        
        winner_events = service.get_events("experiment.winner_declared")
        assert len(winner_events) == 1
        
        event = winner_events[0]
        assert "attribution" in event.data
        
        attribution = event.data["attribution"]
        assert "hypothesis_id" in attribution
        assert "expected_lift" in attribution
        assert "actual_lift" in attribution
        assert "sample_sizes" in attribution
    
    def test_attribution_includes_sample_sizes(self, service, hypothesis):
        """Attribution should include sample sizes for each variant."""
        experiment = service.create_experiment(
            name="Test",
            hypothesis=hypothesis,
            control_content_id="c1",
            treatment_content_id="t1",
            min_sample_size=10,
            min_runtime_hours=0,
        )
        
        service.start_experiment(experiment.id)
        
        control = service.get_variant(experiment.id, VariantType.CONTROL)
        treatment = service.get_variant(experiment.id, VariantType.TREATMENT)
        
        service.record_metrics(experiment.id, control.id, {
            "sample_size": 120,
            "engagement_rate": 0.05,
        })
        service.record_metrics(experiment.id, treatment.id, {
            "sample_size": 130,
            "engagement_rate": 0.06,
        })
        
        decision = service.check_and_complete_experiment(experiment.id)
        
        assert decision.attribution["sample_sizes"]["control"] == 120
        assert decision.attribution["sample_sizes"]["treatment"] == 130
    
    def test_winner_decision_includes_metric_values(self, service, hypothesis):
        """Winner decision should include actual metric values."""
        experiment = service.create_experiment(
            name="Test",
            hypothesis=hypothesis,
            control_content_id="c1",
            treatment_content_id="t1",
            min_sample_size=10,
            min_runtime_hours=0,
        )
        
        service.start_experiment(experiment.id)
        
        control = service.get_variant(experiment.id, VariantType.CONTROL)
        treatment = service.get_variant(experiment.id, VariantType.TREATMENT)
        
        service.record_metrics(experiment.id, control.id, {
            "sample_size": 100,
            "engagement_rate": 0.05,
        })
        service.record_metrics(experiment.id, treatment.id, {
            "sample_size": 100,
            "engagement_rate": 0.07,
        })
        
        decision = service.check_and_complete_experiment(experiment.id)
        
        assert decision.winning_metric == "engagement_rate"
        assert decision.control_value == 0.05
        assert decision.treatment_value == 0.07
        assert abs(decision.lift - 0.4) < 0.01  # 40% lift
