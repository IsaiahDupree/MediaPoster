"""
Comprehensive Test Suite for Auto-Engagement System

Tests cover:
1. CommentTracker - duplicate detection, daily limits
2. EngagementService - pub/sub integration, controllability
3. EngagementWorker - event handling, workflow
4. Integration tests - end-to-end flow

Run with: pytest tests/test_engagement.py -v
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.event_bus import EventBus, Topics, Event
from services.engagement.comment_tracker import CommentTracker, PlatformStatus
from services.engagement.engagement_service import EngagementService, EngagementRequest
from services.workers.engagement_worker import EngagementWorker


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def event_bus():
    """Create a fresh EventBus for testing."""
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = MagicMock()
    
    # Default responses
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[], count=0)
    mock.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': str(uuid4())}])
    mock.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])
    
    return mock


@pytest.fixture
def tracker(mock_supabase):
    """Create a CommentTracker with mocked Supabase."""
    t = CommentTracker(supabase_client=mock_supabase)
    return t


@pytest.fixture
def service(event_bus, tracker):
    """Create an EngagementService for testing."""
    return EngagementService(event_bus=event_bus, tracker=tracker)


@pytest.fixture
def worker(event_bus):
    """Create an EngagementWorker for testing."""
    w = EngagementWorker(event_bus=event_bus, worker_id="test-worker")
    return w


# ============================================================================
# CommentTracker Tests
# ============================================================================

class TestCommentTracker:
    """Tests for CommentTracker."""
    
    @pytest.mark.asyncio
    async def test_has_commented_on_returns_false_for_new_post(self, tracker, mock_supabase):
        """Should return False when we haven't commented on a post."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        result = await tracker.has_commented_on('threads', 'https://threads.net/@user/post/123')
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_has_commented_on_returns_true_for_existing_post(self, tracker, mock_supabase):
        """Should return True when we've already commented on a post."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{'id': 'existing-id'}]
        )
        
        result = await tracker.has_commented_on('threads', 'https://threads.net/@user/post/123')
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_record_comment_creates_entry(self, tracker, mock_supabase):
        """Should create a new comment record."""
        comment_id = str(uuid4())
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{'id': comment_id}]
        )
        
        result = await tracker.record_comment(
            platform='threads',
            post_url='https://threads.net/@user/post/123',
            comment_text='Great post!',
            post_username='user'
        )
        
        assert result == comment_id
        mock_supabase.table.assert_called_with('engagement_comments')
    
    @pytest.mark.asyncio
    async def test_record_comment_raises_on_duplicate(self, tracker, mock_supabase):
        """Should raise ValueError on duplicate comment."""
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )
        
        with pytest.raises(ValueError) as exc:
            await tracker.record_comment(
                platform='threads',
                post_url='https://threads.net/@user/post/123',
                comment_text='Great post!'
            )
        
        assert 'Duplicate' in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_get_daily_count_returns_correct_count(self, tracker, mock_supabase):
        """Should return today's comment count."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            count=42
        )
        
        result = await tracker.get_daily_count('threads')
        
        assert result == 42
    
    @pytest.mark.asyncio
    async def test_is_limit_reached_returns_true_at_limit(self, tracker, mock_supabase):
        """Should return True when at daily limit."""
        # Set limit to 100
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{'daily_limit': 100}]
        )
        # Set count to 100
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            count=100
        )
        
        result = await tracker.is_limit_reached('threads')
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_limit_reached_returns_false_below_limit(self, tracker, mock_supabase):
        """Should return False when below daily limit."""
        # Set limit to 100
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{'daily_limit': 100}]
        )
        # Set count to 50
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            count=50
        )
        
        result = await tracker.is_limit_reached('threads')
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_set_daily_limit_updates_cache(self, tracker, mock_supabase):
        """Should update the limit and cache."""
        await tracker.set_daily_limit('threads', 150)
        
        # Check cache was updated
        assert tracker._limits_cache.get('threads') == 150
        mock_supabase.table.return_value.upsert.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_status_returns_platform_status(self, tracker, mock_supabase):
        """Should return full platform status."""
        # Mock enabled check
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{'is_enabled': True, 'daily_limit': 100}]
        )
        # Mock count
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            count=25
        )
        # Mock last engagement
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        status = await tracker.get_status('threads')
        
        assert isinstance(status, PlatformStatus)
        assert status.platform == 'threads'
        assert status.is_enabled is True


