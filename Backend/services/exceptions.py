"""
Custom exceptions for service layer
"""


class ServiceError(Exception):
    """Base exception for service layer errors"""
    pass


class ValidationError(ServiceError):
    """Raised when input validation fails"""
    pass


class NotFoundError(ServiceError):
    """Raised when a requested resource is not found"""
    pass


class PermissionError(ServiceError):
    """Raised when user doesn't have permission for an action"""
    pass


class ConflictError(ServiceError):
    """Raised when there's a conflict with existing data"""
    pass
