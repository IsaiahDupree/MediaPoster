"""
Tests for Meta Pixel Tracking Service (META-001 through META-008)
=================================================================
Validates pixel installation, event tracking, CAPI, deduplication,
PII hashing, custom audiences, and conversion optimization.
"""
import pytest
from services.meta_pixel_service import (
    MetaPixelService,
    get_meta_pixel_service,
    MetaPixelConfig,
    MetaStandardEvent,
    APP_TO_META_EVENT_MAP,
    CAPIEvent,
    CustomAudience,
    ConversionConfig,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def pixel():
    """Fresh MetaPixelService for testing."""
    MetaPixelService.reset_instance()
    return MetaPixelService(pixel_id="test_pixel_123", access_token="test_token")


# ============================================================================
# META-001: Meta Pixel Installation
# ============================================================================

class TestMETA001_PixelInstallation:
    """META-001: Meta Pixel Installation"""

    def test_pixel_config_creation(self, pixel):
        """META-001: Pixel config has correct fields."""
        assert pixel.config.pixel_id == "test_pixel_123"
        assert pixel.config.access_token == "test_token"
        assert pixel.config.is_installed is True

    def test_install_pixel(self):
        """META-001: Install pixel with ID."""
        svc = MetaPixelService()
        assert svc.is_installed() is False
        svc.install_pixel("new_pixel_456")
        assert svc.is_installed() is True
        assert svc.config.pixel_id == "new_pixel_456"

    def test_get_pixel_init_snippet(self, pixel):
        """META-001: Generate JavaScript init snippet."""
        snippet = pixel.get_pixel_init_snippet()
        assert "test_pixel_123" in snippet
        assert "fbq('init'" in snippet
        assert "fbq('track', 'PageView')" in snippet
        assert "<script>" in snippet

    def test_get_pixel_init_snippet_no_pixel(self):
        """META-001: No snippet when pixel not configured."""
        svc = MetaPixelService()
        snippet = svc.get_pixel_init_snippet()
        assert snippet == ""

    def test_pixel_config_validate(self, pixel):
        """META-001: Config validation works."""
        assert pixel.config.validate() is True
        empty = MetaPixelConfig()
        assert empty.validate() is False

    def test_pixel_config_to_dict(self, pixel):
        """META-001: Config serializes to dict."""
        d = pixel.config.to_dict()
        assert "pixel_id" in d
        assert "access_token" in d
        assert "is_installed" in d


# ============================================================================
# META-002: PageView Tracking
# ============================================================================

class TestMETA002_PageViewTracking:
    """META-002: PageView Tracking"""

    def test_track_page_view(self, pixel):
        """META-002: Track a PageView event."""
        event = pixel.track_page_view(url="https://app.example.com/dashboard")
        assert event.event_name == MetaStandardEvent.PAGE_VIEW
        assert event.event_source_url == "https://app.example.com/dashboard"

    def test_track_page_view_with_user_data(self, pixel):
        """META-002: PageView with user data gets hashed."""
        event = pixel.track_page_view(
            url="https://app.example.com",
            user_data={"em": "user@example.com"},
        )
        assert event.user_data["em"] != "user@example.com"
        assert len(event.user_data["em"]) == 64  # SHA-256 hex

    def test_page_view_increments_stats(self, pixel):
        """META-002: PageView tracking increments pixel event count."""
        pixel.track_page_view()
        pixel.track_page_view()
        assert pixel._stats["pixel_events"] == 2


# ============================================================================
# META-003: Standard Events Mapping
# ============================================================================

class TestMETA003_StandardEventsMapping:
    """META-003: Standard Events Mapping"""

    def test_standard_event_enum(self):
        """META-003: All standard events defined."""
        assert MetaStandardEvent.PAGE_VIEW == "PageView"
        assert MetaStandardEvent.PURCHASE == "Purchase"
        assert MetaStandardEvent.LEAD == "Lead"
        assert MetaStandardEvent.SUBSCRIBE == "Subscribe"
        assert MetaStandardEvent.INITIATE_CHECKOUT == "InitiateCheckout"

    def test_track_standard_event(self, pixel):
        """META-003: Track a standard event with value."""
        event = pixel.track_standard_event(
            event_name=MetaStandardEvent.PURCHASE,
            value=29.99,
            currency="USD",
            content_ids=["plan_pro"],
        )
        assert event.event_name == "Purchase"
        assert event.custom_data["value"] == 29.99
        assert event.custom_data["currency"] == "USD"
        assert event.custom_data["content_ids"] == ["plan_pro"]

    def test_app_to_meta_event_mapping(self):
        """META-003: App events map to Meta standard events."""
        assert APP_TO_META_EVENT_MAP["landing_view"] == MetaStandardEvent.PAGE_VIEW
        assert APP_TO_META_EVENT_MAP["checkout_started"] == MetaStandardEvent.INITIATE_CHECKOUT
        assert APP_TO_META_EVENT_MAP["purchase_completed"] == MetaStandardEvent.PURCHASE
        assert APP_TO_META_EVENT_MAP["platform_connected"] == MetaStandardEvent.LEAD

    def test_map_app_event(self, pixel):
        """META-003: Map app event to Meta event."""
        assert pixel.map_app_event("purchase_completed") == MetaStandardEvent.PURCHASE
        assert pixel.map_app_event("unknown_event") is None

    def test_track_app_event(self, pixel):
        """META-003: Track an app event mapped to Meta."""
        event = pixel.track_app_event("checkout_started", custom_data={"plan": "pro"})
        assert event is not None
        assert event.event_name == MetaStandardEvent.INITIATE_CHECKOUT

    def test_track_unknown_app_event(self, pixel):
        """META-003: Unknown app event returns None."""
        event = pixel.track_app_event("nonexistent_event")
        assert event is None


# ============================================================================
# META-004: CAPI Server-Side Events
# ============================================================================

class TestMETA004_CAPIServerEvents:
    """META-004: CAPI Server-Side Events"""

    def test_send_server_event(self, pixel):
        """META-004: Send a server-side CAPI event."""
        event = pixel.send_server_event(
            event_name=MetaStandardEvent.PURCHASE,
            custom_data={"value": 49.99, "currency": "USD"},
            event_source_url="https://app.example.com/checkout",
        )
        assert event.event_name == "Purchase"
        assert event.action_source == "website"
        assert pixel._stats["server_events"] == 1

    def test_capi_event_to_meta_payload(self):
        """META-004: CAPIEvent serializes to Meta API format."""
        event = CAPIEvent(
            event_name="Purchase",
            event_source_url="https://example.com",
            user_data={"em": "hashed_email"},
            custom_data={"value": 10.00},
        )
        payload = event.to_meta_payload()
        assert payload["event_name"] == "Purchase"
        assert "event_time" in payload
        assert "event_id" in payload
        assert payload["user_data"] == {"em": "hashed_email"}

    def test_build_capi_batch_payload(self, pixel):
        """META-004: Build batch payload for CAPI."""
        e1 = pixel.send_server_event("Purchase")
        e2 = pixel.send_server_event("Lead")
        payload = pixel.build_capi_payload([e1, e2])
        assert len(payload["data"]) == 2

    def test_server_event_with_action_source(self, pixel):
        """META-004: Server event with custom action source."""
        event = pixel.send_server_event(
            event_name="Lead",
            action_source="email",
        )
        assert event.action_source == "email"


# ============================================================================
# META-005: Event Deduplication
# ============================================================================

class TestMETA005_EventDeduplication:
    """META-005: Event Deduplication"""

    def test_same_event_id_different_sources(self, pixel):
        """META-005: Same event_id from pixel+CAPI gets deduplicated."""
        event_id = "shared_evt_001"
        pixel.track_page_view(event_id=event_id)
        pixel.send_server_event("PageView", event_id=event_id)
        assert pixel._stats["deduplicated"] == 1

    def test_different_event_ids_no_dedup(self, pixel):
        """META-005: Different event_ids are not deduplicated."""
        pixel.track_page_view(event_id="evt_1")
        pixel.send_server_event("PageView", event_id="evt_2")
        assert pixel._stats["deduplicated"] == 0

    def test_dedup_stats(self, pixel):
        """META-005: Deduplication statistics."""
        pixel.track_page_view(event_id="d1")
        pixel.send_server_event("PageView", event_id="d1")
        pixel.track_standard_event("Lead", event_id="d2")

        stats = pixel.get_dedup_stats()
        assert stats["total_events"] == 3
        assert stats["deduplicated"] == 1
        assert stats["dedup_rate"] > 0


# ============================================================================
# META-006: User Data Hashing (PII)
# ============================================================================

class TestMETA006_UserDataHashing:
    """META-006: User Data Hashing (PII)"""

    def test_hash_pii_fields(self, pixel):
        """META-006: PII fields are hashed with SHA-256."""
        hashed = pixel.hash_user_data({
            "em": "User@Example.com",
            "ph": "+15551234567",
            "fn": "Jane",
            "external_id": "ext_123",
            "non_pii": "keep_as_is",
        })
        assert hashed["em"] != "User@Example.com"
        assert len(hashed["em"]) == 64
        assert hashed["ph"] != "+15551234567"
        assert hashed["non_pii"] == "keep_as_is"  # Non-PII not hashed

    def test_hash_email(self):
        """META-006: Hash email correctly."""
        h = MetaPixelService.hash_email("User@Example.com")
        assert len(h) == 64
        # Same email different casing should produce same hash
        h2 = MetaPixelService.hash_email("user@example.com")
        assert h == h2

    def test_hash_phone(self):
        """META-006: Hash phone correctly."""
        h = MetaPixelService.hash_phone("+1 (555) 123-4567")
        assert len(h) == 64

    def test_empty_pii_not_hashed(self, pixel):
        """META-006: Empty PII values are not hashed."""
        hashed = pixel.hash_user_data({"em": "", "fn": None})
        assert hashed["em"] == ""
        assert hashed["fn"] is None

    def test_pii_hashing_stats(self, pixel):
        """META-006: PII hashing increments counter."""
        pixel.hash_user_data({"em": "user@test.com", "ph": "1234"})
        assert pixel._stats["pii_hashed"] == 2


# ============================================================================
# META-007: Custom Audiences Setup
# ============================================================================

class TestMETA007_CustomAudiences:
    """META-007: Custom Audiences Setup"""

    def test_create_custom_audience(self, pixel):
        """META-007: Create a custom audience."""
        audience = pixel.create_custom_audience(
            name="Active Users",
            description="Users who posted in last 7 days",
            segment_rules=[{"event": "post_published", "window_days": 7}],
        )
        assert audience.name == "Active Users"
        assert audience.id is not None
        assert len(audience.segment_rules) == 1

    def test_get_custom_audience(self, pixel):
        """META-007: Retrieve audience by ID."""
        created = pixel.create_custom_audience(name="Test")
        found = pixel.get_custom_audience(created.id)
        assert found is not None
        assert found.name == "Test"

    def test_list_custom_audiences(self, pixel):
        """META-007: List all audiences."""
        pixel.create_custom_audience(name="A1")
        pixel.create_custom_audience(name="A2")
        audiences = pixel.list_custom_audiences()
        assert len(audiences) == 2

    def test_update_audience_count(self, pixel):
        """META-007: Update audience member count."""
        audience = pixel.create_custom_audience(name="Big Audience")
        assert audience.member_count == 0
        pixel.update_audience_count(audience.id, 1500)
        assert audience.member_count == 1500

    def test_custom_audience_dataclass(self):
        """META-007: CustomAudience dataclass has correct fields."""
        a = CustomAudience(name="Test", source_type="lookalike")
        d = a.to_dict()
        assert "name" in d
        assert "segment_rules" in d
        assert "member_count" in d
        assert d["source_type"] == "lookalike"


# ============================================================================
# META-008: Conversion Optimization
# ============================================================================

class TestMETA008_ConversionOptimization:
    """META-008: Conversion Optimization"""

    def test_default_conversion_config(self, pixel):
        """META-008: Default conversion optimization settings."""
        config = pixel.get_conversion_config()
        assert config.optimization_goal == "PURCHASE"
        assert MetaStandardEvent.PURCHASE in config.event_priority
        assert config.attribution_window == 7

    def test_set_optimization_goal(self, pixel):
        """META-008: Set optimization goal."""
        pixel.set_optimization_goal("LEAD")
        assert pixel.conversion_config.optimization_goal == "LEAD"

    def test_set_event_priority(self, pixel):
        """META-008: Set event priority order."""
        pixel.set_event_priority(["Lead", "Purchase", "Subscribe"])
        assert pixel.conversion_config.event_priority == ["Lead", "Purchase", "Subscribe"]

    def test_top_conversion_events(self, pixel):
        """META-008: Get top conversion events by volume."""
        for _ in range(5):
            pixel.track_standard_event("PageView")
        for _ in range(3):
            pixel.track_standard_event("Purchase", value=29.99)
        pixel.track_standard_event("Lead")

        top = pixel.get_top_conversion_events(limit=3)
        assert len(top) == 3
        assert top[0]["event_name"] == "PageView"
        assert top[0]["count"] == 5
        assert top[1]["event_name"] == "Purchase"
        assert top[1]["total_value"] == 3 * 29.99

    def test_conversion_config_to_dict(self, pixel):
        """META-008: ConversionConfig serializes."""
        d = pixel.conversion_config.to_dict()
        assert "optimization_goal" in d
        assert "event_priority" in d
        assert "attribution_window" in d


# ============================================================================
# Service-level tests
# ============================================================================

class TestMetaPixelServiceGeneral:
    """General MetaPixelService tests."""

    def test_singleton_pattern(self):
        """MetaPixelService uses singleton pattern."""
        MetaPixelService.reset_instance()
        s1 = get_meta_pixel_service(pixel_id="px_1")
        s2 = get_meta_pixel_service()
        assert s1 is s2
        MetaPixelService.reset_instance()

    def test_get_stats(self, pixel):
        """Service stats include all counters."""
        pixel.track_page_view()
        pixel.send_server_event("Lead")
        stats = pixel.get_stats()
        assert stats["pixel_events"] == 1
        assert stats["server_events"] == 1
        assert "config" in stats
        assert "conversion_config" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
