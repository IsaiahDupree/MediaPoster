"""
Unit Tests for Orchestrator Platform Metadata Extraction (ARCH-003)
====================================================================
Tests the enhanced _extract_platform_metadata method that converts
ContentAnalyzer output into platform-specific publishing metadata.
"""

import pytest
from unittest.mock import Mock, patch

from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus.bus import EventBus


@pytest.fixture
def event_bus():
    """Create an isolated event bus for testing."""
    return EventBus()


@pytest.fixture
def orchestrator(event_bus):
    """Create orchestrator with mocked dependencies."""
    orch = MasterOrchestrator(event_bus=event_bus, use_db=False)
    orch.sora_pipeline = Mock()
    orch.blotato_service = Mock()
    orch.twitter_service = Mock()
    return orch


class TestPlatformMetadataExtraction:
    """Test ARCH-003 platform metadata extraction."""

    def test_extracts_default_metadata(self, orchestrator):
        """Test default metadata extraction from analysis."""
        analysis = {
            "detected_hook": "AI is changing everything",
            "topics": ["AI", "automation"],
            "hashtags": ["ai", "viral", "trending"],
            "viral_score": 85,
            "tone": "energetic",
            "content_type": "tutorial",
            "call_to_action": {
                "type": "follow",
                "text": "Follow for more AI content!",
                "strength": "strong",
            },
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert "default" in metadata
        assert metadata["default"]["hook"] == "AI is changing everything"
        assert metadata["default"]["viral_score"] == 85
        assert metadata["default"]["content_type"] == "tutorial"
        assert metadata["default"]["tone"] == "energetic"
        assert metadata["default"]["cta"] == "Follow for more AI content!"

    def test_tiktok_specific_metadata(self, orchestrator):
        """Test TikTok gets max 10 hashtags."""
        analysis = {
            "detected_hook": "Hook text",
            "hashtags": [f"tag{i}" for i in range(20)],
            "viral_score": 70,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert "tiktok" in metadata
        assert len(metadata["tiktok"]["hashtags"]) <= 10

    def test_instagram_specific_metadata(self, orchestrator):
        """Test Instagram gets max 30 hashtags."""
        analysis = {
            "detected_hook": "Hook text",
            "hashtags": [f"tag{i}" for i in range(35)],
            "viral_score": 70,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert "instagram" in metadata
        assert len(metadata["instagram"]["hashtags"]) <= 30

    def test_youtube_specific_metadata(self, orchestrator):
        """Test YouTube gets max 15 hashtags."""
        analysis = {
            "detected_hook": "Hook text",
            "hashtags": [f"tag{i}" for i in range(20)],
            "viral_score": 70,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert "youtube" in metadata
        assert len(metadata["youtube"]["hashtags"]) <= 15

    def test_twitter_specific_metadata(self, orchestrator):
        """Test Twitter gets max 3 hashtags and truncated title."""
        analysis = {
            "detected_hook": "A" * 300,  # Very long hook
            "hashtags": [f"tag{i}" for i in range(10)],
            "viral_score": 70,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert "twitter" in metadata
        assert len(metadata["twitter"]["hashtags"]) <= 3
        assert len(metadata["twitter"]["title"]) <= 200

    def test_platform_specific_titles_used(self, orchestrator):
        """Test platform-specific titles override default."""
        analysis = {
            "detected_hook": "Default hook",
            "title_tiktok": "TikTok Title",
            "title_instagram": "Insta Title",
            "title_youtube": "YouTube Title",
            "hashtags": ["test"],
            "viral_score": 70,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert metadata["tiktok"]["title"] == "TikTok Title"
        assert metadata["instagram"]["title"] == "Insta Title"
        assert metadata["youtube"]["title"] == "YouTube Title"

    def test_all_platforms_have_metadata(self, orchestrator):
        """Test all 9+ platforms get metadata entries."""
        analysis = {
            "detected_hook": "Hook",
            "hashtags": ["test"],
            "viral_score": 50,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        expected_platforms = [
            "default", "tiktok", "instagram", "youtube",
            "twitter", "threads", "pinterest", "linkedin",
            "facebook", "bluesky",
        ]
        for platform in expected_platforms:
            assert platform in metadata, f"Missing metadata for {platform}"
            assert "hook" in metadata[platform]
            assert "hashtags" in metadata[platform]

    def test_handles_empty_analysis(self, orchestrator):
        """Test graceful handling of empty/minimal analysis."""
        analysis = {}

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert "default" in metadata
        assert metadata["default"]["title"] == "Untitled"
        assert metadata["default"]["viral_score"] == 0

    def test_cta_extraction_from_structured_cta(self, orchestrator):
        """Test CTA is extracted from structured call_to_action field."""
        analysis = {
            "detected_hook": "Hook",
            "call_to_action": {
                "type": "purchase",
                "text": "Buy now and save 50%!",
                "strength": "strong",
            },
            "viral_score": 90,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert metadata["default"]["cta"] == "Buy now and save 50%!"

    def test_cta_empty_when_no_cta(self, orchestrator):
        """Test CTA is empty string when no call_to_action."""
        analysis = {
            "detected_hook": "Hook",
            "viral_score": 50,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert metadata["default"]["cta"] == ""

    def test_viral_score_from_pre_social_score(self, orchestrator):
        """Test viral_score falls back to pre_social_score."""
        analysis = {
            "detected_hook": "Hook",
            "pre_social_score": 75,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert metadata["default"]["viral_score"] == 75

    def test_description_from_viral_analysis(self, orchestrator):
        """Test description falls back to viral_analysis."""
        analysis = {
            "detected_hook": "Hook",
            "viral_analysis": "This content has high viral potential because...",
            "viral_score": 80,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert "high viral potential" in metadata["default"]["description"]

    def test_topics_passed_through(self, orchestrator):
        """Test topics are included in metadata."""
        analysis = {
            "detected_hook": "Hook",
            "topics": ["AI", "productivity", "automation"],
            "viral_score": 70,
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        assert metadata["default"]["topics"] == ["AI", "productivity", "automation"]


class TestPublishWorkerCaptionBuilding:
    """Test ARCH-003 caption building in PublishWorker."""

    def _get_worker(self):
        """Create a PublishWorker with mocked event bus."""
        bus = EventBus()
        from services.workers.publish_worker import PublishWorker
        return PublishWorker(event_bus=bus)

    def test_tiktok_caption_with_structured_cta(self):
        """Test TikTok caption uses structured CTA."""
        worker = self._get_worker()

        analysis = {
            "detected_hook": "You won't believe this AI hack",
            "call_to_action": {
                "type": "follow",
                "text": "Follow @me for more!",
            },
            "hashtags": ["ai", "hack", "viral"],
        }

        caption = worker._build_platform_caption(analysis, "tiktok")

        assert "You won't believe this AI hack" in caption
        assert "Follow @me for more!" in caption
        assert "#ai" in caption
        assert len(caption) <= 2200

    def test_instagram_caption_includes_description(self):
        """Test Instagram caption includes viral_analysis as description."""
        worker = self._get_worker()

        analysis = {
            "detected_hook": "Hook text",
            "viral_analysis": "This video explains how AI transforms content.",
            "call_to_action": {"text": "Save this!"},
            "hashtags": ["ai"],
        }

        caption = worker._build_platform_caption(analysis, "instagram")

        assert "Hook text" in caption
        assert "AI transforms content" in caption
        assert "Save this!" in caption

    def test_twitter_caption_respects_280_limit(self):
        """Test Twitter caption stays within 280 chars."""
        worker = self._get_worker()

        analysis = {
            "detected_hook": "A" * 300,
            "hashtags": ["a", "b", "c", "d", "e"],
        }

        caption = worker._build_platform_caption(analysis, "twitter")

        assert len(caption) <= 280

    def test_youtube_caption_allows_long_content(self):
        """Test YouTube caption allows up to 5000 chars."""
        worker = self._get_worker()

        analysis = {
            "detected_hook": "Hook",
            "viral_analysis": "Long description " * 100,
            "call_to_action": {"text": "Subscribe!"},
            "hashtags": [f"tag{i}" for i in range(15)],
        }

        caption = worker._build_platform_caption(analysis, "youtube")

        assert len(caption) <= 5000
        assert "Subscribe!" in caption

    def test_fallback_cta_when_no_structured_cta(self):
        """Test fallback CTA when no structured call_to_action."""
        worker = self._get_worker()

        analysis = {
            "detected_hook": "Hook",
            "cta": "Custom CTA text",
        }

        caption = worker._build_platform_caption(analysis, "tiktok")

        assert "Custom CTA text" in caption

    def test_default_cta_when_nothing_provided(self):
        """Test default CTA when no CTA data at all."""
        worker = self._get_worker()

        analysis = {
            "detected_hook": "Hook",
        }

        caption = worker._build_platform_caption(analysis, "tiktok")

        assert "Follow for more!" in caption


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
