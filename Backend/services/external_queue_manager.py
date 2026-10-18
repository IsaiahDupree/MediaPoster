"""
External Queue Manager
======================
Intelligent queue management for external video submissions.

Handles:
- Rate limiting per account/platform
- Automatic slot allocation to avoid overwhelming
- Consistent posting schedule maintenance
- Conflict resolution with existing scheduled posts

When external servers submit videos, this manager:
1. Analyzes current schedule for target account/platform
2. Finds optimal time slots that maintain healthy spacing
3. Respects platform rate limits
4. Distributes posts evenly across available slots
"""

import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger
from sqlalchemy import create_engine, text
from zoneinfo import ZoneInfo

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


@dataclass
class PlatformConfig:
    """Configuration for platform posting limits"""
    name: str
    min_interval_minutes: int  # Minimum time between posts
    max_daily_posts: int       # Maximum posts per day per account
    active_start_hour: int = 6   # Start of active hours (local)
    active_end_hour: int = 22    # End of active hours (local)
    preferred_interval_minutes: int = 240  # Preferred spacing (4 hours)


@dataclass
class ScheduledSlot:
    """Represents an allocated time slot"""
    datetime: datetime
    platform: str
    account_id: str
    is_new: bool = True  # True if newly allocated, False if existing


@dataclass
class QueueAnalysis:
    """Analysis of current queue state for an account/platform"""
    platform: str
    account_id: str
    posts_today: int
    posts_this_week: int
    next_available_slot: datetime
    daily_capacity_remaining: int
    existing_slots: List[datetime] = field(default_factory=list)
    recommended_slots: List[datetime] = field(default_factory=list)


# Platform configurations with safe posting limits
PLATFORM_CONFIGS = {
    "tiktok": PlatformConfig(
        name="tiktok",
        min_interval_minutes=30,      # At least 30 min between posts
        max_daily_posts=8,            # Max 8 posts per day
        preferred_interval_minutes=180  # Prefer 3 hours apart
    ),
    "instagram": PlatformConfig(
        name="instagram",
        min_interval_minutes=60,      # At least 1 hour between posts
        max_daily_posts=5,            # Max 5 posts per day
        preferred_interval_minutes=240  # Prefer 4 hours apart
    ),
    "youtube": PlatformConfig(
        name="youtube",
        min_interval_minutes=120,     # At least 2 hours between posts
        max_daily_posts=3,            # Max 3 posts per day
        preferred_interval_minutes=480  # Prefer 8 hours apart
    ),
    "twitter": PlatformConfig(
        name="twitter",
        min_interval_minutes=15,      # At least 15 min between posts
        max_daily_posts=20,           # Max 20 posts per day
        preferred_interval_minutes=60   # Prefer 1 hour apart
    ),
    "threads": PlatformConfig(
        name="threads",
        min_interval_minutes=30,
        max_daily_posts=10,
        preferred_interval_minutes=120
    ),
    "linkedin": PlatformConfig(
        name="linkedin",
        min_interval_minutes=120,
        max_daily_posts=3,
        preferred_interval_minutes=480
    ),
    "pinterest": PlatformConfig(
        name="pinterest",
        min_interval_minutes=30,
        max_daily_posts=15,
        preferred_interval_minutes=60
    ),
    "facebook": PlatformConfig(
        name="facebook",
        min_interval_minutes=60,
        max_daily_posts=5,
        preferred_interval_minutes=240
    ),
    "bluesky": PlatformConfig(
        name="bluesky",
        min_interval_minutes=15,
        max_daily_posts=20,
        preferred_interval_minutes=60
    ),
}


