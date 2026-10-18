"""
Music Selector Tests
====================
Comprehensive test suite for the music selection service.

Test Categories:
    - MusicTrack dataclass tests
    - Music library loading tests
    - Clip analysis tests
    - Music matching/compatibility tests
    - Duration constraint tests (5 min max)
    - AI provider integration tests

Run tests:
    pytest tests/test_music_selector.py -v
    pytest tests/test_music_selector.py -k "duration" -v
"""

import asyncio
import json
import os
import pytest
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_music_index():
    """Sample music index data."""
    return {
        "version": "1.0",
        "tracks": [
            {
                "id": "corporate-tech",
                "file_path": "/music/corporate.mp3",
                "genre": "corporate",
                "moods": ["professional", "upbeat", "confident"],
                "energy_level": 0.7,
                "tempo": 120,
                "duration": 180,
                "attributes": ["no vocals", "business"]
            },
            {
                "id": "lofi-chill",
                "file_path": "/music/lofi.mp3",
                "genre": "lofi",
                "moods": ["relaxed", "chill", "calm"],
                "energy_level": 0.3,
                "tempo": 85,
                "duration": 240,
                "attributes": ["beats", "relaxing"]
            },
            {
                "id": "energetic-pop",
                "file_path": "/music/pop.mp3",
                "genre": "pop",
                "moods": ["happy", "energetic", "exciting"],
                "energy_level": 0.85,
                "tempo": 128,
                "duration": 200,
                "attributes": ["upbeat", "catchy"]
            },
            {
                "id": "ambient-calm",
                "file_path": "/music/ambient.mp3",
                "genre": "ambient",
                "moods": ["peaceful", "serene", "calm"],
                "energy_level": 0.2,
                "tempo": 70,
                "duration": 300,
                "attributes": ["atmospheric", "background"]
            }
        ]
    }


@pytest.fixture
def temp_music_index(sample_music_index):
    """Create temporary music index file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_music_index, f)
        f.flush()  # Ensure data is written
        temp_path = Path(f.name)
    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def sample_transcript_energetic():
    """Sample energetic transcript."""
    return """
    Welcome back to another amazing video! Today we're going to do something 
    absolutely incredible and exciting! You won't believe how awesome this is!
    Let's dive right in and have some fun!
    """


@pytest.fixture
def sample_transcript_calm():
    """Sample calm transcript."""
    return """
    Today we're going to take a slow, peaceful look at some relaxing techniques.
    Find a quiet space and breathe deeply. Let's explore some gentle, calming methods.
    """


@pytest.fixture
def sample_transcript_educational():
    """Sample educational transcript."""
    return """
    In this tutorial, we'll learn how to set up your development environment.
    First, you need to install the required dependencies. Let me show you step by step.
    """


# =============================================================================
# MUSICTRACK DATACLASS TESTS
# =============================================================================

class TestMusicTrackDataclass:
    """Test MusicTrack dataclass."""
    
    def test_musictrack_creation(self):
        """Test MusicTrack can be created."""
        from services.music_selector import MusicTrack
        
        track = MusicTrack(
            id="test-track",
            file_path="/music/test.mp3",
            file_name="test.mp3",
            duration=120.0,
            tempo=100.0,
            energy_level=0.6,
            mood="happy",
            genre="pop"
        )
        
        assert track.id == "test-track"
        assert track.duration == 120.0
        assert track.energy_level == 0.6
    
    def test_musictrack_to_dict(self):
        """Test MusicTrack serialization."""
        from services.music_selector import MusicTrack
        
        track = MusicTrack(
            id="test",
            file_path="/test.mp3",
            file_name="test.mp3",
            duration=60.0,
            tempo=120.0,
            energy_level=0.5,
            mood="neutral",
            genre="general"
        )
        
        data = track.to_dict()
        
        assert data["id"] == "test"
        assert data["duration"] == 60.0
        assert isinstance(data["moods"], list)
    
    def test_musictrack_from_dict(self):
        """Test MusicTrack deserialization."""
        from services.music_selector import MusicTrack
        
        data = {
            "id": "loaded-track",
            "file_path": "/music/loaded.mp3",
            "genre": "electronic",
            "moods": ["energetic", "exciting"],
            "energy_level": 0.8,
            "tempo": 140,
            "duration": 200
        }
        
        track = MusicTrack.from_dict(data)
        
        assert track.id == "loaded-track"
        assert track.genre == "electronic"
        assert track.energy_level == 0.8
        assert "energetic" in track.moods
    
    def test_musictrack_from_dict_with_alternate_keys(self):
        """Test MusicTrack handles alternate key names."""
        from services.music_selector import MusicTrack
        
        # Using keys from music_preprocessor format
        data = {
            "id": "alt-track",
            "file_path": "/music/alt.mp3",
            "detected_mood": "calm",
            "predicted_genre": "ambient",
            "tempo_bpm": 80,
            "energy_level": 0.3
        }
        
        track = MusicTrack.from_dict(data)
        
        assert track.mood == "calm"
        assert track.genre == "ambient"
        assert track.tempo == 80


# =============================================================================
# MUSIC LIBRARY LOADING TESTS
# =============================================================================

class TestMusicLibraryLoading:
    """Test music library loading."""
    
    def test_load_library_from_index(self, temp_music_index, sample_music_index):
        """Test loading library from index file."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(music_index_path=temp_music_index)
        library = selector.load_music_library()
        
        assert len(library) == len(sample_music_index["tracks"])
        assert library[0].id == "corporate-tech"
    
    def test_load_library_from_data(self, sample_music_index):
        """Test loading library from provided data."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector()
        library = selector.load_music_library(index_data=sample_music_index)
        
        assert len(library) == 4
    
    def test_load_demo_tracks_when_no_index(self):
        """Test demo tracks are loaded when no index exists."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(music_index_path=Path("/nonexistent/path.json"))
        library = selector.load_music_library()
        
        # Should load demo tracks
        assert len(library) > 0
        assert any(t.id == "corporate-tech" for t in library)
    
    def test_library_is_cached(self, sample_music_index):
        """Test library is cached after first load."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector()
        library1 = selector.load_music_library(index_data=sample_music_index)
        library2 = selector.load_music_library()
        
        assert library1 is library2
    
    def test_get_library_stats(self, sample_music_index):
        """Test library statistics."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector()
        selector.load_music_library(index_data=sample_music_index)
        
        stats = selector.get_library_stats()
        
        assert stats["tracks"] == 4
        assert "corporate" in stats["genres"]
        assert stats["total_duration_minutes"] > 0


