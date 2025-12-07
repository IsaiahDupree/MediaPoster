"""
Test Suite for Publisher Service
Tests publishing orchestration, retry logic, and status management
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from services.publisher_service import PublisherService
from services.exceptions import ServiceError
from services.platform_adapters.base import PublishResult


@pytest.fixture
def mock_db():
    """Mock async database session"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_scheduled_post():
    """Create a mock scheduled post"""
    post = Mock()
    post.id = uuid4()
    post.clip_id = uuid4()
    post.content_variant_id = None
    post.platform = "tiktok"
    post.scheduled_time = datetime.now() + timedelta(hours=1)
    post.status = "scheduled"
    post.retry_count = 0
    post.last_error = None
    return post


@pytest.fixture
def mock_clip():
    """Create a mock video clip"""
    clip = Mock()
    clip.id = uuid4()
    clip.file_path = "/path/to/video.mp4"
    clip.title = "Test Video"
    return clip


@pytest.fixture
def mock_variant():
    """Create a mock content variant"""
    variant = Mock()
    variant.id = uuid4()
    variant.caption = "Test caption #test"
    variant.title = "Test Title"
    variant.hashtags = ["test", "automation"]
    variant.thumbnail_url = "https://example.com/thumb.jpg"
    return variant


class TestPublishScheduledPost:
    """Test publishing scheduled posts"""
    
    @pytest.mark.asyncio
    async def test_publish_success(self, mock_db, mock_scheduled_post, mock_clip):
        """Test successfully publishing a post"""
        service = PublisherService(mock_db)
        
        # Setup mock database responses
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=mock_scheduled_post)
        
        clip_result = AsyncMock()
        clip_result.scalar_one_or_none = Mock(return_value=mock_clip)
        
        mock_db.execute = AsyncMock(side_effect=[post_result, clip_result, post_result])
        
        # Mock successful publish
        mock_publish_result = PublishResult(
            success=True,
            platform="tiktok",
            platform_post_id="platform_post_123",
            post_url="https://tiktok.com/@user/video/123"
        )
        
        with patch.object(service.multi_publisher, 'publish_to_platform', return_value=mock_publish_result):
            result = await service.publish_scheduled_post(mock_scheduled_post.id)
        
        assert result.success is True
        assert result.platform_post_id == "platform_post_123"
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_publish_post_not_found(self, mock_db):
        """Test publishing non-existent post fails"""
        service = PublisherService(mock_db)
        
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=post_result)
        
        with pytest.raises(ServiceError, match="not found"):
            await service.publish_scheduled_post(uuid4())
    
    @pytest.mark.asyncio
    async def test_publish_clip_not_found(self, mock_db, mock_scheduled_post):
        """Test publishing fails when clip is missing"""
        service = PublisherService(mock_db)
        
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=mock_scheduled_post)
        
        clip_result = AsyncMock()
        clip_result.scalar_one_or_none = Mock(return_value=None)
        
        mock_db.execute = AsyncMock(side_effect=[post_result, clip_result, post_result])
        
        with pytest.raises(ServiceError, match="Clip .* not found"):
            await service.publish_scheduled_post(mock_scheduled_post.id)
    
    @pytest.mark.asyncio
    async def test_publish_failure_triggers_retry(self, mock_db, mock_scheduled_post, mock_clip):
        """Test that publish failure triggers retry logic"""
        service = PublisherService(mock_db)
        
        # Setup mocks
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=mock_scheduled_post)
        
        clip_result = AsyncMock()
        clip_result.scalar_one_or_none = Mock(return_value=mock_clip)
        
        mock_db.execute = AsyncMock(side_effect=[post_result, clip_result, post_result, post_result])
        
        # Mock failed publish
        mock_publish_result = PublishResult(
            success=False,
            platform="tiktok",
            error_message="Platform API error: Rate limit exceeded"
        )
        
        with patch.object(service.multi_publisher, 'publish_to_platform', return_value=mock_publish_result):
            result = await service.publish_scheduled_post(mock_scheduled_post.id)
        
        assert result.success is False
        assert mock_scheduled_post.retry_count == 1
        assert mock_scheduled_post.status == "failed"


