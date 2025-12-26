"""
Correlation ID Middleware

Adds correlation IDs to all requests for request tracing.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import uuid
from loguru import logger


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to all requests.
    
    - Extracts correlation ID from X-Correlation-ID header if present
    - Generates new correlation ID if not present
    - Adds correlation ID to request state
    - Adds correlation ID to response headers
    """
    
    async def dispatch(self, request: Request, call_next):
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Add to request state for use in endpoints
        request.state.correlation_id = correlation_id
        
        # Add to logger context
        logger.bind(correlation_id=correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response

