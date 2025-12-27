"""
Unit Tests for Enhanced Vision Analyzer
=======================================
Tests for structured visual extraction, camera motion detection,
and scene boundary detection.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import json
import numpy as np


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_structured_response():
    """Mock OpenAI response for structured analysis"""
    return {
        "description": "A person speaking directly to camera in a well-lit room",
        "color_palette": {
            "primary": "#2E4057",
            "secondary": "#F5E6CC",
            "accent": "#FF6B6B",
            "colors": ["#2E4057", "#F5E6CC", "#FF6B6B", "#FFFFFF"],
            "mood": "warm",
            "contrast_level": "high"
        },
        "lighting": {
            "type": "studio",
            "direction": "front",
            "quality": "soft",
            "exposure": "proper",
            "shadows": "minimal"
        },
        "camera": {
            "shot_type": "medium",
            "angle": "eye-level",
            "movement_hint": "static",
            "depth_of_field": "shallow"
        },
        "scene": {
            "setting": "indoor",
            "setting_specific": "home office",
            "main_subjects": ["person"],
            "objects": ["desk", "microphone", "ring light"],
            "text_on_screen": ["Subscribe Now"],
            "text_style": "caption",
            "people_count": 1,
            "facial_expressions": ["confident", "engaging"],
            "body_language": "open and welcoming"
        },
        "viral": {
            "hook_potential": 75,
            "pattern_interrupt": False,
            "scroll_stopper_elements": ["direct eye contact", "bold text"],
            "meme_potential": False,
            "emotional_trigger": "curiosity",
            "curiosity_gap": True
        }
    }


@pytest.fixture
def mock_openai_comparison_response():
    """Mock OpenAI response for frame comparison"""
    return {
        "camera_motion": {
            "detected": True,
            "type": "zoom",
            "direction": "in",
            "speed": "slow",
            "confidence": 85
        },
        "scene_change": {
            "is_same_scene": True,
            "transition_type": "none",
            "visual_change_score": 15,
            "change_description": "Slight zoom towards subject"
        },
        "subject_motion": {
            "detected": True,
            "description": "Person gesturing with hands"
        }
    }


# ============================================================================
# EnhancedVisionAnalyzer Tests
# ============================================================================

class TestEnhancedVisionAnalyzer:
    """Tests for EnhancedVisionAnalyzer service"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer with mocked OpenAI"""
        with patch('services.enhanced_vision_analyzer.OpenAI') as mock_openai:
            from services.enhanced_vision_analyzer import EnhancedVisionAnalyzer
            analyzer = EnhancedVisionAnalyzer(
                openai_api_key="test_key",
                model="gpt-4o"
            )
            return analyzer
    
    def test_init_without_api_key(self):
        """Test initialization without API key"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=True):
            from services.enhanced_vision_analyzer import EnhancedVisionAnalyzer
            analyzer = EnhancedVisionAnalyzer(openai_api_key=None)
            assert analyzer.client is None
    
    def test_structured_analysis_prompt_defined(self, analyzer):
        """Test that structured analysis prompt is defined"""
        assert len(analyzer.STRUCTURED_ANALYSIS_PROMPT) > 100
        assert "color_palette" in analyzer.STRUCTURED_ANALYSIS_PROMPT
        assert "lighting" in analyzer.STRUCTURED_ANALYSIS_PROMPT
        assert "camera" in analyzer.STRUCTURED_ANALYSIS_PROMPT
    
    def test_frame_comparison_prompt_defined(self, analyzer):
        """Test that frame comparison prompt is defined"""
        assert len(analyzer.FRAME_COMPARISON_PROMPT) > 100
        assert "camera_motion" in analyzer.FRAME_COMPARISON_PROMPT
        assert "scene_change" in analyzer.FRAME_COMPARISON_PROMPT
    
    @pytest.mark.asyncio
    async def test_analyze_frame_structured_success(self, analyzer, mock_openai_structured_response):
        """Test successful structured frame analysis"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_structured_response)
        
        analyzer.client.chat.completions.create = Mock(return_value=mock_response)
        
        # Mock file reading
        with patch.object(analyzer, 'encode_image', return_value="base64encodedimage"):
            with patch.object(Path, 'exists', return_value=True):
                result = await analyzer.analyze_frame_structured(
                    image_path=Path("/test/frame.jpg"),
                    frame_index=0,
                    timestamp=0.0
                )
        
        assert result.frame_index == 0
        assert result.timestamp == 0.0
        assert result.color_palette.primary == "#2E4057"
        assert result.color_palette.mood == "warm"
        assert result.lighting.type == "studio"
        assert result.camera.shot_type == "medium"
        assert result.scene.setting == "indoor"
        assert result.scene.people_count == 1
        assert result.viral.hook_potential == 75
        assert result.viral.curiosity_gap == True
    
    @pytest.mark.asyncio
    async def test_analyze_frame_file_not_found(self, analyzer):
        """Test analysis with missing file"""
        with pytest.raises(FileNotFoundError):
            await analyzer.analyze_frame_structured(
                image_path=Path("/nonexistent/frame.jpg"),
                frame_index=0,
                timestamp=0.0
            )
    
    @pytest.mark.asyncio
    async def test_compare_frames_for_motion(self, analyzer, mock_openai_comparison_response):
        """Test frame comparison for motion detection"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_comparison_response)
        
        analyzer.client.chat.completions.create = Mock(return_value=mock_response)
        
        with patch.object(analyzer, 'encode_image', return_value="base64encoded"):
            result = await analyzer.compare_frames_for_motion(
                frame1_path=Path("/test/frame1.jpg"),
                frame2_path=Path("/test/frame2.jpg"),
                time_delta=1.0
            )
        
        assert result["camera_motion"]["detected"] == True
        assert result["camera_motion"]["type"] == "zoom"
        assert result["camera_motion"]["direction"] == "in"
        assert result["scene_change"]["is_same_scene"] == True


class TestOpenCVMotionDetection:
    """Tests for OpenCV-based motion detection"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer"""
        with patch('services.enhanced_vision_analyzer.OpenAI'):
            from services.enhanced_vision_analyzer import EnhancedVisionAnalyzer
            return EnhancedVisionAnalyzer(openai_api_key="test")
    
    @pytest.mark.skipif(not pytest.importorskip("cv2", reason="OpenCV not installed"), reason="OpenCV required")
    def test_detect_motion_opencv_static(self, analyzer, tmp_path):
        """Test motion detection on identical frames (should be static)"""
        import cv2
        
        # Create two identical test images
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[40:60, 40:60] = [255, 255, 255]  # White square
        
        frame1 = tmp_path / "frame1.jpg"
        frame2 = tmp_path / "frame2.jpg"
        
        cv2.imwrite(str(frame1), img)
        cv2.imwrite(str(frame2), img)
        
        result = analyzer.detect_motion_opencv(frame1, frame2)
        
        assert result["motion_detected"] == False
        assert result["motion_type"] == "static"
    
    @pytest.mark.skipif(not pytest.importorskip("cv2", reason="OpenCV not installed"), reason="OpenCV required")
    def test_detect_motion_opencv_scene_change(self, analyzer, tmp_path):
        """Test motion detection for scene change"""
        import cv2
        
        # Create two very different images
        img1 = np.zeros((100, 100, 3), dtype=np.uint8)
        img2 = np.ones((100, 100, 3), dtype=np.uint8) * 255
        
        frame1 = tmp_path / "frame1.jpg"
        frame2 = tmp_path / "frame2.jpg"
        
        cv2.imwrite(str(frame1), img1)
        cv2.imwrite(str(frame2), img2)
        
        result = analyzer.detect_motion_opencv(frame1, frame2)
        
        assert result["scene_change_score"] > 50
        assert result["is_scene_boundary"] == True
    
    def test_detect_motion_opencv_missing_file(self, analyzer):
        """Test motion detection with missing file"""
        result = analyzer.detect_motion_opencv(
            Path("/nonexistent1.jpg"),
            Path("/nonexistent2.jpg")
        )
        
        assert "error" in result or result["motion_detected"] == False


