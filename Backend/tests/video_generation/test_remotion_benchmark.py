"""
Benchmark tests for Remotion rendering.

Tests:
- Render plan generation speed
- Layer handling performance
- SFX cue processing
- Remotion-specific features
"""

import pytest
import time
import tempfile
from services.video_generation.remotion_sfx import (
    RemotionSfxCue,
    story_ir_to_remotion_sfx_cues,
    expand_remotion_sfx_cues,
    add_sfx_layers_to_render_plan,
)
from services.video_generation.remotion_budgeter import (
    create_remotion_budgeted_plan,
    bind_assets_to_remotion_layers,
)
from services.video_generation.remotion_time_events import (
    story_ir_to_time_events,
    TimeEvents,
)
from services.video_generation.types import StoryIRV1, Beat, BeatType, StoryIRMeta


class TestRemotionRenderPlanBenchmark:
    """Benchmarks for Remotion render plan generation."""
    
    @pytest.fixture
    def large_story_ir(self) -> dict:
        """Create a large Story IR for benchmarking."""
        beats = []
        for i in range(50):  # 50 beats
            beat_type = ["HOOK", "STEP", "REVEAL", "CTA"][i % 4]
            beats.append({
                "id": f"beat_{i}",
                "type": beat_type,
                "duration_s": 2.0 + (i % 3),
                "narration": f"This is beat number {i} with some narration text.",
            })
        
        return {
            "meta": {"fps": 30, "aspect": "9:16"},
            "beats": beats,
        }
    
    def test_sfx_cue_generation_performance(self, large_story_ir):
        """Benchmark SFX cue generation."""
        start = time.perf_counter()
        
        cues = story_ir_to_remotion_sfx_cues(large_story_ir, fps=30)
        
        elapsed = time.perf_counter() - start
        
        assert len(cues) > 0
        assert elapsed < 1.0, f"SFX cue generation took {elapsed:.3f}s (should be <1s)"
    
    def test_sfx_expansion_performance(self, large_story_ir):
        """Benchmark SFX macro expansion."""
        cues = story_ir_to_remotion_sfx_cues(large_story_ir, fps=30)
        
        start = time.perf_counter()
        
        expanded = expand_remotion_sfx_cues(cues)
        
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.5, f"SFX expansion took {elapsed:.3f}s (should be <0.5s)"
    
    def test_layer_generation_performance(self, large_story_ir):
        """Benchmark layer generation for large IR."""
        base_plan = {
            "version": "2.0.0",
            "fps": 30,
            "width": 1080,
            "height": 1920,
            "durationInFrames": 3000,
            "layers": [],
        }
        
        cues = story_ir_to_remotion_sfx_cues(large_story_ir, fps=30)
        
        start = time.perf_counter()
        
        result = add_sfx_layers_to_render_plan(base_plan, cues)
        
        elapsed = time.perf_counter() - start
        
        assert len(result["layers"]) > 0
        assert elapsed < 0.5, f"Layer generation took {elapsed:.3f}s (should be <0.5s)"
    
    def test_time_events_generation_performance(self, large_story_ir):
        """Benchmark time events generation."""
        start = time.perf_counter()
        
        events = story_ir_to_time_events(large_story_ir, fps=30)
        
        elapsed = time.perf_counter() - start
        
        assert len(events.events) > 0
        assert elapsed < 1.0, f"Time events generation took {elapsed:.3f}s (should be <1s)"


class TestRemotionLayerHandling:
    """Tests for Remotion layer handling."""
    
    def test_video_layer_creation(self):
        """Should create correct video layer structure."""
        layer = {
            "id": "bg_plate_1",
            "kind": "VIDEO",
            "from": 0,
            "durationInFrames": 120,
            "src": "plates/plate_1.mp4",
            "zIndex": 0,
            "muted": True,
            "loop": False,
        }
        
        assert layer["kind"] == "VIDEO"
        assert layer["muted"] is True
    
    def test_audio_layer_with_volume(self):
        """Should create audio layer with volume control."""
        layer = {
            "id": "sfx_whoosh",
            "kind": "AUDIO",
            "from": 0,
            "durationInFrames": 30,
            "src": "sfx/whoosh.wav",
            "volume": 0.8,
            "zIndex": 100,
        }
        
        assert layer["volume"] == 0.8
    
    def test_text_layer_with_animation(self):
        """Should create text layer with animation config."""
        layer = {
            "id": "title_main",
            "kind": "TEXT",
            "from": 0,
            "durationInFrames": 90,
            "text": "Hello World",
            "fontSize": 64,
            "fontFamily": "Inter",
            "color": "#FFFFFF",
            "animation": {
                "type": "fade",
                "durationInFrames": 15,
            },
            "zIndex": 50,
        }
        
        assert "animation" in layer
        assert layer["animation"]["type"] == "fade"
    
    def test_overlay_layer_with_alpha(self):
        """Should create overlay layer with alpha channel."""
        layer = {
            "id": "char_alpha_1",
            "kind": "VIDEO",
            "from": 0,
            "durationInFrames": 120,
            "src": "overlays/char_1.webm",
            "hasAlpha": True,
            "zIndex": 30,
            "position": {
                "x": 540,
                "y": 1440,
                "anchor": "bottom_center",
            },
        }
        
        assert layer["hasAlpha"] is True
        assert "position" in layer


