"""
Tests for Growth Data Plane (GDP-001 through GDP-012)
=====================================================
Validates schema, person/identity management, unified event tracking,
webhook processing, email tracking, click tracking, Stripe integration,
PostHog identity stitching, and Meta Pixel deduplication.
"""
import pytest
import asyncio
from datetime import datetime, timezone

from services.growth_data_plane import (
    GrowthDataPlane,
    get_growth_data_plane,
    Person,
    IdentityLink,
    GDPEvent,
    PersonFeatures,
    IdentityProvider,
    EventSource,
    SegmentTrigger,
    EVENT_SEGMENT_MAP,
    GDP_SCHEMA_SQL,
    # GDP-004 to GDP-010
    ResendEventType,
    StripeEventType,
    SubscriptionStatus,
    EmailEvent,
    ClickEvent,
    SubscriptionSnapshot,
    MetaPixelEvent,
)
from services.event_bus import EventBus


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def event_bus():
    """Fresh EventBus for testing."""
    return EventBus()


@pytest.fixture
def gdp(event_bus):
    """Fresh GrowthDataPlane (in-memory, no DB)."""
    GrowthDataPlane.reset_instance()
    return GrowthDataPlane(event_bus=event_bus, use_db=False)


# ============================================================================
# GDP-001: Schema Setup
# ============================================================================

class TestGDP001_SchemaSetup:
    """GDP-001: Supabase Schema Setup"""

    def test_schema_sql_exists(self, gdp):
        """GDP-001: Schema SQL should be defined."""
        sql = gdp.get_schema_sql()
        assert sql is not None
        assert len(sql) > 100

    def test_schema_has_persons_table(self, gdp):
        """GDP-001: Schema should include gdp_persons table."""
        sql = gdp.get_schema_sql()
        assert "gdp_persons" in sql

    def test_schema_has_identity_links_table(self, gdp):
        """GDP-001: Schema should include gdp_identity_links table."""
        sql = gdp.get_schema_sql()
        assert "gdp_identity_links" in sql

    def test_schema_has_events_table(self, gdp):
        """GDP-001: Schema should include gdp_events table."""
        sql = gdp.get_schema_sql()
        assert "gdp_events" in sql

    def test_schema_has_person_features_table(self, gdp):
        """GDP-001: Schema should include gdp_person_features table."""
        sql = gdp.get_schema_sql()
        assert "gdp_person_features" in sql

    def test_schema_has_segments_table(self, gdp):
        """GDP-001: Schema should include gdp_segments table."""
        sql = gdp.get_schema_sql()
        assert "gdp_segments" in sql

    def test_schema_has_indexes(self, gdp):
        """GDP-001: Schema should include performance indexes."""
        sql = gdp.get_schema_sql()
        assert "CREATE INDEX" in sql
        assert "idx_gdp_events_person_id" in sql
        assert "idx_gdp_events_event_name" in sql
        assert "idx_gdp_events_timestamp" in sql

    def test_schema_has_foreign_keys(self, gdp):
        """GDP-001: Schema should have foreign key constraints."""
        sql = gdp.get_schema_sql()
        assert "REFERENCES gdp_persons(id)" in sql

    @pytest.mark.asyncio
    async def test_ensure_schema_no_db(self, gdp):
        """GDP-001: ensure_schema should return False when no DB."""
        result = await gdp.ensure_schema()
        assert result is False


# ============================================================================
# GDP-002: Person & Identity Tables
# ============================================================================

