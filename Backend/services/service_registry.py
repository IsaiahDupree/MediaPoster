"""
Service Registry (MOD-001)
===========================
Central registry for all services, workers, and background tasks.

This module provides:
- Service registration and discovery
- Health check aggregation
- Service lifecycle management
- Dependency resolution

Usage:
    >>> from services.service_registry import get_service_registry, ServiceType
    >>>
    >>> registry = get_service_registry()
    >>>
    >>> # Register a service
    >>> registry.register(
    ...     name="post_scheduler",
    ...     service_type=ServiceType.WORKER,
    ...     instance=scheduler,
    ...     health_check=lambda: scheduler.is_running
    ... )
    >>>
    >>> # Get service status
    >>> status = registry.get_service_status("post_scheduler")
    >>>
    >>> # Get all services
    >>> services = registry.get_all_services()
"""

from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from loguru import logger
import asyncio


class ServiceType(Enum):
    """Types of services in the system."""
    WORKER = "worker"           # Background workers (PostScheduler, MetricsFetchWorker, etc.)
    API = "api"                 # API endpoints
    EXTERNAL = "external"       # External services (OpenAI, Blotato, etc.)
    DATABASE = "database"       # Database connections
    EVENT_BUS = "event_bus"     # Event bus and pub/sub
    STORAGE = "storage"         # Storage services


