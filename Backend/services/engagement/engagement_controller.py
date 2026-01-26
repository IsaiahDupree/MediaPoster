"""
Engagement Controller
=====================
Controls automated engagement with start/stop, rate limiting, and idle detection.

Features:
- 30 comments per platform per hour
- Start/Stop control via API
- Auto-resume after 2-3 hours of Mac idle time
- Real-time status updates

Usage:
    controller = EngagementController.get_instance()
    await controller.start()
    await controller.stop()
"""
import asyncio
import time
import random
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class EngagementState(Enum):
    """Engagement automation states."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    IDLE_WAITING = "idle_waiting"  # Waiting for idle period to resume


@dataclass
class PlatformStats:
    """Stats for a single platform."""
    platform: str
    comments_this_hour: int = 0
    comments_today: int = 0
    last_comment_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    is_enabled: bool = True


@dataclass
class EngagementStatus:
    """Current engagement status."""
    state: EngagementState
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    total_comments_today: int
    platforms: Dict[str, PlatformStats]
    next_comment_at: Optional[datetime]
    idle_minutes: float
    auto_resume_enabled: bool
    auto_resume_after_hours: float
    comments_per_hour_limit: int
    
    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "total_comments_today": self.total_comments_today,
            "platforms": {
                name: {
                    "comments_this_hour": p.comments_this_hour,
                    "comments_today": p.comments_today,
                    "last_comment_at": p.last_comment_at.isoformat() if p.last_comment_at else None,
                    "is_enabled": p.is_enabled,
                    "errors_count": len(p.errors),
                }
                for name, p in self.platforms.items()
            },
            "next_comment_at": self.next_comment_at.isoformat() if self.next_comment_at else None,
            "idle_minutes": round(self.idle_minutes, 1),
            "auto_resume_enabled": self.auto_resume_enabled,
            "auto_resume_after_hours": self.auto_resume_after_hours,
            "comments_per_hour_limit": self.comments_per_hour_limit,
        }


class EngagementController:
    """
    Controls engagement automation with rate limiting and idle detection.
    
    Rate: 30 comments per platform per hour
    Auto-resume: After 2-3 hours of Mac idle time
    """
    
    _instance: Optional["EngagementController"] = None
    
    # Configuration
    COMMENTS_PER_HOUR_PER_PLATFORM = 30
    MIN_DELAY_BETWEEN_COMMENTS = 60  # 1 minute minimum
    MAX_DELAY_BETWEEN_COMMENTS = 180  # 3 minutes maximum
    AUTO_RESUME_IDLE_HOURS = 0.25  # Resume after 15 minutes idle
    IDLE_CHECK_INTERVAL = 60  # Check idle every 1 minute
    
    PLATFORMS = ['threads', 'instagram', 'tiktok', 'twitter']
    
    def __init__(self):
        self.state = EngagementState.STOPPED
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        
        # Platform stats
        self.platform_stats: Dict[str, PlatformStats] = {
            p: PlatformStats(platform=p) for p in self.PLATFORMS
        }
        
        # Tasks
        self._engagement_task: Optional[asyncio.Task] = None
        self._idle_monitor_task: Optional[asyncio.Task] = None
        
        # Control
        self._should_stop = False
        self._next_comment_at: Optional[datetime] = None
        
        # Auto-resume settings
        self.auto_resume_enabled = True
        self.auto_resume_after_hours = self.AUTO_RESUME_IDLE_HOURS
        
        # Event callbacks
        self._on_comment_posted: List[callable] = []
        self._on_state_changed: List[callable] = []
    
    @classmethod
    def get_instance(cls) -> "EngagementController":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton (for testing)."""
        if cls._instance:
            asyncio.create_task(cls._instance.stop())
        cls._instance = None
    
    # =========================================================================
    # MAC IDLE DETECTION
    # =========================================================================
    
    def get_mac_idle_time(self) -> float:
        """
        Get Mac idle time in seconds using ioreg.
        
        Returns:
            Idle time in seconds, or 0 if detection fails
        """
        try:
            result = subprocess.run(
                ['ioreg', '-c', 'IOHIDSystem'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            for line in result.stdout.split('\n'):
                if 'HIDIdleTime' in line:
                    # Extract the number (in nanoseconds)
                    parts = line.split('=')
                    if len(parts) >= 2:
                        idle_ns = int(parts[-1].strip())
                        return idle_ns / 1_000_000_000  # Convert to seconds
            
            return 0
        except Exception as e:
            logger.warning(f"Failed to get idle time: {e}")
            return 0
    
    def get_idle_minutes(self) -> float:
        """Get idle time in minutes."""
        return self.get_mac_idle_time() / 60
    
    def get_idle_hours(self) -> float:
        """Get idle time in hours."""
        return self.get_mac_idle_time() / 3600
    
    # =========================================================================
    # RATE LIMITING
    # =========================================================================
    
    def _reset_hourly_counts(self):
        """Reset hourly comment counts (called at top of each hour)."""
        for stats in self.platform_stats.values():
            stats.comments_this_hour = 0
    
    def _can_post_on_platform(self, platform: str) -> tuple[bool, str]:
        """
        Check if we can post on a platform.
        
        Returns:
            (can_post, reason)
        """
        stats = self.platform_stats.get(platform)
        if not stats:
            return False, f"Unknown platform: {platform}"
        
        if not stats.is_enabled:
            return False, "Platform is disabled"
        
        if stats.comments_this_hour >= self.COMMENTS_PER_HOUR_PER_PLATFORM:
            return False, f"Hourly limit reached ({self.COMMENTS_PER_HOUR_PER_PLATFORM}/hr)"
        
        return True, "OK"
    
    def _get_next_delay(self) -> int:
        """Get random delay before next comment."""
        return random.randint(
            self.MIN_DELAY_BETWEEN_COMMENTS,
            self.MAX_DELAY_BETWEEN_COMMENTS
        )
    
    # =========================================================================
    # CONTROL METHODS
    # =========================================================================
    
    async def start(self) -> dict:
        """
        Start engagement automation.
        
        Returns:
            Status dict
        """
        if self.state == EngagementState.RUNNING:
            return {"success": False, "error": "Already running"}
        
        logger.info("🚀 Starting engagement automation...")
        
        self.state = EngagementState.RUNNING
        self.started_at = datetime.now(timezone.utc)
        self.stopped_at = None
        self._should_stop = False
        
        # Start engagement loop
        self._engagement_task = asyncio.create_task(self._engagement_loop())
        
        # Start idle monitor (for auto-resume)
        if self.auto_resume_enabled:
            self._idle_monitor_task = asyncio.create_task(self._idle_monitor_loop())
        
        # Notify state change
        await self._notify_state_changed()
        
        logger.success("✅ Engagement automation started")
        
        return {
            "success": True,
            "state": self.state.value,
            "started_at": self.started_at.isoformat()
        }
    
    async def stop(self) -> dict:
        """
        Stop engagement automation.
        
        Returns:
            Status dict
        """
        if self.state == EngagementState.STOPPED:
            return {"success": False, "error": "Already stopped"}
        
        logger.info("🛑 Stopping engagement automation...")
        
        self._should_stop = True
        self.state = EngagementState.STOPPED
        self.stopped_at = datetime.now(timezone.utc)
        
        # Cancel tasks
        if self._engagement_task:
            self._engagement_task.cancel()
            try:
                await self._engagement_task
            except asyncio.CancelledError:
                pass
        
        if self._idle_monitor_task:
            self._idle_monitor_task.cancel()
            try:
                await self._idle_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Notify state change
        await self._notify_state_changed()
        
        logger.success("✅ Engagement automation stopped")
        
        return {
            "success": True,
            "state": self.state.value,
            "stopped_at": self.stopped_at.isoformat()
        }
    
    async def pause(self) -> dict:
        """Pause engagement (can resume later)."""
        if self.state != EngagementState.RUNNING:
            return {"success": False, "error": "Not running"}
        
        self.state = EngagementState.PAUSED
        await self._notify_state_changed()
        
        return {"success": True, "state": self.state.value}
    
    async def resume(self) -> dict:
        """Resume paused engagement."""
        if self.state != EngagementState.PAUSED:
            return {"success": False, "error": "Not paused"}
        
        self.state = EngagementState.RUNNING
        await self._notify_state_changed()
        
        return {"success": True, "state": self.state.value}
    
    def enable_platform(self, platform: str, enabled: bool = True):
        """Enable or disable a platform."""
        if platform in self.platform_stats:
            self.platform_stats[platform].is_enabled = enabled
    
    def set_auto_resume(self, enabled: bool, hours: float = 2.5):
        """Configure auto-resume settings."""
        self.auto_resume_enabled = enabled
        self.auto_resume_after_hours = hours
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    def get_status(self) -> EngagementStatus:
        """Get current engagement status."""
        total_today = sum(s.comments_today for s in self.platform_stats.values())
        
        return EngagementStatus(
            state=self.state,
            started_at=self.started_at,
            stopped_at=self.stopped_at,
            total_comments_today=total_today,
            platforms=self.platform_stats,
            next_comment_at=self._next_comment_at,
            idle_minutes=self.get_idle_minutes(),
            auto_resume_enabled=self.auto_resume_enabled,
            auto_resume_after_hours=self.auto_resume_after_hours,
            comments_per_hour_limit=self.COMMENTS_PER_HOUR_PER_PLATFORM,
        )
    
    # =========================================================================
    # MAIN LOOPS
    # =========================================================================
    
    async def _engagement_loop(self):
        """Main engagement loop - posts comments with rate limiting."""
        logger.info("📢 Engagement loop started")
        
        current_hour = datetime.now().hour
        
        while not self._should_stop:
            try:
                # Check for new hour (reset counts)
                now = datetime.now()
                if now.hour != current_hour:
                    self._reset_hourly_counts()
                    current_hour = now.hour
                    logger.info(f"⏰ New hour ({current_hour}:00) - Reset hourly counts")
                
                # Skip if paused
                if self.state == EngagementState.PAUSED:
                    await asyncio.sleep(10)
                    continue
                
                # Find a platform that can accept comments
                platform = self._select_next_platform()
                
                if platform:
                    await self._post_comment(platform)
                    
                    # Calculate next comment time
                    delay = self._get_next_delay()
                    self._next_comment_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                    
                    logger.info(f"⏳ Next comment in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    # All platforms at limit, wait and check again
                    logger.info("⏸️ All platforms at hourly limit, waiting...")
                    await asyncio.sleep(60)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Engagement loop error: {e}")
                await asyncio.sleep(30)
        
        logger.info("📢 Engagement loop stopped")
    
    async def _idle_monitor_loop(self):
        """Monitor Mac idle time for auto-resume."""
        logger.info("👀 Idle monitor started")
        
        while not self._should_stop:
            try:
                await asyncio.sleep(self.IDLE_CHECK_INTERVAL)
                
                idle_hours = self.get_idle_hours()
                logger.debug(f"Mac idle time: {idle_hours:.2f} hours")
                
                # Auto-resume after idle period
                if self.state == EngagementState.IDLE_WAITING:
                    if idle_hours >= self.auto_resume_after_hours:
                        logger.info(f"🔄 Auto-resuming after {idle_hours:.1f}h idle")
                        self.state = EngagementState.RUNNING
                        await self._notify_state_changed()
                
                # Enter idle waiting if user returns (idle resets)
                if self.state == EngagementState.RUNNING and idle_hours < 0.1:
                    # User is active, could pause if desired
                    pass
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Idle monitor error: {e}")
        
        logger.info("👀 Idle monitor stopped")
    
    def _select_next_platform(self) -> Optional[str]:
        """Select next platform to post on (round-robin with capacity check)."""
        # Sort by fewest comments this hour
        available = []
        for platform, stats in self.platform_stats.items():
            can_post, _ = self._can_post_on_platform(platform)
            if can_post:
                available.append((platform, stats.comments_this_hour))
        
        if not available:
            return None
        
        # Pick the one with fewest comments (balance across platforms)
        available.sort(key=lambda x: x[1])
        return available[0][0]
    
    async def _post_comment(self, platform: str):
        """Post a single comment on a platform."""
        logger.info(f"💬 Posting comment on {platform}...")
        
        stats = self.platform_stats[platform]
        
        try:
            # Note: Safari session check disabled - let engagement modules handle login
            # The engagement modules already verify login state internally
            logger.debug(f"Starting engagement on {platform} (session check delegated to module)")
            
            # Import and run engagement
            from services.engagement.engagement_runner import EngagementRunner
            
            runner = EngagementRunner()
            result = await runner.run_single(platform)
            
            if result.get('posted'):
                stats.comments_this_hour += 1
                stats.comments_today += 1
                stats.last_comment_at = datetime.now(timezone.utc)
                
                logger.success(f"✅ Posted on {platform}: {result.get('comment', '')[:50]}...")
                
                # Notify callbacks
                for callback in self._on_comment_posted:
                    try:
                        await callback(platform, result)
                    except:
                        pass
            else:
                error = result.get('error', 'Unknown error')
                stats.errors.append(error)
                logger.warning(f"⚠️ Failed on {platform}: {error}")
                
        except Exception as e:
            stats.errors.append(str(e))
            logger.error(f"❌ Error posting on {platform}: {e}")
    
    async def _notify_state_changed(self):
        """Notify state change callbacks."""
        for callback in self._on_state_changed:
            try:
                await callback(self.state)
            except:
                pass
    
    # =========================================================================
    # CALLBACKS
    # =========================================================================
    
    def on_comment_posted(self, callback: callable):
        """Register callback for when comment is posted."""
        self._on_comment_posted.append(callback)
    
    def on_state_changed(self, callback: callable):
        """Register callback for state changes."""
        self._on_state_changed.append(callback)


# Singleton getter
def get_engagement_controller() -> EngagementController:
    return EngagementController.get_instance()
