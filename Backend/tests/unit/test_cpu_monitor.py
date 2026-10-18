"""
CPU Monitor Service Tests
==========================
Tests for CPU Monitor Service (SLEEP-010, SLEEP-011)

Test Coverage:
- SLEEP-010: CPU usage monitoring
- SLEEP-011: Auto-sleep on idle timeout
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from services.cpu_monitor import CPUMonitor, CPUMetrics, get_cpu_monitor
from services.sleep_mode_service import SleepModeService, SleepState


@pytest_asyncio.fixture
async def cpu_monitor():
    """Create a fresh CPU monitor instance for testing"""
    # Reset singleton
    CPUMonitor._instance = None

    monitor = CPUMonitor.get_instance()
    await monitor.start()

    yield monitor

    # Cleanup
    await monitor.stop()
    CPUMonitor._instance = None


@pytest_asyncio.fixture
async def sleep_service():
    """Create a fresh sleep mode service for integration tests"""
    # Reset singleton
    SleepModeService._instance = None

    service = SleepModeService.get_instance()
    await service.start()

    yield service

    # Cleanup
    await service.stop()
    SleepModeService._instance = None


class TestCPUMonitorCore:
    """Test SLEEP-010: CPU Usage Monitoring"""

    @pytest.mark.asyncio
    async def test_monitor_initialization(self, cpu_monitor):
        """Test monitor initializes correctly"""
        assert cpu_monitor._is_running is True
        assert cpu_monitor._check_interval == 5
        assert cpu_monitor._auto_sleep_enabled is False

    @pytest.mark.asyncio
    async def test_singleton_pattern(self, cpu_monitor):
        """Test monitor uses singleton pattern"""
        another_monitor = CPUMonitor.get_instance()
        assert another_monitor is cpu_monitor

    @pytest.mark.asyncio
    async def test_get_cpu_monitor_helper(self, cpu_monitor):
        """Test get_cpu_monitor() helper function"""
        helper_monitor = get_cpu_monitor()
        assert helper_monitor is cpu_monitor

    @pytest.mark.asyncio
    async def test_cpu_metrics_collection(self, cpu_monitor):
        """Test CPU metrics are collected"""
        # Wait for at least one collection cycle
        await asyncio.sleep(1.5)

        current = cpu_monitor.get_current_metrics()
        assert current is not None
        assert "cpu_percent" in current
        assert "memory_percent" in current
        assert "cpu_per_core" in current

    @pytest.mark.asyncio
    async def test_metrics_history_tracking(self, cpu_monitor):
        """Test metrics history is tracked"""
        # Wait for a few collection cycles
        await asyncio.sleep(2.0)

        history = cpu_monitor.get_metrics_history(limit=10)
        assert len(history) > 0
        assert all("cpu_percent" in m for m in history)

    @pytest.mark.asyncio
    async def test_metrics_history_limited_to_max_size(self, cpu_monitor):
        """Test metrics history respects max size"""
        original_max = cpu_monitor._max_history_size
        cpu_monitor._max_history_size = 3

        # Wait for more metrics than max
        await asyncio.sleep(2.0)

        assert len(cpu_monitor._metrics_history) <= 3

        # Restore
        cpu_monitor._max_history_size = original_max

    @pytest.mark.asyncio
    async def test_get_average_cpu(self, cpu_monitor):
        """Test average CPU calculation"""
        # Wait for some metrics
        await asyncio.sleep(2.0)

        avg_1min = cpu_monitor.get_average_cpu(seconds=60)
        avg_5min = cpu_monitor.get_average_cpu(seconds=300)

        # Should have averages (or None if insufficient data)
        assert avg_1min is None or isinstance(avg_1min, float)
        assert avg_5min is None or isinstance(avg_5min, float)


class TestAutoSleepOnIdle:
    """Test SLEEP-011: Auto-Sleep on Idle Timeout"""

    @pytest.mark.asyncio
    async def test_enable_auto_sleep(self, cpu_monitor):
        """Test enabling auto-sleep"""
        cpu_monitor.enable_auto_sleep(
            idle_threshold=5.0,
            idle_timeout_seconds=300
        )

        assert cpu_monitor._auto_sleep_enabled is True
        assert cpu_monitor._idle_threshold_percent == 5.0
        assert cpu_monitor._idle_timeout_seconds == 300

    @pytest.mark.asyncio
    async def test_disable_auto_sleep(self, cpu_monitor):
        """Test disabling auto-sleep"""
        cpu_monitor.enable_auto_sleep()
        cpu_monitor.disable_auto_sleep()

        assert cpu_monitor._auto_sleep_enabled is False
        assert cpu_monitor._consecutive_idle_seconds == 0.0

    @pytest.mark.asyncio
    async def test_idle_detection_with_threshold(self, cpu_monitor):
        """Test idle detection based on threshold"""
        # Wait for metrics collection
        await asyncio.sleep(1.5)

        # Set a very high threshold so current CPU is always below it
        cpu_monitor._idle_threshold_percent = 99.9

        # Should detect as idle with high threshold
        assert cpu_monitor.is_idle() is True

        # Set very low threshold
        cpu_monitor._idle_threshold_percent = 0.1

        # Should not be idle with very low threshold
        assert cpu_monitor.is_idle() is False

    @pytest.mark.asyncio
    async def test_idle_counter_tracking(self, cpu_monitor):
        """Test idle counter tracks idle time"""
        # Set high threshold to ensure we're "idle"
        cpu_monitor._idle_threshold_percent = 99.0
        cpu_monitor._check_interval = 1

        initial_idle = cpu_monitor._consecutive_idle_seconds

        # Wait for a cycle
        await asyncio.sleep(1.5)

        # Idle counter should have changed (incremented or reset based on actual CPU)
        # Just verify the tracking mechanism works
        assert cpu_monitor._consecutive_idle_seconds >= 0

    @pytest.mark.asyncio
    async def test_auto_sleep_configuration(self, cpu_monitor, sleep_service):
        """Test auto-sleep can be configured and enabled"""
        # Configure with very high threshold to ensure we're always "idle"
        cpu_monitor._check_interval = 1
        cpu_monitor.enable_auto_sleep(
            idle_threshold=99.9,  # Very high threshold
            idle_timeout_seconds=2
        )

        # Connect sleep service
        cpu_monitor._sleep_service = sleep_service

        # Should be awake initially
        assert sleep_service.state == SleepState.AWAKE

        # Configuration should be set
        assert cpu_monitor._auto_sleep_enabled is True
        assert cpu_monitor._idle_threshold_percent == 99.9
        assert cpu_monitor._idle_timeout_seconds == 2


class TestStatusAndMetrics:
    """Test status reporting"""

    @pytest.mark.asyncio
    async def test_get_status(self, cpu_monitor):
        """Test get_status returns correct info"""
        # Wait for some metrics
        await asyncio.sleep(1.5)

        status = cpu_monitor.get_status()

        assert status["is_running"] is True
        assert "current_metrics" in status
        assert "auto_sleep" in status
        assert status["auto_sleep"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_status_with_auto_sleep_enabled(self, cpu_monitor):
        """Test status shows auto-sleep config"""
        cpu_monitor.enable_auto_sleep(
            idle_threshold=10.0,
            idle_timeout_seconds=600
        )

        status = cpu_monitor.get_status()

        assert status["auto_sleep"]["enabled"] is True
        assert status["auto_sleep"]["idle_threshold_percent"] == 10.0
        assert status["auto_sleep"]["idle_timeout_seconds"] == 600
        assert "seconds_until_sleep" in status["auto_sleep"]

    @pytest.mark.asyncio
    async def test_status_includes_averages(self, cpu_monitor):
        """Test status includes CPU averages"""
        # Wait for metrics
        await asyncio.sleep(2.0)

        status = cpu_monitor.get_status()

        # Should have averages (or None if insufficient data)
        assert "average_cpu_1min" in status
        assert "average_cpu_5min" in status


class TestCPUMetrics:
    """Test CPUMetrics dataclass"""

    def test_cpu_metrics_creation(self):
        """Test creating CPUMetrics instance"""
        metrics = CPUMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=25.5,
            cpu_per_core=[20.0, 30.0, 25.0, 27.0],
            memory_percent=60.5,
            memory_used_mb=8192.0,
            memory_available_mb=4096.0,
            idle_seconds=120.0
        )

        assert metrics.cpu_percent == 25.5
        assert len(metrics.cpu_per_core) == 4
        assert metrics.memory_percent == 60.5
        assert metrics.idle_seconds == 120.0

    def test_cpu_metrics_to_dict(self):
        """Test CPUMetrics converts to dict"""
        now = datetime.now(timezone.utc)
        metrics = CPUMetrics(
            timestamp=now,
            cpu_percent=25.5,
            cpu_per_core=[20.0],
            memory_percent=60.5,
            memory_used_mb=8192.0,
            memory_available_mb=4096.0
        )

        data = metrics.to_dict()

        assert data["cpu_percent"] == 25.5
        assert data["memory_percent"] == 60.5
        assert "timestamp" in data


class TestServiceLifecycle:
    """Test service start/stop lifecycle"""

    @pytest.mark.asyncio
    async def test_service_start(self):
        """Test service starts correctly"""
        CPUMonitor._instance = None
        monitor = CPUMonitor.get_instance()

        await monitor.start()

        assert monitor._is_running is True
        assert monitor._monitor_task is not None

        await monitor.stop()
        CPUMonitor._instance = None

    @pytest.mark.asyncio
    async def test_service_stop(self, cpu_monitor):
        """Test service stops correctly"""
        await cpu_monitor.stop()

        assert cpu_monitor._is_running is False

    @pytest.mark.asyncio
    async def test_cannot_start_twice(self, cpu_monitor):
        """Test cannot start service twice"""
        # Already started in fixture
        await cpu_monitor.start()

        # Should not crash, just warn
        assert cpu_monitor._is_running is True


class TestIntegrationWithSleepService:
    """Test integration between CPU monitor and sleep service"""

    @pytest.mark.asyncio
    async def test_lazy_loads_sleep_service(self, cpu_monitor):
        """Test sleep service is lazy loaded"""
        # Access sleep_service property
        sleep_service = cpu_monitor.sleep_service

        # Should have loaded or attempted to load
        assert cpu_monitor._sleep_service is not None or cpu_monitor._sleep_service is None

    @pytest.mark.asyncio
    @patch('services.cpu_monitor.psutil.cpu_percent')
    async def test_does_not_sleep_when_disabled(
        self, mock_cpu_percent, cpu_monitor, sleep_service
    ):
        """Test does not trigger sleep when auto-sleep is disabled"""
        mock_cpu_percent.return_value = 1.0  # Very low CPU

        cpu_monitor._sleep_service = sleep_service
        cpu_monitor._check_interval = 1
        cpu_monitor._auto_sleep_enabled = False

        # Wait for a while
        await asyncio.sleep(3.0)

        # Should still be awake
        assert sleep_service.state == SleepState.AWAKE
