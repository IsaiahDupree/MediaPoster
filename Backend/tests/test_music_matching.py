"""
Tests for Music Matching (Auto Background Music Suggestion) Service

Tests cover:
1. Unit tests for MusicSelector compatibility scoring
2. Integration tests for music matching API endpoints
3. Scenario tests for different content types

Run with: pytest tests/test_music_matching.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from services.music_selector import (
    MusicSelector,
    MusicTrack,
    MusicMatch,
    ClipAnalysis,
    MAX_CLIP_DURATION_SECONDS
)


# =============================================================================
# Unit Tests: MusicSelector Service
# =============================================================================

class TestMusicSelectorUnit:
    """Unit tests for MusicSelector class"""
    
    def test_music_selector_initialization(self):
        """Test MusicSelector initializes with correct defaults"""
        selector = MusicSelector()
        assert selector.max_clip_duration == MAX_CLIP_DURATION_SECONDS
        assert selector.max_clip_duration == 300  # 5 minutes
    
    def test_music_track_from_dict(self):
        """Test MusicTrack deserialization"""
        data = {
            "id": "test-track",
            "file_path": "/music/test.mp3",
            "file_name": "test.mp3",
            "duration": 180,
            "tempo": 120,
            "energy_level": 0.7,
            "mood": "energetic",
            "genre": "pop",
            "moods": ["happy", "upbeat"],
            "attributes": ["no vocals", "modern"]
        }
        
        track = MusicTrack.from_dict(data)
        
        assert track.id == "test-track"
        assert track.duration == 180
        assert track.tempo == 120
        assert track.energy_level == 0.7
        assert track.mood == "energetic"
        assert "happy" in track.moods
    
    def test_music_track_to_dict(self):
        """Test MusicTrack serialization"""
        track = MusicTrack(
            id="test-track",
            file_path="/music/test.mp3",
            file_name="test.mp3",
            duration=180,
            tempo=120,
            energy_level=0.7,
            mood="energetic",
            genre="pop"
        )
        
        data = track.to_dict()
        
        assert data["id"] == "test-track"
        assert data["duration"] == 180
        assert data["tempo"] == 120
    
    def test_music_match_to_dict(self):
        """Test MusicMatch serialization"""
        track = MusicTrack(
            id="test-track",
            file_path="/music/test.mp3",
            file_name="test.mp3"
        )
        match = MusicMatch(
            track=track,
            compatibility_score=0.85,
            reasoning="High energy match for video content"
        )
        
        data = match.to_dict()
        
        assert data["compatibility_score"] == 0.85
        assert "energy" in data["reasoning"].lower()
        assert data["track"]["id"] == "test-track"
    
    def test_load_demo_tracks(self):
        """Test loading demo music library"""
        selector = MusicSelector()
        library = selector.load_music_library()
        
        # Should have demo tracks
        assert len(library) > 0
        
        # Check demo track IDs exist
        track_ids = [t.id for t in library]
        assert "corporate-tech" in track_ids
        assert "lofi-chill" in track_ids
        assert "energetic-pop" in track_ids
    
    @pytest.mark.asyncio
    async def test_max_duration_enforcement(self):
        """Test that clips over 5 minutes are rejected"""
        selector = MusicSelector()
        
        with pytest.raises(ValueError) as exc_info:
            await selector.select_music_for_clip(
                duration=400  # Over 5 minutes
            )
        
        assert "5 minutes" in str(exc_info.value)


# =============================================================================
# Mood Analysis Tests
# =============================================================================

class TestMoodAnalysis:
    """Tests for mood detection and analysis"""
    
    @pytest.mark.asyncio
    async def test_heuristic_mood_detection_energetic(self):
        """Test heuristic detection of energetic content"""
        selector = MusicSelector()
        
        transcript = "This is amazing! Incredible results, so exciting!"
        mood, energy = selector._analyze_mood_heuristic(transcript)
        
        assert mood == "energetic"
        assert energy > 0.5
    
    @pytest.mark.asyncio
    async def test_heuristic_mood_detection_calm(self):
        """Test heuristic detection of calm content"""
        selector = MusicSelector()
        
        transcript = "Welcome to this peaceful, relaxing meditation session. Breathe slowly and quietly."
        mood, energy = selector._analyze_mood_heuristic(transcript)
        
        assert mood == "calm"
        assert energy < 0.5
    
    @pytest.mark.asyncio
    async def test_heuristic_mood_detection_happy(self):
        """Test heuristic detection of happy content"""
        selector = MusicSelector()
        
        transcript = "I'm so happy to share this! I love it, it's great fun!"
        mood, energy = selector._analyze_mood_heuristic(transcript)
        
        assert mood == "happy"
    
    @pytest.mark.asyncio
    async def test_heuristic_mood_detection_neutral(self):
        """Test heuristic detection defaults to neutral"""
        selector = MusicSelector()
        
        transcript = "Today we will discuss the implementation details of this feature."
        mood, energy = selector._analyze_mood_heuristic(transcript)
        
        assert mood == "neutral"
        assert 0.4 <= energy <= 0.6


# =============================================================================
# Content Type Detection Tests
# =============================================================================

class TestContentTypeDetection:
    """Tests for content type detection"""
    
    def test_corporate_content_detection(self):
        """Test detection of corporate content"""
        selector = MusicSelector()
        
        topics = ["business strategy", "corporate growth", "professional development"]
        content_type = selector._determine_content_type(topics)
        
        assert content_type == "corporate"
    
    def test_educational_content_detection(self):
        """Test detection of educational content"""
        selector = MusicSelector()
        
        topics = ["how to code", "tutorial", "learn python"]
        content_type = selector._determine_content_type(topics)
        
        assert content_type == "educational"
    
    def test_lifestyle_content_detection(self):
        """Test detection of lifestyle content"""
        selector = MusicSelector()
        
        topics = ["day in my life", "vlog", "lifestyle tips"]
        content_type = selector._determine_content_type(topics)
        
        assert content_type == "lifestyle"
    
    def test_fitness_content_detection(self):
        """Test detection of fitness content"""
        selector = MusicSelector()
        
        topics = ["workout routine", "gym tips", "fitness motivation"]
        content_type = selector._determine_content_type(topics)
        
        assert content_type == "fitness"
    
    def test_general_content_fallback(self):
        """Test fallback to general for unknown content"""
        selector = MusicSelector()
        
        topics = ["random topic", "something else"]
        content_type = selector._determine_content_type(topics)
        
        assert content_type == "general"


# =============================================================================
# Music Matching Algorithm Tests
# =============================================================================

class TestMusicMatchingAlgorithm:
    """Tests for the music matching/compatibility algorithm"""
    
    @pytest.mark.asyncio
    async def test_high_energy_video_matches_high_energy_music(self):
        """Energetic video should match with high-energy music"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript="This is incredible! Amazing! So exciting and energetic!",
            topics=["exciting", "action"],
            top_n=3
        )
        
        assert len(matches) > 0
        best_match = matches[0]
        
        # Best match should have decent compatibility
        assert best_match.compatibility_score > 0.3
        # Should prefer high-energy tracks
        assert best_match.track.energy_level >= 0.5
    
    @pytest.mark.asyncio
    async def test_calm_video_matches_calm_music(self):
        """Calm video should match with relaxing music"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=60,
            transcript="Welcome to this peaceful meditation. Relax and breathe slowly.",
            topics=["meditation", "relaxation"],
            top_n=3
        )
        
        assert len(matches) > 0
        best_match = matches[0]
        
        # Should prefer low-energy/calm tracks
        assert best_match.track.energy_level <= 0.6
    
    @pytest.mark.asyncio
    async def test_corporate_video_matches_professional_music(self):
        """Corporate video should match with professional music"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=45,
            transcript="Our business strategy focuses on professional growth and corporate excellence.",
            topics=["business", "corporate", "professional"],
            top_n=3
        )
        
        assert len(matches) > 0
        # Should find matches with reasoning about content type
        assert any("corporate" in m.track.genre.lower() or 
                  "professional" in str(m.track.moods).lower() 
                  for m in matches)
    
    @pytest.mark.asyncio
    async def test_returns_multiple_alternatives(self):
        """Should return multiple ranked alternatives"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript="Test video content",
            top_n=5
        )
        
        # Should return multiple options
        assert len(matches) >= 2
        
        # Should be sorted by score (descending)
        scores = [m.compatibility_score for m in matches]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_all_matches_have_reasoning(self):
        """All matches should include reasoning"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript="Some video content here",
            top_n=3
        )
        
        for match in matches:
            assert match.reasoning is not None
            assert len(match.reasoning) > 0


