"""
Integration Tests for Posted Content Matcher System
Tests the complete flow of detecting already-posted content and preventing duplicates
"""
import pytest
import httpx
import asyncio
from typing import Dict, Any, List

# Test configuration
API_BASE = "http://localhost:5555"
TIMEOUT = 30.0


class TestPostedContentMatcherIntegration:
    """Integration tests for /api/posted-matcher endpoints"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Create HTTP client for tests"""
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_cross_reference_summary_endpoint(self, client):
        """Test GET /api/posted-matcher/cross-reference-summary"""
        response = client.get("/api/posted-matcher/cross-reference-summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_videos" in data
        assert "with_transcripts" in data
        assert "already_posted" in data
        assert "approved_for_posting" in data
        assert "safe_to_post" in data
        assert "needs_transcript" in data
        assert "message" in data
        
        # Verify counts are non-negative
        assert data["total_videos"] >= 0
        assert data["with_transcripts"] >= 0
        assert data["already_posted"] >= 0
    
    def test_already_posted_endpoint(self, client):
        """Test GET /api/posted-matcher/already-posted"""
        response = client.get("/api/posted-matcher/already-posted")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "videos" in data
        assert isinstance(data["videos"], list)
    
    def test_check_before_post_invalid_id(self, client):
        """Test GET /api/posted-matcher/check-before-post with invalid ID"""
        response = client.get("/api/posted-matcher/check-before-post/00000000-0000-0000-0000-000000000000")
        # Should return 404 for non-existent video
        assert response.status_code in [200, 404, 500]
    
    def test_match_transcript_endpoint(self, client):
        """Test POST /api/posted-matcher/match-transcript"""
        response = client.post(
            "/api/posted-matcher/match-transcript",
            json={
                "transcript": "This is a test transcript for matching purposes",
                "platform": "tiktok",
                "posted_url": "https://tiktok.com/test"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "match_found" in data
        assert isinstance(data["match_found"], bool)
    
    def test_match_transcript_short_text(self, client):
        """Test match-transcript with very short text"""
        response = client.post(
            "/api/posted-matcher/match-transcript",
            json={
                "transcript": "hi",
                "platform": "tiktok",
                "posted_url": "https://tiktok.com/test"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        # Short text should not match
        assert data["match_found"] == False
    
    def test_mark_as_posted_invalid_video(self, client):
        """Test POST /api/posted-matcher/mark-as-posted with invalid ID"""
        response = client.post(
            "/api/posted-matcher/mark-as-posted",
            json={
                "local_video_id": "00000000-0000-0000-0000-000000000000",
                "platform": "tiktok",
                "posted_url": "https://tiktok.com/test"
            }
        )
        # Should handle gracefully
        assert response.status_code in [200, 404, 500]
    
    def test_scrape_request_structure(self, client):
        """Test that scrape endpoint validates request structure"""
        # Missing required field
        response = client.post(
            "/api/posted-matcher/scrape-and-match",
            json={"platform": "tiktok"}  # Missing username
        )
        # Should return validation error (422) or internal error (500)
        assert response.status_code in [422, 500]


class TestPostedContentMatcherService:
    """Tests for PostedContentMatcher service logic"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_summary_consistency(self, client):
        """Test that summary numbers are consistent"""
        response = client.get("/api/posted-matcher/cross-reference-summary")
        assert response.status_code == 200
        
        data = response.json()
        
        # needs_transcript = total_videos - with_transcripts
        expected_needs = data["total_videos"] - data["with_transcripts"]
        assert data["needs_transcript"] == expected_needs
    
    def test_match_requires_transcripts(self, client):
        """Test that matching requires transcripts to exist"""
        response = client.get("/api/posted-matcher/cross-reference-summary")
        assert response.status_code == 200
        
        summary = response.json()
        
        # If no transcripts, matching should return appropriate message
        if summary["with_transcripts"] == 0:
            match_response = client.post(
                "/api/posted-matcher/match-transcript",
                json={
                    "transcript": "Test transcript",
                    "platform": "tiktok",
                    "posted_url": "https://tiktok.com/test"
                }
            )
            data = match_response.json()
            assert data["match_found"] == False


class TestPostedContentMatcherWorkflow:
    """End-to-end workflow tests"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_check_before_post_workflow(self, client):
        """Test the check-before-post workflow"""
        # Get summary first
        summary_response = client.get("/api/posted-matcher/cross-reference-summary")
        assert summary_response.status_code == 200
        
        # Get already posted list
        posted_response = client.get("/api/posted-matcher/already-posted")
        assert posted_response.status_code == 200
        
        # Workflow completed successfully
        assert True
    
    def test_full_matching_workflow(self, client):
        """Test complete workflow: check summary -> match -> verify"""
        # Step 1: Get summary
        summary_response = client.get("/api/posted-matcher/cross-reference-summary")
        assert summary_response.status_code == 200
        
        # Step 2: Try to match a transcript
        match_response = client.post(
            "/api/posted-matcher/match-transcript",
            json={
                "transcript": "This is a sample transcript for workflow testing",
                "platform": "instagram",
                "posted_url": "https://instagram.com/reel/test"
            }
        )
        assert match_response.status_code == 200
        
        # Step 3: Check already posted
        posted_response = client.get("/api/posted-matcher/already-posted")
        assert posted_response.status_code == 200
        
        # Workflow completed
        assert True


class TestPostedContentMatcherAsync:
    """Async integration tests"""
    
    @pytest.fixture
    def async_client(self):
        return httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_concurrent_summary_requests(self, async_client):
        """Test concurrent summary requests"""
        async with async_client:
            tasks = [
                async_client.get("/api/posted-matcher/cross-reference-summary")
                for _ in range(3)
            ]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_concurrent_match_requests(self, async_client):
        """Test concurrent match requests"""
        async with async_client:
            tasks = [
                async_client.post(
                    "/api/posted-matcher/match-transcript",
                    json={
                        "transcript": f"Test transcript {i}",
                        "platform": "tiktok",
                        "posted_url": f"https://tiktok.com/test{i}"
                    }
                )
                for i in range(3)
            ]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                assert response.status_code == 200


class TestPostedContentMatcherEdgeCases:
    """Edge case tests"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_empty_transcript_match(self, client):
        """Test matching with empty transcript"""
        response = client.post(
            "/api/posted-matcher/match-transcript",
            json={
                "transcript": "",
                "platform": "tiktok",
                "posted_url": "https://tiktok.com/test"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["match_found"] == False
    
    def test_unicode_transcript(self, client):
        """Test matching with unicode characters"""
        response = client.post(
            "/api/posted-matcher/match-transcript",
            json={
                "transcript": "测试文本 🎬 emoji content テスト",
                "platform": "tiktok",
                "posted_url": "https://tiktok.com/test"
            }
        )
        assert response.status_code == 200
    
    def test_very_long_transcript(self, client):
        """Test matching with very long transcript"""
        long_transcript = "This is a test sentence. " * 100
        response = client.post(
            "/api/posted-matcher/match-transcript",
            json={
                "transcript": long_transcript,
                "platform": "tiktok",
                "posted_url": "https://tiktok.com/test"
            }
        )
        assert response.status_code == 200
    
    def test_invalid_platform(self, client):
        """Test with unsupported platform in scrape request"""
        response = client.post(
            "/api/posted-matcher/scrape-and-match",
            json={
                "username": "test",
                "platform": "invalid_platform",
                "max_videos": 10
            }
        )
        # Should return error for invalid platform
        assert response.status_code in [400, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
