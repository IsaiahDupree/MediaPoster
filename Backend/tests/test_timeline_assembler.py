"""
Timeline Assembler Tests
========================
Unit tests for timeline assembler service.

Run tests:
    pytest tests/test_timeline_assembler.py -v
"""

import asyncio
import os
import tempfile
import pytest
from uuid import uuid4
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_transition_type_values(self):
        """Test TransitionType enum values."""
        from services.video_orchestrator.timeline_assembler import TransitionType
        
        assert TransitionType.CUT.value == "cut"
        assert TransitionType.CROSSFADE.value == "crossfade"
        assert TransitionType.FADE_BLACK.value == "fade_black"
    
    def test_audio_track_type_values(self):
        """Test AudioTrackType enum values."""
        from services.video_orchestrator.timeline_assembler import AudioTrackType
        
        assert AudioTrackType.VOICEOVER.value == "voiceover"
        assert AudioTrackType.MUSIC.value == "music"
        assert AudioTrackType.SFX.value == "sfx"


# =============================================================================
# DATACLASS TESTS
# =============================================================================

class TestTransition:
    """Test Transition dataclass."""
    
    def test_default_transition(self):
        """Test default transition is cut."""
        from services.video_orchestrator.timeline_assembler import Transition, TransitionType
        
        trans = Transition()
        
        assert trans.type == TransitionType.CUT
        assert trans.duration_seconds == 0.5
    
    def test_crossfade_transition(self):
        """Test crossfade transition."""
        from services.video_orchestrator.timeline_assembler import Transition, TransitionType
        
        trans = Transition(type=TransitionType.CROSSFADE, duration_seconds=1.0)
        
        assert trans.type == TransitionType.CROSSFADE
        assert trans.duration_seconds == 1.0
    
    def test_to_dict(self):
        """Test transition serialization."""
        from services.video_orchestrator.timeline_assembler import Transition, TransitionType
        
        trans = Transition(type=TransitionType.FADE_BLACK, duration_seconds=0.75)
        data = trans.to_dict()
        
        assert data["type"] == "fade_black"
        assert data["duration_seconds"] == 0.75


class TestAudioTrack:
    """Test AudioTrack dataclass."""
    
    def test_default_audio_track(self):
        """Test audio track creation."""
        from services.video_orchestrator.timeline_assembler import AudioTrack, AudioTrackType
        
        track = AudioTrack(
            type=AudioTrackType.MUSIC,
            file_path="/path/to/music.mp3"
        )
        
        assert track.type == AudioTrackType.MUSIC
        assert track.volume == 1.0
        assert track.start_time == 0.0
    
    def test_audio_track_with_fades(self):
        """Test audio track with fades."""
        from services.video_orchestrator.timeline_assembler import AudioTrack, AudioTrackType
        
        track = AudioTrack(
            type=AudioTrackType.VOICEOVER,
            file_path="/path/to/vo.wav",
            volume=0.8,
            fade_in=0.5,
            fade_out=1.0
        )
        
        assert track.fade_in == 0.5
        assert track.fade_out == 1.0
    
    def test_to_dict(self):
        """Test audio track serialization."""
        from services.video_orchestrator.timeline_assembler import AudioTrack, AudioTrackType
        
        track = AudioTrack(
            type=AudioTrackType.SFX,
            file_path="/sfx.wav",
            volume=0.5,
            start_time=2.0
        )
        data = track.to_dict()
        
        assert data["type"] == "sfx"
        assert data["volume"] == 0.5
        assert data["start_time"] == 2.0


class TestClipSource:
    """Test ClipSource dataclass."""
    
    def test_clip_source_creation(self):
        """Test clip source creation."""
        from services.video_orchestrator.timeline_assembler import ClipSource
        
        clip = ClipSource(
            clip_id="clip_001",
            file_path="/clips/clip_001.mp4",
            duration=8.0,
            order=0
        )
        
        assert clip.clip_id == "clip_001"
        assert clip.duration == 8.0
        assert clip.order == 0
    
    def test_to_dict(self):
        """Test clip source serialization."""
        from services.video_orchestrator.timeline_assembler import ClipSource
        
        clip = ClipSource(
            clip_id="test",
            file_path="/test.mp4",
            duration=12.0,
            order=1,
            scene_id="scene_001"
        )
        data = clip.to_dict()
        
        assert data["clip_id"] == "test"
        assert data["scene_id"] == "scene_001"


# =============================================================================
# TIMELINE SPEC TESTS
# =============================================================================

