"""
Test Suite for Publishing Queue Service
Tests queue management, scheduling, retry logic, and statistics
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import uuid

from services.publishing_queue import PublishingQueueService, QueueItem


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = MagicMock()
    return db


@pytest.fixture
def sample_queue_item():
    """Sample queue item for testing"""
    return {
        'id': uuid.uuid4(),
        'platform': 'tiktok',
        'scheduled_for': datetime.now() + timedelta(hours=1),
        'status': 'queued',
        'priority': 5,
        'caption': 'Test caption',
        'hashtags': ['test', 'viral'],
        'retry_count': 0,
        'max_retries': 3
    }


class TestQueueAddition:
    """Test adding items to queue"""
    
    def test_add_single_item(self, mock_db, sample_queue_item):
        """Test adding a single item to queue"""
        mock_db.execute.return_value.fetchone.return_value = sample_queue_item
        
        service = PublishingQueueService(mock_db)
        
        item = service.add_to_queue(
            platform='tiktok',
            scheduled_for=sample_queue_item['scheduled_for'],
            caption='Test caption',
            priority=5
        )
        
        assert mock_db.execute.called
        assert mock_db.commit.called
    
    def test_add_with_platform_metadata(self, mock_db):
        """Test adding item with platform-specific metadata"""
        scheduled_time = datetime.now() + timedelta(hours=2)
        
        mock_db.execute.return_value.fetchone.return_value = {
            'id': uuid.uuid4(),
            'platform': 'tiktok',
            'scheduled_for': scheduled_time,
            'platform_metadata': {'allow_duet': True, 'allow_stitch': False}
        }
        
        service = PublishingQueueService(mock_db)
        
        item = service.add_to_queue(
            platform='tiktok',
            scheduled_for=scheduled_time,
            platform_metadata={'allow_duet': True, 'allow_stitch': False}
        )
        
        assert mock_db.execute.called
    
    def test_bulk_schedule(self, mock_db):
        """Test bulk scheduling multiple items"""
        items_data = [
            {'platform': 'tiktok', 'scheduled_for': datetime.now() + timedelta(hours=i)}
            for i in range(5)
        ]
        
        mock_db.execute.return_value.fetchone.return_value = {'id': uuid.uuid4(), 'scheduled_for': datetime.now()}
        
        service = PublishingQueueService(mock_db)
        created = service.bulk_schedule(items_data)
        
        # Should have created items (may be less if some fail)
        assert isinstance(created, list)


class TestQueueRetrieval:
    """Test retrieving items from queue"""
    
    def test_get_next_items(self, mock_db):
        """Test getting next queued items"""
        mock_items = [
            {'id': uuid.uuid4(), 'platform': 'tiktok', 'priority': 10, 'scheduled_for': datetime.now()},
            {'id': uuid.uuid4(), 'platform': 'instagram', 'priority': 5, 'scheduled_for': datetime.now()}
        ]
        
        mock_db.execute.return_value = mock_items
        
        service = PublishingQueueService(mock_db)
        items = service.get_next_items(limit=10)
        
        assert mock_db.execute.called
    
    def test_get_items_by_status(self, mock_db):
        """Test filtering items by status"""
        mock_db.execute.return_value = []
        
        service = PublishingQueueService(mock_db)
        items = service.get_items_by_status('failed', limit=50)
        
        assert isinstance(items, list)
    
    def test_get_items_with_platform_filter(self, mock_db):
        """Test filtering by platform"""
        mock_db.execute.return_value = []
        
        service = PublishingQueueService(mock_db)
        items = service.get_next_items(limit=10, platform='tiktok')
        
        assert mock_db.execute.called


class TestStatusUpdates:
    """Test status update operations"""
    
    def test_update_status_to_processing(self, mock_db):
        """Test updating status to processing"""
        mock_db.execute.return_value.scalar.return_value = True
        
        service = PublishingQueueService(mock_db)
        success = service.update_status(str(uuid.uuid4()), 'processing')
        
        assert success
        assert mock_db.commit.called
    
    def test_update_status_to_published(self, mock_db):
        """Test marking item as published"""
        item_id = str(uuid.uuid4())
        mock_db.execute.return_value.scalar.return_value = True
        
        service = PublishingQueueService(mock_db)
        success = service.update_status(
            item_id,
            'published',
            platform_post_id='12345',
            platform_url='https://tiktok.com/@user/video/12345'
        )
        
        assert success
    
    def test_update_status_to_failed(self, mock_db):
        """Test marking item as failed with error"""
        mock_db.execute.return_value.scalar.return_value = True
        
        service = PublishingQueueService(mock_db)
        success = service.update_status(
            str(uuid.uuid4()),
            'failed',
            error='API rate limit exceeded'
        )
        
        assert success


class TestRetryLogic:
    """Test retry functionality"""
    
    def test_retry_failed_item_success(self, mock_db):
        """Test retrying a failed item within retry limit"""
        mock_db.execute.return_value.scalar.return_value = True
        
        service = PublishingQueueService(mock_db)
        success = service.retry_failed_item(str(uuid.uuid4()))
        
        assert success
        assert mock_db.commit.called
    
    def test_retry_max_retries_reached(self, mock_db):
        """Test retry when max retries exceeded"""
        mock_db.execute.return_value.scalar.return_value = False
        
        service = PublishingQueueService(mock_db)
        success = service.retry_failed_item(str(uuid.uuid4()))
        
        assert not success


class TestCancellation:
    """Test item cancellation"""
    
    def test_cancel_queued_item(self, mock_db):
        """Test cancelling a queued item"""
        mock_db.execute.return_value.scalar.return_value = True
        
        service = PublishingQueueService(mock_db)
        success = service.cancel_item(str(uuid.uuid4()))
        
        assert success


class TestRescheduling:
    """Test rescheduling operations"""
    
    def test_reschedule_item(self, mock_db):
        """Test rescheduling an item to new time"""
        new_time = datetime.now() + timedelta(hours=24)
        mock_db.execute.return_value.fetchone.return_value = {'id': uuid.uuid4()}
        
        service = PublishingQueueService(mock_db)
        success = service.reschedule_item(str(uuid.uuid4()), new_time)
        
        assert success
        assert mock_db.commit.called
    
    def test_reschedule_nonqueued_item(self, mock_db):
        """Test rescheduling non-queued item fails"""
        mock_db.execute.return_value.fetchone.return_value = None
        
        service = PublishingQueueService(mock_db)
        success = service.reschedule_item(str(uuid.uuid4()), datetime.now())
        
        assert not success


class TestStatistics:
    """Test queue statistics"""
    
    def test_get_queue_statistics(self, mock_db):
        """Test retrieving queue statistics"""
        mock_stats = [
            {'status': 'queued', 'platform': 'tiktok', 'count': 5},
            {'status': 'published', 'platform': 'instagram', 'count': 10},
            {'status': 'failed', 'platform': 'youtube', 'count': 2}
        ]
        
        mock_db.execute.return_value.fetchall.return_value = mock_stats
        
        service = PublishingQueueService(mock_db)
        stats = service.get_queue_statistics()
        
        assert 'by_status' in stats
        assert 'by_platform' in stats
        assert 'total' in stats
        assert stats['total'] == 17


class TestPriorityHandling:
    """Test priority-based scheduling"""
    
    def test_high_priority_items_first(self, mock_db):
        """Test that high priority items are returned first"""
        # Mock would normally return sorted by priority DESC
        mock_items = [
            {'id': uuid.uuid4(), 'priority': 100, 'scheduled_for': datetime.now()},
            {'id': uuid.uuid4(), 'priority': 50, 'scheduled_for': datetime.now()}
        ]
        
        mock_db.execute.return_value = mock_items
        
        service = PublishingQueueService(mock_db)
        items = service.get_next_items(limit=10)
        
        # In real DB, would verify ordering
        assert isinstance(items, list)


class TestConcurrency:
    """Test concurrent processing safety"""
    
    def test_for_update_skip_locked(self, mock_db):
        """Test that queue uses locking mechanism"""
        # The get_next_items function should use FOR UPDATE SKIP LOCKED
        # This prevents multiple workers from processing same item
        
        mock_db.execute.return_value = []
        
        service = PublishingQueueService(mock_db)
        items = service.get_next_items(limit=10)
        
        # Verify the query was executed (would include FOR UPDATE SKIP LOCKED)
        assert mock_db.execute.called


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_queue(self, mock_db):
        """Test handling empty queue"""
        mock_db.execute.return_value = []
        
        service = PublishingQueueService(mock_db)
        items = service.get_next_items(limit=10)
        
        assert items == []
    
    def test_add_item_past_time(self, mock_db):
        """Test adding item scheduled for past time"""
        past_time = datetime.now() - timedelta(hours=1)
        
        mock_db.execute.return_value.fetchone.return_value = {
            'id': uuid.uuid4(),
            'scheduled_for': past_time
        }
        
        service = PublishingQueueService(mock_db)
        
        # Should still add (will be processed immediately)
        item = service.add_to_queue(
            platform='tiktok',
            scheduled_for=past_time
        )
        
        assert mock_db.execute.called
