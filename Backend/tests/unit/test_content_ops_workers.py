"""
Content Ops Workers Tests
==========================
Tests for Content Ops Workers (OPS-013 to OPS-016)

Test Coverage:
- OPS-013: Slot Executor Worker
- OPS-014: Learner Worker
- OPS-015: Inbound Listener Worker
- OPS-016: Responder Worker
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from services.workers.slot_executor_worker import SlotExecutorWorker
from services.workers.learner_worker import LearnerWorker
from services.workers.inbound_listener_worker import InboundListenerWorker
from services.workers.responder_worker import ResponderWorker
from services.event_bus import Event


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing"""
    bus = Mock()
    bus.publish = AsyncMock()
    bus.subscribe = Mock()
    bus.set_source = Mock()
    return bus


@pytest.fixture
def mock_event():
    """Create a mock event"""
    def _create_event(topic, payload, correlation_id="test-correlation-id"):
        event = Mock(spec=Event)
        event.topic = topic
        event.payload = payload
        event.correlation_id = correlation_id
        event.id = "test-event-id"
        event.timestamp = datetime.now(timezone.utc)
        event.source = "test-source"
        return event
    return _create_event


# ============================================================================
# OPS-013: Slot Executor Worker Tests
# ============================================================================

class TestSlotExecutorWorker:
    """Test OPS-013: Slot Executor Worker"""

    @pytest.fixture
    def mock_generation_pipeline(self):
        """Mock content generation pipeline"""
        with patch('services.workers.slot_executor_worker.ContentGenerationPipeline') as mock:
            mock_instance = Mock()
            mock.get_instance.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_qa_service(self):
        """Mock QA gate service"""
        with patch('services.workers.slot_executor_worker.QAGateService') as mock:
            mock_instance = Mock()
            mock.get_instance.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_worker_initialization(self, mock_event_bus, mock_generation_pipeline, mock_qa_service):
        """Test worker initializes correctly"""
        worker = SlotExecutorWorker(event_bus=mock_event_bus)

        assert worker.generation_pipeline is not None
        assert worker.qa_service is not None
        assert len(worker._executing_slots) == 0

    @pytest.mark.asyncio
    async def test_worker_subscriptions(self, mock_event_bus, mock_generation_pipeline, mock_qa_service):
        """Test worker subscribes to correct topics"""
        worker = SlotExecutorWorker(event_bus=mock_event_bus)
        subscriptions = worker.get_subscriptions()

        assert "slot.execute.requested" in subscriptions

    @pytest.mark.asyncio
    async def test_handle_slot_execution_request(
        self,
        mock_event_bus,
        mock_event,
        mock_generation_pipeline,
        mock_qa_service
    ):
        """Test handling slot execution request"""
        worker = SlotExecutorWorker(event_bus=mock_event_bus)

        # Create slot execution event
        event = mock_event(
            topic="slot.execute.requested",
            payload={
                "slot_id": "slot-123",
                "plan_id": "plan-456",
                "platform": "x",
                "channel": "post",
                "awareness_level": "problem_aware",
                "fate_target": {"feeling": 0.7, "action": 0.6, "thinking": 0.5, "engagement": 0.8},
                "target_offer_id": "offer-789",
                "target_icp_id": "icp-101",
                "variants": 3
            }
        )

        # Handle event
        await worker.handle_event(event)

        # Verify generation request was emitted
        assert mock_event_bus.publish.called
        call_args = mock_event_bus.publish.call_args
        assert "draft.generate.requested" in str(call_args)

        # Verify slot is tracked
        assert "slot-123" in worker._executing_slots
        assert worker._executing_slots["slot-123"]["status"] == "generating"

    @pytest.mark.asyncio
    async def test_handle_missing_slot_id(
        self,
        mock_event_bus,
        mock_event,
        mock_generation_pipeline,
        mock_qa_service
    ):
        """Test handling event with missing slot_id"""
        worker = SlotExecutorWorker(event_bus=mock_event_bus)

        # Create event without slot_id
        event = mock_event(
            topic="slot.execute.requested",
            payload={"platform": "x"}
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="slot_id is required"):
            await worker.handle_event(event)

    @pytest.mark.asyncio
    async def test_get_execution_stats(self, mock_event_bus, mock_generation_pipeline, mock_qa_service):
        """Test getting execution statistics"""
        worker = SlotExecutorWorker(event_bus=mock_event_bus)

        # Add a tracked execution
        worker._executing_slots["slot-123"] = {
            "started_at": datetime.now(timezone.utc),
            "status": "generating",
            "correlation_id": "test-id"
        }

        stats = worker.get_execution_stats()

        assert stats["in_flight_executions"] == 1
        assert len(stats["executions"]) == 1
        assert stats["executions"][0]["slot_id"] == "slot-123"
        assert stats["executions"][0]["status"] == "generating"