class TestTimelineSpec:
    """Test TimelineSpec dataclass."""
    
    def test_empty_spec(self):
        """Test empty timeline spec."""
        from services.video_orchestrator.timeline_assembler import TimelineSpec
        
        spec = TimelineSpec(clips=[])
        
        assert spec.total_duration == 0.0
    
    def test_spec_with_clips(self):
        """Test spec with clips."""
        from services.video_orchestrator.timeline_assembler import TimelineSpec, ClipSource
        
        clips = [
            ClipSource(clip_id="1", file_path="/1.mp4", duration=8.0, order=0),
            ClipSource(clip_id="2", file_path="/2.mp4", duration=12.0, order=1),
            ClipSource(clip_id="3", file_path="/3.mp4", duration=8.0, order=2)
        ]
        
        spec = TimelineSpec(clips=clips)
        
        assert spec.total_duration == 28.0  # 8 + 12 + 8
    
    def test_spec_with_crossfade_transitions(self):
        """Test spec accounts for crossfade overlap."""
        from services.video_orchestrator.timeline_assembler import (
            TimelineSpec, ClipSource, Transition, TransitionType
        )
        
        clips = [
            ClipSource(clip_id="1", file_path="/1.mp4", duration=10.0, order=0),
            ClipSource(clip_id="2", file_path="/2.mp4", duration=10.0, order=1)
        ]
        
        transitions = [
            Transition(type=TransitionType.CROSSFADE, duration_seconds=2.0)
        ]
        
        spec = TimelineSpec(clips=clips, transitions=transitions)
        
        # 20s total - 1s overlap (half of 2s crossfade)
        assert spec.total_duration == 19.0
    
    def test_spec_default_resolution(self):
        """Test default resolution."""
        from services.video_orchestrator.timeline_assembler import TimelineSpec
        
        spec = TimelineSpec(clips=[])
        
        assert spec.output_resolution == (1920, 1080)
        assert spec.output_fps == 30
    
    def test_to_dict(self):
        """Test spec serialization."""
        from services.video_orchestrator.timeline_assembler import TimelineSpec, ClipSource
        
        clips = [ClipSource(clip_id="1", file_path="/1.mp4", duration=8.0, order=0)]
        spec = TimelineSpec(clips=clips)
        
        data = spec.to_dict()
        
        assert "clips" in data
        assert "transitions" in data
        assert "audio_tracks" in data
        assert data["output_fps"] == 30


# =============================================================================
# TIMELINE ASSEMBLER TESTS
# =============================================================================

