"""
User Event Tracking Service
============================
Track user events for analytics and product insights.

Based on: autonomous-coding-dashboard/harness/prompts/PRD_USER_TRACKING_ALL_TARGETS.md

Event Categories:
- Acquisition: landing_view, signup_started, signup_completed
- Activation: login_success, activation_complete, platform_connected
- Core Value: post_created, post_scheduled, post_published, media_uploaded, template_used
- Monetization: checkout_started, purchase_completed, subscription_upgraded
- Retention: user_returned, feature_adopted
- Error/Performance: error_occurred, api_latency

All events include:
- user_id (if authenticated)
- session_id
- timestamp (ISO 8601 UTC)
- event_name
- properties (dict)
- platform (web, mobile, api)
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from loguru import logger
from enum import Enum
import asyncio
from dataclasses import dataclass, field, asdict


class EventCategory(Enum):
    """Event categories for tracking"""
    ACQUISITION = "acquisition"
    ACTIVATION = "activation"
    CORE_VALUE = "core_value"
    MONETIZATION = "monetization"
    RETENTION = "retention"
    ERROR = "error"
    PERFORMANCE = "performance"


class EventName(Enum):
    """Standard event names"""
    # Acquisition
    LANDING_VIEW = "landing_view"
    SIGNUP_STARTED = "signup_started"
    SIGNUP_COMPLETED = "signup_completed"

    # Activation
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    ACTIVATION_COMPLETE = "activation_complete"
    PLATFORM_CONNECTED = "platform_connected"

    # Core Value
    POST_CREATED = "post_created"
    POST_SCHEDULED = "post_scheduled"
    POST_PUBLISHED = "post_published"
    MEDIA_UPLOADED = "media_uploaded"
    TEMPLATE_USED = "template_used"

    # Monetization
    CHECKOUT_STARTED = "checkout_started"
    PURCHASE_COMPLETED = "purchase_completed"
    SUBSCRIPTION_UPGRADED = "subscription_upgraded"

    # Retention
    USER_RETURNED = "user_returned"
    FEATURE_ADOPTED = "feature_adopted"

    # Error/Performance
    ERROR_OCCURRED = "error_occurred"
    API_LATENCY = "api_latency"


@dataclass
class TrackingEvent:
    """User tracking event"""
    event_name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    platform: str = "web"
    category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission"""
        return {
            "event_name": self.event_name,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "properties": self.properties,
            "platform": self.platform,
            "category": self.category
        }


