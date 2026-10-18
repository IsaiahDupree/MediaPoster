"""
Publisher Service - High-level orchestration of publishing process
Integrating calendar service with multi-platform publisher
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from loguru import logger

from database.models import ScheduledPost, VideoClip, ContentVariant
from services.multi_platform_publisher import MultiPlatformPublisher
from services.platform_adapters.base import PublishRequest, PublishResult
from services.exceptions import ServiceError


class PublisherService:
    """Service for orchestrating scheduled post publishing"""
    
    MAX_RETRIES = 3
    RETRY_DELAYS = [300, 900, 3600]  # 5min, 15min, 1hour in seconds
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.multi_publisher = MultiPlatformPublisher(db)
    
    async def publish_scheduled_post(self, post_id: UUID, skip_status_check: bool = False) -> PublishResult:
        """
        Publish a single scheduled post
        
        NOTE: If skip_status_check=False, this will attempt to atomically mark
        the post as 'publishing'. If another process already did so, it will fail.
        Set skip_status_check=True if you've already called mark_post_as_publishing().
        
        Args:
            post_id: ID of scheduled post
            skip_status_check: If True, skip the atomic status update (assumes already 'publishing')
            
        Returns:
            PublishResult with status and platform post ID
        """
        try:
            # Atomically mark as publishing (unless caller already did so)
            if not skip_status_check:
                can_publish = await self.mark_post_as_publishing(post_id)
                if not can_publish:
                    raise ServiceError(
                        f"Post {post_id} could not be marked as publishing "
                        f"(already processing or not found)"
                    )
            
            # Get scheduled post
            result = await self.db.execute(
                select(ScheduledPost).where(ScheduledPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            
            if not post:
                raise ServiceError(f"Scheduled post {post_id} not found")
            
            # Verify post is in 'publishing' status
            if post.status != 'publishing':
                raise ServiceError(
                    f"Post {post_id} is not in 'publishing' status (current: {post.status})"
                )
            
            # Get content (clip or variant)
            clip = None
            variant = None
            
            if post.clip_id:
                clip_result = await self.db.execute(
                    select(VideoClip).where(VideoClip.id == post.clip_id)
                )
                clip = clip_result.scalar_one_or_none()
                
                if not clip:
                    raise ServiceError(f"Clip {post.clip_id} not found")
            
            if post.content_variant_id:
                variant_result = await self.db.execute(
                    select(ContentVariant).where(ContentVariant.id == post.content_variant_id)
                )
                variant = variant_result.scalar_one_or_none()
            
            # Build publish request
            request = PublishRequest(
                video_path=clip.file_path if clip else "",
                caption=variant.caption if variant else (clip.title if clip else ""),
                title=variant.title if variant else (clip.title if clip else ""),
                hashtags=variant.hashtags if variant else [],
                thumbnail_path=variant.thumbnail_url if variant else None,
                scheduled_time=None  # Publish immediately
            )
            
            #  Publish to platform
            logger.info(f"Publishing post {post_id} to {post.platform}")
            publish_result = await self.multi_publisher.publish_to_platform(
                platform=post.platform,
                request=request,
                content_variant_id=post.content_variant_id,
                clip_id=post.clip_id
            )
            
            # Update post status based on result
            if publish_result.success:
                await self.mark_post_as_published(
                    post_id=post_id,
                    platform_post_id=publish_result.platform_post_id,
                    platform_url=publish_result.post_url
                )
                logger.success(f"✓ Published post {post_id} to {post.platform}")
            else:
                await self.handle_publish_failure(
                    post_id=post_id,
                    error=publish_result.error_message or "Unknown error"
                )
                logger.error(f"✗ Failed to publish post {post_id}: {publish_result.error_message}")
            
            return publish_result
            
        except Exception as e:
            logger.error(f"Error publishing post {post_id}: {e}")
            await self.handle_publish_failure(post_id, str(e))
            raise ServiceError(f"Failed to publish post: {str(e)}")
    
    async def publish_batch(self, post_ids: list[UUID]) -> list[PublishResult]:
        """
        Publish multiple posts
        
        Args:
            post_ids: List of post IDs to publish
            
        Returns:
            List of PublishResults
        """
        results = []
        for post_id in post_ids:
            try:
                result = await self.publish_scheduled_post(post_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to publish {post_id} in batch: {e}")
                results.append(PublishResult(
                    success=False,
                    platform="unknown",
                    error_message=str(e)
                ))
        
        return results
    
    async def mark_post_as_publishing(self, post_id: UUID) -> bool:
        """
        Atomically mark post status as 'publishing' only if still 'scheduled'
        
        This prevents race conditions where multiple workers try to publish
        the same post simultaneously.
        
        Args:
            post_id: Post ID
            
        Returns:
            True if updated (i.e., post was in 'scheduled' state and is now 'publishing')
        """
        try:
            # ATOMIC UPDATE: Only update if status is still 'scheduled'
            # This prevents multiple workers from both marking the same post as 'publishing'
            result = await self.db.execute(
                update(ScheduledPost)
                .where(
                    ScheduledPost.id == post_id,
                    ScheduledPost.status == 'scheduled'  # Only update if still scheduled
                )
                .values(status='publishing')
            )
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Atomically marked post {post_id} as publishing")
                return True
            else:
                # Post not found or already in different status
                logger.warning(f"Could not mark post {post_id} as publishing (not found or already processing)")
                return False
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to mark post as publishing: {e}")
            return False
    
    async def mark_post_as_published(
        self,
        post_id: UUID,
        platform_post_id: str,
        platform_url: Optional[str] = None
    ) -> bool:
        """
        Atomically mark post as successfully published
        
        Uses atomic UPDATE to prevent race conditions and ensure all fields
        are updated together in a transaction.
        
        Args:
            post_id: Post ID
            platform_post_id: Platform's post ID
            platform_url: URL to published post
            
        Returns:
            True if updated
        """
        try:
            # ATOMIC UPDATE: Update all fields in one transaction
            result = await self.db.execute(
                update(ScheduledPost)
                .where(ScheduledPost.id == post_id)
                .values(
                    status='published',
                    published_at=datetime.now(),
                    platform_post_id=platform_post_id,
                    platform_url=platform_url,
                    last_error=None,  # Clear any previous errors
                    error_message=None  # Clear error message too
                )
            )
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Atomically marked post {post_id} as published")
                return True
            else:
                logger.warning(f"Post {post_id} not found for marking as published")
                return False
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to mark post as published: {e}")
            return False
    
    async def mark_post_as_failed(
        self,
        post_id: UUID,
        error: str,
        retry_in_seconds: Optional[int] = None
    ) -> bool:
        """
        Atomically mark post as failed
        
        Args:
            post_id: Post ID
            error: Error message
            retry_in_seconds: Seconds until next retry (None = no retry)
            
        Returns:
            True if updated
        """
        try:
            update_values = {
                'status': 'failed',
                'last_error': error,
                'error_message': error
            }
            
            if retry_in_seconds:
                update_values['next_retry_at'] = datetime.now() + timedelta(seconds=retry_in_seconds)
            
            # ATOMIC UPDATE: Update all fields in one transaction
            result = await self.db.execute(
                update(ScheduledPost)
                .where(ScheduledPost.id == post_id)
                .values(**update_values)
            )
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Atomically marked post {post_id} as failed")
                return True
            else:
                logger.warning(f"Post {post_id} not found for marking as failed")
                return False
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to mark post as failed: {e}")
            return False
    
    async def handle_publish_failure(self, post_id: UUID, error: str) -> None:
        """
        Handle publish failure with retry logic
        
        Uses atomic updates to prevent race conditions.
        
        Args:
            post_id: Post ID
            error: Error message
        """
        try:
            # Get current retry count atomically
            result = await self.db.execute(
                select(ScheduledPost).where(ScheduledPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            
            if not post:
                logger.warning(f"Post {post_id} not found for failure handling")
                return
            
            # Increment retry count
            new_retry_count = (post.retry_count or 0) + 1
            
            # Check if we should retry
            if new_retry_count < self.MAX_RETRIES:
                # Schedule retry with exponential backoff
                retry_delay = self.RETRY_DELAYS[new_retry_count - 1]
                await self.mark_post_as_failed(post_id, error, retry_delay)
                logger.warning(
                    f"Post {post_id} failed ({new_retry_count}/{self.MAX_RETRIES}). "
                    f"Retrying in {retry_delay}s"
                )
            else:
                # Max retries reached - use atomic update
                from sqlalchemy import update
                await self.db.execute(
                    update(ScheduledPost)
                    .where(ScheduledPost.id == post_id)
                    .values(
                        status='max_retries_reached',
                        last_error=f"Max retries reached. Last error: {error}",
                        error_message=f"Max retries reached. Last error: {error}"
                    )
                )
                await self.db.commit()
                logger.error(f"Post {post_id} failed permanently after {self.MAX_RETRIES} retries")
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error handling failure for post {post_id}: {e}")
    
    async def get_posts_due_for_publishing(self, cutoff_time: Optional[datetime] = None) -> list[ScheduledPost]:
        """
        Get posts that are due for publishing
        
        NOTE: This method is used by Celery tasks. The PostScheduler uses
        its own _get_due_posts() method with FOR UPDATE SKIP LOCKED for
        proper concurrency control.
        
        Args:
            cutoff_time: Posts scheduled before this time (default: now)
            
        Returns:
            List of scheduled posts
        """
        if not cutoff_time:
            cutoff_time = datetime.now()
        
        try:
            # NOTE: This query does NOT use FOR UPDATE SKIP LOCKED
            # The actual publishing should use mark_post_as_publishing() which
            # atomically updates status, preventing race conditions
            result = await self.db.execute(
                select(ScheduledPost).where(
                    ScheduledPost.scheduled_time <= cutoff_time,
                    ScheduledPost.status == 'scheduled'
                ).order_by(ScheduledPost.scheduled_time.asc())
            )
            
            posts = result.scalars().all()
            logger.info(f"Found {len(posts)} posts due for publishing")
            return list(posts)
            
        except Exception as e:
            logger.error(f"Error getting due posts: {e}")
            return []
    
    async def get_failed_posts_for_retry(self) -> list[ScheduledPost]:
        """
        Get failed posts that are ready for retry
        
        Returns:
            List of posts to retry
        """
        try:
            now = datetime.now()
            result = await self.db.execute(
                select(ScheduledPost).where(
                    ScheduledPost.status == 'failed',
                    ScheduledPost.retry_count < self.MAX_RETRIES,
                    ScheduledPost.next_retry_at <= now
                )
            )
            
            posts = result.scalars().all()
            logger.info(f"Found {len(posts)} posts ready for retry")
            return list(posts)
            
        except Exception as e:
            logger.error(f"Error getting retry posts: {e}")
            return []
