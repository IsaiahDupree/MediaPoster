"""
Celery Tasks for Scheduled Publishing
"""
from celery import shared_task
from datetime import datetime
from uuid import UUID
from loguru import logger

from database.connection import async_session_maker
from services.publisher_service import PublisherService


@shared_task(name='tasks.scheduled_publishing.check_scheduled_posts')
def check_scheduled_posts():
    """
    Periodic task to check for posts due for publishing
    Runs every minute via Celery Beat
    """
    import asyncio
    
    async def _check():
        async with async_session_maker() as db:
            try:
                publisher = PublisherService(db)
                due_posts = await publisher.get_posts_due_for_publishing()
                
                logger.info(f"Found {len(due_posts)} posts due for publishing")
                
                # Trigger publishing task for each post
                for post in due_posts:
                    publish_scheduled_post.delay(str(post.id))
                    logger.info(f"Queued post {post.id} for publishing")
                
                return len(due_posts)
                
            except Exception as e:
                logger.error(f"Error checking scheduled posts: {e}")
                return 0
    
    return asyncio.run(_check())


@shared_task(
    name='tasks.scheduled_publishing.publish_scheduled_post',
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def publish_scheduled_post(self, post_id: str):
    """
    Publish a single scheduled post
    
    Args:
        post_id: UUID of scheduled post as string
    """
    import asyncio
    
    async def _publish():
        async with async_session_maker() as db:
            try:
                publisher = PublisherService(db)
                post_uuid = UUID(post_id)
                
                result = await publisher.publish_scheduled_post(post_uuid)
                
                if result.success:
                    logger.success(f"✓ Successfully published post {post_id}")
                    return {
                        'success': True,
                        'post_id': post_id,
                        'platform_post_id': result.post_id,
                        'url': result.url
                    }
                else:
                    logger.error(f"✗ Failed to publish post {post_id}: {result.error}")
                    # Let the PublisherService handle retry logic
                    return {
                        'success': False,
                        'post_id': post_id,
                        'error': result.error
                    }
                    
            except Exception as e:
                logger.error(f"Error in publish task for {post_id}: {e}")
                # Retry the Celery task itself for transient errors
                raise self.retry(exc=e)
    
    return asyncio.run(_publish())


@shared_task(name='tasks.scheduled_publishing.retry_failed_posts')
def retry_failed_posts():
    """
    Periodic task to retry failed posts
    Runs every hour via Celery Beat
    """
    import asyncio
    
    async def _retry():
        async with async_session_maker() as db:
            try:
                publisher = PublisherService(db)
                retry_posts = await publisher.get_failed_posts_for_retry()
                
                logger.info(f"Found {len(retry_posts)} posts ready for retry")
                
                # Re-queue for publishing
                for post in retry_posts:
                    publish_scheduled_post.delay(str(post.id))
                    logger.info(f"Re-queued post {post.id} for retry")
                
                return len(retry_posts)
                
            except Exception as e:
                logger.error(f"Error retrying failed posts: {e}")
                return 0
    
    return asyncio.run(_retry())


@shared_task(name='tasks.scheduled_publishing.collect_post_metrics')
def collect_post_metrics():
    """
    Periodic task to collect metrics for recently published posts
    Runs every 15 minutes via Celery Beat
    """
    import asyncio
    from datetime import timedelta
    from database.models import ScheduledPost
    from sqlalchemy import select, and_
    
    async def _collect():
        async with async_session_maker() as db:
            try:
                # Find posts published in last 7 days
                cutoff_date = datetime.now() - timedelta(days=7)
                result = await db.execute(
                    select(ScheduledPost).where(
                        and_(
                            ScheduledPost.status == 'published',
                            ScheduledPost.published_at >= cutoff_date
                        )
                    )
                )
                
                published_posts = result.scalars().all()
                logger.info(f"Collecting metrics for {len(published_posts)} published posts")
                
                # For each post, collect metrics via platform adapters
                # This would integrate with MultiPlatformPublisher.collect_metrics
                metrics_collected = 0
                for post in published_posts:
                    try:
                        # TODO: Implement metric collection via publisher
                        # publisher = MultiPlatformPublisher(db)
                        # if post.platform_post_id:
                        #     hours_since = (datetime.now() - post.published_at).total_seconds() / 3600
                        #     publisher.collect_metrics(post_id, int(hours_since))
                        metrics_collected += 1
                    except Exception as e:
                        logger.warning(f"Failed to collect metrics for post {post.id}: {e}")
                
                logger.info(f"Collected metrics for {metrics_collected} posts")
                return metrics_collected
                
            except Exception as e:
                logger.error(f"Error collecting post metrics: {e}")
                return 0
    
    return asyncio.run(_collect())