# =============================================================================
# API Integration Tests
# =============================================================================

class TestMusicMatchingAPI:
    """Integration tests for music matching API"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        return db
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test music matching health check"""
        try:
            from api.endpoints.music_matching import health_check
        except ImportError:
            pytest.skip("Requires full application context")
        
        response = await health_check()
        
        assert response["status"] == "healthy"
        assert response["service"] == "music_matching"
        assert response["library_tracks"] > 0
    
    @pytest.mark.asyncio
    async def test_list_library_endpoint(self):
        """Test listing music library"""
        try:
            from api.endpoints.music_matching import list_music_library
        except ImportError:
            pytest.skip("Requires full application context")
        
        response = await list_music_library()
        
        assert response["success"] is True
        assert response["total_tracks"] > 0
        assert len(response["tracks"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_track_details(self):
        """Test getting specific track details"""
        try:
            from api.endpoints.music_matching import get_track_details
        except ImportError:
            pytest.skip("Requires full application context")
        
        response = await get_track_details("corporate-tech")
        
        assert response["success"] is True
        assert response["track"]["id"] == "corporate-tech"
    
    @pytest.mark.asyncio
    async def test_get_track_not_found(self):
        """Test 404 for non-existent track"""
        try:
            from api.endpoints.music_matching import get_track_details
        except ImportError:
            pytest.skip("Requires full application context")
        
        with pytest.raises(Exception) as exc_info:
            await get_track_details("non-existent-track")
        
        assert "not found" in str(exc_info.value).lower()


# =============================================================================
# Scenario Tests: Real Content Types
# =============================================================================

class TestRealContentScenarios:
    """Tests simulating real content scenarios"""
    
    @pytest.mark.asyncio
    async def test_tiktok_dance_video(self):
        """Scenario: TikTok dance/trend video"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=15,
            transcript="Check out this dance move! Let's go!",
            topics=["dance", "trend", "viral"],
            top_n=3
        )
        
        assert len(matches) > 0
        # Should return valid matches with reasonable scores
        best = matches[0]
        assert best.compatibility_score > 0.3
        # At least one alternative should be available
        assert len(matches) >= 1
    
    @pytest.mark.asyncio
    async def test_youtube_tutorial(self):
        """Scenario: YouTube tutorial/how-to video"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=180,
            transcript="In this tutorial, I'll show you how to set up your development environment. First, you'll need to install the required packages.",
            topics=["tutorial", "how to", "programming", "education"],
            top_n=3
        )
        
        assert len(matches) > 0
        # Should prefer neutral/calm background music
        best = matches[0]
        assert best.track.energy_level <= 0.7
    
    @pytest.mark.asyncio
    async def test_instagram_reel_product(self):
        """Scenario: Instagram Reel product showcase"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript="Check out this amazing product! It's absolutely incredible and you're going to love it!",
            topics=["product", "review", "shopping"],
            top_n=3
        )
        
        assert len(matches) > 0
        # Should have positive/upbeat music
        best = matches[0]
        assert best.compatibility_score > 0.3
    
    @pytest.mark.asyncio
    async def test_motivational_content(self):
        """Scenario: Motivational/inspirational video"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=60,
            transcript="You can achieve anything you set your mind to. Believe in yourself and never give up!",
            topics=["motivation", "inspiration", "success"],
            top_n=3
        )
        
        assert len(matches) > 0
        # Should match inspirational music
        track_ids = [m.track.id for m in matches]
        # Check if inspirational track is suggested
        assert any("inspirational" in tid or "cinematic" in tid for tid in track_ids) or matches[0].compatibility_score > 0.3


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestMusicMatchingEdgeCases:
    """Tests for edge cases"""
    
    @pytest.mark.asyncio
    async def test_empty_transcript(self):
        """Handle empty transcript gracefully"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript="",
            topics=[],
            top_n=3
        )
        
        # Should still return matches (default to neutral)
        assert len(matches) > 0
    
    @pytest.mark.asyncio
    async def test_very_short_clip(self):
        """Handle very short clips"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=5,
            transcript="Quick tip!",
            top_n=3
        )
        
        assert len(matches) > 0
    
    @pytest.mark.asyncio
    async def test_clip_at_max_duration(self):
        """Handle clip at exactly 5 minutes"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=300,  # Exactly 5 minutes
            transcript="Long form content",
            top_n=3
        )
        
        assert len(matches) > 0
    
    @pytest.mark.asyncio
    async def test_special_characters_in_transcript(self):
        """Handle special characters in transcript"""
        selector = MusicSelector()
        selector.load_music_library()
        
        matches = await selector.select_music_for_clip(
            duration=30,
            transcript="🎉 Amazing!!! 100% the best 💯 @user #trending",
            top_n=3
        )
        
        assert len(matches) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
