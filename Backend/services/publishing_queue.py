"""
Publishing Queue Service
Manages scheduled multi-platform content publishing with priority and retry logic
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
import uuid

from database.models import VideoClip, ContentItem, PlatformPost

logger = logging.getLogger(__name__)


class QueueItem:
    """Represents a publishing queue item"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.content_item_id = kwargs.get('content_item_id')
        self.clip_id = kwargs.get('clip_id')
        self.scheduled_for = kwargs.get('scheduled_for')
        self.priority = kwargs.get('priority', 0)
        self.status = kwargs.get('status', 'queued')
        self.retry_count = kwargs.get('retry_count', 0)
        self.max_retries = kwargs.get('max_retries', 3)
        self.platform = kwargs.get('platform')
        self.platform_metadata = kwargs.get('platform_metadata', {})
        self.caption = kwargs.get('caption')
        self.hashtags = kwargs.get('hashtags', [])
        self.thumbnail_url = kwargs.get('thumbnail_url')
        self.video_url = kwargs.get('video_url')
        self.last_error = kwargs.get('last_error')
        self.platform_post_id = kwargs.get('platform_post_id')
        self.platform_url = kwargs.get('platform_url')
        self.published_at = kwargs.get('published_at')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')


class PublishingQueueService:
    """
    Service for managing scheduled publishing queue
    
    Features:
    - Priority-based scheduling
    - Automatic retry with backoff
    - Platform-specific metadata
    - Concurrent processing safety
    - Queue statistics and monitoring
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def add_to_queue(
        self,
        platform: str,
        scheduled_for: datetime,
        content_item_id: Optional[str] = None,
        clip_id: Optional[str] = None,
        caption: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
        video_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        priority: int = 0,
        platform_metadata: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> QueueItem:
        """
        Add item to publishing queue
        
        Args:
            platform: Platform name (tiktok, instagram, etc.)
            scheduled_for: When to publish
            content_item_id: Optional content item reference
            clip_id: Optional clip reference
            caption: Post caption
            hashtags: List of hashtags
            video_url: URL to video file
            thumbnail_url: URL to thumbnail
            priority: Priority (0-100, higher = more important)
            platform_metadata: Platform-specific settings
            user_id: User creating the queue item
            
        Returns:
            Created QueueItem
        """
        # Create queue item
        query = """
        INSERT INTO publishing_queue (
            platform, scheduled_for, content_item_id, clip_id,
            caption, hashtags, video_url, thumbnail_url, priority,
            platform_metadata, created_by
        VALUES (
            :platform, :scheduled_for, :content_item_id, :clip_id,
            :caption, :hashtags, :video_url, :thumbnail_url, :priority,
            :platform_metadata, :created_by
        )
        RETURNING *
        """
        
        result = self.db.execute(query, {
            'platform': platform,
            'scheduled_for': scheduled_for,
            'content_item_id': uuid.UUID(content_item_id) if content_item_id else None,
            'clip_id': uuid.UUID(clip_id) if clip_id else None,
            'caption': caption,
            'hashtags': hashtags or [],
            'video_url': video_url,
            'thumbnail_url': thumbnail_url,
            'priority': priority,
            'platform_metadata': platform_metadata or {},
            'created_by': uuid.UUID(user_id) if user_id else None
        })
        
        self.db.commit()
        row = result.fetchone()
        
        logger.info(f"Added item to queue: {row['id']} for {platform} at {scheduled_for}")
        
        return QueueItem(**dict(row))
    
    def get_next_items(
        self,
        limit: int = 10,
        platform: Optional[str] = None
    ) -> List[QueueItem]:
        """
        Get next items ready to be processed
        
        Uses FOR UPDATE SKIP LOCKED to prevent concurrent processing
        
        Args:
            limit: Maximum number of items to return
            platform: Optional platform filter
            
        Returns:
            List of QueueItem objects
        """
        query = """
        SELECT * FROM get_next_queue_items(:limit, :platform)
        """
        
        result = self.db.execute(query, {
            'limit': limit,
            'platform': platform
        })
        
        items = [QueueItem(**dict(row)) for row in result]
        
        logger.info(f"Retrieved {len(items)} items from queue")
        
        return items
    
    def update_status(
        self,
        item_id: str,
        status: str,
        error: Optional[str] = None,
        platform_post_id: Optional[str] = None,
        platform_url: Optional[str] = None
    ) -> bool:
        """
        Update queue item status
        
        Args:
            item_id: Queue item UUID
            status: New status (queued, processing, published, failed, cancelled)
            error: Optional error message
            platform_post_id: Platform's post ID
            platform_url: Published post URL
            
        Returns:
            True if updated successfully
        """
        query = """
        SELECT update_queue_status(
            :item_id, :status, :error, :platform_post_id, :platform_url
        )
        """
        
        result = self.db.execute(query, {
            'item_id': uuid.UUID(item_id),
            'status': status,
            'error': error,
            'platform_post_id': platform_post_id,
            'platform_url': platform_url
        })
        
        self.db.commit()
        success = result.scalar()
        
        logger.info(f"Updated queue item {item_id} to status: {status}")
        
        return success
    
    def retry_failed_item(self, item_id: str) -> bool:
        """
        Retry a failed queue item
        
        Args:
            item_id: Queue item UUID
            
        Returns:
            True if retry was scheduled, False if max retries reached
        """
        query = "SELECT retry_queue_item(:item_id)"
        
        result = self.db.execute(query, {'item_id': uuid.UUID(item_id)})
        self.db.commit()
        
        success = result.scalar()
        
        if success:
            logger.info(f"Scheduled retry for queue item {item_id}")
        else:
            logger.warning(f"Cannot retry {item_id} - max retries reached")
        
        return success
    
    def cancel_item(self, item_id: str) -> bool:
        """
        Cancel a queued item
        
        Args:
            item_id: Queue item UUID
            
        Returns:
            True if cancelled successfully
        """
        return self.update_status(item_id, 'cancelled')
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """
        Get queue statistics by status and platform
        
        Returns:
            Dictionary with statistics
        """
        query = "SELECT * FROM get_queue_statistics()"
        
        result = self.db.execute(query)
        rows = result.fetchall()
        
        # Organize by status and platform
        stats = {
            'by_status': {},
            'by_platform': {},
            'total': 0
        }
        
        for row in rows:
            status = row['status']
            platform = row['platform']
            count = row['count']
            
            # By status
            if status not in stats['by_status']:
                stats['by_status'][status] = 0
            stats['by_status'][status] += count
            
            # By platform
            if platform not in stats['by_platform']:
                stats['by_platform'][platform] = 0
            stats['by_platform'][platform] += count
            
            stats['total'] += count
        
        return stats
    
    def get_items_by_status(
        self,
        status: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[QueueItem]:
        """
        Get queue items filtered by status
        
        Args:
            status: Status to filter by
            limit: Maximum number of items
            offset: Pagination offset
            
        Returns:
            List of QueueItem objects
        """
        query = """
        SELECT * FROM publishing_queue
        WHERE status = :status
        ORDER BY priority DESC, scheduled_for ASC
        LIMIT :limit OFFSET :offset
        """
        
        result = self.db.execute(query, {
            'status': status,
            'limit': limit,
            'offset': offset
        })
        
        return [QueueItem(**dict(row)) for row in result]
    
    def bulk_schedule(
        self,
        items: List[Dict[str, Any]]
    ) -> List[QueueItem]:
        """
        Add multiple items to queue in bulk
        
        Args:
            items: List of item dictionaries
            
        Returns:
            List of created QueueItem objects
        """
        created_items = []
        
        for item_data in items:
            try:
                queue_item = self.add_to_queue(**item_data)
                created_items.append(queue_item)
            except Exception as e:
                logger.error(f"Error adding item to queue: {e}")
                continue
        
        logger.info(f"Bulk scheduled {len(created_items)} items")
        
        return created_items
    
    def reschedule_item(
        self,
        item_id: str,
        new_scheduled_time: datetime
    ) -> bool:
        """
        Reschedule a queued item to a new time
        
        Args:
            item_id: Queue item UUID
            new_scheduled_time: New scheduled time
            
        Returns:
            True if rescheduled successfully
        """
        query = """
        UPDATE publishing_queue
        SET scheduled_for = :new_time
        WHERE id = :item_id AND status = 'queued'
        RETURNING id
        """
        
        result = self.db.execute(query, {
            'item_id': uuid.UUID(item_id),
            'new_time': new_scheduled_time
        })
        
        self.db.commit()
        
        success = result.fetchone() is not None
        
        if success:
            logger.info(f"Rescheduled item {item_id} to {new_scheduled_time}")
        
        return success
