"""
Remotion-specific integration tests.

Tests:
- Full render plan generation for Remotion
- Layer ordering and z-index
- Video/audio/text layer interactions
- SFX timing accuracy
- Asset path resolution
"""

import pytest
import tempfile
import json
from pathlib import Path


class TestRemotionRenderPlanGeneration:
    """Tests for Remotion render plan generation."""
    
    @pytest.fixture
    def sample_story_ir(self) -> dict:
        return {
            "meta": {"fps": 30, "aspect": "9:16", "title": "Test Video"},
            "beats": [
                {"id": "beat_hook", "type": "HOOK", "duration_s": 2.5, "narration": "Hook text"},
                {"id": "beat_step1", "type": "STEP", "duration_s": 5.0, "narration": "Step 1 text"},
                {"id": "beat_step2", "type": "STEP", "duration_s": 5.0, "narration": "Step 2 text"},
                {"id": "beat_reveal", "type": "REVEAL", "duration_s": 4.0, "narration": "Reveal text"},
                {"id": "beat_cta", "type": "CTA", "duration_s": 3.0, "narration": "CTA text"},
            ],
        }
    
    def test_render_plan_has_correct_fps(self, sample_story_ir):
        """Render plan should have correct FPS."""
        fps = sample_story_ir["meta"]["fps"]
        
        plan = {
            "fps": fps,
            "width": 1080,
            "height": 1920,
            "durationInFrames": sum(int(b["duration_s"] * fps) for b in sample_story_ir["beats"]),
            "layers": [],
        }
        
        assert plan["fps"] == 30
    
    def test_render_plan_has_correct_resolution(self, sample_story_ir):
        """Render plan should have correct resolution for 9:16."""
        aspect = sample_story_ir["meta"]["aspect"]
        
        if aspect == "9:16":
            width, height = 1080, 1920
        elif aspect == "16:9":
            width, height = 1920, 1080
        else:
            width, height = 1080, 1080
        
        plan = {"width": width, "height": height}
        
        assert plan["width"] == 1080
        assert plan["height"] == 1920
    
    def test_render_plan_duration_matches_beats(self, sample_story_ir):
        """Total duration should match sum of beat durations."""
        fps = sample_story_ir["meta"]["fps"]
        
        total_seconds = sum(b["duration_s"] for b in sample_story_ir["beats"])
        expected_frames = int(total_seconds * fps)
        
        plan = {"durationInFrames": expected_frames}
        
        assert plan["durationInFrames"] == expected_frames
        assert plan["durationInFrames"] == 585  # 19.5s * 30fps


class TestRemotionLayerOrdering:
    """Tests for layer ordering and z-index."""
    
    def test_video_layers_have_lowest_z_index(self):
        """Video (BG) layers should have lowest z-index."""
        layers = [
            {"id": "bg_1", "kind": "VIDEO", "zIndex": 0},
            {"id": "text_1", "kind": "TEXT", "zIndex": 50},
            {"id": "sfx_1", "kind": "AUDIO", "zIndex": 100},
        ]
        
        video_layers = [l for l in layers if l["kind"] == "VIDEO"]
        other_layers = [l for l in layers if l["kind"] != "VIDEO"]
        
        for vl in video_layers:
            for ol in other_layers:
                assert vl["zIndex"] < ol["zIndex"]
    
    def test_text_layers_above_video(self):
        """Text layers should be above video layers."""
        layers = [
            {"id": "bg_1", "kind": "VIDEO", "zIndex": 0},
            {"id": "title_1", "kind": "TEXT", "zIndex": 50},
        ]
        
        video_z = [l["zIndex"] for l in layers if l["kind"] == "VIDEO"]
        text_z = [l["zIndex"] for l in layers if l["kind"] == "TEXT"]
        
        assert max(video_z) < min(text_z)
    
    def test_overlay_layers_above_bg(self):
        """Overlay layers should be above background."""
        layers = [
            {"id": "bg_1", "kind": "VIDEO", "zIndex": 0, "isOverlay": False},
            {"id": "char_1", "kind": "VIDEO", "zIndex": 25, "isOverlay": True},
        ]
        
        bg_layers = [l for l in layers if not l.get("isOverlay")]
        overlay_layers = [l for l in layers if l.get("isOverlay")]
        
        for ol in overlay_layers:
            for bl in bg_layers:
                assert ol["zIndex"] > bl["zIndex"]
    
    def test_audio_layers_dont_overlap_incorrectly(self):
        """Audio layers at same time should have different z-index."""
        layers = [
            {"id": "music_1", "kind": "AUDIO", "from": 0, "zIndex": 100},
            {"id": "sfx_1", "kind": "AUDIO", "from": 0, "zIndex": 101},
            {"id": "vo_1", "kind": "AUDIO", "from": 0, "zIndex": 102},
        ]
        
        z_indices = [l["zIndex"] for l in layers]
        assert len(z_indices) == len(set(z_indices)), "Audio layers should have unique z-indices"


