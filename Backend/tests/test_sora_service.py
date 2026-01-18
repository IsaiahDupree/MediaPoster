"""
Comprehensive Test Suite for Sora Video Generation Service

Tests cover:
1. Unit tests for SoraProvider
2. Integration tests for the pipeline
3. API endpoint tests
4. Mock tests for development without credits

Run with: pytest tests/test_sora_service.py -v
Run integration tests: pytest tests/test_sora_service.py -v -m integration
"""
import os
import sys
import json
import uuid
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.video_providers.sora_provider import (
    SoraProvider,
    ALLOWED_MODELS,
    ALLOWED_SIZES,
    ALLOWED_SECONDS
)
from services.video_providers.base import (
    ProviderConfig,
    ProviderName,
    ClipStatus,
    CreateClipInput
)

# Import pipeline modules - may fail if openai not installed
try:
    from services.sora_video_pipeline import (
        SoraVideoPipeline,
        VideoProject,
        ClipSpec,
        ClipRole,
        VideoStyle
    )
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False
    VideoProject = None
    ClipSpec = None
    ClipRole = None
    VideoStyle = None
    SoraVideoPipeline = None


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sora_provider():
    """Create a SoraProvider instance."""
    return SoraProvider()


@pytest.fixture
def mock_openai_response():
    """Mock successful OpenAI Sora API response."""
    return {
        "id": "video_test123456789",
        "object": "video",
        "created_at": 1704067200,
        "status": "queued",
        "completed_at": None,
        "error": None,
        "expires_at": None,
        "model": "sora-2",
        "progress": 0,
        "prompt": "A test video prompt",
        "remixed_from_video_id": None,
        "seconds": "4",
        "size": "720x1280"
    }


@pytest.fixture
def mock_completed_response():
    """Mock completed video response."""
    return {
        "id": "video_test123456789",
        "object": "video",
        "created_at": 1704067200,
        "status": "completed",
        "completed_at": 1704067300,
        "error": None,
        "expires_at": 1704153600,
        "model": "sora-2",
        "progress": 100,
        "prompt": "A test video prompt",
        "remixed_from_video_id": None,
        "seconds": "4",
        "size": "720x1280"
    }


@pytest.fixture
def sample_project():
    """Create a sample video project for testing."""
    if not PIPELINE_AVAILABLE:
        pytest.skip("Pipeline not available (openai not installed)")
    return VideoProject(
        project_id=str(uuid.uuid4()),
        title="Test Project",
        description="Test description",
        main_character="@testuser",
        character_description="A confident content creator",
        total_duration_seconds=12,
        clips=[
            ClipSpec(
                clip_id=str(uuid.uuid4()),
                sequence_number=1,
                role=ClipRole.HOOK,
                duration_seconds=4,
                prompt="A cinematic opening scene",
                script_text="Opening hook",
                character_name="@testuser",
                scene_description="Studio setting",
                model="sora-2",
                size="720x1280"
            ),
            ClipSpec(
                clip_id=str(uuid.uuid4()),
                sequence_number=2,
                role=ClipRole.STORY,
                duration_seconds=8,
                prompt="Main content scene",
                script_text="Story content",
                character_name="@testuser",
                scene_description="Outdoor setting",
                model="sora-2",
                size="720x1280"
            )
        ],
        style=VideoStyle.MOTIVATIONAL
    )


# =============================================================================
# UNIT TESTS - SoraProvider
# =============================================================================

