"""
Unit tests for RemotionSpecService - Remotion render spec generation
"""
import pytest
from unittest.mock import Mock, patch
from dataclasses import asdict

from services.content_pipeline.remotion_spec_service import (
    RemotionSpecService,
    RemotionRenderSpecV1,
    CaptionSegment,
    Beat,
    TimelineEvent,
    AudioSpec,
    CaptionsSpec,
    ExportSpec,
)


class TestCaptionSegment:
    """Tests for CaptionSegment dataclass"""
    
    def test_segment_basic(self):
        """Basic caption segment"""
        segment = CaptionSegment(
            start_sec=0.0,
            end_sec=2.5,
            text="Hello world"
        )
        assert segment.start_sec == 0.0
        assert segment.end_sec == 2.5
        assert segment.text == "Hello world"
        assert segment.emphasis == []
    
    def test_segment_with_emphasis(self):
        """Caption segment with emphasized words"""
        segment = CaptionSegment(
            start_sec=0.0,
            end_sec=2.5,
            text="Stop scrolling right now",
            emphasis=["Stop", "now"]
        )
        assert segment.emphasis == ["Stop", "now"]


class TestBeat:
    """Tests for Beat dataclass"""
    
    def test_beat_required_fields(self):
        """Beat with required fields"""
        beat = Beat(
            beat_id="b1",
            start_sec=0,
            end_sec=3,
            role="hook",
            summary="Attention-grabbing opening"
        )
        assert beat.beat_id == "b1"
        assert beat.role == "hook"
        assert beat.emotion is None
    
    def test_beat_with_emotion(self):
        """Beat with emotion"""
        beat = Beat(
            beat_id="b2",
            start_sec=3,
            end_sec=15,
            role="problem",
            summary="Presents the challenge",
            emotion="frustration"
        )
        assert beat.emotion == "frustration"


class TestTimelineEvent:
    """Tests for TimelineEvent dataclass"""
    
    def test_background_video_event(self):
        """Background video timeline event"""
        event = TimelineEvent(
            start_sec=0,
            end_sec=60,
            type="background_video",
            src="https://example.com/video.mp4"
        )
        assert event.type == "background_video"
        assert event.src is not None
    
    def test_captions_event(self):
        """Captions timeline event"""
        event = TimelineEvent(
            start_sec=0,
            end_sec=60,
            type="captions",
            preset="CaptionStyleA"
        )
        assert event.type == "captions"
        assert event.preset == "CaptionStyleA"
    
    def test_music_event_with_params(self):
        """Music timeline event with parameters"""
        event = TimelineEvent(
            start_sec=0,
            end_sec=60,
            type="music",
            src="https://example.com/music.mp3",
            params={"gain_db": -12}
        )
        assert event.params["gain_db"] == -12


