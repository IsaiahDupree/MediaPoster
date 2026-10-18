"""
Unit Tests for Sora Pipeline (ARCH-002)
========================================
Tests the SoraPipeline multi-part generation, stitching, and analysis.

Tests cover:
- ARCH-002: Multi-part video generation coordination
- Prompt generation (AI and fallback)
- Stitching integration
- Content analysis integration
- Batch generation
- Error handling and graceful fallbacks
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path


class TestSoraPipelineInit:
    """Test SoraPipeline initialization."""

    def test_import_and_init(self):
        """Test SoraPipeline can be imported and instantiated."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()
        assert pipeline is not None

    def test_creates_output_directories(self, tmp_path):
        """Test output directories are created on init."""
        with patch("automation.sora.pipeline.SORA_OUTPUT_DIR", tmp_path / "output"), \
             patch("automation.sora.pipeline.SORA_PROCESSED_DIR", tmp_path / "processed"):
            from automation.sora.pipeline import SoraPipeline

            pipeline = SoraPipeline()
            assert (tmp_path / "output").exists()
            assert (tmp_path / "processed").exists()

    def test_lazy_loads_stitcher(self):
        """Test stitcher is lazily loaded."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()
        assert pipeline._stitcher is None

        # Accessing property triggers lazy load
        with patch("services.ai_video_pipeline.stitcher.VideoStitcher") as MockStitcher:
            MockStitcher.return_value = Mock()
            stitcher = pipeline.stitcher
            assert stitcher is not None

    def test_lazy_loads_analyzer(self):
        """Test analyzer is lazily loaded."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()
        assert pipeline._analyzer is None


class TestPromptGeneration:
    """Test ARCH-002 prompt generation."""

    def test_fallback_prompts(self):
        """Test fallback prompt generation without AI."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()
        prompts = pipeline._fallback_prompts("AI automation", 3, "@isaiahdupree")

        assert len(prompts) == 3
        assert all("AI automation" in p for p in prompts)
        assert all("@isaiahdupree" in p for p in prompts)
        assert "Opening hook" in prompts[0]
        assert "Development" in prompts[1]
        assert "resolution" in prompts[2].lower()

    def test_fallback_prompts_no_character(self):
        """Test fallback prompts without character."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()
        prompts = pipeline._fallback_prompts("test theme", 2, None)

        assert len(prompts) == 2
        assert all("test theme" in p for p in prompts)
        assert all("@" not in p for p in prompts)

    def test_fallback_prompts_various_counts(self):
        """Test fallback prompts for different part counts."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        for count in [1, 2, 3, 4, 5]:
            prompts = pipeline._fallback_prompts("theme", count, None)
            assert len(prompts) == count

    @pytest.mark.asyncio
    async def test_generate_prompts_ai_success(self):
        """Test AI prompt generation with mocked OpenAI."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"prompts": ["prompt 1", "prompt 2", "prompt 3"]}'))
        ]

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response

        # OpenAI is imported inside the method, so patch the openai module
        with patch.dict("sys.modules", {"openai": Mock(OpenAI=Mock(return_value=mock_client))}):
            prompts = await pipeline._generate_part_prompts("test theme", 3, "@char")

            assert len(prompts) == 3
            assert prompts[0] == "prompt 1"
            assert prompts[1] == "prompt 2"
            assert prompts[2] == "prompt 3"

    @pytest.mark.asyncio
    async def test_generate_prompts_ai_failure_falls_back(self):
        """Test prompt generation falls back on AI failure."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        # Make openai import raise an exception
        with patch.dict("sys.modules", {"openai": Mock(OpenAI=Mock(side_effect=Exception("API error")))}):
            prompts = await pipeline._generate_part_prompts("test theme", 3, None)

            # Should fall back to non-AI prompts
            assert len(prompts) == 3
            assert all("test theme" in p for p in prompts)

    @pytest.mark.asyncio
    async def test_generate_prompts_public_api(self):
        """Test the public generate_prompts() method."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        with patch.object(pipeline, "_generate_part_prompts", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = ["p1", "p2", "p3"]

            result = await pipeline.generate_prompts("theme", 3, "@char")

            assert result == ["p1", "p2", "p3"]
            mock_gen.assert_called_once_with("theme", 3, "@char")