# ============================================================================
# EngagementService Tests
# ============================================================================

class TestEngagementService:
    """Tests for EngagementService."""
    
    @pytest.mark.asyncio
    async def test_request_engagement_publishes_event(self, service, event_bus):
        """Should publish ENGAGEMENT_REQUESTED event."""
        # Mock tracker methods
        service._tracker.is_enabled = AsyncMock(return_value=True)
        service._tracker.get_remaining = AsyncMock(return_value=100)
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event)
        
        event_bus.subscribe(Topics.ENGAGEMENT_REQUESTED, capture_event)
        
        correlation_id = await service.request_engagement('threads', count=5)
        
        # Wait for event dispatch
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 1
        assert events_received[0].topic == Topics.ENGAGEMENT_REQUESTED
        assert events_received[0].payload['platform'] == 'threads'
        assert events_received[0].payload['count'] == 5
    
    @pytest.mark.asyncio
    async def test_request_engagement_raises_when_disabled(self, service):
        """Should raise ValueError when platform is disabled."""
        service._tracker.is_enabled = AsyncMock(return_value=False)
        
        with pytest.raises(ValueError) as exc:
            await service.request_engagement('threads')
        
        assert 'paused' in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_request_engagement_raises_when_limit_reached(self, service):
        """Should raise ValueError when daily limit reached."""
        service._tracker.is_enabled = AsyncMock(return_value=True)
        service._tracker.get_remaining = AsyncMock(return_value=0)
        
        with pytest.raises(ValueError) as exc:
            await service.request_engagement('threads')
        
        assert 'limit' in str(exc.value).lower()
    
    @pytest.mark.asyncio
    async def test_request_engagement_adjusts_count_to_remaining(self, service, event_bus):
        """Should adjust requested count to remaining capacity."""
        service._tracker.is_enabled = AsyncMock(return_value=True)
        service._tracker.get_remaining = AsyncMock(return_value=3)  # Only 3 remaining
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event)
        
        event_bus.subscribe(Topics.ENGAGEMENT_REQUESTED, capture_event)
        
        await service.request_engagement('threads', count=10)  # Request 10
        
        await asyncio.sleep(0.1)
        
        # Should be adjusted to 3
        assert events_received[0].payload['count'] == 3
    
    @pytest.mark.asyncio
    async def test_request_all_platforms_publishes_multiple(self, service, event_bus):
        """Should request engagement on all enabled platforms."""
        service._tracker.is_enabled = AsyncMock(return_value=True)
        service._tracker.get_remaining = AsyncMock(return_value=100)
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event)
        
        event_bus.subscribe(Topics.ENGAGEMENT_REQUESTED, capture_event)
        
        results = await service.request_all_platforms(count_per_platform=2)
        
        await asyncio.sleep(0.1)
        
        assert len(results) == 3  # threads, instagram, tiktok
        assert len(events_received) == 3
    
    @pytest.mark.asyncio
    async def test_pause_platform_disables_it(self, service, event_bus):
        """Should disable engagement for platform."""
        service._tracker.set_enabled = AsyncMock()
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event)
        
        event_bus.subscribe(Topics.ENGAGEMENT_PAUSED, capture_event)
        
        await service.pause_platform('threads')
        
        await asyncio.sleep(0.1)
        
        service._tracker.set_enabled.assert_called_with('threads', False)
        assert len(events_received) == 1
    
    @pytest.mark.asyncio
    async def test_resume_platform_enables_it(self, service, event_bus):
        """Should enable engagement for platform."""
        service._tracker.set_enabled = AsyncMock()
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event)
        
        event_bus.subscribe(Topics.ENGAGEMENT_RESUMED, capture_event)
        
        await service.resume_platform('threads')
        
        await asyncio.sleep(0.1)
        
        service._tracker.set_enabled.assert_called_with('threads', True)
        assert len(events_received) == 1
    
    @pytest.mark.asyncio
    async def test_set_daily_limit_updates_database(self, service):
        """Should update daily limit via tracker."""
        service._tracker.set_daily_limit = AsyncMock()
        
        await service.set_daily_limit('threads', 150)
        
        service._tracker.set_daily_limit.assert_called_with('threads', 150)
    
    @pytest.mark.asyncio
    async def test_invalid_platform_raises(self, service):
        """Should raise ValueError for invalid platform."""
        with pytest.raises(ValueError):
            await service.request_engagement('invalid_platform')


