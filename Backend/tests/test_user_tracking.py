"""
Tests for User Tracking Service
================================
Tests for TRACK-001 through TRACK-005
"""

import pytest
import asyncio
from datetime import datetime, timezone

from services.user_tracking_service import (
    UserTrackingService,
    EventName,
    EventCategory,
    TrackingEvent
)
from utils.tracking_helpers import (
    track_login_success,
    track_platform_connected,
    track_activation_complete,
    track_post_created,
    track_post_scheduled,
    track_post_published,
    track_media_uploaded,
    track_template_used,
    track_checkout_started,
    track_purchase_completed,
    track_subscription_upgraded
)


@pytest.fixture
def tracking_service():
    """Get tracking service instance and clear events"""
    service = UserTrackingService.get_instance()
    service.clear_events()
    service.enable()
    return service


@pytest.mark.asyncio
async def test_track_acquisition_event(tracking_service):
    """Test TRACK-002: Acquisition Event Tracking"""
    # Track landing view
    await tracking_service.track_acquisition(
        event_name=EventName.LANDING_VIEW.value,
        session_id="session123",
        properties={
            "referrer": "google",
            "utm_source": "ads"
        }
    )

    # Verify event was tracked
    events = tracking_service.get_recent_events(limit=1)
    assert len(events) == 1
    assert events[0]["event_name"] == EventName.LANDING_VIEW.value
    assert events[0]["session_id"] == "session123"
    assert events[0]["properties"]["referrer"] == "google"
    assert events[0]["category"] == EventCategory.ACQUISITION.value


@pytest.mark.asyncio
async def test_track_activation_event(tracking_service):
    """Test TRACK-003: Activation Event Tracking"""
    user_id = "user123"

    # Track login success
    await track_login_success(user_id, login_method="email", session_id="session123")

    # Track platform connected
    await track_platform_connected(user_id, platform="twitter", session_id="session123")

    # Track activation complete
    await track_activation_complete(user_id, session_id="session123")

    # Verify events
    events = tracking_service.get_events_by_user(user_id)
    assert len(events) == 3

    # Check login event
    login_event = next(e for e in events if e["event_name"] == EventName.LOGIN_SUCCESS.value)
    assert login_event["user_id"] == user_id
    assert login_event["properties"]["login_method"] == "email"

    # Check platform connected event
    platform_event = next(e for e in events if e["event_name"] == EventName.PLATFORM_CONNECTED.value)
    assert platform_event["properties"]["platform"] == "twitter"

    # Check activation complete event
    activation_event = next(e for e in events if e["event_name"] == EventName.ACTIVATION_COMPLETE.value)
    assert activation_event["user_id"] == user_id


@pytest.mark.asyncio
async def test_track_core_value_events(tracking_service):
    """Test TRACK-004: Core Value Event Tracking"""
    user_id = "user123"

    # Track post created
    await track_post_created(user_id, post_id="post123", platform="twitter")

    # Track post scheduled
    await track_post_scheduled(
        user_id,
        post_id="post123",
        platform="twitter",
        scheduled_time="2026-01-26T12:00:00Z"
    )

    # Track post published
    await track_post_published(user_id, post_id="post123", platform="twitter")

    # Track media uploaded
    await track_media_uploaded(
        user_id,
        media_id="media123",
        media_type="video",
        file_size=1024000
    )

    # Track template used
    await track_template_used(
        user_id,
        template_id="tpl123",
        template_name="Problem-Aware Hook"
    )

    # Verify all events tracked
    events = tracking_service.get_events_by_user(user_id)
    assert len(events) == 5

    # Verify post created
    post_created = next(e for e in events if e["event_name"] == EventName.POST_CREATED.value)
    assert post_created["properties"]["post_id"] == "post123"
    assert post_created["properties"]["platform"] == "twitter"

    # Verify post scheduled
    post_scheduled = next(e for e in events if e["event_name"] == EventName.POST_SCHEDULED.value)
    assert post_scheduled["properties"]["scheduled_time"] == "2026-01-26T12:00:00Z"

    # Verify post published
    post_published = next(e for e in events if e["event_name"] == EventName.POST_PUBLISHED.value)
    assert post_published["properties"]["platform"] == "twitter"

    # Verify media uploaded
    media_uploaded = next(e for e in events if e["event_name"] == EventName.MEDIA_UPLOADED.value)
    assert media_uploaded["properties"]["media_type"] == "video"
    assert media_uploaded["properties"]["file_size"] == 1024000

    # Verify template used
    template_used = next(e for e in events if e["event_name"] == EventName.TEMPLATE_USED.value)
    assert template_used["properties"]["template_name"] == "Problem-Aware Hook"


