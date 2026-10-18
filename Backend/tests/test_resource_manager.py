"""
Tests for Resource Manager Service (BM-005)
=============================================
Validates CPU/Memory/GPU monitoring, throttle level calculation,
singleton pattern, history, and EventBus integration.

Test Categories:
- Singleton & initialisation            (6 tests)
- ThrottleLevel enum                    (5 tests)
- ResourceSnapshot dataclass            (4 tests)
- Throttle level computation            (12 tests)
- get_snapshot                          (4 tests)
- should_throttle / should_pause        (6 tests)
- History                               (4 tests)
- EventBus integration                  (4 tests)
- Monitoring start / stop               (3 tests)

Total: 48 tests
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.resource_manager import (
    ResourceManager,
    ResourceSnapshot,
    ThrottleLevel,
    _GPU_AVAILABLE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the ResourceManager singleton before and after every test."""
    ResourceManager.reset_instance()
    yield
    ResourceManager.reset_instance()


@pytest.fixture
def manager() -> ResourceManager:
    """Return a fresh ResourceManager instance."""
    return ResourceManager.get_instance()


# ===========================================================================
# 1. SINGLETON & INITIALISATION
# ===========================================================================

class TestSingleton:
    """Verify singleton pattern behaviour."""

    def test_get_instance_creates_instance(self):
        """First call to get_instance() creates the singleton."""
        inst = ResourceManager.get_instance()
        assert inst is not None
        assert isinstance(inst, ResourceManager)

    def test_get_instance_returns_same_object(self):
        """Repeated calls return the same object."""
        a = ResourceManager.get_instance()
        b = ResourceManager.get_instance()
        assert a is b

    def test_direct_init_after_singleton_raises(self):
        """Creating a second instance via __init__ raises RuntimeError."""
        ResourceManager.get_instance()
        with pytest.raises(RuntimeError, match="get_instance"):
            ResourceManager()

    def test_reset_instance_clears_singleton(self):
        """reset_instance allows a new singleton to be created."""
        first = ResourceManager.get_instance()
        ResourceManager.reset_instance()
        second = ResourceManager.get_instance()
        assert first is not second

    def test_initial_throttle_is_none(self, manager: ResourceManager):
        """Freshly created manager starts at ThrottleLevel.NONE."""
        assert manager.get_throttle_level() == ThrottleLevel.NONE

    def test_initial_history_is_empty(self, manager: ResourceManager):
        """No history snapshots on a fresh instance."""
        assert manager.get_history() == []


# ===========================================================================
# 2. THROTTLE LEVEL ENUM
# ===========================================================================

class TestThrottleLevelEnum:
    """ThrottleLevel enum values and ordering."""

    def test_enum_values_exist(self):
        """All five levels exist."""
        assert ThrottleLevel.NONE.value == 0
        assert ThrottleLevel.LIGHT.value == 1
        assert ThrottleLevel.MEDIUM.value == 2
        assert ThrottleLevel.HEAVY.value == 3
        assert ThrottleLevel.CRITICAL.value == 4

    def test_ordering(self):
        """Levels are comparable by severity."""
        assert ThrottleLevel.NONE < ThrottleLevel.LIGHT
        assert ThrottleLevel.LIGHT < ThrottleLevel.MEDIUM
        assert ThrottleLevel.MEDIUM < ThrottleLevel.HEAVY
        assert ThrottleLevel.HEAVY < ThrottleLevel.CRITICAL

    def test_names(self):
        """Enum .name attribute is correct."""
        assert ThrottleLevel.NONE.name == "NONE"
        assert ThrottleLevel.CRITICAL.name == "CRITICAL"

    def test_int_conversion(self):
        """Can be used as int."""
        assert int(ThrottleLevel.MEDIUM) == 2

    def test_membership(self):
        """Enum has exactly five members."""
        assert len(ThrottleLevel) == 5


# ===========================================================================
# 3. RESOURCE SNAPSHOT DATACLASS
# ===========================================================================

