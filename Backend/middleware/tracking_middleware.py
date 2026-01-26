"""
User Tracking Middleware
=========================
Automatically track user events based on API requests.

This middleware:
- Tracks landing_view events for dashboard access
- Tracks user_access events for API requests
- Wakes the system from sleep mode on user activity
- Adds session_id to requests for tracking
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import uuid
from datetime import datetime, timezone

from services.user_tracking_service import UserTrackingService, EventName
from services.sleep_mode_service import SleepModeService, WakeTriggerType


class UserTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track user events

    Features:
    - Tracks landing_view for dashboard access
    - Tracks user_access for API requests
    - Wakes system from sleep on user activity
    - Adds session tracking
    """

    def __init__(self, app):
        super().__init__(app)
        self.tracking = UserTrackingService.get_instance()
        self.sleep_service = SleepModeService.get_instance()

    async def dispatch(self, request: Request, call_next):
        """Process request and track events"""

        # Get or create session ID
        session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())

        # Wake system on user activity (if sleeping)
        if self.sleep_service.is_sleeping():
            await self.sleep_service.wake(
                trigger_type=WakeTriggerType.USER_ACCESS,
                metadata={
                    "path": request.url.path,
                    "method": request.method
                }
            )

        # Track landing view for dashboard/landing pages
        path = request.url.path
        if path in ["/", "/dashboard", "/api/dashboard"]:
            await self.tracking.track_acquisition(
                event_name=EventName.LANDING_VIEW.value,
                session_id=session_id,
                properties={
                    "path": path,
                    "referrer": request.headers.get("referer"),
                    "user_agent": request.headers.get("user-agent")
                }
            )

        # Process request
        response = await call_next(request)

        # Set session cookie if new
        if not request.cookies.get("session_id"):
            response.set_cookie(
                key="session_id",
                value=session_id,
                max_age=30 * 24 * 60 * 60,  # 30 days
                httponly=True,
                samesite="lax"
            )

        return response