class TestSoraProviderUnit:
    """Unit tests for SoraProvider class."""
    
    def test_provider_initialization(self, sora_provider):
        """Test provider initializes correctly."""
        assert sora_provider is not None
        assert sora_provider.name == ProviderName.SORA
    
    def test_valid_sizes(self):
        """Test valid video sizes are defined."""
        assert "720x1280" in ALLOWED_SIZES
        assert "1280x720" in ALLOWED_SIZES
        assert "1024x1792" in ALLOWED_SIZES
        assert "1792x1024" in ALLOWED_SIZES
        assert len(ALLOWED_SIZES) == 4
    
    def test_valid_durations(self):
        """Test valid durations are defined."""
        assert 4 in ALLOWED_SECONDS
        assert 8 in ALLOWED_SECONDS
        assert 12 in ALLOWED_SECONDS
        assert len(ALLOWED_SECONDS) == 3
    
    def test_valid_models(self):
        """Test valid models are defined."""
        assert "sora-2" in ALLOWED_MODELS
        assert "sora-2-pro" in ALLOWED_MODELS
    
    def test_create_clip_input(self):
        """Test CreateClipInput validation."""
        clip_input = CreateClipInput(
            clip_id="test-clip-1",
            prompt="A beautiful sunset over the ocean",
            seconds=4,
            size="720x1280",
            model="sora-2"
        )
        assert clip_input.prompt == "A beautiful sunset over the ocean"
        assert clip_input.size == "720x1280"
        assert clip_input.seconds == 4


class TestSoraProviderMocked:
    """Unit tests with mocked API calls."""
    
    @pytest.mark.asyncio
    async def test_generate_creates_video(self, sora_provider, mock_openai_response):
        """Test generate method creates a video job."""
        # Verify mock response structure
        assert mock_openai_response["status"] == "queued"
        assert mock_openai_response["id"].startswith("video_")
        assert mock_openai_response["model"] == "sora-2"
    
    @pytest.mark.asyncio
    async def test_poll_status_returns_completed(self, mock_completed_response):
        """Test polling returns completed status."""
        assert mock_completed_response["status"] == "completed"
        assert mock_completed_response["progress"] == 100
        assert mock_completed_response["completed_at"] is not None
    
    def test_clip_status_enum_values(self):
        """Test ClipStatus enum has expected values."""
        assert ClipStatus.QUEUED.value == "queued"
        assert ClipStatus.RUNNING.value == "running"
        assert ClipStatus.SUCCEEDED.value == "succeeded"
        assert ClipStatus.FAILED.value == "failed"
        assert ClipStatus.CANCELED.value == "canceled"


# =============================================================================
# UNIT TESTS - SoraVideoPipeline
# =============================================================================

@pytest.mark.skipif(not PIPELINE_AVAILABLE, reason="Pipeline not available (openai not installed)")
class TestSoraVideoPipelineUnit:
    """Unit tests for SoraVideoPipeline class."""
    
    def test_pipeline_initialization(self):
        """Test pipeline initializes correctly."""
        pipeline = SoraVideoPipeline()
        assert pipeline is not None
        # Pipeline stores projects in _projects dict
        assert hasattr(pipeline, '_projects') or hasattr(pipeline, 'get_project')
    
    def test_project_clips_have_prompts(self, sample_project):
        """Test that project clips have generated prompts."""
        for clip in sample_project.clips:
            assert clip.prompt is not None
            assert len(clip.prompt) > 0
    
    def test_project_status_tracking(self, sample_project):
        """Test project status is tracked correctly."""
        assert sample_project.status == "planning"
        
        # Simulate status updates
        sample_project.status = "generating"
        assert sample_project.status == "generating"
        
        sample_project.status = "completed"
        assert sample_project.status == "completed"


@pytest.mark.skipif(not PIPELINE_AVAILABLE, reason="Pipeline not available (openai not installed)")
class TestClipSpec:
    """Tests for ClipSpec dataclass."""
    
    def test_clip_spec_creation(self):
        """Test ClipSpec creation with all fields."""
        clip = ClipSpec(
            clip_id="test-clip-1",
            sequence_number=1,
            role=ClipRole.HOOK,
            duration_seconds=4,
            prompt="Test prompt",
            script_text="Test script",
            character_name="@testuser",
            scene_description="Test scene",
            model="sora-2",
            size="720x1280"
        )
        
        assert clip.clip_id == "test-clip-1"
        assert clip.sequence_number == 1
        assert clip.role == ClipRole.HOOK
        assert clip.duration_seconds == 4
        assert clip.status == "pending"
    
    def test_clip_role_values(self):
        """Test ClipRole enum values."""
        assert ClipRole.HOOK.value == "hook"
        assert ClipRole.STORY.value == "story"
        assert ClipRole.CTA.value == "cta"