class TestMultiPartGeneration:
    """Test ARCH-002 multi-part generation coordination."""

    @pytest.mark.asyncio
    async def test_generate_multi_part_basic(self):
        """Test basic multi-part generation flow."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        # Mock all internal methods
        with patch.object(pipeline, "_generate_part_prompts", new_callable=AsyncMock) as mock_prompts, \
             patch.object(pipeline, "_generate_single_part", new_callable=AsyncMock) as mock_gen, \
             patch.object(pipeline, "_stitch_parts", new_callable=AsyncMock) as mock_stitch, \
             patch.object(pipeline, "_analyze_content", new_callable=AsyncMock) as mock_analyze:

            mock_prompts.return_value = ["prompt1", "prompt2", "prompt3"]
            mock_gen.side_effect = [
                {"part_num": 1, "status": "completed", "video_path": "/tmp/p1.mp4", "prompt": "prompt1"},
                {"part_num": 2, "status": "completed", "video_path": "/tmp/p2.mp4", "prompt": "prompt2"},
                {"part_num": 3, "status": "completed", "video_path": "/tmp/p3.mp4", "prompt": "prompt3"},
            ]
            mock_stitch.return_value = "/tmp/stitched.mp4"
            mock_analyze.return_value = {
                "detected_hook": "Amazing AI",
                "viral_score": 85,
                "hashtags": ["ai", "viral"],
            }

            result = await pipeline.generate_multi_part(
                theme="AI automation",
                num_parts=3,
                character="@isaiahdupree",
            )

            assert result["status"] == "completed"
            assert result["successful_parts"] == 3
            assert result["failed_parts"] == 0
            assert result["stitched_video"] == "/tmp/stitched.mp4"
            assert result["analysis"]["viral_score"] == 85
            assert len(result["parts"]) == 3
            assert len(result["prompts"]) == 3

    @pytest.mark.asyncio
    async def test_generate_multi_part_with_custom_prompts(self):
        """Test multi-part generation with pre-provided prompts."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        with patch.object(pipeline, "_generate_part_prompts", new_callable=AsyncMock) as mock_prompts, \
             patch.object(pipeline, "_generate_single_part", new_callable=AsyncMock) as mock_gen, \
             patch.object(pipeline, "_stitch_parts", new_callable=AsyncMock) as mock_stitch, \
             patch.object(pipeline, "_analyze_content", new_callable=AsyncMock) as mock_analyze:

            mock_gen.side_effect = [
                {"part_num": 1, "status": "completed", "video_path": "/tmp/p1.mp4", "prompt": "custom1"},
                {"part_num": 2, "status": "completed", "video_path": "/tmp/p2.mp4", "prompt": "custom2"},
            ]
            mock_stitch.return_value = "/tmp/stitched.mp4"
            mock_analyze.return_value = {"viral_score": 70}

            result = await pipeline.generate_multi_part(
                theme="test",
                num_parts=2,
                part_prompts=["custom1", "custom2"],
            )

            # Should NOT call _generate_part_prompts since custom prompts provided
            mock_prompts.assert_not_called()
            assert result["prompts"] == ["custom1", "custom2"]

    @pytest.mark.asyncio
    async def test_generate_multi_part_partial_failure(self):
        """Test handling when some parts fail."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        with patch.object(pipeline, "_generate_part_prompts", new_callable=AsyncMock) as mock_prompts, \
             patch.object(pipeline, "_generate_single_part", new_callable=AsyncMock) as mock_gen, \
             patch.object(pipeline, "_stitch_parts", new_callable=AsyncMock) as mock_stitch, \
             patch.object(pipeline, "_analyze_content", new_callable=AsyncMock) as mock_analyze:

            mock_prompts.return_value = ["p1", "p2", "p3"]
            mock_gen.side_effect = [
                {"part_num": 1, "status": "completed", "video_path": "/tmp/p1.mp4", "prompt": "p1"},
                {"part_num": 2, "status": "failed", "video_path": None, "error": "timeout", "prompt": "p2"},
                {"part_num": 3, "status": "completed", "video_path": "/tmp/p3.mp4", "prompt": "p3"},
            ]
            mock_stitch.return_value = "/tmp/stitched.mp4"
            mock_analyze.return_value = {"viral_score": 60}

            result = await pipeline.generate_multi_part(theme="test", num_parts=3)

            assert result["status"] == "completed"  # Still succeeds with partial results
            assert result["successful_parts"] == 2
            assert result["failed_parts"] == 1

            # Stitch should only include successful parts
            mock_stitch.assert_called_once()
            call_args = mock_stitch.call_args[0]
            assert len(call_args[0]) == 2  # Only 2 clip paths

    @pytest.mark.asyncio
    async def test_generate_multi_part_all_fail(self):
        """Test handling when all parts fail."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        with patch.object(pipeline, "_generate_part_prompts", new_callable=AsyncMock) as mock_prompts, \
             patch.object(pipeline, "_generate_single_part", new_callable=AsyncMock) as mock_gen:

            mock_prompts.return_value = ["p1", "p2"]
            mock_gen.side_effect = [
                {"part_num": 1, "status": "failed", "video_path": None, "error": "err1", "prompt": "p1"},
                {"part_num": 2, "status": "failed", "video_path": None, "error": "err2", "prompt": "p2"},
            ]

            result = await pipeline.generate_multi_part(theme="test", num_parts=2)

            assert result["status"] == "failed"
            assert result["successful_parts"] == 0
            assert result["failed_parts"] == 2
            assert result["stitched_video"] is None
            assert result["analysis"] is None

    @pytest.mark.asyncio
    async def test_generate_multi_part_single_part_no_stitch(self):
        """Test single part skips stitching."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        with patch.object(pipeline, "_generate_part_prompts", new_callable=AsyncMock) as mock_prompts, \
             patch.object(pipeline, "_generate_single_part", new_callable=AsyncMock) as mock_gen, \
             patch.object(pipeline, "_stitch_parts", new_callable=AsyncMock) as mock_stitch, \
             patch.object(pipeline, "_analyze_content", new_callable=AsyncMock) as mock_analyze:

            mock_prompts.return_value = ["p1"]
            mock_gen.return_value = {
                "part_num": 1, "status": "completed", "video_path": "/tmp/p1.mp4", "prompt": "p1"
            }
            mock_analyze.return_value = {"viral_score": 75}

            result = await pipeline.generate_multi_part(theme="test", num_parts=1)

            # Single clip -> no stitching needed, just use the clip directly
            mock_stitch.assert_not_called()
            assert result["stitched_video"] == "/tmp/p1.mp4"

    @pytest.mark.asyncio
    async def test_generate_multi_part_returns_timing(self):
        """Test total_generation_time is populated."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        with patch.object(pipeline, "_generate_part_prompts", new_callable=AsyncMock) as mock_prompts, \
             patch.object(pipeline, "_generate_single_part", new_callable=AsyncMock) as mock_gen, \
             patch.object(pipeline, "_stitch_parts", new_callable=AsyncMock) as mock_stitch, \
             patch.object(pipeline, "_analyze_content", new_callable=AsyncMock) as mock_analyze:

            mock_prompts.return_value = ["p1"]
            mock_gen.return_value = {
                "part_num": 1, "status": "completed", "video_path": "/tmp/p1.mp4", "prompt": "p1"
            }
            mock_analyze.return_value = {}

            result = await pipeline.generate_multi_part(theme="test", num_parts=1)

            assert "total_generation_time" in result
            assert isinstance(result["total_generation_time"], float)
            assert result["total_generation_time"] >= 0