class TestSceneBoundaryDetection:
    """Tests for scene boundary detection"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer"""
        with patch('services.enhanced_vision_analyzer.OpenAI'):
            from services.enhanced_vision_analyzer import EnhancedVisionAnalyzer
            return EnhancedVisionAnalyzer(openai_api_key="test")
    
    @pytest.mark.asyncio
    async def test_detect_scene_boundaries_empty(self, analyzer):
        """Test scene detection with empty frame list"""
        boundaries = await analyzer.detect_scene_boundaries([], [])
        assert len(boundaries) == 0
    
    @pytest.mark.asyncio
    async def test_detect_scene_boundaries_single_frame(self, analyzer):
        """Test scene detection with single frame"""
        boundaries = await analyzer.detect_scene_boundaries(
            [Path("/test/frame1.jpg")],
            [0.0]
        )
        assert len(boundaries) == 0


class TestCameraMotionSequence:
    """Tests for camera motion sequence detection"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer"""
        with patch('services.enhanced_vision_analyzer.OpenAI'):
            from services.enhanced_vision_analyzer import EnhancedVisionAnalyzer
            return EnhancedVisionAnalyzer(openai_api_key="test")
    
    @pytest.mark.asyncio
    async def test_detect_camera_motion_empty(self, analyzer):
        """Test motion detection with empty frame list"""
        motions = await analyzer.detect_camera_motion_sequence([], [])
        assert len(motions) == 0


