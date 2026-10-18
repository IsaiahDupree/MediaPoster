"""
Unit Tests for Automation Registry (BM-007)
============================================
Tests for automation CRUD, scheduling, status tracking, and metrics.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from services.automation_registry import (
    AutomationRegistry,
    get_automation_registry,
    AutomationStatus,
    AutomationType,
    RunStatus
)


@pytest.fixture
def registry():
    """Get automation registry instance"""
    return get_automation_registry()


@pytest.fixture
async def sample_automation(registry):
    """Create a sample automation for testing"""
    automation_id = await registry.register_automation(
        name="Test Automation",
        automation_type=AutomationType.WORKER.value,
        description="Test automation for unit tests",
        schedule_type="interval",
        schedule_config={"interval_seconds": 60},
        resource_requirements={"cpu": "low", "memory": "low"},
        priority=5,
        tags=["test"]
    )
    return automation_id


class TestAutomationRegistration:
    """Tests for registering and managing automations"""

    @pytest.mark.asyncio
    async def test_register_automation(self, registry):
        """Test registering a new automation"""
        automation_id = await registry.register_automation(
            name="Post Scheduler",
            automation_type=AutomationType.POST_SCHEDULER.value,
            description="Schedules posts at optimal times",
            schedule_type="interval",
            schedule_config={"interval_seconds": 60},
            resource_requirements={"cpu": "low", "memory": "low"},
            priority=8,
            max_concurrent_runs=1,
            tags=["scheduler", "posting"]
        )

        assert automation_id is not None
        assert len(automation_id) == 36  # UUID format

        # Verify it was created
        automation = await registry.get_automation(automation_id)
        assert automation is not None
        assert automation["name"] == "Post Scheduler"
        assert automation["automation_type"] == AutomationType.POST_SCHEDULER.value
        assert automation["status"] == AutomationStatus.ACTIVE.value
        assert automation["priority"] == 8

    @pytest.mark.asyncio
    async def test_get_automation(self, registry, sample_automation):
        """Test retrieving automation by ID"""
        automation = await registry.get_automation(sample_automation)

        assert automation is not None
        assert automation["id"] == sample_automation
        assert automation["name"] == "Test Automation"
        assert automation["enabled"] is True

    @pytest.mark.asyncio
    async def test_get_nonexistent_automation(self, registry):
        """Test retrieving automation that doesn't exist"""
        fake_id = str(uuid4())
        automation = await registry.get_automation(fake_id)

        assert automation is None


class TestAutomationListing:
    """Tests for listing and filtering automations"""

    @pytest.mark.asyncio
    async def test_list_all_automations(self, registry, sample_automation):
        """Test listing all automations"""
        automations = await registry.list_automations()

        assert len(automations) > 0
        assert any(a["id"] == sample_automation for a in automations)

    @pytest.mark.asyncio
    async def test_list_by_status(self, registry, sample_automation):
        """Test filtering automations by status"""
        # Pause the automation
        await registry.update_automation(
            sample_automation,
            status=AutomationStatus.PAUSED.value
        )

        # List paused automations
        paused = await registry.list_automations(status=AutomationStatus.PAUSED.value)

        assert len(paused) > 0
        assert any(a["id"] == sample_automation for a in paused)
        assert all(a["status"] == AutomationStatus.PAUSED.value for a in paused)

    @pytest.mark.asyncio
    async def test_list_by_type(self, registry, sample_automation):
        """Test filtering automations by type"""
        automations = await registry.list_automations(
            automation_type=AutomationType.WORKER.value
        )

        assert len(automations) > 0
        assert any(a["id"] == sample_automation for a in automations)

    @pytest.mark.asyncio
    async def test_list_enabled_only(self, registry, sample_automation):
        """Test filtering for enabled automations only"""
        automations = await registry.list_automations(enabled_only=True)

        assert len(automations) > 0
        assert all(a["enabled"] is True for a in automations)

    @pytest.mark.asyncio
    async def test_list_by_tags(self, registry, sample_automation):
        """Test filtering automations by tags"""
        automations = await registry.list_automations(tags=["test"])

        assert len(automations) > 0
        assert any(a["id"] == sample_automation for a in automations)


