"""
Tests for TrendDetectionService.get_trending_for_niche() — the live, on-demand
"what's trending right now in niche X" query. No DB dependency: mocks the
TikTok/Google Trends scans, the Instagram niche-discovery service, and OpenAI.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.trend_detection import TrendDetectionService, CREATOR_NICHE


def _trend(platform: str, identifier: str, description: str = "") -> dict:
    return {
        "source_platform": platform,
        "trend_type": "topic",
        "trend_identifier": identifier,
        "trend_description": description or identifier,
        "volume_raw": 1000,
    }


class TestGetTrendingForNiche:
    async def test_empty_niche_raises(self):
        svc = TrendDetectionService()
        with pytest.raises(ValueError):
            await svc.get_trending_for_niche("   ")

    async def test_keyword_match_path_no_gpt_needed(self):
        svc = TrendDetectionService()
        raw = [
            _trend("tiktok", "#aiautomation", "AI automation is blowing up right now"),
            _trend("google", "unrelated sports topic"),
        ]
        with (
            patch.object(svc, "scan_tiktok_for_niche", AsyncMock(return_value=[raw[0]])),
            patch.object(svc, "scan_google_trends", AsyncMock(return_value=[raw[1]])),
            patch("services.niche_search_service.get_niche_search_service") as mock_get_ig,
        ):
            ig_service = MagicMock()
            ig_service.discover_niche = AsyncMock(return_value=MagicMock(
                related_hashtags=[{"hashtag": "aiautomation", "media_count": 500}],
                top_accounts=[{"username": "aiautomation_hub"}],
            ))
            mock_get_ig.return_value = ig_service

            result = await svc.get_trending_for_niche("AI automation")

        assert result["niche"] == "AI automation"
        identifiers = [t["identifier"] for t in result["trending"]]
        assert "#aiautomation" in identifiers
        assert "unrelated sports topic" not in identifiers  # filtered out, no niche fit
        assert result["instagram_context"]["hashtags"][0]["hashtag"] == "aiautomation"
        assert "generated_at" in result

    async def test_gpt_path_scores_ambiguous_trends(self):
        svc = TrendDetectionService()
        # deliberately no literal "productivity" substring, so this can't take
        # the keyword-match shortcut — it must go through GPT scoring
        ambiguous = _trend("tiktok", "time-blocking apps are having a moment", "a workflow trick going viral")
        with (
            patch.object(svc, "scan_tiktok_for_niche", AsyncMock(return_value=[ambiguous])),
            patch.object(svc, "scan_google_trends", AsyncMock(return_value=[])),
            patch("services.niche_search_service.get_niche_search_service") as mock_get_ig,
            patch("openai.OpenAI") as mock_openai_cls,
        ):
            mock_get_ig.return_value = MagicMock(
                discover_niche=AsyncMock(return_value=MagicMock(related_hashtags=[], top_accounts=[]))
            )
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = (
                '{"scores": [{"index": 0, "relevance": 0.9, "reason": "matches productivity niche"}]}'
            )
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            result = await svc.get_trending_for_niche("productivity")

        assert len(result["trending"]) == 1
        assert result["trending"][0]["niche_fit"] == 0.9

    async def test_instagram_failure_degrades_gracefully(self):
        svc = TrendDetectionService()
        with (
            patch.object(svc, "scan_tiktok_for_niche", AsyncMock(return_value=[
                _trend("tiktok", "#fitness", "fitness trend"),
            ])),
            patch.object(svc, "scan_google_trends", AsyncMock(return_value=[])),
            patch("services.niche_search_service.get_niche_search_service") as mock_get_ig,
        ):
            mock_get_ig.return_value = MagicMock(
                discover_niche=AsyncMock(side_effect=RuntimeError("RapidAPI down"))
            )
            result = await svc.get_trending_for_niche("fitness")

        assert result["instagram_context"] == {"hashtags": [], "accounts": []}
        assert len(result["trending"]) == 1  # TikTok signal still returned

    async def test_ad_hoc_niche_does_not_mutate_creator_niche_global(self):
        svc = TrendDetectionService()
        before = dict(CREATOR_NICHE)
        with (
            patch.object(svc, "scan_tiktok_for_niche", AsyncMock(return_value=[])),
            patch.object(svc, "scan_google_trends", AsyncMock(return_value=[])),
            patch("services.niche_search_service.get_niche_search_service") as mock_get_ig,
        ):
            mock_get_ig.return_value = MagicMock(
                discover_niche=AsyncMock(return_value=MagicMock(related_hashtags=[], top_accounts=[]))
            )
            await svc.get_trending_for_niche("some completely unrelated niche")

        assert CREATOR_NICHE == before  # single-tenant default config untouched


class TestScanTiktokForNiche:
    """scan_tiktok_for_niche() replaced the broken scan_tiktok_trending() call
    inside get_trending_for_niche() — /trending/hashtags 404s on the real API
    even with a valid key, and scan_tiktok_trending()'s fallback is a
    hardcoded single-tenant (dating/relationships) topic list that must never
    leak into an arbitrary caller-supplied niche query.
    """

    async def test_no_key_returns_empty_not_hardcoded_fallback(self):
        svc = TrendDetectionService()
        with patch("services.trend_detection.RAPIDAPI_KEY", ""):
            result = await svc.scan_tiktok_for_niche("fitness")
        assert result == []

    async def test_parses_real_feed_search_response_shape(self):
        svc = TrendDetectionService()
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "code": 0,
            "data": {
                "videos": [
                    {"title": "Decline core challenge for a strong core", "play_count": 51069024},
                    {"title": "", "play_count": 100},  # blank title must be skipped
                ]
            },
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=fake_response)
        with (
            patch("services.trend_detection.RAPIDAPI_KEY", "fake-key"),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await svc.scan_tiktok_for_niche("fitness")

        assert len(result) == 1
        assert result[0]["source_platform"] == "tiktok"
        assert result[0]["trend_type"] == "video"
        assert "core challenge" in result[0]["trend_description"]
        assert result[0]["volume_raw"] == 51069024

    async def test_never_calls_the_broken_trending_hashtags_endpoint(self):
        svc = TrendDetectionService()
        called_urls = []
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"data": {"videos": []}}

        async def fake_get(url, **kwargs):
            called_urls.append(url)
            return fake_response

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = fake_get
        with (
            patch("services.trend_detection.RAPIDAPI_KEY", "fake-key"),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            await svc.scan_tiktok_for_niche("fitness")

        assert called_urls == ["https://tiktok-scraper7.p.rapidapi.com/feed/search"]

    async def test_network_failure_returns_empty_not_hardcoded_fallback(self):
        svc = TrendDetectionService()
        with (
            patch("services.trend_detection.RAPIDAPI_KEY", "fake-key"),
            patch("httpx.AsyncClient", side_effect=RuntimeError("network down")),
        ):
            result = await svc.scan_tiktok_for_niche("fitness")
        assert result == []


class TestFilterByNicheBackwardCompatible:
    async def test_no_niche_arg_still_uses_creator_niche_global(self):
        svc = TrendDetectionService()
        # A trend that only matches CREATOR_NICHE's hardcoded keywords, not any
        # arbitrary topic — proves the default (no `niche=`) path is unchanged.
        trend = _trend("tiktok", "#datingtips", "dating tips for 2026")
        filtered = await svc.filter_by_niche([trend])
        assert filtered[0]["niche_relevance"] == 0.8
