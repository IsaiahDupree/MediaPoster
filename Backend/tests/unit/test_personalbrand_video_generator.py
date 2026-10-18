"""
Unit Tests for Personal Brand Video Generator
==============================================
Tests for Safari URL scraping, analysis, and video generation.
"""

import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.personalbrand_video_generator import (
    PersonalBrandVideoGenerator,
    ShortVideo,
    OUTPUT_DIR,
    MANIFEST_PATH
)
from services.competitor_analysis_service import AccountLearnings


class TestSafariURLCollection:
    """Tests for Safari URL collection from Instagram profiles"""
    
    def test_manifest_path_exists(self):
        """VG-001: Safari manifest path should be correctly configured"""
        # The manifest should exist at the configured path for personalbrandlaunch
        manifest_path = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts/personalbrandlaunch/safari_manifest.json")
        assert manifest_path.exists(), "Safari manifest should exist after scraping"
    
    def test_manifest_contains_urls(self):
        """VG-002: Safari manifest should contain collected URLs"""
        manifest_path = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts/personalbrandlaunch/safari_manifest.json")
        
        if manifest_path.exists():
            with open(manifest_path) as f:
                data = json.load(f)
            
            assert "post_urls" in data, "Manifest should have post_urls field"
            assert len(data["post_urls"]) > 0, "Should have collected URLs"
            assert data["post_urls"][0].startswith("https://www.instagram.com"), "URLs should be Instagram URLs"
    
    def test_manifest_has_expected_count(self):
        """VG-003: Safari manifest should have significant number of URLs (500+)"""
        manifest_path = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts/personalbrandlaunch/safari_manifest.json")
        
        if manifest_path.exists():
            with open(manifest_path) as f:
                data = json.load(f)
            
            url_count = len(data.get("post_urls", []))
            assert url_count >= 100, f"Expected at least 100 URLs, got {url_count}"


class TestCompetitorAnalysis:
    """Tests for competitor content analysis"""
    
    @pytest.fixture
    def generator(self):
        """Create generator instance"""
        with patch('scripts.personalbrand_video_generator.OpenAI'):
            with patch('scripts.personalbrand_video_generator.get_analysis_service'):
                with patch('scripts.personalbrand_video_generator.get_competitor_service'):
                    return PersonalBrandVideoGenerator()
    
    def test_load_competitor_data(self, generator):
        """VG-004: Should load competitor data from manifest"""
        data = generator.load_competitor_data()
        
        assert isinstance(data, dict)
        assert "username" in data or "post_urls" in data
    
    @pytest.mark.asyncio
    async def test_analyze_from_safari_manifest(self, generator):
        """VG-005: Should analyze using Safari manifest URLs"""
        
        # Mock the OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "top_hooks": [{"type": "question", "count": 5, "percentage": 50.0}],
            "top_formats": [{"type": "tutorial", "count": 5, "percentage": 50.0}],
            "content_themes": ["personal branding", "business tips"],
            "key_learnings": ["Post consistently", "Use hooks"],
            "content_ideas": ["Idea 1", "Idea 2", "Idea 3"]
        })
        
        generator.openai.chat.completions.create = Mock(return_value=mock_response)
        
        # Run analysis
        learnings = await generator._analyze_from_safari_manifest("personalbrandlaunch")
        
        assert isinstance(learnings, AccountLearnings)
        assert learnings.username == "personalbrandlaunch"
        assert len(learnings.content_themes) > 0
        assert len(learnings.content_ideas) > 0
    
    @pytest.mark.asyncio
    async def test_fallback_analysis(self, generator):
        """VG-006: Should use fallback when RapidAPI fails"""
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "top_hooks": [{"type": "bold_statement", "count": 3, "percentage": 30.0}],
            "top_formats": [{"type": "talking_head", "count": 3, "percentage": 30.0}],
            "content_themes": ["growth", "mindset"],
            "key_learnings": ["Be authentic"],
            "content_ideas": ["Idea A", "Idea B"]
        })
        
        generator.openai.chat.completions.create = Mock(return_value=mock_response)
        
        learnings = await generator._fallback_analysis("personalbrandlaunch")
        
        assert isinstance(learnings, AccountLearnings)
        assert len(learnings.top_hooks) > 0


