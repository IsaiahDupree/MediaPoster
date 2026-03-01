"""
Tests for ACTP Organic Publisher - Caption formatting, hashtags, rate limits, validation
"""

import pytest

from services.creative_testing_pipeline.organic_publisher import OrganicPublisher
from services.creative_testing_pipeline.models import Creative, GenerationSource, Platform


def _make_creative(**overrides):
    defaults = {
        "campaign_id": "c1",
        "round_id": "r1",
        "hook": "This productivity hack saved me 3 hours daily",
        "cta": "Try it free today",
        "angle": "productivity time saving",
        "script": "I discovered a method that changed how I work.",
        "generation_source": GenerationSource.SORA,
        "generation_metadata": {"brief": {"style": "ugc", "target_emotion": "curiosity"}},
    }
    defaults.update(overrides)
    return Creative(**defaults)


class TestHashtagGeneration:
    """Test platform-specific hashtag generation."""

    def setup_method(self):
        self.pub = OrganicPublisher()

    def test_tiktok_includes_fyp(self):
        c = _make_creative()
        tags = self.pub._generate_hashtags(c, "tiktok")
        assert "#fyp" in tags
        assert "#foryou" in tags

    def test_youtube_includes_shorts(self):
        c = _make_creative()
        tags = self.pub._generate_hashtags(c, "youtube_shorts")
        assert "#shorts" in tags

    def test_instagram_includes_reels(self):
        c = _make_creative()
        tags = self.pub._generate_hashtags(c, "instagram_reels")
        assert "#reels" in tags

    def test_content_tags_from_angle(self):
        c = _make_creative(angle="fitness weight loss")
        tags = self.pub._generate_hashtags(c, "tiktok")
        assert "#fitness" in tags

    def test_max_hashtag_count_respected(self):
        c = _make_creative(angle="a b c d e f g h i j k l m n o p q r s t")
        tags = self.pub._generate_hashtags(c, "tiktok")
        count = tags.count("#")
        assert count <= 10

    def test_emotion_tag_included(self):
        c = _make_creative()
        tags = self.pub._generate_hashtags(c, "tiktok")
        assert "#curiosity" in tags


class TestCaptionFormatting:
    """Test platform-specific caption formatting."""

    def setup_method(self):
        self.pub = OrganicPublisher()

    def test_tiktok_format(self):
        c = _make_creative()
        caption = self.pub.format_caption_for_platform(c, "tiktok")
        assert c.hook in caption
        assert c.cta in caption
        assert "#fyp" in caption

    def test_youtube_format(self):
        c = _make_creative()
        caption = self.pub.format_caption_for_platform(c, "youtube_shorts")
        assert c.hook[:100] in caption
        assert "#shorts" in caption

    def test_instagram_format(self):
        c = _make_creative()
        caption = self.pub.format_caption_for_platform(c, "instagram_reels")
        assert c.hook in caption
        assert "#reels" in caption
        assert ".\n.\n." in caption  # Instagram separator style


class TestCharacterLimits:
    """Test character limit validation and enforcement."""

    def setup_method(self):
        self.pub = OrganicPublisher()

    def test_tiktok_limit_2200(self):
        result = self.pub.validate_caption("x" * 2200, "tiktok")
        assert result["valid"] is True
        assert result["limit"] == 2200

    def test_over_limit_detected(self):
        result = self.pub.validate_caption("x" * 2500, "tiktok")
        assert result["valid"] is False
        assert result["over_by"] == 300

    def test_youtube_limit_5000(self):
        result = self.pub.validate_caption("x" * 4000, "youtube_shorts")
        assert result["valid"] is True

    def test_enforce_truncates(self):
        long = "x" * 3000
        result = self.pub._enforce_char_limit(long, "tiktok")
        assert len(result) <= 2200
        assert result.endswith("...")

    def test_within_limit_unchanged(self):
        short = "hello world"
        result = self.pub._enforce_char_limit(short, "tiktok")
        assert result == short


class TestRateLimiting:
    """Test platform rate limit tracking."""

    def setup_method(self):
        self.pub = OrganicPublisher()
        self.pub._rate_limit_state = {}

    def test_first_call_allowed(self):
        assert self.pub._check_rate_limit("tiktok") is True

    def test_within_limit_allowed(self):
        for _ in range(9):
            self.pub._check_rate_limit("tiktok")
        assert self.pub._check_rate_limit("tiktok") is True

    def test_over_limit_blocked(self):
        for _ in range(10):
            self.pub._check_rate_limit("tiktok")
        assert self.pub._check_rate_limit("tiktok") is False

    def test_different_platforms_independent(self):
        for _ in range(10):
            self.pub._check_rate_limit("tiktok")
        assert self.pub._check_rate_limit("youtube_shorts") is True


class TestCredentialCheck:
    """Test platform credential validation."""

    def test_returns_dict(self):
        pub = OrganicPublisher()
        creds = pub.check_credentials()
        assert isinstance(creds, dict)
        assert "youtube" in creds
        assert "tiktok" in creds
        assert "instagram" in creds


class TestPlatformSpecs:
    """Test video spec validation per platform."""

    def test_platform_specs_defined(self):
        from services.creative_testing_pipeline.creative_engine import CreativeEngine
        engine = CreativeEngine()
        assert "youtube_shorts" in engine.PLATFORM_SPECS
        assert "tiktok" in engine.PLATFORM_SPECS
        assert "instagram_reels" in engine.PLATFORM_SPECS

    def test_valid_video_passes(self):
        from services.creative_testing_pipeline.creative_engine import CreativeEngine
        engine = CreativeEngine()
        metadata = {
            "duration_seconds": 15,
            "file_size_bytes": 10_000_000,
            "codec": "h264",
        }
        result = engine.validate_for_platform(metadata, "tiktok")
        assert result["valid"] is True

    def test_too_long_fails(self):
        from services.creative_testing_pipeline.creative_engine import CreativeEngine
        engine = CreativeEngine()
        metadata = {"duration_seconds": 200, "file_size_bytes": 10_000_000, "codec": "h264"}
        result = engine.validate_for_platform(metadata, "tiktok")
        assert result["valid"] is False
        assert any("Duration" in e for e in result["errors"])

    def test_wrong_codec_fails(self):
        from services.creative_testing_pipeline.creative_engine import CreativeEngine
        engine = CreativeEngine()
        metadata = {"duration_seconds": 15, "file_size_bytes": 10_000_000, "codec": "av1"}
        result = engine.validate_for_platform(metadata, "instagram_reels")
        assert result["valid"] is False

    def test_unknown_platform_passes(self):
        from services.creative_testing_pipeline.creative_engine import CreativeEngine
        engine = CreativeEngine()
        result = engine.validate_for_platform({}, "unknown_platform")
        assert result["valid"] is True
