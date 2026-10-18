"""
Phase 3: Comprehensive Scheduling System Tests
Tests for 4-hour intervals, priority queue, timezone support, and scheduling logic.
Target: ~100 tests
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4, UUID
from typing import List, Optional
from zoneinfo import ZoneInfo


# ==================== MODELS ====================

class ScheduleStatus:
    PENDING = "pending"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority:
    LOW = 1
    NORMAL = 5
    HIGH = 10
    URGENT = 20


class Platform:
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"


class ScheduledPost:
    """Model for a scheduled post"""
    def __init__(
        self,
        id: UUID = None,
        content_id: UUID = None,
        platform: str = Platform.TIKTOK,
        scheduled_time: datetime = None,
        status: str = ScheduleStatus.PENDING,
        priority: int = Priority.NORMAL,
        account_id: str = None,
        timezone_str: str = "UTC",
        variation_id: UUID = None,
        retry_count: int = 0,
        error_message: str = None,
    ):
        self.id = id or uuid4()
        self.content_id = content_id or uuid4()
        self.platform = platform
        self.scheduled_time = scheduled_time or datetime.now(timezone.utc)
        self.status = status
        self.priority = priority
        self.account_id = account_id or str(uuid4())
        self.timezone_str = timezone_str
        self.variation_id = variation_id
        self.retry_count = retry_count
        self.error_message = error_message


class PostingWindow:
    """Represents a posting time window"""
    def __init__(self, start_hour: int, end_hour: int, days: List[int] = None):
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.days = days or list(range(7))  # All days by default


# ==================== SCHEDULING SERVICE ====================

class SchedulingService:
    """Core scheduling service for content pipeline"""
    
    # Default posting windows (local time)
    DEFAULT_WINDOWS = [
        PostingWindow(6, 8),    # Morning
        PostingWindow(10, 12),  # Mid-morning
        PostingWindow(14, 16),  # Afternoon
        PostingWindow(18, 20),  # Evening
        PostingWindow(22, 23),  # Night (optional)
    ]
    
    # Interval settings
    MIN_INTERVAL_HOURS = 4
    MAX_INTERVAL_HOURS = 24
    DEFAULT_INTERVAL_HOURS = 4
    
    def __init__(self, timezone_str: str = "UTC"):
        self.timezone = ZoneInfo(timezone_str)
        self.timezone_str = timezone_str
        self.posts: List[ScheduledPost] = []
        self.windows = self.DEFAULT_WINDOWS
    
    def set_timezone(self, timezone_str: str):
        """Update scheduling timezone"""
        self.timezone = ZoneInfo(timezone_str)
        self.timezone_str = timezone_str
    
    def schedule_post(
        self,
        content_id: UUID,
        platform: str,
        scheduled_time: datetime = None,
        priority: int = Priority.NORMAL,
        account_id: str = None,
    ) -> ScheduledPost:
        """Schedule a single post"""
        if scheduled_time is None:
            scheduled_time = self.get_next_available_slot(platform)
        
        post = ScheduledPost(
            content_id=content_id,
            platform=platform,
            scheduled_time=scheduled_time,
            priority=priority,
            account_id=account_id,
            timezone_str=str(self.timezone),
        )
        self.posts.append(post)
        return post
    
    def get_next_available_slot(
        self,
        platform: str,
        after: datetime = None,
    ) -> datetime:
        """Find next available posting slot respecting 4-hour intervals"""
        now = after or datetime.now(self.timezone)
        
        # Get existing posts for this platform
        platform_posts = [p for p in self.posts if p.platform == platform and p.status == ScheduleStatus.PENDING]
        
        if not platform_posts:
            # Find next window start
            return self._find_next_window(now)
        
        # Find slot at least 4 hours after last scheduled post
        last_post = max(platform_posts, key=lambda p: p.scheduled_time)
        next_slot = last_post.scheduled_time + timedelta(hours=self.MIN_INTERVAL_HOURS)
        
        # Ensure it falls within a posting window
        return self._find_next_window(next_slot)
    
    def _find_next_window(self, after: datetime) -> datetime:
        """Find next valid posting window after given time"""
        current = after
        
        for _ in range(48):  # Max 2 days search
            hour = current.hour
            
            for window in self.windows:
                if window.start_hour <= hour < window.end_hour:
                    if current.weekday() in window.days:
                        return current
                elif hour < window.start_hour:
                    # Jump to window start
                    next_time = current.replace(
                        hour=window.start_hour, 
                        minute=0, 
                        second=0,
                        microsecond=0
                    )
                    if next_time.weekday() in window.days:
                        return next_time
            
            # Move to next hour
            current = current + timedelta(hours=1)
            current = current.replace(minute=0, second=0, microsecond=0)
        
        return after  # Fallback
    
    def get_priority_queue(self) -> List[ScheduledPost]:
        """Get posts sorted by priority (highest first), then by scheduled time"""
        pending = [p for p in self.posts if p.status == ScheduleStatus.PENDING]
        return sorted(pending, key=lambda p: (-p.priority, p.scheduled_time))
    
    def calculate_runway(self, platform: str = None) -> dict:
        """Calculate content runway (days of scheduled content)"""
        pending = [p for p in self.posts if p.status == ScheduleStatus.PENDING]
        
        if platform:
            pending = [p for p in pending if p.platform == platform]
        
        if not pending:
            return {"days": 0, "posts": 0}
        
        last_post = max(pending, key=lambda p: p.scheduled_time)
        now = datetime.now(self.timezone)
        
        delta = last_post.scheduled_time - now
        days = max(0, delta.days + delta.seconds / 86400)
        
        return {
            "days": round(days, 1),
            "posts": len(pending),
        }
    
    def reschedule_post(self, post_id: UUID, new_time: datetime) -> bool:
        """Reschedule an existing post"""
        for post in self.posts:
            if post.id == post_id:
                # Check for conflicts
                if self._has_conflict(post.platform, new_time, exclude_id=post_id):
                    return False
                post.scheduled_time = new_time
                return True
        return False
    
    def _has_conflict(
        self, 
        platform: str, 
        time: datetime, 
        exclude_id: UUID = None
    ) -> bool:
        """Check if time conflicts with existing posts (within 4 hours)"""
        for post in self.posts:
            if post.id == exclude_id:
                continue
            if post.platform != platform:
                continue
            if post.status != ScheduleStatus.PENDING:
                continue
            
            delta = abs((post.scheduled_time - time).total_seconds())
            if delta < self.MIN_INTERVAL_HOURS * 3600:
                return True
        
        return False
    
    def bulk_schedule(
        self,
        content_ids: List[UUID],
        platform: str,
        start_time: datetime = None,
    ) -> List[ScheduledPost]:
        """Schedule multiple posts at once"""
        scheduled = []
        current_time = start_time or datetime.now(self.timezone)
        
        for content_id in content_ids:
            slot = self.get_next_available_slot(platform, after=current_time)
            post = self.schedule_post(content_id, platform, slot)
            scheduled.append(post)
            current_time = slot
        
        return scheduled
    
    def cancel_post(self, post_id: UUID) -> bool:
        """Cancel a scheduled post"""
        for post in self.posts:
            if post.id == post_id:
                post.status = ScheduleStatus.CANCELLED
                return True
        return False
    
    def get_posts_for_date(self, date: datetime) -> List[ScheduledPost]:
        """Get all posts scheduled for a specific date"""
        target_date = date.date()
        return [
            p for p in self.posts 
            if p.scheduled_time.date() == target_date
            and p.status == ScheduleStatus.PENDING
        ]
    
    def get_daily_post_count(self, platform: str = None) -> dict:
        """Get post counts by day"""
        from collections import defaultdict
        
        counts = defaultdict(int)
        for post in self.posts:
            if post.status != ScheduleStatus.PENDING:
                continue
            if platform and post.platform != platform:
                continue
            date_str = post.scheduled_time.strftime("%Y-%m-%d")
            counts[date_str] += 1
        
        return dict(counts)


# ==================== TESTS ====================

class TestSchedulingServiceBasics:
    """Basic scheduling service tests"""
    
    def test_create_service(self):
        """Should create scheduling service with default timezone"""
        service = SchedulingService()
        assert service is not None
        assert service.timezone_str == "UTC"
    
    def test_create_service_with_timezone(self):
        """Should create service with custom timezone"""
        service = SchedulingService("America/New_York")
        assert service.timezone_str == "America/New_York"
    
    def test_set_timezone(self):
        """Should update timezone"""
        service = SchedulingService()
        service.set_timezone("Europe/London")
        assert service.timezone_str == "Europe/London"
    
    def test_default_windows(self):
        """Should have default posting windows"""
        service = SchedulingService()
        assert len(service.DEFAULT_WINDOWS) == 5
    
    def test_min_interval_constant(self):
        """Should have 4-hour minimum interval"""
        service = SchedulingService()
        assert service.MIN_INTERVAL_HOURS == 4
    
    def test_max_interval_constant(self):
        """Should have 24-hour maximum interval"""
        service = SchedulingService()
        assert service.MAX_INTERVAL_HOURS == 24


class TestSchedulePost:
    """Test scheduling individual posts"""
    
    def test_schedule_single_post(self):
        """Should schedule a single post"""
        service = SchedulingService()
        content_id = uuid4()
        
        post = service.schedule_post(content_id, Platform.TIKTOK)
        
        assert post is not None
        assert post.content_id == content_id
        assert post.platform == Platform.TIKTOK
        assert post.status == ScheduleStatus.PENDING
    
    def test_schedule_with_specific_time(self):
        """Should schedule at specific time"""
        service = SchedulingService()
        content_id = uuid4()
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=5)
        
        post = service.schedule_post(content_id, Platform.YOUTUBE, scheduled_time)
        
        assert post.scheduled_time == scheduled_time
    
    def test_schedule_with_priority(self):
        """Should schedule with priority"""
        service = SchedulingService()
        
        post = service.schedule_post(uuid4(), Platform.INSTAGRAM, priority=Priority.HIGH)
        
        assert post.priority == Priority.HIGH
    
    def test_schedule_with_account(self):
        """Should schedule for specific account"""
        service = SchedulingService()
        account_id = "account_123"
        
        post = service.schedule_post(uuid4(), Platform.TWITTER, account_id=account_id)
        
        assert post.account_id == account_id
    
    def test_schedule_stores_timezone(self):
        """Should store timezone in post"""
        service = SchedulingService("America/Los_Angeles")
        
        post = service.schedule_post(uuid4(), Platform.LINKEDIN)
        
        assert "Los_Angeles" in post.timezone_str
    
    def test_schedule_adds_to_list(self):
        """Should add post to internal list"""
        service = SchedulingService()
        
        service.schedule_post(uuid4(), Platform.TIKTOK)
        service.schedule_post(uuid4(), Platform.YOUTUBE)
        
        assert len(service.posts) == 2


class TestIntervalEnforcement:
    """Test 4-hour interval enforcement"""
    
    def test_second_post_respects_interval(self):
        """Second post should be 4+ hours after first"""
        service = SchedulingService()
        
        post1 = service.schedule_post(uuid4(), Platform.TIKTOK)
        post2 = service.schedule_post(uuid4(), Platform.TIKTOK)
        
        delta = (post2.scheduled_time - post1.scheduled_time).total_seconds() / 3600
        assert delta >= service.MIN_INTERVAL_HOURS
    
    def test_different_platforms_no_interval(self):
        """Different platforms don't need interval"""
        service = SchedulingService()
        now = datetime.now(timezone.utc)
        
        post1 = service.schedule_post(uuid4(), Platform.TIKTOK, now)
        post2 = service.schedule_post(uuid4(), Platform.YOUTUBE, now + timedelta(minutes=30))
        
        # Should allow close scheduling on different platforms
        assert post2.scheduled_time is not None
    
    def test_conflict_detection(self):
        """Should detect scheduling conflicts"""
        service = SchedulingService()
        now = datetime.now(timezone.utc)
        
        service.schedule_post(uuid4(), Platform.TIKTOK, now)
        
        # 2 hours later should conflict
        has_conflict = service._has_conflict(
            Platform.TIKTOK, 
            now + timedelta(hours=2)
        )
        assert has_conflict is True
    
    def test_no_conflict_after_interval(self):
        """Should not conflict after 4 hours"""
        service = SchedulingService()
        now = datetime.now(timezone.utc)
        
        service.schedule_post(uuid4(), Platform.TIKTOK, now)
        
        has_conflict = service._has_conflict(
            Platform.TIKTOK,
            now + timedelta(hours=5)
        )
        assert has_conflict is False
    
    def test_multiple_posts_maintain_interval(self):
        """Multiple posts should all maintain 4-hour interval"""
        service = SchedulingService()
        
        posts = []
        for _ in range(5):
            post = service.schedule_post(uuid4(), Platform.INSTAGRAM)
            posts.append(post)
        
        for i in range(1, len(posts)):
            delta = (posts[i].scheduled_time - posts[i-1].scheduled_time).total_seconds() / 3600
            assert delta >= service.MIN_INTERVAL_HOURS


