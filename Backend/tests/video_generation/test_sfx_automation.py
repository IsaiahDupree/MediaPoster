"""
Unit tests for SFX automation.

Tests:
- SFX cue generation from visual reveals
- Macro expansion
- SFX layer creation
- Remotion SFX integration
"""

import pytest

# Import with fallbacks
try:
    from services.video_generation.remotion_sfx import (
        RemotionSfxCue,
        story_ir_to_remotion_sfx_cues,
        expand_remotion_sfx_cues,
        add_sfx_layers_to_render_plan,
        get_sfx_for_action,
    )
    HAS_REMOTION_SFX = True
except ImportError:
    HAS_REMOTION_SFX = False
    RemotionSfxCue = None

try:
    from services.video_generation.remotion_time_events import (
        story_ir_to_time_events,
        reveals_to_sfx_cues,
        TimeEvents,
        VisualReveal,
    )
    HAS_TIME_EVENTS = True
except ImportError:
    HAS_TIME_EVENTS = False
    TimeEvents = None
    VisualReveal = None


@pytest.mark.skipif(not HAS_REMOTION_SFX, reason="remotion_sfx not implemented")
class TestSfxCueGeneration:
    """Tests for SFX cue generation."""
    
    @pytest.fixture
    def sample_story_ir(self) -> dict:
        return {
            "meta": {"fps": 30, "aspect": "9:16"},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "duration_s": 2.5, "narration": "Hook"},
                {"id": "beat_2", "type": "REVEAL", "duration_s": 4.0, "narration": "Reveal"},
                {"id": "beat_3", "type": "CTA", "duration_s": 3.0, "narration": "CTA"},
            ],
        }
    
    def test_story_ir_to_sfx_cues_returns_list(self, sample_story_ir):
        """Should return list of SFX cues."""
        cues = story_ir_to_remotion_sfx_cues(sample_story_ir, fps=30)
        
        assert cues is not None
        assert isinstance(cues, list)
    
    def test_sfx_cues_have_required_fields(self, sample_story_ir):
        """Each cue should have required fields."""
        cues = story_ir_to_remotion_sfx_cues(sample_story_ir, fps=30)
        
        for cue in cues:
            assert hasattr(cue, 'frame') or 'frame' in cue
            assert hasattr(cue, 'sfx_id') or 'sfxId' in cue
    
    def test_hook_beat_gets_whoosh(self, sample_story_ir):
        """HOOK beat should get whoosh SFX."""
        cues = story_ir_to_remotion_sfx_cues(sample_story_ir, fps=30)
        
        # Find cue for frame 0 (hook)
        hook_cues = [c for c in cues if c.frame == 0]
        
        assert len(hook_cues) > 0
        assert any("whoosh" in c.sfx_id.lower() for c in hook_cues)
    
    def test_reveal_beat_gets_reveal_sfx(self, sample_story_ir):
        """REVEAL beat should get reveal SFX."""
        cues = story_ir_to_remotion_sfx_cues(sample_story_ir, fps=30)
        
        # Calculate reveal beat frame (after hook)
        reveal_frame = int(2.5 * 30)  # HOOK is 2.5s at 30fps
        
        reveal_cues = [c for c in cues if c.frame == reveal_frame]
        
        assert len(reveal_cues) > 0


@pytest.mark.skipif(not HAS_REMOTION_SFX, reason="remotion_sfx not implemented")
class TestSfxMacroExpansion:
    """Tests for SFX macro expansion."""
    
    def test_expand_cues_returns_list(self):
        """Should return expanded cue list."""
        cues = [
            RemotionSfxCue(frame=0, sfx_id="whoosh_fast", volume=1.0),
            RemotionSfxCue(frame=90, sfx_id="reveal_chime", volume=0.8),
        ]
        
        expanded = expand_remotion_sfx_cues(cues)
        
        assert expanded is not None
        assert isinstance(expanded, list)
    
    def test_macro_expansion_resolves_ids(self):
        """Macro expansion should resolve SFX IDs."""
        cues = [
            RemotionSfxCue(frame=0, sfx_id="@HOOK", volume=1.0),
        ]
        
        expanded = expand_remotion_sfx_cues(cues)
        
        # @HOOK macro should resolve to actual SFX ID
        assert len(expanded) > 0
        assert not expanded[0].sfx_id.startswith("@")