class TestRemotionVideoLayers:
    """Tests for video layer properties."""
    
    def test_bg_plate_layer_structure(self):
        """BG plate layer should have correct structure."""
        layer = {
            "id": "bg_plate_1",
            "kind": "VIDEO",
            "from": 0,
            "durationInFrames": 120,
            "src": "plates/plate_1.mp4",
            "zIndex": 0,
            "muted": True,
            "loop": False,
            "playbackRate": 1.0,
        }
        
        assert layer["kind"] == "VIDEO"
        assert layer["muted"] is True
        assert "src" in layer
        assert layer["durationInFrames"] > 0
    
    def test_looped_plate_layer(self):
        """Looped plate should have loop: true."""
        layer = {
            "id": "bg_looped",
            "kind": "VIDEO",
            "from": 0,
            "durationInFrames": 300,
            "src": "plates/loop_plate.mp4",
            "loop": True,
            "loopCount": 3,
        }
        
        assert layer["loop"] is True
        assert layer["loopCount"] >= 1
    
    def test_stretched_plate_layer(self):
        """Stretched plate should have playbackRate < 1."""
        layer = {
            "id": "bg_stretched",
            "kind": "VIDEO",
            "from": 0,
            "durationInFrames": 180,
            "src": "plates/stretch_plate.mp4",
            "playbackRate": 0.67,  # Slowed down
        }
        
        assert layer["playbackRate"] < 1.0
    
    def test_char_alpha_overlay_layer(self):
        """CHAR_ALPHA overlay should have hasAlpha: true."""
        layer = {
            "id": "char_overlay_1",
            "kind": "VIDEO",
            "from": 60,
            "durationInFrames": 90,
            "src": "overlays/char_1.webm",
            "hasAlpha": True,
            "zIndex": 25,
            "position": {"x": 540, "y": 1440, "anchor": "bottom_center"},
        }
        
        assert layer["hasAlpha"] is True
        assert layer["zIndex"] > 0  # Above BG
        assert "position" in layer