class TestAutomationUpdates:
    """Tests for updating automation configuration"""

    @pytest.mark.asyncio
    async def test_update_automation_name(self, registry, sample_automation):
        """Test updating automation name"""
        updated = await registry.update_automation(
            sample_automation,
            name="Updated Test Automation"
        )

        assert updated is True

        # Verify update
        automation = await registry.get_automation(sample_automation)
        assert automation["name"] == "Updated Test Automation"

    @pytest.mark.asyncio
    async def test_update_automation_status(self, registry, sample_automation):
        """Test updating automation status"""
        updated = await registry.update_automation(
            sample_automation,
            status=AutomationStatus.PAUSED.value
        )

        assert updated is True

        # Verify update
        automation = await registry.get_automation(sample_automation)
        assert automation["status"] == AutomationStatus.PAUSED.value

    @pytest.mark.asyncio
    async def test_update_automation_config(self, registry, sample_automation):
        """Test updating automation configuration"""
        new_config = {"custom_setting": "value", "enabled": True}

        updated = await registry.update_automation(
            sample_automation,
            config=new_config
        )

        assert updated is True

        # Verify update
        automation = await registry.get_automation(sample_automation)
        assert automation["config"] == new_config

    @pytest.mark.asyncio
    async def test_update_nonexistent_automation(self, registry):
        """Test updating automation that doesn't exist"""
        fake_id = str(uuid4())
        updated = await registry.update_automation(fake_id, name="Should Fail")

        assert updated is False


class TestAutomationDeletion:
    """Tests for deleting automations"""

    @pytest.mark.asyncio
    async def test_delete_automation(self, registry, sample_automation):
        """Test deleting an automation"""
        deleted = await registry.delete_automation(sample_automation)

        assert deleted is True

        # Verify deletion
        automation = await registry.get_automation(sample_automation)
        assert automation is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_automation(self, registry):
        """Test deleting automation that doesn't exist"""
        fake_id = str(uuid4())
        deleted = await registry.delete_automation(fake_id)

        assert deleted is False


class TestAutomationRuns:
    """Tests for automation run tracking"""

    @pytest.mark.asyncio
    async def test_start_run(self, registry, sample_automation):
        """Test starting an automation run"""
        run_id = await registry.start_run(
            automation_id=sample_automation,
            triggered_by="test",
            trigger_metadata={"test": True}
        )

        assert run_id is not None
        assert len(run_id) == 36  # UUID format

        # Verify automation current_runs incremented
        automation = await registry.get_automation(sample_automation)
        assert automation["current_runs"] == 1

    @pytest.mark.asyncio
    async def test_start_run_for_disabled_automation(self, registry, sample_automation):
        """Test starting run for disabled automation"""
        # Disable automation
        await registry.update_automation(sample_automation, enabled=False)

        run_id = await registry.start_run(automation_id=sample_automation)

        assert run_id is None

    @pytest.mark.asyncio
    async def test_start_run_max_concurrent_reached(self, registry, sample_automation):
        """Test starting run when max concurrent runs reached"""
        # Start first run
        run1_id = await registry.start_run(automation_id=sample_automation)
        assert run1_id is not None

        # Try to start second run (should fail, max_concurrent_runs=1)
        run2_id = await registry.start_run(automation_id=sample_automation)
        assert run2_id is None

    @pytest.mark.asyncio
    async def test_complete_run_success(self, registry, sample_automation):
        """Test completing a successful run"""
        # Start run
        run_id = await registry.start_run(automation_id=sample_automation)

        # Wait a bit
        await asyncio.sleep(0.1)

        # Complete run
        completed = await registry.complete_run(
            run_id=run_id,
            status=RunStatus.SUCCESS.value,
            result_data={"processed": 10}
        )

        assert completed is True

        # Verify automation metrics updated
        automation = await registry.get_automation(sample_automation)
        assert automation["total_runs"] == 1
        assert automation["successful_runs"] == 1
        assert automation["failed_runs"] == 0
        assert automation["current_runs"] == 0

    @pytest.mark.asyncio
    async def test_complete_run_failure(self, registry, sample_automation):
        """Test completing a failed run"""
        # Start run
        run_id = await registry.start_run(automation_id=sample_automation)

        # Wait a bit
        await asyncio.sleep(0.1)

        # Complete run with error
        completed = await registry.complete_run(
            run_id=run_id,
            status=RunStatus.FAILURE.value,
            error_message="Test error"
        )

        assert completed is True

        # Verify automation metrics updated
        automation = await registry.get_automation(sample_automation)
        assert automation["total_runs"] == 1
        assert automation["successful_runs"] == 0
        assert automation["failed_runs"] == 1
        assert automation["last_run_status"] == RunStatus.FAILURE.value
        assert automation["last_run_error"] == "Test error"

    @pytest.mark.asyncio
    async def test_complete_nonexistent_run(self, registry):
        """Test completing run that doesn't exist"""
        fake_id = str(uuid4())
        completed = await registry.complete_run(fake_id, status=RunStatus.SUCCESS.value)

        assert completed is False


