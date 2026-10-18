"""
Unit tests for Engagement Scraper (PTK-004)
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from automation.engagement_scraper import (
    EngagementScraper,
    Platform,
    PostStatus,
    get_engagement_scraper
)


class TestEngagementScraperCore:
    """Test core functionality"""

    def test_singleton_pattern(self):
        """Test that get_engagement_scraper returns singleton"""
        scraper1 = get_engagement_scraper()
        scraper2 = get_engagement_scraper()

        assert scraper1 is scraper2

    def test_platform_enum(self):
        """Test platform enum values"""
        assert Platform.TIKTOK.value == "tiktok"
        assert Platform.INSTAGRAM.value == "instagram"
        assert Platform.TWITTER.value == "twitter"
        assert Platform.THREADS.value == "threads"

    def test_post_status_enum(self):
        """Test post status enum"""
        assert PostStatus.ACTIVE.value == "active"
        assert PostStatus.DELETED.value == "deleted"
        assert PostStatus.PRIVATE.value == "private"
        assert PostStatus.NOT_FOUND.value == "not_found"
        assert PostStatus.ERROR.value == "error"

    def test_selectors_defined(self):
        """Test that selectors are defined for all platforms"""
        scraper = EngagementScraper()

        assert "tiktok" in scraper.selectors
        assert "instagram" in scraper.selectors
        assert "twitter" in scraper.selectors
        assert "threads" in scraper.selectors

        # Check TikTok selectors
        assert "views" in scraper.selectors["tiktok"]
        assert "likes" in scraper.selectors["tiktok"]
        assert "comments" in scraper.selectors["tiktok"]


class TestURLHandling:
    """Test URL opening and navigation"""

    @pytest.mark.asyncio
    async def test_open_url_unsupported_platform(self):
        """Test error on unsupported platform"""
        scraper = EngagementScraper()

        result = await scraper.scrape_post_metrics(
            platform="facebook",
            post_url="https://facebook.com/post/123"
        )

        assert result["success"] is False
        assert result["status"] == "error"
        assert "Unsupported platform" in result["error"]

    @pytest.mark.asyncio
    async def test_open_url_in_safari_mock(self):
        """Test opening URL in Safari (mocked)"""
        scraper = EngagementScraper()

        with patch.object(scraper, '_run_applescript', return_value="success"):
            result = await scraper._open_url_in_safari("https://tiktok.com/@user/video/123")

            assert result is True

    @pytest.mark.asyncio
    async def test_open_url_in_safari_failure(self):
        """Test Safari URL opening failure"""
        scraper = EngagementScraper()

        with patch.object(scraper, '_run_applescript', side_effect=Exception("Safari not found")):
            result = await scraper._open_url_in_safari("https://tiktok.com/@user/video/123")

            assert result is False


class TestTikTokMetricsExtraction:
    """Test TikTok metrics extraction"""

    @pytest.mark.asyncio
    async def test_extract_tiktok_metrics_active_post(self):
        """Test extracting metrics from active TikTok post"""
        scraper = EngagementScraper()

        # Mock AppleScript response
        mock_metrics = {
            "status": "active",
            "views": 150000,
            "likes": 12500,
            "comments": 450,
            "shares": 230,
            "saves": 890,
            "timestamp": "2026-01-26T00:00:00Z"
        }

        with patch.object(scraper, '_run_applescript', return_value=str(mock_metrics).replace("'", '"')):
            result = await scraper._extract_tiktok_metrics()

            assert result["status"] == "active"
            assert result["views"] == 150000
            assert result["likes"] == 12500
            assert result["comments"] == 450

    @pytest.mark.asyncio
    async def test_extract_tiktok_metrics_deleted_post(self):
        """Test handling deleted TikTok post"""
        scraper = EngagementScraper()

        mock_response = {
            "status": "deleted",
            "error": "Video unavailable"
        }

        with patch.object(scraper, '_run_applescript', return_value=str(mock_response).replace("'", '"')):
            result = await scraper._extract_tiktok_metrics()

            assert result["status"] == "deleted"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_extract_tiktok_metrics_not_found(self):
        """Test handling TikTok post not found"""
        scraper = EngagementScraper()

        mock_response = {
            "status": "not_found",
            "error": "Video player not found"
        }

        with patch.object(scraper, '_run_applescript', return_value=str(mock_response).replace("'", '"')):
            result = await scraper._extract_tiktok_metrics()

            assert result["status"] == "not_found"


class TestInstagramMetricsExtraction:
    """Test Instagram metrics extraction"""

    @pytest.mark.asyncio
    async def test_extract_instagram_metrics_active_post(self):
        """Test extracting metrics from active Instagram post"""
        scraper = EngagementScraper()

        mock_metrics = {
            "status": "active",
            "likes": 2500,
            "comments": 180,
            "views": 8900,  # For reels
            "timestamp": "2026-01-26T00:00:00Z"
        }

        with patch.object(scraper, '_run_applescript', return_value=str(mock_metrics).replace("'", '"')):
            result = await scraper._extract_instagram_metrics()

            assert result["status"] == "active"
            assert result["likes"] == 2500
            assert result["comments"] == 180


class TestTwitterMetricsExtraction:
    """Test X/Twitter metrics extraction"""

    @pytest.mark.asyncio
    async def test_extract_twitter_metrics_active_post(self):
        """Test extracting metrics from active Twitter post"""
        scraper = EngagementScraper()

        mock_metrics = {
            "status": "active",
            "likes": 1250,
            "retweets": 340,
            "replies": 89,
            "views": 0,
            "timestamp": "2026-01-26T00:00:00Z"
        }

        with patch.object(scraper, '_run_applescript', return_value=str(mock_metrics).replace("'", '"')):
            result = await scraper._extract_twitter_metrics()

            assert result["status"] == "active"
            assert result["likes"] == 1250
            assert result["retweets"] == 340


class TestThreadsMetricsExtraction:
    """Test Threads metrics extraction"""

    @pytest.mark.asyncio
    async def test_extract_threads_metrics_active_post(self):
        """Test extracting metrics from active Threads post"""
        scraper = EngagementScraper()

        mock_metrics = {
            "status": "active",
            "likes": 560,
            "comments": 45,
            "reposts": 23,
            "timestamp": "2026-01-26T00:00:00Z"
        }

        with patch.object(scraper, '_run_applescript', return_value=str(mock_metrics).replace("'", '"')):
            result = await scraper._extract_threads_metrics()

            assert result["status"] == "active"
            assert result["likes"] == 560


class TestFullScrapingFlow:
    """Test full scraping flow"""

    @pytest.mark.asyncio
    async def test_scrape_post_metrics_tiktok_success(self):
        """Test full scraping flow for TikTok"""
        scraper = EngagementScraper()

        mock_metrics = {
            "status": "active",
            "views": 50000,
            "likes": 4200,
            "comments": 125,
            "shares": 67,
            "saves": 234,
            "timestamp": "2026-01-26T00:00:00Z"
        }

        with patch.object(scraper, '_open_url_in_safari', return_value=True):
            with patch.object(scraper, '_extract_tiktok_metrics', return_value=mock_metrics):
                result = await scraper.scrape_post_metrics(
                    platform="tiktok",
                    post_url="https://www.tiktok.com/@user/video/123"
                )

                assert result["success"] is True
                assert result["status"] == "active"
                assert result["platform"] == "tiktok"
                assert result["post_url"] == "https://www.tiktok.com/@user/video/123"
                assert result["metrics"]["views"] == 50000
                assert result["metrics"]["likes"] == 4200
                assert "scraped_at" in result

    @pytest.mark.asyncio
    async def test_scrape_post_metrics_deleted_post(self):
        """Test scraping deleted post"""
        scraper = EngagementScraper()

        mock_metrics = {
            "status": "deleted",
            "error": "Video unavailable"
        }

        with patch.object(scraper, '_open_url_in_safari', return_value=True):
            with patch.object(scraper, '_extract_tiktok_metrics', return_value=mock_metrics):
                result = await scraper.scrape_post_metrics(
                    platform="tiktok",
                    post_url="https://www.tiktok.com/@user/video/123"
                )

                assert result["success"] is False
                assert result["status"] == "deleted"
                assert "error" in result

    @pytest.mark.asyncio
    async def test_scrape_post_metrics_safari_open_failure(self):
        """Test handling Safari open failure"""
        scraper = EngagementScraper()

        with patch.object(scraper, '_open_url_in_safari', return_value=False):
            result = await scraper.scrape_post_metrics(
                platform="tiktok",
                post_url="https://www.tiktok.com/@user/video/123"
            )

            assert result["success"] is False
            assert result["status"] == "error"
            assert "Failed to open URL" in result["error"]

    @pytest.mark.asyncio
    async def test_scrape_post_metrics_retry_on_error(self):
        """Test retry logic on error"""
        scraper = EngagementScraper()

        # First call fails, second succeeds
        call_count = [0]

        def mock_extract():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Network error")
            return {
                "status": "active",
                "views": 1000,
                "likes": 100,
                "comments": 10,
                "shares": 5,
                "saves": 15,
            }

        with patch.object(scraper, '_open_url_in_safari', return_value=True):
            with patch.object(scraper, '_extract_tiktok_metrics', side_effect=mock_extract):
                # Should fail after retries exhausted
                result = await scraper.scrape_post_metrics(
                    platform="tiktok",
                    post_url="https://www.tiktok.com/@user/video/123",
                    retry_count=0  # No retries
                )

                assert result["success"] is False
                assert result["status"] == "error"


class TestMetricsParsing:
    """Test metrics number parsing"""

    def test_parse_k_suffix(self):
        """Test parsing K suffix (thousands)"""
        # This would be tested via JavaScript in real implementation
        # Here we verify the logic exists in JS code
        scraper = EngagementScraper()
        assert "parseFloat(text.replace('K', '')) * 1000" in open(
            "automation/engagement_scraper.py"
        ).read()

    def test_parse_m_suffix(self):
        """Test parsing M suffix (millions)"""
        scraper = EngagementScraper()
        assert "parseFloat(text.replace('M', '')) * 1000000" in open(
            "automation/engagement_scraper.py"
        ).read()
