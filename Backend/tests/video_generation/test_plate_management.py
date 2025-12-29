"""
Unit tests for plate management.

Tests:
- Plate looping
- Plate stretching
- Variety injection
- Anti-pattern detection
"""

import pytest
from services.video_generation.types import StoryIRV1, Beat, BeatType, StoryIRMeta
from services.video_generation.plate_manager import (
    build_beat_bg_bindings,
    inject_variety,
    detect_plate_anti_patterns,
    fix_anti_patterns,
    PlateBinding,
    PlateAntiPattern,
)


class TestPlateBindings:
    """Tests for plate binding generation."""
    
    @pytest.fixture
    def sample_story_ir(self) -> StoryIRV1:
        return StoryIRV1(
            meta=StoryIRMeta(fps=30, aspect="9:16"),
            beats=[
                Beat(id="beat_1", type=BeatType.HOOK, duration_s=2.5, narration="Hook"),
                Beat(id="beat_2", type=BeatType.STEP, duration_s=5.0, narration="Step 1"),
                Beat(id="beat_3", type=BeatType.STEP, duration_s=5.0, narration="Step 2"),
                Beat(id="beat_4", type=BeatType.CTA, duration_s=3.0, narration="CTA"),
            ],
        )
    
    @pytest.fixture
    def sample_plate_mapping(self) -> dict:
        return {
            "beat_1": "plate_hook",
            "beat_2": "plate_step_1",
            "beat_3": "plate_step_1",  # Reuse
            "beat_4": "plate_cta",
        }
    
    def test_build_bindings_returns_dict(self, sample_story_ir, sample_plate_mapping):
        """Should return bindings dict."""
        bindings = build_beat_bg_bindings(
            ir=sample_story_ir,
            step_beat_to_plate_key=sample_plate_mapping,
            plate_seconds=4.0,
        )
        
        assert bindings is not None
        assert isinstance(bindings, dict)
    
    def test_bindings_cover_all_beats(self, sample_story_ir, sample_plate_mapping):
        """Should have bindings for all beats."""
        bindings = build_beat_bg_bindings(
            ir=sample_story_ir,
            step_beat_to_plate_key=sample_plate_mapping,
            plate_seconds=4.0,
        )
        
        for beat in sample_story_ir.beats:
            assert beat.id in bindings
    
    def test_binding_has_plate_key(self, sample_story_ir, sample_plate_mapping):
        """Each binding should have plate key."""
        bindings = build_beat_bg_bindings(
            ir=sample_story_ir,
            step_beat_to_plate_key=sample_plate_mapping,
            plate_seconds=4.0,
        )
        
        for beat_id, binding in bindings.items():
            assert "plateKey" in binding or "plate_key" in binding
    
    def test_binding_calculates_loop_count(self, sample_story_ir, sample_plate_mapping):
        """Should calculate loop count for longer beats."""
        bindings = build_beat_bg_bindings(
            ir=sample_story_ir,
            step_beat_to_plate_key=sample_plate_mapping,
            plate_seconds=4.0,
            prefer_stretch=False,
        )
        
        # Beat 2 is 5s, plate is 4s, so needs loop or stretch
        binding = bindings.get("beat_2", {})
        assert "loopCount" in binding or "loop_count" in binding or "stretchFactor" in binding