class TestBatchGeneration:
    """Test batch generation (legacy mode)."""

    @pytest.mark.asyncio
    async def test_generate_batch_basic(self):
        """Test basic batch generation."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        with patch.object(pipeline, "_generate_single_part", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = [
                {"part_num": 1, "status": "completed", "video_path": "/tmp/v1.mp4", "prompt": "a"},
                {"part_num": 2, "status": "completed", "video_path": "/tmp/v2.mp4", "prompt": "b"},
            ]

            result = await pipeline.generate_batch(
                prompts=[{"prompt": "a"}, {"prompt": "b"}],
            )

            assert result["status"] == "completed"
            assert result["completed"] == 2
            assert result["failed"] == 0
            assert result["total_prompts"] == 2
            assert len(result["jobs"]) == 2

    @pytest.mark.asyncio
    async def test_generate_batch_with_stitch(self):
        """Test batch generation with stitching requested."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        with patch.object(pipeline, "_generate_single_part", new_callable=AsyncMock) as mock_gen, \
             patch.object(pipeline, "_stitch_parts", new_callable=AsyncMock) as mock_stitch:

            mock_gen.side_effect = [
                {"part_num": 1, "status": "completed", "video_path": "/tmp/v1.mp4", "prompt": "a"},
                {"part_num": 2, "status": "completed", "video_path": "/tmp/v2.mp4", "prompt": "b"},
            ]
            mock_stitch.return_value = "/tmp/batch_stitched.mp4"

            result = await pipeline.generate_batch(
                prompts=[{"prompt": "a"}, {"prompt": "b"}],
                stitch_output=True,
            )

            assert result["stitched_video"] == "/tmp/batch_stitched.mp4"
            mock_stitch.assert_called_once()


