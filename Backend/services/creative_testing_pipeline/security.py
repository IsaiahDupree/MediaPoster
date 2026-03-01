"""
ACTP Security Module
=====================
Input sanitization, secrets validation, request authentication,
rate limiting, and secure error handling.
"""

import html
import logging
import os
import re
import time
from collections import defaultdict
from functools import wraps
from typing import Any, Dict, List, Optional, Set

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# ─── Required Environment Variables ──────────────────────

REQUIRED_SECRETS = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
]

OPTIONAL_SECRETS = [
    "OPENAI_API_KEY",
    "GOOGLE_VEO3_API_KEY",
    "NANO_BANANA_API_KEY",
    "META_ACCESS_TOKEN",
    "TIKTOK_ADS_ACCESS_TOKEN",
    "TIKTOK_ADVERTISER_ID",
    "WAITLISTLAB_API_KEY",
]


class SecretsValidator:
    """Validate that required secrets are set at startup."""

    @staticmethod
    def validate_required() -> Dict[str, bool]:
        """Check all required secrets are present. Returns status per secret."""
        status = {}
        missing = []
        for key in REQUIRED_SECRETS:
            present = bool(os.getenv(key))
            status[key] = present
            if not present:
                missing.append(key)

        if missing:
            logger.error(f"[ACTP:Security] Missing required secrets: {missing}")
        else:
            logger.info("[ACTP:Security] All required secrets validated")

        return status

    @staticmethod
    def validate_optional() -> Dict[str, bool]:
        """Check which optional secrets are configured."""
        return {key: bool(os.getenv(key)) for key in OPTIONAL_SECRETS}

    @staticmethod
    def get_provider_availability() -> Dict[str, bool]:
        """Check which video/ad providers are available based on secrets."""
        return {
            "sora": bool(os.getenv("OPENAI_API_KEY")),
            "veo3": bool(os.getenv("GOOGLE_VEO3_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "nano_banana": bool(os.getenv("NANO_BANANA_API_KEY")),
            "meta_ads": bool(os.getenv("META_ACCESS_TOKEN")),
            "tiktok_ads": bool(os.getenv("TIKTOK_ADS_ACCESS_TOKEN")),
            "waitlistlab": bool(os.getenv("WAITLISTLAB_API_KEY")),
            "youtube": bool(os.getenv("YOUTUBE_ACCESS_TOKEN") or os.getenv("GOOGLE_API_KEY")),
            "tiktok": bool(os.getenv("TIKTOK_ACCESS_TOKEN")),
        }


# ─── Input Sanitization ─────────────────────────────────

class InputSanitizer:
    """Sanitize user inputs to prevent XSS, injection, and other attacks."""

    # Allowed characters in campaign names, hooks, CTAs
    SAFE_TEXT_PATTERN = re.compile(r"[^\w\s\-.,!?'\"@#$%&()+=/:\[\]{}]", re.UNICODE)

    # Max lengths per field
    FIELD_LIMITS = {
        "name": 200,
        "hook": 500,
        "cta": 200,
        "angle": 500,
        "script": 2000,
        "description": 5000,
        "caption": 2200,
    }

    @classmethod
    def sanitize_text(cls, text: str, field_name: str = "text") -> str:
        """Sanitize text input: escape HTML, enforce length limits."""
        if not isinstance(text, str):
            return str(text)

        # HTML escape
        text = html.escape(text, quote=True)

        # Enforce length limit
        max_len = cls.FIELD_LIMITS.get(field_name, 5000)
        if len(text) > max_len:
            text = text[:max_len]

        return text.strip()

    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """Validate and sanitize a URL."""
        if not isinstance(url, str):
            raise ValueError("URL must be a string")

        url = url.strip()

        # Only allow http/https schemes
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL scheme: {url[:20]}")

        # Block private/internal IPs
        blocked_patterns = [
            r"://localhost",
            r"://127\.",
            r"://0\.",
            r"://10\.",
            r"://192\.168\.",
            r"://172\.(1[6-9]|2[0-9]|3[01])\.",
        ]
        for pattern in blocked_patterns:
            if re.search(pattern, url):
                raise ValueError("Internal/private URLs are not allowed")

        return url

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize all string values in a dictionary."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_text(value, key)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_dict(item) if isinstance(item, dict)
                    else cls.sanitize_text(item, key) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    @classmethod
    def validate_file_upload(
        cls,
        filename: str,
        content_type: str,
        file_size: int,
        max_size_mb: int = 500,
    ) -> bool:
        """Validate a file upload: type, size, extension."""
        allowed_types = {"video/mp4", "video/quicktime", "video/webm", "video/mpeg"}
        allowed_extensions = {".mp4", ".mov", ".webm", ".mpeg"}

        if content_type not in allowed_types:
            raise ValueError(f"Invalid file type: {content_type}")

        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_extensions:
            raise ValueError(f"Invalid file extension: {ext}")

        max_bytes = max_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise ValueError(f"File too large: {file_size} bytes (max {max_size_mb}MB)")

        return True


# ─── Rate Limiting ───────────────────────────────────────

class RateLimiter:
    """In-memory rate limiter per client IP."""

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def check(self, client_ip: str) -> bool:
        """Check if client is within rate limit. Returns True if allowed."""
        now = time.time()
        window = now - 60  # 1-minute window

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > window
        ]

        if len(self._requests[client_ip]) >= self.rpm:
            return False

        self._requests[client_ip].append(now)
        return True

    def get_retry_after(self, client_ip: str) -> int:
        """Get seconds until the client can retry."""
        if not self._requests[client_ip]:
            return 0
        oldest = min(self._requests[client_ip])
        return max(0, int(60 - (time.time() - oldest)))


# ─── Authentication Middleware ───────────────────────────

class ACTPAuthMiddleware(BaseHTTPMiddleware):
    """JWT or API key authentication for ACTP endpoints."""

    def __init__(self, app, api_keys: Optional[Set[str]] = None):
        super().__init__(app)
        self.api_keys = api_keys or set()
        # Load API key from env
        env_key = os.getenv("ACTP_API_KEY")
        if env_key:
            self.api_keys.add(env_key)

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health check and docs
        if request.url.path in ("/api/actp/health", "/docs", "/openapi.json"):
            return await call_next(request)

        # Only protect ACTP routes
        if not request.url.path.startswith("/api/actp"):
            return await call_next(request)

        # Check API key
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if api_key and api_key in self.api_keys:
            return await call_next(request)

        # Check Bearer token (Supabase JWT)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if await self._validate_supabase_jwt(token):
                return await call_next(request)

        # No auth configured = allow (for development)
        if not self.api_keys and not os.getenv("SUPABASE_JWT_SECRET"):
            return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "Valid authentication required"},
        )

    async def _validate_supabase_jwt(self, token: str) -> bool:
        """Validate a Supabase JWT token."""
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if not jwt_secret:
            return False

        try:
            import jwt as pyjwt
            payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"], audience="authenticated")
            return bool(payload.get("sub"))
        except Exception:
            return False


