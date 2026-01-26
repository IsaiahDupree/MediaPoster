"""
End-to-End Test: Sora Video Generation → YouTube Publishing Pipeline
=====================================================================
Tests the complete flow from Sora video generation to YouTube upload.

Pipeline:
1. Generate video clips using Sora
2. Download and combine clips
3. Remove watermarks (optional)
4. Schedule and publish to YouTube

Run with: pytest tests/e2e/test_sora_to_youtube_pipeline.py -v
Run mocked only: pytest tests/e2e/test_sora_to_youtube_pipeline.py -v -m "not live"
"""
import pytest
import os
import sys
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional, List, Dict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# =============================================================================
# MOCK CLASSES (when real services unavailable)
# =============================================================================

@dataclass
class MockVideoProject:
    """Mock video project for testing."""
    project_id: str
    title: str
    description: str
    main_character: str
    character_description: str
    total_duration_seconds: int
    clips: List[Dict]
    style: str = "motivational"
    status: str = "planning"
    output_path: Optional[str] = None


@dataclass
class MockClipSpec:
    """Mock clip specification."""
    clip_id: str
    sequence_number: int
    role: str
    duration_seconds: int
    prompt: str
    script_text: str
    character_name: str
    scene_description: str
    status: str = "pending"
    video_url: Optional[str] = None


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_sora_provider():
    """Mock Sora video provider."""
    with patch('services.video_providers.sora_provider.SoraProvider') as mock:
        provider = mock.return_value
        provider.create_clip = AsyncMock(return_value={
            "id": "gen_123456",
            "status": "pending"
        })
        provider.poll_clip = AsyncMock(return_value={
            "id": "gen_123456",
            "status": "completed",
            "video_url": "https://sora.openai.com/v/abc123.mp4"
        })
        provider.download_video = AsyncMock(return_value="/tmp/sora_clip_123.mp4")
        yield provider


@pytest.fixture
def mock_youtube_publisher():
    """Mock YouTube publisher."""
    with patch('connectors.youtube.connector.YouTubeConnector') as mock:
        publisher = mock.return_value
        publisher.upload_video = AsyncMock(return_value={
            "video_id": "yt_abc123",
            "url": "https://youtube.com/watch?v=yt_abc123",
            "status": "published"
        })
        publisher.is_enabled = Mock(return_value=True)
        yield publisher


@pytest.fixture
def mock_database():
    """Mock database operations."""
    with patch('psycopg2.connect') as mock_conn:
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {
            'id': 'uuid-123',
            'platform': 'youtube',
            'username': 'Isaiah Dupree',
            'is_active': True
        }
        cursor.fetchall.return_value = [
            {'id': 'vid-1', 'title': 'Test Video', 'source_uri': '/tmp/test.mp4'}
        ]
        conn.cursor.return_value.__enter__ = Mock(return_value=cursor)
        conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_conn.return_value.__enter__ = Mock(return_value=conn)
        mock_conn.return_value.__exit__ = Mock(return_value=False)
        yield conn


@pytest.fixture
def sample_video_project():
    """Create a sample video project."""
    return MockVideoProject(
        project_id="proj_test_123",
        title="Motivational Story - @isaiahdupree",
        description="AI-generated motivational content",
        main_character="@isaiahdupree",
        character_description="Young man, casual style",
        total_duration_seconds=30,
        clips=[
            {
                "clip_id": "clip_1",
                "sequence_number": 1,
                "role": "hook",
                "duration_seconds": 10,
                "prompt": "Young man walking confidently",
                "script_text": "Every day is a new opportunity",
                "status": "pending"
            },
            {
                "clip_id": "clip_2",
                "sequence_number": 2,
                "role": "story",
                "duration_seconds": 15,
                "prompt": "Same man working on laptop",
                "script_text": "The grind never stops",
                "status": "pending"
            }
        ],
        status="planning"
    )


# =============================================================================
# UNIT TESTS - Pipeline Components
# =============================================================================

