"""
Unit Tests for Music Overlay Service (MUSIC-004)
=================================================
Tests for background music overlay with ducking functionality.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from services.remotion.music_overlay import (
    MusicOverlayService,
    MusicOverlayConfig
)
from services.remotion.models import AudioTrack, SourceType


@pytest.fixture
def mock_music_library(tmp_path):
    """Create a mock music library JSON file."""
    library_data = {
        "tracks": [
            {
                "id": "upbeat_001",
                "name": "Happy Summer",
                "file_path": str(tmp_path / "happy_summer.mp3"),
                "duration_seconds": 60.0,
                "mood": "upbeat",
                "tags": ["energetic", "positive"]
            },
            {
                "id": "chill_001",
                "name": "Calm Waves",
                "file_path": str(tmp_path / "calm_waves.mp3"),
                "duration_seconds": 90.0,
                "mood": "chill",
                "tags": ["relaxing", "ambient"]
            },
            {
                "id": "dramatic_001",
                "name": "Epic Rise",
                "file_path": str(tmp_path / "epic_rise.mp3"),
                "duration_seconds": 45.0,
                "mood": "dramatic",
                "tags": ["intense", "cinematic"]
            }
        ]
    }

    # Create dummy music files
    for track in library_data["tracks"]:
        Path(track["file_path"]).touch()

    # Create library JSON
    library_path = tmp_path / "music_library.json"
    with open(library_path, 'w') as f:
        json.dump(library_data, f)

    return str(library_path)


class TestMusicOverlayServiceInit:
    """Test MusicOverlayService initialization."""

    def test_service_initializes_with_default_library(self):
        """Test service initializes with default library path."""
        service = MusicOverlayService()
        assert service.music_library_path is not None
        assert isinstance(service.music_library, dict)

    def test_service_initializes_with_custom_library(self, mock_music_library):
        """Test service initializes with custom library path."""
        service = MusicOverlayService(music_library_path=mock_music_library)
        assert service.music_library_path == mock_music_library
        assert len(service.music_library.get("tracks", [])) == 3

    def test_service_handles_missing_library(self, tmp_path):
        """Test service handles missing library file gracefully."""
        missing_path = str(tmp_path / "nonexistent.json")
        service = MusicOverlayService(music_library_path=missing_path)
        assert service.music_library == {"tracks": []}


class TestAddMusicOverlay:
    """Test adding music overlay to compositions."""

    def test_add_music_with_track_id(self, mock_music_library):
        """Test adding music using track ID from library."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        config = MusicOverlayConfig(
            music_track_id="upbeat_001",
            volume=0.3,
            duck_volume=0.1
        )

        audio_tracks = service.add_music_overlay(
            video_duration=45.0,
            voiceover_track_id="audio_001",
            config=config
        )

        assert len(audio_tracks) == 1
        assert isinstance(audio_tracks[0], AudioTrack)
        assert audio_tracks[0].id == "music_upbeat_001"
        assert audio_tracks[0].volume == 0.3
        assert audio_tracks[0].ducking is not None
        assert audio_tracks[0].ducking["duck_under"] == "audio_001"

    def test_add_music_with_file_path(self, tmp_path):
        """Test adding music using direct file path."""
        music_file = tmp_path / "custom_music.mp3"
        music_file.touch()

        service = MusicOverlayService()

        config = MusicOverlayConfig(
            music_file_path=str(music_file),
            volume=0.5
        )

        audio_tracks = service.add_music_overlay(
            video_duration=30.0,
            config=config
        )

        assert len(audio_tracks) == 1
        assert audio_tracks[0].source == str(music_file)
        assert audio_tracks[0].volume == 0.5

    def test_add_music_without_voiceover_ducking(self, mock_music_library):
        """Test adding music without voiceover ducking."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        config = MusicOverlayConfig(music_track_id="chill_001")

        audio_tracks = service.add_music_overlay(
            video_duration=45.0,
            config=config
        )

        assert len(audio_tracks) == 1
        assert audio_tracks[0].ducking is None

    def test_add_music_raises_on_missing_track(self, mock_music_library):
        """Test adding music raises error if track not found."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        config = MusicOverlayConfig(music_track_id="nonexistent_track")

        with pytest.raises(ValueError, match="Music track not found"):
            service.add_music_overlay(video_duration=45.0, config=config)

    def test_add_music_raises_on_missing_file(self, tmp_path):
        """Test adding music raises error if file doesn't exist."""
        service = MusicOverlayService()

        config = MusicOverlayConfig(
            music_file_path=str(tmp_path / "nonexistent.mp3")
        )

        with pytest.raises(ValueError, match="Music file not found"):
            service.add_music_overlay(video_duration=45.0, config=config)

    def test_add_music_raises_without_path_or_id(self):
        """Test adding music raises error without path or ID."""
        service = MusicOverlayService()

        config = MusicOverlayConfig()

        with pytest.raises(ValueError, match="must be provided"):
            service.add_music_overlay(video_duration=45.0, config=config)


