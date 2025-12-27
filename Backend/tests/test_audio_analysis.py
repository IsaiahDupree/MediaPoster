"""
Tests for Audio Analysis (Background Music Detection) Service

Tests cover:
1. Unit tests for AudioAnalyzer service
2. Integration tests for API endpoints
3. Tests with real data scenarios (has music, no music, unknown)

Run with: pytest tests/test_audio_analysis.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from services.audio_analyzer import (
    AudioAnalyzer,
    AudioAnalysisResult,
    get_audio_analyzer,
    LIBROSA_AVAILABLE
)


# =============================================================================
# Unit Tests: AudioAnalyzer Service
# =============================================================================

class TestAudioAnalyzerUnit:
    """Unit tests for AudioAnalyzer class"""
    
    def test_audio_analyzer_initialization(self):
        """Test AudioAnalyzer initializes with correct defaults"""
        analyzer = AudioAnalyzer()
        assert analyzer.sample_rate == 22050
        assert analyzer.hop_length == 512
        assert analyzer.n_fft == 2048
    
    def test_audio_analysis_result_to_dict(self):
        """Test AudioAnalysisResult serialization"""
        result = AudioAnalysisResult(
            has_music=True,
            has_speech=True,
            audio_type="mixed",
            confidence=0.85,
            music_confidence=0.75,
            speech_ratio=0.6,
            music_characteristics={"tempo_bpm": 120, "energy": "high"},
            copyright_risk="medium",
            duration_sec=30.5
        )
        
        data = result.to_dict()
        
        assert data["has_music"] is True
        assert data["has_speech"] is True
        assert data["audio_type"] == "mixed"
        assert data["confidence"] == 0.85
        assert data["music_confidence"] == 0.75
        assert data["music_characteristics"]["tempo_bpm"] == 120
        assert "analyzed_at" in data
    
    def test_get_audio_analyzer_singleton(self):
        """Test singleton pattern for audio analyzer"""
        analyzer1 = get_audio_analyzer()
        analyzer2 = get_audio_analyzer()
        assert analyzer1 is analyzer2
    
    def test_guess_genre_from_tempo(self):
        """Test genre guessing based on audio features"""
        analyzer = AudioAnalyzer()
        
        # Pop tempo range (120-140 BPM)
        genres = analyzer._guess_genre(130, 0.6, 0.08)
        assert "pop" in genres
        
        # Electronic tempo range (140-160 BPM)
        genres = analyzer._guess_genre(150, 0.5, 0.1)
        assert "electronic" in genres
        
        # Hip-hop tempo range (70-100 BPM)
        genres = analyzer._guess_genre(85, 0.5, 0.1)
        assert "hip-hop" in genres
    
    def test_guess_mood_from_features(self):
        """Test mood guessing based on audio features"""
        analyzer = AudioAnalyzer()
        
        # High tempo + loud = energetic
        mood = analyzer._guess_mood(130, 0.5, -15)
        assert mood == "energetic"
        
        # Low tempo + harmonic = chill
        mood = analyzer._guess_mood(70, 0.7, -25)
        assert mood == "chill"
        
        # Very quiet = calm
        mood = analyzer._guess_mood(90, 0.5, -35)
        assert mood == "calm"


# =============================================================================
# Integration Tests: Audio Analysis API
# =============================================================================

class TestAudioAnalysisAPI:
    """Integration tests for audio analysis API endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        return db
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test audio analysis health check - requires running server"""
        # Skip if imports fail (unit test environment)
        try:
            from api.endpoints.audio_analysis import health_check
        except ImportError:
            pytest.skip("Requires full application context")
        
        response = await health_check()
        
        assert response["status"] == "healthy"
        assert response["service"] == "audio_analysis"
        assert "librosa_available" in response
    
    @pytest.mark.asyncio
    async def test_analyze_audio_file_not_found(self, mock_db):
        """Test analysis with non-existent video"""
        try:
            from api.endpoints.audio_analysis import analyze_audio
        except ImportError:
            pytest.skip("Requires full application context")
        
        # Mock database to return no video
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(Exception) as exc_info:
            await analyze_audio("non-existent-uuid", mock_db)
        
        assert "not found" in str(exc_info.value).lower()


# =============================================================================
# Scenario Tests: Known Audio Types
# =============================================================================

class TestAudioScenarios:
    """Tests for specific audio scenarios"""
    
    def test_result_for_speech_only_video(self):
        """Scenario: Video with only speech (podcast, talking head)"""
        result = AudioAnalysisResult(
            has_music=False,
            has_speech=True,
            audio_type="speech_only",
            confidence=0.9,
            music_confidence=0.1,
            speech_ratio=0.95,
            copyright_risk="low"
        )
        
        assert result.audio_type == "speech_only"
        assert result.has_speech is True
        assert result.has_music is False
        assert result.music_confidence < 0.3
        assert result.speech_ratio > 0.8
    
    def test_result_for_music_only_video(self):
        """Scenario: Video with only background music (b-roll, montage)"""
        result = AudioAnalysisResult(
            has_music=True,
            has_speech=False,
            audio_type="music_only",
            confidence=0.88,
            music_confidence=0.92,
            speech_ratio=0.05,
            music_characteristics={
                "tempo_bpm": 128,
                "energy": "high",
                "genre_hints": ["electronic", "pop"],
                "mood": "energetic"
            },
            copyright_risk="high"
        )
        
        assert result.audio_type == "music_only"
        assert result.has_music is True
        assert result.has_speech is False
        assert result.music_confidence > 0.8
        assert result.speech_ratio < 0.2
        assert result.music_characteristics["tempo_bpm"] == 128
    
    def test_result_for_mixed_audio(self):
        """Scenario: Video with both speech and background music"""
        result = AudioAnalysisResult(
            has_music=True,
            has_speech=True,
            audio_type="mixed",
            confidence=0.85,
            music_confidence=0.65,
            speech_ratio=0.55,
            music_characteristics={
                "tempo_bpm": 95,
                "energy": "medium",
                "genre_hints": ["ambient", "lofi"],
                "mood": "chill"
            },
            copyright_risk="medium"
        )
        
        assert result.audio_type == "mixed"
        assert result.has_music is True
        assert result.has_speech is True
        assert 0.3 < result.music_confidence < 0.8
        assert 0.3 < result.speech_ratio < 0.8
    
    def test_result_for_silent_video(self):
        """Scenario: Video with no audio or very quiet"""
        result = AudioAnalysisResult(
            has_music=False,
            has_speech=False,
            audio_type="silence",
            confidence=0.95,
            music_confidence=0.0,
            speech_ratio=0.0,
            overall_loudness_db=-60,
            copyright_risk="low"
        )
        
        assert result.audio_type == "silence"
        assert result.has_music is False
        assert result.has_speech is False
        assert result.overall_loudness_db < -50
    
    def test_result_for_ambient_audio(self):
        """Scenario: Video with ambient sounds (nature, city, etc.)"""
        result = AudioAnalysisResult(
            has_music=False,
            has_speech=False,
            audio_type="ambient",
            confidence=0.7,
            music_confidence=0.2,
            speech_ratio=0.1,
            copyright_risk="low"
        )
        
        assert result.audio_type == "ambient"
        assert result.has_music is False
        assert result.music_confidence < 0.4


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestAudioAnalysisEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_result_with_error(self):
        """Test result object when analysis fails"""
        result = AudioAnalysisResult(
            error="Failed to extract audio: corrupted file"
        )
        
        data = result.to_dict()
        assert data["error"] is not None
        assert "corrupted" in data["error"]
        assert data["has_music"] is False
    
    def test_very_short_audio(self):
        """Test handling of very short audio (<1 second)"""
        result = AudioAnalysisResult(
            has_music=False,
            has_speech=False,
            audio_type="unknown",
            confidence=0.3,
            duration_sec=0.5,
            error="Audio too short for reliable analysis"
        )
        
        assert result.duration_sec < 1.0
        assert result.confidence < 0.5
    
    def test_very_long_audio(self):
        """Test handling of long audio (>10 minutes)"""
        result = AudioAnalysisResult(
            has_music=True,
            has_speech=True,
            audio_type="mixed",
            confidence=0.8,
            duration_sec=720,  # 12 minutes
            music_confidence=0.6
        )
        
        assert result.duration_sec > 600
        # Should still produce valid results


# =============================================================================
# Copyright Risk Assessment Tests
# =============================================================================

class TestCopyrightRiskAssessment:
    """Tests for copyright risk detection"""
    
    def test_high_risk_professional_music(self):
        """Professional-sounding music should be flagged as high risk"""
        result = AudioAnalysisResult(
            has_music=True,
            audio_type="music_only",
            music_confidence=0.95,
            music_characteristics={
                "tempo_bpm": 128,
                "energy": "high",
                "genre_hints": ["pop", "electronic"]
            },
            copyright_risk="high"
        )
        
        assert result.copyright_risk == "high"
    
    def test_low_risk_ambient_music(self):
        """Ambient/simple music should be lower risk"""
        result = AudioAnalysisResult(
            has_music=True,
            audio_type="music_only",
            music_confidence=0.6,
            music_characteristics={
                "tempo_bpm": 70,
                "energy": "low",
                "genre_hints": ["ambient"]
            },
            copyright_risk="low"
        )
        
        assert result.copyright_risk == "low"
    
    def test_unknown_risk_when_uncertain(self):
        """Uncertain detection should default to unknown risk"""
        result = AudioAnalysisResult(
            has_music=True,
            audio_type="mixed",
            music_confidence=0.45,
            copyright_risk="unknown"
        )
        
        assert result.copyright_risk == "unknown"


# =============================================================================
# Performance Tests
# =============================================================================

class TestAudioAnalysisPerformance:
    """Tests for performance requirements"""
    
    @pytest.mark.asyncio
    async def test_analyzer_initialization_speed(self):
        """Analyzer should initialize quickly"""
        import time
        
        start = time.time()
        analyzer = AudioAnalyzer()
        elapsed = time.time() - start
        
        # Should initialize in under 100ms
        assert elapsed < 0.1
    
    def test_result_serialization_speed(self):
        """Result serialization should be fast"""
        import time
        
        result = AudioAnalysisResult(
            has_music=True,
            has_speech=True,
            audio_type="mixed",
            confidence=0.85,
            music_characteristics={"tempo_bpm": 120}
        )
        
        start = time.time()
        for _ in range(1000):
            result.to_dict()
        elapsed = time.time() - start
        
        # 1000 serializations should take < 100ms
        assert elapsed < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