class TestVisualStyleAggregation:
    """Tests for style aggregation from multiple frames"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer"""
        with patch('services.enhanced_vision_analyzer.OpenAI'):
            from services.enhanced_vision_analyzer import EnhancedVisionAnalyzer
            return EnhancedVisionAnalyzer(openai_api_key="test")
    
    def test_aggregate_style_empty(self, analyzer):
        """Test style aggregation with empty list"""
        result = analyzer._aggregate_style([])
        assert result == {}
    
    def test_aggregate_style_single_frame(self, analyzer):
        """Test style aggregation with single frame"""
        frame_analyses = [{
            "camera": {"shot_type": "close-up", "angle": "eye-level"},
            "lighting": {"type": "natural"},
            "color_palette": {"mood": "warm"}
        }]
        
        result = analyzer._aggregate_style(frame_analyses)
        
        assert result["dominant_shot_type"] == "close-up"
        assert result["dominant_angle"] == "eye-level"
        assert result["dominant_lighting"] == "natural"
        assert result["dominant_mood"] == "warm"
    
    def test_aggregate_style_multiple_frames(self, analyzer):
        """Test style aggregation with multiple frames"""
        frame_analyses = [
            {"camera": {"shot_type": "medium", "angle": "eye-level"},
             "lighting": {"type": "natural"}, "color_palette": {"mood": "warm"}},
            {"camera": {"shot_type": "medium", "angle": "low"},
             "lighting": {"type": "natural"}, "color_palette": {"mood": "warm"}},
            {"camera": {"shot_type": "close-up", "angle": "eye-level"},
             "lighting": {"type": "studio"}, "color_palette": {"mood": "cool"}},
        ]
        
        result = analyzer._aggregate_style(frame_analyses)
        
        # Medium appears twice, should be dominant
        assert result["dominant_shot_type"] == "medium"
        assert result["dominant_lighting"] == "natural"
        assert result["dominant_mood"] == "warm"
    
    def test_extract_dominant_colors(self, analyzer):
        """Test color extraction from frames"""
        frame_analyses = [
            {"color_palette": {"primary": "#FF0000", "colors": ["#FF0000", "#00FF00"]}},
            {"color_palette": {"primary": "#FF0000", "colors": ["#FF0000", "#0000FF"]}},
            {"color_palette": {"primary": "#00FF00", "colors": ["#00FF00"]}},
        ]
        
        colors = analyzer._extract_dominant_colors(frame_analyses)
        
        assert "#FF0000" in colors  # Appears most frequently
        assert len(colors) <= 10
    
    def test_generate_summary(self, analyzer):
        """Test summary generation"""
        results = {
            "frame_analyses": [
                {"camera": {"shot_type": "medium"}, "lighting": {"type": "natural"}, 
                 "color_palette": {"mood": "warm"}}
            ],
            "scene_boundaries": [{"timestamp": 5.0}],
            "camera_motions": [],
            "overall_style": {
                "dominant_shot_type": "medium",
                "dominant_lighting": "natural",
                "dominant_mood": "warm"
            }
        }
        
        summary = analyzer._generate_summary(results)
        
        assert "medium" in summary.lower() or "style" in summary.lower()
        assert "2 scenes" in summary or "scene" in summary.lower()


# ============================================================================
# Dataclass Tests
# ============================================================================

class TestDataclasses:
    """Tests for dataclass structures"""
    
    def test_color_palette_creation(self):
        """Test ColorPalette dataclass"""
        from services.enhanced_vision_analyzer import ColorPalette
        
        palette = ColorPalette(
            primary="#FF0000",
            secondary="#00FF00",
            accent="#0000FF",
            colors=["#FF0000", "#00FF00"],
            mood="vibrant",
            contrast_level="high"
        )
        
        assert palette.primary == "#FF0000"
        assert palette.mood == "vibrant"
    
    def test_lighting_analysis_creation(self):
        """Test LightingAnalysis dataclass"""
        from services.enhanced_vision_analyzer import LightingAnalysis
        
        lighting = LightingAnalysis(
            type="studio",
            direction="front",
            quality="soft",
            exposure="proper",
            shadows="minimal"
        )
        
        assert lighting.type == "studio"
        assert lighting.shadows == "minimal"
    
    def test_camera_info_creation(self):
        """Test CameraInfo dataclass"""
        from services.enhanced_vision_analyzer import CameraInfo
        
        camera = CameraInfo(
            shot_type="close-up",
            angle="eye-level",
            movement="pan",
            movement_confidence=0.8,
            depth_of_field="shallow"
        )
        
        assert camera.shot_type == "close-up"
        assert camera.movement_confidence == 0.8
    
    def test_scene_boundary_creation(self):
        """Test SceneBoundary dataclass"""
        from services.enhanced_vision_analyzer import SceneBoundary
        
        boundary = SceneBoundary(
            frame_index=30,
            timestamp=1.0,
            boundary_type="cut",
            confidence=0.95,
            visual_change_score=85.0,
            previous_scene_summary="Person talking",
            next_scene_preview="B-roll footage"
        )
        
        assert boundary.frame_index == 30
        assert boundary.boundary_type == "cut"
        assert boundary.confidence == 0.95
    
    def test_camera_motion_sequence_creation(self):
        """Test CameraMotionSequence dataclass"""
        from services.enhanced_vision_analyzer import CameraMotionSequence
        
        motion = CameraMotionSequence(
            start_frame=0,
            end_frame=30,
            start_time=0.0,
            end_time=1.0,
            motion_type="zoom",
            confidence=0.9,
            direction="in",
            speed="slow"
        )
        
        assert motion.motion_type == "zoom"
        assert motion.direction == "in"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