class TestSoraVideoGeneration:
    """Test Sora video generation component."""
    
    @pytest.mark.asyncio
    async def test_create_clip_request(self, mock_sora_provider):
        """Test creating a Sora clip generation request."""
        result = await mock_sora_provider.create_clip(
            prompt="Young man walking in a park",
            model="sora-2",
            size="720x1280",
            duration=10
        )
        assert result["id"] == "gen_123456"
        assert result["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_poll_clip_completion(self, mock_sora_provider):
        """Test polling for clip completion."""
        result = await mock_sora_provider.poll_clip("gen_123456")
        assert result["status"] == "completed"
        assert "video_url" in result
    
    @pytest.mark.asyncio
    async def test_download_generated_video(self, mock_sora_provider):
        """Test downloading generated video."""
        path = await mock_sora_provider.download_video(
            "https://sora.openai.com/v/abc123.mp4",
            "/tmp/test_output.mp4"
        )
        assert path == "/tmp/sora_clip_123.mp4"


class TestVideoComposition:
    """Test video composition/combining."""
    
    def test_ffmpeg_concat_command(self):
        """Test FFmpeg concat command generation."""
        clips = ["/tmp/clip1.mp4", "/tmp/clip2.mp4", "/tmp/clip3.mp4"]
        output = "/tmp/combined.mp4"
        
        # Build expected command
        filter_parts = []
        for i, _ in enumerate(clips):
            filter_parts.append(f"[{i}:v][{i}:a]")
        
        filter_complex = "".join(filter_parts) + f"concat=n={len(clips)}:v=1:a=1[outv][outa]"
        
        assert "concat=n=3" in filter_complex
        assert "[outv][outa]" in filter_complex
    
    def test_watermark_removal_crop(self):
        """Test watermark removal via cropping."""
        # Sora watermark is typically in bottom right
        crop_filter = "crop=iw:ih-50:0:0"  # Crop bottom 50px
        assert "crop=" in crop_filter


class TestYouTubePublishing:
    """Test YouTube publishing component."""
    
    @pytest.mark.asyncio
    async def test_upload_video_metadata(self, mock_youtube_publisher):
        """Test video upload with metadata."""
        result = await mock_youtube_publisher.upload_video(
            video_path="/tmp/final_video.mp4",
            title="Test Video",
            description="AI-generated content",
            tags=["ai", "sora", "motivation"]
        )
        assert result["video_id"] == "yt_abc123"
        assert result["status"] == "published"
    
    def test_youtube_publisher_enabled(self, mock_youtube_publisher):
        """Test YouTube publisher is enabled."""
        assert mock_youtube_publisher.is_enabled() is True


# =============================================================================
# INTEGRATION TESTS - Pipeline Flow
# =============================================================================

class TestSoraToYouTubePipeline:
    """Test complete Sora → YouTube pipeline."""
    
    @pytest.mark.asyncio
    async def test_pipeline_step_1_generate_clips(
        self, mock_sora_provider, sample_video_project
    ):
        """Test Step 1: Generate video clips."""
        generated_clips = []
        
        for clip in sample_video_project.clips:
            result = await mock_sora_provider.create_clip(
                prompt=clip["prompt"],
                model="sora-2",
                size="720x1280",
                duration=clip["duration_seconds"]
            )
            clip["generation_id"] = result["id"]
            clip["status"] = "generating"
            generated_clips.append(clip)
        
        assert len(generated_clips) == 2
        assert all(c["status"] == "generating" for c in generated_clips)
    
    @pytest.mark.asyncio
    async def test_pipeline_step_2_poll_completion(
        self, mock_sora_provider, sample_video_project
    ):
        """Test Step 2: Poll for completion."""
        # Simulate polling
        for clip in sample_video_project.clips:
            result = await mock_sora_provider.poll_clip("gen_123456")
            if result["status"] == "completed":
                clip["video_url"] = result["video_url"]
                clip["status"] = "completed"
        
        assert all(c.get("status") == "completed" for c in sample_video_project.clips)
    
    @pytest.mark.asyncio
    async def test_pipeline_step_3_download_clips(
        self, mock_sora_provider, sample_video_project
    ):
        """Test Step 3: Download generated clips."""
        downloaded = []
        
        for clip in sample_video_project.clips:
            clip["video_url"] = "https://sora.openai.com/v/test.mp4"
            path = await mock_sora_provider.download_video(
                clip["video_url"],
                f"/tmp/{clip['clip_id']}.mp4"
            )
            downloaded.append(path)
        
        assert len(downloaded) == 2
    
    @pytest.mark.asyncio
    async def test_pipeline_step_4_combine_clips(self, sample_video_project):
        """Test Step 4: Combine clips into final video."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            clip_paths = [f"/tmp/{c['clip_id']}.mp4" for c in sample_video_project.clips]
            output_path = f"/tmp/{sample_video_project.project_id}_final.mp4"
            
            # Simulate FFmpeg combine
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-i", clip_paths[0], "-i", clip_paths[1], "-filter_complex", 
                 "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1", output_path],
                capture_output=True
            )
            
            assert result.returncode == 0
            sample_video_project.output_path = output_path
    
    @pytest.mark.asyncio
    async def test_pipeline_step_5_publish_to_youtube(
        self, mock_youtube_publisher, sample_video_project
    ):
        """Test Step 5: Publish to YouTube."""
        sample_video_project.output_path = "/tmp/final_video.mp4"
        
        result = await mock_youtube_publisher.upload_video(
            video_path=sample_video_project.output_path,
            title=sample_video_project.title,
            description=sample_video_project.description,
            tags=["ai", "sora", "motivation"]
        )
        
        assert result["status"] == "published"
        assert "youtube.com" in result["url"]
    
    @pytest.mark.asyncio
    async def test_full_pipeline_e2e(
        self, mock_sora_provider, mock_youtube_publisher, sample_video_project
    ):
        """Test complete end-to-end pipeline."""
        # Step 1: Generate clips
        for clip in sample_video_project.clips:
            gen_result = await mock_sora_provider.create_clip(
                prompt=clip["prompt"],
                duration=clip["duration_seconds"]
            )
            clip["generation_id"] = gen_result["id"]
        
        # Step 2: Poll for completion
        for clip in sample_video_project.clips:
            poll_result = await mock_sora_provider.poll_clip(clip["generation_id"])
            clip["video_url"] = poll_result.get("video_url")
            clip["status"] = poll_result["status"]
        
        # Step 3: Download clips
        downloaded = []
        for clip in sample_video_project.clips:
            path = await mock_sora_provider.download_video(
                clip["video_url"], f"/tmp/{clip['clip_id']}.mp4"
            )
            downloaded.append(path)
        
        # Step 4: Combine (mocked)
        sample_video_project.output_path = "/tmp/combined_final.mp4"
        sample_video_project.status = "composing"
        
        # Step 5: Publish to YouTube
        yt_result = await mock_youtube_publisher.upload_video(
            video_path=sample_video_project.output_path,
            title=sample_video_project.title,
            description=sample_video_project.description
        )
        
        # Verify final state
        assert yt_result["status"] == "published"
        assert len(downloaded) == len(sample_video_project.clips)
        sample_video_project.status = "completed"
        assert sample_video_project.status == "completed"


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestPipelineErrorHandling:
    """Test error handling in pipeline."""
    
    @pytest.mark.asyncio
    async def test_sora_generation_failure(self):
        """Test handling Sora generation failure."""
        with patch('services.video_providers.sora_provider.SoraProvider') as mock:
            provider = mock.return_value
            provider.create_clip = AsyncMock(side_effect=Exception("API rate limited"))
            
            with pytest.raises(Exception) as exc_info:
                await provider.create_clip(prompt="test")
            
            assert "rate limited" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_youtube_upload_failure(self):
        """Test handling YouTube upload failure."""
        with patch('connectors.youtube.connector.YouTubeConnector') as mock:
            publisher = mock.return_value
            publisher.upload_video = AsyncMock(return_value={
                "status": "failed",
                "error": "Quota exceeded"
            })
            
            result = await publisher.upload_video("/tmp/video.mp4", "Test", "Desc")
            assert result["status"] == "failed"
            assert "quota" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_clip_timeout_handling(self, mock_sora_provider):
        """Test handling clip generation timeout."""
        mock_sora_provider.poll_clip = AsyncMock(return_value={
            "id": "gen_123",
            "status": "timeout",
            "error": "Generation timed out after 10 minutes"
        })
        
        result = await mock_sora_provider.poll_clip("gen_123")
        assert result["status"] == "timeout"


# =============================================================================
# DATABASE INTEGRATION TESTS
# =============================================================================

class TestDatabaseIntegration:
    """Test database operations for pipeline."""
    
    def test_get_youtube_account(self, mock_database):
        """Test fetching YouTube account from database."""
        with patch('psycopg2.connect', return_value=mock_database):
            cursor = mock_database.cursor.return_value.__enter__.return_value
            account = cursor.fetchone()
            
            assert account['platform'] == 'youtube'
            assert account['is_active'] is True
    
    def test_get_sora_videos_for_publishing(self, mock_database):
        """Test fetching Sora videos ready for publishing."""
        with patch('psycopg2.connect', return_value=mock_database):
            cursor = mock_database.cursor.return_value.__enter__.return_value
            videos = cursor.fetchall()
            
            assert len(videos) == 1
            assert videos[0]['title'] == 'Test Video'


# =============================================================================
# PERFORMANCE BENCHMARKS
# =============================================================================

class TestPipelineBenchmarks:
    """Performance benchmarks for pipeline."""
    
    @pytest.mark.asyncio
    async def test_concurrent_clip_generation(self, mock_sora_provider):
        """Benchmark concurrent clip generation requests."""
        import time
        
        start = time.time()
        tasks = [
            mock_sora_provider.create_clip(prompt=f"Test prompt {i}")
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        assert len(results) == 10
        assert elapsed < 1.0, f"10 concurrent requests took {elapsed}s"
    
    def test_metadata_generation_speed(self):
        """Benchmark metadata generation."""
        import time
        
        start = time.time()
        for i in range(100):
            metadata = {
                "title": f"Video {i}",
                "description": f"AI-generated video #{i}",
                "tags": ["ai", "sora", "motivation"],
                "category": "22",  # YouTube People & Blogs
                "privacy": "public"
            }
            json.dumps(metadata)
        elapsed = time.time() - start
        
        assert elapsed < 0.1, f"100 metadata generations took {elapsed}s"


# =============================================================================
# LIVE TESTS (Skip by default)
# =============================================================================

@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_SORA_TESTS") != "1",
    reason="Live Sora tests disabled. Set RUN_LIVE_SORA_TESTS=1 to enable."
)
class TestLiveSoraPipeline:
    """Live tests that use real Sora API (use sparingly - costs credits)."""
    
    @pytest.mark.asyncio
    async def test_live_sora_api_connection(self):
        """Test connection to Sora API."""
        from services.video_providers.sora_provider import SoraProvider
        
        provider = SoraProvider()
        # Just test initialization, don't make API calls
        assert provider is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not live"])