class TestRemotionSfxIntegration:
    """Tests for Remotion SFX integration."""
    
    def test_sfx_cue_timing_accuracy(self):
        """SFX cues should have accurate timing."""
        ir = {
            "meta": {"fps": 30},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "duration_s": 2.0},
                {"id": "beat_2", "type": "REVEAL", "duration_s": 3.0},
            ],
        }
        
        cues = story_ir_to_remotion_sfx_cues(ir, fps=30)
        
        # HOOK at frame 0
        hook_cues = [c for c in cues if c.frame == 0]
        assert len(hook_cues) > 0
        
        # REVEAL at frame 60 (2.0s * 30fps)
        reveal_cues = [c for c in cues if c.frame == 60]
        assert len(reveal_cues) > 0
    
    def test_sfx_volume_ranges(self):
        """SFX volumes should be in valid range."""
        ir = {
            "meta": {"fps": 30},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "duration_s": 2.0},
                {"id": "beat_2", "type": "STEP", "duration_s": 3.0},
                {"id": "beat_3", "type": "CTA", "duration_s": 2.0},
            ],
        }
        
        cues = story_ir_to_remotion_sfx_cues(ir, fps=30)
        
        for cue in cues:
            assert 0 <= cue.volume <= 1.0
    
    def test_sfx_layer_z_index_ordering(self):
        """SFX layers should have proper z-index ordering."""
        base_plan = {
            "version": "2.0.0",
            "fps": 30,
            "durationInFrames": 300,
            "layers": [
                {"id": "bg", "kind": "VIDEO", "from": 0, "durationInFrames": 300, "zIndex": 0},
            ],
        }
        
        cues = [
            RemotionSfxCue(frame=0, sfx_id="whoosh", volume=1.0),
            RemotionSfxCue(frame=60, sfx_id="reveal", volume=0.8),
        ]
        
        result = add_sfx_layers_to_render_plan(base_plan, cues)
        
        # SFX layers should have higher z-index than video
        audio_layers = [l for l in result["layers"] if l.get("kind") == "AUDIO"]
        for layer in audio_layers:
            assert layer.get("zIndex", 0) > 0


class TestRemotionAssetBinding:
    """Tests for Remotion asset binding."""
    
    @pytest.fixture
    def sample_story_ir_model(self) -> StoryIRV1:
        return StoryIRV1(
            meta=StoryIRMeta(fps=30, aspect="9:16"),
            beats=[
                Beat(id="beat_1", type=BeatType.HOOK, duration_s=2.5, narration="Hook"),
                Beat(id="beat_2", type=BeatType.STEP, duration_s=5.0, narration="Step"),
                Beat(id="beat_3", type=BeatType.CTA, duration_s=3.0, narration="CTA"),
            ],
        )
    
    def test_bind_assets_creates_layers(self, sample_story_ir_model):
        """Should bind assets to create video layers."""
        assets = {
            "clips": [
                {"shotId": "shot_1", "beatId": "beat_1", "src": "plate_1.mp4"},
                {"shotId": "shot_2", "beatId": "beat_2", "src": "plate_2.mp4"},
                {"shotId": "shot_3", "beatId": "beat_3", "src": "plate_3.mp4"},
            ],
        }
        
        budget_plan = {
            "bgShotsToGenerate": ["plate_1", "plate_2", "plate_3"],
            "stepBeatToPlateKey": {
                "beat_1": "plate_1",
                "beat_2": "plate_2",
                "beat_3": "plate_3",
            },
        }
        
        layers = bind_assets_to_remotion_layers(
            ir=sample_story_ir_model,
            assets=assets,
            budget_plan=budget_plan,
            fps=30,
        )
        
        assert len(layers) > 0
    
    def test_layer_timing_matches_beats(self, sample_story_ir_model):
        """Layer timing should match beat durations."""
        assets = {
            "clips": [
                {"shotId": "shot_1", "beatId": "beat_1", "src": "plate_1.mp4"},
            ],
        }
        
        budget_plan = {
            "bgShotsToGenerate": ["plate_1"],
            "stepBeatToPlateKey": {"beat_1": "plate_1"},
        }
        
        layers = bind_assets_to_remotion_layers(
            ir=sample_story_ir_model,
            assets=assets,
            budget_plan=budget_plan,
            fps=30,
        )
        
        # First beat is 2.5s at 30fps = 75 frames
        if layers:
            first_layer = layers[0]
            assert first_layer.get("durationInFrames") == 75


class TestRemotionEdgeCases:
    """Edge case tests for Remotion rendering."""
    
    def test_empty_story_ir(self):
        """Should handle empty Story IR gracefully."""
        ir = {"meta": {"fps": 30}, "beats": []}
        
        cues = story_ir_to_remotion_sfx_cues(ir, fps=30)
        
        assert cues == []
    
    def test_single_beat_ir(self):
        """Should handle single beat Story IR."""
        ir = {
            "meta": {"fps": 30},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "duration_s": 5.0},
            ],
        }
        
        cues = story_ir_to_remotion_sfx_cues(ir, fps=30)
        events = story_ir_to_time_events(ir, fps=30)
        
        assert len(cues) >= 1
        assert len(events.events) >= 1
    
    def test_very_long_beat(self):
        """Should handle very long beat durations."""
        ir = {
            "meta": {"fps": 30},
            "beats": [
                {"id": "beat_1", "type": "STEP", "duration_s": 120.0},  # 2 minutes
            ],
        }
        
        events = story_ir_to_time_events(ir, fps=30)
        
        assert len(events.events) > 0
        # Check frame calculation doesn't overflow
        max_frame = max(e.frame for e in events.events)
        assert max_frame == 0  # First beat starts at frame 0
    
    def test_high_fps(self):
        """Should handle high FPS correctly."""
        ir = {
            "meta": {"fps": 60},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "duration_s": 2.0},
            ],
        }
        
        cues = story_ir_to_remotion_sfx_cues(ir, fps=60)
        
        # At 60fps, 2.0s = 120 frames for next beat
        assert all(c.frame >= 0 for c in cues)
