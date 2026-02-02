"""
Meta Pixel Tracking Service (META-001 through META-008)
=======================================================
Provides Meta Pixel installation, event tracking, CAPI server-side events,
deduplication, PII hashing, custom audiences, and conversion optimization.

META-001: Meta Pixel Installation - pixel_id config, init snippet
META-002: PageView Tracking - automatic page view events
META-003: Standard Events Mapping - map app events to Meta standard events
META-004: CAPI Server-Side Events - Conversions API for server events
META-005: Event Deduplication - pixel+CAPI dedup via event_id
META-006: User Data Hashing (PII) - SHA-256 hash before sending to Meta
META-007: Custom Audiences Setup - audience definitions from segments
META-008: Conversion Optimization - event priority and value optimization

Usage:
    from services.meta_pixel_service import MetaPixelService, get_meta_pixel_service

    pixel = get_meta_pixel_service()
    pixel.track_page_view(url="https://app.example.com/dashboard")
    pixel.track_standard_event("Purchase", value=29.99, currency="USD")
"""

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List, Optional
from uuid import uuid4
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ============================================================================
# META-001: Configuration & Installation
# ============================================================================

@dataclass
class MetaPixelConfig:
    """Meta Pixel configuration (META-001)."""
    pixel_id: str = ""
    access_token: str = ""
    api_version: str = "v18.0"
    test_event_code: Optional[str] = None  # For testing in Events Manager
    domain_verification: Optional[str] = None
    automatic_matching: bool = True
    cookie_consent_required: bool = True
    is_installed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate(self) -> bool:
        """Check if pixel is properly configured."""
        return bool(self.pixel_id)


# ============================================================================
# META-003: Standard Events Mapping
# ============================================================================

class MetaStandardEvent(str, Enum):
    """Meta standard event types (META-003)."""
    PAGE_VIEW = "PageView"
    VIEW_CONTENT = "ViewContent"
    SEARCH = "Search"
    ADD_TO_CART = "AddToCart"
    ADD_TO_WISHLIST = "AddToWishlist"
    INITIATE_CHECKOUT = "InitiateCheckout"
    ADD_PAYMENT_INFO = "AddPaymentInfo"
    PURCHASE = "Purchase"
    LEAD = "Lead"
    COMPLETE_REGISTRATION = "CompleteRegistration"
    CONTACT = "Contact"
    CUSTOMIZE_PRODUCT = "CustomizeProduct"
    DONATE = "Donate"
    FIND_LOCATION = "FindLocation"
    SCHEDULE = "Schedule"
    START_TRIAL = "StartTrial"
    SUBMIT_APPLICATION = "SubmitApplication"
    SUBSCRIBE = "Subscribe"


# App events → Meta standard events mapping
APP_TO_META_EVENT_MAP: Dict[str, str] = {
    "landing_view": MetaStandardEvent.PAGE_VIEW,
    "login_success": MetaStandardEvent.COMPLETE_REGISTRATION,
    "activation_complete": MetaStandardEvent.LEAD,
    "post_created": MetaStandardEvent.VIEW_CONTENT,
    "post_scheduled": MetaStandardEvent.SCHEDULE,
    "post_published": MetaStandardEvent.VIEW_CONTENT,
    "media_uploaded": MetaStandardEvent.CUSTOMIZE_PRODUCT,
    "template_used": MetaStandardEvent.VIEW_CONTENT,
    "platform_connected": MetaStandardEvent.LEAD,
    "checkout_started": MetaStandardEvent.INITIATE_CHECKOUT,
    "purchase_completed": MetaStandardEvent.PURCHASE,
    "subscription_started": MetaStandardEvent.SUBSCRIBE,
    "trial_started": MetaStandardEvent.START_TRIAL,
    "contact_form": MetaStandardEvent.CONTACT,
    "search": MetaStandardEvent.SEARCH,
}


# ============================================================================
# META-004: CAPI Event Model
# ============================================================================

@dataclass
class CAPIEvent:
    """Conversions API event payload (META-004)."""
    event_name: str = ""
    event_time: int = field(default_factory=lambda: int(time.time()))
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_source_url: Optional[str] = None
    action_source: str = "website"  # website, app, email, phone_call, chat, etc.
    user_data: Dict[str, Any] = field(default_factory=dict)
    custom_data: Dict[str, Any] = field(default_factory=dict)
    opt_out: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_meta_payload(self) -> Dict[str, Any]:
        """Convert to Meta CAPI API format."""
        payload = {
            "event_name": self.event_name,
            "event_time": self.event_time,
            "event_id": self.event_id,
            "action_source": self.action_source,
            "user_data": self.user_data,
        }
        if self.event_source_url:
            payload["event_source_url"] = self.event_source_url
        if self.custom_data:
            payload["custom_data"] = self.custom_data
        if self.opt_out:
            payload["opt_out"] = True
        return payload


