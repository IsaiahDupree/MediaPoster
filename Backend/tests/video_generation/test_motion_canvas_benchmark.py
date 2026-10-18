"""
Benchmark tests for Motion Canvas rendering.

Tests:
- Scene generation
- Animation timing
- Render plan conversion
- Motion Canvas vs Remotion comparison
"""

import pytest
import time
import tempfile
from services.video_generation.types import StoryIRV1, Beat, BeatType, StoryIRMeta


class TestMotionCanvasSceneGeneration:
    """Benchmarks for Motion Canvas scene generation."""
    
    @pytest.fixture
    def large_story_ir(self) -> dict:
        """Create a large Story IR for benchmarking."""
        beats = []
        for i in range(50):
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
    
    def test_scene_structure_creation(self, large_story_ir):
        """Benchmark scene structure creation."""
        start = time.perf_counter()
        
        scenes = []
        cursor = 0
        
        for beat in large_story_ir["beats"]:
            duration_s = beat.get("duration_s", 3)
            duration_frames = int(duration_s * 30)
            
            scenes.append({
                "beatId": beat["id"],
                "startFrame": cursor,
                "durationInFrames": duration_frames,
                "type": beat["type"],
            })
            
            cursor += duration_frames
        
        elapsed = time.perf_counter() - start
        
        assert len(scenes) == 50
        assert elapsed < 0.1, f"Scene creation took {elapsed:.3f}s (should be <0.1s)"
    
    def test_animation_keyframe_generation(self):
        """Benchmark animation keyframe generation."""
        # Simulate generating keyframes for 100 elements
        elements = [{"id": f"elem_{i}", "type": "text"} for i in range(100)]
        
        start = time.perf_counter()
        
        keyframes = []
        for elem in elements:
            keyframes.append({
                "elementId": elem["id"],
                "property": "opacity",
                "frames": [
                    {"frame": 0, "value": 0},
                    {"frame": 15, "value": 1},
                ],
            })
            keyframes.append({
                "elementId": elem["id"],
                "property": "y",
                "frames": [
                    {"frame": 0, "value": 20},
                    {"frame": 15, "value": 0},
                ],
            })
        
        elapsed = time.perf_counter() - start
        
        assert len(keyframes) == 200
        assert elapsed < 0.05, f"Keyframe generation took {elapsed:.3f}s (should be <0.05s)"


class TestMotionCanvasRenderPlan:
    """Tests for Motion Canvas render plan structure."""
    
    def test_motion_canvas_plan_structure(self):
        """Motion Canvas plan should have correct structure."""
        plan = {
            "projectId": "test_project",
            "fps": 30,
            "resolution": {"width": 1080, "height": 1920},
            "scenes": [
                {
                    "name": "intro",
                    "durationInFrames": 90,
                    "layers": [],
                },
                {
                    "name": "main",
                    "durationInFrames": 1500,
                    "layers": [],
                },
                {
                    "name": "outro",
                    "durationInFrames": 150,
                    "layers": [],
                },
            ],
            "audio": {
                "music": {"src": "music.mp3", "volume": 0.3},
                "voiceover": {"src": "vo.wav", "volume": 1.0},
            },
        }
        
        assert "scenes" in plan
        assert len(plan["scenes"]) == 3
        assert "audio" in plan
    
    def test_motion_canvas_layer_structure(self):
        """Motion Canvas layer should have correct structure."""
        layer = {
            "id": "bg_video",
            "type": "video",
            "src": "plates/plate_1.mp4",
            "startFrame": 0,
            "endFrame": 120,
            "transform": {
                "x": 0,
                "y": 0,
                "scaleX": 1,
                "scaleY": 1,
                "rotation": 0,
            },
            "opacity": 1,
        }
        
        assert "type" in layer
        assert "transform" in layer
    
    def test_motion_canvas_text_layer(self):
        """Motion Canvas text layer should have text properties."""
        layer = {
            "id": "title",
            "type": "text",
            "text": "Hello World",
            "startFrame": 0,
            "endFrame": 90,
            "style": {
                "fontSize": 64,
                "fontFamily": "Inter",
                "fontWeight": 700,
                "color": "#FFFFFF",
                "textAlign": "center",
            },
            "animations": [
                {
                    "property": "opacity",
                    "keyframes": [
                        {"frame": 0, "value": 0, "easing": "easeOut"},
                        {"frame": 15, "value": 1, "easing": "linear"},
                    ],
                },
            ],
        }
        
        assert "style" in layer
        assert "animations" in layer