class TestContentAnalysisIntegration:
    """Test ARCH-003 content analysis integration."""

    @pytest.mark.asyncio
    async def test_analyze_content_uses_prompts_as_transcript(self):
        """Test content analysis uses prompts as pseudo-transcript."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        mock_analyzer = Mock()
        mock_analyzer.analyze_transcript.return_value = {
            "detected_hook": "Test hook",
            "viral_score": 80,
            "pre_social_score": 80,
            "hashtags": ["test"],
        }
        pipeline._analyzer = mock_analyzer

        result = await pipeline._analyze_content(
            "/tmp/video.mp4", "test theme", ["prompt1", "prompt2"]
        )

        assert result is not None
        assert result["viral_score"] == 80
        mock_analyzer.analyze_transcript.assert_called_once()

        # Verify the pseudo-transcript includes theme and prompts
        call_args = mock_analyzer.analyze_transcript.call_args
        transcript = call_args[1]["transcript"] if "transcript" in call_args[1] else call_args[0][0]
        assert "test theme" in transcript
        assert "prompt1" in transcript
        assert "prompt2" in transcript

    @pytest.mark.asyncio
    async def test_analyze_content_failure_returns_fallback(self):
        """Test content analysis failure returns fallback result."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        mock_analyzer = Mock()
        mock_analyzer.analyze_transcript.side_effect = Exception("AI error")
        pipeline._analyzer = mock_analyzer

        result = await pipeline._analyze_content(
            "/tmp/video.mp4", "test theme", ["p1"]
        )

        # Should return fallback, not raise
        assert result is not None
        assert result["detected_hook"] == "test theme"
        assert "error" in result


class TestStitchingIntegration:
    """Test video stitching integration."""

    @pytest.mark.asyncio
    async def test_stitch_parts_calls_stitcher(self, tmp_path):
        """Test stitching delegates to VideoStitcher."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        # Create fake output file so Path.exists() check passes
        output_file = tmp_path / "job-123_stitched.mp4"
        output_file.write_text("fake video data")

        mock_stitcher_instance = Mock()
        mock_stitcher_instance.stitch_full_video.return_value = str(output_file)

        with patch("services.ai_video_pipeline.stitcher.VideoStitcher", return_value=mock_stitcher_instance), \
             patch("automation.sora.pipeline.SORA_PROCESSED_DIR", tmp_path):

            result = await pipeline._stitch_parts(
                ["/tmp/p1.mp4", "/tmp/p2.mp4"], "job-123", "test"
            )

            assert result == str(output_file)
            mock_stitcher_instance.stitch_full_video.assert_called_once()

    @pytest.mark.asyncio
    async def test_stitch_single_clip_returns_directly(self):
        """Test stitching with single clip returns it directly."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        result = await pipeline._stitch_parts(
            ["/tmp/p1.mp4"], "job-123", "test"
        )

        assert result == "/tmp/p1.mp4"

    @pytest.mark.asyncio
    async def test_stitch_empty_list_returns_none(self):
        """Test stitching with no clips returns None."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        result = await pipeline._stitch_parts([], "job-123", "test")

        assert result is None


class TestSinglePartGeneration:
    """Test individual part generation."""

    @pytest.mark.asyncio
    async def test_generation_with_no_automation(self):
        """Test single part returns pending_manual when no automation available."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        with patch.object(pipeline, "_sora_generate", new_callable=AsyncMock) as mock_sora:
            mock_sora.return_value = None

            result = await pipeline._generate_single_part(
                prompt="test prompt",
                part_num=1,
                job_id="test-job",
            )

            assert result["status"] == "pending_manual"
            assert result["part_num"] == 1
            assert result["prompt"] == "test prompt"

    @pytest.mark.asyncio
    async def test_generation_exception_returns_failed(self):
        """Test single part returns failed on exception."""
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        with patch.object(pipeline, "_sora_generate", new_callable=AsyncMock) as mock_sora:
            mock_sora.side_effect = Exception("Safari crashed")

            result = await pipeline._generate_single_part(
                prompt="test prompt",
                part_num=2,
                job_id="test-job",
            )

            assert result["status"] == "failed"
            assert "Safari crashed" in result["error"]
            assert result["part_num"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