# ============================================================================
# EngagementWorker Tests
# ============================================================================

class TestEngagementWorker:
    """Tests for EngagementWorker."""
    
    def test_worker_subscribes_to_correct_topics(self, worker):
        """Should subscribe to ENGAGEMENT_REQUESTED."""
        subs = worker.get_subscriptions()
        
        assert Topics.ENGAGEMENT_REQUESTED in subs
    
    @pytest.mark.asyncio
    async def test_worker_emits_started_event(self, worker, event_bus):
        """Should emit ENGAGEMENT_STARTED when processing begins."""
        worker._tracker = Mock()
        worker._tracker.is_enabled = AsyncMock(return_value=True)
        worker._tracker.is_limit_reached = AsyncMock(return_value=False)
        worker._tracker.get_daily_limit = AsyncMock(return_value=100)
        worker._tracker.get_remaining = AsyncMock(return_value=100)
        worker._tracker.has_commented_on = AsyncMock(return_value=False)
        worker._tracker.record_comment = AsyncMock(return_value='comment-id')
        
        # Mock platform module
        mock_module = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.post_url = 'https://threads.net/post/123'
        mock_result.username = 'test_user'
        mock_result.generated_comment = 'Test comment'
        mock_result.comment_posted = True
        mock_result.proof_screenshot = '/tmp/proof.png'
        mock_result.error = None
        mock_module.engage_with_post = Mock(return_value=mock_result)
        worker._get_platform_module = AsyncMock(return_value=mock_module)
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event)
        
        event_bus.subscribe(Topics.ENGAGEMENT_STARTED, capture_event)
        
        event = Event(
            id='test',
            topic=Topics.ENGAGEMENT_REQUESTED,
            timestamp=datetime.now(timezone.utc),
            source='test',
            correlation_id='corr-123',
            payload={'platform': 'threads', 'count': 1}
        )
        
        await worker.handle_event(event)
        
        await asyncio.sleep(0.1)
        
        started_events = [e for e in events_received if e.topic == Topics.ENGAGEMENT_STARTED]
        assert len(started_events) >= 1
    
    @pytest.mark.asyncio
    async def test_worker_skips_when_disabled(self, worker, event_bus):
        """Should emit PAUSED event when platform is disabled."""
        worker._tracker = Mock()
        worker._tracker.is_enabled = AsyncMock(return_value=False)
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event)
        
        event_bus.subscribe(Topics.ENGAGEMENT_PAUSED, capture_event)
        event_bus.subscribe(Topics.ENGAGEMENT_STARTED, capture_event)
        
        event = Event(
            id='test',
            topic=Topics.ENGAGEMENT_REQUESTED,
            timestamp=datetime.now(timezone.utc),
            source='test',
            correlation_id='corr-123',
            payload={'platform': 'threads', 'count': 1}
        )
        
        await worker.handle_event(event)
        
        await asyncio.sleep(0.1)
        
        paused_events = [e for e in events_received if e.topic == Topics.ENGAGEMENT_PAUSED]
        assert len(paused_events) == 1
    
    @pytest.mark.asyncio
    async def test_worker_skips_when_limit_reached(self, worker, event_bus):
        """Should emit DAILY_LIMIT_REACHED when limit is hit."""
        worker._tracker = Mock()
        worker._tracker.is_enabled = AsyncMock(return_value=True)
        worker._tracker.is_limit_reached = AsyncMock(return_value=True)
        worker._tracker.get_daily_limit = AsyncMock(return_value=100)
        worker._tracker.get_remaining = AsyncMock(return_value=0)
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event)
        
        event_bus.subscribe(Topics.ENGAGEMENT_DAILY_LIMIT_REACHED, capture_event)
        event_bus.subscribe(Topics.ENGAGEMENT_STARTED, capture_event)
        
        event = Event(
            id='test',
            topic=Topics.ENGAGEMENT_REQUESTED,
            timestamp=datetime.now(timezone.utc),
            source='test',
            correlation_id='corr-123',
            payload={'platform': 'threads', 'count': 1}
        )
        
        await worker.handle_event(event)
        
        await asyncio.sleep(0.1)
        
        limit_events = [e for e in events_received if e.topic == Topics.ENGAGEMENT_DAILY_LIMIT_REACHED]
        assert len(limit_events) == 1
    
    @pytest.mark.asyncio
    async def test_worker_skips_duplicate_posts(self, worker, event_bus):
        """Should emit COMMENT_SKIPPED for duplicate posts."""
        worker._tracker = Mock()
        worker._tracker.is_enabled = AsyncMock(return_value=True)
        worker._tracker.is_limit_reached = AsyncMock(return_value=False)
        worker._tracker.has_commented_on = AsyncMock(return_value=True)  # Duplicate!
        
        # Mock platform module
        mock_module = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.post_url = 'https://threads.net/post/123'
        mock_result.username = 'test_user'
        mock_result.generated_comment = 'Test comment'
        mock_result.comment_posted = False
        mock_result.error = None
        mock_module.engage_with_post = Mock(return_value=mock_result)
        worker._get_platform_module = AsyncMock(return_value=mock_module)
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event)
        
        event_bus.subscribe(Topics.ENGAGEMENT_COMMENT_SKIPPED, capture_event)
        event_bus.subscribe('*', capture_event)
        
        event = Event(
            id='test',
            topic=Topics.ENGAGEMENT_REQUESTED,
            timestamp=datetime.now(timezone.utc),
            source='test',
            correlation_id='corr-123',
            payload={'platform': 'threads', 'count': 1}
        )
        
        await worker.handle_event(event)
        
        await asyncio.sleep(0.1)
        
        skipped_events = [e for e in events_received if e.topic == Topics.ENGAGEMENT_COMMENT_SKIPPED]
        assert len(skipped_events) >= 1
        assert skipped_events[0].payload.get('reason') == 'duplicate'


