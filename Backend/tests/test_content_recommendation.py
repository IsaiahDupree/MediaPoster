"""
Tests for ContentRecommendationService — fuses live niche trends
(trend_detection.get_trending_for_niche) with historical performance
(content_intelligence.analyze_patterns) into one "what to post next" answer.
"""
from unittest.mock import AsyncMock, MagicMock, patch

from services.content_recommendation import ContentRecommendationService


def _trending(niche="AI automation"):
    return {
        "niche": niche,
        "trending": [
            {"identifier": "#localllm", "platform": "tiktok", "type": "topic",
             "description": "running LLMs locally is having a moment", "score": 0.82, "niche_fit": 0.9},
        ],
        "instagram_context": {"hashtags": [], "accounts": []},
        "generated_at": "2026-07-31T00:00:00+00:00",
    }


def _patterns():
    return {
        "lookback_days": 90,
        "total_posts_analyzed": 12,
        "top_topics": [{"name": "ai_automation_tips", "avg_engagement": 500, "total_views": 5000, "post_count": 6}],
        "top_hooks": [{"name": "bold_claim", "avg_engagement": 480, "total_views": 4000, "post_count": 5}],
        "top_tones": [{"name": "provocative", "avg_engagement": 460, "total_views": 3900, "post_count": 5}],
    }


class TestRecommendNextContent:
    async def test_fuses_trend_and_history_via_gpt(self):
        svc = ContentRecommendationService()
        gpt_json = (
            '{"topic": "Run an LLM locally on a 4070", "angle": "no cloud costs", '
            '"format": "talking-head tutorial", "platform": "tiktok", "hook": "Nobody tells you this", '
            '"reasoning": "matches trending local-LLM topic AND this account\'s top historical topic", '
            '"cites_trend": true, "cites_history": true, "confidence": 0.85}'
        )
        with (
            patch.object(svc.trends, "get_trending_for_niche", AsyncMock(return_value=_trending())),
            patch.object(svc.intel, "analyze_patterns", AsyncMock(return_value=_patterns())),
            patch("openai.OpenAI") as mock_openai_cls,
        ):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = gpt_json
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            result = await svc.recommend_next_content(
                niche="AI automation",
                brand_voice={"tone": "direct", "keywords": ["no-fluff"]},
                target_audience="indie developers",
                available_minutes=20,
            )

        assert result["recommendation"]["cites_trend"] is True
        assert result["recommendation"]["cites_history"] is True
        assert result["sources"]["trend_count"] == 1
        assert result["sources"]["historical_post_count"] == 12

    async def test_no_niche_degrades_to_history_only(self):
        svc = ContentRecommendationService()
        with (
            patch.object(svc.trends, "get_trending_for_niche", AsyncMock()) as mock_trend_call,
            patch.object(svc.intel, "analyze_patterns", AsyncMock(return_value=_patterns())),
            patch("openai.OpenAI", side_effect=Exception("no key configured")),
        ):
            result = await svc.recommend_next_content(niche=None)

        mock_trend_call.assert_not_called()
        # GPT unavailable -> deterministic fallback, but history data exists
        assert result["recommendation"]["cites_history"] is True
        assert result["recommendation"]["cites_trend"] is False
        assert result["recommendation"]["topic"] == "ai_automation_tips"

    async def test_no_data_at_all_returns_plain_no_data_response(self):
        svc = ContentRecommendationService()
        empty_patterns = {"lookback_days": 0, "total_posts_analyzed": 0, "top_topics": [], "top_hooks": [], "top_tones": []}
        with (
            patch.object(svc.intel, "analyze_patterns", AsyncMock(return_value=empty_patterns)),
        ):
            result = await svc.recommend_next_content(niche=None)

        assert result["recommendation"] is None
        assert "No trend data and no historical" in result["reasoning"]

    async def test_trend_lookup_failure_degrades_to_history_only(self):
        svc = ContentRecommendationService()
        with (
            patch.object(svc.trends, "get_trending_for_niche", AsyncMock(side_effect=RuntimeError("RapidAPI down"))),
            patch.object(svc.intel, "analyze_patterns", AsyncMock(return_value=_patterns())),
            patch("openai.OpenAI", side_effect=Exception("no key configured")),
        ):
            result = await svc.recommend_next_content(niche="AI automation")

        assert result["recommendation"]["cites_trend"] is False
        assert result["recommendation"]["cites_history"] is True

    async def test_historical_analysis_error_key_is_treated_as_no_history(self):
        svc = ContentRecommendationService()
        with (
            patch.object(svc.trends, "get_trending_for_niche", AsyncMock(return_value=_trending())),
            patch.object(svc.intel, "analyze_patterns", AsyncMock(return_value={"error": "no DB connection"})),
            patch("openai.OpenAI", side_effect=Exception("no key configured")),
        ):
            result = await svc.recommend_next_content(niche="AI automation")

        assert result["sources"]["historical_post_count"] == 0
        assert result["recommendation"]["cites_trend"] is True
        assert result["recommendation"]["cites_history"] is False
