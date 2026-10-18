"""
Tests for Video Orientation Router (VID-001)
"""

import pytest
from services.format_detector import FormatDetector, FormatAnalysis, ContentFormat, ProductionQuality


class TestVideoOrientationRouter:
    """Test VID-001: Video Orientation Router"""

    @pytest.fixture
    def detector(self):
        """Create FormatDetector instance"""
        return FormatDetector()

    def test_vertical_video_9_16(self, detector):
        """Test vertical 9:16 video routing (TikTok, Reels, Shorts)"""
        # Typical 9:16 video: 1080x1920
        platforms = detector.route_video_by_orientation(1080, 1920)

        assert "tiktok" in platforms
        assert "instagram_reels" in platforms
        assert "youtube_shorts" in platforms

    def test_horizontal_video_16_9(self, detector):
        """Test horizontal 16:9 video routing (YouTube, LinkedIn)"""
        # Typical 16:9 video: 1920x1080
        platforms = detector.route_video_by_orientation(1920, 1080)

        assert "youtube" in platforms
        assert "linkedin" in platforms or "facebook" in platforms

    def test_square_video_1_1(self, detector):
        """Test square 1:1 video routing (Instagram Feed, LinkedIn, Twitter)"""
        # Square video: 1080x1080
        platforms = detector.route_video_by_orientation(1080, 1080)

        assert "instagram_feed" in platforms
        assert "linkedin" in platforms or "twitter" in platforms

    def test_ultra_wide_video(self, detector):
        """Test ultra-wide video routing (YouTube, Twitter)"""
        # Ultra-wide video: 2560x1080 (21:9)
        platforms = detector.route_video_by_orientation(2560, 1080)

        assert "youtube" in platforms

    def test_common_vertical_resolutions(self, detector):
        """Test various common vertical video resolutions"""
        vertical_resolutions = [
            (1080, 1920),  # 9:16 Full HD
            (720, 1280),   # 9:16 HD
            (1440, 2560),  # 9:16 2K
        ]

        for width, height in vertical_resolutions:
            platforms = detector.route_video_by_orientation(width, height)
            assert "tiktok" in platforms, f"TikTok should be in platforms for {width}x{height}"

    def test_common_horizontal_resolutions(self, detector):
        """Test various common horizontal video resolutions"""
        horizontal_resolutions = [
            (1920, 1080),  # 16:9 Full HD
            (1280, 720),   # 16:9 HD
            (3840, 2160),  # 16:9 4K
        ]

        for width, height in horizontal_resolutions:
            platforms = detector.route_video_by_orientation(width, height)
            assert "youtube" in platforms, f"YouTube should be in platforms for {width}x{height}"

    def test_orientation_category_vertical(self, detector):
        """Test get_video_orientation_category for vertical videos"""
        category = detector.get_video_orientation_category(1080, 1920)
        assert category == "vertical"

    def test_orientation_category_horizontal(self, detector):
        """Test get_video_orientation_category for horizontal videos"""
        category = detector.get_video_orientation_category(1920, 1080)
        assert category == "horizontal"

    def test_orientation_category_square(self, detector):
        """Test get_video_orientation_category for square videos"""
        category = detector.get_video_orientation_category(1080, 1080)
        assert category == "square"

    def test_orientation_category_ultra_wide(self, detector):
        """Test get_video_orientation_category for ultra-wide videos"""
        category = detector.get_video_orientation_category(2560, 1080)
        assert category == "ultra-wide"

    def test_routing_with_format_analysis_short_content(self, detector):
        """Test routing with format analysis for short-form content"""
        # Create short-form format analysis
        format_analysis = FormatAnalysis(
            primary_format=ContentFormat.MEME_CONTENT,
            confidence=0.9,
            duration_category="short",
            is_vertical=True
        )

        # Even for non-vertical dimensions, short content should prefer TikTok
        platforms = detector.route_video_by_orientation(1920, 1080, format_analysis)

        # TikTok should be added to platforms for short-form content
        assert "tiktok" in platforms

    def test_routing_with_format_analysis_long_content(self, detector):
        """Test routing with format analysis for long-form content"""
        # Create long-form format analysis
        format_analysis = FormatAnalysis(
            primary_format=ContentFormat.DOCUMENTARY,
            confidence=0.9,
            duration_category="long",
            is_horizontal=True
        )

        # Vertical video with long-form content should add YouTube
        platforms = detector.route_video_by_orientation(1080, 1920, format_analysis)

        assert "youtube" in platforms

    def test_routing_with_professional_quality(self, detector):
        """Test routing prioritizes YouTube for professional quality"""
        format_analysis = FormatAnalysis(
            primary_format=ContentFormat.DOCUMENTARY,
            confidence=0.9,
            production_quality=ProductionQuality.PROFESSIONAL
        )

        # Any video with professional quality should include YouTube
        platforms = detector.route_video_by_orientation(1080, 1920, format_analysis)

        assert "youtube" in platforms

    def test_zero_height_handling(self, detector):
        """Test that zero height doesn't cause division by zero"""
        # Should not raise exception
        platforms = detector.route_video_by_orientation(1920, 0)

        # Should return some platforms (fallback behavior)
        assert isinstance(platforms, list)
        assert len(platforms) > 0


class TestVideoOrientationFeatureAcceptance:
    """
    Acceptance criteria tests for VID-001:
    - Route videos to platforms by orientation (9:16 → Shorts/Reels, 16:9 → YouTube)
    """

    @pytest.fixture
    def detector(self):
        return FormatDetector()

    def test_acceptance_9_16_routes_to_shorts_reels(self, detector):
        """
        Acceptance: 9:16 videos route to Shorts/Reels/TikTok
        """
        # Test 9:16 aspect ratio (0.5625)
        platforms = detector.route_video_by_orientation(1080, 1920)

        # Must include short-form vertical platforms
        vertical_platforms = {"tiktok", "instagram_reels", "youtube_shorts"}
        assert any(p in platforms for p in vertical_platforms), \
            f"9:16 video must route to at least one vertical platform, got {platforms}"

    def test_acceptance_16_9_routes_to_youtube(self, detector):
        """
        Acceptance: 16:9 videos route to YouTube
        """
        # Test 16:9 aspect ratio (1.777)
        platforms = detector.route_video_by_orientation(1920, 1080)

        # Must include YouTube
        assert "youtube" in platforms, \
            f"16:9 video must route to YouTube, got {platforms}"

    def test_acceptance_orientation_determines_routing(self, detector):
        """
        Acceptance: Orientation is the primary routing factor
        """
        vertical_platforms = detector.route_video_by_orientation(1080, 1920)
        horizontal_platforms = detector.route_video_by_orientation(1920, 1080)

        # Vertical and horizontal should have different platform recommendations
        assert vertical_platforms != horizontal_platforms, \
            "Orientation should determine different platform routing"

        # Vertical should prefer short-form
        assert "tiktok" in vertical_platforms or "instagram_reels" in vertical_platforms

        # Horizontal should prefer long-form
        assert "youtube" in horizontal_platforms
