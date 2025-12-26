"""
Standardized Error Handling Framework

Provides consistent error handling patterns across the application.
"""
from typing import Optional, Dict, Any, Generic, TypeVar
from fastapi import HTTPException, status
from datetime import datetime
import uuid
import traceback
from loguru import logger

T = TypeVar('T')


class Result(Generic[T]):
    """
    Standard result type for operations that can fail gracefully.
    
    Use this for recoverable errors instead of raising exceptions.
    """
    def __init__(
        self,
        success: bool,
        data: Optional[T] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.error_code = error_code
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API responses."""
        result = {
            "success": self.success,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp
        }
        
        if self.success:
            result["data"] = self.data
        else:
            result["error"] = self.error
            if self.error_code:
                result["error_code"] = self.error_code
            if self.metadata:
                result["metadata"] = self.metadata
        
        return result
    
    @classmethod
    def success_result(cls, data: T, correlation_id: Optional[str] = None) -> 'Result[T]':
        """Create a successful result."""
        return cls(success=True, data=data, correlation_id=correlation_id)
    
    @classmethod
    def error_result(
        cls,
        error: str,
        error_code: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Result[T]':
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            error_code=error_code,
            correlation_id=correlation_id,
            metadata=metadata
        )


class AppError(Exception):
    """
    Base exception for application errors.
    
    Use this for unrecoverable errors that should be logged and returned to the client.
    """
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.metadata = metadata or {}
        super().__init__(self.message)
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        detail = {
            "error": self.message,
            "correlation_id": self.correlation_id,
            "error_code": self.error_code
        }
        if self.metadata:
            detail["metadata"] = self.metadata
        
        return HTTPException(
            status_code=self.status_code,
            detail=detail
        )


class ValidationError(AppError):
    """Error for validation failures."""
    def __init__(self, message: str, field: Optional[str] = None, correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            correlation_id=correlation_id,
            metadata={"field": field} if field else {}
        )


class NotFoundError(AppError):
    """Error for resource not found."""
    def __init__(self, resource: str, resource_id: Optional[str] = None, correlation_id: Optional[str] = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            correlation_id=correlation_id,
            metadata={"resource": resource, "resource_id": resource_id}
        )


class ConflictError(AppError):
    """Error for resource conflicts (e.g., duplicate)."""
    def __init__(self, message: str, correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            correlation_id=correlation_id
        )


def handle_exception(
    exc: Exception,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Standard exception handler.
    
    Converts exceptions to appropriate HTTPException with logging.
    """
    correlation_id = correlation_id or str(uuid.uuid4())
    context = context or {}
    
    # Handle our custom exceptions
    if isinstance(exc, AppError):
        logger.error(
            f"[{correlation_id}] {exc.__class__.__name__}: {exc.message}",
            extra={"correlation_id": correlation_id, "error_code": exc.error_code, **context}
        )
        return exc.to_http_exception()
    
    # Handle HTTPException (re-raise as-is)
    if isinstance(exc, HTTPException):
        logger.warning(
            f"[{correlation_id}] HTTPException: {exc.detail}",
            extra={"correlation_id": correlation_id, "status_code": exc.status_code, **context}
        )
        return exc
    
    # Handle unexpected exceptions
    error_id = str(uuid.uuid4())
    logger.error(
        f"[{correlation_id}] Unexpected error [{error_id}]: {str(exc)}",
        extra={
            "correlation_id": correlation_id,
            "error_id": error_id,
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
            **context
        }
    )
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error": "An unexpected error occurred",
            "correlation_id": correlation_id,
            "error_id": error_id,
            "error_code": "INTERNAL_ERROR"
        }
    )

