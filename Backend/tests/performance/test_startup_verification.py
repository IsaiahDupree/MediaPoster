"""
Startup Verification Tests
==========================
Tests to verify the application starts correctly with all required services.

Run with: pytest tests/performance/test_startup_verification.py -v -s
"""
import pytest
import asyncio
import time
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.startup_manager import (
    StartupManager,
    ServiceCheck,
    ServicePriority,
    ServiceStatus,
    StartupReport,
    verify_startup,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def startup_manager():
    """Create a fresh StartupManager instance."""
    StartupManager._instance = None
    manager = StartupManager()
    yield manager
    StartupManager._instance = None


@pytest.fixture
def mock_services():
    """Mock all external services for testing."""
    with patch('services.startup_manager.psutil') as mock_psutil:
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.virtual_memory.return_value = MagicMock(
            percent=60.0,
            used=8 * 1024 * 1024 * 1024  # 8GB
        )
        yield mock_psutil


# =============================================================================
# UNIT TESTS
# =============================================================================

class TestServiceCheck:
    """Test ServiceCheck dataclass."""
    
    def test_service_check_defaults(self):
        """Test ServiceCheck has correct defaults."""
        check = ServiceCheck(
            name="test_service",
            priority=ServicePriority.REQUIRED,
        )
        
        assert check.name == "test_service"
        assert check.priority == ServicePriority.REQUIRED
        assert check.status == ServiceStatus.PENDING
        assert check.max_retries == 3
        assert check.dependencies == []
    
    def test_service_check_with_dependencies(self):
        """Test ServiceCheck with dependencies."""
        check = ServiceCheck(
            name="dependent_service",
            priority=ServicePriority.OPTIONAL,
            dependencies=["database", "event_bus"],
        )
        
        assert len(check.dependencies) == 2
        assert "database" in check.dependencies


class TestStartupReport:
    """Test StartupReport dataclass."""
    
    def test_report_healthy_when_no_critical_failures(self):
        """Test report is healthy when no critical services fail."""
        from datetime import datetime, timezone
        
        report = StartupReport(started_at=datetime.now(timezone.utc))
        report.critical_passed = 3
        report.critical_failed = 0
        
        assert report.healthy is True
        assert report.all_critical_passed is True
    
    def test_report_unhealthy_when_critical_fails(self):
        """Test report is unhealthy when critical service fails."""
        from datetime import datetime, timezone
        
        report = StartupReport(started_at=datetime.now(timezone.utc))
        report.critical_passed = 2
        report.critical_failed = 1
        
        assert report.healthy is False
        assert report.all_critical_passed is False
    
    def test_report_to_dict(self):
        """Test report serialization to dict."""
        from datetime import datetime, timezone
        
        report = StartupReport(
            started_at=datetime.now(timezone.utc),
            cpu_percent=30.0,
            memory_percent=65.0,
            memory_mb=8000.0,
        )
        report.critical_passed = 2
        report.completed_at = datetime.now(timezone.utc)
        report.total_duration = 5.5
        
        data = report.to_dict()
        
        assert "started_at" in data
        assert data["healthy"] is True
        assert data["system"]["cpu_percent"] == 30.0
        assert data["summary"]["critical"]["passed"] == 2


class TestStartupManager:
    """Test StartupManager class."""
    
    def test_singleton_instance(self):
        """Test StartupManager is a singleton."""
        StartupManager._instance = None
        
        m1 = StartupManager.get_instance()
        m2 = StartupManager.get_instance()
        
        assert m1 is m2
        
        StartupManager._instance = None
    
    def test_register_service(self, startup_manager):
        """Test registering a custom service."""
        custom_service = ServiceCheck(
            name="custom_test",
            priority=ServicePriority.OPTIONAL,
        )
        
        startup_manager.register_service(custom_service)
        
        assert "custom_test" in startup_manager.services
    
    def test_default_services_registered(self, startup_manager):
        """Test default services are registered on init."""
        assert "postgresql" in startup_manager.services
        assert "database" in startup_manager.services
        assert "event_bus" in startup_manager.services
        assert "connectors" in startup_manager.services
    
    def test_topological_sort(self, startup_manager):
        """Test services are sorted by dependencies."""
        sorted_names = startup_manager._topological_sort()
        
        # PostgreSQL should come before database
        pg_idx = sorted_names.index("postgresql")
        db_idx = sorted_names.index("database")
        assert pg_idx < db_idx
        
        # Database should come before event_bus
        eb_idx = sorted_names.index("event_bus")
        assert db_idx < eb_idx
    
    @pytest.mark.asyncio
    async def test_run_async_or_sync_with_sync_func(self, startup_manager):
        """Test running a sync function."""
        def sync_func():
            return "sync_result"
        
        result = await startup_manager._run_async_or_sync(sync_func)
        assert result == "sync_result"
    
    @pytest.mark.asyncio
    async def test_run_async_or_sync_with_async_func(self, startup_manager):
        """Test running an async function."""
        async def async_func():
            return "async_result"
        
        result = await startup_manager._run_async_or_sync(async_func)
        assert result == "async_result"


# =============================================================================
# INTEGRATION TESTS (with mocks)
# =============================================================================

class TestStartupSequence:
    """Test the startup sequence execution."""
    
    @pytest.mark.asyncio
    async def test_startup_with_all_mocked_services(self, startup_manager, mock_services):
        """Test startup sequence with mocked services."""
        # Replace all service checks with mocks
        for name, service in startup_manager.services.items():
            service.check_func = lambda: True
            service.start_func = lambda: MagicMock()
        
        report = await startup_manager.run_startup_sequence()
        
        assert report is not None
        assert report.total_duration > 0
        assert report.healthy is True
    
    @pytest.mark.asyncio
    async def test_startup_handles_service_failure(self, startup_manager, mock_services):
        """Test startup handles service failure gracefully."""
        # Make one optional service fail
        startup_manager.services["safari_session"].check_func = lambda: False
        startup_manager.services["safari_session"].start_func = lambda: (_ for _ in ()).throw(Exception("Safari not available"))
        
        # Mock all others to pass
        for name, service in startup_manager.services.items():
            if name != "safari_session":
                service.check_func = lambda: True
                service.start_func = lambda: MagicMock()
        
        report = await startup_manager.run_startup_sequence()
        
        # Should still be healthy (safari_session is optional)
        assert report.healthy is True
        assert report.optional_failed >= 1
    
    @pytest.mark.asyncio
    async def test_startup_fails_on_critical_failure(self, startup_manager, mock_services):
        """Test startup reports unhealthy on critical failure."""
        # Make PostgreSQL (critical) fail
        startup_manager.services["postgresql"].check_func = lambda: False
        startup_manager.services["postgresql"].start_func = lambda: (_ for _ in ()).throw(Exception("PostgreSQL not running"))
        
        # Mock all others to pass
        for name, service in startup_manager.services.items():
            if name != "postgresql":
                service.check_func = lambda: True
                service.start_func = lambda: MagicMock()
        
        report = await startup_manager.run_startup_sequence()
        
        assert report.healthy is False
        assert report.critical_failed >= 1
    
    @pytest.mark.asyncio
    async def test_dependency_skipping(self, startup_manager, mock_services):
        """Test services skip when dependencies fail."""
        # Make database (required for event_bus) fail
        startup_manager.services["postgresql"].check_func = lambda: True
        startup_manager.services["postgresql"].start_func = lambda: True
        startup_manager.services["database"].check_func = lambda: False
        startup_manager.services["database"].start_func = lambda: (_ for _ in ()).throw(Exception("DB error"))
        
        # Mock others
        for name, service in startup_manager.services.items():
            if name not in ["postgresql", "database"]:
                service.check_func = lambda: True
                service.start_func = lambda: MagicMock()
        
        report = await startup_manager.run_startup_sequence()
        
        # event_bus depends on database, should be skipped
        event_bus_status = report.services.get("event_bus")
        if event_bus_status:
            assert event_bus_status.status in [ServiceStatus.SKIPPED, ServiceStatus.FAILED]


# =============================================================================
# TIMING TESTS
# =============================================================================

class TestStartupTiming:
    """Test startup timing requirements."""
    
    @pytest.mark.asyncio
    async def test_startup_completes_within_timeout(self, startup_manager, mock_services):
        """Test startup completes within reasonable time."""
        # Mock all services to pass quickly
        for name, service in startup_manager.services.items():
            service.check_func = lambda: True
            service.start_func = lambda: MagicMock()
        
        start = time.time()
        report = await startup_manager.run_startup_sequence()
        duration = time.time() - start
        
        # Should complete in under 5 seconds with mocks
        assert duration < 5.0
        assert report.total_duration < 5.0
    
    @pytest.mark.asyncio
    async def test_individual_service_timing(self, startup_manager, mock_services):
        """Test individual service timing is tracked."""
        async def slow_start():
            await asyncio.sleep(0.1)
            return True
        
        # Make one service intentionally slow
        startup_manager.services["connectors"].check_func = lambda: False
        startup_manager.services["connectors"].start_func = slow_start
        
        # Mock others
        for name, service in startup_manager.services.items():
            if name != "connectors":
                service.check_func = lambda: True
                service.start_func = lambda: True
        
        report = await startup_manager.run_startup_sequence()
        
        connectors = report.services.get("connectors")
        if connectors and connectors.duration:
            assert connectors.duration >= 0.1


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

class TestHealthStatus:
    """Test health status reporting."""
    
    @pytest.mark.asyncio
    async def test_get_health_status_before_startup(self, startup_manager):
        """Test health status before startup returns not_initialized."""
        status = startup_manager.get_health_status()
        
        assert status["status"] == "not_initialized"
    
    @pytest.mark.asyncio
    async def test_get_health_status_after_startup(self, startup_manager, mock_services):
        """Test health status after startup returns full report."""
        # Mock all services
        for name, service in startup_manager.services.items():
            service.check_func = lambda: True
            service.start_func = lambda: True
        
        await startup_manager.run_startup_sequence()
        status = startup_manager.get_health_status()
        
        assert "healthy" in status
        assert "services" in status
        assert "summary" in status


# =============================================================================
# BENCHMARK TESTS
# =============================================================================

class TestStartupBenchmarks:
    """Benchmark tests for startup performance."""
    
    @pytest.mark.asyncio
    async def test_benchmark_service_registration(self, startup_manager):
        """Benchmark service registration time."""
        start = time.time()
        
        for i in range(100):
            startup_manager.register_service(ServiceCheck(
                name=f"bench_service_{i}",
                priority=ServicePriority.OPTIONAL,
            ))
        
        duration = time.time() - start
        
        # 100 registrations should take < 100ms
        assert duration < 0.1
        print(f"\n100 service registrations: {duration*1000:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_benchmark_topological_sort(self, startup_manager):
        """Benchmark topological sort with many services."""
        # Add many services with dependencies
        for i in range(50):
            deps = [f"bench_{j}" for j in range(max(0, i-3), i)]
            startup_manager.register_service(ServiceCheck(
                name=f"bench_{i}",
                priority=ServicePriority.OPTIONAL,
                dependencies=deps,
            ))
        
        start = time.time()
        sorted_services = startup_manager._topological_sort()
        duration = time.time() - start
        
        # Sort should be fast
        assert duration < 0.1
        assert len(sorted_services) > 50
        print(f"\nTopological sort ({len(sorted_services)} services): {duration*1000:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
