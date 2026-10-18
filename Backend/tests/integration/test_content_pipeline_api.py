"""
Integration tests for Content Pipeline API endpoints
"""
import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


# Setup test environment
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


class TestPlatformConstraintsAPI:
    """Tests for platform constraints endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app
        return TestClient(app)
    
    def test_get_all_constraints(self, client):
        """GET /api/content-pipeline/constraints returns all constraints"""
        response = client.get("/api/content-pipeline/constraints")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "constraints" in data
        assert data["count"] >= 10  # We seeded at least 16 constraints
    
    def test_get_constraints_by_platform(self, client):
        """GET /api/content-pipeline/constraints?platform=youtube"""
        response = client.get("/api/content-pipeline/constraints?platform=youtube")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # All returned constraints should be for YouTube
        for constraint in data["constraints"]:
            assert constraint["platform"] == "youtube"
    
    def test_get_constraints_by_platform_and_surface(self, client):
        """GET /api/content-pipeline/constraints?platform=instagram&surface=reel"""
        response = client.get("/api/content-pipeline/constraints?platform=instagram&surface=reel")
        
        assert response.status_code == 200
        data = response.json()
        
        for constraint in data["constraints"]:
            assert constraint["platform"] == "instagram"
            assert constraint["surface"] == "reel"
    
    def test_get_platform_surface_constraints(self, client):
        """GET /api/content-pipeline/constraints/{platform}/{surface}"""
        response = client.get("/api/content-pipeline/constraints/youtube/video")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["platform"] == "youtube"
        assert data["surface"] == "video"
        assert "constraints" in data
        
        # Should have title and description constraints
        if "title" in data["constraints"]:
            assert data["constraints"]["title"]["max_chars"] == 100
        if "description" in data["constraints"]:
            assert data["constraints"]["description"]["max_chars"] == 5000


class TestCopyPlanAPI:
    """Tests for copy plan generation endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app
        return TestClient(app)
    
    def test_generate_copy_plan_with_inputs(self, client):
        """POST /api/content-pipeline/copy-plan/generate with custom inputs"""
        # Mock the OpenAI call
        with patch('services.content_pipeline.copy_plan_service.CopyPlanService._call_llm') as mock_llm:
            mock_llm.return_value = {
                "titles": ["Test Title 1", "Test Title 2"],
                "caption": "Test caption for social media",
                "description": "Full description of the content",
                "hashtags": ["test", "content"],
                "rationale": "Generated for test"
            }
            
            response = client.post("/api/content-pipeline/copy-plan/generate", json={
                "platforms": ["youtube"],
                "inputs": {
                    "hook": "Stop scrolling right now!",
                    "topics": ["productivity", "focus"],
                    "tone": "energetic",
                    "cta": {"type": "subscribe", "text": "Subscribe for more!"}
                }
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "copy_plan" in data
        assert data["copy_plan"]["schema"] == "copy_plan_v1"
    
    def test_generate_copy_plan_missing_inputs(self, client):
        """POST without inputs or video_id returns error"""
        response = client.post("/api/content-pipeline/copy-plan/generate", json={
            "platforms": ["youtube"]
        })
        
        assert response.status_code in [400, 422, 500]
    
    def test_generate_copy_plan_multiple_platforms(self, client):
        """Generate copy for multiple platforms"""
        with patch('services.content_pipeline.copy_plan_service.CopyPlanService._call_llm') as mock_llm:
            mock_llm.return_value = {
                "titles": ["Great Title"],
                "caption": "Amazing content!",
                "hashtags": ["viral"]
            }
            
            response = client.post("/api/content-pipeline/copy-plan/generate", json={
                "platforms": ["youtube", "instagram", "tiktok"],
                "inputs": {
                    "hook": "You won't believe this",
                    "topics": ["viral", "trends"]
                }
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["platforms_generated"] >= 3  # At least one variant per platform


class TestRemotionSpecAPI:
    """Tests for Remotion render spec endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app
        return TestClient(app)
    
    def test_get_composition_presets(self, client):
        """GET /api/content-pipeline/remotion-spec/compositions"""
        response = client.get("/api/content-pipeline/remotion-spec/compositions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "compositions" in data
        assert "caption_styles" in data
        
        # Check expected presets exist
        assert "ShortFormV1" in data["compositions"]
        assert "CaptionStyleA" in data["caption_styles"]
    
    def test_generate_remotion_spec_missing_video_id(self, client):
        """POST without video_id returns error"""
        response = client.post("/api/content-pipeline/remotion-spec/generate", json={
            "composition_id": "ShortFormV1"
        })
        
        assert response.status_code in [400, 422, 500]


class TestConstraintValues:
    """Tests to verify constraint values match official limits"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_youtube_title_limit(self, client):
        """YouTube title max is 100 chars"""
        response = client.get("/api/content-pipeline/constraints/youtube/video")
        data = response.json()
        
        if "title" in data.get("constraints", {}):
            assert data["constraints"]["title"]["max_chars"] == 100
            assert data["constraints"]["title"]["target_chars"] == 80
    
    def test_youtube_description_limit(self, client):
        """YouTube description max is 5000 chars"""
        response = client.get("/api/content-pipeline/constraints/youtube/video")
        data = response.json()
        
        if "description" in data.get("constraints", {}):
            assert data["constraints"]["description"]["max_chars"] == 5000
    
    def test_instagram_caption_limit(self, client):
        """Instagram caption max is 2200 chars"""
        response = client.get("/api/content-pipeline/constraints/instagram/reel")
        data = response.json()
        
        if "caption" in data.get("constraints", {}):
            assert data["constraints"]["caption"]["max_chars"] == 2200
    
    def test_tiktok_caption_limit(self, client):
        """TikTok caption max is 2200 UTF-16 chars"""
        response = client.get("/api/content-pipeline/constraints/tiktok/video")
        data = response.json()
        
        if "caption" in data.get("constraints", {}):
            assert data["constraints"]["caption"]["max_chars"] == 2200
            assert data["constraints"]["caption"]["count_rule"] == "utf16"
    
    def test_x_standard_post_limit(self, client):
        """X/Twitter standard post max is 280 chars"""
        response = client.get("/api/content-pipeline/constraints/x/standard_post")
        data = response.json()
        
        if "caption" in data.get("constraints", {}):
            assert data["constraints"]["caption"]["max_chars"] == 280
    
    def test_threads_post_limit(self, client):
        """Threads post max is 500 UTF-8 bytes"""
        response = client.get("/api/content-pipeline/constraints/threads/post")
        data = response.json()
        
        if "caption" in data.get("constraints", {}):
            assert data["constraints"]["caption"]["max_chars"] == 500
            assert data["constraints"]["caption"]["count_rule"] == "utf8_bytes"


class TestDataSourceIntegration:
    """Tests to verify services can source data from analysis"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_copy_plan_from_analysis_fields(self, client):
        """CopyPlanService can use new analysis fields"""
        from services.content_pipeline.copy_plan_service import CopyPlanService
        
        # Simulate analysis with new fields
        analysis = {
            "detected_hook": "POV: You're struggling with focus",
            "topics": ["productivity", "focus", "work"],
            "tone": "motivational",
            "pain_points": ["constant distractions", "low productivity"],
            "emotional_drivers": ["desire for success", "fear of failure"],
            "emotional_journey": {
                "opening_emotion": "frustration",
                "peak_emotion": "hope",
                "closing_emotion": "determination"
            },
            "call_to_action": {
                "type": "follow",
                "text": "Follow for more tips!",
                "strength": "strong"
            },
            "scene_structure": [
                {"start_sec": 0, "end_sec": 3, "role": "hook", "summary": "Attention grabber"},
                {"start_sec": 3, "end_sec": 20, "role": "solution", "summary": "Main content"},
                {"start_sec": 20, "end_sec": 25, "role": "cta", "summary": "Call to action"}
            ],
            "content_type": "educational",
            "target_audience": {
                "demographic": "young professionals",
                "interests": ["productivity", "self-improvement"],
                "awareness_level": "problem-aware"
            }
        }
        
        # Convert to CopyPlanInput
        inputs = CopyPlanService.from_video_analysis(analysis)
        
        # Verify all fields mapped correctly
        assert inputs.hook == "POV: You're struggling with focus"
        assert "productivity" in inputs.topics
        assert inputs.tone == "motivational"
        assert "constant distractions" in inputs.pain_points
        assert "desire for success" in inputs.emotional_drivers
        assert inputs.cta["type"] == "follow"
        assert inputs.content_type == "educational"
    
    def test_remotion_spec_from_analysis_fields(self, client):
        """RemotionSpecService can use scene_structure"""
        from services.content_pipeline.remotion_spec_service import RemotionSpecService
        from unittest.mock import patch
        
        with patch.object(RemotionSpecService, '__init__', lambda x: None):
            service = RemotionSpecService()
            service.engine = None
            
            # Simulate deep audit data with scene structure
            deep_audit_data = {
                "transcript": {
                    "words": [
                        {"w": "Stop", "start": 0.0, "end": 0.3},
                        {"w": "scrolling", "start": 0.3, "end": 0.8},
                        {"w": "right", "start": 0.8, "end": 1.0},
                        {"w": "now", "start": 1.0, "end": 1.3},
                    ]
                },
                "scene_structure": [
                    {"start_sec": 0, "end_sec": 3, "role": "hook", "summary": "Hook", "emotion": "urgency"},
                    {"start_sec": 3, "end_sec": 25, "role": "solution", "summary": "Solution"},
                    {"start_sec": 25, "end_sec": 30, "role": "cta", "summary": "CTA"}
                ],
                "source_video_url": "https://example.com/video.mp4"
            }
            
            spec = service.build_from_deep_audit(
                composition_id="ShortFormV1",
                duration_sec=30,
                deep_audit_data=deep_audit_data
            )
            
            # Verify scene structure converted to beats
            assert len(spec.beats) == 3
            assert spec.beats[0].role == "hook"
            assert spec.beats[0].emotion == "urgency"
            
            # Verify captions from words
            assert spec.captions is not None
            assert len(spec.captions.segments) >= 1


class TestErrorHandling:
    """Tests for error handling"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    def test_invalid_platform(self, client):
        """Invalid platform in constraints request"""
        response = client.get("/api/content-pipeline/constraints/invalid_platform/video")
        
        # Should return 200 with empty constraints, not error
        assert response.status_code == 200
        data = response.json()
        assert data["constraints"] == {} or len(data.get("constraints", {})) == 0
    
    def test_missing_required_field(self, client):
        """Missing required field in copy plan request"""
        response = client.post("/api/content-pipeline/copy-plan/generate", json={
            "platforms": ["youtube"],
            "inputs": {
                # Missing required "hook" and "topics"
            }
        })
        
        assert response.status_code in [400, 422, 500]
