"""
Tests for Video Ready Pipeline

Tests the workflow: Video Ready → AI Analyze → Publish to YouTube/TikTok
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile

# Add Backend to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.video_ready_pipeline import (
    VideoReadyPipeline,
    VideoReadyWebhookHandler,
    VideoReadyEvent,
    AnalysisResult
)


class TestVideoReadyPipeline:
    """Tests for VideoReadyPipeline class"""
    
    @pytest.fixture
    def pipeline(self):
        """Create a pipeline instance"""
        return VideoReadyPipeline()
    
    @pytest.fixture
    def mock_video_file(self):
        """Create a temporary video file for testing"""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            # Write some dummy content
            f.write(b"fake video content")
            yield f.name
        # Cleanup
        if os.path.exists(f.name):
            os.unlink(f.name)
    
    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly"""
        assert pipeline is not None
        assert pipeline.blotato is not None
        assert pipeline.DEFAULT_ACCOUNTS["youtube"] == 228
        assert pipeline.DEFAULT_ACCOUNTS["tiktok"] == 710
    
    def test_default_accounts_configured(self, pipeline):
        """Test default accounts are configured for all platforms"""
        assert "youtube" in pipeline.DEFAULT_ACCOUNTS
        assert "tiktok" in pipeline.DEFAULT_ACCOUNTS
        assert "instagram" in pipeline.DEFAULT_ACCOUNTS
        assert "threads" in pipeline.DEFAULT_ACCOUNTS
    
    @pytest.mark.asyncio
    async def test_process_video_ready_file_not_found(self, pipeline):
        """Test error handling when video file doesn't exist"""
        result = await pipeline.process_video_ready(
            video_path="/nonexistent/video.mp4",
            source="test",
            publish_to=["youtube"]
        )
        
        assert result["status"] == "error"
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_video_ready_with_mock_analysis(self, pipeline, mock_video_file):
        """Test processing with mocked AI analysis"""
        # Mock the analyze_video method
        mock_analysis = AnalysisResult(
            transcript="Test transcript",
            summary="Test summary",
            suggested_caption="Check this out! 🔥",
            hashtags=["#viral", "#fyp"],
            virality_score=85.0,
            duration_seconds=30.0,
            detected_topics=["entertainment"]
        )
        
        with patch.object(pipeline, 'analyze_video', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_analysis
            
            # Also mock publishing
            with patch.object(pipeline, 'publish_to_platform', new_callable=AsyncMock) as mock_publish:
                mock_publish.return_value = {"success": True, "post_id": "123"}
                
                result = await pipeline.process_video_ready(
                    video_path=mock_video_file,
                    source="test",
                    publish_to=["youtube", "tiktok"],
                    auto_publish=True
                )
                
                assert result["status"] == "completed"
                assert result["analysis"]["suggested_caption"] == "Check this out! 🔥"
                assert result["analysis"]["virality_score"] == 85.0
                assert len(result["publish_results"]) == 2
    
    @pytest.mark.asyncio
    async def test_process_video_ready_no_publish(self, pipeline, mock_video_file):
        """Test processing without auto-publish"""
        mock_analysis = AnalysisResult(
            transcript="Test",
            summary="Summary",
            suggested_caption="Caption",
            hashtags=[],
            virality_score=50.0,
            duration_seconds=15.0,
            detected_topics=[]
        )
        
        with patch.object(pipeline, 'analyze_video', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_analysis
            
            result = await pipeline.process_video_ready(
                video_path=mock_video_file,
                source="test",
                publish_to=["youtube"],
                auto_publish=False  # Don't publish
            )
            
            assert result["status"] == "completed"
            assert result["publish_results"] == []  # No publishing


class TestVideoReadyWebhookHandler:
    """Tests for webhook handler"""
    
    @pytest.fixture
    def handler(self):
        return VideoReadyWebhookHandler()
    
    def test_handler_initialization(self, handler):
        """Test handler initializes correctly"""
        assert handler is not None
        assert handler.pipeline is not None
    
    @pytest.mark.asyncio
    async def test_handle_sora_video_ready(self, handler):
        """Test Sora video ready handler"""
        with patch.object(handler.pipeline, 'process_video_ready', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"status": "completed"}
            
            # Create a temp file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(b"fake")
                
                result = await handler.handle_sora_video_ready(
                    video_path=f.name,
                    prompt="@isaiahdupree on Mars",
                    character="isaiahdupree"
                )
                
                # Verify process was called with correct args
                mock_process.assert_called_once()
                call_args = mock_process.call_args
                assert call_args.kwargs["source"] == "sora"
                assert "youtube" in call_args.kwargs["publish_to"]
                assert "tiktok" in call_args.kwargs["publish_to"]
                
                os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_handle_watermark_removal_complete(self, handler):
        """Test watermark removal complete handler"""
        with patch.object(handler.pipeline, 'process_video_ready', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"status": "completed"}
            
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(b"fake")
                
                result = await handler.handle_watermark_removal_complete(
                    video_path=f.name,
                    original_path="/original/video.mp4"
                )
                
                mock_process.assert_called_once()
                call_args = mock_process.call_args
                assert call_args.kwargs["source"] == "watermark_removal"
                assert call_args.kwargs["metadata"]["cleaned"] == True
                
                os.unlink(f.name)


class TestVideoReadyEvent:
    """Tests for VideoReadyEvent dataclass"""
    
    def test_event_creation(self):
        """Test event creation"""
        event = VideoReadyEvent(
            video_path="/path/to/video.mp4",
            source="sora",
            metadata={"prompt": "test"}
        )
        
        assert event.video_path == "/path/to/video.mp4"
        assert event.source == "sora"
        assert event.metadata["prompt"] == "test"
        assert event.timestamp is not None


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass"""
    
    def test_analysis_result_creation(self):
        """Test analysis result creation"""
        result = AnalysisResult(
            transcript="Hello world",
            summary="A greeting",
            suggested_caption="Watch this! 🎬",
            hashtags=["#hello", "#world"],
            virality_score=75.5,
            duration_seconds=45.0,
            detected_topics=["greeting", "introduction"]
        )
        
        assert result.transcript == "Hello world"
        assert result.virality_score == 75.5
        assert len(result.hashtags) == 2


class TestIntegration:
    """Integration tests (require API keys)"""
    
    @pytest.fixture
    def pipeline(self):
        return VideoReadyPipeline()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    async def test_real_transcription(self, pipeline):
        """Test real transcription with OpenAI (requires API key)"""
        # This test would use a real video file
        # Skip for now unless explicitly running integration tests
        pass
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("BLOTATO_API_KEY"),
        reason="BLOTATO_API_KEY not set"
    )
    async def test_real_blotato_upload(self, pipeline):
        """Test real Blotato upload (requires API key)"""
        # This test would use a real video file and upload to Blotato
        # Skip for now unless explicitly running integration tests
        pass


# Quick test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
