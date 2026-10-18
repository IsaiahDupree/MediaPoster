"""
Unit tests for CrossPipelineLearningService.
Tests record, retrieve, and prompt-injection logic with mocked DB + OpenAI.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_session(fetchone_result=None, fetchall_result=None):
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.fetchone = MagicMock(return_value=fetchone_result)
    execute_result.fetchall = MagicMock(return_value=fetchall_result or [])
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()
    return session


SAMPLE_FATE = {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9}


# ── get_learnings_context ─────────────────────────────────────────────────────

class TestGetLearningsContext:
    @pytest.mark.asyncio
    async def test_returns_no_results_message_when_empty(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService

        session = _make_session(fetchone_result=None)
        service = CrossPipelineLearningService(session)

        result = await service.get_learnings_context()
        assert "No pipeline" in result["context"]
        assert result["generated_at"] is None

    @pytest.mark.asyncio
    async def test_returns_stored_context_blob(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService

        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc)

        row = MagicMock()
        row.context_blob = "• AI automation posts drove 7.2% CTR\n• Awareness level 2 performs best on TikTok"
        row.generated_at = ts

        session = _make_session(fetchone_result=row)
        service = CrossPipelineLearningService(session)

        result = await service.get_learnings_context()
        assert "7.2% CTR" in result["context"]
        assert result["generated_at"] is not None

    @pytest.mark.asyncio
    async def test_generated_at_is_iso_string(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService
        from datetime import datetime, timezone

        row = MagicMock()
        row.context_blob = "some learnings"
        row.generated_at = datetime(2026, 3, 5, 10, 0, 0, tzinfo=timezone.utc)

        session = _make_session(fetchone_result=row)
        service = CrossPipelineLearningService(session)

        result = await service.get_learnings_context()
        # Should be parseable ISO string
        datetime.fromisoformat(result["generated_at"])


# ── get_prompt_injection ──────────────────────────────────────────────────────

class TestGetPromptInjection:
    @pytest.mark.asyncio
    async def test_returns_empty_string_when_no_learnings(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService

        session = _make_session(fetchone_result=None)
        service = CrossPipelineLearningService(session)

        result = await service.get_prompt_injection()
        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_injection_block_with_learnings(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService
        from datetime import datetime, timezone

        row = MagicMock()
        row.context_blob = "• AI content performs best on TikTok"
        row.generated_at = datetime.now(timezone.utc)

        session = _make_session(fetchone_result=row)
        service = CrossPipelineLearningService(session)

        result = await service.get_prompt_injection()
        assert "CROSS-PIPELINE LEARNINGS" in result
        assert "AI content performs best" in result
        assert result.startswith("\n\n[")

    @pytest.mark.asyncio
    async def test_empty_when_context_is_no_pipeline_message(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService
        from datetime import datetime, timezone

        row = MagicMock()
        row.context_blob = "No pipeline results yet"
        row.generated_at = datetime.now(timezone.utc)

        session = _make_session(fetchone_result=row)
        service = CrossPipelineLearningService(session)

        result = await service.get_prompt_injection()
        assert result == ""


# ── record_pipeline_result ────────────────────────────────────────────────────

class TestRecordPipelineResult:
    @pytest.mark.asyncio
    async def test_record_inserts_and_commits(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService

        session = _make_session(fetchall_result=[])
        service = CrossPipelineLearningService(session)

        with patch.object(service, "_regenerate_learnings", new=AsyncMock()):
            row_id = await service.record_pipeline_result(
                pipeline_id="pipe-1",
                theme="AI saves time",
                fate_scores=SAMPLE_FATE,
                awareness_level=2,
                platform="tiktok",
                published_count=5,
                engagement_at_24h=1250.0,
            )

        assert isinstance(row_id, str)
        assert len(row_id) == 36  # UUID length
        session.execute.assert_called()
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_record_triggers_regeneration(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService

        session = _make_session(fetchall_result=[])
        service = CrossPipelineLearningService(session)

        regenerate_called = False

        async def mock_regenerate():
            nonlocal regenerate_called
            regenerate_called = True

        service._regenerate_learnings = mock_regenerate

        await service.record_pipeline_result(
            pipeline_id="pipe-2",
            theme="Social proof hooks",
            fate_scores=SAMPLE_FATE,
            awareness_level=3,
            platform="instagram",
            published_count=3,
            engagement_at_24h=800.0,
        )

        assert regenerate_called, "Should call _regenerate_learnings after recording"

    @pytest.mark.asyncio
    async def test_record_handles_missing_fate_keys(self):
        """Partial FATE scores (missing keys) default to 0.0."""
        from services.cross_pipeline_learning import CrossPipelineLearningService

        session = _make_session(fetchall_result=[])
        service = CrossPipelineLearningService(session)

        with patch.object(service, "_regenerate_learnings", new=AsyncMock()):
            # Shouldn't raise even with empty fate_scores
            row_id = await service.record_pipeline_result(
                pipeline_id="pipe-3",
                theme="Minimal FATE test",
                fate_scores={},  # all missing — should default to 0.0
                awareness_level=1,
                platform="youtube",
                published_count=1,
                engagement_at_24h=200.0,
            )
        assert row_id is not None


# ── _regenerate_learnings (OpenAI integration) ────────────────────────────────

class TestRegenerateLearnings:
    @pytest.mark.asyncio
    async def test_skips_when_no_rows(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService

        session = _make_session(fetchall_result=[])
        service = CrossPipelineLearningService(session)

        # Should return without calling OpenAI when no rows
        with patch("services.cross_pipeline_learning.OPENAI_API_KEY", "test-key"):
            with patch("httpx.AsyncClient") as mock_client:
                await service._regenerate_learnings()
                mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_no_openai_key(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService

        row = MagicMock()
        row.theme = "test"
        row.fate_focus = 0.8
        row.fate_authority = 0.7
        row.fate_tribe = 0.6
        row.fate_emotion = 0.9
        row.awareness_level = 2
        row.platform = "tiktok"
        row.published_count = 5
        row.engagement_at_24h = 1000.0

        session = _make_session(fetchall_result=[row])
        service = CrossPipelineLearningService(session)

        with patch("services.cross_pipeline_learning.OPENAI_API_KEY", ""):
            with patch("httpx.AsyncClient") as mock_client:
                await service._regenerate_learnings()
                mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_openai_and_saves_blob(self):
        from services.cross_pipeline_learning import CrossPipelineLearningService
        import httpx

        row = MagicMock()
        row.theme = "AI automation"
        row.fate_focus = 0.8
        row.fate_authority = 0.7
        row.fate_tribe = 0.6
        row.fate_emotion = 0.9
        row.awareness_level = 2
        row.platform = "tiktok"
        row.published_count = 5
        row.engagement_at_24h = 2500.0

        session = _make_session(fetchall_result=[row])
        service = CrossPipelineLearningService(session)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "choices": [{"message": {"content": "• AI automation drove 7.2% CTR on TikTok"}}]
        })

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("services.cross_pipeline_learning.OPENAI_API_KEY", "sk-test"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                await service._regenerate_learnings()

        # Should have saved context blob
        session.execute.assert_called()
        session.commit.assert_called()