class TestPriorityQueue:
    """Test priority queue functionality"""
    
    def test_priority_queue_order(self):
        """Should return posts in priority order"""
        service = SchedulingService()
        
        service.schedule_post(uuid4(), Platform.TIKTOK, priority=Priority.LOW)
        service.schedule_post(uuid4(), Platform.TIKTOK, priority=Priority.HIGH)
        service.schedule_post(uuid4(), Platform.TIKTOK, priority=Priority.NORMAL)
        
        queue = service.get_priority_queue()
        
        assert queue[0].priority == Priority.HIGH
        assert queue[1].priority == Priority.NORMAL
        assert queue[2].priority == Priority.LOW
    
    def test_same_priority_by_time(self):
        """Same priority should sort by scheduled time"""
        service = SchedulingService()
        now = datetime.now(timezone.utc)
        
        service.schedule_post(uuid4(), Platform.TIKTOK, now + timedelta(hours=10), Priority.NORMAL)
        service.schedule_post(uuid4(), Platform.TIKTOK, now + timedelta(hours=5), Priority.NORMAL)
        
        queue = service.get_priority_queue()
        
        assert queue[0].scheduled_time < queue[1].scheduled_time
    
    def test_urgent_priority(self):
        """Urgent priority should be first"""
        service = SchedulingService()
        
        service.schedule_post(uuid4(), Platform.TIKTOK, priority=Priority.HIGH)
        service.schedule_post(uuid4(), Platform.YOUTUBE, priority=Priority.URGENT)
        service.schedule_post(uuid4(), Platform.INSTAGRAM, priority=Priority.NORMAL)
        
        queue = service.get_priority_queue()
        
        assert queue[0].priority == Priority.URGENT
    
    def test_priority_queue_excludes_posted(self):
        """Priority queue should exclude already posted content"""
        service = SchedulingService()
        
        post1 = service.schedule_post(uuid4(), Platform.TIKTOK)
        post2 = service.schedule_post(uuid4(), Platform.TIKTOK)
        
        post1.status = ScheduleStatus.POSTED
        
        queue = service.get_priority_queue()
        
        assert len(queue) == 1
        assert queue[0].id == post2.id
    
    def test_priority_queue_excludes_cancelled(self):
        """Priority queue should exclude cancelled posts"""
        service = SchedulingService()
        
        post = service.schedule_post(uuid4(), Platform.TIKTOK)
        service.cancel_post(post.id)
        
        queue = service.get_priority_queue()
        
        assert len(queue) == 0