class ExternalQueueManager:
    """
    Manages intelligent queue allocation for external submissions.
    
    Ensures consistent posting schedules by:
    - Analyzing existing scheduled posts per account
    - Allocating new posts to optimal time slots
    - Respecting platform rate limits
    - Maintaining healthy spacing between posts
    """
    
    def __init__(self, timezone_name: str = "America/New_York"):
        self.timezone = ZoneInfo(timezone_name)
        self._engine = None
        logger.info(f"📊 External Queue Manager initialized | Timezone: {timezone_name}")
    
    def get_engine(self):
        if self._engine is None:
            self._engine = create_engine(
                DATABASE_URL,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
            )
        return self._engine
    
    def get_platform_config(self, platform: str) -> PlatformConfig:
        """Get configuration for a platform, with defaults for unknown platforms"""
        return PLATFORM_CONFIGS.get(platform.lower(), PlatformConfig(
            name=platform,
            min_interval_minutes=60,
            max_daily_posts=5,
            preferred_interval_minutes=240
        ))
    
    def analyze_queue(
        self,
        platform: str,
        account_id: str,
        days_ahead: int = 7
    ) -> QueueAnalysis:
        """
        Analyze current queue state for an account/platform.
        
        Returns information about:
        - How many posts are scheduled today/this week
        - When the next available slot is
        - Remaining daily capacity
        - Recommended posting slots
        """
        config = self.get_platform_config(platform)
        engine = self.get_engine()
        now = datetime.now(self.timezone)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        week_end = today_start + timedelta(days=7)
        
        with engine.connect() as conn:
            # Get posts scheduled for today
            today_posts = conn.execute(text("""
                SELECT scheduled_time FROM scheduled_posts
                WHERE platform = :platform 
                AND blotato_account_id = :account_id
                AND scheduled_time >= :today_start
                AND scheduled_time < :today_end
                AND status IN ('scheduled', 'pending', 'publishing')
                ORDER BY scheduled_time
            """), {
                "platform": platform,
                "account_id": account_id,
                "today_start": today_start,
                "today_end": today_end
            }).fetchall()
            
            # Get posts for the week
            week_posts = conn.execute(text("""
                SELECT scheduled_time FROM scheduled_posts
                WHERE platform = :platform 
                AND blotato_account_id = :account_id
                AND scheduled_time >= :today_start
                AND scheduled_time < :week_end
                AND status IN ('scheduled', 'pending', 'publishing')
                ORDER BY scheduled_time
            """), {
                "platform": platform,
                "account_id": account_id,
                "today_start": today_start,
                "week_end": week_end
            }).fetchall()
        
        existing_slots = [row[0] for row in week_posts]
        posts_today = len(today_posts)
        posts_this_week = len(week_posts)
        
        # Calculate next available slot
        next_slot = self._find_next_available_slot(
            existing_slots, config, now, days_ahead
        )
        
        # Generate recommended slots for the next N days
        recommended = self._generate_recommended_slots(
            existing_slots, config, now, days_ahead
        )
        
        return QueueAnalysis(
            platform=platform,
            account_id=account_id,
            posts_today=posts_today,
            posts_this_week=posts_this_week,
            next_available_slot=next_slot,
            daily_capacity_remaining=max(0, config.max_daily_posts - posts_today),
            existing_slots=existing_slots,
            recommended_slots=recommended
        )
    
    def _find_next_available_slot(
        self,
        existing_slots: List[datetime],
        config: PlatformConfig,
        after: datetime,
        days_ahead: int = 7
    ) -> datetime:
        """Find the next available time slot that respects spacing rules"""
        # Start from next hour boundary
        candidate = after.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        end_search = after + timedelta(days=days_ahead)
        
        while candidate < end_search:
            # Check if within active hours
            local_hour = candidate.astimezone(self.timezone).hour
            if local_hour < config.active_start_hour:
                # Move to start of active hours
                candidate = candidate.replace(hour=config.active_start_hour)
                continue
            elif local_hour >= config.active_end_hour:
                # Move to next day's start
                candidate = (candidate + timedelta(days=1)).replace(
                    hour=config.active_start_hour, minute=0, second=0, microsecond=0
                )
                continue
            
            # Check spacing from existing posts
            is_valid = True
            for existing in existing_slots:
                if existing.tzinfo is None:
                    existing = existing.replace(tzinfo=timezone.utc)
                time_diff = abs((candidate - existing).total_seconds() / 60)
                if time_diff < config.min_interval_minutes:
                    is_valid = False
                    break
            
            if is_valid:
                return candidate
            
            # Move forward by minimum interval
            candidate += timedelta(minutes=config.min_interval_minutes)
        
        # Fallback: return 1 day from now
        return after + timedelta(days=1)
    
    def _generate_recommended_slots(
        self,
        existing_slots: List[datetime],
        config: PlatformConfig,
        start: datetime,
        days: int = 7
    ) -> List[datetime]:
        """Generate a list of recommended posting slots"""
        slots = []
        current = start
        end = start + timedelta(days=days)
        
        while current < end and len(slots) < days * config.max_daily_posts:
            slot = self._find_next_available_slot(
                existing_slots + slots,  # Include already recommended slots
                config,
                current,
                days
            )
            
            if slot >= end:
                break
            
            # Check daily limit
            slot_date = slot.astimezone(self.timezone).date()
            slots_on_date = sum(
                1 for s in (existing_slots + slots)
                if (s.astimezone(self.timezone) if s.tzinfo else s.replace(tzinfo=timezone.utc).astimezone(self.timezone)).date() == slot_date
            )
            
            if slots_on_date < config.max_daily_posts:
                slots.append(slot)
                current = slot + timedelta(minutes=config.preferred_interval_minutes)
            else:
                # Move to next day
                next_day = slot.astimezone(self.timezone).replace(
                    hour=config.active_start_hour, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
                current = next_day
        
        return slots
    
    def allocate_slots(
        self,
        videos: List[Dict[str, Any]],
        platform: str,
        account_id: str,
        start_after: Optional[datetime] = None,
        respect_requested_times: bool = False
    ) -> List[Tuple[Dict[str, Any], datetime]]:
        """
        Allocate optimal time slots for a list of videos.
        
        Args:
            videos: List of video dicts (each should have 'video_url', optionally 'requested_time')
            platform: Target platform
            account_id: Target account ID
            start_after: Earliest time to schedule (default: now)
            respect_requested_times: If True, try to honor requested times; if False, optimize spacing
        
        Returns:
            List of (video, allocated_datetime) tuples
        """
        if start_after is None:
            start_after = datetime.now(self.timezone)
        
        config = self.get_platform_config(platform)
        analysis = self.analyze_queue(platform, account_id)
        
        allocated = []
        used_slots = list(analysis.existing_slots)
        
        for video in videos:
            if respect_requested_times and video.get('requested_time'):
                # Try to honor requested time
                requested = datetime.fromisoformat(video['requested_time'].replace('Z', '+00:00'))
                
                # Check if it's valid (respects spacing)
                is_valid = all(
                    abs((requested - existing).total_seconds() / 60) >= config.min_interval_minutes
                    for existing in used_slots
                    if existing.tzinfo is None or (existing.tzinfo and True)
                )
                
                if is_valid:
                    allocated.append((video, requested))
                    used_slots.append(requested)
                    continue
            
            # Find optimal slot
            slot = self._find_next_available_slot(
                used_slots,
                config,
                start_after if not allocated else allocated[-1][1],
                days_ahead=14
            )
            
            allocated.append((video, slot))
            used_slots.append(slot)
            
            logger.debug(f"Allocated slot {slot} for video to {platform}/{account_id}")
        
        return allocated
    
    def get_posting_summary(
        self,
        platform: Optional[str] = None,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of posting activity and capacity.
        
        Returns info useful for external systems to make decisions:
        - Current queue depth
        - Available capacity per day
        - Recommended next posting times
        """
        engine = self.get_engine()
        now = datetime.now(self.timezone)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today_start + timedelta(days=7)
        
        where_clauses = ["scheduled_time >= :today_start", "scheduled_time < :week_end"]
        params = {"today_start": today_start, "week_end": week_end}
        
        if platform:
            where_clauses.append("platform = :platform")
            params["platform"] = platform
        if account_id:
            where_clauses.append("blotato_account_id = :account_id")
            params["account_id"] = account_id
        
        with engine.connect() as conn:
            # Get scheduled posts grouped by platform/account/day
            result = conn.execute(text(f"""
                SELECT 
                    platform,
                    blotato_account_id,
                    DATE(scheduled_time) as post_date,
                    COUNT(*) as post_count
                FROM scheduled_posts
                WHERE {' AND '.join(where_clauses)}
                AND status IN ('scheduled', 'pending', 'publishing')
                GROUP BY platform, blotato_account_id, DATE(scheduled_time)
                ORDER BY platform, blotato_account_id, post_date
            """), params).fetchall()
        
        # Build summary
        summary = {
            "generated_at": now.isoformat(),
            "timezone": str(self.timezone),
            "accounts": {}
        }
        
        for row in result:
            plat, acct, date, count = row
            if plat not in summary["accounts"]:
                summary["accounts"][plat] = {}
            if acct not in summary["accounts"][plat]:
                config = self.get_platform_config(plat)
                summary["accounts"][plat][acct] = {
                    "daily_limit": config.max_daily_posts,
                    "min_interval_minutes": config.min_interval_minutes,
                    "schedule": {}
                }
            
            date_str = date.isoformat() if hasattr(date, 'isoformat') else str(date)
            config = self.get_platform_config(plat)
            summary["accounts"][plat][acct]["schedule"][date_str] = {
                "scheduled": count,
                "remaining_capacity": max(0, config.max_daily_posts - count)
            }
        
        return summary


# Global instance
_queue_manager: Optional[ExternalQueueManager] = None


def get_queue_manager() -> ExternalQueueManager:
    """Get or create the global queue manager instance"""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = ExternalQueueManager()
    return _queue_manager