class TestGDP002_PersonManagement:
    """GDP-002: Person & Identity Tables"""

    @pytest.mark.asyncio
    async def test_create_person(self, gdp):
        """GDP-002: Should create a new person record."""
        pid = await gdp.upsert_person(email="user@example.com", name="Jane Doe")
        assert pid is not None
        assert len(pid) > 0

    @pytest.mark.asyncio
    async def test_get_person(self, gdp):
        """GDP-002: Should retrieve a person by ID."""
        pid = await gdp.upsert_person(email="get@example.com", name="Get Test")
        person = gdp.get_person(pid)
        assert person is not None
        assert person.email == "get@example.com"
        assert person.name == "Get Test"

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, gdp):
        """GDP-002: Upsert should update existing person by email."""
        pid1 = await gdp.upsert_person(email="update@example.com", name="First Name")
        pid2 = await gdp.upsert_person(email="update@example.com", name="Updated Name")
        assert pid1 == pid2
        person = gdp.get_person(pid1)
        assert person.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_person_properties(self, gdp):
        """GDP-002: Person should support arbitrary properties."""
        pid = await gdp.upsert_person(
            email="props@example.com",
            properties={"plan": "pro", "source": "organic"}
        )
        person = gdp.get_person(pid)
        assert person.properties["plan"] == "pro"
        assert person.properties["source"] == "organic"

    @pytest.mark.asyncio
    async def test_person_timestamps(self, gdp):
        """GDP-002: Person should have first_seen_at and last_seen_at."""
        pid = await gdp.upsert_person(email="time@example.com")
        person = gdp.get_person(pid)
        assert person.first_seen_at is not None
        assert person.last_seen_at is not None

    @pytest.mark.asyncio
    async def test_person_to_dict(self, gdp):
        """GDP-002: Person should serialize to dict."""
        pid = await gdp.upsert_person(email="dict@example.com", name="Dict Test")
        person = gdp.get_person(pid)
        d = person.to_dict()
        assert d["email"] == "dict@example.com"
        assert d["name"] == "Dict Test"
        assert "id" in d
        assert "segments" in d

    @pytest.mark.asyncio
    async def test_find_person_by_email(self, gdp):
        """GDP-002: Should find person by email."""
        pid = await gdp.upsert_person(email="find@example.com")
        found = gdp.get_person_by_email("find@example.com")
        assert found is not None
        assert found.id == pid

    @pytest.mark.asyncio
    async def test_find_person_not_found(self, gdp):
        """GDP-002: Should return None for unknown email."""
        found = gdp.get_person_by_email("nonexistent@example.com")
        assert found is None


class TestGDP002_IdentityLinking:
    """GDP-002: Identity link management."""

    @pytest.mark.asyncio
    async def test_link_identity(self, gdp):
        """GDP-002: Should link external identity to person."""
        pid = await gdp.upsert_person(email="link@example.com")
        link_id = await gdp.link_identity(pid, IdentityProvider.STRIPE, "cus_abc123")
        assert link_id is not None

    @pytest.mark.asyncio
    async def test_get_identity_links(self, gdp):
        """GDP-002: Should retrieve all identity links for a person."""
        pid = await gdp.upsert_person(email="links@example.com")
        await gdp.link_identity(pid, IdentityProvider.STRIPE, "cus_abc")
        await gdp.link_identity(pid, IdentityProvider.POSTHOG, "ph_xyz")
        links = gdp.get_identity_links(pid)
        assert len(links) == 2
        providers = {l.provider for l in links}
        assert IdentityProvider.STRIPE in providers
        assert IdentityProvider.POSTHOG in providers

    @pytest.mark.asyncio
    async def test_duplicate_link_prevention(self, gdp):
        """GDP-002: Should not create duplicate identity links."""
        pid = await gdp.upsert_person(email="dup@example.com")
        id1 = await gdp.link_identity(pid, IdentityProvider.STRIPE, "cus_same")
        id2 = await gdp.link_identity(pid, IdentityProvider.STRIPE, "cus_same")
        assert id1 == id2
        links = gdp.get_identity_links(pid)
        assert len(links) == 1

    @pytest.mark.asyncio
    async def test_resolve_person_by_identity(self, gdp):
        """GDP-002: Should resolve person from external identity."""
        pid = await gdp.upsert_person(email="resolve@example.com")
        await gdp.link_identity(pid, IdentityProvider.META, "meta_user_123")
        resolved = gdp.resolve_person_by_identity(IdentityProvider.META, "meta_user_123")
        assert resolved == pid

    @pytest.mark.asyncio
    async def test_resolve_unknown_identity(self, gdp):
        """GDP-002: Should return None for unknown identity."""
        resolved = gdp.resolve_person_by_identity("unknown", "xyz")
        assert resolved is None

    @pytest.mark.asyncio
    async def test_identity_link_metadata(self, gdp):
        """GDP-002: Identity link should support metadata."""
        pid = await gdp.upsert_person(email="meta@example.com")
        await gdp.link_identity(pid, IdentityProvider.STRIPE, "cus_meta", {"plan": "pro"})
        links = gdp.get_identity_links(pid)
        assert links[0].metadata["plan"] == "pro"


# ============================================================================
# GDP-003: Unified Events Table
# ============================================================================

