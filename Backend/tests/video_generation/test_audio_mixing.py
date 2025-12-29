"""
Unit tests for audio mixing.

Tests:
- Audio bus generation
- Track mixing
- SFX cue → track conversion
- Loudness normalization
"""

import pytest
import tempfile
import os
from services.video_generation.audio_bus_mixer import (
    AudioTrack,
    AudioBusConfig,
    AudioBusResult,
    sfx_cues_to_tracks,
)
from services.video_generation.vo_stitcher import (
    BeatNarrationInput,
    NarrationAsset,
    NarrationCue,
    StitchedNarration,
)
from services.video_generation.audio_ducking import (
    story_ir_to_narration_cues,
    calculate_ducking_for_render_plan,
    DuckingConfig,
)


class TestAudioTrack:
    """Tests for AudioTrack model."""
    
    def test_audio_track_creation(self):
        """Should create AudioTrack with defaults."""
        track = AudioTrack(path="/path/to/audio.wav")
        
        assert track.path == "/path/to/audio.wav"
        assert track.volume == 1.0
        assert track.start_seconds == 0
    
    def test_audio_track_with_options(self):
        """Should create AudioTrack with options."""
        track = AudioTrack(
            path="/path/to/audio.wav",
            volume=0.5,
            start_seconds=2.0,
            fade_in_seconds=0.5,
            fade_out_seconds=1.0,
            loop=True,
        )
        
        assert track.volume == 0.5
        assert track.start_seconds == 2.0
        assert track.fade_in_seconds == 0.5
        assert track.fade_out_seconds == 1.0
        assert track.loop is True


class TestAudioBusConfig:
    """Tests for AudioBusConfig model."""
    
    def test_default_config(self):
        """Should have reasonable defaults."""
        config = AudioBusConfig()
        
        assert config.sample_rate == 48000
        assert config.channels == 2
        assert config.normalize is True
        assert config.target_lufs == -16
    
    def test_custom_config(self):
        """Should accept custom values."""
        config = AudioBusConfig(
            sample_rate=44100,
            channels=1,
            normalize=False,
            target_lufs=-14,
        )
        
        assert config.sample_rate == 44100
        assert config.channels == 1
        assert config.normalize is False
        assert config.target_lufs == -14


class TestSfxCuesToTracks:
    """Tests for SFX cue → track conversion."""
    
    def test_converts_cues_to_tracks(self):
        """Should convert SFX cues to audio tracks."""
        cues = [
            {"frame": 0, "sfxId": "whoosh", "volume": 1.0},
            {"frame": 90, "sfxId": "reveal", "volume": 0.8},
        ]
        
        # Create temp SFX directory with mock files
        with tempfile.TemporaryDirectory() as sfx_root:
            # Create mock SFX files
            for sfx_id in ["whoosh", "reveal"]:
                path = os.path.join(sfx_root, f"{sfx_id}.wav")
                with open(path, "w") as f:
                    f.write("mock")
            
            tracks = sfx_cues_to_tracks(cues, sfx_root, fps=30)
            
            assert len(tracks) == 2
    
    def test_track_timing_from_frame(self):
        """Should convert frame to start_seconds."""
        cues = [
            {"frame": 60, "sfxId": "whoosh", "volume": 1.0},
        ]
        
        with tempfile.TemporaryDirectory() as sfx_root:
            path = os.path.join(sfx_root, "whoosh.wav")
            with open(path, "w") as f:
                f.write("mock")
            
            tracks = sfx_cues_to_tracks(cues, sfx_root, fps=30)
            
            # Frame 60 at 30fps = 2 seconds
            assert len(tracks) == 1
            assert tracks[0].start_seconds == 2.0
    
    def test_track_volume_from_cue(self):
        """Should use volume from cue."""
        cues = [
            {"frame": 0, "sfxId": "whoosh", "volume": 0.5},
        ]
        
        with tempfile.TemporaryDirectory() as sfx_root:
            path = os.path.join(sfx_root, "whoosh.wav")
            with open(path, "w") as f:
                f.write("mock")
            
            tracks = sfx_cues_to_tracks(cues, sfx_root, fps=30)
            
            assert tracks[0].volume == 0.5
    
    def test_skips_missing_sfx_files(self):
        """Should skip cues without matching SFX files."""
        cues = [
            {"frame": 0, "sfxId": "missing_sfx", "volume": 1.0},
        ]
        
        with tempfile.TemporaryDirectory() as sfx_root:
            tracks = sfx_cues_to_tracks(cues, sfx_root, fps=30)
            
            assert len(tracks) == 0


