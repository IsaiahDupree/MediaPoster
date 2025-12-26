"""
Error Tracking Middleware

Provides centralized error tracking, logging, and monitoring for the FastAPI application.
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import traceback
import time
import uuid
from typing import Callable
import json


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks all errors, logs them with context, and optionally
    sends them to external services (Sentry, Slack, etc.)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Add request ID to state for tracing
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            
            # Log slow requests (> 5 seconds)
            duration = time.time() - start_time
            if duration > 5:
                logger.warning(
                    f"[{request_id}] Slow request: {request.method} {request.url.path} "
                    f"took {duration:.2f}s"
                )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log the full exception with context
            logger.exception(
                f"[{request_id}] Unhandled exception on {request.method} {request.url.path}\n"
                f"Duration: {duration:.2f}s\n"
                f"Client: {request.client.host if request.client else 'unknown'}\n"
                f"Error: {type(e).__name__}: {str(e)}"
            )
            
            # Return a proper error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "message": str(e) if logger.level("DEBUG").no <= logger._core.min_level else "An error occurred"
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests for debugging and monitoring.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health checks and static files
        skip_paths = ["/health", "/favicon.ico", "/static"]
        if any(request.url.path.startswith(p) for p in skip_paths):
            return await call_next(request)
        
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Log request
        logger.debug(
            f"[{request_id}] → {request.method} {request.url.path}"
        )
        
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log response
        log_level = "warning" if response.status_code >= 400 else "debug"
        getattr(logger, log_level)(
            f"[{request_id}] ← {response.status_code} {request.method} {request.url.path} "
            f"({duration:.3f}s)"
        )
        
        return response


def safe_json_loads(data: str, default=None, context: str = ""):
    """
    Safely parse JSON with error logging.
    
    Args:
        data: JSON string to parse
        default: Default value if parsing fails
        context: Description of what's being parsed for logging
    
    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.warning(
            f"JSON parse error{f' ({context})' if context else ''}: {e}\n"
            f"Data preview: {data[:200]}..."
        )
        return default
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}")
        return default


def log_exception(e: Exception, context: str = "", extra: dict = None):
    """
    Log an exception with full context.
    
    Args:
        e: The exception to log
        context: Description of what was happening
        extra: Additional context data
    """
    extra_str = ""
    if extra:
        extra_str = "\n".join(f"  {k}: {v}" for k, v in extra.items())
        extra_str = f"\nExtra context:\n{extra_str}"
    
    logger.exception(
        f"Exception{f' in {context}' if context else ''}: "
        f"{type(e).__name__}: {str(e)}{extra_str}"
    )