@pytest.mark.asyncio
async def test_track_monetization_events(tracking_service):
    """Test TRACK-005: Monetization Event Tracking"""
    user_id = "user123"

    # Track checkout started
    await track_checkout_started(user_id, plan="pro", price=29.99)

    # Track purchase completed
    await track_purchase_completed(
        user_id,
        plan="pro",
        price=29.99,
        transaction_id="txn123"
    )

    # Track subscription upgraded
    await track_subscription_upgraded(
        user_id,
        from_plan="pro",
        to_plan="enterprise",
        price_delta=70.00
    )

    # Verify all events tracked
    events = tracking_service.get_events_by_user(user_id)
    assert len(events) == 3

    # Verify checkout started
    checkout = next(e for e in events if e["event_name"] == EventName.CHECKOUT_STARTED.value)
    assert checkout["properties"]["plan"] == "pro"
    assert checkout["properties"]["price"] == 29.99

    # Verify purchase completed
    purchase = next(e for e in events if e["event_name"] == EventName.PURCHASE_COMPLETED.value)
    assert purchase["properties"]["transaction_id"] == "txn123"

    # Verify subscription upgraded
    upgrade = next(e for e in events if e["event_name"] == EventName.SUBSCRIPTION_UPGRADED.value)
    assert upgrade["properties"]["from_plan"] == "pro"
    assert upgrade["properties"]["to_plan"] == "enterprise"
    assert upgrade["properties"]["price_delta"] == 70.00


@pytest.mark.asyncio
async def test_get_events_by_name(tracking_service):
    """Test filtering events by name"""
    user_id = "user123"

    # Track multiple events
    await track_post_created(user_id, post_id="post1", platform="twitter")
    await track_post_created(user_id, post_id="post2", platform="instagram")
    await track_media_uploaded(user_id, media_id="media1", media_type="image")

    # Get only post_created events
    post_events = tracking_service.get_events_by_name(EventName.POST_CREATED.value)
    assert len(post_events) == 2
    assert all(e["event_name"] == EventName.POST_CREATED.value for e in post_events)

    # Get only media_uploaded events
    media_events = tracking_service.get_events_by_name(EventName.MEDIA_UPLOADED.value)
    assert len(media_events) == 1
    assert media_events[0]["properties"]["media_type"] == "image"


@pytest.mark.asyncio
async def test_enable_disable_tracking(tracking_service):
    """Test enabling/disabling tracking"""
    user_id = "user123"

    # Tracking enabled by default
    await track_post_created(user_id, post_id="post1", platform="twitter")
    assert len(tracking_service.get_recent_events()) == 1

    # Disable tracking
    tracking_service.disable()
    await track_post_created(user_id, post_id="post2", platform="twitter")
    assert len(tracking_service.get_recent_events()) == 1  # Still 1, not 2

    # Re-enable tracking
    tracking_service.enable()
    await track_post_created(user_id, post_id="post3", platform="twitter")
    assert len(tracking_service.get_recent_events()) == 2  # Now 2


