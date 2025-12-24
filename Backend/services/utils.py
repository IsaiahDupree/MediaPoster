"""
Utility functions for services
Provides common helper functions used across the application
"""
import re
from uuid import UUID
from typing import Optional


def calculate_engagement_rate(likes: int, comments: int, shares: int, followers: int) -> float:
    """Calculate engagement rate as percentage"""
    if followers == 0:
        return 0.0
    return ((likes + comments + shares) / followers) * 100


def validate_video_duration(duration: float, min_duration: float = 5, max_duration: float = 300) -> bool:
    """Validate video duration is within acceptable range"""
    return min_duration <= duration <= max_duration


def calculate_aspect_ratio(width: int, height: int) -> float:
    """Calculate aspect ratio from width and height"""
    if height == 0:
        return 0.0
    return width / height


def validate_post_content(content: str, platform: Optional[str] = None) -> dict:
    """Validate post content for length and content rules"""
    result = {"valid": True, "warnings": []}
    
    if not content or len(content.strip()) == 0:
        result["valid"] = False
        result["warnings"].append("Content cannot be empty")
        return result
    
    # Platform-specific limits
    limits = {
        "twitter": 280,
        "instagram": 2200,
        "tiktok": 2200,
        "youtube": 5000,
    }
    
    max_length = limits.get(platform, 2200)
    if len(content) > max_length:
        result["warnings"].append(f"Content exceeds {platform} limit of {max_length} characters")
    
    return result


def calculate_goal_progress(current: float, target: float) -> float:
    """Calculate goal progress as percentage"""
    if target == 0:
        return 100.0 if current > 0 else 0.0
    return (current / target) * 100


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS and SQL injection"""
    if not text:
        return ""
    
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Escape SQL injection characters
    text = text.replace("'", "''")
    text = text.replace(";", "")
    text = text.replace("--", "")
    
    return text


def format_number(num: int) -> str:
    """Format number for display (e.g., 1000 -> 1K)"""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def parse_duration(seconds: int) -> str:
    """Parse duration in seconds to formatted string (MM:SS or HH:MM:SS)"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def validate_email(email: str) -> bool:
    """Validate email address format"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format"""
    if not url:
        return False
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_uuid(uuid_string: str) -> bool:
    """Validate UUID format"""
    try:
        UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False

