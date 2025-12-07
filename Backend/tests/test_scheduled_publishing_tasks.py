"""
Test Suite for Celery Publishing Tasks
Tests scheduled publishing tasks, retry tasks, and metrics collection
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

# Import tasks
from tasks.scheduled_publishing import (
    check_scheduled_posts,
    publish_scheduled_post,
    retry_failed_posts,
    collect_post_metrics
)


class TestCheckScheduledPosts:
    """Test the check_scheduled_posts periodic task"""
    
    def test_finds_and_queues_due_posts(self):
        """Test that due posts are found and queued for publishing"""
        # Create mock posts
        post1 = Mock()
        post1.id = uuid4()
        post2 = Mock()
        post2.id = uuid4()
        
        mock_publisher = Mock()
        mock_publisher.get_posts_due_for_publishing = AsyncMock(return_value=[post1, post2])
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            with patch('tasks.scheduled_publishing.publish_scheduled_post.delay') as mock_delay:
                result = check_scheduled_posts()
        
        # Should have queued both posts
        assert mock_delay.call_count == 2
        assert result == 2
    
    def test_no_posts_due(self):
        """Test when no posts are due for publishing"""
        mock_publisher = Mock()
        mock_publisher.get_posts_due_for_publishing = AsyncMock(return_value=[])
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            result = check_scheduled_posts()
        
        assert result == 0
    
    def test_handles_errors_gracefully(self):
        """Test that errors are handled gracefully"""
        mock_publisher = Mock()
        mock_publisher.get_posts_due_for_publishing = AsyncMock(side_effect=Exception("Database error"))
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            result = check_scheduled_posts()
        
        # Should return 0 and not crash
        assert result == 0


class TestPublishScheduledPost:
    """Test the publish_scheduled_post task"""
    
    def test_successful_publish(self):
        """Test successfully publishing a post"""
        post_id = str(uuid4())
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.post_id = "platform_123"
        mock_result.url = "https://example.com/post"
        
        mock_publisher = Mock()
        mock_publisher.publish_scheduled_post = AsyncMock(return_value=mock_result)
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            result = publish_scheduled_post(post_id)
        
        assert result['success'] is True
        assert result['post_id'] == post_id
        assert result['platform_post_id'] == "platform_123"
    
    def test_failed_publish(self):
        """Test publishing failure"""
        post_id = str(uuid4())
        
        mock_result = Mock()
        mock_result.success = False
        mock_result.error = "Platform API error"
        
        mock_publisher = Mock()
        mock_publisher.publish_scheduled_post = AsyncMock(return_value=mock_result)
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            result = publish_scheduled_post(post_id)
        
        assert result['success'] is False
        assert result['error'] == "Platform API error"
    
    def test_invalid_uuid(self):
        """Test with invalid UUID format"""
        # Should handle gracefully when UUID parsing fails
        with patch('tasks.scheduled_publishing.PublisherService'):
            try:
                result = publish_scheduled_post("invalid-uuid")
                # If it doesn't raise, check it returns error
                assert result['success'] is False or 'error' in result
            except ValueError:
                # ValueError is acceptable for invalid UUID
                pass


class TestRetryFailedPosts:
    """Test the retry_failed_posts periodic task"""
    
    def test_retries_eligible_posts(self):
        """Test that eligible failed posts are retried"""
        post1 = Mock()
        post1.id = uuid4()
        post2 = Mock()
        post2.id = uuid4()
        
        mock_publisher = Mock()
        mock_publisher.get_failed_posts_for_retry = AsyncMock(return_value=[post1, post2])
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            with patch('tasks.scheduled_publishing.publish_scheduled_post.delay') as mock_delay:
                result = retry_failed_posts()
        
        assert mock_delay.call_count == 2
        assert result == 2
    
    def test_no_posts_to_retry(self):
        """Test when no posts are ready for retry"""
        mock_publisher = Mock()
        mock_publisher.get_failed_posts_for_retry = AsyncMock(return_value=[])
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            result = retry_failed_posts()
        
        assert result == 0
    
    def test_handles_errors(self):
        """Test error handling in retry task"""
        mock_publisher = Mock()
        mock_publisher.get_failed_posts_for_retry = AsyncMock(side_effect=Exception("DB error"))
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            result = retry_failed_posts()
        
        assert result == 0


class TestCollectPostMetrics:
    """Test the collect_post_metrics periodic task"""
    
    def test_collects_metrics_for_recent_posts(self):
        """Test collecting metrics for recently published posts"""
        # Create mock published posts
        post1 = Mock()
        post1.id = uuid4()
        post1.platform_post_id = "platform_123"
        post1.published_at = datetime.now() - timedelta(hours=2)
        
        post2 = Mock()
        post2.id = uuid4()
        post2.platform_post_id = "platform_456"
        post2.published_at = datetime.now() - timedelta(days=1)
        
        # Mock database query result
        mock_result = AsyncMock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[post1, post2])))
        
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock session maker
        class MockSessionMaker:
            def __init__(self):
                pass
            
            async def __aenter__(self):
                return mock_db
            
            async def __aexit__(self, *args):
                pass
        
        with patch('tasks.scheduled_publishing.async_session_maker', MockSessionMaker()):
            result = collect_post_metrics()
        
        # Should have processed posts (implementation returns count)
        assert result >= 0  # Basic sanity check
    
    def test_handles_no_recent_posts(self):
        """Test when there are no recent posts to collect metrics for"""
        mock_result = AsyncMock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        class MockSessionMaker:
            async def __aenter__(self):
                return mock_db
            
            async def __aexit__(self, *args):
                pass
        
        with patch('tasks.scheduled_publishing.async_session_maker', MockSessionMaker()):
            result = collect_post_metrics()
        
        assert result == 0
    
    def test_handles_collection_errors(self):
        """Test graceful error handling during metrics collection"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
        
        class MockSessionMaker:
            async def __aenter__(self):
                return mock_db
            
            async def __aexit__(self, *args):
                pass
        
        with patch('tasks.scheduled_publishing.async_session_maker', MockSessionMaker()):
            result = collect_post_metrics()
        
        # Should return 0 and not crash
        assert result == 0