# ============================================================================
# Integration Tests
# ============================================================================

class TestEngagementIntegration:
    """Integration tests for the full engagement flow."""
    
    @pytest.mark.asyncio
    async def test_full_engagement_flow_emits_all_events(self, event_bus):
        """Should emit all expected events in a successful flow."""
        # Create real service and worker with mocked tracker
        tracker = Mock(spec=CommentTracker)
        tracker.is_enabled = AsyncMock(return_value=True)
        tracker.get_remaining = AsyncMock(return_value=100)
        tracker.is_limit_reached = AsyncMock(return_value=False)
        tracker.has_commented_on = AsyncMock(return_value=False)
        tracker.record_comment = AsyncMock(return_value='comment-123')
        tracker.get_daily_limit = AsyncMock(return_value=100)
        
        service = EngagementService(event_bus=event_bus, tracker=tracker)
        worker = EngagementWorker(event_bus=event_bus)
        worker._tracker = tracker
        
        # Mock platform module
        mock_module = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.post_url = 'https://threads.net/post/123'
        mock_result.username = 'test_user'
        mock_result.generated_comment = 'Test comment'
        mock_result.comment_posted = True
        mock_result.proof_screenshot = '/tmp/proof.png'
        mock_result.error = None
        mock_module.engage_with_post = Mock(return_value=mock_result)
        worker._get_platform_module = AsyncMock(return_value=mock_module)
        
        # Collect all events
        all_events = []
        
        async def capture_all(event):
            all_events.append(event)
        
        event_bus.subscribe('engagement.*', capture_all)
        
        # Subscribe worker
        for topic in worker.get_subscriptions():
            event_bus.subscribe(topic, worker._wrapped_handler)
        
        # Trigger engagement
        correlation_id = await service.request_engagement('threads', count=1)
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # Check events were emitted
        event_topics = [e.topic for e in all_events]
        
        assert Topics.ENGAGEMENT_REQUESTED in event_topics
        assert Topics.ENGAGEMENT_STARTED in event_topics
        assert Topics.ENGAGEMENT_POST_FOUND in event_topics
        assert Topics.ENGAGEMENT_COMMENT_POSTED in event_topics
        assert Topics.ENGAGEMENT_COMPLETED in event_topics
    
    @pytest.mark.asyncio
    async def test_same_post_not_commented_twice(self, event_bus):
        """Should skip posts we've already commented on."""
        tracker = Mock(spec=CommentTracker)
        tracker.is_enabled = AsyncMock(return_value=True)
        tracker.get_remaining = AsyncMock(return_value=100)
        tracker.is_limit_reached = AsyncMock(return_value=False)
        tracker.get_daily_limit = AsyncMock(return_value=100)
        
        # First call: not commented, second call: already commented
        tracker.has_commented_on = AsyncMock(side_effect=[False, True])
        tracker.record_comment = AsyncMock(return_value='comment-123')
        
        worker = EngagementWorker(event_bus=event_bus)
        worker._tracker = tracker
        
        # Mock platform module that returns same post
        mock_module = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.post_url = 'https://threads.net/post/same'  # Same post both times
        mock_result.username = 'test_user'
        mock_result.generated_comment = 'Test comment'
        mock_result.comment_posted = True
        mock_result.proof_screenshot = '/tmp/proof.png'
        mock_result.error = None
        mock_module.engage_with_post = Mock(return_value=mock_result)
        worker._get_platform_module = AsyncMock(return_value=mock_module)
        
        # Collect events
        skipped_events = []
        
        async def capture_skipped(event):
            if event.topic == Topics.ENGAGEMENT_COMMENT_SKIPPED:
                skipped_events.append(event)
        
        event_bus.subscribe(Topics.ENGAGEMENT_COMMENT_SKIPPED, capture_skipped)
        
        # Subscribe worker
        for topic in worker.get_subscriptions():
            event_bus.subscribe(topic, worker._wrapped_handler)
        
        # First engagement - should post
        event1 = Event(
            id='test1',
            topic=Topics.ENGAGEMENT_REQUESTED,
            timestamp=datetime.now(timezone.utc),
            source='test',
            correlation_id='corr-1',
            payload={'platform': 'threads', 'count': 1}
        )
        await worker.handle_event(event1)
        
        await asyncio.sleep(0.1)
        
        # Second engagement - should skip (duplicate)
        event2 = Event(
            id='test2',
            topic=Topics.ENGAGEMENT_REQUESTED,
            timestamp=datetime.now(timezone.utc),
            source='test',
            correlation_id='corr-2',
            payload={'platform': 'threads', 'count': 1}
        )
        await worker.handle_event(event2)
        
        await asyncio.sleep(0.1)
        
        # Should have at least one skipped event
        assert len(skipped_events) >= 1
        assert any(e.payload.get('reason') == 'duplicate' for e in skipped_events)


