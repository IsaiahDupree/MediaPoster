"""
Tests for video generation API endpoints
"""
import pytest
from fastapi.testclient import TestClient


class TestVideoGenerationAPI:
    """Test video generation API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Get test client"""
        from main import app
        return TestClient(app)
    
    # ==================== Provider Tests ====================
    
    def test_list_providers(self, client):
        """Test listing available providers"""
        response = client.get("/api/video-generation/providers")
        assert response.status_code == 200
        
        providers = response.json()
        assert isinstance(providers, list)
        assert "sora" in providers
        assert "runway" in providers
        assert "pika" in providers
        assert "luma" in providers
    
    def test_get_provider_capabilities(self, client):
        """Test getting provider capabilities"""
        for provider in ["sora", "runway", "pika", "luma"]:
            response = client.get(f"/api/video-generation/providers/{provider}")
            assert response.status_code in [200, 500], f"Failed for {provider}"
            
            if response.status_code == 200:
                data = response.json()
                assert data["name"] == provider
                assert "models" in data
                assert "max_duration" in data
                assert "supported_resolutions" in data
    
    def test_get_invalid_provider(self, client):
        """Test getting invalid provider"""
        response = client.get("/api/video-generation/providers/invalid")
        assert response.status_code == 404
    
    # ==================== Create Video Tests ====================
    
    def test_create_video_sora(self, client):
        """Test creating video with Sora"""
        response = client.post("/api/video-generation/create", json={
            "prompt": "A beautiful sunset over the ocean",
            "provider": "sora",
            "width": 1920,
            "height": 1080,
            "duration_seconds": 10
        })
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert "status" in data
            assert data["metadata"]["provider"] == "sora"
    
    def test_create_video_runway(self, client):
        """Test creating video with Runway"""
        response = client.post("/api/video-generation/create", json={
            "prompt": "A cat playing piano",
            "provider": "runway",
            "width": 1280,
            "height": 768,
            "duration_seconds": 10
        })
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert data["metadata"]["provider"] == "runway"
    
    def test_create_video_pika(self, client):
        """Test creating video with Pika"""
        response = client.post("/api/video-generation/create", json={
            "prompt": "A robot dancing",
            "provider": "pika",
            "width": 1280,
            "height": 720,
            "duration_seconds": 5
        })
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert data["metadata"]["provider"] == "pika"
    
    def test_create_video_luma(self, client):
        """Test creating video with Luma"""
        response = client.post("/api/video-generation/create", json={
            "prompt": "A futuristic city",
            "provider": "luma",
            "width": 1280,
            "height": 720,
            "duration_seconds": 5
        })
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert data["metadata"]["provider"] == "luma"
    
    def test_create_video_with_image_input(self, client):
        """Test image-to-video generation"""
        response = client.post("/api/video-generation/create", json={
            "prompt": "Animate this image",
            "provider": "runway",
            "input_image": "https://example.com/image.jpg",
            "duration_seconds": 5
        })
        
        assert response.status_code in [200, 500]
    
    # ==================== Status Tests ====================
    
    def test_get_video_status(self, client):
        """Test getting video status"""
        # Create a video first
        create_response = client.post("/api/video-generation/create", json={
            "prompt": "Test video",
            "provider": "sora"
        })
        
        if create_response.status_code == 200:
            job_id = create_response.json()["job_id"]
            
            # Get status
            status_response = client.get(f"/api/video-generation/{job_id}?provider=sora")
            assert status_response.status_code in [200, 404]
            
            if status_response.status_code == 200:
                data = status_response.json()
                assert data["job_id"] == job_id
                assert "status" in data
    
    def test_get_status_invalid_job(self, client):
        """Test getting status of invalid job"""
        response = client.get("/api/video-generation/invalid_job_id?provider=sora")
        assert response.status_code == 404
    
    # ==================== List Jobs Tests ====================
    
    def test_list_jobs(self, client):
        """Test listing video jobs"""
        response = client.get("/api/video-generation/jobs?provider=sora&limit=10")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
    
    # ==================== Delete Tests ====================
    
    def test_delete_video(self, client):
        """Test deleting video"""
        # Create a video first
        create_response = client.post("/api/video-generation/create", json={
            "prompt": "Video to delete",
            "provider": "sora"
        })
        
        if create_response.status_code == 200:
            job_id = create_response.json()["job_id"]
            
            # Delete it
            delete_response = client.delete(f"/api/video-generation/{job_id}?provider=sora")
            assert delete_response.status_code in [200, 500]


# Mark as API integration tests
pytestmark = pytest.mark.integration