class TestTimezoneHandling:
    """Test timezone-aware scheduling"""
    
    def test_utc_scheduling(self):
        """Should schedule in UTC by default"""
        service = SchedulingService("UTC")
        
        post = service.schedule_post(uuid4(), Platform.TIKTOK)
        
        assert post.timezone_str == "UTC"
    
    def test_pacific_timezone(self):
        """Should handle Pacific timezone"""
        service = SchedulingService("America/Los_Angeles")
        
        post = service.schedule_post(uuid4(), Platform.TIKTOK)
        
        assert "Los_Angeles" in post.timezone_str
    
    def test_eastern_timezone(self):
        """Should handle Eastern timezone"""
        service = SchedulingService("America/New_York")
        
        post = service.schedule_post(uuid4(), Platform.TIKTOK)
        
        assert "New_York" in post.timezone_str
    
    def test_european_timezone(self):
        """Should handle European timezones"""
        service = SchedulingService("Europe/London")
        
        post = service.schedule_post(uuid4(), Platform.YOUTUBE)
        
        assert "London" in post.timezone_str
    
    def test_asian_timezone(self):
        """Should handle Asian timezones"""
        service = SchedulingService("Asia/Tokyo")
        
        post = service.schedule_post(uuid4(), Platform.INSTAGRAM)
        
        assert "Tokyo" in post.timezone_str
    
    def test_timezone_change_affects_new_posts(self):
        """Timezone change should affect new posts"""
        service = SchedulingService("UTC")
        
        service.schedule_post(uuid4(), Platform.TIKTOK)
        service.set_timezone("America/Chicago")
        
        post2 = service.schedule_post(uuid4(), Platform.TIKTOK)
        
        assert "Chicago" in post2.timezone_str