class TestResourceSnapshot:
    """ResourceSnapshot creation and serialisation."""

    def test_create_minimal(self):
        """Create snapshot with only required fields."""
        snap = ResourceSnapshot(
            cpu_percent=45.0,
            memory_percent=60.0,
            memory_available_mb=4096.0,
        )
        assert snap.cpu_percent == 45.0
        assert snap.memory_percent == 60.0
        assert snap.memory_available_mb == 4096.0
        assert snap.gpu_percent is None
        assert snap.gpu_memory_percent is None
        assert snap.throttle_level == ThrottleLevel.NONE

    def test_create_with_gpu(self):
        """Create snapshot including GPU fields."""
        snap = ResourceSnapshot(
            cpu_percent=80.0,
            memory_percent=70.0,
            memory_available_mb=2048.0,
            gpu_percent=55.0,
            gpu_memory_percent=40.0,
            throttle_level=ThrottleLevel.MEDIUM,
        )
        assert snap.gpu_percent == 55.0
        assert snap.gpu_memory_percent == 40.0
        assert snap.throttle_level == ThrottleLevel.MEDIUM

    def test_to_dict(self):
        """to_dict includes all expected keys."""
        snap = ResourceSnapshot(
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_available_mb=3000.0,
            throttle_level=ThrottleLevel.LIGHT,
        )
        d = snap.to_dict()
        assert d["cpu_percent"] == 50.0
        assert d["memory_percent"] == 60.0
        assert d["memory_available_mb"] == 3000.0
        assert d["throttle_level"] == "LIGHT"
        assert d["throttle_level_value"] == 1
        assert "timestamp" in d
        assert d["gpu_percent"] is None

    def test_timestamp_defaults_to_now(self):
        """Default timestamp should be close to now (UTC)."""
        before = datetime.now(timezone.utc)
        snap = ResourceSnapshot(
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_available_mb=0.0,
        )
        after = datetime.now(timezone.utc)
        assert before <= snap.timestamp <= after


# ===========================================================================
# 4. THROTTLE LEVEL COMPUTATION
# ===========================================================================

class TestThrottleComputation:
    """Test compute_throttle_level static method."""

    # --- CPU-only tests (memory below bump threshold) ---------------------

    def test_cpu_below_50_is_none(self):
        """CPU < 50% => NONE."""
        assert ResourceManager.compute_throttle_level(0.0, 0.0) == ThrottleLevel.NONE
        assert ResourceManager.compute_throttle_level(49.9, 50.0) == ThrottleLevel.NONE

    def test_cpu_50_is_light(self):
        """CPU == 50% => LIGHT."""
        assert ResourceManager.compute_throttle_level(50.0, 0.0) == ThrottleLevel.LIGHT

    def test_cpu_60_is_light(self):
        """CPU 50-70% => LIGHT."""
        assert ResourceManager.compute_throttle_level(60.0, 0.0) == ThrottleLevel.LIGHT

    def test_cpu_70_is_medium(self):
        """CPU == 70% => MEDIUM."""
        assert ResourceManager.compute_throttle_level(70.0, 0.0) == ThrottleLevel.MEDIUM

    def test_cpu_80_is_medium(self):
        """CPU 70-85% => MEDIUM."""
        assert ResourceManager.compute_throttle_level(80.0, 0.0) == ThrottleLevel.MEDIUM

    def test_cpu_85_is_heavy(self):
        """CPU == 85% => HEAVY."""
        assert ResourceManager.compute_throttle_level(85.0, 0.0) == ThrottleLevel.HEAVY

    def test_cpu_90_is_heavy(self):
        """CPU 85-95% => HEAVY."""
        assert ResourceManager.compute_throttle_level(90.0, 0.0) == ThrottleLevel.HEAVY

    def test_cpu_95_is_critical(self):
        """CPU == 95% => CRITICAL."""
        assert ResourceManager.compute_throttle_level(95.0, 0.0) == ThrottleLevel.CRITICAL

    def test_cpu_100_is_critical(self):
        """CPU 100% => CRITICAL."""
        assert ResourceManager.compute_throttle_level(100.0, 0.0) == ThrottleLevel.CRITICAL

    # --- Memory bump tests ------------------------------------------------

    def test_memory_bump_none_to_light(self):
        """Memory > 90% bumps NONE -> LIGHT."""
        assert ResourceManager.compute_throttle_level(30.0, 91.0) == ThrottleLevel.LIGHT

    def test_memory_bump_heavy_to_critical(self):
        """Memory > 90% bumps HEAVY -> CRITICAL."""
        assert ResourceManager.compute_throttle_level(90.0, 95.0) == ThrottleLevel.CRITICAL

    def test_memory_bump_critical_stays_critical(self):
        """Memory > 90% cannot bump beyond CRITICAL."""
        assert ResourceManager.compute_throttle_level(96.0, 95.0) == ThrottleLevel.CRITICAL


