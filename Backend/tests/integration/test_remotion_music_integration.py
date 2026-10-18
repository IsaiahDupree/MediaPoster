"""
Integration tests for Remotion music integration.
Tests the ability to populate media with music using RemotionRenderSpec.
"""
import pytest
import os
from unittest.mock import patch, Mock, AsyncMock
from pathlib import Path

# Set up test environment
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


class TestRemotionMusicIntegration:
    """Tests for integrating music with Remotion render specs"""
    
    @pytest.fixture
    def remotion_service(self):
        """Create RemotionSpecService instance"""
        from services.content_pipeline.remotion_spec_service import RemotionSpecService
        with patch.object(RemotionSpecService, '__init__', lambda x: None):
            service = RemotionSpecService()
            service.engine = Mock()
            return service
    
    @pytest.fixture
    def sample_deep_audit_data(self):
        """Sample deep audit data with transcript"""
        return {
            "transcript": {
                "words": [
                    {"w": "Welcome", "start": 0.0, "end": 0.5},
                    {"w": "to", "start": 0.5, "end": 0.7},
                    {"w": "my", "start": 0.7, "end": 0.9},
                    {"w": "video", "start": 0.9, "end": 1.3},
                    {"w": "today", "start": 1.5, "end": 2.0},
                    {"w": "we", "start": 2.0, "end": 2.2},
                    {"w": "talk", "start": 2.2, "end": 2.5},
                    {"w": "about", "start": 2.5, "end": 2.8},
                    {"w": "productivity", "start": 2.8, "end": 3.5},
                ]
            },
            "scene_structure": [
                {"start_sec": 0, "end_sec": 3, "role": "hook", "summary": "Opening hook"},
                {"start_sec": 3, "end_sec": 25, "role": "solution", "summary": "Main content"},
                {"start_sec": 25, "end_sec": 30, "role": "cta", "summary": "Call to action"}
            ],
            "source_video_url": "/path/to/source/video.mp4"
        }
    
    def test_build_spec_with_music_url(self, remotion_service, sample_deep_audit_data):
        """Build Remotion spec with background music URL"""
        spec = remotion_service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data=sample_deep_audit_data,
            music_url="https://example.com/music/track.mp3"
        )
        
        assert spec is not None
        assert spec.audio is not None
        assert spec.audio.music_url == "https://example.com/music/track.mp3"
        
        # Check timeline has music layer
        music_events = [e for e in spec.timeline if e.type == "music"]
        assert len(music_events) == 1
        assert music_events[0].src == "https://example.com/music/track.mp3"
    
    def test_build_spec_with_narration_and_music(self, remotion_service, sample_deep_audit_data):
        """Build spec with both narration and music (should include ducking)"""
        spec = remotion_service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data=sample_deep_audit_data,
            narration_url="https://example.com/narration.mp3",
            music_url="https://example.com/music.mp3"
        )
        
        assert spec.audio is not None
        assert spec.audio.narration_url == "https://example.com/narration.mp3"
        assert spec.audio.music_url == "https://example.com/music.mp3"
        
        # When both narration and music, ducking should be configured
        assert len(spec.audio.ducking) > 0
        assert spec.audio.ducking[0]["amount_db"] == 10
    
    def test_build_spec_with_local_music_path(self, remotion_service, sample_deep_audit_data):
        """Build spec with local music file path"""
        local_music_path = "/data/music/instagram/track123.mp3"
        
        spec = remotion_service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data=sample_deep_audit_data,
            music_url=f"file://{local_music_path}"
        )
        
        assert spec.audio.music_url == f"file://{local_music_path}"
    
    def test_timeline_music_layer_params(self, remotion_service, sample_deep_audit_data):
        """Music layer should have proper gain parameters"""
        spec = remotion_service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data=sample_deep_audit_data,
            music_url="https://example.com/music.mp3"
        )
        
        music_events = [e for e in spec.timeline if e.type == "music"]
        assert len(music_events) == 1
        
        # Default music should be ducked (-12dB)
        assert music_events[0].params.get("gain_db") == -12
    
    def test_spec_duration_matches_music(self, remotion_service, sample_deep_audit_data):
        """Spec duration should account for music"""
        duration = 45  # 45 seconds
        
        spec = remotion_service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=duration,
            deep_audit_data=sample_deep_audit_data,
            music_url="https://example.com/music.mp3"
        )
        
        # Music should span full duration
        music_events = [e for e in spec.timeline if e.type == "music"]
        assert music_events[0].start_sec == 0
        assert music_events[0].end_sec == duration
        
        # Total frames should match
        assert spec.duration_in_frames == duration * spec.fps
    
    def test_captions_and_music_layers_coexist(self, remotion_service, sample_deep_audit_data):
        """Captions and music layers should both be in timeline"""
        spec = remotion_service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data=sample_deep_audit_data,
            music_url="https://example.com/music.mp3",
            caption_style_id="CaptionStyleA"
        )
        
        # Should have both layers
        layer_types = [e.type for e in spec.timeline]
        assert "music" in layer_types
        assert "captions" in layer_types
        
        # Captions should have correct style
        caption_events = [e for e in spec.timeline if e.type == "captions"]
        assert caption_events[0].preset == "CaptionStyleA"
    
    def test_to_remotion_input_props_includes_audio(self, remotion_service, sample_deep_audit_data):
        """Input props should include audio configuration"""
        spec = remotion_service.build_from_deep_audit(
            composition_id="ShortFormV1",
            duration_sec=30,
            deep_audit_data=sample_deep_audit_data,
            narration_url="https://example.com/narration.mp3",
            music_url="https://example.com/music.mp3"
        )
        
        props = remotion_service.to_remotion_input_props(spec)
        
        assert "audio" in props
        assert props["audio"]["narration_url"] == "https://example.com/narration.mp3"
        assert props["audio"]["music_url"] == "https://example.com/music.mp3"