class TestRunHistory:
    """Tests for run history tracking"""

    @pytest.mark.asyncio
    async def test_get_run_history(self, registry, sample_automation):
        """Test retrieving run history"""
        # Create some runs
        for i in range(3):
            run_id = await registry.start_run(automation_id=sample_automation)
            await asyncio.sleep(0.05)
            await registry.complete_run(run_id, status=RunStatus.SUCCESS.value)

        # Get history
        history = await registry.get_run_history(sample_automation, limit=10)

        assert len(history) == 3
        # Most recent first
        assert history[0]["started_at"] > history[1]["started_at"]

    @pytest.mark.asyncio
    async def test_get_run_history_with_status_filter(self, registry, sample_automation):
        """Test filtering run history by status"""
        # Create successful run
        run1_id = await registry.start_run(automation_id=sample_automation)
        await registry.complete_run(run1_id, status=RunStatus.SUCCESS.value)

        # Create failed run
        run2_id = await registry.start_run(automation_id=sample_automation)
        await registry.complete_run(run2_id, status=RunStatus.FAILURE.value)

        # Get only failures
        failures = await registry.get_run_history(
            sample_automation,
            status=RunStatus.FAILURE.value
        )

        assert len(failures) > 0
        assert all(r["status"] == RunStatus.FAILURE.value for r in failures)

    @pytest.mark.asyncio
    async def test_get_active_runs(self, registry, sample_automation):
        """Test retrieving active runs"""
        # Start a run (don't complete it)
        run_id = await registry.start_run(automation_id=sample_automation)

        # Get active runs
        active = await registry.get_active_runs()

        assert len(active) > 0
        assert any(r["id"] == run_id for r in active)
        assert all(r["status"] == RunStatus.RUNNING.value for r in active)


class TestStatistics:
    """Tests for registry statistics"""

    @pytest.mark.asyncio
    async def test_get_stats(self, registry, sample_automation):
        """Test retrieving registry statistics"""
        # Create some activity
        run_id = await registry.start_run(automation_id=sample_automation)
        await registry.complete_run(run_id, status=RunStatus.SUCCESS.value)

        # Get stats
        stats = await registry.get_stats()

        assert "automations" in stats
        assert "runs_24h" in stats
        assert "timestamp" in stats

        # Check automation counts
        assert stats["automations"]["total"] > 0
        assert stats["automations"]["active"] >= 0

        # Check run stats
        assert "total_runs_24h" in stats["runs_24h"]
        assert "successful_runs_24h" in stats["runs_24h"]


class TestSingletonPattern:
    """Tests for singleton pattern"""

    def test_singleton_instance(self):
        """Test that get_instance returns same instance"""
        registry1 = get_automation_registry()
        registry2 = get_automation_registry()

        assert registry1 is registry2

    def test_cannot_create_multiple_instances(self):
        """Test that direct instantiation raises error"""
        with pytest.raises(RuntimeError):
            AutomationRegistry()