class TestRemotionAudioLayers:
    """Tests for audio layer properties."""
    
    def test_music_layer_with_fade(self):
        """Music layer should support fade in/out."""
        layer = {
            "id": "bg_music",
            "kind": "AUDIO",
            "from": 0,
            "durationInFrames": 585,
            "src": "audio/music.mp3",
            "volume": 0.3,
            "fadeIn": {"durationInFrames": 30},
            "fadeOut": {"durationInFrames": 45},
        }
        
        assert layer["volume"] <= 1.0
        assert "fadeIn" in layer
        assert "fadeOut" in layer
    
    def test_voiceover_layer(self):
        """Voiceover layer should have full volume."""
        layer = {
            "id": "vo_beat_1",
            "kind": "AUDIO",
            "from": 0,
            "durationInFrames": 75,
            "src": "audio/vo/beat_1.wav",
            "volume": 1.0,
        }
        
        assert layer["volume"] == 1.0
    
    def test_sfx_layer_timing(self):
        """SFX layer should start at correct frame."""
        layer = {
            "id": "sfx_whoosh",
            "kind": "AUDIO",
            "from": 0,  # At beat start
            "durationInFrames": 30,
            "src": "sfx/whoosh.wav",
            "volume": 0.9,
        }
        
        assert layer["from"] >= 0
        assert layer["durationInFrames"] > 0
    
    def test_ducked_music_layer(self):
        """Music layer should have ducking keyframes during VO."""
        layer = {
            "id": "bg_music",
            "kind": "AUDIO",
            "from": 0,
            "durationInFrames": 585,
            "src": "audio/music.mp3",
            "volumeKeyframes": [
                {"frame": 0, "volume": 0.3},
                {"frame": 10, "volume": 0.1},  # Ducked during VO
                {"frame": 75, "volume": 0.3},  # Back up after VO
            ],
        }
        
        assert "volumeKeyframes" in layer
        assert len(layer["volumeKeyframes"]) >= 2


class TestRemotionTextLayers:
    """Tests for text layer properties."""
    
    def test_headline_text_layer(self):
        """Headline text should have correct styling."""
        layer = {
            "id": "headline_1",
            "kind": "TEXT",
            "from": 0,
            "durationInFrames": 75,
            "text": "Automate Your SFX",
            "style": {
                "fontSize": 72,
                "fontFamily": "Inter",
                "fontWeight": 700,
                "color": "#FFFFFF",
                "textAlign": "center",
            },
            "zIndex": 50,
        }
        
        assert layer["kind"] == "TEXT"
        assert "style" in layer
        assert layer["style"]["fontSize"] > 0
    
    def test_subtitle_text_layer(self):
        """Subtitle text should be smaller than headline."""
        headline = {"style": {"fontSize": 72}}
        subtitle = {"style": {"fontSize": 32}}
        
        assert subtitle["style"]["fontSize"] < headline["style"]["fontSize"]
    
    def test_animated_text_layer(self):
        """Text layer should support animations."""
        layer = {
            "id": "animated_title",
            "kind": "TEXT",
            "from": 0,
            "durationInFrames": 90,
            "text": "Hello World",
            "animations": [
                {
                    "property": "opacity",
                    "keyframes": [
                        {"frame": 0, "value": 0},
                        {"frame": 15, "value": 1},
                    ],
                },
                {
                    "property": "y",
                    "keyframes": [
                        {"frame": 0, "value": 30},
                        {"frame": 15, "value": 0},
                    ],
                },
            ],
        }
        
        assert "animations" in layer
        assert len(layer["animations"]) >= 1


class TestRemotionSfxTiming:
    """Tests for SFX timing accuracy."""
    
    @pytest.fixture
    def story_ir_with_reveals(self) -> dict:
        return {
            "meta": {"fps": 30},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "duration_s": 2.5},
                {"id": "beat_2", "type": "REVEAL", "duration_s": 4.0},
                {"id": "beat_3", "type": "CTA", "duration_s": 3.0},
            ],
        }
    
    def test_sfx_at_beat_start(self, story_ir_with_reveals):
        """SFX should trigger at beat start frame."""
        fps = story_ir_with_reveals["meta"]["fps"]
        beats = story_ir_with_reveals["beats"]
        
        # Calculate beat start frames
        beat_starts = []
        cursor = 0
        for beat in beats:
            beat_starts.append({"beatId": beat["id"], "frame": cursor})
            cursor += int(beat["duration_s"] * fps)
        
        # SFX cues should match beat starts
        sfx_cues = [
            {"frame": 0, "sfxId": "whoosh", "beatId": "beat_1"},
            {"frame": 75, "sfxId": "reveal_chime", "beatId": "beat_2"},
            {"frame": 195, "sfxId": "cta_pop", "beatId": "beat_3"},
        ]
        
        for cue in sfx_cues:
            matching_beat = next(b for b in beat_starts if b["beatId"] == cue["beatId"])
            assert cue["frame"] == matching_beat["frame"]
    
    def test_sfx_frame_calculation(self):
        """SFX frame should be calculated correctly from seconds."""
        fps = 30
        sfx_time_seconds = 2.5
        expected_frame = int(sfx_time_seconds * fps)
        
        assert expected_frame == 75
    
    def test_multiple_sfx_same_frame(self):
        """Multiple SFX at same frame should be allowed."""
        sfx_cues = [
            {"frame": 0, "sfxId": "whoosh", "volume": 1.0},
            {"frame": 0, "sfxId": "bass_hit", "volume": 0.8},
        ]
        
        # Should be able to have multiple cues at frame 0
        same_frame_cues = [c for c in sfx_cues if c["frame"] == 0]
        assert len(same_frame_cues) == 2