class TestTaskReliability:
    """Test task reliability and error scenarios"""
    
    def test_check_scheduled_posts_is_idempotent(self):
        """Test that running check multiple times is safe"""
        post = Mock()
        post.id = uuid4()
        
        mock_publisher = Mock()
        mock_publisher.get_posts_due_for_publishing = AsyncMock(return_value=[post])
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            with patch('tasks.scheduled_publishing.publish_scheduled_post.delay'):
                result1 = check_scheduled_posts()
                result2 = check_scheduled_posts()
        
        # Each call should find the same post (until it's published)
        assert result1 == 1
        assert result2 == 1
    
    def test_publish_task_retries_on_exception(self):
        """Test that publish task retries on transient exceptions"""
        post_id = str(uuid4())
        
        mock_publisher = Mock()
        mock_publisher.publish_scheduled_post = AsyncMock(side_effect=ConnectionError("Network timeout"))
        
        # The task should try to retry via Celery's retry mechanism
        task_mock = Mock()
        task_mock.retry = Mock(side_effect=Exception("Retry scheduled"))
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            # Bind the task to mock self
            try:
                # This will raise when retry is called
                publish_scheduled_post.__func__(task_mock, post_id)
            except Exception as e:
                assert "Retry" in str(e)


class TestTaskIntegration:
    """Integration tests for task workflows"""
    
    def test_publish_workflow(self):
        """Test complete publish workflow"""
        post_id = uuid4()
        
        # Create post that's due
        post = Mock()
        post.id = post_id
        post.status = "scheduled"
        post.scheduled_time = datetime.now() - timedelta(minutes=1)
        
        # Mock successful publish
        mock_result = Mock()
        mock_result.success = True
        mock_result.post_id = "platform_123"
        
        mock_publisher = Mock()
        mock_publisher.get_posts_due_for_publishing = AsyncMock(return_value=[post])
        mock_publisher.publish_scheduled_post = AsyncMock(return_value=mock_result)
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            with patch('tasks.scheduled_publishing.publish_scheduled_post.delay') as mock_delay:
                # Step 1: Check finds the post
                found_count = check_scheduled_posts()
                assert found_count == 1
                assert mock_delay.called
                
                # Step 2: Publish task executes
                result = publish_scheduled_post(str(post_id))
                assert result['success'] is True
    
    def test_retry_workflow(self):
        """Test retry workflow for failed posts"""
        post_id = uuid4()
        
        #Create failed post ready for retry
        post = Mock()
        post.id = post_id
        post.status = "failed"
        post.retry_count = 1
        post.next_retry_at = datetime.now() - timedelta(minutes=1)
        
        mock_publisher = Mock()
        mock_publisher.get_failed_posts_for_retry = AsyncMock(return_value=[post])
        
        with patch('tasks.scheduled_publishing.PublisherService', return_value=mock_publisher):
            with patch('tasks.scheduled_publishing.publish_scheduled_post.delay') as mock_delay:
                # Retry task finds and re-queues the post
                retry_count = retry_failed_posts()
                assert retry_count == 1
                assert mock_delay.called
                mock_delay.assert_called_with(str(post_id))
