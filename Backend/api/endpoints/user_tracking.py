"""
User Tracking API Endpoints
============================
API for tracking user events and retrieving analytics.

Endpoints:
- POST /api/tracking/event - Track a user event
- GET /api/tracking/events - Get recent events
- GET /api/tracking/events/user/{user_id} - Get events for user
- GET /api/tracking/events/{event_name} - Get events by name
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from loguru import logger

from services.user_tracking_service import UserTrackingService, EventName


router = APIRouter(prefix="/api/tracking", tags=["User Tracking"])


class TrackEventRequest(BaseModel):
    """Request to track an event"""
    event_name: str = Field(..., description="Event name (e.g., 'post_created', 'login_success')")
    user_id: Optional[str] = Field(default=None, description="User ID (null for anonymous)")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Event properties")
    platform: str = Field(default="web", description="Platform (web, mobile, api)")
    category: Optional[str] = Field(default=None, description="Event category")


@router.post("/event")
async def track_event(request: TrackEventRequest):
    """
    Track a user event

    Args:
        event_name: Name of the event
        user_id: User ID (optional, null for anonymous)
        session_id: Session ID (optional)
        properties: Event-specific properties
        platform: Platform (web, mobile, api)
        category: Event category (acquisition, activation, etc.)

    Returns:
        Success confirmation
    """
    try:
        tracking = UserTrackingService.get_instance()

        await tracking.track(
            event_name=request.event_name,
            user_id=request.user_id,
            session_id=request.session_id,
            properties=request.properties,
            platform=request.platform,
            category=request.category
        )

        return {
            "success": True,
            "message": "Event tracked",
            "data": {
                "event_name": request.event_name,
                "user_id": request.user_id
            }
        }

    except Exception as e:
        logger.error(f"Error tracking event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_recent_events(limit: int = 100):
    """
    Get recent events

    Args:
        limit: Maximum number of events to return (default: 100, max: 1000)

    Returns:
        List of recent events
    """
    try:
        tracking = UserTrackingService.get_instance()

        # Limit to max 1000
        limit = min(limit, 1000)

        events = tracking.get_recent_events(limit=limit)

        return {
            "success": True,
            "data": {
                "events": events,
                "count": len(events)
            }
        }

    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/user/{user_id}")
async def get_user_events(user_id: str, limit: int = 100):
    """
    Get events for a specific user

    Args:
        user_id: User ID
        limit: Maximum number of events to return (default: 100, max: 1000)

    Returns:
        List of user events
    """
    try:
        tracking = UserTrackingService.get_instance()

        # Limit to max 1000
        limit = min(limit, 1000)

        events = tracking.get_events_by_user(user_id=user_id, limit=limit)

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "events": events,
                "count": len(events)
            }
        }

    except Exception as e:
        logger.error(f"Error getting user events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/name/{event_name}")
async def get_events_by_name(event_name: str, limit: int = 100):
    """
    Get events by name

    Args:
        event_name: Event name
        limit: Maximum number of events to return (default: 100, max: 1000)

    Returns:
        List of events with specified name
    """
    try:
        tracking = UserTrackingService.get_instance()

        # Limit to max 1000
        limit = min(limit, 1000)

        events = tracking.get_events_by_name(event_name=event_name, limit=limit)

        return {
            "success": True,
            "data": {
                "event_name": event_name,
                "events": events,
                "count": len(events)
            }
        }

    except Exception as e:
        logger.error(f"Error getting events by name: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/event-names")
async def get_event_names():
    """
    Get list of standard event names

    Returns:
        List of event names organized by category
    """
    try:
        return {
            "success": True,
            "data": {
                "acquisition": [
                    EventName.LANDING_VIEW.value,
                    EventName.SIGNUP_STARTED.value,
                    EventName.SIGNUP_COMPLETED.value
                ],
                "activation": [
                    EventName.LOGIN_SUCCESS.value,
                    EventName.LOGIN_FAILED.value,
                    EventName.ACTIVATION_COMPLETE.value,
                    EventName.PLATFORM_CONNECTED.value
                ],
                "core_value": [
                    EventName.POST_CREATED.value,
                    EventName.POST_SCHEDULED.value,
                    EventName.POST_PUBLISHED.value,
                    EventName.MEDIA_UPLOADED.value,
                    EventName.TEMPLATE_USED.value
                ],
                "monetization": [
                    EventName.CHECKOUT_STARTED.value,
                    EventName.PURCHASE_COMPLETED.value,
                    EventName.SUBSCRIPTION_UPGRADED.value
                ],
                "retention": [
                    EventName.USER_RETURNED.value,
                    EventName.FEATURE_ADOPTED.value
                ],
                "error_performance": [
                    EventName.ERROR_OCCURRED.value,
                    EventName.API_LATENCY.value
                ]
            }
        }

    except Exception as e:
        logger.error(f"Error getting event names: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable")
async def enable_tracking():
    """Enable user tracking"""
    try:
        tracking = UserTrackingService.get_instance()
        tracking.enable()

        return {
            "success": True,
            "message": "Tracking enabled"
        }

    except Exception as e:
        logger.error(f"Error enabling tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable")
async def disable_tracking():
    """Disable user tracking"""
    try:
        tracking = UserTrackingService.get_instance()
        tracking.disable()

        return {
            "success": True,
            "message": "Tracking disabled"
        }

    except Exception as e:
        logger.error(f"Error disabling tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# TRACK-006: Retention Event Tracking
class TrackRetentionRequest(BaseModel):
    """Request to track retention event"""
    event_name: str = Field(..., description="Event name (user_returned, feature_adopted)")
    user_id: str = Field(..., description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Event properties")


@router.post("/retention")
async def track_retention_event(request: TrackRetentionRequest):
    """
    Track retention event (TRACK-006)

    Events:
    - user_returned: User came back after initial session
    - feature_adopted: User used a feature for the 3rd time

    Args:
        event_name: Event name
        user_id: User ID
        session_id: Session ID (optional)
        properties: Event properties (e.g., days_since_last_visit, feature_name)

    Returns:
        Success confirmation
    """
    try:
        tracking = UserTrackingService.get_instance()

        await tracking.track_retention(
            event_name=request.event_name,
            user_id=request.user_id,
            session_id=request.session_id,
            properties=request.properties
        )

        return {
            "success": True,
            "message": "Retention event tracked",
            "data": {
                "event_name": request.event_name,
                "user_id": request.user_id
            }
        }

    except Exception as e:
        logger.error(f"Error tracking retention event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# TRACK-007: Error & Performance Tracking
class TrackErrorRequest(BaseModel):
    """Request to track error"""
    error_message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(default=None, description="Error code")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Error context")


@router.post("/error")
async def track_error_event(request: TrackErrorRequest):
    """
    Track error event (TRACK-007)

    Args:
        error_message: Error message
        error_code: Error code (e.g., 'API_TIMEOUT', 'VALIDATION_ERROR')
        user_id: User ID (optional)
        session_id: Session ID (optional)
        properties: Additional error context

    Returns:
        Success confirmation
    """
    try:
        tracking = UserTrackingService.get_instance()

        await tracking.track_error(
            error_message=request.error_message,
            error_code=request.error_code,
            user_id=request.user_id,
            session_id=request.session_id,
            properties=request.properties
        )

        return {
            "success": True,
            "message": "Error event tracked"
        }

    except Exception as e:
        logger.error(f"Error tracking error event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TrackPerformanceRequest(BaseModel):
    """Request to track performance metric"""
    metric_name: str = Field(..., description="Metric name (api_latency, lcp, fid, cls)")
    metric_value: float = Field(..., description="Metric value")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Metric context")


@router.post("/performance")
async def track_performance_metric(request: TrackPerformanceRequest):
    """
    Track performance metric (TRACK-007)

    Metrics:
    - api_latency: API response time
    - page_load_time: Page load time
    - lcp: Largest Contentful Paint
    - fid: First Input Delay
    - cls: Cumulative Layout Shift

    Args:
        metric_name: Metric name
        metric_value: Metric value (ms or score)
        user_id: User ID (optional)
        session_id: Session ID (optional)
        properties: Additional context

    Returns:
        Success confirmation
    """
    try:
        tracking = UserTrackingService.get_instance()

        await tracking.track_performance(
            metric_name=request.metric_name,
            metric_value=request.metric_value,
            user_id=request.user_id,
            session_id=request.session_id,
            properties=request.properties
        )

        return {
            "success": True,
            "message": "Performance metric tracked",
            "data": {
                "metric_name": request.metric_name,
                "metric_value": request.metric_value
            }
        }

    except Exception as e:
        logger.error(f"Error tracking performance metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# TRACK-008: User Identification
class IdentifyUserRequest(BaseModel):
    """Request to identify user"""
    user_id: str = Field(..., description="User ID")
    traits: Optional[Dict[str, Any]] = Field(
        default=None,
        description="User traits (email, plan, name, etc.)"
    )


@router.post("/identify")
async def identify_user(request: IdentifyUserRequest):
    """
    Identify user with traits (TRACK-008)

    Associates a user with their traits. Called on login or profile update.

    Args:
        user_id: User ID
        traits: User traits (email, plan, name, company, etc.)

    Example traits:
    {
        "email": "user@example.com",
        "plan": "pro",
        "name": "John Doe",
        "signup_date": "2026-01-15",
        "platforms_connected": ["twitter", "instagram"]
    }

    Returns:
        Success confirmation
    """
    try:
        tracking = UserTrackingService.get_instance()

        await tracking.identify_user(
            user_id=request.user_id,
            traits=request.traits
        )

        return {
            "success": True,
            "message": "User identified",
            "data": {
                "user_id": request.user_id,
                "traits_count": len(request.traits or {})
            }
        }

    except Exception as e:
        logger.error(f"Error identifying user: {e}")
        raise HTTPException(status_code=500, detail=str(e))
