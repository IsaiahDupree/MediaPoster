"""
Calendar Service - Manages scheduled posts and calendar operations
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.models import ScheduledPost, VideoClip, ContentVariant, PlatformPost
from services.exceptions import ServiceError


class CalendarService:
    """Service for managing content calendar and scheduled posts"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_calendar_posts(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        platforms: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get scheduled posts for calendar view
        
        Args:
            user_id: User ID to filter by
            start_date: Optional start date filter
            end_date: Optional end date filter
            platforms: Optional list of platforms to filter by
            status: Optional status filter (scheduled, published, failed, cancelled)
        
        Returns:
            List of scheduled posts with related content data
        """
        try:
            # Build base query
            query = select(ScheduledPost).where(ScheduledPost.status != 'cancelled')
            
            # Apply date filters
            if start_date:
                query = query.where(ScheduledPost.scheduled_time >= start_date)
            if end_date:
                query = query.where(ScheduledPost.scheduled_time <= end_date)
            
            # Apply platform filter
            if platforms:
                query = query.where(ScheduledPost.platform.in_(platforms))
            
            # Apply status filter
            if status:
                query = query.where(ScheduledPost.status == status)
            
            # Order by scheduled time
            query = query.order_by(ScheduledPost.scheduled_time.asc())
            
            result = await self.db.execute(query)
            scheduled_posts = result.scalars().all()
            
            # Format response with content details
            posts_data = []
            for post in scheduled_posts:
                post_dict = {
                    'id': str(post.id),
                    'platform': post.platform,
                    'scheduled_time': post.scheduled_time.isoformat(),
                    'status': post.status,
                    'is_ai_recommended': post.is_ai_recommended,
                    'recommendation_score': post.recommendation_score,
                    'recommendation_reasoning': post.recommendation_reasoning,
                    'published_at': post.published_at.isoformat() if post.published_at else None,
                    'error_message': post.error_message,
                    'created_at': post.created_at.isoformat()
                }
                
                # Include content variant data if available
                if post.content_variant_id:
                    variant_result = await self.db.execute(
                        select(ContentVariant).where(ContentVariant.id == post.content_variant_id)
                    )
                    variant = variant_result.scalar_one_or_none()
                    if variant:
                        post_dict['content'] = {
                            'variant_id': str(variant.id),
                            'caption': variant.caption,
                            'title': variant.title,
                            'hashtags': variant.hashtags,
                            'thumbnail_url': variant.thumbnail_url
                        }
                
                # Include clip data if available
                if post.clip_id:
                    clip_result = await self.db.execute(
                        select(VideoClip).where(VideoClip.id == post.clip_id)
                    )
                    clip = clip_result.scalar_one_or_none()
                    if clip:
                        post_dict['clip'] = {
                            'clip_id': str(clip.id),
                            'title': clip.title,
                            'duration_seconds': clip.duration_seconds,
                            'file_path': clip.file_path
                        }
                
                posts_data.append(post_dict)
            
            logger.info(f"Retrieved {len(posts_data)} calendar posts")
            return posts_data
            
        except Exception as e:
            logger.error(f"Failed to get calendar posts: {e}")
            raise ServiceError(f"Failed to get calendar posts: {str(e)}")
    
    async def schedule_post(
        self,
        clip_id: Optional[UUID] = None,
        content_variant_id: Optional[UUID] = None,
        platform: str = None,
        scheduled_time: datetime = None,
        platform_account_id: Optional[UUID] = None,
        is_ai_recommended: bool = False,
        recommendation_score: Optional[float] = None,
        recommendation_reasoning: Optional[str] = None
    ) -> ScheduledPost:
        """
        Schedule a new post
        
        Args:
            clip_id: Video clip to schedule
            content_variant_id: Content variant to schedule
            platform: Target platform
            scheduled_time: When to publish
            platform_account_id: Specific platform account
            is_ai_recommended: Whether this was AI recommended
            recommendation_score: AI confidence score
            recommendation_reasoning: AI explanation
        
        Returns:
            Created ScheduledPost instance
        """
        try:
            # Validate inputs
            if not (clip_id or content_variant_id):
                raise ValueError("Either clip_id or content_variant_id must be provided")
            
            if not platform:
                raise ValueError("Platform is required")
            
            if not scheduled_time:
                raise ValueError("Scheduled time is required")
            
            # Ensure scheduled time is in the future
            if scheduled_time <= datetime.now(scheduled_time.tzinfo):
                raise ValueError("Scheduled time must be in the future")
            
            # Create scheduled post
            scheduled_post = ScheduledPost(
                clip_id=clip_id,
                content_variant_id=content_variant_id,
                platform=platform,
                scheduled_time=scheduled_time,
                platform_account_id=platform_account_id,
                status='scheduled',
                is_ai_recommended=is_ai_recommended,
                recommendation_score=recommendation_score,
                recommendation_reasoning=recommendation_reasoning
            )
            
            self.db.add(scheduled_post)
            await self.db.commit()
            await self.db.refresh(scheduled_post)
            
            logger.success(f"✓ Scheduled post for {platform} at {scheduled_time}")
            return scheduled_post
            
        except ValueError as e:
            logger.warning(f"Invalid schedule request: {e}")
            raise ServiceError(str(e))
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to schedule post: {e}")
            raise ServiceError(f"Failed to schedule post: {str(e)}")
    
    async def reschedule_post(
        self,
        post_id: UUID,
        new_time: datetime
    ) -> ScheduledPost:
        """
        Reschedule an existing post to a new time
        
        Args:
            post_id: ID of post to reschedule
            new_time: New scheduled time
        
        Returns:
            Updated ScheduledPost instance
        """
        try:
            # Get existing post
            result = await self.db.execute(
                select(ScheduledPost).where(ScheduledPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            
            if not post:
                raise ValueError(f"Scheduled post {post_id} not found")
            
            # Validate can reschedule
            if post.status not in ['scheduled', 'failed']:
                raise ValueError(f"Cannot reschedule post with status: {post.status}")
            
            # Ensure new time is in the future
            if new_time <= datetime.now(new_time.tzinfo):
                raise ValueError("New scheduled time must be in the future")
            
            # Update the scheduled time
            old_time = post.scheduled_time
            post.scheduled_time = new_time
            
            # If previously failed, reset to scheduled
            if post.status == 'failed':
                post.status = 'scheduled'
                post.error_message = None
            
            await self.db.commit()
            await self.db.refresh(post)
            
            logger.info(f"Rescheduled post {post_id} from {old_time} to {new_time}")
            return post
            
        except ValueError as e:
            logger.warning(f"Invalid reschedule request: {e}")
            raise ServiceError(str(e))
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to reschedule post: {e}")
            raise ServiceError(f"Failed to reschedule post: {str(e)}")
    
    async def cancel_scheduled_post(self, post_id: UUID) -> bool:
        """
        Cancel a scheduled post
        
        Args:
            post_id: ID of post to cancel
        
        Returns:
            True if cancelled successfully
        """
        try:
            # Get existing post
            result = await self.db.execute(
                select(ScheduledPost).where(ScheduledPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            
            if not post:
                raise ValueError(f"Scheduled post {post_id} not found")
            
            # Validate can cancel
            if post.status == 'published':
                raise ValueError("Cannot cancel already published post")
            
            # Mark as cancelled
            post.status = 'cancelled'
            
            await self.db.commit()
            
            logger.info(f"Cancelled scheduled post {post_id}")
            return True
            
        except ValueError as e:
            logger.warning(f"Invalid cancel request: {e}")
            raise ServiceError(str(e))
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cancel post: {e}")
            raise ServiceError(f"Failed to cancel post: {str(e)}")
    
    async def get_posting_gaps(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify gaps in posting schedule
        
        Args:
            user_id: User ID
            start_date: Start of analysis period
            end_date: End of analysis period
            platforms: Optional platforms to analyze
        
        Returns:
            List of date ranges with no scheduled posts
        """
        try:
            # Get all scheduled posts in date range
            posts = await self.get_calendar_posts(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                platforms=platforms,
                status='scheduled'
            )
            
            # Identify gaps (days with no posts)
            gaps = []
            current_date = start_date.date()
            end_date_only = end_date.date()
            
            while current_date <= end_date_only:
                # Check if any posts on this day
                has_post = any(
                    datetime.fromisoformat(post['scheduled_time']).date() == current_date
                    for post in posts
                )
                
                if not has_post:
                    gaps.append({
                        'date': current_date.isoformat(),
                        'platforms': platforms or ['all']
                    })
                
                current_date += timedelta(days=1)
            
            logger.info(f"Found {len(gaps)} posting gaps between {start_date} and {end_date}")
            return gaps
            
        except Exception as e:
            logger.error(f"Failed to identify posting gaps: {e}")
            raise ServiceError(f"Failed to identify posting gaps: {str(e)}")
    
    async def bulk_schedule(
        self,
        schedule_data: List[Dict[str, Any]]
    ) -> List[ScheduledPost]:
        """
        Schedule multiple posts at once
        
        Args:
            schedule_data: List of post scheduling data
        
        Returns:
            List of created ScheduledPost instances
        """
        try:
            scheduled_posts = []
            
            for data in schedule_data:
                post = await self.schedule_post(
                    clip_id=data.get('clip_id'),
                    content_variant_id=data.get('content_variant_id'),
                    platform=data['platform'],
                    scheduled_time=data['scheduled_time'],
                    platform_account_id=data.get('platform_account_id'),
                    is_ai_recommended=data.get('is_ai_recommended', False),
                    recommendation_score=data.get('recommendation_score'),
                    recommendation_reasoning=data.get('recommendation_reasoning')
                )
                scheduled_posts.append(post)
            
            logger.success(f"✓ Bulk scheduled {len(scheduled_posts)} posts")
            return scheduled_posts
            
        except Exception as e:
            logger.error(f"Failed to bulk schedule posts: {e}")
            raise ServiceError(f"Failed to bulk schedule posts: {str(e)}")
