"""
Input Validation Utilities

Provides standardized input validation functions for endpoints.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, validator, Field
from fastapi import HTTPException, status
import re
from utils.error_handling import ValidationError


def validate_uuid(uuid_string: str, field_name: str = "id") -> str:
    """Validate UUID format."""
    import uuid
    try:
        uuid_obj = uuid.UUID(uuid_string)
        return str(uuid_obj)
    except ValueError:
        raise ValidationError(
            f"Invalid {field_name} format: {uuid_string}",
            field=field_name
        )


def validate_platform(platform: str) -> str:
    """Validate platform name."""
    valid_platforms = ['tiktok', 'instagram', 'youtube', 'twitter', 'facebook', 'linkedin']
    platform_lower = platform.lower().strip()
    
    if platform_lower not in valid_platforms:
        raise ValidationError(
            f"Invalid platform: {platform}. Valid platforms: {', '.join(valid_platforms)}",
            field="platform"
        )
    
    return platform_lower


def validate_scheduled_time(scheduled_time: datetime, field_name: str = "scheduled_time") -> datetime:
    """Validate scheduled time is in the future."""
    now = datetime.now(timezone.utc)
    
    # Ensure timezone-aware
    if scheduled_time.tzinfo is None:
        scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
    
    # Add 1 second buffer for clock drift
    from datetime import timedelta
    if scheduled_time <= now - timedelta(seconds=1):
        raise ValidationError(
            f"{field_name} must be in the future. Got: {scheduled_time}, Now: {now}",
            field=field_name
        )
    
    return scheduled_time


def validate_file_path(file_path: str, must_exist: bool = True) -> str:
    """Validate file path."""
    from pathlib import Path
    import os
    
    path = Path(file_path)
    
    if must_exist and not path.exists():
        raise ValidationError(
            f"File not found: {file_path}",
            field="file_path"
        )
    
    if must_exist and not path.is_file():
        raise ValidationError(
            f"Path is not a file: {file_path}",
            field="file_path"
        )
    
    if must_exist and not os.access(str(path), os.R_OK):
        raise ValidationError(
            f"File is not readable: {file_path}",
            field="file_path"
        )
    
    return str(path)


def validate_url(url: str, field_name: str = "url") -> str:
    """Validate URL format."""
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValidationError(
            f"Invalid {field_name} format: {url}",
            field=field_name
        )
    
    return url


def validate_hashtags(hashtags: List[str], max_count: int = 30) -> List[str]:
    """Validate hashtags list."""
    if not isinstance(hashtags, list):
        raise ValidationError("hashtags must be a list", field="hashtags")
    
    if len(hashtags) > max_count:
        raise ValidationError(
            f"Too many hashtags: {len(hashtags)}/{max_count}",
            field="hashtags"
        )
    
    # Validate each hashtag format
    validated = []
    for tag in hashtags:
        if not isinstance(tag, str):
            raise ValidationError(f"Hashtag must be a string: {tag}", field="hashtags")
        
        # Remove # if present and validate
        clean_tag = tag.lstrip('#').strip()
        if not clean_tag:
            continue
        
        # Validate format (alphanumeric and underscores)
        if not re.match(r'^[a-zA-Z0-9_]+$', clean_tag):
            raise ValidationError(
                f"Invalid hashtag format: {tag}. Use alphanumeric characters and underscores only.",
                field="hashtags"
            )
        
        validated.append(clean_tag)
    
    return validated


def validate_caption_length(caption: str, max_length: int, platform: Optional[str] = None) -> str:
    """Validate caption length."""
    if not caption:
        return caption
    
    if len(caption) > max_length:
        platform_msg = f" for {platform}" if platform else ""
        raise ValidationError(
            f"Caption too long{platform_msg}: {len(caption)}/{max_length} characters",
            field="caption"
        )
    
    return caption


def validate_priority(priority: int, min_value: int = 0, max_value: int = 100) -> int:
    """Validate priority value."""
    if not isinstance(priority, int):
        raise ValidationError("Priority must be an integer", field="priority")
    
    if priority < min_value or priority > max_value:
        raise ValidationError(
            f"Priority must be between {min_value} and {max_value}. Got: {priority}",
            field="priority"
        )
    
    return priority


class ValidatedRequest(BaseModel):
    """Base class for validated requests with correlation ID support."""
    correlation_id: Optional[str] = None
    
    class Config:
        extra = "forbid"  # Reject extra fields


def validate_request(request: BaseModel, correlation_id: Optional[str] = None) -> BaseModel:
    """
    Validate a request model.
    
    This is a convenience function that can be used in endpoints.
    """
    # Add correlation ID if provided
    if correlation_id and hasattr(request, 'correlation_id'):
        request.correlation_id = correlation_id
    
    return request

