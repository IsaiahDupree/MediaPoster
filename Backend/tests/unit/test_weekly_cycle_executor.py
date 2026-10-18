"""
Unit tests for Weekly Cycle Executor (NAR-004)
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from services.narrative_scheduler.weekly_executor import (
    WeeklyCycleExecutor,
    ExecutionState,
    DailySlotExecution,
    WeeklyCycleMetrics
)


@pytest.fixture
def mock_event_bus():
    """Mock EventBus"""
    mock_bus = Mock()
    mock_bus.publish = AsyncMock()
    mock_bus.set_source = Mock()
    return mock_bus


@pytest.fixture
def mock_database():
    """Mock database engine"""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_engine.connect.return_value.__exit__.return_value = None
    return mock_engine, mock_conn


class TestWeeklyCycleExecutorCore:
    """Test core functionality"""

    def test_singleton_pattern(self):
        """Test that WeeklyCycleExecutor follows singleton pattern"""
        # Reset singleton
        WeeklyCycleExecutor._instance = None

        executor1 = WeeklyCycleExecutor.get_instance()
        executor2 = WeeklyCycleExecutor.get_instance()

        assert executor1 is executor2

    @pytest.mark.asyncio
    async def test_start_stop(self, mock_event_bus, mock_database):
        """Test service start and stop"""
        WeeklyCycleExecutor._instance = None
        executor = WeeklyCycleExecutor()

        with patch.object(executor, 'event_bus', mock_event_bus):
            with patch.object(executor, 'engine', mock_database[0]):
                # Mock _execution_loop
                executor._execution_loop = AsyncMock()

                await executor.start()
                assert executor._is_running is True
                assert executor._task is not None

                await executor.stop()
                assert executor._is_running is False


class TestDailySlotExecution:
    """Test daily slot execution"""

    @pytest.mark.asyncio
    async def test_execute_daily_slots_no_plan(self, mock_event_bus, mock_database):
        """Test execution when no active plan exists"""
        WeeklyCycleExecutor._instance = None
        executor = WeeklyCycleExecutor()

        with patch.object(executor, '_get_current_week_plan', AsyncMock(return_value=None)):
            results = await executor.execute_daily_slots()
            assert results == []

    @pytest.mark.asyncio
    async def test_execute_daily_slots_no_slots(self, mock_event_bus, mock_database):
        """Test execution when no slots for today"""
        WeeklyCycleExecutor._instance = None
        executor = WeeklyCycleExecutor()

        mock_plan = {"id": "week-123", "status": "active"}

        with patch.object(executor, '_get_current_week_plan', AsyncMock(return_value=mock_plan)):
            with patch.object(executor, '_get_today_slots', AsyncMock(return_value=[])):
                results = await executor.execute_daily_slots()
                assert results == []

    @pytest.mark.asyncio
    async def test_execute_single_slot_success(self, mock_event_bus):
        """Test successful execution of a single slot"""
        WeeklyCycleExecutor._instance = None
        executor = WeeklyCycleExecutor()

        # Mock slot
        slot = {
            "id": "slot-123",
            "pillar_name": "Pain Points",
            "template_id": "template-456",
            "scheduled_time": datetime.now(timezone.utc),
            "platform": "tiktok",
            "account_id": "acc-789"
        }

        # Mock content selection
        mock_content = {
            "content_id": "content-123",
            "title": "Test Content"
        }

        # Mock services
        with patch('services.narrative_scheduler.content_selector.ContentSelector.get_instance') as mock_selector:
            with patch('services.content_generation_pipeline.ContentGenerationPipeline') as mock_gen:
                with patch('services.qa_gate_service.QAGateService.get_instance') as mock_qa:
                    # Setup mocks
                    mock_selector.return_value.select_content_for_slot = AsyncMock(return_value=mock_content)
                    mock_gen.return_value.generate_from_template = AsyncMock(return_value={"text": "Generated post"})
                    mock_qa.return_value.check_content = AsyncMock(return_value={"approved": True})

                    # Execute slot
                    result = await executor._execute_slot(slot)

                    # Assertions
                    assert result.content_selected is True
                    assert result.content_id == "content-123"
                    assert result.generation_status == "success"
                    assert result.qa_passed is True
                    assert result.published is True
                    assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_slot_qa_failure(self):
        """Test slot execution when QA fails"""
        WeeklyCycleExecutor._instance = None
        executor = WeeklyCycleExecutor()

        slot = {
            "id": "slot-123",
            "pillar_name": "Pain Points",
            "template_id": "template-456",
            "scheduled_time": datetime.now(timezone.utc)
        }

        mock_content = {"content_id": "content-123"}

        with patch('services.narrative_scheduler.content_selector.ContentSelector.get_instance') as mock_selector:
            with patch('services.content_generation_pipeline.ContentGenerationPipeline') as mock_gen:
                with patch('services.qa_gate_service.QAGateService.get_instance') as mock_qa:
                    mock_selector.return_value.select_content_for_slot = AsyncMock(return_value=mock_content)
                    mock_gen.return_value.generate_from_template = AsyncMock(return_value={"text": "Bad content"})
                    mock_qa.return_value.check_content = AsyncMock(return_value={
                        "approved": False,
                        "reason": "Contains banned phrase"
                    })

                    result = await executor._execute_slot(slot)

                    assert result.qa_passed is False
                    assert result.published is False
                    assert "QA failed" in result.errors[0]


class TestWeeklyReflection:
    """Test weekly reflection functionality"""

    @pytest.mark.asyncio
    async def test_run_weekly_reflection_no_plan(self):
        """Test reflection when no active plan"""
        WeeklyCycleExecutor._instance = None
        executor = WeeklyCycleExecutor()

        with patch.object(executor, '_get_current_week_plan', AsyncMock(return_value=None)):
            result = await executor._run_weekly_reflection_cycle()
            assert result["success"] is False
            assert "No active plan" in result["reason"]

    @pytest.mark.asyncio
    async def test_run_weekly_reflection_success(self):
        """Test successful weekly reflection"""
        WeeklyCycleExecutor._instance = None
        executor = WeeklyCycleExecutor()

        mock_plan = {"id": "week-123", "status": "active"}
        mock_reflection = Mock()
        mock_reflection.learnings = [
            Mock(category="template", insight="Template A outperformed by 2x", confidence=0.9)
        ]
        mock_reflection.best_performing_pillar = "Pain Points"
        mock_reflection.recommendations = ["Increase Pain Points allocation"]
        mock_reflection.to_dict = Mock(return_value={"summary": "Week performed well"})

        with patch.object(executor, '_get_current_week_plan', AsyncMock(return_value=mock_plan)):
            with patch('services.narrative_scheduler.reflection_system.ReflectionSystem') as MockReflection:
                mock_reflection_system = MockReflection.return_value
                mock_reflection_system.generate_weekly_reflection = AsyncMock(return_value=mock_reflection)

                with patch.object(executor, '_store_learnings', AsyncMock()):
                    with patch.object(executor.event_bus, 'publish', AsyncMock()):
                        result = await executor._run_weekly_reflection_cycle()

                        assert result["success"] is True
                        assert result["week_id"] == "week-123"
                        assert len(result["learnings"]) == 1


class TestCycleMetrics:
    """Test cycle metrics calculation"""

    @pytest.mark.asyncio
    async def test_get_cycle_metrics(self):
        """Test getting cycle metrics"""
        WeeklyCycleExecutor._instance = None
        executor = WeeklyCycleExecutor()

        # Add some execution history
        executor.execution_history = [
            DailySlotExecution(
                slot_id="week-123-1",
                scheduled_time=datetime.now(timezone.utc),
                content_selected=True,
                content_id="content-1",
                generation_status="success",
                qa_passed=True,
                published=True,
                metrics={}
            ),
            DailySlotExecution(
                slot_id="week-123-2",
                scheduled_time=datetime.now(timezone.utc),
                content_selected=True,
                content_id="content-2",
                generation_status="success",
                qa_passed=False,
                published=False,
                metrics={},
                errors=["QA failed"]
            )
        ]

        mock_plan = {"id": "week-123"}

        with patch.object(executor, '_get_current_week_plan', AsyncMock(return_value=mock_plan)):
            with patch.object(executor, '_get_learnings', AsyncMock(return_value=[{"type": "test"}])):
                metrics = await executor.get_cycle_metrics("week-123")

                assert metrics.week_id == "week-123"
                assert metrics.total_slots == 2
                assert metrics.executed_slots == 1
                assert metrics.failed_slots == 1
                assert metrics.learnings_count == 1


class TestStateManagement:
    """Test state management"""

    def test_initial_state(self):
        """Test executor starts in IDLE state"""
        WeeklyCycleExecutor._instance = None
        executor = WeeklyCycleExecutor()

        assert executor.state == ExecutionState.IDLE

    @pytest.mark.asyncio
    async def test_state_transitions(self):
        """Test state transitions during execution"""
        WeeklyCycleExecutor._instance = None
        executor = WeeklyCycleExecutor()

        # Mock plan and slots
        with patch.object(executor, '_get_current_week_plan', AsyncMock(return_value={"id": "week-123"})):
            with patch.object(executor, '_get_today_slots', AsyncMock(return_value=[])):
                # Execute slots should transition to EXECUTING then back to IDLE
                await executor.execute_daily_slots()
                # Since no slots, should go back to IDLE immediately
                assert executor.state == ExecutionState.IDLE