class TestGDP003_UnifiedEvents:
    """GDP-003: Unified Events Table"""

    @pytest.mark.asyncio
    async def test_track_event(self, gdp):
        """GDP-003: Should track an event for a person."""
        pid = await gdp.upsert_person(email="event@example.com")
        eid = await gdp.track_event(pid, "post_published", {"platform": "tiktok"})
        assert eid is not None

    @pytest.mark.asyncio
    async def test_event_properties(self, gdp):
        """GDP-003: Event should store properties."""
        pid = await gdp.upsert_person(email="props@example.com")
        await gdp.track_event(pid, "post_created", {"title": "My Post"})
        events = gdp.get_events(person_id=pid)
        assert len(events) == 1
        assert events[0].properties["title"] == "My Post"

    @pytest.mark.asyncio
    async def test_event_source(self, gdp):
        """GDP-003: Event should track source."""
        pid = await gdp.upsert_person(email="source@example.com")
        await gdp.track_event(pid, "landing_view", source=EventSource.WEB)
        events = gdp.get_events(person_id=pid)
        assert events[0].source == EventSource.WEB

    @pytest.mark.asyncio
    async def test_event_timestamp(self, gdp):
        """GDP-003: Event should have timestamp."""
        pid = await gdp.upsert_person(email="ts@example.com")
        await gdp.track_event(pid, "signup_completed")
        events = gdp.get_events(person_id=pid)
        assert events[0].timestamp is not None

    @pytest.mark.asyncio
    async def test_query_events_by_person(self, gdp):
        """GDP-003: Should filter events by person_id."""
        pid1 = await gdp.upsert_person(email="person1@example.com")
        pid2 = await gdp.upsert_person(email="person2@example.com")
        await gdp.track_event(pid1, "post_published")
        await gdp.track_event(pid2, "landing_view")
        await gdp.track_event(pid1, "post_scheduled")
        events_p1 = gdp.get_events(person_id=pid1)
        assert len(events_p1) == 2

    @pytest.mark.asyncio
    async def test_query_events_by_name(self, gdp):
        """GDP-003: Should filter events by event_name."""
        pid = await gdp.upsert_person(email="name@example.com")
        await gdp.track_event(pid, "post_published")
        await gdp.track_event(pid, "post_scheduled")
        await gdp.track_event(pid, "post_published")
        events = gdp.get_events(event_name="post_published")
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_event_count(self, gdp):
        """GDP-003: Should count events per person."""
        pid = await gdp.upsert_person(email="count@example.com")
        await gdp.track_event(pid, "landing_view")
        await gdp.track_event(pid, "signup_completed")
        await gdp.track_event(pid, "post_created")
        count = gdp.get_event_count(pid)
        assert count == 3

    @pytest.mark.asyncio
    async def test_event_to_dict(self, gdp):
        """GDP-003: Event should serialize to dict."""
        pid = await gdp.upsert_person(email="dict@example.com")
        await gdp.track_event(pid, "post_published")
        events = gdp.get_events(person_id=pid)
        d = events[0].to_dict()
        assert d["event_name"] == "post_published"
        assert d["person_id"] == pid

    @pytest.mark.asyncio
    async def test_event_session_id(self, gdp):
        """GDP-003: Event should support session_id."""
        pid = await gdp.upsert_person(email="session@example.com")
        await gdp.track_event(pid, "landing_view", session_id="sess_abc123")
        events = gdp.get_events(person_id=pid)
        assert events[0].session_id == "sess_abc123"


# ============================================================================
# Segment Triggers
# ============================================================================

class TestGDP_SegmentTriggers:
    """Test segment trigger automation."""

    @pytest.mark.asyncio
    async def test_post_published_triggers_first_value(self, gdp):
        """GDP: post_published should trigger first_value segment."""
        pid = await gdp.upsert_person(email="seg@example.com")
        await gdp.track_event(pid, "post_published")
        segments = gdp.get_person_segments(pid)
        assert SegmentTrigger.FIRST_VALUE in segments

    @pytest.mark.asyncio
    async def test_signup_triggers_new_signup(self, gdp):
        """GDP: signup_completed should trigger new_signup segment."""
        pid = await gdp.upsert_person(email="signup@example.com")
        await gdp.track_event(pid, "signup_completed")
        segments = gdp.get_person_segments(pid)
        assert SegmentTrigger.NEW_SIGNUP in segments

    @pytest.mark.asyncio
    async def test_platform_connected_triggers_activated(self, gdp):
        """GDP: first_platform_connected should trigger activated."""
        pid = await gdp.upsert_person(email="activate@example.com")
        await gdp.track_event(pid, "first_platform_connected")
        segments = gdp.get_person_segments(pid)
        assert SegmentTrigger.ACTIVATED in segments

    @pytest.mark.asyncio
    async def test_subscription_triggers_monetized(self, gdp):
        """GDP: subscription_started should trigger monetized."""
        pid = await gdp.upsert_person(email="sub@example.com")
        await gdp.track_event(pid, "subscription_started")
        segments = gdp.get_person_segments(pid)
        assert SegmentTrigger.MONETIZED in segments

    @pytest.mark.asyncio
    async def test_no_trigger_for_landing_view(self, gdp):
        """GDP: landing_view should not trigger any segment."""
        pid = await gdp.upsert_person(email="view@example.com")
        await gdp.track_event(pid, "landing_view")
        segments = gdp.get_person_segments(pid)
        assert len(segments) == 0

    @pytest.mark.asyncio
    async def test_segment_query(self, gdp):
        """GDP: Should query persons by segment."""
        pid1 = await gdp.upsert_person(email="seg1@example.com")
        pid2 = await gdp.upsert_person(email="seg2@example.com")
        await gdp.track_event(pid1, "subscription_started")
        await gdp.track_event(pid2, "landing_view")
        monetized = gdp.get_persons_in_segment(SegmentTrigger.MONETIZED)
        assert len(monetized) == 1
        assert monetized[0].id == pid1

    @pytest.mark.asyncio
    async def test_multiple_segments(self, gdp):
        """GDP: Person can belong to multiple segments."""
        pid = await gdp.upsert_person(email="multi@example.com")
        await gdp.track_event(pid, "signup_completed")
        await gdp.track_event(pid, "first_platform_connected")
        await gdp.track_event(pid, "post_published")
        segments = gdp.get_person_segments(pid)
        assert SegmentTrigger.NEW_SIGNUP in segments
        assert SegmentTrigger.ACTIVATED in segments
        assert SegmentTrigger.FIRST_VALUE in segments


