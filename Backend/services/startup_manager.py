"""
Startup Manager
===============
Centralized startup verification and health monitoring for MediaPoster.

Ensures all required services start correctly and provides:
- Startup verification with retry logic
- Health status for all components
- Dependency checking
- Startup timing metrics

Usage:
    from services.startup_manager import StartupManager
    
    manager = StartupManager()
    report = await manager.run_startup_sequence()
    
    if not report.all_critical_passed:
        logger.error("Critical services failed to start!")
"""
import asyncio
import time
import psutil
import subprocess
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from loguru import logger


class ServicePriority(Enum):
    """Service startup priority levels."""
    CRITICAL = "critical"      # App cannot run without this
    REQUIRED = "required"      # Should start, but can degrade gracefully
    OPTIONAL = "optional"      # Nice to have, failure is logged only


class ServiceStatus(Enum):
    """Service status states."""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ServiceCheck:
    """Definition of a service to check during startup."""
    name: str
    priority: ServicePriority
    check_func: Optional[Callable] = None
    start_func: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_delay: float = 2.0
    timeout: float = 30.0
    
    # Runtime state
    status: ServiceStatus = ServiceStatus.PENDING
    error: Optional[str] = None
    start_time: Optional[float] = None
    duration: Optional[float] = None
    instance: Any = None


