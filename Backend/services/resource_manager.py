"""
Resource Manager Service (BM-005)
==================================
Unified CPU/Memory/GPU monitoring with thresholds, throttling, and alerts
for the automation system.

Features:
- Real-time CPU and memory monitoring via psutil
- Optional GPU monitoring (graceful degradation if GPUtil unavailable)
- Throttle level calculation based on resource usage
- Background monitoring loop with configurable interval
- Event-driven alerts via EventBus when thresholds are crossed
- Integration with Sleep Mode Service for critical resource states
- Historical snapshot storage for trend analysis

Throttle Levels:
- NONE:     CPU < 50%  -- full speed
- LIGHT:    CPU 50-70% -- reduce batch sizes
- MEDIUM:   CPU 70-85% -- pause non-essential workers
- HEAVY:    CPU 85-95% -- pause all but critical work
- CRITICAL: CPU > 95%  -- suggest sleep mode

Memory > 90% bumps throttle level up by one tier.

Usage:
    from services.resource_manager import ResourceManager

    manager = ResourceManager.get_instance()
    await manager.start_monitoring(interval=10)

    snapshot = manager.get_snapshot()
    if manager.should_throttle():
        # Reduce workload
        ...
    if manager.should_pause():
        # Enter sleep mode
        ...
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Deque, Dict, List, Optional

import psutil

# Optional GPU monitoring -- graceful degradation if not available
_GPU_AVAILABLE = False
try:
    import GPUtil  # type: ignore[import-untyped]
    _GPU_AVAILABLE = True
except ImportError:
    GPUtil = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Throttle level enum
# ---------------------------------------------------------------------------

class ThrottleLevel(IntEnum):
    """
    Resource throttle levels.

    Integer values allow comparison (e.g. ``level >= ThrottleLevel.MEDIUM``)
    and arithmetic (bump by +1).
    """
    NONE = 0
    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3
    CRITICAL = 4


# ---------------------------------------------------------------------------
# Resource snapshot dataclass
# ---------------------------------------------------------------------------

@dataclass
class ResourceSnapshot:
    """Point-in-time snapshot of system resource usage."""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    gpu_percent: Optional[float] = None
    gpu_memory_percent: Optional[float] = None
    throttle_level: ThrottleLevel = ThrottleLevel.NONE
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_available_mb": self.memory_available_mb,
            "gpu_percent": self.gpu_percent,
            "gpu_memory_percent": self.gpu_memory_percent,
            "throttle_level": self.throttle_level.name,
            "throttle_level_value": int(self.throttle_level),
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Resource Manager (singleton)
# ---------------------------------------------------------------------------

class ResourceManager:
    """
    Singleton service providing unified resource monitoring.

    Tracks CPU, memory, and (optionally) GPU utilization, computes a
    throttle level, and emits EventBus events when thresholds change.

    Singleton Pattern:
        Use ``ResourceManager.get_instance()``
    """

    _instance: Optional["ResourceManager"] = None

    # -- CPU threshold boundaries for throttle levels -----------------------
    CPU_THRESHOLD_LIGHT = 50.0
    CPU_THRESHOLD_MEDIUM = 70.0
    CPU_THRESHOLD_HEAVY = 85.0
    CPU_THRESHOLD_CRITICAL = 95.0

    # -- Memory threshold that bumps throttle level -------------------------
    MEMORY_BUMP_THRESHOLD = 90.0

    # -- Duration (seconds) of sustained CRITICAL before suggesting sleep ---
    CRITICAL_SLEEP_SUGGEST_SECONDS = 30.0

    # -- Maximum number of snapshots retained in history --------------------
    MAX_HISTORY = 1000

    # -- Default monitoring interval (seconds) ------------------------------
    DEFAULT_INTERVAL = 10

    def __init__(self) -> None:
        if ResourceManager._instance is not None:
            raise RuntimeError("Use ResourceManager.get_instance()")

        # EventBus integration (lazy to avoid circular imports)
        self._event_bus: Optional[Any] = None

        # Current / previous throttle level
        self._current_throttle: ThrottleLevel = ThrottleLevel.NONE

        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task[None]] = None
        self._is_monitoring = False
        self._interval: float = self.DEFAULT_INTERVAL

        # Snapshot history (bounded deque)
        self._history: Deque[ResourceSnapshot] = deque(maxlen=self.MAX_HISTORY)

        # Track how long we have been at CRITICAL level
        self._critical_since: Optional[float] = None  # monotonic timestamp
        self._sleep_suggested = False

        logger.info("ResourceManager initialized (GPU available: %s)", _GPU_AVAILABLE)

    # ------------------------------------------------------------------
    # Singleton helpers
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ResourceManager":
        """Return the singleton instance, creating it on first call."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton -- intended for testing only."""
        if cls._instance is not None:
            # Stop monitoring if running
            cls._instance._is_monitoring = False
            if cls._instance._monitoring_task and not cls._instance._monitoring_task.done():
                cls._instance._monitoring_task.cancel()
        cls._instance = None

    # ------------------------------------------------------------------
    # EventBus accessor (lazy)
    # ------------------------------------------------------------------

    @property
    def event_bus(self) -> Any:
        """Lazy-load EventBus to avoid circular import issues."""
        if self._event_bus is None:
            try:
                from services.event_bus import EventBus
                self._event_bus = EventBus.get_instance()
            except Exception as exc:
                logger.warning("EventBus not available: %s", exc)
        return self._event_bus

    # ------------------------------------------------------------------
    # Throttle level calculation
    # ------------------------------------------------------------------

    @staticmethod
    def _cpu_to_throttle(cpu_percent: float) -> ThrottleLevel:
        """Map CPU percentage to a base throttle level."""
        if cpu_percent >= ResourceManager.CPU_THRESHOLD_CRITICAL:
            return ThrottleLevel.CRITICAL
        if cpu_percent >= ResourceManager.CPU_THRESHOLD_HEAVY:
            return ThrottleLevel.HEAVY
        if cpu_percent >= ResourceManager.CPU_THRESHOLD_MEDIUM:
            return ThrottleLevel.MEDIUM
        if cpu_percent >= ResourceManager.CPU_THRESHOLD_LIGHT:
            return ThrottleLevel.LIGHT
        return ThrottleLevel.NONE

    @staticmethod
    def compute_throttle_level(
        cpu_percent: float,
        memory_percent: float,
    ) -> ThrottleLevel:
        """
        Compute the effective throttle level from CPU and memory usage.

        Memory > 90% bumps the throttle level up by one tier (capped at
        CRITICAL).
        """
        level = ResourceManager._cpu_to_throttle(cpu_percent)

        # Memory bump
        if memory_percent > ResourceManager.MEMORY_BUMP_THRESHOLD:
            level = ThrottleLevel(min(int(level) + 1, int(ThrottleLevel.CRITICAL)))

        return level

    # ------------------------------------------------------------------
    # Snapshot collection
    # ------------------------------------------------------------------

    def _read_gpu(self) -> tuple[Optional[float], Optional[float]]:
        """Read GPU utilization.  Returns (gpu_percent, gpu_memory_percent)."""
        if not _GPU_AVAILABLE or GPUtil is None:
            return None, None
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return None, None
            # Use first GPU
            gpu = gpus[0]
            return gpu.load * 100.0, gpu.memoryUtil * 100.0
        except Exception as exc:
            logger.debug("GPU read failed: %s", exc)
            return None, None

    def get_snapshot(self) -> ResourceSnapshot:
        """
        Collect a *fresh* resource snapshot (non-blocking, synchronous).

        Returns a ``ResourceSnapshot`` reflecting current system state.
        """
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        mem_pct = mem.percent
        mem_avail_mb = mem.available / (1024 * 1024)

        gpu_pct, gpu_mem_pct = self._read_gpu()

        throttle = self.compute_throttle_level(cpu_pct, mem_pct)

        snap = ResourceSnapshot(
            cpu_percent=cpu_pct,
            memory_percent=mem_pct,
            memory_available_mb=round(mem_avail_mb, 1),
            gpu_percent=gpu_pct,
            gpu_memory_percent=gpu_mem_pct,
            throttle_level=throttle,
        )
        return snap

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def get_throttle_level(self) -> ThrottleLevel:
        """Return the current throttle level (from the latest snapshot)."""
        return self._current_throttle

    def should_throttle(self) -> bool:
        """Return ``True`` if current throttle level is MEDIUM or above."""
        return self._current_throttle >= ThrottleLevel.MEDIUM

    def should_pause(self) -> bool:
        """Return ``True`` if current throttle level is CRITICAL."""
        return self._current_throttle >= ThrottleLevel.CRITICAL

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, minutes: int = 5) -> List[ResourceSnapshot]:
        """
        Return snapshots from the last *minutes* minutes.

        Args:
            minutes: Look-back window in minutes (default 5).

        Returns:
            List of ``ResourceSnapshot`` objects, oldest first.
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (minutes * 60)
        return [
            snap for snap in self._history
            if snap.timestamp.timestamp() >= cutoff
        ]

    # ------------------------------------------------------------------
    # Monitoring loop
    # ------------------------------------------------------------------

    async def start_monitoring(self, interval: float = DEFAULT_INTERVAL) -> None:
        """
        Start the background monitoring loop.

        Args:
            interval: Seconds between each snapshot (default 10).
        """
        if self._is_monitoring:
            logger.warning("ResourceManager monitoring already running")
            return

        self._interval = interval
        self._is_monitoring = True

        # Prime psutil CPU counter (first call always returns 0.0)
        psutil.cpu_percent(interval=None)

        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info(
            "ResourceManager monitoring started (interval=%ss)", interval
        )

    async def stop_monitoring(self) -> None:
        """Stop the background monitoring loop."""
        if not self._is_monitoring:
            return

        self._is_monitoring = False
        if self._monitoring_task is not None:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

        logger.info("ResourceManager monitoring stopped")

    async def _monitor_loop(self) -> None:
        """Internal loop: collect snapshot, update state, emit events."""
        try:
            while self._is_monitoring:
                snapshot = self.get_snapshot()
                self._history.append(snapshot)

                old_level = self._current_throttle
                new_level = snapshot.throttle_level
                self._current_throttle = new_level

                # -- Throttle-level change event ----------------------------
                if new_level != old_level:
                    await self._emit_throttle_changed(old_level, new_level)

                # -- Alert for HEAVY / CRITICAL -----------------------------
                if new_level >= ThrottleLevel.HEAVY:
                    await self._emit_alert(snapshot)

                # -- Critical-duration tracking for sleep suggestion --------
                await self._check_critical_duration(new_level)

                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("ResourceManager monitor loop error: %s", exc, exc_info=True)

    # ------------------------------------------------------------------
    # Event emission helpers
    # ------------------------------------------------------------------

    async def _emit_throttle_changed(
        self, old: ThrottleLevel, new: ThrottleLevel
    ) -> None:
        """Publish ``resource.throttle_changed`` via EventBus."""
        bus = self.event_bus
        if bus is None:
            return
        try:
            await bus.publish(
                "resource.throttle_changed",
                {
                    "old_level": old.name,
                    "old_level_value": int(old),
                    "new_level": new.name,
                    "new_level_value": int(new),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            logger.info(
                "Throttle level changed: %s -> %s", old.name, new.name
            )
        except Exception as exc:
            logger.warning("Failed to emit throttle_changed event: %s", exc)

    async def _emit_alert(self, snapshot: ResourceSnapshot) -> None:
        """Publish ``resource.alert`` for HEAVY/CRITICAL states."""
        bus = self.event_bus
        if bus is None:
            return
        try:
            await bus.publish(
                "resource.alert",
                {
                    "throttle_level": snapshot.throttle_level.name,
                    "cpu_percent": snapshot.cpu_percent,
                    "memory_percent": snapshot.memory_percent,
                    "gpu_percent": snapshot.gpu_percent,
                    "timestamp": snapshot.timestamp.isoformat(),
                },
            )
        except Exception as exc:
            logger.warning("Failed to emit resource.alert event: %s", exc)

    async def _check_critical_duration(self, level: ThrottleLevel) -> None:
        """
        When CRITICAL for > 30 seconds continuously, suggest entering
        sleep mode via EventBus.
        """
        now_mono = time.monotonic()

        if level >= ThrottleLevel.CRITICAL:
            if self._critical_since is None:
                self._critical_since = now_mono
                self._sleep_suggested = False

            elapsed = now_mono - self._critical_since
            if elapsed >= self.CRITICAL_SLEEP_SUGGEST_SECONDS and not self._sleep_suggested:
                self._sleep_suggested = True
                logger.warning(
                    "CRITICAL resource usage sustained for %.1fs -- "
                    "suggesting sleep mode",
                    elapsed,
                )
                bus = self.event_bus
                if bus is not None:
                    try:
                        await bus.publish(
                            "resource.sleep_suggested",
                            {
                                "reason": "sustained_critical",
                                "critical_duration_seconds": round(elapsed, 1),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                    except Exception as exc:
                        logger.warning(
                            "Failed to emit sleep_suggested event: %s", exc
                        )
        else:
            # Reset critical tracking when we drop below CRITICAL
            self._critical_since = None
            self._sleep_suggested = False

    # ------------------------------------------------------------------
    # Status / introspection
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary suitable for health-check endpoints."""
        latest = self._history[-1].to_dict() if self._history else None
        return {
            "is_monitoring": self._is_monitoring,
            "interval_seconds": self._interval,
            "current_throttle_level": self._current_throttle.name,
            "current_throttle_value": int(self._current_throttle),
            "gpu_available": _GPU_AVAILABLE,
            "history_size": len(self._history),
            "latest_snapshot": latest,
        }