# ============================================================================
# Person Features (GDP-011)
# ============================================================================

class TestGDP_PersonFeatures:
    """Test person feature computation."""

    @pytest.mark.asyncio
    async def test_compute_features(self, gdp):
        """GDP-011: Should compute features from event history."""
        pid = await gdp.upsert_person(email="feat@example.com")
        await gdp.track_event(pid, "signup_completed")
        await gdp.track_event(pid, "first_platform_connected")
        await gdp.track_event(pid, "post_published")
        features = await gdp.compute_person_features(pid)
        assert features.total_events == 3
        assert features.platforms_connected == 1
        assert features.posts_published == 1
        assert features.is_activated is True
        assert features.is_monetized is False

    @pytest.mark.asyncio
    async def test_features_monetized(self, gdp):
        """GDP-011: Should detect monetized status."""
        pid = await gdp.upsert_person(email="money@example.com")
        await gdp.track_event(pid, "subscription_started")
        features = await gdp.compute_person_features(pid)
        assert features.is_monetized is True

    @pytest.mark.asyncio
    async def test_features_to_dict(self, gdp):
        """GDP-011: Features should serialize to dict."""
        pid = await gdp.upsert_person(email="fdict@example.com")
        features = await gdp.compute_person_features(pid)
        d = features.to_dict()
        assert "person_id" in d
        assert "total_events" in d
        assert "is_activated" in d


# ============================================================================
# Singleton & Stats
# ============================================================================

class TestGDP_SingletonAndStats:
    """Test singleton pattern and statistics."""

    def test_singleton_pattern(self):
        """GDP: Should use singleton pattern."""
        GrowthDataPlane.reset_instance()
        bus = EventBus()
        gdp1 = get_growth_data_plane(event_bus=bus, use_db=False)
        gdp2 = get_growth_data_plane()
        assert gdp1 is gdp2
        GrowthDataPlane.reset_instance()

    @pytest.mark.asyncio
    async def test_stats(self, gdp):
        """GDP: Should provide statistics."""
        pid = await gdp.upsert_person(email="stats@example.com")
        await gdp.track_event(pid, "post_published")
        await gdp.link_identity(pid, IdentityProvider.STRIPE, "cus_stats")
        stats = gdp.get_stats()
        assert stats["total_persons"] == 1
        assert stats["total_events"] == 1
        assert stats["total_identity_links"] == 1


# ============================================================================
# Data Model Validation
# ============================================================================

class TestGDP_DataModels:
    """Test data model integrity."""

    def test_identity_provider_enum(self):
        """GDP: IdentityProvider should have all providers."""
        assert IdentityProvider.EMAIL == "email"
        assert IdentityProvider.POSTHOG == "posthog"
        assert IdentityProvider.STRIPE == "stripe"
        assert IdentityProvider.META == "meta"
        assert IdentityProvider.GOOGLE == "google"
        assert IdentityProvider.BLOTATO == "blotato"

    def test_event_source_enum(self):
        """GDP: EventSource should have all sources."""
        assert EventSource.WEB == "web"
        assert EventSource.APP == "app"
        assert EventSource.EMAIL == "email"
        assert EventSource.STRIPE == "stripe"
        assert EventSource.META == "meta"

    def test_segment_trigger_enum(self):
        """GDP: SegmentTrigger should have all triggers."""
        assert SegmentTrigger.NEW_SIGNUP == "new_signup"
        assert SegmentTrigger.ACTIVATED == "activated"
        assert SegmentTrigger.MONETIZED == "monetized"
        assert SegmentTrigger.AHA_MOMENT == "aha_moment"

    def test_event_segment_mapping(self):
        """GDP: EVENT_SEGMENT_MAP should map all MediaPoster events."""
        assert "post_published" in EVENT_SEGMENT_MAP
        assert "signup_completed" in EVENT_SEGMENT_MAP
        assert "first_platform_connected" in EVENT_SEGMENT_MAP
        assert "subscription_started" in EVENT_SEGMENT_MAP
        assert "landing_view" in EVENT_SEGMENT_MAP
        assert "checkout_started" in EVENT_SEGMENT_MAP

    def test_person_default_fields(self):
        """GDP-002: Person should have correct default fields."""
        p = Person()
        assert p.id is not None
        assert p.segments == []
        assert p.properties == {}
        assert p.first_seen_at is not None

    def test_gdp_event_default_fields(self):
        """GDP-003: GDPEvent should have correct default fields."""
        e = GDPEvent(person_id="abc", event_name="test")
        assert e.id is not None
        assert e.source == EventSource.APP
        assert e.properties == {}
        assert e.timestamp is not None

    def test_identity_link_default_fields(self):
        """GDP-002: IdentityLink should have correct default fields."""
        link = IdentityLink(person_id="abc", provider="stripe", external_id="cus_123")
        assert link.id is not None
        assert link.linked_at is not None
        assert link.metadata == {}


