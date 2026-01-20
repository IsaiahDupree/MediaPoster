"""
Smart Scheduling Service (PIPE-006)
====================================
Intelligent post scheduling with:
- 4-hour intervals between posts
- Daylight hours only (6AM-10PM local time)
- Timezone-aware scheduling
- Conflict resolution (skip if slot already filled)
- Integration with PostScheduler

Usage:
    smart_scheduler = SmartScheduler()

    # Schedule posts for the next 7 days
    slots = await smart_scheduler.schedule_approved_posts(days=7)

    # Get available time slots
    available = await smart_scheduler.get_available_slots(days=7)
"""

import asyncio
from datetime import datetime, timedelta, timezone, time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from zoneinfo import ZoneInfo

from database.connection import get_db_context
from database.models import ScheduledPost
from services.event_bus import EventBus, Topics


@dataclass
class TimeSlot:
    """Represents an available time slot for scheduling"""
    datetime: datetime
    is_available: bool
    reason: Optional[str] = None  # Why slot is unavailable (if applicable)


class SmartScheduler:
    """
    Smart Scheduling Service

    Automatically schedules approved content at optimal intervals:
    - Posts every 4 hours during active hours
    - Active hours: 6AM - 10PM (configurable per timezone)
    - Respects existing scheduled posts (no double-booking)
    - Timezone-aware
    """

    def __init__(
        self,
        timezone_name: str = "America/Los_Angeles",
        active_start_hour: int = 6,   # 6 AM
        active_end_hour: int = 22,     # 10 PM
        interval_hours: int = 4,
    ):
        """
        Initialize Smart Scheduler

        Args:
            timezone_name: IANA timezone name (e.g., "America/Los_Angeles", "America/New_York")
            active_start_hour: Start of active posting hours (0-23)
            active_end_hour: End of active posting hours (0-23)
            interval_hours: Hours between posts
        """
        self.timezone = ZoneInfo(timezone_name)
        self.active_start_hour = active_start_hour
        self.active_end_hour = active_end_hour
        self.interval_hours = interval_hours

        # Event bus integration
        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("smart-scheduler")

        logger.info(
            f"🧠 Smart Scheduler initialized | "
            f"Timezone: {timezone_name} | "
            f"Active hours: {active_start_hour:02d}:00-{active_end_hour:02d}:00 | "
            f"Interval: {interval_hours}h"
        )

    def get_next_slot(self, after: datetime) -> datetime:
        """
        Get the next available time slot after the given datetime

        Args:
            after: Datetime to start searching from (UTC)

        Returns:
            Next available slot (UTC)
        """
        # Convert to local timezone
        local_dt = after.astimezone(self.timezone)

        # Round up to next interval
        next_hour = ((local_dt.hour // self.interval_hours) + 1) * self.interval_hours

        # Create candidate slot
        candidate = local_dt.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        ) + timedelta(hours=next_hour)

        # If candidate is before active hours, move to start of active hours
        if candidate.hour < self.active_start_hour:
            candidate = candidate.replace(hour=self.active_start_hour)

        # If candidate is after active hours, move to next day start
        elif candidate.hour >= self.active_end_hour:
            candidate = (candidate + timedelta(days=1)).replace(hour=self.active_start_hour)

        # If candidate is still in the past, move forward
        while candidate <= local_dt:
            candidate += timedelta(hours=self.interval_hours)

            # If we've exceeded active hours, jump to next day
            if candidate.hour >= self.active_end_hour:
                candidate = (candidate + timedelta(days=1)).replace(hour=self.active_start_hour)

        # Convert back to UTC
        return candidate.astimezone(timezone.utc)

    async def get_scheduled_slots(
        self,
        start: datetime,
        end: datetime,
        db: Optional[AsyncSession] = None
    ) -> List[datetime]:
        """
        Get all existing scheduled post times in the given range

        Args:
            start: Start of range (UTC)
            end: End of range (UTC)
            db: Database session (optional)

        Returns:
            List of scheduled datetimes (UTC)
        """
        async def _get_slots(session: AsyncSession):
            result = await session.execute(
                select(ScheduledPost.scheduled_time)
                .where(
                    and_(
                        ScheduledPost.scheduled_time >= start,
                        ScheduledPost.scheduled_time <= end,
                        ScheduledPost.status.in_(['pending', 'publishing', 'retry'])
                    )
                )
                .order_by(ScheduledPost.scheduled_time)
            )
            return [row[0] for row in result.all()]

        if db:
            return await _get_slots(db)
        else:
            async with get_db_context() as session:
                return await _get_slots(session)

    async def get_available_slots(
        self,
        days: int = 7,
        start_from: Optional[datetime] = None
    ) -> List[TimeSlot]:
        """
        Get list of available time slots for the next N days

        Args:
            days: Number of days to look ahead
            start_from: Starting datetime (defaults to now)

        Returns:
            List of TimeSlot objects with availability status
        """
        if start_from is None:
            start_from = datetime.now(timezone.utc)

        end = start_from + timedelta(days=days)

        # Get existing scheduled posts
        existing_slots = await self.get_scheduled_slots(start_from, end)
        existing_set = {self._round_to_nearest_minute(dt) for dt in existing_slots}

        # Generate all possible slots
        slots = []
        current = self.get_next_slot(start_from)

        while current < end:
            # Check if slot is already taken (within 30 minutes)
            is_available = True
            reason = None

            for existing in existing_set:
                time_diff = abs((current - existing).total_seconds())
                if time_diff < 1800:  # 30 minutes
                    is_available = False
                    reason = f"Slot already filled at {existing.strftime('%I:%M %p')}"
                    break

            slots.append(TimeSlot(
                datetime=current,
                is_available=is_available,
                reason=reason
            ))

            # Move to next slot
            current = self.get_next_slot(current + timedelta(seconds=1))

        return slots

    async def schedule_approved_posts(
        self,
        days: int = 7,
        max_posts: Optional[int] = None,
        platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Schedule approved posts into available time slots

        Args:
            days: Number of days to schedule into
            max_posts: Maximum number of posts to schedule (None = unlimited)
            platforms: List of platforms to filter by (None = all platforms)

        Returns:
            List of scheduled post info dictionaries
        """
        async with get_db_context() as db:
            # Get approved but unscheduled posts from approval queue
            # (Assuming approval_queue table exists, otherwise use scheduled_posts with status='approved')
            from database.models import ApprovalQueue

            query = select(ApprovalQueue).where(
                ApprovalQueue.status == 'approved',
                ApprovalQueue.scheduled_time.is_(None)
            )

            if platforms:
                query = query.where(ApprovalQueue.platforms.overlap(platforms))

            if max_posts:
                query = query.limit(max_posts)

            result = await db.execute(query)
            approved_posts = result.scalars().all()

            if not approved_posts:
                logger.info("No approved posts to schedule")
                return []

            # Get available slots
            slots = await self.get_available_slots(days=days)
            available_slots = [s for s in slots if s.is_available]

            if not available_slots:
                logger.warning("No available time slots found")
                return []

            # Schedule posts into slots
            scheduled = []
            for idx, post in enumerate(approved_posts):
                if idx >= len(available_slots):
                    logger.warning(
                        f"Ran out of available slots. Scheduled {idx}/{len(approved_posts)} posts"
                    )
                    break

                slot = available_slots[idx]

                # Update post with scheduled time
                post.scheduled_time = slot.datetime
                post.status = 'scheduled'

                await db.commit()

                scheduled.append({
                    'post_id': str(post.id),
                    'title': post.title,
                    'platforms': post.platforms,
                    'scheduled_time': slot.datetime.isoformat(),
                    'local_time': slot.datetime.astimezone(self.timezone).strftime('%Y-%m-%d %I:%M %p %Z')
                })

                # Emit event
                await self.event_bus.publish(
                    Topics.SCHEDULE_CREATED,
                    {
                        'post_id': str(post.id),
                        'scheduled_time': slot.datetime.isoformat(),
                        'platforms': post.platforms,
                        'auto_scheduled': True
                    }
                )

                logger.info(
                    f"📅 Scheduled post | "
                    f"Title: {post.title[:50]}... | "
                    f"Time: {slot.datetime.astimezone(self.timezone).strftime('%Y-%m-%d %I:%M %p')}"
                )

            return scheduled

    def _round_to_nearest_minute(self, dt: datetime) -> datetime:
        """Round datetime to nearest minute for comparison"""
        return dt.replace(second=0, microsecond=0)

    def get_next_n_slots(self, n: int, start_from: Optional[datetime] = None) -> List[datetime]:
        """
        Get the next N available time slots

        Args:
            n: Number of slots to return
            start_from: Starting datetime (defaults to now)

        Returns:
            List of datetime objects (UTC)
        """
        if start_from is None:
            start_from = datetime.now(timezone.utc)

        slots = []
        current = self.get_next_slot(start_from)

        for _ in range(n):
            slots.append(current)
            current = self.get_next_slot(current + timedelta(seconds=1))

        return slots

    async def get_schedule_preview(self, days: int = 7) -> Dict[str, Any]:
        """
        Get a preview of the schedule for the next N days

        Args:
            days: Number of days to preview

        Returns:
            Dictionary with schedule statistics and preview
        """
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=days)

        # Get all slots
        all_slots = await self.get_available_slots(days=days)
        available_slots = [s for s in all_slots if s.is_available]
        filled_slots = [s for s in all_slots if not s.is_available]

        # Get posts per day
        posts_per_day = {}
        for slot in all_slots:
            day_key = slot.datetime.astimezone(self.timezone).strftime('%Y-%m-%d')
            if day_key not in posts_per_day:
                posts_per_day[day_key] = {'total': 0, 'filled': 0, 'available': 0}

            posts_per_day[day_key]['total'] += 1
            if slot.is_available:
                posts_per_day[day_key]['available'] += 1
            else:
                posts_per_day[day_key]['filled'] += 1

        return {
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat(),
                'days': days,
                'timezone': str(self.timezone)
            },
            'slots': {
                'total': len(all_slots),
                'available': len(available_slots),
                'filled': len(filled_slots),
                'utilization_percent': (len(filled_slots) / len(all_slots) * 100) if all_slots else 0
            },
            'schedule': {
                'posts_per_day': len(all_slots) // days if days > 0 else 0,
                'interval_hours': self.interval_hours,
                'active_hours': f"{self.active_start_hour:02d}:00-{self.active_end_hour:02d}:00"
            },
            'daily_breakdown': posts_per_day,
            'next_available_slots': [
                {
                    'datetime_utc': s.datetime.isoformat(),
                    'datetime_local': s.datetime.astimezone(self.timezone).strftime('%Y-%m-%d %I:%M %p %Z')
                }
                for s in available_slots[:10]  # Next 10 available slots
            ]
        }


# Singleton instance
_smart_scheduler: Optional[SmartScheduler] = None


def get_smart_scheduler() -> SmartScheduler:
    """Get singleton instance of SmartScheduler"""
    global _smart_scheduler
    if _smart_scheduler is None:
        _smart_scheduler = SmartScheduler()
    return _smart_scheduler