# =============================================================================
# CLIP ANALYSIS TESTS
# =============================================================================

class TestClipAnalysis:
    """Test clip analysis functionality."""
    
    @pytest.mark.asyncio
    async def test_analyze_clip_basic(self):
        """Test basic clip analysis."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        
        analysis = await selector.analyze_clip(
            duration=30,
            transcript="This is a test video",
            topics=["testing"]
        )
        
        assert analysis.duration == 30
        assert analysis.mood in ["neutral", "calm", "happy", "energetic", "sad"]
        assert 0 <= analysis.energy_level <= 1
    
    @pytest.mark.asyncio
    async def test_analyze_clip_energetic_transcript(self, sample_transcript_energetic):
        """Test analysis detects energetic mood."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        
        analysis = await selector.analyze_clip(
            duration=30,
            transcript=sample_transcript_energetic
        )
        
        # Should detect higher energy
        assert analysis.energy_level > 0.5 or analysis.mood in ["energetic", "happy"]
    
    @pytest.mark.asyncio
    async def test_analyze_clip_calm_transcript(self, sample_transcript_calm):
        """Test analysis detects calm mood."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        
        analysis = await selector.analyze_clip(
            duration=30,
            transcript=sample_transcript_calm
        )
        
        # Should detect calmer energy
        assert analysis.energy_level < 0.6 or analysis.mood in ["calm", "peaceful", "neutral"]
    
    @pytest.mark.asyncio
    async def test_analyze_clip_content_type_detection(self):
        """Test content type detection from topics."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        
        # Educational content
        analysis = await selector.analyze_clip(
            duration=30,
            transcript="Learn how to code",
            topics=["tutorial", "education", "learning"]
        )
        assert analysis.content_type == "educational"
        
        # Fitness content
        analysis2 = await selector.analyze_clip(
            duration=30,
            transcript="Workout time",
            topics=["workout", "fitness", "gym"]
        )
        assert analysis2.content_type == "fitness"


# =============================================================================
# DURATION CONSTRAINT TESTS (5 MINUTE MAX)
# =============================================================================

