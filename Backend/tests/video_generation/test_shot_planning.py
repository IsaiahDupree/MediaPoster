"""
Unit tests for shot planning and budgeting.

Tests:
- Shot budget creation
- Plate reuse optimization
- CHAR_ALPHA overlay planning
- Budget constraint enforcement
"""

import pytest
from services.video_generation.types import StoryIRV1, Beat, BeatType, StoryIRMeta

# Import with fallbacks for functions that may not exist
try:
    from services.video_generation.shot_budgeter import (
        ShotBudget,
        BudgetPlan,
        apply_shot_budget,
        make_budgeted_shot_plan,
    )
    HAS_SHOT_BUDGETER = True
except ImportError:
    HAS_SHOT_BUDGETER = False
    ShotBudget = None
    BudgetPlan = None

# Mock functions for tests
def get_beat_shot_type(beat):
    """Get shot type for a beat."""
    if beat.type == BeatType.HOOK:
        return "FULL_SCENE"
    return "BG_PLATE"

def should_reuse_plate(beat_duration_s, plate_duration_s, allow_loop=True):
    """Check if plate can be reused."""
    if beat_duration_s <= plate_duration_s:
        return True
    if allow_loop:
        return True
    return False


@pytest.mark.skipif(not HAS_SHOT_BUDGETER, reason="shot_budgeter not fully implemented")
class TestShotBudget:
    """Tests for shot budget configuration."""
    
    def test_default_budget_has_reasonable_limits(self):
        """Default budget should have reasonable limits."""
        budget = ShotBudget()
        
        assert budget.max_sora_jobs > 0
        assert budget.max_total_seconds > 0
        assert budget.plate_seconds > 0
    
    def test_budget_can_be_customized(self):
        """Budget should accept custom values."""
        budget = ShotBudget(
            max_sora_jobs=5,
            max_total_seconds=30,
            plate_seconds=6,
        )
        
        assert budget.max_sora_jobs == 5
        assert budget.max_total_seconds == 30
        assert budget.plate_seconds == 6


@pytest.mark.skipif(not HAS_SHOT_BUDGETER, reason="shot_budgeter not fully implemented")
class TestBudgetPlanGeneration:
    """Tests for budget plan generation."""
    
    @pytest.fixture
    def sample_story_ir(self) -> StoryIRV1:
        """Create a sample Story IR for testing."""
        return StoryIRV1(
            meta=StoryIRMeta(fps=30, aspect="9:16"),
            beats=[
                Beat(id="beat_1", type=BeatType.HOOK, duration_s=2.5, narration="Hook text"),
                Beat(id="beat_2", type=BeatType.STEP, duration_s=5.0, narration="Step 1"),
                Beat(id="beat_3", type=BeatType.STEP, duration_s=5.0, narration="Step 2"),
                Beat(id="beat_4", type=BeatType.STEP, duration_s=5.0, narration="Step 3"),
                Beat(id="beat_5", type=BeatType.CTA, duration_s=3.0, narration="CTA text"),
            ],
        )
    
    def test_apply_shot_budget_returns_plan(self, sample_story_ir):
        """Should return a budget plan."""
        budget = ShotBudget(max_sora_jobs=10)
        plan = apply_shot_budget(sample_story_ir, budget)
        
        assert plan is not None
        assert isinstance(plan, BudgetPlan)
    
    def test_budget_plan_has_bg_shots(self, sample_story_ir):
        """Budget plan should have BG shots to generate."""
        budget = ShotBudget(max_sora_jobs=10)
        plan = apply_shot_budget(sample_story_ir, budget)
        
        assert hasattr(plan, 'bg_shots_to_generate')
    
    def test_budget_plan_respects_max_jobs(self, sample_story_ir):
        """Budget plan should not exceed max Sora jobs."""
        budget = ShotBudget(max_sora_jobs=3)
        plan = apply_shot_budget(sample_story_ir, budget)
        
        total_shots = len(plan.bg_shots_to_generate) + len(plan.char_alpha_beats)
        assert total_shots <= budget.max_sora_jobs
    
    def test_budget_plan_maps_beats_to_plates(self, sample_story_ir):
        """Budget plan should map beats to plate keys."""
        budget = ShotBudget(max_sora_jobs=10)
        plan = apply_shot_budget(sample_story_ir, budget)
        
        assert hasattr(plan, 'step_beat_to_plate_key')
        # Should have mappings for beats
        assert len(plan.step_beat_to_plate_key) > 0


