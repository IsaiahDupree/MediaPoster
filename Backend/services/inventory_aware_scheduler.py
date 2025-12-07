"""
Inventory-Aware Scheduler Service
Automatically schedules content from resource folder based on available inventory
Maintains consistent posts per day across a fixed horizon (2 months)
Adapts dynamically when new content is added
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, select
import uuid
import math

from database.models import VideoClip, Video, ScheduledPost
from database.connection import async_session_maker, get_db

logger = logging.getLogger(__name__)


@dataclass
class SchedulerConfig:
    """Configuration for inventory-aware scheduler"""
    horizon_months: int = 2  # How far ahead to schedule (default: 2 months)
    min_posts_per_day_short: float = 1.0  # Minimum short-form posts per day
    max_posts_per_day_short: float = 3.0  # Maximum short-form posts per day
    min_posts_per_day_long: float = 0.2  # Minimum long-form posts per day (1 every 5 days)
    max_posts_per_day_long: float = 1.0  # Maximum long-form posts per day
    short_form_duration_max: float = 60.0  # Max duration for short-form (seconds)
    long_form_duration_min: float = 60.0  # Min duration for long-form (seconds)
    preferred_posting_times: List[int] = None  # Preferred hours of day (0-23)
    platforms: List[str] = None  # Platforms to schedule for
    
    def __post_init__(self):
        if self.preferred_posting_times is None:
            # Default: 8am, 12pm, 5pm, 8pm (peak engagement times)
            self.preferred_posting_times = [8, 12, 17, 20]
        if self.platforms is None:
            self.platforms = ['instagram', 'tiktok', 'youtube_shorts']


@dataclass
class ContentInventory:
    """Represents available content inventory"""
    short_form_count: int = 0
    long_form_count: int = 0
    total_count: int = 0
    short_form_items: List[Dict] = None
    long_form_items: List[Dict] = None
    
    def __post_init__(self):
        if self.short_form_items is None:
            self.short_form_items = []
        if self.long_form_items is None:
            self.long_form_items = []


@dataclass
class SchedulePlan:
    """Plan for scheduling content"""
    posts_per_day_short: float
    posts_per_day_long: float
    total_days: int
    total_posts_short: int
    total_posts_long: int
    schedule_start: datetime
    schedule_end: datetime
    can_extend_horizon: bool  # Whether we can extend beyond default horizon


class InventoryAwareScheduler:
    """
    Inventory-aware scheduler that automatically schedules content
    based on available inventory and maintains consistency
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
    
    async def get_available_inventory(self, user_id: Optional[uuid.UUID] = None) -> ContentInventory:
        """
        Get available content from resource folder (videos/clips)
        
        Returns:
            ContentInventory with available short-form and long-form content
        """
        async with async_session_maker() as session:
            # Get all ready clips/videos that haven't been scheduled
            # Short-form: clips with duration <= short_form_duration_max
            # Long-form: videos with duration >= long_form_duration_min
            
            # Get clips (short-form)
            clips_query = select(VideoClip).where(
                and_(
                    VideoClip.status == 'ready',
                    VideoClip.user_id == user_id if user_id else True
                )
            )
            
            # Get videos (long-form)
            # Note: Video model may not have status field, so we'll get all videos
            videos_query = select(Video).where(
                Video.user_id == user_id if user_id else True
            )
            
            # Get already scheduled items to exclude
            scheduled_clips_query = select(ScheduledPost.clip_id).where(
                ScheduledPost.status.in_(['scheduled', 'publishing'])
            )
            scheduled_videos_query = select(ScheduledPost.content_variant_id).where(
                ScheduledPost.status.in_(['scheduled', 'publishing'])
            )
            
            clips_result = await session.execute(clips_query)
            videos_result = await session.execute(videos_query)
            
            clips = clips_result.scalars().all()
            videos = videos_result.scalars().all()
            
            # Get scheduled IDs
            scheduled_clips_result = await session.execute(scheduled_clips_query)
            scheduled_videos_result = await session.execute(scheduled_videos_query)
            scheduled_clip_ids = {str(row[0]) for row in scheduled_clips_result.fetchall() if row[0]}
            scheduled_video_ids = {str(row[0]) for row in scheduled_videos_result.fetchall() if row[0]}
            
            # Filter and categorize
            short_form_items = []
            long_form_items = []
            
            for clip in clips:
                if str(clip.id) not in scheduled_clip_ids:
                    # Get clip duration (computed field: end_time - start_time)
                    duration = (clip.end_time - clip.start_time) if hasattr(clip, 'end_time') and hasattr(clip, 'start_time') else 30.0
                    if duration <= self.config.short_form_duration_max:
                        short_form_items.append({
                            'id': str(clip.id),
                            'type': 'clip',
                            'duration': duration,
                            'title': clip.title or f"Clip {clip.id}",
                            'video_id': str(clip.video_id)
                        })
            
            for video in videos:
                if str(video.id) not in scheduled_video_ids:
                    duration = video.duration_sec if hasattr(video, 'duration_sec') and video.duration_sec else 0
                    if duration >= self.config.long_form_duration_min:
                        long_form_items.append({
                            'id': str(video.id),
                            'type': 'video',
                            'duration': duration,
                            'title': video.file_name or f"Video {video.id}"
                        })
            
            return ContentInventory(
                short_form_count=len(short_form_items),
                long_form_count=len(long_form_items),
                total_count=len(short_form_items) + len(long_form_items),
                short_form_items=short_form_items,
                long_form_items=long_form_items
            )
    
    def calculate_optimal_schedule(self, inventory: ContentInventory) -> SchedulePlan:
        """
        Calculate optimal posts per day based on inventory
        
        Args:
            inventory: Available content inventory
            
        Returns:
            SchedulePlan with optimal scheduling strategy
        """
        now = datetime.now()
        horizon_days = self.config.horizon_months * 30  # Approximate days in horizon
        
        # Calculate optimal posts per day for short-form
        if inventory.short_form_count > 0:
            posts_per_day_short = inventory.short_form_count / horizon_days
            # Clamp to min/max
            posts_per_day_short = max(
                self.config.min_posts_per_day_short,
                min(posts_per_day_short, self.config.max_posts_per_day_short)
            )
        else:
            posts_per_day_short = self.config.min_posts_per_day_short
        
        # Calculate optimal posts per day for long-form
        if inventory.long_form_count > 0:
            posts_per_day_long = inventory.long_form_count / horizon_days
            # Clamp to min/max
            posts_per_day_long = max(
                self.config.min_posts_per_day_long,
                min(posts_per_day_long, self.config.max_posts_per_day_long)
            )
        else:
            posts_per_day_long = self.config.min_posts_per_day_long
        
        # Calculate total posts needed
        total_posts_short = int(posts_per_day_short * horizon_days)
        total_posts_long = int(posts_per_day_long * horizon_days)
        
        # Check if we can extend horizon to use all inventory
        can_extend = False
        if inventory.short_form_count > total_posts_short:
            # Calculate how many days we'd need to use all inventory
            extended_days = math.ceil(inventory.short_form_count / posts_per_day_short)
            if extended_days <= horizon_days * 2:  # Allow up to 2x extension
                can_extend = True
                horizon_days = extended_days
                total_posts_short = inventory.short_form_count
        
        if inventory.long_form_count > total_posts_long:
            extended_days = math.ceil(inventory.long_form_count / posts_per_day_long)
            if extended_days <= horizon_days * 2:
                can_extend = True
                horizon_days = max(horizon_days, extended_days)
                total_posts_long = inventory.long_form_count
        
        schedule_end = now + timedelta(days=horizon_days)
        
        return SchedulePlan(
            posts_per_day_short=posts_per_day_short,
            posts_per_day_long=posts_per_day_long,
            total_days=horizon_days,
            total_posts_short=min(total_posts_short, inventory.short_form_count),
            total_posts_long=min(total_posts_long, inventory.long_form_count),
            schedule_start=now,
            schedule_end=schedule_end,
            can_extend_horizon=can_extend
        )
    
    async def generate_schedule(
        self,
        plan: SchedulePlan,
        inventory: ContentInventory,
        user_id: Optional[uuid.UUID] = None
    ) -> List[Dict]:
        """
        Generate actual schedule with specific times for each post
        
        Args:
            plan: Schedule plan
            inventory: Available inventory
            user_id: User ID for scheduling
            
        Returns:
            List of scheduled post dictionaries
        """
        scheduled_posts = []
        current_date = plan.schedule_start.date()
        end_date = plan.schedule_end.date()
        
        # Distribute posts across days
        short_form_items = inventory.short_form_items.copy()
        long_form_items = inventory.long_form_items.copy()
        
        short_form_accumulator = 0.0
        long_form_accumulator = 0.0
        
        day_index = 0
        
        while current_date <= end_date and (short_form_items or long_form_items):
            # Calculate posts for this day
            short_form_accumulator += plan.posts_per_day_short
            long_form_accumulator += plan.posts_per_day_long
            
            # Schedule short-form posts
            short_form_count_today = int(short_form_accumulator)
            short_form_accumulator -= short_form_count_today
            
            for _ in range(short_form_count_today):
                if not short_form_items:
                    break
                
                item = short_form_items.pop(0)
                posting_time = self._get_posting_time_for_day(current_date, day_index)
                
                # Schedule for each platform
                for platform in self.config.platforms:
                    scheduled_posts.append({
                        'clip_id': item['id'] if item['type'] == 'clip' else None,
                        'content_variant_id': item['id'] if item['type'] == 'video' else None,
                        'platform': platform,
                        'scheduled_time': posting_time,
                        'user_id': user_id
                    })
            
            # Schedule long-form posts
            long_form_count_today = int(long_form_accumulator)
            long_form_accumulator -= long_form_count_today
            
            for _ in range(long_form_count_today):
                if not long_form_items:
                    break
                
                item = long_form_items.pop(0)
                posting_time = self._get_posting_time_for_day(current_date, day_index, is_long_form=True)
                
                # Schedule for each platform (usually just YouTube for long-form)
                platforms = ['youtube'] if 'youtube' in self.config.platforms else self.config.platforms
                for platform in platforms:
                    scheduled_posts.append({
                        'clip_id': None,
                        'content_variant_id': item['id'] if item['type'] == 'video' else None,
                        'platform': platform,
                        'scheduled_time': posting_time,
                        'user_id': user_id
                    })
            
            current_date += timedelta(days=1)
            day_index += 1
        
        return scheduled_posts
    
    def _get_posting_time_for_day(
        self,
        date: datetime.date,
        day_index: int,
        is_long_form: bool = False
    ) -> datetime:
        """
        Get optimal posting time for a given day
        
        Args:
            date: Date to schedule for
            day_index: Index of day (for variety)
            is_long_form: Whether this is long-form content
            
        Returns:
            Datetime for posting
        """
        # For long-form, prefer morning/afternoon
        # For short-form, use preferred times
        if is_long_form:
            preferred_hours = [10, 14, 16]  # Morning/afternoon for long-form
        else:
            preferred_hours = self.config.preferred_posting_times
        
        # Rotate through preferred times
        hour = preferred_hours[day_index % len(preferred_hours)]
        
        return datetime.combine(date, datetime.min.time().replace(hour=hour, minute=0))
    
    async def create_scheduled_posts(
        self,
        scheduled_posts: List[Dict],
        user_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Create scheduled posts in database
        
        Args:
            scheduled_posts: List of post dictionaries
            user_id: User ID
            
        Returns:
            Number of posts created
        """
        async with async_session_maker() as session:
            created_count = 0
            
            for post_data in scheduled_posts:
                try:
                    scheduled_post = ScheduledPost(
                        id=uuid.uuid4(),
                        clip_id=uuid.UUID(post_data['clip_id']) if post_data.get('clip_id') else None,
                        content_variant_id=uuid.UUID(post_data['content_variant_id']) if post_data.get('content_variant_id') else None,
                        platform=post_data['platform'],
                        scheduled_time=post_data['scheduled_time'],
                        status='scheduled'
                    )
                    
                    session.add(scheduled_post)
                    created_count += 1
                except Exception as e:
                    logger.error(f"Error creating scheduled post: {e}")
                    continue
            
            await session.commit()
            logger.info(f"Created {created_count} scheduled posts")
            
            return created_count
    
    async def auto_schedule(
        self,
        user_id: Optional[uuid.UUID] = None,
        force_reschedule: bool = False
    ) -> Dict:
        """
        Main method: Automatically schedule content based on inventory
        
        Args:
            user_id: User ID
            force_reschedule: If True, reschedule even if posts already exist
            
        Returns:
            Dictionary with scheduling results
        """
        # Get available inventory
        inventory = await self.get_available_inventory(user_id)
        
        if inventory.total_count == 0:
            return {
                'success': False,
                'message': 'No available content to schedule',
                'inventory': {
                    'short_form': inventory.short_form_count,
                    'long_form': inventory.long_form_count
                }
            }
        
        # Calculate optimal schedule
        plan = self.calculate_optimal_schedule(inventory)
        
        # Generate schedule
        scheduled_posts = await self.generate_schedule(plan, inventory, user_id)
        
        # Create scheduled posts
        created_count = await self.create_scheduled_posts(scheduled_posts, user_id)
        
        return {
            'success': True,
            'message': f'Scheduled {created_count} posts',
            'plan': {
                'posts_per_day_short': plan.posts_per_day_short,
                'posts_per_day_long': plan.posts_per_day_long,
                'total_days': plan.total_days,
                'schedule_end': plan.schedule_end.isoformat()
            },
            'inventory': {
                'short_form': inventory.short_form_count,
                'long_form': inventory.long_form_count
            },
            'scheduled_count': created_count
        }
    
    async def update_schedule_on_new_content(
        self,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict:
        """
        Called when new content is added to resource folder
        Extends schedule if needed
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with update results
        """
        # Get current inventory
        inventory = await self.get_available_inventory(user_id)
        
        # Get existing schedule
        async with async_session_maker() as session:
            existing_schedule_query = select(ScheduledPost).where(
                and_(
                    ScheduledPost.status == 'scheduled',
                    ScheduledPost.scheduled_time > datetime.now()
                )
            )
            existing_result = await session.execute(existing_schedule_query)
            existing_posts = existing_result.scalars().all()
            
            if not existing_posts:
                # No existing schedule, create new one
                return await self.auto_schedule(user_id)
            
            # Calculate if we need to extend schedule
            latest_scheduled = max(post.scheduled_time for post in existing_posts)
            days_until_end = (latest_scheduled.date() - datetime.now().date()).days
            
            # Recalculate optimal schedule
            plan = self.calculate_optimal_schedule(inventory)
            
            # If new plan extends beyond current schedule, add more posts
            if plan.total_days > days_until_end:
                # Generate additional schedule from end of current to new end
                additional_start = latest_scheduled + timedelta(days=1)
                additional_days = plan.total_days - days_until_end
                
                # Get remaining inventory (not yet scheduled)
                scheduled_posts = await self.generate_schedule(plan, inventory, user_id)
                
                # Filter to only posts after latest_scheduled
                new_posts = [
                    p for p in scheduled_posts
                    if p['scheduled_time'] > latest_scheduled
                ]
                
                created_count = await self.create_scheduled_posts(new_posts, user_id)
                
                return {
                    'success': True,
                    'message': f'Extended schedule with {created_count} additional posts',
                    'extended_days': additional_days,
                    'new_schedule_end': plan.schedule_end.isoformat(),
                    'scheduled_count': created_count
                }
            else:
                return {
                    'success': True,
                    'message': 'Schedule is already optimal',
                    'no_changes': True
                }

