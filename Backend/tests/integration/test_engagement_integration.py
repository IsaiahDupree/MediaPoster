"""
Integration Tests for Auto-Engagement System

Tests the full engagement flow across all 4 platforms:
- Threads, Instagram, TikTok, Twitter

These tests verify:
- Platform modules can be loaded and initialized
- Engagement runner can process all platforms
- Daily limits are respected
- Duplicate detection works
- Pause/resume functionality works
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.engagement.engagement_runner import EngagementRunner, PLATFORMS
from services.engagement.engagement_service import EngagementService, DELAY_CONFIG
from services.engagement.comment_tracker import CommentTracker, PlatformStatus


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_tracker():
    """Create a mock comment tracker."""
    tracker = Mock(spec=CommentTracker)
    tracker.is_enabled = AsyncMock(return_value=True)
    tracker.is_limit_reached = AsyncMock(return_value=False)
    tracker.get_remaining = AsyncMock(return_value=95)
    tracker.record_comment = AsyncMock()
    tracker.has_commented_on = AsyncMock(return_value=False)
    tracker.get_status = AsyncMock(return_value=PlatformStatus(
        platform='test',
        is_enabled=True,
        daily_limit=100,
        today_count=5,
        remaining=95,
        last_engagement=None
    ))
    tracker.get_daily_count = AsyncMock(return_value=5)
    return tracker


@pytest.fixture
def mock_engagement_result():
    """Create a mock engagement result."""
    result = Mock()
    result.success = True
    result.comment_posted = True
    result.post_url = 'https://example.com/post/123'
    result.username = '@testuser'
    result.generated_comment = 'Great post! 🔥'
    result.proof_screenshot = '/tmp/proof.png'
    result.error = ''
    return result


# =============================================================================
# Platform Module Loading Tests
# =============================================================================

class TestPlatformModules:
    """Test that all platform modules can be loaded."""
    
    def test_threads_module_exists(self):
        """Threads module can be imported."""
        from scripts.auto_engagement.threads_engagement import ThreadsEngagement
        assert ThreadsEngagement is not None
    
    def test_instagram_module_exists(self):
        """Instagram module can be imported."""
        from scripts.auto_engagement.instagram_engagement import InstagramEngagement
        assert InstagramEngagement is not None
    
    def test_tiktok_module_exists(self):
        """TikTok module can be imported."""
        from scripts.auto_engagement.tiktok_engagement import TikTokEngagement
        assert TikTokEngagement is not None
    
    def test_twitter_module_exists(self):
        """Twitter module can be imported."""
        from scripts.auto_engagement.twitter_engagement import TwitterEngagement
        assert TwitterEngagement is not None
    
    def test_all_platforms_defined(self):
        """All 4 platforms are defined in PLATFORMS."""
        assert 'threads' in PLATFORMS
        assert 'instagram' in PLATFORMS
        assert 'tiktok' in PLATFORMS
        assert 'twitter' in PLATFORMS
        assert len(PLATFORMS) == 4
    
    def test_all_platforms_have_delay_config(self):
        """All platforms have delay configuration."""
        for platform in PLATFORMS:
            assert platform in DELAY_CONFIG
            assert 'min' in DELAY_CONFIG[platform]
            assert 'max' in DELAY_CONFIG[platform]


# =============================================================================
# Engagement Runner Tests
# =============================================================================

class TestEngagementRunner:
    """Test the EngagementRunner class."""
    
    @pytest.fixture
    def runner(self, mock_tracker):
        """Create runner with mock tracker."""
        runner = EngagementRunner()
        runner._tracker = mock_tracker
        return runner
    
    @pytest.mark.asyncio
    async def test_run_single_checks_enabled(self, runner, mock_tracker):
        """run_single checks if platform is enabled."""
        mock_tracker.is_enabled.return_value = False
        
        result = await runner.run_single('threads')
        
        assert result['success'] is False
        assert 'paused' in result['error'].lower()
        mock_tracker.is_enabled.assert_called_with('threads')
    
    @pytest.mark.asyncio
    async def test_run_single_checks_limit(self, runner, mock_tracker):
        """run_single checks if daily limit is reached."""
        mock_tracker.is_limit_reached.return_value = True
        
        result = await runner.run_single('threads')
        
        assert result['success'] is False
        assert 'limit' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_run_single_records_comment(self, runner, mock_tracker, mock_engagement_result):
        """run_single records comment when posted."""
        with patch.object(runner, '_get_module') as mock_get_module:
            mock_module = Mock()
            mock_module.engage_with_post.return_value = mock_engagement_result
            mock_get_module.return_value = mock_module
            
            result = await runner.run_single('threads')
            
            assert result['success'] is True
            assert result['posted'] is True
            mock_tracker.record_comment.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_platform_respects_count(self, runner, mock_tracker, mock_engagement_result):
        """run_platform runs specified number of engagements."""
        with patch.object(runner, '_get_module') as mock_get_module:
            mock_module = Mock()
            mock_module.engage_with_post.return_value = mock_engagement_result
            mock_get_module.return_value = mock_module
            
            # Disable delay for faster test
            summary = await runner.run_platform('threads', count=3, delay_between=False)
            
            assert summary['posted'] == 3
            assert mock_module.engage_with_post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_run_platform_stops_at_limit(self, runner, mock_tracker, mock_engagement_result):
        """run_platform stops when limit is reached."""
        mock_tracker.get_remaining.return_value = 2  # Only 2 remaining
        
        with patch.object(runner, '_get_module') as mock_get_module:
            mock_module = Mock()
            mock_module.engage_with_post.return_value = mock_engagement_result
            mock_get_module.return_value = mock_module
            
            summary = await runner.run_platform('threads', count=5, delay_between=False)
            
            # Should only run 2 times (remaining capacity)
            assert mock_module.engage_with_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_all_platforms_runs_each(self, runner, mock_tracker, mock_engagement_result):
        """run_all_platforms processes each enabled platform."""
        with patch.object(runner, '_get_module') as mock_get_module:
            mock_module = Mock()
            mock_module.engage_with_post.return_value = mock_engagement_result
            mock_get_module.return_value = mock_module
            
            results = await runner.run_all_platforms(comments_per_platform=1)
            
            # Should have results for all 4 platforms
            assert len(results) == 4
            for platform in PLATFORMS:
                assert platform in results
    
    @pytest.mark.asyncio
    async def test_run_all_skips_paused_platforms(self, runner, mock_tracker, mock_engagement_result):
        """run_all_platforms skips paused platforms."""
        async def is_enabled_side_effect(platform):
            return platform != 'tiktok'  # TikTok is paused
        
        mock_tracker.is_enabled.side_effect = is_enabled_side_effect
        
        with patch.object(runner, '_get_module') as mock_get_module:
            mock_module = Mock()
            mock_module.engage_with_post.return_value = mock_engagement_result
            mock_get_module.return_value = mock_module
            
            results = await runner.run_all_platforms(comments_per_platform=1)
            
            # TikTok should be skipped
            assert results['tiktok']['posted'] == 0
            assert 'Paused' in results['tiktok']['errors']


# =============================================================================
# Daily Limits Integration Tests
# =============================================================================

class TestDailyLimits:
    """Test daily limit enforcement."""
    
    @pytest.fixture
    def runner(self, mock_tracker):
        runner = EngagementRunner()
        runner._tracker = mock_tracker
        return runner
    
    @pytest.mark.asyncio
    async def test_stops_at_zero_remaining(self, runner, mock_tracker):
        """Runner stops when no capacity remaining."""
        mock_tracker.get_remaining.return_value = 0
        
        summary = await runner.run_platform('threads', count=5, delay_between=False)
        
        assert summary['posted'] == 0
        assert 'limit' in summary['errors'][0].lower()
    
    @pytest.mark.asyncio
    async def test_run_until_limits_exhausts_capacity(self, runner, mock_tracker, mock_engagement_result):
        """run_until_limits runs until all limits reached."""
        # Start with 3 remaining for each platform
        remaining_counts = {p: 3 for p in PLATFORMS}
        
        async def get_remaining_side_effect(platform):
            return remaining_counts.get(platform, 0)
        
        async def record_comment_side_effect(**kwargs):
            platform = kwargs.get('platform')
            if platform in remaining_counts:
                remaining_counts[platform] -= 1
        
        mock_tracker.get_remaining.side_effect = get_remaining_side_effect
        mock_tracker.record_comment.side_effect = record_comment_side_effect
        
        with patch.object(runner, '_get_module') as mock_get_module:
            mock_module = Mock()
            mock_module.engage_with_post.return_value = mock_engagement_result
            mock_get_module.return_value = mock_module
            
            results = await runner.run_until_limits(batch_size=2)
            
            # All platforms should have posted their remaining
            total_posted = sum(r['posted'] for r in results.values())
            assert total_posted == 12  # 3 per platform * 4 platforms


# =============================================================================
# Duplicate Detection Tests
# =============================================================================

class TestDuplicateDetection:
    """Test duplicate comment prevention."""
    
    @pytest.fixture
    def runner(self, mock_tracker):
        runner = EngagementRunner()
        runner._tracker = mock_tracker
        return runner
    
    @pytest.mark.asyncio
    async def test_duplicate_not_recorded_twice(self, runner, mock_tracker, mock_engagement_result):
        """Duplicate comments raise error and aren't double-counted."""
        mock_tracker.record_comment.side_effect = ValueError("Duplicate comment")
        
        with patch.object(runner, '_get_module') as mock_get_module:
            mock_module = Mock()
            mock_module.engage_with_post.return_value = mock_engagement_result
            mock_get_module.return_value = mock_module
            
            # Should not raise, just log warning
            result = await runner.run_single('threads')
            
            # Still considered success since comment was posted
            assert result['posted'] is True


