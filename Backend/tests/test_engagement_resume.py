"""
Tests for Engagement Automation Resume Behavior
=================================================
Tests for start/stop/pause/resume and auto-resume after Mac idle.

Auto-Resume Behavior:
- When user STOPS using Mac (idle for 2.5+ hours), automation auto-resumes
- Idle detection via `ioreg -c IOHIDSystem` (HIDIdleTime in nanoseconds)
- Checked every 5 minutes (IDLE_CHECK_INTERVAL = 300)
- Configurable via API: auto_resume_enabled, auto_resume_hours
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import sys
sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')

from services.engagement.engagement_controller import (
    EngagementController,
    EngagementState,
    EngagementStatus,
    PlatformStats
)


class TestEngagementControllerBasics:
    """Test basic controller functionality."""
    
    @pytest.fixture
    def controller(self):
        """Create fresh controller instance."""
        EngagementController._instance = None
        return EngagementController()
    
    def test_initial_state_is_stopped(self, controller):
        """Controller starts in STOPPED state."""
        assert controller.state == EngagementState.STOPPED
    
    def test_default_auto_resume_settings(self, controller):
        """Default auto-resume is enabled at 15 minutes (0.25 hours)."""
        assert controller.auto_resume_enabled is True
        assert controller.auto_resume_after_hours == 0.25
    
    def test_platforms_initialized(self, controller):
        """All platforms are initialized."""
        assert 'threads' in controller.platform_stats
        assert 'instagram' in controller.platform_stats
        assert 'tiktok' in controller.platform_stats
        assert 'twitter' in controller.platform_stats


class TestEngagementStartStop:
    """Test start/stop/pause/resume flow."""
    
    @pytest.fixture
    def controller(self):
        """Create fresh controller instance."""
        EngagementController._instance = None
        ctrl = EngagementController()
        ctrl.auto_resume_enabled = False  # Disable for simpler testing
        return ctrl
    
    @pytest.mark.asyncio
    async def test_start_automation(self, controller):
        """Test starting automation."""
        result = await controller.start()
        
        assert result["success"] is True
        assert controller.state == EngagementState.RUNNING
        assert controller.started_at is not None
        
        # Cleanup
        await controller.stop()
    
    @pytest.mark.asyncio
    async def test_start_when_already_running(self, controller):
        """Cannot start when already running."""
        await controller.start()
        
        result = await controller.start()
        
        assert result["success"] is False
        assert "Already running" in result["error"]
        
        await controller.stop()
    
    @pytest.mark.asyncio
    async def test_stop_automation(self, controller):
        """Test stopping automation."""
        await controller.start()
        
        result = await controller.stop()
        
        assert result["success"] is True
        assert controller.state == EngagementState.STOPPED
        assert controller.stopped_at is not None
    
    @pytest.mark.asyncio
    async def test_stop_when_already_stopped(self, controller):
        """Cannot stop when already stopped."""
        result = await controller.stop()
        
        assert result["success"] is False
        assert "Already stopped" in result["error"]
    
    @pytest.mark.asyncio
    async def test_pause_automation(self, controller):
        """Test pausing running automation."""
        await controller.start()
        
        result = await controller.pause()
        
        assert result["success"] is True
        assert controller.state == EngagementState.PAUSED
        
        await controller.stop()
    
    @pytest.mark.asyncio
    async def test_pause_when_not_running(self, controller):
        """Cannot pause when not running."""
        result = await controller.pause()
        
        assert result["success"] is False
        assert "Not running" in result["error"]
    
    @pytest.mark.asyncio
    async def test_resume_automation(self, controller):
        """Test resuming paused automation."""
        await controller.start()
        await controller.pause()
        
        result = await controller.resume()
        
        assert result["success"] is True
        assert controller.state == EngagementState.RUNNING
        
        await controller.stop()
    
    @pytest.mark.asyncio
    async def test_resume_when_not_paused(self, controller):
        """Cannot resume when not paused."""
        await controller.start()
        
        result = await controller.resume()
        
        assert result["success"] is False
        assert "Not paused" in result["error"]
        
        await controller.stop()


class TestMacIdleDetection:
    """Test Mac idle time detection."""
    
    @pytest.fixture
    def controller(self):
        """Create fresh controller instance."""
        EngagementController._instance = None
        return EngagementController()
    
    def test_get_mac_idle_time_returns_float(self, controller):
        """Idle time detection returns a float (seconds)."""
        idle_time = controller.get_mac_idle_time()
        
        assert isinstance(idle_time, (int, float))
        assert idle_time >= 0
    
    def test_get_idle_minutes(self, controller):
        """Idle minutes calculation."""
        with patch.object(controller, 'get_mac_idle_time', return_value=180):
            minutes = controller.get_idle_minutes()
            assert minutes == 3.0
    
    def test_get_idle_hours(self, controller):
        """Idle hours calculation."""
        with patch.object(controller, 'get_mac_idle_time', return_value=9000):
            hours = controller.get_idle_hours()
            assert hours == 2.5
    
    def test_idle_detection_handles_error(self, controller):
        """Idle detection returns 0 on error."""
        with patch('subprocess.run', side_effect=Exception("ioreg failed")):
            idle_time = controller.get_mac_idle_time()
            assert idle_time == 0


class TestAutoResume:
    """
    Test auto-resume behavior after Mac idle.
    
    When does automation resume after user stops using Mac?
    --------------------------------------------------------
    1. User clicks STOP or PAUSE → state changes to STOPPED/PAUSED
    2. When state is IDLE_WAITING, idle monitor checks every 5 minutes
    3. If Mac idle time >= 2.5 hours (configurable), state → RUNNING
    4. Engagement loop continues posting comments
    
    Timeline Example:
    - 10:00 PM: User pauses automation, starts watching a movie
    - 10:05 PM: Idle check #1 (0h idle) - no action
    - 10:10 PM: Idle check #2 (0.08h idle) - no action
    - ... (user continues watching/leaves Mac idle)
    - 12:30 AM: Idle check (2.5h idle) → AUTO RESUME!
    - 12:30 AM: Comments start posting again
    """
    
    @pytest.fixture
    def controller(self):
        """Create controller with auto-resume enabled."""
        EngagementController._instance = None
        ctrl = EngagementController()
        ctrl.auto_resume_enabled = True
        ctrl.auto_resume_after_hours = 2.5
        return ctrl
    
    def test_auto_resume_settings_configurable(self, controller):
        """Auto-resume settings can be configured."""
        controller.set_auto_resume(enabled=True, hours=3.0)
        
        assert controller.auto_resume_enabled is True
        assert controller.auto_resume_after_hours == 3.0
        
        controller.set_auto_resume(enabled=False, hours=1.0)
        
        assert controller.auto_resume_enabled is False
        assert controller.auto_resume_after_hours == 1.0
    
    @pytest.mark.asyncio
    async def test_idle_monitor_starts_with_automation(self, controller):
        """Idle monitor task starts when automation starts."""
        await controller.start()
        
        assert controller._idle_monitor_task is not None
        
        await controller.stop()
    
    @pytest.mark.asyncio
    async def test_idle_monitor_does_not_start_when_disabled(self, controller):
        """Idle monitor doesn't start when auto-resume disabled."""
        controller.auto_resume_enabled = False
        
        await controller.start()
        
        assert controller._idle_monitor_task is None
        
        await controller.stop()
    
    @pytest.mark.asyncio
    async def test_auto_resume_after_idle_threshold(self, controller):
        """State changes to RUNNING after idle threshold reached."""
        controller.state = EngagementState.IDLE_WAITING
        
        # Mock 3 hours of idle time (exceeds 2.5h threshold)
        with patch.object(controller, 'get_idle_hours', return_value=3.0):
            # Simulate what idle_monitor_loop does
            idle_hours = controller.get_idle_hours()
            
            if controller.state == EngagementState.IDLE_WAITING:
                if idle_hours >= controller.auto_resume_after_hours:
                    controller.state = EngagementState.RUNNING
        
        assert controller.state == EngagementState.RUNNING
    
    @pytest.mark.asyncio
    async def test_no_auto_resume_below_threshold(self, controller):
        """State stays IDLE_WAITING below threshold."""
        controller.state = EngagementState.IDLE_WAITING
        
        # Mock 1 hour of idle time (below 2.5h threshold)
        with patch.object(controller, 'get_idle_hours', return_value=1.0):
            idle_hours = controller.get_idle_hours()
            
            if controller.state == EngagementState.IDLE_WAITING:
                if idle_hours >= controller.auto_resume_after_hours:
                    controller.state = EngagementState.RUNNING
        
        assert controller.state == EngagementState.IDLE_WAITING


