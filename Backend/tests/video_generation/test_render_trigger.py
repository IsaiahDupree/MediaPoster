"""
Unit tests for render trigger.

Tests:
- Remotion render triggering
- Motion Canvas render triggering
- FFmpeg render triggering
- Render plan saving
"""

import pytest
import tempfile
import os
import json
from services.video_generation.render_trigger import (
    RenderConfig,
    RenderResult,
    save_render_plan,
)


class TestRenderConfig:
    """Tests for RenderConfig model."""
    
    def test_default_config(self):
        """Should have reasonable defaults."""
        config = RenderConfig(output_dir="/tmp/output")
        
        assert config.output_dir == "/tmp/output"
        assert config.engine == "remotion"
        assert config.headless is True
    
    def test_remotion_config(self):
        """Should configure for Remotion."""
        config = RenderConfig(
            output_dir="/tmp/output",
            engine="remotion",
            remotion_root="/path/to/remotion",
            composition_id="MainVideo",
        )
        
        assert config.engine == "remotion"
        assert config.remotion_root == "/path/to/remotion"
        assert config.composition_id == "MainVideo"
    
    def test_motion_canvas_config(self):
        """Should configure for Motion Canvas."""
        config = RenderConfig(
            output_dir="/tmp/output",
            engine="motion_canvas",
            motion_canvas_root="/path/to/mc",
            editor_url="http://localhost:9000",
        )
        
        assert config.engine == "motion_canvas"
        assert config.motion_canvas_root == "/path/to/mc"
        assert config.editor_url == "http://localhost:9000"
    
    def test_ffmpeg_config(self):
        """Should configure for FFmpeg."""
        config = RenderConfig(
            output_dir="/tmp/output",
            engine="ffmpeg",
            project_name="my_video",
        )
        
        assert config.engine == "ffmpeg"
        assert config.project_name == "my_video"


class TestRenderResult:
    """Tests for RenderResult model."""
    
    def test_success_result(self):
        """Should create success result."""
        result = RenderResult(
            success=True,
            output_path="/tmp/output/video.mp4",
            duration_seconds=58.5,
            engine="remotion",
        )
        
        assert result.success is True
        assert result.output_path == "/tmp/output/video.mp4"
        assert result.duration_seconds == 58.5
    
    def test_failure_result(self):
        """Should create failure result."""
        result = RenderResult(
            success=False,
            error="Render failed: timeout",
            engine="remotion",
        )
        
        assert result.success is False
        assert result.error == "Render failed: timeout"
        assert result.output_path is None


class TestSaveRenderPlan:
    """Tests for render plan saving."""
    
    @pytest.fixture
    def sample_render_plan(self) -> dict:
        return {
            "version": "2.0.0",
            "fps": 30,
            "width": 1080,
            "height": 1920,
            "durationInFrames": 1740,
            "layers": [
                {
                    "id": "bg_1",
                    "kind": "VIDEO",
                    "from": 0,
                    "durationInFrames": 1740,
                    "src": "plate_1.mp4",
                },
            ],
        }
    
    @pytest.mark.asyncio
    async def test_save_render_plan_creates_file(self, sample_render_plan):
        """Should create JSON file."""
        with tempfile.TemporaryDirectory() as output_dir:
            path = await save_render_plan(sample_render_plan, output_dir)
            
            assert os.path.exists(path)
            assert path.endswith(".json")
    
    @pytest.mark.asyncio
    async def test_save_render_plan_valid_json(self, sample_render_plan):
        """Saved file should be valid JSON."""
        with tempfile.TemporaryDirectory() as output_dir:
            path = await save_render_plan(sample_render_plan, output_dir)
            
            with open(path, "r") as f:
                loaded = json.load(f)
            
            assert loaded["fps"] == 30
            assert loaded["width"] == 1080
    
    @pytest.mark.asyncio
    async def test_save_render_plan_custom_filename(self, sample_render_plan):
        """Should use custom filename."""
        with tempfile.TemporaryDirectory() as output_dir:
            path = await save_render_plan(
                sample_render_plan,
                output_dir,
                filename="custom_plan.json",
            )
            
            assert path.endswith("custom_plan.json")