class TestDurationConstraints:
    """Test 5-minute maximum duration constraint."""
    
    @pytest.mark.asyncio
    async def test_reject_clip_over_5_minutes(self):
        """Test that clips over 5 minutes are rejected."""
        from services.music_selector import MusicSelector, MAX_CLIP_DURATION_SECONDS
        
        selector = MusicSelector()
        
        # 6 minutes = 360 seconds, should be rejected
        with pytest.raises(ValueError) as excinfo:
            await selector.analyze_clip(duration=360)
        
        assert "exceeds maximum" in str(excinfo.value).lower()
        assert "5 minutes" in str(excinfo.value) or "300" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_accept_clip_under_5_minutes(self):
        """Test that clips under 5 minutes are accepted."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        
        # 4 minutes = 240 seconds, should be OK
        analysis = await selector.analyze_clip(duration=240)
        
        assert analysis.duration == 240
    
    @pytest.mark.asyncio
    async def test_accept_clip_exactly_5_minutes(self):
        """Test that clips exactly 5 minutes are accepted."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        
        # Exactly 5 minutes = 300 seconds
        analysis = await selector.analyze_clip(duration=300)
        
        assert analysis.duration == 300
    
    @pytest.mark.asyncio
    async def test_select_music_rejects_long_clips(self, sample_music_index):
        """Test select_music_for_clip rejects clips over 5 minutes."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        selector.load_music_library(index_data=sample_music_index)
        
        with pytest.raises(ValueError) as excinfo:
            await selector.select_music_for_clip(duration=400)
        
        assert "5 minutes" in str(excinfo.value) or "300" in str(excinfo.value)
    
    def test_max_duration_constant(self):
        """Test MAX_CLIP_DURATION_SECONDS is 300 (5 minutes)."""
        from services.music_selector import MAX_CLIP_DURATION_SECONDS
        
        assert MAX_CLIP_DURATION_SECONDS == 300


# =============================================================================
# MUSIC MATCHING TESTS
# =============================================================================

class TestMusicMatching:
    """Test music matching and compatibility."""
    
    @pytest.mark.asyncio
    async def test_select_music_basic(self, sample_music_index):
        """Test basic music selection."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        selector.load_music_library(index_data=sample_music_index)
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript="This is an exciting video!"
        )
        
        assert len(matches) > 0
        assert matches[0].compatibility_score > 0
    
    @pytest.mark.asyncio
    async def test_select_music_returns_sorted(self, sample_music_index):
        """Test matches are sorted by compatibility."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        selector.load_music_library(index_data=sample_music_index)
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript="Test video"
        )
        
        # Verify sorted descending
        scores = [m.compatibility_score for m in matches]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_select_music_respects_top_n(self, sample_music_index):
        """Test top_n parameter limits results."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        selector.load_music_library(index_data=sample_music_index)
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript="Test",
            top_n=2
        )
        
        assert len(matches) <= 2
    
    @pytest.mark.asyncio
    async def test_energetic_clip_matches_energetic_music(self, sample_music_index, sample_transcript_energetic):
        """Test energetic clips match energetic music."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        selector.load_music_library(index_data=sample_music_index)
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript=sample_transcript_energetic,
            topics=["exciting", "fun"]
        )
        
        # Top match should be high-energy
        if matches:
            top_match = matches[0]
            assert top_match.track.energy_level > 0.5 or "energetic" in top_match.track.moods
    
    @pytest.mark.asyncio
    async def test_calm_clip_matches_calm_music(self, sample_music_index, sample_transcript_calm):
        """Test calm clips match calm music."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        selector.load_music_library(index_data=sample_music_index)
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript=sample_transcript_calm,
            topics=["relaxation", "meditation"]
        )
        
        # Should have matches
        assert len(matches) > 0
    
    @pytest.mark.asyncio
    async def test_match_includes_reasoning(self, sample_music_index):
        """Test matches include reasoning."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        selector.load_music_library(index_data=sample_music_index)
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript="Test video content"
        )
        
        assert len(matches) > 0
        assert matches[0].reasoning != ""


# =============================================================================
# COMPATIBILITY CALCULATION TESTS
# =============================================================================

class TestCompatibilityCalculation:
    """Test compatibility score calculation."""
    
    def test_mood_matching_exact(self, sample_music_index):
        """Test exact mood match gives high score."""
        from services.music_selector import MusicSelector, ClipAnalysis, MusicTrack
        
        selector = MusicSelector()
        
        analysis = ClipAnalysis(
            clip_id="test",
            duration=30,
            mood="calm",
            energy_level=0.3
        )
        
        track = MusicTrack(
            id="calm-track",
            file_path="/test.mp3",
            file_name="test.mp3",
            mood="calm",
            energy_level=0.3,
            duration=60
        )
        
        score, reasoning = selector._calculate_compatibility(analysis, track)
        
        assert score > 0.5
        assert "Mood match" in reasoning
    
    def test_energy_matching(self):
        """Test energy level matching."""
        from services.music_selector import MusicSelector, ClipAnalysis, MusicTrack
        
        selector = MusicSelector()
        
        # High energy clip
        analysis = ClipAnalysis(
            clip_id="test",
            duration=30,
            mood="energetic",
            energy_level=0.9
        )
        
        # High energy track - should match well
        high_energy_track = MusicTrack(
            id="high-energy",
            file_path="/test.mp3",
            file_name="test.mp3",
            mood="energetic",
            energy_level=0.85,
            duration=60
        )
        
        # Low energy track - should match poorly
        low_energy_track = MusicTrack(
            id="low-energy",
            file_path="/test2.mp3",
            file_name="test2.mp3",
            mood="calm",
            energy_level=0.2,
            duration=60
        )
        
        high_score, _ = selector._calculate_compatibility(analysis, high_energy_track)
        low_score, _ = selector._calculate_compatibility(analysis, low_energy_track)
        
        assert high_score > low_score
    
    def test_moods_compatible(self):
        """Test mood compatibility checking."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector()
        
        # Compatible pairs
        assert selector._moods_compatible("happy", "energetic") is True
        assert selector._moods_compatible("calm", "peaceful") is True
        
        # Incompatible pairs
        assert selector._moods_compatible("happy", "sad") is False
        assert selector._moods_compatible("energetic", "calm") is False