class TestMoodBasedSuggestions:
    """Test mood-based music suggestions."""

    def test_suggest_music_by_mood_upbeat(self, mock_music_library):
        """Test suggesting upbeat music."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        suggestions = service.suggest_music_by_mood(mood="upbeat", duration=45.0)

        assert len(suggestions) >= 1
        assert suggestions[0]["track_id"] == "upbeat_001"
        assert suggestions[0]["mood"] == "upbeat"

    def test_suggest_music_by_mood_chill(self, mock_music_library):
        """Test suggesting chill music."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        suggestions = service.suggest_music_by_mood(mood="chill", duration=60.0)

        assert len(suggestions) >= 1
        assert suggestions[0]["track_id"] == "chill_001"

    def test_suggest_music_sorts_by_fit_score(self, mock_music_library):
        """Test suggestions sorted by duration fit score."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        # Request 45-second video (should prefer "dramatic_001" which is 45s)
        suggestions = service.suggest_music_by_mood(mood="dramatic", duration=45.0)

        assert len(suggestions) >= 1
        assert suggestions[0]["track_id"] == "dramatic_001"
        assert suggestions[0]["fit_score"] == 1.0

    def test_suggest_music_no_matches(self, mock_music_library):
        """Test suggesting music with no mood matches."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        suggestions = service.suggest_music_by_mood(mood="nonexistent", duration=45.0)

        assert len(suggestions) == 0


class TestVolumeConversion:
    """Test volume to decibel conversion."""

    def test_volume_to_db_full_volume(self):
        """Test converting full volume (1.0) to dB."""
        service = MusicOverlayService()

        db = service._volume_to_db(1.0)

        assert db == 0.0

    def test_volume_to_db_half_volume(self):
        """Test converting half volume (0.5) to dB."""
        service = MusicOverlayService()

        db = service._volume_to_db(0.5)

        assert db == pytest.approx(-6.02, abs=0.1)

    def test_volume_to_db_quarter_volume(self):
        """Test converting quarter volume (0.25) to dB."""
        service = MusicOverlayService()

        db = service._volume_to_db(0.25)

        assert db == pytest.approx(-12.04, abs=0.1)

    def test_volume_to_db_zero_volume(self):
        """Test converting zero volume to dB (should clamp to -60dB)."""
        service = MusicOverlayService()

        db = service._volume_to_db(0.0)

        assert db == -60.0