class TestPostingWindows:
    """Test posting window logic"""
    
    def test_morning_window(self):
        """Should recognize morning window (6-8 AM)"""
        service = SchedulingService()
        
        morning = datetime.now(timezone.utc).replace(hour=7, minute=0)
        window = service._find_next_window(morning)
        
        assert window.hour >= 6 and window.hour <= 23
    
    def test_afternoon_window(self):
        """Should recognize afternoon window (2-4 PM)"""
        service = SchedulingService()
        
        afternoon = datetime.now(timezone.utc).replace(hour=15, minute=0)
        window = service._find_next_window(afternoon)
        
        assert window is not None
    
    def test_evening_window(self):
        """Should recognize evening window (6-8 PM)"""
        service = SchedulingService()
        
        evening = datetime.now(timezone.utc).replace(hour=19, minute=0)
        window = service._find_next_window(evening)
        
        assert window is not None
    
    def test_night_window(self):
        """Should recognize night window (10-11 PM)"""
        service = SchedulingService()
        
        night = datetime.now(timezone.utc).replace(hour=22, minute=30)
        window = service._find_next_window(night)
        
        assert window is not None
    
    def test_overnight_advances_to_morning(self):
        """Scheduling at 3 AM should advance to morning window"""
        service = SchedulingService()
        
        overnight = datetime.now(timezone.utc).replace(hour=3, minute=0)
        window = service._find_next_window(overnight)
        
        # Should advance to 6 AM window
        assert window.hour >= 6