# =============================================================================
# Pause/Resume Tests
# =============================================================================

class TestPauseResume:
    """Test pause/resume functionality."""
    
    @pytest.fixture
    def runner(self, mock_tracker):
        runner = EngagementRunner()
        runner._tracker = mock_tracker
        return runner
    
    @pytest.mark.asyncio
    async def test_paused_platform_skipped(self, runner, mock_tracker):
        """Paused platforms are skipped."""
        mock_tracker.is_enabled.return_value = False
        
        result = await runner.run_single('threads')
        
        assert result['success'] is False
        assert 'paused' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_resumed_platform_processes(self, runner, mock_tracker, mock_engagement_result):
        """Resumed platforms are processed."""
        mock_tracker.is_enabled.return_value = True
        
        with patch.object(runner, '_get_module') as mock_get_module:
            mock_module = Mock()
            mock_module.engage_with_post.return_value = mock_engagement_result
            mock_get_module.return_value = mock_module
            
            result = await runner.run_single('threads')
            
            assert result['success'] is True


# =============================================================================
# Status Report Tests
# =============================================================================

class TestStatusReport:
    """Test status reporting."""
    
    @pytest.fixture
    def runner(self, mock_tracker):
        runner = EngagementRunner()
        runner._tracker = mock_tracker
        return runner
    
    @pytest.mark.asyncio
    async def test_status_report_includes_all_platforms(self, runner, mock_tracker):
        """Status report includes all 4 platforms."""
        report = await runner.get_status_report()
        
        for platform in PLATFORMS:
            assert platform.upper() in report
    
    @pytest.mark.asyncio
    async def test_status_report_shows_counts(self, runner, mock_tracker):
        """Status report shows today count and limit."""
        mock_tracker.get_status.return_value = PlatformStatus(
            platform='threads',
            is_enabled=True,
            daily_limit=100,
            today_count=42,
            remaining=58,
            last_engagement=None
        )
        
        report = await runner.get_status_report()
        
        assert '42' in report
        assert '100' in report


# =============================================================================
# End-to-End Integration Test (Mocked)
# =============================================================================

class TestEndToEnd:
    """End-to-end integration test with mocked Safari."""
    
    @pytest.mark.asyncio
    async def test_full_engagement_cycle(self, mock_tracker, mock_engagement_result):
        """Test complete engagement cycle across all platforms."""
        runner = EngagementRunner()
        runner._tracker = mock_tracker
        
        # Track which platforms were engaged
        engaged_platforms = []
        
        def create_mock_module(platform):
            mock_module = Mock()
            def engage():
                engaged_platforms.append(platform)
                return mock_engagement_result
            mock_module.engage_with_post = engage
            return mock_module
        
        with patch.object(runner, '_get_module', side_effect=create_mock_module):
            results = await runner.run_all_platforms(comments_per_platform=1)
        
        # All 4 platforms should have been engaged
        assert len(engaged_platforms) == 4
        assert set(engaged_platforms) == set(PLATFORMS)
        
        # All should have 1 posted
        for platform in PLATFORMS:
            assert results[platform]['posted'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