class ServiceStatus(Enum):
    """Service health statuses."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"
    STARTING = "starting"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    """Information about a registered service."""
    name: str
    service_type: ServiceType
    instance: Any
    health_check: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_health_check: Optional[datetime] = None
    last_status: ServiceStatus = ServiceStatus.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "service_type": self.service_type.value,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "registered_at": self.registered_at.isoformat(),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "last_status": self.last_status.value,
        }


class ServiceRegistry:
    """
    Service Registry - Central registry for all services.

    Implements MOD-001: Service Registry feature.
    Provides service registration, discovery, and health aggregation.
    """

    _instance: Optional["ServiceRegistry"] = None

    def __init__(self):
        """Initialize service registry."""
        if ServiceRegistry._instance is not None:
            raise RuntimeError("Use ServiceRegistry.get_instance()")

        self._services: Dict[str, ServiceInfo] = {}
        self._health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_running = False

        logger.info("📋 Service Registry initialized")

    @classmethod
    def get_instance(cls) -> "ServiceRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
        self,
        name: str,
        service_type: ServiceType,
        instance: Any,
        health_check: Optional[Callable] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a service.

        Args:
            name: Service identifier (e.g., "post_scheduler")
            service_type: Type of service
            instance: Service instance
            health_check: Optional health check function
            dependencies: Optional list of service names this depends on
            metadata: Optional metadata

        Example:
            >>> registry.register(
            ...     name="post_scheduler",
            ...     service_type=ServiceType.WORKER,
            ...     instance=scheduler,
            ...     health_check=lambda: scheduler.is_running,
            ...     dependencies=["database", "event_bus"]
            ... )
        """
        service_info = ServiceInfo(
            name=name,
            service_type=service_type,
            instance=instance,
            health_check=health_check,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )

        self._services[name] = service_info
        logger.info(f"✓ Registered service: {name} ({service_type.value})")

    def unregister(self, name: str) -> bool:
        """
        Unregister a service.

        Args:
            name: Service identifier

        Returns:
            True if unregistered, False if not found
        """
        if name in self._services:
            del self._services[name]
            logger.info(f"✓ Unregistered service: {name}")
            return True
        return False

    def get_service(self, name: str) -> Optional[Any]:
        """
        Get service instance by name.

        Args:
            name: Service identifier

        Returns:
            Service instance or None if not found
        """
        service_info = self._services.get(name)
        return service_info.instance if service_info else None

    def get_service_info(self, name: str) -> Optional[ServiceInfo]:
        """
        Get service info by name.

        Args:
            name: Service identifier

        Returns:
            ServiceInfo or None if not found
        """
        return self._services.get(name)

    async def check_service_health(self, name: str) -> ServiceStatus:
        """
        Check health of a specific service.

        Args:
            name: Service identifier

        Returns:
            ServiceStatus enum value
        """
        service_info = self._services.get(name)
        if not service_info:
            return ServiceStatus.UNKNOWN

        if not service_info.health_check:
            return ServiceStatus.UNKNOWN

        try:
            # Call health check (can be sync or async)
            result = service_info.health_check()
            if asyncio.iscoroutine(result):
                result = await result

            # Interpret result
            if isinstance(result, bool):
                status = ServiceStatus.HEALTHY if result else ServiceStatus.UNHEALTHY
            elif isinstance(result, dict):
                status_str = result.get("status", "unknown")
                status = ServiceStatus(status_str) if status_str in ServiceStatus._value2member_map_ else ServiceStatus.UNKNOWN
            else:
                status = ServiceStatus.UNKNOWN

            service_info.last_status = status
            service_info.last_health_check = datetime.now(timezone.utc)

            return status

        except Exception as e:
            logger.error(f"Health check failed for {name}: {e}")
            service_info.last_status = ServiceStatus.UNHEALTHY
            service_info.last_health_check = datetime.now(timezone.utc)
            return ServiceStatus.UNHEALTHY

    async def check_all_health(self) -> Dict[str, ServiceStatus]:
        """
        Check health of all services.

        Returns:
            Dictionary mapping service names to their statuses
        """
        results = {}

        for name in self._services:
            status = await self.check_service_health(name)
            results[name] = status

        return results

    def get_service_status(self, name: str) -> Dict[str, Any]:
        """
        Get detailed status of a service.

        Args:
            name: Service identifier

        Returns:
            Dictionary with service status details
        """
        service_info = self._services.get(name)
        if not service_info:
            return {"error": "Service not found"}

        return {
            "name": name,
            "service_type": service_info.service_type.value,
            "status": service_info.last_status.value,
            "last_health_check": service_info.last_health_check.isoformat() if service_info.last_health_check else None,
            "registered_at": service_info.registered_at.isoformat(),
            "dependencies": service_info.dependencies,
            "metadata": service_info.metadata
        }

    def get_all_services(self) -> List[Dict[str, Any]]:
        """
        Get all registered services.

        Returns:
            List of service status dictionaries
        """
        return [self.get_service_status(name) for name in self._services]

    def get_services_by_type(self, service_type: ServiceType) -> List[str]:
        """
        Get all services of a specific type.

        Args:
            service_type: Service type to filter by

        Returns:
            List of service names
        """
        return [
            name for name, info in self._services.items()
            if info.service_type == service_type
        ]

    async def start_health_monitoring(self) -> None:
        """Start periodic health check monitoring."""
        if self._is_running:
            logger.warning("Health monitoring already running")
            return

        self._is_running = True
        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        logger.info("✓ Service Registry health monitoring started")

    async def stop_health_monitoring(self) -> None:
        """Stop periodic health check monitoring."""
        self._is_running = False

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        logger.info("✓ Service Registry health monitoring stopped")

    async def _health_monitor_loop(self) -> None:
        """Background loop for periodic health checks."""
        while self._is_running:
            try:
                await self.check_all_health()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(self._health_check_interval)

    def get_dependency_tree(self, name: str) -> Dict[str, Any]:
        """
        Get dependency tree for a service.

        Args:
            name: Service identifier

        Returns:
            Dependency tree dictionary
        """
        service_info = self._services.get(name)
        if not service_info:
            return {}

        tree = {
            "name": name,
            "dependencies": []
        }

        for dep_name in service_info.dependencies:
            dep_tree = self.get_dependency_tree(dep_name)
            if dep_tree:
                tree["dependencies"].append(dep_tree)

        return tree

    def validate_dependencies(self) -> Dict[str, List[str]]:
        """
        Validate all service dependencies.

        Returns:
            Dictionary mapping service names to lists of missing dependencies
        """
        missing = {}

        for name, info in self._services.items():
            missing_deps = [
                dep for dep in info.dependencies
                if dep not in self._services
            ]
            if missing_deps:
                missing[name] = missing_deps

        return missing


# Global singleton instance
_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get or create the global service registry instance."""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry.get_instance()
    return _registry


__all__ = [
    "ServiceRegistry",
    "ServiceType",
    "ServiceStatus",
    "ServiceInfo",
    "get_service_registry",
]