# =============================================================================
# AI PROVIDER INTEGRATION TESTS
# =============================================================================

class TestAIProviderIntegration:
    """Test AI provider integration for mood analysis."""
    
    def test_get_ai_provider_mock_blocked_in_factory(self):
        """Test mock AI provider raises error from factory but MusicSelector handles gracefully."""
        from services.music_selector import MusicSelector

        selector = MusicSelector(ai_provider="mock")
        # Factory now blocks mock, _get_ai_provider catches the exception and returns None
        provider = selector._get_ai_provider()

        assert provider is None

    def test_get_ai_provider_mock_direct_injection(self):
        """Test mock AI provider can be injected directly for testing."""
        from services.music_selector import MusicSelector
        from services.ai_providers.mock_provider import MockAIProvider

        selector = MusicSelector()
        selector._ai_provider = MockAIProvider()
        provider = selector._get_ai_provider()

        assert provider is not None
        assert provider.name == "mock"
    
    @pytest.mark.asyncio
    async def test_mood_analysis_with_mock_provider(self):
        """Test mood analysis uses mock provider."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector(ai_provider="mock")
        
        analysis = await selector.analyze_clip(
            duration=30,
            transcript="This is an amazing and exciting video!"
        )
        
        # Should have analyzed
        assert analysis.mood is not None
        assert 0 <= analysis.energy_level <= 1
    
    def test_heuristic_mood_analysis_energetic(self):
        """Test heuristic mood detection for energetic content."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector()
        
        transcript = "Amazing incredible exciting wow awesome!"
        mood, energy = selector._analyze_mood_heuristic(transcript)
        
        assert mood == "energetic"
        assert energy > 0.5
    
    def test_heuristic_mood_analysis_calm(self):
        """Test heuristic mood detection for calm content."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector()
        
        transcript = "Peaceful relaxing calm gentle quiet slow"
        mood, energy = selector._analyze_mood_heuristic(transcript)
        
        assert mood == "calm"
        assert energy < 0.5
    
    def test_heuristic_mood_analysis_neutral(self):
        """Test heuristic mood detection for neutral content."""
        from services.music_selector import MusicSelector
        
        selector = MusicSelector()
        
        transcript = "The video shows a process of creating something."
        mood, energy = selector._analyze_mood_heuristic(transcript)
        
        assert mood == "neutral"
        assert 0.3 <= energy <= 0.7


# =============================================================================
# MUSIC MATCH DATACLASS TESTS
# =============================================================================

class TestMusicMatchDataclass:
    """Test MusicMatch dataclass."""
    
    def test_music_match_creation(self):
        """Test MusicMatch can be created."""
        from services.music_selector import MusicMatch, MusicTrack
        
        track = MusicTrack(
            id="test",
            file_path="/test.mp3",
            file_name="test.mp3"
        )
        
        match = MusicMatch(
            track=track,
            compatibility_score=0.85,
            reasoning="Great match for energetic content"
        )
        
        assert match.compatibility_score == 0.85
        assert "energetic" in match.reasoning
    
    def test_music_match_to_dict(self):
        """Test MusicMatch serialization."""
        from services.music_selector import MusicMatch, MusicTrack
        
        track = MusicTrack(
            id="test",
            file_path="/test.mp3",
            file_name="test.mp3",
            genre="pop"
        )
        
        match = MusicMatch(
            track=track,
            compatibility_score=0.75,
            reasoning="Good match"
        )
        
        data = match.to_dict()
        
        assert data["compatibility_score"] == 0.75
        assert data["track"]["id"] == "test"
        assert data["track"]["genre"] == "pop"


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