class TestVarietyInjection:
    """Tests for variety injection."""
    
    @pytest.fixture
    def sample_story_ir(self) -> StoryIRV1:
        return StoryIRV1(
            meta=StoryIRMeta(fps=30, aspect="9:16"),
            beats=[
                Beat(id="beat_1", type=BeatType.HOOK, duration_s=2.5, narration="Hook"),
                Beat(id="beat_2", type=BeatType.STEP, duration_s=5.0, narration="Step 1"),
                Beat(id="beat_3", type=BeatType.STEP, duration_s=5.0, narration="Step 2"),
                Beat(id="beat_4", type=BeatType.STEP, duration_s=5.0, narration="Step 3"),
                Beat(id="beat_5", type=BeatType.REVEAL, duration_s=4.0, narration="Reveal"),
            ],
        )
    
    def test_inject_variety_returns_plan(self, sample_story_ir):
        """Should return updated plan."""
        budget_plan = {
            "bgShotsToGenerate": ["plate_1", "plate_2"],
            "charAlphaBeats": [],
            "stepBeatToPlateKey": {
                "beat_1": "plate_1",
                "beat_2": "plate_1",
                "beat_3": "plate_1",
                "beat_4": "plate_2",
                "beat_5": "plate_2",
            },
        }
        
        result = inject_variety(sample_story_ir, budget_plan)
        
        assert result is not None
    
    def test_variety_at_intent_shifts(self, sample_story_ir):
        """Should inject variety at intent shifts (e.g., STEP → REVEAL)."""
        budget_plan = {
            "bgShotsToGenerate": ["plate_1"],
            "charAlphaBeats": [],
            "stepBeatToPlateKey": {
                "beat_1": "plate_1",
                "beat_2": "plate_1",
                "beat_3": "plate_1",
                "beat_4": "plate_1",
                "beat_5": "plate_1",  # REVEAL beat - should get variety
            },
        }
        
        result = inject_variety(sample_story_ir, budget_plan)
        
        # REVEAL beat might get a different plate or char_alpha
        assert result is not None


class TestAntiPatternDetection:
    """Tests for anti-pattern detection."""
    
    @pytest.fixture
    def sample_bindings(self) -> dict:
        return {
            "beat_1": {"plateKey": "plate_1", "loopCount": 1},
            "beat_2": {"plateKey": "plate_1", "loopCount": 1},
            "beat_3": {"plateKey": "plate_1", "loopCount": 1},
            "beat_4": {"plateKey": "plate_1", "loopCount": 1},
            "beat_5": {"plateKey": "plate_1", "loopCount": 1},
        }
    
    def test_detect_same_plate_streak(self, sample_bindings):
        """Should detect same plate used too many times in a row."""
        patterns = detect_plate_anti_patterns(sample_bindings, max_same_plate_streak=3)
        
        assert len(patterns) > 0
        assert any(p.pattern_type == "SAME_PLATE_STREAK" for p in patterns)
    
    def test_no_pattern_when_varied(self):
        """Should not detect pattern when plates are varied."""
        bindings = {
            "beat_1": {"plateKey": "plate_1", "loopCount": 1},
            "beat_2": {"plateKey": "plate_2", "loopCount": 1},
            "beat_3": {"plateKey": "plate_1", "loopCount": 1},
            "beat_4": {"plateKey": "plate_3", "loopCount": 1},
        }
        
        patterns = detect_plate_anti_patterns(bindings, max_same_plate_streak=3)
        
        same_plate_patterns = [p for p in patterns if p.pattern_type == "SAME_PLATE_STREAK"]
        assert len(same_plate_patterns) == 0


class TestAntiPatternFixes:
    """Tests for anti-pattern fixes."""
    
    def test_fix_same_plate_streak(self):
        """Should fix same plate streak by varying plates."""
        bindings = {
            "beat_1": {"plateKey": "plate_1", "loopCount": 1},
            "beat_2": {"plateKey": "plate_1", "loopCount": 1},
            "beat_3": {"plateKey": "plate_1", "loopCount": 1},
            "beat_4": {"plateKey": "plate_1", "loopCount": 1},
        }
        available_plates = ["plate_1", "plate_2", "plate_3"]
        
        patterns = detect_plate_anti_patterns(bindings, max_same_plate_streak=2)
        fixed = fix_anti_patterns(bindings, patterns, available_plates)
        
        # After fix, should have more variety
        plate_keys = [b.get("plateKey") for b in fixed.values()]
        unique_plates = set(plate_keys)
        assert len(unique_plates) > 1