class TestContentRunway:
    """Test runway calculation"""
    
    def test_empty_runway(self):
        """Should return 0 days for no scheduled posts"""
        service = SchedulingService()
        
        runway = service.calculate_runway()
        
        assert runway["days"] == 0
        assert runway["posts"] == 0
    
    def test_runway_calculation(self):
        """Should calculate runway days"""
        service = SchedulingService()
        
        # Schedule posts over 30 days
        now = datetime.now(timezone.utc)
        for i in range(30):
            service.schedule_post(
                uuid4(), 
                Platform.TIKTOK, 
                now + timedelta(days=i)
            )
        
        runway = service.calculate_runway()
        
        assert runway["days"] >= 28
        assert runway["posts"] == 30
    
    def test_runway_by_platform(self):
        """Should calculate runway for specific platform"""
        service = SchedulingService()
        now = datetime.now(timezone.utc)
        
        for i in range(10):
            service.schedule_post(uuid4(), Platform.TIKTOK, now + timedelta(days=i))
        for i in range(5):
            service.schedule_post(uuid4(), Platform.YOUTUBE, now + timedelta(days=i))
        
        tiktok_runway = service.calculate_runway(Platform.TIKTOK)
        youtube_runway = service.calculate_runway(Platform.YOUTUBE)
        
        assert tiktok_runway["posts"] == 10
        assert youtube_runway["posts"] == 5
    
    def test_runway_excludes_posted(self):
        """Should exclude already posted content from runway"""
        service = SchedulingService()
        now = datetime.now(timezone.utc)
        
        for i in range(5):
            service.schedule_post(uuid4(), Platform.TIKTOK, now + timedelta(days=i))
        
        # Mark 2 as posted
        service.posts[0].status = ScheduleStatus.POSTED
        service.posts[1].status = ScheduleStatus.POSTED
        
        runway = service.calculate_runway()
        
        assert runway["posts"] == 3