# ============================================================================
# GDP-004: Resend Webhook Edge Function
# ============================================================================

class TestGDP004_ResendWebhook:
    """GDP-004: Resend Webhook Processing"""

    @pytest.mark.asyncio
    async def test_process_resend_webhook_delivered(self, gdp):
        """GDP-004: Process email.delivered webhook event."""
        pid = await gdp.upsert_person(email="user@example.com", name="Test User")
        result = await gdp.process_resend_webhook({
            "type": "email.delivered",
            "data": {
                "to": ["user@example.com"],
                "email_id": "msg_123",
                "subject": "Welcome!",
                "created_at": "2026-01-15T00:00:00Z",
            },
        })
        assert result is not None

    @pytest.mark.asyncio
    async def test_process_resend_webhook_clicked(self, gdp):
        """GDP-004: Process email.clicked webhook event."""
        pid = await gdp.upsert_person(email="clicker@example.com")
        result = await gdp.process_resend_webhook({
            "type": "email.clicked",
            "data": {
                "to": ["clicker@example.com"],
                "email_id": "msg_456",
                "subject": "Check this out",
                "click": {"link": "https://example.com/offer"},
            },
        })
        assert result is not None

    @pytest.mark.asyncio
    async def test_process_resend_webhook_no_person(self, gdp):
        """GDP-004: Webhook for unknown email still creates email event."""
        result = await gdp.process_resend_webhook({
            "type": "email.sent",
            "data": {
                "to": ["unknown@example.com"],
                "email_id": "msg_789",
            },
        })
        assert result is not None  # Returns email_event.id
        assert len(gdp._email_events) == 1

    @pytest.mark.asyncio
    async def test_process_resend_webhook_invalid(self, gdp):
        """GDP-004: Reject webhook with missing data."""
        result = await gdp.process_resend_webhook({})
        assert result is None

    def test_resend_event_type_enum(self):
        """GDP-004: ResendEventType enum has all event types."""
        assert ResendEventType.EMAIL_SENT == "email.sent"
        assert ResendEventType.EMAIL_DELIVERED == "email.delivered"
        assert ResendEventType.EMAIL_OPENED == "email.opened"
        assert ResendEventType.EMAIL_CLICKED == "email.clicked"
        assert ResendEventType.EMAIL_BOUNCED == "email.bounced"
        assert ResendEventType.EMAIL_COMPLAINED == "email.complained"


# ============================================================================
# GDP-005: Email Event Tracking
# ============================================================================

class TestGDP005_EmailEventTracking:
    """GDP-005: Email Event Tracking"""

    @pytest.mark.asyncio
    async def test_track_email_event(self, gdp):
        """GDP-005: Track an email event."""
        pid = await gdp.upsert_person(email="email@test.com")
        eid = await gdp.track_email_event(
            email_address="email@test.com",
            event_type="email.opened",
            message_id="msg_001",
            subject="Newsletter #1",
        )
        assert eid is not None
        assert len(gdp._email_events) == 1

    @pytest.mark.asyncio
    async def test_get_email_events_filter(self, gdp):
        """GDP-005: Filter email events by address and type."""
        await gdp.track_email_event("a@test.com", "email.sent")
        await gdp.track_email_event("a@test.com", "email.opened")
        await gdp.track_email_event("b@test.com", "email.sent")

        all_events = gdp.get_email_events()
        assert len(all_events) == 3

        a_events = gdp.get_email_events(email_address="a@test.com")
        assert len(a_events) == 2

        sent_events = gdp.get_email_events(event_type="email.sent")
        assert len(sent_events) == 2

    @pytest.mark.asyncio
    async def test_email_stats(self, gdp):
        """GDP-005: Get email event statistics."""
        await gdp.track_email_event("user@test.com", "email.sent")
        await gdp.track_email_event("user@test.com", "email.delivered")
        await gdp.track_email_event("user@test.com", "email.opened")
        await gdp.track_email_event("user@test.com", "email.opened")

        stats = gdp.get_email_stats()
        assert stats["email.sent"] == 1
        assert stats["email.delivered"] == 1
        assert stats["email.opened"] == 2

    def test_email_event_dataclass(self):
        """GDP-005: EmailEvent dataclass has correct fields."""
        e = EmailEvent(
            email_address="test@example.com",
            event_type="email.opened",
            message_id="msg_123",
        )
        assert e.id is not None
        assert e.email_address == "test@example.com"
        assert e.event_type == "email.opened"
        d = e.to_dict()
        assert "email_address" in d
        assert "event_type" in d


