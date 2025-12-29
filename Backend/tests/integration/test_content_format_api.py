"""
Integration tests for Content Format Detection API.

Tests the /api/content-format endpoints.
"""
import pytest
import httpx
from typing import Dict, Any

BASE_URL = "http://localhost:5555"


class TestContentFormatAPI:
    """Integration tests for content format API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create HTTP client"""
        return httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    # === STATS ENDPOINT ===
    
    def test_get_stats(self, client):
        """GET /api/content-format/stats should return format statistics"""
        response = client.get("/api/content-format/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_videos" in data
        assert "processed" in data
        assert "unprocessed" in data
        assert "by_format" in data
        assert "by_suggested_use" in data
        
        # Verify counts are integers
        assert isinstance(data["total_videos"], int)
        assert isinstance(data["processed"], int)
        
        # by_format should be a dict with format names
        assert isinstance(data["by_format"], dict)
    
    def test_stats_format_breakdown(self, client):
        """Stats should include format breakdown with counts and confidence"""
        response = client.get("/api/content-format/stats")
        data = response.json()
        
        for format_name, info in data["by_format"].items():
            assert "count" in info
            assert "avg_confidence" in info
            assert isinstance(info["count"], int)
            assert isinstance(info["avg_confidence"], (int, float))
    
    # === FORMATS ENDPOINT ===
    
    def test_list_format_types(self, client):
        """GET /api/content-format/formats should list all format types"""
        response = client.get("/api/content-format/formats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "formats" in data
        assert len(data["formats"]) >= 10
        
        # Each format should have value, label, description
        for fmt in data["formats"]:
            assert "value" in fmt
            assert "label" in fmt
            assert "description" in fmt
    
    def test_format_types_include_expected(self, client):
        """Format types should include common formats"""
        response = client.get("/api/content-format/formats")
        data = response.json()
        
        format_values = [f["value"] for f in data["formats"]]
        
        expected_formats = [
            "talking_head",
            "interview",
            "broll_scenic",
            "broll_action",
            "broll_people",
            "animated",
            "screen_recording"
        ]
        
        for expected in expected_formats:
            assert expected in format_values, f"Missing format: {expected}"
    
    # === LIST ENDPOINT ===
    
    def test_list_all_formats(self, client):
        """GET /api/content-format/list should return videos with format data"""
        response = client.get("/api/content-format/list", params={"limit": 10})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "videos" in data
        assert isinstance(data["videos"], list)
    
    def test_list_by_specific_format(self, client):
        """Filter list by specific format type"""
        response = client.get(
            "/api/content-format/list",
            params={"format_type": "talking_head", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned videos should be talking_head
        for video in data["videos"]:
            assert video["format"] == "talking_head"
    
    def test_list_video_structure(self, client):
        """List should return proper video structure"""
        response = client.get("/api/content-format/list", params={"limit": 5})
        data = response.json()
        
        if data["videos"]:
            video = data["videos"][0]
            
            # Required fields
            assert "id" in video
            assert "file_name" in video
            assert "format" in video
            assert "confidence" in video
            
            # Optional but expected fields
            assert "suggested_use" in video
            assert "best_platforms" in video
    
    def test_list_respects_limit(self, client):
        """List should respect limit parameter"""
        response = client.get("/api/content-format/list", params={"limit": 3})
        data = response.json()
        
        assert len(data["videos"]) <= 3
    
    # === DETECT SINGLE VIDEO ===
    
    def test_detect_nonexistent_video(self, client):
        """Detecting format for nonexistent video should return 404"""
        response = client.get("/api/content-format/detect/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 404
    
    def test_detect_returns_format_details(self, client):
        """Detect endpoint should return comprehensive format details"""
        # First get a video ID from the list
        list_response = client.get("/api/content-format/list", params={"limit": 1})
        videos = list_response.json().get("videos", [])
        
        if not videos:
            pytest.skip("No videos available for testing")
        
        video_id = videos[0]["id"]
        response = client.get(f"/api/content-format/detect/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "video_id" in data
        assert "primary_format" in data
        assert "confidence" in data
        assert "attributes" in data
        assert "best_platforms" in data
        assert "suggested_use" in data
        assert "reasons" in data
    
    def test_detect_attributes_structure(self, client):
        """Detect should return proper attributes structure"""
        list_response = client.get("/api/content-format/list", params={"limit": 1})
        videos = list_response.json().get("videos", [])
        
        if not videos:
            pytest.skip("No videos available for testing")
        
        video_id = videos[0]["id"]
        response = client.get(f"/api/content-format/detect/{video_id}")
        data = response.json()
        
        attrs = data["attributes"]
        
        # Verify attribute fields
        assert "has_speech" in attrs
        assert "has_music" in attrs
        assert "has_people" in attrs
        assert "people_speaking" in attrs
        
        # Types should be boolean
        assert isinstance(attrs["has_speech"], bool)
        assert isinstance(attrs["has_people"], bool)
    
    # === DETECT ALL ENDPOINT ===
    
    def test_detect_all_dry_run(self, client):
        """POST /api/content-format/detect-all should process videos"""
        # Use only_unprocessed=true to avoid reprocessing
        response = client.post(
            "/api/content-format/detect-all",
            params={"limit": 5, "only_unprocessed": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "processed" in data
        assert "format_distribution" in data
        assert isinstance(data["processed"], int)
        assert isinstance(data["format_distribution"], dict)
    
    def test_detect_all_respects_limit(self, client):
        """Detect all should respect limit parameter"""
        response = client.post(
            "/api/content-format/detect-all",
            params={"limit": 2, "only_unprocessed": True}
        )
        
        data = response.json()
        # Processed should be <= limit
        assert data["processed"] <= 2
    
    # === FORMAT VALIDATION ===
    
    def test_format_values_are_valid(self, client):
        """All returned format values should be valid enum values"""
        valid_formats = [
            "talking_head", "interview", "broll_scenic", "broll_action",
            "broll_people", "animated", "screen_recording", "slideshow",
            "music_video", "montage", "documentary", "reaction",
            "tutorial_hands", "live_event", "meme_content", "unknown"
        ]
        
        response = client.get("/api/content-format/list", params={"limit": 50})
        data = response.json()
        
        for video in data["videos"]:
            assert video["format"] in valid_formats, f"Invalid format: {video['format']}"
    
    def test_suggested_use_values_valid(self, client):
        """Suggested use values should be valid"""
        valid_uses = ["primary", "overlay", "cutaway", "standalone", "supplemental"]
        
        response = client.get("/api/content-format/list", params={"limit": 50})
        data = response.json()
        
        for video in data["videos"]:
            if video.get("suggested_use"):
                assert video["suggested_use"] in valid_uses
    
    # === CONFIDENCE TESTS ===
    
    def test_confidence_in_valid_range(self, client):
        """Confidence scores should be between 0 and 1"""
        response = client.get("/api/content-format/list", params={"limit": 50})
        data = response.json()
        
        for video in data["videos"]:
            if video.get("confidence") is not None:
                assert 0 <= video["confidence"] <= 1.0
    
    # === PLATFORM RECOMMENDATIONS ===
    
    def test_best_platforms_are_valid(self, client):
        """Best platforms should be valid platform names"""
        valid_platforms = [
            "tiktok", "instagram", "youtube", "twitter", 
            "threads", "linkedin", "facebook", "spotify"
        ]
        
        response = client.get("/api/content-format/list", params={"limit": 20})
        data = response.json()
        
        for video in data["videos"]:
            for platform in video.get("best_platforms", []):
                assert platform in valid_platforms


class TestContentFormatIntegration:
    """Integration tests for format detection workflow"""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    def test_format_detection_workflow(self, client):
        """Test complete format detection workflow"""
        # 1. Get stats
        stats = client.get("/api/content-format/stats").json()
        initial_processed = stats["processed"]
        
        # 2. List formats
        formats = client.get("/api/content-format/formats").json()
        assert len(formats["formats"]) > 0
        
        # 3. List videos by format
        for fmt in ["talking_head", "broll_scenic"]:
            response = client.get(
                "/api/content-format/list",
                params={"format_type": fmt, "limit": 5}
            )
            assert response.status_code == 200
    
    def test_b_roll_formats_have_correct_use(self, client):
        """B-roll formats should have overlay/cutaway suggested use"""
        broll_formats = ["broll_scenic", "broll_action", "broll_people"]
        
        for fmt in broll_formats:
            response = client.get(
                "/api/content-format/list",
                params={"format_type": fmt, "limit": 10}
            )
            data = response.json()
            
            for video in data["videos"]:
                assert video["suggested_use"] in ["overlay", "cutaway"]
    
    def test_talking_head_has_primary_use(self, client):
        """Talking head format should have primary suggested use"""
        response = client.get(
            "/api/content-format/list",
            params={"format_type": "talking_head", "limit": 10}
        )
        data = response.json()
        
        for video in data["videos"]:
            assert video["suggested_use"] == "primary"


# Run tests with: pytest tests/integration/test_content_format_api.py -v