class TestTimelineAssembler:
    """Test TimelineAssembler service."""
    
    @pytest.fixture
    def assembler(self):
        """Create assembler instance."""
        from services.video_orchestrator.timeline_assembler import TimelineAssembler
        return TimelineAssembler()
    
    def test_validate_empty_spec(self, assembler):
        """Test validation of empty spec."""
        from services.video_orchestrator.timeline_assembler import TimelineSpec
        
        spec = TimelineSpec(clips=[])
        valid, errors = assembler.validate_spec(spec)
        
        assert valid is False
        assert "No clips provided" in errors
    
    def test_validate_missing_file(self, assembler):
        """Test validation catches missing files."""
        from services.video_orchestrator.timeline_assembler import TimelineSpec, ClipSource
        
        spec = TimelineSpec(clips=[
            ClipSource(
                clip_id="1",
                file_path="/nonexistent/file.mp4",
                duration=8.0,
                order=0
            )
        ])
        
        valid, errors = assembler.validate_spec(spec)
        
        assert valid is False
        assert any("not found" in e for e in errors)
    
    def test_validate_too_many_transitions(self, assembler):
        """Test validation catches too many transitions."""
        from services.video_orchestrator.timeline_assembler import (
            TimelineSpec, ClipSource, Transition, TransitionType
        )
        
        spec = TimelineSpec(
            clips=[
                ClipSource(clip_id="1", file_path="/1.mp4", duration=8.0, order=0),
                ClipSource(clip_id="2", file_path="/2.mp4", duration=8.0, order=1)
            ],
            transitions=[
                Transition(type=TransitionType.CUT),
                Transition(type=TransitionType.CUT),
                Transition(type=TransitionType.CUT)  # Too many
            ]
        )
        
        valid, errors = assembler.validate_spec(spec)
        
        assert any("Too many transitions" in e for e in errors)
    
    def test_validate_exceeds_5_min(self, assembler):
        """Test validation catches duration exceeding 5 minutes."""
        from services.video_orchestrator.timeline_assembler import TimelineSpec, ClipSource
        
        # 6 clips of 60 seconds = 360 seconds (6 minutes)
        clips = [
            ClipSource(clip_id=str(i), file_path=f"/{i}.mp4", duration=60.0, order=i)
            for i in range(6)
        ]
        
        spec = TimelineSpec(clips=clips)
        
        valid, errors = assembler.validate_spec(spec)
        
        assert any("5 minute limit" in e for e in errors)
    
    def test_estimate_file_size(self, assembler):
        """Test file size estimation."""
        from services.video_orchestrator.timeline_assembler import TimelineSpec, ClipSource
        
        spec = TimelineSpec(
            clips=[ClipSource(clip_id="1", file_path="/1.mp4", duration=60.0, order=0)],
            output_resolution=(1920, 1080)
        )
        
        estimated = assembler.estimate_file_size(spec)
        
        # ~2MB/s for 1080p, so 60s should be ~120MB
        assert estimated > 100 * 1024 * 1024  # > 100MB
        assert estimated < 150 * 1024 * 1024  # < 150MB
    
    @pytest.mark.asyncio
    async def test_assemble_empty_spec(self, assembler):
        """Test assembling empty spec fails."""
        from services.video_orchestrator.timeline_assembler import TimelineSpec
        
        spec = TimelineSpec(clips=[])
        
        result = await assembler.assemble(spec)
        
        assert result.success is False
        assert "No clips" in result.error
    
    @pytest.mark.asyncio
    async def test_simulate_render(self, assembler):
        """Test simulated render (when MoviePy not available)."""
        from services.video_orchestrator.timeline_assembler import TimelineSpec, ClipSource
        
        # Create temp file to simulate clip
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            temp_clip = f.name
        
        try:
            spec = TimelineSpec(
                clips=[ClipSource(clip_id="1", file_path=temp_clip, duration=8.0, order=0)]
            )
            
            # Force simulation mode
            assembler._moviepy_available = False
            
            result = await assembler.assemble(spec)
            
            assert result.success is True
            assert result.output_path is not None
            assert result.duration_seconds == 8.0
            
            # Cleanup output
            if os.path.exists(result.output_path):
                os.unlink(result.output_path)
                
        finally:
            os.unlink(temp_clip)


# =============================================================================
# TIMELINE BUILDER TESTS
# =============================================================================

class TestTimelineBuilder:
    """Test TimelineBuilder."""
    
    def test_add_clip(self):
        """Test adding clips."""
        from services.video_orchestrator.timeline_assembler import TimelineBuilder
        
        builder = TimelineBuilder()
        
        builder.add_clip("clip1", "/clip1.mp4", duration=8.0)
        builder.add_clip("clip2", "/clip2.mp4", duration=12.0)
        
        spec = builder.build()
        
        assert len(spec.clips) == 2
        assert spec.clips[0].clip_id == "clip1"
        assert spec.clips[1].clip_id == "clip2"
    
    def test_add_transition(self):
        """Test adding transitions."""
        from services.video_orchestrator.timeline_assembler import (
            TimelineBuilder, TransitionType
        )
        
        builder = TimelineBuilder()
        
        builder.add_clip("clip1", "/clip1.mp4", duration=8.0)
        builder.add_transition(TransitionType.CROSSFADE, duration=1.0)
        builder.add_clip("clip2", "/clip2.mp4", duration=8.0)
        
        spec = builder.build()
        
        assert len(spec.transitions) == 1
        assert spec.transitions[0].type == TransitionType.CROSSFADE
    
    def test_add_voiceover(self):
        """Test adding voiceover."""
        from services.video_orchestrator.timeline_assembler import TimelineBuilder, AudioTrackType
        
        builder = TimelineBuilder()
        
        builder.add_voiceover("/vo.wav", volume=0.9)
        
        spec = builder.build()
        
        assert len(spec.audio_tracks) == 1
        assert spec.audio_tracks[0].type == AudioTrackType.VOICEOVER
    
    def test_add_music(self):
        """Test adding music."""
        from services.video_orchestrator.timeline_assembler import TimelineBuilder, AudioTrackType
        
        builder = TimelineBuilder()
        
        builder.add_music("/music.mp3", volume=0.3, fade_in=2.0, fade_out=3.0)
        
        spec = builder.build()
        
        assert len(spec.audio_tracks) == 1
        assert spec.audio_tracks[0].type == AudioTrackType.MUSIC
        assert spec.audio_tracks[0].fade_in == 2.0
    
    def test_set_resolution(self):
        """Test setting resolution."""
        from services.video_orchestrator.timeline_assembler import TimelineBuilder
        
        builder = TimelineBuilder()
        
        builder.set_resolution(1280, 720)
        
        spec = builder.build()
        
        assert spec.output_resolution == (1280, 720)
    
    def test_set_fps(self):
        """Test setting FPS."""
        from services.video_orchestrator.timeline_assembler import TimelineBuilder
        
        builder = TimelineBuilder()
        
        builder.set_fps(60)
        
        spec = builder.build()
        
        assert spec.output_fps == 60
    
    def test_fluent_api(self):
        """Test fluent API chaining."""
        from services.video_orchestrator.timeline_assembler import (
            TimelineBuilder, TransitionType
        )
        
        builder = TimelineBuilder()
        
        spec = (builder
            .add_clip("1", "/1.mp4", 8.0)
            .add_transition(TransitionType.CROSSFADE, 0.5)
            .add_clip("2", "/2.mp4", 8.0)
            .add_music("/bg.mp3", volume=0.2)
            .set_resolution(1920, 1080)
            .set_fps(30)
            .build())
        
        assert len(spec.clips) == 2
        assert len(spec.transitions) == 1
        assert len(spec.audio_tracks) == 1
    
    def test_reset(self):
        """Test reset clears builder state."""
        from services.video_orchestrator.timeline_assembler import TimelineBuilder
        
        builder = TimelineBuilder()
        
        builder.add_clip("1", "/1.mp4", 8.0)
        builder.add_music("/music.mp3")
        builder.reset()
        
        spec = builder.build()
        
        assert len(spec.clips) == 0
        assert len(spec.audio_tracks) == 0


