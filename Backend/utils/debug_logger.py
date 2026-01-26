"""
Debug Logger for Backend Services

Provides structured console logging with trace IDs for debugging backend operations.
Part of Phase 14 E2E Testing Framework (E2E-002)
"""

import logging
import json
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any, Callable
from functools import wraps


class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    TEST = "TEST"


class DebugLogger:
    """
    Debug logger with structured output and trace IDs.

    Usage:
        logger = DebugLogger("ServiceName", trace_id="optional-trace-id")
        logger.info("Action performed", {"key": "value"})
        logger.debug("Debug info", {"status": "processing"})
        logger.error("Error occurred", error, {"context": "value"})
    """

    def __init__(self, component: str, trace_id: Optional[str] = None):
        """
        Initialize debug logger.

        Args:
            component: Component/service name
            trace_id: Optional trace ID for correlation
        """
        self.component = component
        self.trace_id = trace_id or f"trace_{int(time.time())}_{uuid.uuid4().hex[:9]}"
        self.logger = logging.getLogger(component)

    def log(self, level: LogLevel, action: str, data: Optional[dict] = None) -> dict:
        """
        Log an entry with structured format.

        Args:
            level: Log level
            action: Action being performed
            data: Optional data payload

        Returns:
            Log entry dictionary
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.value,
            "trace_id": self.trace_id,
            "component": self.component,
            "action": action,
            "data": data
        }

        emoji = {
            "DEBUG": "🔍",
            "INFO": "ℹ️",
            "WARN": "⚠️",
            "ERROR": "❌",
            "TEST": "🧪"
        }[level.value]

        message = f"{emoji} [{entry['timestamp']}] [{self.trace_id}] [{self.component}] {action}"
        if data:
            message += f" | {json.dumps(data)}"

        print(message)
        return entry

    def debug(self, action: str, data: Optional[dict] = None) -> dict:
        """Log debug message"""
        return self.log(LogLevel.DEBUG, action, data)

    def info(self, action: str, data: Optional[dict] = None) -> dict:
        """Log info message"""
        return self.log(LogLevel.INFO, action, data)

    def warn(self, action: str, data: Optional[dict] = None) -> dict:
        """Log warning message"""
        return self.log(LogLevel.WARN, action, data)

    def error(self, action: str, error: Exception, data: Optional[dict] = None) -> dict:
        """Log error message"""
        error_data = {
            **(data or {}),
            "error": str(error),
            "error_type": type(error).__name__
        }
        return self.log(LogLevel.ERROR, action, error_data)

    def test(self, action: str, data: Optional[dict] = None) -> dict:
        """Log test message"""
        return self.log(LogLevel.TEST, action, data)


def timed(logger: DebugLogger, action: str) -> Callable:
    """
    Decorator for timing function execution.

    Args:
        logger: DebugLogger instance
        action: Action description

    Returns:
        Decorator function

    Usage:
        @timed(logger, "Process data")
        async def process_data():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.debug(f"{action} - START")
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                logger.debug(f"{action} - END", {"duration_ms": round(duration, 2)})
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                logger.error(f"{action} - FAILED", e, {"duration_ms": round(duration, 2)})
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.debug(f"{action} - START")
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                logger.debug(f"{action} - END", {"duration_ms": round(duration, 2)})
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                logger.error(f"{action} - FAILED", e, {"duration_ms": round(duration, 2)})
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