@pytest.mark.skipif(not HAS_REMOTION_SFX, reason="remotion_sfx not implemented")
class TestSfxLayerCreation:
    """Tests for SFX layer creation in render plan."""
    
    @pytest.fixture
    def sample_render_plan(self) -> dict:
        return {
            "version": "2.0.0",
            "fps": 30,
            "width": 1080,
            "height": 1920,
            "durationInFrames": 300,
            "layers": [
                {"id": "bg_1", "kind": "VIDEO", "from": 0, "durationInFrames": 300},
            ],
        }
    
    def test_add_sfx_layers_returns_plan(self, sample_render_plan):
        """Should return updated render plan."""
        cues = [
            RemotionSfxCue(frame=0, sfx_id="whoosh", volume=1.0),
        ]
        
        result = add_sfx_layers_to_render_plan(sample_render_plan, cues)
        
        assert result is not None
        assert "layers" in result
    
    def test_sfx_layers_added_to_plan(self, sample_render_plan):
        """SFX layers should be added to render plan."""
        cues = [
            RemotionSfxCue(frame=0, sfx_id="whoosh", volume=1.0),
            RemotionSfxCue(frame=90, sfx_id="reveal", volume=0.8),
        ]
        
        result = add_sfx_layers_to_render_plan(sample_render_plan, cues)
        
        audio_layers = [l for l in result["layers"] if l.get("kind") == "AUDIO"]
        assert len(audio_layers) >= len(cues)
    
    def test_sfx_layers_have_correct_timing(self, sample_render_plan):
        """SFX layers should have correct timing."""
        cues = [
            RemotionSfxCue(frame=45, sfx_id="whoosh", volume=1.0),
        ]
        
        result = add_sfx_layers_to_render_plan(sample_render_plan, cues)
        
        audio_layers = [l for l in result["layers"] if l.get("kind") == "AUDIO"]
        
        # Should have layer starting at frame 45
        assert any(l.get("from") == 45 for l in audio_layers)


@pytest.mark.skipif(not HAS_REMOTION_SFX, reason="remotion_sfx not implemented")
class TestSfxForAction:
    """Tests for action → SFX mapping."""
    
    def test_hook_action_returns_sfx(self):
        """HOOK action should return SFX IDs."""
        sfx = get_sfx_for_action("hook")
        
        assert sfx is not None
        assert len(sfx) > 0
    
    def test_reveal_action_returns_sfx(self):
        """REVEAL action should return SFX IDs."""
        sfx = get_sfx_for_action("reveal")
        
        assert sfx is not None
        assert len(sfx) > 0
    
    def test_cta_action_returns_sfx(self):
        """CTA action should return SFX IDs."""
        sfx = get_sfx_for_action("cta")
        
        assert sfx is not None
        assert len(sfx) > 0
    
    def test_unknown_action_returns_empty(self):
        """Unknown action should return empty list."""
        sfx = get_sfx_for_action("unknown_action")
        
        assert sfx == [] or sfx is None


@pytest.mark.skipif(not HAS_TIME_EVENTS, reason="remotion_time_events not implemented")
class TestTimeEventsGeneration:
    """Tests for time events generation."""
    
    @pytest.fixture
    def sample_story_ir(self) -> dict:
        return {
            "meta": {"fps": 30, "aspect": "9:16"},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "duration_s": 2.5, "narration": "Hook"},
                {"id": "beat_2", "type": "STEP", "duration_s": 5.0, "narration": "Step"},
            ],
        }
    
    def test_story_ir_to_time_events_returns_events(self, sample_story_ir):
        """Should return TimeEvents object."""
        events = story_ir_to_time_events(sample_story_ir, fps=30)
        
        assert events is not None
        assert isinstance(events, TimeEvents)
    
    def test_time_events_has_events_list(self, sample_story_ir):
        """TimeEvents should have events list."""
        events = story_ir_to_time_events(sample_story_ir, fps=30)
        
        assert hasattr(events, 'events')
        assert len(events.events) > 0
    
    def test_time_events_has_reveals(self, sample_story_ir):
        """TimeEvents should track reveals."""
        events = story_ir_to_time_events(sample_story_ir, fps=30)
        
        assert hasattr(events, 'reveals')


@pytest.mark.skipif(not HAS_TIME_EVENTS, reason="remotion_time_events not implemented")
class TestRevealsToSfxCues:
    """Tests for reveals → SFX cue conversion."""
    
    def test_reveals_to_sfx_cues_returns_list(self):
        """Should return list of SFX cues."""
        reveals = [
            VisualReveal(frame=0, reveal_type="text", element_id="title_1"),
            VisualReveal(frame=90, reveal_type="image", element_id="img_1"),
        ]
        
        cues = reveals_to_sfx_cues(reveals)
        
        assert cues is not None
        assert isinstance(cues, list)
    
    def test_each_reveal_gets_cue(self):
        """Each reveal should get an SFX cue."""
        reveals = [
            VisualReveal(frame=0, reveal_type="text", element_id="title_1"),
            VisualReveal(frame=90, reveal_type="text", element_id="title_2"),
        ]
        
        cues = reveals_to_sfx_cues(reveals)
        
        # Should have at least as many cues as reveals
        assert len(cues) >= len(reveals)