# ===========================================================================
# 5. get_snapshot
# ===========================================================================

class TestGetSnapshot:
    """Test the get_snapshot method with mocked psutil."""

    @patch("services.resource_manager.psutil")
    def test_returns_resource_snapshot(self, mock_psutil, manager: ResourceManager):
        """get_snapshot returns a ResourceSnapshot instance."""
        mock_psutil.cpu_percent.return_value = 42.0
        mock_mem = MagicMock()
        mock_mem.percent = 55.0
        mock_mem.available = 4096 * 1024 * 1024  # 4096 MB
        mock_psutil.virtual_memory.return_value = mock_mem

        snap = manager.get_snapshot()
        assert isinstance(snap, ResourceSnapshot)
        assert snap.cpu_percent == 42.0
        assert snap.memory_percent == 55.0
        assert snap.memory_available_mb == 4096.0

    @patch("services.resource_manager.psutil")
    def test_snapshot_throttle_computed(self, mock_psutil, manager: ResourceManager):
        """Throttle level in snapshot matches compute_throttle_level."""
        mock_psutil.cpu_percent.return_value = 75.0
        mock_mem = MagicMock()
        mock_mem.percent = 60.0
        mock_mem.available = 2048 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_mem

        snap = manager.get_snapshot()
        expected = ResourceManager.compute_throttle_level(75.0, 60.0)
        assert snap.throttle_level == expected
        assert snap.throttle_level == ThrottleLevel.MEDIUM

    @patch("services.resource_manager.psutil")
    def test_snapshot_no_gpu_when_unavailable(self, mock_psutil, manager: ResourceManager):
        """GPU fields are None when GPUtil is not available."""
        mock_psutil.cpu_percent.return_value = 10.0
        mock_mem = MagicMock()
        mock_mem.percent = 30.0
        mock_mem.available = 8000 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_mem

        # Ensure GPU path returns None
        with patch.object(manager, "_read_gpu", return_value=(None, None)):
            snap = manager.get_snapshot()
            assert snap.gpu_percent is None
            assert snap.gpu_memory_percent is None

    @patch("services.resource_manager.psutil")
    def test_snapshot_with_gpu(self, mock_psutil, manager: ResourceManager):
        """GPU fields are populated when available."""
        mock_psutil.cpu_percent.return_value = 20.0
        mock_mem = MagicMock()
        mock_mem.percent = 40.0
        mock_mem.available = 6000 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_mem

        with patch.object(manager, "_read_gpu", return_value=(65.0, 50.0)):
            snap = manager.get_snapshot()
            assert snap.gpu_percent == 65.0
            assert snap.gpu_memory_percent == 50.0


# ===========================================================================
# 6. should_throttle / should_pause
# ===========================================================================

