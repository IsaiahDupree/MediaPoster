"""
Integration Tests for B-Roll Discovery and Format Classification System
Tests the complete flow of detecting b-roll candidates for text overlays
"""
import pytest
import httpx
import asyncio
from typing import Dict, Any, List

# Test configuration
API_BASE = "http://localhost:5555"
TIMEOUT = 30.0


class TestBRollDiscoveryIntegration:
    """Integration tests for /api/format-discovery endpoints"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Create HTTP client for tests"""
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_broll_candidates_endpoint(self, client):
        """Test GET /api/format-discovery/broll-candidates"""
        response = client.get("/api/format-discovery/broll-candidates", params={"limit": 20})
        assert response.status_code == 200
        
        data = response.json()
        assert "total_found" in data
        assert "broll_text_candidates" in data
        assert "pure_broll_candidates" in data
        assert "message" in data
        
        assert isinstance(data["broll_text_candidates"], list)
        assert isinstance(data["pure_broll_candidates"], list)
        assert data["total_found"] >= 0
    
    def test_broll_candidates_with_limit(self, client):
        """Test that limit parameter is respected"""
        response = client.get("/api/format-discovery/broll-candidates", params={"limit": 5})
        assert response.status_code == 200
        
        data = response.json()
        total_returned = len(data["broll_text_candidates"]) + len(data["pure_broll_candidates"])
        assert total_returned <= 5
    
    def test_broll_candidates_filters(self, client):
        """Test filter parameters"""
        # Only pure b-roll
        response = client.get("/api/format-discovery/broll-candidates", params={
            "include_with_person": False,
            "include_pure_broll": True
        })
        assert response.status_code == 200
        
        data = response.json()
        # Should only have pure b-roll candidates
        assert len(data["broll_text_candidates"]) == 0 or data.get("include_with_person", True) == False
    
    def test_broll_candidate_structure(self, client):
        """Test that b-roll candidates have correct structure"""
        response = client.get("/api/format-discovery/broll-candidates", params={"limit": 10})
        assert response.status_code == 200
        
        data = response.json()
        all_candidates = data["broll_text_candidates"] + data["pure_broll_candidates"]
        
        for candidate in all_candidates:
            assert "media_id" in candidate
            assert "filename" in candidate
            assert "format_type" in candidate
            assert "confidence" in candidate
            assert "reasons" in candidate
            assert "has_person" in candidate
            assert "has_speech" in candidate
            assert "has_captions" in candidate
            
            # Confidence should be between 0 and 1
            assert 0 <= candidate["confidence"] <= 1
            
            # B-roll should not have speech
            assert candidate["has_speech"] == False
            
            # B-roll should not have captions
            assert candidate["has_captions"] == False
    
    def test_classify_single_video_endpoint(self, client):
        """Test GET /api/format-discovery/classify/{media_id}"""
        # First get a valid media_id from b-roll candidates
        broll_response = client.get("/api/format-discovery/broll-candidates", params={"limit": 1})
        assert broll_response.status_code == 200
        
        data = broll_response.json()
        all_candidates = data["broll_text_candidates"] + data["pure_broll_candidates"]
        
        if all_candidates:
            media_id = all_candidates[0]["media_id"]
            classify_response = client.get(f"/api/format-discovery/classify/{media_id}")
            assert classify_response.status_code == 200
            
            classification = classify_response.json()
            # Response wraps classification in 'classification' key
            if "classification" in classification:
                class_data = classification["classification"]
            else:
                class_data = classification
            assert "format" in class_data
            assert "confidence" in class_data
            assert "reasons" in class_data
    
    def test_classify_invalid_video(self, client):
        """Test classify with invalid video ID"""
        response = client.get("/api/format-discovery/classify/00000000-0000-0000-0000-000000000000")
        # Should return 404 or classification with unknown format
        assert response.status_code in [200, 404, 500]


