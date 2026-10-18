"""
Tests for Sora Pub/Sub Architecture
====================================
Tests for event-driven Sora automation using pub/sub topics.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import sys
sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')

from services.event_bus import EventBus, Event, Topics
from services.workers.sora_worker import SoraWorker, get_sora_worker


class TestSoraTopics:
    """Test Sora topic definitions."""
    
    def test_sora_usage_topics_exist(self):
        """Verify Sora usage topics are defined."""
        assert hasattr(Topics, 'SORA_USAGE_CHECK_REQUESTED')
        assert hasattr(Topics, 'SORA_USAGE_CHECKED')
        assert hasattr(Topics, 'SORA_USAGE_LOW')
        
        assert Topics.SORA_USAGE_CHECK_REQUESTED == "sora.usage.check.requested"
        assert Topics.SORA_USAGE_CHECKED == "sora.usage.checked"
        assert Topics.SORA_USAGE_LOW == "sora.usage.low"
    
    def test_sora_video_topics_exist(self):
        """Verify Sora video generation topics are defined."""
        assert hasattr(Topics, 'SORA_VIDEO_REQUESTED')
        assert hasattr(Topics, 'SORA_VIDEO_STARTED')
        assert hasattr(Topics, 'SORA_VIDEO_PROGRESS')
        assert hasattr(Topics, 'SORA_VIDEO_COMPLETED')
        assert hasattr(Topics, 'SORA_VIDEO_FAILED')
        assert hasattr(Topics, 'SORA_VIDEO_DOWNLOADED')
    
    def test_sora_batch_topics_exist(self):
        """Verify Sora batch topics are defined."""
        assert hasattr(Topics, 'SORA_BATCH_REQUESTED')
        assert hasattr(Topics, 'SORA_BATCH_STARTED')
        assert hasattr(Topics, 'SORA_BATCH_PROGRESS')
        assert hasattr(Topics, 'SORA_BATCH_COMPLETED')
    
    def test_sora_poll_topics_exist(self):
        """Verify Sora polling topics are defined."""
        assert hasattr(Topics, 'SORA_POLL_STARTED')
        assert hasattr(Topics, 'SORA_POLL_TICK')
        assert hasattr(Topics, 'SORA_POLL_STOPPED')


class TestSoraWorker:
    """Test SoraWorker class."""
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create mock EventBus."""
        bus = MagicMock(spec=EventBus)
        bus.publish = AsyncMock(return_value="event-123")
        bus.subscribe = MagicMock()
        return bus
    
    @pytest.fixture
    def worker(self, mock_event_bus):
        """Create SoraWorker with mock bus."""
        return SoraWorker(event_bus=mock_event_bus, worker_id="test-sora-worker")
    
    def test_worker_initialization(self, worker):
        """Test worker initializes correctly."""
        assert worker.worker_id == "test-sora-worker"
        assert worker._is_polling is False
        assert worker._poll_task is None
    
    def test_worker_subscriptions(self, worker):
        """Test worker subscribes to correct topics."""
        subs = worker.get_subscriptions()
        
        assert Topics.SORA_USAGE_CHECK_REQUESTED in subs
        assert Topics.SORA_VIDEO_REQUESTED in subs
        assert Topics.SORA_BATCH_REQUESTED in subs
    
    def test_worker_stats(self, worker):
        """Test worker stats include Sora-specific data."""
        stats = worker.get_stats()
        
        assert "is_polling" in stats
        assert "known_video_count" in stats
        assert "poll_interval" in stats
        assert "max_poll_duration" in stats
        
        assert stats["is_polling"] is False
        assert stats["poll_interval"] == 60
        assert stats["max_poll_duration"] == 900
    
    @pytest.mark.asyncio
    async def test_handle_usage_check_event(self, worker, mock_event_bus):
        """Test handling usage check request event."""
        event = Event(
            topic=Topics.SORA_USAGE_CHECK_REQUESTED,
            payload={"requested_at": datetime.now(timezone.utc).isoformat()},
            source="test",
            correlation_id="corr-123"
        )
        
        # Mock SoraFullAutomation at the import location
        with patch('automation.sora_full_automation.SoraFullAutomation') as MockSora:
            mock_sora = MagicMock()
            mock_sora.get_usage.return_value = {
                "video_gens_left": 47,
                "free_count": 47,
                "paid_count": 0,
                "reset_date": "Jan 26, 2026"
            }
            MockSora.return_value = mock_sora
            
            await worker._handle_usage_check(event)
            
            # Verify usage checked event was emitted
            assert mock_event_bus.publish.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_handle_video_request_event(self, worker, mock_event_bus):
        """Test handling video generation request event."""
        event = Event(
            topic=Topics.SORA_VIDEO_REQUESTED,
            payload={
                "prompt": "A cinematic shot of @isaiahdupree walking through a neon city",
                "character": "isaiahdupree",
                "duration": 15
            },
            source="test",
            correlation_id="corr-456"
        )
        
        with patch('automation.sora_full_automation.SoraFullAutomation') as MockSora:
            mock_sora = MagicMock()
            mock_sora.generate_video = AsyncMock(return_value=True)
            MockSora.return_value = mock_sora
            
            # Mock polling to not actually run
            worker._start_polling = AsyncMock()
            
            await worker._handle_video_request(event)
            
            # Verify started event was emitted
            calls = mock_event_bus.publish.call_args_list
            topics_emitted = [c.kwargs.get('topic', c.args[0] if c.args else None) for c in calls]
            assert Topics.SORA_VIDEO_STARTED in topics_emitted
    
    @pytest.mark.asyncio
    async def test_handle_batch_request_event(self, worker, mock_event_bus):
        """Test handling batch generation request event."""
        event = Event(
            topic=Topics.SORA_BATCH_REQUESTED,
            payload={
                "prompts": [
                    "Part 1: The beginning",
                    "Part 2: The middle",
                    "Part 3: The end"
                ],
                "character": "isaiahdupree",
                "auto_download": True
            },
            source="test",
            correlation_id="corr-789"
        )
        
        await worker._handle_batch_request(event)
        
        # Verify batch started was emitted (check call count)
        assert mock_event_bus.publish.call_count >= 1
    
    def test_stop_polling(self, worker):
        """Test stopping polling task."""
        worker._is_polling = True
        mock_task = MagicMock()
        worker._poll_task = mock_task
        
        worker.stop_polling()
        
        assert worker._is_polling is False
        mock_task.cancel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_worker_stop(self, worker):
        """Test worker stop cleans up polling."""
        worker._is_polling = True
        worker._poll_task = MagicMock()
        
        await worker.stop()
        
        assert worker._is_polling is False