# =============================================================================
# RENDER RESULT TESTS
# =============================================================================

class TestRenderResult:
    """Test RenderResult dataclass."""
    
    def test_success_result(self):
        """Test successful render result."""
        from services.video_orchestrator.timeline_assembler import RenderResult
        
        result = RenderResult(
            success=True,
            output_path="/output/video.mp4",
            duration_seconds=60.0,
            file_size_bytes=50_000_000,
            render_time_seconds=30.0
        )
        
        assert result.success is True
        assert result.error is None
    
    def test_failure_result(self):
        """Test failed render result."""
        from services.video_orchestrator.timeline_assembler import RenderResult
        
        result = RenderResult(
            success=False,
            error="MoviePy failed to process clip"
        )
        
        assert result.success is False
        assert "MoviePy" in result.error
    
    def test_to_dict(self):
        """Test render result serialization."""
        from services.video_orchestrator.timeline_assembler import RenderResult
        
        result = RenderResult(
            success=True,
            output_path="/out.mp4",
            duration_seconds=30.0,
            file_size_bytes=25_000_000
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["output_path"] == "/out.mp4"
        assert data["duration_seconds"] == 30.0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestTimelineIntegration:
    """Integration tests for timeline assembly."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self):
        """Test full assembly workflow with simulation."""
        from services.video_orchestrator.timeline_assembler import (
            TimelineAssembler, TimelineBuilder, TransitionType
        )
        
        # Create temp files to simulate clips
        temp_clips = []
        for i in range(3):
            f = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            f.write(b"fake video " + str(i).encode())
            f.close()
            temp_clips.append(f.name)
        
        try:
            assembler = TimelineAssembler()
            assembler._moviepy_available = False  # Force simulation
            
            builder = TimelineBuilder(assembler)
            
            spec = (builder
                .add_clip("clip1", temp_clips[0], duration=8.0)
                .add_transition(TransitionType.CROSSFADE, 0.5)
                .add_clip("clip2", temp_clips[1], duration=12.0)
                .add_transition(TransitionType.CUT)
                .add_clip("clip3", temp_clips[2], duration=8.0)
                .set_resolution(1920, 1080)
                .build())
            
            # Validate
            valid, errors = assembler.validate_spec(spec)
            assert valid is True, f"Validation failed: {errors}"
            
            # Assemble
            result = await assembler.assemble(spec)
            
            assert result.success is True
            assert result.output_path is not None
            assert result.duration_seconds > 0
            
            # Cleanup
            if os.path.exists(result.output_path):
                os.unlink(result.output_path)
                
        finally:
            for path in temp_clips:
                if os.path.exists(path):
                    os.unlink(path)


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
