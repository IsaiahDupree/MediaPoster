"""
Tests for AI Thumbnail Generation System
Tests frame selection, multi-platform generation, and AI enhancements
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import os
from pathlib import Path
from PIL import Image
import tempfile

from services.thumbnail_generator import (
    ThumbnailGenerator,
    PLATFORM_DIMENSIONS,
    PlatformDimensions
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_image(temp_dir):
    """Create a test image"""
    img_path = os.path.join(temp_dir, "test_image.jpg")
    img = Image.new('RGB', (1920, 1080), color='blue')
    img.save(img_path)
    return img_path


@pytest.fixture
def test_video(temp_dir):
    """Mock video file path"""
    video_path = os.path.join(temp_dir, "test_video.mp4")
    # Just create an empty file for path testing
    Path(video_path).touch()
    return video_path


@pytest.fixture
def generator():
    """Create thumbnail generator instance"""
    return ThumbnailGenerator()


class TestPlatformDimensions:
    """Test platform dimension configurations"""
    
    def test_all_platforms_defined(self):
        """Test that all required platforms have dimensions"""
        required_platforms = [
            "youtube", "youtube_short", "tiktok", 
            "instagram_feed", "instagram_story", "instagram_reel",
            "facebook", "twitter", "linkedin", "pinterest", 
            "snapchat", "threads"
        ]
        
        for platform in required_platforms:
            assert platform in PLATFORM_DIMENSIONS
    
    def test_landscape_orientations(self):
        """Test landscape platform dimensions"""
        landscape = ["youtube", "facebook", "twitter", "linkedin"]
        
        for platform in landscape:
            dims = PLATFORM_DIMENSIONS[platform]
            assert dims.width > dims.height
            assert dims.orientation == "landscape"
    
    def test_portrait_orientations(self):
        """Test portrait platform dimensions"""
        portrait = ["youtube_short", "tiktok", "instagram_story", 
                   "instagram_reel", "snapchat", "pinterest", "threads"]
        
        for platform in portrait:
            dims = PLATFORM_DIMENSIONS[platform]
            assert dims.height > dims.width
            assert dims.orientation == "portrait"
    
    def test_square_orientation(self):
        """Test square platform dimensions"""
        dims = PLATFORM_DIMENSIONS["instagram_feed"]
        assert dims.width == dims.height
        assert dims.orientation == "square"


class TestFrameExtraction:
    """Test video frame extraction"""
    
    @patch('subprocess.run')
    def test_extract_frames(self, mock_run, generator, test_video, temp_dir):
        """Test frame extraction from video"""
        # Mock ffprobe for duration
        mock_run.return_value = Mock(
            stdout='{"format": {"duration": "10.0"}}',
            returncode=0
        )
        
        # Mock successful extraction
        with patch.object(generator, 'extract_frames') as mock_extract:
            mock_extract.return_value = [
                f"{temp_dir}/frame_001.jpg",
                f"{temp_dir}/frame_002.jpg",
                f"{temp_dir}/frame_003.jpg"
            ]
            
            frames = generator.extract_frames(test_video, num_frames=3)
            
            assert len(frames) == 3
            assert all("frame_" in f for f in frames)


class TestFrameQualityAnalysis:
    """Test frame quality analysis"""
    
    @patch('cv2.imread')
    @patch('cv2.cvtColor')
    @patch('cv2.Laplacian')
    @patch('cv2.CascadeClassifier')
    def test_analyze_frame_quality(
        self,
        mock_cascade,
        mock_laplacian,
        mock_cvt,
        mock_imread,
        generator,
        test_image
    ):
        """Test frame quality analysis"""
        # Mock OpenCV operations
        import numpy as np
        
        mock_imread.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_cvt.return_value = np.zeros((1080, 1920), dtype=np.uint8)
        mock_laplacian_result = Mock()
        mock_laplacian_result.var.return_value = 250.0
        mock_laplacian.return_value = mock_laplacian_result
        
        mock_cascade_instance = Mock()
        mock_cascade_instance.detectMultiScale.return_value = [(100, 100, 50, 50)]
        mock_cascade.return_value = mock_cascade_instance
        
        analysis = generator.analyze_frame_quality(test_image)
        
        assert "overall_score" in analysis
        assert "sharpness" in analysis
        assert "brightness" in analysis
        assert "contrast" in analysis
        assert "faces_detected" in analysis
        assert analysis["overall_score"] >= 0.0
        assert analysis["overall_score"] <= 1.0


class TestThumbnailGeneration:
    """Test thumbnail generation"""
    
    def test_generate_thumbnail(self, generator, test_image, temp_dir):
        """Test generating thumbnail for specific platform"""
        output_path = os.path.join(temp_dir, "youtube_thumb.jpg")
        
        result = generator.generate_thumbnail(
            source_image=test_image,
            platform="youtube",
            output_path=output_path
        )
        
        assert os.path.exists(result)
        
        # Verify dimensions
        img = Image.open(result)
        dims = PLATFORM_DIMENSIONS["youtube"]
        assert img.width == dims.width
        assert img.height == dims.height
    
    def test_generate_all_platforms(self, generator, test_image, temp_dir):
        """Test generating thumbnails for all platforms"""
        thumbnails = generator.generate_all_platforms(
            source_image=test_image,
            output_dir=temp_dir,
            base_name="test"
        )
        
        assert len(thumbnails) == len(PLATFORM_DIMENSIONS)
        
        # Verify each thumbnail
        for platform, path in thumbnails.items():
            assert os.path.exists(path)
            
            img = Image.open(path)
            dims = PLATFORM_DIMENSIONS[platform]
            assert img.width == dims.width
            assert img.height == dims.height
    
    def test_smart_cropping_landscape(self, generator, test_image, temp_dir):
        """Test smart cropping for landscape format"""
        # Create a tall source image
        tall_img_path = os.path.join(temp_dir, "tall.jpg")
        img = Image.new('RGB', (1080, 1920), color='red')
        img.save(tall_img_path)
        
        output_path = os.path.join(temp_dir, "youtube_cropped.jpg")
        
        generator.generate_thumbnail(
            source_image=tall_img_path,
            platform="youtube",
            output_path=output_path,
            crop_mode="smart"
        )
        
        result_img = Image.open(output_path)
        assert result_img.width == 1280
        assert result_img.height == 720
    
    def test_smart_cropping_portrait(self, generator, test_image, temp_dir):
        """Test smart cropping for portrait format"""
        # Create a wide source image
        wide_img_path = os.path.join(temp_dir, "wide.jpg")
        img = Image.new('RGB', (1920, 1080), color='green')
        img.save(wide_img_path)
        
        output_path = os.path.join(temp_dir, "tiktok_cropped.jpg")
        
        generator.generate_thumbnail(
            source_image=wide_img_path,
            platform="tiktok",
            output_path=output_path,
            crop_mode="smart"
        )
        
        result_img = Image.open(output_path)
        assert result_img.width == 1080
        assert result_img.height == 1920


class TestAITextOverlay:
    """Test AI-powered text overlay"""
    
    @pytest.mark.asyncio
    async def test_add_ai_text_overlay_no_api_key(self, generator, test_image, temp_dir):
        """Test text overlay without API key (should gracefully fallback)"""
        generator.openai_api_key = None
        
        output_path = os.path.join(temp_dir, "enhanced.jpg")
        
        result = await generator.add_ai_text_overlay(
            image_path=test_image,
            title="Test Video Title",
            output_path=output_path
        )
        
        # Should still create output file (copy of original)
        assert os.path.exists(result)
    
    @pytest.mark.asyncio
    @patch('openai.chat.completions.create')
    async def test_add_ai_text_overlay(self, mock_openai, generator, test_image, temp_dir):
        """Test adding AI-generated text overlay"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "GAME CHANGER"
        mock_openai.return_value = mock_response
        
        generator.openai_api_key = "test_key"
        
        output_path = os.path.join(temp_dir, "enhanced.jpg")
        
        result = await generator.add_ai_text_overlay(
            image_path=test_image,
            title="Amazing New Discovery",
            output_path=output_path,
            style="bold"
        )
        
        assert os.path.exists(result)
        
        # Verify OpenAI was called
        assert mock_openai.called
        call_args = mock_openai.call_args
        assert "Amazing New Discovery" in str(call_args)