# ============================================================================
# Controllability Tests
# ============================================================================

class TestControllability:
    """Tests for pause/resume and limit adjustment."""
    
    @pytest.mark.asyncio
    async def test_pause_stops_engagement(self, service, event_bus):
        """Pausing should prevent new engagements."""
        service._tracker.set_enabled = AsyncMock()
        service._tracker.is_enabled = AsyncMock(return_value=False)
        
        # Pause
        await service.pause_platform('threads')
        
        # Try to engage - should fail
        with pytest.raises(ValueError) as exc:
            await service.request_engagement('threads')
        
        assert 'paused' in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_resume_continues_engagement(self, service, event_bus):
        """Resuming should allow engagements again."""
        service._tracker.set_enabled = AsyncMock()
        service._tracker.is_enabled = AsyncMock(return_value=True)
        service._tracker.get_remaining = AsyncMock(return_value=100)
        
        # Resume
        await service.resume_platform('threads')
        
        # Should be able to engage
        correlation_id = await service.request_engagement('threads')
        
        assert correlation_id is not None
    
    @pytest.mark.asyncio
    async def test_pause_all_stops_all_platforms(self, service, event_bus):
        """Pausing 'all' should disable all platforms."""
        service._tracker.set_enabled = AsyncMock()
        
        await service.pause_platform('all')
        
        # Should have been called for each platform
        assert service._tracker.set_enabled.call_count == 3
    
    @pytest.mark.asyncio
    async def test_increase_limit_allows_more(self, service):
        """Increasing limit should allow more comments."""
        service._tracker.set_daily_limit = AsyncMock()
        service._tracker.is_enabled = AsyncMock(return_value=True)
        service._tracker.get_remaining = AsyncMock(return_value=50)  # Now have more
        
        # Increase limit
        await service.set_daily_limit('threads', 200)
        
        service._tracker.set_daily_limit.assert_called_with('threads', 200)
    
    @pytest.mark.asyncio
    async def test_negative_limit_raises(self, service):
        """Should reject negative limits."""
        with pytest.raises(ValueError):
            await service.set_daily_limit('threads', -10)


# ============================================================================
# CLI Test Runner
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