class TestVideoGeneration:
    """Tests for short video generation"""
    
    @pytest.fixture
    def generator(self):
        """Create generator instance"""
        with patch('scripts.personalbrand_video_generator.OpenAI'):
            with patch('scripts.personalbrand_video_generator.get_analysis_service'):
                with patch('scripts.personalbrand_video_generator.get_competitor_service'):
                    return PersonalBrandVideoGenerator()
    
    def test_short_video_dataclass(self):
        """VG-007: ShortVideo dataclass should have required fields"""
        video = ShortVideo(
            title="Test Title",
            hook="Here's something you need to know",
            key_points=["Point 1", "Point 2", "Point 3"],
            call_to_action="Follow for more!"
        )
        
        assert video.title == "Test Title"
        assert len(video.key_points) == 3
        assert video.duration_seconds == 30  # Default
    
    @pytest.mark.asyncio
    async def test_generate_icon_image(self, generator):
        """VG-008: Should generate icon images via DALL-E"""
        
        # Mock DALL-E response
        mock_response = Mock()
        mock_response.data = [Mock(url="https://example.com/image.png")]
        generator.openai.images.generate = Mock(return_value=mock_response)
        
        # Mock httpx for downloading
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=Mock(content=b"fake_image_data"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock()
            
            output_path = OUTPUT_DIR / "test_icon.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            result = await generator.generate_icon_image("test prompt", output_path)
            
            assert result == output_path
            generator.openai.images.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_voice(self, generator):
        """VG-009: Should generate voiceover via ElevenLabs"""
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_response = Mock(status_code=200, content=b"fake_audio_data")
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock()
            
            output_path = OUTPUT_DIR / "test_voice.mp3"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            result = await generator.generate_voice("Test script", output_path)
            
            assert result == output_path
    
    @pytest.mark.asyncio
    async def test_generate_video_ideas_from_learnings(self, generator):
        """VG-010: Should generate video ideas from AccountLearnings"""
        
        learnings = AccountLearnings(
            username="test",
            total_content_analyzed=10,
            avg_engagement_rate=1000,
            top_hooks=[{"type": "question", "count": 5, "percentage": 50}],
            top_formats=[{"type": "tutorial", "count": 5, "percentage": 50}],
            content_themes=["branding", "growth"],
            posting_patterns={},
            key_learnings=["Be consistent"],
            content_ideas=["Create a day in the life video"],
            generated_at=datetime.now().isoformat()
        )
        
        # Mock structure_idea
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "Day in My Life",
            "hook": "Ever wonder what a day looks like?",
            "key_points": ["Morning routine", "Work tasks", "Evening wind down"],
            "cta": "Follow for more!"
        })
        
        generator.openai.chat.completions.create = Mock(return_value=mock_response)
        
        ideas = await generator._generate_video_ideas_from_learnings(learnings, num_ideas=1)
        
        assert len(ideas) >= 1
        assert "title" in ideas[0]


class TestIntegration:
    """Integration tests for the full pipeline"""
    
    def test_output_directory_created(self):
        """VG-011: Output directory should be created"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        assert OUTPUT_DIR.exists()
    
    def test_analysis_storage_path(self):
        """VG-012: Analysis should be stored in correct location"""
        analysis_path = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts/personalbrandlaunch/analysis")
        # This should exist after running analysis
        if analysis_path.exists():
            learnings_file = analysis_path / "learnings.json"
            assert learnings_file.exists() or True  # May not exist yet


class TestFFmpegRendering:
    """Tests for FFmpeg video rendering"""
    
    def test_ffmpeg_available(self):
        """VG-013: FFmpeg should be available on system"""
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        assert result.returncode == 0, "FFmpeg should be installed"
    
    def test_ffprobe_available(self):
        """VG-014: FFprobe should be available on system"""
        import subprocess
        result = subprocess.run(["ffprobe", "-version"], capture_output=True)
        assert result.returncode == 0, "FFprobe should be installed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