class TestRetryLogic:
    """Test retry functionality"""
    
    @pytest.mark.asyncio
    async def test_retry_increments_count(self, mock_db, mock_scheduled_post):
        """Test that retry count increments"""
        service = PublisherService(mock_db)
        
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=mock_scheduled_post)
        mock_db.execute = AsyncMock(return_value=post_result)
        
        await service.handle_publish_failure(mock_scheduled_post.id, "Test error")
        
        assert mock_scheduled_post.retry_count == 1
        assert mock_scheduled_post.status == "failed"
        assert mock_scheduled_post.next_retry_at is not None
    
    @pytest.mark.asyncio
    async def test_max_retries_reached(self, mock_db, mock_scheduled_post):
        """Test that max retries marks post as permanently failed"""
        service = PublisherService(mock_db)
        mock_scheduled_post.retry_count = 2  # Already tried twice
        
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=mock_scheduled_post)
        mock_db.execute = AsyncMock(return_value=post_result)
        
        await service.handle_publish_failure(mock_scheduled_post.id, "Final attempt failed")
        
        assert mock_scheduled_post.retry_count == 3
        assert mock_scheduled_post.status == "max_retries_reached"
        assert "Max retries reached" in mock_scheduled_post.last_error
    
    @pytest.mark.asyncio
    async def test_retry_delays_exponential(self, mock_db, mock_scheduled_post):
        """Test retry delays follow exponential backoff"""
        service = PublisherService(mock_db)
        
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=mock_scheduled_post)
        mock_db.execute = AsyncMock(return_value=post_result)
        
        # First retry: 5 minutes
        await service.handle_publish_failure(mock_scheduled_post.id, "Error 1")
        delay1 = (mock_scheduled_post.next_retry_at - datetime.now()).total_seconds()
        assert 290 < delay1 < 310  # ~5 minutes (300s)
        
        # Second retry: 15 minutes
        mock_scheduled_post.retry_count = 1
        mock_scheduled_post.next_retry_at = None
        await service.handle_publish_failure(mock_scheduled_post.id, "Error 2")
        delay2 = (mock_scheduled_post.next_retry_at - datetime.now()).total_seconds()
        assert 890 < delay2 < 910  # ~15 minutes (900s)


class TestStatusUpdates:
    """Test status update operations"""
    
    @pytest.mark.asyncio
    async def test_mark_as_publishing(self, mock_db, mock_scheduled_post):
        """Test marking post as publishing"""
        service = PublisherService(mock_db)
        
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=mock_scheduled_post)
        mock_db.execute = AsyncMock(return_value=post_result)
        
        result = await service.mark_post_as_publishing(mock_scheduled_post.id)
        
        assert result is True
        assert mock_scheduled_post.status == "publishing"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_as_published(self, mock_db, mock_scheduled_post):
        """Test marking post as published"""
        service = PublisherService(mock_db)
        
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=mock_scheduled_post)
        mock_db.execute = AsyncMock(return_value=post_result)
        
        platform_id = "platform_post_123"
        platform_url = "https://tiktok.com/@user/video/123"
        
        result = await service.mark_post_as_published(
            mock_scheduled_post.id,
            platform_id,
            platform_url
        )
        
        assert result is True
        assert mock_scheduled_post.status == "published"
        assert mock_scheduled_post.platform_post_id == platform_id
        assert mock_scheduled_post.platform_url == platform_url
        assert mock_scheduled_post.published_at is not None
        assert mock_scheduled_post.last_error is None
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_as_failed(self, mock_db, mock_scheduled_post):
        """Test marking post as failed"""
        service = PublisherService(mock_db)
        
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=mock_scheduled_post)
        mock_db.execute = AsyncMock(return_value=post_result)
        
        error_msg = "Platform API error: Authentication failed"
        result = await service.mark_post_as_failed(mock_scheduled_post.id, error_msg, 300)
        
        assert result is True
        assert mock_scheduled_post.status == "failed"
        assert mock_scheduled_post.last_error == error_msg
        assert mock_scheduled_post.next_retry_at is not None
        mock_db.commit.assert_called_once()


