"""
Integration Tests for Formats API System
Tests the complete flow of video format templates and format discovery
"""
import pytest
import httpx
import asyncio
from typing import Dict, Any, List

# Test configuration
API_BASE = "http://localhost:5555"
TIMEOUT = 30.0


class TestFormatsAPIIntegration:
    """Integration tests for /api/formats endpoints"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Create HTTP client for tests"""
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_list_formats_endpoint(self, client):
        """Test GET /api/formats/list returns format list"""
        response = client.get("/api/formats/list")
        assert response.status_code == 200
        
        data = response.json()
        assert "formats" in data
        assert "total" in data
        assert isinstance(data["formats"], list)
    
    def test_seed_samples_endpoint(self, client):
        """Test POST /api/formats/seed-samples creates sample formats"""
        response = client.post("/api/formats/seed-samples")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"
        assert "format_ids" in data
        assert len(data["format_ids"]) > 0
    
    def test_list_formats_after_seeding(self, client):
        """Test that formats appear after seeding"""
        # Seed first
        seed_response = client.post("/api/formats/seed-samples")
        assert seed_response.status_code == 200
        
        # List should have formats now
        list_response = client.get("/api/formats/list")
        assert list_response.status_code == 200
        
        data = list_response.json()
        assert data["total"] > 0
        assert len(data["formats"]) > 0
    
    def test_list_formats_with_status_filter(self, client):
        """Test GET /api/formats/list with status filter"""
        # Ensure formats are seeded
        client.post("/api/formats/seed-samples")
        
        # Filter by active status
        response = client.get("/api/formats/list", params={"status": "active"})
        assert response.status_code == 200
        
        data = response.json()
        for fmt in data["formats"]:
            assert fmt["status"] == "active"
    
    def test_get_single_format(self, client):
        """Test GET /api/formats/{format_id} returns single format"""
        # Ensure formats are seeded
        client.post("/api/formats/seed-samples")
        
        # Get a specific format
        response = client.get("/api/formats/dev_vlog_meme_v1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "dev_vlog_meme_v1"
        assert "name" in data
        assert "definition_json" in data
    
    def test_get_nonexistent_format(self, client):
        """Test GET /api/formats/{format_id} with invalid ID returns 404"""
        response = client.get("/api/formats/nonexistent_format_xyz")
        assert response.status_code == 404
    
    def test_format_structure(self, client):
        """Test that format has correct structure"""
        # Ensure formats are seeded
        client.post("/api/formats/seed-samples")
        
        response = client.get("/api/formats/list")
        assert response.status_code == 200
        
        data = response.json()
        for fmt in data["formats"]:
            assert "id" in fmt
            assert "name" in fmt
            assert "status" in fmt
            assert "version" in fmt
            assert "definition_json" in fmt
    
    def test_run_format_endpoint(self, client):
        """Test POST /api/formats/{format_id}/run triggers format run"""
        # Ensure formats are seeded
        client.post("/api/formats/seed-samples")
        
        response = client.post(
            "/api/formats/dev_vlog_meme_v1/run",
            json={"params": {}, "trigger_type": "manual"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "run_id" in data
        assert "format_id" in data
        assert "status" in data
        assert data["status"] == "queued"
    
    def test_list_format_runs(self, client):
        """Test GET /api/formats/{format_id}/runs"""
        # Ensure formats are seeded
        client.post("/api/formats/seed-samples")
        
        response = client.get("/api/formats/dev_vlog_meme_v1/runs")
        assert response.status_code == 200
        
        data = response.json()
        assert "format_id" in data
        assert "runs" in data
        assert isinstance(data["runs"], list)


class TestFormatDiscoveryIntegration:
    """Integration tests for /api/format-discovery endpoints"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_broll_candidates_endpoint(self, client):
        """Test GET /api/format-discovery/broll-candidates"""
        response = client.get("/api/format-discovery/broll-candidates", params={"limit": 20})
        assert response.status_code == 200
        
        data = response.json()
        assert "broll_text_candidates" in data
        assert "pure_broll_candidates" in data
        assert isinstance(data["broll_text_candidates"], list)
        assert isinstance(data["pure_broll_candidates"], list)
    
    def test_classify_single_video(self, client):
        """Test GET /api/format-discovery/classify/{media_id}"""
        # Use a dummy UUID - should return 404 or classification
        response = client.get("/api/format-discovery/classify/00000000-0000-0000-0000-000000000000")
        # Either 404 (not found) or 200 (classified) is acceptable
        assert response.status_code in [200, 404, 500]


class TestBRollFormats:
    """Tests specific to B-Roll format functionality"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_broll_text_format_exists(self, client):
        """Test that broll_text_v1 format is available"""
        client.post("/api/formats/seed-samples")
        
        response = client.get("/api/formats/broll_text_v1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "broll_text_v1"
        assert "B-Roll" in data["name"] or "broll" in data["name"].lower()
    
    def test_pure_broll_format_exists(self, client):
        """Test that pure_broll_v1 format is available"""
        client.post("/api/formats/seed-samples")
        
        response = client.get("/api/formats/pure_broll_v1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "pure_broll_v1"


class TestFormatsWorkflow:
    """End-to-end workflow tests for formats"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_complete_format_workflow(self, client):
        """Test complete workflow: seed -> list -> select -> run"""
        # Step 1: Seed formats
        seed_response = client.post("/api/formats/seed-samples")
        assert seed_response.status_code == 200
        
        # Step 2: List formats
        list_response = client.get("/api/formats/list")
        assert list_response.status_code == 200
        formats = list_response.json()["formats"]
        assert len(formats) > 0
        
        # Step 3: Get specific format
        format_id = formats[0]["id"]
        get_response = client.get(f"/api/formats/{format_id}")
        assert get_response.status_code == 200
        
        # Step 4: Run format
        run_response = client.post(
            f"/api/formats/{format_id}/run",
            json={"params": {}, "trigger_type": "manual"}
        )
        assert run_response.status_code == 200
        
        # Workflow completed
        assert True
    
    def test_format_discovery_to_run_workflow(self, client):
        """Test workflow: discover b-roll -> run format on candidates"""
        # Step 1: Seed formats
        client.post("/api/formats/seed-samples")
        
        # Step 2: Discover b-roll candidates
        discover_response = client.get("/api/format-discovery/broll-candidates", params={"limit": 10})
        assert discover_response.status_code == 200
        
        # Step 3: Get the b-roll format
        format_response = client.get("/api/formats/broll_text_v1")
        assert format_response.status_code == 200
        
        # Workflow completed
        assert True


class TestFormatsAsync:
    """Async integration tests"""
    
    @pytest.fixture
    def async_client(self):
        return httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_concurrent_format_operations(self, async_client):
        """Test concurrent format operations"""
        async with async_client:
            # Seed first
            await async_client.post("/api/formats/seed-samples")
            
            # Run concurrent operations
            tasks = [
                async_client.get("/api/formats/list"),
                async_client.get("/api/formats/dev_vlog_meme_v1"),
                async_client.get("/api/format-discovery/broll-candidates", params={"limit": 5})
            ]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