class TestShouldThrottleAndPause:
    """Test convenience boolean accessors."""

    def test_should_throttle_false_for_none(self, manager: ResourceManager):
        """NONE => should_throttle is False."""
        manager._current_throttle = ThrottleLevel.NONE
        assert manager.should_throttle() is False

    def test_should_throttle_false_for_light(self, manager: ResourceManager):
        """LIGHT => should_throttle is False."""
        manager._current_throttle = ThrottleLevel.LIGHT
        assert manager.should_throttle() is False

    def test_should_throttle_true_for_medium(self, manager: ResourceManager):
        """MEDIUM => should_throttle is True."""
        manager._current_throttle = ThrottleLevel.MEDIUM
        assert manager.should_throttle() is True

    def test_should_throttle_true_for_heavy(self, manager: ResourceManager):
        """HEAVY => should_throttle is True."""
        manager._current_throttle = ThrottleLevel.HEAVY
        assert manager.should_throttle() is True

    def test_should_pause_false_for_heavy(self, manager: ResourceManager):
        """HEAVY => should_pause is False."""
        manager._current_throttle = ThrottleLevel.HEAVY
        assert manager.should_pause() is False

    def test_should_pause_true_for_critical(self, manager: ResourceManager):
        """CRITICAL => should_pause is True."""
        manager._current_throttle = ThrottleLevel.CRITICAL
        assert manager.should_pause() is True


# ===========================================================================
# 7. HISTORY
# ===========================================================================

class TestHistory:
    """Test snapshot history retrieval."""

    def test_empty_history(self, manager: ResourceManager):
        """No history when no snapshots have been collected."""
        assert manager.get_history(minutes=5) == []

    def test_history_returns_recent(self, manager: ResourceManager):
        """get_history filters by time window."""
        now = datetime.now(timezone.utc)

        # Add a snapshot from 2 minutes ago
        recent = ResourceSnapshot(
            cpu_percent=40.0,
            memory_percent=50.0,
            memory_available_mb=4000.0,
            timestamp=now - timedelta(minutes=2),
        )
        # Add a snapshot from 10 minutes ago (outside default 5-min window)
        old = ResourceSnapshot(
            cpu_percent=80.0,
            memory_percent=90.0,
            memory_available_mb=1000.0,
            timestamp=now - timedelta(minutes=10),
        )

        manager._history.append(old)
        manager._history.append(recent)

        result = manager.get_history(minutes=5)
        assert len(result) == 1
        assert result[0].cpu_percent == 40.0

    def test_history_with_large_window(self, manager: ResourceManager):
        """Larger window includes older snapshots."""
        now = datetime.now(timezone.utc)

        old = ResourceSnapshot(
            cpu_percent=80.0,
            memory_percent=90.0,
            memory_available_mb=1000.0,
            timestamp=now - timedelta(minutes=10),
        )
        recent = ResourceSnapshot(
            cpu_percent=40.0,
            memory_percent=50.0,
            memory_available_mb=4000.0,
            timestamp=now - timedelta(minutes=2),
        )

        manager._history.append(old)
        manager._history.append(recent)

        result = manager.get_history(minutes=15)
        assert len(result) == 2

    def test_history_respects_max_size(self, manager: ResourceManager):
        """History deque is bounded by MAX_HISTORY."""
        now = datetime.now(timezone.utc)
        for i in range(ResourceManager.MAX_HISTORY + 50):
            snap = ResourceSnapshot(
                cpu_percent=float(i % 100),
                memory_percent=50.0,
                memory_available_mb=4000.0,
                timestamp=now,
            )
            manager._history.append(snap)
        assert len(manager._history) == ResourceManager.MAX_HISTORY


# ===========================================================================
# 8. EVENT BUS INTEGRATION
# ===========================================================================

