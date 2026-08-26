"""
Unit Tests for Script Generator Service (MF-002)
=================================================
Tests script generation from content briefs.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import json

from services.media_factory.script_generator import ScriptGeneratorService
from services.media_factory.contracts.content_brief import (
    ContentBriefSchema,
    BriefAngleSchema,
    BriefScoreSchema
)
from services.media_factory.contracts.script import ScriptSchema, ScriptBeatSchema
from services.media_factory.contracts.cluster import ClusterSchema


@pytest.fixture
def sample_brief():
    """Create a sample content brief."""
    return ContentBriefSchema(
        brief_id="brief_test_001",
        status="scored",
        title="The 5-Minute Productivity Hack",
        hook="Stop doing this (here's the framework that works)",
        promise="Learn a productivity framework that actually works",
        unique_lens="Engineering-style scoring approach",
        format="shorts",
        length_sec=45,
        hook_sec=1.2,
        pattern_interrupt_sec=4.0,
        score=BriefScoreSchema(
            total=78.5,
            velocity=20.0,
            intent=18.0,
            product_fit=22.0,
            differentiation=12.0,
            production_feasibility=6.5
        ),
        worth_covering=True,
        angle=BriefAngleSchema(
            angle_id="angle_001",
            audience_role="creator",
            intent="learn",
            stakes="time",
            format="tutorial",
            promise="Save 2 hours daily",
            unique_lens="Engineering mindset",
            convergence_pattern="Problem × Tool"
        )
    )


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "title": "The 5-Minute Productivity Hack",
        "hook": "Stop doing this (here's the framework that works)",
        "segments": [
            {
                "id": "seg_001",
                "t": "0-2",
                "text": "Stop doing this here's the framework that works",
                "intent": "hook",
                "on_screen": ["Stop", "Framework"],
                "visual_style": "big_text_punch_in",
                "emphasis_words": ["stop", "framework", "works"]
            },
            {
                "id": "seg_002",
                "t": "2-12",
                "text": "Most people approach productivity without considering time constraints and energy levels",
                "intent": "problem",
                "on_screen": ["Problem", "Time"],
                "visual_style": "diagram",
                "emphasis_words": ["most", "without", "time"]
            },
            {
                "id": "seg_003",
                "t": "12-30",
                "text": "Here's the solution use a simple three step framework first identify your peak hours second batch similar tasks third eliminate unnecessary meetings",
                "intent": "solution",
                "on_screen": ["Solution", "3 Steps"],
                "visual_style": "b_roll",
                "emphasis_words": ["solution", "three", "framework"]
            },
            {
                "id": "seg_004",
                "t": "30-40",
                "text": "I used this with over 100 clients and they saved an average of 2 hours per day",
                "intent": "proof",
                "on_screen": ["100+ Clients", "2h Saved"],
                "visual_style": "text_overlay",
                "emphasis_words": ["100", "saved", "2 hours"]
            },
            {
                "id": "seg_005",
                "t": "40-45",
                "text": "Try this framework today and let me know your results",
                "intent": "cta",
                "on_screen": ["Try Today"],
                "visual_style": "big_text_punch_in",
                "emphasis_words": ["try", "today", "results"]
            }
        ],
        "metadata": {
            "word_count": 85,
            "format": "shorts"
        }
    }


class TestScriptGeneration:
    """Test script generation from briefs."""

    @pytest.mark.asyncio
    async def test_generate_script_success(self, sample_brief, mock_openai_response):
        """Test successful script generation."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_response)

        with patch("services.media_factory.script_generator.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            generator = ScriptGeneratorService()
            generator.client = mock_client

            script = await generator.generate_script(sample_brief)

            # Verify script structure
            assert script.brief_id == sample_brief.brief_id
            assert script.title == "The 5-Minute Productivity Hack"
            assert script.hook == "Stop doing this (here's the framework that works)"
            assert len(script.segments) == 5

            # Verify first segment
            first_seg = script.segments[0]
            assert first_seg.id == "seg_001"
            assert first_seg.intent == "hook"
            assert "stop" in [w.lower() for w in first_seg.emphasis_words]

            # Verify timing was calculated
            assert "total_duration_sec" in script.metadata

    @pytest.mark.asyncio
    async def test_generate_script_with_timing(self, sample_brief, mock_openai_response):
        """Test script generation calculates timing correctly."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_response)

        with patch("services.media_factory.script_generator.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            generator = ScriptGeneratorService()
            generator.client = mock_client

            script = await generator.generate_script(sample_brief, words_per_second=2.5)

            # Verify timing metadata
            assert "total_duration_sec" in script.metadata
            assert "word_count" in script.metadata
            assert "estimated_tts_duration" in script.metadata

            # Verify segments have timing
            for segment in script.segments:
                assert "-" in segment.t
                start, end = segment.t.split("-")
                assert float(start) < float(end)

    @pytest.mark.asyncio
    async def test_generate_script_api_error(self, sample_brief):
        """Test script generation handles API errors gracefully."""
        with patch("services.media_factory.script_generator.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
            mock_openai.return_value = mock_client

            generator = ScriptGeneratorService()
            generator.client = mock_client

            with pytest.raises(ValueError, match="Script generation failed"):
                await generator.generate_script(sample_brief)

    @pytest.mark.asyncio
    async def test_generate_script_invalid_json(self, sample_brief):
        """Test script generation handles invalid JSON response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Invalid JSON"

        with patch("services.media_factory.script_generator.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            generator = ScriptGeneratorService()
            generator.client = mock_client

            with pytest.raises(ValueError, match="Invalid JSON response"):
                await generator.generate_script(sample_brief)

    def test_prompt_uses_current_cluster_contract(self, sample_brief):
        """Trend context must use fields that ClusterSchema actually exposes."""
        sample_brief.cluster = ClusterSchema(
            cluster_id="cluster_control_plane",
            name="AI agent control planes",
            what_changed="More agents can act on customer-facing tools.",
            why_people_care="Founders need to bound and stop consequential actions.",
            what_debate="How much autonomy to grant before human approval.",
        )

        generator = ScriptGeneratorService()
        prompt = generator._build_script_prompt(sample_brief)

        assert "What Changed: More agents can act on customer-facing tools." in prompt
        assert "Why People Care: Founders need to bound and stop consequential actions." in prompt
        assert "Debate: How much autonomy to grant before human approval." in prompt


class TestSegmentRegeneration:
    """Test segment regeneration functionality."""

    @pytest.mark.asyncio
    async def test_regenerate_segment_success(self, sample_brief, mock_openai_response):
        """Test successful segment regeneration."""
        # First generate a script
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_response)

        new_segment_data = {
            "id": "seg_001",
            "t": "0-2",
            "text": "Here's why most productivity advice fails",
            "intent": "hook",
            "on_screen": ["Why", "Fails"],
            "visual_style": "big_text_punch_in",
            "emphasis_words": ["why", "fails"]
        }

        with patch("services.media_factory.script_generator.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()

            # First call for generate_script
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            generator = ScriptGeneratorService()
            generator.client = mock_client

            script = await generator.generate_script(sample_brief)

            # Second call for regenerate_segment
            regen_response = MagicMock()
            regen_response.choices = [MagicMock()]
            regen_response.choices[0].message.content = json.dumps(new_segment_data)
            mock_client.chat.completions.create = AsyncMock(return_value=regen_response)

            new_segment = await generator.regenerate_segment(
                script,
                "seg_001",
                "Make it more engaging"
            )

            assert new_segment.id == "seg_001"
            assert "fails" in [w.lower() for w in new_segment.emphasis_words]

    @pytest.mark.asyncio
    async def test_regenerate_nonexistent_segment(self, sample_brief, mock_openai_response):
        """Test regenerating a non-existent segment raises error."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_openai_response)

        with patch("services.media_factory.script_generator.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            generator = ScriptGeneratorService()
            generator.client = mock_client

            script = await generator.generate_script(sample_brief)

            with pytest.raises(ValueError, match="Segment not found"):
                await generator.regenerate_segment(
                    script,
                    "seg_999",
                    "Make it better"
                )


class TestTimingCalculation:
    """Test timing calculation logic."""

    def test_calculate_timing_basic(self):
        """Test basic timing calculation."""
        generator = ScriptGeneratorService()

        script_data = {
            "title": "Test",
            "hook": "Test hook",
            "segments": [
                {
                    "id": "seg_001",
                    "text": "This is a ten word test segment for timing",
                    "intent": "hook",
                    "on_screen": [],
                    "emphasis_words": []
                },
                {
                    "id": "seg_002",
                    "text": "This is another test segment with twenty words to verify the timing calculation works correctly for longer segments",
                    "intent": "problem",
                    "on_screen": [],
                    "emphasis_words": []
                }
            ]
        }

        result = generator._calculate_timing(script_data, words_per_second=2.5)

        # Verify timing added
        assert "t" in result["segments"][0]
        assert "t" in result["segments"][1]

        # Verify metadata
        assert "total_duration_sec" in result["metadata"]
        assert "word_count" in result["metadata"]
        assert result["metadata"]["word_count"] == 27  # Actual word count


class TestSingletonInstance:
    """Test singleton pattern."""

    def test_get_instance_returns_singleton(self):
        """Test get_instance returns the same instance."""
        instance1 = ScriptGeneratorService.get_instance()
        instance2 = ScriptGeneratorService.get_instance()

        assert instance1 is instance2