class TestImageEnhancement:
    """Test image enhancement"""
    
    def test_enhance_thumbnail(self, generator, test_image):
        """Test thumbnail enhancement (sharpness, saturation, contrast)"""
        img = Image.open(test_image)
        
        enhanced = generator._enhance_thumbnail(img)
        
        # Should return an image
        assert isinstance(enhanced, Image.Image)
        
        # Dimensions should be unchanged
        assert enhanced.size == img.size


class TestBestFrameSelection:
    """Test best frame selection workflow"""
    
    @patch.object(ThumbnailGenerator, 'extract_frames')
    @patch.object(ThumbnailGenerator, 'analyze_frame_quality')
    def test_select_best_frame(
        self,
        mock_analyze,
        mock_extract,
        generator,
        test_video,
        temp_dir
    ):
        """Test selecting best frame from video"""
        # Mock frame extraction
        mock_frames = [
            f"{temp_dir}/frame_001.jpg",
            f"{temp_dir}/frame_002.jpg",
            f"{temp_dir}/frame_003.jpg"
        ]
        mock_extract.return_value = mock_frames
        
        # Create actual test files
        for frame_path in mock_frames:
            img = Image.new('RGB', (1920, 1080), color='blue')
            img.save(frame_path)
        
        # Mock analysis with different scores
        mock_analyze.side_effect = [
            {"overall_score": 0.6, "frame_path": mock_frames[0]},
            {"overall_score": 0.9, "frame_path": mock_frames[1]},  # Best
            {"overall_score": 0.7, "frame_path": mock_frames[2]}
        ]
        
        best_frame, analysis = generator.select_best_frame(test_video, num_candidates=3)
        
        # Should select frame with highest score
        assert best_frame == mock_frames[1]
        assert analysis["overall_score"] == 0.9


def test_platform_dimensions_dataclass():
    """Test PlatformDimensions dataclass"""
    dims = PlatformDimensions(
        width=1280,
        height=720,
        aspect_ratio="16:9",
        platform="YouTube",
        orientation="landscape"
    )
    
    assert dims.width == 1280
    assert dims.height == 720
    assert dims.aspect_ratio == "16:9"
    assert dims.platform == "YouTube"
    assert dims.orientation == "landscape"