class TestEventBusIntegration:
    """Test EventBus event emission on throttle changes and alerts."""

    @pytest.mark.asyncio
    async def test_throttle_changed_event(self, manager: ResourceManager):
        """Changing throttle level emits resource.throttle_changed."""
        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock()
        manager._event_bus = mock_bus

        await manager._emit_throttle_changed(ThrottleLevel.NONE, ThrottleLevel.HEAVY)

        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        assert call_args[0][0] == "resource.throttle_changed"
        payload = call_args[0][1]
        assert payload["old_level"] == "NONE"
        assert payload["new_level"] == "HEAVY"

    @pytest.mark.asyncio
    async def test_alert_event(self, manager: ResourceManager):
        """HEAVY/CRITICAL snapshots emit resource.alert."""
        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock()
        manager._event_bus = mock_bus

        snap = ResourceSnapshot(
            cpu_percent=92.0,
            memory_percent=85.0,
            memory_available_mb=1024.0,
            throttle_level=ThrottleLevel.HEAVY,
        )
        await manager._emit_alert(snap)

        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        assert call_args[0][0] == "resource.alert"
        payload = call_args[0][1]
        assert payload["throttle_level"] == "HEAVY"
        assert payload["cpu_percent"] == 92.0

    @pytest.mark.asyncio
    async def test_sleep_suggested_after_sustained_critical(self, manager: ResourceManager):
        """Sustained CRITICAL for > 30s emits resource.sleep_suggested."""
        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock()
        manager._event_bus = mock_bus

        # Simulate having been critical for 31 seconds
        manager._critical_since = time.monotonic() - 31
        manager._sleep_suggested = False

        await manager._check_critical_duration(ThrottleLevel.CRITICAL)

        assert manager._sleep_suggested is True
        # Should have published sleep_suggested event
        publish_calls = mock_bus.publish.call_args_list
        topics = [c[0][0] for c in publish_calls]
        assert "resource.sleep_suggested" in topics

    @pytest.mark.asyncio
    async def test_critical_resets_on_recovery(self, manager: ResourceManager):
        """Dropping below CRITICAL resets the critical timer."""
        manager._critical_since = time.monotonic() - 10
        manager._sleep_suggested = False

        # Now drop to HEAVY
        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock()
        manager._event_bus = mock_bus

        await manager._check_critical_duration(ThrottleLevel.HEAVY)

        assert manager._critical_since is None
        assert manager._sleep_suggested is False


# ===========================================================================
# 9. MONITORING START / STOP
# ===========================================================================

class TestMonitoring:
    """Test start_monitoring and stop_monitoring lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_flag(self, manager: ResourceManager):
        """start_monitoring sets _is_monitoring to True."""
        with patch("services.resource_manager.psutil"):
            await manager.start_monitoring(interval=100)
            assert manager._is_monitoring is True
            await manager.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stop_clears_flag(self, manager: ResourceManager):
        """stop_monitoring sets _is_monitoring to False."""
        with patch("services.resource_manager.psutil"):
            await manager.start_monitoring(interval=100)
            await manager.stop_monitoring()
            assert manager._is_monitoring is False

    @pytest.mark.asyncio
    async def test_double_start_is_noop(self, manager: ResourceManager):
        """Calling start_monitoring twice does not create a second task."""
        with patch("services.resource_manager.psutil"):
            await manager.start_monitoring(interval=100)
            task1 = manager._monitoring_task
            await manager.start_monitoring(interval=100)
            task2 = manager._monitoring_task
            assert task1 is task2
            await manager.stop_monitoring()


# ===========================================================================
# 10. get_status
# ===========================================================================

class TestGetStatus:
    """Test the get_status introspection method."""

    def test_status_keys(self, manager: ResourceManager):
        """get_status returns expected keys."""
        status = manager.get_status()
        assert "is_monitoring" in status
        assert "interval_seconds" in status
        assert "current_throttle_level" in status
        assert "current_throttle_value" in status
        assert "gpu_available" in status
        assert "history_size" in status
        assert "latest_snapshot" in status

    def test_status_defaults(self, manager: ResourceManager):
        """Default status has sensible values."""
        status = manager.get_status()
        assert status["is_monitoring"] is False
        assert status["current_throttle_level"] == "NONE"
        assert status["current_throttle_value"] == 0
        assert status["history_size"] == 0
        assert status["latest_snapshot"] is None

    def test_status_after_snapshot(self, manager: ResourceManager):
        """After adding a snapshot, latest_snapshot is populated."""
        snap = ResourceSnapshot(
            cpu_percent=55.0,
            memory_percent=65.0,
            memory_available_mb=3000.0,
            throttle_level=ThrottleLevel.LIGHT,
        )
        manager._history.append(snap)
        status = manager.get_status()
        assert status["history_size"] == 1
        assert status["latest_snapshot"] is not None
        assert status["latest_snapshot"]["cpu_percent"] == 55.0