class TestSoraEventBusIntegration:
    """Test Sora events flow through EventBus."""
    
    @pytest.fixture
    def event_bus(self):
        """Create fresh EventBus instance."""
        # Reset singleton for test isolation
        EventBus._instance = None
        return EventBus.get_instance()
    
    @pytest.mark.asyncio
    async def test_publish_usage_check_request(self, event_bus):
        """Test publishing usage check request."""
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        event_bus.subscribe(Topics.SORA_USAGE_CHECK_REQUESTED, handler)
        
        event_id = await event_bus.publish(
            Topics.SORA_USAGE_CHECK_REQUESTED,
            {"source": "test"},
            source="test-publisher"
        )
        
        # Give async handlers time to process
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0].topic == Topics.SORA_USAGE_CHECK_REQUESTED
    
    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, event_bus):
        """Test subscribing to sora.* catches all Sora events."""
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        event_bus.subscribe("sora.*", handler)
        
        # Publish various Sora events
        await event_bus.publish(Topics.SORA_USAGE_CHECKED, {"gens": 47})
        await event_bus.publish(Topics.SORA_VIDEO_STARTED, {"prompt": "test"})
        await event_bus.publish(Topics.SORA_POLL_TICK, {"tick": 1})
        
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 3


class TestSoraPubSubScript:
    """Test the sora_pubsub_commands.py script functions."""
    
    @pytest.mark.asyncio
    async def test_script_imports(self):
        """Test script can be imported."""
        from scripts.sora_pubsub_commands import check_usage, generate_video, generate_batch
        
        assert callable(check_usage)
        assert callable(generate_video)
        assert callable(generate_batch)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