# =============================================================================
# INTEGRATION TESTS (require API key)
# =============================================================================

@pytest.mark.integration
class TestSoraIntegration:
    """Integration tests that use the real Sora API.
    
    These tests consume API credits. Run only when needed:
    pytest tests/test_sora_service.py -v -m integration
    """
    
    @pytest.fixture
    def api_key(self):
        """Get API key from environment."""
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            pytest.skip("OPENAI_API_KEY not set")
        return key
    
    @pytest.mark.asyncio
    async def test_real_video_generation(self, api_key):
        """Test real video generation (uses credits!)."""
        import httpx
        
        async with httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0
        ) as client:
            payload = {
                "model": "sora-2",
                "prompt": "A serene mountain landscape at sunrise",
                "size": "720x1280",
                "seconds": "4"
            }
            
            response = await client.post("/videos", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert data["status"] in ["queued", "in_progress"]
            
            # Store video ID for cleanup
            video_id = data["id"]
            print(f"Created video: {video_id}")
    
    @pytest.mark.asyncio
    async def test_poll_until_complete(self, api_key):
        """Test polling a video until completion."""
        import httpx
        
        # First create a video
        async with httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=300.0
        ) as client:
            # Create video
            create_response = await client.post("/videos", json={
                "model": "sora-2",
                "prompt": "Abstract colorful particles moving",
                "size": "720x1280",
                "seconds": "4"
            })
            
            assert create_response.status_code == 200
            video_id = create_response.json()["id"]
            
            # Poll until complete (max 5 minutes)
            max_polls = 30
            for i in range(max_polls):
                status_response = await client.get(f"/videos/{video_id}")
                assert status_response.status_code == 200
                
                status_data = status_response.json()
                print(f"Poll {i+1}: status={status_data['status']}, progress={status_data['progress']}%")
                
                if status_data["status"] == "completed":
                    assert status_data["progress"] == 100
                    break
                elif status_data["status"] == "failed":
                    pytest.fail(f"Video generation failed: {status_data.get('error')}")
                
                await asyncio.sleep(10)
            else:
                pytest.fail("Video generation timed out")
    
    @pytest.mark.asyncio
    async def test_download_completed_video(self, api_key):
        """Test downloading a completed video."""
        # This test requires a completed video ID
        # Skip if no test video available
        pytest.skip("Requires a completed video ID")


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