# ============================================================================
# META-007: Custom Audiences
# ============================================================================

@dataclass
class CustomAudience:
    """Custom audience definition (META-007)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    segment_rules: List[Dict[str, Any]] = field(default_factory=list)
    source_type: str = "segment"  # segment, event, lookalike
    status: str = "active"
    member_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# META-008: Conversion Optimization Config
# ============================================================================

@dataclass
class ConversionConfig:
    """Conversion optimization settings (META-008)."""
    optimization_goal: str = "PURCHASE"  # PURCHASE, LEAD, SUBSCRIBE, etc.
    value_optimization: bool = False
    attribution_window: int = 7  # days
    event_priority: List[str] = field(default_factory=lambda: [
        MetaStandardEvent.PURCHASE,
        MetaStandardEvent.SUBSCRIBE,
        MetaStandardEvent.START_TRIAL,
        MetaStandardEvent.INITIATE_CHECKOUT,
        MetaStandardEvent.LEAD,
        MetaStandardEvent.COMPLETE_REGISTRATION,
        MetaStandardEvent.PAGE_VIEW,
    ])
    dedup_window_seconds: int = 48 * 3600  # 48 hours

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Meta Pixel Service
# ============================================================================

class MetaPixelService:
    """
    Meta Pixel tracking service (META-001 through META-008).

    Provides pixel installation, event tracking, CAPI integration,
    deduplication, PII hashing, custom audiences, and conversion optimization.
    """

    _instance: Optional['MetaPixelService'] = None

    # PII fields that must be hashed before sending to Meta (META-006)
    PII_FIELDS = {"em", "ph", "fn", "ln", "ct", "st", "zp", "country", "db", "ge", "external_id"}

    def __init__(
        self,
        pixel_id: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        self.config = MetaPixelConfig(
            pixel_id=pixel_id or os.getenv("META_PIXEL_ID", ""),
            access_token=access_token or os.getenv("META_ACCESS_TOKEN", ""),
            is_installed=bool(pixel_id or os.getenv("META_PIXEL_ID")),
        )
        self.conversion_config = ConversionConfig()

        # In-memory event stores
        self._pixel_events: List[CAPIEvent] = []
        self._server_events: List[CAPIEvent] = []
        self._dedup_cache: Dict[str, str] = {}  # event_id -> source
        self._custom_audiences: Dict[str, CustomAudience] = {}

        # Stats
        self._stats = {
            "pixel_events": 0,
            "server_events": 0,
            "deduplicated": 0,
            "pii_hashed": 0,
        }

        logger.info("MetaPixelService initialized (pixel_id=%s, installed=%s)",
                     self.config.pixel_id[:6] + "..." if self.config.pixel_id else "none",
                     self.config.is_installed)

    @classmethod
    def get_instance(
        cls,
        pixel_id: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> 'MetaPixelService':
        if cls._instance is None:
            cls._instance = cls(pixel_id, access_token)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    # ------------------------------------------------------------------
    # META-001: Pixel Installation
    # ------------------------------------------------------------------

    def install_pixel(self, pixel_id: str, access_token: Optional[str] = None) -> bool:
        """Install/configure Meta Pixel (META-001)."""
        self.config.pixel_id = pixel_id
        if access_token:
            self.config.access_token = access_token
        self.config.is_installed = True
        logger.info("META-001: Pixel installed: %s", pixel_id)
        return True

    def get_pixel_init_snippet(self) -> str:
        """Generate pixel initialization JavaScript snippet (META-001)."""
        if not self.config.pixel_id:
            return ""
        return f"""<!-- Meta Pixel Code -->