class TestMusicServiceIntegration:
    """Tests for music service integration"""
    
    @pytest.fixture
    def music_search_criteria(self):
        """Sample music search criteria"""
        from services.music.models import MusicSearchCriteria
        return MusicSearchCriteria(
            genre="electronic",
            mood="energetic",
            duration_min=20,
            duration_max=60
        )
    
    @pytest.mark.asyncio
    async def test_suno_adapter_search(self):
        """Test Suno adapter can search local files"""
        from services.music.adapters.suno import SunoAdapter
        
        # Use test directory
        adapter = SunoAdapter(suno_dir="data/suno_test")
        
        from services.music.models import MusicSearchCriteria
        criteria = MusicSearchCriteria(genre="electronic")
        
        results = await adapter.search_music(criteria, limit=5)
        
        # Should return list (may be empty if no files)
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_soundcloud_adapter_requires_key(self):
        """Test SoundCloud adapter requires API key"""
        from services.music.adapters.soundcloud import SoundCloudAdapter
        
        # Without API key
        adapter = SoundCloudAdapter(rapidapi_key=None)
        
        from services.music.models import MusicSearchCriteria
        criteria = MusicSearchCriteria()
        
        results = await adapter.search_music(criteria, limit=5)
        
        # Should return empty without API key
        assert results == []