# ============================================================================
# OPS-014: Learner Worker Tests
# ============================================================================

class TestLearnerWorker:
    """Test OPS-014: Learner Worker"""

    @pytest.fixture
    def mock_template_leaderboard(self):
        """Mock template leaderboard"""
        with patch('services.workers.learner_worker.TemplateLeaderboard') as mock:
            mock_instance = AsyncMock()
            mock_instance.get_all_templates = AsyncMock(return_value=[
                {
                    "template_id": "template-1",
                    "allocation": 0.5,
                    "stats": {
                        "total_uses": 20,
                        "win_rate": 0.75,
                        "avg_engagement_rate": 0.08
                    }
                },
                {
                    "template_id": "template-2",
                    "allocation": 0.3,
                    "stats": {
                        "total_uses": 15,
                        "win_rate": 0.35,
                        "avg_engagement_rate": 0.03
                    }
                }
            ])
            mock_instance.update_allocation = AsyncMock()
            mock_instance.normalize_allocations = AsyncMock()
            mock.get_instance.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_worker_initialization(self, mock_event_bus, mock_template_leaderboard):
        """Test worker initializes correctly"""
        worker = LearnerWorker(event_bus=mock_event_bus)

        assert worker.leaderboard is not None
        assert worker.winner_threshold == 0.70
        assert worker.loser_threshold == 0.05
        assert worker.fork_threshold == 0.80
        assert worker.min_samples == 10

    @pytest.mark.asyncio
    async def test_worker_subscriptions(self, mock_event_bus, mock_template_leaderboard):
        """Test worker subscribes to correct topics"""
        worker = LearnerWorker(event_bus=mock_event_bus)
        subscriptions = worker.get_subscriptions()

        assert "learn.update.requested" in subscriptions
        assert "metrics.snapshot.completed" in subscriptions

    @pytest.mark.asyncio
    async def test_handle_learning_request(
        self,
        mock_event_bus,
        mock_event,
        mock_template_leaderboard
    ):
        """Test handling learning update request"""
        worker = LearnerWorker(event_bus=mock_event_bus)

        # Create learning request event
        event = mock_event(
            topic="learn.update.requested",
            payload={"date": "2026-01-18"}
        )

        # Handle event
        await worker.handle_event(event)

        # Verify learning cycle ran
        assert mock_template_leaderboard.get_all_templates.called
        assert mock_template_leaderboard.normalize_allocations.called

        # Verify completion event was emitted
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_calculate_allocation(self, mock_event_bus, mock_template_leaderboard):
        """Test allocation calculation"""
        worker = LearnerWorker(event_bus=mock_event_bus)

        # High performer
        allocation_high = worker._calculate_allocation(win_rate=0.8, avg_engagement=0.1)
        assert allocation_high >= 0.5  # Should get high allocation

        # Low performer
        allocation_low = worker._calculate_allocation(win_rate=0.2, avg_engagement=0.02)
        assert allocation_low <= 0.15  # Should get low allocation

        # Allocation should be in valid range
        assert 0.05 <= allocation_high <= 0.70
        assert 0.05 <= allocation_low <= 0.70

    @pytest.mark.asyncio
    async def test_get_learning_stats(self, mock_event_bus, mock_template_leaderboard):
        """Test getting learning statistics"""
        worker = LearnerWorker(event_bus=mock_event_bus)

        # Add a learning run
        worker._learning_runs.append({
            "date": "2026-01-18",
            "templates_updated": 5,
            "templates_forked": 2,
            "templates_demoted": 1
        })

        stats = worker.get_learning_stats()

        assert stats["total_learning_runs"] == 1
        assert len(stats["recent_runs"]) == 1
        assert stats["config"]["winner_threshold"] == 0.70


# ============================================================================
# OPS-015: Inbound Listener Worker Tests
# ============================================================================