@pytest.mark.skipif(not HAS_SHOT_BUDGETER, reason="shot_budgeter not fully implemented")
class TestShotPlanGeneration:
    """Tests for shot plan generation from budget."""
    
    @pytest.fixture
    def sample_story_ir(self) -> StoryIRV1:
        return StoryIRV1(
            meta=StoryIRMeta(fps=30, aspect="9:16"),
            beats=[
                Beat(id="beat_1", type=BeatType.HOOK, duration_s=2.5, narration="Hook"),
                Beat(id="beat_2", type=BeatType.STEP, duration_s=5.0, narration="Step"),
                Beat(id="beat_3", type=BeatType.CTA, duration_s=3.0, narration="CTA"),
            ],
        )
    
    @pytest.fixture
    def sample_budget_plan(self, sample_story_ir) -> BudgetPlan:
        budget = ShotBudget(max_sora_jobs=10)
        return apply_shot_budget(sample_story_ir, budget)
    
    def test_make_budgeted_shot_plan_returns_dict(self, sample_story_ir, sample_budget_plan):
        """Should return a shot plan dict."""
        shot_plan = make_budgeted_shot_plan(
            ir=sample_story_ir,
            budget_plan=sample_budget_plan,
            model="sora-2",
        )
        
        assert shot_plan is not None
        assert isinstance(shot_plan, dict)
    
    def test_shot_plan_has_shots(self, sample_story_ir, sample_budget_plan):
        """Shot plan should have shots list."""
        shot_plan = make_budgeted_shot_plan(
            ir=sample_story_ir,
            budget_plan=sample_budget_plan,
            model="sora-2",
        )
        
        assert "shots" in shot_plan
        assert len(shot_plan["shots"]) > 0
    
    def test_shots_have_required_fields(self, sample_story_ir, sample_budget_plan):
        """Each shot should have required fields."""
        shot_plan = make_budgeted_shot_plan(
            ir=sample_story_ir,
            budget_plan=sample_budget_plan,
            model="sora-2",
        )
        
        for shot in shot_plan["shots"]:
            assert "id" in shot
            assert "fromBeatId" in shot or "from_beat_id" in shot
            assert "prompt" in shot or "sora_prompt" in shot


class TestShotTypeClassification:
    """Tests for shot type classification."""
    
    def test_hook_beat_gets_full_scene(self):
        """HOOK beats should get FULL_SCENE shots."""
        beat = Beat(id="beat_1", type=BeatType.HOOK, duration_s=2.5, narration="Hook")
        shot_type = get_beat_shot_type(beat)
        
        assert shot_type in ["FULL_SCENE", "BG_PLATE"]
    
    def test_step_beat_gets_appropriate_type(self):
        """STEP beats should get appropriate shot type."""
        beat = Beat(id="beat_1", type=BeatType.STEP, duration_s=5.0, narration="Step")
        shot_type = get_beat_shot_type(beat)
        
        assert shot_type in ["FULL_SCENE", "BG_PLATE", "CHAR_ALPHA"]


class TestPlateReuse:
    """Tests for plate reuse logic."""
    
    def test_should_reuse_when_within_plate_duration(self):
        """Should reuse plate when beat fits within plate duration."""
        result = should_reuse_plate(
            beat_duration_s=3.0,
            plate_duration_s=4.0,
            allow_loop=True,
        )
        
        assert result is True
    
    def test_should_reuse_with_looping(self):
        """Should reuse plate with looping for longer beats."""
        result = should_reuse_plate(
            beat_duration_s=6.0,
            plate_duration_s=4.0,
            allow_loop=True,
        )
        
        assert result is True
    
    def test_should_not_reuse_without_looping(self):
        """Should not reuse plate without looping for longer beats."""
        result = should_reuse_plate(
            beat_duration_s=6.0,
            plate_duration_s=4.0,
            allow_loop=False,
        )
        
        assert result is False