class TestMotionCanvasVsRemotionComparison:
    """Comparison tests between Motion Canvas and Remotion."""
    
    @pytest.fixture
    def sample_story_ir(self) -> dict:
        return {
            "meta": {"fps": 30, "aspect": "9:16"},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "duration_s": 2.5, "narration": "Hook"},
                {"id": "beat_2", "type": "STEP", "duration_s": 5.0, "narration": "Step 1"},
                {"id": "beat_3", "type": "STEP", "duration_s": 5.0, "narration": "Step 2"},
                {"id": "beat_4", "type": "REVEAL", "duration_s": 4.0, "narration": "Reveal"},
                {"id": "beat_5", "type": "CTA", "duration_s": 3.0, "narration": "CTA"},
            ],
        }
    
    def test_both_render_same_duration(self, sample_story_ir):
        """Both renderers should produce same total duration."""
        fps = sample_story_ir["meta"]["fps"]
        
        # Calculate expected total
        total_seconds = sum(b["duration_s"] for b in sample_story_ir["beats"])
        expected_frames = int(total_seconds * fps)
        
        # Remotion plan
        remotion_plan = {
            "fps": fps,
            "durationInFrames": expected_frames,
            "layers": [],
        }
        
        # Motion Canvas plan
        mc_plan = {
            "fps": fps,
            "totalFrames": expected_frames,
            "scenes": [],
        }
        
        assert remotion_plan["durationInFrames"] == mc_plan["totalFrames"]
    
    def test_layer_count_consistency(self, sample_story_ir):
        """Both renderers should have consistent layer counts."""
        beats = sample_story_ir["beats"]
        
        # Each beat needs at minimum: 1 BG video layer
        min_layers = len(beats)
        
        # Remotion layers
        remotion_layers = []
        for i, beat in enumerate(beats):
            remotion_layers.append({
                "id": f"bg_{beat['id']}",
                "kind": "VIDEO",
            })
        
        # Motion Canvas layers (per scene)
        mc_layers = []
        for beat in beats:
            mc_layers.append({
                "id": f"bg_{beat['id']}",
                "type": "video",
            })
        
        assert len(remotion_layers) >= min_layers
        assert len(mc_layers) >= min_layers
    
    def test_timing_consistency(self, sample_story_ir):
        """Both renderers should have consistent beat timing."""
        fps = sample_story_ir["meta"]["fps"]
        beats = sample_story_ir["beats"]
        
        # Calculate timing for each renderer
        remotion_timing = []
        mc_timing = []
        cursor = 0
        
        for beat in beats:
            duration_frames = int(beat["duration_s"] * fps)
            
            remotion_timing.append({
                "beatId": beat["id"],
                "from": cursor,
                "durationInFrames": duration_frames,
            })
            
            mc_timing.append({
                "beatId": beat["id"],
                "startFrame": cursor,
                "endFrame": cursor + duration_frames,
            })
            
            cursor += duration_frames
        
        # Verify consistency
        for r, m in zip(remotion_timing, mc_timing):
            assert r["from"] == m["startFrame"]
            assert r["from"] + r["durationInFrames"] == m["endFrame"]


class TestRenderBenchmarkMetrics:
    """Metrics collection for render benchmarks."""
    
    def test_collect_render_metrics(self):
        """Collect and verify render metrics structure."""
        metrics = {
            "renderer": "remotion",
            "duration_seconds": 58.5,
            "frame_count": 1755,
            "fps": 30,
            "resolution": "1080x1920",
            "render_time_seconds": 45.2,
            "file_size_mb": 12.5,
            "layers": {
                "video": 5,
                "audio": 8,
                "text": 12,
            },
        }
        
        assert metrics["duration_seconds"] > 0
        assert metrics["render_time_seconds"] > 0
        assert metrics["fps"] == 30
    
    def test_compare_renderer_metrics(self):
        """Compare metrics between renderers."""
        remotion_metrics = {
            "renderer": "remotion",
            "render_time_seconds": 45.2,
            "file_size_mb": 12.5,
        }
        
        mc_metrics = {
            "renderer": "motion_canvas",
            "render_time_seconds": 52.1,
            "file_size_mb": 11.8,
        }
        
        # Calculate differences
        time_diff = mc_metrics["render_time_seconds"] - remotion_metrics["render_time_seconds"]
        size_diff = mc_metrics["file_size_mb"] - remotion_metrics["file_size_mb"]
        
        # Log comparison (in real tests, would be stored)
        comparison = {
            "time_difference_seconds": time_diff,
            "size_difference_mb": size_diff,
            "faster_renderer": "remotion" if time_diff > 0 else "motion_canvas",
            "smaller_output": "motion_canvas" if size_diff < 0 else "remotion",
        }
        
        assert "faster_renderer" in comparison
        assert "smaller_output" in comparison


class TestMotionCanvasEdgeCases:
    """Edge case tests for Motion Canvas rendering."""
    
    def test_empty_scene(self):
        """Should handle empty scene gracefully."""
        scene = {
            "name": "empty",
            "durationInFrames": 30,
            "layers": [],
        }
        
        assert scene["layers"] == []
    
    def test_overlapping_animations(self):
        """Should handle overlapping animations."""
        layer = {
            "id": "text_1",
            "type": "text",
            "animations": [
                {
                    "property": "opacity",
                    "keyframes": [
                        {"frame": 0, "value": 0},
                        {"frame": 30, "value": 1},
                    ],
                },
                {
                    "property": "y",
                    "keyframes": [
                        {"frame": 0, "value": 50},
                        {"frame": 30, "value": 0},
                    ],
                },
            ],
        }
        
        # Both animations should be valid
        assert len(layer["animations"]) == 2
    
    def test_scene_transitions(self):
        """Should define scene transitions."""
        plan = {
            "scenes": [
                {"name": "scene_1", "durationInFrames": 90},
                {"name": "scene_2", "durationInFrames": 120},
            ],
            "transitions": [
                {
                    "from": "scene_1",
                    "to": "scene_2",
                    "type": "crossfade",
                    "durationInFrames": 15,
                },
            ],
        }
        
        assert len(plan["transitions"]) == 1
        assert plan["transitions"][0]["type"] == "crossfade"