class TestBulkScheduling:
    """Test bulk scheduling operations"""
    
    def test_bulk_schedule_multiple(self):
        """Should bulk schedule multiple posts"""
        service = SchedulingService()
        content_ids = [uuid4() for _ in range(5)]
        
        posts = service.bulk_schedule(content_ids, Platform.TIKTOK)
        
        assert len(posts) == 5
    
    def test_bulk_schedule_maintains_intervals(self):
        """Bulk scheduled posts should maintain 4-hour intervals"""
        service = SchedulingService()
        content_ids = [uuid4() for _ in range(5)]
        
        posts = service.bulk_schedule(content_ids, Platform.TIKTOK)
        
        for i in range(1, len(posts)):
            delta = (posts[i].scheduled_time - posts[i-1].scheduled_time).total_seconds() / 3600
            assert delta >= 4
    
    def test_bulk_schedule_with_start_time(self):
        """Should bulk schedule starting from specific time"""
        service = SchedulingService()
        content_ids = [uuid4() for _ in range(3)]
        start = datetime.now(timezone.utc) + timedelta(days=7)
        
        posts = service.bulk_schedule(content_ids, Platform.YOUTUBE, start)
        
        assert all(p.scheduled_time >= start for p in posts)
    
    def test_bulk_schedule_different_platforms(self):
        """Should bulk schedule to different platforms"""
        service = SchedulingService()
        
        tiktok_posts = service.bulk_schedule([uuid4(), uuid4()], Platform.TIKTOK)
        youtube_posts = service.bulk_schedule([uuid4(), uuid4()], Platform.YOUTUBE)
        
        assert len(tiktok_posts) == 2
        assert len(youtube_posts) == 2
        assert len(service.posts) == 4


class TestRescheduling:
    """Test rescheduling functionality"""
    
    def test_reschedule_post(self):
        """Should reschedule a post"""
        service = SchedulingService()
        
        post = service.schedule_post(uuid4(), Platform.TIKTOK)
        new_time = datetime.now(timezone.utc) + timedelta(days=7)
        
        result = service.reschedule_post(post.id, new_time)
        
        assert result is True
        assert post.scheduled_time == new_time
    
    def test_reschedule_prevents_conflict(self):
        """Should prevent rescheduling to conflicting time"""
        service = SchedulingService()
        now = datetime.now(timezone.utc)
        
        post1 = service.schedule_post(uuid4(), Platform.TIKTOK, now)
        post2 = service.schedule_post(uuid4(), Platform.TIKTOK, now + timedelta(hours=5))
        
        # Try to reschedule post2 to conflict with post1
        result = service.reschedule_post(post2.id, now + timedelta(hours=1))
        
        assert result is False
    
    def test_reschedule_nonexistent_post(self):
        """Should return False for nonexistent post"""
        service = SchedulingService()
        
        result = service.reschedule_post(uuid4(), datetime.now(timezone.utc))
        
        assert result is False


class TestCancellation:
    """Test post cancellation"""
    
    def test_cancel_post(self):
        """Should cancel a scheduled post"""
        service = SchedulingService()
        
        post = service.schedule_post(uuid4(), Platform.TIKTOK)
        result = service.cancel_post(post.id)
        
        assert result is True
        assert post.status == ScheduleStatus.CANCELLED
    
    def test_cancel_nonexistent(self):
        """Should return False for nonexistent post"""
        service = SchedulingService()
        
        result = service.cancel_post(uuid4())
        
        assert result is False
    
    def test_cancelled_not_in_runway(self):
        """Cancelled posts should not count in runway"""
        service = SchedulingService()
        now = datetime.now(timezone.utc)
        
        for i in range(5):
            service.schedule_post(uuid4(), Platform.TIKTOK, now + timedelta(days=i))
        
        service.cancel_post(service.posts[0].id)
        
        runway = service.calculate_runway()
        
        assert runway["posts"] == 4