class TestInstagramMusicCrawlerUnit:
    """Unit tests for Instagram music crawler (no external deps)"""
    
    @pytest.mark.skip(reason="Requires aiofiles - install with pip install aiofiles")
    def test_rate_limiter_class(self):
        """Test RateLimiter class directly"""
        from services.music.crawlers.instagram_music_crawler import RateLimiter
        
        limiter = RateLimiter(calls_per_minute=5, calls_per_day=100)
        
        assert limiter.calls_per_minute == 5
        assert limiter.calls_per_day == 100
    
    @pytest.mark.skip(reason="Requires aiofiles - install with pip install aiofiles")
    def test_instagram_track_dataclass(self):
        """Test InstagramTrack dataclass"""
        from services.music.crawlers.instagram_music_crawler import InstagramTrack
        
        track = InstagramTrack(
            track_id="123",
            title="Test Song",
            artist="Test Artist",
            duration_sec=30.0,
            usage_count=1000
        )
        
        assert track.track_id == "123"
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"
        assert track.duration_sec == 30.0
        assert track.usage_count == 1000


class TestRemotionMusicWorkflow:
    """End-to-end tests for Remotion music workflow"""
    
    @pytest.fixture
    def video_analysis_data(self):
        """Sample video analysis for workflow test"""
        return {
            "detected_hook": "Stop scrolling right now",
            "topics": ["productivity", "focus", "work"],
            "tone": "energetic",
            "music_suggestion": {
                "mood": "upbeat",
                "genre": "electronic",
                "tempo": "fast"
            },
            "transcription_data": {
                "words": [
                    {"w": "Stop", "start": 0.0, "end": 0.3},
                    {"w": "scrolling", "start": 0.3, "end": 0.8},
                ]
            },
            "scene_structure": [
                {"start_sec": 0, "end_sec": 3, "role": "hook", "summary": "Attention grabber"}
            ]
        }
    
    def test_full_music_integration_workflow(self, video_analysis_data):
        """Test complete workflow: analysis -> music selection -> Remotion spec"""
        from services.content_pipeline.remotion_spec_service import RemotionSpecService
        from unittest.mock import patch
        
        # 1. Build Remotion spec from analysis
        with patch.object(RemotionSpecService, '__init__', lambda x: None):
            service = RemotionSpecService()
            service.engine = Mock()
            
            # 2. Simulate music selection based on analysis
            music_suggestion = video_analysis_data.get("music_suggestion", {})
            selected_music_url = "https://example.com/upbeat-electronic.mp3"
            
            # 3. Build spec with music
            deep_audit_data = {
                "transcript": video_analysis_data.get("transcription_data", {}),
                "scene_structure": video_analysis_data.get("scene_structure", [])
            }
            
            spec = service.build_from_deep_audit(
                composition_id="ShortFormV1",
                duration_sec=30,
                deep_audit_data=deep_audit_data,
                music_url=selected_music_url,
                caption_style_id="CaptionStyleA"
            )
            
            # 4. Verify spec is complete
            assert spec is not None
            assert spec.composition_id == "ShortFormV1"
            assert spec.audio.music_url == selected_music_url
            
            # 5. Verify Remotion input props are valid
            props = service.to_remotion_input_props(spec)
            
            assert props["composition_id"] == "ShortFormV1"
            assert props["fps"] == 30
            assert props["width"] == 1080
            assert props["height"] == 1920
            assert len(props["timeline"]) > 0
    
    def test_music_recommendation_to_spec(self, video_analysis_data):
        """Test that music recommendations flow into Remotion spec correctly"""
        from services.content_pipeline.remotion_spec_service import RemotionSpecService
        from unittest.mock import patch
        
        # Simulate music recommendation from analysis
        music_rec = video_analysis_data["music_suggestion"]
        
        # Verify recommendation fields
        assert music_rec["mood"] == "upbeat"
        assert music_rec["genre"] == "electronic"
        
        # These would be used to search for music
        # Then the selected track URL goes into the spec
        with patch.object(RemotionSpecService, '__init__', lambda x: None):
            service = RemotionSpecService()
            service.engine = Mock()
            
            spec = service.build_from_deep_audit(
                composition_id="ShortFormV1",
                duration_sec=30,
                deep_audit_data={},
                music_url="https://example.com/matched-track.mp3"
            )
            
            # The workflow connects analysis -> music search -> spec
            assert spec.audio.music_url is not None