class UserTrackingService:
    """
    User Event Tracking Service

    Tracks user events for analytics and product insights.
    Events are logged locally and can be sent to analytics platforms.

    Usage:
        tracking = UserTrackingService.get_instance()

        # Track acquisition event
        await tracking.track(
            event_name=EventName.LANDING_VIEW.value,
            user_id=None,  # Anonymous
            session_id=session_id,
            properties={"referrer": "google", "utm_source": "ads"}
        )

        # Track activation event
        await tracking.track(
            event_name=EventName.LOGIN_SUCCESS.value,
            user_id=user_id,
            session_id=session_id,
            properties={"login_method": "email"}
        )

        # Track core value event
        await tracking.track(
            event_name=EventName.POST_PUBLISHED.value,
            user_id=user_id,
            properties={
                "platform": "twitter",
                "post_id": post_id,
                "scheduled": False
            }
        )
    """

    _instance: Optional["UserTrackingService"] = None

    def __init__(self):
        """Initialize tracking service"""
        if UserTrackingService._instance is not None:
            raise RuntimeError("Use UserTrackingService.get_instance()")

        self.events: List[TrackingEvent] = []
        self._max_events_in_memory = 1000
        self._enabled = True

        logger.info("📊 User Tracking Service initialized")

    @classmethod
    def get_instance(cls) -> "UserTrackingService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def track(
        self,
        event_name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        platform: str = "web",
        category: Optional[str] = None
    ) -> None:
        """
        Track a user event

        Args:
            event_name: Name of the event (use EventName enum values)
            user_id: User ID (None for anonymous events)
            session_id: Session ID for grouping events
            properties: Event-specific properties
            platform: Platform (web, mobile, api)
            category: Event category (acquisition, activation, etc.)
        """
        if not self._enabled:
            logger.debug(f"Tracking disabled, skipping event: {event_name}")
            return

        event = TrackingEvent(
            event_name=event_name,
            user_id=user_id,
            session_id=session_id,
            properties=properties or {},
            platform=platform,
            category=category
        )

        # Add to in-memory store
        self.events.append(event)

        # Trim if too large
        if len(self.events) > self._max_events_in_memory:
            self.events = self.events[-self._max_events_in_memory:]

        # Log event
        logger.info(
            f"📊 Event tracked | {event_name} | "
            f"User: {user_id or 'anonymous'} | "
            f"Properties: {properties or {}}"
        )

        # TODO: Send to analytics platform (Mixpanel, Segment, etc.)
        # For now, just log locally

    async def track_acquisition(
        self,
        event_name: str,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track acquisition event (usually anonymous)"""
        await self.track(
            event_name=event_name,
            session_id=session_id,
            properties=properties,
            category=EventCategory.ACQUISITION.value
        )

    async def track_activation(
        self,
        event_name: str,
        user_id: str,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track activation event (user onboarding)"""
        await self.track(
            event_name=event_name,
            user_id=user_id,
            session_id=session_id,
            properties=properties,
            category=EventCategory.ACTIVATION.value
        )

    async def track_core_value(
        self,
        event_name: str,
        user_id: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track core value event (user getting value from product)"""
        await self.track(
            event_name=event_name,
            user_id=user_id,
            properties=properties,
            category=EventCategory.CORE_VALUE.value
        )

    async def track_monetization(
        self,
        event_name: str,
        user_id: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track monetization event (purchases, upgrades)"""
        await self.track(
            event_name=event_name,
            user_id=user_id,
            properties=properties,
            category=EventCategory.MONETIZATION.value
        )

    async def track_retention(
        self,
        event_name: str,
        user_id: str,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track retention event (TRACK-006)

        Events:
        - user_returned: User came back after initial session
        - feature_adopted: User used a feature for the 3rd time

        Args:
            event_name: Event name (user_returned, feature_adopted)
            user_id: User ID
            session_id: Session ID (optional)
            properties: Event properties (e.g., days_since_last_visit, feature_name)
        """
        await self.track(
            event_name=event_name,
            user_id=user_id,
            session_id=session_id,
            properties=properties,
            category=EventCategory.RETENTION.value
        )

    async def track_error(
        self,
        error_message: str,
        error_code: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track error event (TRACK-007)

        Args:
            error_message: Error message
            error_code: Error code (e.g., 'API_TIMEOUT', 'VALIDATION_ERROR')
            user_id: User ID (optional)
            session_id: Session ID (optional)
            properties: Additional error context (stack_trace, endpoint, etc.)
        """
        error_properties = {
            "error_message": error_message,
            "error_code": error_code,
            **(properties or {})
        }

        await self.track(
            event_name=EventName.ERROR_OCCURRED.value,
            user_id=user_id,
            session_id=session_id,
            properties=error_properties,
            category=EventCategory.ERROR.value
        )

    async def track_performance(
        self,
        metric_name: str,
        metric_value: float,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track performance metric (TRACK-007)

        Metrics:
        - api_latency: API endpoint response time
        - page_load_time: Page load time (Core Web Vitals)
        - lcp: Largest Contentful Paint
        - fid: First Input Delay
        - cls: Cumulative Layout Shift

        Args:
            metric_name: Metric name
            metric_value: Metric value (e.g., latency in ms)
            user_id: User ID (optional)
            session_id: Session ID (optional)
            properties: Additional context (endpoint, page_url, etc.)
        """
        perf_properties = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "unit": "ms" if "latency" in metric_name or "time" in metric_name else "score",
            **(properties or {})
        }

        await self.track(
            event_name=EventName.API_LATENCY.value,
            user_id=user_id,
            session_id=session_id,
            properties=perf_properties,
            category=EventCategory.PERFORMANCE.value
        )

    async def identify_user(
        self,
        user_id: str,
        traits: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Identify user with traits (TRACK-008)

        This associates a user with their traits (email, plan, name, etc.)
        Called on login or when user data is updated.

        Args:
            user_id: User ID
            traits: User traits (email, plan, name, company, etc.)

        Example:
            await tracking.identify_user(
                user_id="user_123",
                traits={
                    "email": "user@example.com",
                    "plan": "pro",
                    "name": "John Doe",
                    "signup_date": "2026-01-15",
                    "platforms_connected": ["twitter", "instagram"]
                }
            )
        """
        # Store user identification event
        await self.track(
            event_name="user_identified",
            user_id=user_id,
            properties={
                "traits": traits or {},
                "identified_at": datetime.now(timezone.utc).isoformat()
            },
            category="identification"
        )

        logger.info(f"👤 User identified | ID: {user_id} | Traits: {list((traits or {}).keys())}")

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events"""
        return [e.to_dict() for e in self.events[-limit:]]

    def get_events_by_user(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events for specific user"""
        user_events = [e for e in self.events if e.user_id == user_id]
        return [e.to_dict() for e in user_events[-limit:]]

    def get_events_by_name(self, event_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events by name"""
        named_events = [e for e in self.events if e.event_name == event_name]
        return [e.to_dict() for e in named_events[-limit:]]

    def enable(self) -> None:
        """Enable tracking"""
        self._enabled = True
        logger.info("📊 User tracking enabled")

    def disable(self) -> None:
        """Disable tracking"""
        self._enabled = False
        logger.warning("📊 User tracking disabled")

    def clear_events(self) -> None:
        """Clear all events (for testing)"""
        self.events.clear()
        logger.info("📊 Event history cleared")
