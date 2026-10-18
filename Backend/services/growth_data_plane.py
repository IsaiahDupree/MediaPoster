"""
Growth Data Plane Service (GDP-001 through GDP-012)
====================================================
Unified event tracking and person identity management for MediaPoster.

Provides:
    - Person & identity link management (GDP-002)
    - Unified event tracking from web/app/email/stripe sources (GDP-003)
    - Resend webhook processing (GDP-004)
    - Email event tracking (GDP-005)
    - Click redirect tracking (GDP-006)
    - Stripe webhook integration (GDP-007)
    - Subscription snapshot management (GDP-008)
    - PostHog identity stitching (GDP-009)
    - Meta Pixel + CAPI deduplication (GDP-010)
    - Person features computation (GDP-011)
    - Segment computation based on event history (GDP-012)
    - Integration with EventBus for real-time processing

Schema (GDP-001):
    - gdp_persons: Canonical person table
    - gdp_identity_links: Identity stitching (posthog, stripe, meta, email)
    - gdp_events: Normalized events from all sources
    - gdp_person_features: Computed features per person
    - gdp_segments: Dynamic segment membership

Usage:
    from services.growth_data_plane import GrowthDataPlane, get_growth_data_plane

    gdp = get_growth_data_plane()
    person_id = await gdp.upsert_person(email="user@example.com", name="Jane")
    await gdp.track_event(person_id, "post_published", {"platform": "tiktok"})
    await gdp.link_identity(person_id, "stripe", "cus_abc123")
"""

import hashlib
import hmac
import logging
import os
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs
from uuid import uuid4

from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)


# ============================================================================
# Enums & Constants
# ============================================================================

class IdentityProvider(str, Enum):
    """Supported identity providers for identity stitching."""
    EMAIL = "email"
    POSTHOG = "posthog"
    STRIPE = "stripe"
    META = "meta"
    GOOGLE = "google"
    BLOTATO = "blotato"
    SAFARI_SESSION = "safari_session"


class EventSource(str, Enum):
    """Event source categories."""
    WEB = "web"
    APP = "app"
    EMAIL = "email"
    STRIPE = "stripe"
    BOOKING = "booking"
    META = "meta"
    SYSTEM = "system"


class SegmentTrigger(str, Enum):
    """Segment triggers based on events."""
    WARM_LEAD = "warm_lead"
    NEW_SIGNUP = "new_signup"
    ACTIVATED = "activated"
    FIRST_ACTION = "first_action"
    FIRST_VALUE = "first_value"
    POWER_USER = "power_user"
    AHA_MOMENT = "aha_moment"
    CHECKOUT_STARTED = "checkout_started"
    MONETIZED = "monetized"
    NEWSLETTER_CLICKER = "newsletter_clicker"


# Event → Segment trigger mapping
EVENT_SEGMENT_MAP: Dict[str, Optional[str]] = {
    "landing_view": None,
    "demo_requested": SegmentTrigger.WARM_LEAD,
    "signup_completed": SegmentTrigger.NEW_SIGNUP,
    "first_platform_connected": SegmentTrigger.ACTIVATED,
    "post_created": SegmentTrigger.FIRST_ACTION,
    "post_scheduled": None,
    "post_published": SegmentTrigger.FIRST_VALUE,
    "video_generated": None,
    "trend_discovered": SegmentTrigger.POWER_USER,
    "auto_engagement_enabled": SegmentTrigger.AHA_MOMENT,
    "checkout_started": SegmentTrigger.CHECKOUT_STARTED,
    "subscription_started": SegmentTrigger.MONETIZED,
    "email.clicked": SegmentTrigger.NEWSLETTER_CLICKER,
    "dm_sent": None,
    "dm_auto_replied": None,
}


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Person:
    """Canonical person record (GDP-002)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    email: Optional[str] = None
    name: Optional[str] = None
    first_seen_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    properties: Dict[str, Any] = field(default_factory=dict)
    segments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IdentityLink:
    """Identity link for cross-system stitching (GDP-002)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    person_id: str = ""
    provider: str = ""  # IdentityProvider value
    external_id: str = ""
    linked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GDPEvent:
    """Unified event record (GDP-003)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    person_id: str = ""
    event_name: str = ""
    source: str = EventSource.APP  # EventSource value
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: Optional[str] = None
    segment_trigger: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PersonFeatures:
    """Computed features per person (GDP-011)."""
    person_id: str = ""
    total_events: int = 0
    first_event_at: Optional[str] = None
    last_event_at: Optional[str] = None
    platforms_connected: int = 0
    posts_published: int = 0
    is_activated: bool = False
    is_monetized: bool = False
    current_segments: List[str] = field(default_factory=list)
    computed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# GDP-004 to GDP-010 Data Models
# ============================================================================

class ResendEventType(str, Enum):
    """Resend webhook event types (GDP-004)."""
    EMAIL_SENT = "email.sent"
    EMAIL_DELIVERED = "email.delivered"
    EMAIL_OPENED = "email.opened"
    EMAIL_CLICKED = "email.clicked"
    EMAIL_BOUNCED = "email.bounced"
    EMAIL_COMPLAINED = "email.complained"


class StripeEventType(str, Enum):
    """Stripe webhook event types (GDP-007)."""
    CHECKOUT_COMPLETED = "checkout.session.completed"
    SUBSCRIPTION_CREATED = "customer.subscription.created"
    SUBSCRIPTION_UPDATED = "customer.subscription.updated"
    SUBSCRIPTION_DELETED = "customer.subscription.deleted"
    INVOICE_PAID = "invoice.paid"
    INVOICE_FAILED = "invoice.payment_failed"
    CHARGE_SUCCEEDED = "charge.succeeded"
    CHARGE_REFUNDED = "charge.refunded"


class SubscriptionStatus(str, Enum):
    """Subscription status values (GDP-008)."""
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"


@dataclass
class EmailEvent:
    """Email event record (GDP-005)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    person_id: Optional[str] = None
    email_address: str = ""
    event_type: str = ""  # ResendEventType value
    message_id: Optional[str] = None
    subject: Optional[str] = None
    link_url: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClickEvent:
    """Click redirect tracking record (GDP-006)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    person_id: Optional[str] = None
    click_id: str = field(default_factory=lambda: str(uuid4()))
    original_url: str = ""
    redirect_url: str = ""
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SubscriptionSnapshot:
    """Subscription state snapshot (GDP-008)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    person_id: str = ""
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    plan_id: Optional[str] = None
    plan_name: Optional[str] = None
    status: str = SubscriptionStatus.ACTIVE
    amount_cents: int = 0
    currency: str = "usd"
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetaPixelEvent:
    """Meta Pixel + CAPI event record (GDP-010)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    event_id: str = field(default_factory=lambda: str(uuid4()))  # For deduplication
    person_id: Optional[str] = None
    pixel_id: Optional[str] = None
    event_name: str = ""  # PageView, Purchase, Lead, etc.
    event_source: str = "website"  # website or server
    action_source: str = "website"  # Meta CAPI action_source
    event_source_url: Optional[str] = None
    user_data: Dict[str, Any] = field(default_factory=dict)  # hashed PII
    custom_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_deduplicated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# SQL Schema Definitions (GDP-001)
# ============================================================================

GDP_SCHEMA_SQL = """
-- Growth Data Plane Schema (GDP-001)
-- Creates tables for person tracking, identity stitching, and unified events.

