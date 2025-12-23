"""
Video Orchestrator API Tests
============================
Unit tests for video orchestrator API endpoints.

Run tests:
    pytest tests/test_video_api_endpoints.py -v
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def client():
    """Create test client."""
    from main import app
    return TestClient(app)


# =============================================================================
# PROJECT ENDPOINT TESTS
# =============================================================================

class TestProjectEndpoints:
    """Test project endpoints."""
    
    def test_create_project(self, client):
        """Test creating a project."""
        response = client.post("/api/video/projects", json={
            "title": "Test Video Project",
            "description": "A test project",
            "tags": ["test", "demo"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Video Project"
        assert "id" in data
        assert "created_at" in data
    
    def test_list_projects(self, client):
        """Test listing projects."""
        # Create a project first
        client.post("/api/video/projects", json={
            "title": "List Test Project"
        })
        
        response = client.get("/api/video/projects")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_project(self, client):
        """Test getting a project by ID."""
        # Create project
        create_response = client.post("/api/video/projects", json={
            "title": "Get Test Project"
        })
        project_id = create_response.json()["id"]
        
        response = client.get(f"/api/video/projects/{project_id}")
        
        assert response.status_code == 200
        assert response.json()["id"] == project_id
    
    def test_get_nonexistent_project(self, client):
        """Test getting a nonexistent project."""
        response = client.get("/api/video/projects/nonexistent-id")
        
        assert response.status_code == 404


# =============================================================================
# BRIEF ENDPOINT TESTS
# =============================================================================

class TestBriefEndpoints:
    """Test brief endpoints."""
    
    def test_create_brief(self, client):
        """Test creating a brief."""
        # Create project first
        project_response = client.post("/api/video/projects", json={
            "title": "Brief Test Project"
        })
        project_id = project_response.json()["id"]
        
        response = client.post("/api/video/briefs", json={
            "project_id": project_id,
            "objective": "Explain product features",
            "audience": "Tech enthusiasts",
            "tone": "Professional",
            "key_points": ["Feature 1", "Feature 2"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["objective"] == "Explain product features"
        assert data["project_id"] == project_id
    
    def test_create_brief_invalid_project(self, client):
        """Test creating brief with invalid project."""
        response = client.post("/api/video/briefs", json={
            "project_id": "invalid-project-id",
            "objective": "Test",
            "audience": "Test"
        })
        
        assert response.status_code == 404


# =============================================================================
# SCRIPT ENDPOINT TESTS
# =============================================================================

class TestScriptEndpoints:
    """Test script endpoints."""
    
    def test_create_script(self, client):
        """Test creating a script."""
        # Create project
        project_response = client.post("/api/video/projects", json={
            "title": "Script Test Project"
        })
        project_id = project_response.json()["id"]
        
        response = client.post("/api/video/scripts", json={
            "project_id": project_id,
            "title": "Test Script",
            "body": "Welcome to our video. This is a test script with multiple sentences. We will demonstrate the features."
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Script"
        assert "word_count" in data
        assert "estimated_duration_seconds" in data
    
    def test_estimate_script_duration(self, client):
        """Test script duration estimation."""
        response = client.post(
            "/api/video/scripts/estimate",
            params={"body": "This is a test script with about twenty words to estimate duration for the video."}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "word_count" in data
        assert "estimated_seconds" in data
        assert "exceeds_max" in data


# =============================================================================
# CLIP PLAN ENDPOINT TESTS
# =============================================================================

class TestClipPlanEndpoints:
    """Test clip plan endpoints."""
    
    @pytest.fixture
    def setup_project_and_script(self, client):
        """Create project and script for testing."""
        # Create project
        project_response = client.post("/api/video/projects", json={
            "title": "ClipPlan Test Project"
        })
        project_id = project_response.json()["id"]
        
        # Create script
        script_response = client.post("/api/video/scripts", json={
            "project_id": project_id,
            "title": "Test Script",
            "body": """
            Welcome to our product demonstration.
            Today we will show you three amazing features.
            First, the intuitive interface makes everything easy.
            Second, automation saves you time every day.
            Third, integration connects all your tools.
            Thank you for watching this video!
            """
        })
        script_id = script_response.json()["id"]
        
        return {"project_id": project_id, "script_id": script_id}
    
    def test_create_clip_plan(self, client, setup_project_and_script):
        """Test creating a clip plan."""
        ids = setup_project_and_script
        
        response = client.post("/api/video/clip-plans", json={
            "project_id": ids["project_id"],
            "script_id": ids["script_id"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "draft"
        assert data["total_clips"] >= 1
        assert len(data["scenes"]) >= 1
    
    def test_create_clip_plan_with_constraints(self, client, setup_project_and_script):
        """Test creating a clip plan with constraints."""
        ids = setup_project_and_script
        
        response = client.post("/api/video/clip-plans", json={
            "project_id": ids["project_id"],
            "script_id": ids["script_id"],
            "constraints": {
                "max_total_seconds": 60,
                "default_clip_seconds": 8,
                "aspect_ratio": "16:9",
                "pacing": {
                    "words_per_minute": 150,
                    "max_words_per_clip": 25
                }
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_duration_seconds"] <= 60
    
    def test_get_clip_plan(self, client, setup_project_and_script):
        """Test getting a clip plan."""
        ids = setup_project_and_script
        
        # Create plan
        create_response = client.post("/api/video/clip-plans", json={
            "project_id": ids["project_id"],
            "script_id": ids["script_id"]
        })
        plan_id = create_response.json()["id"]
        
        # Get plan
        response = client.get(f"/api/video/clip-plans/{plan_id}")
        
        assert response.status_code == 200
        assert response.json()["id"] == plan_id
    
    def test_start_generation(self, client, setup_project_and_script):
        """Test starting clip plan generation."""
        ids = setup_project_and_script
        
        # Create plan
        create_response = client.post("/api/video/clip-plans", json={
            "project_id": ids["project_id"],
            "script_id": ids["script_id"]
        })
        plan_id = create_response.json()["id"]
        
        # Start generation
        response = client.post(f"/api/video/clip-plans/{plan_id}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
    
    def test_get_generation_status(self, client, setup_project_and_script):
        """Test getting generation status."""
        ids = setup_project_and_script
        
        # Create and start plan
        create_response = client.post("/api/video/clip-plans", json={
            "project_id": ids["project_id"],
            "script_id": ids["script_id"]
        })
        plan_id = create_response.json()["id"]
        client.post(f"/api/video/clip-plans/{plan_id}/start")
        
        # Get status
        response = client.get(f"/api/video/clip-plans/{plan_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_clips" in data
        assert "completed_clips" in data


# =============================================================================
# SORA SINGLE GENERATION TESTS
# =============================================================================

class TestSoraEndpoints:
    """Test Sora single generation endpoints."""
    
    def test_sora_generate(self, client):
        """Test Sora video generation."""
        response = client.post("/api/video/sora/generate", json={
            "prompt": "A cat playing piano in a jazz club",
            "model": "sora-2",
            "size": "1280x720",
            "seconds": 8
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] in ["queued", "running", "succeeded"]
        assert data["prompt"] == "A cat playing piano in a jazz club"
    
    def test_sora_remix(self, client):
        """Test Sora video remix."""
        # First generate a video
        gen_response = client.post("/api/video/sora/generate", json={
            "prompt": "A person walking",
            "seconds": 8
        })
        video_id = gen_response.json()["id"]
        
        # Remix it
        response = client.post("/api/video/sora/remix", json={
            "video_id": video_id,
            "prompt": "Add sunset lighting",
            "seconds": 8
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"] != video_id  # Should be new ID
    
    def test_get_sora_video(self, client):
        """Test getting Sora video status."""
        # Generate video
        gen_response = client.post("/api/video/sora/generate", json={
            "prompt": "Test video",
            "seconds": 4
        })
        video_id = gen_response.json()["id"]
        
        # Get status
        response = client.get(f"/api/video/sora/videos/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == video_id
    
    def test_optimize_prompt(self, client):
        """Test prompt optimization."""
        response = client.post("/api/video/sora/optimize-prompt", json={
            "prompt": "A person walking",
            "model": "sora-2",
            "seconds": 8
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["original_prompt"] == "A person walking"
        assert len(data["optimized_prompt"]) >= len(data["original_prompt"])
    
    def test_sora_history(self, client):
        """Test Sora generation history."""
        # Generate a few videos
        client.post("/api/video/sora/generate", json={"prompt": "Video 1", "seconds": 4})
        client.post("/api/video/sora/generate", json={"prompt": "Video 2", "seconds": 4})
        
        response = client.get("/api/video/sora/history")
        
        assert response.status_code == 200
        data = response.json()
        assert "generations" in data
        assert "total" in data


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check."""
        response = client.get("/api/video/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "provider" in data
        assert "stats" in data


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
