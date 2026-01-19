"""
CPU Monitor Service
===================
Monitors CPU usage and triggers auto-sleep when idle for extended periods.

SLEEP-010: CPU Usage Monitoring
SLEEP-011: Auto-Sleep on Idle Timeout

The service:
1. Monitors system CPU usage
2. Tracks idle periods
3. Automatically enters sleep mode when idle threshold is met
4. Reports CPU metrics via API
"""

import asyncio
import psutil
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from loguru import logger
from dataclasses import dataclass, field


@dataclass
class CPUMetrics:
    """CPU usage metrics"""
    timestamp: datetime
    cpu_percent: float
    cpu_per_core: list[float]
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    idle_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "cpu_per_core": self.cpu_per_core,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "idle_seconds": self.idle_seconds
        }


class CPUMonitor:
    """
    CPU Monitor Service

    Monitors CPU usage and triggers auto-sleep when idle.

    Usage:
        monitor = CPUMonitor.get_instance()
        await monitor.start()

        # Configure auto-sleep
        monitor.enable_auto_sleep(
            idle_threshold=5.0,  # CPU below 5%
            idle_timeout_seconds=300  # Idle for 5 minutes
        )
    """

    _instance: Optional["CPUMonitor"] = None

    def __init__(self):
        """Initialize CPU monitor"""
        if CPUMonitor._instance is not None:
            raise RuntimeError("Use CPUMonitor.get_instance()")

        self._is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._check_interval = 5  # Check CPU every 5 seconds

        # CPU metrics
        self._current_metrics: Optional[CPUMetrics] = None
        self._metrics_history: list[CPUMetrics] = []
        self._max_history_size = 100  # Keep last 100 readings (8-9 minutes)

        # Auto-sleep configuration (SLEEP-011)
        self._auto_sleep_enabled = False
        self._idle_threshold_percent = 5.0  # CPU below 5% is considered idle
        self._idle_timeout_seconds = 300  # 5 minutes of idle triggers sleep
        self._last_active_time: Optional[datetime] = None
        self._consecutive_idle_seconds = 0.0

        # Sleep service integration
        self._sleep_service = None

        logger.info("💻 CPU Monitor initialized")

    @classmethod
    def get_instance(cls) -> "CPUMonitor":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def sleep_service(self):
        """Lazy load sleep mode service"""
        if self._sleep_service is None:
            try:
                from services.sleep_mode_service import SleepModeService
                self._sleep_service = SleepModeService.get_instance()
            except Exception as e:
                logger.warning(f"Sleep mode service not available: {e}")
                self._sleep_service = None
        return self._sleep_service

    async def start(self) -> None:
        """Start CPU monitoring"""
        if self._is_running:
            logger.warning("CPU monitor already running")
            return

        self._is_running = True
        self._last_active_time = datetime.now(timezone.utc)
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.success("✓ CPU Monitor started")

    async def stop(self) -> None:
        """Stop CPU monitoring"""
        self._is_running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 CPU Monitor stopped")

    def enable_auto_sleep(
        self,
        idle_threshold: float = 5.0,
        idle_timeout_seconds: int = 300
    ) -> None:
        """
        Enable auto-sleep on idle (SLEEP-011)

        Args:
            idle_threshold: CPU percentage below which system is considered idle (default: 5%)
            idle_timeout_seconds: Seconds of idle time before triggering sleep (default: 300)
        """
        self._auto_sleep_enabled = True
        self._idle_threshold_percent = idle_threshold
        self._idle_timeout_seconds = idle_timeout_seconds

        logger.info(
            f"✓ Auto-sleep enabled | Threshold: {idle_threshold}% CPU | "
            f"Timeout: {idle_timeout_seconds}s idle"
        )

    def disable_auto_sleep(self) -> None:
        """Disable auto-sleep on idle"""
        self._auto_sleep_enabled = False
        self._consecutive_idle_seconds = 0.0
        logger.info("Auto-sleep disabled")

    def get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current CPU metrics"""
        if self._current_metrics:
            return self._current_metrics.to_dict()
        return None

    def get_metrics_history(self, limit: int = 50) -> list[Dict[str, Any]]:
        """
        Get recent CPU metrics history

        Args:
            limit: Maximum number of metrics to return (default: 50)

        Returns:
            List of metrics dictionaries, most recent first
        """
        return [m.to_dict() for m in reversed(self._metrics_history[-limit:])]

    def get_average_cpu(self, seconds: int = 60) -> Optional[float]:
        """
        Get average CPU usage over the last N seconds

        Args:
            seconds: Time window in seconds (default: 60)

        Returns:
            Average CPU percentage or None if insufficient data
        """
        if not self._metrics_history:
            return None

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=seconds)

        recent_metrics = [
            m for m in self._metrics_history
            if m.timestamp >= cutoff
        ]

        if not recent_metrics:
            return None

        return sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)

    def is_idle(self) -> bool:
        """Check if system is currently idle"""
        if not self._current_metrics:
            return False

        return self._current_metrics.cpu_percent < self._idle_threshold_percent

    def get_status(self) -> Dict[str, Any]:
        """
        Get CPU monitor status

        Returns:
            Status dictionary with metrics and auto-sleep config
        """
        current = self.get_current_metrics()
        avg_1min = self.get_average_cpu(60)
        avg_5min = self.get_average_cpu(300)

        return {
            "is_running": self._is_running,
            "check_interval": self._check_interval,
            "current_metrics": current,
            "average_cpu_1min": avg_1min,
            "average_cpu_5min": avg_5min,
            "is_idle": self.is_idle(),
            "auto_sleep": {
                "enabled": self._auto_sleep_enabled,
                "idle_threshold_percent": self._idle_threshold_percent,
                "idle_timeout_seconds": self._idle_timeout_seconds,
                "consecutive_idle_seconds": self._consecutive_idle_seconds,
                "seconds_until_sleep": max(
                    0,
                    self._idle_timeout_seconds - self._consecutive_idle_seconds
                ) if self._auto_sleep_enabled else None
            },
            "metrics_history_size": len(self._metrics_history)
        }

    async def _monitor_loop(self) -> None:
        """Background loop to monitor CPU usage"""
        logger.info("🔍 CPU monitor loop started")

        while self._is_running:
            try:
                # Collect CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_per_core = psutil.cpu_percent(interval=0, percpu=True)
                memory = psutil.virtual_memory()

                now = datetime.now(timezone.utc)

                metrics = CPUMetrics(
                    timestamp=now,
                    cpu_percent=cpu_percent,
                    cpu_per_core=cpu_per_core,
                    memory_percent=memory.percent,
                    memory_used_mb=memory.used / (1024 * 1024),
                    memory_available_mb=memory.available / (1024 * 1024),
                    idle_seconds=self._consecutive_idle_seconds
                )

                # Update current metrics
                self._current_metrics = metrics

                # Add to history
                self._metrics_history.append(metrics)
                if len(self._metrics_history) > self._max_history_size:
                    self._metrics_history.pop(0)

                # Check if system is idle (SLEEP-010)
                if cpu_percent < self._idle_threshold_percent:
                    # System is idle
                    self._consecutive_idle_seconds += self._check_interval

                    logger.debug(
                        f"💤 System idle | CPU: {cpu_percent:.1f}% | "
                        f"Idle: {self._consecutive_idle_seconds:.0f}s"
                    )
                else:
                    # System is active
                    if self._consecutive_idle_seconds > 0:
                        logger.debug(
                            f"💡 System active | CPU: {cpu_percent:.1f}% | "
                            f"Was idle: {self._consecutive_idle_seconds:.0f}s"
                        )

                    self._consecutive_idle_seconds = 0.0
                    self._last_active_time = now

                # Auto-sleep check (SLEEP-011)
                if (
                    self._auto_sleep_enabled and
                    self._consecutive_idle_seconds >= self._idle_timeout_seconds and
                    self.sleep_service and
                    not self.sleep_service.is_sleeping()
                ):
                    logger.info(
                        f"💤 Auto-sleep triggered | CPU idle for "
                        f"{self._consecutive_idle_seconds:.0f}s (threshold: {self._idle_timeout_seconds}s)"
                    )

                    await self.sleep_service.enter_sleep(grace_period_seconds=2.0)

                    # Reset idle counter
                    self._consecutive_idle_seconds = 0.0

                # Wait for next check
                await asyncio.sleep(self._check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in CPU monitor loop: {e}")
                await asyncio.sleep(self._check_interval)

        logger.info("🛑 CPU monitor loop stopped")


# Singleton accessor
def get_cpu_monitor() -> CPUMonitor:
    """Get the singleton CPU monitor instance"""
    return CPUMonitor.get_instance()
