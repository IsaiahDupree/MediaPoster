"""
Rate Limiting Middleware

Provides rate limiting for API endpoints to prevent abuse.
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
from loguru import logger


class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    For production, consider using Redis-based rate limiting.
    """
    def __init__(self):
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier (e.g., IP address, user ID)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        async with self._lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=window_seconds)
            
            # Clean old requests
            self._requests[key] = [
                req_time for req_time in self._requests[key]
                if req_time > window_start
            ]
            
            # Check limit
            request_count = len(self._requests[key])
            
            if request_count >= max_requests:
                return False, 0
            
            # Add current request
            self._requests[key].append(now)
            
            return True, max_requests - request_count - 1


# Global rate limiter instance
_rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    
    Configurable limits per endpoint pattern.
    """
    
    def __init__(self, app, default_limit: int = 100, default_window: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        
        # Configure rate limits per endpoint pattern
        self.limits = {
            # Expensive operations - stricter limits
            "/api/media-db/analyze": (10, 60),  # 10 per minute
            "/api/media-db/batch/analyze": (5, 60),  # 5 per minute
            "/api/media-db/ingest": (20, 60),  # 20 per minute
            "/api/media-db/batch/ingest": (3, 60),  # 3 per minute
            "/api/schedule": (500, 60),  # 500 per minute (increased for batch scheduling)
            "/api/publishing": (100, 60),  # 100 per minute
            "/api/narrative-builder": (200, 60),  # 200 per minute
            
            # Default limits for other endpoints
            "*": (self.default_limit, self.default_window)
        }
        
        # Endpoints exempt from rate limiting (internal/batch operations)
        self.exempt_paths = [
            "/api/schedule/create",
            "/api/schedule/list",
            "/api/narrative-builder/",
        ]
    
    def _get_limit(self, path: str) -> Tuple[int, int]:
        """Get rate limit for a path."""
        # Check exact matches first
        for pattern, limit in self.limits.items():
            if pattern != "*" and path.startswith(pattern):
                return limit
        
        # Return default
        return self.limits.get("*", (self.default_limit, self.default_window))
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique key for rate limiting (IP address)."""
        # Try to get real IP from headers (for reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/api/health", "/health", "/"]:
            return await call_next(request)
        
        # Skip rate limiting for exempt paths (batch operations)
        for exempt_path in self.exempt_paths:
            if request.url.path.startswith(exempt_path):
                return await call_next(request)
        
        # Skip rate limiting for scheduler (internal service)
        # Scheduler is identified by X-Internal-Service header
        internal_service = request.headers.get("X-Internal-Service")
        if internal_service == "nightly-analysis-scheduler":
            return await call_next(request)
        
        # Get rate limit for this endpoint
        max_requests, window_seconds = self._get_limit(request.url.path)
        
        # Get client identifier
        client_key = self._get_client_key(request)
        rate_limit_key = f"{client_key}:{request.url.path}"
        
        # Check rate limit
        is_allowed, remaining = await _rate_limiter.is_allowed(
            rate_limit_key,
            max_requests,
            window_seconds
        )
        
        if not is_allowed:
            correlation_id = getattr(request.state, "correlation_id", "unknown")
            logger.warning(
                f"[{correlation_id}] Rate limit exceeded for {request.url.path} from {client_key}"
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "correlation_id": correlation_id,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": window_seconds,
                    "limit": max_requests,
                    "window_seconds": window_seconds
                },
                headers={
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int((datetime.now() + timedelta(seconds=window_seconds)).timestamp())),
                    "Retry-After": str(window_seconds)
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int((datetime.now() + timedelta(seconds=window_seconds)).timestamp()))
        
        return response

