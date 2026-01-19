"""
Metrics Scheduler Service
Automatically syncs metrics from social platforms on configurable schedules.
Supports different check-back periods per platform.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class SyncInterval(str, Enum):
    """Supported sync intervals"""
    HOURLY = "hourly"           # Every hour
    EVERY_4_HOURS = "4h"        # Every 4 hours
    EVERY_6_HOURS = "6h"        # Every 6 hours
    EVERY_12_HOURS = "12h"      # Every 12 hours
    DAILY = "daily"             # Once per day
    WEEKLY = "weekly"           # Once per week


# Interval to seconds mapping
INTERVAL_SECONDS = {
    SyncInterval.HOURLY: 3600,
    SyncInterval.EVERY_4_HOURS: 4 * 3600,
    SyncInterval.EVERY_6_HOURS: 6 * 3600,
    SyncInterval.EVERY_12_HOURS: 12 * 3600,
    SyncInterval.DAILY: 24 * 3600,
    SyncInterval.WEEKLY: 7 * 24 * 3600,
}


@dataclass
class PlatformSyncConfig:
    """Configuration for syncing a specific platform"""
    platform: str
    enabled: bool = True
    interval: SyncInterval = SyncInterval.EVERY_6_HOURS
    last_sync: Optional[datetime] = None
    next_sync: Optional[datetime] = None
    sync_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class MetricsSyncScheduler:
    """Manages scheduled metrics syncing across platforms"""

    configs: Dict[str, PlatformSyncConfig] = field(default_factory=dict)
    is_running: bool = False
    sync_history: List[Dict[str, Any]] = field(default_factory=list)
    _sleep_service = None
    _scheduled_wake_triggers: Dict[str, str] = field(default_factory=dict)  # platform -> wake_trigger_id

    def __post_init__(self):
        # Initialize default configs for all platforms
        default_platforms = [
            ("instagram", SyncInterval.EVERY_4_HOURS),
            ("tiktok", SyncInterval.EVERY_4_HOURS),
            ("youtube", SyncInterval.EVERY_6_HOURS),
            ("facebook", SyncInterval.EVERY_6_HOURS),
            ("linkedin", SyncInterval.EVERY_12_HOURS),
            ("twitter", SyncInterval.EVERY_4_HOURS),
            ("threads", SyncInterval.EVERY_6_HOURS),
            ("bluesky", SyncInterval.EVERY_6_HOURS),
            ("pinterest", SyncInterval.DAILY),
        ]

        for platform, interval in default_platforms:
            if platform not in self.configs:
                self.configs[platform] = PlatformSyncConfig(
                    platform=platform,
                    interval=interval,
                    next_sync=datetime.now(timezone.utc),
                )

    @property
    def sleep_service(self):
        """Lazy load sleep mode service"""
        if self._sleep_service is None:
            try:
                from services.sleep_mode_service import SleepModeService
                self._sleep_service = SleepModeService.get_instance()
            except Exception as e:
                logger.warning(f"Sleep mode service not available: {e}")
                self._sleep_service = None
        return self._sleep_service
    
    def set_interval(self, platform: str, interval: SyncInterval) -> bool:
        """Update sync interval for a platform"""
        if platform in self.configs:
            self.configs[platform].interval = interval
            self.configs[platform].next_sync = datetime.now(timezone.utc)
            return True
        return False
    
    def enable_platform(self, platform: str, enabled: bool = True) -> bool:
        """Enable or disable syncing for a platform"""
        if platform in self.configs:
            self.configs[platform].enabled = enabled
            return True
        return False
    
    def get_next_sync_time(self, platform: str) -> Optional[datetime]:
        """Get next scheduled sync time for a platform"""
        if platform in self.configs:
            return self.configs[platform].next_sync
        return None
    
    def get_all_configs(self) -> Dict[str, Dict]:
        """Get all platform configurations"""
        return {
            platform: {
                "enabled": config.enabled,
                "interval": config.interval.value,
                "last_sync": config.last_sync.isoformat() if config.last_sync else None,
                "next_sync": config.next_sync.isoformat() if config.next_sync else None,
                "sync_count": config.sync_count,
                "error_count": config.error_count,
                "last_error": config.last_error,
            }
            for platform, config in self.configs.items()
        }
    
    def record_sync(self, platform: str, success: bool, error: Optional[str] = None, posts_synced: int = 0):
        """Record a sync attempt"""
        if platform in self.configs:
            config = self.configs[platform]
            config.last_sync = datetime.now(timezone.utc)
            config.next_sync = datetime.now(timezone.utc) + timedelta(
                seconds=INTERVAL_SECONDS[config.interval]
            )
            config.sync_count += 1

            if not success:
                config.error_count += 1
                config.last_error = error
            else:
                config.last_error = None

            # Add to history
            self.sync_history.append({
                "platform": platform,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": success,
                "error": error,
                "posts_synced": posts_synced,
            })

            # Keep only last 100 entries
            if len(self.sync_history) > 100:
                self.sync_history = self.sync_history[-100:]

            # Schedule wake trigger for next checkback (SLEEP-005)
            self._schedule_wake_for_next_checkback(platform)
    
    def get_due_platforms(self) -> List[str]:
        """Get platforms that are due for syncing"""
        now = datetime.now(timezone.utc)
        return [
            platform
            for platform, config in self.configs.items()
            if config.enabled and config.next_sync and config.next_sync <= now
        ]
    
    def get_sync_history(self, platform: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get sync history, optionally filtered by platform"""
        history = self.sync_history
        if platform:
            history = [h for h in history if h["platform"] == platform]
        return history[-limit:]

    def _schedule_wake_for_next_checkback(self, platform: str) -> None:
        """
        Schedule wake trigger for next metrics checkback (SLEEP-005)

        Args:
            platform: Platform to schedule wake for
        """
        if not self.sleep_service or platform not in self.configs:
            return

        from services.sleep_mode_service import WakeTriggerType

        config = self.configs[platform]

        # Cancel previous wake trigger if exists
        if platform in self._scheduled_wake_triggers:
            old_trigger_id = self._scheduled_wake_triggers[platform]
            self.sleep_service.cancel_wake(old_trigger_id)
            del self._scheduled_wake_triggers[platform]

        # Only schedule if next_sync is in the future
        if not config.next_sync or config.next_sync <= datetime.now(timezone.utc):
            return

        try:
            # Schedule wake trigger for next checkback
            trigger_id = self.sleep_service.schedule_wake(
                wake_time=config.next_sync,
                trigger_type=WakeTriggerType.CHECKBACK_PERIOD,
                metadata={
                    "platform": platform,
                    "interval": config.interval.value,
                    "checkback_type": "metrics_sync"
                }
            )

            # Track the trigger
            self._scheduled_wake_triggers[platform] = trigger_id

            logger.debug(
                f"⏰ Scheduled wake for {platform} metrics checkback at "
                f"{config.next_sync.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )

        except Exception as e:
            logger.warning(f"Failed to schedule wake for {platform} checkback: {e}")


# Global scheduler instance
_scheduler: Optional[MetricsSyncScheduler] = None


def get_scheduler() -> MetricsSyncScheduler:
    """Get the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = MetricsSyncScheduler()
    return _scheduler


async def run_scheduled_sync(db_session=None):
    """
    Run scheduled sync for all due platforms.
    This should be called periodically (e.g., every minute) by a background task.
    """
    from api.content_growth import fetch_platform_metrics, metrics_history
    
    scheduler = get_scheduler()
    due_platforms = scheduler.get_due_platforms()
    
    for platform in due_platforms:
        try:
            logger.info(f"Starting scheduled sync for {platform}")
            
            # In production, fetch posts for this platform from database
            # and sync metrics for each
            posts_synced = 0
            
            # Simulate syncing (in production, iterate over actual posts)
            # This would query scheduled_posts table for this platform
            # and fetch current metrics for each
            
            scheduler.record_sync(platform, success=True, posts_synced=posts_synced)
            logger.info(f"Completed sync for {platform}: {posts_synced} posts")
            
        except Exception as e:
            logger.error(f"Failed to sync {platform}: {e}")
            scheduler.record_sync(platform, success=False, error=str(e))


async def start_scheduler_loop():
    """Start the background scheduler loop"""
    scheduler = get_scheduler()
    scheduler.is_running = True
    
    logger.info("Starting metrics sync scheduler")
    
    while scheduler.is_running:
        try:
            await run_scheduled_sync()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        
        # Check every minute
        await asyncio.sleep(60)


def stop_scheduler():
    """Stop the scheduler loop"""
    scheduler = get_scheduler()
    scheduler.is_running = False
    logger.info("Stopping metrics sync scheduler")