@pytest.mark.asyncio
async def test_event_memory_limit(tracking_service):
    """Test that event history is limited"""
    user_id = "user123"

    # Track more than max events (1000)
    for i in range(1100):
        await track_post_created(user_id, post_id=f"post{i}", platform="twitter")

    # Should only keep last 1000
    events = tracking_service.get_recent_events(limit=2000)
    assert len(events) == 1000

    # Oldest event should be post100, not post0
    oldest_event = events[0]
    assert oldest_event["properties"]["post_id"] == "post100"


@pytest.mark.asyncio
async def test_tracking_event_structure(tracking_service):
    """Test that tracking events have correct structure"""
    user_id = "user123"

    await tracking_service.track(
        event_name="test_event",
        user_id=user_id,
        session_id="session123",
        properties={"key": "value"},
        platform="web",
        category="test"
    )

    events = tracking_service.get_recent_events(limit=1)
    event = events[0]

    # Verify all required fields
    assert "event_name" in event
    assert "timestamp" in event
    assert "user_id" in event
    assert "session_id" in event
    assert "properties" in event
    assert "platform" in event
    assert "category" in event

    # Verify timestamp is valid ISO format
    timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    assert isinstance(timestamp, datetime)


@pytest.mark.asyncio
async def test_track_retention_events(tracking_service):
    """Test TRACK-006: Retention Event Tracking"""
    user_id = "user123"
    session_id = "session123"

    # Track user returned event
    await tracking_service.track_retention(
        event_name=EventName.USER_RETURNED.value,
        user_id=user_id,
        session_id=session_id,
        properties={
            "days_since_last_visit": 3,
            "previous_session_id": "session100"
        }
    )

    # Track feature adopted event
    await tracking_service.track_retention(
        event_name=EventName.FEATURE_ADOPTED.value,
        user_id=user_id,
        session_id=session_id,
        properties={
            "feature_name": "ai_templates",
            "usage_count": 3,
            "first_used_at": "2026-01-20T10:00:00Z"
        }
    )

    # Verify events tracked
    events = tracking_service.get_events_by_user(user_id)
    assert len(events) == 2

    # Verify user returned event
    user_returned = next(e for e in events if e["event_name"] == EventName.USER_RETURNED.value)
    assert user_returned["category"] == EventCategory.RETENTION.value
    assert user_returned["properties"]["days_since_last_visit"] == 3

    # Verify feature adopted event
    feature_adopted = next(e for e in events if e["event_name"] == EventName.FEATURE_ADOPTED.value)
    assert feature_adopted["category"] == EventCategory.RETENTION.value
    assert feature_adopted["properties"]["feature_name"] == "ai_templates"
    assert feature_adopted["properties"]["usage_count"] == 3


@pytest.mark.asyncio
async def test_track_error_events(tracking_service):
    """Test TRACK-007: Error Event Tracking"""
    user_id = "user123"
    session_id = "session123"

    # Track error event
    await tracking_service.track_error(
        error_message="Failed to publish post to Twitter",
        error_code="API_TIMEOUT",
        user_id=user_id,
        session_id=session_id,
        properties={
            "endpoint": "/api/publishing/publish",
            "platform": "twitter",
            "post_id": "post123",
            "retry_count": 3
        }
    )

    # Verify error event tracked
    events = tracking_service.get_events_by_user(user_id)
    assert len(events) == 1

    error_event = events[0]
    assert error_event["event_name"] == EventName.ERROR_OCCURRED.value
    assert error_event["category"] == EventCategory.ERROR.value
    assert error_event["properties"]["error_message"] == "Failed to publish post to Twitter"
    assert error_event["properties"]["error_code"] == "API_TIMEOUT"
    assert error_event["properties"]["platform"] == "twitter"
    assert error_event["properties"]["retry_count"] == 3