# ─── Rate Limit Middleware ───────────────────────────────

class ACTPRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for ACTP endpoints."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute)

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/actp"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        if not self.limiter.check(client_ip):
            retry_after = self.limiter.get_retry_after(client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "message": "Too many requests",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)


# ─── Secure Error Handling ───────────────────────────────

class ACTPErrorHandler:
    """Standardized error responses without exposing internals."""

    ERROR_MAP = {
        400: ("bad_request", "Invalid request"),
        401: ("unauthorized", "Authentication required"),
        403: ("forbidden", "Access denied"),
        404: ("not_found", "Resource not found"),
        409: ("conflict", "Resource conflict"),
        413: ("payload_too_large", "Request body too large"),
        422: ("validation_error", "Invalid input data"),
        429: ("rate_limited", "Too many requests"),
        500: ("internal_error", "An unexpected error occurred"),
        503: ("service_unavailable", "Service temporarily unavailable"),
    }

    @classmethod
    def error_response(
        cls,
        status_code: int,
        detail: Optional[str] = None,
        errors: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Create a standardized error response."""
        code, default_msg = cls.ERROR_MAP.get(status_code, ("error", "Error"))
        response = {
            "error": code,
            "message": detail or default_msg,
            "status_code": status_code,
        }
        if errors:
            response["errors"] = errors
        return response

    @classmethod
    def raise_safe(cls, status_code: int, detail: Optional[str] = None):
        """Raise an HTTPException with standardized format."""
        body = cls.error_response(status_code, detail)
        raise HTTPException(status_code=status_code, detail=body)


# ─── CORS Configuration ─────────────────────────────────

def get_cors_config() -> Dict[str, Any]:
    """Get CORS configuration from environment."""
    origins_str = os.getenv("ACTP_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    origins = [o.strip() for o in origins_str.split(",") if o.strip()]

    return {
        "allow_origins": origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
    }


# ─── Request Size Limits ────────────────────────────────

MAX_REQUEST_BODY_SIZE = int(os.getenv("ACTP_MAX_BODY_SIZE", 10 * 1024 * 1024))  # 10MB default


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforce max request body size."""

    def __init__(self, app, max_size: int = MAX_REQUEST_BODY_SIZE):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=413,
                content=ACTPErrorHandler.error_response(
                    413, f"Request body exceeds {self.max_size // (1024*1024)}MB limit"
                ),
            )
        return await call_next(request)