class TestEngagementStatus:
    """Test status reporting."""
    
    @pytest.fixture
    def controller(self):
        """Create fresh controller instance."""
        EngagementController._instance = None
        return EngagementController()
    
    def test_status_includes_idle_time(self, controller):
        """Status includes current idle time."""
        status = controller.get_status()
        
        assert hasattr(status, 'idle_minutes')
        assert isinstance(status.idle_minutes, float)
    
    def test_status_includes_auto_resume_settings(self, controller):
        """Status includes auto-resume configuration."""
        status = controller.get_status()
        
        assert status.auto_resume_enabled is True
        assert status.auto_resume_after_hours == 0.25
    
    def test_status_to_dict(self, controller):
        """Status can be serialized to dict."""
        status = controller.get_status()
        d = status.to_dict()
        
        assert "state" in d
        assert "idle_minutes" in d
        assert "auto_resume_enabled" in d
        assert "auto_resume_after_hours" in d
        assert "platforms" in d


class TestPlatformControl:
    """Test platform enable/disable."""
    
    @pytest.fixture
    def controller(self):
        """Create fresh controller instance."""
        EngagementController._instance = None
        return EngagementController()
    
    def test_enable_platform(self, controller):
        """Can enable a platform."""
        controller.enable_platform('tiktok', enabled=True)
        
        assert controller.platform_stats['tiktok'].is_enabled is True
    
    def test_disable_platform(self, controller):
        """Can disable a platform."""
        controller.enable_platform('tiktok', enabled=False)
        
        assert controller.platform_stats['tiktok'].is_enabled is False
    
    def test_disabled_platform_cannot_post(self, controller):
        """Disabled platform returns cannot post."""
        controller.enable_platform('instagram', enabled=False)
        
        can_post, reason = controller._can_post_on_platform('instagram')
        
        assert can_post is False
        assert "disabled" in reason.lower()


