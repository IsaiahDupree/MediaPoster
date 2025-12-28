"""
Backend Health Monitor
======================
Monitors backend health, prevents silent failures, and provides detailed logging.

Features:
- Service health checks
- Database connection monitoring
- Job queue status
- Memory/CPU monitoring
- Detailed error aggregation
- Health reports
"""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
from loguru import logger
import traceback


@dataclass
class HealthCheck:
    """Result of a health check"""
    name: str
    status: str  # healthy, degraded, unhealthy
    message: str
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """Record of an error occurrence"""
    timestamp: datetime
    error_type: str
    message: str
    traceback: str
    endpoint: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class BackendHealthMonitor:
    """
    Central health monitoring for the backend.
    Tracks errors, service health, and provides reports.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.start_time = datetime.now()
        self.error_history: deque = deque(maxlen=1000)  # Keep last 1000 errors
        self.health_checks: Dict[str, HealthCheck] = {}
        self.request_count = 0
        self.error_count = 0
        self.slow_request_count = 0
        self._lock = asyncio.Lock()
        
        logger.info("🏥 Backend Health Monitor initialized")
    
    def record_error(
        self,
        error: Exception,
        endpoint: Optional[str] = None,
        context: Optional[Dict] = None
    ):
        """Record an error for tracking"""
        record = ErrorRecord(
            timestamp=datetime.now(),
            error_type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc(),
            endpoint=endpoint,
            context=context or {}
        )
        self.error_history.append(record)
        self.error_count += 1
        
        # Log with severity based on error type
        if "Database" in type(error).__name__ or "Connection" in type(error).__name__:
            logger.critical(f"🔴 DATABASE ERROR: {error}")
        elif "Timeout" in type(error).__name__:
            logger.error(f"⏱️ TIMEOUT ERROR: {error}")
        else:
            logger.error(f"❌ ERROR [{endpoint or 'unknown'}]: {type(error).__name__}: {error}")
    
    def record_request(self, duration_seconds: float, endpoint: str):
        """Record a request for metrics"""
        self.request_count += 1
        if duration_seconds > 5.0:
            self.slow_request_count += 1
            logger.warning(f"🐢 SLOW REQUEST: {endpoint} took {duration_seconds:.2f}s")
    
    async def check_database(self) -> HealthCheck:
        """Check database connectivity"""
        start = time.time()
        try:
            from database.connection import get_db
            from sqlalchemy import text
            
            # Get a fresh session
            async for db in get_db():
                result = await db.execute(text("SELECT 1"))
                result.fetchone()
                break
            
            latency = (time.time() - start) * 1000
            return HealthCheck(
                name="database",
                status="healthy" if latency < 100 else "degraded",
                message="Database connected",
                latency_ms=latency
            )
        except Exception as e:
            return HealthCheck(
                name="database",
                status="unhealthy",
                message=f"Database error: {e}",
                latency_ms=(time.time() - start) * 1000
            )
    
    async def check_external_drive(self) -> HealthCheck:
        """Check if external drive is connected"""
        start = time.time()
        try:
            from config.paths import is_external_drive_connected, get_iphone_import_dir
            
            connected = is_external_drive_connected()
            path = get_iphone_import_dir()
            
            return HealthCheck(
                name="external_drive",
                status="healthy" if connected else "degraded",
                message=f"Drive {'connected' if connected else 'not connected'}: {path}",
                latency_ms=(time.time() - start) * 1000,
                details={"connected": connected, "path": str(path)}
            )
        except Exception as e:
            return HealthCheck(
                name="external_drive",
                status="unhealthy",
                message=f"Drive check error: {e}",
                latency_ms=(time.time() - start) * 1000
            )
    
    def check_memory(self) -> HealthCheck:
        """Check system memory usage"""
        start = time.time()
        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            status = "healthy"
            if memory.percent > 90:
                status = "unhealthy"
            elif memory.percent > 75:
                status = "degraded"
            
            return HealthCheck(
                name="memory",
                status=status,
                message=f"System: {memory.percent:.1f}%, Process: {process_memory.rss / 1024 / 1024:.1f}MB",
                latency_ms=(time.time() - start) * 1000,
                details={
                    "system_percent": memory.percent,
                    "process_mb": process_memory.rss / 1024 / 1024,
                    "available_gb": memory.available / 1024 / 1024 / 1024
                }
            )
        except Exception as e:
            return HealthCheck(
                name="memory",
                status="unknown",
                message=f"Memory check error: {e}",
                latency_ms=(time.time() - start) * 1000
            )
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive report"""
        checks = []
        
        # Database check
        db_check = await self.check_database()
        checks.append(db_check)
        
        # External drive check
        drive_check = await self.check_external_drive()
        checks.append(drive_check)
        
        # Memory check
        memory_check = self.check_memory()
        checks.append(memory_check)
        
        # Store results
        for check in checks:
            self.health_checks[check.name] = check
        
        # Calculate overall status
        statuses = [c.status for c in checks]
        if "unhealthy" in statuses:
            overall = "unhealthy"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"
        
        uptime = datetime.now() - self.start_time
        error_rate = (self.error_count / max(self.request_count, 1)) * 100
        
        return {
            "status": overall,
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime).split('.')[0],
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate_percent": round(error_rate, 2),
            "slow_request_count": self.slow_request_count,
            "checks": {c.name: {
                "status": c.status,
                "message": c.message,
                "latency_ms": round(c.latency_ms, 2)
            } for c in checks},
            "recent_errors": self.get_recent_errors(limit=5),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """Get most recent errors"""
        errors = list(self.error_history)[-limit:]
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "type": e.error_type,
                "message": e.message[:200],
                "endpoint": e.endpoint
            }
            for e in reversed(errors)
        ]
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_errors = [e for e in self.error_history if e.timestamp > cutoff]
        
        # Group by error type
        by_type = {}
        for e in recent_errors:
            by_type[e.error_type] = by_type.get(e.error_type, 0) + 1
        
        # Group by endpoint
        by_endpoint = {}
        for e in recent_errors:
            if e.endpoint:
                by_endpoint[e.endpoint] = by_endpoint.get(e.endpoint, 0) + 1
        
        return {
            "period_hours": hours,
            "total_errors": len(recent_errors),
            "by_type": by_type,
            "by_endpoint": by_endpoint,
            "timestamp": datetime.now().isoformat()
        }


# Singleton instance
_monitor: Optional[BackendHealthMonitor] = None


def get_health_monitor() -> BackendHealthMonitor:
    """Get the singleton health monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = BackendHealthMonitor()
    return _monitor


# Decorator for wrapping async functions with error tracking
def track_errors(endpoint_name: str = None):
    """Decorator to track errors in async functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            monitor = get_health_monitor()
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                monitor.record_request(time.time() - start, endpoint_name or func.__name__)
                return result
            except Exception as e:
                monitor.record_error(e, endpoint_name or func.__name__)
                raise
        return wrapper
    return decorator