class TestInboundListenerWorker:
    """Test OPS-015: Inbound Listener Worker"""

    @pytest.mark.asyncio
    async def test_worker_initialization(self, mock_event_bus):
        """Test worker initializes correctly"""
        worker = InboundListenerWorker(event_bus=mock_event_bus)

        assert len(worker._seen_items) == 0
        assert worker._max_seen_items == 10000
        assert len(worker._platform_handlers) > 0

    @pytest.mark.asyncio
    async def test_worker_subscriptions(self, mock_event_bus):
        """Test worker subscribes to correct topics"""
        worker = InboundListenerWorker(event_bus=mock_event_bus)
        subscriptions = worker.get_subscriptions()

        assert "inbound.poll.requested" in subscriptions
        assert any("webhook" in sub for sub in subscriptions)

    @pytest.mark.asyncio
    async def test_handle_comment_webhook(self, mock_event_bus, mock_event):
        """Test handling comment webhook event"""
        worker = InboundListenerWorker(event_bus=mock_event_bus)

        # Create comment webhook event
        event = mock_event(
            topic="webhook.x.comment",
            payload={
                "external_event_id": "event-123",
                "event_type": "comment",
                "comment_id": "comment-456",
                "text": "Great content!",
                "author_username": "testuser",
                "post_id": "post-789",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )

        # Handle event
        await worker.handle_event(event)

        # Verify comment received event was emitted
        assert mock_event_bus.publish.called
        # Should emit: comment.received, inbound.received, inbound.respond.requested
        assert mock_event_bus.publish.call_count >= 3

    @pytest.mark.asyncio
    async def test_handle_dm_webhook(self, mock_event_bus, mock_event):
        """Test handling DM webhook event"""
        worker = InboundListenerWorker(event_bus=mock_event_bus)

        # Create DM webhook event
        event = mock_event(
            topic="webhook.instagram.dm",
            payload={
                "external_event_id": "event-456",
                "event_type": "dm",
                "message_id": "msg-789",
                "text": "How can I get started?",
                "author_username": "testuser",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )

        # Handle event
        await worker.handle_event(event)

        # Verify DM received event was emitted
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, mock_event_bus):
        """Test duplicate event detection"""
        worker = InboundListenerWorker(event_bus=mock_event_bus)

        # First event should not be duplicate
        is_dup_1 = await worker._is_duplicate("x", "event-123")
        assert is_dup_1 is False

        # Same event should be duplicate
        is_dup_2 = await worker._is_duplicate("x", "event-123")
        assert is_dup_2 is True

    @pytest.mark.asyncio
    async def test_get_listener_stats(self, mock_event_bus):
        """Test getting listener statistics"""
        worker = InboundListenerWorker(event_bus=mock_event_bus)

        # Mark some events as seen
        await worker._is_duplicate("x", "event-1")
        await worker._is_duplicate("instagram", "event-2")

        stats = worker.get_listener_stats()

        assert stats["seen_items_count"] == 2
        assert stats["max_seen_items"] == 10000
        assert len(stats["supported_platforms"]) > 0


# ============================================================================
# OPS-016: Responder Worker Tests
# ============================================================================

class TestResponderWorker:
    """Test OPS-016: Responder Worker"""

    @pytest.fixture
    def mock_dm_permission(self):
        """Mock DM permission service"""
        with patch('services.workers.responder_worker.DMPermissionService') as mock:
            mock_instance = AsyncMock()
            mock_instance.check_consent = AsyncMock(return_value="granted")
            mock.get_instance.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_qa_service(self):
        """Mock QA gate service"""
        with patch('services.workers.responder_worker.QAGateService') as mock:
            mock_instance = AsyncMock()
            mock_instance.check_content = AsyncMock(return_value={"passed": True, "issues": []})
            mock.get_instance.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_ai_client(self):
        """Mock AI client"""
        with patch('services.workers.responder_worker.AIClient') as mock:
            mock_instance = AsyncMock()
            mock_instance.generate_text = AsyncMock(return_value="Thanks for your comment!")
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_worker_initialization(
        self,
        mock_event_bus,
        mock_dm_permission,
        mock_qa_service,
        mock_ai_client
    ):
        """Test worker initializes correctly"""
        worker = ResponderWorker(event_bus=mock_event_bus)

        assert worker.dm_permission is not None
        assert worker.qa_service is not None
        assert worker.ai_client is not None
        assert len(worker._pending_responses) == 0

    @pytest.mark.asyncio
    async def test_worker_subscriptions(
        self,
        mock_event_bus,
        mock_dm_permission,
        mock_qa_service,
        mock_ai_client
    ):
        """Test worker subscribes to correct topics"""
        worker = ResponderWorker(event_bus=mock_event_bus)
        subscriptions = worker.get_subscriptions()

        assert "inbound.respond.requested" in subscriptions

    @pytest.mark.asyncio
    async def test_handle_public_reply_request(
        self,
        mock_event_bus,
        mock_event,
        mock_dm_permission,
        mock_qa_service,
        mock_ai_client
    ):
        """Test handling public reply request"""
        worker = ResponderWorker(event_bus=mock_event_bus)

        # Create response request event
        event = mock_event(
            topic="inbound.respond.requested",
            payload={
                "platform": "x",
                "channel": "comment",
                "platform_object_id": "comment-123",
                "strategy": "public_reply",
                "text": "Great content!",
                "author_username": "testuser"
            }
        )

        # Handle event
        await worker.handle_event(event)

        # Verify AI was called to generate response
        assert mock_ai_client.return_value.generate_text.called

        # Verify QA was run
        assert mock_qa_service.check_content.called

        # Verify response was sent (event emitted)
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_handle_dm_with_permission(
        self,
        mock_event_bus,
        mock_event,
        mock_dm_permission,
        mock_qa_service,
        mock_ai_client
    ):
        """Test handling DM request with permission granted"""
        worker = ResponderWorker(event_bus=mock_event_bus)

        # Permission is granted by default in fixture
        event = mock_event(
            topic="inbound.respond.requested",
            payload={
                "platform": "instagram",
                "channel": "dm",
                "platform_object_id": "dm-456",
                "strategy": "dm_flow",
                "requires_permission_gate": True,
                "text": "How can I get started?",
                "author_username": "testuser"
            }
        )

        # Handle event
        await worker.handle_event(event)

        # Verify permission was checked
        assert mock_dm_permission.check_consent.called

        # Verify response was generated and sent
        assert mock_ai_client.return_value.generate_text.called

    @pytest.mark.asyncio
    async def test_handle_dm_without_permission(
        self,
        mock_event_bus,
        mock_event,
        mock_dm_permission,
        mock_qa_service,
        mock_ai_client
    ):
        """Test handling DM request without permission"""
        # Set permission to denied
        mock_dm_permission.check_consent = AsyncMock(return_value="denied")

        worker = ResponderWorker(event_bus=mock_event_bus)

        event = mock_event(
            topic="inbound.respond.requested",
            payload={
                "platform": "instagram",
                "channel": "dm",
                "platform_object_id": "dm-789",
                "strategy": "dm_flow",
                "requires_permission_gate": True,
                "text": "Can you send me a link?",
                "author_username": "testuser"
            }
        )

        # Handle event
        await worker.handle_event(event)

        # Verify permission was checked
        assert mock_dm_permission.check_consent.called

        # Response should NOT be generated (no permission)
        assert not mock_ai_client.return_value.generate_text.called

    @pytest.mark.asyncio
    async def test_qa_gate_failure(
        self,
        mock_event_bus,
        mock_event,
        mock_dm_permission,
        mock_qa_service,
        mock_ai_client
    ):
        """Test handling QA gate failure"""
        # Set QA to fail
        mock_qa_service.check_content = AsyncMock(
            return_value={"passed": False, "issues": ["Contains prohibited language"]}
        )

        worker = ResponderWorker(event_bus=mock_event_bus)

        event = mock_event(
            topic="inbound.respond.requested",
            payload={
                "platform": "x",
                "channel": "comment",
                "platform_object_id": "comment-999",
                "strategy": "public_reply",
                "text": "Nice!",
                "author_username": "testuser"
            }
        )

        # Handle event
        await worker.handle_event(event)

        # Response should be generated
        assert mock_ai_client.return_value.generate_text.called

        # But NOT sent (QA failed)
        # Instead, approval.required event should be emitted
        calls = [str(call) for call in mock_event_bus.publish.call_args_list]
        assert any("approval.required" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_get_responder_stats(
        self,
        mock_event_bus,
        mock_dm_permission,
        mock_qa_service,
        mock_ai_client
    ):
        """Test getting responder statistics"""
        worker = ResponderWorker(event_bus=mock_event_bus)

        # Add a pending response
        worker._pending_responses["resp-1"] = {
            "platform": "x",
            "channel": "comment",
            "status": "generating"
        }

        stats = worker.get_responder_stats()

        assert stats["total_responses"] == 1
        assert "status_counts" in stats
        assert stats["status_counts"]["generating"] == 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestWorkersIntegration:
    """Test workers working together"""

    @pytest.mark.asyncio
    async def test_workers_start_and_stop(self, mock_event_bus):
        """Test all workers can start and stop cleanly"""
        with patch('services.workers.slot_executor_worker.ContentGenerationPipeline'), \
             patch('services.workers.slot_executor_worker.QAGateService'), \
             patch('services.workers.learner_worker.TemplateLeaderboard'), \
             patch('services.workers.responder_worker.DMPermissionService'), \
             patch('services.workers.responder_worker.QAGateService'), \
             patch('services.workers.responder_worker.AIClient'):

            # Create workers
            slot_worker = SlotExecutorWorker(event_bus=mock_event_bus)
            learner_worker = LearnerWorker(event_bus=mock_event_bus)
            listener_worker = InboundListenerWorker(event_bus=mock_event_bus)
            responder_worker = ResponderWorker(event_bus=mock_event_bus)

            # Start all workers
            await slot_worker.start()
            await learner_worker.start()
            await listener_worker.start()
            await responder_worker.start()

            # Verify all running
            assert slot_worker.is_running
            assert learner_worker.is_running
            assert listener_worker.is_running
            assert responder_worker.is_running

            # Stop all workers
            await slot_worker.stop()
            await learner_worker.stop()
            await listener_worker.stop()
            await responder_worker.stop()

            # Verify all stopped
            assert not slot_worker.is_running
            assert not learner_worker.is_running
            assert not listener_worker.is_running
            assert not responder_worker.is_running