class TestPostRetrieval:
    """Test retrieving posts for publishing"""
    
    @pytest.mark.asyncio
    async def test_get_posts_due_for_publishing(self, mock_db):
        """Test getting posts that are due for publishing"""
        service = PublisherService(mock_db)
        
        # Create mock due posts
        now = datetime.now()
        post1 = Mock()
        post1.id = uuid4()
        post1.scheduled_time = now - timedelta(minutes=5)
        post1.status = "scheduled"
        
        post2 = Mock()
        post2.id = uuid4()
        post2.scheduled_time = now - timedelta(minutes=1)
        post2.status = "scheduled"
        
        result_mock = AsyncMock()
        result_mock.scalars = Mock(return_value=Mock(all=Mock(return_value=[post1, post2])))
        mock_db.execute = AsyncMock(return_value=result_mock)
        
        posts = await service.get_posts_due_for_publishing(now)
        
        assert len(posts) == 2
        assert posts[0].id == post1.id
        assert posts[1].id == post2.id
    
    @pytest.mark.asyncio
    async def test_get_failed_posts_for_retry(self, mock_db):
        """Test getting failed posts ready for retry"""
        service = PublisherService(mock_db)
        
        # Create mock failed post ready for retry
        now = datetime.now()
        post = Mock()
        post.id = uuid4()
        post.status = "failed"
        post.retry_count = 1
        post.next_retry_at = now - timedelta(minutes=1)  # Ready to retry
        
        result_mock = AsyncMock()
        result_mock.scalars = Mock(return_value=Mock(all=Mock(return_value=[post])))
        mock_db.execute = AsyncMock(return_value=result_mock)
        
        posts = await service.get_failed_posts_for_retry()
        
        assert len(posts) == 1
        assert posts[0].id == post.id
        assert posts[0].status == "failed"


class TestBatchPublishing:
    """Test batch publishing functionality"""
    
    @pytest.mark.asyncio
    async def test_publish_batch_all_success(self, mock_db):
        """Test batch publishing with all successes"""
        service = PublisherService(mock_db)
        
        post_ids = [uuid4(), uuid4(), uuid4()]
        
        # Mock successful publishes
        success_result = PublishResult(
            success=True,
            platform="tiktok",
            platform_post_id="platform_123",
            post_url="https://example.com/post"
        )
        
        with patch.object(service, 'publish_scheduled_post', return_value=success_result):
            results = await service.publish_batch(post_ids)
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_publish_batch_mixed_results(self, mock_db):
        """Test batch publishing with mixed success/failure"""
        service = PublisherService(mock_db)
        
        post_ids = [uuid4(), uuid4(), uuid4()]
        
        # Mock mixed results
        results_sequence = [
            PublishResult(success=True, platform="tiktok", platform_post_id="123"),
            PublishResult(success=False, platform="tiktok", error_message="Rate limit"),
            PublishResult(success=True, platform="tiktok", platform_post_id="456")
        ]
        
        with patch.object(service, 'publish_scheduled_post', side_effect=results_sequence):
            results = await service.publish_batch(post_ids)
        
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
    
    @pytest.mark.asyncio
    async def test_publish_batch_handles_exceptions(self, mock_db):
        """Test batch publishing handles individual exceptions"""
        service = PublisherService(mock_db)
        
        post_ids = [uuid4(), uuid4()]
        
        # First succeeds, second raises exception
        def side_effect(post_id):
            if post_id == post_ids[0]:
                return PublishResult(success=True, platform="tiktok", platform_post_id="123")
            raise ServiceError("Post not found")
        
        with patch.object(service, 'publish_scheduled_post', side_effect=side_effect):
            results = await service.publish_batch(post_ids)
        
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "not found" in results[1].error_message


class TestContentVariantPublishing:
    """Test publishing with content variants"""
    
    @pytest.mark.asyncio
    async def test_publish_with_variant(self, mock_db, mock_scheduled_post, mock_variant):
        """Test publishing post with content variant"""
        service = PublisherService(mock_db)
        mock_scheduled_post.content_variant_id = mock_variant.id
        
        post_result = AsyncMock()
        post_result.scalar_one_or_none = Mock(return_value=mock_scheduled_post)
        
        variant_result = AsyncMock()
        variant_result.scalar_one_or_none = Mock(return_value=mock_variant)
        
        mock_db.execute = AsyncMock(side_effect=[post_result, variant_result, post_result])
        
        mock_publish_result = PublishResult(
            success=True,
            platform="tiktok",
            platform_post_id="variant_post_123"
        )
        
        with patch.object(service.multi_publisher, 'publish_to_platform', return_value=mock_publish_result):
            result = await service.publish_scheduled_post(mock_scheduled_post.id)
        
        assert result.success is True
        # Verify variant data was used in publish request
        service.multi_publisher.publish_to_platform.assert_called_once()