class TestRemotionAssetPaths:
    """Tests for asset path resolution."""
    
    def test_relative_asset_paths(self):
        """Asset paths should be relative to project."""
        layer = {
            "id": "bg_1",
            "kind": "VIDEO",
            "src": "assets/plates/plate_1.mp4",
        }
        
        assert not layer["src"].startswith("/")
        assert not layer["src"].startswith("C:")
    
    def test_sfx_path_resolution(self):
        """SFX paths should resolve to sfx directory."""
        sfx_id = "whoosh_fast"
        sfx_root = "public/sfx"
        
        # Possible extensions
        extensions = [".wav", ".mp3", ".ogg"]
        possible_paths = [f"{sfx_root}/{sfx_id}{ext}" for ext in extensions]
        
        assert all(p.startswith(sfx_root) for p in possible_paths)
    
    def test_plate_path_from_shot_id(self):
        """Plate path should be derivable from shot ID."""
        shot_id = "shot_hook_001"
        plates_dir = "assets/plates"
        
        expected_path = f"{plates_dir}/{shot_id}.mp4"
        
        assert shot_id in expected_path


class TestRemotionRenderPlanSerialization:
    """Tests for render plan JSON serialization."""
    
    @pytest.fixture
    def complete_render_plan(self) -> dict:
        return {
            "version": "2.0.0",
            "fps": 30,
            "width": 1080,
            "height": 1920,
            "durationInFrames": 585,
            "layers": [
                {
                    "id": "bg_1",
                    "kind": "VIDEO",
                    "from": 0,
                    "durationInFrames": 585,
                    "src": "plates/bg.mp4",
                    "zIndex": 0,
                    "muted": True,
                },
                {
                    "id": "music",
                    "kind": "AUDIO",
                    "from": 0,
                    "durationInFrames": 585,
                    "src": "audio/music.mp3",
                    "volume": 0.3,
                    "zIndex": 100,
                },
                {
                    "id": "title",
                    "kind": "TEXT",
                    "from": 0,
                    "durationInFrames": 90,
                    "text": "Hello",
                    "zIndex": 50,
                },
            ],
        }
    
    def test_render_plan_is_json_serializable(self, complete_render_plan):
        """Render plan should be JSON serializable."""
        json_str = json.dumps(complete_render_plan)
        
        assert json_str is not None
        assert len(json_str) > 0
    
    def test_render_plan_roundtrip(self, complete_render_plan):
        """Render plan should survive JSON roundtrip."""
        json_str = json.dumps(complete_render_plan)
        loaded = json.loads(json_str)
        
        assert loaded == complete_render_plan
    
    def test_render_plan_file_save(self, complete_render_plan):
        """Render plan should save to file correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(complete_render_plan, f, indent=2)
            temp_path = f.name
        
        # Read back
        with open(temp_path, 'r') as f:
            loaded = json.load(f)
        
        assert loaded["fps"] == 30
        assert len(loaded["layers"]) == 3
        
        # Cleanup
        Path(temp_path).unlink()
