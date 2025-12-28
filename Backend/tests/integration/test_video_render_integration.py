"""
Integration Tests for Video Render Pipeline
Tests the complete flow from creative brief to rendered video
"""
import pytest
import httpx
import asyncio
from typing import Dict, Any

# Test configuration
API_BASE = "http://localhost:5555"
TIMEOUT = 60.0  # Longer timeout for render operations


class TestVideoRenderIntegration:
    """Integration tests for /api/render endpoints"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_list_content_types(self, client):
        """Test GET /api/render/content-types"""
        response = client.get("/api/render/content-types")
        assert response.status_code == 200
        
        data = response.json()
        assert "content_types" in data
        assert len(data["content_types"]) > 0
        
        # Check structure
        for ct in data["content_types"]:
            assert "id" in ct
            assert "name" in ct
            assert "description" in ct
    
    def test_list_jobs_empty(self, client):
        """Test GET /api/render/jobs when empty"""
        response = client.get("/api/render/jobs")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
    
    def test_create_render_job(self, client):
        """Test POST /api/render/create"""
        response = client.post(
            "/api/render/create",
            json={
                "content_type": "motivational_quote",
                "primary_text": "Test quote for integration test",
                "author_attribution": "Test Author",
                "duration_seconds": 3.0,
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert "message" in data
        
        return data["job_id"]
    
    def test_create_render_invalid_type(self, client):
        """Test POST /api/render/create with invalid content type"""
        response = client.post(
            "/api/render/create",
            json={
                "content_type": "invalid_type",
                "primary_text": "Test",
                "duration_seconds": 3.0,
            }
        )
        assert response.status_code == 400
    
    def test_quick_render_quote(self, client):
        """Test POST /api/render/quick for quote"""
        response = client.post(
            "/api/render/quick",
            json={
                "text": "Quick test quote",
                "style": "quote",
                "duration": 3.0,
                "author": "Tester",
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
    
    def test_quick_render_broll(self, client):
        """Test POST /api/render/quick for broll"""
        response = client.post(
            "/api/render/quick",
            json={
                "text": "B-Roll overlay text",
                "style": "broll",
                "duration": 5.0,
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
    
    def test_get_job_status_not_found(self, client):
        """Test GET /api/render/status with invalid job_id"""
        response = client.get("/api/render/status/invalid-job-id")
        assert response.status_code == 404
    
    def test_test_render_endpoint(self, client):
        """Test POST /api/render/test"""
        response = client.post("/api/render/test")
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert "job_id" in data
        assert "render_time_seconds" in data
        
        # Check quality report if render succeeded
        if data["success"]:
            assert "quality_report" in data
            assert data["quality_report"]["passed"] == True


class TestRenderWorkflow:
    """End-to-end workflow tests"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_create_and_check_status(self, client):
        """Test complete workflow: create job -> check status"""
        # Create job
        create_response = client.post(
            "/api/render/create",
            json={
                "content_type": "broll_text",
                "primary_text": "Workflow test",
                "secondary_text": "Testing the pipeline",
                "duration_seconds": 3.0,
            }
        )
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]
        
        # Wait a moment for job to process
        import time
        time.sleep(2)
        
        # Check status
        status_response = client.get(f"/api/render/status/{job_id}")
        assert status_response.status_code == 200
        
        status = status_response.json()
        assert status["job_id"] == job_id
        assert status["status"] in ["queued", "rendering", "completed", "failed"]
    
    def test_full_render_pipeline(self, client):
        """Test complete render from brief to video"""
        # Use test endpoint which waits for completion
        response = client.post("/api/render/test")
        assert response.status_code == 200
        
        result = response.json()
        
        if result["success"]:
            # Verify video was created
            assert result["video_path"] is not None
            assert result["render_time_seconds"] > 0
            
            # Check quality report
            qr = result["quality_report"]
            assert qr["passed"] == True
            assert qr["duration_actual"] > 0
            assert qr["file_size_bytes"] > 0


class TestRenderQuality:
    """Tests for quality validation"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_quality_report_structure(self, client):
        """Test that quality reports have correct structure"""
        response = client.post("/api/render/test")
        assert response.status_code == 200
        
        result = response.json()
        if result["quality_report"]:
            qr = result["quality_report"]
            assert "passed" in qr
            assert "video_path" in qr
            assert "duration_actual" in qr
            assert "duration_expected" in qr
            assert "file_size_bytes" in qr
            assert "resolution" in qr
            assert "fps_actual" in qr
            assert "has_audio" in qr
            assert "issues" in qr
            assert "warnings" in qr


class TestRenderAsync:
    """Async integration tests"""
    
    @pytest.fixture
    def async_client(self):
        return httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_concurrent_job_creation(self, async_client):
        """Test creating multiple jobs concurrently"""
        async with async_client:
            tasks = [
                async_client.post(
                    "/api/render/quick",
                    json={
                        "text": f"Concurrent test {i}",
                        "style": "quote",
                        "duration": 2.0,
                    }
                )
                for i in range(3)
            ]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                assert response.status_code == 200
                assert "job_id" in response.json()


class TestRenderEdgeCases:
    """Edge case tests"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)
    
    def test_empty_text(self, client):
        """Test render with empty text"""
        response = client.post(
            "/api/render/create",
            json={
                "content_type": "motivational_quote",
                "primary_text": "",
                "duration_seconds": 3.0,
            }
        )
        # Should either fail validation or create job that fails
        assert response.status_code in [200, 400, 422]
    
    def test_very_long_text(self, client):
        """Test render with very long text"""
        long_text = "This is a test. " * 50
        response = client.post(
            "/api/render/quick",
            json={
                "text": long_text,
                "style": "quote",
                "duration": 5.0,
            }
        )
        assert response.status_code == 200
    
    def test_unicode_text(self, client):
        """Test render with unicode characters"""
        response = client.post(
            "/api/render/quick",
            json={
                "text": "测试文本 🎬 テスト",
                "style": "quote",
                "duration": 3.0,
            }
        )
        assert response.status_code == 200
    
    def test_max_duration(self, client):
        """Test render at maximum duration"""
        response = client.post(
            "/api/render/create",
            json={
                "content_type": "broll_text",
                "primary_text": "Max duration test",
                "duration_seconds": 120.0,  # Max allowed
            }
        )
        assert response.status_code == 200
    
    def test_over_max_duration(self, client):
        """Test render over maximum duration"""
        response = client.post(
            "/api/render/create",
            json={
                "content_type": "broll_text",
                "primary_text": "Over max duration",
                "duration_seconds": 150.0,  # Over max
            }
        )
        # Should fail validation
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