@pytest.mark.asyncio
async def test_track_performance_metrics(tracking_service):
    """Test TRACK-007: Performance Metric Tracking"""
    user_id = "user123"
    session_id = "session123"

    # Track API latency
    await tracking_service.track_performance(
        metric_name="api_latency",
        metric_value=145.5,
        user_id=user_id,
        session_id=session_id,
        properties={
            "endpoint": "/api/posts/create",
            "method": "POST",
            "status_code": 200
        }
    )

    # Track page load time
    await tracking_service.track_performance(
        metric_name="page_load_time",
        metric_value=1230.0,
        session_id=session_id,
        properties={
            "page_url": "/dashboard",
            "browser": "chrome"
        }
    )

    # Track Core Web Vitals
    await tracking_service.track_performance(
        metric_name="lcp",
        metric_value=2100.0,
        session_id=session_id,
        properties={
            "page_url": "/dashboard"
        }
    )

    # Verify performance events tracked
    events = tracking_service.get_recent_events()
    assert len(events) == 3

    # Verify API latency event
    api_latency = next(e for e in events if e["properties"]["metric_name"] == "api_latency")
    assert api_latency["event_name"] == EventName.API_LATENCY.value
    assert api_latency["category"] == EventCategory.PERFORMANCE.value
    assert api_latency["properties"]["metric_value"] == 145.5
    assert api_latency["properties"]["unit"] == "ms"
    assert api_latency["properties"]["endpoint"] == "/api/posts/create"

    # Verify page load time event
    page_load = next(e for e in events if e["properties"]["metric_name"] == "page_load_time")
    assert page_load["properties"]["metric_value"] == 1230.0
    assert page_load["properties"]["page_url"] == "/dashboard"

    # Verify LCP event
    lcp = next(e for e in events if e["properties"]["metric_name"] == "lcp")
    assert lcp["properties"]["metric_value"] == 2100.0


@pytest.mark.asyncio
async def test_identify_user(tracking_service):
    """Test TRACK-008: User Identification"""
    user_id = "user123"

    # Identify user with traits
    await tracking_service.identify_user(
        user_id=user_id,
        traits={
            "email": "user@example.com",
            "plan": "pro",
            "name": "John Doe",
            "signup_date": "2026-01-15",
            "platforms_connected": ["twitter", "instagram"],
            "company": "Acme Inc",
            "posts_created": 25
        }
    )

    # Verify identification event tracked
    events = tracking_service.get_events_by_user(user_id)
    assert len(events) == 1

    identify_event = events[0]
    assert identify_event["event_name"] == "user_identified"
    assert identify_event["category"] == "identification"
    assert identify_event["user_id"] == user_id

    # Verify traits stored correctly
    traits = identify_event["properties"]["traits"]
    assert traits["email"] == "user@example.com"
    assert traits["plan"] == "pro"
    assert traits["name"] == "John Doe"
    assert traits["platforms_connected"] == ["twitter", "instagram"]
    assert traits["posts_created"] == 25

    # Verify timestamp is present
    assert "identified_at" in identify_event["properties"]


@pytest.mark.asyncio
async def test_identify_user_on_login(tracking_service):
    """Test identifying user on login (typical use case)"""
    user_id = "user123"
    session_id = "session123"

    # Simulate login flow
    # 1. Track login success
    await tracking_service.track_activation(
        event_name=EventName.LOGIN_SUCCESS.value,
        user_id=user_id,
        session_id=session_id,
        properties={"login_method": "email"}
    )

    # 2. Identify user with traits
    await tracking_service.identify_user(
        user_id=user_id,
        traits={
            "email": "user@example.com",
            "plan": "pro",
            "last_login": "2026-01-25T14:30:00Z"
        }
    )

    # Verify both events tracked
    events = tracking_service.get_events_by_user(user_id)
    assert len(events) == 2

    # Login event
    login_event = next(e for e in events if e["event_name"] == EventName.LOGIN_SUCCESS.value)
    assert login_event["properties"]["login_method"] == "email"

    # Identify event
    identify_event = next(e for e in events if e["event_name"] == "user_identified")
    assert identify_event["properties"]["traits"]["plan"] == "pro"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