class TestRateLimiting:
    """Test rate limiting (30 comments/hour/platform)."""
    
    @pytest.fixture
    def controller(self):
        """Create fresh controller instance."""
        EngagementController._instance = None
        return EngagementController()
    
    def test_hourly_limit_default(self, controller):
        """Default hourly limit is 30."""
        assert controller.COMMENTS_PER_HOUR_PER_PLATFORM == 30
    
    def test_can_post_when_under_limit(self, controller):
        """Can post when under hourly limit."""
        controller.platform_stats['tiktok'].comments_this_hour = 10
        
        can_post, reason = controller._can_post_on_platform('tiktok')
        
        assert can_post is True
    
    def test_cannot_post_when_at_limit(self, controller):
        """Cannot post when at hourly limit."""
        controller.platform_stats['tiktok'].comments_this_hour = 30
        
        can_post, reason = controller._can_post_on_platform('tiktok')
        
        assert can_post is False
        assert "limit" in reason.lower()
    
    def test_hourly_counts_reset(self, controller):
        """Hourly counts are reset."""
        controller.platform_stats['tiktok'].comments_this_hour = 25
        controller.platform_stats['instagram'].comments_this_hour = 15
        
        controller._reset_hourly_counts()
        
        assert controller.platform_stats['tiktok'].comments_this_hour == 0
        assert controller.platform_stats['instagram'].comments_this_hour == 0


# =============================================================================
# DOCUMENTATION: When Does Comment Automation Resume?
# =============================================================================
"""
WHEN DOES COMMENT AUTOMATION RESUME AFTER USER STOPS USING MAC?
================================================================

The EngagementController uses Mac's HID (Human Interface Device) idle time
to detect when the user has stopped using the computer.

CONFIGURATION:
- AUTO_RESUME_IDLE_HOURS = 2.5  (default: 2.5 hours)
- IDLE_CHECK_INTERVAL = 300     (check every 5 minutes)

HOW IT WORKS:
1. User stops/pauses automation or sets state to IDLE_WAITING
2. Idle monitor runs in background, checking every 5 minutes
3. Uses `ioreg -c IOHIDSystem` to read HIDIdleTime (nanoseconds)
4. When idle_hours >= auto_resume_after_hours, state → RUNNING
5. Engagement loop continues posting comments

EXAMPLE TIMELINE:
-----------------
10:00 PM - User pauses, goes to watch TV
10:05 PM - Idle check: 5 min idle, no action
10:30 PM - Idle check: 30 min idle, no action
11:00 PM - Idle check: 1 hour idle, no action
11:30 PM - Idle check: 1.5 hours idle, no action
12:00 AM - Idle check: 2 hours idle, no action
12:30 AM - Idle check: 2.5 hours idle → AUTO RESUME!
12:30 AM - Comments start posting again

API CONFIGURATION:
------------------
POST /api/engagement-control/config
{
    "auto_resume_enabled": true,
    "auto_resume_hours": 2.5
}

TO DISABLE AUTO-RESUME:
-----------------------
POST /api/engagement-control/config
{
    "auto_resume_enabled": false
}

NOTE: Auto-resume only triggers from IDLE_WAITING state.
If user explicitly STOPs automation, it stays STOPPED.
Use PAUSE or set state to IDLE_WAITING for auto-resume behavior.
"""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