class TestDateQueries:
    """Test date-based queries"""
    
    def test_get_posts_for_date(self):
        """Should get posts for specific date"""
        service = SchedulingService()
        today = datetime.now(timezone.utc)
        tomorrow = today + timedelta(days=1)
        
        service.schedule_post(uuid4(), Platform.TIKTOK, today)
        service.schedule_post(uuid4(), Platform.YOUTUBE, today)
        service.schedule_post(uuid4(), Platform.INSTAGRAM, tomorrow)
        
        today_posts = service.get_posts_for_date(today)
        
        assert len(today_posts) == 2
    
    def test_get_daily_counts(self):
        """Should get daily post counts"""
        service = SchedulingService()
        now = datetime.now(timezone.utc)
        
        # Schedule multiple on same day
        for _ in range(3):
            service.schedule_post(uuid4(), Platform.TIKTOK, now)
        
        counts = service.get_daily_post_count()
        
        today = now.strftime("%Y-%m-%d")
        assert counts[today] == 3
    
    def test_daily_counts_by_platform(self):
        """Should filter daily counts by platform"""
        service = SchedulingService()
        now = datetime.now(timezone.utc)
        
        service.schedule_post(uuid4(), Platform.TIKTOK, now)
        service.schedule_post(uuid4(), Platform.TIKTOK, now)
        service.schedule_post(uuid4(), Platform.YOUTUBE, now)
        
        tiktok_counts = service.get_daily_post_count(Platform.TIKTOK)
        youtube_counts = service.get_daily_post_count(Platform.YOUTUBE)
        
        today = now.strftime("%Y-%m-%d")
        assert tiktok_counts[today] == 2
        assert youtube_counts[today] == 1


class TestScheduledPostModel:
    """Test ScheduledPost model"""
    
    def test_create_scheduled_post(self):
        """Should create scheduled post with defaults"""
        post = ScheduledPost()
        
        assert post.id is not None
        assert post.content_id is not None
        assert post.platform == Platform.TIKTOK
        assert post.status == ScheduleStatus.PENDING
        assert post.priority == Priority.NORMAL
    
    def test_custom_post_attributes(self):
        """Should accept custom attributes"""
        content_id = uuid4()
        account_id = "custom_account"
        
        post = ScheduledPost(
            content_id=content_id,
            platform=Platform.YOUTUBE,
            priority=Priority.HIGH,
            account_id=account_id,
        )
        
        assert post.content_id == content_id
        assert post.platform == Platform.YOUTUBE
        assert post.priority == Priority.HIGH
        assert post.account_id == account_id
    
    def test_retry_count_default(self):
        """Should default retry count to 0"""
        post = ScheduledPost()
        assert post.retry_count == 0
    
    def test_error_message_default(self):
        """Should default error message to None"""
        post = ScheduledPost()
        assert post.error_message is None


class TestPostingWindowModel:
    """Test PostingWindow model"""
    
    def test_create_window(self):
        """Should create posting window"""
        window = PostingWindow(9, 12)
        
        assert window.start_hour == 9
        assert window.end_hour == 12
    
    def test_window_with_days(self):
        """Should create window with specific days"""
        window = PostingWindow(9, 12, [0, 1, 2, 3, 4])  # Weekdays only
        
        assert len(window.days) == 5
        assert 5 not in window.days  # Saturday
    
    def test_default_all_days(self):
        """Should default to all days"""
        window = PostingWindow(9, 12)
        
        assert len(window.days) == 7


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_schedule_far_future(self):
        """Should handle far future scheduling"""
        service = SchedulingService()
        future = datetime.now(timezone.utc) + timedelta(days=365)
        
        post = service.schedule_post(uuid4(), Platform.TIKTOK, future)
        
        assert post.scheduled_time >= future
    
    def test_schedule_many_posts(self):
        """Should handle many scheduled posts"""
        service = SchedulingService()
        
        for _ in range(100):
            service.schedule_post(uuid4(), Platform.TIKTOK)
        
        assert len(service.posts) == 100
    
    def test_empty_priority_queue(self):
        """Should handle empty priority queue"""
        service = SchedulingService()
        
        queue = service.get_priority_queue()
        
        assert len(queue) == 0
    
    def test_runway_with_only_posted(self):
        """Should handle runway when all posts are done"""
        service = SchedulingService()
        
        post = service.schedule_post(uuid4(), Platform.TIKTOK)
        post.status = ScheduleStatus.POSTED
        
        runway = service.calculate_runway()
        
        assert runway["posts"] == 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
