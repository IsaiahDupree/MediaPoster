"""
Unit Tests for Autonomous Slot Executor
=======================================
Tests AUTO-006: Autonomous Slot Executor

Tests for autonomous slot execution without human intervention.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from workers.slot_executor import (
    AutonomousSlotExecutor,
    SlotStatus,
    get_autonomous_slot_executor
)


class TestAutonomousSlotExecutorCore:
    """Test core autonomous slot executor functionality"""

    def test_executor_initialization(self):
        """Test executor initializes correctly"""
        executor = AutonomousSlotExecutor()

        assert executor._is_running is False
        assert executor.check_interval_seconds == 60
        assert executor.pre_execution_buffer_minutes == 5
        assert executor.max_retries == 3
        assert len(executor._executing_slots) == 0
        assert len(executor._failed_slots) == 0

    def test_singleton_pattern(self):
        """Test get_autonomous_slot_executor returns singleton"""
        executor1 = get_autonomous_slot_executor()
        executor2 = get_autonomous_slot_executor()

        assert executor1 is executor2

    @pytest.mark.asyncio
    async def test_executor_start(self):
        """Test executor can start successfully"""
        executor = AutonomousSlotExecutor()

        with patch.object(executor.event_bus, 'publish', new=AsyncMock()):
            await executor.start()

            assert executor._is_running is True
            assert executor._task is not None

            # Cleanup
            await executor.stop()

    @pytest.mark.asyncio
    async def test_executor_stop(self):
        """Test executor can stop successfully"""
        executor = AutonomousSlotExecutor()

        with patch.object(executor.event_bus, 'publish', new=AsyncMock()):
            await executor.start()
            await asyncio.sleep(0.1)  # Let it start
            await executor.stop()

            assert executor._is_running is False

    @pytest.mark.asyncio
    async def test_executor_cannot_start_twice(self):
        """Test executor handles double-start gracefully"""
        executor = AutonomousSlotExecutor()

        with patch.object(executor.event_bus, 'publish', new=AsyncMock()):
            await executor.start()

            # Try to start again
            await executor.start()

            assert executor._is_running is True

            # Cleanup
            await executor.stop()


class TestSlotExecution:
    """Test slot execution logic"""

    @pytest.mark.asyncio
    async def test_execute_slot_emits_event(self):
        """Test slot execution emits correct event"""
        executor = AutonomousSlotExecutor()

        slot = {
            "slot_id": "slot-001",
            "plan_id": "plan-001",
            "platform": "twitter",
            "channel": "post",
            "awareness_level": "problem_aware",
            "fate_target": "authority",
            "cta_strength": "soft",
            "target_offer_id": None,
            "target_icp_id": None,
            "metadata": {}
        }

        with patch.object(executor.event_bus, 'publish', new=AsyncMock()) as mock_publish, \
             patch.object(executor, '_update_slot_status', new=AsyncMock()), \
             patch.object(executor, '_subscribe_to_completion', new=AsyncMock()):

            await executor._execute_slot(slot)

            # Verify event was published
            mock_publish.assert_called_once()
            call_args = mock_publish.call_args
            assert call_args[0][0] == "slot.execute.requested"
            assert call_args[0][1]["slot_id"] == "slot-001"
            assert call_args[0][1]["auto_execution"] is True

    @pytest.mark.asyncio
    async def test_execute_slot_tracks_execution(self):
        """Test slot execution is tracked correctly"""
        executor = AutonomousSlotExecutor()

        slot = {
            "slot_id": "slot-002",
            "platform": "instagram",
            "channel": "post",
            "awareness_level": "solution_aware",
            "fate_target": "focus"
        }

        with patch.object(executor.event_bus, 'publish', new=AsyncMock()), \
             patch.object(executor, '_update_slot_status', new=AsyncMock()), \
             patch.object(executor, '_subscribe_to_completion', new=AsyncMock()):

            await executor._execute_slot(slot)

            # Verify execution is tracked
            assert "slot-002" in executor._executing_slots
            assert executor._executing_slots["slot-002"]["status"] == SlotStatus.EXECUTING

    @pytest.mark.asyncio
    async def test_execute_slot_handles_duplicate_execution(self):
        """Test duplicate execution is prevented"""
        executor = AutonomousSlotExecutor()

        slot = {
            "slot_id": "slot-003",
            "platform": "tiktok",
            "channel": "post"
        }

        # Add to executing slots
        executor._executing_slots["slot-003"] = {
            "slot_id": "slot-003",
            "started_at": datetime.now(timezone.utc),
            "status": SlotStatus.EXECUTING
        }

        with patch.object(executor.event_bus, 'publish', new=AsyncMock()) as mock_publish:
            await executor._execute_slot(slot)

            # Should not publish event for duplicate
            mock_publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_slot_respects_max_retries(self):
        """Test max retries are enforced"""
        executor = AutonomousSlotExecutor()

        slot = {
            "slot_id": "slot-004",
            "platform": "youtube",
            "channel": "post"
        }

        # Simulate 3 previous failures
        executor._failed_slots["slot-004"] = [
            {"timestamp": datetime.now(timezone.utc), "error": "Error 1"},
            {"timestamp": datetime.now(timezone.utc), "error": "Error 2"},
            {"timestamp": datetime.now(timezone.utc), "error": "Error 3"}
        ]

        with patch.object(executor, '_mark_slot_failed', new=AsyncMock()) as mock_mark_failed:
            await executor._execute_slot(slot)

            # Should mark as permanently failed
            mock_mark_failed.assert_called_once_with("slot-004", "Max retries exceeded")


class TestSlotQuerying:
    """Test slot query logic"""

    @pytest.mark.asyncio
    async def test_get_due_slots_queries_correctly(self):
        """Test due slots query logic"""
        executor = AutonomousSlotExecutor()

        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=5)

        # Mock database connection
        with patch.object(executor.engine, 'connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_conn

            # Mock empty result
            mock_result = MagicMock()
            mock_result.__iter__.return_value = iter([])
            mock_conn.execute.return_value = mock_result

            slots = await executor._get_due_slots(start_time, end_time)

            assert isinstance(slots, list)
            assert len(slots) == 0

    @pytest.mark.asyncio
    async def test_get_due_slots_handles_errors(self):
        """Test error handling in slot queries"""
        executor = AutonomousSlotExecutor()

        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=5)

        # Mock database connection error
        with patch.object(executor.engine, 'connect', side_effect=Exception("DB Error")):
            slots = await executor._get_due_slots(start_time, end_time)

            # Should return empty list on error
            assert slots == []


class TestStatusAndMetrics:
    """Test status reporting and metrics"""

    def test_get_execution_status_includes_all_fields(self):
        """Test status report includes all required fields"""
        executor = AutonomousSlotExecutor()

        status = executor.get_execution_status()

        assert "is_running" in status
        assert "executing_slots" in status
        assert "failed_slots" in status
        assert "check_interval_seconds" in status
        assert "executions" in status
        assert "failures" in status

    def test_get_execution_status_reports_executions(self):
        """Test execution status includes active executions"""
        executor = AutonomousSlotExecutor()

        # Add mock execution
        executor._executing_slots["slot-005"] = {
            "slot_id": "slot-005",
            "started_at": datetime.now(timezone.utc),
            "status": SlotStatus.EXECUTING,
            "retry_count": 0
        }

        status = executor.get_execution_status()

        assert status["executing_slots"] == 1
        assert len(status["executions"]) == 1
        assert status["executions"][0]["slot_id"] == "slot-005"

    def test_get_execution_status_reports_failures(self):
        """Test execution status includes failures"""
        executor = AutonomousSlotExecutor()

        # Add mock failure
        executor._failed_slots["slot-006"] = [
            {
                "timestamp": datetime.now(timezone.utc),
                "error": "Test error"
            }
        ]

        status = executor.get_execution_status()

        assert status["failed_slots"] == 1
        assert "slot-006" in status["failures"]
        assert len(status["failures"]["slot-006"]) == 1


class TestFailureLogging:
    """Test failure logging and tracking"""

    @pytest.mark.asyncio
    async def test_log_slot_failure_tracks_failure(self):
        """Test failures are logged correctly"""
        executor = AutonomousSlotExecutor()

        with patch.object(executor.event_bus, 'publish', new=AsyncMock()):
            await executor._log_slot_failure("slot-007", "Test error")

            assert "slot-007" in executor._failed_slots
            assert len(executor._failed_slots["slot-007"]) == 1
            assert executor._failed_slots["slot-007"][0]["error"] == "Test error"

    @pytest.mark.asyncio
    async def test_log_slot_failure_emits_event(self):
        """Test failure logging emits event"""
        executor = AutonomousSlotExecutor()

        with patch.object(executor.event_bus, 'publish', new=AsyncMock()) as mock_publish:
            await executor._log_slot_failure("slot-008", "Another error")

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args
            assert call_args[0][0] == "slot.execution.failed"
            assert call_args[0][1]["slot_id"] == "slot-008"

    @pytest.mark.asyncio
    async def test_multiple_failures_are_tracked(self):
        """Test multiple failures for same slot are tracked"""
        executor = AutonomousSlotExecutor()

        with patch.object(executor.event_bus, 'publish', new=AsyncMock()):
            await executor._log_slot_failure("slot-009", "Error 1")
            await executor._log_slot_failure("slot-009", "Error 2")
            await executor._log_slot_failure("slot-009", "Error 3")

            assert len(executor._failed_slots["slot-009"]) == 3


class TestDatabaseOperations:
    """Test database operations"""

    @pytest.mark.asyncio
    async def test_update_slot_status(self):
        """Test slot status update"""
        executor = AutonomousSlotExecutor()

        with patch.object(executor.engine, 'connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_conn

            await executor._update_slot_status("slot-010", SlotStatus.EXECUTING)

            # Verify execute was called
            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_slot_status(self):
        """Test getting slot status from database"""
        executor = AutonomousSlotExecutor()

        with patch.object(executor.engine, 'connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_conn

            # Mock result
            mock_result = MagicMock()
            mock_row = MagicMock()
            mock_row.status = SlotStatus.COMPLETED
            mock_result.fetchone.return_value = mock_row
            mock_conn.execute.return_value = mock_result

            status = await executor._get_slot_status("slot-011")

            assert status == SlotStatus.COMPLETED