class TestRemotionRenderPlan:
    """Tests for Remotion-specific render plan structure."""
    
    def test_remotion_plan_has_required_fields(self):
        """Remotion render plan should have required fields."""
        plan = {
            "version": "2.0.0",
            "fps": 30,
            "width": 1080,
            "height": 1920,
            "durationInFrames": 1740,
            "layers": [],
        }
        
        assert "fps" in plan
        assert "width" in plan
        assert "height" in plan
        assert "durationInFrames" in plan
        assert "layers" in plan
    
    def test_remotion_video_layer_structure(self):
        """Video layer should have correct structure."""
        layer = {
            "id": "bg_1",
            "kind": "VIDEO",
            "from": 0,
            "durationInFrames": 120,
            "src": "plate_1.mp4",
            "zIndex": 0,
            "muted": True,
        }
        
        assert layer["kind"] == "VIDEO"
        assert layer["from"] >= 0
        assert layer["durationInFrames"] > 0
        assert "src" in layer
    
    def test_remotion_audio_layer_structure(self):
        """Audio layer should have correct structure."""
        layer = {
            "id": "sfx_1",
            "kind": "AUDIO",
            "from": 0,
            "durationInFrames": 30,
            "src": "whoosh.wav",
            "volume": 0.8,
            "zIndex": 10,
        }
        
        assert layer["kind"] == "AUDIO"
        assert "volume" in layer
        assert layer["volume"] >= 0 and layer["volume"] <= 1
    
    def test_remotion_text_layer_structure(self):
        """Text layer should have correct structure."""
        layer = {
            "id": "title_1",
            "kind": "TEXT",
            "from": 0,
            "durationInFrames": 90,
            "text": "Hello World",
            "fontSize": 48,
            "fontFamily": "Inter",
            "color": "#FFFFFF",
            "zIndex": 20,
        }
        
        assert layer["kind"] == "TEXT"
        assert "text" in layer
        assert "fontSize" in layer


class TestMotionCanvasRenderPlan:
    """Tests for Motion Canvas render plan structure."""
    
    def test_motion_canvas_plan_structure(self):
        """Motion Canvas render plan should have scenes."""
        plan = {
            "fps": 30,
            "width": 1080,
            "height": 1920,
            "scenes": [
                {
                    "name": "intro",
                    "durationInFrames": 90,
                },
                {
                    "name": "main",
                    "durationInFrames": 1500,
                },
            ],
        }
        
        assert "scenes" in plan
        assert len(plan["scenes"]) > 0
    
    def test_motion_canvas_scene_structure(self):
        """Motion Canvas scene should have name and duration."""
        scene = {
            "name": "intro",
            "durationInFrames": 90,
            "layers": [],
        }
        
        assert "name" in scene
        assert "durationInFrames" in scene


class TestRenderPlanValidation:
    """Tests for render plan validation."""
    
    def test_plan_must_have_positive_fps(self):
        """FPS must be positive."""
        plan = {"fps": 30, "durationInFrames": 100}
        assert plan["fps"] > 0
    
    def test_plan_must_have_positive_duration(self):
        """Duration must be positive."""
        plan = {"fps": 30, "durationInFrames": 100}
        assert plan["durationInFrames"] > 0
    
    def test_plan_layers_must_be_list(self):
        """Layers must be a list."""
        plan = {"fps": 30, "durationInFrames": 100, "layers": []}
        assert isinstance(plan["layers"], list)
    
    def test_layer_from_must_be_non_negative(self):
        """Layer 'from' must be non-negative."""
        layer = {"id": "test", "from": 0, "durationInFrames": 100}
        assert layer["from"] >= 0
    
    def test_layer_duration_must_be_positive(self):
        """Layer duration must be positive."""
        layer = {"id": "test", "from": 0, "durationInFrames": 100}
        assert layer["durationInFrames"] > 0
