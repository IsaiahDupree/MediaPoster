"""
Integration Tests for Duplicate Detection System
Tests the complete flow of finding duplicate videos based on transcript similarity
"""
import pytest
import httpx
import asyncio
from typing import Dict, Any, List

# Test configuration
API_BASE = "http://localhost:5555"
TIMEOUT = 30.0


class TestDuplicateDetectionIntegration:
    """Integration tests for /api/duplicates endpoints"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Create HTTP client for tests"""
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_find_duplicates_endpoint(self, client):
        """Test GET /api/duplicates/find returns duplicate pairs"""
        response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 0.85,
            "limit": 50
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "total_pairs" in data
        assert "duplicates" in data
        assert "message" in data
        assert isinstance(data["duplicates"], list)
        assert isinstance(data["total_pairs"], int)
    
    def test_find_duplicates_with_threshold(self, client):
        """Test that similarity threshold is respected"""
        # High threshold - fewer matches
        high_response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 0.95,
            "limit": 50
        })
        assert high_response.status_code == 200
        high_data = high_response.json()
        
        # Lower threshold - more matches (or equal)
        low_response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 0.70,
            "limit": 50
        })
        assert low_response.status_code == 200
        low_data = low_response.json()
        
        # Lower threshold should find >= same number of duplicates
        assert low_data["total_pairs"] >= high_data["total_pairs"]
    
    def test_find_exact_duplicates_endpoint(self, client):
        """Test GET /api/duplicates/exact finds exact matches"""
        response = client.get("/api/duplicates/exact", params={"limit": 50})
        assert response.status_code == 200
        
        data = response.json()
        assert "total_pairs" in data
        assert "duplicates" in data
        
        # All exact duplicates should have very high similarity
        for pair in data["duplicates"]:
            assert pair["similarity_score"] >= 0.99
    
    def test_duplicate_summary_endpoint(self, client):
        """Test GET /api/duplicates/summary returns overview"""
        response = client.get("/api/duplicates/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        assert "estimated_savings_mb" in data
        assert "recommendations" in data
        
        summary = data["summary"]
        assert "exact_matches" in summary
        assert "high_similarity" in summary
        assert "medium_similarity" in summary
    
    def test_duplicate_pair_structure(self, client):
        """Test that duplicate pairs have correct structure"""
        response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 0.70,
            "limit": 10
        })
        assert response.status_code == 200
        
        data = response.json()
        for pair in data["duplicates"]:
            # Check video1 structure
            assert "video1" in pair
            assert "id" in pair["video1"]
            assert "filename" in pair["video1"]
            assert "has_captions" in pair["video1"]
            
            # Check video2 structure
            assert "video2" in pair
            assert "id" in pair["video2"]
            assert "filename" in pair["video2"]
            assert "has_captions" in pair["video2"]
            
            # Check pair metadata
            assert "similarity_score" in pair
            assert "transcript_preview" in pair
            assert "recommendation" in pair
            
            # Similarity should be in valid range
            assert 0 <= pair["similarity_score"] <= 1
    
    def test_caption_status_protection(self, client):
        """Test that caption status protection works"""
        # With protection enabled (default)
        protected_response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 0.80,
            "compare_same_caption_status": True,
            "limit": 50
        })
        assert protected_response.status_code == 200
        protected_data = protected_response.json()
        
        # All pairs should have matching caption status
        for pair in protected_data["duplicates"]:
            v1_captions = pair["video1"]["has_captions"]
            v2_captions = pair["video2"]["has_captions"]
            assert v1_captions == v2_captions, "Caption status should match when protection is enabled"
    
    def test_marked_for_deletion_endpoint(self, client):
        """Test GET /api/duplicates/marked-for-deletion"""
        response = client.get("/api/duplicates/marked-for-deletion")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "videos" in data
        assert "total_size_mb" in data
        assert isinstance(data["videos"], list)


class TestDuplicateDetectionService:
    """Integration tests for DuplicateDetector service logic"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_recommendations_are_valid(self, client):
        """Test that recommendations are valid values"""
        response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 0.70,
            "limit": 20
        })
        assert response.status_code == 200
        
        valid_recommendations = {
            "keep_video1_has_captions",
            "keep_video2_has_captions",
            "keep_video1_longer",
            "keep_video2_longer",
            "review_manually"
        }
        
        data = response.json()
        for pair in data["duplicates"]:
            assert pair["recommendation"] in valid_recommendations
    
    def test_transcript_preview_is_truncated(self, client):
        """Test that transcript preview is reasonably truncated"""
        response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 0.70,
            "limit": 20
        })
        assert response.status_code == 200
        
        data = response.json()
        for pair in data["duplicates"]:
            preview = pair.get("transcript_preview", "")
            # Preview should be truncated (max ~103 chars with "...")
            assert len(preview) <= 200


class TestDuplicateMarkingWorkflow:
    """Tests for the mark-and-delete workflow"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_mark_for_deletion_with_empty_list(self, client):
        """Test marking empty list for deletion"""
        response = client.post(
            "/api/duplicates/mark-for-deletion",
            json={"video_ids": [], "soft_delete": True}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["marked_count"] == 0
    
    def test_mark_for_deletion_with_invalid_ids(self, client):
        """Test marking invalid IDs for deletion"""
        response = client.post(
            "/api/duplicates/mark-for-deletion",
            json={
                "video_ids": ["00000000-0000-0000-0000-000000000000"],
                "soft_delete": True
            }
        )
        # Should succeed but mark 0 or handle gracefully
        assert response.status_code in [200, 404, 500]
    
    def test_full_duplicate_workflow(self, client):
        """Test complete workflow: find -> review -> mark"""
        # Step 1: Find duplicates
        find_response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 0.85,
            "limit": 10
        })
        assert find_response.status_code == 200
        find_data = find_response.json()
        
        # Step 2: Get summary
        summary_response = client.get("/api/duplicates/summary")
        assert summary_response.status_code == 200
        
        # Step 3: Check marked for deletion
        marked_response = client.get("/api/duplicates/marked-for-deletion")
        assert marked_response.status_code == 200
        
        # Workflow completed successfully
        assert True


class TestDuplicateDetectionAsync:
    """Async integration tests for performance"""
    
    @pytest.fixture
    def async_client(self):
        return httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_concurrent_duplicate_searches(self, async_client):
        """Test concurrent duplicate searches"""
        async with async_client:
            tasks = [
                async_client.get("/api/duplicates/find", params={
                    "similarity_threshold": 0.80,
                    "limit": 20
                })
                for _ in range(3)
            ]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_summary_and_find_concurrent(self, async_client):
        """Test summary and find can run concurrently"""
        async with async_client:
            summary_task = async_client.get("/api/duplicates/summary")
            find_task = async_client.get("/api/duplicates/find", params={"limit": 10})
            
            summary_response, find_response = await asyncio.gather(summary_task, find_task)
            
            assert summary_response.status_code == 200
            assert find_response.status_code == 200


class TestDuplicateDetectionEdgeCases:
    """Edge case tests"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_very_high_threshold(self, client):
        """Test with threshold of 1.0 (exact match only)"""
        response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 1.0,
            "limit": 50
        })
        assert response.status_code == 200
    
    def test_minimum_threshold(self, client):
        """Test with minimum allowed threshold"""
        response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 0.5,
            "limit": 50
        })
        assert response.status_code == 200
    
    def test_limit_respects_maximum(self, client):
        """Test that limit is respected"""
        response = client.get("/api/duplicates/find", params={
            "similarity_threshold": 0.70,
            "limit": 5
        })
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["duplicates"]) <= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