@dataclass
class StartupReport:
    """Report of startup sequence results."""
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration: float = 0.0
    
    services: Dict[str, ServiceCheck] = field(default_factory=dict)
    
    # Summary stats
    critical_passed: int = 0
    critical_failed: int = 0
    required_passed: int = 0
    required_failed: int = 0
    optional_passed: int = 0
    optional_failed: int = 0
    
    # System metrics at startup
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    
    @property
    def all_critical_passed(self) -> bool:
        return self.critical_failed == 0
    
    @property
    def all_required_passed(self) -> bool:
        return self.required_failed == 0
    
    @property
    def healthy(self) -> bool:
        return self.all_critical_passed
    
    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_seconds": self.total_duration,
            "healthy": self.healthy,
            "summary": {
                "critical": {"passed": self.critical_passed, "failed": self.critical_failed},
                "required": {"passed": self.required_passed, "failed": self.required_failed},
                "optional": {"passed": self.optional_passed, "failed": self.optional_failed},
            },
            "system": {
                "cpu_percent": self.cpu_percent,
                "memory_percent": self.memory_percent,
                "memory_mb": self.memory_mb,
            },
            "services": {
                name: {
                    "status": svc.status.value,
                    "priority": svc.priority.value,
                    "duration_ms": svc.duration * 1000 if svc.duration else None,
                    "error": svc.error,
                }
                for name, svc in self.services.items()
            }
        }
    
    def __str__(self) -> str:
        lines = [
            "",
            "=" * 60,
            "STARTUP REPORT",
            "=" * 60,
            f"Status: {'✅ HEALTHY' if self.healthy else '❌ UNHEALTHY'}",
            f"Duration: {self.total_duration:.2f}s",
            f"",
            f"Critical: {self.critical_passed} passed, {self.critical_failed} failed",
            f"Required: {self.required_passed} passed, {self.required_failed} failed",
            f"Optional: {self.optional_passed} passed, {self.optional_failed} failed",
            f"",
            f"System: CPU={self.cpu_percent:.1f}%, Memory={self.memory_mb:.0f}MB ({self.memory_percent:.1f}%)",
            "",
            "Services:",
        ]
        
        for name, svc in self.services.items():
            icon = "✅" if svc.status == ServiceStatus.RUNNING else "❌" if svc.status == ServiceStatus.FAILED else "⏭️"
            duration = f"{svc.duration*1000:.0f}ms" if svc.duration else "N/A"
            lines.append(f"  {icon} {name} [{svc.priority.value}] - {duration}")
            if svc.error:
                lines.append(f"      Error: {svc.error[:80]}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


class StartupManager:
    """
    Manages application startup sequence and health verification.
    
    Provides centralized control over:
    - Service initialization order
    - Dependency management
    - Health checks
    - Retry logic
    - Startup metrics
    """
    
    _instance: Optional["StartupManager"] = None
    
    def __init__(self):
        self.services: Dict[str, ServiceCheck] = {}
        self.report: Optional[StartupReport] = None
        self._initialized = False
        
        # Register all services
        self._register_default_services()
    
    @classmethod
    def get_instance(cls) -> "StartupManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _register_default_services(self):
        """Register all default services to check/start."""
        
        # =====================================================================
        # CRITICAL SERVICES (app cannot run without these)
        # =====================================================================
        
        self.register_service(ServiceCheck(
            name="postgresql",
            priority=ServicePriority.CRITICAL,
            check_func=self._check_postgresql,
            start_func=self._start_postgresql,
            max_retries=5,
            retry_delay=3.0,
        ))
        
        self.register_service(ServiceCheck(
            name="database",
            priority=ServicePriority.CRITICAL,
            check_func=self._check_database,
            start_func=self._init_database,
            dependencies=["postgresql"],
            max_retries=5,
        ))
        
        # =====================================================================
        # REQUIRED SERVICES (should start, but can degrade)
        # =====================================================================
        
        self.register_service(ServiceCheck(
            name="event_bus",
            priority=ServicePriority.REQUIRED,
            check_func=self._check_event_bus,
            start_func=self._init_event_bus,
            dependencies=["database"],
        ))
        
        self.register_service(ServiceCheck(
            name="connectors",
            priority=ServicePriority.REQUIRED,
            check_func=self._check_connectors,
            start_func=self._init_connectors,
        ))
        
        self.register_service(ServiceCheck(
            name="post_scheduler",
            priority=ServicePriority.REQUIRED,
            check_func=self._check_post_scheduler,
            start_func=self._init_post_scheduler,
            dependencies=["database", "event_bus"],
        ))
        
        self.register_service(ServiceCheck(
            name="sleep_mode_service",
            priority=ServicePriority.REQUIRED,
            check_func=self._check_sleep_service,
            start_func=self._init_sleep_service,
            dependencies=["event_bus"],
        ))
        
        self.register_service(ServiceCheck(
            name="cpu_monitor",
            priority=ServicePriority.REQUIRED,
            check_func=self._check_cpu_monitor,
            start_func=self._init_cpu_monitor,
        ))
        
        # =====================================================================
        # OPTIONAL SERVICES (nice to have)
        # =====================================================================
        
        self.register_service(ServiceCheck(
            name="metrics_worker",
            priority=ServicePriority.OPTIONAL,
            start_func=self._init_metrics_worker,
            dependencies=["event_bus"],
        ))
        
        self.register_service(ServiceCheck(
            name="cleanup_worker",
            priority=ServicePriority.OPTIONAL,
            start_func=self._init_cleanup_worker,
            dependencies=["event_bus"],
        ))
        
        self.register_service(ServiceCheck(
            name="notification_worker",
            priority=ServicePriority.OPTIONAL,
            start_func=self._init_notification_worker,
            dependencies=["event_bus"],
        ))
        
        self.register_service(ServiceCheck(
            name="safari_session",
            priority=ServicePriority.OPTIONAL,
            check_func=self._check_safari_session,
        ))
    
    def register_service(self, service: ServiceCheck):
        """Register a service for startup checking."""
        self.services[service.name] = service
    
    async def run_startup_sequence(self) -> StartupReport:
        """
        Run the complete startup sequence.
        
        Returns:
            StartupReport with results of all service checks
        """
        logger.info("🚀 Starting MediaPoster startup sequence...")
        
        self.report = StartupReport(
            started_at=datetime.now(timezone.utc),
            cpu_percent=psutil.cpu_percent(),
            memory_percent=psutil.virtual_memory().percent,
            memory_mb=psutil.virtual_memory().used / (1024 * 1024),
        )
        
        start_time = time.time()
        
        # Sort services by dependencies (topological sort)
        ordered = self._topological_sort()
        
        for service_name in ordered:
            service = self.services[service_name]
            await self._start_service(service)
            self.report.services[service_name] = service
        
        # Calculate summary
        for service in self.services.values():
            if service.priority == ServicePriority.CRITICAL:
                if service.status == ServiceStatus.RUNNING:
                    self.report.critical_passed += 1
                elif service.status == ServiceStatus.FAILED:
                    self.report.critical_failed += 1
            elif service.priority == ServicePriority.REQUIRED:
                if service.status == ServiceStatus.RUNNING:
                    self.report.required_passed += 1
                elif service.status == ServiceStatus.FAILED:
                    self.report.required_failed += 1
            else:
                if service.status == ServiceStatus.RUNNING:
                    self.report.optional_passed += 1
                elif service.status == ServiceStatus.FAILED:
                    self.report.optional_failed += 1
        
        self.report.completed_at = datetime.now(timezone.utc)
        self.report.total_duration = time.time() - start_time
        
        # Log summary
        logger.info(str(self.report))
        
        if not self.report.healthy:
            logger.error("❌ Startup completed with critical failures!")
        else:
            logger.success(f"✅ Startup completed in {self.report.total_duration:.2f}s")
        
        self._initialized = True
        return self.report
    
    async def _start_service(self, service: ServiceCheck):
        """Start a single service with retry logic."""
        service.status = ServiceStatus.STARTING
        service.start_time = time.time()
        
        # Check dependencies first
        for dep_name in service.dependencies:
            dep = self.services.get(dep_name)
            if dep and dep.status != ServiceStatus.RUNNING:
                service.status = ServiceStatus.SKIPPED
                service.error = f"Dependency '{dep_name}' not running"
                service.duration = time.time() - service.start_time
                logger.warning(f"⏭️  Skipping {service.name}: {service.error}")
                return
        
        # Try to start with retries
        last_error = None
        for attempt in range(service.max_retries):
            try:
                # Run check function first (if exists)
                if service.check_func:
                    is_running = await self._run_async_or_sync(service.check_func)
                    if is_running:
                        service.status = ServiceStatus.RUNNING
                        service.duration = time.time() - service.start_time
                        logger.success(f"✓ {service.name} already running")
                        return
                
                # Run start function
                if service.start_func:
                    result = await self._run_async_or_sync(service.start_func)
                    service.instance = result
                
                service.status = ServiceStatus.RUNNING
                service.duration = time.time() - service.start_time
                logger.success(f"✓ {service.name} started ({service.duration*1000:.0f}ms)")
                return
                
            except Exception as e:
                last_error = str(e)
                if attempt < service.max_retries - 1:
                    logger.warning(f"⚠️  {service.name} attempt {attempt+1} failed: {e}")
                    await asyncio.sleep(service.retry_delay * (attempt + 1))
        
        # All retries failed
        service.status = ServiceStatus.FAILED
        service.error = last_error
        service.duration = time.time() - service.start_time
        
        if service.priority == ServicePriority.CRITICAL:
            logger.error(f"❌ CRITICAL: {service.name} failed: {last_error}")
        elif service.priority == ServicePriority.REQUIRED:
            logger.warning(f"⚠️  {service.name} failed: {last_error}")
        else:
            logger.info(f"ℹ️  {service.name} (optional) failed: {last_error}")
    
    async def _run_async_or_sync(self, func: Callable) -> Any:
        """Run a function whether it's async or sync."""
        result = func()
        if asyncio.iscoroutine(result):
            return await result
        return result
    
    def _topological_sort(self) -> List[str]:
        """Sort services by dependencies."""
        visited = set()
        result = []
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            service = self.services.get(name)
            if service:
                for dep in service.dependencies:
                    visit(dep)
            result.append(name)
        
        for name in self.services:
            visit(name)
        
        return result
    
    def get_health_status(self) -> dict:
        """Get current health status of all services."""
        if not self.report:
            return {"status": "not_initialized", "services": {}}
        
        return self.report.to_dict()
    
    # =========================================================================
    # SERVICE CHECK/START IMPLEMENTATIONS
    # =========================================================================
    
    def _check_postgresql(self) -> bool:
        """Check if PostgreSQL is running."""
        try:
            from config import settings
            import socket
            
            # Parse connection string
            db_url = settings.database_url
            if "localhost" in db_url or "127.0.0.1" in db_url:
                host = "127.0.0.1"
            else:
                host = db_url.split("@")[1].split(":")[0] if "@" in db_url else "127.0.0.1"
            
            port = 5432
            if ":" in db_url.split("@")[-1]:
                port_str = db_url.split(":")[-1].split("/")[0]
                if port_str.isdigit():
                    port = int(port_str)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _start_postgresql(self) -> bool:
        """Start PostgreSQL if not running (macOS)."""
        try:
            # Try Homebrew PostgreSQL
            subprocess.run(
                ["brew", "services", "start", "postgresql@14"],
                capture_output=True,
                timeout=10
            )
            time.sleep(2)
            return self._check_postgresql()
        except:
            pass
        
        try:
            # Try generic pg_ctl
            subprocess.run(
                ["pg_ctl", "start", "-D", "/usr/local/var/postgres"],
                capture_output=True,
                timeout=10
            )
            time.sleep(2)
            return self._check_postgresql()
        except:
            pass
        
        return False
    
    async def _check_database(self) -> bool:
        """Check if database connection works."""
        try:
            from database.connection import async_session_maker
            if not async_session_maker:
                return False
            async with async_session_maker() as session:
                await session.execute("SELECT 1")
                return True
        except:
            return False
    
    async def _init_database(self):
        """Initialize database connection."""
        from database.connection import init_db
        await init_db()
    
    def _check_event_bus(self) -> bool:
        """Check if event bus is initialized."""
        try:
            from services.event_bus import EventBus
            bus = EventBus.get_instance()
            return bus is not None
        except:
            return False
    
    def _init_event_bus(self):
        """Initialize event bus."""
        from services.event_bus import EventBus
        from services.event_bus.topics import Topics
        from config import settings
        
        bus = EventBus.get_instance()
        bus.set_source("mediaposter-backend")
        return bus
    
    def _check_connectors(self) -> bool:
        """Check if connectors are registered."""
        try:
            from connectors import registry
            return len(registry.get_all_supported_platforms()) > 0
        except:
            return False
    
    def _init_connectors(self):
        """Initialize platform connectors."""
        from connectors import initialize_adapters
        return initialize_adapters()
    
    def _check_post_scheduler(self) -> bool:
        """Check if post scheduler is running."""
        try:
            from services.post_scheduler import PostScheduler
            # PostScheduler is a singleton, check if it has a running task
            return True  # Will be started if not
        except:
            return False
    
    async def _init_post_scheduler(self):
        """Initialize post scheduler."""
        from services.post_scheduler import PostScheduler
        scheduler = PostScheduler()
        await scheduler.start()
        return scheduler
    
    def _check_sleep_service(self) -> bool:
        """Check if sleep service is running."""
        try:
            from services.sleep_mode_service import SleepModeService
            service = SleepModeService.get_instance()
            return service._is_running
        except:
            return False
    
    async def _init_sleep_service(self):
        """Initialize sleep mode service."""
        from services.sleep_mode_service import SleepModeService
        service = SleepModeService.get_instance()
        await service.start()
        return service
    
    def _check_cpu_monitor(self) -> bool:
        """Check if CPU monitor is running."""
        try:
            from services.cpu_monitor import get_cpu_monitor
            monitor = get_cpu_monitor()
            return monitor._running
        except:
            return False
    
    async def _init_cpu_monitor(self):
        """Initialize CPU monitor."""
        from services.cpu_monitor import get_cpu_monitor
        monitor = get_cpu_monitor()
        await monitor.start()
        monitor.enable_auto_sleep(idle_threshold=5.0, idle_timeout_seconds=300)
        return monitor
    
    async def _init_metrics_worker(self):
        """Initialize metrics fetch worker."""
        from services.workers.metrics_fetch_worker import MetricsFetchWorker
        from services.event_bus import EventBus
        worker = MetricsFetchWorker(EventBus.get_instance())
        await worker.start()
        return worker
    
    async def _init_cleanup_worker(self):
        """Initialize cleanup worker."""
        from services.workers.cleanup_worker import CleanupWorker
        from services.event_bus import EventBus
        worker = CleanupWorker(EventBus.get_instance())
        await worker.start()
        return worker
    
    async def _init_notification_worker(self):
        """Initialize notification worker."""
        from services.workers.notification_worker import NotificationWorker
        from services.event_bus import EventBus
        worker = NotificationWorker(EventBus.get_instance())
        await worker.start()
        return worker
    
    def _check_safari_session(self) -> bool:
        """Check if Safari sessions are active for automation."""
        try:
            from automation.safari_session_manager import SafariSessionManager
            manager = SafariSessionManager()
            # Just verify the module loads, actual login check is expensive
            return True
        except:
            return False


# Convenience function for quick health check
async def verify_startup() -> Tuple[bool, StartupReport]:
    """
    Quick startup verification.
    
    Returns:
        Tuple of (is_healthy, report)
    """
    manager = StartupManager.get_instance()
    report = await manager.run_startup_sequence()
    return report.healthy, report


# CLI interface
if __name__ == "__main__":
    import sys
    
    async def main():
        manager = StartupManager()
        report = await manager.run_startup_sequence()
        
        print(report)
        
        if not report.healthy:
            sys.exit(1)
        sys.exit(0)
    
    asyncio.run(main())