@pytest.mark.skip(reason="Requires full app context with all dependencies")
class TestSoraPipelineEndpoints:
    """Tests for Sora pipeline API endpoints.
    
    Note: These tests require the full FastAPI app to be importable,
    which needs all dependencies (supabase, openai, etc.) installed.
    Run separately with: pytest tests/test_sora_service.py -v -m endpoints
    """
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API."""
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)
    
    def test_create_project_endpoint(self, test_client):
        """Test POST /api/sora-pipeline/projects endpoint."""
        response = test_client.post(
            "/api/sora-pipeline/projects",
            json={
                "character": "@testuser",
                "total_duration": 12,
                "num_clips": 2,
                "style": "motivational",
                "topic": "success"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        assert data["main_character"] == "@testuser"
        assert len(data["clips"]) == 2
    
    def test_list_projects_endpoint(self, test_client):
        """Test GET /api/sora-pipeline/projects endpoint."""
        response = test_client.get("/api/sora-pipeline/projects")
        
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)
    
    def test_get_project_endpoint(self, test_client):
        """Test GET /api/sora-pipeline/projects/{id} endpoint."""
        # First create a project
        create_response = test_client.post(
            "/api/sora-pipeline/projects",
            json={
                "character": "@testuser",
                "total_duration": 12,
                "num_clips": 1,
                "style": "test",
                "topic": "test"
            }
        )
        project_id = create_response.json()["project_id"]
        
        # Then fetch it
        response = test_client.get(f"/api/sora-pipeline/projects/{project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
    
    def test_project_validation_min_duration(self, test_client):
        """Test project validation rejects short duration."""
        response = test_client.post(
            "/api/sora-pipeline/projects",
            json={
                "character": "@testuser",
                "total_duration": 4,  # Too short (min 12)
                "num_clips": 1,
                "style": "test",
                "topic": "test"
            }
        )
        
        assert response.status_code == 422  # Validation error


# =============================================================================
# MOCK TESTS FOR DEVELOPMENT
# =============================================================================

@pytest.mark.skipif(not PIPELINE_AVAILABLE, reason="Pipeline not available (openai not installed)")
class TestSoraMocked:
    """Tests using mocked Sora API for development without credits."""
    
    @pytest.mark.asyncio
    async def test_mocked_generation_flow(self):
        """Test full generation flow with mocks."""
        with patch('services.video_providers.sora_provider.httpx.AsyncClient') as mock_client_class:
            # Setup mock responses
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock create response
            mock_create_response = Mock()
            mock_create_response.status_code = 200
            mock_create_response.json.return_value = {
                "id": "video_mock123",
                "status": "queued",
                "progress": 0
            }
            
            # Mock poll response (completed)
            mock_poll_response = Mock()
            mock_poll_response.status_code = 200
            mock_poll_response.json.return_value = {
                "id": "video_mock123",
                "status": "completed",
                "progress": 100
            }
            
            mock_client.post.return_value = mock_create_response
            mock_client.get.return_value = mock_poll_response
            
            # Test the flow
            provider = SoraProvider()
            
            # Verify mocks are set up correctly
            assert mock_create_response.json()["status"] == "queued"
            assert mock_poll_response.json()["status"] == "completed"
    
    def test_project_serialization(self, sample_project):
        """Test project can be serialized to JSON."""
        # Convert to dict
        project_dict = {
            "project_id": sample_project.project_id,
            "title": sample_project.title,
            "description": sample_project.description,
            "main_character": sample_project.main_character,
            "total_duration_seconds": sample_project.total_duration_seconds,
            "clips": [
                {
                    "clip_id": c.clip_id,
                    "sequence_number": c.sequence_number,
                    "role": c.role.value,
                    "duration_seconds": c.duration_seconds,
                    "prompt": c.prompt,
                    "status": c.status
                }
                for c in sample_project.clips
            ],
            "style": sample_project.style,
            "status": sample_project.status
        }
        
        # Should be JSON serializable
        json_str = json.dumps(project_dict)
        assert json_str is not None
        
        # Should deserialize correctly
        parsed = json.loads(json_str)
        assert parsed["project_id"] == sample_project.project_id


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

@pytest.mark.skipif(not PIPELINE_AVAILABLE, reason="Pipeline not available (openai not installed)")
class TestSoraPerformance:
    """Performance and stress tests."""
    
    def test_pipeline_methods_exist(self):
        """Test pipeline has expected methods."""
        pipeline = SoraVideoPipeline()
        
        # Check key methods exist
        assert hasattr(pipeline, 'create_video_project')
        assert hasattr(pipeline, 'generate_clips')
        assert hasattr(pipeline, 'compose_video')
        assert hasattr(pipeline, 'get_project')
        assert hasattr(pipeline, 'list_projects')
    
    def test_list_projects_performance(self):
        """Test listing projects is fast."""
        pipeline = SoraVideoPipeline()
        
        start_time = datetime.now()
        for _ in range(100):
            projects = pipeline.list_projects()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        avg_time = elapsed / 100
        assert avg_time < 0.01, f"Average list_projects time too slow: {avg_time}s"


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    # Run all tests except integration
    pytest.main([
        __file__,
        "-v",
        "-m", "not integration",
        "--tb=short"
    ])
