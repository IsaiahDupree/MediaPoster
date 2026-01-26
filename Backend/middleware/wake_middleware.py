"""
Wake Middleware
===============
Middleware to wake the system from sleep mode when users access the API or dashboard.

Any incoming HTTP request will trigger a wake event if the system is sleeping.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class WakeMiddleware(BaseHTTPMiddleware):
    """
    Wake Middleware

    Wakes the system from sleep mode on any incoming request.
    Ensures the system is responsive when users access the dashboard or API.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process incoming request and wake system if needed

        Args:
            request: The incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response from next handler
        """
        # Skip health checks and sleep status to avoid constant waking
        # The sleep status endpoint should not wake the system (read-only)
        if request.url.path in ["/health", "/api/health", "/api/sleep/health", "/api/sleep/status"]:
            return await call_next(request)

        # Try to wake the system
        try:
            from services.sleep_mode_service import SleepModeService, WakeTriggerType, SleepState

            sleep_service = SleepModeService.get_instance()

            # Only wake if actually sleeping
            if sleep_service.state == SleepState.SLEEPING:
                await sleep_service.wake(
                    trigger_type=WakeTriggerType.USER_ACCESS,
                    metadata={
                        "path": request.url.path,
                        "method": request.method,
                        "client": request.client.host if request.client else "unknown"
                    }
                )

                logger.info(f"💡 System woke from sleep (user access: {request.method} {request.url.path})")

        except Exception as e:
            # Don't fail the request if wake fails
            logger.warning(f"Failed to wake system: {e}")

        # Continue with request
        response = await call_next(request)
        return response