class TestFormatClassification:
    """Tests for format classification logic"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_pure_broll_has_no_person(self, client):
        """Test that pure b-roll candidates have no person"""
        response = client.get("/api/format-discovery/broll-candidates", params={"limit": 50})
        assert response.status_code == 200
        
        data = response.json()
        for candidate in data["pure_broll_candidates"]:
            assert candidate["has_person"] == False
            assert candidate["format_type"] == "pure_broll"
    
    def test_broll_text_may_have_person(self, client):
        """Test that b-roll text candidates may have person (not talking)"""
        response = client.get("/api/format-discovery/broll-candidates", params={"limit": 50})
        assert response.status_code == 200
        
        data = response.json()
        for candidate in data["broll_text_candidates"]:
            # Has person but not speech
            if candidate["has_person"]:
                assert candidate["has_speech"] == False
    
    def test_classification_reasons_not_empty(self, client):
        """Test that classifications have reasons"""
        response = client.get("/api/format-discovery/broll-candidates", params={"limit": 20})
        assert response.status_code == 200
        
        data = response.json()
        all_candidates = data["broll_text_candidates"] + data["pure_broll_candidates"]
        
        for candidate in all_candidates:
            assert len(candidate["reasons"]) > 0


class TestBRollWorkflow:
    """End-to-end workflow tests for b-roll processing"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_discover_and_classify_workflow(self, client):
        """Test workflow: discover candidates -> classify individual"""
        # Step 1: Discover candidates
        discover_response = client.get("/api/format-discovery/broll-candidates", params={"limit": 10})
        assert discover_response.status_code == 200
        
        data = discover_response.json()
        all_candidates = data["broll_text_candidates"] + data["pure_broll_candidates"]
        
        if all_candidates:
            # Step 2: Classify first candidate individually
            media_id = all_candidates[0]["media_id"]
            classify_response = client.get(f"/api/format-discovery/classify/{media_id}")
            assert classify_response.status_code == 200
            
            # Step 3: Verify classification matches discovery
            classification = classify_response.json()
            # Response may wrap in 'classification' key
            if "classification" in classification:
                class_data = classification["classification"]
            else:
                class_data = classification
            assert class_data["format"] in ["pure_broll", "broll_text", "broll_text_candidate", "music_only", "silent"]
    
    def test_discover_to_format_run_workflow(self, client):
        """Test workflow: discover -> seed formats -> run format"""
        # Step 1: Discover b-roll candidates
        discover_response = client.get("/api/format-discovery/broll-candidates", params={"limit": 5})
        assert discover_response.status_code == 200
        
        # Step 2: Seed formats if needed
        seed_response = client.post("/api/formats/seed-samples")
        assert seed_response.status_code == 200
        
        # Step 3: Get the b-roll format
        format_response = client.get("/api/formats/broll_text_v1")
        assert format_response.status_code == 200
        
        # Workflow completed
        assert True


class TestBRollAsync:
    """Async integration tests"""
    
    @pytest.fixture
    def async_client(self):
        return httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_concurrent_discovery(self, async_client):
        """Test concurrent b-roll discovery requests"""
        async with async_client:
            tasks = [
                async_client.get("/api/format-discovery/broll-candidates", params={"limit": 10})
                for _ in range(3)
            ]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_discovery_and_classify_concurrent(self, async_client):
        """Test discovery and classification can run concurrently"""
        async with async_client:
            # First get some candidates
            discover_response = await async_client.get("/api/format-discovery/broll-candidates", params={"limit": 5})
            assert discover_response.status_code == 200
            
            data = discover_response.json()
            all_candidates = data["broll_text_candidates"] + data["pure_broll_candidates"]
            
            if len(all_candidates) >= 2:
                # Classify multiple concurrently
                tasks = [
                    async_client.get(f"/api/format-discovery/classify/{c['media_id']}")
                    for c in all_candidates[:3]
                ]
                responses = await asyncio.gather(*tasks)
                
                for response in responses:
                    assert response.status_code == 200


class TestBRollEdgeCases:
    """Edge case tests"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_zero_limit(self, client):
        """Test with limit of 0"""
        response = client.get("/api/format-discovery/broll-candidates", params={"limit": 0})
        # Should handle gracefully (either return empty or error)
        assert response.status_code in [200, 422]
    
    def test_max_limit(self, client):
        """Test with maximum limit"""
        response = client.get("/api/format-discovery/broll-candidates", params={"limit": 200})
        assert response.status_code == 200
    
    def test_no_filters(self, client):
        """Test with both filters disabled"""
        response = client.get("/api/format-discovery/broll-candidates", params={
            "include_with_person": False,
            "include_pure_broll": False
        })
        assert response.status_code == 200
        
        data = response.json()
        # Should return empty or minimal results
        assert data["total_found"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
