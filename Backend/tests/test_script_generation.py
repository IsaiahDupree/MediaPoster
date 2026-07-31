"""
Tests for ScriptGenerationService — expands a topic into a full production
packet via GPT. Deliberately no deterministic fallback: unavailable AI must
raise ScriptGenerationUnavailable, never return a fabricated script.
"""
import pytest
from unittest.mock import MagicMock, patch

from services.script_generation import ScriptGenerationService, ScriptGenerationUnavailable


def _script_json():
    return (
        '{"hook": "Nobody tells you this about local LLMs", '
        '"context": "Running models locally saves real money.", '
        '"main_points": ["setup", "hardware", "gotchas"], '
        '"proof_or_demo": "live token generation on a 4070", '
        '"cta": "follow for part 2", '
        '"full_spoken_script": "Nobody tells you this about local LLMs...", '
        '"visual_plan": {"opening_visual": "GPU screen recording", '
        '"shots": [{"timestamp": "0:00-0:05", "narration": "hook", "visual": "face cam", "on_screen_text": null}], '
        '"b_roll": ["fan spinning up"]}, '
        '"estimated_recording_minutes": 8, "estimated_editing_minutes": 4}'
    )


class TestGenerateScript:
    async def test_empty_topic_raises_value_error(self):
        svc = ScriptGenerationService()
        with pytest.raises(ValueError):
            await svc.generate_script("   ")

    async def test_real_gpt_call_returns_parsed_script(self):
        svc = ScriptGenerationService()
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = _script_json()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            result = await svc.generate_script(
                topic="Run an LLM locally on a 4070",
                angle="no cloud costs",
                content_format="talking-head tutorial",
                platform="tiktok",
                hook="Nobody tells you this",
                reasoning="matches a trending topic",
                brand_voice={"tone": "direct"},
                target_audience="indie developers",
                available_minutes=15,
            )

        assert result["hook"] == "Nobody tells you this about local LLMs"
        assert result["main_points"] == ["setup", "hardware", "gotchas"]
        assert result["visual_plan"]["opening_visual"] == "GPU screen recording"
        assert result["estimated_recording_minutes"] == 8

    async def test_context_lines_include_all_provided_fields(self):
        svc = ScriptGenerationService()
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = _script_json()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            await svc.generate_script(
                topic="Run an LLM locally",
                angle="no cloud costs",
                platform="tiktok",
                reasoning="matches a trending topic",
            )

            sent = mock_client.chat.completions.create.call_args.kwargs["messages"]
            user_content = sent[1]["content"]
            assert "Topic: Run an LLM locally" in user_content
            assert "Angle: no cloud costs" in user_content
            assert "Platform: tiktok" in user_content
            assert "Why this topic was recommended: matches a trending topic" in user_content

    async def test_available_minutes_scales_the_prompt_instruction(self):
        svc = ScriptGenerationService()
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = _script_json()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            await svc.generate_script(topic="fitness tip", available_minutes=5)

            sent = mock_client.chat.completions.create.call_args.kwargs["messages"]
            system_prompt = sent[0]["content"]
            assert "5 minutes" in system_prompt

    async def test_no_ai_provider_raises_unavailable_not_fabricated_script(self):
        svc = ScriptGenerationService()
        with patch("openai.OpenAI", side_effect=Exception("no key configured")):
            with pytest.raises(ScriptGenerationUnavailable):
                await svc.generate_script(topic="fitness tip")

    async def test_malformed_gpt_response_raises_unavailable(self):
        svc = ScriptGenerationService()
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "not valid json"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            with pytest.raises(ScriptGenerationUnavailable):
                await svc.generate_script(topic="fitness tip")