CREATE TABLE IF NOT EXISTS gdp_persons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    name TEXT,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    properties JSONB DEFAULT '{}',
    segments TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gdp_identity_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES gdp_persons(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    linked_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(provider, external_id)
);

CREATE TABLE IF NOT EXISTS gdp_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES gdp_persons(id) ON DELETE CASCADE,
    event_name TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'app',
    properties JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    session_id TEXT,
    segment_trigger TEXT
);

CREATE TABLE IF NOT EXISTS gdp_person_features (
    person_id UUID PRIMARY KEY REFERENCES gdp_persons(id) ON DELETE CASCADE,
    total_events INTEGER DEFAULT 0,
    first_event_at TIMESTAMPTZ,
    last_event_at TIMESTAMPTZ,
    platforms_connected INTEGER DEFAULT 0,
    posts_published INTEGER DEFAULT 0,
    is_activated BOOLEAN DEFAULT FALSE,
    is_monetized BOOLEAN DEFAULT FALSE,
    current_segments TEXT[] DEFAULT '{}',
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gdp_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES gdp_persons(id) ON DELETE CASCADE,
    segment_name TEXT NOT NULL,
    entered_at TIMESTAMPTZ DEFAULT NOW(),
    exited_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(person_id, segment_name, entered_at)
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_gdp_events_person_id ON gdp_events(person_id);
CREATE INDEX IF NOT EXISTS idx_gdp_events_event_name ON gdp_events(event_name);
CREATE INDEX IF NOT EXISTS idx_gdp_events_timestamp ON gdp_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gdp_events_source ON gdp_events(source);
CREATE INDEX IF NOT EXISTS idx_gdp_identity_links_person ON gdp_identity_links(person_id);
CREATE INDEX IF NOT EXISTS idx_gdp_identity_links_provider ON gdp_identity_links(provider, external_id);
CREATE INDEX IF NOT EXISTS idx_gdp_segments_person ON gdp_segments(person_id);
CREATE INDEX IF NOT EXISTS idx_gdp_segments_active ON gdp_segments(segment_name) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_gdp_persons_email ON gdp_persons(email);
"""


# ============================================================================
# Growth Data Plane Service
# ============================================================================

class GrowthDataPlane:
    """
    Growth Data Plane service (GDP-001, GDP-002, GDP-003).

    Manages person identity, event tracking, and segment computation
    with database persistence and EventBus integration.
    """

    _instance: Optional['GrowthDataPlane'] = None

    def __init__(self, event_bus: Optional[EventBus] = None, use_db: bool = True):
        self.event_bus = event_bus or EventBus.get_instance()
        self.use_db = use_db
        self._db_engine = None

        # In-memory stores (for dev/testing or when DB is unavailable)
        self._persons: Dict[str, Person] = {}
        self._identity_links: Dict[str, List[IdentityLink]] = {}  # person_id -> links
        self._events: List[GDPEvent] = []
        self._person_features: Dict[str, PersonFeatures] = {}
        # GDP-004/005: Email events
        self._email_events: List[EmailEvent] = []
        # GDP-006: Click tracking
        self._click_events: Dict[str, ClickEvent] = {}  # click_id -> ClickEvent
        # GDP-008: Subscription snapshots
        self._subscriptions: Dict[str, SubscriptionSnapshot] = {}  # person_id -> snapshot
        # GDP-010: Meta Pixel events
        self._meta_pixel_events: List[MetaPixelEvent] = []

        if use_db:
            self._init_db()

        self._setup_subscriptions()
        logger.info("Growth Data Plane initialized (db_mode=%s)", use_db)

    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None, use_db: bool = True) -> 'GrowthDataPlane':
        if cls._instance is None:
            cls._instance = cls(event_bus, use_db)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def _init_db(self) -> None:
        """Initialize database connection."""
        try:
            from sqlalchemy import create_engine
            DATABASE_URL = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres@localhost:54322/postgres"
            )
            self._db_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            logger.info("GDP: Database connection initialized")
        except Exception as e:
            logger.warning("GDP: Database init failed: %s, using in-memory mode", e)
            self.use_db = False
            self._db_engine = None

    def _setup_subscriptions(self) -> None:
        """Subscribe to relevant EventBus topics for auto-tracking."""
        self.event_bus.subscribe(Topics.POST_PUBLISHED, self._on_post_published)
        self.event_bus.subscribe(Topics.ACCOUNT_CONNECTED, self._on_platform_connected)
        self.event_bus.subscribe(Topics.PUBLISH_COMPLETED, self._on_publish_completed)
        logger.info("GDP: Subscribed to EventBus topics")

    # ------------------------------------------------------------------
    # Person Management (GDP-002)
    # ------------------------------------------------------------------

    async def upsert_person(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        person_id: Optional[str] = None,
    ) -> str:
        """
        Create or update a person record.

        If email matches an existing person, updates their record.
        Otherwise creates a new person.

        Returns:
            person_id (str)
        """
        now = datetime.now(timezone.utc).isoformat()

        # Check for existing person by email
        if email:
            existing = self._find_person_by_email(email)
            if existing:
                # Update
                if name:
                    existing.name = name
                existing.last_seen_at = now
                if properties:
                    existing.properties.update(properties)
                await self._db_upsert_person(existing)
                return existing.id

        # Create new person
        pid = person_id or str(uuid4())
        person = Person(
            id=pid,
            email=email,
            name=name,
            first_seen_at=now,
            last_seen_at=now,
            properties=properties or {},
        )
        self._persons[pid] = person
        await self._db_upsert_person(person)
        logger.info("GDP: Person created: %s (%s)", pid, email or "no email")
        return pid

    def get_person(self, person_id: str) -> Optional[Person]:
        """Get person by ID."""
        return self._persons.get(person_id)

    def _find_person_by_email(self, email: str) -> Optional[Person]:
        """Find person by email in memory store."""
        for p in self._persons.values():
            if p.email == email:
                return p
        return None

    def get_person_by_email(self, email: str) -> Optional[Person]:
        """Public interface to find person by email."""
        return self._find_person_by_email(email)

    # ------------------------------------------------------------------
    # Identity Linking (GDP-002)
    # ------------------------------------------------------------------

    async def link_identity(
        self,
        person_id: str,
        provider: str,
        external_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Link an external identity to a person.

        Args:
            person_id: Internal person ID
            provider: Identity provider (e.g., "stripe", "posthog")
            external_id: External system identifier
            metadata: Optional extra data about the link

        Returns:
            link_id (str)
        """
        link = IdentityLink(
            person_id=person_id,
            provider=provider,
            external_id=external_id,
            metadata=metadata or {},
        )

        if person_id not in self._identity_links:
            self._identity_links[person_id] = []

        # Prevent duplicate links
        for existing in self._identity_links[person_id]:
            if existing.provider == provider and existing.external_id == external_id:
                return existing.id

        self._identity_links[person_id].append(link)
        await self._db_save_identity_link(link)
        logger.info("GDP: Identity linked: %s -> %s:%s", person_id, provider, external_id)
        return link.id

    def get_identity_links(self, person_id: str) -> List[IdentityLink]:
        """Get all identity links for a person."""
        return self._identity_links.get(person_id, [])

    def resolve_person_by_identity(self, provider: str, external_id: str) -> Optional[str]:
        """Find person_id from external identity."""
        for pid, links in self._identity_links.items():
            for link in links:
                if link.provider == provider and link.external_id == external_id:
                    return pid
        return None

    # ------------------------------------------------------------------
    # Event Tracking (GDP-003)
    # ------------------------------------------------------------------

    async def track_event(
        self,
        person_id: str,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
        source: str = EventSource.APP,
        session_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """
        Track a unified event for a person.

        Automatically triggers segment evaluation if the event has a segment trigger.

        Args:
            person_id: Person who performed the action
            event_name: Event name (e.g., "post_published")
            properties: Event-specific data
            source: Event source (web, app, email, stripe, etc.)
            session_id: Optional session identifier
            timestamp: Optional custom timestamp

        Returns:
            event_id (str)
        """
        segment_trigger = EVENT_SEGMENT_MAP.get(event_name)

        event = GDPEvent(
            person_id=person_id,
            event_name=event_name,
            source=source,
            properties=properties or {},
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            segment_trigger=segment_trigger,
        )

        self._events.append(event)
        await self._db_save_event(event)

        # Update person last_seen_at
        person = self._persons.get(person_id)
        if person:
            person.last_seen_at = event.timestamp

        # Auto-add to segment if triggered
        if segment_trigger:
            await self._add_to_segment(person_id, segment_trigger)

        logger.debug("GDP: Event tracked: %s -> %s (trigger=%s)", person_id, event_name, segment_trigger)
        return event.id

    def get_events(
        self,
        person_id: Optional[str] = None,
        event_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[GDPEvent]:
        """Query events with optional filters."""
        events = self._events
        if person_id:
            events = [e for e in events if e.person_id == person_id]
        if event_name:
            events = [e for e in events if e.event_name == event_name]
        # Sort by timestamp descending
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def get_event_count(self, person_id: str) -> int:
        """Get total event count for a person."""
        return sum(1 for e in self._events if e.person_id == person_id)

    # ------------------------------------------------------------------
    # Segment Management
    # ------------------------------------------------------------------

    async def _add_to_segment(self, person_id: str, segment_name: str) -> None:
        """Add person to a segment."""
        person = self._persons.get(person_id)
        if person and segment_name not in person.segments:
            person.segments.append(segment_name)
            logger.info("GDP: Person %s entered segment '%s'", person_id, segment_name)

    def get_persons_in_segment(self, segment_name: str) -> List[Person]:
        """Get all persons in a segment."""
        return [p for p in self._persons.values() if segment_name in p.segments]

    def get_person_segments(self, person_id: str) -> List[str]:
        """Get all segments a person belongs to."""
        person = self._persons.get(person_id)
        return person.segments if person else []

    # ------------------------------------------------------------------
    # Person Features (GDP-011)
    # ------------------------------------------------------------------

    async def compute_person_features(self, person_id: str) -> PersonFeatures:
        """Compute features for a person based on their event history."""
        events = self.get_events(person_id=person_id, limit=10000)
        person = self._persons.get(person_id)

        features = PersonFeatures(
            person_id=person_id,
            total_events=len(events),
            first_event_at=events[-1].timestamp if events else None,
            last_event_at=events[0].timestamp if events else None,
            platforms_connected=sum(1 for e in events if e.event_name == "first_platform_connected"),
            posts_published=sum(1 for e in events if e.event_name == "post_published"),
            is_activated=any(e.event_name == "first_platform_connected" for e in events),
            is_monetized=any(e.event_name == "subscription_started" for e in events),
            current_segments=person.segments if person else [],
        )

        self._person_features[person_id] = features
        return features

    def get_person_features(self, person_id: str) -> Optional[PersonFeatures]:
        """Get cached features for a person."""
        return self._person_features.get(person_id)

    # ------------------------------------------------------------------
    # Resend Webhook Processing (GDP-004)
    # ------------------------------------------------------------------

    async def process_resend_webhook(
        self,
        webhook_payload: Dict[str, Any],
        webhook_secret: Optional[str] = None,
        signature: Optional[str] = None,
    ) -> Optional[str]:
        """
        Process a Resend webhook event (GDP-004).

        Validates the webhook signature, extracts email event data,
        resolves the person by email, and tracks the event.

        Args:
            webhook_payload: Raw webhook JSON payload from Resend
            webhook_secret: Webhook signing secret for verification
            signature: Request signature header value

        Returns:
            event_id if processed, None if invalid
        """
        # Validate signature if secret provided
        if webhook_secret and signature:
            if not self._verify_resend_signature(webhook_payload, webhook_secret, signature):
                logger.warning("GDP-004: Invalid Resend webhook signature")
                return None

        event_type = webhook_payload.get("type", "")
        data = webhook_payload.get("data", {})
        email_address = data.get("to", [None])[0] if isinstance(data.get("to"), list) else data.get("to")

        if not event_type or not email_address:
            logger.warning("GDP-004: Missing event_type or email in webhook")
            return None

        # Resolve person by email
        person = self._find_person_by_email(email_address)
        person_id = person.id if person else None

        # Create email event
        email_event = EmailEvent(
            person_id=person_id,
            email_address=email_address,
            event_type=event_type,
            message_id=data.get("email_id"),
            subject=data.get("subject"),
            link_url=data.get("click", {}).get("link") if isinstance(data.get("click"), dict) else None,
            metadata={"raw_type": event_type, "created_at": data.get("created_at")},
        )
        self._email_events.append(email_event)

        # Track as GDP event if person found
        if person_id:
            event_id = await self.track_event(
                person_id=person_id,
                event_name=event_type,
                properties={
                    "email": email_address,
                    "message_id": email_event.message_id,
                    "subject": email_event.subject,
                    "link_url": email_event.link_url,
                },
                source=EventSource.EMAIL,
            )
            logger.info("GDP-004: Processed Resend webhook: %s for %s", event_type, email_address)
            return event_id

        logger.info("GDP-004: Resend webhook processed (no person match): %s", email_address)
        return email_event.id

    def _verify_resend_signature(
        self,
        payload: Dict[str, Any],
        secret: str,
        signature: str,
    ) -> bool:
        """Verify Resend webhook HMAC signature."""
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode()
        expected = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    # ------------------------------------------------------------------
    # Email Event Tracking (GDP-005)
    # ------------------------------------------------------------------

    async def track_email_event(
        self,
        email_address: str,
        event_type: str,
        message_id: Optional[str] = None,
        subject: Optional[str] = None,
        link_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Track an email event (GDP-005).

        Args:
            email_address: Recipient email
            event_type: Email event type (sent, delivered, opened, clicked, etc.)
            message_id: Email message ID
            subject: Email subject
            link_url: Clicked link URL (for click events)
            metadata: Additional metadata

        Returns:
            email_event_id
        """
        person = self._find_person_by_email(email_address)

        email_event = EmailEvent(
            person_id=person.id if person else None,
            email_address=email_address,
            event_type=event_type,
            message_id=message_id,
            subject=subject,
            link_url=link_url,
            metadata=metadata or {},
        )
        self._email_events.append(email_event)

        # Track as GDP event if person exists
        if person:
            await self.track_event(
                person_id=person.id,
                event_name=event_type,
                properties={
                    "email": email_address,
                    "message_id": message_id,
                    "subject": subject,
                    "link_url": link_url,
                },
                source=EventSource.EMAIL,
            )

        logger.debug("GDP-005: Email event tracked: %s -> %s", email_address, event_type)
        return email_event.id

    def get_email_events(
        self,
        email_address: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[EmailEvent]:
        """Query email events with optional filters."""
        events = self._email_events
        if email_address:
            events = [e for e in events if e.email_address == email_address]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def get_email_stats(self, email_address: Optional[str] = None) -> Dict[str, int]:
        """Get email event counts by type."""
        events = self._email_events
        if email_address:
            events = [e for e in events if e.email_address == email_address]
        counts: Dict[str, int] = {}
        for e in events:
            counts[e.event_type] = counts.get(e.event_type, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Click Redirect Tracker (GDP-006)
    # ------------------------------------------------------------------

    async def create_tracked_link(
        self,
        original_url: str,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        utm_content: Optional[str] = None,
        person_id: Optional[str] = None,
    ) -> ClickEvent:
        """
        Create a tracked redirect link (GDP-006).

        Generates a click tracking record with UTM parameters
        that can be used as a redirect URL.

        Returns:
            ClickEvent with click_id for building redirect URL
        """
        click = ClickEvent(
            person_id=person_id,
            original_url=original_url,
            redirect_url=original_url,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
        )

        # Build UTM-tagged URL
        params = {}
        if utm_source:
            params["utm_source"] = utm_source
        if utm_medium:
            params["utm_medium"] = utm_medium
        if utm_campaign:
            params["utm_campaign"] = utm_campaign
        if utm_content:
            params["utm_content"] = utm_content

        if params:
            separator = "&" if "?" in original_url else "?"
            click.redirect_url = f"{original_url}{separator}{urlencode(params)}"

        self._click_events[click.click_id] = click
        logger.debug("GDP-006: Tracked link created: %s -> %s", click.click_id, original_url)
        return click

    async def record_click(
        self,
        click_id: str,
        referrer: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[ClickEvent]:
        """
        Record a click on a tracked link (GDP-006).

        Args:
            click_id: Click tracking ID
            referrer: HTTP Referer header
            user_agent: Browser user agent
            ip_address: Client IP (for geo)

        Returns:
            ClickEvent with recorded metadata, or None if not found
        """
        click = self._click_events.get(click_id)
        if not click:
            logger.warning("GDP-006: Click ID not found: %s", click_id)
            return None

        click.referrer = referrer
        click.user_agent = user_agent
        click.ip_address = ip_address
        click.timestamp = datetime.now(timezone.utc).isoformat()

        # Track as GDP event if person identified
        if click.person_id:
            await self.track_event(
                person_id=click.person_id,
                event_name="link.clicked",
                properties={
                    "click_id": click_id,
                    "url": click.original_url,
                    "utm_source": click.utm_source,
                    "utm_campaign": click.utm_campaign,
                },
                source=EventSource.WEB,
            )

        logger.debug("GDP-006: Click recorded: %s", click_id)
        return click

    def get_click_events(
        self,
        person_id: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        limit: int = 50,
    ) -> List[ClickEvent]:
        """Query click events with filters."""
        clicks = list(self._click_events.values())
        if person_id:
            clicks = [c for c in clicks if c.person_id == person_id]
        if utm_campaign:
            clicks = [c for c in clicks if c.utm_campaign == utm_campaign]
        clicks = sorted(clicks, key=lambda c: c.timestamp, reverse=True)
        return clicks[:limit]

    # ------------------------------------------------------------------
    # Stripe Webhook Integration (GDP-007)
    # ------------------------------------------------------------------

    async def process_stripe_webhook(
        self,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> Optional[str]:
        """
        Process a Stripe webhook event (GDP-007).

        Handles checkout.session.completed, subscription lifecycle,
        invoice payments, and charge events.

        Args:
            event_type: Stripe event type string
            event_data: Stripe event object data

        Returns:
            person_id if resolved, None otherwise
        """
        obj = event_data.get("object", {})
        customer_email = obj.get("customer_email") or obj.get("receipt_email") or obj.get("email")
        customer_id = obj.get("customer")

        # Resolve person by email or Stripe identity
        person_id = None
        if customer_id:
            person_id = self.resolve_person_by_identity(IdentityProvider.STRIPE, customer_id)
        if not person_id and customer_email:
            person = self._find_person_by_email(customer_email)
            if person:
                person_id = person.id
                # Auto-link Stripe identity
                if customer_id:
                    await self.link_identity(person_id, IdentityProvider.STRIPE, customer_id)

        if not person_id:
            logger.info("GDP-007: Stripe event %s - no person match (email=%s)", event_type, customer_email)
            return None

        # Map Stripe events to GDP events
        event_map = {
            StripeEventType.CHECKOUT_COMPLETED: "checkout_started",
            StripeEventType.SUBSCRIPTION_CREATED: "subscription_started",
            StripeEventType.SUBSCRIPTION_UPDATED: "subscription_updated",
            StripeEventType.SUBSCRIPTION_DELETED: "subscription_canceled",
            StripeEventType.INVOICE_PAID: "invoice_paid",
            StripeEventType.INVOICE_FAILED: "invoice_failed",
            StripeEventType.CHARGE_SUCCEEDED: "charge_succeeded",
            StripeEventType.CHARGE_REFUNDED: "charge_refunded",
        }
        gdp_event_name = event_map.get(event_type, f"stripe.{event_type}")

        # Track event
        await self.track_event(
            person_id=person_id,
            event_name=gdp_event_name,
            properties={
                "stripe_event_type": event_type,
                "customer_id": customer_id,
                "amount": obj.get("amount_total") or obj.get("amount"),
                "currency": obj.get("currency"),
                "subscription_id": obj.get("subscription") or obj.get("id"),
            },
            source=EventSource.STRIPE,
        )

        # Update subscription snapshot for subscription events
        if event_type in (
            StripeEventType.SUBSCRIPTION_CREATED,
            StripeEventType.SUBSCRIPTION_UPDATED,
            StripeEventType.SUBSCRIPTION_DELETED,
        ):
            await self._update_subscription_snapshot(person_id, obj, event_type)

        logger.info("GDP-007: Stripe event processed: %s -> %s", event_type, gdp_event_name)
        return person_id

    # ------------------------------------------------------------------
    # Subscription Snapshot (GDP-008)
    # ------------------------------------------------------------------

    async def _update_subscription_snapshot(
        self,
        person_id: str,
        stripe_obj: Dict[str, Any],
        event_type: str,
    ) -> SubscriptionSnapshot:
        """Update subscription snapshot from Stripe data (GDP-008)."""
        sub_id = stripe_obj.get("id", "")
        now = datetime.now(timezone.utc).isoformat()

        status = stripe_obj.get("status", SubscriptionStatus.ACTIVE)
        if event_type == StripeEventType.SUBSCRIPTION_DELETED:
            status = SubscriptionStatus.CANCELED

        snapshot = SubscriptionSnapshot(
            person_id=person_id,
            stripe_customer_id=stripe_obj.get("customer"),
            stripe_subscription_id=sub_id,
            plan_id=stripe_obj.get("plan", {}).get("id") if isinstance(stripe_obj.get("plan"), dict) else None,
            plan_name=stripe_obj.get("plan", {}).get("nickname") if isinstance(stripe_obj.get("plan"), dict) else None,
            status=status,
            amount_cents=stripe_obj.get("plan", {}).get("amount", 0) if isinstance(stripe_obj.get("plan"), dict) else 0,
            currency=stripe_obj.get("currency", "usd"),
            current_period_start=stripe_obj.get("current_period_start"),
            current_period_end=stripe_obj.get("current_period_end"),
            cancel_at_period_end=stripe_obj.get("cancel_at_period_end", False),
            updated_at=now,
        )
        self._subscriptions[person_id] = snapshot
        logger.info("GDP-008: Subscription snapshot updated for %s: %s", person_id, status)
        return snapshot

    def get_subscription(self, person_id: str) -> Optional[SubscriptionSnapshot]:
        """Get current subscription snapshot for a person (GDP-008)."""
        return self._subscriptions.get(person_id)

    def get_active_subscribers(self) -> List[SubscriptionSnapshot]:
        """Get all active subscriptions (GDP-008)."""
        return [
            s for s in self._subscriptions.values()
            if s.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)
        ]

    # ------------------------------------------------------------------
    # PostHog Identity Stitching (GDP-009)
    # ------------------------------------------------------------------

    async def stitch_posthog_identity(
        self,
        distinct_id: str,
        email: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Stitch a PostHog distinct_id to a GDP person (GDP-009).

        If the person exists (by email), links the PostHog identity.
        Otherwise creates a new person and links.

        Args:
            distinct_id: PostHog distinct_id (anonymous or identified)
            email: User's email (for person resolution)
            properties: Additional PostHog user properties

        Returns:
            person_id
        """
        # Check if already linked
        existing_pid = self.resolve_person_by_identity(IdentityProvider.POSTHOG, distinct_id)
        if existing_pid:
            # Update properties if provided
            person = self.get_person(existing_pid)
            if person and properties:
                person.properties.update(properties)
                person.last_seen_at = datetime.now(timezone.utc).isoformat()
            return existing_pid

        # Resolve by email or create new person
        person_id = await self.upsert_person(
            email=email,
            properties=properties or {},
        )

        # Link PostHog identity
        await self.link_identity(
            person_id=person_id,
            provider=IdentityProvider.POSTHOG,
            external_id=distinct_id,
            metadata={"source": "posthog", "properties": properties or {}},
        )

        logger.info("GDP-009: PostHog identity stitched: %s -> %s", distinct_id, person_id)
        return person_id

    async def process_posthog_event(
        self,
        distinct_id: str,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> Optional[str]:
        """
        Process a PostHog event and track it in GDP (GDP-009).

        Args:
            distinct_id: PostHog distinct_id
            event_name: PostHog event name (e.g., "$pageview")
            properties: Event properties
            timestamp: Event timestamp

        Returns:
            event_id if person found, None otherwise
        """
        person_id = self.resolve_person_by_identity(IdentityProvider.POSTHOG, distinct_id)
        if not person_id:
            logger.debug("GDP-009: No person for PostHog distinct_id: %s", distinct_id)
            return None

        # Normalize PostHog event names
        normalized_name = event_name.lstrip("$").replace(" ", "_").lower()

        event_id = await self.track_event(
            person_id=person_id,
            event_name=f"posthog.{normalized_name}",
            properties={
                "posthog_distinct_id": distinct_id,
                "original_event": event_name,
                **(properties or {}),
            },
            source=EventSource.WEB,
            timestamp=timestamp,
        )
        return event_id

    # ------------------------------------------------------------------
    # Meta Pixel + CAPI Deduplication (GDP-010)
    # ------------------------------------------------------------------

    async def track_meta_pixel_event(
        self,
        event_name: str,
        pixel_id: Optional[str] = None,
        event_source: str = "website",
        event_source_url: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        person_id: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> MetaPixelEvent:
        """
        Track a Meta Pixel or CAPI event with deduplication (GDP-010).

        Uses event_id for deduplication between browser pixel and server CAPI.

        Args:
            event_name: Meta event name (PageView, Purchase, Lead, etc.)
            pixel_id: Meta Pixel ID
            event_source: "website" (pixel) or "server" (CAPI)
            event_source_url: Page URL where event occurred
            user_data: User data (will be hashed for PII protection)
            custom_data: Custom event data (value, currency, content_ids, etc.)
            person_id: GDP person ID
            event_id: Deduplication event ID (same ID from pixel + CAPI = deduplicated)

        Returns:
            MetaPixelEvent record
        """
        dedup_id = event_id or str(uuid4())

        # Check for deduplication
        is_deduplicated = False
        for existing in self._meta_pixel_events:
            if existing.event_id == dedup_id and existing.event_source != event_source:
                is_deduplicated = True
                existing.is_deduplicated = True
                logger.info("GDP-010: Meta event deduplicated: %s (%s)", dedup_id, event_name)
                break

        # Hash PII data for privacy
        hashed_user_data = self._hash_user_data(user_data or {})

        pixel_event = MetaPixelEvent(
            event_id=dedup_id,
            person_id=person_id,
            pixel_id=pixel_id or os.getenv("META_PIXEL_ID", ""),
            event_name=event_name,
            event_source=event_source,
            action_source=event_source,
            event_source_url=event_source_url,
            user_data=hashed_user_data,
            custom_data=custom_data or {},
            is_deduplicated=is_deduplicated,
        )
        self._meta_pixel_events.append(pixel_event)

        # Track as GDP event if person identified
        if person_id:
            await self.track_event(
                person_id=person_id,
                event_name=f"meta.{event_name.lower()}",
                properties={
                    "pixel_id": pixel_event.pixel_id,
                    "event_source": event_source,
                    "is_deduplicated": is_deduplicated,
                    **(custom_data or {}),
                },
                source=EventSource.META,
            )

        logger.debug("GDP-010: Meta pixel event tracked: %s (%s, dedup=%s)", event_name, event_source, is_deduplicated)
        return pixel_event

    def _hash_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Hash PII fields in user data for Meta CAPI (GDP-010)."""
        pii_fields = {"em", "ph", "fn", "ln", "ct", "st", "zp", "country", "db", "ge"}
        hashed = {}
        for key, value in user_data.items():
            if key in pii_fields and isinstance(value, str) and value:
                hashed[key] = hashlib.sha256(value.lower().strip().encode()).hexdigest()
            else:
                hashed[key] = value
        return hashed

    def get_meta_pixel_events(
        self,
        event_name: Optional[str] = None,
        deduplicated_only: bool = False,
        limit: int = 50,
    ) -> List[MetaPixelEvent]:
        """Query Meta pixel events with filters (GDP-010)."""
        events = self._meta_pixel_events
        if event_name:
            events = [e for e in events if e.event_name == event_name]
        if deduplicated_only:
            events = [e for e in events if e.is_deduplicated]
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def get_meta_dedup_stats(self) -> Dict[str, Any]:
        """Get Meta Pixel deduplication statistics (GDP-010)."""
        total = len(self._meta_pixel_events)
        deduplicated = sum(1 for e in self._meta_pixel_events if e.is_deduplicated)
        by_source = {}
        for e in self._meta_pixel_events:
            by_source[e.event_source] = by_source.get(e.event_source, 0) + 1
        return {
            "total_events": total,
            "deduplicated": deduplicated,
            "dedup_rate": deduplicated / total if total > 0 else 0,
            "by_source": by_source,
        }

    # ------------------------------------------------------------------
    # Schema Management (GDP-001)
    # ------------------------------------------------------------------

    def get_schema_sql(self) -> str:
        """Return the SQL schema for Growth Data Plane tables."""
        return GDP_SCHEMA_SQL

    async def ensure_schema(self) -> bool:
        """Create GDP tables if they don't exist."""
        if not self.use_db or not self._db_engine:
            logger.info("GDP: Skipping schema creation (no database)")
            return False

        try:
            from sqlalchemy import text

            with self._db_engine.connect() as conn:
                conn.execute(text(GDP_SCHEMA_SQL))
                conn.commit()
            logger.info("GDP: Schema created/verified successfully")
            return True
        except Exception as e:
            logger.error("GDP: Schema creation failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Stats / Dashboard
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get Growth Data Plane statistics."""
        return {
            "total_persons": len(self._persons),
            "total_events": len(self._events),
            "total_identity_links": sum(len(links) for links in self._identity_links.values()),
            "total_email_events": len(self._email_events),
            "total_click_events": len(self._click_events),
            "total_subscriptions": len(self._subscriptions),
            "active_subscriptions": len(self.get_active_subscribers()),
            "total_meta_pixel_events": len(self._meta_pixel_events),
            "meta_dedup_stats": self.get_meta_dedup_stats() if self._meta_pixel_events else {},
            "segments": self._get_segment_counts(),
            "event_sources": self._get_event_source_counts(),
        }

    def _get_segment_counts(self) -> Dict[str, int]:
        """Count persons per segment."""
        counts: Dict[str, int] = {}
        for person in self._persons.values():
            for seg in person.segments:
                counts[seg] = counts.get(seg, 0) + 1
        return counts

    def _get_event_source_counts(self) -> Dict[str, int]:
        """Count events per source."""
        counts: Dict[str, int] = {}
        for event in self._events:
            counts[event.source] = counts.get(event.source, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # EventBus Handlers
    # ------------------------------------------------------------------

    async def _on_post_published(self, event) -> None:
        """Handle post.published events."""
        payload = event.payload if hasattr(event, 'payload') else {}
        person_id = payload.get("person_id") or payload.get("user_id")
        if person_id and person_id in self._persons:
            await self.track_event(person_id, "post_published", payload, EventSource.APP)

    async def _on_platform_connected(self, event) -> None:
        """Handle account.connected events."""
        payload = event.payload if hasattr(event, 'payload') else {}
        person_id = payload.get("person_id") or payload.get("user_id")
        if person_id and person_id in self._persons:
            await self.track_event(person_id, "first_platform_connected", payload, EventSource.APP)

    async def _on_publish_completed(self, event) -> None:
        """Handle publish.completed events."""
        payload = event.payload if hasattr(event, 'payload') else {}
        person_id = payload.get("person_id") or payload.get("user_id")
        if person_id and person_id in self._persons:
            await self.track_event(person_id, "post_published", payload, EventSource.APP)

    # ------------------------------------------------------------------
    # Database Persistence
    # ------------------------------------------------------------------

    async def _db_upsert_person(self, person: Person) -> None:
        """Persist person to database."""
        if not self.use_db or not self._db_engine:
            return
        try:
            from sqlalchemy import text
            with self._db_engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO gdp_persons (id, email, name, first_seen_at, last_seen_at, properties, segments)
                    VALUES (:id, :email, :name, :first_seen_at, :last_seen_at, :properties::jsonb, :segments)
                    ON CONFLICT (id) DO UPDATE SET
                        name = COALESCE(EXCLUDED.name, gdp_persons.name),
                        last_seen_at = EXCLUDED.last_seen_at,
                        properties = gdp_persons.properties || EXCLUDED.properties,
                        segments = EXCLUDED.segments,
                        updated_at = NOW()
                """), {
                    "id": person.id,
                    "email": person.email,
                    "name": person.name,
                    "first_seen_at": person.first_seen_at,
                    "last_seen_at": person.last_seen_at,
                    "properties": json.dumps(person.properties),
                    "segments": person.segments,
                })
                conn.commit()
        except Exception as e:
            logger.error("GDP: Failed to save person: %s", e)

    async def _db_save_identity_link(self, link: IdentityLink) -> None:
        """Persist identity link to database."""
        if not self.use_db or not self._db_engine:
            return
        try:
            from sqlalchemy import text
            with self._db_engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO gdp_identity_links (id, person_id, provider, external_id, linked_at, metadata)
                    VALUES (:id, :person_id, :provider, :external_id, :linked_at, :metadata::jsonb)
                    ON CONFLICT (provider, external_id) DO NOTHING
                """), {
                    "id": link.id,
                    "person_id": link.person_id,
                    "provider": link.provider,
                    "external_id": link.external_id,
                    "linked_at": link.linked_at,
                    "metadata": json.dumps(link.metadata),
                })
                conn.commit()
        except Exception as e:
            logger.error("GDP: Failed to save identity link: %s", e)

    async def _db_save_event(self, event: GDPEvent) -> None:
        """Persist event to database."""
        if not self.use_db or not self._db_engine:
            return
        try:
            from sqlalchemy import text
            with self._db_engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO gdp_events (id, person_id, event_name, source, properties, timestamp, session_id, segment_trigger)
                    VALUES (:id, :person_id, :event_name, :source, :properties::jsonb, :timestamp, :session_id, :segment_trigger)
                """), {
                    "id": event.id,
                    "person_id": event.person_id,
                    "event_name": event.event_name,
                    "source": event.source,
                    "properties": json.dumps(event.properties),
                    "timestamp": event.timestamp,
                    "session_id": event.session_id,
                    "segment_trigger": event.segment_trigger,
                })
                conn.commit()
        except Exception as e:
            logger.error("GDP: Failed to save event: %s", e)


# ============================================================================
# Module-level Convenience Functions
# ============================================================================

def get_growth_data_plane(
    event_bus: Optional[EventBus] = None,
    use_db: bool = True,
) -> GrowthDataPlane:
    """Get the singleton GrowthDataPlane instance."""
    return GrowthDataPlane.get_instance(event_bus, use_db)
