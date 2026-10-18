"""
Integration Tests for Audio Analysis (Background Music Detection) Service

Tests cover:
1. API endpoint integration tests against real running server
2. Tests with real media data
3. Database persistence verification
4. End-to-end workflow tests

Run with: pytest tests/integration/test_audio_analysis_integration.py -v
Requires: Backend server running on localhost:5555
"""

import pytest
import httpx
import asyncio
from typing import Dict, Any, Optional, List
import os
from datetime import datetime

# API Configuration
API_URL = os.getenv("API_URL", "http://localhost:5555")

# Known test media IDs - update these with actual media IDs from your database
# These should be categorized based on their known audio characteristics
KNOWN_MUSIC_MEDIA_IDS = [
    # Add media IDs known to have background music
]

NO_MUSIC_MEDIA_IDS = [
    # Add media IDs known to have NO background music (speech only, silence, etc.)
]

UNKNOWN_MEDIA_IDS = [
    # Add media IDs with unknown audio characteristics for testing
    "e960a544-7d67-46ca-8cca-ccbe2ff3b1bf",  # TABL2182.MOV - unknown
]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Create HTTP client for API calls"""
    return httpx.Client(base_url=API_URL, timeout=60.0)


@pytest.fixture
def async_api_client():
    """Create async HTTP client for API calls"""
    return httpx.AsyncClient(base_url=API_URL, timeout=60.0)


# =============================================================================
# Health Check Tests
# =============================================================================

class TestAudioAnalysisHealth:
    """Test audio analysis service health and availability"""
    
    def test_api_health_check(self, api_client):
        """Verify API is running and healthy"""
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_audio_analysis_health_endpoint(self, api_client):
        """Test audio analysis specific health check"""
        response = api_client.get("/api/analysis/audio/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "audio_analysis"
        assert "librosa_available" in data


# =============================================================================
# API Endpoint Integration Tests
# =============================================================================

class TestAudioAnalysisAPI:
    """Integration tests for audio analysis API endpoints"""
    
    def test_analyze_nonexistent_media(self, api_client):
        """Test analyzing non-existent media returns 404"""
        response = api_client.post("/api/analysis/audio/analyze/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", "").lower() or not data.get("success", True)
    
    def test_analyze_invalid_uuid(self, api_client):
        """Test analyzing with invalid UUID format"""
        response = api_client.post("/api/analysis/audio/analyze/not-a-valid-uuid")
        # Should return 400 or 422 for invalid format
        assert response.status_code in [400, 422, 404]
    
    def test_batch_analyze_empty_list(self, api_client):
        """Test batch analysis with empty list"""
        response = api_client.post(
            "/api/analysis/audio/batch",
            json={"media_ids": []}
        )
        # Should handle gracefully
        assert response.status_code in [200, 400]
    
    def test_get_analysis_nonexistent(self, api_client):
        """Test getting analysis for non-existent media"""
        response = api_client.get("/api/analysis/audio/00000000-0000-0000-0000-000000000000")
        assert response.status_code in [404, 200]  # 200 if returns empty result
    
    def test_list_analyzed_media(self, api_client):
        """Test listing media with audio analysis"""
        response = api_client.get("/api/analysis/audio/list")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)


# =============================================================================
# Real Media Tests - Known to Have Background Music
# =============================================================================

class TestKnownMusicMedia:
    """Tests for media known to have background music"""
    
    @pytest.mark.skipif(len(KNOWN_MUSIC_MEDIA_IDS) == 0, reason="No known music media IDs configured")
    @pytest.mark.parametrize("media_id", KNOWN_MUSIC_MEDIA_IDS)
    def test_detect_known_music(self, api_client, media_id):
        """Media known to have music should be detected"""
        response = api_client.post(f"/api/analysis/audio/analyze/{media_id}")
        
        if response.status_code == 404:
            pytest.skip(f"Media {media_id} not found in database")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert data.get("has_background_music") is True, f"Expected music to be detected in {media_id}"
        assert data.get("music_confidence", 0) > 0.5, "Music confidence should be high"
        assert data.get("audio_type") in ["music_only", "mixed"], f"Expected music audio type, got {data.get('audio_type')}"
    
    @pytest.mark.skipif(len(KNOWN_MUSIC_MEDIA_IDS) == 0, reason="No known music media IDs configured")
    def test_music_characteristics_present(self, api_client):
        """Music characteristics should be populated for media with music"""
        if not KNOWN_MUSIC_MEDIA_IDS:
            pytest.skip("No known music media IDs")
        
        media_id = KNOWN_MUSIC_MEDIA_IDS[0]
        response = api_client.post(f"/api/analysis/audio/analyze/{media_id}")
        
        if response.status_code == 404:
            pytest.skip(f"Media {media_id} not found")
        
        data = response.json()
        
        if data.get("has_background_music"):
            characteristics = data.get("music_characteristics", {})
            # Should have at least some characteristics
            assert characteristics, "Music characteristics should be present"
            # Common characteristics to check
            possible_keys = ["tempo_bpm", "energy", "mood", "genre_hints"]
            assert any(k in characteristics for k in possible_keys), "Should have some music characteristics"


# =============================================================================
# Real Media Tests - Known to Have NO Background Music
# =============================================================================

class TestNoMusicMedia:
    """Tests for media known to have NO background music"""
    
    @pytest.mark.skipif(len(NO_MUSIC_MEDIA_IDS) == 0, reason="No known no-music media IDs configured")
    @pytest.mark.parametrize("media_id", NO_MUSIC_MEDIA_IDS)
    def test_detect_no_music(self, api_client, media_id):
        """Media without music should be correctly identified"""
        response = api_client.post(f"/api/analysis/audio/analyze/{media_id}")
        
        if response.status_code == 404:
            pytest.skip(f"Media {media_id} not found in database")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert data.get("has_background_music") is False, f"Expected no music in {media_id}"
        assert data.get("audio_type") in ["speech_only", "silence", "ambient"], f"Unexpected audio type: {data.get('audio_type')}"
    
    @pytest.mark.skipif(len(NO_MUSIC_MEDIA_IDS) == 0, reason="No known no-music media IDs configured")
    def test_speech_detection(self, api_client):
        """Speech-only media should have high speech ratio"""
        if not NO_MUSIC_MEDIA_IDS:
            pytest.skip("No known no-music media IDs")
        
        media_id = NO_MUSIC_MEDIA_IDS[0]
        response = api_client.post(f"/api/analysis/audio/analyze/{media_id}")
        
        if response.status_code == 404:
            pytest.skip(f"Media {media_id} not found")
        
        data = response.json()
        
        if data.get("audio_type") == "speech_only":
            assert data.get("speech_ratio", 0) > 0.7, "Speech-only should have high speech ratio"


# =============================================================================
# Real Media Tests - Unknown Audio Characteristics
# =============================================================================

class TestUnknownMedia:
    """Tests for media with unknown audio characteristics"""
    
    @pytest.mark.skipif(len(UNKNOWN_MEDIA_IDS) == 0, reason="No unknown media IDs configured")
    @pytest.mark.parametrize("media_id", UNKNOWN_MEDIA_IDS)
    def test_analyze_unknown_media(self, api_client, media_id):
        """Unknown media should be analyzable and return valid results"""
        response = api_client.post(f"/api/analysis/audio/analyze/{media_id}")
        
        if response.status_code == 404:
            pytest.skip(f"Media {media_id} not found in database")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a valid response structure
        assert data.get("success") is True
        assert "has_background_music" in data
        assert "audio_type" in data
        assert "confidence" in data
        
        # Print results for manual verification
        print(f"\n--- Analysis Results for {media_id} ---")
        print(f"  Has Music: {data.get('has_background_music')}")
        print(f"  Audio Type: {data.get('audio_type')}")
        print(f"  Confidence: {data.get('confidence')}")
        print(f"  Music Confidence: {data.get('music_confidence')}")
        print(f"  Speech Ratio: {data.get('speech_ratio')}")
        if data.get("music_characteristics"):
            print(f"  Music Characteristics: {data.get('music_characteristics')}")
    
    @pytest.mark.skipif(len(UNKNOWN_MEDIA_IDS) == 0, reason="No unknown media IDs configured")
    def test_analysis_confidence_valid_range(self, api_client):
        """Confidence scores should be in valid 0-1 range"""
        if not UNKNOWN_MEDIA_IDS:
            pytest.skip("No unknown media IDs")
        
        media_id = UNKNOWN_MEDIA_IDS[0]
        response = api_client.post(f"/api/analysis/audio/analyze/{media_id}")
        
        if response.status_code == 404:
            pytest.skip(f"Media {media_id} not found")
        
        data = response.json()
        
        confidence = data.get("confidence")
        if confidence is not None:
            assert 0 <= confidence <= 1, f"Confidence {confidence} out of range"
        
        music_confidence = data.get("music_confidence")
        if music_confidence is not None:
            assert 0 <= music_confidence <= 1, f"Music confidence {music_confidence} out of range"
        
        speech_ratio = data.get("speech_ratio")
        if speech_ratio is not None:
            assert 0 <= speech_ratio <= 1, f"Speech ratio {speech_ratio} out of range"


# =============================================================================
# Database Persistence Tests
# =============================================================================

class TestDatabasePersistence:
    """Tests verifying analysis results are persisted to database"""
    
    @pytest.mark.skipif(len(UNKNOWN_MEDIA_IDS) == 0, reason="No media IDs configured")
    def test_analysis_persisted(self, api_client):
        """Analysis results should be saved to database"""
        if not UNKNOWN_MEDIA_IDS:
            pytest.skip("No media IDs")
        
        media_id = UNKNOWN_MEDIA_IDS[0]
        
        # Run analysis
        response = api_client.post(f"/api/analysis/audio/analyze/{media_id}")
        if response.status_code == 404:
            pytest.skip(f"Media {media_id} not found")
        
        assert response.status_code == 200
        
        # Retrieve analysis
        get_response = api_client.get(f"/api/analysis/audio/{media_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        # Should have analysis data
        assert data.get("has_background_music") is not None or data.get("audio_type") is not None
    
    @pytest.mark.skipif(len(UNKNOWN_MEDIA_IDS) == 0, reason="No media IDs configured")
    def test_analysis_timestamp_updated(self, api_client):
        """Analysis timestamp should be set after analysis"""
        if not UNKNOWN_MEDIA_IDS:
            pytest.skip("No media IDs")
        
        media_id = UNKNOWN_MEDIA_IDS[0]
        
        response = api_client.post(f"/api/analysis/audio/analyze/{media_id}")
        if response.status_code == 404:
            pytest.skip(f"Media {media_id} not found")
        
        data = response.json()
        
        # Should have analyzed_at timestamp
        analyzed_at = data.get("analyzed_at")
        assert analyzed_at is not None, "Analysis timestamp should be set"


# =============================================================================
# Audio Type Classification Tests
# =============================================================================

class TestAudioTypeClassification:
    """Tests for audio type classification accuracy"""
    
    def test_valid_audio_types(self, api_client):
        """All returned audio types should be valid"""
        valid_types = ["speech_only", "music_only", "mixed", "silence", "ambient", "unknown"]
        
        # Get any analyzed media
        response = api_client.get("/api/analysis/audio/list?limit=10")
        if response.status_code != 200:
            pytest.skip("List endpoint not available")
        
        data = response.json()
        items = data.get("items", data if isinstance(data, list) else [])
        
        for item in items:
            audio_type = item.get("audio_type")
            if audio_type:
                assert audio_type in valid_types, f"Invalid audio type: {audio_type}"


# =============================================================================
# Copyright Risk Assessment Tests
# =============================================================================

class TestCopyrightRiskAssessment:
    """Tests for copyright risk detection"""
    
    def test_copyright_risk_values(self, api_client):
        """Copyright risk should be one of expected values"""
        valid_risks = ["low", "medium", "high", "unknown"]
        
        response = api_client.get("/api/analysis/audio/list?limit=10")
        if response.status_code != 200:
            pytest.skip("List endpoint not available")
        
        data = response.json()
        items = data.get("items", data if isinstance(data, list) else [])
        
        for item in items:
            risk = item.get("copyright_risk")
            if risk:
                assert risk in valid_risks, f"Invalid copyright risk: {risk}"


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Performance and timeout tests"""
    
    def test_health_check_fast(self, api_client):
        """Health check should respond quickly"""
        import time
        
        start = time.time()
        response = api_client.get("/api/analysis/audio/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"Health check took {elapsed}s, expected < 1s"
    
    @pytest.mark.skipif(len(UNKNOWN_MEDIA_IDS) == 0, reason="No media IDs configured")
    def test_analysis_completes_within_timeout(self, api_client):
        """Analysis should complete within reasonable time"""
        import time
        
        if not UNKNOWN_MEDIA_IDS:
            pytest.skip("No media IDs")
        
        media_id = UNKNOWN_MEDIA_IDS[0]
        
        start = time.time()
        response = api_client.post(f"/api/analysis/audio/analyze/{media_id}")
        elapsed = time.time() - start
        
        if response.status_code == 404:
            pytest.skip(f"Media {media_id} not found")
        
        assert response.status_code == 200
        # Should complete within 60 seconds for most videos
        assert elapsed < 60, f"Analysis took {elapsed}s, expected < 60s"
        print(f"\nAnalysis completed in {elapsed:.2f}s")


# =============================================================================
# Async Tests
# =============================================================================

class TestAsyncOperations:
    """Tests for async operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, async_api_client):
        """Multiple concurrent health checks should succeed"""
        async with async_api_client as client:
            tasks = [
                client.get("/api/analysis/audio/health")
                for _ in range(5)
            ]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