class TestNarrationCues:
    """Tests for narration cue generation."""
    
    @pytest.fixture
    def sample_story_ir(self) -> dict:
        return {
            "meta": {"fps": 30, "aspect": "9:16"},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "duration_s": 2.5, "narration": "Hook text"},
                {"id": "beat_2", "type": "STEP", "duration_s": 5.0, "narration": "Step text"},
            ],
        }
    
    def test_story_ir_to_narration_cues(self, sample_story_ir):
        """Should generate narration cues from Story IR."""
        cues = story_ir_to_narration_cues(sample_story_ir, fps=30)
        
        assert cues is not None
        assert len(cues) == 2
    
    def test_narration_cues_have_timing(self, sample_story_ir):
        """Narration cues should have timing info."""
        cues = story_ir_to_narration_cues(sample_story_ir, fps=30)
        
        for cue in cues:
            assert hasattr(cue, 'from_frame') or 'fromFrame' in cue
            assert hasattr(cue, 'duration_frames') or 'durationInFrames' in cue


class TestAudioDucking:
    """Tests for audio ducking."""
    
    @pytest.fixture
    def sample_render_plan(self) -> dict:
        return {
            "version": "2.0.0",
            "fps": 30,
            "durationInFrames": 300,
            "layers": [
                {
                    "id": "bg_music",
                    "kind": "AUDIO",
                    "from": 0,
                    "durationInFrames": 300,
                    "src": "music.mp3",
                    "volume": 1.0,
                },
            ],
        }
    
    @pytest.fixture
    def sample_narration_cues(self) -> list:
        return [
            {"beatId": "beat_1", "fromFrame": 0, "durationInFrames": 75},
            {"beatId": "beat_2", "fromFrame": 75, "durationInFrames": 150},
        ]
    
    def test_calculate_ducking_returns_plan(self, sample_render_plan, sample_narration_cues):
        """Should return updated render plan."""
        result = calculate_ducking_for_render_plan(
            sample_render_plan,
            sample_narration_cues,
        )
        
        assert result is not None
        assert "layers" in result
    
    def test_ducking_adds_volume_keyframes(self, sample_render_plan, sample_narration_cues):
        """Ducking should add volume keyframes to music layers."""
        result = calculate_ducking_for_render_plan(
            sample_render_plan,
            sample_narration_cues,
        )
        
        # Find music layer
        music_layer = next(
            (l for l in result["layers"] if l.get("id") == "bg_music"),
            None
        )
        
        assert music_layer is not None
        # Should have ducking info or volume keyframes
        assert "ducking" in music_layer or "volumeKeyframes" in music_layer


class TestDuckingConfig:
    """Tests for ducking configuration."""
    
    def test_default_ducking_config(self):
        """Should have reasonable defaults."""
        config = DuckingConfig()
        
        assert config.base_volume > 0
        assert config.ducked_volume < config.base_volume
        assert config.fade_frames > 0
    
    def test_custom_ducking_config(self):
        """Should accept custom values."""
        config = DuckingConfig(
            base_volume=0.9,
            ducked_volume=0.2,
            fade_frames=10,
        )
        
        assert config.base_volume == 0.9
        assert config.ducked_volume == 0.2
        assert config.fade_frames == 10