# ============================================================================
# GDP-006: Click Redirect Tracker
# ============================================================================

class TestGDP006_ClickRedirectTracker:
    """GDP-006: Click Redirect Tracking"""

    @pytest.mark.asyncio
    async def test_create_tracked_link(self, gdp):
        """GDP-006: Create a tracked redirect link with UTM params."""
        click = await gdp.create_tracked_link(
            original_url="https://example.com/offer",
            utm_source="twitter",
            utm_medium="social",
            utm_campaign="summer2026",
        )
        assert click.click_id is not None
        assert "utm_source=twitter" in click.redirect_url
        assert "utm_medium=social" in click.redirect_url
        assert "utm_campaign=summer2026" in click.redirect_url

    @pytest.mark.asyncio
    async def test_record_click(self, gdp):
        """GDP-006: Record a click with metadata."""
        pid = await gdp.upsert_person(email="clicker@test.com")
        click = await gdp.create_tracked_link(
            original_url="https://example.com",
            person_id=pid,
        )
        recorded = await gdp.record_click(
            click_id=click.click_id,
            referrer="https://twitter.com",
            user_agent="Mozilla/5.0",
            ip_address="1.2.3.4",
        )
        assert recorded is not None
        assert recorded.referrer == "https://twitter.com"
        assert recorded.ip_address == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_record_click_not_found(self, gdp):
        """GDP-006: Record click for unknown ID returns None."""
        result = await gdp.record_click(click_id="nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_click_events(self, gdp):
        """GDP-006: Query click events."""
        await gdp.create_tracked_link("https://a.com", utm_campaign="camp1")
        await gdp.create_tracked_link("https://b.com", utm_campaign="camp2")
        await gdp.create_tracked_link("https://c.com", utm_campaign="camp1")

        all_clicks = gdp.get_click_events()
        assert len(all_clicks) == 3

        camp1 = gdp.get_click_events(utm_campaign="camp1")
        assert len(camp1) == 2

    def test_click_event_dataclass(self):
        """GDP-006: ClickEvent dataclass has correct fields."""
        c = ClickEvent(original_url="https://example.com")
        assert c.click_id is not None
        assert c.original_url == "https://example.com"
        d = c.to_dict()
        assert "click_id" in d
        assert "utm_source" in d


# ============================================================================
# GDP-007: Stripe Webhook Integration
# ============================================================================

class TestGDP007_StripeWebhook:
    """GDP-007: Stripe Webhook Integration"""

    @pytest.mark.asyncio
    async def test_process_checkout_completed(self, gdp):
        """GDP-007: Process checkout.session.completed webhook."""
        pid = await gdp.upsert_person(email="buyer@test.com")
        result = await gdp.process_stripe_webhook(
            event_type=StripeEventType.CHECKOUT_COMPLETED,
            event_data={
                "object": {
                    "customer_email": "buyer@test.com",
                    "customer": "cus_abc123",
                    "amount_total": 2999,
                    "currency": "usd",
                },
            },
        )
        assert result == pid
        # Should auto-link Stripe identity
        links = gdp.get_identity_links(pid)
        stripe_links = [l for l in links if l.provider == IdentityProvider.STRIPE]
        assert len(stripe_links) == 1

    @pytest.mark.asyncio
    async def test_process_subscription_created(self, gdp):
        """GDP-007: Process subscription.created and create snapshot."""
        pid = await gdp.upsert_person(email="sub@test.com")
        await gdp.link_identity(pid, IdentityProvider.STRIPE, "cus_sub123")

        result = await gdp.process_stripe_webhook(
            event_type=StripeEventType.SUBSCRIPTION_CREATED,
            event_data={
                "object": {
                    "id": "sub_123",
                    "customer": "cus_sub123",
                    "status": "active",
                    "plan": {"id": "plan_pro", "nickname": "Pro Plan", "amount": 2999},
                    "currency": "usd",
                    "current_period_start": "2026-01-01",
                    "current_period_end": "2026-02-01",
                },
            },
        )
        assert result == pid
        # Should have created subscription snapshot
        snapshot = gdp.get_subscription(pid)
        assert snapshot is not None
        assert snapshot.stripe_subscription_id == "sub_123"

    @pytest.mark.asyncio
    async def test_process_stripe_unknown_customer(self, gdp):
        """GDP-007: Stripe event for unknown customer returns None."""
        result = await gdp.process_stripe_webhook(
            event_type=StripeEventType.CHARGE_SUCCEEDED,
            event_data={"object": {"customer": "cus_unknown"}},
        )
        assert result is None

    def test_stripe_event_type_enum(self):
        """GDP-007: StripeEventType enum has all event types."""
        assert StripeEventType.CHECKOUT_COMPLETED == "checkout.session.completed"
        assert StripeEventType.SUBSCRIPTION_CREATED == "customer.subscription.created"
        assert StripeEventType.INVOICE_PAID == "invoice.paid"
        assert StripeEventType.CHARGE_REFUNDED == "charge.refunded"


# ============================================================================
# GDP-008: Subscription Snapshot
# ============================================================================

class TestGDP008_SubscriptionSnapshot:
    """GDP-008: Subscription Snapshot Management"""

    @pytest.mark.asyncio
    async def test_subscription_snapshot_creation(self, gdp):
        """GDP-008: Create subscription snapshot from Stripe data."""
        pid = await gdp.upsert_person(email="subscriber@test.com")
        await gdp.link_identity(pid, IdentityProvider.STRIPE, "cus_snap")

        await gdp.process_stripe_webhook(
            event_type=StripeEventType.SUBSCRIPTION_CREATED,
            event_data={
                "object": {
                    "id": "sub_snap1",
                    "customer": "cus_snap",
                    "status": "active",
                    "plan": {"id": "plan_basic", "nickname": "Basic", "amount": 999},
                    "currency": "usd",
                },
            },
        )

        snap = gdp.get_subscription(pid)
        assert snap is not None
        assert snap.status == "active"
        assert snap.amount_cents == 999

    @pytest.mark.asyncio
    async def test_get_active_subscribers(self, gdp):
        """GDP-008: List active subscribers."""
        for i in range(3):
            pid = await gdp.upsert_person(email=f"sub{i}@test.com")
            gdp._subscriptions[pid] = SubscriptionSnapshot(
                person_id=pid,
                status=SubscriptionStatus.ACTIVE if i < 2 else SubscriptionStatus.CANCELED,
            )

        active = gdp.get_active_subscribers()
        assert len(active) == 2

    def test_subscription_snapshot_dataclass(self):
        """GDP-008: SubscriptionSnapshot dataclass has correct fields."""
        s = SubscriptionSnapshot(person_id="pid_123", status=SubscriptionStatus.TRIALING)
        assert s.person_id == "pid_123"
        assert s.status == SubscriptionStatus.TRIALING
        d = s.to_dict()
        assert "stripe_subscription_id" in d
        assert "cancel_at_period_end" in d

    def test_subscription_status_enum(self):
        """GDP-008: SubscriptionStatus enum has all values."""
        assert SubscriptionStatus.ACTIVE == "active"
        assert SubscriptionStatus.CANCELED == "canceled"
        assert SubscriptionStatus.PAST_DUE == "past_due"
        assert SubscriptionStatus.TRIALING == "trialing"


# ============================================================================
# GDP-009: PostHog Identity Stitching
# ============================================================================

class TestGDP009_PostHogIdentityStitching:
    """GDP-009: PostHog Identity Stitching"""

    @pytest.mark.asyncio
    async def test_stitch_new_posthog_identity(self, gdp):
        """GDP-009: Stitch a new PostHog distinct_id to a person."""
        pid = await gdp.stitch_posthog_identity(
            distinct_id="ph_anon_abc123",
            email="posthog_user@test.com",
            properties={"browser": "Chrome"},
        )
        assert pid is not None
        # Should have linked PostHog identity
        resolved = gdp.resolve_person_by_identity(IdentityProvider.POSTHOG, "ph_anon_abc123")
        assert resolved == pid

    @pytest.mark.asyncio
    async def test_stitch_existing_posthog_identity(self, gdp):
        """GDP-009: Re-stitch existing PostHog identity updates properties."""
        pid1 = await gdp.stitch_posthog_identity(
            distinct_id="ph_user_456",
            email="existing@test.com",
        )
        pid2 = await gdp.stitch_posthog_identity(
            distinct_id="ph_user_456",
            email="existing@test.com",
            properties={"plan": "pro"},
        )
        assert pid1 == pid2
        person = gdp.get_person(pid2)
        assert person.properties.get("plan") == "pro"

    @pytest.mark.asyncio
    async def test_process_posthog_event(self, gdp):
        """GDP-009: Process a PostHog event and track in GDP."""
        pid = await gdp.stitch_posthog_identity("ph_track_789", email="ph@test.com")
        event_id = await gdp.process_posthog_event(
            distinct_id="ph_track_789",
            event_name="$pageview",
            properties={"$current_url": "https://app.example.com/dashboard"},
        )
        assert event_id is not None
        events = gdp.get_events(person_id=pid, event_name="posthog.pageview")
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_process_posthog_event_unknown_user(self, gdp):
        """GDP-009: PostHog event for unknown user returns None."""
        result = await gdp.process_posthog_event(
            distinct_id="ph_unknown",
            event_name="$pageview",
        )
        assert result is None


# ============================================================================
# GDP-010: Meta Pixel + CAPI Deduplication
# ============================================================================

class TestGDP010_MetaPixelCAPI:
    """GDP-010: Meta Pixel + CAPI Deduplication"""

    @pytest.mark.asyncio
    async def test_track_meta_pixel_event(self, gdp):
        """GDP-010: Track a Meta Pixel event."""
        event = await gdp.track_meta_pixel_event(
            event_name="PageView",
            pixel_id="123456",
            event_source="website",
            event_source_url="https://example.com/landing",
        )
        assert event.event_name == "PageView"
        assert event.pixel_id == "123456"
        assert event.is_deduplicated is False

    @pytest.mark.asyncio
    async def test_meta_event_deduplication(self, gdp):
        """GDP-010: Deduplicate same event from pixel and CAPI."""
        dedup_id = "evt_dedup_001"
        # First: browser pixel event
        pixel_event = await gdp.track_meta_pixel_event(
            event_name="Purchase",
            event_source="website",
            event_id=dedup_id,
            custom_data={"value": 29.99, "currency": "USD"},
        )
        assert pixel_event.is_deduplicated is False

        # Second: server CAPI event (same event_id)
        capi_event = await gdp.track_meta_pixel_event(
            event_name="Purchase",
            event_source="server",
            event_id=dedup_id,
            custom_data={"value": 29.99, "currency": "USD"},
        )
        assert capi_event.is_deduplicated is True
        # Original pixel event should also be marked
        assert pixel_event.is_deduplicated is True

    @pytest.mark.asyncio
    async def test_meta_user_data_hashing(self, gdp):
        """GDP-010: PII data is hashed in user_data."""
        event = await gdp.track_meta_pixel_event(
            event_name="Lead",
            user_data={
                "em": "user@example.com",
                "ph": "+15551234567",
                "fn": "Jane",
                "external_id": "ext_123",  # non-PII, should not be hashed
            },
        )
        # Email should be hashed (SHA-256)
        assert event.user_data["em"] != "user@example.com"
        assert len(event.user_data["em"]) == 64  # SHA-256 hex digest
        # Phone should be hashed
        assert event.user_data["ph"] != "+15551234567"
        # Non-PII should NOT be hashed
        assert event.user_data["external_id"] == "ext_123"

    @pytest.mark.asyncio
    async def test_meta_dedup_stats(self, gdp):
        """GDP-010: Get deduplication statistics."""
        await gdp.track_meta_pixel_event("PageView", event_source="website", event_id="e1")
        await gdp.track_meta_pixel_event("PageView", event_source="server", event_id="e1")
        await gdp.track_meta_pixel_event("Lead", event_source="website", event_id="e2")

        stats = gdp.get_meta_dedup_stats()
        assert stats["total_events"] == 3
        assert stats["deduplicated"] >= 1
        assert stats["dedup_rate"] > 0
        assert "website" in stats["by_source"]

    @pytest.mark.asyncio
    async def test_get_meta_pixel_events(self, gdp):
        """GDP-010: Query Meta pixel events."""
        await gdp.track_meta_pixel_event("PageView")
        await gdp.track_meta_pixel_event("Purchase")
        await gdp.track_meta_pixel_event("PageView")

        all_events = gdp.get_meta_pixel_events()
        assert len(all_events) == 3

        pv_events = gdp.get_meta_pixel_events(event_name="PageView")
        assert len(pv_events) == 2

    def test_meta_pixel_event_dataclass(self):
        """GDP-010: MetaPixelEvent dataclass has correct fields."""
        e = MetaPixelEvent(event_name="Lead", pixel_id="px_123")
        assert e.event_id is not None
        assert e.event_name == "Lead"
        d = e.to_dict()
        assert "event_id" in d
        assert "is_deduplicated" in d
        assert "action_source" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