<script>
!function(f,b,e,v,n,t,s){{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};if(!f._fbq)f._fbq=n;
n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}}(window,
document,'script','https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{self.config.pixel_id}');
fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id={self.config.pixel_id}&ev=PageView&noscript=1"/></noscript>
<!-- End Meta Pixel Code -->"""

    def is_installed(self) -> bool:
        """Check if pixel is installed (META-001)."""
        return self.config.is_installed and bool(self.config.pixel_id)

    # ------------------------------------------------------------------
    # META-002: PageView Tracking
    # ------------------------------------------------------------------

    def track_page_view(
        self,
        url: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> CAPIEvent:
        """Track a PageView event (META-002)."""
        return self._track_event(
            event_name=MetaStandardEvent.PAGE_VIEW,
            event_source_url=url,
            user_data=user_data,
            event_id=event_id,
        )

    # ------------------------------------------------------------------
    # META-003: Standard Events Mapping
    # ------------------------------------------------------------------

    def track_standard_event(
        self,
        event_name: str,
        value: Optional[float] = None,
        currency: Optional[str] = None,
        content_ids: Optional[List[str]] = None,
        content_type: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> CAPIEvent:
        """Track a Meta standard event (META-003)."""
        cd = custom_data or {}
        if value is not None:
            cd["value"] = value
        if currency:
            cd["currency"] = currency
        if content_ids:
            cd["content_ids"] = content_ids
        if content_type:
            cd["content_type"] = content_type

        return self._track_event(
            event_name=event_name,
            user_data=user_data,
            custom_data=cd,
            event_id=event_id,
        )

    def map_app_event(self, app_event_name: str) -> Optional[str]:
        """Map an app event name to a Meta standard event (META-003)."""
        return APP_TO_META_EVENT_MAP.get(app_event_name)

    def track_app_event(
        self,
        app_event_name: str,
        user_data: Optional[Dict[str, Any]] = None,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[CAPIEvent]:
        """Track an app event mapped to Meta standard event (META-003)."""
        meta_event = self.map_app_event(app_event_name)
        if not meta_event:
            logger.debug("META-003: No Meta mapping for app event: %s", app_event_name)
            return None
        return self.track_standard_event(
            event_name=meta_event,
            user_data=user_data,
            custom_data=custom_data,
        )

    # ------------------------------------------------------------------
    # META-004: CAPI Server-Side Events
    # ------------------------------------------------------------------

    def send_server_event(
        self,
        event_name: str,
        user_data: Optional[Dict[str, Any]] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        event_source_url: Optional[str] = None,
        action_source: str = "website",
        event_id: Optional[str] = None,
    ) -> CAPIEvent:
        """Send a server-side event via Conversions API (META-004)."""
        hashed_ud = self.hash_user_data(user_data or {})

        event = CAPIEvent(
            event_name=event_name,
            event_id=event_id or str(uuid4()),
            event_source_url=event_source_url,
            action_source=action_source,
            user_data=hashed_ud,
            custom_data=custom_data or {},
        )

        # Check dedup
        is_dedup = self._check_dedup(event.event_id, "server")
        if is_dedup:
            self._stats["deduplicated"] += 1

        self._server_events.append(event)
        self._stats["server_events"] += 1
        logger.debug("META-004: Server event sent: %s (dedup=%s)", event_name, is_dedup)
        return event

    def build_capi_payload(self, events: List[CAPIEvent]) -> Dict[str, Any]:
        """Build CAPI batch payload for sending to Meta API (META-004)."""
        return {
            "data": [e.to_meta_payload() for e in events],
            "test_event_code": self.config.test_event_code,
        }

    # ------------------------------------------------------------------
    # META-005: Event Deduplication
    # ------------------------------------------------------------------

    def _check_dedup(self, event_id: str, source: str) -> bool:
        """Check and register event for deduplication (META-005)."""
        if event_id in self._dedup_cache:
            if self._dedup_cache[event_id] != source:
                return True  # Same event_id from different source = duplicate
        self._dedup_cache[event_id] = source
        return False

    def get_dedup_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics (META-005)."""
        total = len(self._pixel_events) + len(self._server_events)
        return {
            "total_events": total,
            "pixel_events": len(self._pixel_events),
            "server_events": len(self._server_events),
            "deduplicated": self._stats["deduplicated"],
            "dedup_cache_size": len(self._dedup_cache),
            "dedup_rate": self._stats["deduplicated"] / total if total > 0 else 0,
        }

    # ------------------------------------------------------------------
    # META-006: User Data Hashing (PII)
    # ------------------------------------------------------------------

    def hash_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Hash PII fields in user data using SHA-256 (META-006)."""
        hashed = {}
        for key, value in user_data.items():
            if key in self.PII_FIELDS and isinstance(value, str) and value:
                hashed[key] = hashlib.sha256(
                    value.lower().strip().encode()
                ).hexdigest()
                self._stats["pii_hashed"] += 1
            else:
                hashed[key] = value
        return hashed

    @staticmethod
    def hash_email(email: str) -> str:
        """Hash an email address for Meta (META-006)."""
        return hashlib.sha256(email.lower().strip().encode()).hexdigest()

    @staticmethod
    def hash_phone(phone: str) -> str:
        """Hash a phone number for Meta (META-006)."""
        # Remove non-numeric chars except leading +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        return hashlib.sha256(cleaned.encode()).hexdigest()

    # ------------------------------------------------------------------
    # META-007: Custom Audiences Setup
    # ------------------------------------------------------------------

    def create_custom_audience(
        self,
        name: str,
        description: str = "",
        segment_rules: Optional[List[Dict[str, Any]]] = None,
        source_type: str = "segment",
    ) -> CustomAudience:
        """Create a custom audience definition (META-007)."""
        audience = CustomAudience(
            name=name,
            description=description,
            segment_rules=segment_rules or [],
            source_type=source_type,
        )
        self._custom_audiences[audience.id] = audience
        logger.info("META-007: Custom audience created: %s (%s)", name, audience.id)
        return audience

    def get_custom_audience(self, audience_id: str) -> Optional[CustomAudience]:
        """Get a custom audience by ID (META-007)."""
        return self._custom_audiences.get(audience_id)

    def list_custom_audiences(self) -> List[CustomAudience]:
        """List all custom audiences (META-007)."""
        return list(self._custom_audiences.values())

    def update_audience_count(self, audience_id: str, count: int) -> bool:
        """Update audience member count (META-007)."""
        audience = self._custom_audiences.get(audience_id)
        if audience:
            audience.member_count = count
            return True
        return False

    # ------------------------------------------------------------------
    # META-008: Conversion Optimization
    # ------------------------------------------------------------------

    def set_optimization_goal(self, goal: str) -> None:
        """Set conversion optimization goal (META-008)."""
        self.conversion_config.optimization_goal = goal
        logger.info("META-008: Optimization goal set to: %s", goal)

    def set_event_priority(self, events: List[str]) -> None:
        """Set event priority order for aggregated event measurement (META-008)."""
        self.conversion_config.event_priority = events

    def get_conversion_config(self) -> ConversionConfig:
        """Get current conversion optimization config (META-008)."""
        return self.conversion_config

    def get_top_conversion_events(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top conversion events by volume (META-008)."""
        event_counts: Dict[str, int] = {}
        event_values: Dict[str, float] = {}

        for event in self._pixel_events + self._server_events:
            name = event.event_name
            event_counts[name] = event_counts.get(name, 0) + 1
            value = event.custom_data.get("value", 0)
            if value:
                event_values[name] = event_values.get(name, 0) + float(value)

        result = []
        for name, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:limit]:
            priority_idx = self.conversion_config.event_priority.index(name) \
                if name in self.conversion_config.event_priority else 99
            result.append({
                "event_name": name,
                "count": count,
                "total_value": event_values.get(name, 0),
                "priority": priority_idx,
            })
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _track_event(
        self,
        event_name: str,
        event_source_url: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> CAPIEvent:
        """Internal event tracking (pixel-side)."""
        hashed_ud = self.hash_user_data(user_data or {})

        event = CAPIEvent(
            event_name=event_name,
            event_id=event_id or str(uuid4()),
            event_source_url=event_source_url,
            user_data=hashed_ud,
            custom_data=custom_data or {},
        )

        is_dedup = self._check_dedup(event.event_id, "pixel")
        if is_dedup:
            self._stats["deduplicated"] += 1

        self._pixel_events.append(event)
        self._stats["pixel_events"] += 1
        return event

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            **self._stats,
            "config": self.config.to_dict(),
            "conversion_config": self.conversion_config.to_dict(),
            "custom_audiences": len(self._custom_audiences),
            "dedup_cache_size": len(self._dedup_cache),
        }


# ============================================================================
# Module-level convenience
# ============================================================================

def get_meta_pixel_service(
    pixel_id: Optional[str] = None,
    access_token: Optional[str] = None,
) -> MetaPixelService:
    """Get the singleton MetaPixelService instance."""
    return MetaPixelService.get_instance(pixel_id, access_token)