class TestCreateMusicLayers:
    """Test creating music layers with smart ducking."""

    def test_create_music_layers_without_voiceover(self, mock_music_library):
        """Test creating music layers without voiceover segments."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        config = MusicOverlayConfig(music_track_id="upbeat_001", volume=0.5)

        layers = service.create_music_layers(
            video_duration=45.0,
            voiceover_segments=None,
            config=config
        )

        assert len(layers) == 1
        assert layers[0]["id"] == "music_full"
        assert layers[0]["start"] == 0.0
        assert layers[0]["end"] == 45.0
        assert layers[0]["volume"] == 0.5

    def test_create_music_layers_with_single_voiceover(self, mock_music_library):
        """Test creating music layers with single voiceover segment."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        config = MusicOverlayConfig(
            music_track_id="upbeat_001",
            volume=0.5,
            duck_volume=0.1
        )

        voiceover_segments = [
            {"start": 5.0, "end": 10.0}
        ]

        layers = service.create_music_layers(
            video_duration=45.0,
            voiceover_segments=voiceover_segments,
            config=config
        )

        # Should have 3 layers: before, ducked, after
        assert len(layers) == 3

        # Before voiceover (0-5s, full volume)
        assert layers[0]["start"] == 0.0
        assert layers[0]["end"] == 5.0
        assert layers[0]["volume"] == 0.5

        # During voiceover (5-10s, ducked volume)
        assert layers[1]["start"] == 5.0
        assert layers[1]["end"] == 10.0
        assert layers[1]["volume"] == 0.1

        # After voiceover (10-45s, full volume)
        assert layers[2]["start"] == 10.0
        assert layers[2]["end"] == 45.0
        assert layers[2]["volume"] == 0.5

    def test_create_music_layers_with_multiple_voiceovers(self, mock_music_library):
        """Test creating music layers with multiple voiceover segments."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        config = MusicOverlayConfig(
            music_track_id="upbeat_001",
            volume=0.5,
            duck_volume=0.1
        )

        voiceover_segments = [
            {"start": 5.0, "end": 10.0},
            {"start": 20.0, "end": 25.0}
        ]

        layers = service.create_music_layers(
            video_duration=45.0,
            voiceover_segments=voiceover_segments,
            config=config
        )

        # Should have 5 layers: before, ducked1, between, ducked2, after
        assert len(layers) == 5


class TestMusicOverlayConfig:
    """Test MusicOverlayConfig dataclass."""

    def test_config_defaults(self):
        """Test MusicOverlayConfig default values."""
        config = MusicOverlayConfig()

        assert config.music_track_id is None
        assert config.music_file_path is None
        assert config.volume == 0.3
        assert config.duck_volume == 0.1
        assert config.fade_in_seconds == 1.0
        assert config.fade_out_seconds == 1.0
        assert config.start_offset == 0.0
        assert config.loop is True
        assert config.mood is None

    def test_config_custom_values(self):
        """Test MusicOverlayConfig with custom values."""
        config = MusicOverlayConfig(
            music_track_id="custom_track",
            volume=0.7,
            duck_volume=0.2,
            mood="energetic"
        )

        assert config.music_track_id == "custom_track"
        assert config.volume == 0.7
        assert config.duck_volume == 0.2
        assert config.mood == "energetic"


class TestIntegrationScenarios:
    """Integration tests for common music overlay scenarios."""

    def test_full_workflow_with_voiceover_ducking(self, mock_music_library):
        """Test complete workflow: select music, add to composition with ducking."""
        service = MusicOverlayService(music_library_path=mock_music_library)

        # 1. Suggest music by mood
        suggestions = service.suggest_music_by_mood(mood="upbeat", duration=45.0)
        assert len(suggestions) > 0

        # 2. Use suggested track
        track_id = suggestions[0]["track_id"]

        # 3. Add music overlay with ducking
        config = MusicOverlayConfig(
            music_track_id=track_id,
            volume=0.3,
            duck_volume=0.1
        )

        audio_tracks = service.add_music_overlay(
            video_duration=45.0,
            voiceover_track_id="voiceover_001",
            config=config
        )

        assert len(audio_tracks) == 1
        assert audio_tracks[0].ducking is not None
        assert audio_tracks[0].ducking["duck_under"] == "voiceover_001"