class TestRemotionSpecService:
    """Tests for RemotionSpecService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        with patch.object(RemotionSpecService, '__init__', lambda x: None):
            service = RemotionSpecService()
            service.engine = Mock()
            return service
    
    def test_words_to_caption_segments_basic(self, service):
        """Convert words to caption segments"""
        words = [
            {"w": "Hello", "start": 0.0, "end": 0.5},
            {"w": "world", "start": 0.5, "end": 1.0},
            {"w": "this", "start": 1.0, "end": 1.3},
            {"w": "is", "start": 1.3, "end": 1.5},
            {"w": "a", "start": 1.5, "end": 1.6},
            {"w": "test", "start": 1.6, "end": 2.0},
        ]
        
        segments = service.words_to_caption_segments(words, max_words_per_segment=3)
        
        assert len(segments) == 2
        assert segments[0].text == "Hello world this"
        assert segments[0].start_sec == 0.0
        assert segments[1].text == "is a test"
    
    def test_words_to_caption_segments_empty(self, service):
        """Empty words list returns empty segments"""
        segments = service.words_to_caption_segments([], max_words_per_segment=6)
        assert segments == []
    
    def test_words_to_caption_segments_single_word(self, service):
        """Single word creates one segment"""
        words = [{"w": "Hello", "start": 0.0, "end": 0.5}]
        segments = service.words_to_caption_segments(words, max_words_per_segment=6)
        
        assert len(segments) == 1
        assert segments[0].text == "Hello"
    
    def test_scene_structure_to_beats(self, service):
        """Convert scene structure to beats"""
        scene_structure = [
            {"start_sec": 0, "end_sec": 3, "role": "hook", "summary": "Opening hook"},
            {"start_sec": 3, "end_sec": 15, "role": "problem", "summary": "The problem"},
            {"start_sec": 15, "end_sec": 25, "role": "solution", "summary": "The solution"},
            {"start_sec": 25, "end_sec": 30, "role": "cta", "summary": "Call to action"},
        ]
        
        beats = service.scene_structure_to_beats(scene_structure)
        
        assert len(beats) == 4
        assert beats[0].role == "hook"
        assert beats[0].beat_id == "b1"
        assert beats[3].role == "cta"
    
    def test_scene_structure_with_beat_ids(self, service):
        """Scene structure with existing beat IDs"""
        scene_structure = [
            {"beat_id": "custom_id", "start_sec": 0, "end_sec": 3, "role": "hook", "summary": "Hook"}
        ]
        
        beats = service.scene_structure_to_beats(scene_structure)
        
        assert beats[0].beat_id == "custom_id"
    
    def test_build_from_deep_audit_basic(self, service):
        """Build spec from basic deep audit data"""
        deep_audit_data = {
            "source_video_url": "https://example.com/video.mp4"
        }
        
        spec = service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data=deep_audit_data
        )
        
        assert spec.schema == "remotion_render_spec_v1"
        assert spec.composition_id == "ShortFormV1"
        assert spec.fps == 30
        assert spec.width == 1080
        assert spec.height == 1920
        assert spec.duration_in_frames == 900  # 30 * 30
    
    def test_build_from_deep_audit_with_words(self, service):
        """Build spec from audit with transcript words"""
        deep_audit_data = {
            "transcript": {
                "words": [
                    {"w": "Hello", "start": 0.0, "end": 0.5},
                    {"w": "world", "start": 0.5, "end": 1.0},
                ]
            }
        }
        
        spec = service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data=deep_audit_data
        )
        
        assert spec.captions is not None
        assert len(spec.captions.segments) >= 1
    
    def test_build_from_deep_audit_with_scene_structure(self, service):
        """Build spec from audit with scene structure"""
        deep_audit_data = {
            "scene_structure": [
                {"start_sec": 0, "end_sec": 10, "role": "hook", "summary": "Hook"},
                {"start_sec": 10, "end_sec": 30, "role": "solution", "summary": "Content"},
            ]
        }
        
        spec = service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data=deep_audit_data
        )
        
        assert len(spec.beats) == 2
        assert spec.beats[0].role == "hook"
    
    def test_build_from_deep_audit_with_audio(self, service):
        """Build spec with narration and music"""
        deep_audit_data = {}
        
        spec = service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data=deep_audit_data,
            narration_url="https://example.com/narration.mp3",
            music_url="https://example.com/music.mp3"
        )
        
        assert spec.audio is not None
        assert spec.audio.narration_url == "https://example.com/narration.mp3"
        assert spec.audio.music_url == "https://example.com/music.mp3"
        assert len(spec.audio.ducking) > 0  # Ducking when both present
    
    def test_build_timeline_with_video(self, service):
        """Build timeline with background video"""
        timeline = service._build_timeline(
            duration_sec=30,
            source_video_url="https://example.com/video.mp4"
        )
        
        assert any(e.type == "background_video" for e in timeline)
        bg_event = next(e for e in timeline if e.type == "background_video")
        assert bg_event.src == "https://example.com/video.mp4"
    
    def test_build_timeline_with_captions(self, service):
        """Build timeline with captions layer"""
        timeline = service._build_timeline(
            duration_sec=30,
            has_captions=True,
            caption_style_id="CaptionStyleB"
        )
        
        assert any(e.type == "captions" for e in timeline)
        caption_event = next(e for e in timeline if e.type == "captions")
        assert caption_event.preset == "CaptionStyleB"
    
    def test_build_timeline_with_music(self, service):
        """Build timeline with music layer"""
        timeline = service._build_timeline(
            duration_sec=30,
            music_url="https://example.com/music.mp3"
        )
        
        assert any(e.type == "music" for e in timeline)
        music_event = next(e for e in timeline if e.type == "music")
        assert music_event.src == "https://example.com/music.mp3"
        assert music_event.params.get("gain_db") == -12
    
    def test_to_remotion_input_props(self, service):
        """Convert spec to Remotion inputProps"""
        spec = RemotionRenderSpecV1(
            composition_id="ShortFormV1",
            fps=30,
            width=1080,
            height=1920,
            duration_in_frames=900,
            timeline=[]
        )
        
        props = service.to_remotion_input_props(spec)
        
        # Python dataclass uses snake_case
        assert props["composition_id"] == "ShortFormV1"
        assert props["fps"] == 30
    
    def test_get_composition_presets(self, service):
        """Get available composition presets"""
        presets = service.get_composition_presets()
        
        assert "ShortFormV1" in presets
        assert presets["ShortFormV1"]["fps"] == 30
        assert presets["ShortFormV1"]["width"] == 1080
        assert presets["ShortFormV1"]["height"] == 1920
    
    def test_get_caption_styles(self, service):
        """Get available caption styles"""
        styles = service.get_caption_styles()
        
        assert "CaptionStyleA" in styles
        assert "CaptionStyleB" in styles


class TestRemotionRenderSpecV1:
    """Tests for RemotionRenderSpecV1 dataclass"""
    
    def test_spec_defaults(self):
        """Default values"""
        spec = RemotionRenderSpecV1()
        
        assert spec.schema == "remotion_render_spec_v1"
        assert spec.composition_id == "ShortFormV1"
        assert spec.fps == 30
        assert spec.width == 1080
        assert spec.height == 1920
    
    def test_spec_with_all_fields(self):
        """Spec with all optional fields"""
        spec = RemotionRenderSpecV1(
            composition_id="LongFormV1",
            fps=60,
            width=1920,
            height=1080,
            duration_in_frames=1800,
            audio=AudioSpec(narration_url="test.mp3"),
            captions=CaptionsSpec(style_id="CaptionStyleA", segments=[]),
            beats=[Beat(beat_id="b1", start_sec=0, end_sec=10, role="hook", summary="Hook")],
            timeline=[TimelineEvent(start_sec=0, end_sec=60, type="background_video")],
            export=ExportSpec(format="mp4", crf=18)
        )
        
        assert spec.composition_id == "LongFormV1"
        assert spec.fps == 60
        assert spec.audio.narration_url == "test.mp3"
        assert len(spec.beats) == 1
    
    def test_spec_to_dict(self):
        """Spec can be converted to dict"""
        spec = RemotionRenderSpecV1(
            duration_in_frames=900,
            timeline=[]
        )
        
        spec_dict = asdict(spec)
        
        assert spec_dict["schema"] == "remotion_render_spec_v1"
        assert spec_dict["duration_in_frames"] == 900


class TestCompositionPresets:
    """Tests for composition presets"""
    
    @pytest.fixture
    def service(self):
        with patch.object(RemotionSpecService, '__init__', lambda x: None):
            service = RemotionSpecService()
            service.engine = Mock()
            return service
    
    def test_short_form_preset(self, service):
        """ShortFormV1 preset for vertical video"""
        spec = service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data={}
        )
        
        assert spec.width == 1080
        assert spec.height == 1920
        assert spec.fps == 30
    
    def test_long_form_preset(self, service):
        """LongFormV1 preset for horizontal video"""
        spec = service.build_from_deep_audit(
            composition_id="LongFormV1",
            duration_sec=300,
            deep_audit_data={}
        )
        
        assert spec.width == 1920
        assert spec.height == 1080
    
    def test_square_preset(self, service):
        """SquareV1 preset for 1:1 video"""
        spec = service.build_from_deep_audit(
            composition_id="SquareV1",
            duration_sec=60,
            deep_audit_data={}
        )
        
        assert spec.width == 1080
        assert spec.height == 1080
    
    def test_custom_dimensions_override(self, service):
        """Custom dimensions override preset"""
        spec = service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data={},
            fps=60,
            width=720,
            height=1280
        )
        
        assert spec.fps == 60
        assert spec.width == 720
        assert spec.height == 1280


class TestEdgeCases:
    """Edge case tests"""
    
    @pytest.fixture
    def service(self):
        with patch.object(RemotionSpecService, '__init__', lambda x: None):
            service = RemotionSpecService()
            service.engine = Mock()
            return service
    
    def test_empty_deep_audit_data(self, service):
        """Handle empty deep audit data"""
        spec = service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data={}
        )
        
        assert spec is not None
        assert spec.captions is None
        assert spec.beats == []
    
    def test_very_long_video(self, service):
        """Handle very long video"""
        spec = service.build_from_deep_audit(
            composition_id="LongFormV1",
            duration_sec=3600,  # 1 hour
            deep_audit_data={}
        )
        
        assert spec.duration_in_frames == 108000  # 3600 * 30
    
    def test_words_with_missing_fields(self, service):
        """Handle words with missing fields"""
        words = [
            {"w": "Hello"},  # Missing start/end
            {"word": "world", "start": 0.5, "end": 1.0},  # Different key
        ]
        
        segments = service.words_to_caption_segments(words, max_words_per_segment=6)
        # Should handle gracefully
        assert isinstance(segments, list)
